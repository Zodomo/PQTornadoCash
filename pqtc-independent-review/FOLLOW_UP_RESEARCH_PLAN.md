# PQTornadoCash — Targeted Experimental Integration Research Plan

**Plan version:** R2.0  
**Prepared:** 2026-09-04  
**Starting public commit:** `e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997`  
**Companion document:** `REPOSITORY_REVIEW.md`  
**Required return:** `TARGETED_RESEARCH_REPORT.md` and a reproducible machine-readable evidence package  
**Authorization:** isolated research code, local test contracts, simulations, and measurements only. No public-chain deployment, real-value custody, production release, verifier upgrade, or migration.

---

## 0. Mandate

The previous round reached a defensible `OUTCOME_D`: no candidate was sufficiently qualified to justify a new full engineering build. It also left the principal structural hypotheses untested because component qualification gates blocked experimental integration.

This round must answer a narrower question:

> Can exact changes to application compression, AIR geometry, transcript handling, and one alternative hiding proof backend materially reduce the cost of the same Classic withdrawal relation, and can at least one complete local verifier path meet a meaningful transaction envelope without disguising security assumptions?

The goal is **not** to return another list of zero deployment-qualified candidates. Zero may remain the correct qualification count. The goal is to return decisive measurements or specific falsifications for the highest-value unanswered questions.

A successful research round may end with no safe build recommendation. It must still show what was implemented, what was measured, what failed, why it failed, and which component sets the remaining limit.

Do not start a full v0.4 product, add a UI, implement Nova, expand chains, or optimize a production relayer in this round.

## 1. Required changes to the research process

### 1.1 Separate permission to measure from permission to promote

The following labels are independent:

1. **Specification status:** exact or incomplete.
2. **Correctness evidence:** untested, reference-tested, cross-language-tested, integrated-tested.
3. **Privacy evidence:** absent, intentionally non-hiding control, configured hiding, composition reviewed.
4. **Security status:** unassessed, known below target, conditional analysis, externally accepted scoped model.
5. **Performance evidence:** unknown, analytical bound, uncalibrated projection, calibrated projection, measured.
6. **Implementation stage:** primitive, relation, native proof, EVM verifier, local complete transaction.
7. **Promotion status:** never inferred from the above automatically; no deployment authorized here.

An exact, reference-correct but unreviewed compressor may be measured in an isolated local proof experiment. It must retain `SECURITY_NOT_QUALIFIED` on every artifact. A non-hiding backend may be measured only as a clearly separated lower-bound/control experiment. It cannot satisfy the privacy portion of a complete candidate result.

External cryptographic review is required before a security claim or deployment recommendation, **not before all performance work**. Run the external review packet in parallel.

### 1.2 Preserve the frozen evidence

- Do not edit v0.3 in place.
- Do not overwrite the previous report, raw runs, candidate statuses, or generated security figures.
- Implement fixes in `research/r2/` or isolated worktrees with distinct source commits.
- Every protocol-affecting research variant receives a new experimental configuration ID.
- Historical output can be annotated or superseded, but never silently regenerated to erase a failed result.
- Reusing an upstream pin is permitted; silently moving it is not.

### 1.3 No metadata-only completion for an executable spike

A status file is not the deliverable for a work package whose acceptance criteria require execution.

A spike is complete only by one of these routes:

- the required experiment executes and returns its measurements;
- a concrete correctness/security counterexample falsifies the exact candidate;
- a minimal reproducer establishes a tool/API/algorithm barrier and the report includes a bounded repair attempt or a reason repair is outside scope;
- an explicitly reviewed resource limit terminates it, with a quantified remaining task.

`NOT_EVALUATED_BECAUSE_NOT_QUALIFIED` is not an acceptable stopping reason for R2's local performance controls.

### 1.4 Retain the original safety constraints

No elliptic-curve/pairing/KZG/IPA/Groth16 wrapper. No trusted verifier service. No note-witness disclosure to an untrusted aggregator. No non-hiding proof represented as private. No relaxed security parameters presented as preserving security. No public network signing or deployment. No unsupported upstream configuration guessed merely to make a benchmark run.

---

## 2. Research questions and required answers

### RQ1 — How much of the hash cost is implementation overhead?

Compare the same H0 permutation/sponge in the generic harness and production-quality implementation, then optimize H5/H6 to a comparable implementation tier. Attribute arithmetic, constants, loops, memory, canonicality, and ABI work. Do not extrapolate a generic kernel into a practical deposit result.

### RQ2 — Does vertical AIR geometry help independently of a new hash?

Prove the existing H0 relation with a narrow vertical AIR. Hold application semantics and initial proof parameters fixed. This question must be answered even if no new compressor is externally accepted.

### RQ3 — Does a complete fixed-compression Classic relation help?

Finish scope, note, nullifier, node, empty-leaf, and statement semantics for one candidate. Prove that exact relation in both horizontal and vertical forms, or report the exact reason one form cannot be implemented within the approved scope.

### RQ4 — Can transcript and verifier changes produce integrated savings?

Implement challenge-boundary framing, full-width continuation binding, and selected arithmetic/codec improvements. Verify a complete proof and measure the resulting call. Kernel deltas alone are insufficient.

### RQ5 — What do the security formulas actually establish?

Check the free analytical parameter `m`, actual batching count, theorem conditions, term composition, and lifetime models. Produce both pinned-equivalent and corrected/alternative analyses. Do not relabel a conditional improvement as a complete quantum proof.

### RQ6 — Does hiding WHIR or structured Spartan–HVZK-WHIR improve this relation?

Move beyond a width-12 upstream smoke. Establish an exact adapter/lowering and generate a hiding proof of the same Classic statement. Measure a complete EVM path if the native and API gates pass.

### RQ7 — What is the best complete local operational envelope?

Return exact one-call and/or two-call transactions, proof bytes, deployment measurements, state behavior, and worst-case bounds. A robust two-call path may remain the best result. A source-derived projection is not a complete transaction.

### RQ8 — What blocks a new full engineering specification?

The final answer must identify whether the remaining barrier is an exact hash-security question, a PCS soundness bound, witness hiding, a lowering, verifier computation, calldata, constructor cost, state mechanics, or insufficient evidence. “No candidate passed” alone is not enough.

---

## 3. Candidate set: small, causal, and versioned

### 3.1 Mandatory core comparisons

Use these logical identities; actual IDs also include source/parameter hashes.

