import React from 'react';
import { useTwinStore } from '../../store/twinStore';

export function LiveFeedHUD() {
  const { state } = useTwinStore();

  const isDamaged = state?.alert?.includes('DAMAGE') || state?.segments?.find(s => s.id === state?.train_segment)?.map_state_name === 'Damaged';
  
  return (
    <div className="relative rounded-xl overflow-hidden border border-[var(--rt-border-dim)] bg-[var(--rt-surface)] flex flex-col h-full min-h-[300px]">
      <div className="absolute inset-0 z-0">
        {/* Unreal Engine Pixel Streaming iframe */}
        <iframe 
          src="http://127.0.0.1:8888" 
          title="Unreal Engine Live Feed" 
          className="w-full h-full border-0 pointer-events-auto"
          allow="autoplay; fullscreen; xr-spatial-tracking"
        />
        {/* HUD Scanline overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] pointer-events-none z-10" />
      </div>

      <div className="relative z-20 p-4 flex flex-col h-full justify-between">
        <div className="flex justify-between items-start">
          <div className="bg-black/50 backdrop-blur-md px-3 py-2 rounded-md border border-white/10">
            <div className="text-[clamp(7px,0.8vw,10px)] font-bold tracking-widest text-[var(--rt-muted)] uppercase mb-1">
              Live Feed :: Sector 04-A
            </div>
            <div className="text-[clamp(12px,1.5vw,18px)] font-bold text-white tracking-widest">
              UE5 RENDERING <span className="inline-block w-2 h-2 rounded-full bg-[var(--rt-amber)] animate-pulse ml-2" />
            </div>
          </div>
          
          <div className="flex gap-2">
            <div className="bg-black/50 backdrop-blur-md px-3 py-1.5 rounded-md border border-white/10 text-right">
              <div className="text-[clamp(6px,0.7vw,9px)] text-[var(--rt-muted)] uppercase tracking-wider">LAT</div>
              <div className="text-[clamp(9px,1vw,12px)] font-mono text-[var(--rt-text)]">51.5074° N</div>
            </div>
            <div className="bg-black/50 backdrop-blur-md px-3 py-1.5 rounded-md border border-white/10 text-right">
              <div className="text-[clamp(6px,0.7vw,9px)] text-[var(--rt-muted)] uppercase tracking-wider">LONG</div>
              <div className="text-[clamp(9px,1vw,12px)] font-mono text-[var(--rt-text)]">0.1278° W</div>
            </div>
          </div>
        </div>

        {/* Central Alert */}
        {isDamaged && (
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-[var(--rt-red)]/20 backdrop-blur-md border border-[var(--rt-red)]/50 p-6 rounded-lg text-center animate-pulse w-3/4 max-w-md">
            <div className="flex items-center justify-center gap-2 mb-2">
              <svg className="w-8 h-8 text-[var(--rt-red)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h2 className="text-[clamp(14px,1.8vw,20px)] font-bold text-[var(--rt-red)] tracking-widest">DAMAGED SEGMENT DETECTED</h2>
            </div>
            <p className="text-[clamp(9px,1vw,12px)] text-[var(--rt-red)] tracking-widest uppercase mt-2 font-semibold">Automatic Emergency Braking Triggered</p>
          </div>
        )}

        <div className="mt-auto flex justify-center">
          <div className="bg-black/60 backdrop-blur-md px-6 py-3 rounded-full border border-white/10 flex items-center gap-4 w-2/3 max-w-sm">
            <span className="text-[clamp(9px,1vw,12px)] font-mono text-[var(--rt-muted)] w-12 text-right">0 km/h</span>
            <div className="flex-1 h-1.5 bg-[var(--rt-border-dim)] rounded-full overflow-hidden">
              <div 
                className={`h-full ${isDamaged ? 'bg-[var(--rt-red)]' : 'bg-[var(--rt-blue)]'} transition-all duration-300 ease-out`}
                style={{ width: `${Math.min(100, Math.max(0, ((state?.commanded_speed_fps || 0) * 3.6) / 245 * 100))}%` }}
              />
            </div>
            <span className="text-[clamp(9px,1vw,12px)] font-mono text-[var(--rt-text)] w-16">
               {((state?.commanded_speed_fps || 0) * 3.6).toFixed(1)} km/h
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
