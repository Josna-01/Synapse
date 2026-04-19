# services/api/src/routers/needs.py
# SYNAPSE — Needs Router
# Handles creation of community needs with automatic urgency scoring.
# Implements the scoring fallback chain: Gemini → rule-based → default (50).

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.api.src.integrations.gemini import score_urgency
from services.api.src.integrations.firebase import write_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/needs", tags=["Needs"])

# ─── Pydantic Models ────────────────────────────────────────────────────────
class CreateNeedRequest(BaseModel):
    description: str = Field(..., description="Plain text description of the community need")
    category: str = Field(..., description="Category: water_sanitation, health, food_security, shelter, etc.")
    affected_count: int = Field(..., ge=1, description="Number of people affected")
    location_name: Optional[str] = Field("", description="Plain text location name")
    admin_code: Optional[str] = Field("", description="Admin boundary code (e.g., district or ward code)")
    lat: Optional[float] = Field(None, description="Latitude")
    lng: Optional[float] = Field(None, description="Longitude")
    source_org: Optional[str] = Field(None, description="ID of the reporting NGO/Coordinator")

class CreateNeedResponse(BaseModel):
    id: str
    status: str
    urgency_score: int
    urgency_level: str
    urgency_explanation: str
    fast_track: bool
    requires_review: bool
    scoring_source: str
    action_taken: str

# ─── Endpoints ──────────────────────────────────────────────────────────────
@router.post("/", response_model=CreateNeedResponse, status_code=status.HTTP_201_CREATED)
async def create_need(request: CreateNeedRequest):
    """
    Create a new community need.
    Automatically calculates urgency score using Gemini NLP, falling back to 
    rule-based scoring, and finally a default score if both fail.
    Evaluates fast-track conditions to bypass manual review.
    """
    logger.info(f"Creating need: {request.category} affecting {request.affected_count}")
    
    # ─── 1. Urgency Scoring Fallback Chain ───
    # Primary: Gemini 2.0 Flash NLP -> 0-100
    # Secondary: Rule-based keyword matching -> based on keyword tiers + boosts
    # Tertiary: Default score = 50 (moderate) with flag: "requires_review: true"
    
    try:
        # score_urgency encapsulates both Primary (Gemini) and Secondary (Rule-based) fallbacks
        urgency_data = await score_urgency(
            description=request.description,
            category=request.category,
            affected_count=request.affected_count,
            admin_code=request.admin_code,
            location_name=request.location_name
        )
    except Exception as e:
        logger.error(f"Urgency scoring completely failed, applying fallback default: {e}")
        # Tertiary Fallback
        urgency_data = {
            "score": 50,
            "level": "moderate",
            "explanation": "Default score assigned due to system unreachability. Coordinator review required.",
            "source": "default_fallback"
        }

    score = urgency_data.get("score", 50)
    level = urgency_data.get("level", "moderate")
    source = urgency_data.get("source", "default_fallback")
    
    # ─── 2. Evaluate Fast-Track Conditions ───
    # Fast-track conditions skip coordinator review and enable auto-dispatch
    auto_dispatch = False
    alert_government = False
    
    if score >= 80:
        auto_dispatch = True
    elif request.category.lower() == "health" and request.affected_count > 100:
        auto_dispatch = True
    elif request.category.lower() == "disaster_relief":
        auto_dispatch = True
        alert_government = True
    
    fast_track = auto_dispatch
    
    # Needs scored purely by the tertiary default fallback require review, or non-fast-track items
    requires_review = (source == "default_fallback") or not fast_track

    # ─── 3. Construct Document ───
    doc_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    
    need_doc = {
        "description": request.description,
        "category": request.category,
        "affected_count": request.affected_count,
        "location_name": request.location_name,
        "admin_code": request.admin_code,
        "location": {
            "lat": request.lat,
            "lng": request.lng
        } if request.lat and request.lng else None,
        "source_org": request.source_org,
        
        # Computed fields
        "urgency_score": score,
        "urgency_level": level,
        "urgency_explanation": urgency_data.get("explanation", ""),
        "scoring_source": source,
        "fast_track": fast_track,
        "requires_review": requires_review,
        "status": "open",
        "reports_count": 1,
        "created_at": now_iso,
        "latest_report_at": now_iso,
        "alert_government": alert_government
    }
    
    # ─── 4. Write to Firestore ───
    try:
        await write_doc("needs", doc_id, need_doc)
    except Exception as e:
        logger.error(f"Failed to write need to Firestore: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to persist need."
        )

    action_taken = "auto_dispatched" if fast_track else "queued_for_review"

    return CreateNeedResponse(
        id=doc_id,
        status=need_doc["status"],
        urgency_score=score,
        urgency_level=level,
        urgency_explanation=need_doc["urgency_explanation"],
        fast_track=fast_track,
        requires_review=requires_review,
        scoring_source=source,
        action_taken=action_taken
    )
