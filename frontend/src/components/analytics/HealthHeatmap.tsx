import { useTwinStore } from '../../store/twinStore'

const STATE_COLOR: Record<number, string> = {
  0: '#10b98166',  // Healthy — emerald
  1: '#f59e0b66',  // Degraded — amber
  2: '#ef444466',  // Damaged — red
}

function getMapState(belief: [number, number, number]): number {
  return belief.indexOf(Math.max(...belief))
}

export function HealthHeatmap() {
  const { segmentBeliefHistory, state } = useTwinStore()
  const nSegs = state?.segments.length ?? 0

  if (nSegs === 0 || segmentBeliefHistory.length === 0) {
    return (
      <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4">
        <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
          Segment Health Heatmap
        </p>
        <div className="flex items-center justify-center h-16 text-zinc-600 text-sm">
          Waiting for data…
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4">
      <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
        Segment Health Heatmap
      </p>
      <div className="flex flex-col gap-1">
        {Array.from({ length: nSegs }, (_, segIdx) => (
          <div key={segIdx} className="flex items-center gap-1.5">
            <span className="text-[9px] text-zinc-600 font-mono w-8 shrink-0">seg{segIdx}</span>
            <div
              className="flex-1 grid gap-px"
              style={{ gridTemplateColumns: `repeat(${segmentBeliefHistory.length}, 1fr)` }}
            >
              {segmentBeliefHistory.map((snap, t) => {
                const beliefs = snap.beliefs[segIdx]
                const color = beliefs
                  ? STATE_COLOR[getMapState(beliefs)]
                  : '#27272a'
                return (
                  <div
                    key={t}
                    className="rounded-[1px]"
                    style={{ height: 10, background: color }}
                  />
                )
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-3 mt-2">
        {[['Healthy', '#10b98166'], ['Degraded', '#f59e0b66'], ['Damaged', '#ef444466']].map(([label, color]) => (
          <div key={label} className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-sm" style={{ background: color }} />
            <span className="text-[9px] text-zinc-600">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
