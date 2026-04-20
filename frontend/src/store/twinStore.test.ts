import { describe, it, expect, beforeEach } from 'vitest'
import { useTwinStore } from './twinStore'
import type { TwinState } from '../types'

function makeTwinState(tick: number, alert: string, segment: number): TwinState {
  return {
    tick,
    timestamp: new Date().toISOString(),
    train_segment: segment,
    commanded_speed_fps: 2.5,
    alert,
    segments: [
      { id: 0, true_state: 0, belief: [0.9, 0.05, 0.05], map_state: 0, map_state_name: 'Healthy', entropy: 0.2 },
    ],
  }
}

describe('twinStore history arrays', () => {
  beforeEach(() => {
    useTwinStore.setState({
      state: null,
      tickHistory: [],
      alertHistory: [],
      positionHistory: [],
      segmentBeliefHistory: [],
      workOrders: [],
      connected: false,
      repairLog: [],
    })
  })

  it('setState appends to alertHistory', () => {
    const { setState } = useTwinStore.getState()
    setState(makeTwinState(1, 'CLEAR', 0))
    const { alertHistory } = useTwinStore.getState()
    expect(alertHistory).toHaveLength(1)
    expect(alertHistory[0]).toEqual({ tick: 1, alert: 'CLEAR' })
  })

  it('setState appends to positionHistory', () => {
    const { setState } = useTwinStore.getState()
    setState(makeTwinState(1, 'CLEAR', 2))
    const { positionHistory } = useTwinStore.getState()
    expect(positionHistory[0]).toEqual({ tick: 1, segment: 2 })
  })

  it('setState appends to segmentBeliefHistory', () => {
    const { setState } = useTwinStore.getState()
    setState(makeTwinState(1, 'CLEAR', 0))
    const { segmentBeliefHistory } = useTwinStore.getState()
    expect(segmentBeliefHistory[0].tick).toBe(1)
    expect(segmentBeliefHistory[0].beliefs[0]).toEqual([0.9, 0.05, 0.05])
  })

  it('history arrays are capped at 60 entries', () => {
    const { setState } = useTwinStore.getState()
    for (let i = 0; i < 65; i++) setState(makeTwinState(i, 'CLEAR', 0))
    const { alertHistory } = useTwinStore.getState()
    expect(alertHistory).toHaveLength(60)
    expect(alertHistory[59].tick).toBe(64)
  })
})

describe('twinStore repairLog', () => {
  beforeEach(() => {
    useTwinStore.setState({ repairLog: [] })
  })

  it('addRepairLog prepends to repairLog', () => {
    const { addRepairLog } = useTwinStore.getState()
    addRepairLog({ timestamp: 'a', type: 'REPAIRED', segment_id: 1, detail: 'done' })
    addRepairLog({ timestamp: 'b', type: 'OVERRIDE', segment_id: 2, detail: 'forced' })
    const { repairLog } = useTwinStore.getState()
    expect(repairLog[0].timestamp).toBe('b')
    expect(repairLog[1].timestamp).toBe('a')
  })

  it('clearRepairLog empties the log', () => {
    const { addRepairLog, clearRepairLog } = useTwinStore.getState()
    addRepairLog({ timestamp: 'a', type: 'REPAIRED', segment_id: 0, detail: 'x' })
    clearRepairLog()
    expect(useTwinStore.getState().repairLog).toHaveLength(0)
  })
})
