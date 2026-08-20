# Podman CI flake triage

Sampled the **50** most recent failed workflow runs in `podman-container-tools/podman`, yielding **106** failed jobs (the `Total Success` required-checks gate is excluded, it is an aggregate and not a real failure).


## Failures by mechanism

| Category | Count | Share | What it means |
|---|---:|---:|---|
| `TEST_FAILURE` | 70 | 66% | A test asserted and the assertion did not hold |
| `BUILD` | 20 | 19% | Compile or vendor step failed; the suite never ran |
| `LINT` | 10 | 9% | Static analysis, formatting, or validation gate |
| `UNKNOWN` | 4 | 4% | No rule matched; needs a human |
| `TIMEOUT_HANG` | 1 | 1% | Job or test exceeded its time budget |
| `INFRA_RESOURCE` | 1 | 1% | Runner ran out of disk, memory, or could not start a VM |

`UNKNOWN` is 4% of the sample. That number is the honest measure of how far the rules go; every entry in it is a rule that has not been written yet, not a failure that has been explained.


## Recurring: same lane, same mechanism, more than once

| Job lane | Mechanism | Times | Example evidence |
|---|---|---:|---|
| `int local root` | `TEST_FAILURE` | 16 | `[FAIL] Podman artifact [It] podman artifact ls` |
| `Validate source code` | `LINT` | 10 | `##[error]libpod/container_internal_common.go:345:5: SA1019: (go.podman.io/buildah/pkg/overlay.Options).RootGID` |
| `int remote root` | `TEST_FAILURE` | 10 | `[FAIL] Podman run networking [It] podman run container with two static IPs one per subnet` |
| `int local rootless` | `TEST_FAILURE` | 10 | `[FAIL] Podman artifact [It] podman artifact ls` |
| `build fedora-current` | `BUILD` | 8 | `pkg/api/handlers/compat/exec.go:29:24: undefined: handlers.ExecCreateConfigJSON` |
| `macos machine applehv` | `TEST_FAILURE` | 6 | `[FAIL] podman machine init [It] machine init with swap` |
| `sys remote root` | `TEST_FAILURE` | 6 | `not ok 317 \|450\| podman detects correct tty size in 3313ms` |
| `Validate source code` | `BUILD` | 4 | `failed step: Check make vendor is clean` |
| `sys local root` | `TEST_FAILURE` | 4 | `not ok 127 \|065\| podman cp file from container to container in 2752ms` |
| `windows machine hyperv` | `TEST_FAILURE` | 4 | `[FAIL] podman machine start [It] start simple machine` |
| `sys local rootless` | `TEST_FAILURE` | 3 | `not ok 93 \|035\| podman logs - --until --follow journald in 7638ms` |
| `build fedora-rawhide` | `BUILD` | 2 | `failed step: Run test on lima` |
| `int remote rootless` | `TEST_FAILURE` | 2 | `[FAIL] Podman artifact [It] podman artifact ls` |
| `apiv2 rootless fedora-current` | `TEST_FAILURE` | 2 | `not ok 1347 [26-containersWait] POST containers/WaitTestingCtr/wait?condition=next-exit [-d {}] : status` |
| `macos machine libkrun` | `TEST_FAILURE` | 2 | `[FAIL] podman machine set [It] set machine cpus, disk, memory` |

These are the quarantine candidates. A lane that fails the same way repeatedly across unrelated PRs is not being broken by those PRs.


## Every classified failure

