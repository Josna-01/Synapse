# SYNAPSE — Stitch UI Generation Prompts
## 4 Professional Dashboard Prompts with Connected Data Flow

---

## HOW TO USE THESE PROMPTS

1. Go to stitch.withgoogle.com
2. Select **Gemini 2.5 Pro (Experimental)** mode
3. Select **Web** as platform
4. Paste ONE prompt at a time — one screen per prompt
5. After generation: use ONE follow-up refinement per iteration
6. Screenshot every successful generation before iterating

---

## DATA CONNECTIONS (READ THIS FIRST)

All 4 dashboards share ONE Firestore database. The data flow is:

```
FIELD WORKER submits report
    → /needs/{id} written to Firestore
    → NGO DASHBOARD shows it on Leaflet heatmap (live listener)
    → NGO COORDINATOR dispatches volunteer
    → /tasks/{id} written
    → VOLUNTEER APP receives FCM push (live update)
        (fallback: Resend email notification if FCM fails)
        (fallback: in-app Firestore notification if email fails)
    → Volunteer accepts → task status updates
    → NGO DASHBOARD shows "Assigned"
    → Volunteer completes → /outcomes/{id} written
    → GOVT DASHBOARD: district urgency score updates on choropleth
    → DONOR PORTAL: campaign people_helped count increments
```

This means: one action in one dashboard immediately affects all other dashboards.
Design every screen with live data in mind — no static states.

### Fallback State Indicators

Every dashboard should visually indicate when fallback mode is active:
- A small amber chip "AI scoring unavailable — rule-based mode" when Gemini is down
- A muted label "Straight-line distance (OSRM unavailable)" on volunteer cards
- A yellow banner "Notification sent via email (FCM unavailable)" on dispatch confirmation
- Fallback states are informational — they never block coordinator actions

---

## PROMPT 1: NGO COORDINATOR DASHBOARD

### Context for Stitch
This is a web dashboard used by NGO coordinators to monitor community needs in real time,
triage by urgency, dispatch volunteers, and generate donor reports. It must look like a
professional humanitarian operations tool — think OCHA ReliefWeb meets Stripe Dashboard.
The map uses Leaflet + OpenStreetMap tiles (not Google Maps). Design the map area to look
like a dark-styled OpenStreetMap tile layer.

### Stitch Prompt

---

Design a professional web dashboard for an NGO humanitarian coordinator.

Platform: Web, desktop-first. Full-width layout.

Audience: NGO coordinators managing multiple community needs simultaneously. They are
time-poor, technically literate, and need to make triage decisions quickly.

Visual style: Authoritative, calm, institutional. No gradients. No decorative elements.
Primary colour: Deep navy #0D2B4E. Accent: Teal #0F6E56. Critical alerts: Red #DC2626.
High urgency: Amber #D97706. Background: #F8F9FC. Card background: white.
Typography: DM Sans, clean sans-serif. No All Caps except navigation section labels.

Layout:
- Fixed 240px dark-navy left sidebar
- 60px white topbar (org name left, search bar centre, alert bell + user chip right)
- Main content area with 28px 32px padding, max-width 1440px

Sidebar content (top to bottom):
- SYNAPSE logo with teal lightning bolt icon, "Intelligence Platform" subtitle in teal
- Green pulsing dot with "Live — 847 active needs" in small muted text
- Navigation sections with 10px uppercase muted section labels:
  OPERATIONS: Dashboard (active, teal left border), Heatmap, Submit Report
  PEOPLE: Volunteer Dispatch, Inter-NGO Network
  INTELLIGENCE: Analytics, AI Agents, Scheme Matcher
- Bottom section: Alerts (with red "3" badge), Settings
- User profile chip: avatar initials circle, name "Amara Osei", role "Field Coordinator"

Main content:

Section 1 — Page header row:
Left: "Command Dashboard" 22px medium, "Real-time intelligence across all regions" subtitle
Right: "Filter" button (outline), "Export" button (outline), "+ Submit Report" button (dark navy fill)

