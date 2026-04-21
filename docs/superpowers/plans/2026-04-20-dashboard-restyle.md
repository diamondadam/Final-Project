# Dashboard Restyle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the reference dashboard's color scheme uniformly across NavBar, AnalyticsPage, and MaintenancePage (and all sub-components), with responsive text sizing using `clamp()` and responsive grid layouts using `lg:` breakpoints.

**Architecture:** CSS custom properties (design tokens) are defined once in `index.css` and referenced throughout via Tailwind's `[var(--token)]` arbitrary-value syntax. No new components are created — only class strings and inline style colors change. `CLASS_COLORS` in `types.ts` is updated so all components that already import it automatically pick up the new palette.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, Recharts, Vite

---

## File Map

| File | Change |
|---|---|
| `frontend/src/index.css` | Add 13 CSS custom property tokens; update body bg |
| `frontend/src/App.tsx` | Update root div bg class |
| `frontend/src/types.ts` | Update `CLASS_COLORS` hex, text, bg values |
| `frontend/src/components/NavBar.tsx` | Full restyle to reference palette |
| `frontend/src/pages/AnalyticsPage.tsx` | Responsive padding, section headers, grid |
| `frontend/src/components/analytics/SpeedAlertChart.tsx` | Card style, tooltip, line + band colors |
| `frontend/src/components/analytics/CommandedVsTargetChart.tsx` | Card style, tooltip, line colors |
| `frontend/src/components/analytics/AlertBreakdown.tsx` | Card style, tile colors |
| `frontend/src/components/analytics/PositionTimeline.tsx` | Card style, line color |
| `frontend/src/components/analytics/HealthHeatmap.tsx` | Card style, cell colors |
| `frontend/src/components/analytics/BeliefConvergence.tsx` | Card style (inherits CLASS_COLORS) |
| `frontend/src/pages/MaintenancePage.tsx` | Responsive padding/grid, action bar, reset button |
| `frontend/src/components/maintenance/WorkOrderList.tsx` | Row tint bg, badge, complete button |
| `frontend/src/components/maintenance/SegmentOverridePanel.tsx` | Card style, override buttons |
| `frontend/src/components/maintenance/RepairHistoryLog.tsx` | Badge colors, row style |

---

### Task 1: CSS tokens + App root background

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Replace index.css with the token-extended version**

Replace the entire contents of `frontend/src/index.css` with:

```css
@import "tailwindcss";

:root {
  --rt-bg:         #111827;
  --rt-surface:    #1f2937;
  --rt-sidebar-bg: #1a2332;
  --rt-border:     #374151;
  --rt-border-dim: #2d3748;
  --rt-cream:      #FDFBD4;
  --rt-blue:       #87CEEB;
  --rt-green:      #ADEBB3;
  --rt-amber:      #f59e0b;
  --rt-red:        #FF1A1A;
  --rt-muted:      #6b7280;
  --rt-muted-dim:  #4b5563;
  --rt-text:       #e5e7eb;
}

body {
  margin: 0;
  background: var(--rt-bg);
  color: var(--rt-text);
  font-family: 'Segoe UI', system-ui, Roboto, sans-serif;
}

#root {
  width: 100%;
  min-height: 100vh;
}
```

- [ ] **Step 2: Update App.tsx root div**

In `frontend/src/App.tsx`, change the root div class from `bg-[#0f1117]` to `bg-[var(--rt-bg)]`:

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useTwinWebSocket } from './hooks/useTwinWebSocket'
import { NavBar } from './components/NavBar'
import { TrackDashboard } from './components/TrackDashboard'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { MaintenancePage } from './pages/MaintenancePage'

