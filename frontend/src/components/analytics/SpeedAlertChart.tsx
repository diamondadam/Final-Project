import {
  ComposedChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceArea, ReferenceLine,
} from 'recharts'
import { useTwinStore } from '../../store/twinStore'
import { getAlertRuns } from './utils'

const ALERT_FILL: Record<string, string> = {
  CLEAR:   '#ADEBB314',
  WARNING: '#f59e0b14',
  DANGER:  '#FF1A1A14',
}

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

export function SpeedAlertChart() {
  const { tickHistory, alertHistory } = useTwinStore()
  const runs = getAlertRuns(alertHistory)

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px] flex items-center justify-between">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Speed + Alert Band
        </span>
        <span className="text-[7px] px-[7px] py-[2px] rounded-full border bg-[#87CEEB22] text-[var(--rt-blue)] border-[#87CEEB44] font-semibold">
          ● LIVE
        </span>
      </div>
      <div className="px-[11px] py-[8px]">
        {tickHistory.length < 2 ? (
          <div className="flex items-center justify-center h-[120px] text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)]">
            Waiting for data…
          </div>
        ) : (
          <div className="min-h-[120px] lg:min-h-[160px]">
            <ResponsiveContainer width="100%" height="100%" minHeight={120}>
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
                <ReferenceLine y={3.0} stroke="#374151" strokeDasharray="4 2" />
                <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#6b7280' }} />
                <YAxis domain={[0, 3.5]} tick={{ fontSize: 10, fill: '#6b7280' }} width={28} />
                <Tooltip {...TOOLTIP_STYLE} />
                <Line
                  type="monotone"
                  dataKey="speed"
                  stroke="#87CEEB"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}
