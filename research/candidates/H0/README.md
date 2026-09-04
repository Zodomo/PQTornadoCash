# H0: Current width-16 P2BB512 sponge baseline

**Status: `BENCHMARK_ONLY`. Custody/deployment eligibility: none.**

## Definition

BabyBear Poseidon2 width 16, x^7, RF=8, RP=13; rate 4; 16-field squeeze

## Application decision

All current sponge roles remain measurable with frozen tags NOTE=`0x11`, NULLIFIER=`0x12`, and APP_MERKLE_NODE=`0x20`, plus explicit version/byte-length/element-count/aux framing. Note payloads are 32 fields (scope 16, nullifier secret 8, trapdoor 8), nullifier payloads are 24 fields (scope 16, secret 8), and nodes are two 16-field digests.

Layout: The frozen v0.3 P2BB512 framing is version, role tag, payload byte length, payload element count, and aux/level in capacity lanes 4..8.

## Decision

Retain only as compatibility and measurement control. The Stage A result is `PASS_BASELINE_ONLY`. Exact blockers are retained in `security/manifest.json`; benchmark speed cannot remove them.

## Commands

Use the common one-command entry points: `python3 research/candidates/hash-compression-common/run.py vectors-parity` and `python3 research/candidates/hash-compression-common/run.py benchmark --samples 1000`.
