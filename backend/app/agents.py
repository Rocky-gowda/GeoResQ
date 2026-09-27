"""
All 7 logical agents for GeoResQ.
All decisions are SIMULATED for hackathon demonstration purposes.
"""
import math
import random
from datetime import datetime
from typing import List, Tuple, Optional

from app.models import (
    Coordinate, VehicleState, VehicleStatus, Incident, IncidentType,
    DeviationCause, AgentDecision, AlternativeRoute, DecisionEvent
)


def haversine_distance(a: Coordinate, b: Coordinate) -> float:
    """Returns distance in meters between two coordinates."""
    R = 6371000
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    dphi = math.radians(b.lat - a.lat)
    dlambda = math.radians(b.lng - a.lng)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def route_distance_km(route: List[Coordinate]) -> float:
    total = 0.0
    for i in range(len(route) - 1):
        total += haversine_distance(route[i], route[i + 1])
    return total / 1000.0


def bearing(a: Coordinate, b: Coordinate) -> float:
    """Returns compass bearing in degrees from a to b."""
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlng = math.radians(b.lng - a.lng)
    x = math.sin(dlng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def distance_to_route(pos: Coordinate, route: List[Coordinate]) -> float:
    """Minimum distance from pos to any segment of the route (meters)."""
    if not route:
        return 0.0
    min_dist = float("inf")
    for wp in route:
        d = haversine_distance(pos, wp)
        if d < min_dist:
            min_dist = d
    return min_dist


def nearest_route_index(pos: Coordinate, route: List[Coordinate]) -> int:
    """Index of the nearest waypoint in route."""
    min_dist = float("inf")
    idx = 0
    for i, wp in enumerate(route):
        d = haversine_distance(pos, wp)
        if d < min_dist:
            min_dist = d
            idx = i
    return idx


def point_in_incident_zone(pos: Coordinate, incidents: List[Incident]) -> List[Incident]:
    """Return incidents whose zone overlaps with pos."""
    result = []
    for inc in incidents:
        if inc.active and haversine_distance(pos, inc.location) <= inc.radius_meters * 1.5:
            result.append(inc)
    return result


def route_passes_through_incidents(route: List[Coordinate], incidents: List[Incident]) -> List[Incident]:
    """Check if any waypoint of the route is within an incident zone."""
    found = []
    found_ids = set()
    for wp in route:
        for inc in incidents:
            if inc.active and inc.id not in found_ids:
                if haversine_distance(wp, inc.location) <= inc.radius_meters * 1.5:
                    found.append(inc)
                    found_ids.add(inc.id)
    return found


# ──────────────────────────────────────────────────────────────
# AGENT 1: Vehicle Monitoring Agent
# ──────────────────────────────────────────────────────────────

class VehicleMonitoringAgent:
    """Tracks simulated GPS position, speed, heading and planned route."""

    def update(self, vehicle: VehicleState, new_pos: Coordinate, speed: float) -> AgentDecision:
        vehicle.actual_trajectory.append(Coordinate(lat=new_pos.lat, lng=new_pos.lng))
        vehicle.current_position = new_pos
        vehicle.speed_kmh = speed

        if len(vehicle.actual_trajectory) >= 2:
            prev = vehicle.actual_trajectory[-2]
            vehicle.heading = bearing(prev, new_pos)

        return AgentDecision(
            agent="[Vehicle Agent]",
            timestamp=datetime.utcnow().isoformat(),
            action="GPS_UPDATE",
            reasoning=f"Position updated to ({new_pos.lat:.4f}, {new_pos.lng:.4f}). Speed: {speed:.1f} km/h. Heading: {vehicle.heading:.0f}°.",
            confidence=0.99,
            data={"lat": new_pos.lat, "lng": new_pos.lng, "speed": speed, "heading": vehicle.heading},
        )


# ──────────────────────────────────────────────────────────────
# AGENT 2: Deviation Detection Agent
# ──────────────────────────────────────────────────────────────

DEVIATION_THRESHOLD_METERS = 120


class DeviationDetectionAgent:
    """Compares actual trajectory against planned trajectory."""

    def detect(self, vehicle: VehicleState) -> Tuple[bool, float, Optional[AgentDecision]]:
        dist = distance_to_route(vehicle.current_position, vehicle.planned_route)
        vehicle.deviation_distance_meters = dist
        deviated = dist > DEVIATION_THRESHOLD_METERS

        if deviated != vehicle.deviation_detected:
            vehicle.deviation_detected = deviated
            action = "DEVIATION_DETECTED" if deviated else "BACK_ON_ROUTE"
            decision = AgentDecision(
                agent="[Deviation Agent]",
                timestamp=datetime.utcnow().isoformat(),
                action=action,
                reasoning=f"Vehicle is {dist:.0f}m from planned route. Threshold: {DEVIATION_THRESHOLD_METERS}m. {'Significant deviation confirmed.' if deviated else 'Vehicle has returned within route tolerance.'}",
                confidence=min(0.97, 0.6 + dist / 500),
                data={"deviation_meters": dist, "threshold_meters": DEVIATION_THRESHOLD_METERS, "deviated": deviated},
            )
            return deviated, dist, decision

        vehicle.deviation_detected = deviated
        return deviated, dist, None


# ──────────────────────────────────────────────────────────────
# AGENT 3: Cause Analysis Agent
# ──────────────────────────────────────────────────────────────

class CauseAnalysisAgent:
    """Determines likely cause of deviation."""

    def analyze(self, vehicle: VehicleState, incidents: List[Incident]) -> AgentDecision:
        nearby = point_in_incident_zone(vehicle.current_position, incidents)
        route_incidents = route_passes_through_incidents(vehicle.planned_route, incidents)

        cause = DeviationCause.NONE
        confidence = 0.5
        evidence = []

        # Check for accident on planned route
        accidents = [i for i in route_incidents if i.type == IncidentType.ACCIDENT]
        closures = [i for i in route_incidents if i.type == IncidentType.ROAD_CLOSURE]
        congestions = [i for i in route_incidents if i.type == IncidentType.CONGESTION]

        if accidents:
            cause = DeviationCause.ACCIDENT
            confidence = 0.92
            evidence = [f"Accident detected on planned route: {accidents[0].description}"]
        elif closures:
            cause = DeviationCause.ROAD_CLOSURE
            confidence = 0.95
            evidence = [f"Road closure on planned route: {closures[0].description}"]
        elif congestions:
            cause = DeviationCause.CONGESTION
            confidence = 0.85
            evidence = [f"Heavy congestion on planned route: {congestions[0].description}"]
        elif vehicle.speed_kmh < 5 and vehicle.deviation_detected:
            cause = DeviationCause.CONGESTION
            confidence = 0.70
            evidence = ["Vehicle speed < 5 km/h suggests severe congestion or blockage."]
        elif vehicle.deviation_detected and not nearby:
            cause = DeviationCause.WRONG_TURN
            confidence = 0.65
            evidence = ["No incidents detected near deviation. Possible wrong turn or navigation error."]
        elif nearby:
            cause = DeviationCause.CONGESTION
            confidence = 0.75
            evidence = [f"Active incident detected near vehicle: {nearby[0].description}"]

        vehicle.deviation_cause = cause
        vehicle.deviation_confidence = confidence

        return AgentDecision(
            agent="[Cause Agent]",
            timestamp=datetime.utcnow().isoformat(),
            action="CAUSE_IDENTIFIED",
            reasoning=f"Likely cause: {cause.value.upper()} (confidence: {confidence:.0%}). Evidence: {'; '.join(evidence) if evidence else 'No direct evidence found.'}",
            confidence=confidence,
            data={
                "cause": cause.value,
                "confidence": confidence,
                "evidence": evidence,
                "nearby_incidents": len(nearby),
                "route_incidents": len(route_incidents),
            },
        )


# ──────────────────────────────────────────────────────────────
# AGENT 4: ETA / Delay Prediction Agent
# ──────────────────────────────────────────────────────────────

AVG_EMERGENCY_SPEED_KMH = 45.0
CONGESTION_SPEED_KMH = 12.0


class ETAPredictionAgent:
    """Calculates planned, current and predicted ETAs."""

    def predict(self, vehicle: VehicleState, incidents: List[Incident]) -> AgentDecision:
        # Remaining route distance
        nearest_idx = nearest_route_index(vehicle.current_position, vehicle.planned_route)
        remaining_waypoints = vehicle.planned_route[nearest_idx:]
        remaining_dist_km = route_distance_km(remaining_waypoints)

        # Planned ETA (fresh)
        planned_remaining = remaining_dist_km / AVG_EMERGENCY_SPEED_KMH * 60

        # Count incident penalty
        route_incs = route_passes_through_incidents(remaining_waypoints, incidents)
        accident_penalty = sum(5 for i in route_incs if i.type == IncidentType.ACCIDENT)
        closure_penalty = sum(8 for i in route_incs if i.type == IncidentType.ROAD_CLOSURE)
        congestion_penalty = sum(3 for i in route_incs if i.type == IncidentType.CONGESTION)
        total_penalty = accident_penalty + closure_penalty + congestion_penalty

        # Speed-based current ETA
        if vehicle.speed_kmh > 1:
            current_eta = remaining_dist_km / vehicle.speed_kmh * 60
        else:
            current_eta = remaining_dist_km / CONGESTION_SPEED_KMH * 60

        predicted_eta = planned_remaining + total_penalty
        delay = max(0.0, predicted_eta - vehicle.planned_eta_minutes)

        vehicle.current_eta_minutes = round(current_eta, 1)
        vehicle.predicted_eta_minutes = round(predicted_eta, 1)
        vehicle.delay_minutes = round(delay, 1)

        return AgentDecision(
            agent="[Prediction Agent]",
            timestamp=datetime.utcnow().isoformat(),
            action="ETA_UPDATED",
            reasoning=(
                f"Remaining distance: {remaining_dist_km:.2f} km. "
                f"Planned ETA: {vehicle.planned_eta_minutes:.1f} min. "
                f"Predicted ETA: {predicted_eta:.1f} min. "
                f"Delay: {delay:.1f} min due to {len(route_incs)} incident(s) on route (+{total_penalty} min penalty)."
            ),
            confidence=0.88,
            data={
                "remaining_km": remaining_dist_km,
                "planned_eta": vehicle.planned_eta_minutes,
                "current_eta": current_eta,
                "predicted_eta": predicted_eta,
                "delay": delay,
                "incident_penalty_min": total_penalty,
            },
        )


# ──────────────────────────────────────────────────────────────
# AGENT 5: Route Optimization Agent
# ──────────────────────────────────────────────────────────────

class RouteOptimizationAgent:
    """Generates and scores alternative routes."""

    def optimize(
        self,
        vehicle: VehicleState,
        incidents: List[Incident],
        alt_routes_data: dict,
    ) -> Tuple[List[AlternativeRoute], AgentDecision]:
        routes = []

        route_configs = alt_routes_data.get(vehicle.id, [])
        for rc in route_configs:
            waypoints = rc["waypoints"]
            dist_km = route_distance_km(waypoints)
            route_incs = route_passes_through_incidents(waypoints, incidents)

            congestion_count = sum(1 for i in route_incs if i.type == IncidentType.CONGESTION)
            incident_count = len(route_incs)

            # Effective speed based on congestion
            effective_speed = AVG_EMERGENCY_SPEED_KMH - (congestion_count * 10) - (incident_count * 5)
            effective_speed = max(effective_speed, 15.0)

            eta_min = dist_km / effective_speed * 60
            time_saved = vehicle.predicted_eta_minutes - eta_min

            # Score: lower is better (0–1)
            congestion_level = "low" if congestion_count == 0 else ("medium" if congestion_count == 1 else "high")
            score = eta_min / 30.0 + incident_count * 0.1 + (0.2 if congestion_level == "high" else 0)
            score = round(min(score, 1.0), 3)

            routes.append(AlternativeRoute(
                id=rc["id"],
                name=rc["name"],
                waypoints=waypoints,
                estimated_time_minutes=round(eta_min, 1),
                distance_km=round(dist_km, 2),
                congestion_level=congestion_level,
                incident_count=incident_count,
                score=score,
                time_saved_minutes=round(time_saved, 1),
            ))

        # Sort by score ascending
        routes.sort(key=lambda r: r.score)

        best = routes[0] if routes else None
        if best:
            vehicle.recommended_route_id = best.id

        decision = AgentDecision(
            agent="[Route Agent]",
            timestamp=datetime.utcnow().isoformat(),
            action="ROUTES_OPTIMIZED",
            reasoning=(
                f"{len(routes)} alternative routes evaluated. "
                + (f"Best route: {best.name} (ETA: {best.estimated_time_minutes:.1f} min, saves {best.time_saved_minutes:.1f} min, {best.incident_count} incidents)." if best else "No alternatives available.")
            ),
            confidence=0.90,
            data={"routes": [r.model_dump() for r in routes], "recommended": best.id if best else None},
        )
        return routes, decision


# ──────────────────────────────────────────────────────────────
# AGENT 6: Decision Orchestrator
# ──────────────────────────────────────────────────────────────

class DecisionOrchestrator:
    """Coordinates all agents and produces a recommendation."""

    def orchestrate(
        self,
        vehicle: VehicleState,
        routes: List[AlternativeRoute],
        incidents: List[Incident],
    ) -> AgentDecision:
        best = next((r for r in routes if r.id == vehicle.recommended_route_id), routes[0] if routes else None)

        action = "RECOMMEND_REROUTE" if vehicle.deviation_detected or vehicle.delay_minutes > 3 else "MAINTAIN_ROUTE"

        reasoning = ""
        if action == "RECOMMEND_REROUTE" and best:
            reasoning = (
                f"Vehicle {vehicle.name} has deviated {vehicle.deviation_distance_meters:.0f}m from planned route. "
                f"Cause: {vehicle.deviation_cause.value} (confidence: {vehicle.deviation_confidence:.0%}). "
                f"Delay: {vehicle.delay_minutes:.1f} min. "
                f"Recommended: {best.name} — ETA {best.estimated_time_minutes:.1f} min (saves {best.time_saved_minutes:.1f} min, {best.incident_count} incidents)."
            )
        else:
            reasoning = (
                f"Vehicle {vehicle.name} is on-route. Delay: {vehicle.delay_minutes:.1f} min. "
                "No rerouting required at this time."
            )

        return AgentDecision(
            agent="[Decision Agent]",
            timestamp=datetime.utcnow().isoformat(),
            action=action,
            reasoning=reasoning,
            confidence=0.93,
            data={
                "action": action,
                "recommended_route": best.id if best else None,
                "delay_minutes": vehicle.delay_minutes,
                "cause": vehicle.deviation_cause.value,
            },
        )


# ──────────────────────────────────────────────────────────────
# AGENT 7: Explanation Agent
# ──────────────────────────────────────────────────────────────

class ExplanationAgent:
    """Converts decisions into natural-language explanations."""

    def explain(
        self,
        vehicle: VehicleState,
        routes: List[AlternativeRoute],
        orchestrator_decision: AgentDecision,
    ) -> str:
        best = next((r for r in routes if r.id == vehicle.recommended_route_id), None)
        cause_map = {
            DeviationCause.ACCIDENT: "an accident",
            DeviationCause.CONGESTION: "heavy congestion",
            DeviationCause.ROAD_CLOSURE: "a road closure",
            DeviationCause.WRONG_TURN: "a possible wrong turn",
            DeviationCause.GPS_ANOMALY: "a GPS anomaly",
            DeviationCause.NONE: "an unidentified obstruction",
        }
        cause_str = cause_map.get(vehicle.deviation_cause, "an incident")

        if orchestrator_decision.action == "RECOMMEND_REROUTE" and best:
            return (
                f"{vehicle.name} has deviated {vehicle.deviation_distance_meters:.0f} meters from its planned route. "
                f"Analysis indicates the deviation is likely caused by {cause_str} detected on the original corridor "
                f"(confidence: {vehicle.deviation_confidence:.0%}). "
                f"{best.name} is recommended because its predicted arrival time is {abs(best.time_saved_minutes):.1f} minutes "
                f"{'shorter' if best.time_saved_minutes > 0 else 'longer'} and it avoids {best.incident_count} active incident(s) on the blocked segment. "
                f"Expected delay on current path: {vehicle.delay_minutes:.1f} minutes. "
                f"This is a [SIMULATED] decision-support recommendation only."
            )
        elif vehicle.deviation_detected:
            return (
                f"{vehicle.name} has deviated from its planned route. "
                f"The likely cause is {cause_str}. "
                f"Current delay estimate: {vehicle.delay_minutes:.1f} minutes. "
                f"Route optimization is in progress. This is a [SIMULATED] analysis."
            )
        else:
            return (
                f"{vehicle.name} is proceeding normally on its planned route. "
                f"No significant deviations detected. "
                f"Predicted ETA: {vehicle.predicted_eta_minutes:.1f} minutes. "
                f"Delay: {vehicle.delay_minutes:.1f} minutes. "
                f"All systems nominal. This is a [SIMULATED] status."
            )
