# GeoResQ — GeoAgentic Emergency Command Center

> **Hackathon Prototype** — All data is SIMULATED. No real emergency services are involved.
> Map uses **OpenStreetMap** tiles + **OSRM** real-road routing (with automatic fallback to simulation routes when OSRM is unavailable).

A full-stack, agentic web application that demonstrates an Emergency Vehicle Command Center using a multi-agent AI architecture for real-time route monitoring, deviation detection, cause analysis, ETA prediction, route optimization, and **Route Memory Intelligence (RMI)**.

---

## Architecture Overview

```
Frontend (React + TypeScript + Vite + Tailwind + Leaflet)
    ↕  REST polling every 1.5s
Backend (Python FastAPI)
    ├── VehicleMonitoringAgent   — GPS tracking & movement simulation
    ├── DeviationDetectionAgent  — Route deviation detection (threshold-based)
    ├── CauseAnalysisAgent       — Incident-aware cause identification
    ├── ETAPredictionAgent       — ETA & delay calculation
    ├── RouteOptimizationAgent   — Multi-route scoring & selection
    ├── DecisionOrchestrator     — Coordinates all agents → recommendation
    ├── ExplanationAgent         — Natural-language decision explanation
    └── RouteMemoryAgent (NEW)   — Experience-driven historical route retrieval & recommendation
         └── RouteMemoryRepository — In-memory journey store with JSON persistence
```

---

## What is Route Memory Intelligence (RMI)?

RMI is a new agentic capability that records previous simulated ambulance journeys, retrieves historically successful routes for recurring origin–destination trips, evaluates them against current road conditions, and recommends the most suitable route.

### Core workflow

```
OBSERVE
→ DETECT DEVIATION
→ DIAGNOSE CAUSE
→ PREDICT ETA
→ RETRIEVE ROUTE MEMORY        ← NEW
→ VALIDATE CANDIDATES          ← NEW
→ OPTIMIZE ROUTE
→ EXPLAIN DECISION
→ MONITOR AGAIN
→ RECORD JOURNEY OUTCOME       ← NEW
```

### Key principles

- Historical performance informs but never overrides current safety conditions.
- A road-closure or blocked route is rejected unconditionally even if historically the fastest.
- No external LLM or API key required — fully deterministic Python logic.
- Journey history is seeded with 5 fictional demonstration records at startup.

---

## Route Memory Scoring Formula

Candidates are ranked using a transparent weighted score (lower = better):

```
score = W_CURRENT_ETA    × (current_eta / 30.0)
      + W_HIST_AVG       × (hist_avg / 25.0)      [0 if no history]
      + W_CONGESTION     × congestion_count × 0.15
      + W_INCIDENT       × incident_count × 0.10
      + W_HIST_DEVIATION × deviation_frequency

Weights:
  W_CURRENT_ETA    = 0.50  (primary — current ETA dominates)
  W_HIST_AVG       = 0.20
  W_CONGESTION     = 0.15
  W_INCIDENT       = 0.10
  W_HIST_DEVIATION = 0.05

Road closure: score = 999 (infeasible — never selected)
```

Origin–destination matching threshold: **500 metres** (configurable via `MATCH_THRESHOLD_METERS` in `route_memory.py`).

---

## Journey Memory Data Model

Each `JourneyRecord` contains:

| Field | Description |
|-------|-------------|
| journey_id | Unique ID (e.g. `J-SEED-001`, `J-VEH_A-ABCD1234`) |
| vehicle_id | `veh_a`, `veh_b`, etc. |
| origin / destination | Coordinates |
| route_id | `M-01`, `M-02`, `M-03`, `route_b`, etc. |
| route_coordinates | List of `{lat, lng}` waypoints |
| route_distance_km | Total route distance |
| actual_travel_time_minutes | Measured travel time |
| planned_travel_time_minutes | Originally estimated time |
| completed_at | ISO 8601 timestamp (simulated) |
| deviation_occurred | Whether vehicle left the route |
| incident_exposure | Number of incidents encountered |
| outcome | `completed` \| `rerouted` \| `aborted` |
| source | `seeded` \| `recorded` |

Seeded records are stored in `backend/app/route_memory_store.json` (created on first startup). The file is regenerated if missing or corrupted.

---

## Seeded Demonstration Data

Five [SIMULATED] journeys are seeded at startup:

