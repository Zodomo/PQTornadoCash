# Source index

All PQTornadoCash links below are pinned to the reviewed public commit:
`e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997`.

This index identifies the source basis, not a claim that every linked file was executed or independently audited. Files read in ranges are explicitly described where that matters. The independent sensitivity code was executed; the repository reproduction commands were not executed in this review environment.

## Repository and report

- **S01 — Review pin and cleanup commit.** [Commit and changed files](https://github.com/Zodomo/PQTornadoCash/commit/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997). Latest public main at the start of review; cleanup removes only the two old-plan/report files. The final report cites earlier evidence epochs.
- **S02 — Final research report.** [NEXT_GENERATION_RESEARCH_REPORT.md](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/final/NEXT_GENERATION_RESEARCH_REPORT.md). Read across its baseline, security, spike, architecture, and decision sections. Primary source for retained counts and measurements; not independently rerun here.
- **S03 — Executive summary.** [EXECUTIVE_MATRIX.csv](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/final/EXECUTIVE_MATRIX.csv).
- **S04 — Unresolved questions.** [UNRESOLVED_QUESTIONS.md](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/final/UNRESOLVED_QUESTIONS.md).
- **S05 — Report-freeze review.** [checkpoint-5-report-freeze.md](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/reviews/checkpoint-5-report-freeze.md). Internal freeze acceptance is not cryptographic approval.
- **S06 — External security questions.** [external-review-request.md](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/security-model/external-review-request.md).
- **S07 — Reproduction instructions.** [research/reproduction/README.md](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/reproduction/README.md).
- **S08 — Governing research plan.** [PQTC_NEXT_GENERATION_RESEARCH_PLAN.md](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/PQTC_NEXT_GENERATION_RESEARCH_PLAN.md). Checked the early scope, eligibility, and target provisions relevant to the gating critique.
- **S09 — Reproduction controller and manifest.** [reproduce.py](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/reproduction/reproduce.py) and [evidence-manifest.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/reproduction/evidence-manifest.json). Read collection/validation logic and manifest entries; no claim of checking every listed hash.

## Hashes, security, and proof models

- **S10 — Exact-instance cryptanalysis packet.** [REVIEW_PACKET.md](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/cryptanalysis/review-packet/REVIEW_PACKET.md).
- **S11 — Hash experiment disposition.** [status.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/candidates/hash-compression-common/status.json).
- **S12 — Independent security-model description.** [README.md](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/security-model/README.md), with S06 for the explicit external review questions.
- **S13 — q32 term output.** [v03-q32.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/security-model/v03-q32.json). Examined the manifest and term-level LDR entries. Very large repeated scenario output was not treated as new independent evidence.
- **S14 — Calculator implementation.** [security_calculator.py](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/security-model/calculator/security_calculator.py). The independent sensitivity transcribes `_common_terms`, `_ldr_candidate`, `_batch_ldr`, and `_ldr`; it is not a substitute for the project implementation.
- **S15 — Pinned upstream regime assumptions.** [Plonky3 security/src/assumption.rs](https://github.com/Plonky3/Plonky3/blob/3152b14a89067c83775a8076cc262ffc48a1fd7c/security/src/assumption.rs). Used for the unique-decoding/Johnson/capacity distinction and explicit conditions.
- **S16 — Concrete opening/reduction representation.** [PQTCQueryVerifier.sol](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/contracts/src/verifier/PQTCQueryVerifier.sol). The visible widths and 524 reduction terms motivate a requested theorem-object mapping, not a claimed confirmed batching bug.
- **S17 — Retained hash gas evidence.** [gas/results.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/candidates/hash-compression-common/gas/results.json).
- **S18 — Generic Solidity hash kernel.** [Poseidon2Kernel.sol](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/candidates/hash-compression-common/solidity/src/Poseidon2Kernel.sol).
- **S19 — Width-32 constant dispatch.** [Poseidon32Candidates.sol](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/candidates/hash-compression-common/solidity/src/Poseidon32Candidates.sol). Inspected the beginning of the generated switch; a gas attribution is requested rather than claimed.
- **S20 — Hash artifact provenance.** [measurement-hashes.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/candidates/hash-compression-common/measurement-hashes.json), [source-hashes.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/candidates/hash-compression-common/source-hashes.json).
- **S21 — FRI model and screening code.** [research/fri-pareto/run.py](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/fri-pareto/run.py). Read projection, status derivation, dominance, and filter logic. The independent review does not claim to have executed the Cartesian sweep.
- **S22 — FRI declared grid and report results.** [grid.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/fri-pareto/grid.json). Grid dimensions and outcomes are reported in S02/S21; this link is a reproduction entry point.
- **S23 — Split optimization evidence.** [V9/outputs/benchmark.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/candidates/V9/outputs/benchmark.json) and [verifier-optimization-common/status.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/candidates/verifier-optimization-common/status.json).
- **S24 — Flock historical capacity and failure.** [batch-capacity.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/candidates/C70-flock-veil/batch-capacity.json).
- **S25 — Advisory regression artifact.** [regression-results.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/advisories/regression-results.json).
- **S26 — Field benchmark methodology.** [field-bakeoff-common/README.md](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/candidates/field-bakeoff-common/README.md) and [solidity-latest.json](https://github.com/Zodomo/PQTornadoCash/blob/e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997/research/candidates/field-bakeoff-common/outputs/solidity-latest.json). Read methodology and representative gas entries, not a full independent timing reconstruction.

## External primary references checked

- **S27 — Ethereum gas cap.** [EIP-7825](https://eips.ethereum.org/EIPS/eip-7825) and [Ethereum Foundation deployment/tooling notice](https://blog.ethereum.org/2025/10/21/fusaka-gascap-update). The cap applies to transaction gas limits; unrestricted calls are not equivalent to capped transactions.
- **S28 — Calldata repricing scenario.** [EIP-8311](https://github.com/ethereum/EIPs/blob/master/EIPS/eip-8311.md), status Draft in the inspected source. A proposal is not an activated target-chain rule.
- **S29 — Exact-mode cryptanalysis.** Merz and Rodríguez García, [Skipping Class: Algebraic Attacks exploiting weak matrices and operation modes of Poseidon2(b), ePrint 2026/306](https://eprint.iacr.org/2026/306). The abstract explicitly distinguishes improved attacks from failure of a claimed security level.
- **S30 — Proximity theory.** Ben-Sasson et al., [On Proximity Gaps for Reed–Solomon Codes, ePrint 2025/2055](https://eprint.iacr.org/2025/2055). The abstract was checked for scope; this review does not claim to prove its theorems or resolve the project's full correlated-agreement composition.
- **S31 — Newer structural attack scope.** Bhati, Tariq, Ashur, [From Round Skipping to S-Box Skipping, ePrint 2026/1692](https://eprint.iacr.org/2026/1692). Provides additional exact-instance applicability questions; it is not treated as proof that PQTC's complete mode is broken.
- **S32 — Proof-system publication identity.** Atapoor et al., [STARK-based Signatures from the RPO Permutation, ePrint 2024/1553](https://eprint.iacr.org/2024/1553), revised August 2026. A reference ID must be checked against its actual title/version and theorem statements rather than relying on informal labels in code comments.

## Independent evidence in this package

- `evidence/ldr_objective_sensitivity.py`: self-contained standard-library arithmetic, including expected-value assertions.
- `evidence/ldr_objective_sensitivity.json`: generated output.
- `evidence/ldr_objective_sensitivity.stdout.txt`: retained stdout from the run.

The script does not import the repository or prove any cryptographic theorem. Its inputs and limitations are embedded in the output.
