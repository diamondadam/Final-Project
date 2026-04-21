# Analytics & Maintenance Pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Analytics page (6-panel telemetry + MPC dashboard) and a Maintenance page (work orders + HITL overrides + repair log) to the existing React frontend.

**Architecture:** All data is sourced from the existing Zustand store; three new history arrays and a repair log are appended to the store's `setState` reducer. No backend changes are needed. Analytics uses Recharts `ComposedChart` for the two featured panels and CSS-grid/div components for heatmap and belief convergence. Maintenance replaces `/work-orders` with a three-region page.

**Tech Stack:** React 19, TypeScript, Tailwind v4, Zustand 5, Recharts 3, Vite 8, Vitest

---

## File Map

**New files:**
```
frontend/src/components/analytics/utils.ts            ← pure helpers: alertLevel, getAlertRuns, getVSafeHistory
frontend/src/components/analytics/utils.test.ts       ← vitest unit tests for helpers
frontend/src/components/analytics/SpeedAlertChart.tsx
frontend/src/components/analytics/AlertBreakdown.tsx
frontend/src/components/analytics/PositionTimeline.tsx
frontend/src/components/analytics/CommandedVsTargetChart.tsx
frontend/src/components/analytics/HealthHeatmap.tsx
frontend/src/components/analytics/BeliefConvergence.tsx
frontend/src/components/maintenance/WorkOrderList.tsx
frontend/src/components/maintenance/SegmentOverridePanel.tsx
frontend/src/components/maintenance/RepairHistoryLog.tsx
frontend/src/pages/AnalyticsPage.tsx
frontend/src/pages/MaintenancePage.tsx
frontend/src/store/twinStore.test.ts                  ← vitest unit tests for store reducer
frontend/vitest.config.ts
```

**Modified files:**
```
frontend/package.json                  ← add vitest dev dep + test scripts
frontend/src/store/twinStore.ts        ← add history arrays, repairLog, new actions
frontend/src/components/NavBar.tsx     ← add Analytics link, rename Work Orders → Maintenance
frontend/src/App.tsx                   ← add /analytics + /maintenance routes, remove /work-orders
```

---

### Task 1: Vitest Setup

**Files:**
- Create: `frontend/vitest.config.ts`
- Modify: `frontend/package.json`

- [ ] **Step 1: Install vitest and jsdom**

```bash
cd frontend && npm install -D vitest jsdom
```

Expected: `node_modules/vitest` appears, no errors.

- [ ] **Step 2: Create vitest config**

Create `frontend/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
  },
})
```

- [ ] **Step 3: Add test scripts to package.json**

In `frontend/package.json`, add to `"scripts"`:

```json
"test": "vitest run",
"test:watch": "vitest"
```

Full scripts block after edit:

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "lint": "eslint .",
  "preview": "vite preview",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

- [ ] **Step 4: Write a smoke test to verify setup**

Create `frontend/src/store/twinStore.test.ts`:

```ts
import { describe, it, expect } from 'vitest'

describe('vitest setup', () => {
  it('works', () => {
    expect(1 + 1).toBe(2)
  })
})
```

- [ ] **Step 5: Run test to confirm passing**

```bash
cd frontend && npm test
```

Expected output:
```
✓ src/store/twinStore.test.ts (1)
Test Files  1 passed (1)
```

- [ ] **Step 6: Commit**

```bash
git add frontend/vitest.config.ts frontend/package.json frontend/src/store/twinStore.test.ts frontend/package-lock.json
git commit -m "feat: add vitest test runner to frontend"
```

---

### Task 2: Extend twinStore — History Arrays + Repair Log

**Files:**
- Modify: `frontend/src/store/twinStore.ts`
- Modify: `frontend/src/store/twinStore.test.ts`

- [ ] **Step 1: Write failing tests for the new store behaviour**

Replace `frontend/src/store/twinStore.test.ts` with:

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { useTwinStore } from './twinStore'
import type { TwinState } from '../types'

function makeTwinState(tick: number, alert: string, segment: number): TwinState {
  return {
    tick,
    timestamp: new Date().toISOString(),
    train_segment: segment,
    commanded_speed_fps: 2.5,
    alert,
    segments: [
      { id: 0, true_state: 0, belief: [0.9, 0.05, 0.05], map_state: 0, map_state_name: 'Healthy', entropy: 0.2 },
    ],
  }
}

