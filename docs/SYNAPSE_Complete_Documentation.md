# SYNAPSE — Complete System Documentation
## Master Reference · Google Solution Challenge 2026
### Judge-Ready · Production-Level · Fallback-Complete

---

## Table of Contents

1. Project Overview
2. Core Innovations (5)
3. Complete System Workflow
4. Four Dashboards — Detailed
5. Authentication System
6. Tech Stack (Full)
7. ADK Agents
8. Fallback Architecture
9. Firestore Schema
10. API Reference
11. Real Data Sources
12. UI Design System
13. Folder Structure
14. Implementation Plan (10 Days)
15. Antigravity + Stitch Workflow
16. Setup Guide
17. Multilingual System
18. 90-Second Demo Script
19. Business Case
20. Risks + Mitigation

---

## 1. Project Overview

### The Problem

Every day across India and the developing world, resources sit idle while communities suffer
from unmet needs. The failure is not scarcity — it is coordination.

**Evidence:**
- India has 3.3 million registered NGOs — more than any country on earth
- NSS + NCC + NYKS collectively have 13 million active youth volunteers
- India's mandatory CSR spend generates ₹26,000+ crore annually
- Jal Jeevan Mission has budget for FHTC to every rural household — yet thousands of
  villages that have filed water shortage reports still lack coverage

**Root causes of misallocation:**
1. Fragmented data — 5 NGOs surveying the same street, none knowing about each other
2. Manual triage — coordinators making urgency decisions by gut feel or relationship
3. Passive matching — volunteers picking convenient tasks, not urgent ones
4. Invisible coverage gaps — no system shows where help is absent despite documented need
5. No feedback loop — outcomes never feed back into resource allocation decisions

### The Solution

SYNAPSE is a four-role coordination platform that makes all actors visible to each other
and routes resources algorithmically to where they are most needed.

| Role | Problem SYNAPSE Solves |
|------|---------------------|
| NGO Coordinator | Triage 12 open needs in 15 minutes instead of 2 hours |
| Volunteer | Receive the highest-urgency task you are best qualified for |
| Government Admin | See district-level needs data and scheme alignment weekly |
| Donor | Trace every rupee to a GPS-verified on-ground outcome |

---

## 2. Core Innovations (5)

### Innovation 1: Paper → Heatmap in 8 Seconds

A field worker photographs a printed survey form. SYNAPSE uses pytesseract (local OCR)
and Gemini to extract structured fields in 8 seconds — location, category, affected
count, severity indicators. The result is a geolocated, scored need record on a live
heatmap, visible to every coordinator with dashboard access.

No app required for the field worker. No login required. Just a phone camera.

### Innovation 2: Explainable Urgency Score (0–100)

Every need gets a transparent, auditable urgency score:

```
score = (severity × 0.35) + (frequency × 0.25) + (recency_decay × 0.20) + (population × 0.20)
```

With a plain-language explanation: *"High — 47 water reports in this ward in 14 days,
8,200 residents affected, most recent report 2 hours ago."*

The coordinator can see every component. They can override the score if they disagree.
They can audit why a fast-track was triggered. No black box.

### Innovation 3: Need-Driven Volunteer Dispatch

Current platforms: volunteers browse a list and pick tasks.
SYNAPSE: the system pushes the highest-urgency task to the best-matched nearby volunteer
before the coordinator even finishes their coffee.

Match score = `skill_similarity(40%) + proximity(30%) + completion_rate(20%) + domain_boost(10%)`

Proximity uses actual OSRM road travel time — not straight-line distance.
Skill similarity uses Gemini embedding cosine similarity — not keyword matching.

### Innovation 4: Verified Impact Chain

Every donation is traceable through a 5-link chain:

```
Donation → Campaign → Volunteer dispatched → GPS check-in verified → Outcome confirmed
```

Not estimated. Not aggregated. Traceable to a specific GPS coordinate, a named volunteer,
a dated outcome report, and a rating from the community.

This is the feature that unlocks corporate CSR commitments and recurring donor loyalty.

### Innovation 5: Feedback Loop — Self-Improving Predictions

Every completed task with an outcome report feeds back into the urgency model:
- Was the urgency score accurate? (was it actually resolved quickly?)
- Was the volunteer match effective? (what was the outcome rating?)

After 6 months of deployment, SYNAPSE urgency predictions are meaningfully more accurate
than day-one predictions. No competitor has this because no competitor has verified
outcome data to learn from.

---

## 3. Complete System Workflow

```
STEP 1 — FIELD DATA CAPTURE
─────────────────────────────
Channel A: Paper survey photo
  → Field worker photographs survey form
  → pytesseract (local OCR) + Gemini extracts structured fields
  → Time: 8 seconds
  → Fallback: manual entry form if OCR confidence < 0.7

Channel B: WhatsApp voice note
  → OpenAI Whisper (local, free) transcribes (125 languages, auto-detect)
  → Gemini NLP extracts: location, category, affected_count, severity
  → Time: 15 seconds

Channel C: Web form / QR code
  → 3-field anonymous web form
  → No login required

Channel D: CSV import
  → NGOs upload existing spreadsheet data
  → Gemini normalises field names to SYNAPSE schema

STEP 2 — AI PROCESSING
────────────────────────
1. Language detection (langdetect)
2. Translation if needed (LibreTranslate + humanitarian glossary)
3. Named Entity Recognition (Gemini: location, category, affected count)
4. Geocoding (Nominatim API → lat/lng + LGD admin boundary codes)
5. Deduplication (Gemini semantic similarity + 500m geo radius + 30-day window)
6. Urgency scoring (formula → 0-100 score + explanation)
7. Rural remoteness boost (bottom-quartile districts: score × 1.3)
8. Write to Firestore /needs/{id}
9. Firestore onSnapshot → live map update in all open dashboards

STEP 3 — NGO TRIAGE
────────────────────
Normal flow (score < 80):
  → Priority queue sorted by score
  → Coordinator clicks "Find Volunteers"
  → Top 3 matches shown
  → One-tap dispatch
  → FCM push sent

Fast-track flow (score ≥ 80):
  → Auto-dispatch to top match
  → Coordinator notified (not asked)
  → SLA: volunteer notified within 5 minutes

STEP 4 — VOLUNTEER EXECUTION
──────────────────────────────
→ FCM push with match explanation (fallback: Resend email → in-app)
→ Accept in one tap
→ flutter_map/OSRM navigation to location
→ GPS check-in on arrival
→ Execute task
→ 3-question outcome form (90 seconds)
→ Badge criteria evaluated
→ Outcome written to /outcomes

STEP 5 — GOVERNMENT MONITORING
────────────────────────────────
Weekly (Monday 6am cron):
→ Aggregate /needs by district
→ Detect coverage gaps (urgency ≥ 60, zero activity in 14 days)
→ Match need clusters to government scheme database
→ Gemini 2.5 Pro generates 2-page district digest
→ Resend delivers to subscribed officials

On anomaly (3σ spike):
→ Immediate alert to district admin
→ SDRF/NDRF suggestion for disaster_relief category

STEP 6 — DONOR IMPACT TRACKING
────────────────────────────────
→ Donation linked to campaign → campaign linked to need cluster
→ On task completion: impact chain computed
→ Donor sees: donation → task → GPS check-in → outcome
→ Monthly Resend email: exact verified numbers
→ CSR export: Section 80G receipt + utilisation certificate

STEP 7 — FEEDBACK LOOP
────────────────────────
Weekly:
→ Outcome data collected from completed tasks
→ Urgency model weights updated
→ Model accuracy tracked in analytics dashboard
→ Cycle repeats: predictions improve with every deployment week
```

