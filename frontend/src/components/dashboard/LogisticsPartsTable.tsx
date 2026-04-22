import React from 'react';
import { useTwinStore } from '../../store/twinStore';
import { CLASS_COLORS } from '../../types';

export function LogisticsPartsTable() {
  const { state, applyCorrection } = useTwinStore();
  const segments = state?.segments || [];

  const handleReplace = (segmentId: number) => {
    // Calling applyCorrection to reset the segment to Healthy (0)
    applyCorrection(segmentId, 0);
  };

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border-dim)] rounded-xl flex flex-col h-full min-h-[300px]">
      <div className="p-5 pb-0 flex justify-between items-center mb-4">
        <div>
          <h2 className="text-[clamp(11px,1.2vw,14px)] font-bold text-white tracking-widest uppercase mb-1">Logistics & Parts</h2>
          <div className="text-[clamp(8px,1vw,10px)] text-[var(--rt-muted)] uppercase tracking-wider">Segment Inventory</div>
        </div>
        <svg className="w-5 h-5 text-[var(--rt-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
        </svg>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-2 px-5 py-2 text-[clamp(8px,1vw,10px)] text-[var(--rt-muted)] uppercase tracking-widest border-b border-[var(--rt-border-dim)] mb-2">
          <div className="col-span-4">Segment</div>
          <div className="col-span-8 text-right">Status</div>
        </div>

        {/* Table Body */}
        <div className="flex-1 overflow-y-auto px-3 custom-scrollbar space-y-1 pb-3">
          {segments.map((seg) => {
            const isDamaged = seg.map_state_name === 'Damaged';
            const isDegraded = seg.map_state_name === 'Degraded';
            const statusColor = isDamaged ? 'text-[var(--rt-red)]' : isDegraded ? 'text-[var(--rt-amber)]' : 'text-[var(--rt-green)]';
            
            const code = seg.id < 10 ? `SG-40${seg.id}` : `SG-4${seg.id}`;

            return (
              <div 
                key={seg.id} 
                className={`grid grid-cols-12 gap-2 px-2 py-3 items-center rounded-lg border ${
                  isDamaged 
                    ? 'bg-[var(--rt-red)]/10 border-[var(--rt-red)]/30' 
                    : 'bg-transparent border-transparent hover:bg-[var(--rt-bg)] hover:border-[var(--rt-border-dim)]'
                } transition-colors`}
              >
                <div className="col-span-4 flex items-center gap-2">
                  {isDamaged && <span className="w-1.5 h-1.5 rounded-full bg-[var(--rt-red)] animate-pulse"></span>}
                  <span className={`text-[clamp(9px,1vw,12px)] font-mono ${isDamaged ? 'text-[var(--rt-red)]' : 'text-[var(--rt-text)]'}`}>{code}</span>
                </div>
                <div className={`col-span-8 text-[clamp(9px,1vw,12px)] font-semibold text-right ${statusColor}`}>
                  {seg.map_state_name.toUpperCase()}
                </div>
                
                {/* Damaged Alert Row Extension */}
                {isDamaged && (
                   <div className="col-span-12 mt-2 pt-2 border-t border-[var(--rt-red)]/20 flex justify-between items-center">
                     <div className="text-[clamp(8px,1vw,10px)] text-[var(--rt-red)] uppercase tracking-wider font-semibold flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                        CRITICAL: REPLACE SEGMENT IMMEDIATELY
                     </div>
                     <button 
                       onClick={() => handleReplace(seg.id)}
                       className="bg-[var(--rt-red)]/20 hover:bg-[var(--rt-red)]/40 text-[var(--rt-red)] border border-[var(--rt-red)]/50 px-3 py-1 rounded text-[clamp(8px,1vw,10px)] uppercase tracking-wider font-bold transition-colors"
                     >
                       * Replace
                     </button>
                   </div>
                )}
              </div>
            );
          })}
          {segments.length === 0 && (
            <div className="text-[var(--rt-muted)] text-[clamp(9px,1vw,12px)] text-center py-8">No inventory data available</div>
          )}
        </div>
      </div>
    </div>
  );
}
