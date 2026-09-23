# Fashion Trend Bot (MVP)

A local-first Python foundation for collecting fashion signals, mapping varied phrases to shared concepts, recording daily observations in SQLite, and producing an explainable trend report.

## Architecture

```text
Sources (sample or configurable RSS feeds)
            ↓
    Signal records
            ↓
 Extract phrase mentions → source evidence
            ↓
     SQLite observations
            ↓
 Aggregate + score → Markdown report
```

```text
src/fashion_trends/
  sources/       Adapters that return source-neutral signals
  processing/    Phrase cleanup and concept mapping
  database/      SQLite schema and repository operations
  scoring/       Explainable daily aggregation and scoring
  reporting/     Markdown report rendering
  cli.py         Local commands to initialize, collect, and report
```

Semantic embeddings/clustering are future extensions. The included sample source is synthetic and is only there to demonstrate the end-to-end pipeline; it does not claim those trends are occurring. The RSS adapter reads feeds configured in `feeds.toml`; each feed is collected independently so one unavailable feed does not prevent the others from running.

## Quick start

Requires Python 3.11+. No third-party runtime packages are needed.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
fashion-trends init
fashion-trends collect --source sample
fashion-trends report --source sample
```

## Collect RSS feeds

The project uses Python's standard library for RSS/Atom parsing and HTTP requests, so no extra package setup is needed. The default `feeds.toml` contains ELLE Fashion and The Guardian Fashion. Add or remove `[[feeds]]` sections in that file to change the feed list:

```toml
[[feeds]]
name = "elle-fashion"
url = "https://www.elle.com/rss/fashion.xml"

[[feeds]]
name = "guardian-fashion"
url = "https://www.theguardian.com/fashion/rss"
```

Collect RSS items, then generate the report:

```powershell
fashion-trends collect --source rss
fashion-trends report --source rss
```

The adapter keeps each article's cleaned headline, summary/description, publication timestamp, URL, and feed name. RSS collection extracts candidate one-to-three-word phrases from headlines and summaries and records them against the original article as evidence. Reports group identical phrases across distinct articles and feeds. By default, multiword phrases must appear in two articles, while single words must appear in four; use `--min-mentions 1` to inspect one-off candidates. This stage finds repeated wording; semantic clustering to connect related but different phrases is a later replaceable step. If a feed is unavailable or malformed, the collector prints a warning and continues with the remaining feeds. To use another feed list, pass `--feeds path\to\feeds.toml` to the RSS collect command. The synthetic source remains available with `fashion-trends collect --source sample`.

Use `fashion-trends report --source sample` to view synthetic observations or `fashion-trends report --source all` to combine sample and RSS data. RSS dates come from article publication dates, so pass `--date YYYY-MM-DD` to report a specific day.

Without installing the command, run `python -m fashion_trends.cli ...` with `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH = "src"`).

By default, the database is `data/fashion_trends.sqlite3`. Pass `--db path\to\file.sqlite3` before or after any command to use a different location (for example, `fashion-trends --db custom.sqlite3 report` or `fashion-trends report --db custom.sqlite3`). Collection is idempotent for a given source, source item, concept, and observation date, so rerunning a source does not duplicate its observations.

## MVP scoring

The score is a transparent heuristic, not a forecast probability. For each phrase on a given day, it combines distinct feed coverage and article count, with a small confidence adjustment. Keep historical daily observations so a later version can score acceleration against prior days. The report shows the feeds and article counts contributing to each phrase.

## Next increments

1. Add additional approved sources behind the `SignalSource` interface.
2. Add historical windows and momentum/acceleration scoring.
3. Add semantic clustering with a replaceable embedding provider.
4. Add scheduling and report delivery after validating source access and desired cadence.
