import { SpeedAlertChart } from '../components/analytics/SpeedAlertChart'
import { AlertBreakdown } from '../components/analytics/AlertBreakdown'
import { PositionTimeline } from '../components/analytics/PositionTimeline'
import { CommandedVsTargetChart } from '../components/analytics/CommandedVsTargetChart'
import { HealthHeatmap } from '../components/analytics/HealthHeatmap'

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
          <div className="flex flex-col gap-4">
            <AlertBreakdown />
            <PositionTimeline />
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
          ② MPC Controller Performance
        </h2>
        <div className="grid grid-cols-[1fr_280px] gap-4">
          <CommandedVsTargetChart />
          <div className="flex flex-col gap-4">
            <HealthHeatmap />
            <div className="text-zinc-600 text-sm p-4">belief panel coming…</div>
          </div>
        </div>
      </section>
    </div>
  )
}
