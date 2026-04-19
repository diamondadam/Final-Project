import { useTwinWebSocket } from './hooks/useTwinWebSocket'
import { TrackDashboard } from './components/TrackDashboard'

export default function App() {
  useTwinWebSocket()

  return (
    <div className="min-h-screen bg-[#0f1117]">
      <TrackDashboard />
    </div>
  )
}
