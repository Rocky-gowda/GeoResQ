import React from 'react';
import { VehicleState, AlternativeRoute } from '../types';

interface Props {
  vehicle: VehicleState | null;
  altRoutes: AlternativeRoute[];
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    on_route: 'bg-blue-900 text-blue-300 border border-blue-600',
    deviated: 'bg-red-900 text-red-300 border border-red-600 animate-pulse',
    arrived: 'bg-green-900 text-green-300 border border-green-600',
    dispatched: 'bg-purple-900 text-purple-300 border border-purple-600',
    idle: 'bg-gray-800 text-gray-400 border border-gray-600',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-semibold uppercase tracking-wide ${colors[status] ?? 'bg-gray-800 text-gray-300'}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

function DataRow({ label, value, highlight }: { label: string; value: React.ReactNode; highlight?: boolean }) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-[#2a3750]">
      <span className="text-[#64748b] text-xs">{label}</span>
      <span className={`text-xs font-semibold ${highlight ? 'text-yellow-400' : 'text-white'}`}>{value}</span>
    </div>
  );
}

function CauseTag({ cause, confidence }: { cause: string; confidence: number }) {
  const colorMap: Record<string, string> = {
    accident: 'bg-red-900 text-red-300 border-red-700',
    congestion: 'bg-yellow-900 text-yellow-300 border-yellow-700',
    road_closure: 'bg-orange-900 text-orange-300 border-orange-700',
    wrong_turn: 'bg-purple-900 text-purple-300 border-purple-700',
    gps_anomaly: 'bg-gray-800 text-gray-300 border-gray-600',
    none: 'bg-gray-800 text-gray-500 border-gray-700',
  };
  const c = colorMap[cause] ?? 'bg-gray-800 text-gray-400 border-gray-600';
  return (
    <div className={`flex items-center gap-2 px-2 py-1 rounded border text-xs font-semibold ${c}`}>
      <span className="uppercase tracking-wide">{cause.replace('_', ' ')}</span>
      <span className="opacity-70">{(confidence * 100).toFixed(0)}%</span>
    </div>
  );
}

export default function IntelligencePanel({ vehicle, altRoutes }: Props) {
  if (!vehicle) {
    return (
      <div className="bg-[#161e2e] rounded-lg p-4 text-[#64748b] text-sm h-full flex items-center justify-center">
        No vehicle selected
      </div>
    );
  }

  const recommended = altRoutes.find(r => r.id === vehicle.recommended_route_id);
  const isDelayed = vehicle.delay_minutes > 2;

  return (
    <div className="bg-[#161e2e] rounded-lg overflow-y-auto h-full">
      {/* Header */}
      <div className="p-3 border-b border-[#2a3750] bg-[#1c2639]">
        <div className="flex items-center justify-between mb-1">
          <span className="text-white font-bold text-sm">
            {vehicle.type === 'ambulance' ? '🚑' : '🚒'} {vehicle.name}
          </span>
          <StatusBadge status={vehicle.status} />
        </div>
        <div className="text-[#64748b] text-xs">[SIMULATED] Emergency Vehicle</div>
      </div>

      <div className="p-3 space-y-1">
        <DataRow label="Vehicle ID" value={vehicle.id.toUpperCase()} />
        <DataRow label="Speed" value={`${vehicle.speed_kmh.toFixed(1)} km/h`} />
        <DataRow label="Heading" value={`${vehicle.heading.toFixed(0)}°`} />

        <div className="pt-2 pb-1">
          <div className="text-[#64748b] text-xs uppercase tracking-widest mb-1">ETA Intelligence</div>
          <DataRow label="Planned ETA" value={`${vehicle.planned_eta_minutes.toFixed(1)} min`} />
          <DataRow label="Predicted ETA" value={
            <span className={isDelayed ? 'text-red-400' : 'text-green-400'}>
              {vehicle.predicted_eta_minutes.toFixed(1)} min
            </span>
          } />
          <DataRow
            label="Expected Delay"
            value={
              <span className={vehicle.delay_minutes > 0 ? 'text-red-400' : 'text-green-400'}>
                {vehicle.delay_minutes > 0 ? '+' : ''}{vehicle.delay_minutes.toFixed(1)} min
              </span>
            }
            highlight={vehicle.delay_minutes > 2}
          />
        </div>

        <div className="pt-2 pb-1">
          <div className="text-[#64748b] text-xs uppercase tracking-widest mb-1">Deviation Analysis</div>
          <DataRow
            label="Deviation"
            value={vehicle.deviation_detected
              ? <span className="text-red-400">⚠ YES ({vehicle.deviation_distance_meters.toFixed(0)}m)</span>
              : <span className="text-green-400">None</span>
            }
          />
          {vehicle.deviation_detected && (
            <div className="mt-2">
              <div className="text-[#64748b] text-xs mb-1">Likely Cause</div>
              <CauseTag cause={vehicle.deviation_cause} confidence={vehicle.deviation_confidence} />
            </div>
          )}
        </div>

        {recommended && (
          <div className="pt-2 pb-1">
            <div className="text-[#64748b] text-xs uppercase tracking-widest mb-1">Recommended Route</div>
            <div className="bg-[#0f2314] border border-green-800 rounded p-2 space-y-1">
              <div className="text-green-400 text-xs font-bold">✅ {recommended.name}</div>
              <DataRow label="ETA" value={`${recommended.estimated_time_minutes.toFixed(1)} min`} />
              <DataRow label="Distance" value={`${recommended.distance_km.toFixed(2)} km`} />
              <DataRow
                label="Time Saved"
                value={
                  <span className="text-green-400">
                    {recommended.time_saved_minutes > 0 ? '-' : '+'}{Math.abs(recommended.time_saved_minutes).toFixed(1)} min
                  </span>
                }
              />
              <DataRow label="Incidents" value={recommended.incident_count} />
              <DataRow label="Congestion" value={recommended.congestion_level.toUpperCase()} />
            </div>
          </div>
        )}

        {altRoutes.length > 0 && (
          <div className="pt-2">
            <div className="text-[#64748b] text-xs uppercase tracking-widest mb-1">All Alternatives</div>
            <div className="space-y-1.5">
              {altRoutes.map(r => (
                <div
                  key={r.id}
                  className={`rounded p-2 border text-xs ${r.id === vehicle.recommended_route_id
                    ? 'bg-green-950 border-green-700'
                    : 'bg-[#1c2639] border-[#2a3750]'}`}
                >
                  <div className="flex justify-between">
                    <span className="font-semibold text-white">{r.name}</span>
                    {r.id === vehicle.recommended_route_id && <span className="text-green-400 text-xs">★ BEST</span>}
                  </div>
                  <div className="text-[#64748b] mt-0.5">
                    ETA: {r.estimated_time_minutes.toFixed(1)} min | Score: {r.score.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