---

## 4. Four Dashboards — Detailed

### Dashboard 1: NGO Coordinator Dashboard

**Owner:** Josna | **Stack:** Next.js 14, TypeScript, Tailwind CSS

**Purpose:** Real-time command centre for NGO coordinators to monitor needs, triage by
urgency, dispatch volunteers, and generate reports.

**Key Screens:**

`/dashboard` — Command Centre
- 4 KPI cards: Active Needs, Volunteers Online, Tasks In Progress, Resolved (30d)
- Live Leaflet/OpenStreetMap heatmap (red = critical, amber = high, teal = moderate)
- Priority queue sorted by urgency score with progress rings
- Alert banners: critical needs and anomaly detections
- Activity feed: live event timeline
- Quick actions: Submit Report, Dispatch Volunteer, Start Campaign, Run AI Agent

`/map` — Full-screen heatmap with category filter pills

`/submit` — OCR photo upload form
- Upload survey photo → pytesseract + Gemini extracts fields → coordinator confirms
- Fallback: photo display + manual form if OCR confidence < 0.7

`/needs/[id]` — Need detail
- Urgency score breakdown: severity + frequency + recency + population
- Plain-language explanation
- Volunteer match results (top 3 with explanation)
- One-tap dispatch
- Source label if fallback scoring was used

`/analytics` — Impact analytics, volunteer performance, model accuracy

`/agents` — AI agent terminal (Orchestrator interface)

**Real-time behaviour:**
- Firestore `onSnapshot` listeners on `/needs` and `/tasks`
- Map updates within 1 second of new need creation
- Priority queue re-sorts automatically on score update

---

### Dashboard 2: Volunteer Mobile App

**Owner:** Ancilla | **Stack:** Flutter 3.x

**Purpose:** Receive task notifications, view match context, navigate to location, check
in via GPS, submit outcomes, track impact and badges.

**Key Screens:**

`TasksScreen` — Home
- flutter_map/OpenStreetMap with nearby task pins coloured by urgency
- Swipeable bottom sheet: task list with accept buttons
- Distance labels: exact if OSRM available, "~Xkm est." if haversine fallback

`TaskDetailScreen`
- Large urgency score circle with colour
- "Why you were matched" card: skill match %, distance, availability
- Task description and action bullets
- Accept / Pass buttons
- Note if match source is fallback

`ActiveTaskScreen`
- 3-step progress indicator: Accept → Check In → Complete
- Embedded flutter_map with OSRM route
- Large "GPS Check In" button
- Contact coordinator button

`ImpactScreen` — Hours chart, tasks donut, people helped counter

`BadgesScreen` — Achievement grid with progress rings, level banner

**Notification handling:**
- FCM push (primary): vibrates, lock screen notification, deep link to task
- Resend email (fallback): sent if FCM token expired or device offline
- In-app (final fallback): notification badge on next app open

**Offline behaviour:**
- Task details cached in shared_preferences local storage
- Outcome form can be completed offline
- Syncs to Firestore when connectivity restored

---

### Dashboard 3: Government / Admin Dashboard

**Owner:** Josna | **Stack:** Next.js 14 (same app, role-gated `/gov` route)

**Purpose:** District-level situational awareness, coverage gap visibility, scheme
alignment, and weekly briefing for district collectors and planning officials.

**Key Screens:**

`/gov` — District Intelligence
- Leaflet choropleth district map: ward polygons coloured by avg urgency (GeoJSON overlay)
- Coverage gap layer: wards with high need + zero NGO activity (hatched overlay)
- Coverage Gaps panel: "High need, zero activity — 8 wards" — most important feature
- Scheme Alignment panel: need category → open scheme → deadline
- Cross-NGO overview table
- District KPI row: Active Needs, Avg Urgency, Coverage Gaps, NGOs Active, Resolution Rate

`/gov/digest` — Weekly digest viewer
- Gemini-generated 2-page briefing
- Download Full PDF
- Sent automatically Monday 6:00 AM via Resend

**Coverage gap detection logic:**
```
For each ward:
  avg_urgency >= 60 AND tasks_14d == 0 → COVERAGE GAP
  → Add to alert queue
  → Surface in digest
  → Red border in choropleth
```

---

### Dashboard 4: Donor / Fundraiser Portal

**Owner:** Ancilla | **Stack:** Next.js 14

**Purpose:** Build donor trust through verified impact evidence. Enable individual and
corporate donations with full traceability.

**Key Screens:**

`/fundraiser` — Campaign grid
- 3-column cards with progress bars, verified impact counts, Donate buttons
- Campaign cards show only GPS-confirmed people_helped — never estimates
- Verified shield badge on verified NGOs

`/fundraiser/[id]` — Campaign detail
- Full funding progress
- 5-step impact chain visualiser: Donation → Campaign → Volunteer → GPS check-in → Outcome
- Donation flow (amount, anonymous option, message)
- "Your donation will help X people" — calculated from historical campaign performance

`/fundraiser/my-impact` — Donor portfolio
- Personal impact timeline: all supported campaigns
- People helped counter (verified only)
- CSR export: Section 80G receipt + utilisation certificate (PDF stored in Supabase Storage)
- Download portfolio PDF

---

## 5. Authentication System

