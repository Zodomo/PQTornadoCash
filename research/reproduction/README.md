# Deterministic reproduction package

This package implements the one-command workflows from research-plan section 25 without authorizing a deployment. The registry contains all minimum candidates (`C00`, `C01`, `C10`, `C11`, `C12`, `C20`, `C21`, `C22`, `C23`, `C30`, and `C40`) and the evidence-only component packages. There are no eligible integrated finalists. Unsupported candidate actions terminate with exit code 2 and machine-readable code `NOT_AVAILABLE_NO_ELIGIBLE_FINALIST`; component evidence is never promoted implicitly.

Run commands from the repository root. Every response is a deterministic JSON envelope. `--dry-run` may appear anywhere and emits ordered argv/cwd/environment records without executing child processes.

```sh
# Inspect the complete registry or one plan candidate.
python3 research/reproduction/reproduce.py registry
python3 research/reproduction/reproduce.py registry --candidate C00

# Regenerate and verify the SHA-256 evidence manifest.
python3 research/reproduction/reproduce.py manifest
python3 research/reproduction/reproduce.py verify-manifest

# Check only the pinned artifacts for one candidate or all candidates.
python3 research/reproduction/reproduce.py verify --candidate C00
python3 research/reproduction/reproduce.py verify --candidate all

# Section 25 workflows for the frozen C00/v0.3 baseline.
python3 research/reproduction/reproduce.py build --candidate C00
python3 research/reproduction/reproduce.py corpus --candidate C00
python3 research/reproduction/reproduce.py prove --candidate C00 --cases all --runs 30
python3 research/reproduction/reproduce.py verify-native --candidate C00 --all
python3 research/reproduction/reproduce.py verify-evm --candidate C00 --client anvil
python3 research/reproduction/reproduce.py security --candidate C00
python3 research/reproduction/reproduce.py report --candidate C00

# The C01 q48 comparator has exactly one supported candidate action.
python3 research/reproduction/reproduce.py security --candidate C01

# Read-only, offline verification; runs no subprocess, build, proof, EVM, RPC, or secret action.
python3 research/reproduction/reproduce.py all-safe
```

For example, this is deliberately unsuccessful:

```sh
python3 research/reproduction/reproduce.py prove --candidate C11 --cases all --runs 30
```

## Safety and outputs

The process environment is reduced to a small toolchain allowlist before any child command is executed. No CLI option accepts an RPC URL, private key, keystore, broadcast path, deployment target, or arbitrary shell command. EVM verification is fixed to the local Foundry/Anvil test harness. Commands are executed as argv arrays with `shell=False`.

Fresh C00 proof outputs go only to `research/reproduction/.work/C00/proofs/`, which is excluded from the evidence manifest. `prove` consumes the fresh derived inputs written by the preceding `corpus` action. The controller checks each proof's retained metadata for OS entropy, immediate native verification, codec round-trip, uniqueness within the run, and inequality with the corresponding authoritative retained proof. It never rewrites the 60 authoritative `research/runs/v03-*.json` records. `verify-native --all` independently verifies the complete pinned 60-proof baseline, while each newly generated proof is already verified by both the prover and the controller. `report` writes deterministic derived tables below `.work`.

The manifest generator defaults to `benchmark-run.schema.json`, the governing research plan, and `research/`. It excludes itself; VCS metadata; cache directories; Python caches; all `target` and `out` build trees; `old_plans` and `old_reports` user moves; `.env` names; reproduction work directories; and conventional temporary suffixes. Verification rehashes every listed regular file and permits later additions until the manifest is regenerated; it does not silently bless changed or missing pinned files.

## Candidate/component boundary

`command-registry.json` distinguishes plan candidates from experimental component packages. Candidate actions are callable only where a complete exact route exists: all seven workflows for frozen C00 and security calculation for comparator C01. Every other action is explicitly unavailable because component benchmarks do not form an eligible integrated candidate. Component records preserve their exact existing entrypoint argv and prerequisites for independent evidence reproduction, including failed and unexecutable packages, but the candidate CLI does not reinterpret them as successful integrated work.
