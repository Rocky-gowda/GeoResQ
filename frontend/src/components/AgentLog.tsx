import React from 'react';
import { AgentDecision } from '../types';

interface Props {
  decisions: AgentDecision[];
  explanation: string;
}

const AGENT_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  '[Vehicle Agent]': { bg: 'bg-blue-950', text: 'text-blue-300', border: 'border-blue-700' },
  '[Deviation Agent]': { bg: 'bg-yellow-950', text: 'text-yellow-300', border: 'border-yellow-700' },
  '[Cause Agent]': { bg: 'bg-red-950', text: 'text-red-300', border: 'border-red-700' },
  '[Prediction Agent]': { bg: 'bg-purple-950', text: 'text-purple-300', border: 'border-purple-700' },
  '[Route Agent]': { bg: 'bg-green-950', text: 'text-green-300', border: 'border-green-700' },
  '[Decision Agent]': { bg: 'bg-orange-950', text: 'text-orange-300', border: 'border-orange-700' },
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return iso.slice(11, 19);
  }
}

export default function AgentLog({ decisions, explanation }: Props) {
  const reversed = [...decisions].reverse();

  return (
    <div className="bg-[#161e2e] rounded-lg overflow-hidden h-full flex flex-col">
      {/* Explanation */}
      <div className="p-3 border-b border-[#2a3750] bg-[#12203a]">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-xs font-bold text-white uppercase tracking-widest">💬 Why this decision?</span>
        </div>
        <p className="text-xs text-[#93c5fd] leading-relaxed italic">{explanation || '[SIMULATED] Awaiting simulation...'}</p>
      </div>

      {/* Log header */}
      <div className="px-3 py-2 border-b border-[#2a3750] bg-[#1c2639]">
        <h3 className="text-white text-xs font-bold uppercase tracking-widest">Agent Decision Log</h3>
      </div>

      {/* Log entries */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {reversed.length === 0 ? (
          <p className="text-[#64748b] text-xs p-2">Awaiting agent activity...</p>
        ) : (
          reversed.map((d, idx) => {
            const colors = AGENT_COLORS[d.agent] ?? { bg: 'bg-[#1c2639]', text: 'text-white', border: 'border-[#2a3750]' };
            return (
              <div key={`${d.timestamp}-${idx}`} className={`rounded border p-2 text-xs ${colors.bg} ${colors.border}`}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className={`font-bold ${colors.text}`}>{d.agent}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${colors.bg} ${colors.border} border ${colors.text}`}>
                      {d.action}
                    </span>
                    <span className="text-[10px] text-[#64748b]">{formatTime(d.timestamp)}</span>
                  </div>
                </div>
                <p className="text-[#94a3b8] leading-snug">{d.reasoning}</p>
                <div className="mt-0.5 text-[10px] text-[#64748b]">
                  Confidence: {(d.confidence * 100).toFixed(0)}%
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
