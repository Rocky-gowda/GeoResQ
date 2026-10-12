/**
 * RouteMemoryPanel — Route Memory Intelligence (RMI) dashboard panel.
 * Displays historical route statistics, candidate comparison, and controls.
 * All data is SIMULATED for hackathon demonstration purposes.
 */
import React, { useState, useCallback } from 'react';
import {
  RMIResult,
  RouteMemoryCandidate,
  RouteHistorySummary,
  JourneyRecord,
  VehicleState,
  AlternativeRoute,
  Coordinate,
} from '../types';
import {
  fetchRouteMemoryHistory,
  fetchRouteMemoryCompare,
  recordJourney,
  resetRouteMemory,
} from '../api';

// ── Helpers ───────────────────────────────────────────────────────────────────

function haversineKm(a: Coordinate, b: Coordinate): number {
  const R = 6371;
  const dLat = (b.lat - a.lat) * Math.PI / 180;
  const dLng = (b.lng - a.lng) * Math.PI / 180;
  const aa = Math.sin(dLat / 2) ** 2 +
    Math.cos(a.lat * Math.PI / 180) * Math.cos(b.lat * Math.PI / 180) *
    Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(aa), Math.sqrt(1 - aa));
}

function routeDistKm(pts: Coordinate[]): number {
  let t = 0;
  for (let i = 0; i < pts.length - 1; i++) t += haversineKm(pts[i], pts[i + 1]);
  return t;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[#64748b] text-[10px] uppercase tracking-widest mb-1 mt-2 font-bold">
      {children}
    </div>
  );
}

function InfoRow({ label, value, accent }: { label: string; value: React.ReactNode; accent?: boolean }) {
  return (
    <div className="flex justify-between items-center py-0.5 border-b border-[#2a3750]">
      <span className="text-[#64748b] text-xs">{label}</span>
      <span className={`text-xs font-semibold ${accent ? 'text-yellow-400' : 'text-white'}`}>{value}</span>
    </div>
  );
}

function SourceBadge({ source }: { source: string }) {
  const cfg: Record<string, string> = {
    memory:    'bg-purple-950 border-purple-700 text-purple-300',
    optimizer: 'bg-blue-950 border-blue-700 text-blue-300',
    current:   'bg-gray-800 border-gray-600 text-gray-300',
  };
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded border font-bold uppercase ${cfg[source] ?? cfg.current}`}>
      {source}
    </span>
  );
}

function MemorySourceBadge({ source }: { source: string }) {
  const cfg: Record<string, { label: string; cls: string }> = {
    'no-match': { label: 'No History', cls: 'bg-gray-800 text-gray-400 border-gray-600' },
    seeded:     { label: '📚 Seeded',  cls: 'bg-indigo-950 text-indigo-300 border-indigo-700' },
    recorded:   { label: '✍ Recorded', cls: 'bg-teal-950 text-teal-300 border-teal-700' },
    mixed:      { label: '↔ Mixed',    cls: 'bg-cyan-950 text-cyan-300 border-cyan-700' },
  };
  const { label, cls } = cfg[source] ?? cfg['no-match'];
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded border font-bold ${cls}`}>{label}</span>
  );
}

// ── Candidate card ────────────────────────────────────────────────────────────

