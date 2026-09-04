# H7: Published RPO-M31 sponge comparator

**Status: `BENCHMARK_ONLY`. Custody/deployment eligibility: none.**

## Definition

RPO-M31 over p=2^31-1, width 24, rate 16, capacity 8, alpha 5/inverse, seven rounds and concluding linear/constants step

## Application decision

The primitive/layout microbenchmark absorbs generic payload after role/version/shape/level using published zero padding/final-block-length domain. Its note and nullifier labels do not make the payloads protocol-complete: scope and frozen semantic secret/trapdoor widths are absent.

Layout exercise: absorbed message begins role, version, shape, level. Published domain 16-finalBlockLength initializes capacity lane 16.

## Decision

Measure the published sponge as a non-Poseidon comparator; never wrap it as a compressor. The Stage A result is `PASS_STAGE_A_BENCHMARK_ONLY`. Exact blockers are retained in `security/manifest.json`; benchmark speed cannot remove them.

## Commands

Use the common one-command entry points: `python3 research/candidates/hash-compression-common/run.py vectors-parity` and `python3 research/candidates/hash-compression-common/run.py benchmark --samples 1000`.
