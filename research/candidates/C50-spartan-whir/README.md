# C50 — Spartan-WHIR controls

This package separates two incompatible evidence tracks:

1. `ethereum/spartan-whir` at `f525cddea38bb605304d3a8e6394dda10ac64b4a` is a native full-ZK Spartan-WHIR implementation. Its upstream README example is an implementation-maturity smoke, **not the frozen v0.3/H0 relation and not PQTC**.
2. `ethereum/sol-spartan-whir` at `b381a9091568d1a4a52b50d0b27488a767051faf` contains standalone plain-WHIR verification with placeholder Spartan fields. It is **not Spartan and not PQTC**.

No upstream source is vendored because both repositories are blocked for copying or redistribution pending an explicit license grant.

## Exact commands

All worktrees and results default to the system temporary directory. Override both paths when durable evidence is required.

```sh
python3 research/candidates/C50-spartan-whir/run.py source-check \
  --workspace /absolute/path/c50-work --output /absolute/path/c50-source-check
```

The native command extracts the pinned README's Circom and JSON blocks at runtime, compiles that exact example, then runs the documented full-ZK setup/prove/verify sequence:

```sh
python3 research/candidates/C50-spartan-whir/run.py native \
  --workspace /absolute/path/c50-work --output /absolute/path/c50-native
```

Required upstream tools are Circom 2.2 with KoalaBear support, a C++ compiler, GMP, `nlohmann-json`, Rust, and Cargo. The executed proof relation is `UPSTREAM_README_EXAMPLE_NOT_FROZEN_H0`; success is `PASS_IMPLEMENTATION_MATURITY_ONLY`, never PQTC.

The retained native attempt is `NOT_EVALUATED`: the required `circom` executable is absent. `outputs/native/result.json` records `MISSING_PREREQUISITE` without treating this as a cryptographic failure.

Reproduce the pinned standalone Solidity-WHIR build and tests:

```sh
python3 research/candidates/C50-spartan-whir/run.py solidity \
  --workspace /absolute/path/c50-work --output /absolute/path/c50-solidity
```

Reproduce the exact transaction-gas harness failure separately:

```sh
python3 research/candidates/C50-spartan-whir/run.py solidity-gas \
  --workspace /absolute/path/c50-work --output /absolute/path/c50-solidity-gas
```

The runner executes these upstream commands without changing them:

The pinned Solidity tree does not retain its dependency gitlinks. Before execution, the runner verifies the authoritative archived plain-WHIR dependency control at `privacy-ethereum/sol-whir@b719b97b5961ac1c1679383b31e55439a26682f9`, materializes `forge-std@035de35f5e366c8d6ed142aec4ccb57fe2dd87d4` and `solady@513f581675374706dbe947284d6b12d19ce35a2a` under the ignored `lib/` directory, and initializes any nested submodules recursively. It verifies the imported source files by SHA-256 and records dependency commits, hashes, and recursive submodule state in `result.json`.

```sh
forge build
forge test
bash .agents/skills/tx-gas-benchmarking/scripts/run_tx_gas_benchmark.sh script/WhirBlobNativeTxBenchmark_k22_jb100_ext5_lir4_ff4_rsv3_pow28.s.sol
```

The pinned `forge build` and `forge test` reproduction completed successfully. That is a standalone plain-WHIR build/test `PASS`, not Spartan and not PQTC.

The exact gas script exits before starting a gas measurement: line 95 expands `target_contract[@]` while the array is unbound under `set -u`. Its disposition is `UNEXECUTABLE_UPSTREAM_HARNESS_AT_PIN`; gas is `NOT_EVALUATED`. Do not patch the upstream script or report a local gas number. The unchanged failed result and logs are retained in `outputs/solidity-gas/`; the successful build/test result is retained in `outputs/solidity/`.

Every Solidity result is labeled `STANDALONE_WHIR_NOT_SPARTAN_NOT_PQTC`. The local gas measurement is `NOT_EVALUATED`. Upstream-only headline values remain isolated in `upstream-claims.json` and every metric is labeled `UPSTREAM_BASELINE_NOT_PQTC`; they are not local results.

## Output

Each action writes `result.json` plus command logs when a command is executed. Validate results against `result.schema.json`. Source pins and byte hashes are in `source-hashes.json`; dispositions and blockers are in `status.json`, `negative-results.json`, and `ADR.md`.
