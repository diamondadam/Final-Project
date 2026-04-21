import { useTwinStore } from '../../store/twinStore'
import { CLASS_COLORS } from '../../types'

const OVERRIDE_BUTTONS = [
  { state: 0, label: 'H', bg: '#ADEBB322', color: 'var(--rt-green)', border: '#ADEBB344', hoverBg: '#ADEBB344', activeBorder: '#ADEBB3' },
  { state: 1, label: 'D', bg: '#f59e0b22', color: 'var(--rt-amber)', border: '#f59e0b44', hoverBg: '#f59e0b44', activeBorder: '#f59e0b'  },
  { state: 2, label: 'X', bg: '#FF1A1A22', color: 'var(--rt-red)',   border: '#FF1A1A44', hoverBg: '#FF1A1A44', activeBorder: '#FF1A1A'  },
] as const

export function SegmentOverridePanel() {
  const { state, applyCorrection } = useTwinStore()

  return (
    <section className="flex flex-col gap-3">
      <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
        <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
          <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
            Segment Override (HITL)
          </span>
          <p className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)] mt-0.5">
            Force-set a segment's belief state
          </p>
        </div>
        <div className="px-[11px] py-[8px]">
          {!state ? (
            <div className="text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)] py-4 text-center">
              Waiting for connection…
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              {state.segments.map((seg) => {
                const colors = CLASS_COLORS[seg.map_state_name]
                return (
                  <div
                    key={seg.id}
                    className="bg-[var(--rt-bg)] border border-[var(--rt-border)] rounded p-3 flex flex-col gap-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)] font-mono">
                        SEG {seg.id}
                      </span>
                      <span
                        className="text-[clamp(7px,0.8vw,9px)] font-semibold"
                        style={{ color: colors.hex }}
                      >
                        {seg.map_state_name.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex gap-1.5">
                      {OVERRIDE_BUTTONS.map((btn) => (
                        <button
                          key={btn.state}
                          onClick={() => applyCorrection(seg.id, btn.state)}
                          className="flex-1 text-[clamp(9px,1vw,11px)] font-bold py-1 rounded transition-all border"
                          style={{
                            background: btn.bg,
                            color: btn.color,
                            borderColor: seg.map_state === btn.state ? btn.activeBorder : btn.border,
                            outline: seg.map_state === btn.state ? `1px solid ${btn.activeBorder}` : 'none',
                          }}
                          onMouseEnter={e => (e.currentTarget.style.background = btn.hoverBg)}
                          onMouseLeave={e => (e.currentTarget.style.background = btn.bg)}
                        >
                          {btn.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
