import { SpeedAlertChart } from '../components/analytics/SpeedAlertChart'

export function AnalyticsPage() {
  return (
    <div className="flex flex-col gap-6 p-6 overflow-y-auto">
      <div>
        <h1 className="text-xl font-semibold text-white tracking-tight">Analytics</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Train telemetry and MPC controller performance</p>
      </div>

      <section>
        <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
          ① Train Telemetry
        </h2>
        <div className="grid grid-cols-[1fr_280px] gap-4">
          <SpeedAlertChart />
          <div className="text-zinc-600 text-sm p-4">companions coming…</div>
        </div>
      </section>
    </div>
  )
}
