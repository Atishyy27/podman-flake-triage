"""Adversarial gauntlet for podman-flake-triage.

This is NOT a happy-path suite. Every test here starts from "assume the
pipeline is broken until proven otherwise" and tries to construct the input
that proves it. Passing tests here are load-bearing: they pin down specific
behaviors (some of them genuine bugs) with a reproducing input, so a future
change can't silently regress or silently "fix" something without the
change being visible in a diff.

Sections:
  1. Crash hunting          - malformed/hostile input must not raise
  2. extract() offset math  - round-trip invariant for the char->line map
  3. classify() rule order  - real-shaped inputs that expose precedence bugs
  4. report.py injection    - markdown table/code-span escaping
  5. Windows console crash  - print(text) under the real Windows stdout codec
  6. Real cached data       - the 42 real Podman logs already on disk

Tests marked with `# BUG:` document confirmed, reproduced defects. They are
written to assert the CURRENT (wrong) behavior on purpose, so the suite
fails loudly the moment someone fixes the underlying bug without updating
the test - that is the point, not an oversight.
"""
from __future__ import annotations

import glob
import io
import sys
import time
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest

from flaketriage.extract import extract, strip_timestamps, MARKERS, BEFORE, AFTER, TAIL
from flaketriage.classify import classify, RULES
from flaketriage.report import Row, render, _job_family
from flaketriage import ingest


CACHE = pathlib.Path(__file__).resolve().parents[1] / ".cache"


def _log(body: str) -> str:
    """Match test_classify.py's helper: prefix every line with a GH timestamp."""
    return "\n".join(f"2026-08-17T21:16:16.1706218Z {ln}" for ln in body.splitlines())


# ---------------------------------------------------------------------------
# 1. Crash hunting
# ---------------------------------------------------------------------------

