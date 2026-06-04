"""
db_loader.py
------------
Day 2 — Tasks 4, 5
  • Build SQLite star schema using SQLAlchemy
  • Load all cleaned datasets into bluestock_mf.db
  • Verify row counts match source CSVs

Usage:
    python scripts/db_loader.py
"""

from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

ROOT      = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
DB_DIR    = ROOT / "data" / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH   = DB_DIR / "bluestock_mf.db"
SCHEMA    = ROOT / "sql" / "schema.sql"

SEP = "=" * 70

def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

def get_engine():
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    return engine

def apply_schema(engine):
    section("Applying Schema")
    sql = SCHEMA.read_text()
    # Execute each statement separately
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                print(f"  ⚠  {e} — {stmt[:60]}")
        conn.commit()
    print("  ✔  Schema applied successfully")


def build_dim_date(engine):
    """Generate a complete dim_date table from 2012 to 2026."""
    section("Building dim_date")
    dates = pd.date_range("2012-01-01", "2026-12-31", freq="D")
    df = pd.DataFrame({
        "date_id":     dates.strftime("%Y-%m-%d"),
        "year":        dates.year,
        "month":       dates.month,
        "quarter":     dates.quarter,
        "month_name":  dates.strftime("%B"),
        "day_of_week": dates.strftime("%A"),
        "is_weekend":  (dates.dayofweek >= 5).astype(int),
    })
    df.to_sql("dim_date", engine, if_exists="replace", index=False)
    print(f"  ✔  dim_date loaded: {len(df):,} rows")


def load_csv(filename, table_name, engine, rename=None, drop_cols=None, date_cols=None):
    """Generic loader: read cleaned CSV → transform → load to SQLite."""
    path = PROCESSED / f"{filename}_clean.csv"
    if not path.exists():
        print(f"  ⚠  File not found: {path.name} — skipping")
        return 0

    df = pd.read_csv(path, low_memory=False)

    if rename:
        df = df.rename(columns=rename)
    if drop_cols:
        df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    if date_cols:
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")

    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"  ✔  {table_name:<30} {len(df):>8,} rows  ← {filename}_clean.csv")
    return len(df)


def load_fact_nav(engine):
    path = PROCESSED / "02_nav_history_clean.csv"
    if not path.exists():
        print("  ⚠  02_nav_history_clean.csv not found — skipping fact_nav")
        return
    df = pd.read_csv(path, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"date": "date_id"})
    df = df[["amfi_code", "date_id", "nav"]].dropna()
    df.to_sql("fact_nav", engine, if_exists="replace", index=False)
    print(f"  ✔  fact_nav                     {len(df):>8,} rows")


def load_fact_transactions(engine):
    path = PROCESSED / "08_investor_transactions_clean.csv"
    if not path.exists():
        print("  ⚠  08_investor_transactions_clean.csv not found")
        return
    df = pd.read_csv(path, low_memory=False)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"transaction_date": "date_id"})
    df.to_sql("fact_transactions", engine, if_exists="replace", index=False)
    print(f"  ✔  fact_transactions            {len(df):>8,} rows")


def load_fact_aum(engine):
    path = PROCESSED / "03_aum_by_fund_house_clean.csv"
    if not path.exists():
        print("  ⚠  03_aum_by_fund_house_clean.csv not found")
        return
    df = pd.read_csv(path, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"date": "date_id"})
    df.to_sql("fact_aum", engine, if_exists="replace", index=False)
    print(f"  ✔  fact_aum                     {len(df):>8,} rows")


def load_fact_sip(engine):
    path = PROCESSED / "04_monthly_sip_inflows_clean.csv"
    if not path.exists():
        print("  ⚠  04_monthly_sip_inflows_clean.csv not found")
        return
    df = pd.read_csv(path, low_memory=False)
    df["month"] = pd.to_datetime(df["month"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"month": "date_id"})
    df.to_sql("fact_sip_inflows", engine, if_exists="replace", index=False)
    print(f"  ✔  fact_sip_inflows             {len(df):>8,} rows")


def load_fact_benchmark(engine):
    path = PROCESSED / "10_benchmark_indices_clean.csv"
    if not path.exists():
        print("  ⚠  10_benchmark_indices_clean.csv not found")
        return
    df = pd.read_csv(path, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"date": "date_id"})
    df.to_sql("fact_benchmark", engine, if_exists="replace", index=False)
    print(f"  ✔  fact_benchmark               {len(df):>8,} rows")


def load_fact_holdings(engine):
    path = PROCESSED / "09_portfolio_holdings_clean.csv"
    if not path.exists():
        print("  ⚠  09_portfolio_holdings_clean.csv not found")
        return
    df = pd.read_csv(path, low_memory=False)
    df["portfolio_date"] = pd.to_datetime(df["portfolio_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"portfolio_date": "date_id"})
    df.to_sql("fact_portfolio_holdings", engine, if_exists="replace", index=False)
    print(f"  ✔  fact_portfolio_holdings      {len(df):>8,} rows")


def verify_counts(engine):
    section("Row Count Verification")
    tables = [
        "dim_fund", "dim_date", "fact_nav", "fact_transactions",
        "fact_performance", "fact_aum", "fact_sip_inflows",
        "fact_benchmark", "fact_portfolio_holdings"
    ]
    with engine.connect() as conn:
        for t in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).fetchone()
                print(f"  {t:<35} {result[0]:>8,} rows")
            except Exception:
                print(f"  {t:<35}  (table not found)")


def run_sample_queries(engine):
    section("Sample Query Results — Q1: Top 5 Funds by AUM")
    q = """
    SELECT f.scheme_name, f.fund_house, p.aum_crore
    FROM fact_performance p
    JOIN dim_fund f ON f.amfi_code = p.amfi_code
    ORDER BY p.aum_crore DESC LIMIT 5
    """
    with engine.connect() as conn:
        try:
            rows = conn.execute(text(q)).fetchall()
            for i, row in enumerate(rows, 1):
                print(f"  {i}. {row[0][:45]:<45} ₹{row[2]:,} Cr")
        except Exception as e:
            print(f"  ⚠  {e}")


def main():
    print(SEP)
    print("  BLUESTOCK MF — DB Loader (Day 2)")
    print(f"  DB path: {DB_PATH}")
    print(SEP)

    engine = get_engine()
    apply_schema(engine)
    build_dim_date(engine)

    section("Loading Dimension Tables")
    load_csv("01_fund_master", "dim_fund", engine,
             date_cols=["launch_date"])

    section("Loading Fact Tables")
    load_fact_nav(engine)
    load_fact_transactions(engine)
    load_csv("07_scheme_performance", "fact_performance", engine)
    load_fact_aum(engine)
    load_fact_sip(engine)
    load_fact_benchmark(engine)
    load_fact_holdings(engine)

    verify_counts(engine)
    run_sample_queries(engine)

    print(f"\n  ✔  Database ready at: {DB_PATH.relative_to(ROOT)}\n")


if __name__ == "__main__":
    main()