Section 2 — Alert banner (appears when critical):
Red strip with thin red left border: "CRITICAL: Cholera risk — Cox's Bazar, 12,000 at risk"
Amber strip: "ANOMALY: 3x surge in food reports — Northern Mali"
Each has a View button and X dismiss button on the right.

Section 2B — Fallback status bar (shown when any API is degraded):
Thin amber bar below alert banners, only visible when needed:
"⚠ AI scoring unavailable — urgency estimates are rule-based. [Learn more]"
Dismissible per session. Never blocks workflow.

Section 3 — KPI stats row (4 equal cards):
Card 1: label "Active Needs" (muted 11px uppercase), value "847" (28px semibold),
        red badge chip "23 critical", trend arrow ▲12.4% in small teal text
Card 2: label "Volunteers Online", value "1,204", green badge chip "available now", trend ▲8.1%
Card 3: label "Tasks In Progress", value "312", amber badge chip "28 regions", trend ▼3.2%
Card 4: label "Resolved (30d)", value "2,891", teal badge chip "verified outcomes", trend ▲18.7%

Section 4 — Quick actions row (4 equal cards):
Each card: small icon + bold label + grey description + right arrow
Cards: "Submit Report" / "Dispatch Volunteer" / "Start Campaign" / "Run AI Agent"

Section 5 — Main content grid (5 columns total):
Left 3 columns — "Needs Heatmap" card:
  - Card header with "Needs Heatmap" label and green pulsing live dot
  - "View full map →" link top right
  - Map area: OpenStreetMap tile layer (light grey tile style) showing a region of India
  - Heatmap markers: coloured circles — red = critical urgency (≥80), amber = high (60-79),
    teal = moderate (<60). Circles have semi-transparent fill matching urgency colour.
  - Map attribution at bottom-right: "© OpenStreetMap contributors"
  - Map legend bottom-left: three coloured circles + labels "Critical / High / Moderate"
  - Category filter pills below map: "All / Water / Health / Food / Shelter"

Right 2 columns — "Priority Queue" card:
  - Card header: "Priority Queue" left, "Sorted by urgency" right in muted text
  - Below header: small filter pills "All / Water / Health / Food"
  - List of 6 need items. Each item:
    * Left: SVG progress ring (circle) showing urgency score 0-100, number inside
      ring colour matches urgency level (red/amber/teal)
    * Right of ring: need title in 13px medium, location in 11px grey below
    * Bottom row: category pill (small, coloured background) + "X reports · Yh ago"
    * Item has coloured left border: red for critical, amber for high, teal for moderate
    * Hover state: "Dispatch" button appears on right
    * Small source chip if fallback: "Rule-based" in muted amber if Gemini unavailable
  - Bottom: "View all 847 active needs →" teal link

Section 6 — Bottom grid (2:1 ratio):
Left — "Live Activity" card:
  Timeline of events. Each event:
  Small coloured icon circle (emoji inside) + message text + actor name + time
  Example entries: ⚡ dispatch, 📝 new report, ✅ resolved, 💙 campaign, 🔔 anomaly
  Include example: "⚠ Email fallback used for volunteer Priya Kumar (FCM offline)"

Right — "NGO Network" card:
  "Active organisations" subtitle
  List of 5 orgs: coloured 2-letter avatar + org name + "X needs · Y volunteers"
  Thin dividers between rows

Data connections from this dashboard to others:
- When coordinator dispatches a volunteer here → Volunteer App receives FCM notification
  (or Resend email if FCM fails, or in-app flag if email fails)
- When outcome is submitted by volunteer → Priority queue urgency score updates here
- When scheme match is found → Government dashboard surfaces the same alert
- When donor report is generated here → Donor portal shows new campaign impact data

---

### Follow-up refinement prompts (use one at a time after first generation):
- "Add a live pulsing indicator on the map showing the most recently added need pin."
- "Make the priority queue items show a volunteer count chip and a 'Dispatch' button on hover with teal background."
- "Change the KPI cards to show a small sparkline chart below each trend percentage."
- "Add a muted 'source: rule-based' chip to urgency scores computed without Gemini."

---

## PROMPT 2: VOLUNTEER MOBILE APP

