"""
Bhashini translation service wrapper.

Uses the Dhruva inference pipeline API for text translation.
Supports batched input — send a list of strings, get a list back.
"""

import httpx

from app.config import settings
from app.logger import get_logger

log = get_logger(__name__)

BHASHINI_INFERENCE_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
HTTP_TIMEOUT = 150.0
SERVICE_ID = "ai4bharat/indictrans-v2-all-gpu--t4"


def translate_texts(
    texts: list[str],
    source_language: str,
    target_language: str,
) -> list[str]:
    """
    Translate a list of text strings from source to target language.
    Returns a list of translated strings in the same order.
    """
    log.info(
        "Bhashini: translating %d text(s) from %s → %s",
        len(texts), source_language, target_language,
    )

    auth_token = settings.bhashini_api_key or "111bab42adbc4c55b817c07c7f705541"
    user_id = settings.bhashini_user_id or "32a5e500fd-c229-4b69-9282-6815a1558ffc"

    headers = {
        "Authorization": auth_token,
        "userID": user_id,
        "ulcaApiKey": auth_token,
        "Content-Type": "application/json",
    }

    body = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_language,
                        "targetLanguage": target_language,
                    },
                    "serviceId": SERVICE_ID,
                },
            }
        ],
        "inputData": {
            "input": [{"source": t} for t in texts],
        },
    }

    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        response = client.post(BHASHINI_INFERENCE_URL, json=body, headers=headers)
        response.raise_for_status()

    result = response.json()
    output_list = result["pipelineResponse"][0]["output"]
    translated = [item["target"] for item in output_list]

    log.info("Bhashini: received %d translation(s)", len(translated))
    return translated