| ID | Application relation | AIR/backend | Purpose |
|---|---|---|---|
| R2-C0 | Frozen H0/P2BB512 v0.3 | frozen horizontal FRI | reference only, not qualified |
| R2-C1 | Exactly H0/P2BB512 v0.3 | vertical low-degree FRI | isolate geometry |
| R2-C2 | Complete H5-like width-32/d12 relation | horizontal FRI | isolate hash/relation change |
| R2-C3 | Same relation as C2 | vertical low-degree FRI | combined structural candidate |
| R2-C4 | H0 or selected complete compression relation | hiding WHIR or structured HVZK-WHIR pipeline | backend comparison |

Do not create 50 more candidate IDs for minor parameter points. A candidate has parameter runs beneath it. Distinguish a pipeline, a parameter configuration, an implementation revision, and an individual measured run.

### 3.2 Secondary candidates

H6-like width-32/d14 is an optional security-margin comparator after H5 semantics and matched-tier measurements exist. H3/H4 may be reopened only if a bounded exact-instance review or optimized width-24 measurement gives a reason. H1 remains a below-target negative control. H2 remains a design gap, not a failed architecture. H7 remains a separate sponge/arithmetic control.

Flock, STIR, Circle, recursion, aggregation, and L2 work receive conditional entry gates later in this plan. They do not block C1 or C3.

### 3.3 Configuration identity

Each configuration must pin:

- semantic relation ID;
- application hash mode and constants digest;
- all role layouts and encodings;
- field and extension polynomial/basis;
- AIR source and derived shape;
- PCS/LDT and hiding mode;
- MMCS and transcript versions;
- proof codec;
- soundness parameters;
- implementation tier and optimization flags;
- toolchain and dependency pins.

Use separate application and proof-system identifiers in research metadata. Do not redesign a production pool's upgrade model in this round. A local harness can evaluate the same semantics under multiple verifiers without authorizing mutable custody.

The frozen v0.3 scope already embeds its old parameter ID. For a pure C0/C1 predicate comparison, hold that application scope and public statement fixed while the experimental verifier configuration is separately bound in the new proof transcript. This is a local verifier experiment, not acceptance by the old immutable pool. For complete local pool tests, instantiate the new experimental context and regenerate its scope, commitments, roots, and notes; compare equivalent abstract scenarios rather than claiming byte-identical roots. This distinction must not become a hidden migration or verifier-upgrade feature.

---

## 4. Common evidence model

### 4.1 Required measurement status enum

Use:

```text
NOT_EVALUATED
EXECUTION_BLOCKED
MEASURED
EXACT_ANALYTICAL_BOUND
CALIBRATED_PROJECTION
UNCALIBRATED_PROJECTION
OUT_OF_MODEL_DOMAIN
NOT_APPLICABLE
```

A value is null unless the declared class supports a number. Zero is reserved for a measured or derived zero.

### 4.2 Required decision status enum

Use:

```text
CONTINUE_EXPERIMENT
REPEAT_MEASUREMENT
DEFER_EXTERNAL_REVIEW
REJECT_EXACT_CANDIDATE
STOP_ENGINEERING_BARRIER
STOP_RESOURCE_LIMIT
READY_FOR_CROSS_CANDIDATE_COMPARISON
NOT_READY_FOR_BUILD_SELECTION
```

`REJECT_EXACT_CANDIDATE` requires an explicit falsifier or an exceeded accepted limit with valid evidence. Missing external review is `DEFER_EXTERNAL_REVIEW`, not a claim of mathematical failure.

### 4.3 Separate physical, product, and security gates

For each candidate, record three separate assessments:

1. **Physical execution:** current target-chain rules, gasLimit, code/initcode limits, transaction admission.
2. **Product target:** preferred gas margin, byte budget, latency, proving time, number of calls.
3. **Security/privacy:** exact assumptions, bounds, zero knowledge, external review.

A measured benchmark can pass physical execution and fail security. That is useful evidence, not permission to deploy. A benchmark can fail a draft repricing scenario but pass today's protocol. Preserve both results.

### 4.4 Required stop-reason class

Every stop must be categorized as:

- proven/constructed security failure;
- incomplete security analysis;
- reference-correctness failure;
- incomplete application semantics;
- measured performance failure;
- analytical impossibility within stated assumptions;
- uncalibrated model prediction;
- missing software/API/configuration;
- licensing/access limitation;
- resource/budget limit;
- project-policy decision.

This prevents the final report from treating administrative deferral, missing work, and a cryptographic break as the same outcome.

---

## 5. Shared workload and controls

### 5.1 Freeze semantic cases, not backend-native trace objects

Each case must include:

- chain and pool context used by the local experiment;
- denomination and version;
- note secret and trapdoor in a canonical experimental representation;
- full note/commitment derivation;
- deposit index;
- ordered tree state or a complete regenerating seed and algorithm;
- Merkle path and path directions;
- nullifier;
- recipient, relayer, and fee;
- exact expected public statement;
- whether the case is public synthetic test data.

All retained witnesses in the research package must be **synthetic and explicitly not funded**. Do not upload real users' notes.

### 5.2 Preserve semantics across the core comparison

C0 and C1 must accept the identical H0 statement and witnesses. C2 and C3 must accept the identical new statement and witnesses. Cross-hash comparisons share the abstract tree/deposit/payout scenario but have different commitments and roots; do not call those roots equal.

For BabyBear-native cases, canonical eight-field secrets can be retained to isolate the hash/AIR comparison. Report their actual entropy. Do not silently map arbitrary 256-bit strings modulo the field. An alternate-field experiment must specify its own injective/rejection-sampled encoding and security consequences.

### 5.3 Workload strata

At minimum:

- fixed witness with fresh proof randomness;
- random notes and paths;
- first/early deposit;
- indices near powers of two and frontier transitions;
- later tree positions generated without allocating a full million-leaf tree unnecessarily;
- all-zero/all-one path-direction patterns where semantically valid;
- roots containing many deposits;
- zero and nonzero relayer fees;
- fee near the denomination;
- canonical field boundaries and byte encodings;
- valid proof-query patterns with low/high frontier overlap.

Do not force verifier-selected query indices in a proof and call it valid. Artificial query sets may be used for verifier-bound analysis, clearly separated from full transcript-valid proofs.

### 5.4 Two comparison modes

**Fixed-parameter mode:** hold queries, blowup, hiding, and commitment policy fixed where the algorithms permit. This isolates implementation and geometry effects. Report any resulting soundness change.

**Security-normalized mode:** select profiles under the same declared security model and target. Report conditional/unconditional model differences explicitly. Do not compare a weak q32 proof to a stronger candidate and attribute all cost to the backend.

Both modes are required. Neither replaces the other.

---

## 6. Work package R2-00 — Provenance and executable baseline

