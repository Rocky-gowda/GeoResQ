import { SimulationState } from './types';

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
