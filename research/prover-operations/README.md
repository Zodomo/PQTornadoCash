# SP-73 prover operations

**Gate: `FAIL`. Evidence: frozen v0.3 H1 baseline operations only. No finalist is selected or security-qualified.**

This package deterministically analyzes the 60 committed `C00/v03-baseline` run records and the committed H1 hardware profile. It does not modify v0.3, run a new prover, project results onto unmeasured hardware, claim a live-chain workflow, or provide external cryptographic acceptance.

## Reproduce and validate

From the repository root:

```sh
python3 research/prover-operations/analyze.py
```

Expected terminal summary:

```text
validated_source_records=60 validated_artifacts=480 output_schema=PASS gate=FAIL
```

To intentionally regenerate retained derived outputs after reviewing changed inputs:

```sh
python3 research/prover-operations/analyze.py --write
python3 research/prover-operations/analyze.py
```

The analyzer:

1. requires exactly `v03-corpus-01..30` and `v03-fixed-01..30`;
2. validates each record against the root `benchmark-run.schema.json`;
3. enforces run ID, candidate, source spike, baseline commit, success, proof-byte, calldata-byte, proof-section, and hardware-profile invariants;
4. verifies the current byte length and SHA-256 of all 480 declared artifacts;
5. builds `results.json` using decimal arithmetic and validates it against `result.schema.json`;
6. checks the retained result byte-for-byte and checks all pinned input SHA-256 values in `source-hashes.json`.

No generation timestamp is included, so equal inputs produce equal output bytes. Source decimal spellings are retained. p90/p95/p99 use nearest rank; mean and population standard deviation use decimal arithmetic rounded half-even to 12 decimal places.

## H1 evidence

The 60 records match `H1_CONTINUITY` on Apple M4 Max, ARM64, 16 physical/logical cores, and 48 GiB recorded RAM. The hardware profile lists NEON as present. Run-level `cpu_features` is empty, so execution of a NEON-specific path is `NOT_EVALUATED`. The profile ID and legacy run-record ID differ and are both retained.

Every source record explicitly says `WARM`. There are zero committed `COLD` records; no item is relabeled based on run order.

| H1 warm metric | Count | Minimum | Median | p90 | p95 | p99 | Maximum | Mean | Population standard deviation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Wall time (ms) | 60 | 272.52025000052527 | 604.9685000180034 | 800.632583006518 | 824.8314580123406 | 1115.2789169864263 | 1115.2789169864263 | 603.736411700083 | 180.216130728066 |
| Proof-only time (ms) | 60 | 253.408375 | 584.9313545000000 | 781.190583 | 804.0041249999999 | 1095.41825 | 1095.41825 | 582.813682650000 | 179.934012449048 |
| Native verify time (ms) | 60 | 2.054208 | 2.16087499999999985 | 2.3104169999999997 | 2.325333 | 2.532458 | 2.532458 | 2.182668033333 | 0.082676527652 |
| Peak RSS (bytes) | 60 | 26,771,456 | 29,483,008 | 30,605,312 | 30,851,072 | 31,653,888 | 31,653,888 | 29,462,528.000000000000 | 987,420.356277642610 |

CPU time is `NOT_EVALUATED`: all 60 `prover.cpu_ms` values are null. Peak RSS is measured, but constrained-memory, swap, allocation-total, OOM, and memory-pressure behavior are not.

## Proof serialization, upload bytes, and disk

The analyzer checks the serialized A/B files against each record's proof totals and the A/B calldata files against its ABI calldata totals.

| Measured byte quantity | Count | Minimum | Median | p90 | p95 | p99 | Maximum | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Raw A+B proof bytes | 60 | 198,052 | 208,940 | 212,524 | 213,100 | 213,804 | 213,804 | 12,517,496 |
| A+B ABI calldata bytes | 60 | 198,728 | 209,608 | 213,192 | 213,768 | 214,472 | 214,472 | 12,557,600 |
| Eight retained artifacts per run | 60 | 417,445 | 489,148 | 546,375 | 548,559 | 554,344 | 554,344 | 29,351,521 |

