import { useTwinStore } from '../../store/twinStore'
import type { RepairLogEntry } from '../../store/twinStore'

const BADGE: Record<RepairLogEntry['type'], string> = {
  REPAIRED: 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30',
  OVERRIDE: 'bg-indigo-500/20 text-indigo-400 ring-1 ring-indigo-500/30',
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function RepairHistoryLog() {
  const { repairLog } = useTwinStore()

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase">
        Repair History
      </h2>
      {repairLog.length === 0 ? (
        <div className="text-zinc-600 text-sm py-4 text-center rounded-xl border border-white/5">
          No repairs or overrides yet
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {repairLog.map((entry, i) => (
            <div
              key={`${entry.timestamp}-${entry.segment_id}-${i}`}
              className="flex items-center gap-3 px-3 py-2 bg-white/[0.03] border border-white/5 rounded-lg"
            >
              <span className="text-[10px] text-zinc-600 font-mono w-16 shrink-0">
                {formatTime(entry.timestamp)}
              </span>
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0 ${BADGE[entry.type]}`}>
                {entry.type}
              </span>
              <span className="text-[11px] text-zinc-400">
                Segment {entry.segment_id} — {entry.detail}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
