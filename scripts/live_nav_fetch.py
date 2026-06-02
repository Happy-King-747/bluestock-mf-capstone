"""
live_nav_fetch.py
-----------------
Day 1 — Tasks 4, 5, 6, 7
  • Fetch live NAV from mfapi.in for HDFC Top 100 + 5 key schemes
  • Explore fund master (unique houses, categories, risk grades)
  • Validate AMFI codes between fund_master and nav_history
  • Save raw JSON responses as CSVs in data/raw/

Usage:
    python scripts/live_nav_fetch.py
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
RAW_DIR   = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────
BASE_URL = "https://api.mfapi.in/mf"

# Task 4 — HDFC Top 100 Direct
HDFC_CODE = 125497

# Task 5 — 5 key schemes
KEY_SCHEMES = {
    119551: "SBI Bluechip Fund Direct Growth",
    120503: "ICICI Prudential Bluechip Fund Direct Growth",
    118632: "Nippon India Large Cap Fund Direct Growth",
    119092: "Axis Bluechip Fund Direct Growth",
    120841: "Kotak Bluechip Fund Direct Growth",
}

SEP = "=" * 70


# ── API helper ─────────────────────────────────────────────────────────────
def fetch_nav(scheme_code: int, retries: int = 3, delay: float = 2.0):
    url = f"{BASE_URL}/{scheme_code}"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            print(f"   ⚠  Timeout on attempt {attempt}/{retries} for {scheme_code}")
        except requests.exceptions.HTTPError as exc:
            print(f"   ✘  HTTP {exc.response.status_code} for {scheme_code}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"   ⚠  Connection error on attempt {attempt}/{retries}")
        except json.JSONDecodeError:
            print(f"   ✘  Invalid JSON response for {scheme_code}")
            return None
        if attempt < retries:
            time.sleep(delay)
    print(f"   ✘  All {retries} attempts failed for {scheme_code}")
    return None


def json_to_dataframe(data: dict, scheme_code: int) -> pd.DataFrame:
    meta = data.get("meta", {})
    nav_records = data.get("data", [])
    df = pd.DataFrame(nav_records)
    df["scheme_code"]     = scheme_code
    df["scheme_name"]     = meta.get("scheme_name", "")
    df["fund_house"]      = meta.get("fund_house", "")
    df["scheme_type"]     = meta.get("scheme_type", "")
    df["scheme_category"] = meta.get("scheme_category", "")
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df["nav"]  = pd.to_numeric(df["nav"], errors="coerce")
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def save_raw(df: pd.DataFrame, filename: str) -> Path:
    path = RAW_DIR / filename
    df.to_csv(path, index=False)
    print(f"   ✔  Saved → {path.relative_to(ROOT)}")
    return path


# ── Task 4 ─────────────────────────────────────────────────────────────────
def task4_hdfc_nav():
    print(f"\n{SEP}")
    print(f"  TASK 4 — Fetch HDFC Top 100 Direct NAV (code: {HDFC_CODE})")
    print(SEP)
    data = fetch_nav(HDFC_CODE)
    if data is None:
        print("  ✘  Could not fetch HDFC NAV data.")
        return None
    df = json_to_dataframe(data, HDFC_CODE)
    print(f"\n  Fund      : {df['scheme_name'].iloc[0]}")
    print(f"  Records   : {len(df):,}")
    print(f"  Date range: {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"  Latest NAV: ₹{df['nav'].iloc[-1]:.4f}  (as of {df['date'].iloc[-1].date()})")
    print(f"\n{df.tail().to_string(index=False)}")
    save_raw(df, f"nav_hdfc_top100_{HDFC_CODE}.csv")
    return df


# ── Task 5 ─────────────────────────────────────────────────────────────────
def task5_five_schemes():
    print(f"\n{SEP}")
    print("  TASK 5 — Fetch 5 Key Scheme NAVs")
    print(SEP)
    all_frames = []
    for code, friendly_name in KEY_SCHEMES.items():
        print(f"\n  ▶ {friendly_name} ({code})")
        data = fetch_nav(code)
        if data is None:
            print(f"    ✘  Skipped.")
            continue
        df = json_to_dataframe(data, code)
        print(f"    Records   : {len(df):,}")
        print(f"    Date range: {df['date'].min().date()} → {df['date'].max().date()}")
        print(f"    Latest NAV: ₹{df['nav'].iloc[-1]:.4f}")
        save_raw(df, f"nav_{code}.csv")
        all_frames.append(df)
        time.sleep(0.5)
    if not all_frames:
        return pd.DataFrame()
    combined = pd.concat(all_frames, ignore_index=True)
    save_raw(combined, "nav_five_schemes_combined.csv")
    return combined


# ── Task 6 ─────────────────────────────────────────────────────────────────
def task6_explore_fund_master():
    print(f"\n{SEP}")
    print("  TASK 6 — Explore Fund Master")
    print(SEP)
    fm_candidates = list(RAW_DIR.glob("*fund_master*.csv")) + \
                    list(RAW_DIR.glob("*fund*master*.csv")) + \
                    list(RAW_DIR.glob("*master*.csv"))
    if not fm_candidates:
        print("\n  ⚠  fund_master CSV not found in data/raw/.")
        print("     Place the file there and re-run.\n")
        print("  ℹ  AMFI Scheme Code Structure:")
        print("     • Each mutual fund scheme has a unique numeric AMFI code")
        print("     • Direct plans & Regular plans have DIFFERENT codes")
        print("     • Growth & IDCW options also get separate codes")
        return
    fm_path = fm_candidates[0]
    print(f"\n  Loading: {fm_path.name}")
    fm = pd.read_csv(fm_path, low_memory=False)
    print(f"  Shape  : {fm.shape}")
    col_map = {}
    for col in fm.columns:
        cl = col.lower().replace(" ", "_")
        if "fund_house" in cl or "amc" in cl:
            col_map["fund_house"] = col
        elif "categ" in cl and "sub" not in cl:
            col_map["category"] = col
        elif "sub" in cl and "categ" in cl:
            col_map["sub_category"] = col
        elif "risk" in cl:
            col_map["risk"] = col
        elif "scheme_code" in cl or "amfi" in cl:
            col_map["scheme_code"] = col

    def show_unique(label, col_key):
        if col_key not in col_map:
            print(f"\n  ⚠  No column found for '{label}'")
            return
        col = col_map[col_key]
        vals = fm[col].dropna().unique()
        print(f"\n  ▶ Unique {label} ({len(vals)}):")
        for v in sorted(vals):
            print(f"     • {v}")

    show_unique("Fund Houses",    "fund_house")
    show_unique("Categories",     "category")
    show_unique("Sub-Categories", "sub_category")
    show_unique("Risk Grades",    "risk")


# ── Task 7 ─────────────────────────────────────────────────────────────────
def task7_validate_amfi_codes():
    print(f"\n{SEP}")
    print("  TASK 7 — Validate AMFI Codes (fund_master ↔ nav_history)")
    print(SEP)
    fm_candidates  = list(RAW_DIR.glob("*fund_master*.csv")) + \
                     list(RAW_DIR.glob("*master*.csv"))
    nav_candidates = list(RAW_DIR.glob("*nav_history*.csv")) + \
                     list(RAW_DIR.glob("*nav*.csv"))
    nav_candidates = [p for p in nav_candidates
                      if not any(str(c) in p.name for c in
                                 [HDFC_CODE] + list(KEY_SCHEMES.keys()))]
    if not fm_candidates or not nav_candidates:
        print("\n  ⚠  fund_master or nav_history CSV not found.")
        print("     Place both files in data/raw/ and re-run.")
        return
    fm  = pd.read_csv(fm_candidates[0],  low_memory=False)
    nav = pd.read_csv(nav_candidates[0], low_memory=False)
    fm_code_col  = next((c for c in fm.columns
                         if "code" in c.lower() or "amfi" in c.lower()), None)
    nav_code_col = next((c for c in nav.columns
                         if "code" in c.lower() or "amfi" in c.lower()), None)
    if not fm_code_col or not nav_code_col:
        print("  ⚠  Cannot identify scheme_code columns automatically.")
        return
    fm_codes  = set(fm[fm_code_col].dropna().astype(int))
    nav_codes = set(nav[nav_code_col].dropna().astype(int))
    in_fm_not_nav = fm_codes - nav_codes
    matched       = fm_codes & nav_codes
    print(f"\n  fund_master  unique codes : {len(fm_codes):,}")
    print(f"  nav_history  unique codes : {len(nav_codes):,}")
    print(f"  Matched codes            : {len(matched):,}")
    print(f"  In fund_master, NOT nav  : {len(in_fm_not_nav):,}")
    quality_ok = len(in_fm_not_nav) == 0
    report = {
        "check": "AMFI Code Validation",
        "fm_codes": len(fm_codes),
        "nav_codes": len(nav_codes),
        "matched": len(matched),
        "missing_in_nav": len(in_fm_not_nav),
        "status": "PASS ✔" if quality_ok else "WARN ⚠",
    }
    report_path = PROCESSED / "amfi_validation_report.csv"
    pd.DataFrame([report]).to_csv(report_path, index=False)
    print(f"\n  ✔  Validation report saved → {report_path.relative_to(ROOT)}")
    print(f"\n  DATA QUALITY STATUS: {report['status']}")


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    print(SEP)
    print("  BLUESTOCK MF — Live NAV Fetch + Fund Exploration (Day 1)")
    print(SEP)
    task4_hdfc_nav()
    task5_five_schemes()
    task6_explore_fund_master()
    task7_validate_amfi_codes()
    print(f"\n{SEP}")
    print("  ✔  All tasks complete. Check data/raw/ and data/processed/")
    print(SEP + "\n")


if __name__ == "__main__":
    main()
