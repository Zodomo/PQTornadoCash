# PQTornado next-generation research

This repository investigates whether a transparent, pairing-free, witness-hiding proof can support private Tornado Classic withdrawals with defensible post-quantum-oriented security and practical Ethereum costs.

The work is a research program, not a production implementation. It compares application hashes, arithmetizations, polynomial commitment schemes, verifier designs, transaction shapes, and deployment environments against one frozen protocol corpus and one set of hard gates.

## Current conclusion

**No candidate is ready for a new build.**

The evidence supports:

- **Outcome:** `OUTCOME_D` — no new full build yet.
- **Recommendation:** `RECOMMEND_ADDITIONAL_TARGETED_RESEARCH`.
- **Eligible finalists:** zero.
- **Complete integrated prototypes:** zero.

One-transaction verification was not demonstrated at the required security and operational margins. A robust two-transaction fallback was also not demonstrated. Some components improved individual metrics, but none passed the complete security, privacy, calldata, gas, deployment, and operational gates together.

This conclusion does not mean that every experiment failed. It means that promising component results cannot yet be combined into a defensible custody system.

## Start here

| Document | Purpose |
|---|---|
| [`research/final/NEXT_GENERATION_RESEARCH_REPORT.md`](research/final/NEXT_GENERATION_RESEARCH_REPORT.md) | Standalone report, evidence, conclusions, and rejected candidates |
| [`research/final/EXECUTIVE_MATRIX.csv`](research/final/EXECUTIVE_MATRIX.csv) | Compact comparison of the principal candidates and gates |
| [`research/final/UNRESOLVED_QUESTIONS.md`](research/final/UNRESOLVED_QUESTIONS.md) | Questions that must close before another full build |
| [`research/reviews/checkpoint-5-report-freeze.md`](research/reviews/checkpoint-5-report-freeze.md) | Final independent review and report-freeze decision |
| [`research/security-model/external-review-request.md`](research/security-model/external-review-request.md) | Cryptographic claims that still require external review |
| [`research/cryptanalysis/review-packet/REVIEW_PACKET.md`](research/cryptanalysis/review-packet/REVIEW_PACKET.md) | Transcript and hash review packet |
| [`research/reproduction/README.md`](research/reproduction/README.md) | Reproduction commands and safety boundaries |
| [`PQTC_NEXT_GENERATION_RESEARCH_PLAN.md`](PQTC_NEXT_GENERATION_RESEARCH_PLAN.md) | Normative experiment definitions, gates, and evidence rules |

## The question we are testing

The primary question is:

> Can a post-quantum-oriented Tornado Classic withdrawal be verified in one Ethereum transaction with useful cost, sufficient margin, witness hiding, and a defensible composed security argument?

If not, the research asks whether a robust two-call protocol, aggregation, recursion, or an alternative deployment environment provides a credible fallback.

Every candidate is evaluated on the complete path:

1. preserve the frozen application semantics;
2. bind the public statement and runtime parameters;
3. hide the witness without a trusted setup or classical wrapper;
4. meet the conservative security target after composition and multi-target effects;
5. produce and verify the exact proof;
6. fit calldata and transaction gas under current and prospective schedules;
7. fit runtime, initcode, and deployment limits;
8. provide acceptable prover latency, memory use, and failure behavior.

Hard gates take precedence over projections and weighted scores. `NOT_EVALUATED` means unknown, never zero.

## Frozen baseline

The baseline is the tagged v0.3 research reference:

```text
tag:    pqtc-v0.3-research-baseline
commit: 00f829001999ee66da6fd5161c4c205c07d0b937
```

Sixty fresh q32 runs reproduced the baseline:

| Metric | Result |
|---|---:|
| Median raw proof | 208,940 B |
| Median ABI calldata | 209,608 B |
| Part A active-total median | 16,664,641.5 gas |
| Part A transactions above the active cap | 9 / 60 |
| Part B active-total median | 13,959,759.5 gas |
| Part B transactions above the active cap | 0 / 60 |
| H0 direct-deposit execution gas | 13,991,021 gas |

The baseline is reproducible, but it is not a viable candidate. Its Part A path has insufficient gas margin, its calldata is large, and q32 does not support the intended conservative security claim.

The corrected q32 accounting separates three different claims:

- 107 bits: conjectural random-words estimate;
- 56 bits: conditional Johnson/list-decoding term;
- 37 bits: unconditional unique-decoding term.

External cryptographic review remains open.

## What we experimented with

### Application relation

- fixed-length Poseidon2 and Keccak-oriented compression candidates;
- width-32 unified layouts;
- binary and higher-arity Merkle trees;
- direct deposits and deferred batching designs;
- vertical/narrow AIR geometry;
- structured Boolean, R1CS, CCS, and AIR decompositions.

### Proof systems and security