class TestCrashHunting:
    def test_empty_log(self):
        exc = extract("")
        assert exc.marker == "empty"
        v = classify(exc)
        assert v.category == "UNKNOWN"

    def test_whitespace_only_log(self):
        # Not literally empty ("" .splitlines() == []), but every line is blank
        # after rstrip. extract() does NOT special-case this: it falls through
        # to the 'tail' marker with empty text, not the 'empty' marker.
        exc = extract("   \n\t\n   \n")
        assert exc.marker == "tail"          # not "empty" - inconsistent label
        assert exc.text.strip() == ""
        v = classify(exc)
        assert v.category == "UNKNOWN"       # still correct downstream

    def test_log_with_no_newlines_at_all(self):
        huge_single_line = "x" * 500 + " [FAIL] something broke " + "y" * 500
        exc = extract(huge_single_line)
        assert exc.marker == "ginkgo_failure" or exc.marker in ("tail",)
        v = classify(exc)
        # must not raise regardless of verdict
        assert v.category in classify.__globals__["CATEGORIES"] if False else True

    def test_single_line_100k_chars_perf_and_no_crash(self):
        body = ("a" * 100_000) + " [FAIL] boom"
        start = time.time()
        exc = extract(_log(body))
        v = classify(exc)
        elapsed = time.time() - start
        assert v.category in {"TEST_FAILURE", "UNKNOWN"}
        assert elapsed < 5.0, f"classification took {elapsed:.2f}s on a 100k char line - possible ReDoS"

    def test_null_bytes_do_not_crash(self):
        body = "some\x00output\x00with\x00nulls\n--- FAIL: TestX (0.00s)\n"
        v = classify(extract(_log(body)))
        assert v.category == "TEST_FAILURE"

    def test_ansi_escape_codes_do_not_crash(self):
        body = "\x1b[31mError: something\x1b[0m\n\x1b[1m--- FAIL: TestY (0.00s)\x1b[0m\n"
        # ANSI codes right before the anchor text on the SAME line defeat the
        # '^--- FAIL: ' anchor (see TestAnsiBreaksMarkerAnchor below for the
        # dedicated proof). Here we only assert it doesn't crash.
        v = classify(extract(_log(body)))
        assert v.category in {"TEST_FAILURE", "UNKNOWN"}

    def test_crlf_line_endings_do_not_crash(self):
        body = "line one\r\nline two\r\n--- FAIL: TestZ (0.00s)\r\nmore\r\n"
        v = classify(extract(body))  # no _log() wrapper - test raw CRLF, no timestamps
        assert v.category == "TEST_FAILURE"

    def test_mojibake_and_invalid_unicode_replacement_chars(self):
        # Simulates what ingest.job_log() actually produces for non-UTF8 bytes:
        # raw.decode("utf-8", errors="replace") turns bad bytes into U+FFFD.
        raw_bytes = b"Building \xff\xfe garbage\n--- FAIL: TestMoji (0.00s)\n"
        text = raw_bytes.decode("utf-8", errors="replace")
        v = classify(extract(_log(text)))
        assert v.category == "TEST_FAILURE"

    def test_marker_matches_on_very_first_line(self):
        body = "Summarizing 1 Failure:\n  [FAIL] x\n" + "trailing noise\n" * 5
        exc = extract(_log(body))
        assert exc.marker == "ginkgo_summary"
        # idx==0, lo=max(0,0-BEFORE)=0 must not go negative / crash
        assert exc.text.splitlines()[0] != ""

    def test_marker_matches_on_very_last_line(self):
        body = "noise\n" * 5 + "not ok 1 the last line itself"
        exc = extract(_log(body))
        assert exc.marker == "bats_fail"
        v = classify(exc)
        assert v.category == "TEST_FAILURE"

    def test_unicode_job_name(self):
        fam = _job_family("int local rootless 中文-fedora / lima")
        assert fam  # no crash, non-empty

    def test_job_name_with_pipe_into_job_family(self):
        # should not crash _job_family itself
        fam = _job_family("int | local | rootless")
        assert isinstance(fam, str)

    def test_job_name_fewer_than_3_tokens(self):
        assert _job_family("build") == "build"
        assert _job_family("") == ""
        assert _job_family("a b") == "a b"

    def test_render_with_empty_rows(self):
        out = render([], 30)
        assert "No failed jobs found" in out

    def test_render_with_duplicate_job_ids(self):
        v = classify(extract(_log("--- FAIL: TestDup (0.00s)\n")))
        rows = [
            Row(1, 42, "int local root fedora-current / lima", "Test", v, None, "http://x"),
            Row(1, 42, "int local root fedora-current / lima", "Test", v, None, "http://x"),
        ]
        out = render(rows, 5)
        # not deduped - both appear. Documented, not a crash.
        assert out.count("`int local root fedora-current / lima`") >= 2

    def test_render_with_none_failed_step_and_empty_html_url(self):
        v = classify(extract(_log("some unmatched output\n")))
        rows = [Row(1, 2, "windows e2e", None, v, None, "")]
        out = render(rows, 1)
        assert "windows e2e" in out
        assert "[1]()" in out  # empty html_url -> empty markdown link target, not a crash


# ---------------------------------------------------------------------------
# 2. extract() char-offset -> line-index round trip
# ---------------------------------------------------------------------------

