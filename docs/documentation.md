# SYNAPSE — Complete Project Documentation
## Industry-Level Technical Reference

---

## Section 1: Core Concept

### Misallocation vs Scarcity — The Critical Distinction

Most humanitarian technology platforms are built on a false assumption: that the problem
is lack of resources. SYNAPSE is built on the correct insight: resources exist, but they
cannot see each other clearly enough to coordinate.

**Evidence:**
- India has 3.3 million registered NGOs — more than any country on earth.
- NSS + NCC + NYKS collectively have 13 million active youth volunteers.
- India's mandatory CSR spend (Companies Act 2013) generates ₹26,000+ crore annually.
- Jal Jeevan Mission has budget for FHTC to every rural household — yet coverage is
  incomplete in thousands of villages that have filed water shortage reports.

The gap between resource existence and resource deployment is caused by:
1. Fragmented data — 5 NGOs surveying the same street, none knowing about each other
2. Manual triage — coordinators making urgency decisions by gut feel or relationship
3. Passive matching — volunteers picking convenient tasks, not urgent ones
4. Invisible coverage gaps — no system shows where help is absent despite documented need
5. No feedback loop — outcomes never feed back into resource allocation decisions

SYNAPSE solves all five simultaneously.

---

## Section 2: Complete System Workflow

```
STEP 1 — FIELD DATA CAPTURE (Input layer)
─────────────────────────────────────────
Field worker is in the community and observes a need.

Input channel A: Paper survey photo
  → Field worker photographs printed survey form
  → pytesseract (local OCR) + Gemini extracts structured fields
  → Time: 8 seconds from photo to Firestore record

Input channel B: WhatsApp voice note
  → Field worker sends voice note to SYNAPSE WhatsApp number
  → OpenAI Whisper (local, free) transcribes (125 languages, auto-detect)
  → Gemini NLP extracts: location, category, affected_count, severity
  → Time: 15 seconds

Input channel C: Web form / QR code
  → Community member scans QR code on NGO-printed poster
  → Fills 3-field web form (no login required)
  → Anonymous submission option available

Input channel D: Open data connectors (background)
  → World Bank API, UN HDX, WHO GHO pull daily context
  → Population density, disease burden, infrastructure gaps
  → Enriches urgency scoring without manual input

Input channel E: CSV import
  → NGOs with existing spreadsheet data upload CSV
  → Gemini normalises field names and maps to SYNAPSE schema
  → Bulk import of historical records

STEP 2 — AI PROCESSING (Intelligence layer)
────────────────────────────────────────────
Every incoming report passes through this pipeline:

1. Language detection (langdetect library)
2. Translation if needed (LibreTranslate — free, open source + humanitarian glossary)
3. Named Entity Recognition (Gemini extracts: location, category, people count)
4. Geocoding (Nominatim API → lat/lng + LGD admin boundary codes)
5. Deduplication check (Gemini semantic similarity, 500m geo radius, 30-day window)
6. Urgency scoring (formula: severity 35% + frequency 25% + recency 20% + population 20%)
7. Rural remoteness boost (bottom-quartile districts: score × 1.3)
8. Write to /needs collection in Firestore
9. Firestore listeners trigger live map update in all open dashboards

STEP 3 — NGO TRIAGE (Decision layer)
─────────────────────────────────────
Normal flow (urgency < 80):
  → Need appears in coordinator's priority queue (sorted by score)
  → Coordinator reviews urgency breakdown + plain-language explanation
  → Coordinator clicks "Find Volunteers"
  → Matching engine returns top 3 candidates with explanation
  → Coordinator selects and dispatches
  → FCM push sent to volunteer

Fast-track flow (urgency ≥ 80):
  → System auto-dispatches to top-matched available volunteer
  → Coordinator is NOTIFIED (not asked — already happening)
  → SLA: volunteer notified within 5 minutes

STEP 4 — VOLUNTEER EXECUTION (Field layer)
───────────────────────────────────────────
  → Volunteer receives FCM push with match explanation
  → Views task detail (requirements, location, context, why matched)
  → Accepts task (one tap)
  → Travels to location (flutter_map + OSRM navigation)
  → GPS check-in on arrival (verifies attendance)
  → Executes task
  → Submits outcome form: resolved? rating 1-5? people helped? notes?
  → Badge criteria evaluated automatically
  → Outcome data written to /outcomes collection

STEP 5 — GOVERNMENT MONITORING (Policy layer)
──────────────────────────────────────────────
Weekly (Monday 6am):
  → Govt Agent reads aggregated /needs data by district
  → Detects coverage gaps (high urgency + zero NGO activity)
  → Matches need clusters to government scheme database
  → Gemini 2.5 Pro generates 2-page district digest
  → Resend delivers digest to subscribed officials

On anomaly:
  → If district urgency rises 3σ above 30-day baseline
  → Immediate alert to district admin
  → SDRF/NDRF suggestion if disaster_relief category

STEP 6 — DONOR IMPACT TRACKING (Accountability layer)
───────────────────────────────────────────────────────
  → Donation received → linked to specific campaign → campaign linked to need cluster
  → When volunteer completes task: impact chain computed
  → Donor sees: donation → task dispatched → GPS check-in verified → outcome confirmed
  → Monthly Resend email: personalised impact update with exact numbers
  → CSR export: Section 80G receipt + utilisation certificate (PDF in Supabase Storage)

STEP 7 — FEEDBACK LOOP (Learning layer)
────────────────────────────────────────
Weekly:
  → All closed tasks with outcome reports collected
  → Was urgency score accurate? (ground truth: was need actually resolved?)
  → Was volunteer match effective? (ground truth: outcome rating)
  → Urgency model weights updated
  → Model accuracy tracked in analytics dashboard
```

---

## Section 2B: Fallback Architecture — System Never Fails

> **Design principle:** Every AI-powered step has a rule-based fallback. Every API call
> has a degraded-mode alternative. The system ALWAYS produces a result — even with zero
> quota remaining on every external API.

### Why Fallback Matters

SYNAPSE is designed for deployment in areas where network connectivity is unreliable,
API quotas run out during a crisis surge, and field workers may not have smartphones.
A system that fails when demand peaks is worse than no system — it creates false
confidence and breaks coordinator workflows at the worst possible moment.

**The fallback principle:** Degrade gracefully, never fail silently, always return a
result with a clear label indicating the source (`gemini`, `rule_based_fallback`,
`haversine_fallback`, `default_fallback`).

