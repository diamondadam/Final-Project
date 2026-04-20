import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { useTwinStore } from '../../store/twinStore'

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#18181b',
    border: '1px solid #3f3f46',
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: '#a1a1aa' },
  itemStyle: { color: '#818cf8' },
}

export function PositionTimeline() {
  const { positionHistory, state } = useTwinStore()
  const nSegs = state?.segments.length ?? 5

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 flex-1">
      <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
        Train Position
      </p>
      {positionHistory.length < 2 ? (
        <div className="flex items-center justify-center h-16 text-zinc-600 text-sm">
          Waiting for data…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={100}>
          <LineChart data={positionHistory}>
            <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#52525b' }} />
            <YAxis
              domain={[0, nSegs - 1]}
              ticks={Array.from({ length: nSegs }, (_, i) => i)}
              tickFormatter={(v) => `seg${v}`}
              tick={{ fontSize: 9, fill: '#52525b' }}
              width={34}
            />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(v: number) => [`seg${v}`, 'position']}
            />
            <Line
              type="stepAfter"
              dataKey="segment"
              stroke="#818cf8"
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
