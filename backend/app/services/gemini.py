"""
Gemini translation service wrapper.

Uses Google Gemini API via REST (httpx) with Structured Outputs (JSON Schema)
for batch and single interactive translations.
"""

import json
import httpx
from typing import List

from app.config import settings
from app.logger import get_logger

log = get_logger(__name__)

LANGUAGE_MAP = {
    "hi": "Hindi",
    "mr": "Marathi",
    "pa": "Punjabi",
    "kn": "Kannada",
    "en": "English",
}

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _get_api_key() -> str:
    key = settings.gemini_api_key
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured in environment settings.")
    return key.strip("'\"")


def _get_model() -> str:
    return getattr(settings, "gemini_model", None) or "gemini-3.1-flash-lite"


def translate_texts(
    texts: List[str],
    source_language: str,
    target_language: str,
) -> List[str]:
    """
    Translate a list of text segments using Gemini with structured JSON output.
    """
    if not texts:
        return []

    api_key = _get_api_key()
    model = _get_model()
    src_name = LANGUAGE_MAP.get(source_language.lower(), source_language)
    tgt_name = LANGUAGE_MAP.get(target_language.lower(), target_language)

    url = f"{GEMINI_API_URL.format(model=model)}?key={api_key}"

    prompt = (
        f"You are a professional video dubbing translator and subtitler. "
        f"Translate the following list of sentences from {src_name} to {tgt_name}. "
        f"Keep each translation concise so it fits within the same spoken audio duration as the original. "
        f"Return the translated sentences in exact corresponding order as a JSON object with key \"translations\".\n\n"
        f"Input sentences:\n{json.dumps(texts, ensure_ascii=False)}"
    )

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "OBJECT",
                "properties": {
                    "translations": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Translated text segments in the exact order as input."
                    }
                },
                "required": ["translations"]
            }
        }
    }

    log.info("Translating %d segments via Gemini model %s...", len(texts), model)

    with httpx.Client(timeout=60.0) as client:
        res = client.post(url, json=payload)
        if res.is_error:
            error_detail = res.text
            log.error("Gemini API Error (HTTP %d): %s", res.status_code, error_detail)
            raise RuntimeError(f"Gemini API Error (HTTP {res.status_code}): {error_detail}")

        data = res.json()

    try:
        raw_json_str = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(raw_json_str)
        translations = result.get("translations", [])

        if len(translations) != len(texts):
            log.warning("Gemini returned %d translations for %d input texts. Adjusting length...", len(translations), len(texts))
            while len(translations) < len(texts):
                translations.append("[Translation missing]")
            translations = translations[:len(texts)]

        log.info("Gemini translation completed successfully.")
        return translations
    except Exception as exc:
        log.error("Failed to parse Gemini response: %s. Response data: %s", exc, data)
        raise RuntimeError(f"Failed to parse Gemini response: {exc}")


def translate_texts_interactive(
    texts: List[str],
    source_language: str,
    target_language: str,
) -> List[str]:
    return translate_texts(texts, source_language, target_language)