function CandidateCard({
  cand,
  isSelected,
  onUse,
}: {
  cand: RouteMemoryCandidate;
  isSelected: boolean;
  onUse: (c: RouteMemoryCandidate) => void;
}) {
  const borderCls = isSelected
    ? 'border-green-700 bg-green-950/40'
    : !cand.feasible
    ? 'border-red-800 bg-red-950/20 opacity-70'
    : 'border-[#2a3750] bg-[#1c2639]';

  return (
    <div className={`rounded p-2 border text-xs space-y-0.5 ${borderCls}`}>
      {/* header row */}
      <div className="flex items-center justify-between gap-1 mb-1">
        <span className="font-bold text-white truncate flex-1">{cand.route_id}</span>
        <SourceBadge source={cand.source} />
        {isSelected && <span className="text-green-400 text-[10px] font-bold">★ SELECTED</span>}
        {!cand.feasible && <span className="text-red-400 text-[10px] font-bold">⛔ BLOCKED</span>}
      </div>

      <InfoRow label="Current ETA" value={`${cand.current_estimated_time.toFixed(1)} min`} />
      {cand.historical_avg_time !== null && (
        <InfoRow label="Hist. Avg ETA" value={`${cand.historical_avg_time.toFixed(1)} min`} />
      )}
      <InfoRow label="Trips (hist.)" value={cand.historical_trip_count} />
      <InfoRow label="Distance" value={`${cand.distance_km.toFixed(2)} km`} />
      <InfoRow
        label="Incidents"
        value={
          <span className={cand.incident_count > 0 ? 'text-yellow-400' : 'text-green-400'}>
            {cand.incident_count}
          </span>
        }
      />
      <InfoRow
        label="Closure"
        value={
          cand.has_closure
            ? <span className="text-red-400">⛔ YES</span>
            : <span className="text-green-400">Clear</span>
        }
      />
      <InfoRow label="Score" value={cand.score === 999 ? 'N/A' : cand.score.toFixed(4)} />

      {cand.rejection_reason && (
        <div className="text-red-400 text-[10px] mt-1 italic leading-tight">
          Rejected: {cand.rejection_reason}
        </div>
      )}
      {cand.selection_reason && (
        <div className="text-green-300 text-[10px] mt-1 italic leading-tight">
          {cand.selection_reason}
        </div>
      )}

      {cand.feasible && !isSelected && (
        <button
          onClick={() => onUse(cand)}
          className="mt-1 w-full bg-blue-900 hover:bg-blue-800 text-blue-200 text-[10px] font-bold py-0.5 rounded border border-blue-700 transition-colors"
        >
          Use This Route
        </button>
      )}
    </div>
  );
}

// ── History stats row ─────────────────────────────────────────────────────────

function HistStatsRow({ stat }: { stat: RouteHistorySummary }) {
  return (
    <div className="rounded p-1.5 border border-[#2a3750] bg-[#1c2639] text-xs space-y-0.5">
      <div className="flex justify-between">
        <span className="text-purple-300 font-bold">{stat.route_id}</span>
        <span className="text-[#64748b]">{stat.trip_count} trip{stat.trip_count !== 1 ? 's' : ''}</span>
      </div>
      <div className="flex gap-3 text-[10px]">
        <span className="text-[#94a3b8]">Avg: <span className="text-white">{stat.avg_travel_time} min</span></span>
        <span className="text-[#94a3b8]">Best: <span className="text-green-400">{stat.best_travel_time} min</span></span>
        <span className="text-[#94a3b8]">Dev: <span className={stat.deviation_frequency > 0.3 ? 'text-yellow-400' : 'text-white'}>{(stat.deviation_frequency * 100).toFixed(0)}%</span></span>
      </div>
    </div>
  );
}

// ── Journey history row ───────────────────────────────────────────────────────

