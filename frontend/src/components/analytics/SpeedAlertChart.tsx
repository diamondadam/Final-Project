import {
  ComposedChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceArea, ReferenceLine,
} from 'recharts'
import { useTwinStore } from '../../store/twinStore'
import { getAlertRuns } from './utils'

const ALERT_FILL: Record<string, string> = {
  CLEAR:   '#10b98114',
  WARNING: '#f59e0b14',
  DANGER:  '#ef444414',
}

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#18181b',
    border: '1px solid #3f3f46',
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: '#a1a1aa' },
  itemStyle: { color: '#34d399' },
}

export function SpeedAlertChart() {
  const { tickHistory, alertHistory } = useTwinStore()
  const runs = getAlertRuns(alertHistory)

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 h-full">
      <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
        Speed + Alert Band
      </p>
      {tickHistory.length < 2 ? (
        <div className="flex items-center justify-center h-32 text-zinc-600 text-sm">
          Waiting for data…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <ComposedChart data={tickHistory}>
            {runs.map((r, i) => (
              <ReferenceArea
                key={i}
                x1={r.x1}
                x2={r.x2}
                fill={ALERT_FILL[r.level]}
                strokeOpacity={0}
              />
            ))}
            <ReferenceLine y={3.0} stroke="#3f3f46" strokeDasharray="4 2" />
            <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#52525b' }} />
            <YAxis
              domain={[0, 3.5]}
              tick={{ fontSize: 10, fill: '#52525b' }}
              width={28}
            />
            <Tooltip {...TOOLTIP_STYLE} />
            <Line
              type="monotone"
              dataKey="speed"
              stroke="#34d399"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
