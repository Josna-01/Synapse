# services/api/src/integrations/gemini.py
# SYNAPSE — Gemini Integration Layer
# Primary: gemini-2.5-flash | Bulk: gemini-2.5-flash-lite | Reports: gemini-2.5-pro
# Every call has fallback. No single point of failure.

import os
import logging
import asyncio
import base64
import httpx
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Model constants ────────────────────────────────────────────────────────
GEMINI_FLASH   = "gemini-2.5-flash"
GEMINI_LITE    = "gemini-2.5-flash-lite"   # bulk / quota-saving calls
GEMINI_PRO     = "gemini-2.5-pro"           # digest / CSR reports
EMBED_MODEL    = "text-embedding-004"        # Gemini Embedding 2

GEMINI_BASE    = "https://generativelanguage.googleapis.com/v1beta"
VISION_BASE    = "https://vision.googleapis.com/v1"

API_KEY = os.environ["GEMINI_API_KEY"]
VISION_KEY = os.environ.get("GOOGLE_CLOUD_API_KEY", API_KEY)

TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# ─── Urgency keyword tiers (used as Gemini fallback) ────────────────────────
KEYWORD_TIERS = {
    "critical": {
        "words": ["death", "dying", "dead", "emergency", "flood", "fire", "collapse",
                  "drowning", "explosion", "critical", "severe", "disaster", "fatality"],
        "base": 85
    },
    "high": {
        "words": ["water", "food", "hunger", "starvation", "medicine", "sick", "disease",
                  "injury", "hospital", "fever", "malnutrition", "epidemic", "outbreak"],
        "base": 65
    },
    "moderate": {
        "words": ["shelter", "school", "sanitation", "hygiene", "toilet", "roof",
                  "education", "repair", "damage", "flooding", "contamination"],
        "base": 45
    },
    "low": {
        "words": ["support", "training", "awareness", "program", "workshop",
                  "community", "development", "capacity"],
        "base": 20
    }
}

RURAL_BOTTOM_QUARTILE = set(os.environ.get("RURAL_DISTRICT_CODES", "").split(","))


# ─── Haversine (used as Routes API fallback) ─────────────────────────────────
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# ─── Core HTTP helper ────────────────────────────────────────────────────────
async def _post_gemini(model: str, payload: dict) -> dict:
    url = f"{GEMINI_BASE}/models/{model}:generateContent?key={API_KEY}"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _extract_text(resp: dict) -> str:
    return resp["candidates"][0]["content"]["parts"][0]["text"]


# ─── Rule-based urgency score fallback ───────────────────────────────────────
def rule_based_score(
    description: str,
    affected_count: int = 0,
    admin_code: str = "",
    category: str = ""
) -> dict:
    """
    Keyword-based urgency scoring. Returns same schema as Gemini scoring.
    Used whenever Gemini is unavailable (quota, timeout, network).
    """
    text = (description + " " + category).lower()
    score = 20
    level_label = "low"

    for tier, data in KEYWORD_TIERS.items():
        if any(word in text for word in data["words"]):
            score = data["base"]
            level_label = tier
            break

    # Affected count boost
    if affected_count > 500:
        score = min(100, score + 15)
    elif affected_count > 100:
        score = min(100, score + 10)

    # Rural boost
    if admin_code in RURAL_BOTTOM_QUARTILE:
        score = min(100, int(score * 1.3))

    # Determine level
    if score >= 80:
        level = "critical"
    elif score >= 60:
        level = "high"
    elif score >= 40:
        level = "moderate"
    else:
        level = "low"

    explanation = (
        f"Urgency estimated via keyword analysis (Gemini unavailable). "
        f"Detected tier: {level_label}. "
        f"Score factors: description keywords ({level_label} tier → base {score})"
        + (f", affected count {affected_count} (+boost)" if affected_count > 100 else "")
        + (", rural district multiplier applied." if admin_code in RURAL_BOTTOM_QUARTILE else ".")
    )

    return {
        "score": score,
        "level": level,
        "explanation": explanation,
        "source": "rule_based_fallback"
    }