| Journey ID | Route | Actual Time | Notes |
|------------|-------|-------------|-------|
| J-SEED-001 | M-01 (Direct corridor) | 16.8 min | Clean run |
| J-SEED-002 | M-01 (Direct corridor) | 24.3 min | Congestion hit, rerouted |
| J-SEED-003 | M-02 (Eastern Bypass) | 19.1 min | Clean |
| J-SEED-004 | M-02 (Eastern Bypass) | 18.5 min | Clean, slightly faster |
| J-SEED-005 | M-03 (Western Loop) | 21.4 min | Clean, longest |

At least two alternatives (M-01 and M-02) share the same O/D pair so the comparison is immediately demonstrable.

---

## Deterministic Demo Scenario

1. Dashboard opens → seeded journey history is loaded.
2. Click **▶ START SIMULATION**.
3. Ambulance A starts on its planned route (matching the M-01 historical corridor).
4. Click **🧠 RMI** tab in the right panel.
5. The Route Memory Agent shows 5 matched historical journeys across 3 route candidates.
6. At tick 8+, an accident/congestion triggers deviation; the M-01 direct route is penalised (it passes through the incident zone).
7. M-02 (Eastern Bypass) is selected as the feasible route with the lowest current ETA.
8. The selection reason explains: "Historical avg was 18.8 min; current conditions add Xmin but this is still the best option."
9. Click **⚖️ Compare** to re-run RMI analysis against current live conditions.
10. Click **✍ Record Completed Journey** to persist the outcome.
11. The next run reflects updated statistics.
12. Click **↺ Reset** (with confirmation) to restore to the 5 seeded records.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |

---

## Quick Start

### 1. Clone / Open project

```bash
cd geo
```

### 2. Backend Setup (Terminal 1)

```bash
cd backend

# Windows:
python -m venv venv
venv\Scripts\activate

# macOS/Linux:
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Backend runs at: http://localhost:8001
API docs: http://localhost:8001/docs

> **Note:** The frontend Vite proxy is configured to port **8001**. The README previously showed port 8000 — port 8001 is correct.

### 3. Frontend Setup (Terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

---

## How to Reset Demo Memory

Two ways:

1. **UI:** Click **🧠 RMI** tab → **↺ Reset** button → confirm.
2. **API:** `POST /api/route-memory/reset`
3. **File:** Delete `backend/app/route_memory_store.json` and restart the backend — seeds will be regenerated.

---

## Using the Application

1. Open http://localhost:5173
2. Map loads immediately with OSM tiles — no API key needed
3. Click **▶ START SIMULATION** to begin
4. Ambulance A follows its planned route (ticks 1–7), then **deliberately deviates** at tick 8+ due to simulated accident/congestion
5. The app fetches real-road OSRM geometry for all routes
6. **🧠 RMI tab** shows Route Memory Intelligence analysis in real-time
7. Click **⚖️ Compare** to run on-demand analysis against current conditions
8. Click **Use This Route** on any candidate to display it on the map (amber dashed line)
9. Click **✍ Record Completed Journey** after the simulation completes to persist the outcome
10. Click **⏸ PAUSE** to freeze, **↺ RESET** to restart from scratch

---

## API Endpoints

### Simulation (existing)

| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/state | Full simulation state (JSON) — includes `rmi_result` |
| POST | /api/start | Start simulation |
| POST | /api/pause | Pause simulation |
| POST | /api/reset | Reset simulation to initial state |
| GET | /api/health | Health check |
| GET | /api/route | OSRM proxy (with fallback) |

### Route Memory Intelligence (new)

| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/route-memory/history | All stored journey records |
| GET | /api/route-memory/matches/{vehicle_id} | Historical routes matching vehicle's current O/D |
| GET | /api/route-memory/compare/{vehicle_id} | Full RMI analysis for vehicle |
| POST | /api/route-memory/record/{vehicle_id} | Record a completed journey |
| POST | /api/route-memory/reset | Reset memory to seeded records |

---

## Dashboard Features

### Map (Center)
- 🔵 Planned routes (dashed blue)
- 🟢 Actual trajectory (green / red when deviated)
- 🟢 Recommended alternative route (solid green)
- 🟣 Other alternative routes (dashed purple)
- 🟡 Selected historical route from RMI (dashed amber) — **NEW**
- 💥 Incident zones (accident, road closure, congestion)
- 🚑 Vehicle markers with live popups

### Right Panel (4 tabs)

| Tab | Content |
|-----|---------|
| 🎯 Intel | Vehicle ID, status, speed, ETAs, delay, deviation cause, recommended route |
| 🤖 Agents | Color-coded live decision log for all 8 agents + natural-language explanation |
| ⚖️ What-If | Side-by-side ETA comparison: current vs original vs Route B vs Route C |
| 🧠 RMI | **NEW** Route Memory Intelligence: historical stats, candidate comparison, controls |

### RMI Panel controls

| Button | Action |
|--------|--------|
| 📋 View History | Loads all stored journey records |
| ⚖️ Compare | Runs fresh RMI analysis against current conditions |
| ↺ Reset | Restores to seeded demonstration records (with confirmation) |
| ✍ Record Completed Journey | Persists the current journey outcome once |
| Use This Route | Sets a candidate as the recommended route and shows it on the map |

### Bottom Strip
- **Decision Timeline** — chronological event log including RMI analysis events
- **Dispatch Consideration** — when Ambulance A is delayed ≥4 min, shows Ambulance B as an alternative

---

## Agentic Workflow (Updated)

```
OBSERVE  → DETECT   → DIAGNOSE  → PREDICT  → RETRIEVE  → VALIDATE  → OPTIMIZE  → EXPLAIN  → MONITOR
   |          |           |           |           |            |           |           |
