import { useTwinStore } from '../../store/twinStore'
import type { RepairLogEntry } from '../../store/twinStore'

const BADGE: Record<RepairLogEntry['type'], { bg: string; color: string; border: string }> = {
  REPAIRED: { bg: '#ADEBB322', color: 'var(--rt-green)', border: '#ADEBB344' },
  OVERRIDE: { bg: '#87CEEB22', color: 'var(--rt-blue)',  border: '#87CEEB44' },
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function RepairHistoryLog() {
  const { repairLog } = useTwinStore()
  return (
    <section className="flex flex-col gap-3">
      <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
        <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
          <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
            Repair History
          </span>
        </div>
        <div className="px-[11px] py-[8px]">
          {repairLog.length === 0 ? (
            <div className="text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)] py-4 text-center">
              No repairs or overrides yet
            </div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {repairLog.map((entry, i) => {
                const badge = BADGE[entry.type]
                return (
                  <div key={`${entry.timestamp}-${entry.segment_id}-${i}`}
                    className="flex items-center gap-3 px-3 py-2 rounded border border-[var(--rt-border)] bg-[var(--rt-bg)]">
                    <span className="text-[clamp(8px,0.9vw,10px)] text-[var(--rt-muted)] font-mono w-16 shrink-0">
                      {formatTime(entry.timestamp)}
                    </span>
                    <span className="text-[clamp(7px,0.8vw,9px)] font-semibold px-1.5 py-0.5 rounded shrink-0 border"
                      style={{ background: badge.bg, color: badge.color, borderColor: badge.border }}>
                      {entry.type}
                    </span>
                    <span className="text-[clamp(9px,1vw,11px)] text-[var(--rt-text)]">
                      Segment {entry.segment_id} — {entry.detail}
                    </span>
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
