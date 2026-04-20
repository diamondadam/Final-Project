import { store, pushHistory } from './state.js';

const WS_URL = 'ws://localhost:8000/ws';
const MAX_BACKOFF_MS = 30_000;

let ws = null;
let retryDelay = 1000;
let retryTimer = null;

function setIndicator(status, label) {
  const dot   = document.getElementById('ws-dot');
  const lbl   = document.getElementById('ws-label');
  dot.className = `ws-dot ${status}`;
  lbl.textContent = label;
}

function connect() {
  setIndicator('reconnecting', 'Connecting…');
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    retryDelay = 1000;
    setIndicator('connected', 'Connected');
  };

  ws.onmessage = (event) => {
    let state;
    try { state = JSON.parse(event.data); } catch { return; }
    store.latest = state;
    pushHistory(state);
    document.dispatchEvent(new CustomEvent('twinstate', { detail: state }));
  };

  ws.onclose = () => {
    retryDelay = Math.min(retryDelay * 2, MAX_BACKOFF_MS);
    setIndicator('reconnecting', `Retry in ${Math.round(retryDelay / 1000)}s…`);
    scheduleReconnect();
  };

  ws.onerror = () => { /* onclose fires automatically after onerror */ };
}

function scheduleReconnect() {
  clearTimeout(retryTimer);
  retryTimer = setTimeout(connect, retryDelay);
}

// Export report: download latest TwinState as JSON
document.getElementById('export-btn').addEventListener('click', (e) => {
  e.preventDefault();
  if (!store.latest) return;
  const blob = new Blob([JSON.stringify(store.latest, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), {
    href: url,
    download: `twin-state-tick-${store.latest.tick}.json`,
  });
  a.click();
  URL.revokeObjectURL(url);
});

function updateAlertBanner(state) {
  const banner = document.getElementById('alert-banner');
  const text   = document.getElementById('alert-text');
  const tick   = document.getElementById('alert-tick');

  const alert = (state.alert || '').toUpperCase();
  banner.className = 'alert-banner';

  if (alert.startsWith('DANGER'))  banner.classList.add('state-damaged');
  else if (alert.startsWith('WARNING')) banner.classList.add('state-degraded');
  else banner.classList.add('state-clear');

  text.textContent = state.alert || 'All clear.';
  tick.textContent = `TICK #${state.tick} · ${new Date(state.timestamp).toLocaleTimeString()}`;
}

document.addEventListener('twinstate', (e) => updateAlertBanner(e.detail));

const SEG_STATE_CLASS = ['seg-healthy', 'seg-degraded', 'seg-damaged'];

function updateFeedPanel(state) {
  const segEl  = document.getElementById('coord-seg');
  const latEl  = document.getElementById('coord-lat');
  const longEl = document.getElementById('coord-long');

  // Static CMU Pittsburgh coords — swap for live GPS when available
  latEl.textContent  = '40.4427° N';
  longEl.textContent = '79.9432° W';

  const activeSeg = state.train_segment;
  const segState  = state.segments?.[activeSeg]?.map_state ?? 0;

  segEl.textContent = `SEG ${activeSeg}`;
  segEl.className   = `coord-value ${SEG_STATE_CLASS[segState]}`;
}

document.addEventListener('twinstate', (e) => updateFeedPanel(e.detail));

connect();

// Mark data as stale if no tick received for 10 seconds
let staleTimer = null;

function resetStaleTimer() {
  clearTimeout(staleTimer);
  const banner = document.getElementById('alert-banner');
  banner.classList.remove('alert-stale');
  staleTimer = setTimeout(() => {
    banner.classList.add('alert-stale');
  }, 10_000);
}

document.addEventListener('twinstate', resetStaleTimer);
