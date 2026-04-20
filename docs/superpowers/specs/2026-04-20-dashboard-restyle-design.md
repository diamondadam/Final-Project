# Design Spec — Dashboard Restyle (Reference Color Scheme)

**Date:** 2026-04-20  
**Status:** Approved  
**Scope:** NavBar + TrackDashboard + AnalyticsPage + MaintenancePage (all sub-components)

---

## Goal

Apply the legacy reference dashboard's color scheme and panel aesthetic uniformly across all three React pages so they look like one coherent product. Pages remain separate routes under a shared NavBar.

---

## Token System (Option B — CSS vars + Tailwind arbitrary values)

Define all design tokens as CSS custom properties in `frontend/src/index.css`. Components reference them via Tailwind's `[var(--token)]` syntax.

```css
:root {
  --rt-bg:          #111827;
  --rt-surface:     #1f2937;
  --rt-sidebar-bg:  #1a2332;
  --rt-border:      #374151;
  --rt-border-dim:  #2d3748;
  --rt-cream:       #FDFBD4;
  --rt-blue:        #87CEEB;
  --rt-green:       #ADEBB3;
  --rt-amber:       #f59e0b;
  --rt-red:         #FF1A1A;
  --rt-muted:       #6b7280;
  --rt-muted-dim:   #4b5563;
  --rt-text:        #e5e7eb;
}
```

Also update `App`'s root div from `bg-[#0f1117]` to `bg-[var(--rt-bg)]`.

---

## Component-Level Changes

### NavBar

| Property | Before | After |
|---|---|---|
| Background | `bg-[#0f1117]` | `bg-[var(--rt-sidebar-bg)]` |
| Border | `border-white/10` | `border-[var(--rt-border)]` |
| Logo text | `text-white text-sm font-semibold` | `text-[var(--rt-cream)] text-[clamp(9px,1vw,11px)] tracking-[2px] font-bold uppercase` |
| Nav link (inactive) | `text-zinc-400` | `text-[var(--rt-muted)]` |
| Nav link (active/hover) | `bg-white/10 text-white` | `bg-[var(--rt-border-dim)] text-[var(--rt-cream)]` |
| WS dot (connected) | `bg-emerald-500` | `bg-[var(--rt-green)]` |
| WS dot (disconnected) | `bg-zinc-600` | `bg-[var(--rt-red)]` |
| WS label | `text-zinc-500 text-xs` | `text-[var(--rt-muted)] text-[clamp(8px,0.9vw,10px)]` |
| Open WO badge | `bg-red-500` | `bg-[var(--rt-red)]` |

### Shared Panel Card pattern

All cards across Analytics and Maintenance switch from glass to solid:

```
Before: bg-white/[0.03] border border-white/10 rounded-xl p-4
After:  bg-[var(--rt-surface)] border border-[var(--rt-border)] rounded overflow-hidden
```

Panel header (where applicable):
```
border-b border-[var(--rt-border)] px-[11px] py-[7px] flex items-center justify-between
```

Panel title:
```
Before: text-xs font-semibold tracking-widest text-zinc-500 uppercase
After:  text-[clamp(7px,0.9vw,9px)] font-bold tracking-[2px] text-[var(--rt-cream)] uppercase
```

Panel body padding: `px-[11px] py-[8px]`

### State color mapping

| State | Text (before) | Text (after) | Badge bg (after) | Badge border (after) |
|---|---|---|---|---|
| Healthy | `text-emerald-400` | `text-[var(--rt-green)]` | `bg-[#ADEBB322]` | `border-[#ADEBB344]` |
| Degraded | `text-amber-400` | `text-[var(--rt-amber)]` | `bg-[#f59e0b22]` | `border-[#f59e0b44]` |
| Damaged | `text-red-400` | `text-[var(--rt-red)]` | `bg-[#FF1A1A22]` | `border-[#FF1A1A44]` |

### Analytics Components

**SpeedAlertChart / CommandedVsTargetChart**
- Recharts tooltip: `background: '#1f2937'`, `border: '1px solid #374151'`
- Speed line color: `#34d399` → `#87CEEB` (reference blue for velocity)
- v_safe line: stays `#f59e0b` (amber)
- Reference line: `#374151`
- Axis tick fill: `#6b7280`
- Alert band fills: CLEAR `#ADEBB314`, WARNING `#f59e0b14`, DANGER `#FF1A1A14`

**AlertBreakdown**
- Tile backgrounds: CLEAR `bg-[#ADEBB310]`, WARNING `bg-[#f59e0b10]`, DANGER `bg-[#FF1A1A10]`
- Tile text colors: use `--rt-green`, `--rt-amber`, `--rt-red`

