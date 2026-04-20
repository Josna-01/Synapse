# SYNAPSE — Community Intelligence & Volunteer Dispatch Platform

Turn scattered NGO data into live community intelligence. Automatically dispatch the right volunteer to the right need before the window closes.

## Problem Statement
Every day across India and the developing world, NGOs collect vital data about community needs — on paper, in WhatsApp groups, in spreadsheets that nobody reads. Volunteers want to help but pick convenient tasks instead of urgent ones. Government schemes sit unfunded because district officials don't know which communities qualify. Donors write cheques and never learn if they made a difference.

The problem is not lack of resources. It is poor visibility causing misallocation.

## Solution Overview
SYNAPSE is a four-role platform that solves visibility:

| Role | Problem SYNAPSE solves |
|---|---|
| **NGO Coordinator** | Triage 12 open needs in 15 minutes instead of 2 hours |
| **Volunteer** | Receive the highest-urgency task you are best qualified for, not what's easiest |
| **Government Admin** | See district-level needs data and scheme alignment opportunities weekly |
| **Donor / Fundraiser** | Trace every rupee to a GPS-verified on-ground outcome |

## Core Innovation
*   **Paper → heatmap in 8 seconds** — Gemini + pytesseract OCR converts a field worker's survey photo into a structured, scored, geolocated need record on the live map.
*   **Explainable urgency score (0–100)** — No more gut-feel triage. Every need has a transparent score: `(severity × 0.35) + (frequency × 0.25) + (recency × 0.20) + (population × 0.20)` with plain-language explanation: "High — 47 water reports in 14 days, 8,200 residents affected."
*   **Need-driven volunteer dispatch** — Flips the passive listing model. System pushes the highest-urgency task to the best-matched nearby volunteer proactively.
*   **Verified impact chain** — Every donation is traceable to a specific task, a GPS-verified volunteer check-in, and a confirmed outcome. Not estimated impact — verified.
*   **Feedback loop** — Outcome reports retrain urgency scoring weekly. After 6 months, SYNAPSE predictions are more accurate than any competitor.

## Fallback Architecture — System Never Fails
SYNAPSE is built for real-world deployment: poor connectivity, API quota limits, and last-minute demo surges are all handled gracefully. Every critical component has a fallback mode. The system always produces a result.

| Component | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|---|---|---|---|---|
| Urgency scoring | Gemini 2.5 Flash | Rule-based keywords | Default score (50) | — |
| Volunteer matching | OSRM travel time + Gemini embeddings | Haversine straight-line distance | Radius filter only | Accept all available |
| Survey OCR | pytesseract + Gemini | Manual form entry | — | — |
| Notifications | FCM push | Email (Resend) | In-app Firestore flag | — |

**Key files:**
*   `services/api/src/fallbacks/scoring.py` — Rule-based urgency scoring
*   `services/api/src/fallbacks/matching.py` — Haversine distance matching
*   `services/api/src/fallbacks/notify.py` — Multi-channel notification with fallback
*   `services/api/src/integrations/gemini.py` — Gemini wrapper with fallback trigger

## Features by Dashboard

### NGO Coordinator Dashboard (Josna)
*   Live Leaflet/OpenStreetMap heatmap with urgency colour ramps (real-time Firestore listener)
*   Priority queue sorted by Gemini urgency score (0–100) — not submission time
*   One-click volunteer dispatch with skill-match explanation
*   OCR photo upload → structured need in 8 seconds (manual fallback if OCR fails)
*   Cross-NGO deduplication alerts
*   Inter-NGO coordination inbox
*   Government scheme matching suggestions (Jal Jeevan, PM-POSHAN, MGNREGA)
*   Gemini-generated donor impact PDF (one click, replaces 3 days of manual reporting)
*   Predictive alerts: "Water cluster in Ward 6 will likely peak in 6 days"
*   Fallback state banner when AI scoring is unavailable

