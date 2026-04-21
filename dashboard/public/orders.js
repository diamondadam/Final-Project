import { store } from './state.js';

const API = 'http://localhost:8000';
const MATERIALS = ['Steel 3/8"', 'Aluminum 1/2"', 'Aluminum 3/8"'];

async function fetchOrders() {
  try {
    const res = await fetch(`${API}/work-orders`);
    if (!res.ok) return;
    const data = await res.json();
    store.workOrders = data.work_orders || [];
    renderOrders();
  } catch {
    // API unavailable — retain last known list silently
  }
}

function getSegmentBelief(segId) {
  if (!store.latest) return null;
  return store.latest.segments?.find(s => s.id === segId) ?? null;
}

function renderOrders() {
  const list  = document.getElementById('orders-list');
  const badge = document.getElementById('orders-badge');
  const orders = store.workOrders;

  // Backend returns status as uppercase "OPEN" or "COMPLETED"
  const openOrders = orders.filter(o => o.status === 'OPEN');

  // Sort: damaged first, then by live belief confidence (falling back to stored confidence)
  const liveConf = (o) => {
    const seg = getSegmentBelief(o.segment_id);
    return seg ? Math.max(...seg.belief) : (o.confidence ?? 0);
  };
  const sorted = [...openOrders].sort((a, b) => {
    if (a.severity !== b.severity) return a.severity === 'DAMAGED' ? -1 : 1;
    return liveConf(b) - liveConf(a);
  });

  badge.textContent = openOrders.length > 0 ? `${openOrders.length} OPEN` : 'ALL CLEAR';
  badge.className   = openOrders.length > 0 ? 'panel-badge badge-red' : 'panel-badge badge-muted';

  list.innerHTML = '';

  if (openOrders.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'order-item ok';
    empty.style.justifyContent = 'center';
    empty.innerHTML = '<span style="color:#6b7280;font-size:11px;">No open work orders</span>';
    list.appendChild(empty);
    return;
  }

  sorted.forEach((order, idx) => {
    const liveSegData = getSegmentBelief(order.segment_id);
    const confidence  = liveSegData
      ? Math.round(Math.max(...liveSegData.belief) * 100)
      : Math.round((order.confidence ?? 0) * 100);
    const stateClass  = order.severity === 'DAMAGED' ? 'damaged' : 'degraded';
    const rankColor   = order.severity === 'DAMAGED' ? '#FF1A1A' : '#f59e0b';

    const item = document.createElement('div');
    item.className = `order-item ${stateClass}`;
    item.dataset.orderId = order.id;

    item.innerHTML = `
      <span class="order-rank" style="color:${rankColor};">#${idx + 1}</span>
      <div class="order-info">
        <div class="order-name">SEG ${order.segment_id} — ${(order.severity || 'UNKNOWN')[0] + (order.severity || 'UNKNOWN').slice(1).toLowerCase()}</div>
        <div class="order-sub">Confidence ${confidence}% · ID: ${order.id}</div>
      </div>
      <div class="order-actions">
        <select class="mat-select">
          ${MATERIALS.map(m => `<option>${m}</option>`).join('')}
        </select>
        <button class="complete-btn" data-order-id="${order.id}">✓ Mark Complete</button>
      </div>
    `;

    item.querySelector('.complete-btn').addEventListener('click', () => completeOrder(order.id, item));
    list.appendChild(item);
  });
}

async function completeOrder(orderId, itemEl) {
  const btn = itemEl.querySelector('.complete-btn');
  btn.disabled = true;
  btn.textContent = 'Completing…';

  try {
    const res = await fetch(`${API}/work-orders/${orderId}/complete`, { method: 'POST' });
    if (!res.ok) throw new Error('API error');
    await fetchOrders(); // refresh list
  } catch {
    itemEl.classList.add('error');
    btn.disabled = false;
    btn.textContent = '✓ Mark Complete';
    setTimeout(() => itemEl.classList.remove('error'), 800);
  }
}

// Poll every 5s + refresh on each WebSocket tick
fetchOrders();
setInterval(fetchOrders, 5000);
document.addEventListener('twinstate', renderOrders);