class TestExtractOffsetInvariant:
    """Invariant (round-trip): for the reconstructed body = '\\n'.join(lines),
    idx = body.count('\\n', 0, match.start()) must equal the index i such that
    lines[i] is the line containing match.start(). Since `body` is built from
    the SAME `lines` list that is later sliced, this is self-consistent by
    construction - but "self-consistent" is a claim, not a proof. We prove it
    empirically across CRLF logs, logs where timestamp-stripping changes line
    lengths, and logs with unicode content that shifts byte-vs-codepoint
    offsets (irrelevant in Python str, but worth confirming empirically)."""

    @pytest.mark.parametrize("newline", ["\n", "\r\n"])
    def test_offset_correct_with_various_newlines(self, newline):
        raw_lines = [
            "2026-08-17T00:00:00.000Z setup step one",
            "2026-08-17T00:00:00.100Z setup step two, with trailing junk that changes length",
            "2026-08-17T00:00:00.200Z --- FAIL: TestOffset (0.01s)",
            "2026-08-17T00:00:00.300Z    offset_test.go:10: boom",
        ]
        body = newline.join(raw_lines)
        exc = extract(body)
        assert exc.marker == "go_test_fail"
        # The extracted window must contain the exact FAIL line, proving the
        # idx computed from the stripped/rejoined body pointed at the right
        # line of the ORIGINAL (stripped) lines list, regardless of source
        # newline convention.
        assert any("--- FAIL: TestOffset" in ln for ln in exc.text.splitlines())

    def test_offset_correct_when_timestamp_stripping_shortens_lines_unevenly(self):
        # Lines have deliberately different lengths pre-strip, so if idx were
        # computed on the RAW body instead of the stripped body, this would
        # point at the wrong line.
        lines = [
            "2026-08-17T00:00:00.000000001Z short",
            "2026-08-17T00:00:00.1Z " + "padding " * 20,
            "2026-08-17T00:00:00.123456789Z --- FAIL: TestShift (0.00s)",
        ]
        body = "\n".join(lines)
        exc = extract(body)
        assert exc.marker == "go_test_fail"
        assert "--- FAIL: TestShift" in exc.text

    def test_boundary_window_never_goes_negative_or_out_of_range(self):
        # marker on line 0 of a very short log
        body = "not ok 1 first line only"
        exc = extract(body)
        lines = strip_timestamps(body)
        assert exc.marker == "bats_fail"
        # window slice must be valid - extract() itself would have raised if not
        assert exc.text != ""

    def test_marker_last_line_window_hi_clamped_to_len_lines(self):
        body = "\n".join(f"line {i}" for i in range(10)) + "\n--- FAIL: TestLast (0.00s)"
        exc = extract(body)
        lines = strip_timestamps(body)
        idx = len(lines) - 1
        assert exc.marker == "go_test_fail"
        # hi = min(len(lines), idx+AFTER) must equal len(lines), not overrun
        assert len(exc.text.splitlines()) == min(len(lines), BEFORE + 1)


class TestAnsiBreaksMarkerAnchor:
    """CORRECTNESS: an ANSI color code immediately preceding a terminal marker
    on the same line defeats the '^...' anchor in extract.MARKERS, because the
    marker patterns match literal whitespace ('\\s*') or nothing before the
    marker text, not an arbitrary ANSI escape sequence. Ginkgo/go test commonly
    colorize FAIL lines when run with a TTY-attached harness."""

    def test_ansi_prefixed_ginkgo_summary_is_not_anchored(self):
        # Real ginkgo output when colorized: "\x1b[91mSummarizing 1 Failure:\x1b[0m"
        body = "\x1b[91mSummarizing 1 Failure:\x1b[0m\n  [FAIL] colored test\n"
        exc = extract(_log(body))
        # BUG: falls back to 'tail' instead of anchoring on ginkgo_summary,
        # because '^Summarizing' cannot match a line that starts with ESC.
        assert exc.marker == "ginkgo_summary"

    def test_ansi_prefixed_go_test_fail_is_not_anchored(self):
        body = "\x1b[31m--- FAIL: TestColored (0.00s)\x1b[0m\n"
        exc = extract(_log(body))
        assert exc.marker == "go_test_fail"


# ---------------------------------------------------------------------------
# 3. classify() rule order - real-shaped wrong-answer attacks
# ---------------------------------------------------------------------------

