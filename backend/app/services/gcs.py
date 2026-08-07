"""
GCS service wrapper.

All GCS operations go through this module so the rest of the codebase
never touches the google-cloud-storage SDK directly.
"""

import json
import uuid
import datetime
from typing import Optional

from google.cloud import storage
from google.oauth2 import service_account

from app.config import settings
from app.logger import get_logger

log = get_logger(__name__)

def _build_client() -> storage.Client:
    """Build a GCS client from the service-account JSON *string* stored in env."""
    info = json.loads(settings.gcs_service_account_json)
    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    client = storage.Client(
        credentials=credentials,
        project=credentials.project_id,
    )
    log.info("GCS client initialised (project=%s, bucket=%s)",
             credentials.project_id, settings.gcs_bucket_name)
    return client


# Lazy singleton — created on first use so the app still boots without creds
_client: Optional[storage.Client] = None


def get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def _bucket() -> storage.Bucket:
    bucket = get_client().bucket(settings.gcs_bucket_name)
    return bucket


def ensure_bucket_cors():
    """Attempt to configure CORS on the GCS bucket so browser PUT uploads succeed."""
    try:
        bucket = _bucket()
        origins = [settings.client_cors_origin_url, "http://localhost:5173", "http://127.0.0.1:5173", "https://ai-translation.theapprenticeproject.org"]
        cors_rule = {
            "origin": list(set([o for o in origins if o])),
            "method": ["GET", "PUT", "POST", "DELETE", "HEAD", "OPTIONS"],
            "responseHeader": ["*"],
            "maxAgeSeconds": 3600,
        }
        bucket.cors = [cors_rule]
        bucket.patch()
        log.info("Successfully set CORS rules on GCS bucket %s", settings.gcs_bucket_name)
    except Exception as e:
        log.warning("Could not auto-set GCS bucket CORS rules: %s", e)


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #

def make_object_name(filename: str, prefix: str = "originals") -> str:
    """
    Build a deterministic, collision-free GCS object name.
    Example: originals/a1b2c3d4_my-video.mp4
    """
    uid = uuid.uuid4().hex[:8]
    safe_name = filename.replace(" ", "_")
    parts = [p.strip("/") for p in [settings.gcs_bucket_prefix, prefix, f"{uid}_{safe_name}"] if p and p.strip("/")]
    return "/".join(parts)


def get_resumable_upload_url(object_name: str, content_type: str) -> str:
    """
    Generate a v4-signed resumable upload URI.
    The browser PUT-s the file directly to this URL — no backend bandwidth used.
    """
    blob = _bucket().blob(object_name)
    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=15),
        method="PUT",
        content_type=content_type,
    )
    log.info("Generated signed upload URL for %s", object_name)
    return url


def upload_bytes(object_name: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """
    Upload raw bytes from the backend (e.g. processed audio from TTS).
    Used by pipeline tasks, not by the frontend.
    """
    blob = _bucket().blob(object_name)
    blob.upload_from_string(data, content_type=content_type)
    log.info("Uploaded %d bytes to gs://%s/%s",
             len(data), settings.gcs_bucket_name, object_name)


def upload_file_stream(object_name: str, file_obj, content_type: str = "application/octet-stream") -> None:
    """Upload a file stream directly from backend to GCS."""
    blob = _bucket().blob(object_name)
    blob.upload_from_file(file_obj, content_type=content_type)
    log.info("Uploaded file stream to gs://%s/%s", settings.gcs_bucket_name, object_name)


def get_signed_download_url(object_name: str, expiry_minutes: int = 60) -> str:
    """Return a v4 signed URL for reading a file (used for download step)."""
    blob = _bucket().blob(object_name)
    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=expiry_minutes),
        method="GET",
    )
    log.info("Generated signed download URL for %s (expires in %dm)",
             object_name, expiry_minutes)
    return url


def download_blob_to_bytes(object_name: str) -> bytes:
    """Download a GCS object and return its content as bytes."""
    blob = _bucket().blob(object_name)
    data = blob.download_as_bytes()
    log.info("Downloaded %d bytes from gs://%s/%s",
             len(data), settings.gcs_bucket_name, object_name)
    return data


def upload_from_file(object_name: str, file_path: str, content_type: str = "application/octet-stream") -> None:
    """Upload a local file to GCS."""
    blob = _bucket().blob(object_name)
    blob.upload_from_filename(file_path, content_type=content_type)
    log.info("Uploaded file %s to gs://%s/%s",
             file_path, settings.gcs_bucket_name, object_name)


def delete_object(object_name: str) -> None:
    """Delete a GCS object (optional cleanup after pipeline completion)."""
    blob = _bucket().blob(object_name)
    blob.delete()
    log.info("Deleted gs://%s/%s", settings.gcs_bucket_name, object_name)