```
Firebase Auth — three login methods:

COORDINATORS:
  Email/password login
  Role: "coordinator"
  Verified: org_id required (admin assigns)
  Access: /dashboard, /map, /submit, /needs/*, /analytics, /agents

VOLUNTEERS:
  Google Sign-In (fastest for mobile)
  Phone OTP (for users without Google account)
  Role: "volunteer"
  Access: Flutter app (all screens)
  Web: /volunteer/* (read-only task board)

FIELD WORKERS (report submission only):
  Phone OTP
  Role: "field_worker"
  Access: /submit only — no dashboard access

GOVERNMENT OFFICIALS:
  Email/password login (issued by admin)
  Role: "admin"
  Access: /gov/*, /gov/digest

DONORS:
  Google Sign-In or email/password
  Role: "donor"
  Anonymous donation option (no login required for one-time donate)
  Access: /fundraiser/*, /fundraiser/my-impact

Firestore security rules enforce role-based access per collection.
```

---

## 6. Tech Stack (Full)

### Frontend

| Technology | Used for | Why |
|---|---|---|
| Next.js 14 (App Router) | NGO + Govt + Donor dashboards | SSR, fast, one codebase for 3 portals |
| Flutter 3.x | Volunteer Mobile App | FCM built-in, offline-capable |
| Tailwind CSS | All web dashboards | Consistent design system, rapid iteration |
| DM Sans | All body text | Professional, highly legible |
| DM Serif Display | Donor portal headings | Emotional resonance for fundraising context |

### Backend

| Technology | Used for | Why |
|---|---|---|
| FastAPI (Python) | OCR, scoring, matching endpoints | Async, native ML/AI library support |
| Railway.app | FastAPI hosting | Simple deploy, free tier, auto-deploy from GitHub |
| Firebase App Hosting | Next.js deployment | Git-connected CI/CD, global CDN, free |

### Database & Storage

| Technology | Used for | Why |
|---|---|---|
| Cloud Firestore | All operational data + real-time listeners | Replaces Socket.io, 50K reads/day free |
| Supabase Storage | Survey images, audio files, generated PDFs | 1GB free, no credit card, signed URLs |

### Authentication

| Technology | Used for |
|---|---|
| Firebase Auth | Email/password, Google Sign-In, Phone OTP — all roles |

### AI / ML

| API / Library | Used for | Cost |
|---|---|---|
| Gemini 2.5 Flash | OCR extraction, urgency scoring, match explanation, donor reports | 15 RPM / 1M tokens/day free |
| Gemini 2.5 Pro | District digest, CSR report generation | Paid, used sparingly |
| pytesseract (local) | Survey OCR (12 Indian scripts) | Free, open source |
| OpenAI Whisper (local) | Voice note transcription (125 languages) | Free, open source |
| LibreTranslate | Field reports + dashboard i18n (50+ languages) | Free, open source |
| Google ADK | Multi-agent orchestration | Open source (Apache 2.0) |

### Maps & Location

| API / Library | Used for | Cost |
|---|---|---|
| Leaflet + OpenStreetMap | NGO heatmap, volunteer task map, govt choropleth | Free, no key |
| Nominatim | Address → lat/lng + LGD admin boundary codes | Free, no key |
| OSRM | Actual road travel time for volunteer matching | Free, no key |
| Overpass API | Nearby hospitals/facilities for volunteer briefing | Free, no key |
| GeoJSON + Leaflet | Custom admin boundary overlays (GADM polygons) | Free, static files |
| flutter_map + latlong2 | Flutter volunteer map | Free, open source |

### Notifications & Messaging

| Technology | Used for |
|---|---|
| Firebase Cloud Messaging (FCM) | Volunteer push notifications |
| WhatsApp Cloud API | Field worker voice/text intake |
| Resend | Weekly digests, donor emails, FCM fallback notifications |

---

## 7. ADK Agents

### What is ADK?

ADK = Agent Development Kit. Traditional code hardcodes every processing step. ADK gives
the code a reasoning layer: you define an agent's goal and tools, and the agent decides
its own steps, retries failures, and routes to fallback paths.

### Agent 1: NGO Agent

**Model:** Gemini 2.5 Flash | **Human-in-loop:** Yes (non-fast-track)

Processes survey inputs → scores urgency → deduplicates → writes to Firestore.

Tools: pytesseract OCR, Whisper STT, LibreTranslate, Nominatim geocoding, Gemini scoring.
Fallbacks: rule-based scoring if Gemini unavailable, manual form if OCR unavailable.

### Agent 2: Volunteer Agent

**Model:** Gemini 2.5 Flash | **Memory:** Off

Matches volunteers to needs → sends notifications → manages task lifecycle → awards badges.

Fallbacks: Haversine distance if OSRM unavailable, Resend email/in-app if FCM fails.

### Agent 3: Government Agent

**Model:** Gemini 2.5 Pro | **Schedule:** Monday 6:00 AM cron (Railway cron job)

Aggregates district data → detects coverage gaps → matches schemes → generates digest
→ sends via Resend to district officials.

### Agent 4: Donor Agent

**Model:** Gemini 2.5 Pro | **Memory:** On

Computes verified impact chains → generates personalised narratives → produces CSR exports
→ stores PDFs in Supabase Storage → emails signed URLs via Resend.

### Agent 5: Orchestrator

**Model:** Gemini 2.5 Flash | **Max iterations:** 5

Routes all incoming events to the correct agent. Single entry point. Logs every routing
decision in `/agent_logs`.

---

## 8. Fallback Architecture

> **Design principle:** Every AI step has a rule-based fallback. Every API call has a
> degraded-mode alternative. The system ALWAYS produces a result.

### Why Fallback is Not Optional

SYNAPSE is built for deployment where:
- API quotas run out during crisis surge (when demand is highest)
- Network connectivity is unreliable (rural and peri-urban deployments)
- Demo environments hit free-tier limits at the worst moment

A system that fails silently during a flood response is not a humanitarian tool —
it is a liability. SYNAPSE is designed to degrade gracefully across every component,
always returning a labelled result with a clear `source` field.

### Fallback Layer 1: Urgency Scoring

```
PRIMARY:   Gemini 2.5 Flash NLP → weighted formula → 0-100
              ↓ (quota exhausted or API unreachable)
SECONDARY: Rule-based keyword matching
           Keywords:
             critical (85): death, dying, emergency, flood, fire, cholera, famine
             high (65):     water, food, hunger, medicine, sick, shortage
             moderate (45): shelter, school, sanitation, hygiene, displacement
             low (20):      support, training, awareness
           Boost: +15 if affected > 500, +10 if > 100
              ↓ (no keywords match)
TERTIARY:  Default score = 50 (moderate), requires_review: true

Source label stored: "gemini" | "rule_based_fallback" | "default_fallback"
```

