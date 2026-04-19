export interface SegmentState {
  id: number
  true_state: number
  belief: [number, number, number]   // [P(Healthy), P(Degraded), P(Damaged)]
  map_state: number                  // 0 | 1 | 2
  map_state_name: 'Healthy' | 'Degraded' | 'Damaged'
  entropy: number
}

export interface TwinState {
  tick: number
  timestamp: string
  train_segment: number
  commanded_speed_fps: number
  alert: string
  segments: SegmentState[]
}

export const CLASS_COLORS = {
  Healthy:  { bg: 'bg-emerald-500',  text: 'text-emerald-400',  hex: '#10b981' },
  Degraded: { bg: 'bg-amber-500',    text: 'text-amber-400',    hex: '#f59e0b' },
  Damaged:  { bg: 'bg-red-500',      text: 'text-red-400',      hex: '#ef4444' },
} as const
