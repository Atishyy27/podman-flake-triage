"""podman-flake-triage: pull real Podman CI failures, classify them, write a report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ingest
from .classify import classify
from .extract import extract
from .report import Row, render


def cmd_fetch(args: argparse.Namespace) -> int:
    cache = ingest.Cache(Path(args.cache))
    runs = ingest.failed_runs(cache, args.runs)
    print(f"{len(runs)} failed runs", file=sys.stderr)
    total = 0
    for i, run in enumerate(runs, 1):
        jobs = ingest.failed_jobs(cache, run["id"])
        for job in jobs:
            ingest.job_log(cache, job.job_id)
            total += 1
        print(f"  [{i}/{len(runs)}] run {run['id']}: {len(jobs)} failed jobs",
              file=sys.stderr)
    print(f"cached {total} job logs into {args.cache}", file=sys.stderr)
    return 0


def _rows(cache: ingest.Cache, limit: int) -> list[Row]:
    rows: list[Row] = []
    for run in ingest.failed_runs(cache, limit):
        for job in ingest.failed_jobs(cache, run["id"]):
            log = ingest.job_log(cache, job.job_id)
            excerpt = extract(log)
            verdict = classify(excerpt, job.name, job.failed_step or "")
            rows.append(
                Row(
                    run_id=job.run_id,
                    job_id=job.job_id,
                    job_name=job.name,
                    failed_step=job.failed_step,
                    verdict=verdict,
                    created_at=run.get("created_at"),
                    html_url=job.html_url or run.get("html_url", ""),
                )
            )
    return rows


def cmd_report(args: argparse.Namespace) -> int:
    cache = ingest.Cache(Path(args.cache))
    rows = _rows(cache, args.runs)
    text = render(rows, args.runs)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out} ({len(rows)} failed jobs)", file=sys.stderr)
    else:
        print(text)
    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    """Emit an unlabeled JSONL sample for hand-labelling, so accuracy can be measured."""
    cache = ingest.Cache(Path(args.cache))
    rows = _rows(cache, args.runs)
    step = max(1, len(rows) // args.n)
    picked = rows[::step][: args.n]
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in picked:
            fh.write(
                json.dumps(
                    {
                        "job_id": r.job_id,
                        "job_name": r.job_name,
                        "failed_step": r.failed_step,
                        "url": r.html_url,
                        "predicted": r.verdict.category,
                        "evidence": r.verdict.evidence,
                        "true_label": "",
                    }
                )
                + "\n"
            )
    print(f"wrote {len(picked)} rows to {args.out}; fill in true_label by hand",
          file=sys.stderr)
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    """Score predictions against a hand-labelled file produced by `sample`."""
    labelled = [
        json.loads(ln)
        for ln in Path(args.labels).read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    scored = [r for r in labelled if r.get("true_label")]
    if not scored:
        print("no rows have true_label filled in", file=sys.stderr)
        return 1
    hits = sum(1 for r in scored if r["predicted"] == r["true_label"])
    print(f"labelled: {len(scored)}")
    print(f"correct:  {hits}")
    print(f"accuracy: {100 * hits / len(scored):.1f}%")
    wrong = [r for r in scored if r["predicted"] != r["true_label"]]
    if wrong:
        print("\nmisclassified:")
        for r in wrong:
            print(f"  {r['job_name']}: predicted {r['predicted']}, actually {r['true_label']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="flaketriage", description=__doc__)
    p.add_argument("--cache", default=".cache", help="cache directory (default .cache)")
    p.add_argument("--runs", type=int, default=30, help="how many failed runs to sample")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch", help="download and cache runs, jobs and logs").set_defaults(
        func=cmd_fetch
    )

    r = sub.add_parser("report", help="classify cached failures and write a report")
    r.add_argument("--out", default=None, help="write markdown here instead of stdout")
    r.set_defaults(func=cmd_report)

    s = sub.add_parser("sample", help="emit a JSONL sample to hand-label")
    s.add_argument("--n", type=int, default=40)
    s.add_argument("--out", default="eval/sample.jsonl")
    s.set_defaults(func=cmd_sample)

    e = sub.add_parser("eval", help="score predictions against hand labels")
    e.add_argument("--labels", default="eval/sample.jsonl")
    e.set_defaults(func=cmd_eval)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
