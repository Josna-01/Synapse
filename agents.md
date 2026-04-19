# agents.md — SYNAPSE Multi-Agent System
## Google ADK Configuration + Fallback Architecture

---

## Project Overview

**SYNAPSE** solves resource misallocation caused by poor visibility between NGOs, volunteers,
government authorities, and donors. Resources exist — coordination does not.

**Stack:** Google ADK · Gemini 2.0 Flash · Firebase · Cloud Run · FastAPI

---

## What is ADK?

ADK = Agent Development Kit

**Without ADK — traditional code:**
```
You write:
  1. call OCR
  2. call Gemini
  3. call Geocoding
  4. write to Firestore
  (you control every step, every condition)
```

**With ADK:**
```
You say: "Process this survey"
NGO Agent decides:
  → needs OCR first
  → then translation
  → then geocoding
  → then urgency scoring
  → then deduplication
  (agent figures out the steps, retries on failure, uses fallbacks)
```

ADK gives code a reasoning layer. The agent reads the goal, selects the right tools,
handles errors, and routes failures to fallback paths without you hardcoding every case.

**In SYNAPSE specifically:**
```
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

```
┌──────────────────────────────────────────────────────────┐
│               SYNAPSE ORCHESTRATOR AGENT                    │
│           (Routes all events to correct agent)           │
└──────┬───────────────┬────────────────┬──────────────────┘
       │               │                │               │
  ┌────▼───┐    ┌──────▼──┐    ┌────────▼─┐    ┌──────▼──────┐
  │  NGO   │    │VOLUNTEER│    │  GOVT    │    │   DONOR     │
  │ AGENT  │    │  AGENT  │    │  AGENT   │    │   AGENT     │
  └────────┘    └─────────┘    └──────────┘    └─────────────┘
       │               │                │               │
       └───────────────┴────────────────┴───────────────┘
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
- Survey photo (bytes)
- WhatsApp voice note (audio bytes)
- Web form submission (JSON)
- CSV upload (file)

### Output
- Structured `/needs/{id}` record in Firestore
- Urgency score (0-100) with breakdown and explanation
- Deduplication result (`{action: "merged"}` or `{action: "new", need_id}`)
- Dispatch trigger (if fast-track)
- Weekly coordinator digest

### Responsibilities
- OCR extraction from paper survey photos (Cloud Vision API + Document AI)
- WhatsApp voice note transcription (Cloud Speech-to-Text v2)
- Cross-language field report translation (Cloud Translation API v3)
- Address normalisation to lat/lng + admin boundary codes (Geocoding API v4)
- Cross-NGO deduplication (Gemini semantic similarity + geo radius check)
- Urgency scoring (Gemini-driven weighted formula)
- Volunteer match initiation
- Auto-generated donor impact reports (Gemini)
- Weekly coordinator digest (Gmail API)

### Example Flow
```
Field worker uploads photo of paper survey
    ↓
Cloud Vision API → extracts text
    ↓
Cloud Translation API → normalises to English
    ↓
Gemini NLP → extracts: location, category, affected_count, severity_hint
    ↓
Geocoding API → resolves to lat/lng + admin boundary code
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

```
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

```
PRIMARY:   Gemini 2.0 Flash NLP → weighted formula → 0-100
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

```
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

```
urgency_score >= 80                          → auto_dispatch (skip coordinator review)
category == health AND affected_count > 100  → auto_dispatch
category == disaster_relief                  → auto_dispatch + alert government
anomaly: 3σ spike vs 30-day baseline         → alert all orgs in region
```

### OCR Fallback

```
PRIMARY:   Cloud Vision API + Document AI → automatic field extraction
              ↓ (quota exhausted or confidence < 0.7)
SECONDARY: Return partial extraction results + flag for manual completion
           UI: show original photo left, editable form right
           source: "manual_fallback" stored in Firestore for audit
```

---

## Agent 2: Volunteer Agent

