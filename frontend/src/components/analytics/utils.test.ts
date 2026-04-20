import { describe, it, expect } from 'vitest'
import { alertLevel, getAlertRuns, getVSafeHistory, V_SAFE_MULT } from './utils'

describe('alertLevel', () => {
  it('returns CLEAR for "CLEAR"', () => {
    expect(alertLevel('CLEAR')).toBe('CLEAR')
  })
  it('returns WARNING for warning strings', () => {
    expect(alertLevel('WARNING – Degraded track. Proceed with caution.')).toBe('WARNING')
  })
  it('returns DANGER for danger strings', () => {
    expect(alertLevel('DANGER – Damaged track detected. Speed reduced. Whistle!')).toBe('DANGER')
  })
})

describe('getAlertRuns', () => {
  it('returns empty array for empty input', () => {
    expect(getAlertRuns([])).toEqual([])
  })
  it('groups consecutive identical alert levels into runs', () => {
    const history = [
      { tick: 1, alert: 'CLEAR' },
      { tick: 2, alert: 'CLEAR' },
      { tick: 3, alert: 'WARNING – x' },
      { tick: 4, alert: 'CLEAR' },
    ]
    const runs = getAlertRuns(history)
    expect(runs).toHaveLength(3)
    expect(runs[0]).toEqual({ x1: 1, x2: 2, level: 'CLEAR' })
    expect(runs[1]).toEqual({ x1: 3, x2: 3, level: 'WARNING' })
    expect(runs[2]).toEqual({ x1: 4, x2: 4, level: 'CLEAR' })
  })
})

describe('V_SAFE_MULT', () => {
  it('maps health states to speed multipliers', () => {
    expect(V_SAFE_MULT[0]).toBe(3.0)
    expect(V_SAFE_MULT[1]).toBe(1.8)
    expect(V_SAFE_MULT[2]).toBe(0.9)
  })
})

describe('getVSafeHistory', () => {
  it('computes v_safe from MAP state of the current segment per tick', () => {
    const tickHistory = [{ tick: 1, speed: 2.5, timestamp: '' }]
    const positionHistory = [{ tick: 1, segment: 0 }]
    // segment 0 has Degraded MAP state (belief index 1 is highest)
    const segmentBeliefHistory = [{ tick: 1, beliefs: [[0.1, 0.8, 0.1] as [number,number,number]] }]
    const result = getVSafeHistory(tickHistory, positionHistory, segmentBeliefHistory)
    expect(result).toHaveLength(1)
    expect(result[0]).toEqual({ tick: 1, commanded: 2.5, vSafe: 1.8 })
  })
})
