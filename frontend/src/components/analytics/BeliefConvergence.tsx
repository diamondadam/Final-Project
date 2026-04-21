import { useTwinStore } from '../../store/twinStore'
import { CLASS_COLORS } from '../../types'

const BAR_COLORS = [
  CLASS_COLORS.Healthy.hex,
  CLASS_COLORS.Degraded.hex,
  CLASS_COLORS.Damaged.hex,
]
const BAR_LABELS = ['H', 'D', 'X']

export function BeliefConvergence() {
  const { state } = useTwinStore()

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden flex-1">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Belief Convergence
        </span>
      </div>
      <div className="px-[11px] py-[8px]">
        {!state ? (
          <div className="flex items-center justify-center h-16 text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)]">
            Waiting for data…
          </div>
        ) : (
          <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${state.segments.length}, 1fr)` }}>
            {state.segments.map((seg) => (
              <div key={seg.id} className="flex flex-col gap-1">
                <span className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)] font-mono text-center">
                  SEG {seg.id}
                </span>
                <div className="flex items-end justify-center gap-0.5 h-10">
                  {seg.belief.map((p, i) => (
                    <div key={i} className="flex flex-col items-center gap-px flex-1">
                      <div
                        className="w-full rounded-sm transition-all duration-500"
                        style={{
                          height: `${Math.max(p * 100, 4)}%`,
                          backgroundColor: BAR_COLORS[i],
                          opacity: 0.8,
                        }}
                      />
                      <span className="text-[clamp(7px,0.8vw,8px)] text-[var(--rt-muted)]">{BAR_LABELS[i]}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