### Purpose
Matches the best volunteer to each need, manages task lifecycle, awards badges.

### Input
- Need record from Firestore (after urgency scoring)
- Volunteer pool from `/volunteers` collection
- Task outcome reports from `/outcomes`

### Output
- Top 3 volunteer matches with plain-language explanation
- FCM push notification to selected volunteer
- Task record in `/tasks/{id}`
- Badge evaluations and awards

### Responsibilities
- Volunteer matching (Routes API travel time + Gemini skill similarity)
- FCM push notifications with match explanation
- GPS check-in verification
- Task status lifecycle management (pending → accepted → in_progress → completed)
- Outcome report ingestion (feeds back to urgency model)
- Badge criteria evaluation and award

### Example Flow
```
Coordinator clicks "Find Volunteers" for need #1842
    ↓
Hard filter: available == true, hours_30d < 40, language match, schedule overlap
    ↓
Routes API: filter by actual travel time ≤ 90 minutes
    ↓
Gemini embeddings: cosine similarity of volunteer skills vs task requirements
    ↓
Composite ranking: skill_similarity(40%) + proximity(30%) + completion_rate(20%) + domain_boost(10%)
    ↓
Return top 3 with explanations: "91% skill match, 8 min away, available now"
    ↓
Coordinator selects → FCM push sent → volunteer accepts → task created
    ↓
GPS check-in → outcome form → badge evaluation → urgency recalibration
```

### Matching Algorithm

```
Step 1 — Hard filters:
  available == true
  hours_30d < 40  (burnout prevention)
  Routes API actual travel time <= 90 minutes
  language_required in volunteer.languages
  availability_slots overlap with task.scheduled_at

Step 2 — Composite ranking:
  match_score = (skill_similarity × 0.40)
              + (proximity_score × 0.30)
              + (completion_rate × 0.20)
              + (domain_experience_boost × 0.10)

  skill_similarity:   Gemini embedding cosine similarity (volunteer skills vs task requirements)
  proximity_score:    1 - (travel_time_mins / 90)
  completion_rate:    historical task completion rate from /outcomes
  domain_boost:       0.1 if need.category in volunteer.domains else 0

Step 3 — Return top 3 with plain-language explanation:
  "Matched: nurse skill (91%), 8 min away, available now."
```

### Matching Fallback

```
PRIMARY:   Routes API actual travel time + Gemini embedding cosine similarity
              ↓ (Routes API quota exhausted)
SECONDARY: Haversine straight-line distance formula
           R = 6371km
           distance = R × 2 × atan2(√a, √(1-a))
           Filter: distance ≤ 15km
           Label: match_source: "haversine_fallback"
           UI note: "~Xkm (straight-line estimate)"
              ↓ (volunteer location data unavailable)
TERTIARY:  Radius filter only — all volunteers within 15km regardless of skills
           Label: match_source: "radius_fallback"
              ↓ (no volunteers pass any filter)
QUATERNARY: Return all available volunteers
           Label: match_source: "accept_all_fallback"
           Note: "Coordinator should verify suitability"
```

### Notification Fallback

```
PRIMARY:   Firebase Cloud Messaging (FCM) push notification
              ↓ (FCM token expired or device offline)
SECONDARY: Email via Gmail API / Resend
              ↓ (email not available)
TERTIARY:  In-app notification flag in Firestore /notifications collection
           Shown on next dashboard load

All three channels store notification_channel: "fcm" | "email" | "in_app_fallback"
in the task record for audit and analytics.
```

### Badge System (20 badges across 7 categories)

```
FIRST ACTION:   first_report, first_task, first_donation
TASKS:          tasks_5 (bronze), tasks_25 (silver), tasks_100 (gold), tasks_500 (platinum)
HOURS:          hours_10 (bronze), hours_50 (silver), hours_200 (gold)
STREAK:         streak_7 (bronze), streak_30 (gold)
IMPACT:         people_100 (silver), people_1000 (gold)
DOMAIN:         water_specialist, health_specialist (domain-specific gold)
SPECIAL:        crisis_responder, top_rated, team_leader
```