describe('twinStore history arrays', () => {
  beforeEach(() => {
    useTwinStore.setState({
      state: null,
      tickHistory: [],
      alertHistory: [],
      positionHistory: [],
      segmentBeliefHistory: [],
      workOrders: [],
      connected: false,
      repairLog: [],
    })
  })

  it('setState appends to alertHistory', () => {
    const { setState } = useTwinStore.getState()
    setState(makeTwinState(1, 'CLEAR', 0))
    const { alertHistory } = useTwinStore.getState()
    expect(alertHistory).toHaveLength(1)
    expect(alertHistory[0]).toEqual({ tick: 1, alert: 'CLEAR' })
  })

  it('setState appends to positionHistory', () => {
    const { setState } = useTwinStore.getState()
    setState(makeTwinState(1, 'CLEAR', 2))
    const { positionHistory } = useTwinStore.getState()
    expect(positionHistory[0]).toEqual({ tick: 1, segment: 2 })
  })

  it('setState appends to segmentBeliefHistory', () => {
    const { setState } = useTwinStore.getState()
    setState(makeTwinState(1, 'CLEAR', 0))
    const { segmentBeliefHistory } = useTwinStore.getState()
    expect(segmentBeliefHistory[0].tick).toBe(1)
    expect(segmentBeliefHistory[0].beliefs[0]).toEqual([0.9, 0.05, 0.05])
  })

  it('history arrays are capped at 60 entries', () => {
    const { setState } = useTwinStore.getState()
    for (let i = 0; i < 65; i++) setState(makeTwinState(i, 'CLEAR', 0))
    const { alertHistory } = useTwinStore.getState()
    expect(alertHistory).toHaveLength(60)
    expect(alertHistory[59].tick).toBe(64)
  })
})

describe('twinStore repairLog', () => {
  beforeEach(() => {
    useTwinStore.setState({ repairLog: [] })
  })

  it('addRepairLog prepends to repairLog', () => {
    const { addRepairLog } = useTwinStore.getState()
    addRepairLog({ timestamp: 'a', type: 'REPAIRED', segment_id: 1, detail: 'done' })
    addRepairLog({ timestamp: 'b', type: 'OVERRIDE', segment_id: 2, detail: 'forced' })
    const { repairLog } = useTwinStore.getState()
    expect(repairLog[0].timestamp).toBe('b')
    expect(repairLog[1].timestamp).toBe('a')
  })

  it('clearRepairLog empties the log', () => {
    const { addRepairLog, clearRepairLog } = useTwinStore.getState()
    addRepairLog({ timestamp: 'a', type: 'REPAIRED', segment_id: 0, detail: 'x' })
    clearRepairLog()
    expect(useTwinStore.getState().repairLog).toHaveLength(0)
  })
})
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd frontend && npm test
```

Expected: multiple failures about `alertHistory`, `positionHistory`, etc. not existing.

- [ ] **Step 3: Update twinStore.ts**

Replace the full contents of `frontend/src/store/twinStore.ts` with:

```ts
import { create } from 'zustand'
import type { TwinState, WorkOrder } from '../types'

export interface RepairLogEntry {
  timestamp: string
  type: 'REPAIRED' | 'OVERRIDE'
  segment_id: number
  detail: string
}

interface TwinStore {
  state: TwinState | null
  connected: boolean
  tickHistory: { tick: number; speed: number; timestamp: string }[]
  alertHistory: { tick: number; alert: string }[]
  positionHistory: { tick: number; segment: number }[]
  segmentBeliefHistory: { tick: number; beliefs: [number, number, number][] }[]
  workOrders: WorkOrder[]
  repairLog: RepairLogEntry[]

  setState: (s: TwinState) => void
  setConnected: (c: boolean) => void
  setWorkOrders: (orders: WorkOrder[]) => void
  addRepairLog: (entry: RepairLogEntry) => void
  clearRepairLog: () => void
  refreshWorkOrders: () => Promise<void>
  completeWorkOrder: (id: string) => Promise<void>
  applyCorrection: (segment_id: number, state: number) => Promise<void>
  resetAll: () => Promise<void>
}

const CLASS_NAMES = ['Healthy', 'Degraded', 'Damaged']

export const useTwinStore = create<TwinStore>((set, get) => ({
  state: null,
  connected: false,
  tickHistory: [],
  alertHistory: [],
  positionHistory: [],
  segmentBeliefHistory: [],
  workOrders: [],
  repairLog: [],

  setState: (s) =>
    set((prev) => ({
      state: s,
      tickHistory: [
        ...prev.tickHistory.slice(-59),
        { tick: s.tick, speed: s.commanded_speed_fps, timestamp: s.timestamp },
      ],
      alertHistory: [
        ...prev.alertHistory.slice(-59),
        { tick: s.tick, alert: s.alert },
      ],
      positionHistory: [
        ...prev.positionHistory.slice(-59),
        { tick: s.tick, segment: s.train_segment },
      ],
      segmentBeliefHistory: [
        ...prev.segmentBeliefHistory.slice(-59),
        {
          tick: s.tick,
          beliefs: s.segments.map((seg) => seg.belief as [number, number, number]),
        },
      ],
    })),

  setConnected: (connected) => set({ connected }),

  setWorkOrders: (orders) => set({ workOrders: orders }),

  addRepairLog: (entry) =>
    set((prev) => ({ repairLog: [entry, ...prev.repairLog] })),

  clearRepairLog: () => set({ repairLog: [] }),

  refreshWorkOrders: async () => {
    try {
      const res = await fetch('/api/work-orders')
      const data = await res.json()
      set({ workOrders: data.work_orders })
    } catch {
      // silently ignore — UI will show stale data
    }
  },

  completeWorkOrder: async (id: string) => {
    await fetch(`/api/work-orders/${id}/complete`, { method: 'POST' })
    await get().refreshWorkOrders()
  },

  applyCorrection: async (segment_id: number, state: number) => {
    await fetch('/api/correction', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ segment_id, state }),
    })
    get().addRepairLog({
      timestamp: new Date().toISOString(),
      type: 'OVERRIDE',
      segment_id,
      detail: `forced → ${CLASS_NAMES[state]}`,
    })
  },

  resetAll: async () => {
    await fetch('/api/reset', { method: 'POST' })
    await get().refreshWorkOrders()
    set({ repairLog: [] })
  },
}))
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd frontend && npm test
```

Expected:
```
✓ src/store/twinStore.test.ts (7)
Test Files  1 passed (1)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/twinStore.ts frontend/src/store/twinStore.test.ts
git commit -m "feat: extend twinStore with history arrays and repair log"
```

---

### Task 3: Analytics Utility Helpers + Tests

**Files:**
- Create: `frontend/src/components/analytics/utils.ts`
- Create: `frontend/src/components/analytics/utils.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/components/analytics/utils.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { alertLevel, getAlertRuns, getVSafeHistory, V_SAFE_MULT } from './utils'

