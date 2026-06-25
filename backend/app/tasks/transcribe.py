"""
Task 2 — Transcribe audio using ElevenLabs STT (Scribe v2).

Generates a signed GCS URL for the extracted mp3 and passes it
directly to ElevenLabs STT via cloud_storage_url — no file download needed.
Stores timestamped segments in job.meta, enqueues translate.
"""

import redis
from rq import Queue
from rq.job import Job

from app.config import settings
from app.logger import get_logger
from app.services import gcs, elevenlabs

log = get_logger(__name__)


def transcribe(job_id: str) -> None:
    conn = redis.from_url(settings.redis_url)
    # Always fetch and update the ROOT job so polling /api/jobs/{job_id} reflects reality
    job = Job.fetch(job_id, connection=conn)

    try:
        job.meta["stage"] = "transcribing"
        job.save_meta()
        log.info("[%s] Starting transcription", job_id)

        # Generate a signed URL for the extracted mp3 in GCS —
        # ElevenLabs STT accepts cloud_storage_url directly
        audio_object = job.meta["gcs_audio"]
        audio_url = gcs.get_signed_download_url(audio_object, expiry_minutes=30)

        # Send signed URL to ElevenLabs STT
        segments = elevenlabs.speech_to_text(audio_url)

        # Store segments in root job meta
        job.meta["segments"] = [
            {
                "index": i,
                "original": seg["text"],
                "translated": "",
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
            }
            for i, seg in enumerate(segments)
        ]
        job.meta["stage"] = "translating"
        job.save_meta()

        log.info("[%s] Transcription complete (%d segments), enqueuing translate",
                 job_id, len(segments))

        q = Queue("default", connection=conn)
        q.enqueue(
            "app.tasks.translate.translate_segments",
            job_id,
            job_id=f"{job_id}_translate",
            meta=job.meta,
            job_timeout=900,
        )

    except Exception as exc:
        log.error("[%s] Transcription failed: %s", job_id, exc, exc_info=True)
        job.meta["status"] = "failed"
        job.meta["error"] = str(exc)
        job.save_meta()