**Goal:** make the latest public handoff reproducible and establish the baseline ledgers needed for all later decisions.

### Inputs

- Public commit `e51a5c5…`.
- Final report and evidence manifest.
- Existing 60 baseline records and proof artifacts/regenerators.
- Current source, dependency locks, and reproduction commands.

### Implementation tasks

1. Create a clean checkout of the pinned public commit.
2. Run all five handoff checks and retain command, cwd, exit status, stdout/stderr, environment inventory, and artifact hashes.
3. State which checks are metadata-only. Do not label `all-safe` as proof verification.
4. Build the frozen code with pinned tools in a clean environment.
5. Verify a retained proof natively and in the complete EVM harness.
6. Generate at least ten fresh baseline proofs as a clean-environment smoke. Do not overwrite the 60 retained runs.
7. Produce a relationship table for report, measurement, source, public cleanup, and reproduction commits.
8. Verify that deletion of excluded historical files does not affect the pinned package; record the actual command outcome rather than assuming failure or success.

### Required byte ledger

Instrument the canonical parser. For every proof, report exact bytes in:

- ABI and transaction envelope;
- common/public header;
- repeated global data;
- commitments;
- out-of-domain openings;
- quotient and random openings;
- hiding salts/mask openings;
- initial row openings;
- initial MMCS frontier;
- each FRI round's values, salts, and frontier;
- final polynomial;
- grinding witnesses;
- checkpoint/proof identifiers;
- terminators and alignment.

The section totals must sum exactly to the complete serialized proof and ABI lengths. Shared fields and repeated A/B data must be distinguished. A parser failing that sum fails the ledger gate.

### Required gas ledger

Measure and attribute:

- parse/canonicality;
- transcript hashing and challenge sampling;
- AIR evaluation;
- OOD/quotient identities;
- alpha powers and opening aggregates;
- inverse calculations;
- row reductions;
- MMCS hashing/path handling;
- FRI arithmetic;
- checkpoint storage/deletion;
- public-statement reconstruction;
- nullifier write;
- payout calls;
- transaction intrinsic/calldata floor.

Use actual instrumentation and opcode/call traces. Report overlapping measurements rather than summing them as if independent.

### Deployment measurement

Run a **top-level local signed CREATE transaction** under the target gas cap, separately from an unrestricted internal Foundry measurement. Retain initcode bytes, runtime bytes, calldata/intrinsic, code-deposit cost, constructor execution, storage initialization, and result. Never use an unrestricted `eth_call` as proof of capped transaction feasibility.

If deployment fails, retain the failing receipt/simulation and decompose the required initialization. Do not change constructor semantics yet; that belongs to R2-08.

### Exit gate

Pass when baseline artifacts, ledgers, and clean-environment command records agree. Failure to reproduce is a high-priority blocker for comparative claims, not grounds to erase old measurements.

---

## 7. Work package R2-01 — Security-model correction and sensitivity

**Goal:** establish what the existing formulas prove, what they assume, and which analysis choices are unnecessarily pessimistic or optimistic.

### 7.1 Three calculators, one evidence table

Retain:

1. the exact pinned upstream-equivalent path;
2. the project's independent translation;
3. a separately versioned sensitivity/alternative analysis.

Do not change the first two to hide disagreements. Every row must identify its formula version.

### 7.2 Optimize the correct objective

Reproduce the supplied independent `ldr_objective_sensitivity.py` outputs. Then implement a reviewed full-objective selector over allowed `m` values.

For every `m`, retain:

- proximity preconditions;
- list size and alpha/gamma;
- AIR term;
- DEEP term;
- FRI commit and query terms;
- batching term, including dominant and full-expression variants where supported;
- challenge and MMCS caps;
- selected theorem regime and its conditions;
- the recorded aggregate and, separately, an arithmetic error-sum sensitivity.

Compare the FRI-only optimum with the full-model optimum at q32, q48, q64 and at candidate profiles. State whether `m` is purely analytical or affects any runtime parameter. A claimed zero-runtime improvement requires showing that proof generation and verification are unchanged.

### 7.3 Map the actual batching objects

Generate a structured inventory from the native PCS:

- each commitment and matrix;
- base-field width and height;
- extension decomposition;
- hiding columns and separate random commitments;
- opening points/rotations;
- random-linear-combination coefficients;
- quotient chunks and their coefficient columns.

Map that inventory to the exact theorem's `num_batched_functions` parameter. Explain the relationship among 210 nominal functions, 330 visible base-column entries where applicable, and 524 reduction terms. Do not replace a count mechanically. Provide the derivation, regression tests, and a reviewer question if the theorem's object remains ambiguous.

### 7.4 Clarify the security games

Create one sheet per game:

- secret recovery for any funded note;
- useful commitment collision and double spending;
- false accumulator membership;
- nullifier aliasing;
- proof forgery;
- A/B continuation substitution;
- witness indistinguishability;
- inner/outer proof composition.

Each sheet states the adversary, public inputs, oracle access, query/work budget, number of targets, advantage bound, source assumptions, and lifetime interpretation.

Separate probability bounds from attack work factors. Distinguish no-Johnson-condition UDR analysis from unconditional security of a hash-based NIZK. Do not call a lower bound an exhibited attack.

### 7.5 Review round-skipping and mode security

Build an exact-instance attack matrix for H0/H5/H6 and any reopened H3/H4 mode:

- field and extension, if any;
- width and S-box exponent;
- matrices and constants;
- full/partial rounds;
- variable/fixed input lanes;
- feed-forward positions;
- truncation/output lanes;
- domain/control framing;
- preimage/collision/CICO goal;
- applicable attack version;
- computed cost and memory assumptions;
- measured reduced-instance evidence;
- safety margin relative to the chosen target.

Use `APPLICABLE_COST_UNKNOWN` when only applicability is known. A paper reporting a speedup does not supply a security bit level by itself.

### 7.6 Deliverables and gate

Deliver `SECURITY_MODEL_REVIEW.md`, generated term tables, tests, counterexamples, and a focused external-review request. All unresolved QROM and primitive assumptions remain visible.

**Pass for research continuation:** formulas and object mapping are explicit and tested; unresolved conditions are named.  
**Pass for security qualification:** only a scoped accepted analysis, not granted automatically here.  
**Stop an exact candidate:** a demonstrated below-target attack or unrepairable relation flaw, with evidence.

This work runs in parallel with R2-02 through R2-07. It does not block their non-custodial measurements merely because external review is open.

---

## 8. Work package R2-02 — Complete hash semantics and matched-tier implementation

**Goal:** determine whether fixed compression is useful after controlling for correctness, scope, and implementation quality.

### 8.1 Required exact constructions

