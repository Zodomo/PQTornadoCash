# PQTC Next-Generation Research Evidence

This directory contains reproducible evidence for `PQTC_NEXT_GENERATION_RESEARCH_PLAN.md`. It is research-only. Nothing here authorizes deployment or modifies the frozen v0.3 custody design.

## Baseline

- Frozen tag: `pqtc-v0.3-research-baseline`
- Frozen commit: `00f829001999ee66da6fd5161c4c205c07d0b937`
- Starting implementation: PQTC v0.3
- Public-network execution: prohibited until separate explicit authorization

The baseline tag points to the committed v0.3 snapshot. New measurements and candidate experiments are stored under `research/`; the v0.3 implementation is not optimized in place.

## Evidence rules

1. Every candidate has an immutable ID, manifest, assumptions, source hashes, status, ADR, and retained negative results.
2. `PASS`, `FAIL`, `CONDITIONAL`, `DEFERRED`, `BENCHMARK_ONLY`, and `NOT_EVALUATED` retain the meanings in the research plan.
3. A benchmark that lacks witness hiding, complete statement binding, accepted security accounting, or complete EVM verification is never promoted from `BENCHMARK_ONLY` because it is fast.
4. Raw proof bytes and exact ABI calldata are separate measurements.
5. Transaction gates use complete top-level transaction gas and all three calldata schedules.
6. Security tables separate proven, conjectural, heuristic, and generic-ceiling claims.
7. Unavailable independent or external review is recorded as an unresolved dependency. It is never simulated or self-awarded.
8. No live note secret, private key, RPC credential, or `.env` value may enter an artifact.

## Layout

- `common-corpus/`: backend-neutral semantic witnesses, invalid mutations, tree histories, and deterministic generators.
- `harness/`: run validation, gas schedules, proof byte ledgers, hardware capture, summary generation, and evidence hashing.
- `candidates/<candidate-id>/`: candidate definition, ADR, assumptions, vectors, proofs, gas, native, security, and status.
- `runs/`: one schema-valid JSON object per benchmark run.
- `summaries/`: generated CSV and JSON comparisons.
- `external-baselines/`: pinned upstream source/reproduction evidence.
- `advisories/`: applicability matrix and executable regressions.
- `cryptanalysis/`: primitive/mode/transcript review packets.
- `reviews/`: internal checkpoint minutes and independent-review records.
- `final/`: standalone report, executive matrix, unresolved questions, and evidence manifest.

## Reproduction policy

The canonical entry point is `python3 research/harness/benchctl/benchctl.py`. Individual candidate READMEs contain candidate-specific commands. Commands default to local execution and must not use a public RPC endpoint.

Generated evidence is accepted only when its source commit, toolchain, hardware profile, inputs, output hashes, and gate result are recorded. The final manifest covers every retained file with SHA-256 and Ethereum Keccak-256; the manifest excludes itself to avoid self-reference.
