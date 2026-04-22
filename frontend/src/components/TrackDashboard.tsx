import React from 'react';
import { useTwinStore } from '../store/twinStore'
import { AlertBanner } from './AlertBanner'
import { TrackConfigurator } from './TrackConfigurator'
import { LiveFeedHUD } from './dashboard/LiveFeedHUD'
import { SegmentStatusList } from './dashboard/SegmentStatusList'
import { TelemetryChart } from './dashboard/TelemetryChart'
import { LogisticsPartsTable } from './dashboard/LogisticsPartsTable'

export function TrackDashboard() {
  const { state } = useTwinStore()

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[clamp(14px,1.8vw,20px)] font-bold text-white tracking-widest uppercase">
            Kinetic Digital Twin
          </h1>
          <p className="text-[clamp(9px,1vw,11px)] text-[var(--rt-blue)] mt-0.5 tracking-wider uppercase">System Node 04 - Main Terminal</p>
        </div>
        <AlertBanner />
      </div>

      {/* Main 2x2 Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {/* Top Left: Live Feed HUD (Takes up more space if we want, but 2x2 is fine. Let's do a 2-column layout where left is 2 parts, right is 1 part if we use xl:grid-cols-3) */}
        <div className="xl:col-span-2">
          <LiveFeedHUD />
        </div>
        
        {/* Top Right: Segment Status */}
        <div className="xl:col-span-1">
          <SegmentStatusList />
        </div>

        {/* Bottom Left: Telemetry Chart */}
        <div className="xl:col-span-2">
          <TelemetryChart />
        </div>

        {/* Bottom Right: Logistics & Parts */}
        <div className="xl:col-span-1">
          <LogisticsPartsTable />
        </div>
      </div>

      {/* Track configurator for demo controls */}
      <div className="mt-8">
         <h2 className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-widest text-zinc-500 uppercase mb-3">
           System Override & Simulation Controls
         </h2>
         <TrackConfigurator />
      </div>

    </div>
  )
}
