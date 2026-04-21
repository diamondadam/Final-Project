import { SpeedAlertChart } from '../components/analytics/SpeedAlertChart'
import { AlertBreakdown } from '../components/analytics/AlertBreakdown'
import { PositionTimeline } from '../components/analytics/PositionTimeline'
import { CommandedVsTargetChart } from '../components/analytics/CommandedVsTargetChart'
import { HealthHeatmap } from '../components/analytics/HealthHeatmap'
import { BeliefConvergence } from '../components/analytics/BeliefConvergence'

export function AnalyticsPage() {
  return (
    <div className="flex flex-col gap-5 p-3 sm:p-4 lg:p-6 overflow-y-auto">
      <div>
        <h1 className="text-[clamp(14px,1.8vw,20px)] font-bold text-[var(--rt-cream)] tracking-tight uppercase">
          Analytics
        </h1>
        <p className="text-[clamp(9px,1vw,11px)] text-[var(--rt-muted)] mt-0.5">
          Train telemetry and MPC controller performance
        </p>
      </div>

      <section>
        <h2 className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-muted)] uppercase mb-3">
          ① Train Telemetry
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-4">
          <SpeedAlertChart />
          <div className="flex flex-col gap-4">
            <AlertBreakdown />
            <PositionTimeline />
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-muted)] uppercase mb-3">
          ② MPC Controller Performance
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-4">
          <CommandedVsTargetChart />
          <div className="flex flex-col gap-4">
            <HealthHeatmap />
            <BeliefConvergence />
          </div>
        </div>
      </section>
    </div>
  )
}
