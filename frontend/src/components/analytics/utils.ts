export type AlertLevel = 'CLEAR' | 'WARNING' | 'DANGER'

export function alertLevel(alert: string): AlertLevel {
  if (alert === 'CLEAR') return 'CLEAR'
  if (alert.startsWith('WARNING')) return 'WARNING'
  if (alert.startsWith('DANGER')) return 'DANGER'
  // Unknown alert strings fail safe: treat as DANGER so the UI never under-reports severity
  return 'DANGER'
}

export function getAlertRuns(
  history: { tick: number; alert: string }[],
): { x1: number; x2: number; level: AlertLevel }[] {
  if (history.length === 0) return []
  const runs: { x1: number; x2: number; level: AlertLevel }[] = []
  let runStart = history[0].tick
  let runLevel = alertLevel(history[0].alert)
  for (let i = 1; i < history.length; i++) {
    const lvl = alertLevel(history[i].alert)
    if (lvl !== runLevel) {
      runs.push({ x1: runStart, x2: history[i - 1].tick, level: runLevel })
      runStart = history[i].tick
      runLevel = lvl
    }
  }
  runs.push({ x1: runStart, x2: history[history.length - 1].tick, level: runLevel })
  return runs
}

export const V_SAFE_MULT: Record<number, number> = { 0: 3.0, 1: 1.8, 2: 0.9 }

export function getVSafeHistory(
  tickHistory: { tick: number; speed: number; timestamp: string }[],
  positionHistory: { tick: number; segment: number }[],
  segmentBeliefHistory: { tick: number; beliefs: [number, number, number][] }[],
): { tick: number; commanded: number; vSafe: number }[] {
  const len = Math.min(tickHistory.length, positionHistory.length, segmentBeliefHistory.length)
  const result: { tick: number; commanded: number; vSafe: number }[] = []
  for (let i = 0; i < len; i++) {
    const seg = positionHistory[i].segment
    const beliefs = segmentBeliefHistory[i].beliefs[seg]
    if (!beliefs) continue
    const mapState = beliefs.indexOf(Math.max(...beliefs))
    result.push({
      tick: tickHistory[i].tick,
      commanded: tickHistory[i].speed,
      vSafe: V_SAFE_MULT[mapState] ?? 3.0,
    })
  }
  return result
}