**HealthHeatmap**
- Cell colors: Healthy `#ADEBB366`, Degraded `#f59e0b66`, Damaged `#FF1A1A66`
- Empty cell: `#1f2937`
- Segment label: `text-[var(--rt-muted)]`

**BeliefConvergence**
- Bar colors: `#ADEBB3`, `#f59e0b`, `#FF1A1A` (matching updated CLASS_COLORS)
- Labels: `text-[var(--rt-muted)]`

**PositionTimeline**
- Line stroke: `#87CEEB` (reference blue, replaces `#818cf8` indigo)

### Maintenance Components

**WorkOrderList — WorkOrderRow**
- Open DAMAGED row: `bg-[#1f1515] border-[#FF1A1A44]`
- Open DEGRADED row: `bg-[#1f1a0f] border-[#f59e0b44]`
- Completed row: `bg-[var(--rt-surface)] border-[var(--rt-border)] opacity-50`
- Severity badge: use updated state color mapping above
- Complete button: `bg-[#ADEBB322] text-[var(--rt-green)] border border-[#ADEBB355] hover:bg-[#ADEBB344]`
- Refresh button: `text-[var(--rt-muted)] hover:text-[var(--rt-text)]`

**SegmentOverridePanel**
- Card surface: same shared panel pattern
- Override H button: `bg-[#ADEBB322] text-[var(--rt-green)]`
- Override D button: `bg-[#f59e0b22] text-[var(--rt-amber)]`
- Override X button: `bg-[#FF1A1A22] text-[var(--rt-red)]`

**RepairHistoryLog**
- REPAIRED badge: `bg-[#ADEBB322] text-[var(--rt-green)] border-[#ADEBB344]`
- OVERRIDE badge: `bg-[#87CEEB22] text-[var(--rt-blue)] border-[#87CEEB44]` (replaces indigo)
- Row background: `bg-[var(--rt-surface)] border-[var(--rt-border)]`
- Timestamp: `text-[var(--rt-muted)]`

**MaintenancePage — Reset All button**
- `bg-[#FF1A1A22] text-[var(--rt-red)] border border-[#FF1A1A44] hover:bg-[#FF1A1A33]`

---

## Responsive Strategy

### Text sizing — `clamp()` via Tailwind arbitrary values

| Role | Class |
|---|---|
| Panel / section titles | `text-[clamp(7px,0.9vw,9px)]` |
| Body / badge text | `text-[clamp(9px,1.1vw,11px)]` |
| Sub / meta text | `text-[clamp(8px,1vw,10px)]` |
| Large readout numbers | `text-[clamp(14px,2vw,20px)]` |
| Segment IDs (mono) | `text-[clamp(8px,0.9vw,10px)]` |

### Layout — breakpoint grid

Both AnalyticsPage and MaintenancePage use `grid-cols-[1fr_280px]` side-by-side at `lg` and fall back to single-column below:

```
Before: grid grid-cols-[1fr_280px] gap-4
After:  grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4
```

Sidebar panels (AlertBreakdown, PositionTimeline, SegmentOverridePanel) stack below the main chart/list on small screens and move to the right column on large screens.

Chart `height` props: replace fixed `height={160}` with `height="100%"` inside a `min-h-[120px] lg:min-h-[160px]` wrapper div so charts scale with the container.

### Page padding
```
Before: p-6
After:  p-3 sm:p-4 lg:p-6
```

---

## Files to Change

1. `frontend/src/index.css` — add CSS token vars, update body bg
2. `frontend/src/App.tsx` — update root bg class
3. `frontend/src/components/NavBar.tsx`
4. `frontend/src/types.ts` — update `CLASS_COLORS` hex values
5. `frontend/src/pages/AnalyticsPage.tsx`
6. `frontend/src/pages/MaintenancePage.tsx`
7. `frontend/src/components/analytics/SpeedAlertChart.tsx`
8. `frontend/src/components/analytics/AlertBreakdown.tsx`
9. `frontend/src/components/analytics/PositionTimeline.tsx`
10. `frontend/src/components/analytics/CommandedVsTargetChart.tsx`
11. `frontend/src/components/analytics/HealthHeatmap.tsx`
12. `frontend/src/components/analytics/BeliefConvergence.tsx`
13. `frontend/src/components/maintenance/WorkOrderList.tsx`
14. `frontend/src/components/maintenance/SegmentOverridePanel.tsx`
15. `frontend/src/components/maintenance/RepairHistoryLog.tsx`

---

## Non-Goals

- TrackDashboard (home page) component internals — only touched via the shared token vars already set on `body`/root
- Backend changes
- New routes or new components
- Changes to chart data or store logic