**File:** `services/api/src/fallbacks/scoring.py`

### Fallback Layer 2: Volunteer Matching

```
PRIMARY:   OSRM travel time + Gemini embedding cosine similarity
              ↓ (OSRM unavailable or timeout)
SECONDARY: Haversine straight-line distance formula
           Filter: ≤ 15km, sorted by distance
           Label: match_source: "haversine_fallback"
           UI: "~Xkm (straight-line estimate)"
              ↓ (volunteer location data missing)
TERTIARY:  Radius filter only — all volunteers within 15km
           Label: match_source: "radius_fallback"
              ↓ (no volunteers pass filter)
QUATERNARY: Return all available volunteers
           Label: match_source: "accept_all_fallback"
```

**File:** `services/api/src/fallbacks/matching.py`

### Fallback Layer 3: OCR / Survey Intake

```
PRIMARY:   pytesseract (local) + Gemini → automatic extraction
              ↓ (pytesseract confidence < 0.7 or failure)
SECONDARY: Return partial extraction + manual form flag
           UI: original photo on left, editable form on right
           Source: "manual_fallback"
           Stored in Firestore for audit
```

**File:** `services/api/src/fallbacks/ocr.py`

### Fallback Layer 4: Notifications

```
PRIMARY:   FCM push notification
              ↓ (token expired or device offline)
SECONDARY: Email via Resend
              ↓ (email not available)
TERTIARY:  In-app Firestore flag (shown on next app load)

Channel stored in task record: notification_channel field
```

**File:** `services/api/src/fallbacks/notify.py`

### Fallback Layer 5: Translation

```
PRIMARY:   LibreTranslate (free, open source) → English
              ↓ (LibreTranslate endpoint unavailable)
SECONDARY: langdetect passthrough — raw text stored, flagged for coordinator review
```

### Fallback Layer 6: Geocoding

```
PRIMARY:   Nominatim API → lat/lng + admin boundary code
              ↓ (Nominatim unavailable or no result)
SECONDARY: Manual lat/lng entry by coordinator
              ↓ (location completely unknown)
TERTIARY:  Admin code extracted from text (best-guess district matching)
```

### Fallback Summary Table

| Component | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|-----------|---------|------------|------------|------------|
| Urgency scoring | Gemini 2.5 Flash | Rule-based keywords | Default (50) | — |
| Volunteer matching | OSRM + Gemini | Haversine formula | Radius filter | Accept all |
| Survey OCR | pytesseract + Gemini | Manual form | — | — |
| Notifications | FCM push | Resend email | In-app flag | — |
| Translation | LibreTranslate | langdetect passthrough | Raw text stored | — |
| Geocoding | Nominatim | Manual lat/lng entry | Admin code from text | — |

### Fallback Visibility in UI

Every dashboard shows fallback state to coordinators:
- Amber chip: "Rule-based scoring" on urgency scores computed without Gemini
- Muted label: "~Xkm (straight-line est.)" on haversine-matched volunteer cards
- Banner: "AI scoring unavailable — estimates active" in topbar when Gemini is down
- Activity feed entry: "Email fallback used for volunteer [name] (FCM offline)"

Fallbacks are informational. They never block coordinator actions.

---

## 9. Firestore Schema

```
/organisations/{org_id}
  name, type, country, focus_areas, verified, member_count

/users/{user_id}
  email, role, org_id, created_at

/needs/{need_id}
  title, description, category, status
  urgency_score (0-100)
  urgency_level ("critical"|"high"|"moderate"|"low")
  urgency_source ("gemini"|"rule_based_fallback"|"default_fallback")
  urgency_breakdown {severity, frequency, recency, population, explanation}
  location (GeoPoint), location_name
  admin1, admin2, admin3, admin2_code
  affected_count, reports_count, source_orgs[]
  is_fast_track, intake_source
  created_at, latest_report_at, resolved_at

/volunteers/{volunteer_id}
  user_id, name, skills[], domains[], languages[]
  location (GeoPoint), max_travel_km, transport_mode
  availability {day: [{start, end}]}
  hours_30d, tasks_completed, avg_rating, completion_rate
  badges[], current_level, total_points
  fcm_token, email, verified, org_id

/tasks/{task_id}
  need_id, volunteer_id, assigned_by, status
  match_score, match_source, match_explanation
  notification_channel
  scheduled_at, accepted_at, started_at, completed_at
  checkin_location (GeoPoint), checkin_photo_url, campaign_id

/outcomes/{task_id}
  resolved, rating (1-5), people_helped, notes
  reporter_id, verified_by, recorded_at

/campaigns/{campaign_id}
  title, description, goal_amount, raised_amount, currency
  category, linked_need_ids[], org_id, status
  donor_count, is_verified, created_at, ends_at

/donations/{donation_id}
  campaign_id, donor_user_id, amount, currency
  anonymous, message, created_at

/impact_chains/{donation_id}
  donation_id, campaign_id, need_cluster_id
  tasks[] [{task_id, volunteer_name, checkin_verified, outcome}]
  total_people_helped, computed_at

/scheme_matches/{match_id}
  need_cluster_id, admin2_code, scheme_name, scheme_url
  deadline, status, flagged_by, created_at

/notifications/{notification_id}
  user_id, task_id, message, read
  channel ("fcm"|"resend_email"|"in_app_fallback"), created_at

/agent_logs/{log_id}
  agent, action, input, output
  fallback_used, fallback_tier, duration_ms, timestamp
```

---

## 10. API Reference

### FastAPI Endpoints

```
GET    /health
       → {status: "ok", project: "SYNAPSE"}

GET    /health/deep
       → {status: "ok"|"degraded", integrations: {gemini, storage, nominatim, osrm, overpass}}

POST   /api/v1/needs
       Body: {title, description, category, location, affected_count, org_id}
       → {need_id, urgency_score, urgency_source, is_fast_track}

GET    /api/v1/needs/{need_id}
       → Full need record with urgency breakdown

POST   /api/v1/surveys/ocr
       Body: multipart/form-data image file
       → {extracted_fields, confidence, source: "ocr_auto"|"manual_fallback"}

POST   /api/v1/surveys/voice
       Body: multipart/form-data audio file
       → {transcript, extracted_fields}

GET    /api/v1/volunteers/match?need_id={id}&limit=3
       → [{volunteer_id, name, match_score, match_source, explanation}]

POST   /api/v1/tasks
       Body: {need_id, volunteer_id, assigned_by}
       → {task_id, notification_channel}

PATCH  /api/v1/tasks/{task_id}
       Body: {status, checkin_location?, outcome?}
       → Updated task record

POST   /api/v1/campaigns
       Body: {title, description, goal_amount, linked_need_ids, org_id}
       → {campaign_id}

GET    /api/v1/analytics/district?admin2_code={code}
       → {avg_urgency, coverage_gaps[], active_needs_count, resolution_rate}

POST   /api/v1/agents/run
       Body: {event_type, payload}
       → {result, agent_used, fallback_used, duration_ms}

POST   /webhooks/whatsapp
       Body: WhatsApp Cloud API webhook payload
       → {status: "processed"}
```

