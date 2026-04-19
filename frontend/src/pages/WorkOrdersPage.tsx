import { WorkOrderPanel } from '../components/WorkOrderPanel'

export function WorkOrdersPage() {
  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-white tracking-tight">Work Orders</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Track repair requests and reset segment beliefs on completion</p>
      </div>
      <WorkOrderPanel />
    </div>
  )
}
