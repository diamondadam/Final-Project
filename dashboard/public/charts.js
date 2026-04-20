import { deriveAcceleration, deriveMpcSmoothed } from './state.js';

const MAX_POINTS = 30;

// Build empty label array ["-30s", "-29s", ..., "now"]
function makeLabels() {
  return Array.from({ length: MAX_POINTS }, (_, i) => {
    const s = i - MAX_POINTS; // -30 to -1
    return i === MAX_POINTS - 1 ? 'now' : `${s}s`;
  });
}

const ctx = document.getElementById('telem-chart').getContext('2d');

const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: makeLabels(),
    datasets: [
      {
        label: 'Velocity',
        data: Array(MAX_POINTS).fill(null),
        borderColor: '#87CEEB',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.3,
      },
      {
        label: 'Acceleration',
        data: Array(MAX_POINTS).fill(null),
        borderColor: '#FDFBD4',
        borderWidth: 1.5,
        borderDash: [5, 3],
        pointRadius: 0,
        tension: 0.3,
      },
      {
        label: 'MPC Speed',
        data: Array(MAX_POINTS).fill(null),
        borderColor: '#f59e0b',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.3,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    plugins: { legend: { display: false } },
    scales: {
      x: {
        ticks: { color: '#4b5563', font: { size: 9 }, maxRotation: 0 },
        grid:  { color: '#2d3748', drawBorder: false },
        title: {
          display: true,
          text: 'Time (last 30 ticks · 1 tick = 1s)',
          color: '#6b7280',
          font: { size: 8, style: 'italic' },
        },
      },
      y: {
        min: 0, max: 3.5,
        ticks: { color: '#4b5563', font: { size: 9 }, stepSize: 1 },
        grid:  { color: '#2d3748', drawBorder: false },
        title: {
          display: true,
          text: 'fps',
          color: '#6b7280',
          font: { size: 9 },
        },
      },
    },
  },
});

function updateChart(state) {
  const vel   = state.commanded_speed_fps;
  const accel = deriveAcceleration();
  const mpc   = deriveMpcSmoothed();

  // Shift data arrays: drop oldest, push newest
  const [velData, accelData, mpcData] = chart.data.datasets.map(d => d.data);
  velData.shift();   velData.push(vel);
  accelData.shift(); accelData.push(accel);
  mpcData.shift();   mpcData.push(mpc);

  chart.update('none'); // skip animation for live data

  // Update readout cells
  document.getElementById('rv-velocity').textContent = (vel ?? 0).toFixed(2);
  document.getElementById('rv-accel').textContent    = accel.toFixed(2);
  document.getElementById('rv-mpc').textContent      = mpc.toFixed(2);
}

document.addEventListener('twinstate', (e) => updateChart(e.detail));