---

## 11. Real Data Sources

### Government APIs (India)

| Dataset | URL | Used for |
|---------|-----|----------|
| NDAP | ndap.nic.in/api/ | District health/water/education baseline |
| LGD Directory | lgdirectory.gov.in/ | Admin boundary codes |
| Census 2011 | censusindia.gov.in/ | Village population data |
| JJM Dashboard | ejalshakti.gov.in/jjmreport/ | FHTC coverage by district |
| MGNREGA MIS | nregarep2.nic.in/netnrega/ | Employment demand/supply |
| MyScheme Portal | myscheme.gov.in/api | 750+ active government schemes |
| SECC 2011 | secc.gov.in/ | BPL household data |

### Geospatial Data

| Dataset | URL | Used for |
|---------|-----|----------|
| GADM Boundaries | gadm.org/download_country.html | Admin boundary GeoJSON (all levels) |
| NASA SEDAC | sedac.ciesin.columbia.edu/ | Population density grids |
| OpenStreetMap / Overpass | overpass-api.de/api/interpreter | Infrastructure points |
| Nominatim | nominatim.openstreetmap.org | Address → lat/lng geocoding |

### Open Humanitarian Data

| Dataset | URL | Coverage |
|---------|-----|----------|
| UN HDX / OCHA | data.humdata.org/api/3/ | 180+ countries, crisis data |
| WHO GHO | ghoapi.azureedge.net/api/ | Global health indicators |
| World Bank | api.worldbank.org/v2/ | Country poverty/development data |
| ReliefWeb | api.reliefweb.int/v1/ | Active global crisis reports |

### Hackathon Demo Data Strategy

| Component | Demo | Production |
|---|---|---|
| Needs | 12 seeded needs, 3 districts | Live NGO submissions |
| Volunteers | 8 seed profiles | Real registrations |
| Population density | Hardcoded per demo district | NASA SEDAC daily cache |
| Admin boundaries | GADM GeoJSON pre-loaded as static file | Same + LGD codes |
| Government schemes | 15 static Firestore documents | MyScheme API live |

---

## 12. UI Design System

### Colour Palette

| Role | Hex | Usage |
|------|-----|-------|
| Navy | #0D2B4E | NGO sidebar, primary buttons, headings |
| Teal | #0F6E56 | Success, volunteer, positive states |
| Purple | #534AB7 | Government/admin role |
| Amber | #D97706 | Donor portal, warnings, fallback indicators |
| Red | #DC2626 | Critical urgency, error alerts |
| Page bg | #F8F9FC | Dashboard background |
| Card bg | #FFFFFF | All card backgrounds |

### Urgency Colour System (Universal)

| Score | Level | Colour |
|-------|-------|--------|
| ≥ 80 | Critical | Red #DC2626 |
| 60–79 | High | Amber #D97706 |
| 40–59 | Moderate | Teal #0F6E56 |
| < 40 | Low | Gray #6B7280 |

### Fallback State Colours

Fallback is functional, not broken. Use amber — not red.

| State | Background | Text |
|-------|------------|------|
| Rule-based scoring active | #FEF3C7 | #92400E |
| Haversine matching active | #FEF3C7 | #92400E |
| Email fallback used | #FEF3C7 | #92400E |

### Typography

| Element | Font | Weight | Size |
|---------|------|--------|------|
| Headings | DM Sans | 500 | 22px |
| Body | DM Sans | 400 | 13px |
| Stats | DM Sans | 600 | 28px (tabular-nums) |
| Display (donor) | DM Serif Display | 400 | 24–40px |

### Card System

```css
background: #FFFFFF;
border: 0.5px solid #E5E7EB;
border-radius: 12px;
box-shadow: 0 1px 3px rgba(0,0,0,0.04);
padding: 20px 24px;
```

### Status Indicators

| Status | Colour |
|--------|--------|
| Open | Blue #2563EB |
| Assigned | Amber #D97706 |
| In Progress | Purple #7C3AED |
| Resolved | Teal #0F6E56 |
| Verified | Deep Teal #085041 |

---

## 13. Folder Structure

```
synapse/
├── apps/
│   ├── web/                      # Next.js 14 — all web dashboards
│   │   └── src/
│   │       ├── app/
│   │       │   ├── (auth)/       # login, register, role-select
│   │       │   ├── dashboard/    # NGO coordinator
│   │       │   ├── map/          # full-screen heatmap
│   │       │   ├── submit/       # OCR + manual form
│   │       │   ├── needs/[id]/   # need detail
│   │       │   ├── analytics/    # impact metrics
│   │       │   ├── agents/       # agent terminal
│   │       │   ├── gov/          # government dashboard
│   │       │   └── fundraiser/   # donor portal
│   │       ├── components/
│   │       │   ├── ui/           # shared primitives
│   │       │   ├── dashboard/    # coordinator components
│   │       │   ├── map/          # Leaflet map components
│   │       │   │   ├── MapComponent.tsx       # shell (SSR-safe)
│   │       │   │   ├── LeafletMapInner.tsx    # client-only Leaflet
│   │       │   │   └── ChoroplethMap.tsx      # GeoJSON choropleth
│   │       │   ├── fundraiser/   # donor components
│   │       │   └── gov/          # govt components
│   │       └── lib/
│   │           ├── api.ts
│   │           ├── firebase.ts
│   │           └── utils.ts
│   │
│   └── mobile/                   # Flutter volunteer app
│       ├── lib/
│       │   ├── screens/
│       │   │   ├── tasks/
│       │   │   ├── task_detail/
│       │   │   ├── active_task/
│       │   │   ├── impact/
│       │   │   └── badges/
│       │   ├── services/
│       │   │   ├── firebase_service.dart
│       │   │   ├── fcm_service.dart
│       │   │   └── maps_service.dart
│       │   └── models/
│       └── pubspec.yaml
│
├── services/
│   └── api/                      # FastAPI backend
│       └── src/
│           ├── main.py
│           ├── routers/
│           │   ├── needs.py          # ← Josna
│           │   ├── surveys.py        # ← Josna
│           │   ├── analytics.py      # ← Josna
│           │   ├── volunteers.py     # ← Ancilla
│           │   ├── tasks.py          # ← Ancilla
│           │   └── campaigns.py      # ← Ancilla
│           ├── agents/
│           │   ├── orchestrator.py
│           │   ├── ngo_agent.py
│           │   ├── volunteer_agent.py
│           │   ├── govt_agent.py
│           │   └── donor_agent.py
│           ├── fallbacks/            # ← RESILIENCE LAYER (both build)
│           │   ├── scoring.py        # rule-based urgency
│           │   ├── matching.py       # haversine distance
│           │   ├── notify.py         # Resend email + in-app
│           │   └── ocr.py            # manual entry flag
│           └── integrations/
│               ├── gemini.py         # ← Josna
│               ├── maps.py           # ← Josna (Nominatim + OSRM + Overpass)
│               ├── firebase.py       # both
│               ├── storage.py        # ← Josna (Supabase Storage, renamed from cloudinary.py)
│               └── fcm.py            # ← Ancilla
│
├── firebase/
│   ├── firestore.rules
│   ├── firestore.indexes.json
│   └── functions/
│       └── badge_triggers.js
│
├── public/
│   └── geojson/
│       └── india_districts.geojson   # GADM district boundaries (static file)
│
├── scripts/
│   ├── seed.py
│   └── load_gadm.py                  # Downloads GADM → outputs GeoJSON
│
├── agents.md
├── README.md
├── .env.example
└── docker-compose.yml
```