---

### Fallback Layer 1: Urgency Scoring

```
PRIMARY:   Gemini 2.5 Flash NLP classification → weighted formula → 0-100 score
              ↓ (if Gemini quota exhausted or API unreachable)
SECONDARY: Rule-based keyword scoring
              ↓ (if text is empty or no keywords match)
TERTIARY:  Default score = 50 (moderate) with explanation flag
```

**Rule-based fallback implementation:**

```python
# services/api/src/fallbacks/scoring.py

KEYWORDS = {
    "critical": ["death", "dying", "emergency", "flood", "fire", "cholera",
                 "famine", "outbreak", "collapse", "explosion"],
    "high":     ["water", "food", "hunger", "medicine", "sick", "injury",
                 "shortage", "contamination", "malnutrition", "dehydration"],
    "moderate": ["shelter", "school", "sanitation", "hygiene", "latrine",
                 "displacement", "homeless", "repair", "access"],
    "low":      ["support", "training", "awareness", "documentation", "survey"]
}

def rule_based_score(text: str, affected_count: int = 0) -> dict:
    text_lower = text.lower()
    base_score = 20  # default floor

    for word in KEYWORDS["critical"]:
        if word in text_lower:
            base_score = 85
            break

    for word in KEYWORDS["high"]:
        if word in text_lower:
            base_score = max(base_score, 65)
            break

    for word in KEYWORDS["moderate"]:
        if word in text_lower:
            base_score = max(base_score, 45)
            break

    if affected_count > 500:
        base_score = min(base_score + 15, 100)
    elif affected_count > 100:
        base_score = min(base_score + 10, 100)

    return {
        "score": base_score,
        "source": "rule_based_fallback",
        "explanation": f"Estimated score based on keyword analysis. "
                       f"Affected: {affected_count}. AI scoring unavailable."
    }

def default_score() -> dict:
    return {
        "score": 50,
        "source": "default_fallback",
        "explanation": "Default moderate score assigned. "
                       "Coordinator review required."
    }
```

**Integration in urgency pipeline:**

```python
# services/api/src/agents/ngo_agent.py

async def compute_urgency_score(need: dict) -> dict:
    try:
        result = await gemini_score(need)
        result["source"] = "gemini"
        return result
    except QuotaExceededError:
        return rule_based_score(need["description"], need.get("affected_count", 0))
    except Exception:
        return default_score()
```

---

### Fallback Layer 2: Volunteer Matching

```
PRIMARY:   OSRM actual road travel time → Gemini embedding cosine similarity
              ↓ (if OSRM unavailable or timeout)
SECONDARY: Haversine straight-line distance (geographic formula, no API)
              ↓ (if volunteer location data unavailable)
TERTIARY:  Radius filter only — return all volunteers within 15km
              ↓ (if no volunteers qualify)
QUATERNARY: Accept all available volunteers regardless of distance
```

**Haversine fallback implementation:**

```python
# services/api/src/fallbacks/matching.py

from math import radians, sin, cos, sqrt, atan2

def haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = (sin(dlat / 2) ** 2 +
         cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2)
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def haversine_filter(task_lat, task_lng, volunteers, max_km=15):
    """
    Fallback when OSRM routing is unavailable.
    Uses straight-line distance instead of actual travel time.
    Returns volunteers sorted by distance, labelled as fallback.
    """
    nearby = []
    for v in volunteers:
        dist = haversine_km(task_lat, task_lng, v["lat"], v["lng"])
        if dist <= max_km:
            v["estimated_km"] = round(dist, 2)
            v["match_source"] = "haversine_fallback"
            v["match_note"] = "Straight-line distance. Actual travel time unavailable."
            nearby.append(v)
    return sorted(nearby, key=lambda x: x["estimated_km"])

def radius_accept_all(volunteers):
    """
    Last resort: return all available volunteers with no distance filter.
    Used when location data is missing or no volunteers pass proximity filter.
    """
    for v in volunteers:
        v["match_source"] = "accept_all_fallback"
        v["match_note"] = "No proximity filtering applied. Coordinator should verify."
    return volunteers
```

**Integration in matching pipeline:**

```python
# services/api/src/agents/volunteer_agent.py

async def find_volunteer_matches(need: dict, limit: int = 3) -> list:
    try:
        # Primary: OSRM travel time + Gemini skill similarity
        return await osrm_and_gemini_match(need, limit)
    except OSRMError:
        # Secondary: Haversine distance
        all_volunteers = await get_available_volunteers()
        return haversine_filter(
            need["location"]["lat"],
            need["location"]["lng"],
            all_volunteers
        )[:limit]
    except Exception:
        # Tertiary: Return all available volunteers
        all_volunteers = await get_available_volunteers()
        return radius_accept_all(all_volunteers)[:limit]
```

---

### Fallback Layer 3: OCR / Survey Intake

```
PRIMARY:   pytesseract (local) + Gemini → automatic field extraction
              ↓ (if OCR confidence < 0.7 or pytesseract fails)
SECONDARY: Manual entry form — pre-filled with any partial extraction results
```

**Implementation:**

```python
# services/api/src/routers/surveys.py

async def process_survey_photo(image_bytes: bytes, org_id: str) -> dict:
    try:
        extracted = await pytesseract_ocr(image_bytes)
        if extracted["confidence"] < 0.7:
            raise LowConfidenceError("OCR confidence below threshold")
        return {**extracted, "source": "ocr_auto", "requires_review": False}
    except (LowConfidenceError, Exception):
        # Return partial data + flag for manual completion
        return {
            "source": "manual_fallback",
            "requires_review": True,
            "prefilled": {},  # Any partial extraction results
            "message": "Automatic extraction unavailable. "
                       "Please complete the form manually."
        }
```

**UI behaviour on fallback:**
- If OCR fails → coordinator sees the original photo on the left, manual form on the right
- Any partial extractions pre-fill the form fields
- Form submission works identically whether auto or manual
- A `source: "manual_fallback"` flag is stored in Firestore for audit purposes

---

### Fallback Layer 4: Notifications

```
PRIMARY:   Firebase Cloud Messaging (FCM) push notification to volunteer app
              ↓ (if FCM token expired or device offline)
SECONDARY: Email notification via Resend
              ↓ (if email not available)
TERTIARY:  In-app notification on next dashboard load (Firestore-based)
```

**Implementation:**

