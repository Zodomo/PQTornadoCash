# Independent security model

This directory contains the SP-01 manifest-driven translation of the security formulas at pinned Plonky3 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`. It is deterministic Python using only the standard library. It does not import project protocol code and does not modify or endorse the frozen v0.3 implementation.

Every result is labeled `UNREVIEWED_RESEARCH_RESULT`, sets `security_qualified_candidate` to `false`, and records that independent human acceptance has not occurred. Random-words values are conjectural and intentionally disclose that Plonky3 does not model `num_batched_functions` on that path. They must not be used alone to qualify a candidate.

After two rejected rounds and six corrected findings, internal reviewer `SecurityModelReview` returned `ACCEPT_METHOD_WITH_LIMITATIONS` with no remaining code findings. External human cryptographic review remains open; see `ADR.md`, `status.json`, and `external-review-request.md`. Internal methodology acceptance is not candidate qualification.

## Run

From the repository root:

```sh
python3 research/security-model/calculator/security_calculator.py calculate research/security-model/manifests/v03-q32.json --format json
python3 research/security-model/calculator/security_calculator.py calculate research/security-model/manifests/v03-q32.json --format csv
python3 research/security-model/calculator/security_calculator.py calculate research/security-model/manifests/v03-q32.json --format table
python3 research/security-model/calculator/security_calculator.py calculate research/security-model/manifests/v03-q32.json --format table --target-count-log2 32
python3 research/security-model/calculator/security_calculator.py targets research/security-model/manifests/v03-q32.json
```

The committed `v03-q32.*`, `v02-q48.*`, and `legacy-v02-q48-width230-assumptions.*` files are generated from the corresponding files in `manifests/`. `target-profiles.json` searches buildable log-blowups 1 through 12 and queries 1 through 512 for 80, 100, 112, and 128 quantum-bit targets, minimizing queries then blowup. It reports unattainable targets rather than manufacturing a passing profile. Random-words search results retain their conjectural and actual batching-omission metadata and are explicitly excluded from target recommendations.

Focused tests:

```sh
python3 -m unittest discover -s research/security-model/calculator/tests -p 'test_*.py' -v
```

## Manifest rules

A manifest must pin the exact Plonky3 commit and state logical trace height, hiding degree padding, proof degree, AIR constraint shape, batching decomposition, FRI geometry, challenge budget, grinding, and classical/quantum MMCS binding assumptions. Validation rejects:

- non-power-of-two logical trace heights;
- a proof degree inconsistent with logical height plus hiding padding;
- challenge budgets above the stated extension-field size;
- final polynomial lengths outside the LDE fold domain, nonzero final polynomial logs not strictly below the committed proof degree, or maximum fold arities beyond the available LDE fold depth;
- zero queries, fields, constraints, or batching functions;
- non-ZK degree above `2^log_blowup + 1` and ZK degree above the tighter `2^log_blowup` limit documented by the pinned wrapper;
- an unknown `batch_count_derivation`, an explicit derivation without rationale, or a derived batch count inconsistent with relation width + quotient chunks + hiding functions.

`logical_trace_height=256`, `hiding_degree_padding_bits=1`, and `proof_degree_bits=9` are intentionally separate. All soundness formulas use the post-hiding proof degree, while output retains the logical height and padding as independently inspectable inputs.

## Output semantics

Each regime reports term formula, pinned source, concrete inputs, classical bits, quantum-adjusted bits, theorem/conjecture status, applicability, binding status, omissions, and bottlenecks sorted low-to-high. The random-words, UDR, and LDR composites take Plonky3's round-by-round minimum. Best proven security takes `max(UDR,LDR)` because those are independent valid theorem regimes.

Configured grinding is credited only at its actual site: commit grinding to the FRI commit phase and query grinding to the query phase. Classical accounting adds all configured bits. Quantum accounting adds half, matching the project's Grover-style treatment. Neither credit is silently applied to AIR, DEEP, batching, challenge, or MMCS terms.

Multi-target scenarios use a conservative union bound over `2^0`, `2^20`, `2^32`, and `2^40` potential proof-forgery targets, subtracting the target-count logarithm from each applicable per-proof term. The optional composition manifest computes `-log2(sum_i count_i * 2^-bits_i)` directly for inner and outer components; it does not replace this with a minimum. Component theorem status and omissions remain explicit.


LDR rows and any aggregate that selects LDR are machine-labeled `conditional-theorem-johnson-correlated-agreement`, with the mutual-correlated-agreement condition repeated in `assumptions`/`omissions`. If pinned `best_ldr_m` has no valid `m`, LDR is emitted as unavailable at zero bits while the independently valid UDR report is preserved.
The final-polynomial term is shown as a deterministic degree/length check with no invented probabilistic bit value. MMCS and challenge-field rows are caps. The calculator does not prove transcript binding, QROM security, zero knowledge, structural hash/field security, or implementation equivalence.
