"""
Route Memory Intelligence (RMI) — Agent 8
Stores, retrieves, evaluates and recommends routes based on journey history.

All data is SIMULATED for hackathon demonstration purposes.
No real emergency journeys are stored or represented.
"""

import json
import math
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Tuple

from app.models import Coordinate, Incident, IncidentType

# ── Configuration ──────────────────────────────────────────────────────────────
MATCH_THRESHOLD_METERS = 500.0   # origins/destinations within this distance are "same"
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "route_memory_store.json")

# Scoring weights — documented, deterministic
W_CURRENT_ETA      = 0.50   # current estimated travel time (primary)
W_HIST_AVG         = 0.20   # historical average travel time
W_CONGESTION       = 0.15   # congestion penalty
W_INCIDENT         = 0.10   # incident exposure count
W_HIST_DEVIATION   = 0.05   # historical deviation frequency


# ── Haversine helper (local, no import from agents to keep module independent) ─
def _haversine(a: Coordinate, b: Coordinate) -> float:
    """Returns distance in metres between two coordinates."""
    R = 6_371_000
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    dphi = math.radians(b.lat - a.lat)
    dl   = math.radians(b.lng - a.lng)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def _route_dist_km(route: List[Coordinate]) -> float:
    total = 0.0
    for i in range(len(route) - 1):
        total += _haversine(route[i], route[i + 1])
    return total / 1_000.0


def _route_incidents(route: List[Coordinate], incidents: List[Incident]) -> Tuple[int, int, bool]:
    """Return (total_incident_count, congestion_count, has_closure)."""
    seen = set()
    congestion = 0
    closure = False
    for wp in route:
        for inc in incidents:
            if inc.active and inc.id not in seen:
                if _haversine(wp, inc.location) <= inc.radius_meters * 1.5:
                    seen.add(inc.id)
                    if inc.type == IncidentType.CONGESTION:
                        congestion += 1
                    elif inc.type == IncidentType.ROAD_CLOSURE:
                        closure = True
    return len(seen), congestion, closure


# ── Data model ─────────────────────────────────────────────────────────────────

