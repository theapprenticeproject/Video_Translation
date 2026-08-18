import json
import redis
from app.config import settings
from app.logger import get_logger

log = get_logger(__name__)

def _redis_conn() -> redis.Redis:
    return redis.from_url(settings.redis_url)

def save_job_meta(job_id: str, meta: dict) -> None:
    conn = _redis_conn()
    conn.set(f"job:meta:{job_id}", json.dumps(meta))

def get_job_meta(job_id: str) -> dict | None:
    conn = _redis_conn()
    data = conn.get(f"job:meta:{job_id}")
    if data:
        return json.loads(data.decode("utf-8"))
    return None

def add_user_job(user_id: str, job_id: str) -> None:
    conn = _redis_conn()
    key = f"user:jobs:{user_id}"
    conn.lrem(key, 0, job_id)
    conn.lpush(key, job_id)

def get_user_jobs(user_id: str) -> list[str]:
    conn = _redis_conn()
    job_ids = conn.lrange(f"user:jobs:{user_id}", 0, -1)
    return [jid.decode("utf-8") for jid in job_ids]

def save_user_voice(user_id: str, voice: dict) -> None:
    conn = _redis_conn()
    key = f"user:voices:{user_id}"
    conn.hset(key, voice["voice_id"], json.dumps(voice))

def get_user_voices(user_id: str) -> list[dict]:
    conn = _redis_conn()
    key = f"user:voices:{user_id}"
    
    # Self-healing cleanup: Delete the incorrect cached Liam ID from Redis if it exists
    conn.hdel(key, "TX3293t7o4WbqthJuOC3")
    
    voices = conn.hgetall(key)
    result = []
    
    # 1. Fetch custom voices from Redis database
    for k, v in voices.items():
        try:
            val = json.loads(v.decode("utf-8"))
            result.append(val)
        except Exception:
            result.append({
                "voice_id": k.decode("utf-8"),
                "name": k.decode("utf-8"),
                "speed": 1.0,
                "stability": 0.5,
                "style": 0.0
            })
    
    # 2. Query ElevenLabs dynamically to get all available preset and custom voices on their account!
    try:
        from app.services.elevenlabs import _get_client
        client = _get_client()
        res = client.voices.get_all()
        el_voices = getattr(res, "voices", [])
        
        for v in el_voices:
            # Check if this voice is already in our list to prevent duplicates
            if not any(cv["voice_id"] == v.voice_id for cv in result):
                result.append({
                    "voice_id": v.voice_id,
                    "name": v.name,
                    "speed": 1.0,
                    "stability": 0.5,
                    "style": 0.0
                })
    except Exception as exc:
        log.warning("Failed to fetch voices dynamically from ElevenLabs: %s. Using fallback presets.", exc)
        
    # 3. Always include correct preset fallbacks (if they are not already in the list)
    # We do NOT save these in Redis so they can be easily updated in code later
    default_voices = [
        {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel (Female)", "speed": 1.0, "stability": 0.5, "style": 0.0},
        {"voice_id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi (Female)", "speed": 1.0, "stability": 0.5, "style": 0.0},
        {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella (Female)", "speed": 1.0, "stability": 0.5, "style": 0.0},
        {"voice_id": "ErXwobaYiN019PkySvjV", "name": "Antoni (Male)", "speed": 1.0, "stability": 0.5, "style": 0.0},
        {"voice_id": "TX3LPaxmHKxFdv7VOQHJ", "name": "Liam (Male)", "speed": 1.0, "stability": 0.5, "style": 0.0},
    ]
    for v in default_voices:
        if not any(cv["voice_id"] == v["voice_id"] for cv in result):
            result.append(v)
        
    return result

def delete_user_voice(user_id: str, voice_id: str) -> None:
    conn = _redis_conn()
    key = f"user:voices:{user_id}"
    conn.hdel(key, voice_id)
