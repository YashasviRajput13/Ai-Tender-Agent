"""
scheduler.py — Enhanced background tender intelligence scheduler.

Runs CPPP bulk fetch automatically at a configured interval.
Writes a status.json file for the dashboard to read.
"""
import sys, os, time, json, schedule, threading, subprocess
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

SCHEDULE_INTERVAL_HOURS = int(os.getenv("SCHEDULER_INTERVAL_HOURS", "6"))
PAGES_PER_RUN = int(os.getenv("SCHEDULER_PAGES", "3"))
LOG_FILE    = Path(__file__).parent / "scheduler.log"
STATUS_FILE = Path(__file__).parent / "scheduler_status.json"

KEYWORD_CATEGORIES = [
    "", "Road", "Construction", "Water", "IT", "Software",
    "Supply", "Maintenance", "Electrical", "Civil",
]

_lock = threading.Lock()
_state = {"running": False, "last_run": None, "next_run": None,
          "total_runs": 0, "total_saved": 0, "errors": 0}


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    # Rotate log if > 1MB
    if LOG_FILE.stat().st_size > 1_000_000:
        content = LOG_FILE.read_text(encoding="utf-8")
        lines = content.splitlines()
        LOG_FILE.write_text("\n".join(lines[-500:]) + "\n", encoding="utf-8")


def write_status():
    try:
        STATUS_FILE.write_text(json.dumps({
            **_state,
            "last_run": _state["last_run"].isoformat() if _state["last_run"] else None,
            "next_run": _state["next_run"].isoformat() if _state["next_run"] else None,
        }), encoding="utf-8")
    except Exception:
        pass


def run_fetch_job():
    global _state
    with _lock:
        if _state["running"]:
            log("⏭️  Skipping — previous job still running.")
            return
        _state["running"] = True
    write_status()

    log("=" * 55)
    log(f"🚀 AUTO-SCHEDULER: Run #{_state['total_runs'] + 1}")
    log("=" * 55)

    project_dir = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(project_dir, "cppp_bulk_fetch.py")
    categories = KEYWORD_CATEGORIES[:3]

    for kw in categories:
        label = f"'{kw}'" if kw else "(all)"
        log(f"📋 Fetching {label} — {PAGES_PER_RUN} pages…")
        try:
            result = subprocess.run(
                [sys.executable, script, kw, str(PAGES_PER_RUN)],
                cwd=project_dir, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=300,
            )
            for line in result.stdout.splitlines():
                if "Saved:" in line:
                    log(f"  {line.strip()}")
                    try:
                        n = int(line.split("Saved:")[1].split("|")[0].strip())
                        _state["total_saved"] += n
                    except Exception:
                        pass
            if result.returncode != 0 and result.stderr:
                log(f"  ⚠️ {result.stderr[:200]}")
                _state["errors"] += 1
        except subprocess.TimeoutExpired:
            log(f"  ⏱️  Timeout for {label}")
            _state["errors"] += 1
        except Exception as e:
            log(f"  ❌ Error: {e}")
            _state["errors"] += 1
        time.sleep(2)

    _state["last_run"] = datetime.now()
    _state["total_runs"] += 1
    _state["running"] = False
    log(f"✅ Run #{_state['total_runs']} done. Total saved: {_state['total_saved']}")
    log("=" * 55 + "\n")
    write_status()


def start_scheduler():
    log("🤖 Tender Intelligence Scheduler started.")
    log(f"   Interval : every {SCHEDULE_INTERVAL_HOURS} hours")
    log(f"   Pages    : {PAGES_PER_RUN} per category")
    log("   Press Ctrl+C to stop.\n")

    log("⚡ Running initial fetch on startup…")
    run_fetch_job()

    schedule.every(SCHEDULE_INTERVAL_HOURS).hours.do(run_fetch_job)
    _state["next_run"] = schedule.next_run()
    log(f"⏰ Next run: {_state['next_run'].strftime('%Y-%m-%d %H:%M:%S')}")
    write_status()

    while True:
        schedule.run_pending()
        _state["next_run"] = schedule.next_run()
        write_status()
        time.sleep(30)


if __name__ == "__main__":
    try:
        start_scheduler()
    except KeyboardInterrupt:
        log("🛑 Scheduler stopped by user.")
