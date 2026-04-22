import React from 'react';
import { useTwinStore } from '../../store/twinStore';
import { CLASS_COLORS } from '../../types';

export function SegmentStatusList() {
  const { state } = useTwinStore();

  const segments = state?.segments || [];
  
  const healthyCount = segments.filter(s => s.map_state_name === 'Healthy').length;
  const degradedCount = segments.filter(s => s.map_state_name === 'Degraded').length;
  const damagedCount = segments.filter(s => s.map_state_name === 'Damaged').length;
  
  const total = segments.length || 1;
  const healthyPct = (healthyCount / total) * 100;
  const degradedPct = (degradedCount / total) * 100;
  const damagedPct = (damagedCount / total) * 100;

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border-dim)] rounded-xl p-5 flex flex-col h-full min-h-[300px]">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-[clamp(11px,1.2vw,14px)] font-bold text-white tracking-widest uppercase">Segment Status</h2>
        <svg className="w-5 h-5 text-[var(--rt-muted)] cursor-help" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>

      <div className="flex-1 overflow-y-auto pr-2 space-y-3 custom-scrollbar">
        {segments.map((seg) => {
          const statusColors = CLASS_COLORS[seg.map_state_name];
          const isHealthy = seg.map_state_name === 'Healthy';
          const isDamaged = seg.map_state_name === 'Damaged';

          return (
            <div key={seg.id} className="bg-[var(--rt-bg)] border border-[var(--rt-border-dim)] rounded-lg p-3 flex justify-between items-center">
              <div>
                <div className="text-[clamp(8px,1vw,10px)] text-[var(--rt-muted)] uppercase tracking-wider mb-1">
                  Segment {seg.id < 10 ? `0${seg.id}` : seg.id}
                </div>
                <div className={`text-[clamp(11px,1.2vw,14px)] font-semibold tracking-wide ${isHealthy ? 'text-white' : statusColors.text}`}>
                  {seg.map_state_name === 'Healthy' ? 'Healthy Segment' : 
                   seg.map_state_name === 'Degraded' ? 'Degraded Health' : 'Damaged - CRITICAL'}
                </div>
              </div>
              <div className="flex items-center justify-center">
                {isHealthy ? (
                  <div className="w-8 h-8 rounded-md border border-[var(--rt-green)]/30 flex items-center justify-center">
                    <svg className="w-5 h-5 text-[var(--rt-green)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                ) : isDamaged ? (
                   <div className="w-8 h-8 rounded-md border border-[var(--rt-red)]/50 bg-[var(--rt-red)]/10 flex items-center justify-center animate-pulse">
                     <span className="text-[var(--rt-red)] font-bold">!</span>
                   </div>
                ) : (
                  <div className="w-8 h-8 rounded-md border border-[var(--rt-amber)]/50 bg-[var(--rt-amber)]/10 flex items-center justify-center">
                    <span className="text-[var(--rt-amber)] font-bold">⚠</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {segments.length === 0 && (
          <div className="text-[var(--rt-muted)] text-[clamp(9px,1vw,12px)] text-center py-8">Waiting for segment data...</div>
        )}
      </div>

      <div className="mt-6 pt-4 border-t border-[var(--rt-border-dim)]">
        <div className="text-[clamp(8px,1vw,10px)] text-[var(--rt-muted)] uppercase tracking-wider mb-2">Overall Network Integrity</div>
        <div className="flex h-2 rounded-full overflow-hidden mb-2 bg-[var(--rt-border-dim)]">
          <div className="bg-[var(--rt-green)] h-full transition-all duration-500" style={{ width: `${healthyPct}%` }} />
          <div className="bg-[var(--rt-amber)] h-full transition-all duration-500" style={{ width: `${degradedPct}%` }} />
          <div className="bg-[var(--rt-red)] h-full transition-all duration-500" style={{ width: `${damagedPct}%` }} />
        </div>
        <div className="flex justify-between text-[clamp(8px,1vw,10px)] text-[var(--rt-muted)] font-mono">
          <span className="text-[var(--rt-green)]">{healthyPct.toFixed(0)}% NOMINAL</span>
          {degradedPct > 0 && <span className="text-[var(--rt-amber)]">{degradedPct.toFixed(0)}% CAUTION</span>}
          {damagedPct > 0 && <span className="text-[var(--rt-red)] animate-pulse">{damagedPct.toFixed(0)}% CRITICAL</span>}
        </div>
      </div>
    </div>
  );
}
