import { useTwinStore } from '../store/twinStore'
import { WorkOrderList } from '../components/maintenance/WorkOrderList'
import { SegmentOverridePanel } from '../components/maintenance/SegmentOverridePanel'
import { RepairHistoryLog } from '../components/maintenance/RepairHistoryLog'

export function MaintenancePage() {
  const { workOrders, repairLog, resetAll } = useTwinStore()
  const openCount = workOrders.filter((w) => w.status === 'OPEN').length

  return (
    <div className="flex flex-col gap-5 p-3 sm:p-4 lg:p-6">

      {/* Action bar */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[clamp(14px,1.8vw,20px)] font-bold text-[var(--rt-cream)] tracking-tight uppercase">
            Maintenance
          </h1>
          <p className="text-[clamp(9px,1vw,11px)] text-[var(--rt-muted)] mt-0.5">
            Work orders · segment overrides · repair log
          </p>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <div className="flex items-center gap-3 text-[clamp(9px,1vw,11px)] text-[var(--rt-muted)]">
            <span>
              <span className="text-[var(--rt-text)] font-semibold">{openCount}</span> open WOs
            </span>
            <span>
              <span className="text-[var(--rt-text)] font-semibold">{repairLog.length}</span> repairs
            </span>
          </div>
          <button
            onClick={resetAll}
            className="text-[clamp(9px,1vw,11px)] px-3 py-1.5 rounded bg-[#FF1A1A22] text-[var(--rt-red)] border border-[#FF1A1A44] hover:bg-[#FF1A1A33] font-semibold transition-colors"
          >
            Reset All Beliefs
          </button>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-5">
        <WorkOrderList />
        <SegmentOverridePanel />
      </div>

      {/* Repair history */}
      <RepairHistoryLog />

    </div>
  )
}
