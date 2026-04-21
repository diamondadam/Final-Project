import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts'
import { useTwinStore } from '../../store/twinStore'
import { getVSafeHistory } from './utils'

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#1f2937',
    border: '1px solid #374151',
    borderRadius: 4,
    fontSize: 11,
  },
  labelStyle: { color: '#6b7280' },
}

export function CommandedVsTargetChart() {
  const { tickHistory, positionHistory, segmentBeliefHistory } = useTwinStore()
  const chartData = getVSafeHistory(tickHistory, positionHistory, segmentBeliefHistory)

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Commanded vs. v_safe Target
        </span>
      </div>
      <div className="px-[11px] py-[8px]">
        {chartData.length < 2 ? (
          <div className="flex items-center justify-center h-[120px] text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)]">
            Waiting for data…
          </div>
        ) : (
          <div className="min-h-[120px] lg:min-h-[160px]">
            <ResponsiveContainer width="100%" height="100%" minHeight={120}>
              <LineChart data={chartData}>
                <ReferenceLine y={3.0} stroke="#374151" strokeDasharray="4 2" />
                <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#6b7280' }} />
                <YAxis domain={[0, 3.5]} tick={{ fontSize: 10, fill: '#6b7280' }} width={28} />
                <Tooltip
                  {...TOOLTIP_STYLE}
                  formatter={(val: number, name: string) => [
                    `${val.toFixed(2)} fps`,
                    name === 'vSafe' ? 'v_safe target' : 'commanded',
                  ]}
                />
                <Legend
                  wrapperStyle={{ fontSize: 10, color: '#6b7280' }}
                  formatter={(val) => (val === 'vSafe' ? 'v_safe target' : 'commanded')}
                />
                <Line
                  type="monotone"
                  dataKey="vSafe"
                  stroke="#f59e0b"
                  strokeWidth={1.5}
                  strokeDasharray="5 3"
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="commanded"
                  stroke="#87CEEB"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}
