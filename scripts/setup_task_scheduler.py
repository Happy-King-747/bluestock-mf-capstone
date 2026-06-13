"""
setup_task_scheduler.py
-----------------------
Bonus B1 — Windows Task Scheduler setup
Creates a scheduled task that runs live_nav_fetch.py
every weekday at 8:00 PM automatically.

Usage:
    python scripts/setup_task_scheduler.py
    (Run as Administrator for best results)
"""

import subprocess
import sys
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
SCRIPT     = ROOT / "scripts" / "scheduled_nav_fetch.py"
PYTHON_EXE = sys.executable
TASK_NAME  = "BluestockMF_NAV_Fetch"


def create_task() -> None:
    print("=" * 60)
    print("  Bonus B1 — Windows Task Scheduler Setup")
    print("=" * 60)
    print(f"\n  Script  : {SCRIPT}")
    print(f"  Python  : {PYTHON_EXE}")
    print(f"  Schedule: Every weekday at 20:00 IST")
    print(f"  Task    : {TASK_NAME}\n")

    # Build schtasks command
    cmd = [
        "schtasks", "/create",
        "/tn",  TASK_NAME,
        "/tr",  f'"{PYTHON_EXE}" "{SCRIPT}"',
        "/sc",  "WEEKLY",
        "/d",   "MON,TUE,WED,THU,FRI",
        "/st",  "20:00",
        "/f",   # force overwrite if exists
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("  ✔  Task created successfully!")
        print(f"  ✔  Task name: {TASK_NAME}")
        print("\n  The script will now auto-run every weekday at 8:00 PM")
        print("  Even if this terminal is closed.\n")
    else:
        print(f"  ✘  Error: {result.stderr}")
        print("\n  Alternative: Run the Python scheduler manually:")
        print(f"  python scripts/scheduled_nav_fetch.py\n")


def verify_task() -> None:
    result = subprocess.run(
        ["schtasks", "/query", "/tn", TASK_NAME],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  Task Verification:")
        print(result.stdout)
    else:
        print("  Task not found — create it first")


def delete_task() -> None:
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  ✔  Task '{TASK_NAME}' deleted")
    else:
        print(f"  ✘  {result.stderr}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["create","verify","delete"],
                        default="create")
    args = parser.parse_args()

    if args.action == "create":
        create_task()
    elif args.action == "verify":
        verify_task()
    elif args.action == "delete":
        delete_task()