### Context for Stitch
Flutter mobile app used by volunteers to receive task notifications, view task context,
navigate to location, check in via GPS, and submit outcome reports. The design should be
warmer and more personal than the coordinator dashboard, but still professional.
The map uses flutter_map with OpenStreetMap tiles (not Google Maps).

### Stitch Prompt

---

Design a mobile app interface for a humanitarian volunteer.

Platform: Mobile (Flutter), iOS and Android. Portrait orientation. 390px width.

Audience: Volunteers aged 20-45 who want to help their community. They receive push
notifications and need to act quickly. Interface should feel action-oriented but human.

Visual style: Clean, warm, professional. Primary: Teal #0F6E56. Secondary: Navy #0D2B4E.
Urgency colours: Red #DC2626 (critical), Amber #D97706 (high), Teal (moderate).
Background: white. Material 3 design system. Generous touch targets (minimum 48px).

Show FOUR screens in a 2x2 grid:

SCREEN 1 — Tasks Home (default landing screen):
Top: App bar with "SYNAPSE" title, notification bell icon (badge "2"), user avatar
Below app bar: Full-width OpenStreetMap tile map view showing volunteer's neighbourhood
  Map pins: coloured circles (red/amber/teal by urgency), volunteer location as blue dot
  Each pin shows category icon
  Map attribution: "© OpenStreetMap contributors"
Swipeable bottom sheet (mid-position):
  "3 tasks near you" header with distance filter "Within 5 km ▾"
  Category filter chips: All · Water · Health · Food · Shelter
  Task list items (3 visible):
    Each: urgency score badge (circle, coloured) + task title + location line + "X km away"
    "Accept" button on right (small teal pill)
    Small muted note if haversine fallback: "~Xkm (est.)" instead of exact distance
Welcome strip (teal background strip at top): "Good morning. 3 urgent tasks match your skills."

SCREEN 2 — Task Detail:
Top: back arrow + "Task #1842"
Urgency section: large red "87" score circle (40px), title "Acute water shortage",
  location "Ward 6, Accra", three chips: "Water & Sanitation" | "Critical" | "47 reports"
"Why you were matched" card (light navy background):
  Star icon + "91% skill match"
  Three rows: ✓ Nurse skill matches task | ✓ 1.2km away | ✓ Available today
  Small note if fallback used: "Distance estimated (straight-line)"
What's needed card: task description text, bullet points of actions
When & where card: date/time + embedded mini OpenStreetMap + "Get directions →"
Bottom sticky bar (white, border top): "Pass" ghost button left + "Accept Task" large teal button right

SCREEN 3 — Active Task (volunteer en route / on site):
Progress indicator at top: three steps [Accept ✓] → [Check In ○] → [Complete ○]
Large embedded OpenStreetMap showing route from volunteer to task location
  Route line drawn on map (OSRM routing if available, straight line if fallback)
Task title bar below map: "Water shortage — Ward 6"
Large prominent "GPS Check In" button (full width, teal fill, 56px height)
  Below it: "Tap when you arrive at the location"
Status chip: "In Progress · Accepted 24 min ago"
"Contact coordinator" button (outline, small) at bottom

SCREEN 4 — Badges Tab:
Header: "Achievements" with subtitle "Your impact, recognised"
Level banner: [Champion ⚡] progress bar showing 2,100/4,000 points to next level "Hero"
Earned badge grid (3 columns, coloured cards with checkmark):
  First Responder 🚀 · Ten Hour Club ⏱ · Community Impact 👥 · Water Guardian 💧
Locked badge section (greyed out, 50% opacity):
  Shows progress ring around locked badges: "Health Hero — 7/10 health tasks"
Impact stats below: 142 hrs · 31 tasks · 1,240 people helped

Bottom navigation bar: Tasks · Map · Impact · Badges · Profile

Data connections from this app to others:
- FCM notification received here is triggered by coordinator dispatch on NGO Dashboard
  (if FCM fails, volunteer also gets a Resend email; if email fails, notification queues in-app)
- GPS check-in event here updates task status on NGO coordinator's task board
- Outcome form submission here triggers donor portal impact count update
- Badge earned here is visible on volunteer's public profile

