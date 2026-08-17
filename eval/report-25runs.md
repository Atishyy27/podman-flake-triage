# Podman CI flake triage

Sampled the **25** most recent failed workflow runs in `podman-container-tools/podman`, yielding **42** failed jobs (the `Total Success` required-checks gate is excluded, it is an aggregate and not a real failure).


## Failures by mechanism

| Category | Count | Share | What it means |
|---|---:|---:|---|
| `TEST_FAILURE` | 29 | 69% | A test asserted and the assertion did not hold |
| `UNKNOWN` | 5 | 12% | No rule matched; needs a human |
| `BUILD` | 5 | 12% | Compile or vendor step failed; the suite never ran |
| `LINT` | 2 | 5% | Static analysis, formatting, or validation gate |
| `TIMEOUT_HANG` | 1 | 2% | Job or test exceeded its time budget |

`UNKNOWN` is 12% of the sample. That number is the honest measure of how far the rules go; every entry in it is a rule that has not been written yet, not a failure that has been explained.


## Recurring: same lane, same mechanism, more than once

| Job lane | Mechanism | Times | Example evidence |
|---|---|---:|---|
| `int local root` | `TEST_FAILURE` | 7 | `[FAIL] Podman rmi [It] podman image rm - concurrent with shared layers` |
| `sys remote root` | `TEST_FAILURE` | 5 | `not ok 317 \|450\| podman detects correct tty size in 3313ms` |
| `int local rootless` | `TEST_FAILURE` | 3 | `[FAIL] Podman run memory [It] podman run memory test on oomkilled container` |
| `macos machine applehv` | `TEST_FAILURE` | 3 | `[FAIL] podman machine rm [It] Remove running machine` |
| `sys local rootless` | `TEST_FAILURE` | 3 | `not ok 317 \|450\| podman detects correct tty size in 2846ms` |
| `build fedora-current` | `BUILD` | 3 | `failed step: Run test on lima` |
| `Validate source code` | `LINT` | 2 | `##[error]pkg/domain/infra/abi/images.go:29:1: File is not properly formatted (gofumpt)` |
| `Validate source code` | `UNKNOWN` | 2 | `` |

These are the quarantine candidates. A lane that fails the same way repeatedly across unrelated PRs is not being broken by those PRs.


## Every classified failure

