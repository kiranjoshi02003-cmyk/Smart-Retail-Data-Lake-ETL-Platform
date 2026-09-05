# Power BI Dashboard Specification - Smart Retail Platform

## Data Model Architecture (Star Schema)

The Power BI report directly connects to the **Gold Data Mart Layer** in PostgreSQL using DirectQuery or Import Mode.

```
                  +-------------------+
                  |   dim_customers   |
                  +-------------------+
                            | (1)
                            | 
                            | (*)
+------------------+  (*) +-------------------+ (*)  +------------------+
|   dim_products   |----->|    fact_sales     |<-----|    dim_stores    |
+------------------+      +-------------------+      +------------------+
        | (1)                      ^                          | (1)
        |                          |                          |
        | (1)                      | (*)                      | (*)
        +---------------->+-------------------+<--------------+
                          | fact_inventory... |
                          +-------------------+
```

### Relationships & Cardinality
1. `dim_customers[customer_id]` (1) -> `fact_sales[customer_id]` (*)
2. `dim_products[product_id]` (1) -> `fact_sales[product_id]` (*)
3. `dim_stores[store_id]` (1) -> `fact_sales[store_id]` (*)
4. `dim_products[product_id]` (1) -> `fact_inventory_snapshot[product_id]` (*)
5. `dim_stores[store_id]` (1) -> `fact_inventory_snapshot[store_id]` (*)

---

## Report Page Layouts

### Page 1: Executive Sales Overview & Financial Performance
- **KPI Header Cards**:
  - `Total Sales` (with MoM Growth % indicator badge)
  - `Net Profit` & `Profit Margin %`
  - `Average Order Value (AOV)`
  - `Total Transactions`
- **Main Visuals**:
  - **Line & Clustered Column Chart**: Monthly Revenue vs. Net Profit (X-Axis: Date, Y-Axis: Sales & Margin)
  - **Donut Chart**: Revenue by Sales Channel (In-Store, Online, Mobile App)
  - **Bar Chart**: Top 10 Revenue by Category & Product
  - **Map Visual**: Store Sales performance by State & City

### Page 2: Inventory Optimization & Supply Chain Health
- **KPI Header Cards**:
  - `Total Stock On Hand`
  - `Total Inventory Valuation ($)`
  - `Reorder Alert Count` (Filtered to `REORDER_NEEDED`)
  - `Stock Turnover Ratio`
- **Main Visuals**:
  - **Matrix Table**: Products requiring emergency reorder with Deficit Quantity and Store location
  - **Treemap**: Stock Valuation distribution across Categories
  - **Scatter Plot**: Stock On Hand vs. Reorder Point by Product

### Page 3: Customer Behavior & RFM Segmentation
- **KPI Header Cards**:
  - `Active Customer Count`
  - `Avg Customer Lifetime Value (CLV)`
  - `Champions Customer Count`
  - `At Risk Customer Count`
- **Main Visuals**:
  - **Column Chart**: Customer Distribution across RFM Segments (Champions, Loyal, Potential, At Risk)
  - **Scatter Chart**: Recency (Days) vs Monetary Spend (CLV)
  - **Table Grid**: Customer Roster with Contact Email, Loyalty Tier, Total Orders, and Segment Status