---

## Agent 3: Government Agent

### Purpose
Aggregates district-level needs data, detects coverage gaps, matches government schemes,
generates weekly digests for officials.

### Input
- Aggregated `/needs` data by admin boundary
- Completed tasks and outcomes by ward
- Government scheme database (static + MyScheme API)
- District historical data

### Output
- District urgency aggregation per ward/block
- Coverage gap list (high need + zero activity)
- Scheme match alerts with deadlines
- Weekly Gemini-generated 2-page digest
- PDF export for official records

### Responsibilities
- District-level urgency aggregation per admin boundary
- Coverage gap detection (high need + zero NGO activity)
- Government scheme matching with application deadlines
- SDG alignment tagging per need cluster
- Weekly Gemini-generated digest (sent every Monday 6am)
- PDF export for official records

### Example Flow
```
Monday 6:00 AM cron trigger fires
    ↓
Read all /needs with created_at >= 7 days ago, grouped by admin2_code (district)
    ↓
For each ward: compute avg_urgency + count tasks in last 14 days
    ↓
Coverage gap detection: avg_urgency >= 60 AND tasks_14d == 0
    ↓
Scheme matching: need_category → aligned schemes with open deadlines
    ↓
Gemini 2.5 Pro generates 2-page district digest
    ↓
Gmail API sends digest to district officials at 6:00 AM local time
```

### Coverage Gap Detection

```
For each ward/block in district:
    avg_urgency = mean(needs.urgency_score) WHERE admin3_code = ward
    tasks_14d   = count(tasks) WHERE admin3_code = ward AND created_at >= 14 days ago

    IF avg_urgency >= 60 AND tasks_14d == 0:
        → COVERAGE GAP: "High need, zero NGO activity"
        → Add to government alert queue
        → Surface in district digest
```

### Scheme Matching Database

```
CATEGORY              SCHEME                        SOURCE
──────────────────────────────────────────────────────────────────────
water_sanitation  →   Jal Jeevan Mission            ejalshakti.gov.in
water_sanitation  →   Swachh Bharat Mission-G       sbmg.gov.in
food_security     →   PM-POSHAN (Mid Day Meal)       pmposhan.education.gov.in
food_security     →   Poshan Abhiyan                poshanabhiyaan.gov.in
health            →   Ayushman Bharat PMJAY          pmjay.gov.in
employment        →   MGNREGA                        nrega.nic.in
shelter           →   PMAY-G                         pmayg.nic.in
disaster_relief   →   SDRF/NDRF Activation           ndma.gov.in
```

### Weekly Digest (Gemini 2.5 Pro)

```
Prompt context sent to Gemini:
  - top 5 needs by urgency this week
  - coverage gaps list (ward + urgency + category)
  - pending scheme matches with deadlines
  - resolution rate this week vs last week
  - anomaly flags
  - fallback usage stats (how many scores were rule-based this week)

Output: 2-page official briefing in configurable language
        (Hindi for state officials, English for district collectors)
        Sent via Gmail API every Monday 6:00 AM local time
```

---

## Agent 4: Donor Agent

### Purpose
Computes verified impact chains, generates personalised donor reports, exports CSR compliance
documents, and tracks campaign progress.

### Input
- Completed task records from `/tasks`
- Outcome reports from `/outcomes`
- Donation records from `/donations`
- Campaign data from `/campaigns`

### Output
- Verified impact chain per donation
- Real-time campaign progress update
- Gemini-generated personalised impact narrative
- CSR compliance export (Section 80G + utilisation certificate)
- Monthly impact email digest

### Responsibilities
- Campaign card generation from linked need clusters
- Verified impact chain computation (donation → task → outcome)
- Real-time campaign progress tracking
- Gemini-generated personalised impact reports
- CSR compliance export (Section 80G + utilisation certificate)
- Monthly impact email digest