### Volunteer Mobile App (Ancilla — Flutter)
*   flutter_map/OpenStreetMap showing nearby open tasks as urgency-coloured pins
*   FCM push: "Water shortage, 1.2km. Matched: nurse skill 91%. Urgency: 87/100. Accept?"
*   Task detail: why matched, what's needed, estimated time, embedded navigation
*   GPS check-in on arrival (verifies attendance)
*   3-question outcome form on task close (90 seconds)
*   Badge system: 20 achievements across 7 categories (tasks, hours, streak, impact, domain)
*   Level progression: Newcomer → Helper → Responder → Champion → Hero → Legend
*   Impact dashboard: hours, tasks, "you helped 1,240 people", verifiable certificates
*   Offline mode: task details cached in shared_preferences local storage (works on 2G)
*   Email notification fallback if FCM token is expired

### Government / Admin Dashboard (Josna)
*   District-level choropleth map (Leaflet + GeoJSON GADM boundaries)
*   Coverage gap layer: wards with high need AND zero NGO activity
*   Scheme matcher: need cluster → aligned government scheme → application deadline
*   Cross-NGO coordination overview: who is doing what where
*   Gemini-generated weekly digest (Monday 6am, PDF export)
*   SDG alignment tags per need cluster
*   Historical trend charts (is this district improving or worsening?)

### Donor / Fundraiser Portal (Ancilla)
*   Active campaigns with live funding progress bars
*   Verified impact chain: donation → task → GPS check-in → outcome report
*   One-click Gemini-generated impact PDF
*   CSR compliance export: Section 80G receipt + utilisation certificate
*   Campaign creation for NGO coordinators (linked to need clusters)
*   Anonymous donation option
*   Recurring donation setup
*   Corporate donor portfolio view

## Tech Stack

### Frontend
| Technology | Used for | Why |
|---|---|---|
| Next.js 14 (App Router) | NGO Dashboard + Govt Dashboard + Donor Portal | SSR, fast, one codebase |
| Flutter 3.x | Volunteer Mobile App | FCM built-in, offline-capable |
| Tailwind CSS | All web dashboards | Consistent design system, fast iteration |
| DM Sans + DM Serif Display | Typography | Professional, not generic |

### Backend
| Technology | Used for | Why |
|---|---|---|
| FastAPI (Python) | AI pipeline endpoints (OCR, scoring, matching) | Async, native ML/AI integration |
| Railway.app | Hosting FastAPI | Simple deploy, free tier, no cold-start |
| Firebase App Hosting | Next.js deployment | Git-connected CI/CD, global CDN, free |

### Database & Real-time
| Technology | Used for | Why |
|---|---|---|
| Cloud Firestore | All operational data + real-time listeners | Replaces Socket.io, 50K reads/day free |
| Supabase Storage | Survey images, audio, generated PDFs | 1GB free, no credit card, signed URLs |

### Authentication
| Technology | Used for |
|---|---|
| Firebase Auth | Email/password (coordinators), Google Sign-In (volunteers), Phone OTP (field workers) |

### AI / ML (API-based only — no custom models)
| API | Used for | Free tier |
|---|---|---|
| Gemini 2.5 Flash | OCR extraction, urgency scoring, matching explanation, reports | 15 RPM / 1M tokens/day |
| Gemini 2.5 Pro | District digest, CSR report generation | Paid, used sparingly |
| pytesseract (local) | Paper survey OCR (12 Indian scripts) | Free, open source |
| OpenAI Whisper (local) | WhatsApp voice note transcription (125 languages) | Free, open source |
| LibreTranslate | Field reports + bot responses (50+ languages) | Free, open source |
| Google Agent Development Kit | Multi-agent orchestration | Open source (Apache 2.0) |

### Maps & Location
| API | Used for | Cost |
|---|---|---|
| Leaflet + OpenStreetMap | NGO heatmap, volunteer task map, govt choropleth | Free, no key needed |
| Nominatim | Address → lat/lng + admin boundary codes | Free, no key needed |
| OSRM | Actual travel time for volunteer matching | Free, no key needed |
| Overpass API | Nearby hospitals/facilities for volunteer briefing | Free, no key needed |
| GeoJSON + Leaflet | Custom admin boundary overlays (GADM polygons) | Free, static files |

### Notifications & Messaging
| Technology | Used for |
|---|---|
| Firebase Cloud Messaging (FCM) | Volunteer push notifications (free, no limits) |
| WhatsApp Cloud API | Field worker voice/text report intake |
| Resend | Weekly digests, donor impact emails, FCM fallback |

