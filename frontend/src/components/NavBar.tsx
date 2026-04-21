import { NavLink } from 'react-router-dom'
import { useTwinStore } from '../store/twinStore'

export function NavBar() {
  const connected = useTwinStore((s) => s.connected)
  const openCount = useTwinStore((s) => s.workOrders.filter((w) => w.status === 'OPEN').length)

  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `relative px-3 py-1.5 rounded text-[clamp(9px,1.1vw,11px)] tracking-wide transition-colors ${
      isActive
        ? 'bg-[var(--rt-border-dim)] text-[var(--rt-cream)]'
        : 'text-[var(--rt-muted)] hover:bg-[var(--rt-border-dim)] hover:text-[var(--rt-cream)]'
    }`

  return (
    <nav className="flex items-center gap-1 px-4 h-11 border-b border-[var(--rt-border)] bg-[var(--rt-sidebar-bg)] shrink-0">
      <span className="text-[clamp(9px,1vw,11px)] font-bold text-[var(--rt-cream)] mr-4 tracking-[2px] uppercase">
        Rail Twin
      </span>

      <NavLink to="/" end className={linkCls}>Dashboard</NavLink>
      <NavLink to="/analytics" className={linkCls}>Analytics</NavLink>
      <NavLink to="/maintenance" aria-label={openCount > 0 ? `Maintenance, ${openCount} open work orders` : 'Maintenance'} className={linkCls}>
        Maintenance
        {openCount > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[var(--rt-red)] text-[#111827] text-[9px] font-bold flex items-center justify-center">
            {openCount > 9 ? '9+' : openCount}
          </span>
        )}
      </NavLink>

      <div className="ml-auto flex items-center gap-2">
        <span
          aria-hidden="true"
          className={`w-2 h-2 rounded-full ${connected ? 'bg-[var(--rt-green)]' : 'bg-[var(--rt-red)]'}`}
        />
        <span className="text-[clamp(8px,0.9vw,10px)] text-[var(--rt-muted)]">
          {connected ? 'Live' : 'Disconnected'}
        </span>
      </div>
    </nav>
  )
}