### Example Flow
```
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
Email sent: "Your ₹5,000 donation helped 280 families get clean water today."
    ↓
Impact chain stored in /impact_chains/{donation_id} for CSR audit
```

### Impact Chain (Verified, Not Estimated)

```
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

```
Input:  donor_id + period (e.g., "FY 2025-26")
Process: Gemini 2.5 Pro generates formal compliance document
Output:
  - Section 80G receipt
  - Utilisation certificate
  - Verified impact metrics (GPS-confirmed only)
  - NGO registration details
  - Certification statement
  Stored in Cloud Storage → signed URL → emailed to donor
```

---

## Agent 5: Orchestrator Agent

### Purpose
The single entry point for all incoming events. Reads the event type and routes to the
correct agent. Prevents agents from being called directly or out of order.

### Input
- Any incoming event: survey upload, volunteer action, weekly cron, donation, outcome

### Output
- Routed call to the correct agent
- Event log in `/agent_logs`

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

```
FIELD WORKER
    │ photo / voice / form / CSV
    ▼
[NGO AGENT]
    ├── Vision API → extract structured fields
    │   (fallback: manual entry form)
    ├── Speech-to-Text → transcribe voice
    ├── Translation → normalise language
    ├── Geocoding → resolve location
    │   (fallback: manual lat/lng)
    ├── Deduplication → merge or create
    ├── Urgency Score → 0-100 + explanation
    │   (fallback: rule-based → default 50)
    └── Write /needs/{id}
              │
              ├── IF fast-track (score≥80):
              │       [VOLUNTEER AGENT]
              │            ├── Routes API → filter by travel time
              │            │   (fallback: Haversine → radius → accept all)
              │            ├── Gemini → skill similarity ranking
              │            ├── FCM push → volunteer phone
              │            │   (fallback: email → in-app)
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
              │            └── Gmail sends to officials
              │
              └── ON TASK COMPLETION:
                      [DONOR AGENT]
                           ├── Impact chain computed
                           ├── Campaign people_helped counter incremented
                           ├── Gemini generates impact narrative
                           └── Email update to donors
```

---

## Why the Agent System is Powerful

1. **Autonomous decision-making**: Each agent decides its own processing steps based on
   the data it receives — no hardcoded conditional chains.

2. **Fault tolerance**: Each agent has fallback paths built in. If Gemini is down, the
   NGO Agent switches to rule-based scoring without requiring a code change or restart.

3. **Separation of concerns**: NGO Agent never touches donor logic. Donor Agent never
   touches government logic. Each agent has a single, clear responsibility.

4. **Composability**: The Orchestrator can call agents in any combination. Future agents
   (e.g., a Climate Agent or Media Agent) can be added by registering them in the routing
   map — no changes to existing agents.

5. **Auditability**: Every agent action is logged in `/agent_logs` with input, output,
   duration, and whether a fallback was used. Coordinators can see exactly how any
   decision was made.

6. **Hackathon alignment**: Google ADK is the core technology Solution Challenge 2026 is
   evaluating. Demonstrating a multi-agent system with real fallback logic and real Google
   API integrations shows production-level engineering judgment.

---

## ADK Configuration (adk_config.yaml)

```yaml
project_id: synapse-platform-prod
location: us-central1

agents:
  orchestrator:
    name: synapse_orchestrator
    model: gemini-2.0-flash
    max_iterations: 5

  ngo_agent:
    name: ngo_coordinator_agent
    model: gemini-2.0-flash
    human_in_loop: true      # Coordinator reviews before non-fast-track dispatch
    memory: true
    fallback_scoring: true   # Enable rule-based fallback

  volunteer_agent:
    name: volunteer_dispatch_agent
    model: gemini-2.0-flash
    memory: false
    fallback_matching: true  # Enable haversine fallback
    fallback_notify: true    # Enable email + in-app notification fallback

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