These are measured payload and retained-file sizes, not network measurements. Serialization time, upload time, transport, retry behavior, temporary files, build/precomputation caches, workspace high-water usage, and peak free-space requirement are `NOT_EVALUATED`.

## Platform and workflow matrix

| Requirement | Result | Exact evidence boundary |
|---|---|---|
| H1 Apple ARM64/NEON warm | `PARTIALLY_MEASURED` | 60 warm records; NEON is a hardware capability, not an executed-path record. |
| H1 cold first proof | `NOT_EVALUATED` | 0 cold records. |
| H2 commodity x86-64/AVX2 | `NOT_EVALUATED` | H2 is marked unavailable; no record exists. |
| H3 high-end x86-64/AVX-512 | `NOT_EVALUATED` | H3 is marked unavailable; no record exists. |
| Scalar/portable build | `NOT_EVALUATED` | No build/run or feature-selection record. |
| AVX2 path | `NOT_EVALUATED` | No x86-64/AVX2 evidence. |
| AVX-512 path | `NOT_EVALUATED` | No x86-64/AVX-512 evidence. |
| WASM/browser | `NOT_EVALUATED` | No WASM proof/witness evidence; optional for the gate. |
| Trusted setup | Not required | All source records say `trusted_setup=false`. This does not mean precomputation takes zero time. |
| Setup/precomputation | `NOT_EVALUATED` | No phase time or cache bytes. |
| Cancellation | `NOT_EVALUATED` | No attempt, latency, cleanup, or partial-output record. |
| Progress | `NOT_EVALUATED` | No progress stream. |
| Memory pressure | `NOT_EVALUATED` | RSS exists; no pressure experiment. |
| Deterministic crash recovery | `NOT_EVALUATED` | No authenticated checkpoint, injected crash, resume, mismatch rejection, or resumed result. |
| Practical CLI | `SPECIFICATION_ONLY_NOT_IMPLEMENTED` | The existing generator is destructive and batch-oriented. |

`cli-workflow.json` defines the proposed offline `prepare`, `prove`, `cancel`, `resume`, `inspect`, and `package` workflow, progress/checkpoint contracts, exit codes, and exact current/next measurement commands. It gives no gate credit. H2/H3 acquisition must occur in isolated worktrees and distinct output namespaces. The current generator hard-codes incomplete feature/condition metadata; the documented metadata-retention precondition must be fixed before those measurements can qualify.

## Operational privacy review

The retained baseline prover reads a local synthetic witness and writes local proof artifacts. The baseline README says its local t8n route does not contact RPC or read `.env`. This establishes only the retained research data flow.

`privacy-review.json` separately addresses:

- witness services and remote memory/compute;
- telemetry inventory and safe defaults;
- RPC linkage to commitment/root/path interest;
- centralized path-provider observation, denial, and equivocation;
- proof upload metadata;
- process/container/VM/TEE witness isolation;
- attestation roots, freshness, rollback, debug state, and limitations;
- and a compatible offline local fallback.

No production proving service is proposed or accepted. Secure witness isolation, attestation, telemetry behavior, deployed RPC/path acquisition, and production local fallback remain `NOT_EVALUATED`. A cross-user aggregator receives proofs and public statements only, never witnesses. Proof upload can still reveal transaction intent and timing.

## Gate and blockers

SP-73 requires complete H1/H2/H3 measurements and a practical CLI workflow. The gate is necessarily `FAIL` because H1 cold is missing, H2 and H3 are absent, and the product CLI is only a specification. Setup/precomputation, cancellation, progress, memory pressure, and crash recovery are additional missing required workflows.

Exact blockers and next actions are retained in `negative-results.json`; exact acquisition commands and their prerequisites/limitations are in `cli-workflow.json`. H2/H3 remain `NOT_EVALUATED`, not projections from H1. Browser/mobile is optional. No “good UX” claim, finalist designation, accepted security, live-chain result, or external review is made.