- H0 frozen application sponge as the control.
- H5-like width-32, 12-output feed-forward compression as the primary new relation.
- H6-like width-32, 14-output mode only as a bounded margin comparator after H5 is complete.

Freeze separate research identifiers. Do not reuse incomplete prior H5 vectors as if they were the new complete protocol.

### 8.2 Role specification

For each role, specify the full permutation input, constants, and output extraction:

- scope/context derivation;
- note commitment;
- nullifier;
- empty leaf;
- Merkle parent with level;
- statement/payout binding;
- any proof-system role, if the primitive is reused there.

Write a table of every input lane. Include padding/fixed lanes and their constraints. Prove encoding injectivity over the allowed typed messages or provide a precise argument and tests. Use distinct domains; do not assume four reserved lanes are universally necessary or sufficient.

The primary width-32/d12 layout hypothesis is:

```text
node:       left[12] | right[12] | controls[4] | fixed[4]
note:       scope[12] | secret[8] | trapdoor[8] | controls[4]
nullifier:  scope[12] | secret[8] | controls[4] | fixed[8]
```

This is an experimental layout to review, not an approved hash scheme. Define scope and empty-leaf derivation separately; the first implementation may use a reviewed multi-block framing for public-only context if one permutation cannot encode all metadata safely. Do not force an unsafe one-permutation claim for every role just to meet an operation-count target.

### 8.3 Constants and parity

1. Regenerate constants from the documented script and parameters.
2. Compare every round constant and matrix entry with the pinned source.
3. Retain script, command, output, hashes, and a machine-readable comparison.
4. Maintain an independent simple reference implementation.
5. Run at least 10,000 shared random/edge vectors through Rust, TypeScript, and Solidity, in bounded chunks.
6. Stream large corpora rather than requiring one huge in-memory JSON object.
7. Compare complete role outputs, not only primitive permutations.

### 8.4 Required misuse suite

Reject or distinguish every relevant mutation:

- role/domain swap;
- scope or parameter-context swap;
- payload length/count mismatch;
- level change;
- child order swap;
- note/nullifier reinterpretation;
- malformed field encoding;
- field value at/above modulus;
- altered secret/trapdoor width;
- endian swap;
- fixed-lane mutation;
- wrong feed-forward lane;
- wrong truncation;
- empty-leaf/node confusion;
- scope omitted from any role that requires it.

Tests must call the actual implementation. An external expected-label oracle is not a replacement for an implementation-level rejection or changed digest.

### 8.5 Implementation tiers

Implement each selected hash at two tiers:

- **Reference tier:** simple, obviously traceable arithmetic.
- **EVM tier:** fixed-size state, specialized constants, bounded unchecked arithmetic where justified, efficient reductions, and no avoidable giant per-round switch traversal.

For H0, measure both generic and existing optimized implementations under the **same** harness. This calibration quantifies how much earlier results reflected implementation style.

For H5/H6, test at least two constant-access strategies, such as generated straight-line round code versus packed/indexed constants. Retain disassembly/opcode attribution before claiming the switch caused a particular cost.

### 8.6 Benchmarks

Measure permutation, compression, each role, twenty-level hashing, complete deposit, and constructor initialization. Use identical ABI and state accounting for comparable complete operations.

Record:

- gas by operation;
- arithmetic/dispatch/memory/call breakdown;
- runtime/initcode bytes;
- deployment gas;
- native latency and code size;
- operation and permutation counts;
- validity of the cryptanalytic model;
- exact semantic omissions, if any.

### Gate

A new hash becomes **research-relation eligible** after complete semantics, constants parity, reference correctness, and misuse tests. External security review may remain open.

It becomes a **cost success** only on measured complete operations, not by multiplying a primitive number by twenty. Failing the preferred 4M deposit target is recorded, but does not automatically block studying its withdrawal proof or a batched-deposit architecture.

Stop after the primary H5 comparison and at most one H6 comparison unless the review identifies a specific reason to expand. Do not reopen every algebraic hash family in this round.

---

## 9. Work package R2-03 — Vertical AIR control using H0

**Goal:** answer the geometry question without any dependency on new hash approval.

### Required implementation

Implement an AIR for the exact existing H0 sponge withdrawal relation with a narrow, multi-row permutation schedule. Preserve:

- note and nullifier preimages;
- scope and domain framing;
- all sponge absorb/squeeze steps;
- twenty-level path semantics;
- public statement and payout binding;
- secret representation;
- witness hiding.

The reference is the frozen horizontal AIR, not a newly simplified host function.

### Initial geometry search

Use a bounded design set:

1. whole-round vertical state;
2. small lane-group schedule;
3. one lower-degree S-box decomposition variant.

Choose no more than three initial geometries before real proof-size measurement. Expand only if the data identifies a specific tradeoff.

For `x^7`, specify actual intermediates and degree bounds. Example identities may use `a=x^2`, `b=a^2`, and `y=x*a*b`, but degree-three constraints, additional intermediate columns, and transition gating must be included in symbolic degree accounting. Do not claim all constraints are degree two merely because the S-box can be decomposed.

### Required correctness checks

- Reference host computation versus horizontal trace versus vertical trace.
- Every row's phase, round, domain, carry, and workspace update.
- Same secret used for nullifier and commitment.
- Boolean path bits and private index consistency.
- Every level's child ordering.
- No unconstrained unused/padding rows.
- Exact public-input binding.
- Mutations before, at, and after every phase boundary.
- Symbolically derived degree, constraint count, and committed widths.

### Measurements

Generate actual hiding proofs at fixed research parameters first. Report:

- logical and masked trace height;
- main/preprocessed/auxiliary widths;
- number and degree of constraints;
- quotient chunks;
- actual commitment/opening inventory;
- random codewords/salts;
- exact proof bytes by section;
- prover time and RSS;
- native verifier time;
- generated AIR evaluator runtime and gas where available.

Then run the security-normalized profiles from R2-01. Record any profile that becomes unbuildable after hiding expansion.

### Gate

The minimum completed result is one correct vertical H0 hiding proof and its byte ledger. A larger/slower result is a valid negative experiment. An unimplemented AIR because H0 is not security-qualified is not completion.

Promote a geometry for C3 only if measured proof/opening or verifier savings justify its complexity. Do not mandate a particular percentage if a smaller gain unlocks a meaningful whole-path improvement; report the predeclared target and actual value separately.

---

## 10. Work package R2-04 — Complete compression relation and causal comparison

**Goal:** combine the exact R2-02 hash relation with the best bounded geometry from R2-03.

### Required comparisons

