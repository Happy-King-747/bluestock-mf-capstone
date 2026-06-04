-- ============================================================
--  schema.sql
--  Bluestock Mutual Fund Analytics — SQLite Star Schema
--  Day 2 — Verified & Tested
-- ============================================================

PRAGMA foreign_keys = ON;

-- ── dim_date ──────────────────────────────────────────────────────────────
-- Calendar dimension: 2012-01-01 to 2026-12-31 (generated in Python)
CREATE TABLE IF NOT EXISTS dim_date (
    date_id      TEXT    PRIMARY KEY,   -- YYYY-MM-DD
    year         INTEGER NOT NULL,
    month        INTEGER NOT NULL,      -- 1–12
    quarter      INTEGER NOT NULL,      -- 1–4
    month_name   TEXT    NOT NULL,
    day_of_week  TEXT    NOT NULL,
    is_weekend   INTEGER NOT NULL DEFAULT 0  -- 0=weekday, 1=weekend
);

-- ── fact_nav ──────────────────────────────────────────────────────────────
-- Daily NAV per mutual fund scheme
-- Source: 02_nav_history.csv + mfapi.in live feed
CREATE TABLE IF NOT EXISTS fact_nav (
    nav_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code  INTEGER NOT NULL REFERENCES dim_date(date_id),
    date_id    TEXT    NOT NULL REFERENCES dim_date(date_id),
    nav        REAL    NOT NULL CHECK (nav > 0),
    UNIQUE (amfi_code, date_id)
);

-- ── fact_transactions ─────────────────────────────────────────────────────
-- Investor buy / sell / SIP transactions
-- Source: 08_investor_transactions.csv
CREATE TABLE IF NOT EXISTS fact_transactions (
    txn_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id        TEXT    NOT NULL,
    amfi_code          INTEGER NOT NULL,
    date_id            TEXT    NOT NULL REFERENCES dim_date(date_id),
    transaction_type   TEXT    NOT NULL
                           CHECK (transaction_type IN
                           ('SIP','Lumpsum','Redemption','Switch_In','Switch_Out','SWP','STP')),
    amount_inr         REAL    NOT NULL CHECK (amount_inr > 0),
    state              TEXT,
    city               TEXT,
    city_tier          TEXT    CHECK (city_tier IN ('T30','B30')),
    age_group          TEXT,
    gender             TEXT,
    annual_income_lakh REAL,
    payment_mode       TEXT,
    kyc_status         TEXT    CHECK (kyc_status IN
                           ('Verified','Pending','Rejected','Under Review','Unknown')),
    transaction_month  TEXT    -- YYYY-MM derived column for aggregation
);

-- ── fact_performance ──────────────────────────────────────────────────────
-- Risk / return metrics snapshot per scheme
-- Source: 07_scheme_performance.csv
CREATE TABLE IF NOT EXISTS fact_performance (
    perf_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code           INTEGER NOT NULL UNIQUE,
    scheme_name         TEXT,
    fund_house          TEXT,
    category            TEXT,
    plan                TEXT,
    return_1yr_pct      REAL,
    return_3yr_pct      REAL,
    return_5yr_pct      REAL,
    benchmark_3yr_pct   REAL,
    alpha               REAL,
    beta                REAL,
    sharpe_ratio        REAL,
    sortino_ratio       REAL,
    std_dev_ann_pct     REAL,
    max_drawdown_pct    REAL,   -- always <= 0
    aum_crore           INTEGER,
    expense_ratio_pct   REAL,   -- valid range: 0.1 – 2.5
    morningstar_rating  INTEGER CHECK (morningstar_rating BETWEEN 1 AND 5),
    risk_grade          TEXT,
    alpha_vs_benchmark  REAL    -- derived: return_3yr_pct - benchmark_3yr_pct
);

-- ── Indexes ───────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_nav_amfi     ON fact_nav(amfi_code);
CREATE INDEX IF NOT EXISTS idx_nav_date     ON fact_nav(date_id);
CREATE INDEX IF NOT EXISTS idx_txn_date     ON fact_transactions(date_id);
CREATE INDEX IF NOT EXISTS idx_txn_type     ON fact_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_txn_state    ON fact_transactions(state);
CREATE INDEX IF NOT EXISTS idx_perf_aum     ON fact_performance(aum_crore);
CREATE INDEX IF NOT EXISTS idx_perf_sharpe  ON fact_performance(sharpe_ratio);
