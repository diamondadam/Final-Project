import { NavLink } from 'react-router-dom'
import { useTwinStore } from '../store/twinStore'

export function NavBar() {
  const connected = useTwinStore((s) => s.connected)
  const openCount = useTwinStore((s) => s.workOrders.filter((w) => w.status === 'OPEN').length)

  return (
    <nav className="flex items-center gap-1 px-4 h-12 border-b border-white/10 bg-[#0f1117] shrink-0">
      <span className="text-sm font-semibold text-white mr-4 tracking-tight">Rail Twin</span>

      <NavLink
        to="/"
        end
        className={({ isActive }) =>
          `px-3 py-1.5 rounded-md text-sm transition-colors ${
            isActive ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`
        }
      >
        Dashboard
      </NavLink>

      <NavLink
        to="/analytics"
        className={({ isActive }) =>
          `px-3 py-1.5 rounded-md text-sm transition-colors ${
            isActive ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`
        }
      >
        Analytics
      </NavLink>

      <NavLink
        to="/maintenance"
        aria-label={openCount > 0 ? `Maintenance, ${openCount} open work orders` : 'Maintenance'}
        className={({ isActive }) =>
          `relative px-3 py-1.5 rounded-md text-sm transition-colors ${
            isActive ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`
        }
      >
        Maintenance
        {openCount > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
            {openCount > 9 ? '9+' : openCount}
          </span>
        )}
      </NavLink>

      <div className="ml-auto flex items-center gap-2">
        <span aria-hidden="true" className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-zinc-600'}`} />
        <span className="text-xs text-zinc-500">{connected ? 'Live' : 'Disconnected'}</span>
      </div>
    </nav>
  )
}
