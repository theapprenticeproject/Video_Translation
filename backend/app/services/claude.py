"""
Claude translation service wrapper.

Uses the Anthropic Messages and Message Batches API to translate text segments.
Supports:
1. Message Batches API (Primary): For asynchronous processing, high reliability, and cost efficiency.
2. Interactive Messages API (Secondary Fallback): For instant real-time fallback in case of batch failure.
"""

import json
import httpx
import time
from typing import List

from app.config import settings
from app.logger import get_logger

log = get_logger(__name__)

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_BATCH_URL = "https://api.anthropic.com/v1/messages/batches"
HTTP_TIMEOUT = 150.0
DEFAULT_MODEL = "claude-sonnet-4-6"

# Map 2-letter codes to full language names for Claude
LANGUAGE_MAP = {
    "hi": "Hindi",
    "mr": "Marathi",
    "pa": "Punjabi",
    "ka": "Kannada",
    "en": "English",
}


def translate_texts(
    texts: List[str],
    source_language: str,
    target_language: str,
) -> List[str]:
    """
    Translate a list of text strings from source to target language using Claude.
    Tries Anthropic Message Batches API first, with automatic fallback to Interactive Messages API.
    """
    if not texts:
        return []

    try:
        log.info("Attempting translation via Anthropic Message Batches API...")
        return translate_texts_batch(texts, source_language, target_language)
    except Exception as exc:
        log.warning("Anthropic Batch API failed or timed out: %s. Falling back to real-time Messages API...", exc)
        return translate_texts_interactive(texts, source_language, target_language)


def translate_texts_batch(
    texts: List[str],
    source_language: str,
    target_language: str,
) -> List[str]:
    """Translate list of texts using the Anthropic Message Batches API with polling."""
    api_key = settings.anthropic_api_key
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured in settings.")

    src_name = LANGUAGE_MAP.get(source_language.lower(), source_language)
    tgt_name = LANGUAGE_MAP.get(target_language.lower(), target_language)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # 1. Construct batch requests
    requests_payload = []
    for i, text in enumerate(texts):
        requests_payload.append({
            "custom_id": f"seg_{i}",
            "params": {
                "model": DEFAULT_MODEL,
                "max_tokens": 500,
                "messages": [
                    {"role": "user", "content": f"Translate this sentence from {src_name} to {tgt_name}. Return ONLY the translation, nothing else: {text}"}
                ]
            }
        })

    body = {
        "requests": requests_payload
    }

    # 2. Create message batch
    with httpx.Client(timeout=30.0) as client:
        res = client.post(ANTHROPIC_BATCH_URL, json=body, headers=headers)
        res.raise_for_status()
        batch_info = res.json()
        batch_id = batch_info["id"]

    log.info("Created Anthropic Message Batch ID: %s. Polling status...", batch_id)

    # 3. Poll for completion
    poll_start = time.time()
    max_poll_time = 300  # 5 minutes max wait time inside background worker task
    status = "in_progress"

    while status == "in_progress":
        if time.time() - poll_start > max_poll_time:
            raise TimeoutError(f"Anthropic batch translation timed out after {max_poll_time} seconds.")

        time.sleep(5)
        with httpx.Client(timeout=30.0) as client:
            poll_res = client.get(f"{ANTHROPIC_BATCH_URL}/{batch_id}", headers=headers)
            poll_res.raise_for_status()
            status_info = poll_res.json()
            status = status_info["processing_status"]
            log.info("Batch status: %s", status)

    if status != "ended":
        raise RuntimeError(f"Anthropic batch processing ended with non-success status: {status}")

    results_url = status_info.get("results_url")
    if not results_url:
        raise RuntimeError("No results URL found in completed Anthropic batch status.")

    # 4. Download and parse results
    log.info("Downloading batch results from Anthropic...")
    with httpx.Client(timeout=30.0) as client:
        results_res = client.get(results_url, headers=headers)
        results_res.raise_for_status()

    lines = results_res.text.strip().split("\n")
    translations = [None] * len(texts)

    for line in lines:
        if not line.strip():
            continue
        item = json.loads(line)
        custom_id = item["custom_id"]
        index = int(custom_id.split("_")[1])

        result_item = item["result"]
        if result_item["type"] == "succeeded":
            content = result_item["message"]["content"][0]["text"].strip()
            translations[index] = content
        else:
            log.warning("Batch segment %s errored. Attempting single fallback...", custom_id)
            translations[index] = translate_single_text(texts[index], source_language, target_language)

    # Check for missing translations and fill them
    for idx, val in enumerate(translations):
        if val is None:
            translations[idx] = translate_single_text(texts[idx], source_language, target_language)

    log.info("Batch translation completed successfully.")
    return translations


def translate_texts_interactive(
    texts: List[str],
    source_language: str,
    target_language: str,
) -> List[str]:
    """Translate list of texts using the Interactive Messages API with structured tool use."""
    api_key = settings.anthropic_api_key
    src_name = LANGUAGE_MAP.get(source_language.lower(), source_language)
    tgt_name = LANGUAGE_MAP.get(target_language.lower(), target_language)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    body = {
        "model": DEFAULT_MODEL,
        "max_tokens": 4000,
        "system": f"You are a professional translator and subtitler. Translate the list of sentences from {src_name} to {tgt_name} and return the results using the return_translations tool.",
        "messages": [
            {
                "role": "user",
                "content": f"Translate these sentences from {src_name} to {tgt_name}:\n{json.dumps(texts, ensure_ascii=False)}"
            }
        ],
        "tools": [
            {
                "name": "return_translations",
                "description": "Returns the translated text segments in the exact order and length as the input.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "translations": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "The translated text segments."
                        }
                    },
                    "required": ["translations"]
                }
            }
        ],
        "tool_choice": {"type": "tool", "name": "return_translations"}
    }

    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        response = client.post(ANTHROPIC_MESSAGES_URL, json=body, headers=headers)
        response.raise_for_status()

    result = response.json()
    
    # Extract translations from tool call
    tool_use = None
    for block in result.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == "return_translations":
            tool_use = block
            break

    if not tool_use:
        raise RuntimeError("Claude did not return translations in the expected structured format.")

    translated = tool_use["input"]["translations"]

    # Safety padding if count mismatches
    if len(translated) != len(texts):
        while len(translated) < len(texts):
            translated.append("[Translation missing]")
        translated = translated[:len(texts)]

    return translated


def translate_single_text(
    text: str,
    source_language: str,
    target_language: str,
) -> str:
    """Translate a single sentence using the standard Messages API (fallback)."""
    api_key = settings.anthropic_api_key
    src_name = LANGUAGE_MAP.get(source_language.lower(), source_language)
    tgt_name = LANGUAGE_MAP.get(target_language.lower(), target_language)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    body = {
        "model": DEFAULT_MODEL,
        "max_tokens": 500,
        "system": f"You are an expert translator. Translate the text from {src_name} to {tgt_name}. Return ONLY the translation, with no explanation or commentary.",
        "messages": [
            {"role": "user", "content": f"Translate: {text}"}
        ]
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(ANTHROPIC_MESSAGES_URL, json=body, headers=headers)
            res.raise_for_status()
            result = res.json()
            return result["content"][0]["text"].strip()
    except Exception as exc:
        log.error("Single fallback translation failed for '%s': %s", text, exc)
        return "[Translation missing]"
