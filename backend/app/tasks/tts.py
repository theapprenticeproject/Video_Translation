"""
Task 4 — Generate TTS audio using ElevenLabs (eleven_v3) segment by segment.

Reads approved (possibly user-edited) segments from the ROOT job meta,
generates TTS audio for each segment using its specific voice and settings (speed, stability, style),
mixes them together using ffmpeg at their correct timestamps (using adelay/amix),
and uploads the mixed mp3 back to GCS.
"""

import os
import subprocess
import tempfile
import redis
from rq.job import Job

from app.config import settings
from app.logger import get_logger
from app.services import gcs, elevenlabs
from app.services.db import save_job_meta, get_job_meta

log = get_logger(__name__)


def generate_tts(job_id: str) -> None:
    conn = redis.from_url(settings.redis_url)
    
    # Try to fetch the RQ job, but do NOT crash if it has expired from Redis
    try:
        job = Job.fetch(job_id, connection=conn)
    except Exception:
        log.warning("[%s] RQ Job not found (might have expired). Using persistent DB instead.", job_id)
        job = None

    try:
        # Fetch meta from persistent store
        meta = get_job_meta(job_id)
        if not meta:
            # Fallback to job.meta if DB meta is somehow missing
            if job:
                meta = job.meta
            else:
                raise RuntimeError(f"Job metadata for {job_id} not found in DB or RQ")

        meta["status"] = "processing"
        meta["stage"] = "generating_tts"
        save_job_meta(job_id, meta)
        
        if job:
            job.meta.update(meta)
            job.save_meta()

        log.info("[%s] Starting multi-speaker/multi-setting TTS generation", job_id)

        segments = meta.get("segments", [])
        default_voice_id = meta.get("voice_id", "")

        with tempfile.TemporaryDirectory() as tmp_dir:
            delayed_inputs = []
            
            for seg in segments:
                text = seg.get("translated", "").strip()
                if not text:
                    log.info("[%s] Skipping segment %d: empty translation", job_id, seg["index"])
                    continue
                
                # Fetch settings for this segment or use defaults
                seg_voice_id = seg.get("voice_id") or default_voice_id
                speed = seg.get("speed")
                if speed is None:
                    speed = 1.0
                stability = seg.get("stability")
                if stability is None:
                    stability = 0.5
                style = seg.get("style")
                if style is None:
                    style = 0.0
                
                log.info(
                    "[%s] Generating segment %d: voice=%s speed=%.2f stability=%.2f style=%.2f text='%s'",
                    job_id, seg["index"], seg_voice_id, speed, stability, style, text[:30]
                )
                
                try:
                    audio_bytes = elevenlabs.text_to_speech_with_settings(
                        text=text,
                        voice_id=seg_voice_id,
                        stability=stability,
                        style=style,
                        speed=speed,
                    )
                except Exception as e:
                    log.error("[%s] Failed to generate TTS for segment %d: %s", job_id, seg["index"], e)
                    raise RuntimeError(f"ElevenLabs TTS failed for segment {seg['index']}: {e}")
                
                # Save to temp file
                seg_file_path = os.path.join(tmp_dir, f"seg_{seg['index']}.mp3")
                with open(seg_file_path, "wb") as f:
                    f.write(audio_bytes)
                
                delay_ms = int(seg.get("start", 0.0) * 1000)
                if delay_ms < 0:
                    delay_ms = 0
                    
                delayed_inputs.append({"file": seg_file_path, "delay": delay_ms})

            output_path = os.path.join(tmp_dir, "output.mp3")

            if not delayed_inputs:
                log.warning("[%s] No segments with translations to synthesize", job_id)
                # Create a 1-second silent audio file
                cmd = ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1", "-y", output_path]
                subprocess.run(cmd, check=True)
            elif len(delayed_inputs) == 1:
                # Single segment
                item = delayed_inputs[0]
                if item["delay"] == 0:
                    output_path = item["file"]
                else:
                    cmd = [
                        "ffmpeg", "-i", item["file"],
                        "-filter_complex", f"[0:a]adelay={item['delay']}|{item['delay']}",
                        "-y", output_path
                    ]
                    subprocess.run(cmd, check=True)
            else:
                # Multiple segments — construct inputs
                cmd = ["ffmpeg"]
                for item in delayed_inputs:
                    cmd.extend(["-i", item["file"]])
                
                # Construct filter complex
                filter_parts = []
                mixed_labels = []
                for idx, item in enumerate(delayed_inputs):
                    filter_parts.append(f"[{idx}:a]adelay={item['delay']}|{item['delay']}[a{idx}]")
                    mixed_labels.append(f"[a{idx}]")
                
                mix_label_str = "".join(mixed_labels)
                filter_parts.append(f"{mix_label_str}amix=inputs={len(delayed_inputs)}:dropout_transition=0:normalize=0")
                
                filter_complex = ";".join(filter_parts)
                cmd.extend(["-filter_complex", filter_complex, "-y", output_path])
                
                log.info("[%s] Running ffmpeg mix with filter: %s", job_id, filter_complex[:200])
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode != 0:
                    raise RuntimeError(f"ffmpeg mixing failed: {result.stderr}")

            # Upload final output to GCS
            bucket_prefix = settings.gcs_bucket_prefix
            processed_object = f"{bucket_prefix}/processed/{job_id}_translated.mp3"
            gcs.upload_from_file(processed_object, output_path, content_type="audio/mpeg")

        # Update root job meta — pipeline complete
        meta["gcs_processed"] = processed_object
        meta["status"] = "complete"
        meta["stage"] = "done"
        save_job_meta(job_id, meta)
        
        if job:
            job.meta.update(meta)
            job.save_meta()

        log.info("[%s] TTS generation and mixing complete — %s", job_id, processed_object)

    except Exception as exc:
        log.error("[%s] TTS generation failed: %s", job_id, exc, exc_info=True)
        # Fetch meta again or use local
        try:
            meta = get_job_meta(job_id) or {}
        except Exception:
            meta = {}
        meta["status"] = "failed"
        meta["error"] = str(exc)
        save_job_meta(job_id, meta)
        
        if job:
            job.meta.update(meta)
            job.save_meta()
