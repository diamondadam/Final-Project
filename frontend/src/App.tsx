import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useTwinWebSocket } from './hooks/useTwinWebSocket'
import { NavBar } from './components/NavBar'
import { TrackDashboard } from './components/TrackDashboard'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { MaintenancePage } from './pages/MaintenancePage'

export default function App() {
  useTwinWebSocket()

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[var(--rt-bg)] flex flex-col">
        <NavBar />
        <div className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<TrackDashboard />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/maintenance" element={<MaintenancePage />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