```python
# services/api/src/fallbacks/notify.py

async def notify_volunteer(volunteer: dict, task: dict) -> dict:
    notification_payload = {
        "title": f"Urgent: {task['category'].replace('_', ' ').title()}",
        "body": f"{task['title']} — {task['location_name']}. "
                f"Urgency: {task['urgency_score']}/100. Tap to accept.",
        "data": {"task_id": task["id"], "type": "dispatch"}
    }

    # Attempt 1: FCM push
    if volunteer.get("fcm_token"):
        try:
            await send_fcm(volunteer["fcm_token"], notification_payload)
            return {"channel": "fcm", "status": "sent"}
        except FCMError:
            pass  # fall through

    # Attempt 2: Resend email
    if volunteer.get("email"):
        try:
            await send_resend_email(
                to=volunteer["email"],
                subject=notification_payload["title"],
                body=notification_payload["body"]
            )
            return {"channel": "resend_email", "status": "sent"}
        except EmailError:
            pass  # fall through

    # Attempt 3: In-app Firestore flag
    await db.collection("notifications").add({
        "user_id": volunteer["user_id"],
        "task_id": task["id"],
        "message": notification_payload["body"],
        "read": False,
        "channel": "in_app_fallback",
        "created_at": firestore.SERVER_TIMESTAMP
    })
    return {"channel": "in_app_fallback", "status": "queued"}
```

---

### Fallback Summary Table

| Component | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|-----------|---------|------------|------------|------------|
| Urgency scoring | Gemini 2.5 Flash | Rule-based keywords | Default score (50) | — |
| Volunteer matching | OSRM + Gemini embeddings | Haversine distance | Radius filter only | Accept all available |
| OCR / survey intake | pytesseract + Gemini | Manual form entry | — | — |
| Notifications | FCM push | Resend email | In-app Firestore flag | — |
| Translation | LibreTranslate | langdetect + English passthrough | Raw text stored | — |
| Geocoding | Nominatim API | Manual lat/lng entry | Admin boundary from text | — |

**All fallback responses include a `source` field** so coordinators and the analytics
dashboard can track how often each tier is used.

---

## Section 3: Real-Time Data Sources and APIs

### APIs for Hackathon Demo

| API / Library | URL / Source | Auth | Free Tier | Used For |
|---|---|---|---|---|
| Gemini 2.5 Flash | https://generativelanguage.googleapis.com/v1beta/ | API Key | 15 RPM, 1M tokens/day | OCR extraction, scoring, matching |
| Gemini 2.5 Pro | https://generativelanguage.googleapis.com/v1beta/ | API Key | Paid, used sparingly | Digests, CSR reports |
| pytesseract (local) | pip install pytesseract | None | Free, open source | Survey photo OCR |
| OpenAI Whisper (local) | pip install openai-whisper | None | Free, open source | Voice note transcription |
| LibreTranslate | https://libretranslate.com | Optional | Free tier | Field report translation |
| Nominatim | https://nominatim.openstreetmap.org | None (User-Agent) | Free | Address → lat/lng geocoding |
| OSRM | http://router.project-osrm.org | None | Free | Road travel time |
| Overpass API | https://overpass-api.de/api/interpreter | None | Free | Nearby facilities |
| Leaflet + OSM tiles | https://{s}.tile.openstreetmap.org | None | Free | Web maps (heatmap, choropleth) |
| flutter_map + OSM | pub.dev/packages/flutter_map | None | Free, open source | Flutter volunteer map |
| Supabase Storage | https://supabase.com | API Key | 1GB free | File storage |
| Resend | https://resend.com | API Key | 3,000 emails/month | Digest + donor emails |
| WhatsApp Cloud API | https://graph.facebook.com/v18.0/ | Bearer token | 1,000 conv/month free | Field worker input |
| Firebase (all) | Firebase SDK | Firebase config | Spark plan free | Auth, Firestore, FCM, App Hosting |

### Real Government Data Sources (Production)

| Dataset | URL | Data | Auth |
|---------|-----|------|------|
| NDAP | https://ndap.nic.in/api/ | District health/water/education | Free API key |
| LGD Directory | https://lgdirectory.gov.in/ | Admin boundary codes | Free download |
| Census 2011 | https://censusindia.gov.in/ | Village population | Free download |
| JJM Dashboard | https://ejalshakti.gov.in/jjmreport/ | FHTC coverage by district | Web scrape |
| MGNREGA MIS | https://nregarep2.nic.in/netnrega/ | Employment demand/supply | Web scrape |
| MyScheme Portal | https://www.myscheme.gov.in/api | 750+ schemes + status | API key required |
| SECC 2011 | https://secc.gov.in/ | BPL household data | Free download |
| NASA SEDAC | https://sedac.ciesin.columbia.edu/ | Population density grids | Free API |
| GADM Boundaries | https://gadm.org/download_country.html | Admin GeoJSON polygons | Free download |

### Open Humanitarian Data Sources

| Dataset | URL | Coverage |
|---------|-----|----------|
| UN HDX / OCHA | https://data.humdata.org/api/3/ | 180+ countries, crisis data |
| WHO GHO | https://ghoapi.azureedge.net/api/ | Global health indicators |
| World Bank | https://api.worldbank.org/v2/ | Country poverty/development |
| ReliefWeb | https://api.reliefweb.int/v1/ | Active crisis reports globally |
| OpenStreetMap Overpass | https://overpass-api.de/api/interpreter | Infrastructure points globally |

### Hackathon vs Production Data Strategy

| Component | Hackathon Demo | Production |
|---|---|---|
| Needs data | 12 seeded needs in 3 districts (Firestore) | Live NGO submissions |
| Population density | Hardcoded per demo district | NASA SEDAC API daily cache |
| Admin boundaries | GADM GeoJSON static file | Same + LGD codes |
| Government schemes | 15 schemes as static Firestore documents | MyScheme API live |
| Open data enrichment | Not active | World Bank, WHO, UN HDX daily jobs |
| NGO data | Synthetic realistic profiles | Real NGO onboarding |
| Volunteer profiles | 8 seed volunteers | Real volunteer registrations |

---

## Section 4: NGO Real-World Process

### How NGOs Actually Operate

**Organisation types in India:**
- Tier 1 (large): CRY, Pratham, WaterAid, MSF — 50+ staff, existing digital systems
- Tier 2 (mid-size): 2-20 staff, partially digital, coordinator is also field worker
- Tier 3 (grassroots): 1-3 volunteers, paper-only, WhatsApp is their system

