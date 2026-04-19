import { create } from 'zustand'
import type { TwinState } from '../types'

interface TwinStore {
  state: TwinState | null
  connected: boolean
  tickHistory: { tick: number; speed: number; timestamp: string }[]
  setState: (s: TwinState) => void
  setConnected: (c: boolean) => void
}

export const useTwinStore = create<TwinStore>((set) => ({
  state: null,
  connected: false,
  tickHistory: [],

  setState: (s) =>
    set((prev) => ({
      state: s,
      tickHistory: [
        ...prev.tickHistory.slice(-60),   // keep last 60 ticks
        { tick: s.tick, speed: s.commanded_speed_fps, timestamp: s.timestamp },
      ],
    })),

  setConnected: (connected) => set({ connected }),
}))
