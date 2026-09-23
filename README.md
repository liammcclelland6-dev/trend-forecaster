# Fashion Trend Bot (MVP)

A local-first Python foundation for collecting fashion signals, mapping varied phrases to shared concepts, recording daily observations in SQLite, and producing an explainable trend report.

## Architecture

```text
Sources (sample feed now; adapters later)
            ↓
    Signal records
            ↓
 Normalize phrases → canonical concepts
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

Semantic embeddings/clustering and real source adapters are future extensions. The included sample source is synthetic and is only there to demonstrate the end-to-end pipeline; it does not claim those trends are occurring. Real sources can be added behind the `SignalSource` interface, respecting each service's API terms and access rules.

## Quick start

Requires Python 3.11+. No third-party runtime packages are needed.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
fashion-trends init
fashion-trends collect --source sample
fashion-trends report
```

Without installing the command, run `python -m fashion_trends.cli ...` with `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH = "src"`).

By default, the database is `data/fashion_trends.sqlite3`. Pass `--db path\to\file.sqlite3` before or after any command to use a different location (for example, `fashion-trends --db custom.sqlite3 report` or `fashion-trends report --db custom.sqlite3`). Collection is idempotent for a given source, source item, concept, and observation date, so rerunning a source does not duplicate its observations.

## MVP scoring

The score is a transparent heuristic, not a forecast probability. For each concept on a given day, it combines distinct source coverage and signal count, with a small capped weight for source confidence. Keep historical daily observations so a later version can score acceleration against prior days. The report shows the evidence and source names that contributed to each score.

## Next increments

1. Add one real adapter at a time (for example, an approved trends API or RSS feeds).
2. Add historical windows and momentum/acceleration scoring.
3. Add semantic clustering with a replaceable embedding provider.
4. Add scheduling and report delivery after validating source access and desired cadence.
