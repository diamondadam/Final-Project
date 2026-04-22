import React, { useMemo } from 'react';
import { useTwinStore } from '../../store/twinStore';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export function TelemetryChart() {
  const { tickHistory } = useTwinStore();

  const chartData = useMemo(() => {
    return tickHistory.map((entry) => ({
      tick: entry.tick,
      velocity: entry.speed * 3.6, // convert fps to roughly km/h visual scale
    }));
  }, [tickHistory]);

  const currentVelocity = chartData.length > 0 ? chartData[chartData.length - 1].velocity : 0;
  
  // Calculate Peak Velocity
  const peakVelocity = useMemo(() => {
    if (chartData.length === 0) return 0;
    return Math.max(...chartData.map(d => d.velocity));
  }, [chartData]);

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border-dim)] rounded-xl p-5 flex flex-col h-full min-h-[300px]">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-[clamp(11px,1.2vw,14px)] font-bold text-white tracking-widest uppercase mb-1">Real-Time Telemetry</h2>
          <div className="text-[clamp(8px,1vw,10px)] text-[var(--rt-muted)] uppercase tracking-wider">Rolling Stock Performance Logs</div>
        </div>
        <div className="flex gap-4 text-[clamp(8px,1vw,10px)] font-bold tracking-widest uppercase">
          <div className="flex items-center gap-1.5 text-white">
            <span className="w-2 h-2 rounded-full bg-[var(--rt-blue)]"></span> VELOCITY
          </div>
        </div>
      </div>

      <div className="flex-1 w-full relative min-h-[160px] mb-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--rt-border-dim)" vertical={false} />
            <XAxis dataKey="tick" hide />
            <YAxis 
              tick={{ fontSize: 10, fill: 'var(--rt-muted)' }} 
              axisLine={false}
              tickLine={false}
              domain={[-20, 'auto']}
            />
            <Tooltip
              contentStyle={{ background: 'var(--rt-bg)', border: '1px solid var(--rt-border-dim)', borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: 'var(--rt-muted)', marginBottom: 4 }}
              itemStyle={{ padding: '2px 0' }}
            />
            <Line
              type="monotone"
              dataKey="velocity"
              name="Velocity (km/h)"
              stroke="var(--rt-blue)"
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-3 mt-auto">
        <div className="bg-[var(--rt-bg)] border border-[var(--rt-border-dim)] rounded-lg p-3">
          <div className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)] uppercase tracking-wider mb-2">Current Velocity</div>
          <div className="text-[clamp(16px,2vw,20px)] font-bold text-white leading-none">
            {currentVelocity.toFixed(1)} <span className="text-[clamp(8px,1vw,10px)] text-[var(--rt-muted)] font-normal">KM/H</span>
          </div>
        </div>
        <div className="bg-[var(--rt-bg)] border border-[var(--rt-border-dim)] rounded-lg p-3">
          <div className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)] uppercase tracking-wider mb-2">Peak Velocity</div>
          <div className="text-[clamp(16px,2vw,20px)] font-bold text-white leading-none">
            {peakVelocity.toFixed(1)} <span className="text-[clamp(8px,1vw,10px)] text-[var(--rt-muted)] font-normal">KM/H</span>
          </div>
        </div>
      </div>
    </div>
  );
}
