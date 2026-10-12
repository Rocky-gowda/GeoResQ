"""
Tests for Route Memory Intelligence (RMI) feature.
Run from geo/backend/ directory:
  python test_rmi.py

All test data is SIMULATED — no real emergency routes.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models import Coordinate, Incident, IncidentType
from app.route_memory import (
    RouteMemoryRepository, RouteMemoryAgent, JourneyRecord,
    _haversine, MATCH_THRESHOLD_METERS,
)


# ─── Helpers ────────────────────────────────────────────────────────────────

def make_test_repo() -> RouteMemoryRepository:
    """Return a fresh in-memory repository (no file I/O) seeded with demo data."""
    repo = RouteMemoryRepository()
    repo._journeys = []   # start empty
    repo._loaded   = True  # skip file load
    # Seed it manually via reset_to_seed (writes seeds without touching file)
    from app.route_memory import _make_seed_journeys
    repo._journeys = _make_seed_journeys()
    return repo


ORIGIN = Coordinate(lat=12.9550, lng=77.6100)
DEST   = Coordinate(lat=12.9850, lng=77.5800)

BLOCKING_INCIDENT = Incident(
    id="test_closure",
    type=IncidentType.ROAD_CLOSURE,
    location=Coordinate(lat=12.9700, lng=77.5960),   # sits ON planned M-01 route
    radius_meters=500,
    severity="high",
    description="[TEST] Road closure for test.",
    active=True,
)

CONGESTION_INCIDENT = Incident(
    id="test_cong",
    type=IncidentType.CONGESTION,
    location=Coordinate(lat=12.9670, lng=77.5990),
    radius_meters=300,
    severity="medium",
    description="[TEST] Congestion for test.",
    active=True,
)


# ─── Tests ───────────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0

def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        print(f"  OK  {name}")
        PASS += 1
    else:
        print(f"  FAIL: {name}" + (f" -- {detail}" if detail else ""))
        FAIL += 1


# ── Test 1: Seed history loads successfully ───────────────────────────────────
print("\n[Test 1] Seed history loads successfully")
repo = make_test_repo()
journeys = repo.all_journeys()
check("Has at least 5 seeded journeys", len(journeys) >= 5,
      f"got {len(journeys)}")
check("Has multiple route IDs", len({j.route_id for j in journeys}) >= 3,
      str({j.route_id for j in journeys}))
check("All sources are 'seeded'", all(j.source == "seeded" for j in journeys))


# ── Test 2: Matching O/D retrieves historical routes ─────────────────────────
print("\n[Test 2] Matching O/D retrieves historical routes")
repo = make_test_repo()
matching = repo.find_matching_journeys(ORIGIN, DEST)
check("Matching journeys found", len(matching) > 0, f"got {len(matching)}")
check("All three routes are represented",
      {"M-01", "M-02", "M-03"}.issubset({j.route_id for j in matching}))

# Slightly off (within threshold)
near_origin = Coordinate(lat=ORIGIN.lat + 0.003, lng=ORIGIN.lng + 0.003)  # ~450m
near_matching = repo.find_matching_journeys(near_origin, DEST)
check("Near-origin (within threshold) still matches", len(near_matching) > 0,
      f"distance≈{_haversine(ORIGIN, near_origin):.0f}m")

# Far away — should NOT match
far_origin = Coordinate(lat=13.05, lng=77.70)
far_matching = repo.find_matching_journeys(far_origin, DEST)
check("Far origin does NOT match", len(far_matching) == 0,
      f"got {len(far_matching)}")


# ── Test 3: Road closure makes route infeasible ───────────────────────────────
print("\n[Test 3] Route is rejected when road closure makes it infeasible")
repo = make_test_repo()
agent = RouteMemoryAgent(repo)
result = agent.analyse(
    vehicle_id            = "veh_a",
    origin                = ORIGIN,
    destination           = DEST,
    incidents             = [BLOCKING_INCIDENT],
    optimizer_candidates  = [],
    predicted_eta_minutes = 20.0,
)
all_candidates = result["candidate_routes"]
blocked = [c for c in all_candidates if c["has_closure"]]
rejected = result["rejected_routes"]
check("At least one route is blocked by closure", len(blocked) > 0,
      f"candidates={[c['route_id'] for c in all_candidates]}")
check("Blocked routes appear in rejected list", len(rejected) > 0)
# Verify rejected routes have reason
check("Rejected routes have rejection reasons",
      all(r["reason"] for r in rejected))


# ── Test 4: Congestion affects route ranking ──────────────────────────────────
print("\n[Test 4] Current congestion affects route ranking")
repo = make_test_repo()
agent = RouteMemoryAgent(repo)

result_clean = agent.analyse("veh_a", ORIGIN, DEST, [], [], 20.0)
result_cong  = agent.analyse("veh_a", ORIGIN, DEST, [CONGESTION_INCIDENT], [], 20.0)

# With congestion, estimated ETAs should generally be higher
if result_clean["selected_route"] and result_cong["selected_route"]:
    eta_clean = result_clean["selected_route"]["current_estimated_time"]
    eta_cong  = result_cong["selected_route"]["current_estimated_time"]
    check("Congestion increases ETA (or at least does not decrease below 0.1 min)",
          eta_cong >= eta_clean - 0.1,   # small tolerance
          f"clean={eta_clean:.1f} cong={eta_cong:.1f}")
else:
    check("Selected route exists with and without congestion",
          result_clean["selected_route"] is not None and result_cong["selected_route"] is not None)


# ── Test 5: No-history case falls back gracefully ─────────────────────────────
print("\n[Test 5] No-history case uses fallback gracefully")
repo = make_test_repo()
agent = RouteMemoryAgent(repo)
far_origin = Coordinate(lat=13.10, lng=77.80)
far_dest   = Coordinate(lat=13.15, lng=77.85)
result = agent.analyse("veh_a", far_origin, far_dest, [], [], 20.0)
check("memory_source is 'no-match'", result["memory_source"] == "no-match",
      f"got {result['memory_source']}")
check("matched_journeys_count is 0", result["matched_journeys_count"] == 0)
check("Log events mention no-match",
      any("No matching" in e for e in result["log_events"]))


# ── Test 6: Recording a journey updates statistics exactly once ───────────────
print("\n[Test 6] Recording a journey updates statistics exactly once")
repo = make_test_repo()
initial_count = len(repo.all_journeys())

m01_coords = [
    Coordinate(lat=12.9550, lng=77.6100),
    Coordinate(lat=12.9700, lng=77.5960),
    Coordinate(lat=12.9850, lng=77.5800),
]
new_record = JourneyRecord(
    journey_id                  = "J-TEST-001",
    vehicle_id                  = "veh_a",
    origin                      = ORIGIN,
    destination                 = DEST,
    route_id                    = "M-01",
    route_coordinates           = m01_coords,
    route_distance_km           = 3.5,
    actual_travel_time_minutes  = 17.5,
    planned_travel_time_minutes = 16.0,
    completed_at                = "2025-07-01T10:00:00Z",
    deviation_occurred          = False,
    incident_exposure           = 0,
    outcome                     = "completed",
    source                      = "recorded",
)
repo.record_journey(new_record)
check("Journey count increased by exactly 1",
      len(repo.all_journeys()) == initial_count + 1,
      f"was {initial_count}, now {len(repo.all_journeys())}")

# Re-recording the same object should still add 1 (idempotency is at API level,
# the repo itself just appends)
repo2 = make_test_repo()
before = len(repo2.all_journeys())
repo2.record_journey(new_record)
check("Second record adds one more (dedup is API-level)",
      len(repo2.all_journeys()) == before + 1)

# After recording, stats update
stats = repo.compute_route_stats(repo.find_matching_journeys(ORIGIN, DEST))
check("M-01 stats include the new recorded trip",
      stats.get("M-01") is not None and stats["M-01"].trip_count >= 3,
      f"M-01 trips={stats.get('M-01', None) and stats['M-01'].trip_count}")


# ── Test 7: Reset restores seeded records ─────────────────────────────────────
print("\n[Test 7] Reset restores seeded demonstration records")
repo = make_test_repo()
repo.record_journey(new_record)  # add an extra
count_before_reset = len(repo.all_journeys())
repo.reset_to_seed()
count_after = len(repo.all_journeys())
check("After reset, count equals seed count (5)", count_after == 5,
      f"got {count_after}")
check("No 'recorded' source records remain after reset",
      all(j.source == "seeded" for j in repo.all_journeys()))


# ── Test 8: Existing simulation endpoints still work ─────────────────────────
print("\n[Test 8] Existing simulation engine still works")
from app.simulation_engine import SimulationEngine
eng = SimulationEngine()
eng.start()
for _ in range(15):
    eng.tick_update()
s = eng.get_state()
check("State has vehicles", len(s.vehicles) > 0)
check("State has incidents", len(s.incidents) > 0)
veh_a = next((v for v in s.vehicles if v.id == "veh_a"), None)
check("Vehicle A exists", veh_a is not None)
check("Alternative routes generated", "veh_a" in s.alternative_routes)
check("rmi_result populated after ticks", s.rmi_result is not None,
      f"rmi_result={s.rmi_result}")
if s.rmi_result:
    rmi = s.rmi_result
    check("RMI has matching_history_found key", "matching_history_found" in rmi)
    check("RMI candidate_routes is a list", isinstance(rmi.get("candidate_routes"), list))
    check("RMI matched_journeys_count >= 0",
          isinstance(rmi.get("matched_journeys_count"), int) and rmi["matched_journeys_count"] >= 0)


# ─── Summary ─────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Tests passed: {PASS}   Failed: {FAIL}")
if FAIL > 0:
    print("SOME TESTS FAILED -- check output above.")
    sys.exit(1)
else:
    print("ALL RMI TESTS PASSED.")
    sys.exit(0)