class JourneyRecord:
    """One completed (simulated) journey."""

    def __init__(
        self,
        journey_id: str,
        vehicle_id: str,
        origin: Coordinate,
        destination: Coordinate,
        route_id: str,
        route_coordinates: List[Coordinate],
        route_distance_km: float,
        actual_travel_time_minutes: float,
        planned_travel_time_minutes: float,
        completed_at: str,
        deviation_occurred: bool = False,
        incident_exposure: int = 0,
        outcome: str = "completed",
        source: str = "seeded",
    ):
        self.journey_id              = journey_id
        self.vehicle_id              = vehicle_id
        self.origin                  = origin
        self.destination             = destination
        self.route_id                = route_id
        self.route_coordinates       = route_coordinates
        self.route_distance_km       = route_distance_km
        self.actual_travel_time_minutes  = actual_travel_time_minutes
        self.planned_travel_time_minutes = planned_travel_time_minutes
        self.completed_at            = completed_at
        self.deviation_occurred      = deviation_occurred
        self.incident_exposure       = incident_exposure
        self.outcome                 = outcome   # completed | aborted | rerouted
        self.source                  = source    # seeded | recorded

    def to_dict(self) -> dict:
        return {
            "journey_id":                   self.journey_id,
            "vehicle_id":                   self.vehicle_id,
            "origin":                       {"lat": self.origin.lat, "lng": self.origin.lng},
            "destination":                  {"lat": self.destination.lat, "lng": self.destination.lng},
            "route_id":                     self.route_id,
            "route_coordinates":            [{"lat": c.lat, "lng": c.lng} for c in self.route_coordinates],
            "route_distance_km":            self.route_distance_km,
            "actual_travel_time_minutes":   self.actual_travel_time_minutes,
            "planned_travel_time_minutes":  self.planned_travel_time_minutes,
            "completed_at":                 self.completed_at,
            "deviation_occurred":           self.deviation_occurred,
            "incident_exposure":            self.incident_exposure,
            "outcome":                      self.outcome,
            "source":                       self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "JourneyRecord":
        return cls(
            journey_id                  = d["journey_id"],
            vehicle_id                  = d["vehicle_id"],
            origin                      = Coordinate(**d["origin"]),
            destination                 = Coordinate(**d["destination"]),
            route_id                    = d["route_id"],
            route_coordinates           = [Coordinate(**c) for c in d["route_coordinates"]],
            route_distance_km           = d["route_distance_km"],
            actual_travel_time_minutes  = d["actual_travel_time_minutes"],
            planned_travel_time_minutes = d["planned_travel_time_minutes"],
            completed_at                = d["completed_at"],
            deviation_occurred          = d.get("deviation_occurred", False),
            incident_exposure           = d.get("incident_exposure", 0),
            outcome                     = d.get("outcome", "completed"),
            source                      = d.get("source", "seeded"),
        )


class RouteStats:
    """Aggregated statistics for a (origin_key → destination_key → route_id) triple."""

    def __init__(
        self,
        od_key: str,
        route_id: str,
        route_coordinates: List[Coordinate],
        trip_count: int,
        avg_travel_time: float,
        best_travel_time: float,
        deviation_frequency: float,
        last_used: str,
    ):
        self.od_key             = od_key
        self.route_id           = route_id
        self.route_coordinates  = route_coordinates
        self.trip_count         = trip_count
        self.avg_travel_time    = avg_travel_time
        self.best_travel_time   = best_travel_time
        self.deviation_frequency = deviation_frequency
        self.last_used          = last_used

    def to_dict(self) -> dict:
        return {
            "od_key":             self.od_key,
            "route_id":           self.route_id,
            "route_coordinates":  [{"lat": c.lat, "lng": c.lng} for c in self.route_coordinates],
            "trip_count":         self.trip_count,
            "avg_travel_time":    self.avg_travel_time,
            "best_travel_time":   self.best_travel_time,
            "deviation_frequency": self.deviation_frequency,
            "last_used":          self.last_used,
        }


# ── Seeded demonstration data ──────────────────────────────────────────────────
# These are labelled [SEEDED] — they represent plausible fictional historical journeys
# for demonstration purposes only. No real emergency data.

def _make_seed_journeys() -> List[JourneyRecord]:
    """
    Seed records: at least 3 journeys, with at least 2 different routes between
    the same origin–destination pair, so RMI novelty is demonstrable immediately.

    Origin  ≈ VEHICLE_A_START    (12.9550, 77.6100)
    Dest    ≈ VEHICLE_A_DEST     (12.9850, 77.5800)
    """
    # --- Route M-01: Direct MG Road Corridor (planned route coords) ---
    m01_coords = [
        Coordinate(lat=12.9550, lng=77.6100),
        Coordinate(lat=12.9580, lng=77.6080),
        Coordinate(lat=12.9610, lng=77.6050),
        Coordinate(lat=12.9640, lng=77.6020),
        Coordinate(lat=12.9670, lng=77.5990),
        Coordinate(lat=12.9700, lng=77.5960),
        Coordinate(lat=12.9720, lng=77.5930),
        Coordinate(lat=12.9750, lng=77.5900),
        Coordinate(lat=12.9780, lng=77.5870),
        Coordinate(lat=12.9810, lng=77.5840),
        Coordinate(lat=12.9850, lng=77.5800),
    ]

    # --- Route M-02: Eastern Bypass (alt_route_b coords) ---
    m02_coords = [
        Coordinate(lat=12.9550, lng=77.6100),
        Coordinate(lat=12.9580, lng=77.6085),
        Coordinate(lat=12.9700, lng=77.5960),
        Coordinate(lat=12.9720, lng=77.5980),
        Coordinate(lat=12.9745, lng=77.5955),
        Coordinate(lat=12.9768, lng=77.5925),
        Coordinate(lat=12.9800, lng=77.5860),
        Coordinate(lat=12.9835, lng=77.5825),
        Coordinate(lat=12.9850, lng=77.5800),
    ]

    # --- Route M-03: Western Loop (alt_route_c coords) ---
    m03_coords = [
        Coordinate(lat=12.9550, lng=77.6100),
        Coordinate(lat=12.9580, lng=77.6090),
        Coordinate(lat=12.9700, lng=77.5960),
        Coordinate(lat=12.9680, lng=77.5940),
        Coordinate(lat=12.9700, lng=77.5910),
        Coordinate(lat=12.9730, lng=77.5880),
        Coordinate(lat=12.9770, lng=77.5845),
        Coordinate(lat=12.9810, lng=77.5818),
        Coordinate(lat=12.9850, lng=77.5800),
    ]

    origin = Coordinate(lat=12.9550, lng=77.6100)
    dest   = Coordinate(lat=12.9850, lng=77.5800)

    journeys = [
        # Journey 1: M-01, clear run, no incidents
        JourneyRecord(
            journey_id             = "J-SEED-001",
            vehicle_id             = "veh_a",
            origin                 = origin,
            destination            = dest,
            route_id               = "M-01",
            route_coordinates      = m01_coords,
            route_distance_km      = round(_route_dist_km(m01_coords), 2),
            actual_travel_time_minutes  = 16.8,
            planned_travel_time_minutes = 16.0,
            completed_at           = "2025-06-01T09:14:00Z",
            deviation_occurred     = False,
            incident_exposure      = 0,
            outcome                = "completed",
            source                 = "seeded",
        ),
        # Journey 2: M-01, congestion hit, slower
        JourneyRecord(
            journey_id             = "J-SEED-002",
            vehicle_id             = "veh_a",
            origin                 = origin,
            destination            = dest,
            route_id               = "M-01",
            route_coordinates      = m01_coords,
            route_distance_km      = round(_route_dist_km(m01_coords), 2),
            actual_travel_time_minutes  = 24.3,
            planned_travel_time_minutes = 16.0,
            completed_at           = "2025-06-03T17:42:00Z",
            deviation_occurred     = True,
            incident_exposure      = 1,
            outcome                = "rerouted",
            source                 = "seeded",
        ),
        # Journey 3: M-02 Eastern Bypass, no incidents, faster
        JourneyRecord(
            journey_id             = "J-SEED-003",
            vehicle_id             = "veh_a",
            origin                 = origin,
            destination            = dest,
            route_id               = "M-02",
            route_coordinates      = m02_coords,
            route_distance_km      = round(_route_dist_km(m02_coords), 2),
            actual_travel_time_minutes  = 19.1,
            planned_travel_time_minutes = 18.5,
            completed_at           = "2025-06-05T11:08:00Z",
            deviation_occurred     = False,
            incident_exposure      = 0,
            outcome                = "completed",
            source                 = "seeded",
        ),
        # Journey 4: M-02 Eastern Bypass, slightly faster second run
        JourneyRecord(
            journey_id             = "J-SEED-004",
            vehicle_id             = "veh_a",
            origin                 = origin,
            destination            = dest,
            route_id               = "M-02",
            route_coordinates      = m02_coords,
            route_distance_km      = round(_route_dist_km(m02_coords), 2),
            actual_travel_time_minutes  = 18.5,
            planned_travel_time_minutes = 18.5,
            completed_at           = "2025-06-07T08:33:00Z",
            deviation_occurred     = False,
            incident_exposure      = 0,
            outcome                = "completed",
            source                 = "seeded",
        ),
        # Journey 5: M-03 Western Loop, slightly longer
        JourneyRecord(
            journey_id             = "J-SEED-005",
            vehicle_id             = "veh_a",
            origin                 = origin,
            destination            = dest,
            route_id               = "M-03",
            route_coordinates      = m03_coords,
            route_distance_km      = round(_route_dist_km(m03_coords), 2),
            actual_travel_time_minutes  = 21.4,
            planned_travel_time_minutes = 20.0,
            completed_at           = "2025-06-09T14:55:00Z",
            deviation_occurred     = False,
            incident_exposure      = 0,
            outcome                = "completed",
            source                 = "seeded",
        ),
    ]
    return journeys


# ── Repository ─────────────────────────────────────────────────────────────────

class RouteMemoryRepository:
    """
    In-memory journey store with optional JSON persistence.
    Thread-safety: single-process FastAPI, no locks needed.
    """

    def __init__(self):
        self._journeys: List[JourneyRecord] = []
        self._loaded = False

    # ── init ──────────────────────────────────────────────────────────────────

    def load(self):
        """Load from JSON file if it exists; otherwise seed and save."""
        if self._loaded:
            return
        self._loaded = True

        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                journeys = [JourneyRecord.from_dict(d) for d in data.get("journeys", [])]
                # Validate — if empty or corrupted, re-seed
                if journeys:
                    self._journeys = journeys
                    return
            except Exception:
                pass  # fall through to seed

        # Seed
        self._journeys = _make_seed_journeys()
        self._persist()

    def _persist(self):
        """Write current journeys to JSON file (best-effort)."""
        try:
            os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump({"journeys": [j.to_dict() for j in self._journeys]}, f, indent=2)
        except Exception:
            pass  # persistence failure must never crash the app

    def reset_to_seed(self):
        """Restore seeded demo records, discard any recorded journeys."""
        self._journeys = _make_seed_journeys()
        self._persist()

    # ── query ─────────────────────────────────────────────────────────────────

    def all_journeys(self) -> List[JourneyRecord]:
        return list(self._journeys)

    def find_matching_journeys(
        self,
        origin: Coordinate,
        destination: Coordinate,
        threshold_m: float = MATCH_THRESHOLD_METERS,
    ) -> List[JourneyRecord]:
        """Return journeys whose origin AND destination are within threshold of the query pair."""
        return [
            j for j in self._journeys
            if _haversine(origin, j.origin) <= threshold_m
            and _haversine(destination, j.destination) <= threshold_m
        ]

    def compute_route_stats(
        self,
        journeys: List[JourneyRecord],
    ) -> Dict[str, RouteStats]:
        """Aggregate per-route statistics from a list of matching journeys."""
        grouped: Dict[str, List[JourneyRecord]] = {}
        for j in journeys:
            grouped.setdefault(j.route_id, []).append(j)

        stats: Dict[str, RouteStats] = {}
        for route_id, recs in grouped.items():
            times = [r.actual_travel_time_minutes for r in recs]
            deviations = [r for r in recs if r.deviation_occurred]
            od_key = f"{recs[0].origin.lat:.4f},{recs[0].origin.lng:.4f}" \
                     f"→{recs[0].destination.lat:.4f},{recs[0].destination.lng:.4f}"
            stats[route_id] = RouteStats(
                od_key             = od_key,
                route_id           = route_id,
                route_coordinates  = recs[0].route_coordinates,  # use first record's geometry
                trip_count         = len(recs),
                avg_travel_time    = round(sum(times) / len(times), 1),
                best_travel_time   = round(min(times), 1),
                deviation_frequency = round(len(deviations) / len(recs), 2),
                last_used          = max(r.completed_at for r in recs),
            )
        return stats

    # ── record ────────────────────────────────────────────────────────────────

    def record_journey(self, record: JourneyRecord):
        """Append a new journey record and persist."""
        self._journeys.append(record)
        self._persist()


# ── Candidate route ────────────────────────────────────────────────────────────

class CandidateRoute:
    """A fully evaluated candidate for route selection."""

    def __init__(
        self,
        route_id: str,
        route_name: str,
        source: str,                     # "memory", "optimizer", "current"
        waypoints: List[Coordinate],
        historical_trip_count: int,
        historical_avg_time: Optional[float],
        current_estimated_time: float,
        distance_km: float,
        incident_count: int,
        congestion_count: int,
        has_closure: bool,
        score: float,
        feasible: bool,
        rejection_reason: Optional[str],
        selection_reason: Optional[str],
    ):
        self.route_id               = route_id
        self.route_name             = route_name
        self.source                 = source
        self.waypoints              = waypoints
        self.historical_trip_count  = historical_trip_count
        self.historical_avg_time    = historical_avg_time
        self.current_estimated_time = current_estimated_time
        self.distance_km            = distance_km
        self.incident_count         = incident_count
        self.congestion_count       = congestion_count
        self.has_closure            = has_closure
        self.score                  = score
        self.feasible               = feasible
        self.rejection_reason       = rejection_reason
        self.selection_reason       = selection_reason

    def to_dict(self) -> dict:
        return {
            "route_id":               self.route_id,
            "route_name":             self.route_name,
            "source":                 self.source,
            "waypoints":              [{"lat": c.lat, "lng": c.lng} for c in self.waypoints],
            "historical_trip_count":  self.historical_trip_count,
            "historical_avg_time":    self.historical_avg_time,
            "current_estimated_time": self.current_estimated_time,
            "distance_km":            round(self.distance_km, 2),
            "incident_count":         self.incident_count,
            "congestion_count":       self.congestion_count,
            "has_closure":            self.has_closure,
            "score":                  round(self.score, 4),
            "feasible":               self.feasible,
            "rejection_reason":       self.rejection_reason,
            "selection_reason":       self.selection_reason,
        }


# ── Route Memory Agent ─────────────────────────────────────────────────────────

class RouteMemoryAgent:
    """
    Agent 8 — Route Memory Intelligence (RMI).

    Workflow:
      1. Match current O/D pair against journey history.
      2. Retrieve per-route statistics.
      3. For each candidate, score using current conditions.
      4. Reject infeasible candidates (closure / blocked).
      5. Select best feasible candidate.
      6. Return structured reasoning.

    Scoring formula (lower = better):
      score = W_CURRENT_ETA   * (current_eta / 30.0)
            + W_HIST_AVG      * (hist_avg / 25.0)     [0 if no history]
            + W_CONGESTION    * congestion_count * 0.15
            + W_INCIDENT      * incident_count * 0.1
            + W_HIST_DEVIATION * deviation_freq

    Weights: W_CURRENT_ETA=0.50, W_HIST_AVG=0.20,
             W_CONGESTION=0.15, W_INCIDENT=0.10, W_HIST_DEVIATION=0.05
    """

    AVG_SPEED_KMH      = 45.0
    CONGESTION_PENALTY = 8.0   # km/h reduction per congestion incident
    MIN_SPEED_KMH      = 15.0

    def __init__(self, repository: RouteMemoryRepository):
        self.repo = repository

    # ── public interface ──────────────────────────────────────────────────────

    def analyse(
        self,
        vehicle_id: str,
        origin: Coordinate,
        destination: Coordinate,
        incidents: List[Incident],
        optimizer_candidates: List[dict],   # list of {"id","name","waypoints": List[Coordinate]}
        predicted_eta_minutes: float,
    ) -> dict:
        """
        Returns structured RMI reasoning dict ready for API response and decision log.
        """
        matching = self.repo.find_matching_journeys(origin, destination)
        stats    = self.repo.compute_route_stats(matching)
        memory_source = "no-match" if not matching else "seeded" if all(
            j.source == "seeded" for j in matching
        ) else "recorded" if all(j.source == "recorded" for j in matching) else "mixed"

        candidates: List[CandidateRoute] = []

        # ── A: Memory-retrieved routes ──────────────────────────────────────
        memory_route_ids_added: set = set()
        for route_id, st in stats.items():
            if route_id in memory_route_ids_added:
                continue
            cand = self._evaluate_candidate(
                route_id          = route_id,
                route_name        = f"Memory Route {route_id}",
                source            = "memory",
                waypoints         = st.route_coordinates,
                incidents         = incidents,
                stats             = st,
            )
            candidates.append(cand)
            memory_route_ids_added.add(route_id)

        # ── B: Optimizer candidates ─────────────────────────────────────────
        for oc in optimizer_candidates:
            oc_id = oc["id"]
            # Check if this optimizer route matches a memory route by proximity
            matched_stat: Optional[RouteStats] = None
            for sid, st in stats.items():
                # If start of memory route ≈ start of optimizer route, consider matched
                if st.route_coordinates and oc["waypoints"]:
                    if _haversine(st.route_coordinates[0], oc["waypoints"][0]) < 200:
                        matched_stat = st
                        break

            cand = self._evaluate_candidate(
                route_id  = oc_id,
                route_name= oc.get("name", oc_id),
                source    = "optimizer",
                waypoints = oc["waypoints"],
                incidents = incidents,
                stats     = matched_stat,
            )
            # Avoid exact duplicate route IDs from memory
            if oc_id not in {c.route_id for c in candidates}:
                candidates.append(cand)

        # ── C: current route (no-history fallback tracking) ─────────────────
        if not candidates:
            # Create a synthetic straight-line candidate
            direct_coords = [origin, destination]
            candidates.append(self._evaluate_candidate(
                route_id  = "current",
                route_name= "Current Planned Route",
                source    = "current",
                waypoints = direct_coords,
                incidents = incidents,
                stats     = None,
            ))

        # ── Select best feasible ─────────────────────────────────────────────
        feasible = [c for c in candidates if c.feasible]
        rejected = [c for c in candidates if not c.feasible]

        selected: Optional[CandidateRoute] = None
        selection_reason = "No feasible route found."

        if feasible:
            feasible.sort(key=lambda c: c.score)
            selected = feasible[0]
            # Annotate winner
            if selected.historical_avg_time is not None:
                diff = selected.historical_avg_time - selected.current_estimated_time
                if diff > 0:
                    selected.selection_reason = (
                        f"Best current ETA ({selected.current_estimated_time:.1f} min). "
                        f"Historical avg was {selected.historical_avg_time:.1f} min; "
                        f"current conditions are {diff:.1f} min better."
                    )
                else:
                    selected.selection_reason = (
                        f"Best current ETA ({selected.current_estimated_time:.1f} min). "
                        f"Historical avg was {selected.historical_avg_time:.1f} min; "
                        f"current conditions add {abs(diff):.1f} min but this is still the best option."
                    )
            else:
                selected.selection_reason = (
                    f"Selected as best feasible route (ETA {selected.current_estimated_time:.1f} min). "
                    "No matching history for this route."
                )
            selection_reason = selected.selection_reason

        # ── Estimated time saved vs predicted_eta ───────────────────────────
        time_saved = 0.0
        if selected:
            time_saved = round(predicted_eta_minutes - selected.current_estimated_time, 1)

        # ── Build historical statistics summary ──────────────────────────────
        hist_summary = []
        for route_id, st in stats.items():
            hist_summary.append({
                "route_id":          st.route_id,
                "trip_count":        st.trip_count,
                "avg_travel_time":   st.avg_travel_time,
                "best_travel_time":  st.best_travel_time,
                "deviation_frequency": st.deviation_frequency,
                "last_used":         st.last_used,
            })

        # ── Decision log events ──────────────────────────────────────────────
        log_events = []
        if not matching:
            log_events.append(
                "[Route Memory Agent] No matching route history found for this origin–destination pair. "
                "Falling back to optimizer candidates."
            )
        else:
            log_events.append(
                f"[Route Memory Agent] {len(matching)} historical journeys matched "
                f"the current O/D pair (threshold: {MATCH_THRESHOLD_METERS:.0f} m). "
                f"Memory source: {memory_source}."
            )
            for route_id, st in stats.items():
                log_events.append(
                    f"[Route Memory Agent] {route_id}: {st.trip_count} historical trip(s), "
                    f"avg {st.avg_travel_time} min, best {st.best_travel_time} min, "
                    f"deviation rate {st.deviation_frequency:.0%}."
                )
        for rc in rejected:
            log_events.append(
                f"[Route Memory Agent] {rc.route_id} REJECTED — {rc.rejection_reason}"
            )
        if selected:
            log_events.append(
                f"[Route Optimization Agent] {selected.route_id} is feasible "
                f"and has the lowest current estimated travel time ({selected.current_estimated_time:.1f} min)."
            )
            hist_note = (
                f"Historical familiarity was considered (avg {selected.historical_avg_time:.1f} min). "
                if selected.historical_avg_time is not None else
                "No prior history for this route. "
            )
            log_events.append(
                f"[Decision Orchestrator] {selected.route_id} recommended. "
                + hist_note +
                "Current road conditions determined the final selection."
            )

        return {
            "matching_history_found":  len(matching) > 0,
            "matched_journeys_count":  len(matching),
            "memory_source":           memory_source,
            "candidate_routes":        [c.to_dict() for c in candidates],
            "historical_statistics":   hist_summary,
            "current_condition_checks": {
                "active_incidents": [i.id for i in incidents if i.active],
                "origin":           {"lat": origin.lat, "lng": origin.lng},
                "destination":      {"lat": destination.lat, "lng": destination.lng},
            },
            "rejected_routes":         [
                {"route_id": c.route_id, "reason": c.rejection_reason}
                for c in rejected
            ],
            "selected_route":          selected.to_dict() if selected else None,
            "selection_reason":        selection_reason,
            "estimated_time_saved_minutes": time_saved,
            "log_events":              log_events,
        }

    # ── private helpers ───────────────────────────────────────────────────────

    def _estimate_eta(self, waypoints: List[Coordinate], incidents: List[Incident]) -> float:
        dist_km = _route_dist_km(waypoints)
        _, congestion_count, _ = _route_incidents(waypoints, incidents)
        speed = max(
            self.MIN_SPEED_KMH,
            self.AVG_SPEED_KMH - congestion_count * self.CONGESTION_PENALTY,
        )
        return dist_km / speed * 60

    def _evaluate_candidate(
        self,
        route_id: str,
        route_name: str,
        source: str,
        waypoints: List[Coordinate],
        incidents: List[Incident],
        stats: Optional[RouteStats],
    ) -> CandidateRoute:
        dist_km = _route_dist_km(waypoints)
        inc_count, congestion_count, has_closure = _route_incidents(waypoints, incidents)

        # Feasibility — road closure blocks a route unconditionally
        feasible = not has_closure
        rejection_reason: Optional[str] = None
        if has_closure:
            rejection_reason = (
                "Active road closure detected on this route. "
                "Route is infeasible regardless of historical performance."
            )

        current_eta = self._estimate_eta(waypoints, incidents)

        # Historical inputs
        hist_avg   = stats.avg_travel_time        if stats else None
        hist_dev   = stats.deviation_frequency    if stats else 0.0
        trip_count = stats.trip_count             if stats else 0

        # Scoring (lower is better, capped at 1.0)
        score = (
            W_CURRENT_ETA    * (current_eta / 30.0)
            + W_HIST_AVG     * ((hist_avg / 25.0) if hist_avg else 0.0)
            + W_CONGESTION   * (congestion_count * 0.15)
            + W_INCIDENT     * (inc_count * 0.10)
            + W_HIST_DEVIATION * hist_dev
        )
        if has_closure:
            score = 999.0   # infeasible routes float to the bottom

        return CandidateRoute(
            route_id               = route_id,
            route_name             = route_name,
            source                 = source,
            waypoints              = waypoints,
            historical_trip_count  = trip_count,
            historical_avg_time    = hist_avg,
            current_estimated_time = round(current_eta, 1),
            distance_km            = dist_km,
            incident_count         = inc_count,
            congestion_count       = congestion_count,
            has_closure            = has_closure,
            score                  = round(min(score, 1.0) if score < 999 else 999.0, 4),
            feasible               = feasible,
            rejection_reason       = rejection_reason,
            selection_reason       = None,
        )


# ── Module-level singleton ─────────────────────────────────────────────────────

_repository = RouteMemoryRepository()


def get_repository() -> RouteMemoryRepository:
    _repository.load()
    return _repository
