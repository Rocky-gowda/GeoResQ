"""
Simulation engine — manages state and ticks for all vehicles.
All data is SIMULATED for hackathon demonstration purposes.
"""
import math
import random
from datetime import datetime
from typing import Dict, List, Optional

from app.models import (
    Coordinate, VehicleState, VehicleType, VehicleStatus, DeviationCause,
    AlternativeRoute, DecisionEvent, SimulationState, Incident
)
from app.simulation_data import (
    VEHICLE_A_START, VEHICLE_A_DESTINATION, VEHICLE_A_PLANNED_ROUTE,
    VEHICLE_A_DEVIATION_ROUTE, VEHICLE_A_ALT_ROUTE_B, VEHICLE_A_ALT_ROUTE_C,
    VEHICLE_B_START, VEHICLE_B_DESTINATION, VEHICLE_B_PLANNED_ROUTE,
    VEHICLE_C_START, VEHICLE_C_DESTINATION, VEHICLE_C_PLANNED_ROUTE,
    INITIAL_INCIDENTS,
)
from app.agents import (
    VehicleMonitoringAgent, DeviationDetectionAgent, CauseAnalysisAgent,
    ETAPredictionAgent, RouteOptimizationAgent, DecisionOrchestrator,
    ExplanationAgent, haversine_distance, route_distance_km, nearest_route_index,
)


def interpolate(a: Coordinate, b: Coordinate, t: float) -> Coordinate:
    return Coordinate(lat=a.lat + (b.lat - a.lat) * t, lng=a.lng + (b.lng - a.lng) * t)


