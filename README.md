# GeoResQ — GeoAgentic Emergency Command Center

> **Hackathon Prototype** — All data is SIMULATED. No real emergency services are involved.
> Map uses **OpenStreetMap** tiles + **OSRM** real-road routing (with automatic fallback to simulation routes when OSRM is unavailable).

A full-stack, agentic web application that demonstrates an Emergency Vehicle Command Center using a multi-agent AI architecture for real-time route monitoring, deviation detection, cause analysis, ETA prediction, and route optimization.

---

## Architecture Overview

```
Frontend (React + TypeScript + Vite + Tailwind + Leaflet)
    ↕  REST polling every 1.2s
Backend (Python FastAPI)
    ├── VehicleMonitoringAgent   — GPS tracking & movement simulation
    ├── DeviationDetectionAgent  — Route deviation detection (threshold-based)
    ├── CauseAnalysisAgent       — Incident-aware cause identification
    ├── ETAPredictionAgent       — ETA & delay calculation
    ├── RouteOptimizationAgent   — Multi-route scoring & selection
    ├── DecisionOrchestrator     — Coordinates all agents → recommendation
    └── ExplanationAgent         — Natural-language decision explanation
```

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
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
API docs: http://localhost:8000/docs

### 3. Frontend Setup (Terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

---

## Using the Application

1. Open http://localhost:5173
2. The **map loads immediately** with OSM tiles — no API key needed
3. Click **▶ START SIMULATION** to begin
4. Ambulance A follows its planned route (ticks 1–6), then **deliberately deviates** at tick 7+ due to simulated accident/congestion
5. The app automatically fetches a real-road OSRM route from the vehicle's current position to the destination — the green line shows the new recommended road path
6. The header shows **🛣️ OSRM Roads** when real road geometry is loaded, or **📐 Sim Routes** when using fallback
7. Click **⏸ PAUSE** to freeze, **↺ RESET** to restart from scratch (clears route cache too)

## Map — Fixed Issues

| Problem | Fix |
|---------|-----|
| "Loading map..." stuck permanently | `MapContainer` is now **always mounted** — loading overlay sits on top but never replaces the map |
| Leaflet CSS not loading | Imported directly in `MapView.tsx` via `import 'leaflet/dist/leaflet.css'` (bundled, no CDN dependency) |
| Map container had no explicit height | Container now uses `style={{ width: '100%', height: '100%' }}` with correct flex layout |
| Routes drawn as straight lines | OSRM road geometry fetched and decoded; fallback to simulation waypoints if OSRM unavailable |
| Map destroyed on re-render | `MapContainer` is never conditionally rendered; only child overlays update |
| Coordinate order bug | `routing.ts` sends `lng,lat` to OSRM; Leaflet always receives `[lat, lng]` |

---

## Dashboard Features

### Map (Center)
- 🔵 Planned routes (dashed blue)
- 🟢 Actual trajectory (green / red when deviated)
- 🟢 Recommended alternative route (solid green)
- 🟣 Other alternative routes (dashed purple)
- 💥 Incident zones (accident, road closure, congestion)
- 🚑 Vehicle markers with live popups

### Right Panel (3 tabs)
| Tab | Content |
|-----|---------|
| 🎯 Intel | Vehicle ID, status, speed, ETAs, delay, deviation cause, recommended route |
| 🤖 Agents | Color-coded live decision log for all 7 agents + natural-language explanation |
| ⚖️ What-If | Side-by-side ETA comparison: current vs original vs Route B vs Route C |

### Bottom Strip
- **Decision Timeline** — chronological event log (GPS updates, congestion, accident, deviation, ETA, routes, recommendation)
- **Dispatch Consideration** — when Ambulance A is delayed ≥4 min, shows Ambulance B as an alternative (decision support only, no real dispatch)

---

## Agentic Workflow

```
OBSERVE → DETECT → DIAGNOSE → PREDICT → OPTIMIZE → EXPLAIN → MONITOR AGAIN
   ↓          ↓         ↓          ↓          ↓          ↓
Vehicle    Deviation  Cause     ETA/Delay   Route     Explanation
Agent      Agent      Agent     Agent       Agent     Agent
                                            └── Decision Orchestrator coordinates all
```

---

## Simulated Scenario (Bengaluru-style fictional coordinates)

| Entity | Description |
|--------|-------------|
| Ambulance A | Primary vehicle. Follows planned route, deviates at tick 8 due to incidents |
| Ambulance B | Nearby alternative, shown as dispatch consideration when A is delayed |
| Fire Vehicle C | Separate corridor, follows its own route |
| Incident 1 | Multi-vehicle collision on Ambulance A's planned corridor |
| Incident 2 | Road closure due to utility work |
| Incident 3 | Heavy congestion zone |

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/state | Full simulation state (JSON) |
| POST | /api/start | Start simulation |
| POST | /api/pause | Pause simulation |
| POST | /api/reset | Reset to initial state |
| GET | /api/health | Health check |
| GET | /docs | Swagger UI |

---

## Hackathon Demo Script

1. Start both servers (backend port 8000, frontend port 5173)
2. Open http://localhost:5173 — map loads immediately with OSM tiles
3. You see 3 vehicles, 3 incident zones, and planned routes on the map
4. Click **▶ START SIMULATION**
5. After ~7 ticks (~10 seconds), Ambulance A deviates east
6. Red alert banner: "DEVIATION — Ambulance A — ACCIDENT — Xm off-route"
7. Header shows **🛣️ OSRM Roads** — routes follow real Bengaluru streets
8. Right panel → **🎯 Intel** tab: shows delay, cause (ACCIDENT 92%), recommended route with time saved
9. Right panel → **🤖 Agents** tab: shows all 7 agents' decisions + natural-language explanation
10. Right panel → **⚖️ What-If** tab: compare all 4 route options side-by-side
11. Bottom strip → Dispatch panel activates: "Ambulance B is available with lower ETA"
12. Ask the judge: "Note that OSRM shows the route following real roads in Bengaluru — not straight lines"

## Project Structure

```
geo/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── models.py            # Pydantic models
│       ├── simulation_data.py   # Static routes & incidents
│       ├── agents.py            # All 7 agents
│       └── simulation_engine.py # Tick-based simulation loop
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── main.tsx
│       ├── App.tsx              # Main layout & controls
│       ├── api.ts               # Backend API client
│       ├── types.ts             # TypeScript interfaces
│       ├── index.css
│       └── components/
│           ├── MapView.tsx          # Leaflet map
│           ├── IntelligencePanel.tsx # Vehicle intel panel
│           ├── DecisionTimeline.tsx  # Event timeline
│           ├── AgentLog.tsx          # Agent decisions + explanation
│           ├── WhatIfPanel.tsx       # What-if comparison
│           └── DispatchPanel.tsx     # Dispatch consideration
└── README.md
```

---

## Notes

- No API keys required — uses OpenStreetMap (free, no key needed)
- No database — all state is in-memory
- No authentication — local prototype only
- The map uses Leaflet + OpenStreetMap tiles
- All vehicle positions, incidents, and agent decisions are SIMULATED
- This is a decision-support prototype only — no real dispatch actions are performed
