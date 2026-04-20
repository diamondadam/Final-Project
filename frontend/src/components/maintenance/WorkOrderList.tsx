import { useEffect } from 'react'
import { useTwinStore } from '../../store/twinStore'
import type { WorkOrder } from '../../types'

const SEVERITY_STYLES = {
  DAMAGED:  { badge: 'bg-red-500/20 text-red-400 ring-1 ring-red-500/30',    dot: 'bg-red-500'    },
  DEGRADED: { badge: 'bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/30', dot: 'bg-amber-500' },
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function WorkOrderRow({ wo, onComplete }: { wo: WorkOrder; onComplete: (id: string, segId: number) => void }) {
  const sev = SEVERITY_STYLES[wo.severity]
  const isOpen = wo.status === 'OPEN'

  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
      isOpen ? 'border-white/10 bg-white/[0.03]' : 'border-white/5 bg-white/[0.015] opacity-50'
    }`}>
      <span className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${sev.dot} ${isOpen ? '' : 'opacity-40'}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${sev.badge}`}>
            {wo.severity}
          </span>
          <span className="text-xs text-zinc-300 font-medium">Segment {wo.segment_id}</span>
          <span className="text-[10px] text-zinc-600 font-mono">{formatTime(wo.created_at)}</span>
        </div>
        <p className="text-[11px] text-zinc-500 mt-0.5 truncate">{wo.alert_message}</p>
        <div className="flex gap-3 mt-1 text-[10px] text-zinc-600">
          <span>Confidence: {(wo.confidence * 100).toFixed(0)}%</span>
          <span>Speed: {wo.commanded_speed_fps.toFixed(2)} fps</span>
          {wo.completed_at && <span>Completed: {formatTime(wo.completed_at)}</span>}
        </div>
      </div>
      {isOpen && (
        <button
          onClick={() => onComplete(wo.id, wo.segment_id)}
          className="flex-shrink-0 text-[11px] px-2.5 py-1 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition-colors"
        >
          Complete
        </button>
      )}
    </div>
  )
}

export function WorkOrderList() {
  const { workOrders, refreshWorkOrders, completeWorkOrder, addRepairLog } = useTwinStore()

  useEffect(() => {
    refreshWorkOrders()
    const id = setInterval(refreshWorkOrders, 5000)
    return () => clearInterval(id)
  }, [refreshWorkOrders])

  async function handleComplete(id: string, segmentId: number) {
    await completeWorkOrder(id)
    addRepairLog({
      timestamp: new Date().toISOString(),
      type: 'REPAIRED',
      segment_id: segmentId,
      detail: 'work order completed, belief reset',
    })
  }

  const open = workOrders.filter((w) => w.status === 'OPEN')
  const completed = workOrders.filter((w) => w.status === 'COMPLETED')

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase">
          Work Orders
        </h2>
        <div className="flex items-center gap-2">
          {open.length > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400 ring-1 ring-red-500/30 font-semibold">
              {open.length} open
            </span>
          )}
          <button
            onClick={refreshWorkOrders}
            className="text-[11px] text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {workOrders.length === 0 ? (
        <div className="text-zinc-600 text-sm py-6 text-center rounded-xl border border-white/5">
          No work orders — all segments nominal
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {open.map((wo) => (
            <WorkOrderRow key={wo.id} wo={wo} onComplete={handleComplete} />
          ))}
          {completed.length > 0 && open.length > 0 && (
            <div className="border-t border-white/5 pt-2 mt-1" />
          )}
          {completed.map((wo) => (
            <WorkOrderRow key={wo.id} wo={wo} onComplete={handleComplete} />
          ))}
        </div>
      )}
    </section>
  )
}