---

## 14. Implementation Plan (10 Days)

### Day 1 — Foundation (Josna solo)

**Josna:**
- [ ] Create GitHub repo, push folder structure
- [ ] Set up Firebase project, enable Firestore + Auth + FCM + App Hosting
- [ ] Set up Supabase project, create three storage buckets
- [ ] Create all foundation files:
  - `integrations/gemini.py` (with fallback trigger)
  - `integrations/firebase.py`
  - `integrations/storage.py` (Supabase Storage)
  - `integrations/maps.py` (Nominatim + OSRM + Overpass + haversine)
  - `fallbacks/scoring.py`
  - `fallbacks/matching.py`
  - `fallbacks/notify.py`
  - `main.py`
- [ ] Push to `josna-dev` branch
- [ ] Share Firebase project ID + google-services.json with Ancilla

**Ancilla:**
- [ ] Clone repo, create `ancilla-dev` branch
- [ ] Install Flutter, run `flutter doctor`
- [ ] Install Firebase CLI
- [ ] Set up `apps/mobile/` Flutter project skeleton with flutter_map
- [ ] Place `google-services.json` in `apps/mobile/android/app/`

---

### Day 2 — Core APIs

**Josna:**
- [ ] `routers/needs.py` — POST /needs with urgency scoring + fallback chain
- [ ] `routers/surveys.py` — POST /surveys/ocr with pytesseract + manual fallback
- [ ] `agents/ngo_agent.py` — process_survey, score_and_deduplicate
- [ ] Test: submit a photo → get need with urgency score in Firestore

**Ancilla:**
- [ ] `integrations/fcm.py` — send FCM with Resend email fallback
- [ ] `routers/volunteers.py` — GET /volunteers, PATCH volunteer profile
- [ ] `routers/tasks.py` — GET/POST/PATCH task lifecycle
- [ ] `agents/volunteer_agent.py` — find_matches with haversine fallback

---

### Day 3 — NGO Dashboard (Josna)

- [ ] Firebase Auth setup (email + Google + OTP)
- [ ] `/dashboard` — KPI cards + activity feed
- [ ] `/map` — Leaflet/OpenStreetMap heatmap with Firestore `onSnapshot`
- [ ] Priority queue component with urgency progress rings
- [ ] Alert banners (critical + anomaly)
- [ ] Fallback state indicator (amber banner when rule-based active)

---

### Day 4 — Volunteer App (Ancilla)

- [ ] `TasksScreen` — flutter_map + bottom sheet task list
- [ ] `TaskDetailScreen` — match explanation + accept/pass
- [ ] `ActiveTaskScreen` — GPS check-in + outcome form
- [ ] FCM push handler — deep link to task detail
- [ ] shared_preferences offline caching for task details

---

### Day 5 — NGO Dashboard cont. (Josna)

- [ ] `/submit` — OCR upload form + manual fallback display
- [ ] `/needs/[id]` — urgency breakdown + volunteer match + dispatch
- [ ] Volunteer dispatch flow (find matches → show cards → confirm)
- [ ] One-tap dispatch → FCM fires → Firestore task written

---

### Day 6 — Government Dashboard (Josna)

- [ ] `/gov` — Leaflet choropleth map with GeoJSON GADM boundary overlay
- [ ] Coverage gap panel (high urgency + zero activity detection)
- [ ] Scheme matcher table
- [ ] `agents/govt_agent.py` — coverage_gap_detection, scheme_matching
- [ ] `/gov/digest` — digest viewer + PDF download
- [ ] Run `python scripts/load_gadm.py` to generate `public/geojson/india_districts.geojson`

---

### Day 7 — Donor Portal (Ancilla)

- [ ] `/fundraiser` — campaign cards with live progress bars
- [ ] `/fundraiser/[id]` — impact chain visualiser + donation flow
- [ ] `agents/donor_agent.py` — impact chain computation
- [ ] `routers/campaigns.py` — CRUD + impact counter
- [ ] CSR PDF export (Gemini 2.5 Pro + Supabase Storage signed URL + Resend)

---

### Day 8 — Badges + Impact (Ancilla)

- [ ] `BadgesScreen` — achievement grid with progress rings
- [ ] `ImpactScreen` — hours chart, tasks donut, people helped
- [ ] Badge evaluation logic in `volunteer_agent.py`
- [ ] `/fundraiser/my-impact` — donor portfolio + certificates

---

### Day 9 — Orchestrator + Integration Testing

**Both:**
- [ ] `agents/orchestrator.py` — routing map for all event types
- [ ] End-to-end test: photo upload → need → dispatch → FCM → check-in → outcome
- [ ] Test all fallback paths: disable Gemini → verify rule-based activates
- [ ] Test haversine fallback: mock OSRM failure (disconnect network)
- [ ] Test email fallback: use expired FCM token
- [ ] Seed demo data: `python seed.py --district mysuru --needs 12 --volunteers 8`

---

### Day 10 — Demo Prep + Polish

