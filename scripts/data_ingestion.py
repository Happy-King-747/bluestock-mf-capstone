"""
data_ingestion.py
-----------------
Day 1 — Task 3: Load all provided CSV datasets, print diagnostics,
and note any anomalies. Results are saved to data/processed/.

Usage:
    python scripts/data_ingestion.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
RAW_DIR     = ROOT / "data" / "raw"
PROCESSED   = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

# ── Helpers ────────────────────────────────────────────────────────────────
SEP = "=" * 70

def section(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")

def analyse_df(name: str, df: pd.DataFrame) -> dict:
    """Print key diagnostics and return an anomaly summary dict."""
    section(f"Dataset: {name}")

    print(f"\n▶ Shape      : {df.shape[0]:,} rows × {df.shape[1]} columns")

    print("\n▶ Data types :")
    print(df.dtypes.to_string())

    print("\n▶ Head (5 rows) :")
    print(df.head().to_string())

    # ── Anomaly checks ────────────────────────────────────────────────────
    anomalies = []

    # Missing values
    null_counts = df.isnull().sum()
    cols_with_nulls = null_counts[null_counts > 0]
    if not cols_with_nulls.empty:
        anomalies.append(f"Nulls found: {cols_with_nulls.to_dict()}")

    # Duplicate rows
    n_dups = df.duplicated().sum()
    if n_dups > 0:
        anomalies.append(f"Duplicate rows: {n_dups}")

    # Object columns that look numeric (common CSV issue)
    for col in df.select_dtypes(include="object").columns:
        sample = df[col].dropna().head(100)
        converted = pd.to_numeric(sample, errors="coerce")
        if converted.notna().mean() > 0.8:
            anomalies.append(f"Column '{col}' looks numeric but stored as object")

    # Negative values in columns that should be positive
    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].lt(0).any():
            anomalies.append(f"Negative values in column '{col}'")

    print("\n▶ Anomalies  :")
    if anomalies:
        for a in anomalies:
            print(f"   ⚠  {a}")
    else:
        print("   ✔  None detected")

    return {"dataset": name, "rows": df.shape[0], "cols": df.shape[1],
            "nulls": int(cols_with_nulls.sum()), "duplicates": int(n_dups),
            "anomalies": "; ".join(anomalies) if anomalies else "None"}


def load_all_csvs() -> dict:
    """Load every CSV found in data/raw/ and return a name→DataFrame dict."""
    csv_files = sorted(RAW_DIR.glob("*.csv"))

    if not csv_files:
        print(f"\n⚠  No CSV files found in {RAW_DIR}")
        print("   Place your 10 datasets there and re-run.\n")
        return {}

    datasets = {}
    for path in csv_files:
        name = path.stem
        try:
            df = pd.read_csv(path, low_memory=False)
            datasets[name] = df
            print(f"✔  Loaded  {name:<40} {df.shape}")
        except Exception as exc:
            print(f"✘  FAILED  {name:<40} {exc}")

    return datasets


def save_quality_report(summaries: list) -> None:
    report_path = PROCESSED / "data_quality_summary.csv"
    pd.DataFrame(summaries).to_csv(report_path, index=False)
    print(f"\n✔  Data quality report saved → {report_path.relative_to(ROOT)}")


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    print(SEP)
    print("  BLUESTOCK MUTUAL FUND — Data Ingestion (Day 1 / Task 3)")
    print(SEP)
    print(f"\n  Raw data directory : {RAW_DIR}")

    datasets = load_all_csvs()

    if not datasets:
        sys.exit(0)

    summaries = []
    for name, df in datasets.items():
        summary = analyse_df(name, df)
        summaries.append(summary)

    # Save cleaned copies with date columns parsed
    for name, df in datasets.items():
        for col in df.columns:
            if col.lower() in ("date", "nav_date", "transaction_date", "as_on_date"):
                try:
                    df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
                except Exception:
                    pass
        out_path = PROCESSED / f"{name}_clean.csv"
        df.to_csv(out_path, index=False)

    save_quality_report(summaries)

    section("SUMMARY")
    print(pd.DataFrame(summaries)[["dataset", "rows", "cols", "nulls",
                                   "duplicates", "anomalies"]].to_string(index=False))
    print("\n✔  Ingestion complete.\n")


if __name__ == "__main__":
    main()
