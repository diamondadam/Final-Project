import { useTwinStore } from '../../store/twinStore'
import { CLASS_COLORS } from '../../types'

const OVERRIDE_BUTTONS = [
  { state: 0, label: 'H', cls: 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30', activeCls: 'ring-1 ring-emerald-400' },
  { state: 1, label: 'D', cls: 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30',       activeCls: 'ring-1 ring-amber-400'   },
  { state: 2, label: 'X', cls: 'bg-red-500/20 text-red-400 hover:bg-red-500/30',             activeCls: 'ring-1 ring-red-400'     },
] as const

export function SegmentOverridePanel() {
  const { state, applyCorrection } = useTwinStore()

  if (!state) {
    return (
      <section className="flex flex-col gap-3">
        <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase">
          Segment Override (HITL)
        </h2>
        <div className="text-zinc-600 text-sm py-4 text-center">Waiting for connection…</div>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-3">
      <div>
        <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase">
          Segment Override (HITL)
        </h2>
        <p className="text-[11px] text-zinc-600 mt-1">Force-set a segment's belief state</p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {state.segments.map((seg) => {
          const colors = CLASS_COLORS[seg.map_state_name]
          return (
            <div
              key={seg.id}
              className="bg-white/[0.03] border border-white/10 rounded-xl p-3 flex flex-col gap-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-zinc-500 font-mono">SEG {seg.id}</span>
                <span className={`text-[10px] font-semibold ${colors.text}`}>
                  {seg.map_state_name.toUpperCase()}
                </span>
              </div>
              <div className="flex gap-1.5">
                {OVERRIDE_BUTTONS.map(({ state: btnState, label, cls, activeCls }) => (
                  <button
                    key={btnState}
                    onClick={() => applyCorrection(seg.id, btnState)}
                    className={`flex-1 text-[11px] font-bold py-1 rounded-md transition-all ${cls} ${
                      seg.map_state === btnState ? activeCls : ''
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
