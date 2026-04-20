import { useTwinStore } from '../../store/twinStore'
import { alertLevel } from './utils'

const TILES = [
  { level: 'CLEAR',   label: 'CLEAR',   textCls: 'text-emerald-400', bgCls: 'bg-emerald-500/10' },
  { level: 'WARNING', label: 'WARNING', textCls: 'text-amber-400',   bgCls: 'bg-amber-500/10'   },
  { level: 'DANGER',  label: 'DANGER',  textCls: 'text-red-400',     bgCls: 'bg-red-500/10'     },
] as const

export function AlertBreakdown() {
  const { alertHistory } = useTwinStore()
  const total = alertHistory.length

  const counts = { CLEAR: 0, WARNING: 0, DANGER: 0 }
  for (const { alert } of alertHistory) counts[alertLevel(alert)]++

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4">
      <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
        Alert Breakdown
      </p>
      <div className="flex gap-2">
        {TILES.map(({ level, label, textCls, bgCls }) => {
          const pct = total === 0 ? 0 : Math.round((counts[level] / total) * 100)
          return (
            <div key={level} className={`flex-1 ${bgCls} rounded-lg p-2 flex flex-col items-center gap-0.5`}>
              <span className={`text-lg font-bold font-mono ${textCls}`}>{pct}%</span>
              <span className="text-[9px] text-zinc-600">{label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
