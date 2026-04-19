# services/api/src/integrations/cloudinary.py
# SYNAPSE — Cloudinary File Storage Integration
# Chosen over Firebase Storage: fully free tier (25GB), no Blaze plan required.
# Handles: survey images, audio files, generated PDFs, OCR-ready URLs.

import os
import logging
import hashlib
import time
import hmac
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

CLOUD_NAME  = os.environ["CLOUDINARY_CLOUD_NAME"]
API_KEY     = os.environ["CLOUDINARY_API_KEY"]
API_SECRET  = os.environ["CLOUDINARY_API_SECRET"]

UPLOAD_BASE = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}"
TIMEOUT     = httpx.Timeout(60.0, connect=15.0)   # uploads can be large

# Folder structure inside Cloudinary
FOLDERS = {
    "survey_images": "synapse/surveys",
    "audio":         "synapse/audio",
    "pdfs":          "synapse/reports",
    "avatars":       "synapse/avatars"
}


# ─── Signature helper ────────────────────────────────────────────────────────
def _sign(params: dict) -> str:
    """Generate Cloudinary API request signature."""
    sorted_params = "&".join(
        f"{k}={v}" for k, v in sorted(params.items()) if k not in ("file", "api_key")
    )
    to_sign = sorted_params + API_SECRET
    return hashlib.sha256(to_sign.encode()).hexdigest()


# ─── upload_survey_image() ───────────────────────────────────────────────────
async def upload_survey_image(
    file_bytes: bytes,
    filename: str,
    need_id: str = None,
    org_id: str = None
) -> dict:
    """
    Upload a field survey photo to Cloudinary.
    Returns Cloudinary URL + public_id, or error dict with error_flag=True.
    Images are tagged for easy batch retrieval and OCR.
    """
    folder = FOLDERS["survey_images"]
    timestamp = int(time.time())
    public_id = f"{folder}/{need_id or 'unlinked'}_{timestamp}"
    tags = ["survey", org_id or "untagged"]

    params = {
        "timestamp": timestamp,
        "folder": folder,
        "public_id": public_id,
        "tags": ",".join(tags),
        "quality": "auto:best",   # best quality for OCR accuracy
        "fetch_format": "auto"
    }
    params["signature"] = _sign(params)
    params["api_key"] = API_KEY

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{UPLOAD_BASE}/image/upload",
                data=params,
                files={"file": (filename, file_bytes, "image/jpeg")}
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "success": True,
            "url": data["secure_url"],
            "public_id": data["public_id"],
            "width": data.get("width"),
            "height": data.get("height"),
            "format": data.get("format"),
            "bytes": data.get("bytes"),
            "ocr_url": get_optimised_url(data["public_id"], for_ocr=True)
        }

    except Exception as e:
        logger.error(f"upload_survey_image failed ({e})")
        return {
            "success": False,
            "error_flag": True,
            "error": str(e),
            "url": None,
            "public_id": None,
            "ocr_url": None
        }


# ─── upload_audio() ──────────────────────────────────────────────────────────
async def upload_audio(
    file_bytes: bytes,
    filename: str,
    need_id: str = None
) -> dict:
    """
    Upload a WhatsApp voice note or field audio recording.
    Supports mp3, ogg, m4a, wav (Cloud Speech-to-Text accepts these).
    """
    folder = FOLDERS["audio"]
    timestamp = int(time.time())
    public_id = f"{folder}/audio_{need_id or 'unlinked'}_{timestamp}"

    params = {
        "timestamp": timestamp,
        "folder": folder,
        "public_id": public_id,
        "resource_type": "video",   # Cloudinary uses 'video' for audio files
        "tags": "voice_note,survey"
    }
    params["signature"] = _sign(params)
    params["api_key"] = API_KEY

    try:
        # Detect mime type from filename
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "ogg"
        mime_map = {"mp3": "audio/mpeg", "ogg": "audio/ogg", "m4a": "audio/mp4", "wav": "audio/wav"}
        mime = mime_map.get(ext, "audio/ogg")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{UPLOAD_BASE}/video/upload",
                data=params,
                files={"file": (filename, file_bytes, mime)}
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "success": True,
            "url": data["secure_url"],
            "public_id": data["public_id"],
            "duration_seconds": data.get("duration"),
            "bytes": data.get("bytes")
        }

    except Exception as e:
        logger.error(f"upload_audio failed ({e})")
        return {
            "success": False,
            "error_flag": True,
            "error": str(e),
            "url": None,
            "public_id": None
        }