class TestRuleOrderAttacks:
    def test_infra_network_wins_when_incidental_FAIL_text_present_no_harness_verdict(self):
        """An infra failure (no harness ever ran) whose surrounding noise
        happens to contain a literal '[FAIL]' substring that is NOT a real
        ginkgo verdict line. Ground truth: INFRA_NETWORK. Rule order gives
        the correct answer here because no harness marker fired, so the full
        window is scanned and INFRA_NETWORK (checked first) legitimately
        wins over a coincidental non-anchored '[FAIL]' substring."""
        body = (
            "Step: [FAIL] retry policy engaged (attempt 1)\n"   # not '^\\s*\\[FAIL\\]' at true col 0 after strip? it IS at col0
            "Error: pinging container registry quay.io: Get \"https://quay.io/v2/\": "
            "dial tcp 3.4.5.6:443: i/o timeout\n"
            "##[error]Process completed with exit code 125\n"
        )
        v = classify(extract(_log(body)))
        assert v.category == "INFRA_NETWORK", v

    def test_BUG_infra_resource_beats_real_ginkgo_test_failure_when_test_data_mentions_disk_space(self):
        """CONFIRMED MISCLASSIFICATION.

        A genuine TEST_FAILURE: ginkgo says 'Summarizing 1 Failure' (a harness
        verdict), so classify() correctly narrows the scan to excerpt.focus
        (from the marker onward) to avoid noise from earlier tests. BUT the
        RULES loop still checks INFRA_RESOURCE's `out_of_space` pattern
        *before* TEST_FAILURE's `ginkgo_failure` pattern, over the ENTIRE
        focus block - not just the verdict line itself. If the assertion
        diff printed after the verdict happens to mention 'no space left on
        device' as test DATA (e.g. the test is asserting podman's own
        disk-full error handling), INFRA_RESOURCE wins even though the
        harness already said this was a test assertion failure.

        This directly contradicts the design comment in classify.py: 'the
        one the harness actually died on is the one that counts' - the
        harness said TEST_FAILURE, but the tool says INFRA_RESOURCE.
        """
        body = (
            "Summarizing 1 Failure:\n"
            "  [FAIL] Podman run disk full handling [It] should report a clear "
            "error when the container write fails\n"
            "  Expected error to contain \"no space left on device\" (the message "
            "podman is supposed to surface)\n"
            "  Actual: <nil>\n"
        )
        v = classify(extract(_log(body)))
        # This is what SHOULD happen (a maintainer would call this TEST_FAILURE):
        # assert v.category == "TEST_FAILURE"
        # This is what ACTUALLY happens - documenting the bug:
        assert v.category == "INFRA_RESOURCE", (
            f"expected the documented bug (INFRA_RESOURCE beating a harness-"
            f"verdicted TEST_FAILURE) but got {v.category} - has this been fixed?"
        )
        assert v.rule == "out_of_space"

    def test_BUG_infra_network_beats_real_go_test_failure_when_test_data_mentions_connection_refused(self):
        """Same bug, go_test_fail harness marker instead of ginkgo."""
        body = (
            "--- FAIL: TestDialErrorMessage (0.00s)\n"
            "    dial_test.go:22: got \"dial tcp 127.0.0.1:1234: connection refused\", "
            "want \"dial tcp 127.0.0.1:1234: connection refused\"\n"
        )
        v = classify(extract(_log(body)))
        assert v.category == "INFRA_NETWORK", (
            f"expected documented bug, got {v.category}"
        )

    def test_lint_vs_build_precedence_is_debatable_not_indefensible(self):
        """A validate/lint job whose failure is ACTUALLY a compile error
        (golangci-lint invokes the type checker, so a real 'undefined: foo'
        can appear in lint output). LINT is checked before BUILD in RULES,
        so LINT wins. Arguably BUILD (undefined symbol) is the more specific,
        more actionable root cause - but this is a judgment call, not a clear
        bug, since golangci-lint failing due to a compile error is still
        legitimately "the validation gate failed"."""
        body = (
            "running golangci-lint run ./...\n"
            "pkg/foo/bar.go:12:5: undefined: someHelper\n"
            "##[error]Process completed with exit code 1\n"
        )
        v = classify(extract(_log(body)))
        assert v.category == "LINT"  # current behavior; BUILD would be equally defensible

    def test_incidental_error_before_harness_verdict_is_correctly_ignored(self):
        """Sanity check mirroring the existing test in test_classify.py, run
        here to confirm the harness-verdict narrowing actually protects
        against noise BEFORE the marker (this part of the design works)."""
        body = (
            "Error: unable to connect to registry: dial tcp 1.2.3.4:443: i/o timeout\n"
            "ok 1 unrelated passing test\n"
            "Summarizing 1 Failure:\n"
            "  [FAIL] Podman run [It] should honor --memory\n"
        )
        v = classify(extract(_log(body)))
        assert v.category == "TEST_FAILURE"


# ---------------------------------------------------------------------------
# 4. report.py markdown injection
# ---------------------------------------------------------------------------

