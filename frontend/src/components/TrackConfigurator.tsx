import { useEffect, useState } from 'react'
import { useTwinStore } from '../store/twinStore'

const STATES = [
  { value: 0, label: 'Healthy',  short: 'H', color: 'bg-emerald-500 hover:bg-emerald-400', ring: 'ring-emerald-500' },
  { value: 1, label: 'Degraded', short: 'D', color: 'bg-amber-500   hover:bg-amber-400',   ring: 'ring-amber-500'   },
  { value: 2, label: 'Damaged',  short: 'X', color: 'bg-red-500     hover:bg-red-400',     ring: 'ring-red-500'     },
]

const MIN_SEGMENTS = 2
const MAX_SEGMENTS = 10

export function TrackConfigurator() {
  const { state } = useTwinStore()
  const [config, setConfig] = useState<number[]>([0, 1, 2, 1, 0])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved]   = useState(false)

  // Sync once on first state arrival
  useEffect(() => {
    if (state && config.join() === [0,1,2,1,0].join()) {
      setConfig(state.segments.map(s => s.true_state))
    }
  }, [state?.tick === 1])  // only on first tick

  function cycleSegment(idx: number) {
    setConfig(prev => {
      const next = [...prev]
      next[idx] = (next[idx] + 1) % 3
      return next
    })
    setSaved(false)
  }

  function addSegment() {
    if (config.length >= MAX_SEGMENTS) return
    setConfig(prev => [...prev, 0])
    setSaved(false)
  }

  function removeSegment() {
    if (config.length <= MIN_SEGMENTS) return
    setConfig(prev => prev.slice(0, -1))
    setSaved(false)
  }

  async function apply() {
    setSaving(true)
    try {
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ track_config: config }),
      })
      setSaved(true)
    } finally {
      setSaving(false)
    }
  }

  async function reset() {
    await fetch('/api/reset', { method: 'POST' })
    setSaved(false)
  }

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 flex flex-col gap-4">

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase">
          Track Configuration
        </h2>
        <div className="flex gap-2">
          <button
            onClick={removeSegment}
            disabled={config.length <= MIN_SEGMENTS}
            className="w-6 h-6 rounded text-zinc-400 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center text-lg leading-none transition-colors"
            title="Remove last segment"
          >−</button>
          <button
            onClick={addSegment}
            disabled={config.length >= MAX_SEGMENTS}
            className="w-6 h-6 rounded text-zinc-400 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center text-lg leading-none transition-colors"
            title="Add segment"
          >+</button>
        </div>
      </div>

      {/* Segment toggles */}
      <div className="flex flex-wrap gap-2">
        {config.map((stateVal, idx) => {
          const s = STATES[stateVal]
          return (
            <button
              key={idx}
              onClick={() => cycleSegment(idx)}
              title={`Segment ${idx}: ${s.label} — click to cycle`}
              className={`
                flex flex-col items-center gap-1 rounded-lg px-3 py-2
                ring-1 ${s.ring} ${s.color} text-white transition-all duration-150
                min-w-[52px]
              `}
            >
              <span className="text-[10px] font-mono opacity-70">S{idx}</span>
              <span className="text-xs font-semibold">{s.label}</span>
            </button>
          )
        })}
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-[11px] text-zinc-600">
        {STATES.map(s => (
          <span key={s.value} className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${s.color.split(' ')[0]}`} />
            {s.label}
          </span>
        ))}
        <span className="ml-auto opacity-50">Click segment to cycle state</span>
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-1 border-t border-white/5">
        <button
          onClick={apply}
          disabled={saving}
          className="flex-1 py-1.5 rounded-lg text-sm font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition-colors"
        >
          {saving ? 'Applying…' : saved ? '✓ Applied' : 'Apply Configuration'}
        </button>
        <button
          onClick={reset}
          className="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
          title="Reset beliefs without changing config"
        >
          Reset Beliefs
        </button>
      </div>
    </div>
  )
}
