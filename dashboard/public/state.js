// Shared mutable store — imported by all panel modules
export const store = {
  latest: null,       // most recent TwinState from WebSocket
  history: [],        // last 30 TwinStates (oldest → newest)
  workOrders: [],     // cached from GET /work-orders
};

// Append state to history, cap at 30
export function pushHistory(state) {
  store.history.push(state);
  if (store.history.length > 30) store.history.shift();
}

// Compute acceleration fps² from last two history entries (1 tick = 1s)
export function deriveAcceleration() {
  const h = store.history;
  if (h.length < 2) return 0;
  const delta = (h[h.length - 1].commanded_speed_fps - h[h.length - 2].commanded_speed_fps) / 1.0;
  return Math.round(delta * 100) / 100;
}

// 3-tick rolling average of commanded_speed_fps
export function deriveMpcSmoothed() {
  const h = store.history;
  const recent = h.slice(-3);
  if (recent.length === 0) return 0;
  const avg = recent.reduce((s, t) => s + t.commanded_speed_fps, 0) / recent.length;
  return Math.round(avg * 100) / 100;
}
