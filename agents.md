# agents.md — SYNAPSE Multi-Agent System
## Google ADK Configuration + Fallback Architecture

---

## Project Overview
**SYNAPSE** solves resource misallocation caused by poor visibility between NGOs, volunteers, government authorities, and donors. Resources exist — coordination does not.

**Stack:** Google ADK · Gemini 2.5 Flash · Firebase · Railway.app · FastAPI

---

## What is ADK?
ADK = Agent Development Kit

**Without ADK — traditional code:**
```text
You write:
  1. call OCR
  2. call Gemini
  3. call Geocoding
  4. write to Firestore
  (you control every step, every condition)
```

**With ADK:**
```text
You say: "Process this survey"
NGO Agent decides:
  → needs OCR first
  → then translation
  → then geocoding
  → then urgency scoring
  → then deduplication
  (agent figures out the steps, retries on failure, uses fallbacks)
```

ADK gives code a reasoning layer. The agent reads the goal, selects the right tools, handles errors, and routes failures to fallback paths without you hardcoding every case.

**In SYNAPSE specifically:**
```text
SYNAPSE Orchestrator Agent
  reads incoming event
  decides which agent to call
        ↓
  ┌─────────────┐
  │  NGO Agent  │ → processes survey photos
  │             │   scores urgency (Gemini → rule-based → default)
  │             │   deduplicates needs
  └─────────────┘
        ↓
  ┌──────────────────┐
  │ Volunteer Agent  │ → matches volunteers
  │                  │   sends FCM push (→ email → in-app fallback)
  │                  │   awards badges
  └──────────────────┘
        ↓
  ┌─────────────┐
  │ Govt Agent  │ → weekly digest
  │             │   scheme matching
  └─────────────┘
        ↓
  ┌──────────────┐
  │ Donor Agent  │ → impact chain
  │              │   CSR reports
  └──────────────┘
```

Judges value ADK because it is the central technology the Solution Challenge is built around.

---

## Agent Architecture
```text
┌──────────────────────────────────────────────────────────┐
│               SYNAPSE ORCHESTRATOR AGENT                 │
│           (Routes all events to correct agent)           │
└──────┬───────────────┬────────────────┬──────────────────┘
       │               │                │                  │
  ┌────▼───┐    ┌──────▼──┐    ┌────────▼─┐    ┌──────▼──────┐
  │  NGO   │    │VOLUNTEER│    │  GOVT    │    │   DONOR     │
  │ AGENT  │    │  AGENT  │    │  AGENT   │    │   AGENT     │
  └────────┘    └─────────┘    └──────────┘    └─────────────┘
       │               │                │                  │
       └───────────────┴────────────────┴──────────────────┘
                                │
                   ┌────────────▼────────────┐
                   │   CLOUD FIRESTORE       │
                   │   (Shared data layer)   │
                   └─────────────────────────┘
```

---

## Agent 1: NGO Agent

### Purpose
Processes field data, scores urgency, deduplicates needs, and initiates volunteer dispatch.

### Input
*   Survey photo (bytes)
*   WhatsApp voice note (audio bytes)
*   Web form submission (JSON)
*   CSV upload (file)

### Output
*   Structured `/needs/{id}` record in Firestore
*   Urgency score (0-100) with breakdown and explanation
*   Deduplication result (`{action: "merged"}` or `{action: "new", need_id}`)
*   Dispatch trigger (if fast-track)
*   Weekly coordinator digest

### Responsibilities
*   OCR extraction from paper survey photos (pytesseract + Gemini)
*   WhatsApp voice note transcription (OpenAI Whisper — local, free)
*   Cross-language field report translation (LibreTranslate — free, open source)
*   Address normalisation to lat/lng + admin boundary codes (Nominatim API)
*   Cross-NGO deduplication (Gemini semantic similarity + geo radius check)
*   Urgency scoring (Gemini-driven weighted formula)
*   Volunteer match initiation
*   Auto-generated donor impact reports (Gemini)
*   Weekly coordinator digest (Resend)

