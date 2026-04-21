import { store } from './state.js'; // retained: callers can invoke renderSegments(store.latest) directly on demand

const STATE_COLORS = ['#ADEBB3', '#f59e0b', '#FF1A1A'];
const STATE_NAMES  = ['Healthy', 'Degraded', 'Damaged'];
const TEXT_COLORS  = ['#0d1117', '#0d1117', '#ffffff'];
const ACTIVE_CLASSES = ['active-healthy', 'active-degraded', 'active'];

function renderSegments(state) {
  const list   = document.getElementById('seg-list');
  const badge  = document.getElementById('seg-badge');
  const segs   = state.segments || [];
  const active = state.train_segment;

  // Badge: count damaged segments
  const damagedCount  = segs.filter(s => s.map_state === 2).length;
  const degradedCount = segs.filter(s => s.map_state === 1).length;

  if (damagedCount > 0) {
    badge.textContent = `${damagedCount} DAMAGED`;
    badge.className = 'panel-badge badge-red';
  } else if (degradedCount > 0) {
    badge.textContent = `${degradedCount} DEGRADED`;
    badge.className = 'panel-badge badge-amber';
  } else {
    badge.textContent = 'ALL CLEAR';
    badge.className = 'panel-badge badge-muted';
  }

  // Rows — rebuild DOM on each tick (panel is small, cost is negligible)
  list.innerHTML = '';
  segs.forEach(seg => {
    const isActive  = seg.id === active;
    const mapState  = seg.map_state;          // 0 | 1 | 2
    const pct       = Math.round(Math.max(...seg.belief) * 100);
    const color     = STATE_COLORS[mapState];
    const textColor = TEXT_COLORS[mapState];
    const label     = STATE_NAMES[mapState];

    const row = document.createElement('div');
    row.className = 'seg-row' + (isActive ? ` ${ACTIVE_CLASSES[mapState]}` : '');

    row.innerHTML = `
      <span class="seg-id">${isActive ? `SEG ${seg.id} ▶` : `SEG ${seg.id}`}</span>
      <div class="seg-bar-wrap">
        <div class="seg-bar" style="width:${pct}%;background:${color};">
          <span class="seg-bar-label" style="color:${textColor};">${label}</span>
        </div>
      </div>
      <span class="seg-pct" style="color:${color};">${pct}%</span>
    `;
    list.appendChild(row);
  });
}

document.addEventListener('twinstate', (e) => renderSegments(e.detail));
