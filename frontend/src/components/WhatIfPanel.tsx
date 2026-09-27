import React from 'react';
import { WhatIfOption } from '../types';

interface Props {
  options: Record<string, WhatIfOption>;
  baseEta: number;
}

const optionColors = [
  'border-blue-700 bg-blue-950 text-blue-300',
  'border-gray-600 bg-gray-900 text-gray-400',
  'border-green-700 bg-green-950 text-green-300',
  'border-purple-700 bg-purple-950 text-purple-300',
];

export default function WhatIfPanel({ options, baseEta }: Props) {
  const entries = Object.values(options);

  return (
    <div className="bg-[#161e2e] rounded-lg overflow-hidden h-full">
      <div className="p-2 border-b border-[#2a3750] bg-[#1c2639]">
        <h3 className="text-white text-xs font-bold uppercase tracking-widest">⚖️ What-If Comparison</h3>
      </div>
      <div className="p-2 space-y-2">
        {entries.length === 0 ? (
          <p className="text-[#64748b] text-xs p-2">Awaiting route analysis...</p>
        ) : (
          entries.map((opt, idx) => (
            <div
              key={opt.id}
              className={`rounded border p-2 text-xs ${optionColors[idx % optionColors.length]}`}
            >
              <div className="font-bold mb-1">{opt.name}</div>
              <div className="flex justify-between">
                <span className="opacity-70">Predicted ETA</span>
                <span className="font-semibold">{opt.predicted_eta.toFixed(1)} min</span>
              </div>
              <div className="flex justify-between">
                <span className="opacity-70">Delay</span>
                <span className={`font-semibold ${opt.delay > 0 ? 'text-red-400' : 'text-green-400'}`}>
                  {opt.delay > 0 ? '+' : ''}{opt.delay.toFixed(1)} min
                </span>
              </div>
              <div className="flex justify-between">
                <span className="opacity-70">Time Saved</span>
                <span className={`font-semibold ${opt.time_saved > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {opt.time_saved > 0 ? '-' : '+'}{Math.abs(opt.time_saved).toFixed(1)} min
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