### Example Flow
```text
Field worker uploads photo of paper survey
    ↓
pytesseract → extracts raw text
    ↓
LibreTranslate → normalises to English
    ↓
Gemini NLP → extracts: location, category, affected_count, severity_hint
    ↓
Nominatim API → resolves to lat/lng + admin boundary code
    ↓
Deduplication check → same category + 500m + 30-day window
    ↓
Urgency scoring → 0-100 + explanation
    ↓
Write /needs/{id} to Firestore
    ↓
IF score >= 80 → trigger Volunteer Agent auto-dispatch
ELSE          → appear in coordinator priority queue
```

### Urgency Scoring Formula
```text
score = (severity × 0.35) + (frequency × 0.25) + (recency_decay × 0.20) + (population × 0.20)

severity:        Gemini NLP classification of report text → 0-35 points
frequency:       count of same-category reports within 500m / 30 days → 0-25 points
recency_decay:   20 × e^(-0.1 × days_since_latest_report) → 0-20 points
population:      NASA SEDAC population density normalised to district → 0-20 points
rural_boost:     districts in bottom quartile remoteness index → final × 1.3 (cap 100)

Output: integer 0-100 + plain-language explanation
Levels: critical ≥80 | high 60-79 | moderate 40-59 | low <40
```

### Urgency Scoring Fallback
```text
PRIMARY:   Gemini 2.5 Flash NLP → weighted formula → 0-100
              ↓ (Gemini quota exhausted or unreachable)
SECONDARY: Rule-based keyword matching
           KEYWORDS:
             critical: ["death", "dying", "emergency", "flood", "fire", "cholera"]
             high:     ["water", "food", "hunger", "medicine", "sick", "shortage"]
             moderate: ["shelter", "school", "sanitation", "hygiene"]
             low:      ["support", "training", "awareness"]
           Base score: 85 / 65 / 45 / 20 based on highest keyword match
           +15 if affected_count > 500 | +10 if > 100
              ↓ (no keywords match or text is empty)
TERTIARY:  Default score = 50 (moderate) with flag: "requires_review: true"

All fallback results include: source: "rule_based_fallback" or "default_fallback"
```

### Deduplication Logic
```text
New need arrives
    │
    ├── Query /needs: same category + within 500m + within 30 days
    │
    ├── For each candidate:
    │       Gemini semantic similarity check
    │       Threshold: 0.85
    │
    ├── If duplicate found:
    │       Increment reports_count
    │       ARRAY_UNION source_orgs
    │       Update latest_report_at
    │       Return {action: "merged"}
    │
    └── If no duplicate:
            Write new /needs record
            Return {action: "new", need_id}
```

### Fast-Track Conditions
```text
urgency_score >= 80                          → auto_dispatch (skip coordinator review)
category == health AND affected_count > 100  → auto_dispatch
category == disaster_relief                  → auto_dispatch + alert government
anomaly: 3σ spike vs 30-day baseline         → alert all orgs in region
```

### OCR Fallback
```text
PRIMARY:   pytesseract (local) + Gemini → automatic field extraction
              ↓ (confidence < 0.7 or pytesseract fails)
SECONDARY: Return partial extraction results + flag for manual completion
           UI: show original photo left, editable form right
           source: "manual_fallback" stored in Firestore for audit
```

---

## Agent 2: Volunteer Agent

### Purpose
Matches the best volunteer to each need, manages task lifecycle, awards badges.

### Input
*   Need record from Firestore (after urgency scoring)
*   Volunteer pool from `/volunteers` collection
*   Task outcome reports from `/outcomes`

### Output
*   Top 3 volunteer matches with plain-language explanation
*   FCM push notification to selected volunteer
*   Task record in `/tasks/{id}`
*   Badge evaluations and awards

### Responsibilities
*   Volunteer matching (OSRM travel time + Gemini skill similarity)
*   FCM push notifications with match explanation
*   GPS check-in verification
*   Task status lifecycle management (pending → accepted → in_progress → completed)
*   Badge award evaluation on task completion
*   Outcome report processing + urgency score recalibration trigger

