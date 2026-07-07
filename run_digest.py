"""
Manually run the daily eventio_messages digest — for testing, or an
on-demand resend. Does the same thing the daily scheduler does.

Usage:
    python run_digest.py            # normal run (skipped if already sent today)
    python run_digest.py --force    # bypass the once-a-day claim lock
    python run_digest.py --hours 48 # look back further than 24h
"""

import argparse
import logging

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

from utils.digest import run_daily_digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="bypass the once-a-day claim lock")
    parser.add_argument("--hours", type=int, default=24, help="how many hours back to look")
    args = parser.parse_args()

    summary = run_daily_digest(hours=args.hours, force=args.force)
    print(summary)

    if not summary["sent"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
