# Podman CI flake triage

Sampled the **8** most recent failed workflow runs in `podman-container-tools/podman`, yielding **11** failed jobs (the `Total Success` required-checks gate is excluded, it is an aggregate and not a real failure).


## Failures by mechanism

| Category | Count | Share | What it means |
|---|---:|---:|---|
| `TEST_FAILURE` | 8 | 73% | A test asserted and the assertion did not hold |
| `LINT` | 2 | 18% | Static analysis, formatting, or validation gate |
| `UNKNOWN` | 1 | 9% | No rule matched; needs a human |

`UNKNOWN` is 9% of the sample. That number is the honest measure of how far the rules go; every entry in it is a rule that has not been written yet, not a failure that has been explained.


## Recurring: same lane, same mechanism, more than once

| Job lane | Mechanism | Times | Example evidence |
|---|---|---:|---|
| `int local rootless` | `TEST_FAILURE` | 2 | `[FAIL] Podman run memory [It] podman run memory test on oomkilled container` |
| `sys local rootless` | `TEST_FAILURE` | 2 | `not ok 317 \|450\| podman detects correct tty size in 2846ms` |
| `Validate source code` | `LINT` | 2 | `##[error]pkg/domain/infra/abi/images.go:29:1: File is not properly formatted (gofumpt)` |

These are the quarantine candidates. A lane that fails the same way repeatedly across unrelated PRs is not being broken by those PRs.


## Every classified failure

| Run | Job | Mechanism | Rule | Confidence | Evidence |
|---|---|---|---|---|---|
| [32064420161](https://github.com/podman-container-tools/podman/actions/runs/32064420161/job/95492950874) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `##[error]pkg/domain/infra/abi/images.go:29:1: File is not properly formatted (gofumpt)` |
| [32049160036](https://github.com/podman-container-tools/podman/actions/runs/32049160036/job/95444081716) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `##[error]cmd/rootlessport/main.go:300:4: The copy of the 'for' variable "protocol" can be ` |
| [32065520074](https://github.com/podman-container-tools/podman/actions/runs/32065520074/job/95499929634) | `int local root fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman rmi [It] podman image rm - concurrent with shared layers` |
| [32064146201](https://github.com/podman-container-tools/podman/actions/runs/32064146201/job/95495973174) | `int local rootless debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run networking [It] podman run bridge network same port different HostIPs ro` |
| [32067619067](https://github.com/podman-container-tools/podman/actions/runs/32067619067/job/95506772433) | `int local rootless fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run memory [It] podman run memory test on oomkilled container` |
| [32066350407](https://github.com/podman-container-tools/podman/actions/runs/32066350407/job/95503029568) | `macos machine applehv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine rm [It] Remove running machine` |
| [32053009523](https://github.com/podman-container-tools/podman/actions/runs/32053009523/job/95459823136) | `sys local root fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 434 \|610\| check Go template formatting in 61625ms` |
| [32065520074](https://github.com/podman-container-tools/podman/actions/runs/32065520074/job/95499929625) | `sys local rootless debian-sid / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 317 \|450\| podman detects correct tty size in 2846ms` |
| [32064146201](https://github.com/podman-container-tools/podman/actions/runs/32064146201/job/95495972930) | `sys local rootless fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 212 \|220\| podman healthcheck in 8534ms` |
| [32066350407](https://github.com/podman-container-tools/podman/actions/runs/32066350407/job/95503029355) | `windows machine hyperv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine set [It] set machine cpus, disk, memory` |
| [32044569797](https://github.com/podman-container-tools/podman/actions/runs/32044569797/job/95429662818) | `copilot-pull-request-reviewer` | `UNKNOWN` | `no_rule_matched` | low | `` |