SYNAPSE is designed for Tier 2 and Tier 3 primarily — they have the most acute need for
coordination tools and the least capacity to build their own.

**Verification process (real):**
1. Report received (WhatsApp / paper / call)
2. Coordinator calls field worker to confirm accuracy (2-6 hours delay)
3. Cross-reference with known area data (manual, from memory)
4. SYNAPSE replaces steps 2-3 with: deduplication check (cross-NGO), frequency scoring
   (how many similar reports?), and field worker account verification

**Prioritisation (real):**
- Current: gut feel, loudest phone call, personal relationship with field worker
- SYNAPSE: algorithmic score (0-100) with transparent breakdown — coordinator can audit
  every component and override if they disagree

**Allocation (real):**
- Current: WhatsApp broadcast to volunteer group, wait for reply, 3 rounds minimum
- SYNAPSE: top-3 matched volunteers with skill%, distance, availability — one-tap dispatch

**Reporting (real):**
- Current: 3 days of manual compilation, WhatsApp export archaeology, estimation
- SYNAPSE: one-click Gemini-generated PDF from verified outcome data

---

## Section 5: Government Role

### Relevant Government Schemes and Authorities

| Scheme | Ministry | Coverage | SYNAPSE Alignment |
|--------|----------|----------|-----------------|
| Jal Jeevan Mission | Jal Shakti | Rural FHTC | Water shortage clusters |
| PM-POSHAN | Education | School meals | Child nutrition reports |
| Ayushman Bharat PMJAY | Health | ₹5L health cover | Health emergency reports |
| MGNREGA | Rural Development | 100 days employment | Livelihood distress |
| PMAY-G | Rural Development | Housing for all | Shelter needs |
| Swachh Bharat Mission-G | Jal Shakti | ODF+ sanitation | Sanitation reports |
| Poshan Abhiyan | Women & Child | Child malnutrition | Under-5 malnutrition |
| SDRF/NDRF | NDMA | Disaster response | Disaster relief triggers |

### Why Visibility is Missing Today

1. **Data fragmentation**: District collector receives data from 20-50 NGOs as separate
   PDF reports, quarterly. No aggregated real-time view.

2. **No cross-NGO synthesis**: Two NGOs in the same ward never share data. Collective
   impact is invisible. Coverage gaps are invisible.

3. **Scheme under-utilisation**: District officials are unaware which ground-level needs
   align with currently-open scheme applications.

4. **Monitoring without action**: PFMS, DBT Bharat track spending, not outcomes. A scheme
   can show 100% budget utilisation while the intended beneficiaries remain unserved.

### SYNAPSE Government Value Proposition

1. **Real-time district situational awareness** — without building anything
2. **Coverage gap visibility** — the signature feature no other platform offers
3. **Scheme alignment alerts** — turns data into funding action
4. **Weekly digest replaces quarterly briefings** — 52 briefings/year vs 4

---

## Section 6: Donor Flow and Trust

### How Donors Actually Decide (Psychology)

1. **Awareness** — Campaign appears in search, social, or recommendation
2. **Trust evaluation** — Is this NGO legitimate? (FCRA registration, past reports)
3. **Impact prediction** — If I give ₹5,000, what will actually happen?
4. **First donation** — Small amount to test trust (₹500-2,000 typically)
5. **Impact confirmation** — Did my money do something? (Email, report, update)
6. **Recurring commitment** — Repeat donations or monthly setup
7. **Evangelism** — Share with colleagues, recommend for corporate CSR

### The Trust Crisis

"How do I know my money actually helped?" is the single largest barrier to first-time
NGO donation in India. Current platforms answer with:
- "Your donation helped ~500 people" (estimated, not verified)
- Annual report published 18 months after donation (too late to matter psychologically)
- General programme updates unconnected to specific donations

### SYNAPSE Trust Solution

Every donation is traceable:
```
₹5,000 donation (04 April 2026)
    → Campaign: "Clean Water for Ayawaso West" (WaterAid Ghana, verified ✓)
    → Task #1842 dispatched (05 April 2026)
    → Volunteer: Amara Osei, arrived 06 April 2026 (GPS: 5.614°N, 0.205°W ✓)
    → Outcome: "120 families received water. 480 people. Rating 4.9/5." (07 April 2026)
    → Resend email sent to donor with outcome details
```

Not estimated. Not aggregated. Traceable to a specific GPS coordinate, a named volunteer,
and a dated outcome report.

### CSR Compliance (Corporate Donors)

India's Companies Act 2013 Section 135 requires companies with:
- Net worth ≥ ₹500 crore OR
- Turnover ≥ ₹1,000 crore OR
- Net profit ≥ ₹5 crore

to spend 2% of average net profit on CSR activities and file detailed reports.

SYNAPSE CSR export provides:
- Section 80G donation receipt
- Utilisation certificate (verified outcomes, not declared intention)
- GPS-verified impact metrics (acceptable to company auditors)
- Per-project breakdown with NGO registration numbers
- Format compatible with MCA annual CSR filing
- PDFs stored in Supabase Storage, delivered via signed URL in Resend email

This is the feature that unlocks ₹50,000-5,00,000 corporate donations.

---

## Section 7: Business Impact and Scalability

### Why This is Scalable

1. **Data flywheel**: More NGOs → more needs data → better urgency predictions →
   more accurate dispatch → better outcomes → more NGO trust → more NGOs.

2. **Zero marginal cost per new NGO**: Adding 1,000 more NGOs costs ~$0 in
   infrastructure. Firestore scales automatically. Railway.app scales containers.

3. **API-first architecture**: Any third party can build on SYNAPSE data via the public
   anonymised API. Creates an ecosystem of tools.

4. **Government adoption creates viral expansion**: A single state-level adoption creates
   mandatory data-sharing across all district NGOs in that state.

5. **Fallback architecture enables deployment in low-resource environments**: SYNAPSE works
   even when open-source APIs are rate-limited or connectivity is poor. This is the
   critical differentiator for rural and last-mile deployment.

### Revenue Model (Post-Hackathon)

| Stream | Target | Model |
|--------|--------|-------|
| NGO SaaS subscription | Tier 2+ NGOs | ₹2,000-5,000/month per org |
| Government API access | District/state governments | Annual licence |
| CSR compliance platform | Large corporations | ₹50,000-2,00,000/year |
| Donor platform fee | 2.5% of donations processed | Transaction-based |
| Volunteer certification | NSS/NCC partnerships | Per-certificate fee |

