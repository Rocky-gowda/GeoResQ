import React, { useEffect, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { SimulationState, VehicleState, Incident, AlternativeRoute, Coordinate } from '../types';

// ── Fix Leaflet default icon paths broken by Vite bundling ──────────────────
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  shadowUrl: new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
});

interface Props {
  state: SimulationState | null;
  selectedVehicleId: string | null;
}

// ── Coordinate helpers ───────────────────────────────────────────────────────
function toLatLng(c: Coordinate): [number, number] {
  return [c.lat, c.lng];
}

// ── Color helpers ────────────────────────────────────────────────────────────
function vehicleColor(v: VehicleState): string {
  if (v.status === 'deviated') return '#ef4444';
  if (v.type === 'fire') return '#f97316';
  if (v.type === 'ambulance') return '#3b82f6';
  return '#22c55e';
}
function incidentColor(inc: Incident): string {
  if (inc.type === 'accident') return '#ef4444';
  if (inc.type === 'road_closure') return '#f97316';
  return '#f59e0b';
}
function vehicleEmoji(v: VehicleState): string {
  if (v.type === 'fire') return '🚒';
  if (v.type === 'ambulance') return '🚑';
  return '🚓';
}
function incidentIcon(type: string): string {
  const m: Record<string, string> = { accident: '💥', road_closure: '🚧', congestion: '🚦' };
  return m[type] ?? '⚠️';
}

// ── MapController: fits bounds once on first data, then follows veh_a ────────
function MapController({ state }: { state: SimulationState | null }) {
  const map = useMap();
  const hasFit = useRef(false);

  useEffect(() => {
    if (!state) return;
    if (!hasFit.current) {
      // Collect all waypoints across all vehicles' planned routes
      const pts: L.LatLngTuple[] = [];
      state.vehicles.forEach(v => {
        v.planned_route.forEach(c => pts.push([c.lat, c.lng]));
        pts.push([v.current_position.lat, v.current_position.lng]);
        pts.push([v.destination.lat, v.destination.lng]);
      });
      state.incidents.forEach(i => pts.push([i.location.lat, i.location.lng]));
      if (pts.length > 0) {
        try {
          map.fitBounds(L.latLngBounds(pts), { padding: [40, 40], maxZoom: 15 });
        } catch {
          map.setView([12.9716, 77.5946], 14);
        }
        hasFit.current = true;
      }
    }
  }, [state, map]);

  // Softly pan toward veh_a while sim is running (don't re-fit aggressively)
  useEffect(() => {
    if (!state?.running) return;
    const vehA = state.vehicles.find(v => v.id === 'veh_a');
    if (!vehA) return;
    const currentCenter = map.getCenter();
    const target = L.latLng(vehA.current_position.lat, vehA.current_position.lng);
    // Only pan if vehicle drifted more than 500m from current center
    if (currentCenter.distanceTo(target) > 1500) {
      map.panTo(target, { animate: true, duration: 1.0 });
    }
  }, [state, map]);

  return null;
}

