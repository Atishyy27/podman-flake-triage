"""Pull failed CI runs, their failed jobs, and job logs from the GitHub Actions API.

Everything is cached to disk on first fetch. Podman's CI is busy enough that a single
uncached sweep of 50 runs is a few hundred API calls, and the point of the cache is that
re-running the classifier while tuning rules costs nothing and gives identical input.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path

API = "https://api.github.com"
REPO = "podman-container-tools/podman"

# Appears as a failed job on nearly every failed run. It is the required-checks gate,
# not a real failure, and counting it drowns the actual signal.
AGGREGATE_JOBS = {"Total Success"}

# Bot/meta jobs that are not Podman test lanes. Counting them inflates both the
# denominator and the UNKNOWN rate with things no maintainer would ever triage.
BOT_JOB_PREFIXES = ("copilot-", "claude-", "dependabot")


@dataclass
class FailedJob:
    run_id: int
    job_id: int
    name: str
    failed_step: str | None
    started_at: str | None
    html_url: str

    def as_dict(self) -> dict:
        return asdict(self)


def _token() -> str:
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    try:
        out = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise SystemExit(
            "no credentials: set GITHUB_TOKEN or authenticate with `gh auth login`"
        ) from exc


class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """The logs endpoint 302s to Azure blob storage, which rejects the request outright
    if GitHub's Authorization header is forwarded to it. Drop the header whenever the
    redirect leaves api.github.com."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and "api.github.com" not in newurl:
            new.headers = {
                k: v for k, v in new.headers.items() if k.lower() != "authorization"
            }
            new.unredirected_hdrs.pop("Authorization", None)
        return new


_opener = urllib.request.build_opener(_StripAuthOnRedirect)


def _get(path: str, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {_token()}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "podman-flake-triage",
        },
    )
    for attempt in range(4):
        try:
            with _opener.open(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            # Secondary rate limits answer 403 with a Retry-After; primary limits 429.
            if exc.code in (403, 429) and attempt < 3:
                wait = int(exc.headers.get("Retry-After", 2 ** (attempt + 3)))
                time.sleep(min(wait, 60))
                continue
            raise
    raise RuntimeError(f"gave up fetching {path}")


class Cache:
    def __init__(self, root: Path):
        self.root = root
        (self.root / "logs").mkdir(parents=True, exist_ok=True)

    def read_json(self, key: str):
        p = self.root / f"{key}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def write_json(self, key: str, data) -> None:
        p = self.root / f"{key}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def read_log(self, job_id: int) -> str | None:
        p = self.root / "logs" / f"{job_id}.log"
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else None

    def write_log(self, job_id: int, text: str) -> None:
        (self.root / "logs" / f"{job_id}.log").write_text(
            text, encoding="utf-8", errors="replace"
        )


def failed_runs(cache: Cache, limit: int) -> list[dict]:
    """Most recent failed workflow runs, newest first."""
    cached = cache.read_json(f"runs_{limit}")
    if cached is not None:
        return cached

    runs: list[dict] = []
    page = 1
    while len(runs) < limit:
        per = min(100, limit - len(runs))
        raw = _get(
            f"/repos/{REPO}/actions/runs?status=failure&per_page={per}&page={page}"
        )
        batch = json.loads(raw).get("workflow_runs", [])
        if not batch:
            break
        runs.extend(batch)
        page += 1

    slim = [
        {
            "id": r["id"],
            "name": r.get("name"),
            "created_at": r.get("created_at"),
            "head_branch": r.get("head_branch"),
            "event": r.get("event"),
            "html_url": r.get("html_url"),
        }
        for r in runs[:limit]
    ]
    cache.write_json(f"runs_{limit}", slim)
    return slim


def failed_jobs(cache: Cache, run_id: int) -> list[FailedJob]:
    """Failed jobs for one run, with the aggregate gate job filtered out."""
    cached = cache.read_json(f"jobs/{run_id}")
    if cached is None:
        raw = _get(f"/repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100")
        cached = json.loads(raw).get("jobs", [])
        cache.write_json(f"jobs/{run_id}", cached)

    out: list[FailedJob] = []
    for job in cached:
        if job.get("conclusion") != "failure":
            continue
        name = job.get("name", "")
        if name in AGGREGATE_JOBS or name.lower().startswith(BOT_JOB_PREFIXES):
            continue
        failed_step = next(
            (
                s.get("name")
                for s in job.get("steps") or []
                if s.get("conclusion") == "failure"
            ),
            None,
        )
        out.append(
            FailedJob(
                run_id=run_id,
                job_id=job["id"],
                name=job.get("name", "?"),
                failed_step=failed_step,
                started_at=job.get("started_at"),
                html_url=job.get("html_url", ""),
            )
        )
    return out


def job_log(cache: Cache, job_id: int) -> str:
    """Plain-text log for a single job. The job-level endpoint returns text directly,
    unlike the run-level endpoint which returns a zip archive."""
    cached = cache.read_log(job_id)
    if cached is not None:
        return cached
    try:
        raw = _get(f"/repos/{REPO}/actions/jobs/{job_id}/logs", accept="application/vnd.github.raw")
        # utf-8-sig strips a leading BOM. Some real Podman logs carry one, and it
        # both defeats the timestamp regex on line 0 and crashes cp1252 stdout.
        text = raw.decode("utf-8-sig", errors="replace")
    except urllib.error.HTTPError as exc:
        # Logs expire; treat as empty rather than aborting a whole sweep.
        if exc.code in (404, 410):
            text = ""
        else:
            raise
    cache.write_log(job_id, text)
    return text
