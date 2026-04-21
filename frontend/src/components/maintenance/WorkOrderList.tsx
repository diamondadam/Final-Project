import { useEffect } from 'react'
import { useTwinStore } from '../../store/twinStore'
import type { WorkOrder } from '../../types'

const SEVERITY_STYLES = {
  DAMAGED:  {
    rowBg: '#1f1515', rowBorder: '#FF1A1A44',
    badgeBg: '#FF1A1A22', badgeColor: '#FF1A1A', badgeBorder: '#FF1A1A44',
    dotColor: '#FF1A1A',
  },
  DEGRADED: {
    rowBg: '#1f1a0f', rowBorder: '#f59e0b44',
    badgeBg: '#f59e0b22', badgeColor: '#f59e0b', badgeBorder: '#f59e0b44',
    dotColor: '#f59e0b',
  },
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function WorkOrderRow({ wo, onComplete }: { wo: WorkOrder; onComplete: (id: string, segId: number) => void }) {
  const sev = SEVERITY_STYLES[wo.severity]
  const isOpen = wo.status === 'OPEN'

  return (
    <div
      className={`flex items-start gap-3 p-3 rounded border transition-colors ${
        isOpen ? '' : 'opacity-50 bg-[var(--rt-surface)] border-[var(--rt-border)]'
      }`}
      style={isOpen ? { background: sev.rowBg, borderColor: sev.rowBorder } : undefined}
    >
      <span
        className="mt-1 w-2 h-2 rounded-full flex-shrink-0"
        style={{ background: isOpen ? sev.dotColor : '#6b7280' }}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className="text-[clamp(8px,0.9vw,10px)] font-semibold px-1.5 py-0.5 rounded border"
            style={{ background: sev.badgeBg, color: sev.badgeColor, borderColor: sev.badgeBorder }}
          >
            {wo.severity}
          </span>
          <span className="text-[clamp(9px,1.1vw,12px)] text-[var(--rt-text)] font-medium">
            Segment {wo.segment_id}
          </span>
          <span className="text-[clamp(8px,0.9vw,10px)] text-[var(--rt-muted)] font-mono">
            {formatTime(wo.created_at)}
          </span>
        </div>
        <p className="text-[clamp(8px,1vw,11px)] text-[var(--rt-muted)] mt-0.5 truncate">{wo.alert_message}</p>
        <div className="flex gap-3 mt-1 text-[clamp(7px,0.9vw,10px)] text-[var(--rt-muted-dim)]">
          <span>Confidence: {(wo.confidence * 100).toFixed(0)}%</span>
          <span>Speed: {wo.commanded_speed_fps.toFixed(2)} fps</span>
          {wo.completed_at && <span>Completed: {formatTime(wo.completed_at)}</span>}
        </div>
      </div>
      {isOpen && (
        <button
          onClick={() => onComplete(wo.id, wo.segment_id)}
          className="flex-shrink-0 text-[clamp(8px,0.9vw,10px)] px-3 py-1.5 rounded font-semibold transition-colors border"
          style={{
            background: '#ADEBB322',
            color: '#ADEBB3',
            borderColor: '#ADEBB355',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#ADEBB344')}
          onMouseLeave={e => (e.currentTarget.style.background = '#ADEBB322')}
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
      <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
        <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px] flex items-center justify-between">
          <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
            Work Orders
          </span>
          <div className="flex items-center gap-2">
            {open.length > 0 && (
              <span
                className="text-[clamp(7px,0.8vw,9px)] px-[7px] py-[2px] rounded-full border font-semibold"
                style={{ background: '#FF1A1A22', color: '#FF1A1A', borderColor: '#FF1A1A44' }}
              >
                {open.length} open
              </span>
            )}
            <button
              onClick={refreshWorkOrders}
              className="text-[clamp(8px,0.9vw,10px)] text-[var(--rt-muted)] hover:text-[var(--rt-text)] transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>
        <div className="px-[11px] py-[8px]">
          {workOrders.length === 0 ? (
            <div className="text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)] py-6 text-center">
              No work orders — all segments nominal
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {open.map((wo) => (
                <WorkOrderRow key={wo.id} wo={wo} onComplete={handleComplete} />
              ))}
              {completed.length > 0 && open.length > 0 && (
                <div className="border-t border-[var(--rt-border)] pt-2 mt-1" />
              )}
              {completed.map((wo) => (
                <WorkOrderRow key={wo.id} wo={wo} onComplete={handleComplete} />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