## Architecture Overview
```text
┌─────────────────────────────────────────────────────────────────────┐
│                        SYNAPSE PLATFORM                              │
├─────────────────────────────────────────────────────────────────────┤
│  INPUTS                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Survey   │  │ WhatsApp │  │  Web     │  │  Open Data       │   │
│  │ Photo    │  │ Voice    │  │  Form    │  │  (World Bank,    │   │
│  │          │  │ Note     │  │          │  │   UN HDX, WHO)   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │              │                  │             │
│       └──────────────┴──────────────┴──────────────────┘           │
│                               │                                      │
│                    ┌──────────▼──────────┐                          │
│                    │   FASTAPI BACKEND   │                          │
│                    │   (Railway.app)     │                          │
│                    │                     │                          │
│                    │  pytesseract OCR    │                          │
│                    │  Whisper STT        │                          │
│                    │  LibreTranslate     │                          │
│                    │  Nominatim geocode  │                          │
│                    │  Gemini scoring     │                          │
│                    └──────────┬──────────┘                          │
│                               │                                      │
│                    ┌──────────▼──────────┐                          │
│                    │  GOOGLE ADK AGENTS  │                          │
│                    │                     │                          │
│                    │  Orchestrator       │                          │
│                    │  NGO Agent          │                          │
│                    │  Volunteer Agent    │                          │
│                    │  Govt Agent         │                          │
│                    │  Donor Agent        │                          │
│                    └──────────┬──────────┘                          │
│                               │                                      │
│              ┌────────────────▼────────────────┐                    │
│              │         CLOUD FIRESTORE          │                    │
│              │  (Real-time listener → UI)       │                    │
│              └────────────────┬────────────────┘                    │
│                               │                                      │
│  ┌────────────┐  ┌────────────▼────┐  ┌──────────┐  ┌───────────┐ │
│  │  NGO       │  │  VOLUNTEER APP  │  │  GOVT    │  │  DONOR    │ │
│  │  DASHBOARD │  │  (Flutter)      │  │  ADMIN   │  │  PORTAL   │ │
│  │  Next.js   │  │  flutter_map    │  │  Next.js │  │  Next.js  │ │
│  │  Leaflet   │  │  FCM push       │  │  Leaflet │  │           │ │
│  └────────────┘  └─────────────────┘  └──────────┘  └───────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Folder Structure
```text
synapse/
├── apps/
│   ├── web/                          # Next.js web app (NGO + Govt + Donor)
│   │   └── src/app/
│   │       ├── dashboard/            # NGO Coordinator dashboard
│   │       ├── gov/                  # Government admin dashboard
│   │       └── components/
│   │           └── map/              # Leaflet map components
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
│       │   │   ├── matching.py       # Haversine distance (OSRM fallback)
│       │   │   ├── notify.py         # Email + in-app (FCM fallback)
│       │   │   └── ocr.py            # Manual entry flag (pytesseract fallback)
│       │   └── integrations/
│       │       ├── gemini.py         # Gemini wrapper with fallback trigger
│       │       ├── maps.py           # OSRM + Nominatim + haversine combo
│       │       ├── firebase.py       # Firestore helpers
│       │       ├── storage.py        # Supabase Storage upload (renamed from cloudinary.py)
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
│   └── load_gadm.py                  # Load admin boundary polygons → GeoJSON
│
├── public/
│   └── geojson/
│       └── india_districts.geojson   # GADM district boundaries (static file)
│
├── agents.md
├── README.md
├── .env.example
└── docker-compose.yml                # Local dev environment
```

## How the System Works (Simple Explanation)
1.  A field worker photographs a paper survey or sends a WhatsApp voice note.
2.  SYNAPSE uses pytesseract + Gemini to read it and create a structured record.
    *   If OCR is unavailable → the coordinator fills a manual form instead.
3.  An urgency score (0-100) is computed using a formula: severity + frequency + recency + population.
    *   If Gemini is unavailable → a rule-based keyword system scores it.
    *   If that fails → a default score of 50 is assigned.
4.  The need appears on the NGO coordinator's live Leaflet heatmap.
    *   Critical needs (score ≥ 80) are auto-dispatched without waiting for coordinator.
5.  The best volunteer is found using actual travel time (OSRM) + skill matching.
    *   If OSRM is unavailable → straight-line distance (Haversine formula) is used instead.
6.  A push notification is sent to the volunteer's phone.
    *   If FCM fails → an email is sent via Resend instead.
    *   If email fails → a notification waits in-app.
7.  The volunteer accepts, travels, GPS checks in, completes the task, and submits an outcome.
8.  The outcome flows back: urgency score recalibrated, donor impact counter updated, government coverage gap cleared.

The system never fails silently. Every fallback is labelled and logged.

## Demo Flow (90-Second Arc)
1.  **SCAN (8s)**
    *   Field worker photographs printed survey form.
    *   pytesseract + Gemini OCR extracts: location, category, affected count, urgency hint.
    *   New `/needs` record written to Firestore.

2.  **MAP UPDATES LIVE (5s)**
    *   NGO coordinator's laptop: Leaflet map adds red pin.
    *   Priority queue: "Acute water shortage — 87/100" appears at position #1.
    *   Alert banner: "New critical need — water shortage, Ward 6."

3.  **DISPATCH (5s)**
    *   Coordinator clicks need → sees urgency breakdown + plain explanation.
    *   Clicks "Find Volunteers" → top 3 shown with skill%, distance, availability.
    *   Coordinator clicks dispatch → FCM fires.

4.  **PHONE VIBRATES LIVE (on table, visible to judges)**
    *   Notification: "Water shortage, 1.2km. Matched: nurse skill 91%. Urgency: 87/100. Accept?"
    *   Volunteer taps Accept.
    *   Coordinator dashboard: task status → "Assigned — Amara Osei".

5.  **OUTCOME + FEEDBACK LOOP (10s)**
    *   Pre-seeded completed task: outcome submitted.
    *   Urgency score updates 87 → 42 (partially resolved).
    *   Donor portal: campaign impact counter increments.
    *   "That outcome data just retrains our urgency model — no other platform does this."

## Screens Overview

### NGO Coordinator (Josna — Next.js)
*   `/dashboard` — Command centre: KPI cards, live heatmap, priority queue, activity feed
*   `/map` — Full-screen Leaflet heatmap with category filters
*   `/submit` — OCR photo upload + structured form
*   `/needs/[id]` — Need detail: urgency breakdown, volunteer match, dispatch
*   `/analytics` — Impact charts, volunteer performance, model accuracy
*   `/agents` — AI agent terminal

### Government Admin (Josna — same Next.js app)
*   `/gov` — Leaflet choropleth map, coverage gaps, scheme matcher
*   `/gov/digest` — Weekly Gemini digest viewer + PDF export

### Volunteer App (Ancilla — Flutter)
*   `TasksScreen` — flutter_map with nearby task pins
*   `TaskDetailScreen` — Why matched, what to do, Accept/Pass
*   `ActiveTaskScreen` — Navigation + GPS check-in + outcome form
*   `ImpactScreen` — Hours chart, tasks donut, people helped counter
*   `BadgesScreen` — Achievement grid with progress rings

### Donor Portal (Ancilla — Next.js)
*   `/fundraiser` — Featured campaigns grid
*   `/fundraiser/[id]` — Campaign detail, donation flow, impact chain
*   `/fundraiser/my-impact` — Portfolio, CSR export, certificates

## Future Scope
*   **Predictive forecasting** — "Water cluster in Ward 6 will peak in 6 days" using historical pattern analysis and seasonal data
*   **WhatsApp full conversation bot** — Complete 5-question intake flow without any app
*   **NSS/NCC integration** — API hooks to national volunteer databases (13M students)
*   **USSD fallback** — Zero-smartphone access via keypad phone for truly last-mile communities
*   **UN HDX integration** — Global expansion data layer for 180+ countries
*   **Volunteer NSS certificate integration** — DigiLocker-linked verifiable credentials
*   **Multi-country scheme database** — Expand beyond India to WASH programs, UN SDG funds

## Team
| Developer | Dashboards | Stack |
|---|---|---|
| Josna | NGO Coordinator + Government Admin | Next.js 14, TypeScript, Leaflet/OSM, Gemini |
| Ancilla | Volunteer Mobile App + Donor Portal | Flutter, Firebase, FCM, Next.js |

*(Shared: Firebase Auth, Cloud Firestore, FastAPI backend, Google ADK agents, fallback layer)*

## License
Apache 2.0 — see `LICENSE` for details.