| Run | Job | Mechanism | Rule | Confidence | Evidence |
|---|---|---|---|---|---|
| [32282109382](https://github.com/podman-container-tools/podman/actions/runs/32282109382/job/96165940244) | `Cross Build (Linux, FreeBSD)` | `BUILD` | `compile_error` | high | `##[error]pkg/api/handlers/compat/exec.go:29:24: undefined: handlers.ExecCreateConfigJSON` |
| [32362185353](https://github.com/podman-container-tools/podman/actions/runs/32362185353/job/96403925329) | `Validate source code changes` | `BUILD` | `step_name_build` | low | `failed step: Check make vendor is clean` |
| [32144725978](https://github.com/podman-container-tools/podman/actions/runs/32144725978/job/95741504058) | `Validate source code changes` | `BUILD` | `step_name_build` | low | `failed step: Build each commit` |
| [31816252486](https://github.com/podman-container-tools/podman/actions/runs/31816252486/job/94818536544) | `Validate source code changes` | `BUILD` | `step_name_build` | low | `failed step: Check make vendor is clean` |
| [31809018650](https://github.com/podman-container-tools/podman/actions/runs/31809018650/job/94794824043) | `Validate source code changes` | `BUILD` | `step_name_build` | low | `failed step: Check make vendor is clean` |
| [32282109382](https://github.com/podman-container-tools/podman/actions/runs/32282109382/job/96165940892) | `build debian-sid / lima` | `BUILD` | `compile_error` | high | `pkg/api/handlers/compat/exec.go:29:24: undefined: handlers.ExecCreateConfigJSON` |
| [32282109382](https://github.com/podman-container-tools/podman/actions/runs/32282109382/job/96165940801) | `build fedora-current / lima` | `BUILD` | `compile_error` | high | `pkg/api/handlers/compat/exec.go:29:24: undefined: handlers.ExecCreateConfigJSON` |
| [32144725978](https://github.com/podman-container-tools/podman/actions/runs/32144725978/job/95741504341) | `build fedora-current / lima` | `BUILD` | `step_name_build` | low | `failed step: Run test on lima` |
| [32081246176](https://github.com/podman-container-tools/podman/actions/runs/32081246176/job/95661599015) | `build fedora-current / lima` | `BUILD` | `step_name_build` | low | `failed step: Run test on lima` |
| [31975812388](https://github.com/podman-container-tools/podman/actions/runs/31975812388/job/95363694196) | `build fedora-current / lima` | `BUILD` | `step_name_build` | low | `failed step: Run test on lima` |
| [31833900347](https://github.com/podman-container-tools/podman/actions/runs/31833900347/job/95361225942) | `build fedora-current / lima` | `BUILD` | `step_name_build` | low | `failed step: Run test on lima` |
| [31830148124](https://github.com/podman-container-tools/podman/actions/runs/31830148124/job/94863630984) | `build fedora-current / lima` | `BUILD` | `step_name_build` | low | `failed step: Run test on lima` |
| [31806148561](https://github.com/podman-container-tools/podman/actions/runs/31806148561/job/94785440071) | `build fedora-current / lima` | `BUILD` | `step_name_build` | low | `failed step: Run test on lima` |
| [31802052979](https://github.com/podman-container-tools/podman/actions/runs/31802052979/job/94772167056) | `build fedora-current / lima` | `BUILD` | `step_name_build` | low | `failed step: Run test on lima` |
| [32282109382](https://github.com/podman-container-tools/podman/actions/runs/32282109382/job/96165940496) | `build fedora-prior / lima` | `BUILD` | `compile_error` | high | `pkg/api/handlers/compat/exec.go:29:24: undefined: handlers.ExecCreateConfigJSON` |
| [32359929867](https://github.com/podman-container-tools/podman/actions/runs/32359929867/job/96397157179) | `build fedora-rawhide / lima` | `BUILD` | `step_name_build` | low | `failed step: Run test on lima` |
| [32282109382](https://github.com/podman-container-tools/podman/actions/runs/32282109382/job/96165940777) | `build fedora-rawhide / lima` | `BUILD` | `compile_error` | high | `pkg/api/handlers/compat/exec.go:29:24: undefined: handlers.ExecCreateConfigJSON` |
| [31869969647](https://github.com/podman-container-tools/podman/actions/runs/31869969647/job/94976976480) | `windows installer hyperv` | `BUILD` | `step_name_build` | low | `failed step: Build docs` |
| [31869969647](https://github.com/podman-container-tools/podman/actions/runs/31869969647/job/94976976446) | `windows installer wsl` | `BUILD` | `step_name_build` | low | `failed step: Build docs` |
| [31770301280](https://github.com/podman-container-tools/podman/actions/runs/31770301280/job/94676770701) | `windows unit` | `BUILD` | `compile_error` | high | `package go.podman.io/podman/v6/pkg/api/handlers/compat: build constraints exclude all Go f` |
| [31911449880](https://github.com/podman-container-tools/podman/actions/runs/31911449880/job/95398591212) | `farm rootless fedora-current / lima` | `INFRA_RESOURCE` | `oom_or_vm` | high | `chown: cannot access '/dev/kvm': No such file or directory` |
| [32315314995](https://github.com/podman-container-tools/podman/actions/runs/32315314995/job/96266213883) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `##[error]libpod/container_internal_common.go:345:5: SA1019: (go.podman.io/buildah/pkg/over` |
| [32282109382](https://github.com/podman-container-tools/podman/actions/runs/32282109382/job/96165940332) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `##[error]pkg/api/handlers/exec_test.go:46:21: undefined: handlers.ExecCreateConfigJSON (ty` |
| [32245763236](https://github.com/podman-container-tools/podman/actions/runs/32245763236/job/96059886231) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `##[error]pkg/api/handlers/compat/networks.go:77:6: slicesbackward: backward loop over slic` |
| [32234356215](https://github.com/podman-container-tools/podman/actions/runs/32234356215/job/96020655559) | `Validate source code changes` | `LINT` | `step_name_lint` | low | `failed step: Validate renovate config` |
| [32090211476](https://github.com/podman-container-tools/podman/actions/runs/32090211476/job/95570821947) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `##[error]cmd/podman/artifact/list.go:97:44: quietOut - result 0 (error) is always nil (unp` |
| [32064420161](https://github.com/podman-container-tools/podman/actions/runs/32064420161/job/95492950874) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `##[error]pkg/domain/infra/abi/images.go:29:1: File is not properly formatted (gofumpt)` |
| [32050526660](https://github.com/podman-container-tools/podman/actions/runs/32050526660/job/95734692787) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `+ /home/ubuntu/golangci-lint-2.12.2-linux-amd64/golangci-lint run --build-tags=apparmor,se` |
| [32049160036](https://github.com/podman-container-tools/podman/actions/runs/32049160036/job/95444081716) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `##[error]cmd/rootlessport/main.go:300:4: The copy of the 'for' variable "protocol" can be ` |
| [32032383520](https://github.com/podman-container-tools/podman/actions/runs/32032383520/job/96098853398) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `##[error]pkg/domain/infra/abi/generate.go:39:30: non-wrapping format verb for fmt.Errorf. ` |
| [31802052979](https://github.com/podman-container-tools/podman/actions/runs/31802052979/job/94772167023) | `Validate source code changes` | `LINT` | `validation_gate` | medium | `CGO_ENABLED=0 GOOS=freebsd hack/golangci-lint.sh` |
| [31879825400](https://github.com/podman-container-tools/podman/actions/runs/31879825400/job/95000741570) | `Validate source code changes` | `TEST_FAILURE` | `bats_failure` | high | `not ok 3 PR 8685 - multiple commits, no tests` |
| [32247003769](https://github.com/podman-container-tools/podman/actions/runs/32247003769/job/96052524051) | `apiv2 rootless fedora-current / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 1347 [26-containersWait] POST containers/WaitTestingCtr/wait?condition=next-exit [-` |
| [31869923347](https://github.com/podman-container-tools/podman/actions/runs/31869923347/job/95348083456) | `apiv2 rootless fedora-current / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 1347 [26-containersWait] POST containers/WaitTestingCtr/wait?condition=next-exit [-` |
| [31821911636](https://github.com/podman-container-tools/podman/actions/runs/31821911636/job/94840717454) | `bud local root fedora-current / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 486 bud with --raw-iidfile alias` |
| [31821911636](https://github.com/podman-container-tools/podman/actions/runs/31821911636/job/94840717740) | `bud remote root fedora-current / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 486 bud with --raw-iidfile alias` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087525041) | `int local root debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887215) | `int local root debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [31954250080](https://github.com/podman-container-tools/podman/actions/runs/31954250080/job/95342989730) | `int local root debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman container interface name [It] podman container interface name with default s` |
| [31762145156](https://github.com/podman-container-tools/podman/actions/runs/31762145156/job/94652128250) | `int local root debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run [It] podman run check personality support` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087525053) | `int local root fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887117) | `int local root fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [31954250080](https://github.com/podman-container-tools/podman/actions/runs/31954250080/job/95342990186) | `int local root fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman volume plugins [It] remove plugin with stopped plugin succeeds` |
| [31795981093](https://github.com/podman-container-tools/podman/actions/runs/31795981093/job/94759411374) | `int local root fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run networking [It] podman run container with two static IPs one per subnet` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087525334) | `int local root fedora-prior / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887266) | `int local root fedora-prior / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [31954250080](https://github.com/podman-container-tools/podman/actions/runs/31954250080/job/95342989696) | `int local root fedora-prior / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman volume plugins [It] remove plugin with stopped plugin succeeds` |
| [31813098642](https://github.com/podman-container-tools/podman/actions/runs/31813098642/job/94812362325) | `int local root fedora-prior / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run networking [It] podman run network connection with default bridge` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087525161) | `int local root fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887269) | `int local root fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32032269509](https://github.com/podman-container-tools/podman/actions/runs/32032269509/job/95397793390) | `int local root fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman rmi [It] podman image rm - concurrent with shared layers` |
| [31954250080](https://github.com/podman-container-tools/podman/actions/runs/31954250080/job/95342989588) | `int local root fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman volume plugins [It] remove plugin with stopped plugin succeeds` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087524925) | `int local rootless debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887417) | `int local rootless debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087524897) | `int local rootless fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32067619067](https://github.com/podman-container-tools/podman/actions/runs/32067619067/job/95506772433) | `int local rootless fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run memory [It] podman run memory test on oomkilled container` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887557) | `int local rootless fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [31813098642](https://github.com/podman-container-tools/podman/actions/runs/31813098642/job/94812361968) | `int local rootless fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run networking [It] podman run network connection with host` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087524902) | `int local rootless fedora-prior / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887730) | `int local rootless fedora-prior / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087524931) | `int local rootless fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887638) | `int local rootless fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32262283062](https://github.com/podman-container-tools/podman/actions/runs/32262283062/job/96102083292) | `int remote root debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run networking [It] podman run container with two static IPs one per subnet` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087525133) | `int remote root debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887758) | `int remote root debian-sid / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32262283062](https://github.com/podman-container-tools/podman/actions/runs/32262283062/job/96102083773) | `int remote root fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman run networking [It] podman run container with two static IPs one per subnet` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087525015) | `int remote root fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887237) | `int remote root fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087524908) | `int remote root fedora-prior / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887613) | `int remote root fedora-prior / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087524840) | `int remote root fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887700) | `int remote root fedora-rawhide / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32256545532](https://github.com/podman-container-tools/podman/actions/runs/32256545532/job/96087524806) | `int remote rootless fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32035469850](https://github.com/podman-container-tools/podman/actions/runs/32035469850/job/95667887718) | `int remote rootless fedora-current / lima` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] Podman artifact [It] podman artifact ls` |
| [32262283062](https://github.com/podman-container-tools/podman/actions/runs/32262283062/job/96102081059) | `macos machine applehv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine init [It] machine init with swap` |
| [32247003769](https://github.com/podman-container-tools/podman/actions/runs/32247003769/job/96052522896) | `macos machine applehv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine init [It] machine init with volume` |
| [32176110300](https://github.com/podman-container-tools/podman/actions/runs/32176110300/job/95842744429) | `macos machine applehv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine start [It] machine init --now with --update-connection` |
| [32032269509](https://github.com/podman-container-tools/podman/actions/runs/32032269509/job/95397791321) | `macos machine applehv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine set [It] set while machine already running` |
| [31911449880](https://github.com/podman-container-tools/podman/actions/runs/31911449880/job/95398590155) | `macos machine applehv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine ssh [It] verify machine rootfulness` |
| [31758832312](https://github.com/podman-container-tools/podman/actions/runs/31758832312/job/94643414549) | `macos machine applehv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine proxy settings propagation [It] ssh to running machine and check pro` |
| [32147262349](https://github.com/podman-container-tools/podman/actions/runs/32147262349/job/95749965967) | `macos machine libkrun` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine set [It] set machine cpus, disk, memory` |
| [32023775922](https://github.com/podman-container-tools/podman/actions/runs/32023775922/job/95372062768) | `macos machine libkrun` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine init [DeferCleanup (Each)] machine init with volume` |
| [32176110300](https://github.com/podman-container-tools/podman/actions/runs/32176110300/job/95842746104) | `sys local root fedora-prior / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 301 [500] podman network reload in 853ms` |
| [31795981093](https://github.com/podman-container-tools/podman/actions/runs/31795981093/job/94759411048) | `sys local root fedora-prior / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 93 \|035\| podman logs - --until --follow journald in 10466ms` |
| [32262283062](https://github.com/podman-container-tools/podman/actions/runs/32262283062/job/96102084073) | `sys local root fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 127 \|065\| podman cp file from container to container in 2752ms` |
| [32053009523](https://github.com/podman-container-tools/podman/actions/runs/32053009523/job/95459823136) | `sys local root fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 434 \|610\| check Go template formatting in 61625ms` |
| [31803613327](https://github.com/podman-container-tools/podman/actions/runs/31803613327/job/94780711510) | `sys local rootless debian-sid / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 165 \|090\| events - container inspect data - journald in 1367ms` |
| [32032269509](https://github.com/podman-container-tools/podman/actions/runs/32032269509/job/95397793259) | `sys local rootless fedora-prior / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 93 \|035\| podman logs - --until --follow journald in 7638ms` |
| [31803613327](https://github.com/podman-container-tools/podman/actions/runs/31803613327/job/94780710875) | `sys local rootless fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 299 [500] podman networking: port with --userns=keep-id for rootless or --uidmap=* ` |
| [31821754525](https://github.com/podman-container-tools/podman/actions/runs/31821754525/job/94843947061) | `sys remote root debian-sid / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 51 [032] podman sigproxy test: exec in 12957ms` |
| [31821754525](https://github.com/podman-container-tools/podman/actions/runs/31821754525/job/94843947000) | `sys remote root fedora-current / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 51 [032] podman sigproxy test: exec in 13271ms` |
| [31821754525](https://github.com/podman-container-tools/podman/actions/runs/31821754525/job/94843946834) | `sys remote root fedora-prior / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 51 [032] podman sigproxy test: exec in 13077ms` |
| [31970389202](https://github.com/podman-container-tools/podman/actions/runs/31970389202/job/95363052438) | `sys remote root fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 317 \|450\| podman detects correct tty size in 3313ms` |
| [31821754525](https://github.com/podman-container-tools/podman/actions/runs/31821754525/job/94843947126) | `sys remote root fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 51 [032] podman sigproxy test: exec in 12786ms` |
| [31758832312](https://github.com/podman-container-tools/podman/actions/runs/31758832312/job/94643415283) | `sys remote root fedora-rawhide / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 160 \|090\| events with disjunctive filters - default in 1714ms` |
| [31821754525](https://github.com/podman-container-tools/podman/actions/runs/31821754525/job/94843946950) | `sys remote rootless fedora-current / lima` | `TEST_FAILURE` | `bats_failure` | high | `not ok 51 [032] podman sigproxy test: exec in 12855ms` |
| [32147262349](https://github.com/podman-container-tools/podman/actions/runs/32147262349/job/95749965975) | `windows machine hyperv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine start [It] start simple machine` |
| [31762180270](https://github.com/podman-container-tools/podman/actions/runs/31762180270/job/94653588223) | `windows machine hyperv` | `TEST_FAILURE` | `ginkgo_failure` | high | `Summarizing 1 Failure:` |
| [31762145156](https://github.com/podman-container-tools/podman/actions/runs/31762145156/job/94652127375) | `windows machine hyperv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] podman machine rm [It] Remove machine sharing ssh key with another machine` |
| [31758832312](https://github.com/podman-container-tools/podman/actions/runs/31758832312/job/94643414583) | `windows machine hyperv` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] run cp commands [DeferCleanup (Each)] podman cp` |
| [31791185291](https://github.com/podman-container-tools/podman/actions/runs/31791185291/job/94741407151) | `windows machine wsl` | `TEST_FAILURE` | `ginkgo_failure` | high | `[FAIL] run basic podman commands [It] Volume ops` |
| [32032269509](https://github.com/podman-container-tools/podman/actions/runs/32032269509/job/95397791367) | `macos machine libkrun` | `TIMEOUT_HANG` | `timeout` | medium | `##[error]The operation was canceled.` |
| [32286196688](https://github.com/podman-container-tools/podman/actions/runs/32286196688/job/96176191113) | `Validate source code changes` | `UNKNOWN` | `no_rule_matched` | low | `` |
| [31758832312](https://github.com/podman-container-tools/podman/actions/runs/31758832312/job/94640564624) | `govulncheck` | `UNKNOWN` | `no_rule_matched` | low | `` |
| [32143424666](https://github.com/podman-container-tools/podman/actions/runs/32143424666/job/95734806140) | `int local rootless debian-sid / lima` | `UNKNOWN` | `no_rule_matched` | low | `` |
| [32025596823](https://github.com/podman-container-tools/podman/actions/runs/32025596823/job/95393218275) | `sys local rootless fedora-rawhide / lima` | `UNKNOWN` | `no_rule_matched` | low | `` |
