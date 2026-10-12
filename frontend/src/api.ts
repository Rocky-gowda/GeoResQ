import { SimulationState, RMIResult, JourneyRecord } from './types';

// All /api/* calls go through Vite proxy → http://127.0.0.1:8001
const BASE = '/api';
const FETCH_TIMEOUT_MS = 5000;

async function fetchWithTimeout(input: RequestInfo, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchState(): Promise<SimulationState> {
  const res = await fetchWithTimeout(`${BASE}/state`);
  if (!res.ok) throw new Error(`Backend error: ${res.status}`);
  return res.json();
}

export async function startSimulation(): Promise<void> {
  await fetchWithTimeout(`${BASE}/start`, { method: 'POST' });
}

export async function pauseSimulation(): Promise<void> {
  await fetchWithTimeout(`${BASE}/pause`, { method: 'POST' });
}

export async function resetSimulation(): Promise<void> {
  await fetchWithTimeout(`${BASE}/reset`, { method: 'POST' });
}

/**
 * Health check — hits /api/health which is proxied to the GeoResQ backend.
 * Returns true when the backend responds 200 with { status: "ok" }.
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetchWithTimeout(`${BASE}/health`);
    if (!res.ok) return false;
    const json = await res.json();
    return json?.status === 'ok';
  } catch {
    return false;
  }
}

// ── Route Memory Intelligence API ─────────────────────────────────────────────

export async function fetchRouteMemoryHistory(): Promise<{ total: number; journeys: JourneyRecord[] }> {
  const res = await fetchWithTimeout(`${BASE}/route-memory/history`);
  if (!res.ok) throw new Error(`RMI history error: ${res.status}`);
  return res.json();
}

export async function fetchRouteMemoryMatches(vehicleId: string): Promise<{
  matched_count: number;
  journeys: JourneyRecord[];
  route_stats: Record<string, unknown>;
}> {
  const res = await fetchWithTimeout(`${BASE}/route-memory/matches/${vehicleId}`);
  if (!res.ok) throw new Error(`RMI matches error: ${res.status}`);
  return res.json();
}

export async function fetchRouteMemoryCompare(vehicleId: string): Promise<RMIResult> {
  const res = await fetchWithTimeout(`${BASE}/route-memory/compare/${vehicleId}`);
  if (!res.ok) throw new Error(`RMI compare error: ${res.status}`);
  return res.json();
}

export interface RecordJourneyBody {
  vehicle_id: string;
  origin: { lat: number; lng: number };
  destination: { lat: number; lng: number };
  route_id: string;
  route_coordinates: Array<{ lat: number; lng: number }>;
  route_distance_km: number;
  actual_travel_time_minutes: number;
  planned_travel_time_minutes: number;
  deviation_occurred?: boolean;
  incident_exposure?: number;
  outcome?: string;
}

export async function recordJourney(
  vehicleId: string,
  body: RecordJourneyBody,
): Promise<{ journey_id: string; message: string; total_journeys: number }> {
  const res = await fetchWithTimeout(`${BASE}/route-memory/record/${vehicleId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`RMI record error: ${res.status}`);
  return res.json();
}

export async function resetRouteMemory(): Promise<{ status: string; message: string; total_journeys: number }> {
  const res = await fetchWithTimeout(`${BASE}/route-memory/reset`, { method: 'POST' });
  if (!res.ok) throw new Error(`RMI reset error: ${res.status}`);
  return res.json();
}
