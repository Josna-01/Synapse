# SYNAPSE — Community Intelligence & Volunteer Dispatch Platform

> **Turn scattered NGO data into live community intelligence. Automatically dispatch the
> right volunteer to the right need before the window closes.**

---

## Problem Statement

Every day across India and the developing world, NGOs collect vital data about community
needs — on paper, in WhatsApp groups, in spreadsheets that nobody reads. Volunteers want
to help but pick convenient tasks instead of urgent ones. Government schemes sit unfunded
because district officials don't know which communities qualify. Donors write cheques and
never learn if they made a difference.

**The problem is not lack of resources. It is poor visibility causing misallocation.**

---

## Solution Overview

SYNAPSE is a four-role platform that solves visibility:

| Role | Problem SYNAPSE solves |
|------|----------------------|
| **NGO Coordinator** | Triage 12 open needs in 15 minutes instead of 2 hours |
| **Volunteer** | Receive the highest-urgency task you are best qualified for, not what's easiest |
| **Government Admin** | See district-level needs data and scheme alignment opportunities weekly |
| **Donor / Fundraiser** | Trace every rupee to a GPS-verified on-ground outcome |

---

## Core Innovation

1. **Paper → heatmap in 8 seconds** — Gemini Vision OCR converts a field worker's
   survey photo into a structured, scored, geolocated need record on the live map.

2. **Explainable urgency score (0–100)** — No more gut-feel triage. Every need has a
   transparent score: `(severity × 0.35) + (frequency × 0.25) + (recency × 0.20) + (population × 0.20)`
   with plain-language explanation: "High — 47 water reports in 14 days, 8,200 residents affected."

3. **Need-driven volunteer dispatch** — Flips the passive listing model. System pushes
   the highest-urgency task to the best-matched nearby volunteer proactively.

4. **Verified impact chain** — Every donation is traceable to a specific task, a
   GPS-verified volunteer check-in, and a confirmed outcome. Not estimated impact — verified.

5. **Feedback loop** — Outcome reports retrain urgency scoring weekly. After 6 months,
   SYNAPSE predictions are more accurate than any competitor.

---

## Fallback Architecture — System Never Fails

SYNAPSE is built for real-world deployment: poor connectivity, API quota limits, and
last-minute demo surges are all handled gracefully. Every critical component has a
fallback mode. The system always produces a result.

| Component | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|-----------|---------|------------|------------|------------|
| Urgency scoring | Gemini 2.0 Flash | Rule-based keywords | Default score (50) | — |
| Volunteer matching | Routes API + Gemini embeddings | Haversine straight-line distance | Radius filter only | Accept all available |
| Survey OCR | Cloud Vision + Document AI | Manual form entry | — | — |
| Notifications | FCM push | Email (Gmail/Resend) | In-app Firestore flag | — |

Key files:
- `services/api/src/fallbacks/scoring.py` — Rule-based urgency scoring
- `services/api/src/fallbacks/matching.py` — Haversine distance matching
- `services/api/src/fallbacks/notify.py` — Multi-channel notification with fallback
- `services/api/src/integrations/gemini.py` — Gemini wrapper with fallback trigger

---

## Features by Dashboard

### NGO Coordinator Dashboard (Amisha)
- Live Google Maps heatmap with urgency colour ramps (real-time Firestore listener)
- Priority queue sorted by Gemini urgency score (0–100) — not submission time
- One-click volunteer dispatch with skill-match explanation
- OCR photo upload → structured need in 8 seconds (manual fallback if OCR fails)
- Cross-NGO deduplication alerts
- Inter-NGO coordination inbox
- Government scheme matching suggestions (Jal Jeevan, PM-POSHAN, MGNREGA)
- Gemini-generated donor impact PDF (one click, replaces 3 days of manual reporting)
- Predictive alerts: "Water cluster in Ward 6 will likely peak in 6 days"
- Fallback state banner when AI scoring is unavailable

### Volunteer Mobile App (Ancilla — Flutter)
- Google Maps showing nearby open tasks as urgency-coloured pins
- FCM push: "Water shortage, 1.2km. Matched: nurse skill 91%. Urgency: 87/100. Accept?"
- Task detail: why matched, what's needed, estimated time, embedded navigation
- GPS check-in on arrival (verifies attendance)
- 3-question outcome form on task close (90 seconds)
- Badge system: 20 achievements across 7 categories (tasks, hours, streak, impact, domain)
- Level progression: Newcomer → Helper → Responder → Champion → Hero → Legend
- Impact dashboard: hours, tasks, "you helped 1,240 people", verifiable certificates
- Offline mode: task details cached in Hive local storage (works on 2G)
- Email notification fallback if FCM token is expired

