"""
scripts/scheduler.py
Automated Data Pipeline Scheduler for NIDA Social Listening
Runs daily data collection jobs for Pantip, YouTube, and News platforms.
"""
import os
import sys
import time
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_collection_job():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting scheduled NIDA Social Listening collection...")
    platforms = ["pantip", "youtube", "news"]
    for platform in platforms:
        out_file = PROJECT_ROOT / "social_listening" / "data" / f"comments_{platform}.jsonl"
        cmd = f"python social_listening/run_collector.py --platform {platform} --output {out_file}"
        print(f"Executing: {cmd}")
        os.system(cmd)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Scheduled collection complete.")


def main():
    scheduler = BlockingScheduler()
    # Run once at startup
    run_collection_job()

    # Schedule to run every day at midnight (00:00)
    scheduler.add_job(run_collection_job, "cron", hour=0, minute=0)
    print("NIDA Social Listening Scheduler started. Press Ctrl+C to exit.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