C2 and C3 must share identical application semantics. Produce the 2×2 comparison table in Section 3, at both fixed-parameter and security-normalized settings.

### Designs

- Horizontal compression AIR: one complete permutation per row where supported, including all controller constraints.
- Vertical compression AIR: round/lane schedule from R2-03, adapted to the wider exact permutation.
- All role inputs, fixed lanes, output extraction, and feed-forward additions must be constrained.
- Do not treat one correctly proved permutation as proof of a correctly linked Merkle path.
- Bind the whole statement, not only root and nullifier.

### Public-only context optimization

Evaluate the payout/context binding separately:

- original application-hash payout digest;
- public fixed-width fields bound directly in the transcript;
- EVM-computed conventional digest mapped injectively into public values.

Only one of these should be integrated into the comparison first. It must have an explicit statement-binding argument. Public values do not need unnecessary private computation, but cannot disappear from Fiat–Shamir or be accepted under multiple encodings.

### Gate

Complete reference correctness, a full hiding proof, byte ledger, native verification, and an EVM cost prototype. The initial local verifier may use a test harness without custody. A mocked proof verifier does not count.

The final comparison must answer:

- how much came from fewer application permutations;
- how much came from narrower rows;
- how much came from lower degree/quotient changes;
- how much came from public statement changes;
- what extra prover cost was paid;
- what security assumptions changed.

---

## 11. Work package R2-05 — Transcript, codec, and verifier integration

**Goal:** turn the useful T3/V1–V9 component results into real whole-path evidence.

### 11.1 Transcript state machine

Implement explicit phases for every Fiat–Shamir dependency boundary. A phase specifies:

- required typed messages;
- permitted count/length;
- order;
- challenge(s) produced;
- transition to the next phase.

The API must reject sampling before mandatory observations and reject missing, duplicate, reordered, or cross-phase frames. Both runtime checked and type-state APIs are acceptable if serialization interoperability remains testable.

Keep message arrays batched only within a challenge epoch. Never absorb data after a challenge when the security proof requires it before that challenge.

### 11.2 Cross-language transcript tests

Retain canonical bytes, state before/after, accepted field samples, rejected samples, extension coefficient order, and query indices. Run Rust, TypeScript, and Solidity on the same vectors. Exercise boundaries around frame length, empty arrays, repeated types, phase reset, noncanonical values, and rejection sampling.

A mutation test must exercise the real transcript implementation, not merely compare externally supplied labels.

### 11.3 Full-width continuation bindings

For the two-call experiment, authoritative statement/global/checkpoint/proof commitments must preserve the selected full binding width. A 32-byte map key can be an index, but it must not silently replace the full commitment where collision resistance is relied on.

Store/check both halves, or provide a reviewed argument that a particular key requires only a different security property. Widen every dependency in a consistent versioned encoding. Demonstrate that changing either half invalidates completion.

### 11.4 Arithmetic and memory changes

Choose at most three promising existing kernel improvements for integration first:

- typed transcript batching;
- fused parsing/canonicality/reduction;
- streamed or reused alpha accumulation;
- checked inverse witnesses;
- removal of duplicate array copies;
- fixed-size scratch reuse;
- reuse of query-point computations.

Each change must have a differential test and a measured full-path delta. An inverse witness must be checked against the correct nonzero denominator; supplying an inverse is not an authorization to skip field checks.

### 11.5 Codec correctness

Measure raw bytes, ABI bytes, signed envelope bytes, zero/nonzero distribution, canonicality checks, and parse gas. Preserve exact count bounds and reject trailing data. If a digest-width variant is measured, treat it as a separate cryptographic configuration and maintain explicit unqualified status pending its binding analysis.

### Gate

At least one complete valid proof must pass native and Solidity verification under the new transcript/codec, and the mutation corpus must fail. Report actual one-call and two-call costs. Do not sum microbenchmark savings into a claimed complete transaction.

---

## 12. Work package R2-06 — Repair the parameter/Pareto methodology

**Goal:** use models to prioritize measurements, not to manufacture impossibility claims.

### 12.1 Status repair

Remove the hard-coded implication `not measured → TWO_TX_FAIL`. Preserve historical outputs and provide a migration/explanation table. Separate modeled gate results, physical measured results, and qualification.

### 12.2 Exact byte model

Build the model from the real codec and proof geometry:

- each opened row width;
- actual quotient and masking matrices;
- repeated openings and rotations;
- FRI arity-dependent sibling count;
- final polynomial length;
- cap size and exact/deduced frontier sharing;
- canonical framing and ABI overhead.

The parser's ledger must validate the formula at measured anchors. A formal lower bound may ignore positive terms but must be labeled as such; an empirical regression is not a lower bound.

### 12.3 EVM cost model

Separate:

- prover domain-size work;
- verifier query-count work;
- Merkle authentication depth;
- opened column reductions;
- FRI fold arithmetic;
- fixed transcript/AIR overhead;
- state and payout.

Do not multiply total verifier gas by the LDE size merely because prover FFT work grows that way. Fit coefficients only where the model structure is justified and retain residuals and validation points.

### 12.4 Bounded anchor grid

Start with no more than twelve actual proof anchors per selected relation. Include:

- the baseline q32 and q48 shapes;
- the first no-Johnson-condition profile near the target according to the reviewed calculator;
- one conditional-model profile where accepted for measurement;
- at least two blowups;
- one alternate final-polynomial length;
- one alternate folding arity only if implemented correctly;
- one relevant cap/codec variant.

Use adaptive selection after the first anchors. Do not generate another half-million-row table before a small model has predictive validity.

### 12.5 Security and cost optimization

Optimize analytical `m` independently of protocol choices. Then search protocol parameters under explicitly named security models. Report Pareto sets separately for:

- unqualified fixed-parameter performance controls;
- no-additional-Johnson-condition analysis;
- conditional Johnson analysis;
- accepted externally reviewed model, if available.

Never rank conditional and unconditional quantities as a single scalar without preserving the assumption distinction.

### 12.6 Bounded field/extension continuation

After a real narrow relation supplies exact arithmetic and byte counts, choose at most one alternate challenge-extension or base-field path for an integrated comparison. Use the existing F0–F5 kernels as diagnostic inputs, not as a ranking result. Repeat the relevant dot-product, inversion, and FRI-fold workloads with warmup and meaningful sample duration.

Prefer first separating extension-degree changes from base-field changes. A larger challenge extension over the same base field may preserve the application hash, but needs a supported, independently checked irreducible polynomial/basis and a complete PCS implementation. A different base field changes the native hash instance unless the original computation is emulated non-natively. Report this explicitly, including new constants, role encodings, proof bytes, and cryptanalysis obligations.

