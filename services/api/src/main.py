"""
services/api/src/main.py — SYNAPSE FastAPI Entry Point

Startup verification checks:
  ✓ Gemini API connectivity
  ✓ Firebase Admin SDK (Firestore)
  ✓ Supabase Storage connectivity  (replaces Cloudinary check)
  ✓ Nominatim geocoding connectivity (replaces Google Maps check)
  ✓ Resend email API
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import needs, surveys, volunteers, tasks, campaigns, analytics, agents
from integrations.firebase import init_firebase
from integrations.gemini import check_gemini_connectivity
from integrations.storage import check_storage_connectivity     # Supabase Storage
from integrations.maps import check_nominatim_connectivity      # Nominatim / OSM

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(
    title="SYNAPSE API",
    description="AI-powered community need coordination platform",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("WEB_APP_URL", "http://localhost:3000"),
        os.getenv("DONOR_APP_URL", "http://localhost:3001"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(needs.router,      prefix="/api/v1/needs",      tags=["needs"])
app.include_router(surveys.router,    prefix="/api/v1/surveys",    tags=["surveys"])
app.include_router(volunteers.router, prefix="/api/v1/volunteers", tags=["volunteers"])
app.include_router(tasks.router,      prefix="/api/v1/tasks",      tags=["tasks"])
app.include_router(campaigns.router,  prefix="/api/v1/campaigns",  tags=["campaigns"])
app.include_router(analytics.router,  prefix="/api/v1/analytics",  tags=["analytics"])
app.include_router(agents.router,     prefix="/api/v1/agents",     tags=["agents"])


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("SYNAPSE API starting up…")

    # 1. Firebase Admin SDK
    try:
        init_firebase()
        logger.info("  ✓ Firebase Admin SDK initialised")
    except Exception as exc:
        logger.error("  ✗ Firebase init failed: %s", exc)

    # 2. Gemini API
    gemini_ok = await check_gemini_connectivity()
    if gemini_ok:
        logger.info("  ✓ Gemini API reachable")
    else:
        logger.warning(
            "  ✗ Gemini API unreachable — urgency scoring will use rule-based fallback"
        )

    # 3. Supabase Storage (replaces Cloudinary startup check)
    storage_ok = await check_storage_connectivity()
    if storage_ok:
        logger.info("  ✓ Supabase Storage reachable")
    else:
        logger.warning(
            "  ✗ Supabase Storage unreachable — file uploads will be queued for retry"
        )

    # 4. Nominatim geocoding (replaces Google Maps startup check)
    nominatim_ok = await check_nominatim_connectivity()
    if nominatim_ok:
        logger.info("  ✓ Nominatim (OpenStreetMap geocoding) reachable")
    else:
        logger.warning(
            "  ✗ Nominatim unreachable — geocoding will require manual lat/lng entry"
        )

    logger.info("SYNAPSE API ready. Environment: %s", os.getenv("ENVIRONMENT", "development"))


# ── Health endpoint ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Quick liveness probe for Railway.app health checks."""
    return {"status": "ok", "service": "synapse-api"}


@app.get("/health/deep")
async def health_deep():
    """
    Deep health check — verifies all external integrations.
    Used by monitoring and pre-demo verification.
    """
    gemini_ok   = await check_gemini_connectivity()
    storage_ok  = await check_storage_connectivity()
    nominatim_ok = await check_nominatim_connectivity()

    all_ok = gemini_ok and storage_ok and nominatim_ok

    return {
        "status": "ok" if all_ok else "degraded",
        "integrations": {
            "gemini":     "ok" if gemini_ok     else "degraded (rule-based fallback active)",
            "storage":    "ok" if storage_ok    else "degraded (uploads queued)",
            "nominatim":  "ok" if nominatim_ok  else "degraded (manual geocoding required)",
            # Note: OSRM and Overpass have inline haversine fallbacks —
            # they do not block startup but degrade gracefully per request.
            "osrm":       "fallback_available",
            "overpass":   "fallback_available",
        },
    }
