"""Command-line entry point."""

import argparse
from datetime import date

from fashion_trends.database.repository import connect, save_observations
from fashion_trends.processing.normalize import normalize
from fashion_trends.reporting.markdown import render_daily
from fashion_trends.scoring.daily import score_day
from fashion_trends.sources.sample import SampleSource


def main() -> None:
    parser = argparse.ArgumentParser(prog="fashion-trends")
    parser.add_argument("--db", default="data/fashion_trends.sqlite3", help="SQLite database path")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Create the database schema")
    collect = subparsers.add_parser("collect", help="Collect signals from a source")
    collect.add_argument("--source", choices=["sample"], default="sample")
    collect.add_argument("--date", type=date.fromisoformat, default=date.today())
    report = subparsers.add_parser("report", help="Print a daily Markdown report")
    report.add_argument("--date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    with connect(args.db) as connection:
        if args.command == "init":
            print(f"Initialized database at {args.db}")
        elif args.command == "collect":
            source = SampleSource()
            signals = source.fetch(args.date)
            normalized = [item for signal in signals for item in normalize(signal)]
            count = save_observations(connection, normalized)
            print(f"Collected {len(signals)} signals; saved {count} new observations for {args.date}.")
        elif args.command == "report":
            print(render_daily(args.date, score_day(connection, args.date)))


if __name__ == "__main__":
    main()