### Government / Admin Dashboard (Amisha)
- District-level choropleth map (Google Maps Datasets API + GADM boundaries)
- Coverage gap layer: wards with high need AND zero NGO activity
- Scheme matcher: need cluster → aligned government scheme → application deadline
- Cross-NGO coordination overview: who is doing what where
- Gemini-generated weekly digest (Monday 6am, PDF export)
- SDG alignment tags per need cluster
- Historical trend charts (is this district improving or worsening?)

### Donor / Fundraiser Portal (Ancilla)
- Active campaigns with live funding progress bars
- Verified impact chain: donation → task → GPS check-in → outcome report
- One-click Gemini-generated impact PDF
- CSR compliance export: Section 80G receipt + utilisation certificate
- Campaign creation for NGO coordinators (linked to need clusters)
- Anonymous donation option
- Recurring donation setup
- Corporate donor portfolio view

---

## Tech Stack

### Frontend
| Technology | Used for | Why |
|---|---|---|
| Next.js 14 (App Router) | NGO Dashboard + Govt Dashboard + Donor Portal | SSR, fast, one codebase |
| Flutter | Volunteer Mobile App | Google-native, FCM built-in, offline-capable |
| Tailwind CSS | All web dashboards | Consistent design system, fast iteration |
| DM Sans + DM Serif Display | Typography | Professional, not generic |

### Backend
| Technology | Used for | Why |
|---|---|---|
| FastAPI (Python) | AI pipeline endpoints (OCR, scoring, matching) | Async, native ML/AI integration |
| Google Cloud Run | Hosting FastAPI | Serverless, scales to zero, 2M req/month free |
| Firebase App Hosting | Next.js deployment | Git-connected CI/CD, global CDN, free |

### Database & Real-time
| Technology | Used for | Why |
|---|---|---|
| Cloud Firestore | All operational data + real-time listeners | Replaces Socket.io, 50K reads/day free |
| PostgreSQL + PostGIS | Geospatial queries (volunteer matching) | ST_DWithin for proximity filtering |
| Cloud Storage | Survey images, audio, generated PDFs | Native Vision API integration, 5GB free |

### Authentication
| Technology | Used for |
|---|---|
| Firebase Auth | Email/password (coordinators), Google Sign-In (volunteers), Phone OTP (field workers) |

### AI / ML (API-based only — no custom models)
| API | Used for | Free tier |
|---|---|---|
| Gemini 2.0 Flash | OCR extraction, urgency scoring, matching explanation, reports | 15 RPM / 1M tokens/day |
| Gemini 2.5 Pro | District digest, CSR report generation | Paid, used sparingly |
| Cloud Vision API + Document AI | Paper survey OCR (12 Indian scripts) | 1,000 units/month free |
| Cloud Speech-to-Text v2 | WhatsApp voice note transcription (125 languages) | 60 min/month free |
| Cloud Translation API v3 | Field reports + bot responses (50+ languages) | 500K chars/month free |
| Google Agent Development Kit | Multi-agent orchestration | Open source (Apache 2.0) |

### Maps & Location
| API | Used for | Free tier |
|---|---|---|
| Maps JavaScript API | NGO heatmap, volunteer task map, govt choropleth | 28,500 loads/month |
| Geocoding API v4 | Address → lat/lng + admin boundary codes | 40K requests/month |
| Routes API | Actual travel time for volunteer matching (not straight-line) | 40K routes/month |
| Places API (New) | Nearby hospitals/facilities for volunteer briefing | 17K requests/month |
| Maps Datasets API | Custom admin boundary overlays (GADM polygons) | 5 datasets free |