### Real-World Adoption Path

1. **Hackathon (now)**: 3 pilot districts, synthetic data, working demo
2. **Month 0-3**: 5 NGO pilot partners (iVolunteer, CRY, WaterAid India)
3. **Month 3-12**: 3 district government partnerships, 500 volunteers
4. **Year 1-2**: State-level adoption in Karnataka, scale to South Asia
5. **Year 2-3**: Sub-Saharan Africa expansion (Kenya, Ghana — UN HDX data ready)
6. **Year 3+**: Global — position as open-source standard for community needs aggregation

---

## Section 8: Role-Based Ownership

### Josna's Build

| Component | Tech Stack | Why |
|-----------|-----------|-----|
| NGO Coordinator Dashboard | Next.js 14 + TypeScript + Tailwind | SSR, fast, component reuse |
| Government Admin Dashboard | Same Next.js app, /gov route | One codebase, role-gated |
| Leaflet/OSM heatmap | react-leaflet + OpenStreetMap tiles | Free, no API key, full-featured |
| GeoJSON choropleth | react-leaflet GeoJSON layer + GADM | No Datasets API needed |
| Live Firestore listeners | Firebase SDK (onSnapshot) | Real-time without Socket.io |
| Urgency scoring display | Custom SVG progress rings | Precise, animated, no library |
| Alert banner system | Custom React component | Dismissible, severity-typed |
| Scheme matcher UI | Table + status badges | Government-readable format |
| Gemini digest viewer | Card component + PDF export | Embedded iframe + download |
| Fallback integrations | gemini.py, storage.py, maps.py, scoring.py, matching.py | Core resilience layer |

**Josna's environment variables needed:**
```
NEXT_PUBLIC_FIREBASE_API_KEY
NEXT_PUBLIC_FIREBASE_PROJECT_ID
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
NEXT_PUBLIC_FIREBASE_APP_ID
NEXT_PUBLIC_API_URL  (FastAPI backend URL on Railway)
GEMINI_API_KEY
SUPABASE_URL
SUPABASE_KEY
RESEND_API_KEY
NOMINATIM_BASE_URL   (no key needed — only URL)
OSRM_BASE_URL        (no key needed — only URL)
```

### Ancilla's Build

| Component | Tech Stack | Why |
|-----------|-----------|-----|
| Volunteer Mobile App | Flutter 3.x | FCM built-in, offline |
| Donor Portal | Next.js 14 (shared codebase) | Same components as NGO dashboard |
| FCM push notifications | Firebase Cloud Messaging | Free, no limits, rich notifications |
| Offline task caching | shared_preferences (Flutter) | Works on 2G, no internet required |
| flutter_map in Flutter | flutter_map + OpenStreetMap | Free, open source, no API key |
| Badge system | Custom Flutter widgets + animations | Gamification, progress rings |
| Campaign cards | Next.js + Tailwind | Consistent with other web dashboards |
| Impact chain visualiser | Custom SVG timeline | Visual trust evidence |
| CSR PDF export | Gemini-generated + Supabase Storage + Resend | Signed URL in email |
| FCM fallback (email) | Resend | Ensures volunteer always notified |

**Ancilla's environment variables needed:**
```
FIREBASE_GOOGLE_SERVICES  (google-services.json + GoogleService-Info.plist)
NEXT_PUBLIC_FIREBASE_*    (same as Josna's set)
NEXT_PUBLIC_API_URL
FCM_SERVER_KEY
# Note: no Flutter Google Maps key needed — flutter_map uses OpenStreetMap (free)
```

### Shared Ownership (Both)

| Component | Owner | Dependency |
|-----------|-------|------------|
| Firestore schema | Both | Must agree before any coding |
| Firebase Auth + role system | Josna (Day 1) | Blocks Ancilla's login |
| FastAPI backend | Split by router | /needs, /surveys → Josna; /volunteers, /campaigns → Ancilla |
| Seed data script | Either | Both need demo data |
| Google ADK agents | Either (post-MVP) | Agents enhance existing flows |
| Fallback files | Both build together | Core reliability layer |

---

## Section 9: Firestore Schema

```
COLLECTIONS AND DOCUMENTS:

/organisations/{org_id}
  name: string
  type: "ngo" | "government" | "csr"
  country: string
  focus_areas: string[]
  verified: boolean
  member_count: number

/users/{user_id}
  email: string
  role: "coordinator" | "volunteer" | "admin" | "donor"
  org_id: string | null
  created_at: timestamp

/needs/{need_id}
  title: string
  description: string
  category: "water_sanitation" | "food_security" | "health" | "shelter" | "education"
             | "protection" | "disaster_relief" | "employment"
  status: "open" | "assigned" | "in_progress" | "resolved" | "verified"
  urgency_score: number  (0-100)
  urgency_level: "critical" | "high" | "moderate" | "low"
  urgency_source: "gemini" | "rule_based_fallback" | "default_fallback"
  urgency_breakdown: { severity, frequency, recency, population, explanation }
  location: GeoPoint
  location_name: string
  admin1: string  (state/province)
  admin2: string  (district)
  admin3: string  (block/ward)
  admin2_code: string  (LGD code)
  country: string
  affected_count: number
  reports_count: number
  source_orgs: string[]  (org_ids of all NGOs who reported this need)
  org_id: string  (primary owning org)
  is_fast_track: boolean
  intake_source: "ocr_auto" | "manual_fallback" | "voice" | "web_form" | "csv"
  created_at: timestamp
  latest_report_at: timestamp
  resolved_at: timestamp | null

/volunteers/{volunteer_id}
  user_id: string
  name: string
  skills: string[]
  domains: string[]
  languages: string[]
  location: GeoPoint
  max_travel_km: number
  transport_mode: "walk" | "cycle" | "motorcycle" | "car" | "transit"
  availability: { [day]: [{start: "HH:MM", end: "HH:MM"}] }
  hours_30d: number
  tasks_completed: number
  avg_rating: number
  completion_rate: number
  badges: string[]  (badge slugs)
  current_level: "newcomer" | "helper" | "responder" | "champion" | "hero" | "legend"
  total_points: number
  verified: boolean
  fcm_token: string
  email: string  (used for Resend email fallback notifications)
  org_id: string | null

/tasks/{task_id}
  need_id: string
  volunteer_id: string
  assigned_by: string  (user_id of coordinator)
  status: "pending" | "accepted" | "in_progress" | "completed" | "cancelled"
  match_score: number
  match_source: "osrm_gemini" | "haversine_fallback" | "radius_fallback" | "accept_all_fallback"
  match_explanation: string
  notification_channel: "fcm" | "resend_email" | "in_app_fallback"
  scheduled_at: timestamp | null
  accepted_at: timestamp | null
  started_at: timestamp | null
  completed_at: timestamp | null
  checkin_location: GeoPoint | null
  checkin_photo_url: string | null  (Supabase Storage signed URL)
  campaign_id: string | null

/outcomes/{task_id}
  resolved: boolean
  rating: number  (1-5)
  people_helped: number
  notes: string
  reporter_id: string
  verified_by: string | null
  recorded_at: timestamp

/campaigns/{campaign_id}
  title: string
  description: string
  goal_amount: number
  raised_amount: number
  currency: string
  category: string
  linked_need_ids: string[]
  org_id: string
  status: "active" | "completed" | "paused"
  donor_count: number
  is_verified: boolean
  created_at: timestamp
  ends_at: timestamp | null

/donations/{donation_id}
  campaign_id: string
  donor_user_id: string | null
  amount: number
  currency: string
  anonymous: boolean
  message: string | null
  created_at: timestamp

/scheme_matches/{match_id}
  need_cluster_id: string
  admin2_code: string
  scheme_name: string
  scheme_url: string
  deadline: timestamp | null
  status: "open" | "closed" | "flagged"
  flagged_by: string | null
  created_at: timestamp

/notifications/{notification_id}
  user_id: string
  task_id: string
  message: string
  read: boolean
  channel: "fcm" | "resend_email" | "in_app_fallback"
  created_at: timestamp

/agent_logs/{log_id}
  agent: string
  action: string
  input: map
  output: map
  fallback_used: boolean
  fallback_tier: string | null
  duration_ms: number
  timestamp: timestamp
```