The field experiment passes only with a complete native proof and an EVM arithmetic/codec measurement for its actual geometry. If omitted because the current field is not the measured bottleneck, retain the quantitative reason. Do not let a six-way field port delay the mandatory geometry and full-path experiments.

### Gate

A model used to eliminate a candidate must either have a rigorous bound or be validated within its stated domain and only support a prioritization decision. Any point outside calibration becomes `OUT_OF_MODEL_DOMAIN`, not a fabricated measured failure.

---

## 13. Work package R2-07 — One exact hiding alternative backend

**Goal:** make at least one alternative proof backend answer the same relation question.

### Preferred branch

Hiding WHIR / structured Spartan–HVZK-WHIR. Start from the already executed upstream hiding PCS smoke, but do not carry its synthetic width-12 benchmark into the candidate matrix as a complete withdrawal result.

### Stage A: API and theorem fit

Produce an adapter design containing:

- relation representation;
- PIOP and constraint closure;
- PCS interface;
- hiding mechanism for every witness-dependent oracle/message;
- transcript boundaries;
- parameter derivation;
- exact pinned dependency graph;
- Solidity verifier requirements;
- license inventory.

Resolve whether an AIR can use the available PCS directly. If not, specify a structured lowering to R1CS/CCS/multilinear constraints. Generic sparse-matrix closure is not the default. Every matrix evaluation claim still needs correct closure.

### Stage B: same-relation native proof

Prove either exact H0 first or the completed C2/C3 application relation. Retain public/witness equivalence tests against the reference function. Produce real hiding proof bytes, native verification, malformed-proof tests, and security term tables.

### Stage C: EVM kernel and full-verifier path

Build only the components needed for this relation. Measure extension arithmetic, commitment verification, sumcheck/zerocheck, transcript, and constraint closure, then integrate. Modularization for code-size limits is allowed; a classical wrapper is not.

### Explicit stops

- Missing package/API: minimal reproducer plus a bounded adapter attempt.
- Unsupported security parameters: exact parameter derivation failure, not guessed presets.
- Hiding does not compose: document which witness-dependent value remains exposed; keep the non-hiding result as a lower bound only.
- Solidity script fails before execution: retain failure and repair the harness if bounded; do not call it a gas failure.
- License unclear: report that limitation without giving a legal conclusion. Request an appropriate review before incorporating the dependency into a distributable candidate.

### Gate

The desired completed result is a real hiding Classic proof and a complete local EVM verification measurement. A blocked branch must return a specific minimal barrier, not `NO_ELIGIBLE_HASH`. Its performance experiment may use an explicitly unqualified but fully specified hash relation.

---

## 14. Work package R2-08 — Complete local operational prototypes

**Goal:** obtain a definitive measurement for at most two selected pipelines.

### 14.1 Local harness, not a new product

Create a minimal non-production local ETH-like test pool or an existing-pool adapter with actual cryptographic verification. Preserve fixed denomination, known-root membership, nullifier consumption, recipient/relayer binding, and atomic final payment. It may be deployed only to a local disposable chain using public test keys and no valuable assets.

Do not add governance, upgrades, token support, frontend, or production deployment scripts.

### 14.2 One-call path

Construct one canonical complete proof transaction. Include exact ABI, intrinsic cost, actual execution, all calls, storage, and payout. Verify through a top-level local transaction under the protocol cap. Report both the current physical cap and the original project targets.

If the one-call proof exceeds a cap, preserve the full payload and trace. Do not split it silently and continue to label it one-call.

### 14.3 Two-call path

Measure actual splits rather than only projections. Start with a small predeclared set selected by existing V9 evidence, such as 12/20 and 14/18 for a 32-query control, plus a balanced-work split for the stronger profile. Query counts may differ for the selected protocol; split by actual verified work.

Implement:

- fixed consumer binding;
- one active checkpoint per statement/nullifier according to an explicit policy;
- full authoritative digest comparison;
- expiry/replacement;
- permissionless cleanup or a bounded storage/economic argument;
- rollback on failed proof or failed payout;
- stale-root handling;
- deterministic continuation semantics.

A normal withdrawal must remain no more than two calls. Exceptional cleanup is reported separately and cannot authorize value movement. Part A is not a complete proof of knowledge. Do not permanently reserve or consume a nullifier after a prefix. Model malicious prefixes that cannot finish, competing valid proofs, and replacement races; a one-slot policy must not let an adversary indefinitely censor the legitimate final withdrawal.

### 14.4 Deposit and constructor

Measure complete deposits over frontier-relevant indices. Test zero-tree precomputation or code-embedded constants only under an exact scope/domain argument. A scope-specific zero tree cannot be replaced with global constants without specifying why semantics remain correct or explicitly declaring a new version.

Separate stateless verifier fingerprints from deployment manifests where immutable parameter IDs would otherwise create a circular runtime-hash dependency.

### 14.5 Worst-case analysis

Retain:

- conservative maximum serialized lengths;
- maximum frontier bounds for the exact multiproof algorithm;
- maximum loops/allocations;
- worst reachable gas by branch;
- storage-state-dependent costs;
- maximum declared gasLimit needed, not only receipt gas after refunds.

Generate high-frontier and duplicate-query tests. Bound malformed proofs separately from valid ones. A sampled maximum is not a theorem; label both.

### Gate

A pipeline reaches `COMPLETE_LOCAL_MEASUREMENT` only with an actual cryptographic proof, exact complete call(s), source-bound bytecode, deployment measurement, state/payout tests, and a byte/gas ledger.

It may still be `SECURITY_NOT_QUALIFIED`. That is an acceptable research result and must not be promoted to public deployment.

---

## 15. Work package R2-09 — Conditional branches, not another broad reset

### 15.1 Recursion

Enter only if a complete inner hiding proof exists and direct verification remains the measured bottleneck.

Prove verification of that exact proof, not Fibonacci. The outer witness inventory must exclude note secrets and unmasked application traces. A non-hiding outer proof is considered only with a written composition argument showing that revealing its witness-dependent information exposes no more than the already-ZK inner proof and public data.

Use an adequately parameterized inner proof. Recursion does not strengthen an inner proof that can already be forged. Account for both errors and all transcript/commitment assumptions.

### 15.2 Flock/VEIL

Enter only after bounded source/configuration repair can execute a Keccak control. The retained failure is specifically a missing `M21_FAST_SECURITY_CONFIG` for the historical padded batch. Obtain an upstream-supported configuration or a reviewed parameter derivation; do not invent a preset.