# ─── score_urgency() ─────────────────────────────────────────────────────────
async def score_urgency(
    description: str,
    category: str,
    affected_count: int,
    admin_code: str = "",
    location_name: str = ""
) -> dict:
    """
    Primary: Gemini 2.5 Flash scoring with weighted formula.
    Fallback: rule_based_score().
    Returns: { score, level, explanation, source }
    """
    prompt = f"""You are a humanitarian urgency scoring engine.

Score this community need report on a scale of 0-100 using this EXACT formula:

score = (severity × 0.35) + (frequency × 0.25) + (recency_decay × 0.20) + (population × 0.20)

Where:
- severity (0-35): NLP classification of report text gravity
- frequency (0-25): estimated repeat rate / clustering likelihood
- recency_decay (0-20): 20 × e^(-0.1 × estimated_days_of_persistence)
- population (0-20): estimated population density impact, normalized

Levels: critical ≥80 | high 60-79 | moderate 40-59 | low <40
Rural districts (bottom quartile remoteness): apply 1.3× multiplier, cap at 100.

Input:
Category: {category}
Description: {description}
Affected count: {affected_count}
Location: {location_name}
Admin code: {admin_code}

Respond in this exact JSON format (no markdown):
{{
  "score": <integer 0-100>,
  "level": "<critical|high|moderate|low>",
  "explanation": "<2-sentence plain-language explanation any government official can audit>"
}}"""

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 300}
        }
        resp = await _post_gemini(GEMINI_FLASH, payload)
        raw = await _extract_text(resp)
        import json
        data = json.loads(raw.strip())
        data["source"] = "gemini"
        return data

    except Exception as e:
        logger.warning(f"score_urgency Gemini failed ({e}), using rule-based fallback")
        return rule_based_score(description, affected_count, admin_code, category)


# ─── extract_need_from_ocr() ──────────────────────────────────────────────────
async def extract_need_from_ocr(image_url: str) -> dict:
    """
    Primary: Cloud Vision API → full text → Gemini structured extraction.
    Fallback: Returns partial schema with error flag for manual form completion.
    """
    # Step 1: Cloud Vision OCR
    raw_text = ""
    vision_ok = False
    try:
        url = f"{VISION_BASE}/images:annotate?key={VISION_KEY}"
        payload = {
            "requests": [{
                "image": {"source": {"imageUri": image_url}},
                "features": [
                    {"type": "DOCUMENT_TEXT_DETECTION"},
                    {"type": "TEXT_DETECTION"}
                ]
            }]
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        raw_text = data["responses"][0].get("fullTextAnnotation", {}).get("text", "")
        vision_ok = bool(raw_text.strip())
    except Exception as e:
        logger.warning(f"Cloud Vision OCR failed ({e}), returning manual-entry fallback")

    if not vision_ok:
        return {
            "extracted": False,
            "requires_manual_entry": True,
            "fields": {},
            "source": "vision_api_failed"
        }

    # Step 2: Gemini structured extraction from OCR text
    prompt = f"""Extract structured fields from this humanitarian survey text (OCR output from a field survey photo).

OCR Text:
{raw_text}

Return ONLY this JSON (no markdown, no explanation):
{{
  "category": "<water_sanitation|food_security|health|shelter|education|employment|disaster_relief|other>",
  "description": "<concise summary of the need, max 200 chars>",
  "location_raw": "<address or place name as found in text>",
  "affected_count": <integer or null>,
  "reporter_name": "<name if found or null>",
  "reporter_org": "<organisation if found or null>",
  "date_reported": "<YYYY-MM-DD if found or null>",
  "urgency_keywords": ["<keyword1>", "<keyword2>"]
}}"""

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 500}
        }
        resp = await _post_gemini(GEMINI_FLASH, payload)
        raw = await _extract_text(resp)
        import json
        fields = json.loads(raw.strip())
        return {
            "extracted": True,
            "requires_manual_entry": False,
            "fields": fields,
            "raw_ocr_text": raw_text,
            "source": "vision_api+gemini"
        }
    except Exception as e:
        logger.warning(f"Gemini field extraction failed ({e})")
        return {
            "extracted": True,
            "requires_manual_entry": True,
            "fields": {"raw_ocr_text": raw_text},
            "source": "vision_api_only_gemini_failed"
        }


