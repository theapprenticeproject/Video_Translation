"""
Jobs routes — Stage 3.

POST   /api/jobs                    — create job, enqueue extract_audio
GET    /api/jobs                    — list all past jobs
GET    /api/jobs/{job_id}           — poll job status + meta
PATCH  /api/jobs/{job_id}/segments  — save user-edited translations
POST   /api/jobs/{job_id}/approve   — enqueue generate_tts after review
GET    /api/jobs/{job_id}/download  — get signed download URL for processed file
"""

import time
import uuid

import redis
from rq import Queue
from rq.job import Job
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import require_auth
from app.config import settings
from app.logger import get_logger
from app.services import gcs
from app.services.db import (
    save_job_meta,
    get_job_meta,
    add_user_job,
    get_user_jobs,
)

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
    object_name: str        # GCS object name from the upload step
    source_language: str = "hi"  # source language of video audio
    language: str           # target language code, e.g. "hi", "mr", "pa", "kn", "en"
    voice_id: str           # ElevenLabs voice ID for TTS


class CreateJobResponse(BaseModel):
    job_id: str


@router.post(
    "",
    response_model=CreateJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a translation job",
)
def create_job(body: CreateJobRequest, user_id: str = Depends(require_auth)) -> CreateJobResponse:
    job_id = uuid.uuid4().hex[:12]
    log.info("Creating job %s for object=%s source=%s target=%s voice=%s",
             job_id, body.object_name, body.source_language, body.language, body.voice_id)

    meta = {
        "status": "processing",
        "stage": "extracting",
        "error": None,
        "gcs_original": body.object_name,
        "gcs_audio": None,
        "gcs_processed": None,
        "source_language": body.source_language,
        "language": body.language,
        "voice_id": body.voice_id,
        "segments": [],
        "created_at": time.time(),
        "filename": body.object_name.split("/")[-1],
    }

    # Save initial state in persistent store & link to user
    save_job_meta(job_id, meta)
    add_user_job(user_id, job_id)

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
# GET /api/jobs — list all past translation jobs
# --------------------------------------------------------------------------- #

class JobHistoryItem(BaseModel):
    job_id: str
    status: str
    stage: str
    error: str | None = None
    filename: str
    created_at: float
    source_language: str
    language: str
    voice_id: str


@router.get(
    "",
    response_model=list[JobHistoryItem],
    summary="List all past translation jobs",
)
def list_jobs(user_id: str = Depends(require_auth)) -> list[JobHistoryItem]:
    job_ids = get_user_jobs(user_id)
    result = []
    for jid in job_ids:
        meta = get_job_meta(jid)
        if meta:
            # Sync status if active
            if meta.get("status") not in ("complete", "failed"):
                try:
                    conn = _redis_conn()
                    rq_job = Job.fetch(jid, connection=conn)
                    if rq_job and rq_job.meta:
                        meta.update(rq_job.meta)
                        save_job_meta(jid, meta)
                except Exception:
                    pass
            
            result.append(JobHistoryItem(
                job_id=jid,
                status=meta.get("status", "unknown"),
                stage=meta.get("stage", "unknown"),
                error=meta.get("error"),
                filename=meta.get("filename", meta.get("gcs_original", "unknown.mp4").split("/")[-1]),
                created_at=meta.get("created_at", 0.0),
                source_language=meta.get("source_language", "hi"),
                language=meta.get("language", "mr"),
                voice_id=meta.get("voice_id", ""),
            ))
    return result


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
    source_language: str | None = None
    language: str | None = None
    voice_id: str | None = None
    segments: list[dict] = []


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status and metadata",
)
def get_job_status(job_id: str, user_id: str = Depends(require_auth)) -> JobStatusResponse:
    meta = get_job_meta(job_id)
    if not meta:
        # Fallback to RQ fetch just in case it exists there but not in DB
        try:
            job = _fetch_job(job_id)
            meta = job.meta
            if meta:
                save_job_meta(job_id, meta)
                add_user_job(user_id, job_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # Sync with RQ if still active
    if meta.get("status") not in ("complete", "failed"):
        try:
            job = _fetch_job(job_id)
            if job and job.meta:
                meta.update(job.meta)
                save_job_meta(job_id, meta)
        except Exception:
            pass

    return JobStatusResponse(
        job_id=job_id,
        status=meta.get("status", "unknown"),
        stage=meta.get("stage", "unknown"),
        error=meta.get("error"),
        gcs_original=meta.get("gcs_original"),
        gcs_processed=meta.get("gcs_processed"),
        source_language=meta.get("source_language", "hi"),
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
    start: float
    end: float
    voice_id: str | None = None
    speed: float | None = None
    stability: float | None = None
    style: float | None = None


class UpdateSegmentsRequest(BaseModel):
    segments: list[Segment]


@router.patch(
    "/{job_id}/segments",
    status_code=status.HTTP_200_OK,
    summary="Update translated segments (user edits)",
)
def update_segments(job_id: str, body: UpdateSegmentsRequest, user_id: str = Depends(require_auth)) -> dict:
    meta = get_job_meta(job_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found in DB",
        )

    if meta.get("status") != "awaiting_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is in status '{meta.get('status')}', not awaiting_review",
        )

    meta["segments"] = [seg.model_dump() for seg in body.segments]
    save_job_meta(job_id, meta)

    # Sync to RQ job if it still exists
    try:
        job = _fetch_job(job_id)
        job.meta["segments"] = meta["segments"]
        job.save_meta()
    except Exception:
        pass

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
def approve_job(job_id: str, user_id: str = Depends(require_auth)) -> dict:
    meta = get_job_meta(job_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found in DB",
        )

    if meta.get("status") != "awaiting_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is in status '{meta.get('status')}', not awaiting_review",
        )

    meta["status"] = "processing"
    meta["stage"] = "generating_tts"
    save_job_meta(job_id, meta)

    # Sync to RQ job if it still exists
    try:
        job = _fetch_job(job_id)
        job.meta["status"] = "processing"
        job.meta["stage"] = "generating_tts"
        job.save_meta()
    except Exception:
        pass

    conn = _redis_conn()
    q = Queue("default", connection=conn)
    q.enqueue(
        "app.tasks.tts.generate_tts",
        job_id,
        job_id=f"{job_id}_tts",
        meta=meta,
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
def get_download_url(job_id: str, user_id: str = Depends(require_auth)) -> DownloadResponse:
    meta = get_job_meta(job_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found in DB",
        )

    if meta.get("status") != "complete":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not complete (status={meta.get('status')})",
        )

    gcs_processed = meta.get("gcs_processed")
    if not gcs_processed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No processed file found",
        )

    download_url = gcs.get_signed_download_url(gcs_processed)
    log.info("[%s] Download URL generated", job_id)
    return DownloadResponse(download_url=download_url)
