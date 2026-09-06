"""
TTS Preview route.

POST /api/tts/preview
Returns an audio/mpeg byte stream generated dynamically using ElevenLabs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth import require_auth
from app.logger import get_logger
from app.services import elevenlabs

log = get_logger(__name__)
router = APIRouter(prefix="/api/tts", tags=["tts"])


class TTSPreviewRequest(BaseModel):
    text: str
    voice_id: str
    speed: float = 1.0
    stability: float = 0.5
    style: float = 0.0


@router.post(
    "/preview",
    status_code=status.HTTP_200_OK,
    summary="Generate a live audio preview for a specific segment",
    responses={
        200: {
            "content": {"audio/mpeg": {}},
            "description": "Returns raw mp3 audio bytes.",
        }
    },
)
def generate_preview(body: TTSPreviewRequest, user_id: str = Depends(require_auth)):
    log.info("Live TTS preview requested for voice=%s length=%d", body.voice_id, len(body.text))
    
    if not body.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text cannot be empty.",
        )
        
    try:
        audio_bytes = elevenlabs.text_to_speech_with_settings(
            text=body.text,
            voice_id=body.voice_id,
            stability=body.stability,
            style=body.style,
            speed=body.speed,
        )
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as exc:
        log.error("Failed to generate live TTS preview: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate live preview audio. Check ElevenLabs quota or Voice ID.",
        ) from exc
