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
}
