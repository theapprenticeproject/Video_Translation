"""
ElevenLabs service wrapper — STT and TTS.

Uses the official `elevenlabs` Python SDK.
STT: Scribe v2 — supports cloud_storage_url (signed GCS URLs)
TTS: eleven_v3 — latest model, 70+ languages
"""

from elevenlabs import ElevenLabs, VoiceSettings

from app.config import settings
from app.logger import get_logger

log = get_logger(__name__)

_client: ElevenLabs | None = None


def _get_client() -> ElevenLabs:
    """Lazy singleton for the ElevenLabs SDK client."""
    global _client
    if _client is None:
        _client = ElevenLabs(api_key=settings.elevenlabs_api_key)
        log.info("ElevenLabs SDK client initialised")
    return _client


def speech_to_text(audio_url: str) -> list[dict]:
    """
    Transcribe audio via ElevenLabs Scribe v2.

    Accepts a cloud_storage_url (e.g. signed GCS URL) — no file download needed.
    Returns list of segments: [{"text": "...", "start": 0.0, "end": 2.5}, ...]
    """
    log.info("ElevenLabs STT: transcribing from URL")
    client = _get_client()

    result = client.speech_to_text.convert(
        cloud_storage_url=audio_url,
        model_id="scribe_v2",
        timestamps_granularity="word",
    )

    # Group word-level results into sentence segments
    segments: list[dict] = []
    current_text: list[str] = []
    current_start: float | None = None
    current_end: float = 0

    for word_info in result.words or []:
        if word_info.type != "word":
            continue

        word_text = word_info.text or ""
        start = word_info.start or 0
        end = word_info.end or 0

        if current_start is None:
            current_start = start
        current_end = end
        current_text.append(word_text)

        # Split on sentence-ending punctuation
        stripped = word_text.rstrip()
        if stripped.endswith((".", "!", "?", "।")):
            segments.append({
                "text": " ".join(current_text).strip(),
                "start": current_start,
                "end": current_end,
            })
            current_text = []
            current_start = None
            current_end = 0

    # Flush remaining words as a final segment
    if current_text:
        segments.append({
            "text": " ".join(current_text).strip(),
            "start": current_start or 0,
            "end": current_end,
        })

    log.info("ElevenLabs STT: got %d segments", len(segments))
    return segments


def text_to_speech(text: str, voice_id: str) -> bytes:
    """
    Generate speech from text via ElevenLabs TTS (eleven_v3).
    Returns raw audio bytes (mp3).
    """
    log.info("ElevenLabs TTS: generating audio for voice=%s, text_len=%d",
             voice_id, len(text))
    client = _get_client()

    audio_iter = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_v3",
    )

    # Collect all chunks into bytes
    audio_bytes = b"".join(audio_iter)

    log.info("ElevenLabs TTS: received %d bytes of audio", len(audio_bytes))
    return audio_bytes


def text_to_speech_with_settings(
    text: str,
    voice_id: str,
    stability: float = 0.5,
    style: float = 0.0,
    speed: float = 1.0,
) -> bytes:
    """
    Generate speech from text via ElevenLabs TTS (eleven_v3) with speed and voice settings.
    Returns raw audio bytes (mp3).
    """
    log.info("ElevenLabs TTS settings: generating audio for voice=%s, text_len=%d, speed=%.2f, stability=%.2f, style=%.2f",
             voice_id, len(text), speed, stability, style)
    client = _get_client()

    settings = VoiceSettings(
        stability=stability,
        similarity_boost=0.75,
        style=style,
        use_speaker_boost=True,
        speed=speed,
    )

    audio_iter = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_v3",
        voice_settings=settings,
    )

    # Collect all chunks into bytes
    audio_bytes = b"".join(audio_iter)

    log.info("ElevenLabs TTS settings: received %d bytes of audio", len(audio_bytes))
    return audio_bytes

