"""
etl_pipeline.py
---------------
D1 — ETL Pipeline Script (Bluestock MF Analytics)
Runs without manual steps. Handles errors gracefully.

Covers:
  - Load all 10 CSV datasets from data/raw/
  - Print shape, dtypes, head for each
  - Detect anomalies (nulls, duplicates, type issues)
  - Fetch live NAV from mfapi.in for 6 key schemes
  - Validate AMFI codes between fund_master and nav_history
  - Save data quality report to data/processed/

Usage:
    python scripts/etl_pipeline.py
"""

import sys
import json
import time
from pathlib import Path

import pandas as pd
import numpy as np
import requests

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
RAW       = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────
BASE_URL    = "https://api.mfapi.in/mf"
HDFC_CODE   = 125497
KEY_SCHEMES = {
    119551: "SBI Bluechip Fund Direct Growth",
    120503: "ICICI Prudential Bluechip Fund Direct Growth",
    118632: "Nippon India Large Cap Fund Direct Growth",
    119092: "Axis Bluechip Fund Direct Growth",
    120841: "Kotak Bluechip Fund Direct Growth",
}

SEP = "=" * 65


def section(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


# ── Helpers ────────────────────────────────────────────────────────────────
def fetch_nav(code: int, retries: int = 3, delay: float = 2.0) -> dict | None:
    """Fetch NAV from mfapi.in with retry logic."""
    url = f"{BASE_URL}/{code}"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            print(f"   ⚠  Timeout attempt {attempt}/{retries}")
        except requests.exceptions.HTTPError as e:
            print(f"   ✘  HTTP {e.response.status_code}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"   ⚠  Connection error attempt {attempt}/{retries}")
        except json.JSONDecodeError:
            print(f"   ✘  Invalid JSON response")
            return None
        if attempt < retries:
            time.sleep(delay)
    return None


def json_to_df(data: dict, code: int) -> pd.DataFrame:
    """Convert mfapi.in JSON to clean DataFrame."""
    meta = data.get("meta", {})
    df   = pd.DataFrame(data.get("data", []))
    df["scheme_code"]     = code
    df["scheme_name"]     = meta.get("scheme_name", "")
    df["fund_house"]      = meta.get("fund_house", "")
    df["scheme_category"] = meta.get("scheme_category", "")
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df["nav"]  = pd.to_numeric(df["nav"], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def analyse_df(name: str, df: pd.DataFrame) -> dict:
    """Print diagnostics and return anomaly summary."""
    section(f"Dataset: {name}")
    print(f"  Shape      : {df.shape[0]:,} rows × {df.shape[1]} columns")
    print(f"\n  Dtypes:\n{df.dtypes.to_string()}")
    print(f"\n  Head (3 rows):\n{df.head(3).to_string()}")

    anomalies = []
    nulls = df.isnull().sum()
    cols_with_nulls = nulls[nulls > 0]
    if not cols_with_nulls.empty:
        anomalies.append(f"Nulls: {cols_with_nulls.to_dict()}")

    n_dups = df.duplicated().sum()
    if n_dups > 0:
        anomalies.append(f"Duplicate rows: {n_dups}")

    for col in df.select_dtypes(include="object").columns:
        sample    = df[col].dropna().head(100)
        converted = pd.to_numeric(sample, errors="coerce")
        if converted.notna().mean() > 0.8:
            anomalies.append(f"Column '{col}' looks numeric but stored as object")

    print(f"\n  Anomalies: {'; '.join(anomalies) if anomalies else 'None detected ✔'}")
    return {
        "dataset":    name,
        "rows":       df.shape[0],
        "cols":       df.shape[1],
        "nulls":      int(cols_with_nulls.sum()),
        "duplicates": int(n_dups),
        "anomalies":  "; ".join(anomalies) if anomalies else "None",
    }


# ── Step 1: Load CSVs ─────────────────────────────────────────────────────
def load_csvs() -> dict[str, pd.DataFrame]:
    section("STEP 1 — Load all CSV datasets")
    csv_files = sorted(RAW.glob("*.csv"))
    if not csv_files:
        print(f"  ⚠  No CSVs found in {RAW}")
        return {}

    datasets = {}
    for path in csv_files:
        name = path.stem
        try:
            df = pd.read_csv(path, low_memory=False)
            datasets[name] = df
            print(f"  ✔  {name:<45} {df.shape}")
        except Exception as e:
            print(f"  ✘  {name}: {e}")
    return datasets


# ── Step 2: Analyse each dataset ──────────────────────────────────────────
def analyse_all(datasets: dict) -> list[dict]:
    section("STEP 2 — Analyse datasets")
    summaries = []
    core_names = [k for k in datasets if not k.startswith("nav_")]
    for name in core_names[:10]:
        summary = analyse_df(name, datasets[name])
        summaries.append(summary)
    return summaries


# ── Step 3: Fetch live NAV ────────────────────────────────────────────────
def fetch_live_nav() -> None:
    section("STEP 3 — Fetch live NAV from mfapi.in")

    # HDFC Top 100
    print(f"\n  Fetching HDFC Top 100 (code: {HDFC_CODE})")
    data = fetch_nav(HDFC_CODE)
    if data:
        df = json_to_df(data, HDFC_CODE)
        df.to_csv(RAW / f"nav_hdfc_{HDFC_CODE}.csv", index=False)
        print(f"  ✔  {len(df):,} records | Latest NAV: ₹{df['nav'].iloc[-1]:.4f}")

    # 5 key schemes
    all_frames = []
    for code, name in KEY_SCHEMES.items():
        print(f"\n  Fetching {name} ({code})")
        data = fetch_nav(code)
        if data:
            df = json_to_df(data, code)
            df.to_csv(RAW / f"nav_{code}.csv", index=False)
            all_frames.append(df)
            print(f"  ✔  {len(df):,} records | Latest NAV: ₹{df['nav'].iloc[-1]:.4f}")
        time.sleep(0.5)

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        combined.to_csv(RAW / "nav_five_schemes_combined.csv", index=False)
        print(f"\n  ✔  Combined: {len(combined):,} records saved")


# ── Step 4: Validate AMFI codes ───────────────────────────────────────────
def validate_amfi_codes() -> None:
    section("STEP 4 — Validate AMFI codes")
    fm_files  = list(RAW.glob("*fund_master*.csv")) + list(RAW.glob("*master*.csv"))
    nav_files = list(RAW.glob("*nav_history*.csv"))

    if not fm_files or not nav_files:
        print("  ⚠  fund_master or nav_history not found — skipping validation")
        return

    fm  = pd.read_csv(fm_files[0],  low_memory=False)
    nav = pd.read_csv(nav_files[0], low_memory=False)

    fm_col  = next((c for c in fm.columns  if "code" in c.lower()), None)
    nav_col = next((c for c in nav.columns if "code" in c.lower()), None)

    if not fm_col or not nav_col:
        print("  ⚠  Cannot identify scheme_code columns")
        return

    fm_codes  = set(fm[fm_col].dropna().astype(int))
    nav_codes = set(nav[nav_col].dropna().astype(int))
    matched   = fm_codes & nav_codes
    missing   = fm_codes - nav_codes

    print(f"  fund_master codes  : {len(fm_codes):,}")
    print(f"  nav_history codes  : {len(nav_codes):,}")
    print(f"  Matched            : {len(matched):,}")
    print(f"  Missing in nav     : {len(missing):,}")
    print(f"  Status             : {'✔ PASS' if not missing else '⚠ WARN — some codes missing'}")

    report = pd.DataFrame([{
        "check": "AMFI Code Validation",
        "fm_codes": len(fm_codes),
        "nav_codes": len(nav_codes),
        "matched": len(matched),
        "missing": len(missing),
        "status": "PASS" if not missing else "WARN",
    }])
    report.to_csv(PROCESSED / "amfi_validation_report.csv", index=False)


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> None:
    print(SEP)
    print("  BLUESTOCK MF ANALYTICS — ETL Pipeline (D1)")
    print(SEP)

    datasets  = load_csvs()
    summaries = analyse_all(datasets)
    fetch_live_nav()
    validate_amfi_codes()

    # Save quality report
    if summaries:
        pd.DataFrame(summaries).to_csv(PROCESSED / "data_quality_summary.csv", index=False)
        print(f"\n  ✔  Data quality report saved → data/processed/data_quality_summary.csv")

    # Save cleaned copies
    for name, df in datasets.items():
        for col in df.columns:
            if col.lower() in ("date","nav_date","transaction_date","launch_date","month"):
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    pass
        df.to_csv(PROCESSED / f"{name}_clean.csv", index=False)

    section("ETL COMPLETE")
    print(f"  Datasets loaded     : {len(datasets)}")
    print(f"  Quality report saved: data/processed/data_quality_summary.csv")
    print(f"  Live NAV fetched    : 6 schemes\n")


if __name__ == "__main__":
    main()
