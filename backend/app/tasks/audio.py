"""
Task 1 — Extract audio from uploaded media file.

Downloads the original from GCS, uses ffmpeg to extract audio as mp3,
uploads the extracted mp3 back to GCS, then enqueues the transcribe task.
"""

import os
import subprocess
import tempfile

import redis
from rq import Queue, get_current_job

from app.config import settings
from app.logger import get_logger
from app.services import gcs
from app.services.db import save_job_meta

log = get_logger(__name__)


def extract_audio(job_id: str) -> None:
    job = get_current_job()
    conn = redis.from_url(settings.redis_url)

    try:
        job.meta["stage"] = "extracting"
        job.save_meta()
        save_job_meta(job_id, job.meta)
        log.info("[%s] Starting audio extraction", job_id)

        gcs_original = job.meta["gcs_original"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Download original file from GCS
            input_data = gcs.download_blob_to_bytes(gcs_original)
            input_ext = os.path.splitext(gcs_original)[1] or ".mp4"
            input_path = os.path.join(tmp_dir, f"input{input_ext}")
            with open(input_path, "wb") as f:
                f.write(input_data)

            # Run ffmpeg to extract audio
            output_path = os.path.join(tmp_dir, f"{job_id}.mp3")
            cmd = [
                "ffmpeg", "-i", input_path,
                "-vn", "-acodec", "libmp3lame",
                "-y", output_path,
            ]
            log.info("[%s] Running: %s", job_id, " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result.stderr}")

            # Upload extracted mp3 back to GCS
            audio_object_name = gcs_original.rsplit(".", 1)[0] + ".mp3"
            gcs.upload_from_file(audio_object_name, output_path, content_type="audio/mpeg")

        # Update meta and enqueue next task
        job.meta["gcs_audio"] = audio_object_name
        job.meta["stage"] = "transcribing"
        job.save_meta()
        save_job_meta(job_id, job.meta)

        log.info("[%s] Audio extraction complete, enqueuing transcribe", job_id)
        q = Queue("default", connection=conn)
        q.enqueue(
            "app.tasks.transcribe.transcribe",
            job_id,
            job_id=f"{job_id}_transcribe",
            meta=job.meta,
            job_timeout=1500,
        )

    except Exception as exc:
        log.error("[%s] Audio extraction failed: %s", job_id, exc, exc_info=True)
        job.meta["status"] = "failed"
        job.meta["error"] = str(exc)
        job.save_meta()
        save_job_meta(job_id, job.meta)
