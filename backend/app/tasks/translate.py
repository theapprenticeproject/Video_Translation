"""
Task 3 — Translate segments using Bhashini.

Reads the transcribed segments from the ROOT job meta, translates via Bhashini,
stores {original, translated} pairs, then STOPS — sets status to
'awaiting_review' for user HITL editing.
"""

import redis
from rq.job import Job

from app.config import settings
from app.logger import get_logger
from app.services import claude

log = get_logger(__name__)

# Source language for the original audio (assumed Hindi for now)
SOURCE_LANGUAGE = "hi"


def translate_segments(job_id: str) -> None:
    conn = redis.from_url(settings.redis_url)
    # Always fetch and update the ROOT job so polling /api/jobs/{job_id} reflects reality
    job = Job.fetch(job_id, connection=conn)

    try:
        job.meta["stage"] = "translating"
        job.save_meta()
        log.info("[%s] Starting translation", job_id)

        segments = job.meta["segments"]
        target_language = job.meta["language"]

        # Batch translate all segment texts using Claude
        original_texts = [seg["original"] for seg in segments]
        translated_texts = claude.translate_texts(
            original_texts,
            source_language=SOURCE_LANGUAGE,
            target_language=target_language,
        )

        # Update segments with translations
        for seg, translated in zip(segments, translated_texts):
            seg["translated"] = translated

        job.meta["segments"] = segments
        job.meta["status"] = "awaiting_review"
        job.meta["stage"] = "awaiting_review"
        job.save_meta()

        log.info("[%s] Translation complete, awaiting user review", job_id)
        # STOP here — do NOT enqueue next task.
        # User reviews/edits segments in UI, then calls POST /approve
        # which enqueues generate_tts.

    except Exception as exc:
        log.error("[%s] Translation failed: %s", job_id, exc, exc_info=True)
        job.meta["status"] = "failed"
        job.meta["error"] = str(exc)
        job.save_meta()
