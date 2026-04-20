# SYNAPSE — TECH STACK REFERENCE
> Complete dependency, setup, and integration guide for all 4 dashboards.
> Last updated: June 2025

---

## Overview

| Layer | Technology | Owner |
|---|---|---|
| Web dashboards (NGO + Govt + Donor) | Next.js 14 App Router + TypeScript | Josna |
| Mobile app (Volunteer) | Flutter 3.x | Ancilla |
| Backend AI pipeline | FastAPI (Python 3.12) + Railway.app | Both |
| Multi-agent orchestration | Google ADK Python SDK | Both |
| Database + Auth + Messaging | Firebase (Spark plan) | Both |
| File storage | Supabase Storage (free tier) | Both |
| Primary AI | Gemini 2.5 Flash + Pro | Both |

---

## Dashboard 1 — NGO Coordinator Dashboard (Josna)

**Framework:** Next.js 14 with App Router  
**Location:** `apps/web/src/app/dashboard/`

### APIs and libraries used:
- **Leaflet + OpenStreetMap** — live urgency heatmap with coloured markers
- **Nominatim API** — converts field survey addresses to lat/lng (OpenStreetMap geocoding)
- **Tesseract.js** (frontend) / **pytesseract** (backend) — OCR from survey photos (12 Indian scripts + handwriting)
- **OpenAI Whisper (local)** — transcribes WhatsApp voice notes
- **LibreTranslate** — normalises multi-language field reports
- **Gemini 2.5 Flash** — urgency scoring, dedup, match explanation, impact reports

### How they connect:
1. Field worker uploads photo → Supabase Storage → URL passed to FastAPI
2. FastAPI calls pytesseract → raw OCR text
3. Raw text → LibreTranslate → English → Gemini → structured JSON (category, description, location, count)
4. Structured data → Nominatim API → lat/lng + admin boundary code
5. Deduplication check (Gemini similarity + 500m geo radius)
6. Urgency score computed → written to Firestore `/needs/{id}`
7. Next.js dashboard reads Firestore real-time listener → map updates live

### npm install:
```bash
cd apps/web
npm install next@14 react react-dom typescript @types/react @types/node
npm install firebase
npm install leaflet react-leaflet @types/leaflet
npm install tailwindcss postcss autoprefixer
npm install lucide-react
```

---

## Dashboard 2 — Government / Admin Dashboard (Josna)

**Framework:** Next.js 14 (same codebase, route: `apps/web/src/app/gov/`)

### APIs and libraries used:
- **Leaflet + OpenStreetMap** + **GeoJSON** — district choropleth using GADM polygon overlays
- **Gemini 2.5 Pro** — weekly digest generation (2-page official briefing)
- **Resend** — sends digest to officials every Monday 6am

### How they connect:
1. Government Agent (scheduled Monday 6am via Railway cron) reads Firestore
2. Aggregates needs by admin boundary code
3. Coverage gap detection: avg_urgency ≥ 60 + zero tasks in 14 days
4. Gemini 2.5 Pro generates digest → Resend sends to district emails
5. React dashboard renders Firestore data via real-time listener
6. GeoJSON boundary files loaded directly into Leaflet (no external dataset API needed)

### GADM boundary setup:
```bash
# Download GADM GeoJSON and serve as static assets
cd scripts
python load_gadm.py --country IN --level 3   # level 3 = sub-district/block
# Output: public/geojson/india_districts.geojson
```

---

## Dashboard 3 — Volunteer Mobile App (Ancilla)

**Framework:** Flutter 3.x  
**Location:** `apps/mobile/`

### APIs and libraries used:
- **flutter_map + OpenStreetMap** — task map with nearby pins
- **Firebase Cloud Messaging (FCM)** — free, unlimited push notifications
- **OSRM API** — navigation routing to task location
- **Overpass API** — nearby facilities for volunteer briefing

### How they connect:
1. Volunteer Agent ranks matched volunteers → writes to `/tasks/{id}`
2. FCM push sent to volunteer's device token → app vibrates/alerts
3. Volunteer taps Accept → task status: `pending → accepted`
4. Volunteer navigates via flutter_map → arrives → GPS check-in
5. haversine_km validates check-in within 300m of task
6. Outcome form submitted → `/outcomes/{id}` written → urgency recalibrated

### Flutter pub dependencies:
```yaml
# pubspec.yaml
dependencies:
  flutter:
    sdk: flutter
  firebase_core: ^3.0.0
  firebase_auth: ^5.0.0
  cloud_firestore: ^5.0.0
  firebase_messaging: ^15.0.0
  flutter_map: ^6.0.0
  latlong2: ^0.9.0
  geolocator: ^12.0.0
  flutter_local_notifications: ^17.0.0
  http: ^1.2.0
  shared_preferences: ^2.2.0   # offline task caching
  cached_network_image: ^3.3.0
```

