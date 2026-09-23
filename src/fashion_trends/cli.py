"""Command-line entry point."""

import argparse
from datetime import date

from fashion_trends.database.repository import connect, save_observations
from fashion_trends.models import NormalizedSignal
from fashion_trends.processing.normalize import normalize
from fashion_trends.processing.phrases import extract_phrases
from fashion_trends.reporting.markdown import render_daily
from fashion_trends.scoring.daily import score_window
from fashion_trends.sources.rss import RSSSource
from fashion_trends.sources.sample import SampleSource


def main() -> None:
    parser = argparse.ArgumentParser(prog="fashion-trends")
    parser.add_argument("--db", dest="db_before", help="SQLite database path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_db_option(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--db", dest="db_after", help="SQLite database path")

    init = subparsers.add_parser("init", help="Create the database schema")
    add_db_option(init)
    collect = subparsers.add_parser("collect", help="Collect signals from a source")
    add_db_option(collect)
    collect.add_argument("--source", choices=["sample", "rss"], default="sample")
    collect.add_argument("--feeds", default="feeds.toml", help="TOML feed list for --source rss")
    collect.add_argument("--date", type=date.fromisoformat, default=date.today())
    report = subparsers.add_parser("report", help="Print a daily Markdown report")
    add_db_option(report)
    report.add_argument("--date", type=date.fromisoformat, default=date.today())
    report.add_argument("--source", choices=["rss", "sample", "all"], default="rss")
    report.add_argument("--window-days", type=int, default=7)
    report.add_argument(
        "--min-mentions", type=int,
        help="Minimum distinct articles per phrase (RSS defaults: 2 for phrases, 4 for single words)",
    )
    args = parser.parse_args()
    db_path = args.db_after or args.db_before or "data/fashion_trends.sqlite3"

    with connect(db_path) as connection:
        if args.command == "init":
            print(f"Initialized database at {db_path}")
        elif args.command == "collect":
            source = RSSSource(args.feeds) if args.source == "rss" else SampleSource()
            signals = source.fetch(args.date)
            if args.source == "rss":
                normalized = [
                    NormalizedSignal(mention.signal, mention.phrase, mention.phrase.title())
                    for signal in signals
                    for mention in extract_phrases(signal)
                ]
            else:
                normalized = [item for signal in signals for item in normalize(signal)]
            count = save_observations(connection, normalized)
            print(f"Collected {len(signals)} signals; saved {count} new observations for {args.date}.")
        elif args.command == "report":
            print(render_daily(
                args.date,
                score_window(
                    connection,
                    args.date,
                    args.window_days,
                    args.source,
                    args.min_mentions,
                ),
                args.window_days,
            ))


if __name__ == "__main__":
    main()
