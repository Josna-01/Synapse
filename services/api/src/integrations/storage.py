"""
integrations/storage.py — SYNAPSE File Storage Integration
Uses Supabase Storage (free tier, no credit card required).

Previously: integrations/cloudinary.py (Cloudinary)
Renamed to:  integrations/storage.py (Supabase Storage)

All function signatures are identical to the previous cloudinary.py version
so no calling code needs to change — only the import path changes:
  from integrations.cloudinary import ...
  → from integrations.storage import ...

Supabase Storage docs: https://supabase.com/docs/guides/storage

Bucket structure:
  synapse-surveys/  — field survey photos
  synapse-audio/    — voice notes
  synapse-reports/  — generated PDFs

Environment variables required:
  SUPABASE_URL   — https://your-project.supabase.co
  SUPABASE_KEY   — service_role key (from Project Settings → API)
"""

import os
import logging
import mimetypes
from pathlib import Path
from typing import Optional

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ── Supabase client (initialised once at module load) ────────────────────────

_supabase: Optional[Client] = None


def _get_client() -> Client:
    global _supabase
    if _supabase is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _supabase = create_client(url, key)
    return _supabase


# ── Bucket names ─────────────────────────────────────────────────────────────

BUCKET_SURVEYS = "synapse-surveys"
BUCKET_AUDIO   = "synapse-audio"
BUCKET_REPORTS = "synapse-reports"

# Signed URL expiry (seconds) — 1 hour for downloads
SIGNED_URL_EXPIRY = 3600


# ── Upload helpers ────────────────────────────────────────────────────────────

def _upload(bucket: str, path: str, data: bytes, content_type: str) -> Optional[str]:
    """
    Internal helper: upload bytes to a Supabase Storage bucket.
    Returns the storage path on success, None on failure.
    """
    try:
        client = _get_client()
        client.storage.from_(bucket).upload(
            path=path,
            file=data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        return path
    except Exception as exc:
        logger.error("Supabase Storage upload failed (bucket=%s, path=%s): %s",
                     bucket, path, exc)
        return None


# ── Public API (same function names as cloudinary.py) ───────────────────────

async def upload_survey_image(
    image_bytes: bytes,
    filename: str,
    need_id: str,
) -> Optional[str]:
    """
    Upload a field survey photo to Supabase Storage.

    Returns a signed URL valid for SIGNED_URL_EXPIRY seconds,
    or None on failure.

    Previously: cloudinary.py::upload_survey_image → Cloudinary URL
    Now:        storage.py::upload_survey_image → Supabase signed URL
    """
    ext = Path(filename).suffix or ".jpg"
    storage_path = f"{need_id}/{filename}"
    content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"

    path = _upload(BUCKET_SURVEYS, storage_path, image_bytes, content_type)
    if path is None:
        return None

    return _get_signed_url(BUCKET_SURVEYS, path)


async def upload_audio(
    audio_bytes: bytes,
    filename: str,
    submission_id: str,
) -> Optional[str]:
    """
    Upload a WhatsApp voice note to Supabase Storage.

    Returns a signed URL valid for SIGNED_URL_EXPIRY seconds,
    or None on failure.

    Previously: cloudinary.py::upload_audio
    """
    storage_path = f"{submission_id}/{filename}"
    content_type = mimetypes.guess_type(filename)[0] or "audio/ogg"

    path = _upload(BUCKET_AUDIO, storage_path, audio_bytes, content_type)
    if path is None:
        return None

    return _get_signed_url(BUCKET_AUDIO, path)


async def upload_pdf(
    pdf_bytes: bytes,
    filename: str,
    report_type: str,
    entity_id: str,
) -> Optional[str]:
    """
    Upload a generated PDF (CSR report, donor impact, govt digest) to Supabase Storage.

    Args:
        report_type: "csr_report" | "impact_report" | "govt_digest"
        entity_id:   donor_id, campaign_id, or digest_id

    Returns a signed URL valid for SIGNED_URL_EXPIRY seconds,
    or None on failure.

    Previously: cloudinary.py::upload_pdf
    """
    storage_path = f"{report_type}/{entity_id}/{filename}"

    path = _upload(BUCKET_REPORTS, storage_path, pdf_bytes, "application/pdf")
    if path is None:
        return None

    return _get_signed_url(BUCKET_REPORTS, path)


async def delete_file(bucket: str, storage_path: str) -> bool:
    """
    Delete a file from Supabase Storage.

    Returns True on success, False on failure.

    Previously: cloudinary.py::delete_file
    """
    try:
        client = _get_client()
        client.storage.from_(bucket).remove([storage_path])
        logger.info("Deleted %s from bucket %s", storage_path, bucket)
        return True
    except Exception as exc:
        logger.error("Supabase Storage delete failed (bucket=%s, path=%s): %s",
                     bucket, storage_path, exc)
        return False


async def get_optimised_url(bucket: str, storage_path: str) -> Optional[str]:
    """
    Get a fresh signed URL for an existing file in Supabase Storage.

    This replaces the Cloudinary transformation URL pattern.
    Supabase Storage does not apply image transformations at the CDN level
    (use the image transformation API add-on if needed — free tier covers basics).

    Previously: cloudinary.py::get_optimised_url → Cloudinary CDN URL with transforms
    Now:        storage.py::get_optimised_url → Supabase signed URL
    """
    return _get_signed_url(bucket, storage_path)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_signed_url(bucket: str, storage_path: str) -> Optional[str]:
    """Generate a signed URL for a Supabase Storage object."""
    try:
        client = _get_client()
        result = client.storage.from_(bucket).create_signed_url(
            storage_path, SIGNED_URL_EXPIRY
        )
        # result is {"signedURL": "https://..."}
        return result.get("signedURL")
    except Exception as exc:
        logger.error("Supabase signed URL generation failed: %s", exc)
        return None


# ── Startup Health Check ──────────────────────────────────────────────────────

async def check_storage_connectivity() -> bool:
    """
    Verify Supabase Storage is reachable by listing files in synapse-surveys bucket.
    Called on FastAPI startup.

    Replaces: Cloudinary connectivity check on startup.
    """
    try:
        client = _get_client()
        client.storage.from_(BUCKET_SURVEYS).list(path="", options={"limit": 1})
        logger.info("Supabase Storage connectivity: OK")
        return True
    except Exception as exc:
        logger.warning("Supabase Storage connectivity check failed: %s", exc)
        return False
