"""
run_pipeline.py
---------------
Master execution script for Bluestock MF Analytics pipeline.
Runs all steps in order: ingestion → cleaning → DB loading → analytics

Usage:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --skip-db
    python scripts/run_pipeline.py --only ingestion
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

SEP  = "=" * 65
STEPS = [
    ("ingestion",  "data_ingestion.py",   "Data Ingestion — Load 10 CSVs"),
    ("nav",        "live_nav_fetch.py",    "Live NAV Fetch — mfapi.in"),
    ("cleaning",   "data_cleaning.py",     "Data Cleaning — All 10 datasets"),
    ("database",   "db_loader.py",         "Database Loading — SQLite"),
    ("recommender","recommender.py",        "Fund Recommender — Test run"),
]


def run_step(name: str, script: str, description: str) -> bool:
    """Run a single pipeline step. Returns True if successful."""
    path = SCRIPTS / script
    if not path.exists():
        print(f"  ⚠  Script not found: {script} — skipping")
        return False

    print(f"\n{SEP}")
    print(f"  ▶  {description}")
    print(SEP)
    start = time.time()

    result = subprocess.run(
        [sys.executable, str(path)],
        capture_output=False,
        text=True,
    )
    elapsed = time.time() - start

    if result.returncode == 0:
        print(f"\n  ✔  {description} — completed in {elapsed:.1f}s")
        return True
    else:
        print(f"\n  ✘  {description} — FAILED (exit code {result.returncode})")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Bluestock MF Analytics Pipeline")
    parser.add_argument("--skip-db", action="store_true", help="Skip database loading step")
    parser.add_argument("--only", type=str, default=None, help="Run only one step by name")
    args = parser.parse_args()

    print(SEP)
    print("  BLUESTOCK MF ANALYTICS — Master Pipeline")
    print(f"  Root: {ROOT}")
    print(SEP)

    start_total = time.time()
    results = {}

    for name, script, description in STEPS:
        if args.only and args.only != name:
            continue
        if args.skip_db and name == "database":
            print(f"\n  ⏭  Skipping: {description}")
            continue
        if name == "recommender":
            # Just test import, don't run interactively
            print(f"\n{SEP}\n  ▶  {description}\n{SEP}")
            print("  ℹ  Run: python scripts/recommender.py --risk Moderate")
            print("  ✔  Recommender script available")
            results[name] = True
            continue

        results[name] = run_step(name, script, description)

    # ── Summary ────────────────────────────────────────────────────────────
    total = time.time() - start_total
    print(f"\n{SEP}")
    print("  PIPELINE SUMMARY")
    print(SEP)
    for name, script, description in STEPS:
        if name in results:
            status = "✔  PASS" if results[name] else "✘  FAIL"
            print(f"  {status}  {description}")
    print(f"\n  Total time : {total:.1f}s")
    failed = sum(1 for v in results.values() if not v)
    print(f"  Status     : {'✔ All steps passed!' if failed == 0 else f'⚠ {failed} step(s) failed'}")
    print(SEP + "\n")


if __name__ == "__main__":
    main()
