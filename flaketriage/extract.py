"""Cut a job log down to the part that actually explains the failure.

This is the part naive implementations get wrong, and it is the reason this tool is not
just `grep -i error`. Podman's e2e suites are full of tests that deliberately provoke
errors and then assert on them, so a single passing run can contain dozens of lines
matching /error/i. Classifying the whole log means classifying that noise.

So: find the authoritative terminal marker the harness prints when it decides the job
failed, and only look at a bounded window around it. If no marker exists (an infra
failure that died before the harness ran), fall back to the tail, which is where setup
failures surface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# GitHub prefixes every log line with an ISO-8601 timestamp.
TS = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s?")

# Podman's lima-hosted e2e jobs then add their own elapsed-time prefix, e.g.
#   2026-08-17T21:16:16.1706218Z [+0627s] Summarizing 1 Failure:
# Both have to come off, or every line-anchored marker silently fails to match and the
# whole job falls through to UNKNOWN. This was a real bug: it made 64% of a live sample
# unclassifiable, and every one of those was an e2e job whose verdict was right there in
# the log.
ELAPSED = re.compile(r"^\[\+\d+s\]\s?")

# Some steps emit ANSI colour codes; they break naive line matching.
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# Terminal markers, most authoritative first. Each is a point where a test harness or
# the shell has already decided the job failed and is reporting why.
MARKERS: list[tuple[str, re.Pattern[str]]] = [
    ("ginkgo_summary", re.compile(r"^Summarizing \d+ Failure", re.M)),
    ("go_test_fail", re.compile(r"^--- FAIL: ", re.M)),
    ("bats_fail", re.compile(r"^not ok \d+ ", re.M)),
    ("make_error", re.compile(r"^make(?:\[\d+\])?: \*\*\* .*Error \d+", re.M)),
    ("process_exit", re.compile(r"^##\[error\]Process completed with exit code \d+", re.M)),
    ("gha_error", re.compile(r"^##\[error\]", re.M)),
]

BEFORE = 40
AFTER = 80
TAIL = 120


# Markers where a test harness has already stated its own verdict. Text BEFORE one of
# these belongs to earlier, possibly passing, tests; only text from the marker onward
# describes the failure being classified.
HARNESS_MARKERS = {"ginkgo_summary", "go_test_fail", "bats_fail"}


@dataclass
class Excerpt:
    text: str
    marker: str
    """Which terminal marker anchored the excerpt, or 'tail' if none was found."""
    focus: str = ""
    """The text from the marker onward. For harness markers this is the failure block
    itself; classifying against it avoids inheriting noise from earlier tests."""

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines()

    @property
    def focus_lines(self) -> list[str]:
        return (self.focus or self.text).splitlines()

    @property
    def harness_verdict(self) -> bool:
        return self.marker in HARNESS_MARKERS


def strip_timestamps(log: str) -> list[str]:
    """Normalise a raw job log to bare content lines.

    Order matters: GitHub's timestamp is outermost, Ginkgo's elapsed marker sits inside
    it, and ANSI codes can wrap either.
    """
    out: list[str] = []
    for raw in log.splitlines():
        ln = ANSI.sub("", raw)
        ln = TS.sub("", ln)
        ln = ELAPSED.sub("", ln)
        out.append(ln.rstrip())
    return out


def extract(log: str) -> Excerpt:
    """Return the window of the log worth classifying."""
    lines = strip_timestamps(log)
    if not lines:
        return Excerpt(text="", marker="empty")

    body = "\n".join(lines)
    for name, pattern in MARKERS:
        match = pattern.search(body)
        if not match:
            continue
        # Translate the character offset back to a line index.
        idx = body.count("\n", 0, match.start())
        lo = max(0, idx - BEFORE)
        hi = min(len(lines), idx + AFTER)
        return Excerpt(
            text="\n".join(lines[lo:hi]),
            marker=name,
            focus="\n".join(lines[idx:hi]),
        )

    tail = "\n".join(lines[-TAIL:])
    return Excerpt(text=tail, marker="tail", focus=tail)
