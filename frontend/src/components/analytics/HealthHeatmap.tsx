import { useTwinStore } from '../../store/twinStore'

const STATE_COLOR: Record<number, string> = {
  0: '#ADEBB366',
  1: '#f59e0b66',
  2: '#FF1A1A66',
}

function getMapState(belief: [number, number, number]): number {
  return belief.indexOf(Math.max(...belief))
}

export function HealthHeatmap() {
  const { segmentBeliefHistory, state } = useTwinStore()
  const nSegs = state?.segments.length ?? 0

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Segment Health Heatmap
        </span>
      </div>
      <div className="px-[11px] py-[8px]">
        {nSegs === 0 || segmentBeliefHistory.length === 0 ? (
          <div className="flex items-center justify-center h-16 text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)]">
            Waiting for data…
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-1">
              {Array.from({ length: nSegs }, (_, segIdx) => (
                <div key={segIdx} className="flex items-center gap-1.5">
                  <span className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)] font-mono w-8 shrink-0">
                    seg{segIdx}
                  </span>
                  <div
                    className="flex-1 grid gap-px"
                    style={{ gridTemplateColumns: `repeat(${segmentBeliefHistory.length}, 1fr)` }}
                  >
                    {segmentBeliefHistory.map((snap, t) => {
                      const beliefs = snap.beliefs[segIdx]
                      const color = beliefs ? STATE_COLOR[getMapState(beliefs)] : '#1f2937'
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
              {[['Healthy', '#ADEBB366'], ['Degraded', '#f59e0b66'], ['Damaged', '#FF1A1A66']].map(([label, color]) => (
                <div key={label} className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-sm" style={{ background: color }} />
                  <span className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)]">{label}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
