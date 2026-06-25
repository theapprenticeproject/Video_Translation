"""
Task 4 — Generate TTS audio using ElevenLabs (eleven_v3).

Reads approved (possibly user-edited) segments from the ROOT job meta,
concatenates translated text, generates TTS audio, uploads to GCS.
"""

import redis
from rq.job import Job

from app.config import settings
from app.logger import get_logger
from app.services import gcs, elevenlabs

log = get_logger(__name__)


def generate_tts(job_id: str) -> None:
    conn = redis.from_url(settings.redis_url)
    # Always fetch and update the ROOT job so polling /api/jobs/{job_id} reflects reality
    job = Job.fetch(job_id, connection=conn)

    try:
        job.meta["status"] = "processing"
        job.meta["stage"] = "generating_tts"
        job.save_meta()
        log.info("[%s] Starting TTS generation", job_id)

        segments = job.meta["segments"]
        voice_id = job.meta["voice_id"]

        # Concatenate all translated segments into a single text block
        full_text = " ".join(seg["translated"] for seg in segments)

        # Generate audio via ElevenLabs TTS (eleven_v3)
        audio_bytes = elevenlabs.text_to_speech(full_text, voice_id)

        # Build the processed object name
        bucket_prefix = settings.gcs_bucket_prefix
        processed_object = f"{bucket_prefix}/processed/{job_id}_translated.mp3"

        # Upload to GCS
        gcs.upload_bytes(processed_object, audio_bytes, content_type="audio/mpeg")

        # Update root job meta — pipeline complete
        job.meta["gcs_processed"] = processed_object
        job.meta["status"] = "complete"
        job.meta["stage"] = "done"
        job.save_meta()

        log.info("[%s] TTS generation complete — %s", job_id, processed_object)

    except Exception as exc:
        log.error("[%s] TTS generation failed: %s", job_id, exc, exc_info=True)
        job.meta["status"] = "failed"
        job.meta["error"] = str(exc)
        job.save_meta()