describe('alertLevel', () => {
  it('returns CLEAR for "CLEAR"', () => {
    expect(alertLevel('CLEAR')).toBe('CLEAR')
  })
  it('returns WARNING for warning strings', () => {
    expect(alertLevel('WARNING – Degraded track. Proceed with caution.')).toBe('WARNING')
  })
  it('returns DANGER for danger strings', () => {
    expect(alertLevel('DANGER – Damaged track detected. Speed reduced. Whistle!')).toBe('DANGER')
  })
})

describe('getAlertRuns', () => {
  it('returns empty array for empty input', () => {
    expect(getAlertRuns([])).toEqual([])
  })
  it('groups consecutive identical alert levels into runs', () => {
    const history = [
      { tick: 1, alert: 'CLEAR' },
      { tick: 2, alert: 'CLEAR' },
      { tick: 3, alert: 'WARNING – x' },
      { tick: 4, alert: 'CLEAR' },
    ]
    const runs = getAlertRuns(history)
    expect(runs).toHaveLength(3)
    expect(runs[0]).toEqual({ x1: 1, x2: 2, level: 'CLEAR' })
    expect(runs[1]).toEqual({ x1: 3, x2: 3, level: 'WARNING' })
    expect(runs[2]).toEqual({ x1: 4, x2: 4, level: 'CLEAR' })
  })
})

describe('V_SAFE_MULT', () => {
  it('maps health states to speed multipliers', () => {
    expect(V_SAFE_MULT[0]).toBe(3.0)
    expect(V_SAFE_MULT[1]).toBe(1.8)
    expect(V_SAFE_MULT[2]).toBe(0.9)
  })
})

describe('getVSafeHistory', () => {
  it('computes v_safe from MAP state of the current segment per tick', () => {
    const tickHistory = [{ tick: 1, speed: 2.5, timestamp: '' }]
    const positionHistory = [{ tick: 1, segment: 0 }]
    // segment 0 has Degraded MAP state (belief index 1 is highest)
    const segmentBeliefHistory = [{ tick: 1, beliefs: [[0.1, 0.8, 0.1] as [number,number,number]] }]
    const result = getVSafeHistory(tickHistory, positionHistory, segmentBeliefHistory)
    expect(result).toHaveLength(1)
    expect(result[0]).toEqual({ tick: 1, commanded: 2.5, vSafe: 1.8 })
  })
})
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd frontend && npm test
```

Expected: fails with "Cannot find module './utils'".

- [ ] **Step 3: Implement utils.ts**

Create `frontend/src/components/analytics/utils.ts`:

```ts
export type AlertLevel = 'CLEAR' | 'WARNING' | 'DANGER'

export function alertLevel(alert: string): AlertLevel {
  if (alert === 'CLEAR') return 'CLEAR'
  if (alert.startsWith('WARNING')) return 'WARNING'
  return 'DANGER'
}

export function getAlertRuns(
  history: { tick: number; alert: string }[],
): { x1: number; x2: number; level: AlertLevel }[] {
  if (history.length === 0) return []
  const runs: { x1: number; x2: number; level: AlertLevel }[] = []
  let runStart = history[0].tick
  let runLevel = alertLevel(history[0].alert)
  for (let i = 1; i < history.length; i++) {
    const lvl = alertLevel(history[i].alert)
    if (lvl !== runLevel) {
      runs.push({ x1: runStart, x2: history[i - 1].tick, level: runLevel })
      runStart = history[i].tick
      runLevel = lvl
    }
  }
  runs.push({ x1: runStart, x2: history[history.length - 1].tick, level: runLevel })
  return runs
}

export const V_SAFE_MULT: Record<number, number> = { 0: 3.0, 1: 1.8, 2: 0.9 }

