# podman-flake-triage

Pulls real failed CI runs from `podman-container-tools/podman`, works out *why* each job
failed, and reports which failures keep recurring.

Built as a prototype for the LFX Mentorship Term-3 project
[Agentic CI Flake Categorization and Analysis](https://github.com/podman-container-tools/podman/issues/29265).

## What this is

A working tool, run against real data. Not a mockup, not a design doc. Every number in
the generated report comes from the GitHub Actions API against Podman's actual CI
history. Nothing here is synthetic.

## What this is NOT

- **Not the mentorship project.** The full project wants an LLM agent, plain-English
  explanations and auto-filed issues. This is the layer underneath that: the ingestion,
  the failure extraction, and a deterministic classifier that produces the labeled
  ground truth an agent would have to be measured against. I built this part first
  deliberately, because an agent with no evaluation set is unfalsifiable.
- **Not an LLM.** Classification here is rule-based and auditable. That is a scoping
  choice, not a limitation I am hiding: see "Why rules first" below.
- **Not connected to Podman.** It only reads the public API. It posts nothing, opens
  nothing, and comments nowhere.

## Why rules first, not an agent first

The failure mode for this kind of tool is a classifier that is confidently wrong. An
agent that labels a genuine product regression as "infrastructure noise" is worse than
no agent, because maintainers stop reading the output and the flake stays.

So the order here is deliberate: build the extraction and a deterministic baseline,
measure it against hand labels, and only then add a model that has to beat a number.
`UNKNOWN` is reported as a first-class category for the same reason. The share of
`UNKNOWN` is the honest measure of how far the rules reach.

## The hard part: incidental errors

Podman's e2e suites are full of tests that deliberately provoke errors and assert on
them. A single passing run contains dozens of lines matching `/error/i`. Any tool built
on `grep -i error` will read the first one and misclassify.

The extractor handles this by anchoring on the *terminal marker* the harness prints when
it has already decided the job failed (`Summarizing N Failure`, `--- FAIL:`,
`not ok N`, `make: *** Error`, `##[error]Process completed`), and, when that marker came
from a test harness, classifying only the block from the marker onward. Text above it
belongs to earlier tests.

There is a regression test for exactly this case:
`tests/test_classify.py::test_incidental_errors_do_not_beat_the_real_failure`, where a
log contains a registry timeout from an earlier test *and* a real Ginkgo assertion
failure. The correct answer is `TEST_FAILURE`. Before the fix, the tool said
`INFRA_NETWORK`.

## Taxonomy

| Category | Meaning |
|---|---|
| `INFRA_NETWORK` | Registry, DNS or transport failure outside the code under test |
| `INFRA_RESOURCE` | Runner out of disk or memory, or a VM that would not start |
| `BUILD` | Compile or vendor step failed; the suite never ran |
| `LINT` | Static analysis, formatting or validation gate |
| `TEST_FAILURE` | A test asserted and the assertion did not hold |
| `TIMEOUT_HANG` | Job or test exceeded its time budget |
| `UNKNOWN` | No rule matched. Needs a human. |

Every verdict carries the exact log line that produced it, plus the rule name and a
confidence. A category alone is an assertion; a category with its evidence line is
something a maintainer can check in two seconds and disagree with.

## Quickstart

```bash
# auth: uses GITHUB_TOKEN, or falls back to `gh auth token`
python -m flaketriage.cli --runs 25 fetch            # download + cache runs, jobs, logs
python -m flaketriage.cli --runs 25 report --out report.md
```

Everything is cached under `.cache/`, so re-running while tuning rules costs no API
calls and gives byte-identical input.

## Measuring it

Accuracy claims need labels, so there is a path to produce them:

```bash
python -m flaketriage.cli --runs 25 sample --n 40 --out eval/sample.jsonl
# fill in "true_label" on each row by reading the linked job
python -m flaketriage.cli eval --labels eval/sample.jsonl
```

`eval` prints accuracy and lists every misclassification. See `eval/RESULTS.md` for the
measured run.

## Status and limitations

- Sampled window is the most recent N failed runs, not the full history.
- `TIMEOUT_HANG` rules are written from GitHub Actions convention; that category was not
  observed in the initial sample, so it is the least tested of the six.
- The `Total Success` job is excluded everywhere. It is the required-checks gate and it
  appears as "failed" on nearly every failed run; counting it drowns the real signal.
- Job logs expire. Runs old enough to have lost their logs are treated as empty rather
  than aborting the sweep.
- Rules were written against a sample of Podman's CI. They will not transfer unchanged
  to another project's log formats.

## Layout

```
flaketriage/
  ingest.py     GitHub Actions API client, disk cache, redirect/rate-limit handling
  extract.py    terminal-marker anchoring, the incidental-error defence
  classify.py   taxonomy + rules, each returning its evidence line
  report.py     recurrence-first markdown report
  cli.py        fetch / report / sample / eval
tests/          regression tests, including the incidental-error case
```

## Author

Atishay Jain, [github.com/Atishyy27](https://github.com/Atishyy27)