### Notifications & Messaging
| Technology | Used for |
|---|---|
| Firebase Cloud Messaging (FCM) | Volunteer push notifications (free, no limits) |
| WhatsApp Cloud API | Field worker voice/text report intake |
| Gmail API + Resend | Weekly digests, donor impact emails, FCM fallback |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                              │
│                                                                     │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Next.js Web    │  │   Flutter    │  │    Next.js Web       │  │
│  │  NGO Dashboard  │  │  Volunteer   │  │  Govt + Donor Portal │  │
│  │  (Amisha)       │  │  App         │  │  (Amisha + Ancilla)  │  │
│  │                 │  │  (Ancilla)   │  │                      │  │
│  └────────┬────────┘  └──────┬───────┘  └──────────┬───────────┘  │
└───────────│──────────────────│─────────────────────│───────────────┘
            │                  │                      │
            └──────────────────┴──────────────────────┘
                                │
                ┌───────────────▼───────────────┐
                │        FIREBASE LAYER         │
                │   Firestore (real-time sync)  │
                │   Firebase Auth               │
                │   Firebase App Hosting        │
                │   Cloud Storage               │
                └───────────────┬───────────────┘
                                │
                ┌───────────────▼───────────────┐
                │      FASTAPI BACKEND          │
                │      (Cloud Run)              │
                │                               │
                │  /api/v1/needs                │
                │  /api/v1/ocr                  │
                │  /api/v1/volunteers/match     │
                │  /api/v1/agents/run           │
                │  /webhooks/whatsapp           │
                │                               │
                │  fallbacks/scoring.py         │
                │  fallbacks/matching.py        │
                │  fallbacks/notify.py          │
                └───────────────┬───────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼──────┐    ┌──────────▼─────────┐    ┌────────▼──────────┐
│  GOOGLE AI   │    │    GOOGLE MAPS     │    │   GOOGLE CLOUD    │
│              │    │                   │    │                   │
│  Gemini 2.0  │    │  Maps JS API      │    │  Cloud Vision     │
│  Gemini 2.5  │    │  Geocoding API    │    │  Document AI      │
│  ADK Agents  │    │  Routes API       │    │  Speech-to-Text   │
│  Translation │    │  Places API       │    │  Cloud Translation│
│  ↓ fallback  │    │  ↓ haversine      │    │  ↓ manual entry   │
│  rule-based  │    │  formula          │    │  fallback         │
└──────────────┘    └───────────────────┘    └───────────────────┘
```

---

## Setup Instructions

### Prerequisites
- Node.js 20+
- Python 3.12+
- Flutter SDK 3.x
- Firebase CLI (`npm install -g firebase-tools`)
- Google Cloud SDK (`gcloud`)

### 1. Clone repository
```bash
git clone https://github.com/your-team/synapse.git
cd synapse
```

### 2. Copy environment variables
```bash
cp .env.example .env
# Fill in all variables — see .env.example for documentation
```

### 3. Firebase setup
```bash
firebase login
firebase init  # Select: Hosting, Firestore, Authentication, Storage
firebase deploy --only firestore:rules,firestore:indexes
```

### 4. Install web dependencies
```bash
cd apps/web
npm install
```

### 5. Install Python backend dependencies
```bash
cd services/api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 6. Seed demo data
```bash
cd scripts
python seed.py --district mysuru --needs 12 --volunteers 8 --campaigns 3
```

### 7. Run development servers
```bash
# Terminal 1: Web dashboard
cd apps/web && npm run dev

# Terminal 2: FastAPI backend
cd services/api && uvicorn src.main:app --reload --port 8000

# Terminal 3: Flutter app
cd apps/mobile && flutter run
```

---

## Environment Variables

