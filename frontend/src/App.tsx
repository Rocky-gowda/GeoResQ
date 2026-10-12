import React, { useEffect, useState, useCallback, useRef } from 'react';
import { SimulationState, VehicleState, AlternativeRoute, Coordinate } from './types';
import { fetchState, startSimulation, pauseSimulation, resetSimulation, checkHealth } from './api';
import { getRoute, clearRouteCache } from './routing';
import MapView from './components/MapView';
import IntelligencePanel from './components/IntelligencePanel';
import DecisionTimeline from './components/DecisionTimeline';
import AgentLog from './components/AgentLog';
import WhatIfPanel from './components/WhatIfPanel';
import DispatchPanel from './components/DispatchPanel';
import RouteMemoryPanel from './components/RouteMemoryPanel';

const POLL_INTERVAL_MS = 1500;
// Reroute every N ticks to avoid hammering OSRM
const REROUTE_EVERY_N_TICKS = 8;

// ── Routing status indicator ─────────────────────────────────────────────────
type RoutingStatus = 'idle' | 'fetching' | 'osrm' | 'fallback' | 'error';

// ── Vehicle tab ──────────────────────────────────────────────────────────────
function VehicleTab({ vehicle, selected, onClick }: { vehicle: VehicleState; selected: boolean; onClick: () => void }) {
  const statusColor =
    vehicle.status === 'deviated' ? 'text-red-400' :
    vehicle.status === 'arrived'  ? 'text-green-400' : 'text-blue-400';
  const borderColor = selected
    ? vehicle.status === 'deviated' ? 'border-red-500' : 'border-blue-500'
    : 'border-transparent';

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border-2 text-xs transition-all ${borderColor} ${selected ? 'bg-[#1c2639]' : 'bg-[#0f1623] hover:bg-[#161e2e]'}`}
    >
      <span>{vehicle.type === 'ambulance' ? '🚑' : '🚒'}</span>
      <div className="text-left">
        <div className="text-white font-semibold">{vehicle.name}</div>
        <div className={`${statusColor} capitalize`}>{vehicle.status.replace(/_/g, ' ')}</div>
      </div>
      {vehicle.deviation_detected && (
        <span className="text-red-400 text-xs animate-pulse ml-1">⚠</span>
      )}
    </button>
  );
}

// ── Routing status badge ─────────────────────────────────────────────────────
function RoutingBadge({ status }: { status: RoutingStatus }) {
  if (status === 'idle') return null;
  const cfg: Record<RoutingStatus, { label: string; cls: string }> = {
    idle:     { label: '', cls: '' },
    fetching: { label: '🛣️ Routing…', cls: 'bg-blue-950 border-blue-700 text-blue-300 animate-pulse' },
    osrm:     { label: '🛣️ OSRM Roads', cls: 'bg-green-950 border-green-700 text-green-300' },
    fallback: { label: '📐 Sim Routes', cls: 'bg-yellow-950 border-yellow-700 text-yellow-300' },
    error:    { label: '⚠ Routing N/A', cls: 'bg-red-950 border-red-700 text-red-300' },
  };
  const { label, cls } = cfg[status];
  return (
    <div className={`text-[10px] px-2 py-1 rounded border font-semibold ${cls}`}>{label}</div>
  );
}

// ── OSRM enrichment helpers ──────────────────────────────────────────────────

/**
 * Given a SimulationState from the backend, fetch OSRM real-road geometry
 * for vehicle A's planned route and all alternative routes.
 * Returns a new state object with osrm_* fields populated.
 */
async function enrichStateWithOsrm(
  state: SimulationState,
  onStatus: (s: RoutingStatus) => void,
): Promise<SimulationState> {
  onStatus('fetching');

  try {
    const vehA = state.vehicles.find(v => v.id === 'veh_a');
    if (!vehA || vehA.planned_route.length < 2) {
      onStatus('fallback');
      return state;
    }

    const from = vehA.current_position;
    const dest = vehA.destination;

    // ── 1. Real-road planned route ─────────────────────────────────────────
    const plannedResult = await getRoute(
      from,
      dest,
      vehA.planned_route,
    );

    // ── 2. Alternative routes ─────────────────────────────────────────────
    const altRoutes = state.alternative_routes['veh_a'] ?? [];
    const enrichedAlts: AlternativeRoute[] = await Promise.all(
      altRoutes.map(async (alt) => {
        const viaPoints = alt.waypoints.slice(1, -1); // strip first/last (start/end same)
        const result = await getRoute(from, dest, alt.waypoints, viaPoints.length > 0 ? viaPoints : undefined);
        return {
          ...alt,
          osrm_waypoints: result.waypoints,
          routing_source: result.source,
          // Update ETA and distance from OSRM when real road used
          estimated_time_minutes: result.source === 'osrm'
            ? parseFloat(result.duration_minutes.toFixed(1))
            : alt.estimated_time_minutes,
          distance_km: result.source === 'osrm'
            ? parseFloat(result.distance_km.toFixed(2))
            : alt.distance_km,
          time_saved_minutes: result.source === 'osrm'
            ? parseFloat((plannedResult.duration_minutes - result.duration_minutes).toFixed(1))
            : alt.time_saved_minutes,
        };
      })
    );

    // ── 3. Patch vehicles ────────────────────────────────────────────────
    const enrichedVehicles = state.vehicles.map(v => {
      if (v.id !== 'veh_a') return v;
      return {
        ...v,
        osrm_planned_route: plannedResult.waypoints,
        routing_source: plannedResult.source,
      };
    });

    const anyOsrm = plannedResult.source === 'osrm' ||
      enrichedAlts.some(a => a.routing_source === 'osrm');
    onStatus(anyOsrm ? 'osrm' : 'fallback');

    return {
      ...state,
      vehicles: enrichedVehicles,
      alternative_routes: {
        ...state.alternative_routes,
        veh_a: enrichedAlts,
      },
    };
  } catch {
    onStatus('fallback');
    return state;
  }
}

// ── App ───────────────────────────────────────────────────────────────────────
type BackendStatus = 'connecting' | 'online' | 'offline';

export default function App() {
  const [state, setState] = useState<SimulationState | null>(null);
  const [selectedVehicleId, setSelectedVehicleId] = useState<string>('veh_a');
  const [activeTab, setActiveTab] = useState<'intelligence' | 'agents' | 'whatif' | 'rmi'>('intelligence');
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('connecting');
  const [routingStatus, setRoutingStatus] = useState<RoutingStatus>('idle');
  // RMI: historical route display on map
  const [rmiHistoricalWaypoints, setRmiHistoricalWaypoints] = useState<Coordinate[] | null>(null);
  const [rmiHistoricalRouteId, setRmiHistoricalRouteId] = useState<string | null>(null);

  const pollRef     = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastTickRef = useRef<number>(-1);
  const isEnriching = useRef(false);
  // Keep a ref to the latest state so loadState doesn't need state as a dependency
  // (avoids the interval being torn down and re-created on every state update)
  const stateRef    = useRef<SimulationState | null>(null);

  // ── One-shot health probe on mount ────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    const probe = async () => {
      const ok = await checkHealth();
      if (!cancelled) setBackendStatus(ok ? 'online' : 'offline');
    };
    probe();
    return () => { cancelled = true; };
  }, []);

  // ── Fetch state + OSRM enrich ──────────────────────────────────────────────
  // loadState is stable (no state dependency) — the interval never resets on re-render.
  const loadState = useCallback(async () => {
    try {
      const raw = await fetchState();
      setBackendStatus('online');

      const prevState = stateRef.current;

      // Enrich with OSRM only every N ticks (and not while already fetching)
      const shouldEnrich =
        !isEnriching.current &&
        (lastTickRef.current === -1 ||
          raw.tick - lastTickRef.current >= REROUTE_EVERY_N_TICKS ||
          // Always enrich when deviation first appears
          (raw.vehicles.find(v => v.id === 'veh_a')?.deviation_detected &&
           !prevState?.vehicles.find(v => v.id === 'veh_a')?.deviation_detected));

      if (shouldEnrich && (raw.alternative_routes['veh_a']?.length ?? 0) > 0) {
        isEnriching.current = true;
        lastTickRef.current = raw.tick;
        try {
          const enriched = await enrichStateWithOsrm(raw, setRoutingStatus);
          stateRef.current = enriched;
          setState(enriched);
        } finally {
          isEnriching.current = false;
        }
      } else {
        // Merge OSRM fields from previous state to avoid flicker
        if (prevState) {
          const merged: SimulationState = {
            ...raw,
            vehicles: raw.vehicles.map(v => {
              const prev = prevState.vehicles.find(p => p.id === v.id);
              return {
                ...v,
                osrm_planned_route: prev?.osrm_planned_route ?? v.osrm_planned_route,
                routing_source: prev?.routing_source ?? v.routing_source,
              };
            }),
            alternative_routes: {
              ...raw.alternative_routes,
              veh_a: (raw.alternative_routes['veh_a'] ?? []).map((alt, i) => {
                const prevAlt = prevState.alternative_routes['veh_a']?.[i];
                return prevAlt
                  ? { ...alt, osrm_waypoints: prevAlt.osrm_waypoints, routing_source: prevAlt.routing_source }
                  : alt;
              }),
            },
          };
          stateRef.current = merged;
          setState(merged);
        } else {
          stateRef.current = raw;
          setState(raw);
        }
      }
    } catch {
      setBackendStatus('offline');
    }
  }, []); // stable — no state dependency

  useEffect(() => {
    loadState();
    pollRef.current = setInterval(loadState, POLL_INTERVAL_MS);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []); // runs once on mount — interval never resets

  const handleStart = async () => { await startSimulation(); await loadState(); };
  const handlePause = async () => { await pauseSimulation(); await loadState(); };
  const handleReset = async () => {
    clearRouteCache();
    lastTickRef.current = -1;
    await resetSimulation();
    await loadState();
  };

  const primaryVehicle = state?.vehicles.find(v => v.id === selectedVehicleId) ?? null;
  const altRoutes = state?.alternative_routes[selectedVehicleId] ?? [];
  const isRunning = state?.running ?? false;

  return (
    <div className="h-screen w-screen bg-[#0a0f1a] flex flex-col overflow-hidden font-sans">

      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="flex-shrink-0 bg-[#0f1623] border-b border-[#1e2d45] px-4 py-2 flex items-center gap-3">
        {/* Brand */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="bg-[#1c2639] rounded px-2 py-1">
            <span className="text-[#3b82f6] font-black text-base tracking-tight">GeoResQ</span>
          </div>
          <div>
            <div className="text-white text-sm font-bold leading-tight">GeoAgentic Emergency Command Center</div>
            <div className="text-[#64748b] text-[10px]">[ALL DATA SIMULATED — HACKATHON PROTOTYPE]</div>
          </div>
        </div>

        {/* Vehicle tabs */}
        <div className="flex items-center gap-2 ml-3">
          {state?.vehicles.map(v => (
            <VehicleTab
              key={v.id}
              vehicle={v}
              selected={selectedVehicleId === v.id}
              onClick={() => setSelectedVehicleId(v.id)}
            />
          ))}
        </div>

        <div className="flex-1" />

        {/* Routing status */}
        <RoutingBadge status={routingStatus} />

        {/* Tick counter */}
        {state && (
          <div className="text-[#64748b] text-xs bg-[#161e2e] border border-[#2a3750] rounded px-2 py-1 flex-shrink-0">
            TICK {state.tick}
          </div>
        )}

        {/* Connection status badge — always visible, 3 states */}
        {backendStatus === 'connecting' && (
          <div className="bg-[#161e2e] border border-[#2a3750] text-[#64748b] text-xs px-3 py-1 rounded animate-pulse flex-shrink-0">
            📡 Connecting to backend…
          </div>
        )}
        {backendStatus === 'online' && (
          <div className="bg-green-950 border border-green-800 text-green-400 text-xs px-3 py-1 rounded flex-shrink-0">
            ✓ Backend Online
          </div>
        )}
        {backendStatus === 'offline' && (
          <div className="bg-red-950 border border-red-700 text-red-300 text-xs px-3 py-1 rounded animate-pulse flex-shrink-0">
            ⚠ Backend Offline
          </div>
        )}

        {/* Simulation controls */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {!isRunning ? (
            <button
              onClick={handleStart}
              className="bg-green-700 hover:bg-green-600 text-white text-xs font-bold px-4 py-1.5 rounded flex items-center gap-1.5 transition-colors"
            >
              ▶ START SIMULATION
            </button>
          ) : (
            <button
              onClick={handlePause}
              className="bg-yellow-700 hover:bg-yellow-600 text-white text-xs font-bold px-4 py-1.5 rounded flex items-center gap-1.5 transition-colors"
            >
              ⏸ PAUSE
            </button>
          )}
          <button
            onClick={handleReset}
            className="bg-[#1c2639] hover:bg-[#2a3750] text-white text-xs font-bold px-3 py-1.5 rounded border border-[#2a3750] transition-colors"
          >
            ↺ RESET
          </button>
        </div>
      </header>

      {/* ── Main Layout ────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden min-h-0">

        {/* Map — large center area, always rendered */}
        <div className="flex-1 relative min-w-0" style={{ minHeight: 0 }}>
          <MapView
            state={state}
            selectedVehicleId={selectedVehicleId}
            historicalRouteWaypoints={rmiHistoricalWaypoints}
            historicalRouteId={rmiHistoricalRouteId}
          />

          {/* Legend overlay */}
          <div className="absolute bottom-4 left-4 bg-[#0f1623]/90 border border-[#2a3750] rounded-lg p-3 text-xs space-y-1.5 backdrop-blur-sm z-[900] pointer-events-none">
            <div className="text-[#64748b] font-bold mb-1 uppercase tracking-widest text-[10px]">Map Legend</div>
            <LegendRow color="#3b82f6" dash label="Planned Route" />
            <LegendRow color="#22c55e" label="Actual Path (on route)" />
            <LegendRow color="#ef4444" label="Deviation Path" />
            <LegendRow color="#22c55e" thick label="Recommended Route" />
            <LegendRow color="#818cf8" dash label="Alternative Routes" />
            {rmiHistoricalWaypoints && (
              <LegendRow color="#f59e0b" dash label="Historical Route (RMI)" />
            )}
          </div>

          {/* Deviation alert */}
          {primaryVehicle?.deviation_detected && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-red-950/95 border-2 border-red-600 text-red-200 text-xs font-bold px-4 py-2 rounded-lg animate-pulse z-[900] flex items-center gap-2 backdrop-blur-sm pointer-events-none">
              <span>🚨</span>
              <span>
                DEVIATION — {primaryVehicle.name} — {' '}
                {primaryVehicle.deviation_cause.replace(/_/g, ' ').toUpperCase()} — {' '}
                {primaryVehicle.deviation_distance_meters.toFixed(0)}m off-route
              </span>
              <span>🚨</span>
            </div>
          )}
        </div>

        {/* Right Panel */}
        <div className="w-80 flex-shrink-0 bg-[#0a0f1a] border-l border-[#1e2d45] flex flex-col overflow-hidden">
          {/* Tab selector */}
          <div className="flex border-b border-[#1e2d45] flex-shrink-0 flex-wrap">
            {(['intelligence', 'agents', 'whatif', 'rmi'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-2 text-[10px] font-bold uppercase tracking-wider transition-colors min-w-0 ${
                  activeTab === tab
                    ? 'bg-[#161e2e] text-white border-b-2 border-blue-500'
                    : 'text-[#64748b] hover:text-white hover:bg-[#161e2e]'
                } ${tab === 'rmi' ? (activeTab === 'rmi' ? 'border-purple-500' : '') : ''}`}
              >
                {tab === 'intelligence' ? '🎯 Intel'
                  : tab === 'agents' ? '🤖 Agents'
                  : tab === 'whatif' ? '⚖️ What-If'
                  : '🧠 RMI'}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-hidden p-2 min-h-0">
            {activeTab === 'intelligence' && (
              <IntelligencePanel vehicle={primaryVehicle} altRoutes={altRoutes} />
            )}
            {activeTab === 'agents' && (
              <AgentLog
                decisions={state?.agent_decisions ?? []}
                explanation={state?.explanation ?? ''}
              />
            )}
            {activeTab === 'whatif' && (
              <WhatIfPanel
                options={state?.what_if_comparison ?? {}}
                baseEta={primaryVehicle?.planned_eta_minutes ?? 12}
              />
            )}
            {activeTab === 'rmi' && (
              <RouteMemoryPanel
                rmiResult={state?.rmi_result ?? null}
                vehicle={primaryVehicle}
                altRoutes={altRoutes}
                onUseRoute={(routeId, waypoints) => {
                  // Show historical route on map
                  setRmiHistoricalWaypoints(waypoints);
                  setRmiHistoricalRouteId(routeId);
                }}
              />
            )}
          </div>
        </div>
      </div>

      {/* ── Bottom strip ───────────────────────────────────────── */}
      <div className="flex-shrink-0 h-48 bg-[#0a0f1a] border-t border-[#1e2d45] flex gap-2 px-2 py-2 overflow-hidden">
        <div className="w-1/2 overflow-hidden">
          <DecisionTimeline events={state?.decision_timeline ?? []} />
        </div>
        <div className="w-1/2 overflow-hidden">
          <DispatchPanel dispatch={state?.dispatch_consideration ?? null} />
        </div>
      </div>
    </div>
  );
}

// ── Legend helper ─────────────────────────────────────────────────────────────
function LegendRow({ color, label, dash, thick }: { color: string; label: string; dash?: boolean; thick?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span style={{
        display: 'inline-block',
        width: 18,
        height: thick ? 4 : 2,
        background: dash ? 'transparent' : color,
        opacity: 0.9,
        borderTop: dash ? `2px dashed ${color}` : undefined,
      } as React.CSSProperties} />
      <span className="text-[#94a3b8] text-[10px]">{label}</span>
    </div>
  );
}
