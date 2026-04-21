import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { useTwinStore } from '../../store/twinStore'

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#1f2937',
    border: '1px solid #374151',
    borderRadius: 4,
    fontSize: 11,
  },
  labelStyle: { color: '#6b7280' },
  itemStyle: { color: '#87CEEB' },
}

export function PositionTimeline() {
  const { positionHistory, state } = useTwinStore()
  const nSegs = state?.segments.length ?? 5

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden flex-1">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Train Position
        </span>
      </div>
      <div className="px-[11px] py-[8px]">
        {positionHistory.length < 2 ? (
          <div className="flex items-center justify-center h-16 text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)]">
            Waiting for data…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={100}>
            <LineChart data={positionHistory}>
              <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#6b7280' }} />
              <YAxis
                domain={[0, nSegs - 1]}
                ticks={Array.from({ length: nSegs }, (_, i) => i)}
                tickFormatter={(v) => `seg${v}`}
                tick={{ fontSize: 9, fill: '#6b7280' }}
                width={34}
              />
              <Tooltip
                {...TOOLTIP_STYLE}
                formatter={(v) => [`seg${v}`, 'position']}
              />
              <Line
                type="stepAfter"
                dataKey="segment"
                stroke="#87CEEB"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
