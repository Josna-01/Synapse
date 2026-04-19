# services/api/src/fallbacks/matching.py
# SYNAPSE — Haversine-Based Volunteer Matching Fallback
# Used whenever Routes API is unavailable (quota, network error).
# Returns IDENTICAL schema to live Routes API matching — drop-in replacement.

import logging
from math import radians, sin, cos, sqrt, atan2
from typing import Optional

logger = logging.getLogger(__name__)

# Default maximum radius for volunteer matching (km)
DEFAULT_MAX_KM = 15.0

# Travel speed assumptions (km/h) — conservative urban averages
SPEED = {
    "driving":  35.0,   # urban with traffic
    "walking":   5.0,
    "transit":  20.0,
    "cycling":  15.0
}


# ─── haversine_km() ──────────────────────────────────────────────────────────
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Great-circle distance between two GPS coordinates in kilometres.
    Uses the haversine formula. Free, no quota, always available.
    """
    R = 6371  # Earth mean radius (km)
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


# ─── estimate_travel_time() ──────────────────────────────────────────────────
def estimate_travel_time(distance_km: float, mode: str = "driving") -> float:
    """
    Convert straight-line distance to approximate travel time (minutes).
    Applies a 1.4× road-factor correction (straight line < actual road distance).
    Returns same unit as Routes API (minutes, float).
    """
    speed = SPEED.get(mode.lower(), SPEED["driving"])
    road_distance_km = distance_km * 1.4   # correction for road winding
    return (road_distance_km / speed) * 60


# ─── haversine_filter() ──────────────────────────────────────────────────────
def haversine_filter(
    need_lat: float,
    need_lng: float,
    volunteers: list[dict],
    max_km: float = DEFAULT_MAX_KM,
    mode: str = "driving"
) -> list[dict]:
    """
    Filter and sort volunteers by haversine distance from a need location.
    Returns volunteers within max_km, sorted by distance (nearest first).
    Each volunteer dict is extended with:
      - distance_km: float
      - travel_time_mins: float
      - match_source: "haversine_fallback"
      - match_source_label: human-readable indicator string
    """
    results = []
    for volunteer in volunteers:
        v_lat = volunteer.get("lat")
        v_lng = volunteer.get("lng")

        if v_lat is None or v_lng is None:
            logger.debug(f"Volunteer {volunteer.get('id')} has no coordinates, skipping")
            continue

        try:
            km = haversine_km(need_lat, need_lng, v_lat, v_lng)
        except Exception as e:
            logger.warning(f"haversine_km failed for volunteer {volunteer.get('id')}: {e}")
            continue

        if km <= max_km:
            travel_mins = estimate_travel_time(km, mode)
            results.append({
                **volunteer,
                "distance_km": round(km, 2),
                "travel_time_mins": round(travel_mins, 1),
                "match_source": "haversine_fallback",
                "match_source_label": "⚠️  Matched via: Estimated distance (API unavailable)"
            })

    results.sort(key=lambda v: v["distance_km"])
    return results


# ─── rank_volunteers() ───────────────────────────────────────────────────────
def rank_volunteers(
    volunteers: list[dict],
    task_requirements: str = "",
    max_travel_mins: float = 90.0
) -> list[dict]:
    """
    Rank pre-filtered volunteers by composite fallback score.
    Used when Gemini embedding is also unavailable.

    Composite score (mirrors real match_score formula):
      match_score = (skill_similarity × 0.40) + (proximity_score × 0.30)
                  + (completion_rate × 0.20) + (domain_boost × 0.10)

    In fallback mode:
      skill_similarity → keyword overlap (0-1)
      proximity_score  → 1 - (travel_time_mins / 90)
      completion_rate  → from volunteer.completion_rate field (0-1)
      domain_boost     → 0.1 if category overlaps volunteer.domains, else 0
    """
    req_words = set(task_requirements.lower().split())

    ranked = []
    for v in volunteers:
        # Hard filter: max travel time
        travel_mins = v.get("travel_time_mins", 999)
        if travel_mins > max_travel_mins:
            continue

        # Skill similarity via keyword overlap
        skills_text = " ".join(v.get("skills", [])).lower()
        skill_words = set(skills_text.split())
        overlap = len(req_words & skill_words) if req_words else 0
        skill_sim = min(1.0, overlap / max(len(req_words), 1)) if req_words else 0.5

        # Proximity score
        proximity = max(0.0, 1.0 - (travel_mins / max_travel_mins))

        # Completion rate
        completion = v.get("completion_rate", 0.7)  # default 70% if unknown

        # Domain boost (not available in fallback — set to 0)
        domain_boost = 0.0

        score = (
            skill_sim * 0.40
            + proximity * 0.30
            + completion * 0.20
            + domain_boost * 0.10
        )

        ranked.append({
            **v,
            "match_score": round(score, 4),
            "skill_similarity": round(skill_sim, 4),
            "proximity_score": round(proximity, 4),
            "match_source": v.get("match_source", "haversine_fallback"),
            "match_source_label": v.get("match_source_label", "⚠️  Matched via: Estimated distance (API unavailable)")
        })

    ranked.sort(key=lambda v: v["match_score"], reverse=True)
    return ranked[:3]   # Return top 3, same as Routes API path


# ─── top_3_fallback_matches() ────────────────────────────────────────────────
def top_3_fallback_matches(
    need_lat: float,
    need_lng: float,
    task_requirements: str,
    volunteers: list[dict],
    max_km: float = DEFAULT_MAX_KM,
    max_travel_mins: float = 90.0,
    mode: str = "driving"
) -> list[dict]:
    """
    Full fallback matching pipeline.
    Step 1: haversine_filter (distance-based hard filter)
    Step 2: rank_volunteers (composite score)
    Returns top 3 with plain-language explanation attached.
    """
    nearby = haversine_filter(need_lat, need_lng, volunteers, max_km, mode)
    top3 = rank_volunteers(nearby, task_requirements, max_travel_mins)

    for match in top3:
        skills = match.get("skills", [])
        top_skill = skills[0] if skills else "general"
        sim_pct = int(match.get("skill_similarity", 0) * 100)
        mins = match.get("travel_time_mins", 0)
        match["explanation"] = (
            f"Matched: {top_skill} skill ({sim_pct}%), "
            f"~{mins:.0f} min away (estimated), available now."
        )

    return top3