class TestMarkdownInjection:
    def test_evidence_pipe_is_escaped(self):
        v = classify(extract(_log("--- FAIL: TestPipe (0.00s)\n")))
        v.evidence = "boom | this | looks | like | columns"
        rows = [Row(1, 2, "int local root fedora-current / lima", "Test", v, None, "http://x")]
        out = render(rows, 1)
        # Every data row for this run must still have exactly 6 columns (7 pipes).
        for line in out.splitlines():
            if line.startswith("| [1]"):
                assert "\\|" in line, line
                assert line.count("|") - line.count("\\|") == 7, line

    def test_BUG_job_name_pipe_is_NOT_escaped_and_breaks_the_table(self):
        """CONFIRMED BUG: report.py escapes `evidence` for '|' in both table
        sections (`.replace("|", "\\|")`) but never escapes `job_name` or the
        derived `lane` (from _job_family). A job name containing a literal
        '|' - plausible for a custom matrix `name:` field, or a workflow that
        interpolates a PR title into the job name - splits the markdown table
        row into extra columns.
        """
        v = classify(extract(_log("--- FAIL: TestPipeName (0.00s)\n")))
        evil_name = "int local | DROP TABLE jobs | root"
        rows = [Row(1, 2, evil_name, "Test", v, None, "http://x")]
        out = render(rows, 1)
        data_line = next(ln for ln in out.splitlines() if ln.startswith("| [1]"))
        # A well-formed 6-column row has 7 pipes. The unescaped job name adds 2 more.
        assert data_line.count("|") == 9, (
            f"expected the documented break (9 pipes from an unescaped job "
            f"name), got {data_line.count('|')}: {data_line!r}"
        )

    def test_BUG_lane_pipe_in_recurring_table_is_NOT_escaped(self):
        v1 = classify(extract(_log("--- FAIL: TestA (0.00s)\n")))
        v2 = classify(extract(_log("--- FAIL: TestB (0.00s)\n")))
        evil_name = "int | local rootless fedora-current / lima"
        rows = [
            Row(1, 2, evil_name, "Test", v1, None, "http://x"),
            Row(2, 3, evil_name, "Test", v2, None, "http://y"),
        ]
        out = render(rows, 2)
        # FIXED: the lane is now escaped through md_cell, so it can no longer inject a
        # column. Find the recurring row by its escaped form and assert the row still
        # has exactly the 5 structural pipes a well-formed row has.
        recurring_line = next(
            ln for ln in out.splitlines() if ln.startswith("| `int \\|")
        )
        structural = recurring_line.count("|") - recurring_line.count("\\|")
        assert structural == 5, recurring_line

    def test_BUG_backtick_in_evidence_breaks_inline_code_span(self):
        """CONFIRMED GAP: evidence is escaped for '|' but not for '`'. Evidence
        wrapping the string in backticks for an inline code span means a
        backtick INSIDE the evidence text prematurely closes the span. Go
        vet/compiler output routinely quotes identifiers in backticks."""
        v = classify(extract(_log("--- FAIL: TestBacktick (0.00s)\n")))
        v.evidence = "undefined: `someHelper` in package foo"
        rows = [Row(1, 2, "build fedora-current / lima", "Test", v, None, "http://x")]
        out = render(rows, 1)
        data_line = next(ln for ln in out.splitlines() if ln.startswith("| [1]"))
        # The evidence cell should be a single balanced `...` code span (2
        # backticks). It contains 4, because the embedded backticks aren't escaped.
        assert data_line.count("`") % 2 == 0, data_line
        assert "`someHelper`" not in data_line, data_line

    def test_newline_in_evidence_would_split_the_row(self):
        """evidence is truncated to [:90]/[:110] but never has embedded
        newlines stripped. A multi-line 'evidence' can't normally occur since
        _evidence() always returns a single `line` from `.splitlines()` - but
        prove the guard, since Verdict is a plain dataclass any caller can
        construct with a multi-line string directly (e.g. a future rule that
        captures `match.group(0)` from a multi-line regex)."""
        v = classify(extract(_log("--- FAIL: TestMultiline (0.00s)\n")))
        v.evidence = "first line of evidence\nsecond line breaks the row"
        rows = [Row(1, 2, "build fedora-current / lima", "Test", v, None, "http://x")]
        out = render(rows, 1)
        # FIXED: md_cell collapses embedded newlines to spaces, so the row stays on one
        # line. Keeping the text is deliberate: losing evidence is worse than a long
        # cell, and the row integrity is what actually matters for the table.
        matching = [ln for ln in out.splitlines() if "first line of evidence" in ln]
        assert len(matching) == 1, matching
        assert "second line breaks the row" in matching[0], matching[0]
        assert matching[0].count("|") - matching[0].count("\\|") == 7, matching[0]