# ─── generate_match_explanation() ────────────────────────────────────────────
async def generate_match_explanation(
    volunteer_name: str,
    volunteer_skills: list[str],
    task_requirements: str,
    skill_similarity: float,
    travel_time_mins: float,
    urgency_score: int,
    match_source: str = "routes_api"
) -> dict:
    """
    Primary: Gemini Flash generates natural-language match explanation for FCM push.
    Fallback: Template string.
    """
    source_label = "Live traffic routing (Routes API)" if match_source == "routes_api" else "Estimated distance (API unavailable)"

    try:
        prompt = f"""Generate a concise volunteer match explanation for a humanitarian dispatch notification.
Keep it under 30 words. Warm, action-oriented tone.

Volunteer: {volunteer_name}
Skills: {', '.join(volunteer_skills)}
Task requirement: {task_requirements}
Skill match: {skill_similarity:.0%}
Travel time: {travel_time_mins:.0f} minutes
Urgency score: {urgency_score}/100

Format: "Matched: <skill reason> ({similarity}%), <travel_time> min away, available now."
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 80}
        }
        resp = await _post_gemini(GEMINI_LITE, payload)
        explanation = (await _extract_text(resp)).strip()
        return {
            "explanation": explanation,
            "match_source_label": source_label,
            "source": "gemini"
        }
    except Exception as e:
        logger.warning(f"generate_match_explanation Gemini failed ({e}), using template")
        top_skill = volunteer_skills[0] if volunteer_skills else "skill"
        explanation = (
            f"Matched: {top_skill} ({skill_similarity:.0%}), "
            f"{travel_time_mins:.0f} min away, available now."
        )
        return {
            "explanation": explanation,
            "match_source_label": source_label,
            "source": "template_fallback"
        }


# ─── generate_impact_report() ────────────────────────────────────────────────
async def generate_impact_report(
    ngo_name: str,
    period: str,
    needs_resolved: int,
    people_helped: int,
    top_needs: list[dict],
    donations_received: float,
    volunteers_deployed: int
) -> dict:
    """
    Primary: Gemini Pro generates donor-facing narrative impact report.
    Fallback: Structured template with same data.
    """
    needs_summary = "\n".join(
        [f"- {n.get('category','')}: {n.get('description','')} (urgency {n.get('urgency_score',0)})" for n in top_needs[:5]]
    )
    prompt = f"""You are writing a formal donor impact report for a humanitarian NGO.
Write 3 paragraphs (max 250 words total) that a donor will read to understand impact.
Tone: professional, evidence-based, warm. Use numbers prominently.

NGO: {ngo_name}
Period: {period}
Needs resolved: {needs_resolved}
People helped: {people_helped:,}
Donations received: ₹{donations_received:,.0f}
Volunteers deployed: {volunteers_deployed}
Top resolved needs:
{needs_summary}

