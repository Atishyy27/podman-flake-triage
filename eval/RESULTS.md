# Measured results

Run 18 Aug 2026 against `podman-container-tools/podman` live CI. Full report:
[`report-25runs.md`](report-25runs.md).

## Sample

25 most recent failed workflow runs → **42 failed jobs** after excluding the
`Total Success` required-checks gate.

## Classification

| Category | Count | Share |
|---|---:|---:|
| `TEST_FAILURE` | 29 | 69% |
| `UNKNOWN` | 5 | 12% |
| `BUILD` | 5 | 12% |
| `LINT` | 2 | 5% |
| `TIMEOUT_HANG` | 1 | 2% |

**12% UNKNOWN is reported, not hidden.** Each one is a rule that has not been written,
not a failure that has been explained. Any tool of this kind can reach 0% UNKNOWN by
guessing; the number is only meaningful if it is allowed to be non-zero.

## Recurring lanes

| Job lane | Times | Example evidence |
|---|---:|---|
| `int local root` | 7 | `[FAIL] Podman rmi [It] podman image rm - concurrent with shared layers` |
| `sys remote root` | 5 | `not ok 317 podman detects correct tty size in 3313ms` |
| `int local rootless` | 3 | `[FAIL] Podman run memory [It] podman run memory test on oomkilled container` |

These recur across unrelated PRs, which is the signal that separates a flake from a
branch that is genuinely broken.

**Are these already tracked?** Podman tracks flakes with a `flakes` label; there are 42
open. None of the three above matched an open flake-labelled issue *by title*. That is
weak evidence — they may well be tracked under different wording, and title matching is
not a real check. **Not claiming these are undiscovered.** Confirming that properly means
reading the 42 issues, which is exactly the kind of manual triage this tool is meant to
reduce, and is listed as follow-up work rather than asserted as a finding.

## Two bugs that only real data exposed

Both were invisible against synthetic fixtures, and both are the reason this was built
against the live API instead of hand-written samples.

**1. Auth dropped on redirect.** The job-logs endpoint 302s to Azure blob storage.
`urllib` forwarded GitHub's `Authorization` header to Azure, which rejected it with a
401. Fixed by stripping the header on any cross-host redirect.

**2. Unstripped Ginkgo prefix → 64% UNKNOWN.** Podman's lima-hosted e2e jobs prefix each
line with an elapsed marker *inside* GitHub's timestamp:

```
2026-08-17T21:16:16.1706218Z [+0627s] Summarizing 1 Failure:
```

Every line-anchored marker regex silently failed to match, so the richest logs in the
sample, the e2e ones, all fell through to `UNKNOWN`. **After stripping both prefixes,
UNKNOWN fell from 64% to 9%** on the same cached data, with no rule changes.

That is the single most useful thing this exercise produced: the failure mode was not a
missing rule, it was a normalisation bug upstream of every rule, and no amount of adding
categories would have found it.

## Accuracy against hand labels

Not yet measured. The path exists (`sample` → hand-label → `eval`) and is the next step;
no accuracy figure is claimed until those labels exist.