// ── Main MapView ─────────────────────────────────────────────────────────────
// IMPORTANT: MapContainer must NEVER be conditionally rendered or unmounted.
// We always mount it and pass null-safe props to child components.
export default function MapView({ state, selectedVehicleId }: Props) {
  const primaryVehicle = state?.vehicles.find(v => v.id === (selectedVehicleId ?? 'veh_a')) ?? null;

  // Per-selected-vehicle alt routes
  const altRoutes: AlternativeRoute[] =
    (selectedVehicleId && state?.alternative_routes[selectedVehicleId])
      ? state!.alternative_routes[selectedVehicleId]
      : (state?.alternative_routes['veh_a'] ?? []);

  const recommendedId = primaryVehicle?.recommended_route_id ?? null;

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      {/* Loading overlay — sits ON TOP of the map, does NOT replace it */}
      {!state && (
        <div
          style={{
            position: 'absolute', inset: 0, zIndex: 999,
            background: 'rgba(15,22,35,0.85)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          <div style={{ color: '#64748b', fontSize: 14 }}>
            <span style={{ marginRight: 8 }}>📡</span>
            Connecting to backend…
          </div>
        </div>
      )}

      <MapContainer
        center={[12.9716, 77.5946]}
        zoom={14}
        style={{ width: '100%', height: '100%' }}
        zoomControl={true}
        attributionControl={true}
      >
        {/* OSM tile layer */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
          keepBuffer={4}
          errorTileUrl="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        />

        {/* Dynamic controller — only renders when state exists */}
        {state && <MapController state={state} />}

        {/* ── Incidents ──────────────────────────────────────── */}
        {state?.incidents.filter(i => i.active).map(inc => (
          <React.Fragment key={inc.id}>
            <Circle
              center={toLatLng(inc.location)}
              radius={inc.radius_meters}
              pathOptions={{
                color: incidentColor(inc),
                fillColor: incidentColor(inc),
                fillOpacity: 0.18,
                weight: 2,
                dashArray: '6 4',
              }}
            />
            <CircleMarker
              center={toLatLng(inc.location)}
              radius={11}
              pathOptions={{
                color: incidentColor(inc),
                fillColor: incidentColor(inc),
                fillOpacity: 0.92,
                weight: 2,
              }}
            >
              <Popup>
                <div style={{ minWidth: 180 }}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>
                    {incidentIcon(inc.type)} {inc.type.replace(/_/g, ' ').toUpperCase()}
                  </div>
                  <div style={{ fontSize: 11, marginTop: 4 }}>{inc.description}</div>
                  <div style={{ fontSize: 11, marginTop: 4, color: '#c2410c' }}>
                    Severity: {inc.severity.toUpperCase()}
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          </React.Fragment>
        ))}

        {/* ── Alternative / recommended routes ───────────────── */}
        {altRoutes.map(route => {
          const isRecommended = route.id === recommendedId;
          // Use osrm_waypoints if available (real road geometry), else fallback
          const positions: [number, number][] =
            (route.osrm_waypoints && route.osrm_waypoints.length > 1)
              ? route.osrm_waypoints.map(toLatLng)
              : route.waypoints.map(toLatLng);

          return (
            <Polyline
              key={route.id}
              positions={positions}
              pathOptions={{
                color: isRecommended ? '#22c55e' : '#818cf8',
                weight: isRecommended ? 6 : 3,
                opacity: isRecommended ? 0.92 : 0.55,
                dashArray: isRecommended ? undefined : '10 6',
              }}
            >
              <Popup>
                <div style={{ minWidth: 180 }}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>
                    {isRecommended ? '✅ RECOMMENDED: ' : ''}{route.name}
                  </div>
                  {route.routing_source && (
                    <div style={{ fontSize: 10, color: '#6b7280', marginBottom: 4 }}>
                      {route.routing_source === 'osrm' ? '🛣️ Real road routing (OSRM)' : '📐 Simulated route'}
                    </div>
                  )}
                  <div style={{ fontSize: 12 }}>ETA: <b>{route.estimated_time_minutes.toFixed(1)} min</b></div>
                  <div style={{ fontSize: 12 }}>Saves: <b style={{ color: route.time_saved_minutes > 0 ? '#16a34a' : '#dc2626' }}>{route.time_saved_minutes > 0 ? '-' : '+'}{Math.abs(route.time_saved_minutes).toFixed(1)} min</b></div>
                  <div style={{ fontSize: 12 }}>Distance: {route.distance_km.toFixed(2)} km</div>
                  <div style={{ fontSize: 12 }}>Incidents on path: {route.incident_count}</div>
                  <div style={{ fontSize: 12 }}>Congestion: {route.congestion_level}</div>
                </div>
              </Popup>
            </Polyline>
          );
        })}

        {/* ── Vehicles ───────────────────────────────────────── */}
        {state?.vehicles.map(vehicle => {
          // Use osrm_planned_route if available, else fallback to planned_route
          const plannedPositions: [number, number][] =
            (vehicle.osrm_planned_route && vehicle.osrm_planned_route.length > 1)
              ? vehicle.osrm_planned_route.map(toLatLng)
              : vehicle.planned_route.map(toLatLng);

          const trajectoryPositions: [number, number][] =
            vehicle.actual_trajectory.length > 1
              ? vehicle.actual_trajectory.map(toLatLng)
              : [];

          const isDeviated = vehicle.deviation_detected;

          return (
            <React.Fragment key={vehicle.id}>
              {/* Planned route — blue dashed */}
              {plannedPositions.length > 1 && (
                <Polyline
                  positions={plannedPositions}
                  pathOptions={{
                    color: '#3b82f6',
                    weight: vehicle.id === 'veh_a' ? 3 : 2,
                    opacity: 0.45,
                    dashArray: '8 5',
                  }}
                />
              )}

              {/* Actual trajectory */}
              {trajectoryPositions.length > 1 && (
                <Polyline
                  positions={trajectoryPositions}
                  pathOptions={{
                    color: isDeviated ? '#ef4444' : '#22c55e',
                    weight: 3,
                    opacity: 0.85,
                  }}
                />
              )}

              {/* Vehicle marker */}
              <CircleMarker
                center={toLatLng(vehicle.current_position)}
                radius={vehicle.id === 'veh_a' ? 14 : 10}
                pathOptions={{
                  color: '#ffffff',
                  fillColor: vehicleColor(vehicle),
                  fillOpacity: 1,
                  weight: 2.5,
                }}
              >
                <Popup>
                  <div style={{ minWidth: 200 }}>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>
                      {vehicleEmoji(vehicle)} {vehicle.name}
                    </div>
                    <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 6 }}>[SIMULATED]</div>
                    <table style={{ fontSize: 12, width: '100%', borderCollapse: 'collapse' }}>
                      <tbody>
                        <tr><td style={{ color: '#6b7280' }}>Status</td><td style={{ fontWeight: 600, textAlign: 'right' }}>{vehicle.status.replace(/_/g, ' ').toUpperCase()}</td></tr>
                        <tr><td style={{ color: '#6b7280' }}>Speed</td><td style={{ textAlign: 'right' }}>{vehicle.speed_kmh.toFixed(1)} km/h</td></tr>
                        <tr><td style={{ color: '#6b7280' }}>Heading</td><td style={{ textAlign: 'right' }}>{vehicle.heading.toFixed(0)}°</td></tr>
                        <tr><td style={{ color: '#6b7280' }}>Predicted ETA</td><td style={{ textAlign: 'right' }}>{vehicle.predicted_eta_minutes.toFixed(1)} min</td></tr>
                        <tr>
                          <td style={{ color: '#6b7280' }}>Delay</td>
                          <td style={{ textAlign: 'right', fontWeight: 600, color: vehicle.delay_minutes > 2 ? '#dc2626' : '#16a34a' }}>
                            {vehicle.delay_minutes > 0 ? '+' : ''}{vehicle.delay_minutes.toFixed(1)} min
                          </td>
                        </tr>
                        {vehicle.deviation_detected && (
                          <tr>
                            <td colSpan={2} style={{ color: '#dc2626', fontWeight: 700, paddingTop: 4 }}>
                              ⚠ DEVIATION: {vehicle.deviation_distance_meters.toFixed(0)}m<br />
                              Cause: {vehicle.deviation_cause.replace(/_/g, ' ')} ({(vehicle.deviation_confidence * 100).toFixed(0)}%)
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </Popup>
              </CircleMarker>

              {/* Destination marker */}
              <CircleMarker
                center={toLatLng(vehicle.destination)}
                radius={9}
                pathOptions={{
                  color: '#22c55e',
                  fillColor: '#22c55e',
                  fillOpacity: 0.75,
                  weight: 2.5,
                }}
              >
                <Popup>
                  <div style={{ fontWeight: 700 }}>🏥 Destination — {vehicle.name}</div>
                </Popup>
              </CircleMarker>
            </React.Fragment>
          );
        })}
      </MapContainer>
    </div>
  );
}