### Matching Formula
```text
match_score = (skill_similarity × 0.40) + (proximity_score × 0.30) +
              (completion_rate × 0.20) + (domain_boost × 0.10)

skill_similarity: Gemini text-embedding-004 cosine similarity
                  volunteer.skills ↔ need.required_skills
proximity_score:  OSRM actual road travel time → converted to 0-30 score
                  fallback: haversine straight-line km → 0-30 score
completion_rate:  historical task completion % → 0-20
domain_boost:     +10 if volunteer has domain badge (water, health, education, etc.)
```

### Volunteer Matching Fallback
```text
PRIMARY:   OSRM travel time + Gemini skill embeddings
              ↓ (OSRM timeout or unreachable)
FALLBACK 1: Haversine straight-line distance + Gemini skill embeddings
              ↓ (Gemini embeddings unavailable)
FALLBACK 2: Haversine distance only → filter radius 5km → sort by completion_rate
              ↓ (no volunteers in radius)
FALLBACK 3: Expand radius to 15km → accept all available volunteers

source field: "osrm_match" | "haversine_match" | "radius_match" | "all_available"
```

### Notification Fallback
```text
PRIMARY:   FCM push to volunteer device token
              ↓ (FCM token expired or delivery failed)
FALLBACK 1: Email via Resend → volunteer.email
              ↓ (email delivery failed)
FALLBACK 2: In-app notification: write to /notifications/{volunteer_id}
            → Firestore real-time listener triggers app badge
```

### Badge System
**20 badges across 7 categories:**
*   **Tasks:**     First Response, Quick Responder, Hundred Club
*   **Hours:**     Dawn Patrol, Night Owl, Weekend Warrior
*   **Streak:**    7-Day Streak, 30-Day Streak, Unbreakable
*   **Impact:**    Lifesaver, Community Champion, District Hero
*   **Domain:**    Water Guardian, Health Champion, Education Advocate
*   **Teams:**     Collaborator, Bridge Builder
*   **Skills:**    All-Rounder, Specialist

**Level progression:**
```text
Newcomer (0-5 tasks) → Helper (6-15) → Responder (16-30)
→ Champion (31-50) → Hero (51-100) → Legend (100+)
```

---

## Agent 3: Government Agent

### Purpose
Aggregates district-level need data, detects coverage gaps, matches government schemes, and generates weekly intelligence digests for district officials.

### Input
*   All `/needs` records in Firestore (read-only)
*   District boundary codes from need records
*   Scheme database (static JSON + Firestore `/schemes` collection)

### Output
*   Aggregated district need summary
*   Coverage gap alerts (high need + zero NGO activity)
*   Scheme alignment suggestions
*   Gemini-generated weekly digest (PDF)
*   Email delivery via Resend to district officials

### Responsibilities
*   District-level needs aggregation by admin boundary code
*   Coverage gap detection: `avg_urgency ≥ 60` + zero tasks assigned in 14 days
*   Government scheme alignment (Jal Jeevan, PM-POSHAN, MGNREGA, etc.)
*   SDG tag mapping per need cluster
*   Weekly Gemini 2.5 Pro digest generation
*   Resend delivery to configured district email list

### Example Flow
```text
Monday 6am — scheduled cron trigger
    ↓
Government Agent wakes
    ↓
Reads all /needs records from past 7 days (Firestore)
    ↓
Groups by admin_boundary_code (district/block level)
    ↓
For each district:
    avg_urgency, total_needs, total_tasks, coverage_ratio
    ↓
Coverage gap detection:
    avg_urgency >= 60 AND tasks_assigned_last_14_days == 0
    → flag as "uncovered_high_need"
    ↓
Scheme matching:
    need.category == "water" → Jal Jeevan Mission
    need.category == "food"  → PM-POSHAN
    need.category == "work"  → MGNREGA
    ↓
Gemini 2.5 Pro → generate 2-page official briefing
    ↓
Resend → email to district_emails list
    ↓
Write /digests/{week_id} to Firestore → available on govt dashboard
```

