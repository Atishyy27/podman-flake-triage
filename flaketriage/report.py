"""Turn classified failures into something a maintainer would act on.

The useful question is not "what failed today", it is "which of these keeps happening".
So the report leads with recurrence: the same job failing the same way across different
runs is a flake worth quarantining, a one-off is usually just a broken PR.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .classify import CATEGORIES, Verdict


@dataclass
class Row:
    run_id: int
    job_id: int
    job_name: str
    failed_step: str | None
    verdict: Verdict
    created_at: str | None
    html_url: str


def md_cell(text: str, limit: int = 110) -> str:
    """Make arbitrary log text safe inside a markdown table cell.

    Three things break a table: a pipe splits the row into extra columns, a newline
    ends the row early, and a backtick closes the inline code span so the rest of the
    cell renders as prose. Go tooling quotes identifiers in backticks routinely
    (`undefined: `someHelper``), so the third is not hypothetical.
    """
    if not text:
        return ""
    flat = " ".join(text.split())  # collapses newlines and runs of whitespace
    flat = flat.replace("\\", "\\\\").replace("|", "\\|").replace("`", "'")
    return flat[:limit]


def _job_family(job_name: str) -> str:
    """Collapse podman's matrix job names to the part that identifies the test lane.

    'int local rootless fedora-rawhide / lima' -> 'int local rootless'
    Distro and runner vary across the matrix; the lane is what recurs.
    """
    head = job_name.split("/")[0].strip()
    parts = head.split()
    return " ".join(parts[:3]) if len(parts) >= 3 else head


def render(rows: list[Row], sampled_runs: int) -> str:
    if not rows:
        return "# Podman CI flake triage\n\nNo failed jobs found in the sampled window.\n"

    by_cat = Counter(r.verdict.category for r in rows)
    recurring: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for r in rows:
        recurring[(_job_family(r.job_name), r.verdict.category)].append(r)

    repeated = {k: v for k, v in recurring.items() if len(v) > 1}
    out: list[str] = []

    out.append("# Podman CI flake triage\n")
    out.append(
        f"Sampled the **{sampled_runs}** most recent failed workflow runs in "
        f"`podman-container-tools/podman`, yielding **{len(rows)}** failed jobs "
        f"(the `Total Success` required-checks gate is excluded, it is an aggregate "
        f"and not a real failure).\n"
    )

    out.append("\n## Failures by mechanism\n")
    out.append("| Category | Count | Share | What it means |")
    out.append("|---|---:|---:|---|")
    for cat, n in by_cat.most_common():
        out.append(
            f"| `{cat}` | {n} | {100 * n / len(rows):.0f}% | {CATEGORIES.get(cat, '')} |"
        )

    unknown = by_cat.get("UNKNOWN", 0)
    out.append(
        f"\n`UNKNOWN` is {100 * unknown / len(rows):.0f}% of the sample. That number is "
        f"the honest measure of how far the rules go; every entry in it is a rule that "
        f"has not been written yet, not a failure that has been explained.\n"
    )

    out.append("\n## Recurring: same lane, same mechanism, more than once\n")
    if not repeated:
        out.append("_Nothing recurred in this window._\n")
    else:
        out.append("| Job lane | Mechanism | Times | Example evidence |")
        out.append("|---|---|---:|---|")
        for (lane, cat), items in sorted(
            repeated.items(), key=lambda kv: -len(kv[1])
        ):
            ev = next((i.verdict.evidence for i in items if i.verdict.evidence), "")
            ev = md_cell(ev)
            out.append(f"| `{md_cell(lane, 60)}` | `{cat}` | {len(items)} | `{ev}` |")
        out.append(
            "\nThese are the quarantine candidates. A lane that fails the same way "
            "repeatedly across unrelated PRs is not being broken by those PRs.\n"
        )

    out.append("\n## Every classified failure\n")
    out.append("| Run | Job | Mechanism | Rule | Confidence | Evidence |")
    out.append("|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: (x.verdict.category, x.job_name)):
        ev = md_cell(r.verdict.evidence or "", 90)
        out.append(
            f"| [{r.run_id}]({r.html_url}) | `{md_cell(r.job_name, 60)}` | `{r.verdict.category}` "
            f"| `{r.verdict.rule}` | {r.verdict.confidence} | `{ev}` |"
        )

    return "\n".join(out) + "\n"
