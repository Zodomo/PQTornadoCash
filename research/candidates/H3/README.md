# H3: Width-24 d=10 feed-forward node compressor

**Status: `BENCHMARK_ONLY`. Custody/deployment eligibility: none.**

## Definition

Trunc_10(Poseidon2_BabyBear_24(x)+x), first ten lanes

## Application decision

The primitive/layout microbenchmark places 20 generic payload lanes followed by role/version/shape/level, exactly filling 24 lanes. Its note and nullifier labels do not make the payloads protocol-complete: scope and frozen semantic secret/trapdoor widths are absent.

Layout exercise: lanes 0..19 generic payload; 20 role; 21 version; 22 shape=20; 23 level.

## Decision

Execute primitive and layout benchmarks only. Complete application-role parity is `NOT_EVALUATED`. The Stage A result is `PASS_STAGE_A_BENCHMARK_ONLY`; exact blockers are retained in `security/manifest.json`.

## Commands

Use the common one-command entry points: `python3 research/candidates/hash-compression-common/run.py vectors-parity` and `python3 research/candidates/hash-compression-common/run.py benchmark --samples 1000`.
