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

export interface WorkOrder {
  id: string
  segment_id: number
  severity: 'DEGRADED' | 'DAMAGED'
  belief: [number, number, number]
  confidence: number
  commanded_speed_fps: number
  alert_message: string
  created_at: string
  status: 'OPEN' | 'COMPLETED'
  completed_at: string | null
}

export const CLASS_COLORS = {
  Healthy:  { bg: 'bg-[#ADEBB3]', text: 'text-[#ADEBB3]', hex: '#ADEBB3' },
  Degraded: { bg: 'bg-[#f59e0b]', text: 'text-[#f59e0b]', hex: '#f59e0b' },
  Damaged:  { bg: 'bg-[#FF1A1A]', text: 'text-[#FF1A1A]', hex: '#FF1A1A' },
} as const
