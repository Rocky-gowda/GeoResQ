"""
GeoResQ — FastAPI backend entry point.
All simulation data is SIMULATED for hackathon demonstration purposes.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

from app.simulation_engine import SimulationEngine

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