### Choropleth Map Data
GeoJSON GADM district boundaries loaded as static file:
`public/geojson/india_districts.geojson`

Leaflet renders choropleth by joining Firestore urgency data with GeoJSON features using `admin_boundary_code` as the join key.

*No external map dataset API required.*

---

## Agent 4: Donor Agent

### Purpose
Computes verified impact chains, generates personalised donor reports, exports CSR compliance documents, and tracks campaign progress.

### Input
*   Completed task records from `/tasks`
*   Outcome reports from `/outcomes`
*   Donation records from `/donations`
*   Campaign data from `/campaigns`

### Output
*   Verified impact chain per donation
*   Real-time campaign progress update
*   Gemini-generated personalised impact narrative
*   CSR compliance export (Section 80G + utilisation certificate)
*   Monthly impact email digest

### Responsibilities
*   Campaign card generation from linked need clusters
*   Verified impact chain computation (donation → task → outcome)
*   Real-time campaign progress tracking
*   Gemini-generated personalised impact reports
*   CSR compliance export (Section 80G + utilisation certificate)
*   Monthly impact email digest

### Example Flow
```text
Volunteer submits outcome form: resolved ✓, 280 families, rating 4.9/5
    ↓
/outcomes/{task_id} written to Firestore
    ↓
Donor Agent listens on Firestore trigger
    ↓
Finds all donations linked to this task's campaign
    ↓
Computes impact chain:
  donation_id → campaign_id → need_cluster_id → task_id → outcome_id
    ↓
Increments campaign.people_helped by outcome.people_helped
    ↓
Gemini generates personalised impact narrative for each donor
    ↓
Resend email: "Your ₹5,000 donation helped 280 families get clean water today."
    ↓
Impact chain stored in /impact_chains/{donation_id} for CSR audit
```

### Impact Chain (Verified, Not Estimated)
```text
Donation received
    │
    ├── Linked to campaign
    │
    ├── Campaign linked to need_cluster_id
    │
    ├── need_cluster → tasks (status: completed)
    │
    ├── tasks → outcomes
    │       outcome.resolved == true
    │       outcome.gps_checkin_verified == true
    │       outcome.people_helped (number)
    │
    └── Chain stored in /impact_chains/{donation_id}
        Shown on donor portal as traceable evidence
```

### CSR Report Generation
```text
Input:  donor_id + period (e.g., "FY 2025-26")
Process: Gemini 2.5 Pro generates formal compliance document
Output:
  - Section 80G receipt
  - Utilisation certificate
  - Verified impact metrics (GPS-confirmed only)
  - NGO registration details
  - Certification statement
  Stored in Supabase Storage → signed URL → emailed to donor via Resend
```

---

## Agent 5: Orchestrator Agent

### Purpose
The single entry point for all incoming events. Reads the event type and routes to the correct agent. Prevents agents from being called directly or out of order.

### Input
*   Any incoming event: survey upload, volunteer action, weekly cron, donation, outcome

### Output
*   Routed call to the correct agent
*   Event log in `/agent_logs`

### Example Routing Logic
```python
# services/api/src/agents/orchestrator.py

async def route_event(event: dict) -> dict:
    event_type = event.get("type")

    routing_map = {
        "survey_upload":      ngo_agent.process_survey,
        "voice_note":         ngo_agent.process_voice,
        "need_created":       ngo_agent.score_and_deduplicate,
        "dispatch_requested": volunteer_agent.find_matches,
        "task_accepted":      volunteer_agent.update_task_status,
        "task_completed":     volunteer_agent.process_outcome,
        "weekly_digest":      govt_agent.generate_digest,
        "donation_received":  donor_agent.link_donation,
        "outcome_submitted":  donor_agent.update_impact_chain,
    }

    handler = routing_map.get(event_type)
    if not handler:
        await log_agent_event("orchestrator", "unrouted_event", event)
        return {"status": "unrouted", "event_type": event_type}

    result = await handler(event)
    await log_agent_event("orchestrator", event_type, event, result)
    return result
```

