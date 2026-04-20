import { create } from 'zustand'
import type { TwinState, WorkOrder } from '../types'

export interface RepairLogEntry {
  timestamp: string
  type: 'REPAIRED' | 'OVERRIDE'
  segment_id: number
  detail: string
}

interface TwinStore {
  state: TwinState | null
  connected: boolean
  tickHistory: { tick: number; speed: number; timestamp: string }[]
  alertHistory: { tick: number; alert: string }[]
  positionHistory: { tick: number; segment: number }[]
  segmentBeliefHistory: { tick: number; beliefs: [number, number, number][] }[]
  workOrders: WorkOrder[]
  repairLog: RepairLogEntry[]

  setState: (s: TwinState) => void
  setConnected: (c: boolean) => void
  setWorkOrders: (orders: WorkOrder[]) => void
  addRepairLog: (entry: RepairLogEntry) => void
  clearRepairLog: () => void
  refreshWorkOrders: () => Promise<void>
  completeWorkOrder: (id: string) => Promise<void>
  applyCorrection: (segment_id: number, state: number) => Promise<void>
  resetAll: () => Promise<void>
}

const CLASS_NAMES = ['Healthy', 'Degraded', 'Damaged']

export const useTwinStore = create<TwinStore>((set, get) => ({
  state: null,
  connected: false,
  tickHistory: [],
  alertHistory: [],
  positionHistory: [],
  segmentBeliefHistory: [],
  workOrders: [],
  repairLog: [],

  setState: (s) =>
    set((prev) => ({
      state: s,
      tickHistory: [
        ...prev.tickHistory.slice(-59),
        { tick: s.tick, speed: s.commanded_speed_fps, timestamp: s.timestamp },
      ],
      alertHistory: [
        ...prev.alertHistory.slice(-59),
        { tick: s.tick, alert: s.alert },
      ],
      positionHistory: [
        ...prev.positionHistory.slice(-59),
        { tick: s.tick, segment: s.train_segment },
      ],
      segmentBeliefHistory: [
        ...prev.segmentBeliefHistory.slice(-59),
        {
          tick: s.tick,
          beliefs: s.segments.map((seg) => seg.belief as [number, number, number]),
        },
      ],
    })),

  setConnected: (connected) => set({ connected }),

  setWorkOrders: (orders) => set({ workOrders: orders }),

  addRepairLog: (entry) =>
    set((prev) => ({ repairLog: [entry, ...prev.repairLog] })),

  clearRepairLog: () => set({ repairLog: [] }),

  refreshWorkOrders: async () => {
    try {
      const res = await fetch('/api/work-orders')
      const data = await res.json()
      set({ workOrders: data.work_orders })
    } catch {
      // silently ignore — UI will show stale data
    }
  },

  completeWorkOrder: async (id: string) => {
    await fetch(`/api/work-orders/${id}/complete`, { method: 'POST' })
    await get().refreshWorkOrders()
  },

  applyCorrection: async (segment_id: number, state: number) => {
    await fetch('/api/correction', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ segment_id, state }),
    })
    get().addRepairLog({
      timestamp: new Date().toISOString(),
      type: 'OVERRIDE',
      segment_id,
      detail: `forced → ${CLASS_NAMES[state]}`,
    })
  },

  resetAll: async () => {
    await fetch('/api/reset', { method: 'POST' })
    await get().refreshWorkOrders()
    set({ repairLog: [] })
  },
}))
