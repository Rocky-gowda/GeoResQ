/**
 * OSRM routing client with fallback.
 * Tries backend proxy first (/api/route), then direct OSRM public API,
 * then falls back to simulation waypoints on any failure.
 * All data is labelled SIMULATED in the UI.
 */

import { Coordinate } from './types';

const OSRM_DIRECT = 'https://router.project-osrm.org/route/v1/driving';
const BACKEND_PROXY = '/api/route';
const TIMEOUT_MS = 7000;
const MAX_RETRIES = 1;

export interface OsrmResult {
  waypoints: Coordinate[];    // full decoded road geometry
  distance_km: number;
  duration_minutes: number;
  source: 'osrm' | 'fallback';
}

// ── Simple LRU-style cache to avoid hammering OSRM ─────────────────────────
const _cache = new Map<string, { result: OsrmResult; ts: number }>();
const CACHE_TTL_MS = 30_000; // 30 s

function cacheKey(from: Coordinate, to: Coordinate, via?: Coordinate[]): string {
  const pts = [from, ...(via ?? []), to];
  return pts.map(p => `${p.lat.toFixed(4)},${p.lng.toFixed(4)}`).join('|');
}

function fromCache(key: string): OsrmResult | null {
  const entry = _cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.ts > CACHE_TTL_MS) { _cache.delete(key); return null; }
  return entry.result;
}

function toCache(key: string, result: OsrmResult): void {
  if (_cache.size > 50) {
    const oldest = [..._cache.entries()].sort((a, b) => a[1].ts - b[1].ts)[0];
    if (oldest) _cache.delete(oldest[0]);
  }
  _cache.set(key, { result, ts: Date.now() });
}

// ── Decode OSRM polyline6 ───────────────────────────────────────────────────
function decodePolyline6(encoded: string): Coordinate[] {
  const pts: Coordinate[] = [];
  let idx = 0, lat = 0, lng = 0;
  while (idx < encoded.length) {
    let result = 1, shift = 0, b: number;
    do { b = encoded.charCodeAt(idx++) - 63 - 1; result += b << shift; shift += 5; } while (b >= 0x1f);
    lat += (result & 1) !== 0 ? ~(result >> 1) : result >> 1;
    result = 1; shift = 0;
    do { b = encoded.charCodeAt(idx++) - 63 - 1; result += b << shift; shift += 5; } while (b >= 0x1f);
    lng += (result & 1) !== 0 ? ~(result >> 1) : result >> 1;
    pts.push({ lat: lat / 1e6, lng: lng / 1e6 });
  }
  return pts;
}

// ── Fetch with timeout ──────────────────────────────────────────────────────
async function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: controller.signal });
    return res;
  } finally {
    clearTimeout(timer);
  }
}

// ── Internal: call OSRM via backend proxy or directly ─────────────────────
interface OsrmRaw {
  waypoints: Coordinate[];
  distance_km: number;
  duration_minutes: number;
}

async function callOsrm(
  from: Coordinate,
  to: Coordinate,
  via?: Coordinate[],
): Promise<OsrmRaw> {

  // ── 1. Try backend proxy first (/api/route) ───────────────────
  try {
    const viaStr = via?.map(p => `${p.lng},${p.lat}`).join(';');
    const params = new URLSearchParams({
      from_lat: String(from.lat),
      from_lng: String(from.lng),
      to_lat: String(to.lat),
      to_lng: String(to.lng),
    });
    if (viaStr) params.set('via', viaStr);

    const proxyRes = await fetchWithTimeout(`${BACKEND_PROXY}?${params}`, TIMEOUT_MS);
    if (proxyRes.ok) {
      const json = await proxyRes.json();
      if (json.routes?.length > 0) {
        const r = json.routes[0];
        const pts = decodePolyline6(r.geometry as string);
        if (pts.length > 0) {
          return {
            waypoints: pts,
            distance_km: r.distance / 1000,
            duration_minutes: r.duration / 60,
          };
        }
      }
    }
  } catch { /* fall through to direct */ }

  // ── 2. Try direct OSRM ────────────────────────────────────────
  // IMPORTANT: OSRM expects lng,lat — NOT lat,lng
  const allPts = [from, ...(via ?? []), to];
  const coordStr = allPts.map(p => `${p.lng},${p.lat}`).join(';');
  const url = `${OSRM_DIRECT}/${coordStr}?overview=full&geometries=polyline6&steps=false`;

  const res = await fetchWithTimeout(url, TIMEOUT_MS);
  if (!res.ok) throw new Error(`OSRM HTTP ${res.status}`);
  const json = await res.json();
  if (!json.routes?.length) throw new Error('No OSRM routes returned');

  const r = json.routes[0];
  const pts = decodePolyline6(r.geometry as string);
  return {
    waypoints: pts.length > 0 ? pts : [from, to],
    distance_km: r.distance / 1000,
    duration_minutes: r.duration / 60,
  };
}

// ── Public routing function ─────────────────────────────────────────────────
/**
 * Route from `from` to `to`, optionally via `via` waypoints.
 * Falls back to simulation waypoints on any OSRM error.
 */
export async function getRoute(
  from: Coordinate,
  to: Coordinate,
  fallbackWaypoints: Coordinate[],
  via?: Coordinate[],
  attempt = 0,
): Promise<OsrmResult> {
  const key = cacheKey(from, to, via);
  const cached = fromCache(key);
  if (cached) return cached;

  try {
    const data = await callOsrm(from, to, via);
    const result: OsrmResult = {
      waypoints: data.waypoints,
      distance_km: data.distance_km,
      duration_minutes: data.duration_minutes,
      source: 'osrm',
    };
    toCache(key, result);
    return result;

  } catch {
    if (attempt < MAX_RETRIES) {
      await new Promise(r => setTimeout(r, 1000));
      return getRoute(from, to, fallbackWaypoints, via, attempt + 1);
    }
    // Graceful fallback — never break the map
    const fallback: OsrmResult = {
      waypoints: fallbackWaypoints,
      distance_km: haversineRouteKm(fallbackWaypoints),
      duration_minutes: haversineRouteKm(fallbackWaypoints) / 45 * 60,
      source: 'fallback',
    };
    return fallback;
  }
}

// ── Haversine for fallback distance ────────────────────────────────────────
function haversineRouteKm(pts: Coordinate[]): number {
  let total = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const R = 6371;
    const lat1 = pts[i].lat * Math.PI / 180;
    const lat2 = pts[i + 1].lat * Math.PI / 180;
    const dlat = (pts[i + 1].lat - pts[i].lat) * Math.PI / 180;
    const dlng = (pts[i + 1].lng - pts[i].lng) * Math.PI / 180;
    const a = Math.sin(dlat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dlng / 2) ** 2;
    total += 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }
  return total;
}

// ── Clear entire cache (call on reset) ─────────────────────────────────────
export function clearRouteCache(): void {
  _cache.clear();
}
