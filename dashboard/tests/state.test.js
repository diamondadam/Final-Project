const { test } = require('node:test');
const assert = require('node:assert/strict');

// state.js uses ES module exports — load via dynamic import
let store, pushHistory, deriveAcceleration, deriveMpcSmoothed;

test('setup', async () => {
  const mod = await import('../public/state.js');
  store = mod.store;
  pushHistory = mod.pushHistory;
  deriveAcceleration = mod.deriveAcceleration;
  deriveMpcSmoothed = mod.deriveMpcSmoothed;
});

test('store initialises with empty state', () => {
  assert.equal(store.latest, null);
  assert.deepEqual(store.history, []);
  assert.deepEqual(store.workOrders, []);
});

test('pushHistory caps at 30 entries', () => {
  for (let i = 0; i < 35; i++) {
    pushHistory({ commanded_speed_fps: i, tick: i });
  }
  assert.equal(store.history.length, 30);
  assert.equal(store.history[29].tick, 34); // most recent last
});

test('deriveAcceleration returns 0 when history has fewer than 2 entries', () => {
  store.history = [{ commanded_speed_fps: 1.5 }];
  assert.equal(deriveAcceleration(), 0);
});

test('deriveAcceleration computes delta between last two ticks', () => {
  store.history = [
    { commanded_speed_fps: 1.0 },
    { commanded_speed_fps: 1.6 },
  ];
  // (1.6 - 1.0) / 1.0 tick = 0.6 fps²
  assert.ok(Math.abs(deriveAcceleration() - 0.6) < 0.001);
});

test('deriveAcceleration rounds to 2 decimal places', () => {
  store.history = [
    { commanded_speed_fps: 1.0 },
    { commanded_speed_fps: 1.333 },
  ];
  assert.equal(deriveAcceleration(), 0.33);
});

test('deriveMpcSmoothed returns 0 when history is empty', () => {
  store.history = [];
  assert.equal(deriveMpcSmoothed(), 0);
});

test('deriveMpcSmoothed averages up to 3 recent ticks', () => {
  store.history = [
    { commanded_speed_fps: 1.0 },
    { commanded_speed_fps: 2.0 },
    { commanded_speed_fps: 3.0 },
  ];
  // (1 + 2 + 3) / 3 = 2.0
  assert.equal(deriveMpcSmoothed(), 2.0);
});

test('deriveMpcSmoothed uses only last 3 from longer history', () => {
  store.history = [
    { commanded_speed_fps: 0.5 },
    { commanded_speed_fps: 1.0 },
    { commanded_speed_fps: 2.0 },
    { commanded_speed_fps: 3.0 },
  ];
  // last 3: (1 + 2 + 3) / 3 = 2.0
  assert.equal(deriveMpcSmoothed(), 2.0);
});
