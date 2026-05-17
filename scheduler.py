"""
scheduler.py — Background automated tender intelligence scheduler.

Runs CPPP bulk fetch automatically at a configured interval.
Supports multiple keyword categories so you capture all relevant tenders.

Run:  uv run python scheduler.py
"""
import sys
import os
import time
import schedule
import threading
import subprocess
from datetime import datetime
from pathlib import Path

# Fix Windows cp1252 encoding — must be before any print/log
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────
SCHEDULE_INTERVAL_HOURS = 6      # Run every 6 hours
PAGES_PER_RUN = 3                # Pages to scrape each run (≈30 tenders)
LOG_FILE = Path(__file__).parent / "scheduler.log"

# Keyword categories to scrape — customize to match your business
KEYWORD_CATEGORIES = [
    "",              # All tenders (no filter) — first pass
    "Road",
    "Construction",
    "Water",
    "IT",
    "Software",
    "Supply",
    "Maintenance",
    "Electrical",
    "Civil",
]

# ── Scheduler State ──────────────────────────────────────────────────────────
_lock = threading.Lock()
_running = False
_last_run = None
_next_run = None
_total_runs = 0
_total_saved = 0


def log(message: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_fetch_job():
    """Core job: runs cppp_bulk_fetch for each keyword category."""
    global _running, _last_run, _total_runs, _total_saved

    with _lock:
        if _running:
            log("⏭️  Skipping — previous job still running.")
            return
        _running = True

    log("="*55)
    log(f"🚀 AUTO-SCHEDULER: Starting tender fetch run #{_total_runs + 1}")
    log("="*55)

    project_dir = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(project_dir, "cppp_bulk_fetch.py")

    categories_to_run = KEYWORD_CATEGORIES[:3]  # Limit to first 3 per run to avoid rate limits

    for keyword in categories_to_run:
        label = f"'{keyword}'" if keyword else "(all)"
        log(f"\n📋 Fetching category: {label} — {PAGES_PER_RUN} pages...")

        try:
            result = subprocess.run(
                ["uv", "run", "python", script, keyword, str(PAGES_PER_RUN)],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per category
            )
            # Extract saved count from output
            for line in result.stdout.splitlines():
                if "Saved:" in line:
                    log(f"  {line.strip()}")
                    parts = line.split("Saved:")
                    if len(parts) > 1:
                        try:
                            n = int(parts[1].split("|")[0].strip())
                            _total_saved += n
                        except Exception:
                            pass

            if result.returncode != 0 and result.stderr:
                log(f"  ⚠️  Errors: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            log(f"  ⏱️  Timeout for keyword {label}")
        except Exception as e:
            log(f"  ❌ Error: {e}")

        time.sleep(2)  # Brief pause between keyword runs

    _last_run = datetime.now()
    _total_runs += 1
    _running = False

    log(f"\n✅ Run #{_total_runs} complete. Total saved this session: {_total_saved}")
    log("="*55 + "\n")


def start_scheduler():
    global _next_run
    log(f"🤖 Tender Intelligence Scheduler started.")
    log(f"   Interval  : every {SCHEDULE_INTERVAL_HOURS} hours")
    log(f"   Categories: {len(KEYWORD_CATEGORIES)} keyword groups")
    log(f"   Log file  : {LOG_FILE}")
    log(f"   Press Ctrl+C to stop.\n")

    # Run immediately on start
    log("⚡ Running initial fetch on startup...")
    run_fetch_job()

    # Then schedule recurring runs
    schedule.every(SCHEDULE_INTERVAL_HOURS).hours.do(run_fetch_job)
    _next_run = schedule.next_run()

    log(f"\n⏰ Next scheduled run: {_next_run.strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        schedule.run_pending()
        _next_run = schedule.next_run()
        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    try:
        start_scheduler()
    except KeyboardInterrupt:
        log("\n🛑 Scheduler stopped by user.")