```env
# ===== GEMINI =====
GEMINI_API_KEY=your_gemini_api_key_here

# ===== FIREBASE =====
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY=your_private_key
FIREBASE_CLIENT_EMAIL=your_client_email

# ===== GOOGLE MAPS =====
GOOGLE_MAPS_API_KEY=your_maps_key_here
NEXT_PUBLIC_GOOGLE_MAPS_KEY=your_maps_key_here

# ===== FIREBASE CLIENT (Next.js) =====
NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_auth_domain
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your_storage_bucket
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id

# ===== CLOUDINARY =====
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_key
CLOUDINARY_API_SECRET=your_cloudinary_secret

# ===== FCM =====
FCM_SERVER_KEY=your_fcm_key

# ===== BACKEND =====
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Folder Structure

```
synapse/
├── apps/
│   ├── web/                          # Next.js 14 — All web dashboards
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── (auth)/           # Login, register, OTP
│   │   │   │   ├── dashboard/        # NGO coordinator view
│   │   │   │   ├── map/              # Full-screen heatmap
│   │   │   │   ├── submit/           # Report submission form
│   │   │   │   ├── needs/[id]/       # Need detail page
│   │   │   │   ├── volunteer/        # Volunteer portal (web)
│   │   │   │   ├── gov/              # Government admin view
│   │   │   │   ├── fundraiser/       # Donor portal
│   │   │   │   ├── analytics/        # Impact analytics
│   │   │   │   └── agents/           # AI agent interface
│   │   │   ├── components/
│   │   │   │   ├── ui/               # Shared: StatCard, UrgencyBadge, Avatar
│   │   │   │   ├── dashboard/        # AlertsBanner, QuickActions, ActivityFeed
│   │   │   │   ├── map/              # NeedsMapWidget
│   │   │   │   ├── volunteer/        # VolunteerCard, BadgeGrid, TaskBoard
│   │   │   │   ├── fundraiser/       # CampaignCard, DonationFlow, ImpactChain
│   │   │   │   └── agents/           # AgentTerminal, AgentLog
│   │   │   ├── lib/
│   │   │   │   ├── api.ts            # All API client functions
│   │   │   │   ├── firebase.ts       # Firestore + Auth initialisation
│   │   │   │   └── utils.ts          # Helpers, urgency colours, formatters
│   │   │   ├── types/index.ts        # All TypeScript types
│   │   │   └── styles/globals.css    # Design tokens, component classes
│   │   ├── package.json
│   │   ├── next.config.js
│   │   └── tailwind.config.js
│   │
│   └── mobile/                       # Flutter volunteer app
│       ├── lib/
│       │   ├── main.dart
│       │   ├── screens/
│       │   │   ├── tasks/            # Nearby tasks map + list
│       │   │   ├── task_detail/      # Task info + accept/pass
│       │   │   ├── active_task/      # Check-in + navigation
│       │   │   ├── impact/           # Hours, tasks, lives helped
│       │   │   └── badges/           # Achievement grid
│       │   ├── services/
│       │   │   ├── firebase_service.dart
│       │   │   ├── fcm_service.dart
│       │   │   └── maps_service.dart
│       │   └── models/               # Dart models for Volunteer, Task, Badge
│       └── pubspec.yaml
│
├── services/
│   └── api/                          # FastAPI Python backend
│       ├── src/
│       │   ├── main.py               # App entry point
│       │   ├── routers/
│       │   │   ├── needs.py          # CRUD + urgency scoring
│       │   │   ├── surveys.py        # OCR + WhatsApp webhook
│       │   │   ├── volunteers.py     # Matching engine
│       │   │   ├── tasks.py          # Task lifecycle
│       │   │   ├── campaigns.py      # Fundraiser campaigns
│       │   │   ├── analytics.py      # Impact metrics
│       │   │   └── agents.py         # ADK agent runner
│       │   ├── agents/
│       │   │   ├── orchestrator.py
│       │   │   ├── ngo_agent.py
│       │   │   ├── volunteer_agent.py
│       │   │   ├── govt_agent.py
│       │   │   └── donor_agent.py
│       │   ├── fallbacks/            # ← RESILIENCE LAYER
│       │   │   ├── scoring.py        # Rule-based urgency (Gemini fallback)
│       │   │   ├── matching.py       # Haversine distance (Routes API fallback)
│       │   │   ├── notify.py         # Email + in-app (FCM fallback)
│       │   │   └── ocr.py            # Manual entry flag (Vision API fallback)
│       │   └── integrations/
│       │       ├── gemini.py         # Gemini wrapper with fallback trigger
│       │       ├── maps.py           # Routes + haversine combo
│       │       ├── firebase.py       # Firestore helpers
│       │       ├── cloudinary.py     # Image/file upload
│       │       └── fcm.py            # FCM push + email fallback
│       └── requirements.txt
│
├── firebase/
│   ├── firestore.rules               # Security rules
│   ├── firestore.indexes.json        # Composite indexes
│   └── functions/
│       └── badge_triggers.js         # Cloud Functions for badge awards
│
├── scripts/
│   ├── seed.py                       # Load demo data
│   └── load_gadm.py                  # Load admin boundary polygons
│
├── agents.md
├── README.md
├── .env.example
└── docker-compose.yml                # Local: Postgres + Redis
```

---

## How the System Works (Simple Explanation)

```
1. A field worker photographs a paper survey or sends a WhatsApp voice note.

2. SYNAPSE uses AI (Gemini + Cloud Vision) to read it and create a structured record.
   If AI is unavailable → the coordinator fills a manual form instead.

3. An urgency score (0-100) is computed using a formula: severity + frequency + recency + population.
   If Gemini is unavailable → a rule-based keyword system scores it.
   If that fails → a default score of 50 is assigned.