---

### Follow-up refinement prompts (use one at a time):
- "Make the FCM notification mockup more prominent — show it as a lock screen notification at the top of Screen 1."
- "Add a burn-out indicator on the Profile screen showing '38/40 hours this month — take a break soon'."
- "Make the badge cards have a subtle glow effect on earned badges and a lock icon on locked ones."
- "Show a small amber chip 'Distance estimated' when haversine fallback is active on task cards."

---

## PROMPT 3: GOVERNMENT / ADMIN DASHBOARD

### Context for Stitch
Web dashboard for district collectors and government officials. Read-only view of
aggregated community needs, coverage gaps, and scheme alignment opportunities. Looks like
a World Bank or UN data portal — authoritative, data-dense, policy-oriented.
The choropleth map uses Leaflet + GeoJSON GADM polygon overlays (not Google Maps Datasets API).
Design the map to show coloured district polygons on an OpenStreetMap base layer.

### Stitch Prompt

---

Design a professional government district administration dashboard.

Platform: Web, desktop-first.

Audience: District collectors, government planning officials. They check this weekly, not
daily. They need a briefing-style interface that tells them where to direct policy attention.

Visual style: Authoritative institutional design. More subdued than the NGO dashboard.
Primary: Navy #0D2B4E. Accent: Purple #534AB7 (government, different from NGO's teal).
Background: white. No decorative elements. Think World Bank Open Data dashboard aesthetic.

Layout: Same sidebar structure as NGO dashboard but with different navigation items.

Sidebar navigation:
  MONITORING: District Overview (active), Heatmap View
  INTELLIGENCE: Coverage Gaps, Scheme Matcher, Cross-NGO Overview
  REPORTS: Weekly Digest, PDF Export, Historical Trends

Main content:

Section 1 — Header:
Left: "District Intelligence — Mysuru District, Karnataka" title
Right: District selector dropdown, "Download PDF" button, "Last updated: 2 min ago" muted

Section 2 — District KPI row (5 cards, slightly smaller):
Active Needs: 234 | Avg Urgency Score: 71.2 | Coverage Gaps: 8 wards |
NGOs Active: 12 | Resolution Rate: 58% this week

Section 3 — Main grid (60/40 split):

Left 60% — Choropleth District Map:
  OpenStreetMap base layer showing Mysuru district divided into blocks/wards
  Ward polygons (GeoJSON overlays) filled by urgency colour:
    deep red (critical ≥80), amber (high 60-79), light teal (moderate/improving <60)
  "Coverage Gap" wards marked with a warning pattern overlay (hatching or diagonal lines)
  Map attribution: "© OpenStreetMap contributors"
  Map controls: zoom + / -, layer toggle (Urgency / NGO Activity / Coverage Gaps)
  Map legend: urgency colour scale + "Coverage gap" explanation
  Click a ward → tooltip card:
    "Ayawaso West Ward 6 · Avg urgency: 87 · NGO activity: None in 14 days · Top need: Water"
    Two buttons: "Flag for review" | "View full detail"

Right 40% — split into two stacked panels:

Top panel — "Coverage Gaps" (most important government feature):
  Heading: "High need, zero NGO activity" with red badge "8 wards"
  Explanation text: "These areas have documented needs but no volunteer activity in 14 days."
  List of 5 gaps:
    Each row: ward name + top category chip + urgency score + "X days without coverage"
    Red urgency indicator on left border
    "Flag" button on right
  "This visualisation exists nowhere else" — make it visually prominent

Bottom panel — "Scheme Alignment":
  Heading: "Active funding opportunities"
  Table with columns: Need Category | Scheme Name | Status | Deadline
  3 rows example:
    Water & Sanitation | Jal Jeevan Mission | Open | 18 days
    Food Security | PM-POSHAN | Open | Rolling
    Health | Ayushman Bharat | Open | Rolling
  Each row: "View scheme →" link and "Flag for action" button
  Bottom: "Powered by MyScheme.gov.in" attribution

Section 4 — Bottom row (full width):

