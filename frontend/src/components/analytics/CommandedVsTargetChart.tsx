import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts'
import { useTwinStore } from '../../store/twinStore'
import { getVSafeHistory } from './utils'

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#18181b',
    border: '1px solid #3f3f46',
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: '#a1a1aa' },
}

export function CommandedVsTargetChart() {
  const { tickHistory, positionHistory, segmentBeliefHistory } = useTwinStore()
  const chartData = getVSafeHistory(tickHistory, positionHistory, segmentBeliefHistory)

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 h-full">
      <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
        Commanded vs. v_safe Target
      </p>
      {chartData.length < 2 ? (
        <div className="flex items-center justify-center h-32 text-zinc-600 text-sm">
          Waiting for data…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={chartData}>
            <ReferenceLine y={3.0} stroke="#3f3f46" strokeDasharray="4 2" />
            <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#52525b' }} />
            <YAxis
              domain={[0, 3.5]}
              tick={{ fontSize: 10, fill: '#52525b' }}
              width={28}
            />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(val: number, name: string) => [
                `${val.toFixed(2)} fps`,
                name === 'vSafe' ? 'v_safe target' : 'commanded',
              ]}
            />
            <Legend
              wrapperStyle={{ fontSize: 10, color: '#71717a' }}
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
              stroke="#34d399"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