4. The need appears on the NGO coordinator's live heatmap.
   Critical needs (score ≥ 80) are auto-dispatched without waiting for coordinator.

5. The best volunteer is found using actual travel time (Routes API) + skill matching.
   If Routes API is unavailable → straight-line distance (Haversine formula) is used instead.

6. A push notification is sent to the volunteer's phone.
   If FCM fails → an email is sent instead.
   If email fails → a notification waits in-app.

7. The volunteer accepts, travels, GPS checks in, completes the task, and submits an outcome.

8. The outcome flows back: urgency score recalibrated, donor impact counter updated,
   government coverage gap cleared.
```

The system never fails silently. Every fallback is labelled and logged.

---

## Demo Flow (90-Second Arc)

```
1. SCAN (8s)
   Field worker photographs printed survey form.
   Gemini Vision OCR extracts: location, category, affected count, urgency hint.
   New /needs record written to Firestore.

2. MAP UPDATES LIVE (5s)
   NGO coordinator's laptop: Google Maps adds red pin.
   Priority queue: "Acute water shortage — 87/100" appears at position #1.
   Alert banner: "New critical need — water shortage, Ward 6."

3. DISPATCH (5s)
   Coordinator clicks need → sees urgency breakdown + plain explanation.
   Clicks "Find Volunteers" → top 3 shown with skill%, distance, availability.
   Coordinator clicks dispatch → FCM fires.

4. PHONE VIBRATES LIVE (on table, visible to judges)
   Notification: "Water shortage, 1.2km. Matched: nurse skill 91%. Urgency: 87/100. Accept?"
   Volunteer taps Accept.
   Coordinator dashboard: task status → "Assigned — Amara Osei".

5. OUTCOME + FEEDBACK LOOP (10s)
   Pre-seeded completed task: outcome submitted.
   Urgency score updates 87 → 42 (partially resolved).
   Donor portal: campaign impact counter increments.
   "That outcome data just retrains our urgency model — no other platform does this."
```

---

## Screens Overview

### NGO Coordinator (Amisha — Next.js)
- `/dashboard` — Command centre: KPI cards, live heatmap, priority queue, activity feed
- `/map` — Full-screen heatmap with category filters
- `/submit` — OCR photo upload + structured form
- `/needs/[id]` — Need detail: urgency breakdown, volunteer match, dispatch
- `/analytics` — Impact charts, volunteer performance, model accuracy
- `/agents` — AI agent terminal

### Government Admin (Amisha — same Next.js app)
- `/gov` — Choropleth map, coverage gaps, scheme matcher
- `/gov/digest` — Weekly Gemini digest viewer + PDF export

### Volunteer App (Ancilla — Flutter)
- `TasksScreen` — Google Maps with nearby task pins
- `TaskDetailScreen` — Why matched, what to do, Accept/Pass
- `ActiveTaskScreen` — Navigation + GPS check-in + outcome form
- `ImpactScreen` — Hours chart, tasks donut, people helped counter
- `BadgesScreen` — Achievement grid with progress rings

### Donor Portal (Ancilla — Next.js)
- `/fundraiser` — Featured campaigns grid
- `/fundraiser/[id]` — Campaign detail, donation flow, impact chain
- `/fundraiser/my-impact` — Portfolio, CSR export, certificates

---

## Future Scope

1. **Predictive forecasting** — "Water cluster in Ward 6 will peak in 6 days" using
   historical pattern analysis and seasonal data
2. **WhatsApp full conversation bot** — Complete 5-question intake flow without any app
3. **NSS/NCC integration** — API hooks to national volunteer databases (13M students)
4. **USSD fallback** — Zero-smartphone access via keypad phone for truly last-mile communities
5. **UN HDX integration** — Global expansion data layer for 180+ countries
6. **Volunteer NSS certificate integration** — DigiLocker-linked verifiable credentials
7. **Multi-country scheme database** — Expand beyond India to WASH programs, UN SDG funds

---

## Team

| Developer | Dashboards | Stack |
|---|---|---|
| **Amisha** | NGO Coordinator + Government Admin | Next.js 14, TypeScript, Google Maps API, Gemini |
| **Ancilla** | Volunteer Mobile App + Donor Portal | Flutter, Firebase, FCM, Next.js 14 |

**Shared:** Firebase Auth, Cloud Firestore, FastAPI backend, Google ADK agents, fallback layer

---

## License
Apache 2.0 — see LICENSE for details.