class SimulationEngine:
    def __init__(self):
        self.tick = 0
        self.running = False
        self.incidents: List[Incident] = [i.model_copy() for i in INITIAL_INCIDENTS]
        self.agent_decisions = []
        self.decision_timeline: List[DecisionEvent] = []
        self.explanation = ""
        self.alternative_routes: Dict[str, List[AlternativeRoute]] = {}
        self.alt_routes_data: Dict[str, list] = {}
        self._vehicles: Dict[str, VehicleState] = {}
        self._vehicle_route_idx: Dict[str, int] = {}
        self._vehicle_deviation_phase: Dict[str, bool] = {}
        self._reset()

    # ── helpers ──────────────────────────────────────────────

    def _make_event(self, event_type: str, desc: str, vehicle_id: str, severity: str = "info") -> DecisionEvent:
        return DecisionEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            description=desc,
            vehicle_id=vehicle_id,
            severity=severity,
        )

    def _total_route_dist(self, vehicle_id: str) -> float:
        v = self._vehicles[vehicle_id]
        return route_distance_km(v.planned_route)

    def _planned_eta(self, dist_km: float, speed: float = 45.0) -> float:
        return dist_km / speed * 60

    # ── reset / init ─────────────────────────────────────────

    def _reset(self):
        self.tick = 0
        self.running = False
        self.incidents = [i.model_copy() for i in INITIAL_INCIDENTS]
        self.agent_decisions = []
        self.decision_timeline = []
        self.explanation = "[SIMULATED] Awaiting simulation start."

        dist_a = route_distance_km(VEHICLE_A_PLANNED_ROUTE)
        dist_b = route_distance_km(VEHICLE_B_PLANNED_ROUTE)
        dist_c = route_distance_km(VEHICLE_C_PLANNED_ROUTE)

        self._vehicles = {
            "veh_a": VehicleState(
                id="veh_a",
                name="Ambulance A",
                type=VehicleType.AMBULANCE,
                status=VehicleStatus.ON_ROUTE,
                current_position=Coordinate(**VEHICLE_A_START.model_dump()),
                speed_kmh=0.0,
                heading=0.0,
                planned_route=[Coordinate(**c.model_dump()) for c in VEHICLE_A_PLANNED_ROUTE],
                actual_trajectory=[Coordinate(**VEHICLE_A_START.model_dump())],
                destination=Coordinate(**VEHICLE_A_DESTINATION.model_dump()),
                planned_eta_minutes=round(self._planned_eta(dist_a), 1),
                current_eta_minutes=round(self._planned_eta(dist_a), 1),
                predicted_eta_minutes=round(self._planned_eta(dist_a), 1),
                delay_minutes=0.0,
                deviation_detected=False,
                deviation_distance_meters=0.0,
                deviation_cause=DeviationCause.NONE,
                deviation_confidence=0.0,
            ),
            "veh_b": VehicleState(
                id="veh_b",
                name="Ambulance B",
                type=VehicleType.AMBULANCE,
                status=VehicleStatus.DISPATCHED,
                current_position=Coordinate(**VEHICLE_B_START.model_dump()),
                speed_kmh=0.0,
                heading=0.0,
                planned_route=[Coordinate(**c.model_dump()) for c in VEHICLE_B_PLANNED_ROUTE],
                actual_trajectory=[Coordinate(**VEHICLE_B_START.model_dump())],
                destination=Coordinate(**VEHICLE_B_DESTINATION.model_dump()),
                planned_eta_minutes=round(self._planned_eta(dist_b), 1),
                current_eta_minutes=round(self._planned_eta(dist_b), 1),
                predicted_eta_minutes=round(self._planned_eta(dist_b), 1),
                delay_minutes=0.0,
                deviation_detected=False,
                deviation_distance_meters=0.0,
                deviation_cause=DeviationCause.NONE,
                deviation_confidence=0.0,
            ),
            "veh_c": VehicleState(
                id="veh_c",
                name="Fire Vehicle C",
                type=VehicleType.FIRE,
                status=VehicleStatus.ON_ROUTE,
                current_position=Coordinate(**VEHICLE_C_START.model_dump()),
                speed_kmh=0.0,
                heading=0.0,
                planned_route=[Coordinate(**c.model_dump()) for c in VEHICLE_C_PLANNED_ROUTE],
                actual_trajectory=[Coordinate(**VEHICLE_C_START.model_dump())],
                destination=Coordinate(**VEHICLE_C_DESTINATION.model_dump()),
                planned_eta_minutes=round(self._planned_eta(dist_c), 1),
                current_eta_minutes=round(self._planned_eta(dist_c), 1),
                predicted_eta_minutes=round(self._planned_eta(dist_c), 1),
                delay_minutes=0.0,
                deviation_detected=False,
                deviation_distance_meters=0.0,
                deviation_cause=DeviationCause.NONE,
                deviation_confidence=0.0,
            ),
        }

        self._vehicle_route_idx = {"veh_a": 0, "veh_b": 0, "veh_c": 0}
        self._vehicle_deviation_phase = {"veh_a": False, "veh_b": False, "veh_c": False}

        # Alternative routes data
        self.alt_routes_data = {
            "veh_a": [
                {
                    "id": "route_b",
                    "name": "Route B (Eastern Bypass)",
                    "waypoints": [Coordinate(**c.model_dump()) for c in VEHICLE_A_ALT_ROUTE_B],
                },
                {
                    "id": "route_c",
                    "name": "Route C (Western Loop)",
                    "waypoints": [Coordinate(**c.model_dump()) for c in VEHICLE_A_ALT_ROUTE_C],
                },
            ],
        }
        self.alternative_routes = {}

    # ── movement ─────────────────────────────────────────────

    def _advance_vehicle_along_route(
        self,
        vehicle_id: str,
        route: List[Coordinate],
        tick_seconds: float = 1.5,
        speed_kmh: float = 45.0,
        noise: bool = True,
    ) -> bool:
        """Move vehicle along route. Returns True if reached end."""
        idx = self._vehicle_route_idx[vehicle_id]
        if idx >= len(route) - 1:
            return True

        target = route[idx + 1]
        current = self._vehicles[vehicle_id].current_position
        dist = haversine_distance(current, target)
        step_m = tick_seconds * speed_kmh * 1000 / 3600  # metres per tick (speed * time)

        if dist <= step_m:
            self._vehicle_route_idx[vehicle_id] = idx + 1
            pos = Coordinate(lat=target.lat, lng=target.lng)
        else:
            t = step_m / dist
            pos = interpolate(current, target, t)

        # Tiny GPS noise
        if noise:
            pos = Coordinate(
                lat=pos.lat + random.uniform(-0.00003, 0.00003),
                lng=pos.lng + random.uniform(-0.00003, 0.00003),
            )

        self._vehicles[vehicle_id].current_position = pos
        return False

    # ── main tick ────────────────────────────────────────────

    def tick_update(self):
        if not self.running:
            return

        self.tick += 1
        t = self.tick

        mon_agent = VehicleMonitoringAgent()
        dev_agent = DeviationDetectionAgent()
        cause_agent = CauseAnalysisAgent()
        eta_agent = ETAPredictionAgent()
        route_agent = RouteOptimizationAgent()
        orch_agent = DecisionOrchestrator()
        explain_agent = ExplanationAgent()

        new_decisions = []
        new_events = []

        # ── Vehicle A ────────────────────────────────────────
        veh_a = self._vehicles["veh_a"]

        # Phase logic: deviate after tick 8
        if t >= 8 and not self._vehicle_deviation_phase["veh_a"]:
            self._vehicle_deviation_phase["veh_a"] = True
            veh_a.status = VehicleStatus.DEVIATED
            # Reset route index to 0 of deviation route
            self._vehicle_route_idx["veh_a"] = 0
            new_events.append(self._make_event(
                "deviation_started", "[SIMULATED] Vehicle A began deviating from planned route due to incident.", "veh_a", "warning"
            ))

        if self._vehicle_deviation_phase["veh_a"]:
            route_a = VEHICLE_A_DEVIATION_ROUTE
            speed_a = 28.0 + random.uniform(-3, 3)
        else:
            route_a = VEHICLE_A_PLANNED_ROUTE
            speed_a = 45.0 + random.uniform(-5, 5)

        reached = self._advance_vehicle_along_route("veh_a", route_a, speed_kmh=speed_a)
        if reached:
            veh_a.status = VehicleStatus.ARRIVED
            veh_a.speed_kmh = 0.0
        else:
            veh_a.speed_kmh = round(speed_a, 1)

        # Agent 1
        mon_dec = mon_agent.update(veh_a, veh_a.current_position, veh_a.speed_kmh)
        new_decisions.append(mon_dec)
        if t % 3 == 0:
            new_events.append(self._make_event("gps_update", f"[SIMULATED] GPS position updated: ({veh_a.current_position.lat:.4f}, {veh_a.current_position.lng:.4f})", "veh_a", "info"))

        # Agent 2
        deviated, dev_dist, dev_dec = dev_agent.detect(veh_a)
        if dev_dec:
            new_decisions.append(dev_dec)
            severity = "warning" if deviated else "info"
            new_events.append(self._make_event(
                "deviation_detected" if deviated else "back_on_route",
                f"[SIMULATED] {'Deviation detected' if deviated else 'Back on route'}: {dev_dist:.0f}m from planned path.",
                "veh_a", severity
            ))

        # Agent 3
        if deviated or t % 5 == 0:
            cause_dec = cause_agent.analyze(veh_a, self.incidents)
            new_decisions.append(cause_dec)
            if deviated:
                new_events.append(self._make_event(
                    "cause_identified",
                    f"[SIMULATED] Cause identified: {veh_a.deviation_cause.value} (confidence {veh_a.deviation_confidence:.0%}).",
                    "veh_a", "warning"
                ))
                # Congestion event
                if veh_a.deviation_cause.value == "congestion":
                    new_events.append(self._make_event("congestion_detected", "[SIMULATED] Congestion detected on planned route.", "veh_a", "warning"))
                if veh_a.deviation_cause.value == "accident":
                    new_events.append(self._make_event("accident_detected", "[SIMULATED] Accident detected on planned route.", "veh_a", "critical"))

        # Agent 4
        if t % 2 == 0:
            eta_dec = eta_agent.predict(veh_a, self.incidents)
            new_decisions.append(eta_dec)
            if veh_a.delay_minutes > 2:
                new_events.append(self._make_event(
                    "eta_updated",
                    f"[SIMULATED] ETA updated: {veh_a.predicted_eta_minutes:.1f} min (delay: {veh_a.delay_minutes:.1f} min).",
                    "veh_a", "warning"
                ))

        # Agent 5 – run once early, then every 6 ticks
        if t == 9 or t % 6 == 0:
            alt_routes, route_dec = route_agent.optimize(veh_a, self.incidents, self.alt_routes_data)
            self.alternative_routes["veh_a"] = alt_routes
            new_decisions.append(route_dec)
            new_events.append(self._make_event(
                "routes_generated",
                f"[SIMULATED] {len(alt_routes)} alternative routes evaluated.",
                "veh_a", "info"
            ))

        # Agent 6
        routes_a = self.alternative_routes.get("veh_a", [])
        orch_dec = orch_agent.orchestrate(veh_a, routes_a, self.incidents)
        new_decisions.append(orch_dec)
        if orch_dec.action == "RECOMMEND_REROUTE":
            new_events.append(self._make_event(
                "recommendation_generated",
                f"[SIMULATED] Route recommendation generated: {veh_a.recommended_route_id}.",
                "veh_a", "info"
            ))

        # Agent 7
        self.explanation = explain_agent.explain(veh_a, routes_a, orch_dec)

        # ── Vehicle B ────────────────────────────────────────
        veh_b = self._vehicles["veh_b"]
        if veh_b.status != VehicleStatus.ARRIVED:
            speed_b = 40.0 + random.uniform(-5, 5)
            reached_b = self._advance_vehicle_along_route("veh_b", VEHICLE_B_PLANNED_ROUTE, speed_kmh=speed_b)
            if reached_b:
                veh_b.status = VehicleStatus.ARRIVED
                veh_b.speed_kmh = 0.0
            else:
                veh_b.speed_kmh = round(speed_b, 1)
            mon_agent.update(veh_b, veh_b.current_position, veh_b.speed_kmh)
            eta_agent.predict(veh_b, self.incidents)

        # ── Vehicle C ────────────────────────────────────────
        veh_c = self._vehicles["veh_c"]
        if veh_c.status != VehicleStatus.ARRIVED:
            speed_c = 35.0 + random.uniform(-5, 5)
            reached_c = self._advance_vehicle_along_route("veh_c", VEHICLE_C_PLANNED_ROUTE, speed_kmh=speed_c)
            if reached_c:
                veh_c.status = VehicleStatus.ARRIVED
                veh_c.speed_kmh = 0.0
            else:
                veh_c.speed_kmh = round(speed_c, 1)
            mon_agent.update(veh_c, veh_c.current_position, veh_c.speed_kmh)
            eta_agent.predict(veh_c, self.incidents)

        # Append new decisions (cap at 50)
        self.agent_decisions = (self.agent_decisions + new_decisions)[-50:]
        self.decision_timeline = (self.decision_timeline + new_events)[-30:]

    # ── state export ─────────────────────────────────────────

    def get_state(self) -> SimulationState:
        veh_a = self._vehicles.get("veh_a")
        veh_b = self._vehicles.get("veh_b")

        # Dispatch consideration
        dispatch = None
        if veh_a and veh_b and veh_a.delay_minutes >= 4:
            dispatch = {
                "triggered": True,
                "primary_vehicle": veh_a.id,
                "alternative_vehicle": veh_b.id,
                "reason": f"[SIMULATED] {veh_a.name} is delayed by {veh_a.delay_minutes:.1f} minutes due to {veh_a.deviation_cause.value}.",
                "alt_eta": veh_b.predicted_eta_minutes,
                "primary_eta": veh_a.predicted_eta_minutes,
                "note": "This is decision-support only. No real dispatch action taken.",
            }
        else:
            dispatch = {"triggered": False}

        # What-if comparison
        routes_a = self.alternative_routes.get("veh_a", [])
        what_if = {
            "current_route": {
                "id": "current",
                "name": "Current (Deviated) Path",
                "predicted_eta": veh_a.predicted_eta_minutes if veh_a else 0,
                "delay": veh_a.delay_minutes if veh_a else 0,
                "time_saved": 0,
            },
            "original_route": {
                "id": "original",
                "name": "Original Planned Route",
                "predicted_eta": (veh_a.planned_eta_minutes if veh_a else 0) + 8,
                "delay": 8.0,
                "time_saved": -8.0,
            },
        }
        for r in routes_a:
            what_if[r.id] = {
                "id": r.id,
                "name": r.name,
                "predicted_eta": r.estimated_time_minutes,
                "delay": max(0, r.estimated_time_minutes - (veh_a.planned_eta_minutes if veh_a else 12)),
                "time_saved": r.time_saved_minutes,
            }

        return SimulationState(
            running=self.running,
            tick=self.tick,
            vehicles=list(self._vehicles.values()),
            incidents=self.incidents,
            alternative_routes=self.alternative_routes,
            agent_decisions=self.agent_decisions[-20:],
            decision_timeline=self.decision_timeline[-20:],
            explanation=self.explanation,
            what_if_comparison=what_if,
            dispatch_consideration=dispatch,
        )

    # ── controls ─────────────────────────────────────────────

    def start(self):
        self.running = True

    def pause(self):
        self.running = False

    def reset(self):
        self._reset()
