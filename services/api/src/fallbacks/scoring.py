# services/api/src/fallbacks/scoring.py
# SYNAPSE — Rule-Based Urgency Scoring Fallback
# Used whenever Gemini is unavailable (quota exceeded, timeout, network error).
# Returns IDENTICAL schema to Gemini urgency scoring — drop-in replacement.

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Keyword tiers ───────────────────────────────────────────────────────────
CRITICAL_KEYWORDS = [
    "death", "dying", "dead", "bodies", "fatality", "fatalities",
    "emergency", "flood", "flash flood", "fire", "collapse", "building collapse",
    "drowning", "explosion", "blast", "cyclone", "earthquake",
    "critical", "severe", "disaster", "epidemic", "outbreak", "contamination",
    "poisoning", "famine", "starvation", "displacement", "evacuated"
]

HIGH_KEYWORDS = [
    "water", "no water", "water shortage", "drinking water",
    "food", "hunger", "malnourished", "malnutrition",
    "medicine", "medication", "hospital", "sick", "illness", "disease",
    "injury", "injured", "fever", "diarrhea", "cholera", "dengue",
    "child", "children", "infant", "pregnant", "maternal",
    "violence", "unsafe", "threat", "danger", "attack"
]

MODERATE_KEYWORDS = [
    "shelter", "housing", "roof", "leaking", "damaged",
    "school", "education", "learning", "students",
    "sanitation", "hygiene", "toilet", "latrine", "sewage",
    "garbage", "waste", "flooding", "waterlogging",
    "repair", "infrastructure", "road", "bridge"
]

LOW_KEYWORDS = [
    "support", "training", "awareness", "workshop", "program",
    "community", "development", "capacity building",
    "information", "guidance", "counselling"
]

# Districts in remoteness bottom quartile (populated from env or seed)
RURAL_DISTRICT_CODES: set[str] = set(
    os.environ.get("RURAL_DISTRICT_CODES", "").split(",")
)

# Category-specific base scores (used when category is clear but description is sparse)
CATEGORY_BASE_SCORES = {
    "disaster_relief":  85,
    "health":           65,
    "food_security":    65,
    "water_sanitation": 60,
    "shelter":          50,
    "education":        40,
    "employment":       30,
    "other":            35
}


def _keyword_tier(text: str) -> tuple[str, int]:
    """Classify text into urgency tier using keyword matching. Returns (tier, base_score)."""
    text_lower = text.lower()

    if any(kw in text_lower for kw in CRITICAL_KEYWORDS):
        return "critical", 85
    if any(kw in text_lower for kw in HIGH_KEYWORDS):
        return "high", 65
    if any(kw in text lower for kw in MODERATE_KEYWORDS):
        return "moderate", 45
    if any(kw in text_lower for kw in LOW_KEYWORDS):
        return "low", 20

    return "unknown", 25   # Default: slightly above minimum


def _apply_affected_boost(score: int, affected_count: int) -> tuple[int, str]:
    """Apply affected-count boost and return (boosted_score, note)."""
    if affected_count > 500:
        return min(100, score + 15), f"affected count {affected_count} (+15)"
    if affected_count > 100:
        return min(100, score + 10), f"affected count {affected_count} (+10)"
    if affected_count > 50:
        return min(100, score + 5), f"affected count {affected_count} (+5)"
    return score, ""


def _apply_rural_boost(score: int, admin_code: str) -> tuple[int, bool]:
    """Apply 1.3× rural multiplier for bottom-quartile remoteness districts."""
    if admin_code and admin_code in RURAL_DISTRICT_CODES:
        return min(100, int(score * 1.3)), True
    return score, False


def _score_to_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "moderate"
    return "low"


def _build_explanation(
    tier: str,
    base_score: int,
    final_score: int,
    affected_boost_note: str,
    rural_applied: bool,
    category: str,
    affected_count: int
) -> str:
    parts = [
        f"Urgency estimated via rule-based keyword analysis (Gemini unavailable).",
        f"Keyword classification: {tier} tier (base score {base_score})."
    ]
    if affected_boost_note:
        parts.append(f"Count boost applied: {affected_boost_note}.")
    if rural_applied:
        parts.append("Rural district multiplier (×1.3) applied.")
    if category and category != "other":
        parts.append(f"Category '{category}' confirmed tier assessment.")
    return " ".join(parts)


# ─── Main public function ─────────────────────────────────────────────────────
def rule_based_score(
    description: str,
    category: str = "other",
    affected_count: int = 0,
    admin_code: str = "",
    location_name: str = ""
) -> dict:
    """
    Rule-based urgency scoring. Drop-in fallback for score_urgency() in gemini.py.

    Returns exactly the same schema as Gemini scoring:
    {
        "score": int 0-100,
        "level": "critical" | "high" | "moderate" | "low",
        "explanation": str,
        "source": "rule_based_fallback"
    }
    """
    combined_text = f"{description} {category} {location_name}"

    # Step 1: Keyword tier detection
    tier, base_score = _keyword_tier(combined_text)

    # Step 2: Category override (if keyword match is weak)
    if tier == "unknown" and category in CATEGORY_BASE_SCORES:
        base_score = CATEGORY_BASE_SCORES[category]
        tier = _score_to_level(base_score)

    # Step 3: Affected count boost
    score, affected_note = _apply_affected_boost(base_score, affected_count)

    # Step 4: Rural multiplier
    score, rural_applied = _apply_rural_boost(score, admin_code)

    # Step 5: Final level
    level = _score_to_level(score)

    explanation = _build_explanation(
        tier, base_score, score, affected_note, rural_applied, category, affected_count
    )

    return {
        "score": score,
        "level": level,
        "explanation": explanation,
        "source": "rule_based_fallback"
    }


# ─── Batch scoring (for re-scoring many needs) ───────────────────────────────
def batch_rule_based_score(needs: list[dict]) -> list[dict]:
    """
    Score a list of needs dicts. Each dict must have keys:
    description, category, affected_count, admin_code, location_name (all optional except description).
    Returns list with urgency_score and urgency_level injected.
    """
    results = []
    for need in needs:
        scored = rule_based_score(
            description=need.get("description", ""),
            category=need.get("category", "other"),
            affected_count=need.get("affected_count", 0),
            admin_code=need.get("admin_code", ""),
            location_name=need.get("location_name", "")
        )
        results.append({**need, **scored})
    return results