| Run | Job | Mechanism | Rule | Confidence | Evidence |
|---|---|---|---|---|---|
| [31975812388](https://github.com/podman-container-tools/podman/actions/runs/31975812388/job/95363694196) | `build fedora-current / lima` | `BUILD` | `step_name_build` | low | `failed step: Run test on lima` |
| [31833900347](https://github.com/podman-container-tools/podman/actions/runs/31833900347/job/95361225942) | `build fedora-current / lima` | `BUILD` | `step_name_build` | low | `failed step: Run test on lima` |
| [31830148124](https://github.com/podman-container-tools/podman/actions/runs/31830148124/job/94863630984) | `build fedora-current / lima` | `BUILD` | `step_name_build` | low | `failed step: Run test on lima` |
| [31869969647](https://github.com/podman-container-tools/podman/actions/runs/31869969647/job/94976976480) | `windows installer hyperv` | `BUILD` | `step_name_build` | low | `failed step: Build docs` |
| [31869969647](https://github.com/podman-container-tools/podman/actions/runs/31869969647/job/94976976446) | `windows installer wsl` | `BUILD` | `step_name_build` | low | `failed step: Build docs` |
| [32064420161](https://github.com/podman-container-tools/podman/actions/runs/32064420161/job/95492950874) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `##[error]pkg/domain/infra/abi/images.go:29:1: File is not properly formatted (gofumpt)` |
| [32049160036](https://github.com/podman-container-tools/podman/actions/runs/32049160036/job/95444081716) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `##[error]cmd/rootlessport/main.go:300:4: The copy of the 'for' variable "protocol" can be ` |
| [31879825400](https://github.com/podman-container-tools/podman/actions/runs/31879825400/job/95000741570) | `Validate source code changes` | `TEST_FAILURE` | `bats_failure` | high | `not ok 3 PR 8685 - multiple commits, no tests` |
| [31869923347](https://github.com/podman-container-tools/podman/actions/runs/31869923347/job/95348083456) | `apiv2 rootless fedora-current / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 1347 [26-containersWait] POST containers/WaitTestingCtr/wait?condition=next-exit [-` |
| [31821911636](https://github.com/podman-container-tools/podman/actions/runs/31821911636/job/94840717454) | `bud local root fedora-current / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 486 bud with --raw-iidfile alias` |
| [31821911636](https://github.com/podman-container-tools/podman/actions/runs/31821911636/job/94840717740) | `bud remote root fedora-current / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 486 bud with --raw-iidfile alias` |
| [31954250080](https://github.com/podman-container-tools/podman/actions/runs/31954250080/job/95342989730) | `int local root debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman container interface name [It] podman container interface name with default s` |
| [31954250080](https://github.com/podman-container-tools/podman/actions/runs/31954250080/job/95342990186) | `int local root fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman volume plugins [It] remove plugin with stopped plugin succeeds` |
| [31954250080](https://github.com/podman-container-tools/podman/actions/runs/31954250080/job/95342989696) | `int local root fedora-prior / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman volume plugins [It] remove plugin with stopped plugin succeeds` |
| [31813098642](https://github.com/podman-container-tools/podman/actions/runs/31813098642/job/94812362325) | `int local root fedora-prior / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run networking [It] podman run network connection with default bridge` |
| [32065520074](https://github.com/podman-container-tools/podman/actions/runs/32065520074/job/95499929634) | `int local root fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman rmi [It] podman image rm - concurrent with shared layers` |
| [32032269509](https://github.com/podman-container-tools/podman/actions/runs/32032269509/job/95397793390) | `int local root fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman rmi [It] podman image rm - concurrent with shared layers` |
| [31954250080](https://github.com/podman-container-tools/podman/actions/runs/31954250080/job/95342989588) | `int local root fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman volume plugins [It] remove plugin with stopped plugin succeeds` |
| [32064146201](https://github.com/podman-container-tools/podman/actions/runs/32064146201/job/95495973174) | `int local rootless debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run networking [It] podman run bridge network same port different HostIPs ro` |
| [32067619067](https://github.com/podman-container-tools/podman/actions/runs/32067619067/job/95506772433) | `int local rootless fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run memory [It] podman run memory test on oomkilled container` |
| [31813098642](https://github.com/podman-container-tools/podman/actions/runs/31813098642/job/94812361968) | `int local rootless fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run networking [It] podman run network connection with host` |
| [32066350407](https://github.com/podman-container-tools/podman/actions/runs/32066350407/job/95503029568) | `macos machine applehv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine rm [It] Remove running machine` |
| [32032269509](https://github.com/podman-container-tools/podman/actions/runs/32032269509/job/95397791321) | `macos machine applehv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine set [It] set while machine already running` |
| [31911449880](https://github.com/podman-container-tools/podman/actions/runs/31911449880/job/95398590155) | `macos machine applehv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine ssh [It] verify machine rootfulness` |
| [32023775922](https://github.com/podman-container-tools/podman/actions/runs/32023775922/job/95372062768) | `macos machine libkrun` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine init [DeferCleanup (Each)] machine init with volume` |
| [32053009523](https://github.com/podman-container-tools/podman/actions/runs/32053009523/job/95459823136) | `sys local root fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 434 \|610\| check Go template formatting in 61625ms` |
| [32065520074](https://github.com/podman-container-tools/podman/actions/runs/32065520074/job/95499929625) | `sys local rootless debian-sid / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 317 \|450\| podman detects correct tty size in 2846ms` |
| [32032269509](https://github.com/podman-container-tools/podman/actions/runs/32032269509/job/95397793259) | `sys local rootless fedora-prior / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 93 \|035\| podman logs - --until --follow journald in 7638ms` |
| [32064146201](https://github.com/podman-container-tools/podman/actions/runs/32064146201/job/95495972930) | `sys local rootless fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 212 \|220\| podman healthcheck in 8534ms` |
| [31821754525](https://github.com/podman-container-tools/podman/actions/runs/31821754525/job/94843947061) | `sys remote root debian-sid / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 51 [032] podman sigproxy test: exec in 12957ms` |
| [31821754525](https://github.com/podman-container-tools/podman/actions/runs/31821754525/job/94843947000) | `sys remote root fedora-current / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 51 [032] podman sigproxy test: exec in 13271ms` |
| [31821754525](https://github.com/podman-container-tools/podman/actions/runs/31821754525/job/94843946834) | `sys remote root fedora-prior / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 51 [032] podman sigproxy test: exec in 13077ms` |
| [31970389202](https://github.com/podman-container-tools/podman/actions/runs/31970389202/job/95363052438) | `sys remote root fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 317 \|450\| podman detects correct tty size in 3313ms` |
| [31821754525](https://github.com/podman-container-tools/podman/actions/runs/31821754525/job/94843947126) | `sys remote root fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 51 [032] podman sigproxy test: exec in 12786ms` |
| [31821754525](https://github.com/podman-container-tools/podman/actions/runs/31821754525/job/94843946950) | `sys remote rootless fedora-current / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 51 [032] podman sigproxy test: exec in 12855ms` |
| [32066350407](https://github.com/podman-container-tools/podman/actions/runs/32066350407/job/95503029355) | `windows machine hyperv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine set [It] set machine cpus, disk, memory` |
| [32032269509](https://github.com/podman-container-tools/podman/actions/runs/32032269509/job/95397791367) | `macos machine libkrun` | `TIMEOUT_HANG` | `timeout` | medium | `##[error]The operation was canceled.` |
| [31816252486](https://github.com/podman-container-tools/podman/actions/runs/31816252486/job/94818536544) | `Validate source code changes` | `UNKNOWN` | `no_rule_matched` | low | `` |
| [31809018650](https://github.com/podman-container-tools/podman/actions/runs/31809018650/job/94794824043) | `Validate source code changes` | `UNKNOWN` | `no_rule_matched` | low | `` |
| [32044569797](https://github.com/podman-container-tools/podman/actions/runs/32044569797/job/95429662818) | `copilot-pull-request-reviewer` | `UNKNOWN` | `no_rule_matched` | low | `` |
| [31911449880](https://github.com/podman-container-tools/podman/actions/runs/31911449880/job/95398591212) | `farm rootless fedora-current / lima` | `UNKNOWN` | `no_rule_matched` | low | `` |
| [32025596823](https://github.com/podman-container-tools/podman/actions/runs/32025596823/job/95393218275) | `sys local rootless fedora-rawhide / lima` | `UNKNOWN` | `no_rule_matched` | low | `` |