---

## Data Flow Between All Agents
```text
FIELD WORKER
    │ photo / voice / form / CSV
    ▼
[NGO AGENT]
    ├── pytesseract → extract text from photo
    │   (fallback: manual entry form)
    ├── Whisper → transcribe voice note
    ├── LibreTranslate → normalise language
    ├── Nominatim → resolve location to lat/lng
    │   (fallback: manual lat/lng entry)
    ├── Deduplication → merge or create
    ├── Urgency Score → 0-100 + explanation
    │   (fallback: rule-based → default 50)
    └── Write /needs/{id}
              │
              ├── IF fast-track (score≥80):
              │       [VOLUNTEER AGENT]
              │            ├── OSRM → filter by travel time
              │            │   (fallback: Haversine → radius → accept all)
              │            ├── Gemini → skill similarity ranking
              │            ├── FCM push → volunteer phone
              │            │   (fallback: Resend email → in-app)
              │            ├── Accept → write /tasks/{id}
              │            ├── Check-in → update /tasks/{id}
              │            ├── Outcome form → write /outcomes/{id}
              │            └── Badge evaluation → update /volunteers/{id}
              │                        │
              │                        └── outcome feeds back:
              │                            urgency score recalibrated
              │
              ├── WEEKLY TRIGGER (Monday 6am):
              │       [GOVT AGENT]
              │            ├── Read /needs aggregate by district
              │            ├── Detect coverage gaps
              │            ├── Match schemes
              │            ├── Gemini generates digest
              │            └── Resend delivers to officials
              │
              └── ON TASK COMPLETION:
                      [DONOR AGENT]
                           ├── Impact chain computed
                           ├── Campaign people_helped counter incremented
                           ├── Gemini generates impact narrative
                           └── Resend email update to donors
```

---

## Why the Agent System is Powerful
1.  **Autonomous decision-making**: Each agent decides its own processing steps based on the data it receives — no hardcoded conditional chains.
2.  **Fault tolerance**: Each agent has fallback paths built in. If Gemini is down, the NGO Agent switches to rule-based scoring without requiring a code change or restart.
3.  **Separation of concerns**: NGO Agent never touches donor logic. Donor Agent never touches government logic. Each agent has a single, clear responsibility.
4.  **Composability**: The Orchestrator can call agents in any combination. Future agents (e.g., a Climate Agent or Media Agent) can be added by registering them in the routing map — no changes to existing agents.
5.  **Auditability**: Every agent action is logged in `/agent_logs` with input, output, duration, and whether a fallback was used. Coordinators can see exactly how any decision was made.
6.  **Hackathon alignment**: Google ADK is the core technology Solution Challenge 2026 is evaluating. Demonstrating a multi-agent system with real fallback logic and real Google API integrations shows production-level engineering judgment.

---

## ADK Configuration (adk_config.yaml)
```yaml
project_id: synapse-platform-prod
location: us-central1

agents:
  orchestrator:
    name: synapse_orchestrator
    model: gemini-2.5-flash
    max_iterations: 5

  ngo_agent:
    name: ngo_coordinator_agent
    model: gemini-2.5-flash
    human_in_loop: true      # Coordinator reviews before non-fast-track dispatch
    memory: true
    fallback_scoring: true   # Enable rule-based fallback

  volunteer_agent:
    name: volunteer_dispatch_agent
    model: gemini-2.5-flash
    memory: false
    fallback_matching: true  # Enable haversine fallback when OSRM unavailable
    fallback_notify: true    # Enable Resend email + in-app notification fallback

  govt_agent:
    name: government_intelligence_agent
    model: gemini-2.5-pro    # Complex digest generation
    schedule: "0 6 * * MON"

  donor_agent:
    name: donor_impact_agent
    model: gemini-2.5-pro    # CSR report generation
    memory: true

mcp_servers:
  - name: firestore-mcp
    type: url
    url: https://firestore.googleapis.com/mcp/v1
  - name: drive-mcp
    type: url
    url: https://drivemcp.googleapis.com/mcp/v1
```