function JourneyRow({ j }: { j: JourneyRecord }) {
  return (
    <div className="rounded p-1.5 border border-[#2a3750] bg-[#161e2e] text-[10px] space-y-0.5">
      <div className="flex justify-between">
        <span className="text-[#94a3b8] font-semibold">{j.journey_id}</span>
        <span className={j.source === 'seeded' ? 'text-indigo-300' : 'text-teal-300'}>
          {j.source}
        </span>
      </div>
      <div className="flex gap-2 text-[#64748b]">
        <span>Route: <span className="text-white">{j.route_id}</span></span>
        <span>Actual: <span className="text-white">{j.actual_travel_time_minutes} min</span></span>
        <span className={j.deviation_occurred ? 'text-yellow-400' : 'text-green-400'}>
          {j.deviation_occurred ? '⚠ deviated' : '✓ clean'}
        </span>
      </div>
      <div className="text-[#475569]">{j.completed_at.split('T')[0]}</div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

type RMITab = 'analysis' | 'history';
type OpStatus = 'idle' | 'loading' | 'success' | 'error';

interface Props {
  rmiResult: RMIResult | null;
  vehicle: VehicleState | null;
  altRoutes: AlternativeRoute[];
  onUseRoute: (routeId: string, waypoints: Coordinate[]) => void;
}

export default function RouteMemoryPanel({ rmiResult, vehicle, altRoutes, onUseRoute }: Props) {
  const [activeTab, setActiveTab] = useState<RMITab>('analysis');
  const [historyData, setHistoryData] = useState<JourneyRecord[] | null>(null);
  const [compareData, setCompareData] = useState<RMIResult | null>(null);
  const [opStatus, setOpStatus] = useState<OpStatus>('idle');
  const [opMessage, setOpMessage] = useState('');
  const [recordStatus, setRecordStatus] = useState<OpStatus>('idle');
  const [recordMsg, setRecordMsg] = useState('');
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(
    rmiResult?.selected_route?.route_id ?? null,
  );
  const [expandedLog, setExpandedLog] = useState(false);

  // Use the live rmi from simulation state, or the on-demand compare result
  const rmi = compareData ?? rmiResult;

  const handleViewHistory = useCallback(async () => {
    setOpStatus('loading');
    setOpMessage('');
    try {
      const data = await fetchRouteMemoryHistory();
      setHistoryData(data.journeys);
      setActiveTab('history');
      setOpStatus('success');
      setOpMessage(`${data.total} journey records loaded.`);
    } catch (e) {
      setOpStatus('error');
      setOpMessage((e as Error).message ?? 'Failed to load history.');
    }
  }, []);

  const handleCompare = useCallback(async () => {
    if (!vehicle) return;
    setOpStatus('loading');
    setOpMessage('');
    try {
      const data = await fetchRouteMemoryCompare(vehicle.id);
      setCompareData(data);
      setSelectedCandidateId(data.selected_route?.route_id ?? null);
      setActiveTab('analysis');
      setOpStatus('success');
      setOpMessage('Comparison updated from current conditions.');
    } catch (e) {
      setOpStatus('error');
      setOpMessage((e as Error).message ?? 'Compare failed.');
    }
  }, [vehicle]);

  const handleUseRoute = useCallback((cand: RouteMemoryCandidate) => {
    setSelectedCandidateId(cand.route_id);
    onUseRoute(cand.route_id, cand.waypoints);
    setOpMessage(`Route ${cand.route_id} set as recommended route.`);
    setOpStatus('success');
  }, [onUseRoute]);

  const handleRecordJourney = useCallback(async () => {
    if (!vehicle || !rmi?.selected_route) return;
    setRecordStatus('loading');
    setRecordMsg('');
    try {
      const sel = rmi.selected_route;
      const origin = vehicle.planned_route[0] ?? vehicle.current_position;
      const dist = routeDistKm(sel.waypoints);
      const result = await recordJourney(vehicle.id, {
        vehicle_id:                 vehicle.id,
        origin:                     { lat: origin.lat, lng: origin.lng },
        destination:                { lat: vehicle.destination.lat, lng: vehicle.destination.lng },
        route_id:                   sel.route_id,
        route_coordinates:          sel.waypoints,
        route_distance_km:          dist,
        actual_travel_time_minutes: vehicle.predicted_eta_minutes,
        planned_travel_time_minutes: vehicle.planned_eta_minutes,
        deviation_occurred:         vehicle.deviation_detected,
        incident_exposure:          sel.incident_count,
        outcome:                    vehicle.status === 'arrived' ? 'completed' : 'in_progress',
      });
      setRecordStatus('success');
      setRecordMsg(result.message);
    } catch (e) {
      setRecordStatus('error');
      setRecordMsg((e as Error).message ?? 'Record failed.');
    }
  }, [vehicle, rmi]);

  const handleReset = useCallback(async () => {
    if (!window.confirm('Reset route memory to seeded demonstration records?')) return;
    setOpStatus('loading');
    setOpMessage('');
    try {
      const result = await resetRouteMemory();
      setCompareData(null);
      setHistoryData(null);
      setSelectedCandidateId(null);
      setOpStatus('success');
      setOpMessage(result.message);
    } catch (e) {
      setOpStatus('error');
      setOpMessage((e as Error).message ?? 'Reset failed.');
    }
  }, []);

  const displayedRmi = rmi;

  return (
    <div className="bg-[#161e2e] rounded-lg overflow-y-auto h-full text-xs">
      {/* ── Header ─────────────────────────────── */}
      <div className="p-2 border-b border-[#2a3750] bg-[#1c2639] sticky top-0 z-10">
        <div className="flex items-center justify-between mb-1">
          <span className="text-white font-bold text-sm">🧠 Route Memory Intelligence</span>
          {displayedRmi && <MemorySourceBadge source={displayedRmi.memory_source} />}
        </div>
        <div className="text-[#64748b] text-[10px]">[SIMULATED] Historical route experience</div>
      </div>

      {/* ── Controls ────────────────────────────── */}
      <div className="p-2 border-b border-[#2a3750] space-y-1.5">
        <div className="flex gap-1 flex-wrap">
          <button
            onClick={handleViewHistory}
            disabled={opStatus === 'loading'}
            className="flex-1 bg-[#1c2639] hover:bg-[#2a3750] text-[#94a3b8] hover:text-white text-[10px] font-bold py-1 px-2 rounded border border-[#2a3750] transition-colors disabled:opacity-50"
          >
            📋 View History
          </button>
          <button
            onClick={handleCompare}
            disabled={!vehicle || opStatus === 'loading'}
            className="flex-1 bg-[#1c2639] hover:bg-[#2a3750] text-[#94a3b8] hover:text-white text-[10px] font-bold py-1 px-2 rounded border border-[#2a3750] transition-colors disabled:opacity-50"
          >
            ⚖️ Compare
          </button>
          <button
            onClick={handleReset}
            disabled={opStatus === 'loading'}
            className="bg-[#1c2639] hover:bg-red-950 text-red-400 hover:text-red-300 text-[10px] font-bold py-1 px-2 rounded border border-red-900 transition-colors disabled:opacity-50"
          >
            ↺ Reset
          </button>
        </div>

        {/* Record journey button */}
        <button
          onClick={handleRecordJourney}
          disabled={!vehicle || !rmi?.selected_route || recordStatus === 'loading'}
          className="w-full bg-teal-950 hover:bg-teal-900 text-teal-300 text-[10px] font-bold py-1 px-2 rounded border border-teal-800 transition-colors disabled:opacity-40"
        >
          {recordStatus === 'loading' ? '⏳ Recording…' : '✍ Record Completed Journey'}
        </button>

        {/* Status messages */}
        {opStatus !== 'idle' && opMessage && (
          <div className={`text-[10px] px-2 py-0.5 rounded ${
            opStatus === 'error' ? 'bg-red-950 text-red-300 border border-red-800'
            : opStatus === 'loading' ? 'bg-blue-950 text-blue-300 border border-blue-800 animate-pulse'
            : 'bg-green-950 text-green-300 border border-green-800'
          }`}>
            {opStatus === 'loading' ? '⏳ ' : opStatus === 'error' ? '⚠ ' : '✓ '}
            {opMessage}
          </div>
        )}
        {recordStatus !== 'idle' && recordMsg && (
          <div className={`text-[10px] px-2 py-0.5 rounded ${
            recordStatus === 'error' ? 'bg-red-950 text-red-300 border border-red-800'
            : 'bg-teal-950 text-teal-300 border border-teal-800'
          }`}>
            {recordStatus === 'error' ? '⚠ ' : '✓ '}{recordMsg}
          </div>
        )}
      </div>

      {/* ── Tabs ────────────────────────────────── */}
      <div className="flex border-b border-[#2a3750] sticky top-[72px] bg-[#161e2e] z-10">
        {(['analysis', 'history'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-1 text-[10px] font-bold uppercase tracking-wider transition-colors ${
              activeTab === tab
                ? 'bg-[#1c2639] text-white border-b-2 border-purple-500'
                : 'text-[#64748b] hover:text-white hover:bg-[#161e2e]'
            }`}
          >
            {tab === 'analysis' ? '🧠 Analysis' : '📋 History'}
          </button>
        ))}
      </div>

      <div className="p-2 space-y-2">

        {/* ── ANALYSIS TAB ──────────────────────── */}
        {activeTab === 'analysis' && (
          <>
            {!displayedRmi && (
              <div className="text-[#64748b] text-xs text-center py-4">
                Start the simulation to run Route Memory Analysis, or click ⚖️ Compare.
              </div>
            )}

            {displayedRmi && (
              <>
                {/* Summary cards */}
                <div className="grid grid-cols-2 gap-1">
                  <div className="bg-[#1c2639] rounded p-1.5 border border-[#2a3750] text-center">
                    <div className="text-white font-bold text-sm">
                      {displayedRmi.matched_journeys_count}
                    </div>
                    <div className="text-[#64748b] text-[10px]">Matched Journeys</div>
                  </div>
                  <div className="bg-[#1c2639] rounded p-1.5 border border-[#2a3750] text-center">
                    <div className={`font-bold text-sm ${displayedRmi.estimated_time_saved_minutes > 0 ? 'text-green-400' : 'text-[#94a3b8]'}`}>
                      {displayedRmi.estimated_time_saved_minutes > 0 ? '-' : ''}{Math.abs(displayedRmi.estimated_time_saved_minutes).toFixed(1)} min
                    </div>
                    <div className="text-[#64748b] text-[10px]">Est. Time Saved</div>
                  </div>
                </div>

                {/* Current O/D */}
                {vehicle && (
                  <>
                    <SectionTitle>Current Journey</SectionTitle>
                    <InfoRow
                      label="Origin"
                      value={`${vehicle.planned_route[0]?.lat.toFixed(4) ?? '—'}, ${vehicle.planned_route[0]?.lng.toFixed(4) ?? '—'}`}
                    />
                    <InfoRow
                      label="Destination"
                      value={`${vehicle.destination.lat.toFixed(4)}, ${vehicle.destination.lng.toFixed(4)}`}
                    />
                    <InfoRow
                      label="Predicted ETA"
                      value={`${vehicle.predicted_eta_minutes.toFixed(1)} min`}
                      accent={vehicle.delay_minutes > 2}
                    />
                  </>
                )}

                {/* Historical statistics */}
                {displayedRmi.historical_statistics.length > 0 && (
                  <>
                    <SectionTitle>Historical Route Statistics</SectionTitle>
                    <div className="space-y-1">
                      {displayedRmi.historical_statistics.map(s => (
                        <HistStatsRow key={s.route_id} stat={s} />
                      ))}
                    </div>
                  </>
                )}

                {/* Candidate routes */}
                {displayedRmi.candidate_routes.length > 0 && (
                  <>
                    <SectionTitle>Candidate Route Comparison</SectionTitle>
                    <div className="space-y-1.5">
                      {displayedRmi.candidate_routes.map(c => (
                        <CandidateCard
                          key={c.route_id}
                          cand={c}
                          isSelected={c.route_id === (selectedCandidateId ?? displayedRmi.selected_route?.route_id)}
                          onUse={handleUseRoute}
                        />
                      ))}
                    </div>
                  </>
                )}

                {/* Rejected */}
                {displayedRmi.rejected_routes.length > 0 && (
                  <>
                    <SectionTitle>Rejected Routes</SectionTitle>
                    {displayedRmi.rejected_routes.map(r => (
                      <div key={r.route_id} className="rounded p-1.5 border border-red-900 bg-red-950/20 space-y-0.5">
                        <span className="text-red-400 font-bold">⛔ {r.route_id}</span>
                        <div className="text-red-300 text-[10px] italic">{r.reason}</div>
                      </div>
                    ))}
                  </>
                )}

                {/* Selection reason */}
                {displayedRmi.selection_reason && (
                  <>
                    <SectionTitle>Selection Rationale</SectionTitle>
                    <div className="bg-[#1c2639] rounded p-2 border border-[#2a3750] text-[#94a3b8] text-[10px] leading-relaxed italic">
                      {displayedRmi.selection_reason}
                    </div>
                  </>
                )}

                {/* Decision log */}
                {displayedRmi.log_events.length > 0 && (
                  <>
                    <SectionTitle>
                      Agent Decision Log{' '}
                      <button
                        onClick={() => setExpandedLog(v => !v)}
                        className="text-blue-400 hover:text-blue-300 text-[10px] normal-case ml-1"
                      >
                        {expandedLog ? '▲ hide' : '▼ show'}
                      </button>
                    </SectionTitle>
                    {expandedLog && (
                      <div className="space-y-0.5 max-h-40 overflow-y-auto">
                        {displayedRmi.log_events.map((ev, i) => (
                          <div key={i} className="text-[#64748b] text-[10px] leading-tight py-0.5 border-b border-[#2a3750]">
                            {ev}
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </>
            )}
          </>
        )}

        {/* ── HISTORY TAB ───────────────────────── */}
        {activeTab === 'history' && (
          <>
            {!historyData && (
              <div className="text-[#64748b] text-xs text-center py-4">
                Click 📋 View History to load journey records.
              </div>
            )}
            {historyData && (
              <>
                <div className="text-[#64748b] text-[10px] mb-1">
                  {historyData.length} total journey records. All data is [SIMULATED].
                </div>
                <div className="space-y-1 max-h-[400px] overflow-y-auto">
                  {historyData.map(j => (
                    <JourneyRow key={j.journey_id} j={j} />
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
