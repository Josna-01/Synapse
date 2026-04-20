"""
fallbacks/matching.py — SYNAPSE Volunteer Matching Fallback

This file provides the haversine straight-line distance matching fallback
used when OSRM (Open Source Routing Machine) is unavailable.

Primary path: OSRM actual road travel time + Gemini skill embeddings
Fallback 1:   Haversine straight-line distance + Gemini skill embeddings  ← this file
Fallback 2:   Haversine + radius filter only (Gemini unavailable)
Fallback 3:   Accept all available volunteers (no proximity constraint)

Previously this docstring referenced "Routes API" (Google Routes API).
OSRM is now the primary routing source — haversine remains the fallback.
No logic changes — only comment updates.
"""

import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Haversine formula ─────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate straight-line distance between two points in kilometres.

    Used as the primary fallback when OSRM travel-time routing is unavailable.
    Pure Python — no external API, no quota, always works.
    """
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def haversine_proximity_score(distance_km: float, max_km: float = 20.0) -> float:
    """
    Convert a haversine distance to a 0–30 proximity score.

    0 km  → 30 points (maximum proximity score)
    max_km → 0 points
    """
    if distance_km >= max_km:
        return 0.0
    return round(30.0 * (1.0 - distance_km / max_km), 2)


# ── Fallback matching pipeline ────────────────────────────────────────────────

def match_volunteers_haversine(
    need: dict,
    volunteers: list[dict],
    radius_km: float = 5.0,
    max_results: int = 3,
) -> list[dict]:
    """
    Match volunteers to a need using haversine distance only.

    Called when OSRM routing is unavailable. Ranks candidates by:
      proximity_score (30%) + completion_rate (20%) → total out of 50
    Skill similarity is excluded because Gemini embeddings are also unavailable
    in a full-fallback scenario (see Fallback 2 in the matching pipeline).

    Args:
        need:        {"lat": float, "lng": float, ...}
        volunteers:  [{"id": str, "lat": float, "lng": float,
                       "completion_rate": float, ...}, ...]
        radius_km:   search radius — 5km default, expanded to 15km in Fallback 3
        max_results: top N to return

    Returns:
        List of volunteer dicts with added keys:
          distance_km, proximity_score, match_score, match_source
    """
    need_lat = need["lat"]
    need_lng = need["lng"]

    candidates = []
    for v in volunteers:
        dist = haversine_km(need_lat, need_lng, v["lat"], v["lng"])
        if dist > radius_km:
            continue

        prox = haversine_proximity_score(dist, max_km=radius_km)
        completion = v.get("completion_rate", 0.5) * 20  # 0–20 points

        candidates.append({
            **v,
            "distance_km": round(dist, 2),
            "proximity_score": prox,
            "match_score": round(prox + completion, 2),
            "match_source": "haversine_fallback",
        })

    candidates.sort(key=lambda x: x["match_score"], reverse=True)

    if not candidates and radius_km < 15.0:
        # Fallback 3: expand radius
        logger.warning(
            "No volunteers within %.1fkm — expanding radius to 15km (Fallback 3)", radius_km
        )
        return match_volunteers_haversine(need, volunteers, radius_km=15.0, max_results=max_results)

    if not candidates:
        # Fallback 3 (final): accept all available volunteers regardless of distance
        logger.warning("No volunteers within 15km — returning all available (Fallback 3 final)")
        return [
            {
                **v,
                "distance_km": round(haversine_km(need_lat, need_lng, v["lat"], v["lng"]), 2),
                "proximity_score": 0.0,
                "match_score": v.get("completion_rate", 0.5) * 20,
                "match_source": "all_available_fallback",
            }
            for v in volunteers
        ][:max_results]

    return candidates[:max_results]
