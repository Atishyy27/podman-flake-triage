"""The interesting cases are the ones a naive `grep -i error` gets wrong."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from flaketriage.classify import classify
from flaketriage.extract import extract, strip_timestamps


def _log(body: str) -> str:
    return "\n".join(f"2026-08-17T21:16:16.1706218Z {ln}" for ln in body.splitlines())


def test_strips_github_timestamps():
    assert strip_timestamps(_log("hello"))[0] == "hello"


def test_incidental_errors_do_not_beat_the_real_failure():
    # Podman e2e tests deliberately provoke errors and assert on them. A grep-based
    # classifier reads the first 'Error:' and calls this a network flake. It is not:
    # the harness says a test assertion failed.
    body = _log(
        "Error: no such container foo\n"
        "Error: unable to connect to registry: dial tcp 1.2.3.4:443: i/o timeout\n"
        "ok 12 podman run\n"
        "Summarizing 1 Failure:\n"
        "  [FAIL] Podman run [It] should honor --memory\n"
    )
    v = classify(extract(body))
    assert v.category == "TEST_FAILURE", v


def test_real_network_flake_is_caught():
    body = _log(
        "Trying to pull quay.io/libpod/alpine:latest...\n"
        "Error: pinging container registry quay.io: Get \"https://quay.io/v2/\": "
        "dial tcp 3.4.5.6:443: i/o timeout\n"
        "##[error]Process completed with exit code 125\n"
    )
    v = classify(extract(body))
    assert v.category == "INFRA_NETWORK", v
    assert "i/o timeout" in v.evidence


def test_disk_exhaustion():
    body = _log("write /var/tmp/x: no space left on device\n"
                "##[error]Process completed with exit code 1\n")
    assert classify(extract(body)).category == "INFRA_RESOURCE"


def test_go_test_failure():
    body = _log("--- FAIL: TestParseEnv (0.00s)\n    env_test.go:41: got 1 want 2\n")
    assert classify(extract(body)).category == "TEST_FAILURE"


def test_unknown_is_admitted_not_guessed():
    body = _log("some output nobody wrote a rule for yet\n")
    v = classify(extract(body))
    assert v.category == "UNKNOWN"
    assert v.rule == "no_rule_matched"


def test_extract_anchors_on_marker_not_tail():
    body = _log("Summarizing 1 Failure:\n  [FAIL] x\n" + "noise\n" * 400)
    assert extract(body).marker == "ginkgo_summary"


def test_empty_log_is_not_a_crash():
    assert classify(extract("")).category == "UNKNOWN"
