# Measured results

Run 18 Aug 2026 against `podman-container-tools/podman` live CI. Full report:
[`report-25runs.md`](report-25runs.md).

## Sample

25 most recent failed workflow runs → **41 failed jobs** after excluding the
`Total Success` required-checks gate and GitHub bot jobs (`copilot-*`), which are not
Podman test lanes and only inflate the denominator.

## Classification

| Category | Count | Share |
|---|---:|---:|
| `TEST_FAILURE` | 29 | 71% |
| `BUILD` | 7 | 17% |
| `LINT` | 2 | 5% |
| `TIMEOUT_HANG` | 1 | 2% |
| `UNKNOWN` | 1 | 2% |
| `INFRA_RESOURCE` | 1 | 2% |

**2% UNKNOWN is reported, not hidden.** Each one is a rule that has not been written,
not a failure that has been explained. Any tool of this kind can reach 0% UNKNOWN by
guessing; the number is only meaningful if it is allowed to be non-zero.

## Recurring tests

Counted **per failing test, deduplicated by run**. An earlier version of this report
grouped by job lane instead, which answered a different and much weaker question: a lane
can go red seven times on seven unrelated tests and none of them is a flake. The lane
number looked impressive and meant very little.

Deduplicating by run matters just as much. Podman fans one commit across a large OS/mode
matrix, so a PR that genuinely breaks a test yields a dozen failures of that test from a
single push. Widening the sample to 50 runs made this concrete: `podman artifact ls`
failed **26 times**, the largest count in the whole sample, and every one traced to two
runs on a single branch that was itself reworking `artifact ls` output. That is a
regression in one PR, not a flake. Two more apparent hot-spots collapsed the same way.

After correcting for both, the 25-run sample yields exactly one genuine candidate:

| Job lane | Failing test | Distinct runs |
|---|---|---:|
| `int local root` | `[FAIL] Podman rmi [It] podman image rm - concurrent with shared layers` | 2 |

Both occurrences are on **pushes to `main`**, roughly 7.5 hours apart, so neither is
attributable to any contributor's branch. Widening to 50 runs did not add a third, which
is consistent with a real but rare failure rather than noise.

Prior art: issue **#18659** described this exact race and was closed in 2023 by **#18664**
("don't remove concurrently with builds"), then locked. The same test is failing the same
way on trunk again, so the fix regressed or was incomplete.

The other two lanes that looked recurring under the old grouping do not survive it:
`podman detects correct tty size` is already tracked in open issue **#10710**, where a
maintainer stated in 2023 that it likely cannot be fixed without a bidirectional conmon
channel; and `podman run memory test on oomkilled container` appeared exactly once, which
is not evidence of anything.

## A third pass: adversarial testing

A separate hostile pass wrote 39 more tests and found four real defects, three of them
confirmed against specific cached logs rather than invented inputs:

- `Check make vendor is clean` failures fell to `UNKNOWN`, even though the BUILD
  category's own description says "compile or **vendor** step". Jobs `94794824043`,
  `94818536544`.
- A runner missing `/dev/kvm` fell to `UNKNOWN`, though "could not start a VM" is
  literally the `INFRA_RESOURCE` description. Job `95398591212`.
- Some real logs carry a UTF-8 BOM, which defeated the timestamp regex on line 0 and
  crashed `print()` on a cp1252 Windows console.
- Backticks inside evidence closed the markdown inline-code span early, which matters
  because Go tooling quotes identifiers in backticks constantly.

Fixing those took **UNKNOWN from 12% to 2%** on the same 25 runs.

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