---

## Section 10: Core Logic — Detailed Implementation

### Urgency Scoring (No ML — Formula + Gemini API)

```python
# services/api/src/agents/ngo_agent.py

import math
import json
from datetime import datetime, timedelta
from google import genai
from fallbacks.scoring import rule_based_score, default_score

client = genai.Client()

async def compute_urgency_score(need: dict) -> dict:

    # COMPONENT 1: Severity (0-35 points)
    # Use Gemini to classify severity from report text
    try:
        severity_response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""
            Rate the humanitarian severity of this field report on a scale of 1-5.
            1 = minor inconvenience, 5 = life-threatening emergency.
            Report: {need['description']}
            Category: {need['category']}
            Affected: {need['affected_count']} people

            Respond with ONLY a JSON object: {{"severity": <1-5>, "reason": "<one sentence>"}}
            """,
            config={{"response_mime_type": "application/json"}}
        )
        severity_data = json.loads(severity_response.text)
        severity_score = severity_data["severity"] * 7  # Maps 1-5 to 7-35

    except Exception:
        # Fallback: rule-based scoring
        return rule_based_score(need.get("description", ""), need.get("affected_count", 0))

    # COMPONENT 2: Frequency (0-25 points)
    nearby_count = need.get("_nearby_reports_count", 1)
    frequency_score = min((nearby_count / 50) * 25, 25)

    # COMPONENT 3: Recency decay (0-20 points)
    latest = need.get("latest_report_at", datetime.now())
    days_old = max(0, (datetime.now() - latest).days)
    recency_score = 20 * math.exp(-0.1 * days_old)

    # COMPONENT 4: Population density (0-20 points)
    pop_percentile = need.get("_population_percentile", 0.5)
    population_score = pop_percentile * 20

    base_score = severity_score + frequency_score + recency_score + population_score

    # RURAL REMOTENESS MULTIPLIER
    remoteness_percentile = need.get("_remoteness_percentile", 0.5)
    if remoteness_percentile < 0.25:
        final_score = min(base_score * 1.3, 100)
        rural_boost_applied = True
    else:
        final_score = base_score
        rural_boost_applied = False

    try:
        explanation_response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""
            Write a 1-2 sentence plain-language explanation of this urgency score for
            an NGO coordinator. Be specific — mention the numbers.

            Need: {need['title']}
            Location: {need['location_name']}
            Score: {round(final_score)}/100
            Severity component: {round(severity_score)}/35 — reason: {severity_data['reason']}
            Frequency: {nearby_count} reports in this area in 30 days
            Population affected: {need['affected_count']} people
            Rural boost applied: {rural_boost_applied}
            """,
        )
        explanation = explanation_response.text.strip()
    except Exception:
        explanation = (f"Score {round(final_score)}/100 based on severity, "
                       f"frequency ({nearby_count} nearby reports), and "
                       f"population ({need.get('affected_count', 0)} affected).")

    level = (
        "critical" if final_score >= 80 else
        "high"     if final_score >= 60 else
        "moderate" if final_score >= 40 else
        "low"
    )

    return {
        "score": round(final_score),
        "level": level,
        "source": "gemini",
        "breakdown": {
            "severity": round(severity_score, 1),
            "frequency": round(frequency_score, 1),
            "recency": round(recency_score, 1),
            "population": round(population_score, 1),
        },
        "rural_boost_applied": rural_boost_applied,
        "explanation": explanation,
    }
```

### Fast-Track System

```python
# services/api/src/routers/needs.py

FAST_TRACK_TRIGGERS = {
    "score_threshold": 80,
    "health_mass_casualty": {"category": "health", "min_affected": 100},
    "disaster_any": {"category": "disaster_relief"},
    "anomaly_detected": True,
}

async def process_new_need(need_data: dict) -> dict:
    score = need_data["urgency_score"]
    category = need_data["category"]
    affected = need_data["affected_count"]
    anomaly = need_data.get("anomaly_detected", False)

    is_fast_track = (
        score >= FAST_TRACK_TRIGGERS["score_threshold"] or
        (category == "health" and affected >= 100) or
        category == "disaster_relief" or
        anomaly
    )

    if is_fast_track:
        matches = await find_volunteer_matches(need_data, limit=1)
        if matches:
            top_volunteer = matches[0]
            task_id = await create_task(need_data["id"], top_volunteer["id"])
            # Use fallback-aware notification (FCM → Resend → in-app)
            notification_result = await notify_volunteer(top_volunteer, {
                **need_data, "id": task_id
            })
            await notify_coordinator(need_data["org_id"], {
                "type": "fast_track_dispatched",
                "message": f"Auto-dispatched {top_volunteer['name']} to "
                           f"{need_data['title']} (score: {score}). "
                           f"Notified via: {notification_result['channel']}"
            })

        need_data["is_fast_track"] = True
        need_data["status"] = "assigned"
    else:
        need_data["is_fast_track"] = False
        need_data["status"] = "open"

    return need_data
```

