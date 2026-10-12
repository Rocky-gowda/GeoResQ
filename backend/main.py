"""
GeoResQ — FastAPI backend entry point.
All simulation data is SIMULATED for hackathon demonstration purposes.
"""
import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

from app.simulation_engine import SimulationEngine
from app.route_memory import get_repository, RouteMemoryAgent, JourneyRecord
from app.models import (
    JourneyRecordRequest, JourneyRecordResponse,
    Coordinate,
)

OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"

engine = SimulationEngine()
_bg_task: asyncio.Task = None  # type: ignore[assignment]


async def _simulation_loop():
    while True:
        engine.tick_update()
        await asyncio.sleep(1.5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bg_task
    _bg_task = asyncio.create_task(_simulation_loop())
    yield
    if _bg_task:
        _bg_task.cancel()


app = FastAPI(title="GeoResQ API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "GeoResQ — GeoAgentic Emergency Command Center API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "ok",
    }


@app.get("/health")
async def health_root():
    """Root-level health check — required by frontend startup probe."""
    return {"status": "ok"}


@app.get("/api/state")
async def get_state():
    return engine.get_state()


@app.post("/api/start")
async def start_simulation():
    engine.start()
    return {"status": "started", "tick": engine.tick}


@app.post("/api/pause")
async def pause_simulation():
    engine.pause()
    return {"status": "paused", "tick": engine.tick}


@app.post("/api/reset")
async def reset_simulation():
    engine.reset()
    return {"status": "reset"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "simulated": True}


@app.get("/api/route")
async def proxy_osrm(
    from_lat: float = Query(...),
    from_lng: float = Query(...),
    to_lat: float = Query(...),
    to_lng: float = Query(...),
    via: Optional[str] = Query(None),  # semicolon-separated "lng,lat" pairs
):
    """
    Backend OSRM proxy. Avoids any browser CORS issues with the public OSRM endpoint.
    Falls back to a simple straight-line response on failure.
    """
    try:
        # Build coordinate string: OSRM wants lng,lat order
        coord_parts = [f"{from_lng},{from_lat}"]
        if via:
            coord_parts += [p.strip() for p in via.split(";") if p.strip()]
        coord_parts.append(f"{to_lng},{to_lat}")
        coord_str = ";".join(coord_parts)

        url = f"{OSRM_BASE}/{coord_str}?overview=full&geometries=polyline6&steps=false"

        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        # Return a structured error so frontend can fall back gracefully
        return JSONResponse(
            status_code=503,
            content={"error": "osrm_unavailable", "detail": str(exc)},
        )


# ══════════════════════════════════════════════════════════════════════════════
# ROUTE MEMORY INTELLIGENCE API
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/route-memory/history")
async def route_memory_history():
    """
    Return all stored journey records (seeded + recorded).
    Note: all journey data is SIMULATED — no real emergency routes.
    """
    repo = get_repository()
    journeys = repo.all_journeys()
    return {
        "total": len(journeys),
        "journeys": [j.to_dict() for j in journeys],
        "note": "[SIMULATED] All journey history is fictional demonstration data.",
    }


@app.get("/api/route-memory/matches/{vehicle_id}")
async def route_memory_matches(vehicle_id: str):
    """
    Find historical routes matching the current vehicle's O/D pair.
    Uses the engine's current vehicle state for origin/destination.
    """
    veh = next((v for v in engine.get_state().vehicles if v.id == vehicle_id), None)
    if not veh:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found.")

    repo = get_repository()
    origin = veh.planned_route[0] if veh.planned_route else veh.current_position
    dest   = veh.destination

    matching = repo.find_matching_journeys(origin, dest)
    stats    = repo.compute_route_stats(matching)

    return {
        "vehicle_id":    vehicle_id,
        "origin":        {"lat": origin.lat, "lng": origin.lng},
        "destination":   {"lat": dest.lat, "lng": dest.lng},
        "matched_count": len(matching),
        "journeys":      [j.to_dict() for j in matching],
        "route_stats":   {rid: s.to_dict() for rid, s in stats.items()},
        "note": "[SIMULATED] All journey history is fictional demonstration data.",
    }


@app.get("/api/route-memory/compare/{vehicle_id}")
async def route_memory_compare(vehicle_id: str):
    """
    Run the full Route Memory Intelligence analysis for the given vehicle.
    Returns candidate routes, historical statistics, and the recommended route.
    """
    state = engine.get_state()
    veh   = next((v for v in state.vehicles if v.id == vehicle_id), None)
    if not veh:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found.")

    repo   = get_repository()
    agent  = RouteMemoryAgent(repo)
    origin = veh.planned_route[0] if veh.planned_route else veh.current_position
    dest   = veh.destination

    # Build optimizer candidates from current sim state
    opt_candidates = [
        {"id": r.id, "name": r.name, "waypoints": r.waypoints}
        for r in (state.alternative_routes.get(vehicle_id) or [])
    ]

    rmi = agent.analyse(
        vehicle_id            = vehicle_id,
        origin                = origin,
        destination           = dest,
        incidents             = state.incidents,
        optimizer_candidates  = opt_candidates,
        predicted_eta_minutes = veh.predicted_eta_minutes,
    )
    rmi["vehicle_id"] = vehicle_id
    rmi["note"]       = "[SIMULATED] All route memory data is fictional demonstration data."
    return rmi


@app.post("/api/route-memory/record/{vehicle_id}", response_model=JourneyRecordResponse)
async def route_memory_record(vehicle_id: str, body: JourneyRecordRequest):
    """
    Record a completed simulated journey and update route statistics.
    Each journey_id is unique — duplicate submissions are idempotent by journey_id.
    """
    repo = get_repository()

    # Prevent re-recording the same route_id+vehicle combination in the same second
    existing = repo.all_journeys()
    recent = [
        j for j in existing
        if j.vehicle_id == vehicle_id
        and j.route_id == body.route_id
        and j.source == "recorded"
        and j.completed_at[:16] == datetime.utcnow().isoformat()[:16]  # same minute
    ]
    if recent:
        return JourneyRecordResponse(
            journey_id = recent[0].journey_id,
            message    = "Journey already recorded this minute. No duplicate created.",
            total_journeys = len(existing),
        )

    jid    = f"J-{vehicle_id.upper()}-{uuid.uuid4().hex[:8].upper()}"
    record = JourneyRecord(
        journey_id                  = jid,
        vehicle_id                  = body.vehicle_id,
        origin                      = body.origin,
        destination                 = body.destination,
        route_id                    = body.route_id,
        route_coordinates           = body.route_coordinates,
        route_distance_km           = body.route_distance_km,
        actual_travel_time_minutes  = body.actual_travel_time_minutes,
        planned_travel_time_minutes = body.planned_travel_time_minutes,
        completed_at                = datetime.utcnow().isoformat() + "Z",
        deviation_occurred          = body.deviation_occurred,
        incident_exposure           = body.incident_exposure,
        outcome                     = body.outcome,
        source                      = "recorded",
    )
    repo.record_journey(record)

    return JourneyRecordResponse(
        journey_id     = jid,
        message        = f"[SIMULATED] Journey {jid} recorded successfully.",
        total_journeys = len(repo.all_journeys()),
    )


@app.post("/api/route-memory/reset")
async def route_memory_reset():
    """Reset route memory to the seeded demonstration records."""
    repo = get_repository()
    repo.reset_to_seed()
    # Also clear the engine's cached RMI result
    engine._rmi_result = None
    return {
        "status": "reset",
        "message": "[SIMULATED] Route memory restored to 5 seeded demonstration records.",
        "total_journeys": len(repo.all_journeys()),
    }