"Weekly Digest" card (Gemini-generated):
  Header with date "Week of April 7-14, 2026"
  Preview of Gemini digest text (2 paragraphs, formal tone):
    "This week, Ayawaso West district recorded its highest urgency average in 30 days..."
  "Download Full PDF" navy button + "View Online" ghost button
  Chip: "Generated by Gemini 2.5 Pro · Sent Monday 6:00 AM via Resend"
  Note: Small muted note showing digest data source — "Computed from 234 verified need records"

"Cross-NGO Overview" mini-table:
  Columns: Organisation | Active Needs | Volunteers | Districts Covered | Resolution Rate
  5 rows of NGO data

Data connections from this dashboard to others:
- District urgency data here is computed from /needs written by NGO coordinators
- Coverage gaps update in real time when NGO coordinators dispatch volunteers
- Scheme matches here are surfaced to NGO coordinators as suggestions on their dashboard
- Weekly digest data comes from the same Firestore database all other dashboards read
- Urgency scores shown here include source label (Gemini / rule-based) for auditability

---

### Follow-up refinement prompts:
- "Make the coverage gap list items expandable — clicking a gap shows the specific needs in that ward."
- "Add a trend indicator on the choropleth map showing whether each ward is improving or worsening week-on-week."
- "Add a 'Compare districts' feature allowing officials to view two districts side by side."

---

## PROMPT 4: DONOR / FUNDRAISER PORTAL

### Context for Stitch
Web portal for donors and CSR teams. Warmer and more emotionally resonant than the
coordinator dashboard. Must build trust through verified impact evidence, not just numbers.

### Stitch Prompt

---

Design a professional donor portal for a humanitarian fundraising platform.

Platform: Web, desktop-first. Warmer, more consumer-facing than the NGO coordinator dashboard.

Audience: Individual donors, corporate CSR managers, philanthropists. They need to trust
that their money is reaching the right place. Trust signals are more important than
feature density. Make it feel like a premium, transparent giving platform.

Visual style: Warm white. Amber accent #D97706 (distinct from NGO teal and Govt purple).
Display font: DM Serif Display for campaign headings (emotional). Body: DM Sans.
No sidebar — top navigation only. Clean, generous whitespace. 3-column grid layout.

Top navigation:
  Left: SYNAPSE logo + "Donor Portal" label
  Centre: Browse Campaigns · My Impact · How It Works
  Right: "Login" ghost button + "Donate Now" amber fill button

Hero banner (full width, navy background, white text):
  Headline in DM Serif Display: "Every rupee, traceable."
  Subtitle: "See exactly where your contribution goes — GPS verified, outcome confirmed."
  Two stats prominently: "₹24.7L raised · 2,891 people helped (verified)"
  CTA button: "Browse Active Campaigns" (amber fill)

Section 1 — "Featured Campaigns" (3-column grid):

Each campaign card:
  Cover image area (solid colour block if no image) with category badge top-left
  ✓ Verified shield badge top-right (teal, if NGO is verified)
  Campaign title in DM Serif Display, 16px
  Organisation name in muted text
  Progress bar: raised amount / goal amount, percentage label
    Bar colour: teal fill, grey track. "₹17,800 of ₹25,000 raised"
  "X days left" badge + "Y donors" count
  "Impact so far" row: people helped number (from verified outcomes — NOT estimates)
    Small note: "Verified from 3 completed tasks · GPS confirmed"
  Large "Donate" button (amber fill, full width, bottom of card)

Show 3 cards:
  1. "Clean Water for Ayawaso West" — Water & Sanitation — 71% funded — 312 people helped
  2. "Emergency Health Response Cox's Bazar" — Health — 76% funded — 891 donors
  3. "Flood Relief Sylhet Families" — Shelter — 57% funded — 1,204 donors

Section 2 — "How Your Donation Works" (trust builder):
Full-width section, light grey background
Heading: "The impact chain — from donation to verified outcome"

5-step horizontal flow (connected by arrows):
  1 💳 Your donation → 2 📋 Campaign → 3 🧑‍🤝‍🧑 Volunteer dispatched →
  4 📍 GPS check-in → 5 ✅ Outcome verified

