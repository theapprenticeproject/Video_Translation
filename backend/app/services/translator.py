"""
Unified Translation Dispatcher.

Routes translation requests to Gemini, Claude, or Bhashini based on settings.translation_provider.
"""

from typing import List
from app.config import settings
from app.logger import get_logger
from app.services import gemini, claude, bhashini

log = get_logger(__name__)

def translate_texts(
    texts: List[str],
    source_language: str,
    target_language: str,
) -> List[str]:
    provider = getattr(settings, "translation_provider", "gemini").lower()
    log.info("Translation provider selected: %s", provider)

    if provider == "claude":
        return claude.translate_texts(texts, source_language, target_language)
    elif provider == "bhashini":
        return bhashini.translate_texts(texts, source_language, target_language)
    else:  # default to gemini
        return gemini.translate_texts(texts, source_language, target_language)


def translate_texts_interactive(
    texts: List[str],
    source_language: str,
    target_language: str,
) -> List[str]:
    provider = getattr(settings, "translation_provider", "gemini").lower()
    log.info("Interactive translation provider selected: %s", provider)

    if provider == "claude":
        return claude.translate_texts_interactive(texts, source_language, target_language)
    elif provider == "bhashini":
        return bhashini.translate_texts(texts, source_language, target_language)
    else:  # default to gemini
        return gemini.translate_texts_interactive(texts, source_language, target_language)