export function getVSafeHistory(
  tickHistory: { tick: number; speed: number; timestamp: string }[],
  positionHistory: { tick: number; segment: number }[],
  segmentBeliefHistory: { tick: number; beliefs: [number, number, number][] }[],
): { tick: number; commanded: number; vSafe: number }[] {
  const len = Math.min(tickHistory.length, positionHistory.length, segmentBeliefHistory.length)
  const result: { tick: number; commanded: number; vSafe: number }[] = []
  for (let i = 0; i < len; i++) {
    const seg = positionHistory[i].segment
    const beliefs = segmentBeliefHistory[i].beliefs[seg]
    if (!beliefs) continue
    const mapState = beliefs.indexOf(Math.max(...beliefs))
    result.push({
      tick: tickHistory[i].tick,
      commanded: tickHistory[i].speed,
      vSafe: V_SAFE_MULT[mapState] ?? 3.0,
    })
  }
  return result
}
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
cd frontend && npm test
```

Expected:
```
✓ src/store/twinStore.test.ts (7)
✓ src/components/analytics/utils.test.ts (7)
Test Files  2 passed (2)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/analytics/utils.ts frontend/src/components/analytics/utils.test.ts
git commit -m "feat: add analytics utility helpers with tests"
```

---

### Task 4: NavBar + App Routes

**Files:**
- Modify: `frontend/src/components/NavBar.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Update NavBar.tsx**

Replace full contents of `frontend/src/components/NavBar.tsx`:

```tsx
import { NavLink } from 'react-router-dom'
import { useTwinStore } from '../store/twinStore'

export function NavBar() {
  const { connected, workOrders } = useTwinStore()
  const openCount = workOrders.filter((w) => w.status === 'OPEN').length

  return (
    <nav className="flex items-center gap-1 px-4 h-12 border-b border-white/10 bg-[#0f1117] shrink-0">
      <span className="text-sm font-semibold text-white mr-4 tracking-tight">Rail Twin</span>

      <NavLink
        to="/"
        end
        className={({ isActive }) =>
          `px-3 py-1.5 rounded-md text-sm transition-colors ${
            isActive ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`
        }
      >
        Dashboard
      </NavLink>

      <NavLink
        to="/analytics"
        className={({ isActive }) =>
          `px-3 py-1.5 rounded-md text-sm transition-colors ${
            isActive ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`
        }
      >
        Analytics
      </NavLink>

      <NavLink
        to="/maintenance"
        className={({ isActive }) =>
          `relative px-3 py-1.5 rounded-md text-sm transition-colors ${
            isActive ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`
        }
      >
        Maintenance
        {openCount > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
            {openCount > 9 ? '9+' : openCount}
          </span>
        )}
      </NavLink>

      <div className="ml-auto flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-zinc-600'}`} />
        <span className="text-xs text-zinc-500">{connected ? 'Live' : 'Disconnected'}</span>
      </div>
    </nav>
  )
}
```

- [ ] **Step 2: Update App.tsx**

Replace full contents of `frontend/src/App.tsx`:

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
      <div className="min-h-screen bg-[#0f1117] flex flex-col">
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

- [ ] **Step 3: Create placeholder pages so App.tsx compiles**

Create `frontend/src/pages/AnalyticsPage.tsx`:

```tsx
export function AnalyticsPage() {
  return <div className="p-6 text-zinc-500">Analytics — coming soon</div>
}
```

Create `frontend/src/pages/MaintenancePage.tsx`:

```tsx
export function MaintenancePage() {
  return <div className="p-6 text-zinc-500">Maintenance — coming soon</div>
}
```

- [ ] **Step 4: Start dev server and verify**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173. Verify:
- NavBar shows: Dashboard · Analytics · Maintenance
- `/analytics` renders "Analytics — coming soon"
- `/maintenance` renders "Maintenance — coming soon"
- `/work-orders` no longer exists (404 is fine)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/NavBar.tsx frontend/src/App.tsx frontend/src/pages/AnalyticsPage.tsx frontend/src/pages/MaintenancePage.tsx
git commit -m "feat: add Analytics and Maintenance routes, update NavBar"
```

---

### Task 5: SpeedAlertChart

**Files:**
- Create: `frontend/src/components/analytics/SpeedAlertChart.tsx`

- [ ] **Step 1: Implement SpeedAlertChart.tsx**

Create `frontend/src/components/analytics/SpeedAlertChart.tsx`:

