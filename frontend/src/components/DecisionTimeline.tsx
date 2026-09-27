import React from 'react';
import { DecisionEvent } from '../types';

interface Props {
  events: DecisionEvent[];
}

function severityColor(severity: string): string {
  if (severity === 'critical') return 'bg-red-900 border-red-600 text-red-300';
  if (severity === 'warning') return 'bg-yellow-950 border-yellow-700 text-yellow-300';
  return 'bg-[#1c2639] border-[#2a3750] text-[#94a3b8]';
}

function severityDot(severity: string): string {
  if (severity === 'critical') return 'bg-red-500';
  if (severity === 'warning') return 'bg-yellow-500';
  return 'bg-blue-500';
}

function eventIcon(type: string): string {
  const map: Record<string, string> = {
    gps_update: '📡',
    congestion_detected: '🚦',
    accident_detected: '💥',
    deviation_detected: '⚠️',
    back_on_route: '✅',
    cause_identified: '🔍',
    eta_updated: '⏱️',
    routes_generated: '🗺️',
    recommendation_generated: '✨',
    deviation_started: '🔀',
  };
  return map[type] ?? '📋';
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return iso.slice(11, 19);
  }
}

export default function DecisionTimeline({ events }: Props) {
  const reversed = [...events].reverse();

  return (
    <div className="bg-[#161e2e] rounded-lg overflow-hidden h-full">
      <div className="p-2 border-b border-[#2a3750] bg-[#1c2639]">
        <h3 className="text-white text-xs font-bold uppercase tracking-widest">Decision Timeline</h3>
      </div>
      <div className="overflow-y-auto h-[calc(100%-36px)] p-2 space-y-1.5">
        {reversed.length === 0 ? (
          <p className="text-[#64748b] text-xs p-2">Awaiting events...</p>
        ) : (
          reversed.map((ev, idx) => (
            <div
              key={`${ev.timestamp}-${idx}`}
              className={`flex items-start gap-2 px-2 py-1.5 rounded border text-xs ${severityColor(ev.severity)}`}
            >
              <div className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${severityDot(ev.severity)}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1 flex-wrap">
                  <span>{eventIcon(ev.event_type)}</span>
                  <span className="font-semibold uppercase tracking-wide opacity-80 text-[10px]">
                    {ev.event_type.replace(/_/g, ' ')}
                  </span>
                </div>
                <p className="mt-0.5 leading-snug opacity-90">{ev.description}</p>
                <p className="text-[10px] opacity-50 mt-0.5">{formatTime(ev.timestamp)}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