**Both:**
- [ ] Run full 90-second demo arc from memory (3 practice runs)
- [ ] Pre-seed: fast-track need (score 87), completed task with outcome
- [ ] Ensure demo phone has FCM token current and notification shows on lock screen
- [ ] All fallback source labels visible in UI
- [ ] Agent logs showing at least one complete end-to-end run
- [ ] README.md updated with final setup steps

---

## 15. Antigravity + Stitch Workflow

### What Antigravity Does

Antigravity is Google's AI-powered development environment. It connects to your codebase
via MCP (Model Context Protocol) and can write, edit, and run code using an agent interface.
For SYNAPSE, it replaces manually writing boilerplate — you describe what you want, it
generates code into your actual files.

### What Stitch Does

Stitch generates professional UI mockups from natural language prompts. You describe a
dashboard screen and it generates a pixel-ready visual. Use it to generate the UI for all
4 SYNAPSE dashboards before writing any React or Flutter code.

### Setup (One-Time)

**Step 1: Get Stitch API key**
1. Go to stitch.withgoogle.com
2. Profile picture → Stitch Settings → API Keys → Create Key
3. Copy immediately (shown once only)

**Step 2: Connect Stitch to Antigravity**
1. Open Antigravity
2. Create workspace "synapse", point to your synapse/ folder
3. Agent chat → 3 dots (...) → MCP Servers → search "Stitch" → Install
4. Paste Stitch API key → Save
5. Test: type "List my Stitch projects" in agent chat

**Step 3: Load project context**
1. Drag `agents.md` into Antigravity workspace
2. Drag `README.md` into workspace
3. In agent chat: "Read agents.md and README.md and understand the full SYNAPSE architecture"

### Workflow for Each Feature

```
1. Generate UI in Stitch:
   Paste the prompt from stitch_prompts.md
   Screenshot the result
   Use ONE follow-up refinement if needed

2. Code the component in Antigravity:
   "Generate a React component matching this Stitch mockup.
    It should use Tailwind CSS and react-leaflet for the map.
    Connect to Firestore /needs collection.
    It must show urgency score as a coloured progress ring.
    If score source is 'rule_based_fallback', show an amber chip."

3. Test and commit:
   git add . && git commit -m "feat: NGO priority queue component"
   git push origin josna-dev
```

### Team Split in Antigravity

```
Josna works in:        Ancilla works in:
  apps/web/              apps/mobile/
  services/api/routers/  donor/
    needs.py               services/api/routers/
    surveys.py               volunteers.py
    analytics.py             tasks.py
  agents/ngo_agent.py       campaigns.py
  agents/govt_agent.py   agents/volunteer_agent.py
  integrations/gemini.py  agents/donor_agent.py
  integrations/maps.py   integrations/fcm.py
  integrations/storage.py
```

**Golden rule: never touch the other person's files without messaging first.**

---

## 16. Setup Guide

### Prerequisites

```bash
node --version       # 20+
python --version     # 3.12+
flutter --version    # 3.x
firebase --version   # latest
# Note: gcloud CLI no longer needed — backend hosted on Railway
```

### System Dependencies (for OCR)

```bash
# Install Tesseract OCR engine + all Indian language packs
sudo apt-get install tesseract-ocr tesseract-ocr-all

# Verify installation
tesseract --version
tesseract --list-langs | grep -E "kan|hin|tam|tel|ben"
```

### Step-by-Step Setup

```bash
# 1. Clone repo
git clone https://github.com/your-team/synapse.git
cd synapse

# 2. Environment variables
cp .env.example services/api/.env
# Fill in: GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY, RESEND_API_KEY

# 3. Firebase
firebase login
firebase use synapse-platform
firebase deploy --only firestore:rules,firestore:indexes

# 4. Web dependencies
cd apps/web && npm install
# Includes leaflet react-leaflet @types/leaflet

# 5. Python backend
cd services/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Pre-download Whisper model weights (~150MB)
python -c "import whisper; whisper.load_model('base')"

# 7. Generate GADM GeoJSON boundary file
cd scripts
python load_gadm.py --country IN --level 3
# Output: ../public/geojson/india_districts.geojson

# 8. Seed demo data
python seed.py --district mysuru --needs 12 --volunteers 8 --campaigns 3

# 9. Run all three servers
# Terminal 1:
cd apps/web && npm run dev        # → localhost:3000

# Terminal 2:
cd services/api && uvicorn src.main:app --reload --port 8080  # → localhost:8080

# Terminal 3:
cd apps/mobile && flutter run     # → Android/iOS device or emulator
```

### Environment Variables Reference

```env
# services/api/.env
GEMINI_API_KEY=
FIREBASE_PROJECT_ID=
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
SUPABASE_URL=
SUPABASE_KEY=
NOMINATIM_BASE_URL=https://nominatim.openstreetmap.org
OSRM_BASE_URL=http://router.project-osrm.org
OVERPASS_BASE_URL=https://overpass-api.de/api
RESEND_API_KEY=
RESEND_FROM_EMAIL=noreply@synapse.example.com
LIBRETRANSLATE_URL=https://libretranslate.com
WHISPER_MODEL=base
ENVIRONMENT=development
PORT=8080
NEXT_PUBLIC_API_URL=http://localhost:8080

# apps/web/.env.local
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_APP_ID=
NEXT_PUBLIC_API_URL=http://localhost:8080
# No map API key needed — Leaflet uses OpenStreetMap tiles (free, no key)
```

---

## 17. Multilingual System

### Supported Languages

| Language | Script | Voice Input | Dashboard |
|----------|--------|-------------|-----------|
| English | Latin | Yes | Full |
| Hindi | Devanagari | Yes | Full |
| Bengali | Bengali | Yes | Partial |
| Tamil | Tamil | Yes | Partial |
| Telugu | Telugu | Yes | Partial |
| Kannada | Kannada | Yes | Planned |

### Translation Pipeline

```
1. Field worker submits in Tamil voice note
2. OpenAI Whisper (local) → Tamil transcript
3. LibreTranslate → English
   (Humanitarian glossary: IDP ≠ identification, NFI kit stays as-is)
4. Gemini NLP → extracts structured fields from English
5. Stored in Firestore as English (normalised)
6. Rendered to Tamil coordinator via LibreTranslate
7. Government digest → Hindi for state officials, English for district collectors
8. Donor email → donor's preferred language
```

### i18n Implementation

```
Web: next-intl (Next.js)
  Language stored in user Firestore profile
  Toggle in topbar navigation

Flutter: flutter_localizations package
  Defaults to device language on first launch
  User changes in Profile → Preferences

WhatsApp bot:
  Auto-detects input language via Whisper
  Responds in same language via LibreTranslate
```