export default function App() {
  useTwinWebSocket()

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[var(--rt-bg)] flex flex-col">
        <NavBar />
        <div className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<TrackDashboard />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/maintenance" element={<MaintenancePage />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css frontend/src/App.tsx
git commit -m "style: add reference dashboard CSS tokens to index.css"
```

---

### Task 2: Update CLASS_COLORS in types.ts

**Files:**
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Update CLASS_COLORS constant**

In `frontend/src/types.ts`, replace the `CLASS_COLORS` block (lines 32–36):

```ts
export const CLASS_COLORS = {
  Healthy:  { bg: 'bg-[#ADEBB3]', text: 'text-[#ADEBB3]', hex: '#ADEBB3' },
  Degraded: { bg: 'bg-[#f59e0b]', text: 'text-[#f59e0b]', hex: '#f59e0b' },
  Damaged:  { bg: 'bg-[#FF1A1A]', text: 'text-[#FF1A1A]', hex: '#FF1A1A' },
} as const
```

- [ ] **Step 2: Run existing tests to verify nothing broke**

```bash
cd frontend && npm run test
```

Expected: all tests pass (CLASS_COLORS consumers use `.hex` or `.text` — same shape, new values).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts
git commit -m "style: update CLASS_COLORS to reference dashboard palette"
```

---

### Task 3: NavBar

**Files:**
- Modify: `frontend/src/components/NavBar.tsx`

- [ ] **Step 1: Replace NavBar with reference-styled version**

Replace the entire contents of `frontend/src/components/NavBar.tsx`:

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/NavBar.tsx
git commit -m "style: restyle NavBar to reference dashboard palette"
```

---

### Task 4: AnalyticsPage layout

**Files:**
- Modify: `frontend/src/pages/AnalyticsPage.tsx`

- [ ] **Step 1: Replace AnalyticsPage with responsive version**

Replace the entire contents of `frontend/src/pages/AnalyticsPage.tsx`:

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AnalyticsPage.tsx
git commit -m "style: responsive layout for AnalyticsPage"
```

---

### Task 5: SpeedAlertChart

**Files:**
- Modify: `frontend/src/components/analytics/SpeedAlertChart.tsx`

- [ ] **Step 1: Replace SpeedAlertChart**

Replace the entire contents of `frontend/src/components/analytics/SpeedAlertChart.tsx`:

```tsx
import {
  ComposedChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceArea, ReferenceLine,
} from 'recharts'
import { useTwinStore } from '../../store/twinStore'
import { getAlertRuns } from './utils'

const ALERT_FILL: Record<string, string> = {
  CLEAR:   '#ADEBB314',
  WARNING: '#f59e0b14',
  DANGER:  '#FF1A1A14',
}

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#1f2937',
    border: '1px solid #374151',
    borderRadius: 4,
    fontSize: 11,
  },
  labelStyle: { color: '#6b7280' },
  itemStyle: { color: '#87CEEB' },
}

export function SpeedAlertChart() {
  const { tickHistory, alertHistory } = useTwinStore()
  const runs = getAlertRuns(alertHistory)

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px] flex items-center justify-between">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Speed + Alert Band
        </span>
        <span className="text-[7px] px-[7px] py-[2px] rounded-full border bg-[#87CEEB22] text-[var(--rt-blue)] border-[#87CEEB44] font-semibold">
          ● LIVE
        </span>
      </div>
      <div className="px-[11px] py-[8px]">
        {tickHistory.length < 2 ? (
          <div className="flex items-center justify-center h-[120px] text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)]">
            Waiting for data…
          </div>
        ) : (
          <div className="min-h-[120px] lg:min-h-[160px]">
            <ResponsiveContainer width="100%" height="100%" minHeight={120}>
              <ComposedChart data={tickHistory}>
                {runs.map((r, i) => (
                  <ReferenceArea
                    key={i}
                    x1={r.x1}
                    x2={r.x2}
                    fill={ALERT_FILL[r.level]}
                    strokeOpacity={0}
                  />
                ))}
                <ReferenceLine y={3.0} stroke="#374151" strokeDasharray="4 2" />
                <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#6b7280' }} />
                <YAxis domain={[0, 3.5]} tick={{ fontSize: 10, fill: '#6b7280' }} width={28} />
                <Tooltip {...TOOLTIP_STYLE} />
                <Line
                  type="monotone"
                  dataKey="speed"
                  stroke="#87CEEB"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/analytics/SpeedAlertChart.tsx
git commit -m "style: restyle SpeedAlertChart to reference palette"
```

---

### Task 6: CommandedVsTargetChart

**Files:**
- Modify: `frontend/src/components/analytics/CommandedVsTargetChart.tsx`

- [ ] **Step 1: Replace CommandedVsTargetChart**

Replace the entire contents of `frontend/src/components/analytics/CommandedVsTargetChart.tsx`:

```tsx
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts'
import { useTwinStore } from '../../store/twinStore'
import { getVSafeHistory } from './utils'

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#1f2937',
    border: '1px solid #374151',
    borderRadius: 4,
    fontSize: 11,
  },
  labelStyle: { color: '#6b7280' },
}

export function CommandedVsTargetChart() {
  const { tickHistory, positionHistory, segmentBeliefHistory } = useTwinStore()
  const chartData = getVSafeHistory(tickHistory, positionHistory, segmentBeliefHistory)

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Commanded vs. v_safe Target
        </span>
      </div>
      <div className="px-[11px] py-[8px]">
        {chartData.length < 2 ? (
          <div className="flex items-center justify-center h-[120px] text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)]">
            Waiting for data…
          </div>
        ) : (
          <div className="min-h-[120px] lg:min-h-[160px]">
            <ResponsiveContainer width="100%" height="100%" minHeight={120}>
              <LineChart data={chartData}>
                <ReferenceLine y={3.0} stroke="#374151" strokeDasharray="4 2" />
                <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#6b7280' }} />
                <YAxis domain={[0, 3.5]} tick={{ fontSize: 10, fill: '#6b7280' }} width={28} />
                <Tooltip
                  {...TOOLTIP_STYLE}
                  formatter={(val: number, name: string) => [
                    `${val.toFixed(2)} fps`,
                    name === 'vSafe' ? 'v_safe target' : 'commanded',
                  ]}
                />
                <Legend
                  wrapperStyle={{ fontSize: 10, color: '#6b7280' }}
                  formatter={(val) => (val === 'vSafe' ? 'v_safe target' : 'commanded')}
                />
                <Line
                  type="monotone"
                  dataKey="vSafe"
                  stroke="#f59e0b"
                  strokeWidth={1.5}
                  strokeDasharray="5 3"
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="commanded"
                  stroke="#87CEEB"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/analytics/CommandedVsTargetChart.tsx
git commit -m "style: restyle CommandedVsTargetChart to reference palette"
```

---

### Task 7: AlertBreakdown

**Files:**
- Modify: `frontend/src/components/analytics/AlertBreakdown.tsx`

- [ ] **Step 1: Replace AlertBreakdown**

Replace the entire contents of `frontend/src/components/analytics/AlertBreakdown.tsx`:

```tsx
import { useTwinStore } from '../../store/twinStore'
import { alertLevel } from './utils'

const TILES = [
  { level: 'CLEAR',   label: 'CLEAR',   color: 'var(--rt-green)', bg: '#ADEBB310' },
  { level: 'WARNING', label: 'WARNING', color: 'var(--rt-amber)', bg: '#f59e0b10' },
  { level: 'DANGER',  label: 'DANGER',  color: 'var(--rt-red)',   bg: '#FF1A1A10' },
] as const

export function AlertBreakdown() {
  const { alertHistory } = useTwinStore()
  const total = alertHistory.length

  const counts = { CLEAR: 0, WARNING: 0, DANGER: 0 }
  for (const { alert } of alertHistory) counts[alertLevel(alert)]++

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Alert Breakdown
        </span>
      </div>
      <div className="px-[11px] py-[8px] flex gap-2">
        {TILES.map(({ level, label, color, bg }) => {
          const pct = total === 0 ? 0 : Math.round((counts[level] / total) * 100)
          return (
            <div
              key={level}
              className="flex-1 rounded p-2 flex flex-col items-center gap-0.5"
              style={{ background: bg }}
            >
              <span
                className="text-[clamp(14px,2vw,20px)] font-bold font-mono"
                style={{ color }}
              >
                {pct}%
              </span>
              <span className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)]">{label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/analytics/AlertBreakdown.tsx
git commit -m "style: restyle AlertBreakdown to reference palette"
```

---

### Task 8: PositionTimeline

**Files:**
- Modify: `frontend/src/components/analytics/PositionTimeline.tsx`

- [ ] **Step 1: Replace PositionTimeline**

Replace the entire contents of `frontend/src/components/analytics/PositionTimeline.tsx`:

```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { useTwinStore } from '../../store/twinStore'

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#1f2937',
    border: '1px solid #374151',
    borderRadius: 4,
    fontSize: 11,
  },
  labelStyle: { color: '#6b7280' },
  itemStyle: { color: '#87CEEB' },
}

export function PositionTimeline() {
  const { positionHistory, state } = useTwinStore()
  const nSegs = state?.segments.length ?? 5

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden flex-1">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Train Position
        </span>
      </div>
      <div className="px-[11px] py-[8px]">
        {positionHistory.length < 2 ? (
          <div className="flex items-center justify-center h-16 text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)]">
            Waiting for data…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={100}>
            <LineChart data={positionHistory}>
              <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#6b7280' }} />
              <YAxis
                domain={[0, nSegs - 1]}
                ticks={Array.from({ length: nSegs }, (_, i) => i)}
                tickFormatter={(v) => `seg${v}`}
                tick={{ fontSize: 9, fill: '#6b7280' }}
                width={34}
              />
              <Tooltip
                {...TOOLTIP_STYLE}
                formatter={(v: number) => [`seg${v}`, 'position']}
              />
              <Line
                type="stepAfter"
                dataKey="segment"
                stroke="#87CEEB"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/analytics/PositionTimeline.tsx
git commit -m "style: restyle PositionTimeline to reference palette"
```

---

### Task 9: HealthHeatmap

**Files:**
- Modify: `frontend/src/components/analytics/HealthHeatmap.tsx`

- [ ] **Step 1: Replace HealthHeatmap**

Replace the entire contents of `frontend/src/components/analytics/HealthHeatmap.tsx`:

```tsx
import { useTwinStore } from '../../store/twinStore'

const STATE_COLOR: Record<number, string> = {
  0: '#ADEBB366',
  1: '#f59e0b66',
  2: '#FF1A1A66',
}

function getMapState(belief: [number, number, number]): number {
  return belief.indexOf(Math.max(...belief))
}

export function HealthHeatmap() {
  const { segmentBeliefHistory, state } = useTwinStore()
  const nSegs = state?.segments.length ?? 0

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Segment Health Heatmap
        </span>
      </div>
      <div className="px-[11px] py-[8px]">
        {nSegs === 0 || segmentBeliefHistory.length === 0 ? (
          <div className="flex items-center justify-center h-16 text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)]">
            Waiting for data…
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-1">
              {Array.from({ length: nSegs }, (_, segIdx) => (
                <div key={segIdx} className="flex items-center gap-1.5">
                  <span className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)] font-mono w-8 shrink-0">
                    seg{segIdx}
                  </span>
                  <div
                    className="flex-1 grid gap-px"
                    style={{ gridTemplateColumns: `repeat(${segmentBeliefHistory.length}, 1fr)` }}
                  >
                    {segmentBeliefHistory.map((snap, t) => {
                      const beliefs = snap.beliefs[segIdx]
                      const color = beliefs ? STATE_COLOR[getMapState(beliefs)] : '#1f2937'
                      return (
                        <div
                          key={t}
                          className="rounded-[1px]"
                          style={{ height: 10, background: color }}
                        />
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-3 mt-2">
              {[['Healthy', '#ADEBB366'], ['Degraded', '#f59e0b66'], ['Damaged', '#FF1A1A66']].map(([label, color]) => (
                <div key={label} className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-sm" style={{ background: color }} />
                  <span className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)]">{label}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/analytics/HealthHeatmap.tsx
git commit -m "style: restyle HealthHeatmap to reference palette"
```

---

### Task 10: BeliefConvergence

**Files:**
- Modify: `frontend/src/components/analytics/BeliefConvergence.tsx`

- [ ] **Step 1: Replace BeliefConvergence**

Replace the entire contents of `frontend/src/components/analytics/BeliefConvergence.tsx`:

```tsx
import { useTwinStore } from '../../store/twinStore'
import { CLASS_COLORS } from '../../types'

const BAR_COLORS = [
  CLASS_COLORS.Healthy.hex,
  CLASS_COLORS.Degraded.hex,
  CLASS_COLORS.Damaged.hex,
]
const BAR_LABELS = ['H', 'D', 'X']

export function BeliefConvergence() {
  const { state } = useTwinStore()

  return (
    <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden flex-1">
      <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
        <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
          Belief Convergence
        </span>
      </div>
      <div className="px-[11px] py-[8px]">
        {!state ? (
          <div className="flex items-center justify-center h-16 text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)]">
            Waiting for data…
          </div>
        ) : (
          <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${state.segments.length}, 1fr)` }}>
            {state.segments.map((seg) => (
              <div key={seg.id} className="flex flex-col gap-1">
                <span className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)] font-mono text-center">
                  SEG {seg.id}
                </span>
                <div className="flex items-end justify-center gap-0.5 h-10">
                  {seg.belief.map((p, i) => (
                    <div key={i} className="flex flex-col items-center gap-px flex-1">
                      <div
                        className="w-full rounded-sm transition-all duration-500"
                        style={{
                          height: `${Math.max(p * 100, 4)}%`,
                          backgroundColor: BAR_COLORS[i],
                          opacity: 0.8,
                        }}
                      />
                      <span className="text-[clamp(7px,0.8vw,8px)] text-[var(--rt-muted)]">{BAR_LABELS[i]}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/analytics/BeliefConvergence.tsx
git commit -m "style: restyle BeliefConvergence to reference palette"
```

---

### Task 11: MaintenancePage layout

**Files:**
- Modify: `frontend/src/pages/MaintenancePage.tsx`

- [ ] **Step 1: Replace MaintenancePage**

Replace the entire contents of `frontend/src/pages/MaintenancePage.tsx`:

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/MaintenancePage.tsx
git commit -m "style: responsive layout for MaintenancePage"
```

---

### Task 12: WorkOrderList

**Files:**
- Modify: `frontend/src/components/maintenance/WorkOrderList.tsx`

- [ ] **Step 1: Replace WorkOrderList**

Replace the entire contents of `frontend/src/components/maintenance/WorkOrderList.tsx`:

```tsx
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
            color: 'var(--rt-green)',
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
                style={{ background: '#FF1A1A22', color: 'var(--rt-red)', borderColor: '#FF1A1A44' }}
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/maintenance/WorkOrderList.tsx
git commit -m "style: restyle WorkOrderList to reference palette"
```

---

### Task 13: SegmentOverridePanel

**Files:**
- Modify: `frontend/src/components/maintenance/SegmentOverridePanel.tsx`

- [ ] **Step 1: Replace SegmentOverridePanel**

Replace the entire contents of `frontend/src/components/maintenance/SegmentOverridePanel.tsx`:

```tsx
import { useTwinStore } from '../../store/twinStore'
import { CLASS_COLORS } from '../../types'

const OVERRIDE_BUTTONS = [
  { state: 0, label: 'H', bg: '#ADEBB322', color: 'var(--rt-green)', border: '#ADEBB344', hoverBg: '#ADEBB344', activeBorder: '#ADEBB3' },
  { state: 1, label: 'D', bg: '#f59e0b22', color: 'var(--rt-amber)', border: '#f59e0b44', hoverBg: '#f59e0b44', activeBorder: '#f59e0b'  },
  { state: 2, label: 'X', bg: '#FF1A1A22', color: 'var(--rt-red)',   border: '#FF1A1A44', hoverBg: '#FF1A1A44', activeBorder: '#FF1A1A'  },
] as const

export function SegmentOverridePanel() {
  const { state, applyCorrection } = useTwinStore()

  return (
    <section className="flex flex-col gap-3">
      <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
        <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
          <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
            Segment Override (HITL)
          </span>
          <p className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)] mt-0.5">
            Force-set a segment's belief state
          </p>
        </div>
        <div className="px-[11px] py-[8px]">
          {!state ? (
            <div className="text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)] py-4 text-center">
              Waiting for connection…
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              {state.segments.map((seg) => {
                const colors = CLASS_COLORS[seg.map_state_name]
                return (
                  <div
                    key={seg.id}
                    className="bg-[var(--rt-bg)] border border-[var(--rt-border)] rounded p-3 flex flex-col gap-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[clamp(7px,0.8vw,9px)] text-[var(--rt-muted)] font-mono">
                        SEG {seg.id}
                      </span>
                      <span
                        className="text-[clamp(7px,0.8vw,9px)] font-semibold"
                        style={{ color: colors.hex }}
                      >
                        {seg.map_state_name.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex gap-1.5">
                      {OVERRIDE_BUTTONS.map((btn) => (
                        <button
                          key={btn.state}
                          onClick={() => applyCorrection(seg.id, btn.state)}
                          className="flex-1 text-[clamp(9px,1vw,11px)] font-bold py-1 rounded transition-all border"
                          style={{
                            background: btn.bg,
                            color: btn.color,
                            borderColor: seg.map_state === btn.state ? btn.activeBorder : btn.border,
                            outline: seg.map_state === btn.state ? `1px solid ${btn.activeBorder}` : 'none',
                          }}
                          onMouseEnter={e => (e.currentTarget.style.background = btn.hoverBg)}
                          onMouseLeave={e => (e.currentTarget.style.background = btn.bg)}
                        >
                          {btn.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/maintenance/SegmentOverridePanel.tsx
git commit -m "style: restyle SegmentOverridePanel to reference palette"
```

---

### Task 14: RepairHistoryLog

**Files:**
- Modify: `frontend/src/components/maintenance/RepairHistoryLog.tsx`

- [ ] **Step 1: Replace RepairHistoryLog**

Replace the entire contents of `frontend/src/components/maintenance/RepairHistoryLog.tsx`:

```tsx
import { useTwinStore } from '../../store/twinStore'
import type { RepairLogEntry } from '../../store/twinStore'

const BADGE: Record<RepairLogEntry['type'], { bg: string; color: string; border: string }> = {
  REPAIRED: { bg: '#ADEBB322', color: 'var(--rt-green)', border: '#ADEBB344' },
  OVERRIDE: { bg: '#87CEEB22', color: 'var(--rt-blue)',  border: '#87CEEB44' },
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function RepairHistoryLog() {
  const { repairLog } = useTwinStore()

  return (
    <section className="flex flex-col gap-3">
      <div className="bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden">
        <div className="border-b border-[var(--rt-border)] px-[11px] py-[7px]">
          <span className="text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase">
            Repair History
          </span>
        </div>
        <div className="px-[11px] py-[8px]">
          {repairLog.length === 0 ? (
            <div className="text-[var(--rt-muted)] text-[clamp(9px,1vw,11px)] py-4 text-center">
              No repairs or overrides yet
            </div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {repairLog.map((entry, i) => {
                const badge = BADGE[entry.type]
                return (
                  <div
                    key={`${entry.timestamp}-${entry.segment_id}-${i}`}
                    className="flex items-center gap-3 px-3 py-2 rounded border border-[var(--rt-border)] bg-[var(--rt-bg)]"
                  >
                    <span className="text-[clamp(8px,0.9vw,10px)] text-[var(--rt-muted)] font-mono w-16 shrink-0">
                      {formatTime(entry.timestamp)}
                    </span>
                    <span
                      className="text-[clamp(7px,0.8vw,9px)] font-semibold px-1.5 py-0.5 rounded shrink-0 border"
                      style={{ background: badge.bg, color: badge.color, borderColor: badge.border }}
                    >
                      {entry.type}
                    </span>
                    <span className="text-[clamp(9px,1vw,11px)] text-[var(--rt-text)]">
                      Segment {entry.segment_id} — {entry.detail}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/maintenance/RepairHistoryLog.tsx
git commit -m "style: restyle RepairHistoryLog to reference palette"
```

---

### Task 15: Verify tests, lint, and final commit

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

```bash
cd frontend && npm run test
```

Expected output: all tests pass. The `twinStore.test.ts` and `utils.test.ts` suites test behavior only — no visual classes — so they must be unaffected.

- [ ] **Step 2: Run lint**

```bash
cd frontend && npm run lint
```

Expected: no errors. If any `no-unused-vars` or similar fire on removed Tailwind class imports, fix them inline.

- [ ] **Step 3: Build to catch TypeScript errors**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no type errors.

- [ ] **Step 4: Final commit**

```bash
cd frontend
git add -A
git commit -m "style: complete reference dashboard restyle across analytics and maintenance pages"
```
