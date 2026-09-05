/* ============================================================
   GAMING DASHBOARD CHART.JS ENGINE
   ============================================================ */

let curveChartInstance = null;

function renderTrendChart(monthlyTrends) {
  const ctx = document.getElementById('curveChart').getContext('2d');

  const gradient = ctx.createLinearGradient(0, 0, 0, 140);
  gradient.addColorStop(0, 'rgba(59, 130, 246, 0.4)');
  gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

  const labels = ['1.00x', '2.00x', '3.00x', '4.00x'];
  const points = [1.12, 1.45, 1.85, 2.54];

  if (curveChartInstance) {
    curveChartInstance.destroy();
  }

  curveChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Multiplier',
        data: points,
        borderColor: '#3b82f6',
        backgroundColor: gradient,
        borderWidth: 3,
        fill: true,
        tension: 0.4,
        pointRadius: [0, 0, 0, 5],
        pointBackgroundColor: '#3b82f6',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.03)' },
          ticks: { color: '#5a5d7a', font: { family: 'JetBrains Mono', size: 10 } }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.03)' },
          ticks: {
            color: '#5a5d7a',
            font: { family: 'JetBrains Mono', size: 10 },
            callback: function(val) { return val.toFixed(2) + 'x'; }
          }
        }
      }
    }
  });
}

function updateCurveChart(points) {
  if (curveChartInstance) {
    curveChartInstance.data.datasets[0].data = points;
    curveChartInstance.update();
  }
}