---

## 18. 90-Second Demo Script

**Setup before demo:**
- Seed: 12 active needs including one at urgency 87 in Ward 6 Mysuru
- Pre-completed task with outcome (for feedback loop demo)
- Demo phone with SYNAPSE app installed, FCM token current
- Coordinator dashboard open on laptop (Leaflet map loaded)
- Government dashboard tab ready

---

```
SECOND 0-8: THE SCAN
──────────────────────
[Hold phone up, photograph printed survey form]
"A field worker just photographed a paper survey. Watch."
[Upload → 8 seconds → red pin appears on coordinator's Leaflet map]
"8 seconds. That survey is now on a live heatmap for every coordinator in this district."

SECOND 8-15: THE MAP WAKES UP
───────────────────────────────
[Point to coordinator laptop]
"The coordinator didn't press anything. The Firestore listener fired the moment
that photo was processed. Priority queue — top result: 87 out of 100."
[Click the need card]

SECOND 15-22: URGENCY EXPLAINED
──────────────────────────────────
[Urgency breakdown visible]
"Severity: 32 out of 35. Frequency: 23 reports in this ward in 14 days.
Recency: 18 — reported 2 hours ago. This score is not a black box.
Every coordinator can audit every number. And they can override it."

SECOND 22-28: DISPATCH
────────────────────────
[Click "Find Volunteers"]
"Top match: 91% skill similarity, 8 minutes away, available now.
That's not straight-line distance — that's actual OSRM road travel time.
That's not keyword matching — that's Gemini embedding cosine similarity."
[Click dispatch]

SECOND 28-38: THE PHONE MOMENT
─────────────────────────────────
[Hold demo phone up visibly]
[FCM notification arrives — read it aloud]
"Water shortage, Ward 6. 8 minutes away. Nurse skill: 91%. Urgency: 87.
Accept?"
[Tap accept — coordinator dashboard shows "Assigned — Amara Osei"]
"Every role in this system just connected — in real time, live, in front of you."

SECOND 38-52: THE FEEDBACK LOOP
──────────────────────────────────
[Show pre-seeded completed task]
"Here's a completed task. Outcome: 280 families received water. Rating 4.9.
Watch the urgency score."
[Score drops from 87 to 39]
"That outcome data just recalibrated the urgency model.
Not just for this need — for every similar need in this district.
No other platform does this. No competitor has verified outcome data to learn from.
After 6 months of deployment, SYNAPSE predictions are meaningfully more accurate
than on day one."

SECOND 52-60: GOVERNMENT VIEW
───────────────────────────────
[Switch to government dashboard tab]
"Ward 6 — urgency drops on the Leaflet choropleth. Coverage gap removed.
And look here: Jal Jeevan Mission, open for applications, 18 days left.
The scheme was always there. The district collector just never knew
which community needed it most — until now."
[Pause]
"This is the coordination that was always possible. SYNAPSE is what makes it happen."
```

---

## 19. Business Case

### Market Size

- 3.3 million registered NGOs in India
- ₹26,000+ crore mandatory CSR spend annually
- 13 million active youth volunteers (NSS + NCC + NYKS)
- 700+ districts requiring coordination infrastructure

### Why SYNAPSE Wins

1. **Addresses the actual problem**: Resource misallocation — not scarcity. This
   distinction is correct, evidence-backed, and non-obvious.

2. **Uses Google's core evaluation criteria**: Gemini (scoring + matching + reports),
   ADK (multi-agent), Firebase (real-time), open-source stack (maintainable, scalable).

3. **Fallback architecture = production judgment**: A demo that degrades gracefully under
   quota limits shows engineering maturity that raw feature lists do not.

4. **Verified impact chain**: No competing platform has GPS-confirmed, outcome-linked
   impact data. This is the trust layer that unlocks corporate CSR.

5. **Feedback loop**: Self-improving predictions after deployment is a genuine
   competitive moat. No competitor can replicate this without verified outcome data.

### Revenue Model

| Stream | Target | Model |
|--------|--------|-------|
| NGO SaaS | Tier 2+ NGOs | ₹2,000–5,000/month per org |
| Government API | District/state | Annual licence |
| CSR platform | Corporates | ₹50,000–2,00,000/year |
| Donor platform fee | All donations | 2.5% transaction |
| Volunteer certification | NSS/NCC | Per-certificate |

### Adoption Path

```
Now:        Hackathon demo — 3 districts, synthetic data
Month 0-3:  5 NGO pilots (iVolunteer, CRY, WaterAid India)
Month 3-12: 3 district government partnerships, 500 volunteers
Year 1-2:   State-level adoption in Karnataka
Year 2-3:   Sub-Saharan Africa (Kenya, Ghana — UN HDX data ready)
Year 3+:    Global — open-source standard for community needs aggregation
```

---

## 20. Risks + Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Gemini quota exhausted during demo | Medium | Rule-based fallback active; amber indicator shown; never fails silently |
| OSRM routing unavailable | Medium | Haversine fallback active; straight-line distance shown with "est." label |
| FCM push fails during demo | Low | Resend email fallback preloaded; test email address configured on demo device |
| OCR misreads field survey | Low | Manual fallback form shown alongside photo; coordinator can correct |
| Firestore read limits hit | Low | Demo uses 12 seeded needs; well within 50K/day free tier |
| Firebase Auth OTP not delivered | Low | Google Sign-In as backup; test account pre-authenticated |
| Demo phone not receiving FCM | Low | App force-killed and restarted before demo; token refreshed |
| Coordinator accidentally merges wrong PR | Medium | Never work directly on main; all changes via PR; one reviewer required |
| API key committed to GitHub | Low | `.gitignore` blocks `.env`; `.env.example` has no real keys; pre-commit hook added |
| Volunteer location unavailable | Low | Radius filter fallback → accept all; coordinator manually confirms suitability |
| Supabase Storage unavailable | Low | File uploads queued in Firestore for retry; PDFs regenerated on next request |
| Nominatim rate limit (1 req/sec) | Low | Request queue with 1.1s delay; fallback to manual lat/lng entry |

### Fallback as Risk Mitigation

The entire fallback architecture described in Section 8 is itself a risk mitigation
strategy. Every component that could fail during a demo, a crisis surge, or a rural
deployment has a labelled degraded-mode alternative that:

1. Always returns a result
2. Labels the result with its source
3. Never blocks the coordinator's ability to act
4. Logs the fallback usage for analytics and audit

This is not defensive programming — it is production-level design judgment. The fallback
system is a feature, not a safety net.
