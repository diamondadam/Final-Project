import { useTwinStore } from '../store/twinStore'

export function AlertBanner() {
  const { state, connected } = useTwinStore()

  if (!connected) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-zinc-800 text-zinc-400 text-sm rounded-lg">
        <span className="w-2 h-2 rounded-full bg-zinc-500 animate-pulse" />
        Connecting to digital twin…
      </div>
    )
  }

  if (!state) return null

  const isDanger  = state.alert.startsWith('DANGER')
  const isWarning = state.alert.startsWith('WARNING')

  const styles = isDanger
    ? 'bg-red-900/60 border border-red-500 text-red-300'
    : isWarning
    ? 'bg-amber-900/60 border border-amber-500 text-amber-300'
    : 'bg-emerald-900/40 border border-emerald-700 text-emerald-400'

  const dot = isDanger ? 'bg-red-400 animate-pulse' : isWarning ? 'bg-amber-400' : 'bg-emerald-400'

  return (
    <div className={`flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium ${styles}`}>
      <span className={`w-2 h-2 rounded-full shrink-0 ${dot}`} />
      <span>{state.alert}</span>
      <span className="ml-auto text-xs opacity-60">
        Tick #{state.tick} · {state.commanded_speed_fps.toFixed(2)} fps
      </span>
    </div>
  )
}
