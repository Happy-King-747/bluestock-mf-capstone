# Bluestock Mutual Fund Analytics — Capstone Project

End-to-end data analytics pipeline on Indian mutual fund data covering **40 schemes**, **64,320 NAV records**, and **32,778 investor transactions** (2022–2026).

**Intern:** Revanth A | **Organisation:** Bluestock Fintech MJ28 | **Completed:** June 2026

---

## Project Overview

This project builds a complete analytics platform for Indian mutual funds including:
- ETL pipeline fetching live NAV from AMFI API
- SQLite star schema database with 9 tables
- Exploratory data analysis with 15 charts
- Performance metrics — CAGR, Sharpe, Alpha, Beta, VaR, Drawdown
- Interactive Power BI dashboard (4 pages)
- Streamlit web app (Bonus B2)
- Fund recommender system
- Advanced analytics — cohort analysis, SIP continuity, HHI concentration

---

## Folder Structure

```
bluestock_mf_capstone/
├── data/
│   ├── raw/           ← original CSVs + live NAV fetched from mfapi.in
│   ├── processed/     ← cleaned CSVs + analytical outputs
│   └── db/            ← bluestock_mf.db (SQLite — not committed)
├── notebooks/
│   ├── EDA_Analysis.ipynb
│   ├── Performance_Analytics.ipynb
│   └── Advanced_Analytics.ipynb
├── scripts/
│   ├── run_pipeline.py        ← master execution script
│   ├── data_ingestion.py      ← Day 1: load + validate all CSVs
│   ├── live_nav_fetch.py      ← Day 1: fetch live NAV from mfapi.in
│   ├── data_cleaning.py       ← Day 2: clean all 10 datasets
│   ├── db_loader.py           ← Day 2: load into SQLite
│   └── recommender.py         ← Day 6: fund recommender system
├── sql/
│   ├── schema.sql             ← SQLite star schema (9 tables)
│   └── queries.sql            ← 10 analytical SQL queries
├── dashboard/
│   ├── bluestock_mf_dashboard.pbix   ← Power BI dashboard
│   └── streamlit_dashboard.py        ← Streamlit alternative (Bonus B2)
├── streamlit/
│   └── streamlit_dashboard.py        ← Streamlit app (separate folder)
├── reports/
│   ├── Final_Report.pdf
│   ├── Dashboard.pdf
│   ├── data_quality_day1.txt
│   ├── chart01 to chart15 (EDA charts)
│   └── dashboard_page1 to page4 (Power BI screenshots)
├── slides/
│   └── Bluestock_MF_Presentation.pptx
├── data_dictionary.md
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/Happy-King-747/bluestock-mf-capstone.git
cd bluestock-mf-capstone
```

### 2. Install dependencies
```bash
python -m pip install -r requirements.txt
```

### 3. Place raw CSV files
Copy all 10 provided CSV datasets into `data/raw/`

### 4. Run the full pipeline
```bash
python scripts/run_pipeline.py
```

Or run individual steps:
```bash
python scripts/data_ingestion.py     # Step 1: Load CSVs
python scripts/live_nav_fetch.py     # Step 2: Fetch live NAV
python scripts/data_cleaning.py      # Step 3: Clean all data
python scripts/db_loader.py          # Step 4: Load into SQLite
```

### 5. Open Jupyter notebooks
```bash
jupyter notebook notebooks/
```

### 6. Run Streamlit dashboard
```bash
python -m streamlit run dashboard/streamlit_dashboard.py
```
Opens at: http://localhost:8501

### 7. Open Power BI dashboard
Open `dashboard/bluestock_mf_dashboard.pbix` in Power BI Desktop.

### 8. Fund Recommender
```bash
python scripts/recommender.py --risk Low
python scripts/recommender.py --risk Moderate
python scripts/recommender.py --risk High
```

---

## Dataset Descriptions

| File | Rows | Columns | Description |
|------|------|---------|-------------|
| 01_fund_master.csv | 40 | 15 | Scheme metadata — fund house, category, expense ratio, risk grade |
| 02_nav_history.csv | 46,000 | 3 | Daily NAV for 40 schemes (2022–2026) |
| 03_aum_by_fund_house.csv | 90 | 5 | Monthly AUM by fund house (2022–2024) |
| 04_monthly_sip_inflows.csv | 48 | 6 | Industry SIP inflow statistics |
| 05_category_inflows.csv | 144 | 3 | Net inflows by category and month |
| 06_industry_folio_count.csv | 21 | 6 | Quarterly folio count by type |
| 07_scheme_performance.csv | 40 | 19 | Risk/return metrics — Sharpe, Beta, drawdown |
| 08_investor_transactions.csv | 32,778 | 13 | Individual investor transactions |
| 09_portfolio_holdings.csv | 322 | 8 | Stock-level portfolio holdings |
| 10_benchmark_indices.csv | 8,050 | 3 | Daily Nifty 50, Nifty 100 values |

---

## Key Results

| Metric | Best Fund | Value |
|--------|-----------|-------|
| Highest 3yr CAGR | Axis Midcap Regular | 35.10% |
| Best Sharpe Ratio | Mirae Asset Large Cap | 1.45 |
| Best Composite Score | UTI Mid Cap Regular | 86.86/100 |
| Lowest Expense Ratio | Direct plan funds | 0.55% |
| Highest Daily VaR | Small Cap funds | −2.1% |
| Top SIP State | Punjab | ₹X Cr |

---

## Deliverables

| ID | Deliverable | File | Weight |
|----|-------------|------|--------|
| D1 | ETL pipeline | scripts/data_ingestion.py | 15% |
| D2 | SQLite database | data/db/bluestock_mf.db | 10% |
| D3 | EDA notebook | notebooks/EDA_Analysis.ipynb | 15% |
| D4 | Performance metrics | notebooks/Performance_Analytics.ipynb | 15% |
| D5 | Power BI dashboard | dashboard/bluestock_mf_dashboard.pbix | 20% |
| D6 | Advanced analytics | notebooks/Advanced_Analytics.ipynb | 10% |
| D7 | Final report + slides | reports/Final_Report.pdf + slides/ | 15% |

**Bonus completed:**
- B2 — Streamlit web app ✔
- B4 — Fund recommender system ✔

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Language | Python 3.14 |
| Data | pandas, numpy, scipy |
| Visualisation | matplotlib, seaborn, plotly |
| Database | SQLite, SQLAlchemy |
| Dashboard | Power BI Desktop, Streamlit |
| Version Control | Git, GitHub |
| Notebooks | Jupyter Lab |

---

## Notes

- `*.db` files are excluded from Git — recreate using `python scripts/db_loader.py`
- Live NAV data is fetched fresh each run from `https://api.mfapi.in/mf/`
- All monetary values are in INR Crore unless stated otherwise
- CAGR calculations use 252 trading days per year (not calendar days)
