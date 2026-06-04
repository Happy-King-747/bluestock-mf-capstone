"""
data_cleaning.py
----------------
Day 2 — Tasks 1, 2, 3
  • Clean nav_history       — dates, forward-fill, dedup, NAV > 0
  • Clean investor_transactions — standardise types, validate amounts, dates
  • Clean scheme_performance — numeric validation, expense_ratio range check
  • Also lightly clean remaining 7 datasets (dates + types)

Usage:
    python scripts/data_cleaning.py
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT      = Path(__file__).resolve().parent.parent
RAW       = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

SEP = "=" * 70

def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

def save(df, name):
    path = PROCESSED / f"{name}_clean.csv"
    df.to_csv(path, index=False)
    print(f"  ✔  Saved → {path.relative_to(ROOT)}  ({len(df):,} rows)")

# ── TASK 1 — nav_history ───────────────────────────────────────────────────
def clean_nav_history():
    section("TASK 1 — Cleaning: 02_nav_history")
    df = pd.read_csv(RAW / "02_nav_history.csv", low_memory=False)
    print(f"  Raw shape       : {df.shape}")

    # Parse date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df["date"].isna().sum()
    print(f"  Unparseable dates removed : {bad_dates}")
    df = df.dropna(subset=["date"])

    # Remove duplicates (same amfi_code + date)
    before = len(df)
    df = df.drop_duplicates(subset=["amfi_code", "date"])
    print(f"  Duplicates removed        : {before - len(df)}")

    # Sort
    df = df.sort_values(["amfi_code", "date"]).reset_index(drop=True)

    # Forward-fill missing NAV for weekends / holidays per fund
    # Reindex each fund to full calendar range, then ffill
    filled_frames = []
    for code, grp in df.groupby("amfi_code"):
        grp = grp.set_index("date")
        full_range = pd.date_range(grp.index.min(), grp.index.max(), freq="D")
        grp = grp.reindex(full_range)
        grp["amfi_code"] = code
        grp["nav"] = grp["nav"].ffill()
        grp.index.name = "date"
        grp = grp.reset_index()
        filled_frames.append(grp)

    df_filled = pd.concat(filled_frames, ignore_index=True)
    print(f"  Rows after forward-fill   : {len(df_filled):,}  (was {len(df):,})")

    # Validate NAV > 0
    invalid_nav = df_filled[df_filled["nav"] <= 0]
    print(f"  NAV <= 0 rows removed     : {len(invalid_nav)}")
    df_filled = df_filled[df_filled["nav"] > 0]

    # Final types
    df_filled["amfi_code"] = df_filled["amfi_code"].astype(int)
    df_filled["nav"]       = df_filled["nav"].round(4)

    print(f"  Final shape               : {df_filled.shape}")
    save(df_filled, "02_nav_history")
    return df_filled


# ── TASK 2 — investor_transactions ────────────────────────────────────────
def clean_investor_transactions():
    section("TASK 2 — Cleaning: 08_investor_transactions")
    df = pd.read_csv(RAW / "08_investor_transactions.csv", low_memory=False)
    print(f"  Raw shape : {df.shape}")

    # Parse date
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    bad = df["transaction_date"].isna().sum()
    print(f"  Bad dates removed         : {bad}")
    df = df.dropna(subset=["transaction_date"])

    # Standardise transaction_type
    type_map = {
        "sip": "SIP", "lumpsum": "Lumpsum", "redemption": "Redemption",
        "switch in": "Switch_In", "switch out": "Switch_Out",
        "switch_in": "Switch_In", "switch_out": "Switch_Out",
        "swp": "SWP", "stp": "STP",
    }
    before_types = df["transaction_type"].unique().tolist()
    df["transaction_type"] = df["transaction_type"].str.strip().str.lower().map(
        lambda x: type_map.get(x, x.title())
    )
    after_types = df["transaction_type"].unique().tolist()
    print(f"  Transaction types before  : {sorted(before_types)}")
    print(f"  Transaction types after   : {sorted(after_types)}")

    # Validate amount > 0
    invalid_amt = (df["amount_inr"] <= 0).sum()
    print(f"  Amount <= 0 rows removed  : {invalid_amt}")
    df = df[df["amount_inr"] > 0]

    # Validate KYC status enum
    valid_kyc = {"Verified", "Pending", "Rejected", "Under Review"}
    df["kyc_status"] = df["kyc_status"].str.strip().str.title()
    unknown_kyc = ~df["kyc_status"].isin(valid_kyc)
    print(f"  Unknown KYC values found  : {unknown_kyc.sum()}")
    df.loc[unknown_kyc, "kyc_status"] = "Unknown"

    # Remove duplicate transactions
    before = len(df)
    df = df.drop_duplicates()
    print(f"  Duplicates removed        : {before - len(df)}")

    print(f"  Final shape               : {df.shape}")
    save(df, "08_investor_transactions")
    return df


# ── TASK 3 — scheme_performance ───────────────────────────────────────────
def clean_scheme_performance():
    section("TASK 3 — Cleaning: 07_scheme_performance")
    df = pd.read_csv(RAW / "07_scheme_performance.csv", low_memory=False)
    print(f"  Raw shape : {df.shape}")

    return_cols = ["return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
                   "benchmark_3yr_pct", "alpha", "beta",
                   "sharpe_ratio", "sortino_ratio", "std_dev_ann_pct", "max_drawdown_pct"]

    # Validate all return columns are numeric
    for col in return_cols:
        if col in df.columns:
            before = df[col].dtype
            df[col] = pd.to_numeric(df[col], errors="coerce")
            nulls = df[col].isna().sum()
            if nulls > 0:
                print(f"  ⚠  {col}: {nulls} non-numeric values coerced to NaN")

    # Expense ratio range check: 0.1% to 2.5%
    if "expense_ratio_pct" in df.columns:
        out_of_range = df[
            (df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5)
        ]
        print(f"  Expense ratio out of range (0.1–2.5%): {len(out_of_range)} rows")
        if len(out_of_range) > 0:
            print(df.loc[out_of_range.index, ["scheme_name", "expense_ratio_pct"]].to_string())

    # max_drawdown_pct should be <= 0 (negative is correct)
    if "max_drawdown_pct" in df.columns:
        positive_dd = df[df["max_drawdown_pct"] > 0]
        print(f"  max_drawdown_pct > 0 (anomaly): {len(positive_dd)} rows — expected negative")

    # Beta should be between 0 and 2 typically
    if "beta" in df.columns:
        odd_beta = df[(df["beta"] < 0) | (df["beta"] > 3)]
        print(f"  Beta out of normal range (0–3): {len(odd_beta)} rows")

    print(f"  Final shape : {df.shape}")
    save(df, "07_scheme_performance")
    return df


# ── LIGHT CLEAN — remaining 7 datasets ────────────────────────────────────
def clean_remaining():
    section("Light Cleaning — Remaining 7 Datasets")

    files = {
        "01_fund_master":         {"date_cols": ["launch_date"]},
        "03_aum_by_fund_house":   {"date_cols": ["date"]},
        "04_monthly_sip_inflows": {"date_cols": ["month"]},
        "05_category_inflows":    {"date_cols": ["month"]},
        "06_industry_folio_count":{"date_cols": ["month"]},
        "09_portfolio_holdings":  {"date_cols": ["portfolio_date"]},
        "10_benchmark_indices":   {"date_cols": ["date"]},
    }

    for fname, cfg in files.items():
        path = RAW / f"{fname}.csv"
        if not path.exists():
            print(f"  ⚠  Not found: {fname}.csv")
            continue
        df = pd.read_csv(path, low_memory=False)
        for col in cfg["date_cols"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        # Fill yoy_growth_pct nulls with 0 for SIP inflows (expected missing)
        if "yoy_growth_pct" in df.columns:
            df["yoy_growth_pct"] = df["yoy_growth_pct"].fillna(0)
        df = df.drop_duplicates()
        save(df, fname)


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(SEP)
    print("  BLUESTOCK MF — Data Cleaning (Day 2)")
    print(SEP)

    nav     = clean_nav_history()
    txn     = clean_investor_transactions()
    perf    = clean_scheme_performance()
    clean_remaining()

    section("CLEANING COMPLETE")
    print(f"  nav_history rows after cleaning  : {len(nav):,}")
    print(f"  transactions rows after cleaning : {len(txn):,}")
    print(f"  scheme_performance rows          : {len(perf):,}")
    print(f"\n  ✔  All cleaned CSVs saved to data/processed/\n")


if __name__ == "__main__":
    main()