Vehicle  Deviation  Cause      ETA/Delay  Route      Candidate   Route      Explanation
Agent    Agent      Agent      Agent      Memory     Check       Agent      Agent
                                          Agent (NEW)
                                              └── Decision Orchestrator coordinates all
```

---

## Running Tests

### RMI tests (27 assertions)

```bash
cd backend
venv\Scripts\activate    # Windows
# source venv/bin/activate  # macOS/Linux
python test_rmi.py
```

### Existing simulation tests

```bash
python test_sim.py
```

### Frontend type-check and build

```bash
cd frontend
npm run build
```

---

## Project Structure

```
geo/
├── backend/
│   ├── main.py                  # FastAPI entry point + RMI API endpoints (NEW)
│   ├── requirements.txt
│   ├── test_sim.py              # Existing simulation tests
│   ├── test_rmi.py              # NEW: RMI tests (27 checks)
│   └── app/
│       ├── __init__.py
│       ├── models.py            # Pydantic models + RMI models (updated)
│       ├── simulation_data.py   # Static routes & incidents
│       ├── agents.py            # Agents 1–7 (unchanged)
│       ├── route_memory.py      # NEW: Agent 8 — Route Memory Intelligence
│       ├── route_memory_store.json  # Auto-generated: journey persistence
│       └── simulation_engine.py # Tick-based simulation — integrates Agent 8 (updated)
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── main.tsx
│       ├── App.tsx              # Main layout — adds RMI tab (updated)
│       ├── api.ts               # Backend API client — adds RMI calls (updated)
│       ├── types.ts             # TypeScript types — adds RMI types (updated)
│       ├── routing.ts           # OSRM routing client (unchanged)
│       ├── index.css
│       └── components/
│           ├── MapView.tsx          # Leaflet map — adds historical route layer (updated)
│           ├── IntelligencePanel.tsx # Vehicle intel panel (unchanged)
│           ├── DecisionTimeline.tsx  # Event timeline (unchanged)
│           ├── AgentLog.tsx          # Agent decisions (unchanged)
│           ├── WhatIfPanel.tsx       # What-if comparison (unchanged)
│           ├── DispatchPanel.tsx     # Dispatch consideration (unchanged)
│           └── RouteMemoryPanel.tsx  # NEW: RMI dashboard panel
└── README.md
```

---

## Limitations

- **Simulated journey history only** — all route memory records are fictional demonstration data. No real emergency-service journeys are stored or represented.
- **Estimated travel times** — ETAs are calculated from simulated route geometry and speed assumptions, not real-time traffic data.
- **No guarantee of real-world route safety** — this is a decision-support prototype only. Do not use for real emergency dispatch.
- **OSRM dependency** — real-road geometry requires the public OSRM endpoint (falls back to simulation waypoints when unavailable).
- **In-memory only for the current session** — route memory is persisted to `route_memory_store.json` between restarts, but is not a production database.
- **O/D matching is proximity-based** — 500 m threshold may produce false positives in dense urban areas with multiple nearby trip origins.

---

## Notes

- No API keys required — uses OpenStreetMap (free, no key needed)
- No external LLM — all agent logic is deterministic Python
- No authentication — local prototype only
- The map uses Leaflet + OpenStreetMap tiles
- All vehicle positions, incidents, and agent decisions are SIMULATED
- This is a decision-support prototype only — no real dispatch actions are performed
