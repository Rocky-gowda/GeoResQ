import React from 'react';
import { DispatchConsideration } from '../types';

interface Props {
  dispatch: DispatchConsideration | null;
}

export default function DispatchPanel({ dispatch }: Props) {
  if (!dispatch || !dispatch.triggered) {
    return (
      <div className="bg-[#161e2e] rounded-lg p-3 border border-[#2a3750]">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[#64748b] text-xs font-bold uppercase tracking-widest">🚁 Dispatch Consideration</span>
        </div>
        <p className="text-[#64748b] text-xs">No dispatch consideration at this time. Primary vehicle is on track.</p>
      </div>
    );
  }

  return (
    <div className="bg-[#1a1209] rounded-lg p-3 border border-yellow-700 animate-pulse">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-yellow-400 text-xs font-bold uppercase tracking-widest">⚡ Dispatch Consideration Active</span>
        <span className="bg-yellow-900 text-yellow-300 text-[10px] px-2 py-0.5 rounded border border-yellow-700 font-semibold">DECISION SUPPORT ONLY</span>
      </div>
      <p className="text-yellow-200 text-xs leading-relaxed mb-3">{dispatch.reason}</p>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-red-950 border border-red-800 rounded p-2">
          <div className="text-red-400 font-semibold mb-0.5">Primary Vehicle</div>
          <div className="text-white font-bold">{dispatch.primary_vehicle?.toUpperCase()}</div>
          <div className="text-[#94a3b8]">ETA: {dispatch.primary_eta?.toFixed(1)} min</div>
        </div>
        <div className="bg-green-950 border border-green-800 rounded p-2">
          <div className="text-green-400 font-semibold mb-0.5">Alternative Vehicle</div>
          <div className="text-white font-bold">{dispatch.alternative_vehicle?.toUpperCase()}</div>
          <div className="text-[#94a3b8]">ETA: {dispatch.alt_eta?.toFixed(1)} min</div>
        </div>
      </div>
      <p className="text-[#64748b] text-[10px] mt-2 italic">{dispatch.note}</p>
    </div>
  );
}