```tsx
import {
  ComposedChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceArea, ReferenceLine,
} from 'recharts'
import { useTwinStore } from '../../store/twinStore'
import { getAlertRuns } from './utils'

const ALERT_FILL: Record<string, string> = {
  CLEAR:   '#10b98114',
  WARNING: '#f59e0b14',
  DANGER:  '#ef444414',
}

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#18181b',
    border: '1px solid #3f3f46',
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: '#a1a1aa' },
  itemStyle: { color: '#34d399' },
}

export function SpeedAlertChart() {
  const { tickHistory, alertHistory } = useTwinStore()
  const runs = getAlertRuns(alertHistory)

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 h-full">
      <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
        Speed + Alert Band
      </p>
      {tickHistory.length < 2 ? (
        <div className="flex items-center justify-center h-32 text-zinc-600 text-sm">
          Waiting for data…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
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
            <ReferenceLine y={3.0} stroke="#3f3f46" strokeDasharray="4 2" />
            <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#52525b' }} />
            <YAxis
              domain={[0, 3.5]}
              tick={{ fontSize: 10, fill: '#52525b' }}
              width={28}
            />
            <Tooltip {...TOOLTIP_STYLE} />
            <Line
              type="monotone"
              dataKey="speed"
              stroke="#34d399"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Wire into AnalyticsPage and verify in browser**

Replace `frontend/src/pages/AnalyticsPage.tsx`:

```tsx
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
```

Open http://localhost:5173/analytics. Verify:
- Speed line renders and updates each tick
- Background shading changes color with alert state
- Dashed reference line at 3.0 fps is visible
- Tooltip shows speed on hover

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/analytics/SpeedAlertChart.tsx frontend/src/pages/AnalyticsPage.tsx
git commit -m "feat: add SpeedAlertChart with alert band coloring"
```

---

### Task 6: AlertBreakdown + PositionTimeline

**Files:**
- Create: `frontend/src/components/analytics/AlertBreakdown.tsx`
- Create: `frontend/src/components/analytics/PositionTimeline.tsx`

- [ ] **Step 1: Implement AlertBreakdown.tsx**

Create `frontend/src/components/analytics/AlertBreakdown.tsx`:

```tsx
import { useTwinStore } from '../../store/twinStore'
import { alertLevel } from './utils'

const TILES = [
  { level: 'CLEAR',   label: 'CLEAR',   textCls: 'text-emerald-400', bgCls: 'bg-emerald-500/10' },
  { level: 'WARNING', label: 'WARNING', textCls: 'text-amber-400',   bgCls: 'bg-amber-500/10'   },
  { level: 'DANGER',  label: 'DANGER',  textCls: 'text-red-400',     bgCls: 'bg-red-500/10'     },
] as const

export function AlertBreakdown() {
  const { alertHistory } = useTwinStore()
  const total = alertHistory.length

  const counts = { CLEAR: 0, WARNING: 0, DANGER: 0 }
  for (const { alert } of alertHistory) counts[alertLevel(alert)]++

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4">
      <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
        Alert Breakdown
      </p>
      <div className="flex gap-2">
        {TILES.map(({ level, label, textCls, bgCls }) => {
          const pct = total === 0 ? 0 : Math.round((counts[level] / total) * 100)
          return (
            <div key={level} className={`flex-1 ${bgCls} rounded-lg p-2 flex flex-col items-center gap-0.5`}>
              <span className={`text-lg font-bold font-mono ${textCls}`}>{pct}%</span>
              <span className="text-[9px] text-zinc-600">{label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Implement PositionTimeline.tsx**

Create `frontend/src/components/analytics/PositionTimeline.tsx`:

```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { useTwinStore } from '../../store/twinStore'

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#18181b',
    border: '1px solid #3f3f46',
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: '#a1a1aa' },
  itemStyle: { color: '#818cf8' },
}

export function PositionTimeline() {
  const { positionHistory, state } = useTwinStore()
  const nSegs = state?.segments.length ?? 5

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 flex-1">
      <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
        Train Position
      </p>
      {positionHistory.length < 2 ? (
        <div className="flex items-center justify-center h-16 text-zinc-600 text-sm">
          Waiting for data…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={100}>
          <LineChart data={positionHistory}>
            <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#52525b' }} />
            <YAxis
              domain={[0, nSegs - 1]}
              ticks={Array.from({ length: nSegs }, (_, i) => i)}
              tickFormatter={(v) => `seg${v}`}
              tick={{ fontSize: 9, fill: '#52525b' }}
              width={34}
            />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(v: number) => [`seg${v}`, 'position']}
            />
            <Line
              type="stepAfter"
              dataKey="segment"
              stroke="#818cf8"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Wire companions into AnalyticsPage Section 1**

Update `frontend/src/pages/AnalyticsPage.tsx` — replace the companion placeholder with real components:

```tsx
import { SpeedAlertChart } from '../components/analytics/SpeedAlertChart'
import { AlertBreakdown } from '../components/analytics/AlertBreakdown'
import { PositionTimeline } from '../components/analytics/PositionTimeline'

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
        <div className="text-zinc-600 text-sm p-4">Section 2 coming…</div>
      </section>
    </div>
  )
}
```

- [ ] **Step 4: Verify in browser**

Open http://localhost:5173/analytics. Verify:
- AlertBreakdown shows three percentage tiles that update each tick
- PositionTimeline step chart cycles through segment indices
- Both companion panels sit flush in the right column alongside SpeedAlertChart

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/analytics/AlertBreakdown.tsx frontend/src/components/analytics/PositionTimeline.tsx frontend/src/pages/AnalyticsPage.tsx
git commit -m "feat: add AlertBreakdown and PositionTimeline companion panels"
```

---

### Task 7: CommandedVsTargetChart

**Files:**
- Create: `frontend/src/components/analytics/CommandedVsTargetChart.tsx`

- [ ] **Step 1: Implement CommandedVsTargetChart.tsx**

Create `frontend/src/components/analytics/CommandedVsTargetChart.tsx`:

```tsx
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts'
import { useTwinStore } from '../../store/twinStore'
import { getVSafeHistory } from './utils'

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#18181b',
    border: '1px solid #3f3f46',
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: '#a1a1aa' },
}

