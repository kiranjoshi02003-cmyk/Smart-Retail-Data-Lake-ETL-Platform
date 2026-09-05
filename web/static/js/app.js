/* ============================================================
   SMART RETAIL DATA PLATFORM CONTROLLER & ROUTER
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  await refreshDashboardData();
  await refreshMedallionSummary();
}

function switchTab(tabId) {
  document.querySelectorAll('.nav-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.workspace-panel').forEach(sec => sec.classList.remove('active'));

  const activeBtn = Array.from(document.querySelectorAll('.nav-tab-btn')).find(btn => btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(tabId));
  if (activeBtn) activeBtn.classList.add('active');

  const targetView = document.getElementById(`view-${tabId}`);
  if (targetView) targetView.classList.add('active');

  if (tabId === 'dashboard') {
    refreshDashboardData();
  } else if (tabId === 'medallion') {
    refreshMedallionSummary();
  } else if (tabId === 'inspector') {
    inspectSelectedTable();
  }
}

function selectSpeedChip(element, rateVal, points) {
  document.querySelectorAll('.stat-chip').forEach(c => c.classList.remove('active'));
  element.classList.add('active');
  
  const badge = document.getElementById('live-rate-badge');
  if (badge) badge.innerText = rateVal;
  
  updateCurveChart(points);
}

function analyzeTopStore() {
  switchTab('sql');
  loadSqlPreset('regional');
}

function inspectTopProduct() {
  switchTab('inspector');
  const dropdown = document.getElementById('table-select');
  if (dropdown) {
    dropdown.value = 'dim_products';
    inspectSelectedTable();
  }
}

async function refreshDashboardData() {
  try {
    const res = await fetch('/api/kpis');
    const data = await res.json();

    if (data.status === 'SUCCESS') {
      const f = data.financials;
      const i = data.inventory;

      const rev = (f.total_revenue || 0).toLocaleString('en-US', { minimumFractionDigits: 2 });
      document.getElementById('nav-total-revenue').innerText = `${rev} $`;
      document.getElementById('stat-profit-total').innerText = `$${(f.total_profit / 1000).toFixed(1)}k Profit`;
      document.getElementById('stat-inventory-alerts').innerText = `${i.reorder_alerts || 0} Reorder Alerts`;

      if (data.monthly_trends) renderTrendChart(data.monthly_trends);

      if (data.category_performance) {
        const tbody = document.getElementById('category-performance-body');
        tbody.innerHTML = data.category_performance.map(cat => `
          <tr>
            <td style="font-weight: 600;">${cat.category}</td>
            <td style="font-family: var(--font-mono); color: var(--accent-cyan);">$${cat.revenue.toLocaleString()}</td>
            <td style="font-family: var(--font-mono); color: var(--accent-green);">$${cat.profit.toLocaleString()}</td>
            <td style="font-family: var(--font-mono);">${cat.units.toLocaleString()}</td>
            <td><span style="background: rgba(16, 185, 129, 0.15); color: var(--accent-green); padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700;">ACTIVE</span></td>
          </tr>
        `).join('');
      }
    }
  } catch (err) {
    console.error('Failed to refresh dashboard data:', err);
  }
}

async function refreshMedallionSummary() {
  try {
    const res = await fetch('/api/medallion/summary');
    const data = await res.json();

    if (data.status === 'SUCCESS' && data.summary) {
      const s = data.summary;
      document.getElementById('m-bronze-sales').innerText = (s.bronze_sales || 0).toLocaleString();
      document.getElementById('m-silver-sales').innerText = (s.silver_sales || 0).toLocaleString();
      document.getElementById('m-gold-fact-sales').innerText = (s.gold_fact_sales || 0).toLocaleString();
      document.getElementById('m-gold-dim-cust').innerText = (s.gold_dim_customers || 0).toLocaleString();
    }
  } catch (err) {
    console.error('Failed to load Medallion summary:', err);
  }
}

async function triggerEtl(forceRegen = false) {
  const pill = document.getElementById('etl-status-pill');
  if (pill) pill.innerText = 'STATUS: RUNNING...';

  appendLog('[INFO] Triggering Bronze-Silver-Gold Medallion Pipeline Run...');

  try {
    const res = await fetch('/api/pipeline/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_regenerate: forceRegen })
    });
    const report = await res.json();

    if (report.status === 'SUCCESS') {
      appendLog(`[SUCCESS] Batch ${report.batch_id} finished in ${report.execution_time_seconds}s`);
      appendLog(`[GOLD MART] Revenue: $${report.gold_stage.total_revenue.toLocaleString()}, Profit: $${report.gold_stage.total_profit.toLocaleString()}`);

      if (pill) pill.innerText = 'STATUS: SUCCESS';

      // Update active chip with live execution runtime
      const activeChip = document.querySelector('.stat-chip.active');
      if (activeChip) {
        activeChip.innerText = `${report.execution_time_seconds.toFixed(2)}s`;
      }

      await refreshMedallionSummary();
      await refreshDashboardData();
    } else {
      appendLog(`[ERROR] ETL Failed: ${report.message}`);
      if (pill) pill.innerText = 'STATUS: FAILED';
    }
  } catch (err) {
    appendLog(`[ERROR] Network error: ${err.message}`);
  }
}

function appendLog(msg) {
  const terminal = document.getElementById('terminal-log');
  if (!terminal) return;
  const timestamp = new Date().toLocaleTimeString();
  const entry = document.createElement('div');
  entry.innerText = `[${timestamp}] ${msg}`;
  terminal.appendChild(entry);
  terminal.scrollTop = terminal.scrollHeight;
}

async function inspectSelectedTable() {
  const dropdown = document.getElementById('table-select');
  if (!dropdown) return;
  const tableName = dropdown.value;
  const headEl = document.getElementById('inspector-table-head');
  const bodyEl = document.getElementById('inspector-table-body');

  if (bodyEl) bodyEl.innerHTML = '<tr><td>Loading table...</td></tr>';

  try {
    const res = await fetch(`/api/table/${tableName}?limit=25`);
    const data = await res.json();

    if (data.status === 'SUCCESS' && data.columns && data.columns.length > 0) {
      if (headEl) headEl.innerHTML = `<tr>${data.columns.map(c => `<th>${c}</th>`).join('')}</tr>`;
      if (bodyEl) {
        bodyEl.innerHTML = data.data.map(row => 
          `<tr>${data.columns.map(c => `<td style="font-family: var(--font-mono);">${row[c] !== null ? row[c] : 'NULL'}</td>`).join('')}</tr>`
        ).join('');
      }
    }
  } catch (err) {
    if (bodyEl) bodyEl.innerHTML = '<tr><td>Failed to load table</td></tr>';
  }
}