Retain the 44 logical permutations, 48 supported capacity permutations, and four dummy computations as distinct counts where that source geometry remains applicable. Measure the exact glue relation and hiding overhead before quoting throughput for a withdrawal. No cross-user witness pooling.

### 15.3 STIR/Circle

Retain source-watch and non-hiding controls. Enter a complete candidate only with a concrete hiding construction or a justified already-ZK-inner-proof wrapper. Do not block the mainline while waiting for upstream features.

### 15.4 Aggregation

Enter only when one complete individual hiding proof and a plausible outer proof path exist. Start with N=2,4,8, then expand if data warrants. Measure all public payouts/nullifiers and failure handling. Prover input is proofs plus public statements, not notes.

### 15.5 L2 transport

Enter after one exact candidate payload is available, or to test the precise two-call baseline envelope as a diagnostic.

For each selected chain, distinguish source-pinned rules, configured node behavior, and actual authorized receipt evidence. In this research authorization, run local/source-reproduction checks only unless the user separately approves public testnet use.

Test raw proof, ABI, signed transaction, gas limit, txpool/sequencer size limits, and actual data-fee calculation. A rejected 210 KiB combined transaction is not a rejection of a future 60 KiB proof or two 100 KiB calls.

### 15.6 Hardware expansion

Do not block primitive/AIR work on procuring machines. Once a candidate reaches complete native proof status, measure one commodity x86 laptop/desktop and a portable build in addition to H1. Include cold and warm operation, thread counts, CPU features, memory, and proof generation randomness policy.

---

## 16. Measurement protocol

### 16.1 Native measurements

For promoted native comparisons:

- pin release compiler and CPU target;
- record SIMD/portable path;
- run one benchmark process at a time;
- include warmup;
- collect at least 30 independent timed proof runs per primary configuration;
- measure fixed and varied witness strata separately;
- report median, p90, p95, p99, min, max, standard deviation, and sample count;
- do not make a strong p99 claim from 30 samples; show the order statistic and uncertainty;
- separate setup/precomputation, witness generation, commit/FFT, prove, serialize, and native verify;
- report RSS units and measurement method explicitly.

For tiny kernels, batch enough iterations that timer overhead is negligible and total timed duration is meaningful. Retain individual aggregate samples. Do not time a single nanosecond-scale operation and rank fields on it.

### 16.2 EVM measurements

Record source/bytecode hash, compiler, optimizer, via-IR, hardfork, cold/warm access state, harness topology, calldata, call depth, and gas measurement type.

Distinguish:

- internal gasleft delta;
- unrestricted simulation;
- complete modeled transaction;
- capped top-level local transaction;
- public-chain receipt, if separately authorized.

A low-level external benchmark call is not identical to a top-level transaction. Keep both where useful.

### 16.3 Gas scenarios

Compute independently:

```text
standard_path = intrinsic_standard + actual_execution
active_floor  = applicable EIP-7623 floor
scenario64    = applicable 64-per-byte floor
scenario96    = applicable 96-per-byte floor
receipt_model = max(standard_path, relevant_floor)
```

Do not add a floor on top of execution. Do not use refunds to justify a gasLimit that exceeds the protocol cap. Evaluate each A/B transaction separately. Also report hypothetical one-call bytes, but do not treat A+B byte concatenation as an automatically valid unified proof codec.

### 16.4 Paired comparisons and attribution

Use the same abstract case, masks policy, environment, and measurement order where possible. Record when a protocol change prevents identical proof randomness. Alternate candidate order to reduce thermal/drift bias.

Report confidence intervals or bootstrap intervals for paired differences when meaningful. Deterministic gas changes under identical inputs do not need invented statistical intervals; distribution over valid proofs does.

### 16.5 Worst-case and statistical evidence

For a proposed complete local pipeline, collect at least 100 fresh transcript-valid proofs if practical, plus generated worst-shape verifier tests. Report the empirical cap-exceedance count with its sample size. Zero failures does not prove zero probability; a formal serialized-size/control-flow bound remains required for robust claims.

If proof generation is expensive, return a resource-limited smaller sample with the limitation. Do not replace missing samples with duplicate deterministic fixtures.

---

## 17. Gates and targets

### 17.1 Physical gates

Use the active target's actual limits. At the reviewed Ethereum baseline these include the EIP-7825 16,777,216 transaction cap, EIP-170 runtime limit, and initcode constraints. Reverify versions at execution time and retain the source/configuration.

### 17.2 Product targets retained for comparison

- Preferred one-call research envelope: at most 14M total gas and 80 KiB ABI calldata.
- Preferred robust two-call envelope: at most 12M per call, 20M combined, and 128 KiB total ABI calldata.
- Preferred deposit: at most 4M total gas, with lower values desirable.
- Prefer runtime modules under 22,000 bytes and deployment under 14M.
- Retain active, 64/64, and 96/96 scenario columns.

These remain targets, not permission to suppress measurements outside them. Report `PHYSICAL_PASS_PRODUCT_TARGET_FAIL` when appropriate. An informed later decision may choose different economic targets, but engineers may not silently change them to claim success.

### 17.3 Security gates

No configuration receives a complete quantum-bit claim from a hash family name, capacity arithmetic, or the random-words estimate alone. A security-qualified recommendation requires the accepted game, assumptions, losses, lifetime exposure, and exact-instance review.

A candidate may be recommended for **additional targeted cryptographic review** on the strength of measured feasibility even while unqualified. Do not conflate that recommendation with build/deployment approval.

### 17.4 Research stop gates

Stop an exact branch for a concrete reproduced relation bug, below-target attack, unsupported indispensable feature, or measured failure that persists after the predeclared bounded optimization attempt. State what would reopen it.

Do not stop merely because:

- the current control is not production-approved;
- a predicted value from an uncalibrated model is high;
- one upstream script needs a bounded compatibility repair;
- the work does not yet produce a qualified finalist;
- a digest/role layout has not yet been implemented by the assigned owner.

---

## 18. Team ownership and sequence

Assign distinct implementation and review owners. An agent may implement a component, but its own green tests are not independent cryptographic review.

