/* ============================================================
   INTERACTIVE SQL WORKBENCH MODULE
   ============================================================ */

let currentSqlResults = null;

const SQL_PRESETS = {
  mom: `SELECT 
    STRFTIME('%Y-%m', transaction_date) AS sales_month,
    COUNT(DISTINCT transaction_id) AS total_orders,
    SUM(quantity) AS total_units_sold,
    ROUND(SUM(gross_amount), 2) AS gross_revenue,
    ROUND(SUM(net_profit), 2) AS net_profit,
    ROUND(SUM(net_profit) / SUM(gross_amount) * 100, 2) AS overall_margin_pct
FROM fact_sales
GROUP BY sales_month
ORDER BY sales_month ASC;`,

  rfm: `SELECT 
    rfm_segment,
    COUNT(customer_id) AS customer_count,
    ROUND(AVG(total_spend), 2) AS avg_lifetime_spend,
    ROUND(SUM(total_spend), 2) AS segment_total_spend,
    ROUND(AVG(days_since_last_purchase), 1) AS avg_recency_days
FROM dim_customers
GROUP BY rfm_segment
ORDER BY segment_total_spend DESC;`,

  reorder: `SELECT 
    p.category,
    p.product_name,
    s.store_name,
    s.region,
    i.stock_on_hand,
    i.reorder_point,
    (i.reorder_point - i.stock_on_hand) AS deficit_quantity,
    i.inventory_valuation
FROM fact_inventory_snapshot i
JOIN dim_products p ON i.product_id = p.product_id
JOIN dim_stores s ON i.store_id = s.store_id
WHERE i.reorder_status = 'REORDER_NEEDED'
ORDER BY deficit_quantity DESC;`,

  margin: `SELECT 
    p.product_id,
    p.product_name,
    p.category,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.gross_amount), 2) AS total_revenue,
    ROUND(SUM(f.net_profit), 2) AS total_profit,
    p.profit_margin_pct AS catalog_margin_pct
FROM fact_sales f
JOIN dim_products p ON f.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.profit_margin_pct
ORDER BY total_profit DESC
LIMIT 10;`,

  regional: `SELECT 
    st.region,
    st.store_name,
    st.city,
    COUNT(DISTINCT f.transaction_id) AS transaction_count,
    ROUND(SUM(f.gross_amount), 2) AS store_revenue,
    ROUND(SUM(f.net_profit), 2) AS store_profit
FROM fact_sales f
JOIN dim_stores st ON f.store_id = st.store_id
GROUP BY st.region, st.store_name, st.city
ORDER BY store_revenue DESC;`
};

function loadSqlPreset(presetKey) {
  if (SQL_PRESETS[presetKey]) {
    document.getElementById('sql-editor').value = SQL_PRESETS[presetKey];
    executeCurrentSql();
  }
}

async function executeCurrentSql() {
  const editor = document.getElementById('sql-editor');
  if (!editor) return;

  const queryStr = editor.value.trim();
  const headEl = document.getElementById('sql-result-head');
  const bodyEl = document.getElementById('sql-result-body');
  const countEl = document.getElementById('sql-result-count');

  if (!queryStr) {
    alert("Please enter a SQL query to execute.");
    return;
  }

  if (countEl) countEl.innerText = '(Executing...)';

  try {
    const res = await fetch('/api/sql/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: queryStr })
    });
    const result = await res.json();

    if (result.status === 'SUCCESS') {
      currentSqlResults = result.data;
      if (countEl) countEl.innerText = `(${result.row_count} rows returned)`;

      if (result.columns && result.columns.length > 0) {
        if (headEl) headEl.innerHTML = `<tr>${result.columns.map(c => `<th>${c}</th>`).join('')}</tr>`;
        
        if (result.data && result.data.length > 0) {
          if (bodyEl) {
            bodyEl.innerHTML = result.data.map(row => 
              `<tr>${result.columns.map(c => `<td style="font-family: var(--font-mono);">${row[c] !== null ? row[c] : '<i style="color: var(--text-dim);">NULL</i>'}</td>`).join('')}</tr>`
            ).join('');
          }
        } else {
          if (bodyEl) bodyEl.innerHTML = `<tr><td colspan="${result.columns.length}" style="text-align: center; color: var(--text-muted);">Query executed cleanly. 0 rows returned.</td></tr>`;
        }
      } else {
        if (headEl) headEl.innerHTML = '<tr><th>Result</th></tr>';
        if (bodyEl) bodyEl.innerHTML = `<tr><td>Command executed successfully. Affected rows: ${result.data[0]?.affected_rows || 0}</td></tr>`;
      }
    } else {
      if (countEl) countEl.innerText = '(Execution Error)';
      if (headEl) headEl.innerHTML = '<tr><th style="color: var(--accent-pink);">SQL Error</th></tr>';
      if (bodyEl) bodyEl.innerHTML = `<tr><td style="color: var(--accent-pink); font-family: var(--font-mono);">${result.message}</td></tr>`;
    }
  } catch (err) {
    if (countEl) countEl.innerText = '(Network Error)';
    if (headEl) headEl.innerHTML = '<tr><th style="color: var(--accent-pink);">Fetch Error</th></tr>';
    if (bodyEl) bodyEl.innerHTML = `<tr><td style="color: var(--accent-pink);">${err.message}</td></tr>`;
  }
}

function exportSqlResultsCsv() {
  if (!currentSqlResults || currentSqlResults.length === 0) {
    alert("No query results available to export!");
    return;
  }
  const keys = Object.keys(currentSqlResults[0]);
  let csvContent = keys.join(",") + "\n";

  currentSqlResults.forEach(row => {
    let line = keys.map(k => `"${String(row[k] || '').replace(/"/g, '""')}"`).join(",");
    csvContent += line + "\n";
  });

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.setAttribute("download", `sql_query_export_${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