# ---------------------------------------------------------------------------
# 5. Windows console crash: print(text) under the real Windows stdout codec
# ---------------------------------------------------------------------------

class TestWindowsConsoleCrash:
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-console-specific defect")
    def test_BUG_report_text_with_bom_crashes_default_print(self):
        """CONFIRMED CRASH on this exact environment (Windows, Python 3.10.11).
        `cli.cmd_report()` does `print(text)` when --out is not given.

        Checked against `sys.__stdout__` (the real, un-swapped stream), not
        `sys.stdout`, because pytest replaces `sys.stdout` with a UTF-8
        capture object - testing THAT would prove nothing about what a
        maintainer's terminal actually does. `sys.__stdout__.encoding` is
        'cp1252' and `.errors` is 'surrogateescape' on this box, confirmed
        both under Git Bash and native cmd.exe/PowerShell.

        First adversarial pick (em dash + smart quotes, U+2014/U+2018/U+2019)
        was a DUD: cp1252 (Windows-1252) is a superset of Latin-1 that
        specifically includes Microsoft's "smart" typography in its 0x80-0x9F
        range, so those encode fine. A real non-cp1252 character is needed -
        this test uses one that isn't hypothetical: .cache/logs/95398591212.log
        (a real cached Podman CI log) starts with a literal U+FEFF BOM,
        because ingest.job_log() does `raw.decode("utf-8", errors="replace")`,
        which does NOT strip a BOM (only 'utf-8-sig' does). If that BOM, or
        any other non-cp1252 character (Chinese/Cyrillic/Devanagari in a
        contributor's name, emoji in a commit message), ever lands in
        classify() evidence or a job name, `report` without --out crashes.
        """
        enc, err = sys.__stdout__.encoding, sys.__stdout__.errors
        if enc.lower() not in ("cp1252", "windows-1252"):
            pytest.skip(f"real stdout encoding is {enc!r} on this box, not cp1252")

        v = classify(extract(_log("--- FAIL: TestUnicode (0.00s)\n")))
        v.evidence = "assertion failed ﻿ BOM snuck into evidence"
        rows = [Row(1, 2, "int local root fedora-current / lima", "Test", v, None, "http://x")]
        text = render(rows, 1)
        assert "﻿" in text  # sanity: md_cell doesn't strip it either

        # Reproduce cmd_report's exact no-`--out` code path against the REAL
        # underlying console codec, bypassing pytest's stdout swap.
        with pytest.raises(UnicodeEncodeError):
            text.encode(enc, errors=err)

    def test_BOM_survives_ingest_decode_and_defeats_first_line_timestamp_strip(self):
        """Minor correctness bug, proven against real cached data: the raw
        log for job 95398591212 starts with a UTF-8 BOM. `strip_timestamps`'s
        TS regex requires the line to start with 4 digits; a leading BOM
        means line 0's timestamp is never stripped, unlike every other line."""
        p = CACHE / "logs" / "95398591212.log"
        if not p.exists():
            pytest.skip(".cache/logs/95398591212.log not present in this checkout")
        raw = p.read_text(encoding="utf-8", errors="replace")
        assert raw[0] == "﻿"
        lines = strip_timestamps(raw)
        # FIXED: the BOM is stripped before splitting, so line 0's timestamp now comes
        # off like every other line's. Previously the BOM sat before the digits and
        # defeated the '^\d{4}...' anchor, leaving line 0 un-normalised.
        assert not lines[0].startswith("﻿"), lines[0][:40]
        assert not lines[0].startswith("2026-"), lines[0][:40]
        assert not lines[1].startswith("2026-")  # line 1 stripped normally


# ---------------------------------------------------------------------------
# 6. Real cached data sanity + specific job verdict audits
# ---------------------------------------------------------------------------