export function CommandedVsTargetChart() {
  const { tickHistory, positionHistory, segmentBeliefHistory } = useTwinStore()
  const chartData = getVSafeHistory(tickHistory, positionHistory, segmentBeliefHistory)

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 h-full">
      <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
        Commanded vs. v_safe Target
      </p>
      {chartData.length < 2 ? (
        <div className="flex items-center justify-center h-32 text-zinc-600 text-sm">
          Waiting for data…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={chartData}>
            <ReferenceLine y={3.0} stroke="#3f3f46" strokeDasharray="4 2" />
            <XAxis dataKey="tick" tick={{ fontSize: 10, fill: '#52525b' }} />
            <YAxis
              domain={[0, 3.5]}
              tick={{ fontSize: 10, fill: '#52525b' }}
              width={28}
            />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(val: number, name: string) => [
                `${val.toFixed(2)} fps`,
                name === 'vSafe' ? 'v_safe target' : 'commanded',
              ]}
            />
            <Legend
              wrapperStyle={{ fontSize: 10, color: '#71717a' }}
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
              stroke="#34d399"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Add Section 2 shell with the featured panel to AnalyticsPage**

Update `frontend/src/pages/AnalyticsPage.tsx` — replace the Section 2 placeholder:

```tsx
import { SpeedAlertChart } from '../components/analytics/SpeedAlertChart'
import { AlertBreakdown } from '../components/analytics/AlertBreakdown'
import { PositionTimeline } from '../components/analytics/PositionTimeline'
import { CommandedVsTargetChart } from '../components/analytics/CommandedVsTargetChart'

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
          <div className="text-zinc-600 text-sm p-4">companions coming…</div>
        </div>
      </section>
    </div>
  )
}
```

- [ ] **Step 3: Verify in browser**

Open http://localhost:5173/analytics. Verify:
- Two lines visible: amber dashed (v_safe target) and emerald solid (commanded)
- On healthy segments the lines overlap near 3.0 fps
- On degraded/damaged segments the amber line drops and commanded follows with slight smoothing lag
- Legend shows "v_safe target" and "commanded"

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/analytics/CommandedVsTargetChart.tsx frontend/src/pages/AnalyticsPage.tsx
git commit -m "feat: add CommandedVsTargetChart showing MPC smoothing"
```

---

### Task 8: HealthHeatmap

**Files:**
- Create: `frontend/src/components/analytics/HealthHeatmap.tsx`

- [ ] **Step 1: Implement HealthHeatmap.tsx**

Create `frontend/src/components/analytics/HealthHeatmap.tsx`:

```tsx
import { useTwinStore } from '../../store/twinStore'

const STATE_COLOR: Record<number, string> = {
  0: '#10b98166',  // Healthy — emerald
  1: '#f59e0b66',  // Degraded — amber
  2: '#ef444466',  // Damaged — red
}

function getMapState(belief: [number, number, number]): number {
  return belief.indexOf(Math.max(...belief))
}

export function HealthHeatmap() {
  const { segmentBeliefHistory, state } = useTwinStore()
  const nSegs = state?.segments.length ?? 0

  if (nSegs === 0 || segmentBeliefHistory.length === 0) {
    return (
      <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4">
        <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
          Segment Health Heatmap
        </p>
        <div className="flex items-center justify-center h-16 text-zinc-600 text-sm">
          Waiting for data…
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4">
      <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
        Segment Health Heatmap
      </p>
      <div className="flex flex-col gap-1">
        {Array.from({ length: nSegs }, (_, segIdx) => (
          <div key={segIdx} className="flex items-center gap-1.5">
            <span className="text-[9px] text-zinc-600 font-mono w-8 shrink-0">seg{segIdx}</span>
            <div
              className="flex-1 grid gap-px"
              style={{ gridTemplateColumns: `repeat(${segmentBeliefHistory.length}, 1fr)` }}
            >
              {segmentBeliefHistory.map((snap, t) => {
                const beliefs = snap.beliefs[segIdx]
                const color = beliefs
                  ? STATE_COLOR[getMapState(beliefs)]
                  : '#27272a'
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
        {[['Healthy', '#10b98166'], ['Degraded', '#f59e0b66'], ['Damaged', '#ef444466']].map(([label, color]) => (
          <div key={label} className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-sm" style={{ background: color }} />
            <span className="text-[9px] text-zinc-600">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add to AnalyticsPage Section 2 companion column**

Update `frontend/src/pages/AnalyticsPage.tsx` — add HealthHeatmap import and replace the companion placeholder in Section 2:

```tsx
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
```

- [ ] **Step 3: Verify in browser**

Open http://localhost:5173/analytics. Verify:
- One row per segment, labeled seg0…segN
- Each row fills left-to-right as ticks accumulate
- Cells are emerald/amber/red according to MAP state
- Color legend visible below the grid

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/analytics/HealthHeatmap.tsx frontend/src/pages/AnalyticsPage.tsx
git commit -m "feat: add SegmentHealthHeatmap CSS grid panel"
```

---

### Task 9: BeliefConvergence + Complete AnalyticsPage

**Files:**
- Create: `frontend/src/components/analytics/BeliefConvergence.tsx`
- Modify: `frontend/src/pages/AnalyticsPage.tsx`

- [ ] **Step 1: Implement BeliefConvergence.tsx**

Create `frontend/src/components/analytics/BeliefConvergence.tsx`:

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

  if (!state) {
    return (
      <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 flex-1">
        <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
          Belief Convergence
        </p>
        <div className="flex items-center justify-center h-16 text-zinc-600 text-sm">
          Waiting for data…
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 flex-1">
      <p className="text-xs font-semibold tracking-widest text-zinc-500 uppercase mb-3">
        Belief Convergence
      </p>
      <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${state.segments.length}, 1fr)` }}>
        {state.segments.map((seg) => (
          <div key={seg.id} className="flex flex-col gap-1">
            <span className="text-[9px] text-zinc-500 font-mono text-center">
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
                      opacity: 0.75,
                    }}
                  />
                  <span className="text-[8px] text-zinc-600">{BAR_LABELS[i]}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Complete AnalyticsPage — replace belief placeholder**

Replace the full contents of `frontend/src/pages/AnalyticsPage.tsx`:

```tsx
import { SpeedAlertChart } from '../components/analytics/SpeedAlertChart'
import { AlertBreakdown } from '../components/analytics/AlertBreakdown'
import { PositionTimeline } from '../components/analytics/PositionTimeline'
import { CommandedVsTargetChart } from '../components/analytics/CommandedVsTargetChart'
import { HealthHeatmap } from '../components/analytics/HealthHeatmap'
import { BeliefConvergence } from '../components/analytics/BeliefConvergence'

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
            <BeliefConvergence />
          </div>
        </div>
      </section>
    </div>
  )
}
```

- [ ] **Step 3: Full Analytics page verification in browser**

Open http://localhost:5173/analytics. With the backend running, verify all 6 panels:
- Section ①: SpeedAlertChart (speed + colored bands), AlertBreakdown (3 %-tiles), PositionTimeline (step chart)
- Section ②: CommandedVsTargetChart (two overlaid lines), HealthHeatmap (fills tick-by-tick), BeliefConvergence (animated mini bars per segment)
- Navigating away and back does not reset charts (store persists)

- [ ] **Step 4: Run all tests to confirm nothing regressed**

```bash
cd frontend && npm test
```

Expected: all tests still pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/analytics/BeliefConvergence.tsx frontend/src/pages/AnalyticsPage.tsx
git commit -m "feat: complete Analytics page with all 6 panels"
```

---

### Task 10: WorkOrderList (Maintenance)

**Files:**
- Create: `frontend/src/components/maintenance/WorkOrderList.tsx`

- [ ] **Step 1: Implement WorkOrderList.tsx**

Create `frontend/src/components/maintenance/WorkOrderList.tsx`:

```tsx
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
  }, [])

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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/maintenance/WorkOrderList.tsx
git commit -m "feat: add WorkOrderList with repairLog integration"
```

---

### Task 11: SegmentOverridePanel

**Files:**
- Create: `frontend/src/components/maintenance/SegmentOverridePanel.tsx`

- [ ] **Step 1: Implement SegmentOverridePanel.tsx**

Create `frontend/src/components/maintenance/SegmentOverridePanel.tsx`:

```tsx
import { useTwinStore } from '../../store/twinStore'
import { CLASS_COLORS } from '../../types'

const OVERRIDE_BUTTONS = [
  { state: 0, label: 'H', cls: 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30', activeCls: 'ring-1 ring-emerald-400' },
  { state: 1, label: 'D', cls: 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30',       activeCls: 'ring-1 ring-amber-400'   },
  { state: 2, label: 'X', cls: 'bg-red-500/20 text-red-400 hover:bg-red-500/30',             activeCls: 'ring-1 ring-red-400'     },
] as const

export function SegmentOverridePanel() {
  const { state, applyCorrection } = useTwinStore()

  if (!state) {
    return (
      <section className="flex flex-col gap-3">
        <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase">
          Segment Override (HITL)
        </h2>
        <div className="text-zinc-600 text-sm py-4 text-center">Waiting for connection…</div>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-3">
      <div>
        <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase">
          Segment Override (HITL)
        </h2>
        <p className="text-[11px] text-zinc-600 mt-1">Force-set a segment's belief state</p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {state.segments.map((seg) => {
          const colors = CLASS_COLORS[seg.map_state_name]
          return (
            <div
              key={seg.id}
              className="bg-white/[0.03] border border-white/10 rounded-xl p-3 flex flex-col gap-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-zinc-500 font-mono">SEG {seg.id}</span>
                <span className={`text-[10px] font-semibold ${colors.text}`}>
                  {seg.map_state_name.toUpperCase()}
                </span>
              </div>
              <div className="flex gap-1.5">
                {OVERRIDE_BUTTONS.map(({ state: btnState, label, cls, activeCls }) => (
                  <button
                    key={btnState}
                    onClick={() => applyCorrection(seg.id, btnState)}
                    className={`flex-1 text-[11px] font-bold py-1 rounded-md transition-all ${cls} ${
                      seg.map_state === btnState ? activeCls : ''
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/maintenance/SegmentOverridePanel.tsx
git commit -m "feat: add SegmentOverridePanel HITL controls"
```

---

### Task 12: RepairHistoryLog + Complete MaintenancePage

**Files:**
- Create: `frontend/src/components/maintenance/RepairHistoryLog.tsx`
- Modify: `frontend/src/pages/MaintenancePage.tsx`

- [ ] **Step 1: Implement RepairHistoryLog.tsx**

Create `frontend/src/components/maintenance/RepairHistoryLog.tsx`:

```tsx
import { useTwinStore } from '../../store/twinStore'
import type { RepairLogEntry } from '../../store/twinStore'

const BADGE: Record<RepairLogEntry['type'], string> = {
  REPAIRED: 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30',
  OVERRIDE: 'bg-indigo-500/20 text-indigo-400 ring-1 ring-indigo-500/30',
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function RepairHistoryLog() {
  const { repairLog } = useTwinStore()

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-xs font-semibold tracking-widest text-zinc-500 uppercase">
        Repair History
      </h2>
      {repairLog.length === 0 ? (
        <div className="text-zinc-600 text-sm py-4 text-center rounded-xl border border-white/5">
          No repairs or overrides yet
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {repairLog.map((entry, i) => (
            <div
              key={i}
              className="flex items-center gap-3 px-3 py-2 bg-white/[0.03] border border-white/5 rounded-lg"
            >
              <span className="text-[10px] text-zinc-600 font-mono w-16 shrink-0">
                {formatTime(entry.timestamp)}
              </span>
              <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0 ${BADGE[entry.type]}`}>
                {entry.type}
              </span>
              <span className="text-[11px] text-zinc-400">
                Segment {entry.segment_id} — {entry.detail}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
```

- [ ] **Step 2: Complete MaintenancePage.tsx**

Replace the full contents of `frontend/src/pages/MaintenancePage.tsx`:

```tsx
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
```

- [ ] **Step 3: Full Maintenance page verification in browser**

Open http://localhost:5173/maintenance with the backend running. Verify:
- Action bar shows open WO count and repair count, both update live
- Work order list shows open orders with Complete buttons; completing one adds a REPAIRED entry to Repair History
- Segment Override panel shows one card per segment; active state button is highlighted; clicking a different button calls POST /correction and adds OVERRIDE to history
- Reset All Beliefs button calls POST /reset and clears repair log
- Repair History shows entries in reverse-chronological order with correct REPAIRED/OVERRIDE badges

- [ ] **Step 4: Run all tests one final time**

```bash
cd frontend && npm test
```

Expected: all 14 tests pass.

- [ ] **Step 5: Final commit**

```bash
git add frontend/src/components/maintenance/RepairHistoryLog.tsx frontend/src/pages/MaintenancePage.tsx
git commit -m "feat: complete Maintenance page with work orders, HITL overrides, and repair log"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task covering it |
|---|---|
| Analytics Option B layout (featured + companion) | Tasks 5–9 |
| Speed + Alert Band chart with background colors | Task 5 |
| Alert State Breakdown 3 tiles | Task 6 |
| Train Position step chart | Task 6 |
| Commanded vs v_safe two-line chart | Task 7 |
| Segment Health Heatmap CSS grid | Task 8 |
| Belief Convergence mini bars | Task 9 |
| Store: alertHistory, positionHistory, segmentBeliefHistory | Task 2 |
| Store: repairLog, addRepairLog, clearRepairLog, applyCorrection, resetAll | Task 2 |
| NavBar: Analytics link + Maintenance rename | Task 4 |
| `/analytics` + `/maintenance` routes, remove `/work-orders` | Task 4 |
| Maintenance action bar with stats + Reset All | Task 12 |
| WorkOrderList with repairLog entry on complete | Task 10 |
| SegmentOverridePanel H/D/X buttons + POST /correction | Task 11 |
| RepairHistoryLog REPAIRED/OVERRIDE badges | Task 12 |
| Dashboard color scheme throughout | All component tasks (palette values hardcoded per spec) |

**No placeholders found.** All code blocks are complete. All type names are consistent across tasks (`RepairLogEntry`, `alertLevel`, `getAlertRuns`, `getVSafeHistory`, `V_SAFE_MULT`).