Do NOT use markdown. Write plain paragraphs only."""

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 400}
        }
        resp = await _post_gemini(GEMINI_PRO, payload)
        narrative = (await _extract_text(resp)).strip()
        return {"narrative": narrative, "source": "gemini"}
    except Exception as e:
        logger.warning(f"generate_impact_report Gemini failed ({e}), using template")
        narrative = (
            f"{ngo_name} Impact Report — {period}\n\n"
            f"During this period, {ngo_name} resolved {needs_resolved} community needs, "
            f"directly supporting {people_helped:,} people across identified wards. "
            f"A total of {volunteers_deployed} volunteers were deployed across critical areas.\n\n"
            f"Donor contributions of ₹{donations_received:,.0f} were fully channelled into "
            f"verified field operations, with GPS-confirmed task completion for all major interventions.\n\n"
            f"Top resolved categories included: "
            + ", ".join([n.get("category", "") for n in top_needs[:3]]) + "."
        )
        return {"narrative": narrative, "source": "template_fallback"}


# ─── get_embedding() ─────────────────────────────────────────────────────────
async def get_embedding(text: str) -> list[float]:
    """
    Gemini Embedding 2 for skill similarity (cosine similarity matching).
    Fallback: TF-IDF approximation using shared vocabulary.
    """
    try:
        url = f"{GEMINI_BASE}/models/{EMBED_MODEL}:embedContent?key={API_KEY}"
        payload = {
            "model": f"models/{EMBED_MODEL}",
            "content": {"parts": [{"text": text}]}
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()["embedding"]["values"]
    except Exception as e:
        logger.warning(f"get_embedding failed ({e}), returning zeros (fallback to keyword matching)")
        return []


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    from math import sqrt
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sqrt(sum(x ** 2 for x in a))
    mag_b = sqrt(sum(x ** 2 for x in b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def keyword_similarity_fallback(skills: list[str], requirements: str) -> float:
    """Simple word overlap when embeddings are unavailable."""
    req_words = set(requirements.lower().split())
    skill_words = set(" ".join(skills).lower().split())
    overlap = len(req_words & skill_words)
    return min(1.0, overlap / max(len(req_words), 1))


async def skill_similarity(volunteer_skills: list[str], task_requirements: str) -> tuple[float, str]:
    """
    Returns (similarity_score 0-1, source_label).
    Primary: Gemini embeddings + cosine similarity.
    Fallback: keyword overlap.
    """
    skills_text = " ".join(volunteer_skills)
    emb_a = await get_embedding(skills_text)
    emb_b = await get_embedding(task_requirements)
    if emb_a and emb_b:
        return cosine_similarity(emb_a, emb_b), "gemini_embedding"
    score = keyword_similarity_fallback(volunteer_skills, task_requirements)
    return score, "keyword_fallback"


# ─── generate_govt_digest() ──────────────────────────────────────────────────
async def generate_govt_digest(
    district: str,
    top_needs: list[dict],
    coverage_gaps: list[dict],
    scheme_matches: list[dict],
    resolution_rate_this_week: float,
    resolution_rate_last_week: float,
    anomaly_flags: list[str],
    language: str = "English"
) -> dict:
    """
    Gemini Pro generates the weekly government digest.
    Fallback: structured plain-text template.
    """
    gaps_text = "\n".join([f"- Ward {g.get('ward')}: urgency {g.get('avg_urgency')}, zero NGO activity, category: {g.get('category')}" for g in coverage_gaps[:5]])
    needs_text = "\n".join([f"- {n.get('category')}: {n.get('description')} (score {n.get('urgency_score')})" for n in top_needs[:5]])
    scheme_text = "\n".join([f"- {s.get('category')} → {s.get('scheme')} ({s.get('source')})" for s in scheme_matches[:5]])

    prompt = f"""You are generating an official government district briefing for humanitarian coordination.
Write a formal 2-page digest in {language}. Use section headers. Tone: official, data-driven.

District: {district}
Week ending: {datetime.now().strftime('%d %B %Y')}
Resolution rate this week: {resolution_rate_this_week:.1%}
Resolution rate last week: {resolution_rate_last_week:.1%}
Anomaly flags: {'; '.join(anomaly_flags) if anomaly_flags else 'None'}

Top needs by urgency:
{needs_text}

Coverage gaps (high need, zero NGO activity):
{gaps_text}

Scheme matches:
{scheme_text}

Write the briefing now."""

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1500}
        }
        resp = await _post_gemini(GEMINI_PRO, payload)
        digest = (await _extract_text(resp)).strip()
        return {"digest": digest, "source": "gemini_pro"}
    except Exception as e:
        logger.warning(f"generate_govt_digest Gemini failed ({e}), using template")
        digest = (
            f"DISTRICT HUMANITARIAN BRIEFING — {district}\n"
            f"Week ending {datetime.now().strftime('%d %B %Y')}\n\n"
            f"RESOLUTION PERFORMANCE\n"
            f"This week: {resolution_rate_this_week:.1%} | Last week: {resolution_rate_last_week:.1%}\n\n"
            f"TOP PRIORITY NEEDS\n{needs_text}\n\n"
            f"COVERAGE GAPS REQUIRING ATTENTION\n{gaps_text}\n\n"
            f"GOVERNMENT SCHEME MATCHES\n{scheme_text}\n\n"
            f"ANOMALY FLAGS\n{'; '.join(anomaly_flags) if anomaly_flags else 'None detected.'}"
        )
        return {"digest": digest, "source": "template_fallback"}


# ─── api_wrapper (generic call-with-fallback) ─────────────────────────────────
async def api_call(primary, fallback, *args, **kwargs):
    """
    Generic wrapper: try primary → on any error → run fallback.
    Returns (result, source_label).
    """
    try:
        result = await primary(*args, **kwargs)
        return result, "primary"
    except Exception as e:
        logger.warning(f"Primary call failed ({e}), running fallback")
        try:
            result = await fallback(*args, **kwargs)
            return result, "fallback"
        except Exception as fe:
            logger.error(f"Fallback also failed ({fe})")
            raise
