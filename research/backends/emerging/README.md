# Emerging backend reproduction package

This package supplies shared exact-pin checkout, byte-hash verification, command logging, and result recording for C50, C60, and C70. It contains no backend integration and no PQTC finalist.

## Focused source checks

Run one candidate at a time to avoid measurement or build contention:

```sh
python3 research/backends/emerging/run.py C50 \
  --workspace /absolute/path/emerging-work --output /absolute/path/c50-source-check
python3 research/backends/emerging/run.py C60 \
  --workspace /absolute/path/emerging-work --output /absolute/path/c60-source-check
python3 research/backends/emerging/run.py C70 \
  --workspace /absolute/path/emerging-work --output /absolute/path/c70-source-check
```

The dispatcher runs only `source-check`; it never builds or benchmarks. Exact executable reproduction commands are documented and implemented in each candidate package:

- `../../candidates/C50-spartan-whir/README.md`
- `../../candidates/C60-recursion/README.md`
- `../../candidates/C70-flock-veil/README.md`

## Evidence rules

- Frozen v0.3/H0 is the only faithful PQTC relation control.
- Native Spartan's `PASS` means upstream full-ZK implementation maturity only.
- Standalone Solidity WHIR build/tests pass, but remain not Spartan and not PQTC. Its exact upstream gas harness is `UNEXECUTABLE_UPSTREAM_HARNESS_AT_PIN`; local gas is `NOT_EVALUATED`.
- Toy Fibonacci is not PQTC; recursion remains `DEFERRED`.
- Historical Flock batch-44 is `UNEXECUTABLE_AT_PIN/FAIL`: the exact command produces no number because `m21_fast` is unregistered. Its capacity semantics remain `UPSTREAM_BASELINE_NOT_PQTC`, and Flock remains `STOP`.
- VEIL is an experimental mismatched PoC and remains `DEFERRED`.
- Missing Spartan license grants block vendoring or redistribution.

Candidate output validates against both its local `result.schema.json` and the aggregate `result.schema.json` here. Pins and source hashes are in `source-hashes.json` and the candidate source manifests.

If an executable prerequisite is missing, command runners fail closed without a traceback after writing `result.json`. The record has `execution_status: "NOT_EVALUATED"` and a `blocker` with `kind: "MISSING_PREREQUISITE"` plus the missing executable name. No absent-tool run is represented as a failed cryptographic evaluation.
