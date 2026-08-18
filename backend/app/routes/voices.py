from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.auth import require_auth
from app.services.db import (
    get_user_voices,
    save_user_voice,
    delete_user_voice,
)

router = APIRouter(prefix="/api/voices", tags=["voices"])


class VoiceModel(BaseModel):
    voice_id: str
    name: str
    speed: float = 1.0
    stability: float = 0.5
    style: float = 0.0


@router.get(
    "",
    summary="List all user saved ElevenLabs voices",
)
def list_voices(user_id: str = Depends(require_auth)) -> list[dict]:
    return get_user_voices(user_id)


@router.post(
    "",
    summary="Save or update a custom ElevenLabs voice",
    status_code=status.HTTP_200_OK,
)
def save_voice(voice: VoiceModel, user_id: str = Depends(require_auth)) -> dict:
    save_user_voice(user_id, voice.model_dump())
    return {"detail": "Voice saved successfully"}


@router.delete(
    "/{voice_id}",
    summary="Delete a custom ElevenLabs voice",
    status_code=status.HTTP_200_OK,
)
def delete_voice(voice_id: str, user_id: str = Depends(require_auth)) -> dict:
    delete_user_voice(user_id, voice_id)
    return {"detail": "Voice deleted successfully"}
