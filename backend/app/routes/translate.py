
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.translator import translate_texts_interactive
from app.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/api/translate", tags=["translate"])

class TranslateSingleRequest(BaseModel):
    text: str
    target_language: str
    source_language: Optional[str] = "en"

class TranslateSingleResponse(BaseModel):
    translated_text: str

@router.post("/single", response_model=TranslateSingleResponse)
def translate_single(req: TranslateSingleRequest):
    if not req.text.strip():
        return TranslateSingleResponse(translated_text="")
        
    try:
        # We use interactive (real-time) API instead of batch for instant UI feedback
        # The prompt in claude.py can be adjusted to enforce conciseness
        translations = translate_texts_interactive(
            texts=[req.text],
            source_language=req.source_language or "en",
            target_language=req.target_language
        )
        
        if not translations:
            return TranslateSingleResponse(translated_text="")
            
        return TranslateSingleResponse(translated_text=translations[0])
    except Exception as exc:
        log.error("Failed to retranslate single segment: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

