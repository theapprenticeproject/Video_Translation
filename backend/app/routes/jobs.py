"""
Jobs routes — Stage 3.

POST   /api/jobs                    — create job, enqueue extract_audio
GET    /api/jobs/{job_id}           — poll job status + meta
PATCH  /api/jobs/{job_id}/segments  — save user-edited translations
POST   /api/jobs/{job_id}/approve   — enqueue generate_tts after review
GET    /api/jobs/{job_id}/download  — get signed download URL for processed file
"""

import uuid

import redis
from rq import Queue
from rq.job import Job
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from app.logger import get_logger
from app.services import gcs

log = get_logger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])

TIMEOUT_SHORT = 300     # 5 min 
TIMEOUT_DEFAULT = 600   # 10 min 
TIMEOUT_LONG = 1500     # 25 min 


def _redis_conn() -> redis.Redis:
    return redis.from_url(settings.redis_url)


def _fetch_job(job_id: str) -> Job:
    """Fetch an RQ job by ID, raise 404 if not found."""
    conn = _redis_conn()
    try:
        job = Job.fetch(job_id, connection=conn)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    return job


# --------------------------------------------------------------------------- #
# POST /api/jobs — create a new pipeline job
# --------------------------------------------------------------------------- #

class CreateJobRequest(BaseModel):
    object_name: str   # GCS object name from the upload step
    language: str      # target language code, e.g. "hi", "mr", "pa"
    voice_id: str      # ElevenLabs voice ID for TTS


class CreateJobResponse(BaseModel):
    job_id: str


@router.post(
    "",
    response_model=CreateJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a translation job",
)
def create_job(body: CreateJobRequest) -> CreateJobResponse:
    job_id = uuid.uuid4().hex[:12]
    log.info("Creating job %s for object=%s lang=%s voice=%s",
             job_id, body.object_name, body.language, body.voice_id)

    meta = {
        "status": "processing",
        "stage": "extracting",
        "error": None,
        "gcs_original": body.object_name,
        "gcs_audio": None,
        "gcs_processed": None,
        "language": body.language,
        "voice_id": body.voice_id,
        "segments": [],
    }

    conn = _redis_conn()
    q = Queue("default", connection=conn)
    q.enqueue(
        "app.tasks.audio.extract_audio",
        job_id,
        job_id=job_id,
        meta=meta,
        job_timeout=TIMEOUT_SHORT,
    )

    log.info("Job %s enqueued", job_id)
    return CreateJobResponse(job_id=job_id)


# --------------------------------------------------------------------------- #
# GET /api/jobs/{job_id} — poll job status
# --------------------------------------------------------------------------- #

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    stage: str
    error: str | None = None
    gcs_original: str | None = None
    gcs_processed: str | None = None
    language: str | None = None
    voice_id: str | None = None
    segments: list[dict] = []


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status and metadata",
)
def get_job_status(job_id: str) -> JobStatusResponse:
    job = _fetch_job(job_id)
    meta = job.meta
    return JobStatusResponse(
        job_id=job_id,
        status=meta.get("status", "unknown"),
        stage=meta.get("stage", "unknown"),
        error=meta.get("error"),
        gcs_original=meta.get("gcs_original"),
        gcs_processed=meta.get("gcs_processed"),
        language=meta.get("language"),
        voice_id=meta.get("voice_id"),
        segments=meta.get("segments", []),
    )


# --------------------------------------------------------------------------- #
# PATCH /api/jobs/{job_id}/segments — save user edits
# --------------------------------------------------------------------------- #

class Segment(BaseModel):
    index: int
    original: str
    translated: str


class UpdateSegmentsRequest(BaseModel):
    segments: list[Segment]


@router.patch(
    "/{job_id}/segments",
    status_code=status.HTTP_200_OK,
    summary="Update translated segments (user edits)",
)
def update_segments(job_id: str, body: UpdateSegmentsRequest) -> dict:
    job = _fetch_job(job_id)

    if job.meta.get("status") != "awaiting_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is in status '{job.meta.get('status')}', not awaiting_review",
        )

    job.meta["segments"] = [seg.model_dump() for seg in body.segments]
    job.save_meta()
    log.info("[%s] Segments updated by user (%d segments)", job_id, len(body.segments))
    return {"detail": "Segments updated"}


# --------------------------------------------------------------------------- #
# POST /api/jobs/{job_id}/approve — enqueue TTS after review
# --------------------------------------------------------------------------- #

@router.post(
    "/{job_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve translations and start TTS",
)
def approve_job(job_id: str) -> dict:
    job = _fetch_job(job_id)

    if job.meta.get("status") != "awaiting_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is in status '{job.meta.get('status')}', not awaiting_review",
        )

    job.meta["status"] = "processing"
    job.meta["stage"] = "generating_tts"
    job.save_meta()

    conn = _redis_conn()
    q = Queue("default", connection=conn)
    q.enqueue(
        "app.tasks.tts.generate_tts",
        job_id,
        job_id=f"{job_id}_tts",
        meta=job.meta,
        job_timeout=TIMEOUT_LONG,
    )

    log.info("[%s] Approved — TTS enqueued", job_id)
    return {"detail": "TTS generation started"}


# --------------------------------------------------------------------------- #
# GET /api/jobs/{job_id}/download — signed download URL
# --------------------------------------------------------------------------- #

class DownloadResponse(BaseModel):
    download_url: str


@router.get(
    "/{job_id}/download",
    response_model=DownloadResponse,
    summary="Get download URL for processed audio",
)
def get_download_url(job_id: str) -> DownloadResponse:
    job = _fetch_job(job_id)

    if job.meta.get("status") != "complete":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not complete (status={job.meta.get('status')})",
        )

    gcs_processed = job.meta.get("gcs_processed")
    if not gcs_processed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No processed file found",
        )

    download_url = gcs.get_signed_download_url(gcs_processed)
    log.info("[%s] Download URL generated", job_id)
    return DownloadResponse(download_url=download_url)