- hiding FRI parameter sweeps;
- HVZK-WHIR;
- STIR and Circle readiness;
- Spartan-WHIR;
- recursive transparent compression;
- Flock and VEIL controls;
- digest width, transcript binding, continuation binding, QROM status, and multi-target accounting.

### EVM and product architecture

- transcript and verifier arithmetic changes;
- field and extension-field kernels;
- exact current and prospective calldata-gas schedules;
- aggregation;
- robust two-call state machines;
- L2 admission and economics;
- prover latency, memory, cancellation, and recovery behavior.

## What worked

These are successful research results, not approved production components:

- The v0.3 baseline was independently reproduced with retained proofs, native verification, and exact EVM simulations.
- The corpus, run schema, gas models, artifact hashing, scorecards, and report generators are deterministic and fail closed.
- H0 Merkle parity passed across 1,000 retained roots.
- The compression study retained 18,146 Rust/TypeScript vectors and Solidity anchor checks.
- Transcript and verifier experiments found useful isolated arithmetic and batching improvements.
- The field bakeoff produced reproducible component measurements across six field configurations.
- The FRI sweep evaluated 504,000 parameter rows and found 120 nondominated q111 rows at or above 100 generated-proven bits.
- The two-call state-machine harness passed its abstract safety and liveness attack tests.
- SP-91 reproduced the negative decision chain from a clean detached worktree.
- All 62 candidate scorecards, eight Pareto axes, and the final report can be regenerated deterministically.

## What did not work—or remains insufficient

- No compression candidate produced an accepted complete relation with full Rust, TypeScript, and Solidity parity plus external security review.
- The q32 baseline is below the conservative security target.
- All retained security-feasible q111 FRI frontier rows failed the robust two-call filter.
- HVZK-WHIR, STIR, Circle, Spartan-WHIR, recursion, Flock, and VEIL provided useful controls or upstream evidence, but no exact integrated PQTC backend.
- Aggregation had no eligible individual proof to aggregate.
- The robust two-call state machine was validated only as a state machine; its complete proof, calldata, and gas path remains unevaluated.
- A 210 KiB ordinary transaction was rejected by the selected OP, Arbitrum, and Scroll admission probes; the required live network study is incomplete.
- Prover evidence covers the retained H1 warm path, but cold runs, broader hardware, cancellation, and crash recovery remain incomplete.
- No candidate has an externally accepted composed security argument.
- No candidate produced a complete integrated proof, verifier, transaction, and deployment envelope.

Negative and deferred results are retained intentionally. See [`research/report-synthesis/scorecards/`](research/report-synthesis/scorecards/) and the report’s rejected/deferred-candidate section.

## Evidence model

The repository distinguishes:

- **measured:** produced by the named retained run;
- **computed scenario:** deterministically calculated from measured inputs, but not a network receipt;
- **projection:** useful for screening only;
- **benchmark-only:** an isolated component or incompatible control;
- **conditional:** depends on an unresolved assumption;
- **deferred:** stopped because a prerequisite or maturity gate was absent;
- **not evaluated:** no supported value exists.

The machine-readable evidence is organized under:

```text
research/runs/                 Run-level JSON
research/summaries/            Proof, gas, security, prover, and candidate tables
research/candidates/           Candidate manifests, status, results, and negative results
research/report-synthesis/     Scorecards, source map, weights, and Pareto datasets
research/reviews/              Formal checkpoint decisions
research/reproduction/         Offline reproduction controller and evidence manifest
research/final/                Standalone report and executive outputs
```

Every promoted numeric claim should resolve to a run ID or a hashed artifact. The final inventory is pinned by [`research/final/evidence-manifest.json`](research/final/evidence-manifest.json).

## Reproduce the evidence

Run from the repository root:

```sh
python3 research/reproduction/reproduce.py verify-manifest
python3 research/reproduction/reproduce.py all-safe
python3 research/run-records/reproduce.py check
python3 research/report-synthesis/generate.py --check
python3 research/final/generate.py --check
```

The safe reproduction path performs no live-chain actions and uses no secret inputs. Candidate-specific build, proof, and verifier commands are registered in [`research/reproduction/command-registry.json`](research/reproduction/command-registry.json).

## What would justify another full build

At minimum, future work must provide:

1. an accepted fixed application relation;
2. a hiding backend for that exact relation;
3. an externally reviewed composed security argument;
4. exact proof and ABI measurements;
5. complete verifier and transaction gas under all required schedules;
6. deployment-size and deployment-gas evidence;
7. representative prover operations evidence;
8. independent reproduction of the integrated result.

Until then, the correct action is targeted blocker-closing research—not implementation or deployment.

## Safety boundary

This repository does not authorize a v0.4 protocol, custody migration, production verifier, or deployment. Any future engineering specification requires a separate reviewed decision after the unresolved security and integration gates close.
