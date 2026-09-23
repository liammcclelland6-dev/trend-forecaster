"""Markdown daily report renderer."""

from datetime import date


def render_daily(observed_on: date, scores: list[dict[str, object]]) -> str:
    lines = [f"# Fashion signal report — {observed_on.isoformat()}", "",
             "> Heuristic evidence ranking; not a forecast probability.", ""]
    if not scores:
        lines.extend(["No observations found for this date.", ""])
        return "\n".join(lines)
    lines.extend(["| Rank | Concept | Score | Sources | Observations |", "|---:|---|---:|---|---:|"])
    for index, item in enumerate(scores, start=1):
        lines.append(
            f"| {index} | {item['canonical_label']} | {item['score']} | "
            f"{item['sources']} | {item['observation_count']} |"
        )
    lines.extend(["", "## Interpretation", "", 
                  "A higher score reflects more observations across more distinct sources, "
                  "with a small confidence adjustment. Compare multiple dates before treating "
                  "a concept as accelerating.", ""])
    return "\n".join(lines)
