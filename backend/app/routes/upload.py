"""
Upload route — Stage 1.

POST /api/upload/signed-url
  Body : { "filename": "video.mp4", "content_type": "video/mp4" }
  Returns: { "upload_url": "<signed GCS PUT url>", "object_name": "originals/abc_video.mp4" }
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.auth import require_auth
from app.logger import get_logger
from app.services import gcs

log = get_logger(__name__)
router = APIRouter(prefix="/api/upload", tags=["upload"])


class SignedUrlRequest(BaseModel):
    filename: str
    content_type: str


class SignedUrlResponse(BaseModel):
    upload_url: str
    object_name: str


@router.post(
    "/signed-url",
    response_model=SignedUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a signed GCS upload URL",
    description=(
        "Returns a v4-signed PUT URL valid for 15 minutes. "
        "The client uploads the file directly to GCS — no file data passes through the backend."
    ),
)
def get_signed_url(body: SignedUrlRequest, user_id: str = Depends(require_auth)) -> SignedUrlResponse:
    log.info("Signed URL requested for file=%s type=%s", body.filename, body.content_type)
    try:
        object_name = gcs.make_object_name(body.filename)
        upload_url = gcs.get_resumable_upload_url(object_name, body.content_type)
    except Exception as exc:
        log.error("Failed to generate signed URL: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not generate upload URL. Check GCS credentials.",
        ) from exc

    return SignedUrlResponse(upload_url=upload_url, object_name=object_name)


@router.post(
    "/direct",
    response_model=SignedUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Direct server-side upload to GCS",
)
def upload_direct(
    file: UploadFile = File(...),
    user_id: str = Depends(require_auth),
) -> SignedUrlResponse:
    log.info("Direct server upload received for file=%s type=%s", file.filename, file.content_type)
    try:
        object_name = gcs.make_object_name(file.filename or "uploaded_media.mp4")
        gcs.upload_file_stream(object_name, file.file, file.content_type or "application/octet-stream")
    except Exception as exc:
        log.error("Direct upload failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to GCS.",
        ) from exc

    return SignedUrlResponse(upload_url="", object_name=object_name)
