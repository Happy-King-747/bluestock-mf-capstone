-- ============================================================
--  queries.sql
--  Bluestock Mutual Fund Analytics — 10 Analytical Queries
--  Day 2 — All queries tested and verified on bluestock_mf.db
-- ============================================================

-- ── Q1: Top 5 Funds by AUM ────────────────────────────────────────────────
-- Business use: identify largest schemes by assets under management
-- Result: Mirae Asset Emerging Bluechip leads with ₹49,046 Cr
SELECT
    scheme_name,
    fund_house,
    category,
    aum_crore,
    RANK() OVER (ORDER BY aum_crore DESC) AS aum_rank
FROM fact_performance
ORDER BY aum_crore DESC
LIMIT 5;


-- ── Q2: Average NAV per Month (any scheme) ───────────────────────────────
-- Business use: track monthly price trend — replace amfi_code as needed
-- Result: SBI Bluechip monthly avg NAV across 2022
SELECT
    d.year,
    d.month,
    d.month_name,
    ROUND(AVG(n.nav), 4)  AS avg_nav,
    ROUND(MIN(n.nav), 4)  AS min_nav,
    ROUND(MAX(n.nav), 4)  AS max_nav
FROM fact_nav n
JOIN dim_date d ON d.date_id = n.date_id
WHERE n.amfi_code = 119551        -- change to any amfi_code
  AND d.is_weekend = 0
GROUP BY d.year, d.month
ORDER BY d.year, d.month;


-- ── Q3: SIP Transaction Volume by Month ──────────────────────────────────
-- Business use: identify seasonal SIP patterns and monthly volume trends
SELECT
    d.year,
    d.month_name,
    COUNT(*)                           AS sip_count,
    ROUND(SUM(t.amount_inr) / 1e7, 2) AS total_sip_crore,
    ROUND(AVG(t.amount_inr), 0)        AS avg_sip_inr
FROM fact_transactions t
JOIN dim_date d ON d.date_id = t.date_id
WHERE t.transaction_type = 'SIP'
GROUP BY d.year, d.month
ORDER BY d.year, d.month;


-- ── Q4: Transaction Volume by State ──────────────────────────────────────
-- Business use: geographic distribution of investor activity
-- Result: Punjab, MP, Tamil Nadu are top 3 states
SELECT
    state,
    COUNT(*)                            AS total_txns,
    ROUND(SUM(amount_inr) / 1e7, 2)    AS total_crore,
    COUNT(DISTINCT investor_id)         AS unique_investors
FROM fact_transactions
GROUP BY state
ORDER BY total_txns DESC;


-- ── Q5: Funds with Expense Ratio Below 1% (Low-Cost Funds) ───────────────
-- Business use: filter cost-efficient Direct plans for portfolio selection
-- Result: 14 funds including SBI Direct, Nippon Direct, HDFC Top 100 Direct
SELECT
    scheme_name,
    fund_house,
    category,
    plan,
    expense_ratio_pct,
    return_3yr_pct,
    sharpe_ratio
FROM fact_performance
WHERE expense_ratio_pct < 1.0
ORDER BY expense_ratio_pct ASC;


-- ── Q6: Best Alpha Generators (3yr Return vs Benchmark) ──────────────────
-- Business use: find funds that consistently beat their benchmark
-- Result: HDFC Short Term and Kotak Emerging top the alpha table
SELECT
    scheme_name,
    fund_house,
    category,
    return_3yr_pct,
    benchmark_3yr_pct,
    ROUND(return_3yr_pct - benchmark_3yr_pct, 2) AS alpha_over_bench,
    sharpe_ratio,
    morningstar_rating
FROM fact_performance
WHERE return_3yr_pct IS NOT NULL
ORDER BY alpha_over_bench DESC
LIMIT 10;


-- ── Q7: Risk-Adjusted Return Leaderboard (Sharpe Ratio) ──────────────────
-- Business use: rank equity funds by return per unit of risk taken
-- Excludes liquid funds (Sharpe > 5) to keep equity-only comparison
SELECT
    scheme_name,
    fund_house,
    category,
    risk_grade,
    ROUND(sharpe_ratio, 3)    AS sharpe,
    ROUND(beta, 3)            AS beta,
    ROUND(std_dev_ann_pct, 2) AS volatility_pct,
    return_5yr_pct,
    morningstar_rating
FROM fact_performance
WHERE sharpe_ratio IS NOT NULL
  AND sharpe_ratio <= 5        -- exclude liquid funds
ORDER BY sharpe_ratio DESC
LIMIT 10;


-- ── Q8: Transaction Split by Type and Gender ─────────────────────────────
-- Business use: understand gender-based investment preferences
-- Result: Males invest ~2x more in Lumpsum; SIP is popular across genders
SELECT
    transaction_type,
    gender,
    COUNT(*)                            AS txn_count,
    ROUND(SUM(amount_inr) / 1e7, 2)    AS total_crore,
    ROUND(AVG(amount_inr), 0)           AS avg_amount
FROM fact_transactions
GROUP BY transaction_type, gender
ORDER BY transaction_type, txn_count DESC;


-- ── Q9: Age Group Investment Behaviour ───────────────────────────────────
-- Business use: identify which age groups prefer SIP vs Lumpsum
-- Result: 26-35 age group drives the highest SIP volume (8,063 transactions)
SELECT
    age_group,
    transaction_type,
    COUNT(*)                            AS txn_count,
    ROUND(SUM(amount_inr) / 1e7, 2)    AS total_crore,
    ROUND(AVG(amount_inr), 0)           AS avg_amount_inr
FROM fact_transactions
GROUP BY age_group, transaction_type
ORDER BY age_group, txn_count DESC;


-- ── Q10: City Tier vs KYC Compliance ─────────────────────────────────────
-- Business use: assess KYC completion rates across T30 vs B30 cities
-- Result: Both tiers show 92% verified, 8% pending — uniform compliance
SELECT
    city_tier,
    kyc_status,
    COUNT(*)                                                        AS count,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER (PARTITION BY city_tier), 1)          AS pct_of_tier
FROM fact_transactions
GROUP BY city_tier, kyc_status
ORDER BY city_tier, count DESC;
