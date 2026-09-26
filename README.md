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

RSS reports can optionally group related phrases with a local sentence-embedding model. The included sample source is synthetic and is only there to demonstrate the end-to-end pipeline; it does not claim those trends are occurring. The RSS adapter reads feeds configured in `feeds.toml`; each feed is collected independently so one unavailable feed does not prevent the others from running.

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

The adapter keeps each article's cleaned headline, summary/description, publication timestamp, URL, and feed name. RSS collection extracts candidate one-to-three-word phrases from headlines and summaries and records them against the original article as evidence. Standard reports group identical phrases across distinct articles and feeds. By default, multiword phrases must appear in two articles, while single words must appear in four; use `--min-mentions 1` to inspect one-off candidates. If a feed is unavailable or malformed, the collector prints a warning and continues with the remaining feeds. To use another feed list, pass `--feeds path\to\feeds.toml` to the RSS collect command. The synthetic source remains available with `fashion-trends collect --source sample`.

### Optional semantic grouping

Install the optional model package from the project folder:

```powershell
python -m pip install -e ".[semantic]"
```

Then run a semantic report:

```powershell
fashion-trends report --source rss --semantic
```

The first report downloads `sentence-transformers/all-MiniLM-L6-v2` and its model files; an internet connection is required for that initial download. Later runs use the local cache and run inference on the CPU. The report displays a representative phrase and the related phrases grouped with it, so you can inspect what the model connected. Adjust the cosine similarity cutoff with `--similarity-threshold 0.72` (the default is `0.72`); a higher value makes grouping stricter. Every phrase in a group must meet the cutoff with every other phrase, which prevents long chains of weakly related phrases from merging. Semantic grouping is an experimental aid for connecting phrase variations: it does not invent a trend name, identify entities such as people or events, or establish that a trend is growing. Compare the article counts, feeds, and date windows before interpreting a group.

Use `fashion-trends report --source sample` to view synthetic observations or `fashion-trends report --source all` to combine sample and RSS data. RSS dates come from article publication dates. Reports compare a recent window with the preceding window; set `--window-days 1` for a daily comparison or `--date YYYY-MM-DD` to choose the final date. Historical change becomes meaningful after collections have populated both windows.

## Review phrase candidates

`fashion_vocabulary.toml` is an editable starter vocabulary for garments, styles, materials, details, colors, and silhouettes. It only suggests a category during review; a phrase with no vocabulary match is still included. The list is intentionally small and should grow from phrases found in the feeds.

After pulling phrase-extraction updates, recollect RSS items so the database uses the cleaner phrase candidates, then export up to 50 recurring multiword phrase/source pairs:

```powershell
fashion-trends collect --source rss
fashion-trends review-export --source rss --limit 50 --output data/phrase_review.csv
```

The export sample focuses on recurring two- and three-word phrases; one-off and unmatched phrases remain in SQLite and are not discarded. It includes the phrase, suggested category and matched seed terms, source, article count, latest date, title, a summary excerpt, and URL. Fill in `review_category`, `reviewed_name`, `related_terms`, and `review_notes`; mark unfamiliar phrases unsure or generic as appropriate. Add useful new terms and aliases to `fashion_vocabulary.toml`, then rerun the export to see the updated suggestions. Use `--vocabulary path\to\file.toml` to point to another vocabulary file. This review data will help us evaluate extraction and filtering before considering model fine-tuning.

Without installing the command, run `python -m fashion_trends.cli ...` with `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH = "src"`).

By default, the database is `data/fashion_trends.sqlite3`. Pass `--db path\to\file.sqlite3` before or after any command to use a different location (for example, `fashion-trends --db custom.sqlite3 report` or `fashion-trends report --db custom.sqlite3`). Collection is idempotent for a given source, source item, concept, and observation date, so rerunning a source does not duplicate its observations.

## MVP scoring

The score is a transparent heuristic, not a forecast probability. For each phrase on a given day, it combines distinct feed coverage and article count, with a small confidence adjustment. Keep historical daily observations so a later version can score acceleration against prior days. The report shows the feeds and article counts contributing to each phrase.

## Next increments

1. Add additional approved sources behind the `SignalSource` interface.
2. Add historical windows and momentum/acceleration scoring.
3. Use reviewed phrase candidates to improve phrase extraction and distinguish fashion concepts from names, places, and events.
4. Add scheduling and report delivery after validating source access and desired cadence.