Below the flow: "Every link is confirmed, not estimated. You receive an update at each step."
Small note: "If a step cannot be automatically verified, a coordinator manually confirms it."

Section 3 — Impact numbers (4 metric cards, teal accent):
₹24.7L total raised | 2,891 people helped (verified) | 312 tasks completed | 48 NGO partners

Section 4 — "For Corporate Donors" (CSR section):
Two-column: left text, right visual

Left column:
  Heading: "CSR compliance made simple"
  Body: Explain Section 80G receipts, utilisation certificates, verified impact reports
  Feature bullets:
    ✓ Section 80G receipt with every donation
    ✓ GPS-verified impact reports for board presentations
    ✓ One-click export for annual CSR filing
    ✓ Campaign portfolio view across all giving
  "Schedule a CSR Demo" navy button

Right column:
  Mock PDF report preview card showing:
    "SYNAPSE CSR Impact Report · Q4 2025-26"
    "Total donated: ₹2,00,000"
    "Verified beneficiaries: 1,240"
    "Tasks funded: 23"
    Certification stamp

Data connections from this portal to others:
- Campaign "people_helped" count updates in real time from volunteer outcome reports
- Impact chain data comes directly from /outcomes written by volunteer app
- CSR report PDFs are stored in Supabase Storage — signed URLs emailed via Resend
- New campaigns created here by NGO coordinators are linked to /needs clusters
- All impact counts labelled as "verified" come only from GPS-confirmed outcomes —
  never estimated figures

---

### Follow-up refinement prompts:
- "Add a donor's personal impact timeline — a vertical feed showing updates from every campaign they've supported."
- "Make the impact chain section interactive — hover on each step to see real example data from an actual resolved case."
- "Add a 'Recurring donation' setup card after the campaign grid with toggle and frequency selector."

---

## CONSISTENT DESIGN SYSTEM ACROSS ALL 4 PROMPTS

All four prompts share this foundation. If generating multiple dashboards, ensure these
are consistent:

### Colour Roles
- Navy #0D2B4E — NGO sidebar, primary buttons, headings
- Teal #0F6E56 — Success, volunteer, positive states
- Purple #534AB7 — Government/admin role
- Amber #D97706 — Donor portal accent, warnings, fallback indicators
- Red #DC2626 — Critical urgency, alerts
- Background #F8F9FC — Page background
- White #FFFFFF — Card backgrounds

### Urgency Colour System (universal)
- Score ≥ 80 = Critical = Red #DC2626
- Score 60-79 = High = Amber #D97706
- Score 40-59 = Moderate = Teal #0F6E56
- Score < 40 = Low = Gray #6B7280

### Fallback State Colours
- Fallback active (amber chip): background #FEF3C7, text #92400E
- Text: "[component] unavailable — fallback active"
- Never red — fallback is functional, not broken

### Map Styling Notes (for all prompts)
- All maps use OpenStreetMap tiles: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
- Always include OSM attribution: "© OpenStreetMap contributors"
- No Google Maps logo, no Google attribution — use OSM branding only
- Heatmap markers: semi-transparent filled circles (not Google Maps pins)
- Choropleth: Leaflet GeoJSON polygon fills (not Google Maps Datasets polygons)

### Typography
- Headings: DM Sans, weight 500
- Body: DM Sans, weight 400, 13px
- Display (donor portal only): DM Serif Display
- Numbers/stats: tabular-nums, weight 600

### Card System
- Background: white
- Border: 0.5px solid #E5E7EB
- Border radius: 12px
- Box shadow: 0 1px 3px rgba(0,0,0,0.04)

### Status Indicators
- Open: Blue #2563EB
- Assigned: Amber #D97706
- In Progress: Purple #7C3AED
- Resolved: Teal #0F6E56
- Verified: Deep Teal #085041

### Source/Fallback Chips (shown on data elements when applicable)
- AI-scored: no chip (default)
- Rule-based score: small amber chip "Rule-based"
- Default score: small amber chip "Needs review"
- OSRM match: no chip (default)
- Haversine match: small muted chip "~Xkm est."
- FCM delivered: no chip (default)
- Resend email fallback: muted chip "Email sent"