---

## Section 11: Architecture Diagrams

### System Architecture (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SYNAPSE PLATFORM                                     │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        FRONTEND LAYER                                   │   │
│  │                                                                         │   │
│  │  ┌─────────────────────┐    ┌──────────────┐    ┌────────────────────┐ │   │
│  │  │  NEXT.JS 14 WEB     │    │   FLUTTER    │    │   NEXT.JS 14 WEB   │ │   │
│  │  │                     │    │   MOBILE     │    │                    │ │   │
│  │  │  /dashboard (Josna) │    │  VOLUNTEER   │    │  /gov   (Josna)    │ │   │
│  │  │  /map (Leaflet/OSM) │    │  APP         │    │  /fundraiser       │ │   │
│  │  │  /submit            │    │  (Ancilla)   │    │  (Ancilla)         │ │   │
│  │  │  /needs/[id]        │    │              │    │                    │ │   │
│  │  │  /analytics         │    │  Tasks       │    │  Campaigns         │ │   │
│  │  │  /agents            │    │  Badges      │    │  Impact chain      │ │   │
│  │  └─────────┬───────────┘    └──────┬───────┘    └──────────┬─────────┘ │   │
│  └────────────│───────────────────────│──────────────────────│────────────┘   │
│               │                       │                      │                 │
│               └───────────────────────┴──────────────────────┘                │
│                                       │                                        │
│  ┌────────────────────────────────────▼──────────────────────────────────┐    │
│  │                        FIREBASE LAYER                                 │    │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────┐  │    │
│  │  │  FIRESTORE  │  │ FIREBASE     │  │  FIREBASE   │  │  SUPABASE  │  │    │
│  │  │  Real-time  │  │ AUTH         │  │  APP        │  │  STORAGE   │  │    │
│  │  │  DB + sync  │  │ Email/OTP/   │  │  HOSTING    │  │  Images    │  │    │
│  │  │             │  │ Google login │  │  Next.js    │  │  PDFs      │  │    │
│  │  └──────┬──────┘  └──────────────┘  └─────────────┘  └────────────┘  │    │
│  │         │                                                               │    │
│  │  ┌──────▼──────┐  ┌──────────────────────────────────────────────────┐│    │
│  │  │    CLOUD    │  │           FIREBASE CLOUD MESSAGING               ││    │
│  │  │  FUNCTIONS  │  │  FCM Push → Resend email → In-app fallback       ││    │
│  │  │  Triggers   │  └──────────────────────────────────────────────────┘│    │
│  │  └─────────────┘                                                       │    │
│  └────────────────────────────────────┬───────────────────────────────────┘    │
│                                       │                                        │
│  ┌────────────────────────────────────▼───────────────────────────────────┐    │
│  │              FASTAPI BACKEND (Python — Railway.app)                    │    │
│  │                                                                         │    │
│  │  /api/v1/needs     /api/v1/surveys/ocr    /api/v1/volunteers           │    │
│  │  /api/v1/tasks     /api/v1/campaigns      /api/v1/analytics            │    │
│  │  /api/v1/agents/run  /webhooks/whatsapp                                │    │
│  │                                                                         │    │
│  │  fallbacks/scoring.py   fallbacks/matching.py   fallbacks/notify.py    │    │
│  └────────────────────────────────────┬───────────────────────────────────┘    │
│                                       │                                        │
│  ┌──────────────┬────────────────────┬┴────────────────┬──────────────────┐   │
│  │              │                    │                 │                  │   │
│  │ GOOGLE AI    │ OPEN-SOURCE MAPS   │ LOCAL AI TOOLS  │ GOOGLE ADK       │   │
│  │              │                    │                 │ AGENTS           │   │
│  │ Gemini 2.5   │ Leaflet + OSM      │ pytesseract OCR │                  │   │
│  │ Gemini 2.5   │ Nominatim geocode  │ Whisper STT     │ NGO Agent        │   │
│  │ Flash + Pro  │ OSRM routing       │ LibreTranslate  │ Volunteer Agent  │   │
│  │              │ Overpass places    │                 │ Govt Agent       │   │
│  │              │ flutter_map        │                 │ Donor Agent      │   │
│  └──────────────┴────────────────────┴─────────────────┴──────────────────┘   │
│                                                                                 │
│  [All AI/API layers have rule-based or formula fallbacks — system never fails]  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
FIELD WORKER
    │
    ├─[photo]──→ pytesseract OCR ──→ Gemini: extract fields ──→ /needs/{id}
    │              (fallback: manual form)                              │
    ├─[voice]──→ Whisper STT ──→ LibreTranslate ──→ Gemini ──→ /needs/{id}
    │                                                                   │
    └─[form]───→ Nominatim API ──→ Firestore write ────────────→ /needs/{id}
                  (fallback: manual lat/lng)
                                                                       │
                                          ┌────────────────────────────┤
                                          │ Firestore onSnapshot fires  │
                                          │                             │
                                    ┌─────▼──────┐              ┌──────▼──────┐
                                    │  NGO DASH  │              │  GOVT DASH  │
                                    │  Leaflet   │              │  Leaflet    │
                                    │  heatmap   │              │  choropleth │
                                    └─────┬──────┘              └─────────────┘
                                          │ coordinator clicks dispatch
                                          ▼
                                   URGENCY SCORING
                                   Gemini → rule-based → default(50)
                                          │
                                   VOLUNTEER MATCHING
                                   OSRM → Haversine → radius → accept all
                                          │
                                   /tasks/{id} written
                                          │
                                   NOTIFICATION
                                   FCM → Resend email → In-app
                                          │
                                    ┌─────▼──────┐
                                    │  VOLUNTEER │
                                    │  flutter_  │
                                    │  map app   │
                                    └─────┬──────┘
                                          │ volunteer accepts
                                          ▼
                                   /tasks/{id} status: accepted
                                          │
                                    ┌─────▼──────────────────────┐
                                    │  GPS check-in → in_progress│
                                    │  Outcome form → completed  │
                                    └─────┬──────────────────────┘
                                          │ outcome written
                              ┌───────────┴──────────────┐
                              │                           │
                    ┌─────────▼────┐          ┌──────────▼───────┐
                    │  DONOR PORTAL│          │  NGO DASHBOARD   │
                    │  impact count│          │  urgency score   │
                    │  updates     │          │  recalibrated    │
                    └──────────────┘          └──────────────────┘
