"""
Service to fetch media from external URLs (YouTube and Google Drive)
and upload to GCS for pipeline processing.
"""

import os
import re
import tempfile
import uuid
import httpx
from urllib.parse import parse_qs, urlparse

from app.logger import get_logger
from app.services import gcs

log = get_logger(__name__)


def is_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    return any(yt in hostname.lower() for yt in ["youtube.com", "youtu.be"])


def is_google_drive_url(url: str) -> bool:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    return "drive.google.com" in hostname.lower() or "docs.google.com" in hostname.lower()


def extract_drive_file_id(url: str) -> str | None:
    # Pattern 1: /file/d/{ID}/
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    
    # Pattern 2: id={ID}
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "id" in qs and qs["id"]:
        return qs["id"][0]
        
    return None


def fetch_from_youtube(url: str) -> tuple[str, str]:
    """
    Downloads YouTube video or audio using yt-dlp, uploads to GCS.
    Returns (object_name, filename).
    """
    import yt_dlp

    log.info("Downloading YouTube media: %s", url)
    temp_dir = tempfile.mkdtemp(prefix="yt_download_")
    out_template = os.path.join(temp_dir, "%(title).50s [%(id)s].%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    if not os.path.exists(filename):
        downloaded = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
        if not downloaded:
            raise RuntimeError("YouTube download failed: no file was created.")
        filename = downloaded[0]

    base_name = os.path.basename(filename)
    object_name = gcs.make_object_name(base_name)

    log.info("Uploading downloaded YouTube file %s to GCS as %s...", base_name, object_name)
    gcs.upload_from_file(object_name, filename, content_type="video/mp4")

    try:
        os.remove(filename)
        os.rmdir(temp_dir)
    except Exception:
        pass

    return object_name, base_name


def fetch_from_google_drive(url: str) -> tuple[str, str]:
    """
    Downloads public Google Drive file, uploads to GCS.
    Returns (object_name, filename).
    """
    file_id = extract_drive_file_id(url)
    if not file_id:
        raise ValueError("Could not extract a valid Google Drive file ID from the provided URL.")

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    log.info("Downloading Google Drive file id=%s", file_id)

    temp_dir = tempfile.mkdtemp(prefix="drive_download_")
    temp_path = os.path.join(temp_dir, f"drive_{file_id}.mp4")

    with httpx.Client(timeout=180.0, follow_redirects=True) as client:
        with client.stream("GET", download_url) as response:
            if response.is_error:
                raise RuntimeError(f"Failed to download Google Drive file: HTTP {response.status_code}")

            content_disp = response.headers.get("Content-Disposition", "")
            base_name = f"drive_{file_id}.mp4"
            if "filename=" in content_disp:
                match = re.search(r'filename="?([^";]+)"?', content_disp)
                if match:
                    base_name = match.group(1)

            with open(temp_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)

    if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
        raise RuntimeError("Google Drive download returned an empty file. Make sure file sharing is set to 'Anyone with the link'.")

    object_name = gcs.make_object_name(base_name)
    log.info("Uploading downloaded Drive file %s to GCS as %s...", base_name, object_name)
    gcs.upload_from_file(object_name, temp_path, content_type="video/mp4")

    try:
        os.remove(temp_path)
        os.rmdir(temp_dir)
    except Exception:
        pass

    return object_name, base_name


def fetch_media_from_url(url: str) -> tuple[str, str]:
    """
    Main entrypoint: parses URL, routes to YouTube or Google Drive,
    and returns (object_name, filename).
    """
    clean_url = url.strip()
    if is_youtube_url(clean_url):
        return fetch_from_youtube(clean_url)
    elif is_google_drive_url(clean_url):
        return fetch_from_google_drive(clean_url)
    else:
        raise ValueError("Unsupported URL format. Please provide a valid YouTube or Google Drive link.")