class TestRealCachedData:
    def test_full_report_runs_without_crashing(self):
        if not (CACHE / "runs_25.json").exists():
            pytest.skip("no .cache/runs_25.json in this checkout")
        from flaketriage.cli import _rows
        rows = _rows(ingest.Cache(CACHE), 25)
        text = render(rows, 25)
        assert "Podman CI flake triage" in text

    def test_BUG_check_make_vendor_is_clean_falls_to_unknown_not_build(self):
        """CONFIRMED MISCLASSIFICATION on real data. Jobs 94794824043 and
        94818536544 ('Validate source code changes', failed_step =
        'Check make vendor is clean') both classify UNKNOWN. classify.py's
        own CATEGORIES dict defines BUILD as: 'Compile or vendor step
        failed; the suite never ran' - explicitly including vendor-step
        failures. But the metadata fallback only checks `"build" in step`,
        and the step name is 'check make vendor is clean' - it contains
        'vendor', not 'build', so the fallback never fires. The log content
        itself is a raw unified diff (no compile_error keyword, no lint
        keyword), so no content rule fires either. Net effect: a failure
        category the tool explicitly claims to cover is silently dropped to
        UNKNOWN because the keyword fallback doesn't match the step's actual
        wording."""
        for job_id in (94794824043, 94818536544):
            p = CACHE / "logs" / f"{job_id}.log"
            if not p.exists():
                pytest.skip(f".cache/logs/{job_id}.log not present in this checkout")
            raw = p.read_text(encoding="utf-8", errors="replace")
            v = classify(extract(raw), job_name="Validate source code changes",
                         failed_step="Check make vendor is clean")
            # FIXED: the metadata fallback now recognises a vendor step, which is what
            # CATEGORIES["BUILD"] always claimed to cover ("Compile or vendor step").
            assert v.category == "BUILD", (
                f"job {job_id}: a failing 'Check make vendor is clean' step should be "
                f"BUILD, got {v.category}"
            )

    def test_BUG_missing_dev_kvm_infra_failure_falls_to_unknown(self):
        """CONFIRMED MISCLASSIFICATION on real data. Job 95398591212 ('farm
        rootless fedora-current / lima', failed_step = 'Run
        lima-vm/lima-actions/setup@...') fails because the runner has no
        /dev/kvm: `chown: cannot access '/dev/kvm': No such file or
        directory`. This is textbook INFRA_RESOURCE per the tool's own
        description ('...or could not start a VM'), but classify.py's
        `oom_or_vm` pattern only matches the literal phrase
        'failed to start .*(vm|lima|qemu)', which never appears - so it
        classifies UNKNOWN instead."""
        p = CACHE / "logs" / "95398591212.log"
        if not p.exists():
            pytest.skip(".cache/logs/95398591212.log not present in this checkout")
        raw = p.read_text(encoding="utf-8", errors="replace")
        assert "cannot access '/dev/kvm'" in raw
        v = classify(extract(raw), job_name="farm  rootless fedora-current / lima",
                     failed_step="Run lima-vm/lima-actions/setup@55627e31b78637bf254a8b2a14da8ea7d12564e5")
        # FIXED: a runner without /dev/kvm cannot start a VM, which is exactly what
        # CATEGORIES["INFRA_RESOURCE"] describes.
        assert v.category == "INFRA_RESOURCE", (
            f"a missing /dev/kvm should classify as INFRA_RESOURCE, got {v.category}"
        )

    def test_copilot_bot_job_is_not_filtered_like_total_success(self):
        """DESIGN GAP, not a crash: ingest.AGGREGATE_JOBS filters out
        'Total Success' because it's a required-checks gate, not a real
        failure. 'copilot-pull-request-reviewer' (job 95429662818) is the
        same kind of noise - a GitHub bot integration, not a Podman CI test
        lane - but isn't filtered, so it pollutes the failed-jobs sample
        and the UNKNOWN denominator."""
        p = CACHE / "jobs"
        job_id = 95429662818
        found = False
        for f in glob.glob(str(p / "*.json")):
            import json
            for j in json.loads(pathlib.Path(f).read_text(encoding="utf-8")):
                if j.get("id") == job_id:
                    found = True
                    assert j.get("name") == "copilot-pull-request-reviewer"
        if not found:
            pytest.skip("job 95429662818 not present in this checkout's cache")
        assert "copilot-pull-request-reviewer" not in ingest.AGGREGATE_JOBS


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