```

---

## Section 12: Demo Flow

### Story-Based 90-Second Demo Arc

**The story:** "A community in Ward 6, Mysuru District has been without clean water for 3
days. 300 families. A field worker walks door to door and fills a paper survey. Watch what
happens when she photographs that survey and opens SYNAPSE."

```
SECOND 0-8: THE SCAN
  Field worker holds printed survey form in front of phone camera.
  Uploads via SYNAPSE mobile form.
  pytesseract + Gemini extracts: Ward 6, Mysuru, Water & Sanitation, ~300 families, HIGH.
  Record written to Firestore.
  Say: "8 seconds. That's all it takes."

SECOND 8-13: THE MAP WAKES UP
  Coordinator laptop on screen.
  Leaflet/OpenStreetMap heatmap adds new red circle marker in Ward 6.
  Priority queue: "Acute water shortage — 87/100" slides to position #1.
  Alert banner appears: "Critical need detected — Ward 6, Mysuru."
  Say: "The coordinator didn't press anything. The map updated the moment the photo was taken."

SECOND 13-20: URGENCY EXPLAINED
  Click the need card.
  Urgency breakdown panel: Severity 32/35 | Frequency 23/25 | Recency 18/20 | Population 14/20
  Plain text below: "High — similar reports from 3 NGOs in 14 days, 8,200 residents in area,
  most recent report 2 hours ago."
  Say: "The score explains itself. Every NGO coordinator, district collector, and donor
  can audit this number."

SECOND 20-25: DISPATCH
  Click "Find Volunteers."
  Three cards appear: Amara Osei (91% skill match, 8 min away, available now).
  Click dispatch.
  Say: "The algorithm matched by actual skill and real road travel time — not straight-line distance."

SECOND 25-35: THE PHONE MOMENT
  [Demo phone visible on table or held up]
  FCM notification arrives on phone screen.
  Read aloud: "Water shortage, 8 min away. Matched: nurse skill 91%, available now.
  Urgency: 87/100. Accept?"
  Volunteer taps Accept.
  Coordinator's task board: "Assigned — Amara Osei."
  Say: "Every role just connected — in real time, live, in front of you."

SECOND 35-50: THE FEEDBACK LOOP
  Show a pre-seeded completed task.
  3-question outcome form submitted: resolved ✓, 4.9/5, "280 families received water."
  Urgency score updates: 87 → 39.
  Donor portal: campaign impact counter increments by 280 people.
  Say: "That outcome just retrains our urgency model. No other platform does this.
  After 6 months, SYNAPSE predictions are more accurate than any competitor — because
  we are the only system learning from verified ground-truth outcomes."

SECOND 50-60: THE GOVERNMENT VIEW
  Switch to government dashboard.
  Show: Ward 6 urgency drops on Leaflet GeoJSON choropleth. Coverage gap removed.
  Show: Scheme matcher — "Jal Jeevan Mission: open for applications, 18 days left."
  Say: "The district collector sees this automatically. Every Monday, a Gemini-generated
  briefing lands in their inbox via Resend. This is the scheme alignment that was always
  possible — it just never happened because nobody connected the data."
```

---

## Section 13: Multilingual System

### Supported Languages

| Language | Script | NLP Model | Voice Input | Dashboard UI |
|----------|--------|-----------|-------------|--------------|
| English | Latin | Gemini native | Yes | Full |
| Hindi | Devanagari | LibreTranslate + Gemini | Yes | Full |
| Bengali | Bengali | LibreTranslate + Gemini | Yes | Partial |
| Tamil | Tamil | LibreTranslate + Gemini | Yes | Partial |
| Telugu | Telugu | LibreTranslate + Gemini | Yes | Partial |
| Kannada | Kannada | LibreTranslate + Gemini | Yes | Planned |

### Translation Flow

```
1. Field worker submits in Tamil
2. OpenAI Whisper (local, free) → Tamil transcript
3. LibreTranslate → English
   (Custom humanitarian glossary prevents: "IDP" ≠ "identification",
    "NFI kit" stays as-is, "ration card" = "राशन कार्ड")
4. Gemini NLP extracts structured fields from English text
5. STORED in Firestore as English (normalised)
6. RENDERED to Tamil-speaking coordinator via LibreTranslate
7. Government digest sent in Hindi to state officials
8. Donor impact email sent in donor's preferred language via Resend
```

### Language Selection Flow

```
Dashboard: Language toggle in top navigation bar
  Current: English | Toggle → shows language options
  Selection stored in user Firestore profile
  All dynamic text re-rendered via i18n (next-intl for Next.js)

Flutter app:
  Defaults to device language on first launch
  User can change in Profile → Preferences
  flutter_localizations package handles all UI strings

WhatsApp bot:
  Whisper detects input language automatically
  LibreTranslate responds in same language as user's message
  Language preference stored in Firestore user profile after first interaction
```

---

## Future Scope

1. **USSD / IVR fallback** — Zero-smartphone access. Dial *99*SYNAPSE#, answer 5 IVR
   questions in native language. For truly last-mile communities (2G, keypad phones).

2. **Predictive forecasting** — "Ward 6 water cluster will likely peak in 6 days."
   Historical pattern analysis + seasonal data + disease outbreak trajectories.

3. **NSS/NCC integration** — API hooks to national volunteer portals. 13M students with
   mandatory hour requirements. SYNAPSE provides exactly what they need: verified hour logs.

4. **WhatsApp full conversation bot** — Complete 5-question intake flow without any app.
   State machine handles multi-turn conversations.

5. **UN HDX integration** — Global expansion data layer. Covers 180+ countries.
   Enables expansion to Sub-Saharan Africa, Southeast Asia without rebuilding data layer.

6. **DigiLocker certificate integration** — Volunteer certificates issued directly to
   Aadhaar-linked DigiLocker accounts. Tamper-proof, verifiable, government-recognised.

7. **BigQuery analytics warehouse** — Move heavy aggregation from Firestore to BigQuery.
   Enables complex district trend analysis and embedded dashboards.

8. **Offline-first web PWA** — Service worker caches coordinator dashboard for use in
   areas with intermittent connectivity.
