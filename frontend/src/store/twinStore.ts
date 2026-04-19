import { create } from 'zustand'
import type { TwinState, WorkOrder } from '../types'

interface TwinStore {
  state: TwinState | null
  connected: boolean
  tickHistory: { tick: number; speed: number; timestamp: string }[]
  workOrders: WorkOrder[]
  setState: (s: TwinState) => void
  setConnected: (c: boolean) => void
  setWorkOrders: (orders: WorkOrder[]) => void
  completeWorkOrder: (id: string) => Promise<void>
  refreshWorkOrders: () => Promise<void>
}

export const useTwinStore = create<TwinStore>((set, get) => ({
  state: null,
  connected: false,
  tickHistory: [],
  workOrders: [],

  setState: (s) =>
    set((prev) => ({
      state: s,
      tickHistory: [
        ...prev.tickHistory.slice(-60),
        { tick: s.tick, speed: s.commanded_speed_fps, timestamp: s.timestamp },
      ],
    })),

  setConnected: (connected) => set({ connected }),

  setWorkOrders: (orders) => set({ workOrders: orders }),

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
}))
