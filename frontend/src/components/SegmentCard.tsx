import type { SegmentState, WorkOrder } from '../types'
import { CLASS_COLORS } from '../types'

interface Props {
  segment: SegmentState
  isActive: boolean
  workOrder?: WorkOrder | null
}

const BELIEF_LABELS = ['H', 'D', 'X']
const BELIEF_COLORS = ['bg-emerald-500', 'bg-amber-500', 'bg-red-500']

const WO_STATUS_STYLES = {
  OPEN:      'bg-orange-500/20 text-orange-400 ring-orange-500/30',
  COMPLETED: 'bg-zinc-500/20 text-zinc-400 ring-zinc-500/30',
}

export function SegmentCard({ segment, isActive, workOrder }: Props) {
  const colors = CLASS_COLORS[segment.map_state_name]
  const confidence = (Math.max(...segment.belief) * 100).toFixed(1)
  const entropyPct = Math.min(segment.entropy / Math.log(3), 1)   // normalise to [0,1]

  return (
    <div
      className={`
        relative rounded-xl border p-4 flex flex-col gap-3 transition-all duration-300
        ${isActive ? 'border-white/40 bg-white/5 shadow-lg shadow-white/5' : 'border-white/10 bg-white/[0.03]'}
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-zinc-500">SEG {segment.id}</span>
          {isActive && (
            <span className="text-[10px] font-semibold tracking-widest text-white/60 bg-white/10 px-1.5 py-0.5 rounded">
              TRAIN
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {workOrder && (
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ring-1 ${WO_STATUS_STYLES[workOrder.status]}`}>
              WO {workOrder.status}
            </span>
          )}
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${colors.text} bg-white/5`}>
            {segment.map_state_name.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Confidence */}
      <div>
        <div className="flex justify-between text-xs text-zinc-500 mb-1">
          <span>Confidence</span>
          <span className={`font-mono font-semibold ${colors.text}`}>{confidence}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${colors.bg}`}
            style={{ width: `${confidence}%` }}
          />
        </div>
      </div>

      {/* Belief breakdown */}
      <div className="flex gap-1.5">
        {segment.belief.map((p, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <span className="text-[10px] text-zinc-600">{BELIEF_LABELS[i]}</span>
            <div className="w-full rounded-sm bg-white/10 overflow-hidden" style={{ height: '24px' }}>
              <div
                className={`w-full rounded-sm transition-all duration-500 ${BELIEF_COLORS[i]}`}
                style={{ height: `${p * 100}%`, marginTop: `${(1 - p) * 100}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-zinc-500">{(p * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>

      {/* Entropy */}
      <div className="flex justify-between text-[11px] text-zinc-600">
        <span>Uncertainty</span>
        <span className="font-mono">
          {entropyPct < 0.3 ? '▼ Low' : entropyPct < 0.7 ? '◆ Med' : '▲ High'}
        </span>
      </div>
    </div>
  )
}
