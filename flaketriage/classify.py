"""Assign a failure mechanism to an extracted log excerpt.

Every rule returns the line that fired it. A category on its own is an assertion; a
category plus the line it came from is something a maintainer can check in two seconds
and disagree with. That distinction is the whole design.

Ordering matters. Rules are evaluated most-specific first, because an infra failure and
a test failure can both leave network-shaped text in the same log, and the one the
harness actually died on is the one that counts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .extract import Excerpt


@dataclass
class Verdict:
    category: str
    evidence: str
    """The exact log line that triggered the classification."""
    rule: str
    confidence: str  # high | medium | low


CATEGORIES = {
    "INFRA_NETWORK": "Registry, DNS or transport failure outside the code under test",
    "INFRA_RESOURCE": "Runner ran out of disk, memory, or could not start a VM",
    "BUILD": "Compile or vendor step failed; the suite never ran",
    "LINT": "Static analysis, formatting, or validation gate",
    "TEST_FAILURE": "A test asserted and the assertion did not hold",
    "TIMEOUT_HANG": "Job or test exceeded its time budget",
    "UNKNOWN": "No rule matched; needs a human",
}

# (category, rule name, pattern, confidence)
RULES: list[tuple[str, str, re.Pattern[str], str]] = [
    (
        "INFRA_NETWORK",
        "registry_unreachable",
        re.compile(
            r"(dial tcp .*(i/o timeout|connection refused))"
            r"|(TLS handshake timeout)"
            r"|(no such host)"
            r"|(temporary failure in name resolution)"
            r"|(error pinging docker registry)"
            r"|(Get \"https://[^\"]+\": .*timeout)",
            re.I,
        ),
        "high",
    ),
    (
        "INFRA_NETWORK",
        "registry_rate_limit",
        re.compile(r"(toomanyrequests)|(rate limit|429 Too Many Requests)", re.I),
        "high",
    ),
    (
        "INFRA_RESOURCE",
        "out_of_space",
        re.compile(r"(no space left on device)|(disk quota exceeded)", re.I),
        "high",
    ),
    (
        "INFRA_RESOURCE",
        "oom_or_vm",
        re.compile(
            r"(out of memory)|(Cannot allocate memory)|(oom-kill)"
            r"|(failed to start .*(vm|lima|qemu))"
            r"|(cannot access '/dev/kvm')|(/dev/kvm.*no such file)",
            re.I,
        ),
        "high",
    ),
    (
        "TIMEOUT_HANG",
        "timeout",
        re.compile(
            r"(The (job|operation) (was canceled|has timed out))"
            r"|(context deadline exceeded)"
            r"|(panic: test timed out)"
            r"|(Timed out after [\d.]+s)",
            re.I,
        ),
        "medium",
    ),
    (
        "LINT",
        "validation_gate",
        re.compile(
            r"(golangci-lint)|(gofmt -l)|(Please run .*make validate)"
            r"|(^\s*ERROR: .*lint)|(codespell)",
            re.I | re.M,
        ),
        "medium",
    ),
    (
        "BUILD",
        "compile_error",
        re.compile(
            r"(^# github\.com/containers/podman)"
            r"|(undefined: )|(cannot find package)"
            r"|(build constraints exclude all Go files)"
            r"|(vendor/modules\.txt.*inconsistent)",
            re.M,
        ),
        "high",
    ),
    (
        "TEST_FAILURE",
        "ginkgo_failure",
        re.compile(r"(^\s*\[FAIL\])|(^Summarizing \d+ Failure)", re.M),
        "high",
    ),
    (
        "TEST_FAILURE",
        "go_test_failure",
        re.compile(r"^--- FAIL: ", re.M),
        "high",
    ),
    (
        "TEST_FAILURE",
        "bats_failure",
        re.compile(r"^not ok \d+ ", re.M),
        "high",
    ),
]


# For some rules the line that MATCHES is not the line worth showing. "Summarizing 1
# Failure:" proves a test failed but does not say which; the "[FAIL] ..." line below it
# names the test. Where a rule has a better evidence line available, prefer it.
PREFERRED_EVIDENCE: dict[str, re.Pattern[str]] = {
    "ginkgo_failure": re.compile(r"^\s*\[FAIL\]\s*(.+)$", re.M),
    "validation_gate": re.compile(
        r"^.*?(\.go:\d+:\d+:.*|Please run .*|^\s*ERROR:.*)$", re.M
    ),
    "compile_error": re.compile(r"^.*(undefined: |cannot find package|\.go:\d+:\d+:).*$", re.M),
}


def _evidence(lines: list[str], body: str, pattern: re.Pattern[str], rule: str) -> str:
    better = PREFERRED_EVIDENCE.get(rule)
    if better:
        for line in lines:
            m = better.search(line)
            if m:
                return line.strip()[:300]
    for line in lines:
        if pattern.search(line):
            return line.strip()[:300]
    match = pattern.search(body)
    return match.group(0).strip()[:300] if match else ""


def classify(excerpt: Excerpt, job_name: str = "", failed_step: str = "") -> Verdict:
    if not excerpt.text.strip():
        return Verdict("UNKNOWN", "", "empty_log", "low")

    # When a test harness printed its own verdict, only the block from that verdict
    # onward describes this failure. Everything above it belongs to earlier tests, many
    # of which deliberately provoke errors and assert on them. Scanning the whole
    # excerpt is how a classifier ends up calling a real assertion failure a network
    # flake, which is the single most common way this kind of tool goes wrong.
    scan = excerpt.focus if excerpt.harness_verdict else excerpt.text
    scan_lines = excerpt.focus_lines if excerpt.harness_verdict else excerpt.lines

    for category, rule, pattern, confidence in RULES:
        if pattern.search(scan):
            return Verdict(
                category, _evidence(scan_lines, scan, pattern, rule), rule, confidence
            )

    # Job metadata is a weaker signal than the log, so it only gets consulted when no
    # log rule fired at all.
    step = (failed_step or "").lower()
    name = (job_name or "").lower()
    if "build" in step or "vendor" in step or name.startswith("build "):
        return Verdict("BUILD", f"failed step: {failed_step}", "step_name_build", "low")
    if "validate" in step or "lint" in name:
        return Verdict("LINT", f"failed step: {failed_step}", "step_name_lint", "low")

    return Verdict("UNKNOWN", "", "no_rule_matched", "low")
