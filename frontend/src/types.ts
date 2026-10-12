// GeoResQ shared TypeScript types

export interface Coordinate {
  lat: number;
  lng: number;
}

export type VehicleType = 'ambulance' | 'fire' | 'police';
export type VehicleStatus = 'on_route' | 'deviated' | 'arrived' | 'idle' | 'dispatched';
export type DeviationCause = 'accident' | 'congestion' | 'road_closure' | 'wrong_turn' | 'gps_anomaly' | 'none';
export type IncidentType = 'accident' | 'road_closure' | 'congestion';

export interface VehicleState {
  id: string;
  name: string;
  type: VehicleType;
  status: VehicleStatus;
  current_position: Coordinate;
  speed_kmh: number;
  heading: number;
  planned_route: Coordinate[];
  actual_trajectory: Coordinate[];
  destination: Coordinate;
  planned_eta_minutes: number;
  current_eta_minutes: number;
  predicted_eta_minutes: number;
  delay_minutes: number;
  deviation_detected: boolean;
  deviation_distance_meters: number;
  deviation_cause: DeviationCause;
  deviation_confidence: number;
  recommended_route_id: string | null;
  // OSRM real-road route geometry (optional — populated by backend when OSRM available)
  osrm_planned_route?: Coordinate[];
  routing_source?: 'osrm' | 'simulation' | 'fallback';
}

export interface Incident {
  id: string;
  type: IncidentType;
  location: Coordinate;
  radius_meters: number;
  severity: string;
  description: string;
  active: boolean;
}

export interface AlternativeRoute {
  id: string;
  name: string;
  waypoints: Coordinate[];
  estimated_time_minutes: number;
  distance_km: number;
  congestion_level: string;
  incident_count: number;
  score: number;
  time_saved_minutes: number;
  // OSRM real-road route geometry (optional)
  osrm_waypoints?: Coordinate[];
  routing_source?: 'osrm' | 'simulation' | 'fallback';
}

export interface AgentDecision {
  agent: string;
  timestamp: string;
  action: string;
  reasoning: string;
  confidence: number;
  data: Record<string, unknown>;
}

export interface DecisionEvent {
  timestamp: string;
  event_type: string;
  description: string;
  vehicle_id: string;
  severity: string;
}

export interface DispatchConsideration {
  triggered: boolean;
  primary_vehicle?: string;
  alternative_vehicle?: string;
  reason?: string;
  alt_eta?: number;
  primary_eta?: number;
  note?: string;
}

export interface WhatIfOption {
  id: string;
  name: string;
  predicted_eta: number;
  delay: number;
  time_saved: number;
}

// ── Route Memory Intelligence types ──────────────────────────────────────────

export interface RouteMemoryCandidate {
  route_id: string;
  route_name: string;
  source: 'memory' | 'optimizer' | 'current';
  waypoints: Coordinate[];
  historical_trip_count: number;
  historical_avg_time: number | null;
  current_estimated_time: number;
  distance_km: number;
  incident_count: number;
  congestion_count: number;
  has_closure: boolean;
  score: number;
  feasible: boolean;
  rejection_reason: string | null;
  selection_reason: string | null;
}

export interface RouteHistorySummary {
  route_id: string;
  trip_count: number;
  avg_travel_time: number;
  best_travel_time: number;
  deviation_frequency: number;
  last_used: string;
}

export interface JourneyRecord {
  journey_id: string;
  vehicle_id: string;
  origin: Coordinate;
  destination: Coordinate;
  route_id: string;
  route_coordinates: Coordinate[];
  route_distance_km: number;
  actual_travel_time_minutes: number;
  planned_travel_time_minutes: number;
  completed_at: string;
  deviation_occurred: boolean;
  incident_exposure: number;
  outcome: string;
  source: 'seeded' | 'recorded';
}

export interface RMIResult {
  matching_history_found: boolean;
  matched_journeys_count: number;
  memory_source: 'no-match' | 'seeded' | 'recorded' | 'mixed';
  candidate_routes: RouteMemoryCandidate[];
  historical_statistics: RouteHistorySummary[];
  current_condition_checks: Record<string, unknown>;
  rejected_routes: Array<{ route_id: string; reason: string }>;
  selected_route: RouteMemoryCandidate | null;
  selection_reason: string;
  estimated_time_saved_minutes: number;
  log_events: string[];
}

export interface SimulationState {
  running: boolean;
  tick: number;
  vehicles: VehicleState[];
  incidents: Incident[];
  alternative_routes: Record<string, AlternativeRoute[]>;
  agent_decisions: AgentDecision[];
  decision_timeline: DecisionEvent[];
  explanation: string;
  what_if_comparison: Record<string, WhatIfOption>;
  dispatch_consideration: DispatchConsideration | null;
  rmi_result: RMIResult | null;
}