```bash
flutter pub get
flutter run --flavor development
```

### FCM setup:
1. Firebase Console → Project Settings → Cloud Messaging → get Server Key
2. Add `google-services.json` to `apps/mobile/android/app/`
3. Add `GoogleService-Info.plist` to `apps/mobile/ios/Runner/`

---

## Dashboard 4 — Donor / Fundraiser Portal (Ancilla)

**Framework:** Next.js 14 (`donor/` directory — separate deployment)

### APIs and libraries used:
- **Gemini 2.5 Pro** — personalised impact narratives, CSR report generation
- **Firebase Auth** — shared with other dashboards (same Firebase project)
- **Firestore** — `/campaigns`, `/impact_chains`, `/outcomes`
- **Supabase Storage** — generated PDFs
- **Resend** — donor impact emails

### CSR Report flow:
1. Donor clicks "Generate Report" → API call to `/api/v1/campaigns/{id}/csr-report`
2. Donor Agent reads impact chain: donation → need_cluster → tasks (GPS-verified)
3. Gemini 2.5 Pro generates Section 80G receipt + utilisation certificate
4. PDF uploaded to Supabase Storage → signed URL emailed to donor via Resend

```bash
cd donor
npm install
# Same dependencies as apps/web
```

---

## Maps & Location Setup

### Leaflet + OpenStreetMap
- No API key required — tiles served from OpenStreetMap CDN
- npm: `leaflet react-leaflet @types/leaflet`
- Tile URL: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
- Attribution required: © OpenStreetMap contributors
- Env var: none needed

### Nominatim (Geocoding)
- No API key required — free public endpoint
- Endpoint: `https://nominatim.openstreetmap.org/search`
- Usage policy: max 1 request/second, add `User-Agent` header
- Replaces: Google Geocoding API
- Env var: `NOMINATIM_BASE_URL=https://nominatim.openstreetmap.org`

### OSRM (Routing)
- No API key required — free public endpoint
- Endpoint: `http://router.project-osrm.org/route/v1`
- Provides: actual road travel time (replaces Routes API)
- SYNAPSE fallback: haversine formula (free, no quota, no API)
- Env var: `OSRM_BASE_URL=http://router.project-osrm.org`

### Overpass API (Places)
- No API key required — free public endpoint
- Endpoint: `https://overpass-api.de/api/interpreter`
- Used for: Nearby hospitals/facilities in volunteer task briefing
- Replaces: Google Places API

---

## OCR, Speech & Translation Setup

### pytesseract (Backend OCR)
- Open source — free, no API key
- Install: `pip install pytesseract --break-system-packages`
- Also install system dependency: `apt-get install tesseract-ocr tesseract-ocr-all`
- Supports: 12+ Indian scripts via `tesseract-ocr-all` language pack
- Handles: printed text; Gemini used for handwriting and structured extraction

### Tesseract.js (Frontend OCR)
- Runs in browser — no server round-trip needed for simple forms
- npm: `npm install tesseract.js`
- Used for: instant client-side preview before sending to backend

### OpenAI Whisper (local — Speech to Text)
- Open source — free, runs locally on Railway container
- Install: `pip install openai-whisper --break-system-packages`
- Model: `whisper-base` (good balance of speed and accuracy for Indian languages)
- Supports: 125+ languages including all Indian regional languages
- Used for: WhatsApp voice notes from field workers

### LibreTranslate (Translation)
- Open source — free self-hosted or free public endpoint
- Install: `pip install libretranslate --break-system-packages`
- Or use public endpoint: `https://libretranslate.com/translate`
- Used for: Field reports in regional languages → normalised English for scoring

---

## Firebase Setup (Spark Plan — Free)

> ⚠️ Do NOT upgrade to Blaze plan. Spark plan is sufficient for hackathon demo.
> Firebase Storage requires Blaze. We use Supabase Storage instead for all file storage.

### What to enable (in order):
1. **Firebase Console** → Create project "synapse-platform-prod"
2. **Authentication** → Sign-in methods:
   - Enable: Email/Password
   - Enable: Google
   - (Optional) Enable: Phone (for field worker OTP)
3. **Firestore Database** → Create in production mode → Region: `asia-south1` (Mumbai)
4. **Cloud Messaging** → Enabled by default (needed for volunteer FCM push)
5. **App Hosting** → Connect GitHub repo → auto-deploy on push to `main`

### Firestore Security Rules:
```
File: firebase/firestore.rules
```
Deploy: `firebase deploy --only firestore:rules`

### Firebase Admin SDK (backend):
```bash
pip install firebase-admin --break-system-packages
```
Credentials: Download service account JSON from Console → Project Settings → Service Accounts.
On Railway: set as environment variable `FIREBASE_CREDENTIALS_JSON` (JSON string).

### Environment variables (frontend):
```env
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=
```

---

## Supabase Storage Setup (Free — No Credit Card Required)

