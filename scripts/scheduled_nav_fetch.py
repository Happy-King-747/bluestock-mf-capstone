"""
scheduled_nav_fetch.py
----------------------
Bonus B1 — Scheduled ETL: Auto-fetch NAV every weekday at 8 PM
Uses the 'schedule' library to run continuously in background.

Usage:
    pip install schedule
    python scripts/scheduled_nav_fetch.py

To stop: press Ctrl + C
"""

import schedule
import time
import json
import logging
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).resolve().parent.parent
RAW     = ROOT / "data" / "raw"
LOGS    = ROOT / "reports"
RAW.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "nav_fetch_log.txt"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

# ── Schemes to fetch ───────────────────────────────────────────────────────
SCHEMES = {
    125497: "HDFC Top 100 Direct",
    119551: "SBI Bluechip Direct",
    120503: "ICICI Bluechip Direct",
    118632: "Nippon Large Cap Direct",
    119092: "Axis Bluechip Direct",
    120841: "Kotak Bluechip Direct",
}

BASE_URL = "https://api.mfapi.in/mf"


def fetch_nav(code: int, retries: int = 3) -> dict | None:
    """Fetch NAV from mfapi.in with retry logic."""
    url = f"{BASE_URL}/{code}"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log.warning(f"Attempt {attempt}/{retries} failed for {code}: {e}")
            if attempt < retries:
                time.sleep(2)
    return None


def run_nav_fetch() -> None:
    """Main job: fetch latest NAV for all schemes and append to CSV."""
    today = datetime.now()

    # Skip weekends
    if today.weekday() >= 5:
        log.info(f"Weekend ({today.strftime('%A')}) — skipping fetch")
        return

    log.info(f"{'='*50}")
    log.info(f"Starting NAV fetch — {today.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"{'='*50}")

    success = 0
    failed  = 0

    for code, name in SCHEMES.items():
        log.info(f"Fetching: {name} ({code})")
        data = fetch_nav(code)

        if data is None:
            log.error(f"FAILED: {name} ({code})")
            failed += 1
            continue

        # Get only latest NAV record
        records = data.get("data", [])
        if not records:
            log.warning(f"No data returned for {name}")
            failed += 1
            continue

        latest = records[0]  # most recent first
        new_row = pd.DataFrame([{
            "fetch_timestamp": today.strftime("%Y-%m-%d %H:%M:%S"),
            "scheme_code":     code,
            "scheme_name":     data["meta"].get("scheme_name", name),
            "nav_date":        latest.get("date", ""),
            "nav":             float(latest.get("nav", 0)),
        }])

        # Append to daily NAV log
        log_path = RAW / "live_nav_daily_log.csv"
        if log_path.exists():
            new_row.to_csv(log_path, mode="a", header=False, index=False)
        else:
            new_row.to_csv(log_path, index=False)

        log.info(f"  ✔  NAV: ₹{latest.get('nav')} as of {latest.get('date')}")
        success += 1
        time.sleep(0.5)  # be polite to API

    log.info(f"Fetch complete — Success: {success} | Failed: {failed}")
    log.info(f"Log saved → {RAW / 'live_nav_daily_log.csv'}")


def main() -> None:
    log.info("Bluestock MF — Scheduled NAV Fetcher started")
    log.info("Schedule: Every weekday at 20:00 IST")
    log.info("Press Ctrl+C to stop\n")

    # Schedule job every weekday at 8 PM
    schedule.every().monday.at("20:00").do(run_nav_fetch)
    schedule.every().tuesday.at("20:00").do(run_nav_fetch)
    schedule.every().wednesday.at("20:00").do(run_nav_fetch)
    schedule.every().thursday.at("20:00").do(run_nav_fetch)
    schedule.every().friday.at("20:00").do(run_nav_fetch)

    # Also run immediately once on start for testing
    log.info("Running once immediately for testing...")
    run_nav_fetch()

    log.info("\nScheduler running — next run at 20:00 on next weekday")
    log.info("Keep this terminal open to maintain the schedule\n")

    while True:
        schedule.run_pending()
        time.sleep(60)  # check every minute


if __name__ == "__main__":
    main()
