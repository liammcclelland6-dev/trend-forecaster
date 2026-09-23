"""Markdown daily report renderer."""

from datetime import date


def render_daily(
    observed_on: date,
    scores: list[dict[str, object]],
    window_days: int = 7,
) -> str:
    start_date = observed_on.fromordinal(observed_on.toordinal() - window_days + 1)
    lines = [
        f"# Fashion signal report — {start_date.isoformat()} to {observed_on.isoformat()}", "",
        f"> Recent {window_days} days compared with the previous {window_days} days; "
        "heuristic evidence, not a forecast probability.", "",
    ]
    if not scores:
        lines.extend(["No phrases met the minimum mention count for this date range and source selection.", ""])
        return "\n".join(lines)
    lines.extend([
        "| Rank | Phrase | Score | Recent articles | Previous articles | Change | Feeds |",
        "|---:|---|---:|---:|---:|---:|---|",
    ])
    for index, item in enumerate(scores, start=1):
        change_pct = item["change_pct"]
        change = "No prior mentions" if change_pct is None else f"{change_pct:+.1f}%"
        lines.append(
            f"| {index} | {item['canonical_label']} | {item['score']} | "
            f"{item['recent_articles']} | {item['previous_articles']} | {change} | {item['sources']} |"
        )
    lines.extend(["", "## Interpretation", "", 
                  "A higher score reflects recent article count and distinct feed coverage. "
                  "Change compares equal-length publication-date windows and is shown for phrases "
                  "with prior mentions.", ""])
    return "\n".join(lines)