> **Why Supabase Storage and not Firebase Storage?**
> Firebase Storage requires the Blaze (pay-as-you-go) plan as of February 2026.
> Supabase's free tier provides 1GB storage + 2GB bandwidth/month. No card needed.
> We use Supabase Storage ONLY — not Supabase database (Firestore handles all data).

### Setup:
1. Sign up at [supabase.com](https://supabase.com) (free, no card)
2. Dashboard → Storage → Create buckets:
   - `synapse-surveys` (public: false)
   - `synapse-audio` (public: false)
   - `synapse-reports` (public: false)
3. API Keys tab → copy Project URL and anon/service_role key

### Environment variables:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
```

### Install (backend):
```bash
pip install supabase --break-system-packages
```

### Bucket structure in Supabase Storage:
- `synapse-surveys/` — field survey photos
- `synapse-audio/` — voice notes
- `synapse-reports/` — generated PDFs

---

## Google ADK — Agent Setup

### Install:
```bash
pip install google-adk --break-system-packages
pip install google-generativeai --break-system-packages
```

### How agents connect to Firestore and Gemini:
- Each agent file imports `from integrations.firebase import ...` and `from integrations.gemini import ...`
- Orchestrator receives events → dispatches to correct agent by event type
- Agents write results back to Firestore → Next.js real-time listeners update UI

### ADK config file:
```
services/api/adk_config.yaml
```

### Run locally:
```bash
cd services/api/src
adk run --config ../adk_config.yaml
```

### Deploy to Railway:
```bash
# Push to GitHub → Railway auto-deploys from main branch
# Or use Railway CLI:
railway up --service synapse-api
```

---

## Backend Python Dependencies

```bash
# requirements.txt
pip install fastapi uvicorn httpx firebase-admin google-generativeai \
  google-adk supabase pytesseract openai-whisper libretranslate \
  python-multipart python-dotenv \
  --break-system-packages
```

Full `requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.31.0
httpx==0.27.2
firebase-admin==6.5.0
google-generativeai==0.8.3
google-adk==1.0.0
supabase==2.5.0
pytesseract==0.3.10
openai-whisper==20231117
python-multipart==0.0.12
python-dotenv==1.0.1
resend==0.7.0
```

---

## Environment Variables — Complete List

```env
# .env (backend — services/api/.env)

# Gemini
GEMINI_API_KEY=

# Firebase Admin
FIREBASE_PROJECT_ID=synapse-platform-prod
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json   # dev only; Railway uses env var

# Supabase Storage
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key

# Maps & Location (no keys needed — all open source)
OSRM_BASE_URL=http://router.project-osrm.org
NOMINATIM_BASE_URL=https://nominatim.openstreetmap.org
OVERPASS_BASE_URL=https://overpass-api.de/api

# Email
RESEND_API_KEY=

# Translation
LIBRETRANSLATE_URL=https://libretranslate.com

# App
ENVIRONMENT=development
PORT=8080
LOG_LEVEL=INFO
WEB_APP_URL=http://localhost:3000
DONOR_APP_URL=http://localhost:3001

# Rural districts (comma-separated admin codes for 1.3x urgency boost)
RURAL_DISTRICT_CODES=KA-KODAGU,KA-CHIKMAGALUR,KA-SHIVAMOGGA
```

```env
# .env.local (Next.js frontend — apps/web/.env.local)
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=
NEXT_PUBLIC_API_URL=http://localhost:8080
# Note: no map API key needed — Leaflet uses OpenStreetMap tiles (free, no key)
```

---

## Branch & Deployment Summary

| Branch | Owner | Deployment |
|---|---|---|
| `main` | Stable only | Firebase App Hosting (auto-deploy) |
| `josna-dev` | Josna | Preview deployment on push |
| `ancilla-dev` | Ancilla | Preview deployment on push |

**Never work directly on `main`.** PR → review → merge.

---

## Demo Requirements Checklist

- [ ] `GEMINI_API_KEY` set and valid
- [ ] Firebase project created, Firestore rules deployed
- [ ] Supabase project created, buckets created, env vars populated
- [ ] `RESEND_API_KEY` set and valid
- [ ] Tesseract system package installed: `apt-get install tesseract-ocr tesseract-ocr-all`
- [ ] Whisper model downloaded: `python -c "import whisper; whisper.load_model('base')"`
- [ ] Seed data loaded: `python scripts/seed.py`
- [ ] GADM GeoJSON loaded: `python scripts/load_gadm.py`
- [ ] FastAPI running: `uvicorn main:app --host 0.0.0.0 --port 8080`
- [ ] Next.js running: `npm run dev` (port 3000)
- [ ] Donor portal running: `npm run dev` (port 3001)
- [ ] Test: upload survey photo → check Firestore → check map update
- [ ] Test: dispatch volunteer → verify FCM notification
- [ ] Test: complete outcome → verify urgency score update
