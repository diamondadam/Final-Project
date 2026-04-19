import { useTwinStore } from '../store/twinStore'
import { SegmentCard } from './SegmentCard'
import { AlertBanner } from './AlertBanner'
import { TrackConfigurator } from './TrackConfigurator'
import { WorkOrderPanel } from './WorkOrderPanel'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

export function TrackDashboard() {
  const { state, tickHistory } = useTwinStore()

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">
            Rail Track Digital Twin
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">Track health monitoring dashboard</p>
        </div>
        <AlertBanner />
      </div>

      {/* Segment grid */}
      <section>
        <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
          Track Segments
        </h2>
        {state ? (
          <div className="grid grid-cols-2 xl:grid-cols-3 gap-3">
            {state.segments.map((seg) => (
              <SegmentCard
                key={seg.id}
                segment={seg}
                isActive={seg.id === state.train_segment}
              />
            ))}
          </div>
        ) : (
          <div className="text-zinc-600 text-sm py-12 text-center">
            Waiting for digital twin data…
          </div>
        )}
      </section>

      {/* Track configurator */}
      <TrackConfigurator />

      {/* Work orders */}
      <WorkOrderPanel />

      {/* Speed history chart */}
      {tickHistory.length > 1 && (
        <section>
          <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
            Commanded Speed History
          </h2>
          <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4">
            <ResponsiveContainer width="100%" height={120}>
              <LineChart data={tickHistory}>
                <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#52525b' }} />
                <YAxis
                  domain={[0, 3.5]}
                  tick={{ fontSize: 10, fill: '#52525b' }}
                  width={28}
                />
                <Tooltip
                  contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#a1a1aa' }}
                  itemStyle={{ color: '#34d399' }}
                />
                <ReferenceLine y={3.0} stroke="#3f3f46" strokeDasharray="4 2" />
                <Line
                  type="monotone"
                  dataKey="speed"
                  stroke="#34d399"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

    </div>
  )
}
