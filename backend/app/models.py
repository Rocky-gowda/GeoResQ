from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class VehicleType(str, Enum):
    AMBULANCE = "ambulance"
    FIRE = "fire"
    POLICE = "police"


class VehicleStatus(str, Enum):
    ON_ROUTE = "on_route"
    DEVIATED = "deviated"
    ARRIVED = "arrived"
    IDLE = "idle"
    DISPATCHED = "dispatched"


class IncidentType(str, Enum):
    ACCIDENT = "accident"
    ROAD_CLOSURE = "road_closure"
    CONGESTION = "congestion"


class DeviationCause(str, Enum):
    ACCIDENT = "accident"
    CONGESTION = "congestion"
    ROAD_CLOSURE = "road_closure"
    WRONG_TURN = "wrong_turn"
    GPS_ANOMALY = "gps_anomaly"
    NONE = "none"


class Coordinate(BaseModel):
    lat: float
    lng: float


class Incident(BaseModel):
    id: str
    type: IncidentType
    location: Coordinate
    radius_meters: float
    severity: str  # low, medium, high
    description: str
    active: bool = True


class VehicleState(BaseModel):
    id: str
    name: str
    type: VehicleType
    status: VehicleStatus
    current_position: Coordinate
    speed_kmh: float
    heading: float
    planned_route: List[Coordinate]
    actual_trajectory: List[Coordinate]
    destination: Coordinate
    planned_eta_minutes: float
    current_eta_minutes: float
    predicted_eta_minutes: float
    delay_minutes: float
    deviation_detected: bool
    deviation_distance_meters: float
    deviation_cause: DeviationCause
    deviation_confidence: float
    recommended_route_id: Optional[str] = None
    # OSRM real-road fields — populated by frontend, echoed back for consistency
    osrm_planned_route: Optional[List[Coordinate]] = None
    routing_source: Optional[str] = None  # 'osrm' | 'simulation'


class AlternativeRoute(BaseModel):
    id: str
    name: str
    waypoints: List[Coordinate]
    estimated_time_minutes: float
    distance_km: float
    congestion_level: str
    incident_count: int
    score: float
    time_saved_minutes: float
    # OSRM real-road fields
    osrm_waypoints: Optional[List[Coordinate]] = None
    routing_source: Optional[str] = None  # 'osrm' | 'simulation'


class AgentDecision(BaseModel):
    agent: str
    timestamp: str
    action: str
    reasoning: str
    confidence: float
    data: Dict[str, Any] = {}


class DecisionEvent(BaseModel):
    timestamp: str
    event_type: str
    description: str
    vehicle_id: str
    severity: str  # info, warning, critical


class SimulationState(BaseModel):
    running: bool
    tick: int
    vehicles: List[VehicleState]
    incidents: List[Incident]
    alternative_routes: Dict[str, List[AlternativeRoute]]
    agent_decisions: List[AgentDecision]
    decision_timeline: List[DecisionEvent]
    explanation: str
    what_if_comparison: Dict[str, Any]
    dispatch_consideration: Optional[Dict[str, Any]] = None
