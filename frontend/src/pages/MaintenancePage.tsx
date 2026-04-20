import { useTwinStore } from '../store/twinStore'
import { WorkOrderList } from '../components/maintenance/WorkOrderList'
import { SegmentOverridePanel } from '../components/maintenance/SegmentOverridePanel'
import { RepairHistoryLog } from '../components/maintenance/RepairHistoryLog'

export function MaintenancePage() {
  const { workOrders, repairLog, resetAll } = useTwinStore()
  const openCount = workOrders.filter((w) => w.status === 'OPEN').length

  return (
    <div className="flex flex-col gap-6 p-6 max-w-5xl mx-auto">

      {/* Action bar */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight">Maintenance</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Work orders · segment overrides · repair log
          </p>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <div className="flex items-center gap-3 text-sm text-zinc-500">
            <span>
              <span className="text-white font-semibold">{openCount}</span> open WOs
            </span>
            <span>
              <span className="text-white font-semibold">{repairLog.length}</span> repairs
            </span>
          </div>
          <button
            onClick={resetAll}
            className="text-sm px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 ring-1 ring-red-500/30 hover:bg-red-500/30 font-semibold transition-colors"
          >
            Reset All Beliefs
          </button>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-[1fr_280px] gap-6">
        <WorkOrderList />
        <SegmentOverridePanel />
      </div>

      {/* Repair history */}
      <RepairHistoryLog />

    </div>
  )
}