| Package | Primary owner | Review owner | Dependencies |
|---|---|---|---|
| R2-00 baseline/provenance | reproducibility engineer | measurement reviewer | none |
| R2-01 security | cryptographic analyst | independent cryptographic reviewer | retained formulas; does not block sandbox controls |
| R2-02 hash modes/kernels | hash/EVM engineer | hash analyst + parity reviewer | R2-00 schema/corpus |
| R2-03 H0 vertical AIR | AIR engineer | independent relation reviewer | baseline corpus; no H5 approval dependency |
| R2-04 complete compression AIR | AIR engineer | relation/hash reviewer | R2-02 research eligibility + R2-03 findings |
| R2-05 transcript/verifier | verifier engineer | protocol/codec reviewer | frozen relation and phase spec |
| R2-06 Pareto correction | measurement/model engineer | security + performance reviewers | ledgers and actual anchors |
| R2-07 alternative backend | proof-system engineer | proof-system reviewer | exact relation; API fit |
| R2-08 full local paths | integration engineer | EVM/state reviewer | selected actual proofs and verifier pieces |
| R2-09 optional branches | assigned specialist | appropriate reviewer | explicit conditional entry gate |
| R2-10 synthesis | evidence editor | independent review coordinator | all required evidence dispositions |

### Review checkpoints

**Checkpoint A:** provenance and status semantics fixed; corpus and exact experimental scope frozen.  
**Checkpoint B:** H0 generic/optimized calibration and one vertical H0 proof exist; no metadata-only substitution.  
**Checkpoint C:** complete compression relation, parity/misuse, and causal comparison exist or a concrete falsification is retained.  
**Checkpoint D:** one exact hiding alternative backend reaches native proof or returns a minimal irreducible barrier; transcript improvements reach a complete proof.  
**Checkpoint E:** at most two complete local pipelines measured, including constructor and state costs.  
**Checkpoint F:** report passes evidence checks and an independent reviewer chooses the next action.

External cryptographic review proceeds throughout. A missing response must remain open, not be forged or inferred from internal approval.

---

## 19. Required final handoff

Return these files:

```text
research/r2/final/
  TARGETED_RESEARCH_REPORT.md
  CANDIDATE_MATRIX.csv
  OPPORTUNITY_MATRIX.csv
  FINDINGS.json
  UNRESOLVED_QUESTIONS.md
  SECURITY_TERMS.csv
  BYTE_LEDGER.csv
  GAS_LEDGER.csv
  RUN_MANIFEST.json
  EVIDENCE_MANIFEST.json
  REPRODUCTION.md
  SOURCE_AND_LICENSES.md
  DECISION.md
```

Retain source, scripts, raw logs, proof artifacts/regenerators, vectors, and local transaction receipts under versioned candidate/run directories. The report should link to them rather than duplicate enormous vectors inline.

### Required candidate matrix columns

- stable pipeline/configuration ID;
- relation/hash/AIR/backend;
- implementation tier and source commit;
- exact completed stage;
- ZK status;
- unconditional-regime and conditional-regime bound labels;
- exact missing assumptions;
- native proof bytes and ABI bytes;
- proof/verify time and RSS;
- direct/A/B/deposit/deployment gas;
- current physical gate;
- product-target gate;
- future scenario gates;
- sample count and worst-case evidence;
- stop reason class;
- next experiment and decision owner.

### Required opportunity matrix

List the next inexpensive information-producing experiment independently of promotion status. A cryptographically unqualified but reference-correct candidate can have high information value. A heavily documented unimplemented branch should not dominate a measured promising branch simply because both are unqualified.

### Required unresolved-question format

Each open question must have:

1. exact claim being decided;
2. why it affects a build choice;
3. current evidence;
4. missing artifact or theorem;
5. smallest decisive experiment;
6. assigned owner and reviewer;
7. stop/reopen condition;
8. which other tasks genuinely depend on it;
9. what can proceed independently.

Do not return only “external review open” or “no candidate passed.”

---

## 20. Final report structure

The return template in this package is normative for content, not formatting. The report must contain:

1. An executive decision, with the evidence that changed since e51a5c5.
2. Exact source and environment provenance.
3. Completed-versus-planned experiment matrix.
4. Baseline reproduction and ledgers.
5. Security-model changes, including the `m` objective and batching-object mapping.
6. Exact hash role and attack applicability matrices.
7. Matched-tier implementation results.
8. Horizontal/vertical and H0/compression causal comparison.
9. Transcript and full-verifier integrated deltas.
10. Calibrated parameter/Pareto analysis.
11. Exact alternative-backend results.
12. Complete local one-/two-call and deployment evidence.
13. Privacy and operational state review.
14. Optional branch results, clearly separated.
15. Negative results and unexecuted work.
16. Remaining blockers with owners and decisive tests.
17. Proposed next engineering-spec scope, only if supported.

A separate automated validator must catch null-as-zero, unknown-as-failed, mismatched source hashes, unsupported qualification labels, component-sum gas claims, and incomplete ledger sums.

---

## 21. Allowed final decisions

Choose one, with an evidence-based explanation:

### `RECOMMEND_FULL_ENGINEERING_SPEC`

At least one complete local pipeline has measured feasibility, a defensible accepted security/privacy path, and no unresolved architectural rewrite. This authorizes requesting a specification, not deployment.

### `RECOMMEND_SECURITY_REVIEW_OF_MEASURED_FINALIST`

A complete measured path is promising, but exact cryptographic review is the principal remaining blocker. Name the finite questions and candidate rather than asking for an open-ended audit of every branch.

### `RECOMMEND_ROBUST_TWO_CALL_SPEC`

One call remains unsupported, but a bounded two-call pipeline has acceptable measured cost, security/privacy, and state behavior.

### `RECOMMEND_AGGREGATION_OR_L2_EXPERIMENT`

Exact direct-path measurements identify the bottleneck, and a concrete aggregation or target-chain strategy could address it. Return a scoped next experiment, not a generic suggestion to “use L2.”

### `RECOMMEND_ONE_MORE_TARGETED_SPIKE`

Only a small, named technical uncertainty blocks selection. Define that experiment and explain why its outcome would change the decision.

### `REJECT_CURRENT_ARCHITECTURAL_LINEAGE`

An exact measured or analytical obstruction rules out the studied lineage under the stated target, after the relevant structural hypotheses were actually tested. Do not use this outcome merely because external review or integration was never performed.

---

## 22. Definition of done

This round is complete when the team returns:

- a clean, source-pinned baseline reproduction;
- exact baseline proof-byte and gas ledgers;
- an audited-for-consistency security-model comparison, with unresolved cryptographic assumptions explicit;
- matched-tier H0/new-compression measurements and full role/parity/misuse evidence;
- at least one actual vertical H0 hiding proof;
- a completed new-compression relation comparison or a concrete falsification;
- an integrated transcript/verifier experiment;
- one same-relation alternative-backend result or a minimal demonstrated barrier;
- at most two complete local operational measurements;
- a calibrated rather than tautological feasibility matrix;
- a return report that allows the next architecture decision to be made from data.

No public deployment is part of this definition. No production-security claim is implied by finishing the experiments. The intended outcome is enough reliable evidence to stop guessing about the next full build.
