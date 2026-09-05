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
  } else if (tabId === 'anomaly') {
    runAnomalyDetection();
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

/* ============================================================
   ML ANOMALY DETECTION CONTROLLER
   ============================================================ */
let currentMlReportData = null;

async function runAnomalyDetection() {
  const datasetSelect = document.getElementById('ml-dataset-select');
  const contaminationEl = document.getElementById('ml-contamination');
  const nEstimatorsEl = document.getElementById('ml-n-estimators');
  const randomStateEl = document.getElementById('ml-random-state');
  const tbody = document.getElementById('ml-table-body');

  if (!datasetSelect) return;

  const payload = {
    dataset_name: datasetSelect.value,
    contamination: parseFloat(contaminationEl ? contaminationEl.value : 0.05),
    n_estimators: parseInt(nEstimatorsEl ? nEstimatorsEl.value : 100),
    random_state: parseInt(randomStateEl ? randomStateEl.value : 42)
  };

  if (tbody) tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--accent-cyan);"><i class="fa-solid fa-spinner fa-spin"></i> Running Preprocessing Pipeline & Isolation Forest Model...</td></tr>';

  try {
    const res = await fetch('/api/ml/anomaly-detect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.status === 'SUCCESS') {
      currentMlReportData = data;
      
      // Update KPIs
      const k = data.kpi_summary;
      document.getElementById('ml-kpi-total').innerText = (k.total_transactions || 0).toLocaleString();
      document.getElementById('ml-kpi-dq-count').innerText = (k.rule_based_dq_issues_count || 0).toLocaleString();
      document.getElementById('ml-kpi-anomalies').innerText = (k.ml_anomalies_count || 0).toLocaleString();
      document.getElementById('ml-kpi-pct').innerText = `${k.anomaly_percentage}%`;
      document.getElementById('ml-kpi-avg-score').innerText = k.average_anomaly_score;

      // Render Charts
      if (data.score_distribution) renderAnomalyDistChart(data.score_distribution);
      if (data.anomalies_by_country) renderAnomalyCountryChart(data.anomalies_by_country);

      // Render Table
      filterMlTable();
    } else {
      if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--accent-pink);">Error: ${data.message}</td></tr>`;
    }
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--accent-pink);">Failed to connect to backend: ${err.message}</td></tr>`;
  }
}

function filterMlTable() {
  if (!currentMlReportData || !currentMlReportData.top_suspicious_transactions) return;

  const searchInput = document.getElementById('ml-search-input');
  const filterSelect = document.getElementById('ml-status-filter');
  const tbody = document.getElementById('ml-table-body');

  const query = (searchInput ? searchInput.value : '').toLowerCase().trim();
  const filterVal = filterSelect ? filterSelect.value : 'ALL';

  let list = currentMlReportData.top_suspicious_transactions;

  if (filterVal !== 'ALL') {
    list = list.filter(item => item.system_status === filterVal);
  }

  if (query) {
    list = list.filter(item => 
      item.invoice_no.toLowerCase().includes(query) ||
      item.customer_id.toLowerCase().includes(query) ||
      item.country.toLowerCase().includes(query) ||
      item.description.toLowerCase().includes(query) ||
      item.stock_code.toLowerCase().includes(query)
    );
  }

  if (list.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted);">No records match filter criteria</td></tr>';
    return;
  }

  tbody.innerHTML = list.map(item => {
    let statusPill = '';
    if (item.system_status === 'DATA QUALITY ISSUE') {
      statusPill = `<span class="status-pill status-dq-issue" title="${item.dq_reason || 'Rule Violation'}"><i class="fa-solid fa-triangle-exclamation"></i> DQ ISSUE</span>`;
    } else if (item.system_status === 'ML-DETECTED ANOMALY') {
      statusPill = `<span class="status-pill status-ml-anomaly"><i class="fa-solid fa-brain"></i> ML ANOMALY</span>`;
    } else {
      statusPill = `<span class="status-pill status-normal">NORMAL</span>`;
    }

    const scoreColor = item.anomaly_score > 0.65 ? 'color: var(--accent-pink); font-weight: 800;' : 
                      item.anomaly_score > 0.45 ? 'color: var(--accent-amber); font-weight: 700;' : 'color: var(--text-muted);';

    return `
      <tr>
        <td style="font-family: var(--font-mono); font-weight: 700;">${item.invoice_no}</td>
        <td style="font-family: var(--font-mono); color: var(--accent-cyan);">$${item.total_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
        <td style="font-family: var(--font-mono);">${item.quantity}</td>
        <td style="font-family: var(--font-mono);">$${item.unit_price.toFixed(2)}</td>
        <td style="font-family: var(--font-mono);">${item.customer_id}</td>
        <td>${item.country}</td>
        <td>${statusPill}</td>
        <td style="font-family: var(--font-mono); ${scoreColor}">${item.anomaly_score.toFixed(4)}</td>
        <td>
          <button class="action-btn-sm" style="padding: 3px 8px; font-size: 10px;" onclick="inspectTransaction(${item.transaction_index})">
            Inspect
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function inspectTransaction(txIdx) {
  if (!currentMlReportData || !currentMlReportData.top_suspicious_transactions) return;
  const item = currentMlReportData.top_suspicious_transactions.find(t => t.transaction_index === txIdx);
  if (!item) return;

  const modal = document.getElementById('transaction-modal');
  const bodyEl = document.getElementById('modal-body-content');

  bodyEl.innerHTML = `
    <div style="margin-bottom: 1rem;">
      <div style="font-size: 11px; color: var(--text-muted);">CLASSIFICATION DIAGNOSIS</div>
      <div style="font-size: 16px; font-weight: 800; color: ${item.system_status.includes('ML') ? 'var(--accent-pink)' : item.system_status.includes('QUALITY') ? 'var(--accent-amber)' : 'var(--accent-green)'};">
        ${item.system_status}
      </div>
      ${item.dq_reason ? `<div style="font-size: 11px; color: var(--accent-amber); margin-top: 4px;"><strong>Rule Violations:</strong> ${item.dq_reason}</div>` : ''}
    </div>

    <div class="detail-grid">
      <div class="detail-item"><label>Invoice No</label><span>${item.invoice_no}</span></div>
      <div class="detail-item"><label>Stock Code</label><span>${item.stock_code}</span></div>
      <div class="detail-item"><label>Description</label><span>${item.description}</span></div>
      <div class="detail-item"><label>Customer ID</label><span>${item.customer_id}</span></div>
      <div class="detail-item"><label>Total Amount</label><span style="color: var(--accent-cyan);">$${item.total_amount.toFixed(2)}</span></div>
      <div class="detail-item"><label>Quantity</label><span>${item.quantity}</span></div>
      <div class="detail-item"><label>Unit Price</label><span>$${item.unit_price.toFixed(2)}</span></div>
      <div class="detail-item"><label>Country</label><span>${item.country}</span></div>
      <div class="detail-item"><label>Isolation Forest Score</label><span style="color: var(--accent-purple);">${item.anomaly_score}</span></div>
      <div class="detail-item"><label>Anomaly Prediction</label><span>${item.anomaly_label}</span></div>
    </div>
  `;

  if (modal) modal.style.display = 'flex';
}

function closeTransactionModal() {
  const modal = document.getElementById('transaction-modal');
  if (modal) modal.style.display = 'none';
}

