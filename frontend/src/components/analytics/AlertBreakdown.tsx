import { useTwinStore } from '../../store/twinStore'
import { alertLevel } from './utils'

const TILES = [
  { level: 'CLEAR',   label: 'CLEAR',   color: 'var(--rt-green)', bg: '#ADEBB310' },
  { level: 'WARNING', label: 'WARNING', color: 'var(--rt-amber)', bg: '#f59e0b10' },
  { level: 'DANGER',  label: 'DANGER',  color: 'var(--rt-red)',   bg: '#FF1A1A10' },
] as const

export function AlertBreakdown() {
  const { alertHistory } = useTwinStore()
  const total = alertHistory.length

  const counts = { CLEAR: 0, WARNING: 0, DANGER: 0 }
  for (const { alert } of alertHistory) counts[alertLevel(alert)]++

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Alert Breakdown
        </span>
      </div>
      <div className="px-[11px] py-[8px] flex gap-2">
        {TILES.map(({ level, label, color, bg }) => {
          const pct = total === 0 ? 0 : Math.round((counts[level] / total) * 100)
          return (
            <div
              key={level}
              className="flex-1 rounded p-2 flex flex-col items-center gap-0.5"
              style={{ background: bg }}
            >
              <span
                className="text-[clamp(14px,2vw,20px)] font-bold font-mono"
                style={{ color }}
              >
                {pct}%
              </span>
              <span className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)]">{label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