# ─── upload_pdf() ────────────────────────────────────────────────────────────
async def upload_pdf(
    file_bytes: bytes,
    filename: str,
    report_type: str = "impact_report",
    entity_id: str = None
) -> dict:
    """
    Upload a generated PDF (impact report, CSR certificate, govt digest).
    Returns signed URL valid for 7 days (for email delivery) + permanent URL.
    """
    folder = FOLDERS["pdfs"]
    timestamp = int(time.time())
    public_id = f"{folder}/{report_type}_{entity_id or 'generic'}_{timestamp}"

    params = {
        "timestamp": timestamp,
        "folder": folder,
        "public_id": public_id,
        "resource_type": "raw",
        "tags": f"pdf,{report_type}"
    }
    params["signature"] = _sign(params)
    params["api_key"] = API_KEY

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{UPLOAD_BASE}/raw/upload",
                data=params,
                files={"file": (filename, file_bytes, "application/pdf")}
            )
            resp.raise_for_status()
            data = resp.json()

        # Generate signed URL valid for 7 days
        signed_url = _generate_signed_url(data["public_id"], expiry_seconds=7 * 24 * 3600)

        return {
            "success": True,
            "url": data["secure_url"],
            "signed_url": signed_url,
            "public_id": data["public_id"],
            "bytes": data.get("bytes")
        }

    except Exception as e:
        logger.error(f"upload_pdf failed ({e})")
        return {
            "success": False,
            "error_flag": True,
            "error": str(e),
            "url": None,
            "signed_url": None,
            "public_id": None
        }


def _generate_signed_url(public_id: str, expiry_seconds: int = 604800) -> str:
    """Generate a time-limited signed URL for sensitive PDFs."""
    expiry = int(time.time()) + expiry_seconds
    to_sign = f"public_id={public_id}&timestamp={expiry}{API_SECRET}"
    sig = hashlib.sha256(to_sign.encode()).hexdigest()
    return (
        f"https://res.cloudinary.com/{CLOUD_NAME}/raw/upload"
        f"?public_id={public_id}&timestamp={expiry}&signature={sig}&api_key={API_KEY}"
    )


# ─── delete_file() ───────────────────────────────────────────────────────────
async def delete_file(public_id: str, resource_type: str = "image") -> bool:
    """
    Delete a file from Cloudinary (used for cleanup after deduplication merges).
    resource_type: 'image' | 'video' | 'raw'
    """
    timestamp = int(time.time())
    params = {"public_id": public_id, "timestamp": timestamp}
    params["signature"] = _sign(params)
    params["api_key"] = API_KEY

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{UPLOAD_BASE}/{resource_type}/destroy",
                data=params
            )
            resp.raise_for_status()
            data = resp.json()
        return data.get("result") == "ok"
    except Exception as e:
        logger.error(f"delete_file {public_id} failed ({e})")
        return False


# ─── get_optimised_url() ─────────────────────────────────────────────────────
def get_optimised_url(public_id: str, for_ocr: bool = False, width: int = None) -> str:
    """
    Generate a Cloudinary transformation URL.
    for_ocr=True: high quality, no compression — optimal for Cloud Vision API.
    width: optional responsive resize.
    """
    base = f"https://res.cloudinary.com/{CLOUD_NAME}/image/upload"

    if for_ocr:
        # Maximum quality, lossless, greyscale-enhanced for OCR
        transforms = "q_100,fl_lossless,e_sharpen:80,e_contrast:30"
    elif width:
        transforms = f"w_{width},c_scale,q_auto,f_auto"
    else:
        transforms = "q_auto,f_auto"

    return f"{base}/{transforms}/{public_id}"


# ─── get_upload_signature() (for direct frontend uploads) ────────────────────
def get_upload_signature(folder_key: str = "survey_images") -> dict:
    """
    Generate a signed upload preset for direct browser/Flutter → Cloudinary uploads.
    Avoids routing large files through FastAPI backend.
    """
    folder = FOLDERS.get(folder_key, FOLDERS["survey_images"])
    timestamp = int(time.time())
    params = {
        "timestamp": timestamp,
        "folder": folder,
        "tags": "direct_upload"
    }
    signature = _sign(params)
    return {
        "signature": signature,
        "timestamp": timestamp,
        "api_key": API_KEY,
        "cloud_name": CLOUD_NAME,
        "folder": folder
    }
