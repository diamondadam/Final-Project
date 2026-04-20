import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useTwinWebSocket } from './hooks/useTwinWebSocket'
import { NavBar } from './components/NavBar'
import { TrackDashboard } from './components/TrackDashboard'
import { WorkOrdersPage } from './pages/WorkOrdersPage'

export default function App() {
  useTwinWebSocket()

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#0f1117] flex flex-col">
        <NavBar />
        <div className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<TrackDashboard />} />
            <Route path="/work-orders" element={<WorkOrdersPage />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
