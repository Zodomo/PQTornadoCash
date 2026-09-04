# PQ Tornado Classic v0.3 — Exhaustive Engineering Report

**Snapshot generated:** 2026-09-03T14:07:43-05:00  
**Protocol implementation:** v0.3  
**Review status:** pre-deployment research implementation; unaudited  
**Deployment status:** no v0.3 Sepolia or mainnet deployment; no v0.3 network receipts  
**Scope of this package:** architecture, implementation, complete first-party source, original plan, deviations, security analysis, gas evidence, tests, reproducibility, limitations, and reviewer checklist

---

## Table of contents

1. Purpose and evidence boundary
2. Executive assessment
3. Requirements and preserved invariants
4. System architecture
5. Canonical data model and hashing
6. Withdrawal AIR
7. Proof system
8. Canonical two-part proof
9. Solidity architecture
10. Off-chain implementation
11. Original plan deviations
12. Gas analysis
13. Security and privacy analysis
14. Verification evidence and test intent
15. Reproducibility and build
16. Known limitations and required external review
17. Reviewer procedure
18. Complete source inventory
19. Solidity declaration completeness manifest
20. Generated artifact inventory
21. Explicit exclusions
22. Appendix A — original engineering plan
23. Appendix B — current documentation and ADRs
24. Appendix C — complete first-party implementation and tests
25. Appendix D — build, workspace, CI, and deployment-template configuration
26. Appendix E — generated parameter manifests and security outputs
27. Appendix F — verification command record

## 1. Purpose and evidence boundary

This document is intended to be the only package delivered to an external reviewer. It therefore contains both the engineering narrative and the complete first-party source snapshot. All Solidity production contracts, Solidity libraries, Solidity verifier modules, Foundry scripts, Foundry tests and test helper contracts are reproduced verbatim. The Rust workspace, TypeScript SDK and relayer, tests, build configuration, CI workflow, dependency lock files, current protocol documentation, architecture decisions, and original engineering plan are also reproduced verbatim in later appendices.

The report excludes only external dependencies, generated compiler/build directories, private environment material, historical broadcast records, and large generated proof/vector payloads. Excluded generated payloads are identified by exact byte length and SHA-256 digest, and the complete code that regenerates and validates them is included. No claim in this report should be interpreted as an audit, deployment authorization, mainnet-readiness statement, or proof that Ethereum itself is post-quantum secure.

The implementation achieves the requested local operational shape:

- a deposit is one state-changing Ethereum transaction;
- a withdrawal is exactly two state-changing pool transactions;
- proof bytes are supplied directly as calldata;
- no proof-data contract, fact publication transaction, trusted verifier service, administrator, proxy, upgrade key, trusted setup, elliptic-curve proof wrapper, or third-call fallback is used.

The final security review is not wholly favorable. The q32 proof profile reaches 107 bits only under the documented random-words conjecture. Its generated proven bounds are 37 bits under unique decoding and 56 bits under list decoding. This is lower than the earlier q48 profile's conservative proven result. Therefore the current implementation meets the transaction-count and local gas objectives but does **not** establish the later strict requirement that optimization must not weaken any security measure. This is a deployment blocker, not a wording issue.

## 2. Executive assessment

### 2.1 What was built

PQ Tornado Classic v0.3 is a fixed-denomination native-ETH privacy pool modeled on the one-note/one-withdrawal shape of Tornado Classic. A user creates two private values, derives one public note commitment, deposits that commitment into a depth-20 append-only binary tree, later proves knowledge of the note opening and an authentication path, publishes a pool-scoped nullifier, binds the proof to an exact payout, and receives the fixed denomination less any relayer fee.

The proof is a transparent, pairing-free, hiding Plonky3 STARK over BabyBear with a degree-four extension field and hiding two-adic FRI. Application hashing is a field-native Poseidon2 sponge named P2BB512-v1. Proof commitments, Fiat-Shamir transcript operations, and parameter identifiers use a domain-separated pair of Keccak-256 outputs named KeccakPair512. The EVM verifies the STARK itself through hand-written Solidity arithmetic, transcript, MMCS, DEEP, FRI, AIR, and proof-codec components.

The complete proof remains noninteractive. Splitting verification into A and B does not create an interactive public-coin protocol. Part A verifies a fixed prefix of the deterministic verification computation and stores a compact, consumer-bound continuation checkpoint. Part B replays and checks all bindings required to resume, verifies the fixed suffix, consumes the checkpoint, marks the nullifier, and pays in the same EVM transaction. The checkpoint never stores proof bytes or caller-selected challenges.

### 2.2 Current measured result

The current source-bound parameter ID is:

`0x35adfcc070249bb0393c2fd45f0bbd48ef03cbfc08070d03335eaf952975e62ab7bc82ead4f8c1f1c39b3372be85195853134dfc9d24f43b97a5e0454ea07779`

The regenerated proof fixture is:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Part A | 101,990 | `117620affe3dd9788089bc357f894c999d94215bcea54c26db6c28f5244764e7` |
| Part B | 108,294 | `b73057343f2e5f0f8557ce157f1576eb7ebffd665d09342b4096af57f4e8ab18` |
| Total | 210,284 | — |

The full pool-facing local Foundry model measured:

| Operation | Execution gas | Standard intrinsic | Modeled transaction gas | Margin below 16,777,216 |
|---|---:|---:|---:|---:|
| Deposit | 13,991,021 | at most 22,088 | at most 14,013,109 | at least 2,764,107 |
| Withdrawal A: `beginWithdrawal` | 14,891,070 | 1,648,232 | 16,539,302 | 237,914 |
| Withdrawal B: `withdraw` plus payment | 12,356,373 | 1,749,536 | 14,105,909 | 2,671,307 |

The A margin is narrow. These values describe one regenerated proof fixture. Pruned multiproof frontier sizes and byte distributions depend on transcript-derived query collisions. The tests do not yet prove a worst-case upper bound over every valid proof/query schedule. An external reviewer must not generalize the fixture measurement into a universal gas theorem without additional analysis.

### 2.3 Verification result

The final source snapshot passed:

- Rust workspace: 47 tests across eight suites;
- TypeScript SDK/relayer: 18 tests;
- Solidity: 63 tests across eight suites;
- pool invariants: three invariants, 64 runs and 1,024 calls per invariant;
- all 1,000 cross-language P2BB512/application-tree vectors;
- a Rust-to-Solidity AIR differential vector;
- real-proof transcript, statement, query-order, MMCS-frontier, FRI-salt, mixed-proof, replay, and consumer-binding mutations;
- deterministic parameter-manifest regeneration by byte-for-byte directory comparison;
- `cargo clippy --workspace --all-targets --all-features --locked` with warnings but successful exit;
- `forge lint` with intentional fixed-width narrowing warnings but successful exit;
- `forge build --sizes`;
- a clean reproducible Docker build that reran Rust, TypeScript, Solidity, invariant, gas, and code-size checks.

The Docker image manifest produced by the verified build was `sha256:8e17028c7a23b2be5c818281f32835ee0e2992db1a97ad31e4543e20080ffef8`.

### 2.4 Review verdict

The artifact is technically coherent as a pre-deployment research implementation and satisfies the local one-deposit/two-withdrawal-call gate. It is **not deployable under the strict no-security-weakening requirement** because:

1. q32 lowers conservative proven FRI/STARK decoding bounds relative to q48;
2. the 107-bit figure is conjectured, not proven;
3. the pinned BabyBear Poseidon2 instance lacks an independent structural classical and quantum cryptanalysis in this application;
4. the custom KeccakPair512 Fiat-Shamir composition lacks a complete QROM proof;
5. the valid-proof worst-case gas bound has not been proven, and A has only 237,914 gas of fixture-specific margin;
6. valid abandoned A checkpoints can create unbounded registry storage without a cleanup/economic bound;
7. the generated deployment manifest does not yet bind reviewed runtime code hashes;
8. no network deployment, receipt, independent audit, or adversarial public demonstration exists.

## 3. Requirements and preserved invariants

The core product model was retained from the original plan:

- native ETH only;
- one immutable denomination per pool;
- one commitment per deposit;
- one note spent per withdrawal;
- a 20-level append-only binary Merkle tree;
- a transparent hash-based STARK with no trusted setup;
- BabyBear base field and degree-four challenge extension;
- mandatory witness hiding through random codewords and salted Merkle leaves;
- proof verification by the EVM without Groth16, KZG, IPA, pairing, or elliptic-curve compression;
- immutable, non-upgradeable custody contracts;
- permissionless proving and submission;
- statement binding to scope, root, nullifier, recipient, relayer, and fee;
- atomic nullifier marking and payment;
- canonical encodings with version separation;
- reorg-aware off-chain tree reconstruction;
- no claim that Ethereum accounts, signatures, consensus, networking, or public metadata become post-quantum private.

The following invariants define v0.3:

1. Every application digest is 16 canonical BabyBear elements encoded as 64 big-endian bytes.
2. Every secret is exactly eight canonical BabyBear limbs. A limb at or above 2,013,265,921 is rejected, not reduced.
3. A note commitment binds the 16-element scope, eight secret limbs, and eight trapdoor limbs.
4. A nullifier binds the same scope and eight secret limbs.
5. Merkle nodes bind left child, right child, and level.
6. Scope binds chain ID, pool address, denomination, tree depth, protocol version, and parameter ID.
7. The proof binds the four public digests: scope, root, nullifier, and payout.
8. The payout digest binds recipient, relayer, and 256-bit fee.
9. Query positions are transcript-derived; callers cannot choose them.
10. All proof counts, dimensions, rounds, and half boundaries are fixed by version/profile checks.
11. Part B is valid only for the exact part-A continuation, statement, parameter, global proof, query schedule, and consumer.
12. A proof cannot transfer value twice because the pool marks the canonical nullifier.
13. Payment failure or reentrancy reverts checkpoint consumption and nullifier marking through EVM transaction rollback.

## 4. System architecture

### 4.1 Layer map

```text
User/relayer tooling
  ├─ TypeScript SDK: note/hash/tree/calldata/receipt validation
  ├─ Rust CLI: parameters, vectors, notes, indexing, proving, native verification
  └─ Rust indexer: confirmed event replay, cross-source checks, rollback

Cryptographic application layer
  ├─ CanonicalSecret: 8 canonical BabyBear u32 limbs
  ├─ P2BB512-v1: Poseidon2 width 16, rate 4, capacity 12
  ├─ Digest512: 16 field elements / 64 encoded bytes
  ├─ depth-20 P2BB512 Merkle tree
  └─ scope, note, nullifier, payout encodings

Proof layer
  ├─ WithdrawalAir: 256 rows × 190 columns
  ├─ hiding two-adic PCS, proof degree bits 9
  ├─ four masking codewords and eight salt elements per MMCS leaf
  ├─ log blowup 4, nine binary FRI rounds, 32 queries
  ├─ KeccakPair512 proof MMCS and transcript
  └─ strict v3 A/B proof codec

EVM layer
  ├─ PQTCClassicPool: custody, deposits, roots, nullifiers, payout
  ├─ PQTCVerificationRegistry: A/B continuation and replay binding
  ├─ PQTCAirStageVerifier: segmented AIR evaluation
  ├─ PQTCQueryVerifier: MMCS/DEEP/FRI query checks
  └─ fixed arithmetic, transcript, codec, Poseidon2 and MMCS libraries
```

### 4.2 Trust model

No privileged party can change the denomination, tree depth, parameter ID, verifier contracts, protocol version, or scope after deployment. There is no owner, proxy, governance hook, emergency withdrawal, trusted prover, allowlisted relayer, or trusted verifier service. A malicious prover can waste its own resources and submit invalid transactions. A malicious relayer can censor or delay a user, but the user can replace it. Safety relies on Ethereum executing the deployed immutable bytecode correctly.

The off-chain indexer is not a consensus oracle. It must use confirmed blocks, support rollback, and can cross-check independent sources. A dishonest or unavailable endpoint affects liveness or can mislead an inadequately configured client; it cannot cause the on-chain pool to accept an unknown root.

## 5. Canonical data model and hashing

### 5.1 `Digest512`

A `Digest512` consists of `left` and `right` 32-byte halves. For application hashes, those 64 bytes encode 16 canonical BabyBear elements, four bytes per element, big-endian. The EVM validates field canonicality at trust boundaries. Although the carrier is 512 bits, the security of the P2BB512 sponge is governed by its field capacity and structural assumptions, not by the display width alone.

### 5.2 P2BB512-v1

P2BB512 uses Plonky3's pinned BabyBear Poseidon2 permutation:

- width: 16 field elements;
- rate: 4;
- capacity: 12;
- S-box: degree seven;
- full rounds: eight;
- partial rounds: thirteen;
- squeeze: all 16 elements, requiring four rate blocks.

Capacity framing binds the P2BB512 version, one-byte domain, original payload byte length, payload field-element count, and auxiliary value. Payload elements are absorbed in four-element blocks. Empty payloads still invoke a permutation. Merkle nodes place the tree level in the auxiliary value, which prevents cross-level node reuse.

The approximate capacity is `12 × log2(2,013,265,921) ≈ 370.9` bits. Under an ideal-permutation generic Brassard-Høyer-Tapp collision model, dividing by three gives approximately 123.6 quantum bits. This is an idealized generic ceiling, not a structural proof for the exact Poseidon2 constants and round count.

### 5.3 Canonical secrets

Each 32-byte secret is eight big-endian `u32` values strictly below the BabyBear modulus. Generation uses rejection sampling from operating-system randomness, so each limb is uniform and no modulo bias is introduced. One secret contains about `8 × log2(p) ≈ 247.3` classical entropy bits, corresponding to about 123.6 bits under idealized Grover search.

This representation is deliberately narrower than an unconstrained 256-bit byte string. It avoids byte-to-field range decomposition inside the AIR and lets Rust, TypeScript, note encoding, and the AIR share one exact representation. The change saved enough columns and constraints to contribute to EVM feasibility. It also reduces the idealized generic secret-search claim from 128 to about 123.6 quantum bits. That reduction must be treated as a security deviation, not hidden behind the 32-byte storage size.

### 5.4 Scope

The scope is immutable per pool and binds:

- chain ID;
- pool address;
- denomination;
- tree depth 20;
- protocol version 3;
- exact 512-bit parameter ID.

Because commitments, nullifiers, and Merkle roots include the scope, a note cannot be replayed across pools, chains, denominations, protocol versions, or parameter sets.

### 5.5 Note commitment and nullifier

The commitment payload contains 32 field elements:

```text
scope[16] || nullifierSecret[8] || trapdoor[8]
```

The nullifier payload contains 24 field elements:

```text
scope[16] || nullifierSecret[8]
```

Separate domain tags and byte/element lengths prevent one operation from being reinterpreted as the other. Every secret limb is constrained and tested for binding.

### 5.6 Merkle tree

The application tree has depth 20 and capacity 1,048,576 leaves. Empty leaf and zero-node values are scope-specific. Every internal node hashes two 16-element digests with the current level as auxiliary data. The pool maintains filled subtrees, the next leaf index, current root, and a set of known historical roots. Off-chain Rust and TypeScript trees are checked against Solidity using 1,000 generated vectors and multi-insert path tests.

### 5.7 Payout and public statement

The payout digest binds a 20-byte recipient, 20-byte relayer, and 32-byte big-endian fee. The public STARK values are 64 BabyBear elements obtained by concatenating the field elements of scope, root, nullifier, and payout digest. The pool reconstructs these values independently before both verifier calls.

## 6. Withdrawal AIR

### 6.1 Relation

The private witness contains the nullifier secret, trapdoor, leaf index, 20 path bits, and 20 sibling digests. The AIR proves that:

1. the public nullifier is derived from the scope and secret;
2. the note commitment is derived from the same scope and secret plus trapdoor;
3. the note commitment follows the private authentication path to the public root;
4. path bits agree with the leaf index;
5. the public payout fields are bound into the proof statement;
6. all intermediate hashes execute the pinned P2BB512 transition.

### 6.2 Shape

The final AIR has:

- 256 rows;
- 190 columns;
- 1,186 constraints;
- maximum constraint degree seven;
- 240 active application-hash permutations;
- 64 public values;
- 210 batched opening functions (`190 trace + 16 quotient-related + 4`).

Column layout:

- 0–156: Poseidon2 sub-AIR columns;
- 157–161: operation selectors;
- 162–165: four step bits;
- 166–170: five Merkle-level bits;
- 171: last-level selector;
- 172: path bit;
- 173: remaining index;
- 174–189: 16 shared work columns.

Row schedule:

| Rows | Operation | Count |
|---|---|---:|
| 0–8 | nullifier hash | 9 |
| 9–19 | note commitment | 11 |
| 20–239 | 20 level-bound Merkle hashes | 220 |
| 240–243 | payout public-value binding | 4 |
| 244–255 | padding | 12 |

### 6.3 Nullifier-first workspace reuse

The key width reduction is scheduling the nullifier before the note commitment. The first eight work columns initially hold the secret. The nullifier operation consumes the secret without overwriting the full work state. The note operation then consumes the same secret and trapdoor and writes the resulting note digest into the 16 work columns. Each Merkle level overwrites that work value with its parent. This removes separate long-lived secret, trapdoor, note, and Merkle-state column groups.

This schedule reduced width from the v0.2 design's 230 columns to 190. The change is security-sensitive because accidental unconstrained workspace would permit witness substitution. Tests perturb every private limb and work column, assert the exact row schedule, exercise operation boundaries, verify every public field, and compare the Rust evaluator with Solidity.

## 7. Proof system

### 7.1 Pinned stack

- Plonky3 commit: `3152b14a89067c83775a8076cc262ffc48a1fd7c`;
- BabyBear base field;
- degree-four BabyBear extension;
- hiding two-adic FRI PCS;
- base trace degree bits: eight;
- masked proof degree bits: nine;
- log blowup: four;
- binary FRI rounds: nine;
- final polynomial bound: one;
- queries: 32;
- commit grinding: 16 configured classical bits;
- query grinding: 16 configured classical bits;
- random masking codewords: four;
- MMCS salt fields per leaf: eight.

The production API obtains masking randomness from the operating system. It does not expose a caller-selected deterministic masking seed. Two proofs of the same witness should differ while remaining verifiable.

### 7.2 KeccakPair512 proof hashing

Proof commitments and transcript operations retain KeccakPair512. For tag `t` and payload `m`:

```text
left  = keccak256(0x00 || t || m)
right = keccak256(0x01 || t || m)
digest = left || right
```

It is not standardized Keccak-512. Domain tags distinguish proof leaves, proof nodes, transcript initialization, transcript absorption/squeezing, parameter manifests, statements, checkpoints, proof IDs, and verification IDs. Typed fixed-width encodings and explicit lengths are required to avoid ambiguity.

### 7.3 Transcript and queries

The transcript observes the parameter ID, 64 public values, degree metadata, trace and quotient commitments/openings, hiding commitments/openings, FRI commitments, proof-of-work witnesses, final polynomial, and all other global objects. It then derives all 32 query indices. Query order is canonical and proof parts cannot reorder or replace positions. Duplicate derived indices are supported through one canonical sorted-unique multiproof frontier.

The design assumes random-oracle-style Fiat-Shamir behavior. A complete proof of the custom two-branch transcript and whole STARK composition in the quantum random-oracle model is not available.

### 7.4 Security accounting

The generated `sepolia-v0.3` result is:

| Model | Bits |
|---|---:|
| Random-words conjecture | 107 |
| Proven unique decoding | 37 |
| Proven list decoding | 56 |
| Best generated proven bound | 56 |
| Conservative challenge-field budget | 120 |
| Quantum-adjusted MMCS cap | 128 |

The 107-bit result satisfies the project's configured 100-bit target only under the random-words conjecture. The implementation must not claim 100-bit proven soundness. Grinding receives only the generator's quantum-adjusted square-root credit. Multi-target use and unbounded proof volume can further affect interpretation.

## 8. Canonical two-part proof

### 8.1 Clean version boundary

v0.3 is an incompatible cutover:

- protocol version 3;
- AIR version 3;
- proof codec version 3;
- verifier interface version 3;
- manifest magic `PQTCPRM3`;
- part-A magic `PQTCPA03`;
- part-B magic `PQTCPB03`;
- note prefix `pqtc-note-v3:`;
- profile `sepolia-v0.3`;
- v3 statement, checkpoint, proof, and verification domains.

There is no v2 compatibility parser, alias, fallback selector, or fact adapter. Old notes and roots are invalid because scope includes protocol version and parameter ID.

### 8.2 Global data and halves

Each part contains a strict common header and byte-identical 9,208-byte global section. The global section contains the trace and quotient commitments/openings, FRI roots and related objects required by the continuation. Repetition costs calldata but lets B independently check the continuation without trusting mutable storage for large proof objects.

Part A verifies query positions 0–15. Part B verifies positions 16–31. Each half encodes a fixed start and count. Input MMCS batches use fixed matrix count/width pairs `(1,8)`, `(1,194)`, and `(16,8)`, including four random columns. Nine FRI rounds follow. Every pruned frontier has a bounded count and canonical traversal.

### 8.3 Continuation binding

The registry constructs:

- `statementKey`: parameter ID plus all public values;
- `globalDigest`: Keccak digest of the exact global bytes;
- checkpoint digest: statement, global bytes, transcript continuation, challenges, all query indices, and canonical unique set;
- `coreProofId`: statement plus full part A;
- `verificationId`: core proof ID plus registry `msg.sender`.

Because `msg.sender` is the pool when users call `beginWithdrawal`, only that pool can complete B. An observer can front-run an identical A through the same pool, but the result is the same idempotent checkpoint and the observer pays for donated work. A different caller receives a different verification namespace.

## 9. Solidity architecture

### 9.1 `PQTCClassicPool`

The pool owns ETH and the application tree. Constructor immutables bind denomination, parameter ID, registry, tree depth, protocol version, and scope. There is no administrative mutation path.

Deposit checks exact value, rejects a zero, duplicate, or noncanonical commitment, inserts one leaf, records the resulting root, and emits the deposit. The depth-20 insertion executes 20 P2BB512 node hashes and is the dominant deposit cost.

`beginWithdrawal` validates root/nullifier/payout conditions, reconstructs public values, and forwards part A to the registry. It returns the consumer-specific verification ID.

`withdraw` repeats validation, calls registry completion with part B, marks the nullifier, and transfers `denomination - fee` to the recipient and `fee` to the relayer. State is updated before external transfers and guarded against reentrancy. Any later revert restores pool and registry state atomically.

### 9.2 `PQTCVerificationRegistry`

The registry pins the AIR verifier, query verifier, and parameter ID as immutables. Part A parses and checks the full global data, transcript checkpoint, first AIR segments, and first 16 queries before writing a fixed-size `StoredCheckpoint`. The AIR evaluator is divided into seven ranges; A evaluates ranges 0–2 and stores the accumulator/cursor, while B evaluates ranges 3–6 and requires the final quotient relation.

B requires an existing checkpoint and exact consumer, parameter, statement, core proof ID, global digest, and checkpoint digest. It performs remaining AIR, DEEP, MMCS and FRI checks, deletes the checkpoint, then returns success to the pool.

There is no consumed-proof tombstone. Reuse is prevented at the value layer by the nullifier. A valid abandoned checkpoint can persist. Since anyone with a valid proof can create one through a pool, the storage-griefing bound must be resolved before deployment.

### 9.3 Arithmetic and verifier modules

- `BabyBear` implements canonical base-field arithmetic.
- `BabyBearExt4` and `BabyBearExt4Packed` implement degree-four extension operations and packed EVM representations.
- `CanonicalCodec` parses strict fixed-width calldata without broad `abi.decode` allocations.
- `Transcript512` mirrors the Rust transcript.
- `MmcsVerifier` verifies canonical pruned binary multiproofs, duplicate-query consistency, salts, and root reconstruction.
- `StarkOodVerifier` performs DEEP out-of-domain algebra.
- `AirEvaluatorPoseidon` mirrors the 1,186-constraint Rust AIR in segmented Horner order.
- `PQTCAirStageVerifier` exposes bounded segments so A and B share one accumulator.
- `PQTCQueryVerifier` verifies fixed input batches, reductions, and all nine FRI rounds.
- `FriVerifier` supplies fixed fold operations.

The implementation uses intentional narrowing casts only after shifts/masks or fixed protocol bounds. Foundry lint reports these casts because Solidity does not encode the surrounding proof in the type system. Reviewers should independently confirm each instance rather than treating a successful lint exit as proof.

## 10. Off-chain implementation

### 10.1 Rust crates

`pqtc-spec` owns protocol constants, canonical secrets, digest and statement types, and serialization. `pqtc-hash` owns KeccakPair512, P2BB512, scope/note/nullifier/payout functions, and the note codec. `pqtc-merkle` provides the canonical tree and authentication paths. `pqtc-poseidon-air` owns relation checking, trace generation, constraints, and shape reporting. `pqtc-stark` owns proof configuration, prover/verifier, MMCS/transcript operations, queries, and the A/B codec. `pqtc-security` owns manifests, IDs, source hashing, and security estimates. `pqtc-indexer` replays confirmed blocks and reorgs. `pqtc-cli` composes all user and review workflows.

### 10.2 TypeScript SDK and relayer

The SDK independently implements canonical field parsing, note encoding, P2BB512, tree operations, public-value construction, calldata, and relayer request/receipt validation. The relayer validates chain, registry, pool, parameter, statement, request deadline, transaction status, and the exact `VerificationStarted` event before constructing or broadcasting B. It does not become a trusted verifier; the contracts repeat all safety checks.

### 10.3 CLI workflow

The CLI supports parameter generation, 1,000-vector generation, verifier differential vectors, proving benchmarks, note creation, deposit preparation, cross-checked tree synchronization, confirmed path creation, proof generation, and native A/B verification. Proof generation uses operating-system hiding entropy. Parameter manifests are deterministic; proof bytes intentionally are not.

## 11. Original plan deviations

The original engineering plan is reproduced verbatim in Appendix A. The following table is the authoritative deviation analysis.

| Original plan or intermediate decision | Implemented v0.3 | Why changed | Justification and review status |
|---|---|---|---|
| Sepolia deployment and public demonstration were the final deliverable. | No deployment was performed. | The later user instruction explicitly prohibited deployment while design optimization continued. | Authorized scope change. All scripts/templates remain review-only. No receipt evidence is claimed. |
| KeccakPair512 for application commitments, nullifiers, tree nodes, and payout. | P2BB512-v1 Poseidon2 for all application hashes; KeccakPair512 remains for proof MMCS, transcript, and manifests. | A Keccak AIR made EVM proof verification operationally enormous. v0.1 required 818 transactions and proof-data shards. | Documented by ADR-0004. It removes operational impossibility but adds Poseidon2 structural-analysis risk and a lower generic capacity ceiling. Requires external cryptanalysis. |
| Two unrestricted random 32-byte secrets, idealized 128-bit Grover work. | Two 32-byte encodings of eight canonical BabyBear limbs, about 247.3 entropy bits and 123.6 idealized Grover bits each. | Eliminates byte decomposition/range machinery and permits direct AIR field use. | Canonical rejection sampling is sound and unbiased, but the generic quantum estimate is about 4.4 bits lower. This is a material security deviation. |
| Keccak reference AIR plus a narrower microcoded Keccak optimization AIR. | One field-native Poseidon2 AIR; no live Keccak application AIR. | Maintaining a second Keccak AIR did not solve calldata/opening cost sufficiently and duplicated a large correctness surface. | Clean replacement rather than dual semantics. Cross-language P2BB512 vectors and differential AIR tests replace reference/compact equivalence tests. |
| 44 Keccak-f operations in the withdrawal relation. | 240 Poseidon2 permutations in a 256-row trace. | Poseidon2 operations are much cheaper to arithmetize and verify despite greater count. | Measured proof/EVM results justify operationally; cryptographic equivalence is not claimed because this is a new hash construction. |
| Original 128 public values in the Keccak design. | 64 public BabyBear values: four 16-element digests. | Application digests are natively canonical field elements. | Reduces openings and calldata while binding the same semantic statement fields. |
| v0.2 width-230 AIR, note before nullifier. | Width 190, nullifier first, shared 16-column work area. | Lifetime analysis showed secret and hash outputs could safely reuse columns. | Constraint mutation and schedule tests cover reuse. This is a soundness-critical optimization requiring line-by-line review. |
| v0.2 production profile used 48 queries split 24/24. | v0.3 uses 32 queries split 16/16. | Even after width reduction, q48 could not fit two EIP-7825-bounded pool transactions. | Achieves gas gate and retains 107 conjectured bits, but proven bounds fall to 37/56. **Not justified under an absolute no-security-weakening rule.** |
| Mandatory staged session/fact fallback with bonds, expiry, cleanup, query batches, and a separate fact withdrawal. | One compact consumer-bound checkpoint between A and B; no fact, bond, expiry, proof shard, or third call. | v0.1 staging measured 818 transactions and was unusable. The later requirement capped withdrawal at two transactions. | Trust and atomicity improve. Storage cleanup was removed, leaving abandoned-checkpoint griefing as a deployment blocker. |
| Each staged transaction below 12,000,000 gas. | A is 16,539,302 and B 14,105,909 intrinsic-inclusive; each is below EIP-7825's 16,777,216 limit. | The acceptance criterion changed from many small stages to at most two complete calls. | Meets the later explicit transaction cap model, not the original 12M per-stage target. |
| Direct one-transaction withdrawal was preferred if below about 15M; otherwise staging. | Exactly two transactions. | Complete direct verification plus payout does not fit. | Matches the later user requirement; no claim of one-call withdrawal. |
| Version-1 note/proof/manifest names and domains. | Clean v3 cutover. | Two material hash/AIR/profile migrations occurred. | Required by the original plan's ADR/versioning rule. Old artifacts are rejected, not silently decoded. |
| Parameter manifest expected final runtime code hashes. | Manifest schema supports ordered runtime hashes, but current generated profiles contain an empty list. | There is no deployment candidate or finalized independently reviewed runtime set. | Acceptable for research tests; blocker for a deployment candidate. |
| Complete testnet dataset: multiple deposits, unrelated funded accounts, relayer, receipts, public artifact bundle. | Local deterministic vectors, generated proof fixture, Foundry execution, and Docker reproduction only. | Deployment was prohibited. | Explicitly unresolved. Local evidence cannot substitute for receipts or anonymity-set behavior. |
| Compact AIR gate preferred at least 4× proof/calldata reduction. | Width fell 230→190 and proof is about 210KB; the change was selected to cross the transaction limit, not a demonstrated 4× reduction. | The binding requirement became the two-transaction cap. | Deviation from the original heuristic. Measured feasibility, not 4× size reduction, was the decision criterion. |
| Security target around 100 bits under generated quantum-adjusted accounting. | 107 conjectured, 37 UDR, 56 LDR/best proven. | q32 was the only tested profile to fit two calls after available optimizations. | Conjectured target passes; proven 100-bit target does not. Claims are deliberately limited. |
| Circle FRI retained as optional optimization. | Not adopted. | Available Circle PCS did not provide the required hiding configuration in the pinned stack. | Original rationale retained. Hiding took priority over speculative proof-size reduction. |

### 11.1 Chronology

**v0.1 baseline.** The initial architecture followed the plan literally: KeccakPair512 at the application layer, a wide Keccak AIR, staged verification, proof bytes stored or deployed in shards, query work spread across many calls, fact publication, and later withdrawal. It preserved familiar EVM hashing but produced a measured 818-transaction flow. That was a valid feasibility experiment and an operational failure.

**v0.2 pivot.** Application hashing moved to P2BB512. The relation became 256 rows by 230 columns with 64 public values. A 48-query proof was split across two consumer-bound calls instead of hundreds of session calls. The verifier was semantically much cleaner, but full pool-facing estimates remained about 21.65M and 20.87M gas, above the per-transaction cap. Registry-only execution was also too high. v0.2 therefore failed the requested operational gate.

**v0.3 optimization.** Lifetime analysis changed the row schedule, secret representation, and workspace layout, reducing width to 190. The production profile moved to q32 and the proof was split 16/16. The regenerated full ABI fixture passes at 16.539M and 14.106M. The application and proof formats were versioned again because commitment preimages, parameter IDs, notes, AIR shape, proof bytes, and security parameters all changed.

## 12. Gas analysis

### 12.1 EIP-7623 accounting

For these ordinary calls, without creation or access lists, define calldata tokens:

```text
T = zeroBytes + 4 × nonzeroBytes
standardPath = 21,000 + 4 × T + executionGas
floorPath = 21,000 + 10 × T
modeledReceiptGas = max(standardPath, floorPath)
```

The floor is an alternative minimum for the whole transaction. It is not added to execution gas.

Current fixture calldata:

| Call | Bytes | Zero | Nonzero | Calldata gas | Base + calldata intrinsic |
|---|---:|---:|---:|---:|---:|
| A | 102,308 | 808 | 101,500 | 1,627,232 | 1,648,232 |
| B | 108,644 | 814 | 107,830 | 1,728,536 | 1,749,536 |

For A, `T=406,808`, so the floor is 4,089,080 and the standard path is 16,539,302. For B, `T=432,134`, so the floor is 4,342,340 and the standard path is 14,105,909. The standard path governs both.

### 12.2 Verifier component profile

The regenerated fixture produced these diagnostic values:

| Component/profile point | Gas |
|---|---:|
| parsing, transcript, storage baseline | 2,929,782 |
| AIR first segment contribution | 2,863,647 |
| alpha/inverse/shared OOD contribution | 1,504,643 |
| input MMCS contribution | 1,751,463 |
| DEEP X reductions | 2,483,581 |
| nine FRI rounds | 2,523,737 |
| actual registry A execution | 14,056,853 |
| actual registry B execution | 11,470,158 |

The pool-facing harness deliberately adds an external measurement call, making its execution number conservative relative to a direct top-level pool call. The exact intrinsic calculation uses the actual encoded pool ABI calldata.

### 12.3 Gas uncertainty

The following are not proven:

- maximum pruned-frontier length across every transcript-derived query multiset;
- maximum zero/nonzero byte distribution across every valid proof;
- maximum execution cost across all valid duplicate-query patterns;
- worst deposit storage transition across every tree position and warm/cold access environment;
- client/network enforcement details beyond the modeled Prague/EIP assumptions.

Given A's 237,914 margin, worst-case analysis is mandatory before deployment. A single passing random proof is a gate, not a universal bound.

## 13. Security and privacy analysis

### 13.1 Note hiding

Public commitments expose only the P2BB512 digest. Security relies on independent uniform secret/trapdoor limbs, operating-system randomness, and the preimage behavior of the exact P2BB512 construction. The note encoding preserves secrets locally and includes checksum/version/context. Device compromise, note exfiltration, weak operating-system entropy, or telemetry defeats this property.

### 13.2 Commitment and accumulator binding

Binding relies on Poseidon2/P2BB512 collision resistance, domain/length separation, canonical element encoding, and level-bound Merkle hashing. The 512-bit output representation does not independently grant 256-bit quantum collision security. The generic idealized capacity ceiling is about 123.6 bits, and no structural result for the exact instance is supplied.

### 13.3 Nullifier uniqueness and replay

The nullifier is deterministic for scope and secret. Canonical encodings remove multiple-representation ambiguity. The pool maps both digest halves and rejects reuse. Cross-pool replay changes scope. Part-A proof replay alone can recreate a checkpoint after completion, but the spent-nullifier check prevents another payout through the pool.

### 13.4 Knowledge soundness

Knowledge soundness depends on the complete AIR constraints, DEEP composition, hiding PCS, MMCS binding, FRI parameters, transcript binding, and Rust/Solidity equivalence. The generator reports 107 conjectured bits but only 56 best proven bits. The report does not upgrade this to a stronger claim.

### 13.5 Zero knowledge

The logical trace contains secrets, path data, and intermediate hashes. Plonky3's hiding PCS adds four random codewords and salted MMCS leaves. Fresh entropy is required per proof. The implementation tests that production construction uses OS entropy and that repeated proofs can differ. A full independent proof that the composed protocol leaks no witness information, especially through malformed inputs, proof length, query collisions, timing, or implementation side channels, is still required.

### 13.6 Statement and consumer binding

The pool constructs public values, so a relayer cannot alter payout fields without changing the statement. The registry binds continuation to `msg.sender`, which is the pool. Core proof and checkpoint digests prevent mixing A and B from different proofs. Mutation tests exercise statement changes, global changes, mixed parts, reordered queries, and salt/frontier corruption.

### 13.7 Operational privacy

The cryptographic proof does not hide transaction origin, recipient activity, fee, relayer behavior, timing, RPC access, browser telemetry, network address, or anonymity-set quality. Deposits and withdrawals are public. A small or correlated anonymity set can defeat practical privacy even if the proof is zero knowledge.

### 13.8 Ethereum post-quantum boundary

Ethereum account signatures, proposer/validator keys, consensus, storage addressing, transaction propagation, and the native asset are outside the proof-system claim. A quantum attacker who can forge Ethereum account signatures may disrupt users independently of note cryptography. The accurate description is a post-quantum-oriented application proof experiment on top of classically authenticated Ethereum.

## 14. Verification evidence and test intent

### 14.1 Cross-language vectors

The hash corpus contains 1,000 v3 cases covering commitments, nullifiers, payout digests, empty nodes, level-bound Merkle nodes, insertions, roots, and note encoding. Rust generates it; TypeScript and Solidity consume it. Boundary tests reject noncanonical limbs. Domain, length, byte order, level, and digest-half mutations change results.

### 14.2 AIR tests

Tests assert 256×190 shape, 1,186 constraints, degree seven, exact selector schedule, public-value binding, private limb usage, work-column constraints, operation boundaries, Merkle boundaries, and a valid witness. Solidity evaluates a generated Rust differential vector and preserves segmented Horner order.

### 14.3 Proof/verifier mutation tests

The real proof suite covers:

- strict v3 magic, version, profile and end markers;
- v2 rejection;
- noncanonical public and opened fields;
- exact 16/16 query split;
- reordered first-half queries;
- reordered second-half queries;
- transcript-bound global mutation;
- part-B global mutation;
- FRI salt mutation at a regenerated offset;
- malformed pruned frontier;
- mixed proof ID;
- changed statement at completion;
- consumer mismatch;
- idempotent duplicate A;
- one-use completion.

### 14.4 Pool tests and invariants

Pool tests cover exact denomination, duplicate/zero/noncanonical commitments, root evolution, path parity, scope versioning, known roots, canonical nullifiers, recipient/relayer/fee validation, checkpoint binding, payment failure rollback, reentrancy, forced balance, double spend, and atomic payout. Stateful invariants check that balance equals deposits minus withdrawals, withdrawals never exceed deposits, and the last withdrawn nullifier remains spent.

### 14.5 What tests do not prove

Tests do not prove cryptographic assumptions, absence of all Solidity bugs, worst-case gas for all valid proofs, network inclusion, censorship resistance, endpoint honesty, anonymity quality, or production side-channel resistance. Fuzz/invariant counts are finite. Generated vectors can catch parity errors but do not replace formal equivalence proofs.

## 15. Reproducibility and build

Pinned versions:

- Rust 1.97.0;
- Plonky3 exact commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`;
- Solidity 0.8.30;
- Foundry 1.7.1;
- Prague EVM target;
- Node 24.19.0;
- pnpm 11.20.0.

The Dockerfile installs these tools, copies the source, then runs Rust tests, a frozen pnpm install, TypeScript tests, Solidity code-size build, and Solidity tests. The parameter generator was run twice into separate directories and `diff -ru` returned no differences. This establishes deterministic manifests and security outputs for one source snapshot. It does not imply deterministic proof bytes; hiding randomness intentionally changes proofs.

Final production runtime sizes:

| Contract | Runtime bytes | EIP-170 margin |
|---|---:|---:|
| `PQTCAirStageVerifier` | 17,805 | 6,771 |
| `PQTCQueryVerifier` | 12,956 | 11,620 |
| `PQTCVerificationRegistry` | 13,123 | 11,453 |
| `PQTCClassicPool` | 7,548 | 17,028 |

## 16. Known limitations and required external review

### 16.1 Cryptographic blockers

- Decide whether 107 conjectured / 56 best proven bits is acceptable. If strict preservation of q48 proven security is required, reject q32.
- Independently review P2BB512 framing, capacity argument, constants, full/partial rounds, and structural attacks.
- Review the custom KeccakPair512 transcript and complete Fiat-Shamir composition in classical ROM and QROM settings.
- Review hiding PCS composition and ensure no deterministic/reused masking randomness can enter production.
- Verify every AIR constraint and boundary against the intended relation.
- Verify Rust and Solidity transcript, extension arithmetic, DEEP, MMCS, FRI, and codec equivalence.

### 16.2 EVM blockers

- Establish worst-case valid-proof gas, not only fixture gas.
- Review all calldata cursor arithmetic, bounds, allocations, loop limits, and narrowing casts.
- Quantify or eliminate abandoned-checkpoint storage griefing.
- Bind independently reviewed runtime code hashes into a deployment-candidate manifest.
- Repeat code-size and gas checks from exact deployment bytecode.
- Obtain actual network receipts only after explicit deployment authorization.

### 16.3 Operational blockers

- Review RPC cross-check assumptions and reorg depths.
- Review relayer replacement, transaction replacement, deadline, and receipt/event validation.
- Define safe note backup and local secret handling.
- Measure proving time/memory on representative user hardware.
- Establish a meaningful anonymity-set demonstration without linking deposits and withdrawals operationally.

## 17. Reviewer procedure

A reviewer should proceed in this order:

1. Read Sections 1–16 and the deviation table before reading code.
2. Treat Appendix A as the original baseline, not the current specification.
3. Treat current protocol/security/AIR documents in Appendix B as the normative v3 description.
4. Recompute hashes in the source manifest below.
5. Audit `pqtc-spec`, `pqtc-hash`, and SDK domain parity first.
6. Audit AIR trace generation and constraints together; do not review either in isolation.
7. Audit Rust proof transcript/codec and Solidity transcript/codec side by side.
8. Confirm every proof-controlled count is version-fixed and bounded before allocation or looping.
9. Reproduce manifests and compare exact bytes and parameter ID.
10. Generate multiple fresh proofs, verify natively and in EVM, and measure worst observed frontier/gas distributions.
11. Construct adversarial valid query-collision patterns or derive a formal maximum.
12. Review checkpoint storage economics and rollback across both contracts.
13. Do not authorize deployment solely because fixture gas and tests pass.

## 18. Complete source inventory

This report embeds 59 first-party source/configuration files totaling 528,942 bytes before Markdown framing.

| File | Language | Bytes | SHA-256 |
|---|---|---:|---|
| `contracts/src/PQTCClassicPool.sol` | solidity | 8,652 | `5ce4f94692e87922efd0584e543afc43937ad8647161dd4e3e16bb8a442c0fd0` |
| `contracts/src/PQTCDomains.sol` | solidity | 731 | `82575864ba97c7c4045b5a0d9ea5ab2c7a672b3ceb79550433a8e907c7697025` |
| `contracts/src/PQTCVerificationRegistry.sol` | solidity | 23,407 | `8553941eb44998dca5bd18cc6eeb7d016bb8cccfa334efb7f693a4a1575a4722` |
| `contracts/src/libraries/BabyBear.sol` | solidity | 1,371 | `0b260468dfdd98e9a837165dbd61a2f908f15bed31e8e7fb285b0c6242ed5d63` |
| `contracts/src/libraries/BabyBearExt4.sol` | solidity | 4,288 | `fa3063d15f60b4fde8570b23228a9d05fd90221fb40d3ba5b0eb153412da0e3f` |
| `contracts/src/libraries/BabyBearExt4Packed.sol` | solidity | 5,418 | `84440d8861592ac49c70600ea99ad3978a92e2cae55dfadc5720850bf3b0d874` |
| `contracts/src/libraries/CanonicalCodec.sol` | solidity | 2,864 | `d5b52d20c25e1e88079016993877e588c15c020a3c19f7c9f7437ea938926929` |
| `contracts/src/libraries/Digest512.sol` | solidity | 618 | `be41fb4d1d6ba6c2cd44ca3fe9d0b8515c4ca6a156b05342b9678a3e97cc9f75` |
| `contracts/src/libraries/KeccakPair512.sol` | solidity | 1,214 | `2f526fcf9c2fd2ef889938260df6585392d90f6217c0abbcae38cd257090a7d8` |
| `contracts/src/libraries/P2BB512.sol` | solidity | 21,406 | `eac664c088b7acacd0401dc1714afaa3a7e6459a71b93b330f6c321c70139534` |
| `contracts/src/libraries/PQTCApplicationHash.sol` | solidity | 7,317 | `add9a5b6a21f32216b9f87a64abd24c49710405d7a3f59f5d918824e2713fe5d` |
| `contracts/src/libraries/PQTCProofCodec.sol` | solidity | 4,780 | `a4fd095958ca9c35268bb7a5b5da5950a09b0c3b4c5f50118fbeeb455d6f61bd` |
| `contracts/src/libraries/Transcript512.sol` | solidity | 5,577 | `1928fc0fd636e900db5575bc85d5fc0d51ff6efcd6271e62871d0810ea7c35c1` |
| `contracts/src/verifier/AirEvaluatorPoseidon.sol` | solidity | 21,818 | `eb34d91b6c94c53c010078b6a90d7222841dddb5808d7d4021be3538b741e09e` |
| `contracts/src/verifier/FriVerifier.sol` | solidity | 2,062 | `01f91143211fd02db8b22ff8362196faba53aa131943a5b46ab2744462c2330b` |
| `contracts/src/verifier/MmcsVerifier.sol` | solidity | 9,328 | `950892ccf87e23f30083b3ea1d9689e8904b2770d25a280fed7b056010cced4d` |
| `contracts/src/verifier/PQTCAirStageVerifier.sol` | solidity | 3,547 | `4f810d9fe141236e5f19219c31dc225dba37e0f9657b20364bbb21ece7d16202` |
| `contracts/src/verifier/PQTCQueryVerifier.sol` | solidity | 16,578 | `8c6316f1132875dc647cba0d51c4779c8b14d97cf904acea67f01577efffa92f` |
| `contracts/src/verifier/StarkOodVerifier.sol` | solidity | 4,709 | `9f44097ddc797d3bf0841584d68983696952aecaeaac79e15021115ed2251828` |
| `contracts/test/AirEvaluator.t.sol` | solidity | 6,849 | `b86a5482e0ac235548678866ffb97025e7e3a39f0ab584fafd175e09325d97ca` |
| `contracts/test/BabyBear.t.sol` | solidity | 1,915 | `00cc49cfbd3fd201a2e0019cbfc4a120ef298fbbe8f1f7311e64c96cefe878d9` |
| `contracts/test/HashVectors.t.sol` | solidity | 6,780 | `c1fb6dfe291acb0f7854ff1205d87ab343bcf00618e33fbf8724dca71c0603a3` |
| `contracts/test/P2BB512.t.sol` | solidity | 6,711 | `12de6c8ff8eb312c02e01be265dcf16d4307f2ebd5af6ed19f9205019cb19bba` |
| `contracts/test/PQTCClassicPool.t.sol` | solidity | 18,661 | `0f7b47328a3668a5bb0caf1ef0459f0e39e59d2155004a30d529320e5c873d6e` |
| `contracts/test/PQTCClassicPoolInvariant.t.sol` | solidity | 5,009 | `32e4ab2d4c317d3633abe33ba51d76eca836c5ad2aad46d23b08e5c439240edf` |
| `contracts/test/StagedVerifier.t.sol` | solidity | 18,228 | `f8a5707247dfe5b4eb98da42eaf353073e71256db8c9f97e6b5c4237c824c125` |
| `contracts/test/VerifierFoundation.t.sol` | solidity | 6,851 | `d1b96f53fb4443bf981b6553ea745fe78d5fe1239cb369d6feb1e5afcaf4555f` |
| `crates/pqtc-cli/Cargo.toml` | toml | 864 | `3d74f02bf0059aeefab6b752e93a986ab20e415e59c9ebcea94db77ce90f948c` |
| `crates/pqtc-cli/src/main.rs` | rust | 41,315 | `33237faccaa91f93981a5a7f799a4f0748c40cd83f3fe39d38e240b690355a94` |
| `crates/pqtc-hash/Cargo.toml` | toml | 439 | `b1e69d03afb27cfbb30dfe53ab0892378d15481b53ec3efb129b9cc4c90ece61` |
| `crates/pqtc-hash/src/lib.rs` | rust | 23,669 | `44d0e1f817ffbfd92c65ffee0bb34eb1b5002c4fcce7f88fee75e3661a5266f6` |
| `crates/pqtc-indexer/Cargo.toml` | toml | 309 | `2cc72f6eb0f2af8e1ecdf14df0336cc2613f4da55c5350f9e1bcd554f24c462b` |
| `crates/pqtc-indexer/src/lib.rs` | rust | 10,178 | `30f34740b54c72a7eb2d22c9443e0b44ab9688911dc1ecbc494e4e71cd8c9479` |
| `crates/pqtc-merkle/Cargo.toml` | toml | 373 | `b2d2a8a9e78c6f0edddd6c629b7bdc49cf4428b43fc241aa60dcb20956cc0647` |
| `crates/pqtc-merkle/src/lib.rs` | rust | 8,027 | `e88b08bede72a6c3d12b582d6bdb2e4f0f073719469a5383579605dcea164609` |
| `crates/pqtc-poseidon-air/Cargo.toml` | toml | 603 | `9adea4eb899121cad7fd644aa9af75f6c73f0ca51c39a17767b24d7d600f7afb` |
| `crates/pqtc-poseidon-air/src/air.rs` | rust | 23,561 | `feb6d3a9949b69b55acc20e9b8826e0086bef1f9f7ae296df8ed4cafc61a3c53` |
| `crates/pqtc-poseidon-air/src/lib.rs` | rust | 14,715 | `5a25c94d811f4e6004634af887baa5f4c8b53ead18a33db4e0a8868a45811c26` |
| `crates/pqtc-security/Cargo.toml` | toml | 499 | `ccd74b00cf0342facf98c04aca8a4fd5f8b87d063316f6435ebcfcce092d22dd` |
| `crates/pqtc-security/src/lib.rs` | rust | 13,741 | `53e97ad9b4da7a472393f681ae86e1ec1a370efd805812d626424df9f2b41df7` |
| `crates/pqtc-spec/Cargo.toml` | toml | 343 | `e9976f9d7be608ed6e03612383489cbdcfca7f08176db8b3f01c12f8cb51b901` |
| `crates/pqtc-spec/src/domains.rs` | rust | 529 | `b020c104d76dac15ef912c8a0891c6eb3e18b61865eed131b5b606ef3d3ec63f` |
| `crates/pqtc-spec/src/lib.rs` | rust | 13,445 | `0f6d38b4e028d8162390454fddc6d72d440a6750c1e84ef80655066142d56ec5` |
| `crates/pqtc-stark/Cargo.toml` | toml | 638 | `4d132001a27feb07a0ebe848adfbacbc6b3928eab7229d05d494247f8f751e0b` |
| `crates/pqtc-stark/src/codec.rs` | rust | 41,763 | `006e0183d2a259075003ec73e6d2199160cba9a2148b08d46b9611de30d69d94` |
| `crates/pqtc-stark/src/crypto.rs` | rust | 9,976 | `4ca0894b4172e8b53d7efed35064426e99c5770cdd4f895dae8aa29ed312091a` |
| `crates/pqtc-stark/src/lib.rs` | rust | 4,465 | `eb0166dccf6fe1e8cdcd59f8a94dcfda058dbc4fd73bf5f7925b160c66d6b967` |
| `crates/pqtc-stark/src/query.rs` | rust | 19,575 | `feb1b778459660babee3a199cab968f6403874df0a97d1a524baee5f3c8640a2` |
| `packages/sdk/package.json` | json | 768 | `2fcc6919b555985d6405b809f6fc128ca5c2bf521a677b5bcb395c4d87e2a4bd` |
| `packages/sdk/src/domains.ts` | typescript | 1,461 | `291575c9a6389628f9187c49bc1d9f350788ad9943132327e98ade2bdc0a5db0` |
| `packages/sdk/src/index.ts` | typescript | 23,917 | `ad783a94010a598b27d372e7274a96a07ed9a867a8d636ec872775ea6ac34a71` |
| `packages/sdk/src/relayer.ts` | typescript | 26,676 | `8452c16486935ec7974e8c58b752e1928a63f3bdc77a02c0d259cdb2d36f34ed` |
| `packages/sdk/test/domains.test.ts` | typescript | 1,336 | `dba50f5867f7c3b008974e2b1571076addb3994b5131ced916f48d46ab789ca4` |
| `packages/sdk/test/relayer.test.ts` | typescript | 13,966 | `1341666c147255bb3530179af23e16c80596d20a0fa8a17b42c69f93f01b630d` |
| `packages/sdk/test/vectors.test.ts` | typescript | 9,671 | `7b8718e9f0bc9d8b8c22edf5cdf6c4a141e9a0a52cf345ff9fa28743c17226b2` |
| `packages/sdk/tsconfig.json` | json | 347 | `a2ff4eb744682b923b5b2d6791abe5f04f21fb8d3ea12c1f2e452fa9de44a95a` |
| `script/DeploySepolia.s.sol` | solidity | 2,031 | `67e244bb058b1d15ac3a25657323dd2b27413be2a09b4afccbc1e811a0c3497d` |
| `script/LocalTwoPartE2E.s.sol` | solidity | 1,503 | `c0d158b63f18523af68059b8a3fb9e8110a09d7477b0f7b82ac0bd25ff28db8d` |
| `script/SubmitTwoPartProof.s.sol` | solidity | 1,550 | `5f17ea132ecf68d43021e0af7b25d56e55896072e805079c7a460c5a094398fc` |

## 19. Solidity declaration completeness manifest

The embedded Solidity files contain 48 first-party contract, library, or interface declarations. Each appears in full in Appendix C.

| Declaration | Kind | File |
|---|---|---|
| `IPQTCVerificationRegistry` | interface | `contracts/src/PQTCClassicPool.sol` |
| `PQTCClassicPool` | contract | `contracts/src/PQTCClassicPool.sol` |
| `PQTCDomains` | library | `contracts/src/PQTCDomains.sol` |
| `PQTCVerificationRegistry` | contract | `contracts/src/PQTCVerificationRegistry.sol` |
| `BabyBear` | library | `contracts/src/libraries/BabyBear.sol` |
| `BabyBearExt4` | library | `contracts/src/libraries/BabyBearExt4.sol` |
| `BabyBearExt4Packed` | library | `contracts/src/libraries/BabyBearExt4Packed.sol` |
| `CanonicalCodec` | library | `contracts/src/libraries/CanonicalCodec.sol` |
| `Digest512Lib` | library | `contracts/src/libraries/Digest512.sol` |
| `KeccakPair512` | library | `contracts/src/libraries/KeccakPair512.sol` |
| `P2BB512` | library | `contracts/src/libraries/P2BB512.sol` |
| `PQTCApplicationHash` | library | `contracts/src/libraries/PQTCApplicationHash.sol` |
| `PQTCProofCodec` | library | `contracts/src/libraries/PQTCProofCodec.sol` |
| `Transcript512` | library | `contracts/src/libraries/Transcript512.sol` |
| `AirEvaluatorPoseidon` | library | `contracts/src/verifier/AirEvaluatorPoseidon.sol` |
| `FriVerifier` | library | `contracts/src/verifier/FriVerifier.sol` |
| `MmcsVerifier` | library | `contracts/src/verifier/MmcsVerifier.sol` |
| `PQTCAirStageVerifier` | contract | `contracts/src/verifier/PQTCAirStageVerifier.sol` |
| `PQTCQueryVerifier` | contract | `contracts/src/verifier/PQTCQueryVerifier.sol` |
| `StarkOodVerifier` | library | `contracts/src/verifier/StarkOodVerifier.sol` |
| `PoseidonAirHarness` | contract | `contracts/test/AirEvaluator.t.sol` |
| `OodHarness` | contract | `contracts/test/AirEvaluator.t.sol` |
| `AirEvaluatorTest` | contract | `contracts/test/AirEvaluator.t.sol` |
| `BabyBearHarness` | contract | `contracts/test/BabyBear.t.sol` |
| `BabyBearTest` | contract | `contracts/test/BabyBear.t.sol` |
| `HashVectorsTest` | contract | `contracts/test/HashVectors.t.sol` |
| `P2BB512Harness` | contract | `contracts/test/P2BB512.t.sol` |
| `P2BB512Test` | contract | `contracts/test/P2BB512.t.sol` |
| `PoolMockRegistry` | contract | `contracts/test/PQTCClassicPool.t.sol` |
| `PaymentReceiver` | contract | `contracts/test/PQTCClassicPool.t.sol` |
| `RejectPayment` | contract | `contracts/test/PQTCClassicPool.t.sol` |
| `ReentrantRecipient` | contract | `contracts/test/PQTCClassicPool.t.sol` |
| `PQTCClassicPoolTest` | contract | `contracts/test/PQTCClassicPool.t.sol` |
| `InvariantRegistry` | contract | `contracts/test/PQTCClassicPoolInvariant.t.sol` |
| `PoolInvariantHandler` | contract | `contracts/test/PQTCClassicPoolInvariant.t.sol` |
| `PQTCClassicPoolInvariantTest` | contract | `contracts/test/PQTCClassicPoolInvariant.t.sol` |
| `FixturePool` | contract | `contracts/test/StagedVerifier.t.sol` |
| `NoopAirStageVerifier` | contract | `contracts/test/StagedVerifier.t.sol` |
| `NoopQueryVerifier` | contract | `contracts/test/StagedVerifier.t.sol` |
| `FriSkippingQueryVerifier` | contract | `contracts/test/StagedVerifier.t.sol` |
| `SkipInputQueryVerifier` | contract | `contracts/test/StagedVerifier.t.sol` |
| `NoReductionQueryVerifier` | contract | `contracts/test/StagedVerifier.t.sol` |
| `CompactVerifierTest` | contract | `contracts/test/StagedVerifier.t.sol` |
| `VerifierFoundationHarness` | contract | `contracts/test/VerifierFoundation.t.sol` |
| `VerifierFoundationTest` | contract | `contracts/test/VerifierFoundation.t.sol` |
| `DeploySepolia` | contract | `script/DeploySepolia.s.sol` |
| `LocalTwoPartE2E` | contract | `script/LocalTwoPartE2E.s.sol` |
| `SubmitTwoPartProof` | contract | `script/SubmitTwoPartProof.s.sol` |

## 20. Generated artifact inventory

Large vectors and proof payloads are generated evidence rather than source code. They are not expanded inline because they would add about 4.7 MB of machine-generated data. Their exact snapshot identities are:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `parameters/ci/manifest.bin` | 148 | `31d86f7c1cba14f02c376aae8c9d23f16e754ea0f039e90817adf3b6ebdf8112` |
| `parameters/ci/manifest.json` | 891 | `781c5ee70cbf7607a54d809262d0f28c4b3ec48f4e044c7409524e4fd603677b` |
| `parameters/ci/parameter-id.txt` | 131 | `14ee74d203c34e6c2c4d74442afa45c3c1ff85de74735a2207730fe71ca81444` |
| `parameters/ci/security-analysis.json` | 278 | `a17ccc27ff3684d528489a43779389f9cff2a2bcd087d85960a39c36fe001447` |
| `parameters/dev/manifest.bin` | 149 | `2a057502d5157799eeabad5269cf77127e9382d0e0b8d63b235f7f523c58b86a` |
| `parameters/dev/manifest.json` | 891 | `1efbaf8674058400220e34bbf4d1095a90e302e329d7f73c3945826d45f466aa` |
| `parameters/dev/parameter-id.txt` | 131 | `b3de16a9fd29c3a238f141b2b7182e7a9a76cecccfdb3fa17d948bf7a2a6d189` |
| `parameters/dev/security-analysis.json` | 274 | `c627f1d404bc5b64333226dddf7d8e3ee2869855d7ed506c7930c63583c3e6ba` |
| `parameters/sepolia-v0.3/manifest.bin` | 158 | `3c4233b4e316d6725abb416eb78fa543ca987c4dc487ada7e67c463e5ad0d21e` |
| `parameters/sepolia-v0.3/manifest.json` | 903 | `0d891caaddfc6d954655e15cf86e90ed99825c9f060df907c3afabab695b1c42` |
| `parameters/sepolia-v0.3/parameter-id.txt` | 131 | `dc13595b449af2270a79cc8c95d7454f32788e8ca9c0e9aab0f28c1b577521c1` |
| `parameters/sepolia-v0.3/security-analysis.json` | 279 | `790d06863695a6ce591454d564af1822659802f8433bef24f80bfdfd2151458d` |
| `test-vectors/verifier/v3/part-a.pqtc` | 101,990 | `117620affe3dd9788089bc357f894c999d94215bcea54c26db6c28f5244764e7` |
| `test-vectors/verifier/v3/part-b.pqtc` | 108,294 | `b73057343f2e5f0f8557ce157f1576eb7ebffd665d09342b4096af57f4e8ab18` |
| `test-vectors/verifier/v3.json` | 2,631,824 | `41f93db40e659a96b27fe13fd8e6915c501d8f1fb4de78a0d2093a3ac5f8160e` |
| `test-vectors/hash/v3.json` | 1,855,944 | `4515d8f26dbc03dd694ea3347dfa7dc5d543e67516a5ceafdd6b1ad23c2e5ad2` |

The small human-readable manifests, security reports, parameter IDs, and binary manifest hex are included in Appendix E.

## 21. Explicit exclusions

- `lib/forge-std/**`: external dependency;
- Cargo registry/git checkouts and `node_modules/**`: external dependencies;
- `target/**`, `out/**`, `cache/**`, `packages/sdk/dist/**`: generated build output;
- `broadcast/**`: historical execution records from earlier experiments, not v3 source and potentially misleading as deployment evidence;
- `.env`: private/local environment material;
- `soljson-latest.js`: external compiler distribution;
- large generated JSON vector corpora and binary proof parts: represented by hashes above and regenerable from included code;
- empty legacy directories: no source content.

---

# Appendix A — Original engineering plan, verbatim

The following is the complete original plan. It is included to let reviewers verify every deviation rather than relying on the summary above.

## `pq-tornado-classic-engineering-plan.md`

- Bytes: 48,850
- SHA-256: `968467bc933d492a3cbbcc3ef2decac36c709b09f4ab03752d4f33e040ff95cb`

<details><summary>Complete file</summary>

````markdown
# PQ Tornado Cash Classic — Engineering Plan

**Status:** implementation-ready research plan  
**Target:** a functional fixed-denomination ETH privacy pool deployed on Ethereum Sepolia  
**Proof model:** transparent, hash-based, zero-knowledge STARK  
**Application hash:** EVM Keccak-256, composed into a 512-bit digest  
**Arithmetization:** custom AIR  
**PCS/LDT:** two-adic hiding FRI for the first testnet release  
**Primary implementation framework:** Plonky3, pinned to an exact commit  
**Security status of final testnet artifact:** research experiment, not production-ready or audited

---

## 1. Objective

Build a Tornado Cash Classic-style privacy pool whose **application-level anonymity set and spend proof do not depend on elliptic-curve discrete logarithms, pairings, KZG, IPA, Groth16, PLONK/KZG, or another classical proof wrapper**.

At the end of the plan, a user must be able to:

1. Generate a random note locally.
2. Deposit a fixed amount of Sepolia ETH with the note commitment.
3. Reconstruct the pool's Keccak Merkle tree from events.
4. Generate a genuinely witness-hiding STARK proving ownership of one unspent commitment.
5. Have that proof verified by EVM contracts on Sepolia, either:
   - atomically in one transaction if the optimized verifier fits Ethereum limits; or
   - through a permissionless staged verifier that records a fact before withdrawal.
6. Withdraw to an unrelated recipient through an unrelated relayer.
7. Observe rejection of replay, double-spend, malformed-proof, wrong-root, wrong-nullifier, wrong-recipient, and wrong-fee attempts.

The testnet deployment is the deliverable. A production security claim is not.

---

## 2. Scope boundary

### 2.1 In scope

- Native ETH only.
- One immutable denomination per pool.
- One commitment per deposit.
- One note consumed per withdrawal.
- Twenty-level append-only Merkle tree.
- Keccak-based note commitments, nullifiers, tree nodes, proof commitments, and transcript.
- Custom AIR expressing:
  - note commitment derivation;
  - nullifier derivation;
  - Merkle membership;
  - binding to the withdrawal statement.
- A transparent zero-knowledge STARK.
- Direct EVM verification and a staged-verification fallback.
- Rust prover, verifier, CLI, indexer, TypeScript SDK, Solidity contracts, deployment scripts, benchmarks, and reproducible test vectors.
- Sepolia deployment and end-to-end demonstration.

### 2.2 Explicitly out of scope

- Tornado Nova / arbitrary private balances.
- Multiple private inputs or outputs.
- Change notes.
- Private internal transfers.
- ERC-20 support.
- Cross-chain bridging.
- Account abstraction or paymasters.
- Yield.
- Governance.
- Upgradeable custody contracts.
- Compliance or association-set filtering.
- Recursive proof aggregation.
- A browser prover or polished frontend.
- Making Ethereum accounts, validators, or consensus post-quantum secure.
- A claim that the entire Ethereum transaction lifecycle is post-quantum secure.

These exclusions are deliberate. They keep the first relation close to Tornado Classic and isolate the proof-system research.

---

## 3. Threat model and intended claim

Treat Ethereum as an ideal append-only state machine for this experiment. The claim being investigated is:

> Given an honest EVM execution of the deployed contracts, a quantum-capable adversary cannot recover a note from its public commitment, open one commitment in two useful ways, forge membership in the accepted deposit tree, produce a valid spend proof without the note witness, or link a valid zero-knowledge withdrawal proof to a particular deposit better than permitted by public metadata.

### 3.1 Security properties required

1. **Note hiding**
   - Public commitments must not reveal either 256-bit note secret.
   - Notes are generated by an operating-system CSPRNG.

2. **Commitment binding**
   - It must be computationally infeasible, including under generic quantum attacks, to find two useful openings to one commitment.

3. **Accumulator binding**
   - It must be infeasible to create a false Merkle path or alternate accepted tree under the same root.

4. **Nullifier uniqueness**
   - One note deterministically maps to one public nullifier.
   - A nullifier is scoped to one pool and protocol version.

5. **Quantum-oriented knowledge soundness**
   - An accepted proof must imply knowledge of a valid note opening and Merkle path.

6. **Zero knowledge**
   - The proof must hide note secrets, leaf index, path bits, siblings, and intermediate Keccak states.
   - Merely using a STARK is insufficient; hiding must be enabled and reviewed.

7. **Statement binding**
   - The proof must be bound to the exact scope, root, nullifier, recipient, relayer, and fee.

8. **No classical proof wrapper**
   - Ethereum must verify the hash-based STARK itself or an equally post-quantum-oriented outer proof.
   - Groth16/KZG/IPA compression is prohibited.

### 3.2 Honest limitations

- Keccak and FRI security against quantum attackers is modeled through concrete and random-oracle-style analyses, not an unconditional proof of post-quantum security.
- Fiat–Shamir composition requires a separate quantum-random-oracle review.
- Ethereum's own `keccak256` storage addressing, account signatures, and consensus are outside scope.
- The testnet artifact is described as a **PQ-oriented zk-STARK mixer experiment**, not audited production software.

---

## 4. Locked architecture decisions

Agents must not silently reopen these choices. Any material change requires an Architecture Decision Record (ADR), updated test vectors, and a changed protocol identifier.

| Area | Locked v0.1 decision |
|---|---|
| Pool model | Tornado Classic, fixed denomination |
| Asset | Native Sepolia ETH |
| Tree depth | 20 |
| Note ownership | Knowledge of two random 32-byte secrets |
| Application hash | `KeccakPair512`, defined below |
| Merkle tree | Binary append-only tree, direct EVM insertion |
| Proof arithmetization | Custom AIR |
| First PCS | Plonky3 hiding two-adic FRI |
| Base field | BabyBear |
| Challenge field | Degree-4 BabyBear extension |
| Transcript | Keccak-based, custom 512-bit transcript state |
| Proof commitment | Hiding Merkle MMCS using 512-bit Keccak-pair digests |
| Circle FRI | Deferred optimization track; not v0.1 |
| Verification | Direct verifier if feasible; staged verifier is mandatory fallback |
| Custody contract | Immutable and non-upgradeable |
| Testnet | Ethereum Sepolia |
| Production claim | Prohibited |

### Why two-adic hiding FRI first

Plonky3 currently provides a hiding FRI PCS and hiding Merkle MMCS with cryptographic randomness. Its current Circle PCS is not a hiding PCS. Circle FRI therefore remains a useful future benchmark, but it is not allowed to block the first functional zero-knowledge release.

### Why BabyBear + degree-4 extension

- The Keccak AIR represents 64-bit lanes using 16-bit limbs, fitting naturally in a roughly 31-bit field.
- BabyBear multiplication remains within inexpensive EVM word arithmetic.
- The degree-4 extension provides a challenge space large enough for a testnet target around 100 bits, subject to the generated security report.
- Plonky3 already demonstrates hiding FRI with this field family.

A short Phase 0 benchmark may compare Goldilocks with a quadratic extension, but changing the baseline requires an ADR before protocol code is written.

---

## 5. Cryptographic encoding specification

This section is normative.

### 5.1 `KeccakPair512`

`KeccakPair512` is **not** standard Keccak-512. It is two domain-separated EVM Keccak-256 invocations:

```text
K512(tag, payload) =
    keccak256(0x00 || tag || payload)
    ||
    keccak256(0x01 || tag || payload)
```

The output is 64 bytes:

```text
Digest512 {
    bytes32 left;   // branch 0
    bytes32 right;  // branch 1
}
```

Every protocol message uses fixed-width fields and explicit byte order. No ambiguous variable-length concatenation is permitted.

The schemas below are deliberately at most 135 bytes per branch, so each EVM Keccak-256 call absorbs one rate block.

### 5.2 Domain tags

Freeze one-byte tags in `spec/domains.rs`, `packages/sdk/src/domains.ts`, and `contracts/src/PQTCDomains.sol`.

```text
0x10 SCOPE
0x11 NOTE
0x12 NULLIFIER
0x13 EMPTY_LEAF
0x14 PAYOUT
0x15 STATEMENT
0x20 APP_MERKLE_NODE

0x40 PROOF_LEAF
0x41 PROOF_NODE
0x42 TRANSCRIPT_INIT
0x43 TRANSCRIPT_ABSORB
0x44 TRANSCRIPT_SQUEEZE
0x45 PARAMETER_MANIFEST
```

Changing a tag changes the protocol.

### 5.3 Canonical integer encodings

- `chainId`: unsigned 64-bit, big-endian.
- `protocolVersion`: unsigned 32-bit, big-endian.
- `treeDepth`: unsigned 8-bit.
- `denomination`: unsigned 256-bit, big-endian.
- `fee`: unsigned 256-bit, big-endian.
- `address`: exactly 20 bytes.
- Base-field wire element: unsigned 32-bit, big-endian, and strictly less than the BabyBear modulus.
- Extension element: four canonical base-field coefficients in coefficient order.
- `Digest512`: `left || right`.

The deployment script must reject a chain ID above `2^64 - 1`.

### 5.4 Parameter identifier

Generate a canonical binary parameter manifest, `parameters/v0.1/manifest.bin`, containing at least:

- Plonky3 commit.
- Rust toolchain.
- field and extension definitions;
- AIR version and AIR source hash;
- tree depth;
- all hash domains and encodings;
- trace shape;
- FRI blowup;
- FRI folding schedule;
- query count;
- final polynomial bound;
- grinding parameters;
- hiding random-codeword count;
- hiding MMCS salt count;
- proof codec version;
- Solidity verifier interface versions and expected runtime code hashes.

Then:

```text
parameterId = K512(PARAMETER_MANIFEST, manifest.bin)
```

The human-readable `manifest.json` is generated from the same typed Rust object; it is not the hashed source of truth.

### 5.5 Pool scope

```text
scopePayload =
    chainId_u64
    || poolAddress_20
    || denomination_u256
    || treeDepth_u8
    || protocolVersion_u32
    || parameterId_64

scope = K512(SCOPE, scopePayload)
```

Payload size per branch:

```text
1 branch + 1 tag + 8 + 20 + 32 + 1 + 4 + 64 = 131 bytes
```

The pool computes and stores `scope` in its constructor.

### 5.6 Note

Generate independently:

```text
nullifierSecret : 32 random bytes
trapdoor        : 32 random bytes
```

Then:

```text
commitment = K512(
    NOTE,
    scope_64 || nullifierSecret_32 || trapdoor_32
)
```

Per-branch message size is 130 bytes.

### 5.7 Nullifier

```text
nullifierHash = K512(
    NULLIFIER,
    scope_64 || nullifierSecret_32
)
```

Per-branch message size is 98 bytes.

The commitment is intentionally not included. Reusing a nullifier secret across notes causes the notes to share a nullifier and harms only the user; the SDK must reject locally detected secret reuse.

### 5.8 Empty leaf and zero tree

```text
zero[0] = K512(EMPTY_LEAF, scope_64)

for level in 0..19:
    zero[level + 1] =
        K512(APP_MERKLE_NODE, level_u8 || zero[level] || zero[level])
```

### 5.9 Merkle node

At tree level `level`, where 0 joins leaves:

```text
parent = K512(
    APP_MERKLE_NODE,
    level_u8 || left_64 || right_64
)
```

Per-branch message size is 131 bytes.

Level domain separation is mandatory.

### 5.10 Payout binding

```text
payoutDigest = K512(
    PAYOUT,
    recipient_20 || relayer_20 || fee_u256
)
```

Per-branch message size is 106 bytes.

The Solidity pool recomputes this digest. The digest is included in the STARK public values and boundary-constrained by the AIR.

### 5.11 Public statement

The STARK public values, in exact order, are:

```text
scope.left[16-bit limbs 0..15]
scope.right[16-bit limbs 0..15]

root.left[16-bit limbs 0..15]
root.right[16-bit limbs 0..15]

nullifierHash.left[16-bit limbs 0..15]
nullifierHash.right[16-bit limbs 0..15]

payoutDigest.left[16-bit limbs 0..15]
payoutDigest.right[16-bit limbs 0..15]
```

Each `bytes32` is split into sixteen 16-bit big-endian limbs. Total public base-field values: 128.

The verifier absorbs all public values before proof commitments.

### 5.12 Private witness

```text
nullifierSecret : [u8; 32]
trapdoor        : [u8; 32]
leafIndex       : u32, constrained to 20 bits
pathBits        : [bit; 20]
siblings        : [Digest512; 20]
```

`pathBits[level]` must equal bit `level` of `leafIndex`.

---

## 6. Withdrawal relation

The AIR proves:

```text
commitment = K512(NOTE, scope || nullifierSecret || trapdoor)

computedNullifier =
    K512(NULLIFIER, scope || nullifierSecret)

computedNullifier == public nullifierHash

current = commitment

for level in 0..19:
    bit = pathBits[level]
    assert bit * (bit - 1) == 0

    left  = bit == 0 ? current        : siblings[level]
    right = bit == 0 ? siblings[level] : current

    current =
        K512(APP_MERKLE_NODE, level || left || right)

current == public root
```

The AIR also constrains all four public digests—scope, root, nullifier, and payout—to the verifier-supplied public values.

No amount arithmetic is private. The pool's denomination is immutable and enforced in Solidity.

---

## 7. AIR implementation strategy

The project intentionally has two AIR implementations.

## 7.1 Reference AIR: correctness first

Use Plonky3's maintained Keccak-f AIR as the primitive and extend it with a controller.

### Fixed operation schedule

The withdrawal requires exactly 44 Keccak-f permutations:

```text
0,1      note digest branches
2,3      nullifier digest branches
4,5      Merkle level 0 branches
6,7      Merkle level 1 branches
...
42,43    Merkle level 19 branches
```

Each permutation uses 24 Keccak-f rounds, for 1,056 active rows. Pad to a power-of-two trace height of 2,048 before hiding-FRI expansion.

### Controller responsibilities

Add controller columns and constraints that:

- identify operation, branch, level, and Keccak round;
- place the exact fixed-length message in the rate portion;
- apply Ethereum Keccak padding (`0x01`, zeros, final `0x80`);
- force capacity lanes to zero at permutation start;
- expose the first 32 output bytes at permutation end;
- combine two branch outputs into one `Digest512`;
- carry the note commitment into the Merkle chain;
- choose sibling ordering using a boolean path bit;
- compare the computed nullifier and root with public values;
- boundary-bind the payout digest;
- force idle/padding rows into one canonical form.

### Endianness

The EVM hashes byte strings. Keccak lanes are internally little-endian. Golden vectors must verify identical outputs across:

- Solidity `keccak256`;
- a Rust Keccak implementation configured for Ethereum Keccak, not NIST SHA3;
- the AIR witness generator;
- the native proof verifier;
- the Solidity STARK verifier.

### Why this AIR is only the reference path

The maintained Plonky3 Keccak AIR is wide: its columns include round flags, several complete lane-state representations, bit decompositions, and scratch values. That makes it excellent for correctness and prover reuse but expensive to open in an EVM proof.

The reference AIR is nevertheless sufficient for the required testnet release when combined with staged verification.

## 7.2 Compact AIR: EVM optimization track

After the reference proof is frozen, implement a narrower, longer microcoded Keccak AIR.

Target design:

- BabyBear field.
- Bit-sliced or 8/16-bit-limb representation.
- Preprocessed schedule columns for phase, round, lane, and rotation.
- Serialize expensive XOR/AND/rotation work over additional rows instead of opening thousands of columns per FRI query.
- Reuse a small state/scratch column set.
- Use lookup/permutation arguments only where they reduce total EVM verification cost.
- Target:
  - no more than 384 main-trace columns;
  - trace height no greater than `2^20` for one withdrawal;
  - identical public statement and witness schema;
  - identical `KeccakPair512` test vectors.

Candidate phase layout:

```text
ABSORB/PAD
THETA_C
THETA_D
THETA_APPLY
RHO_PI
CHI
IOTA
SQUEEZE
CONTROLLER
```

Do not optimize by weakening constraints. The reference and compact AIRs must accept exactly the same valid witnesses.

### Compact AIR equivalence tests

For randomized witnesses:

1. Run the plain Rust reference function.
2. Generate reference AIR trace and validate all constraints.
3. Generate compact AIR trace and validate all constraints.
4. Compare commitment, nullifier, and root.
5. Mutate each witness component and confirm both AIRs reject.

The compact AIR is a stretch gate for a single-transaction verifier, not a gate for the staged Sepolia demo.

---

## 8. Proof stack

## 8.1 Mainline stack

```text
Classic withdrawal relation
        ↓
custom Keccak AIR
        ↓
Plonky3 uni-STARK or batch-STARK
        ↓
HidingFriPcs
        ↓
two-adic radix-2 FRI
        ↓
MerkleTreeHidingMmcs
        ↓
KeccakPair512 commitments
        ↓
Keccak-based Fiat–Shamir
```

Use `p3-batch-stark` only if separating the controller and Keccak AIR materially improves the implementation. A monolithic reference AIR is acceptable and likely simpler.

## 8.2 Zero-knowledge configuration

The proof configuration must use:

- `HidingFriPcs`, not `TwoAdicFriPcs`;
- `MerkleTreeHidingMmcs`, not the non-hiding MMCS;
- a CSPRNG seeded from OS entropy;
- generated, reviewed values for:
  - random codeword count;
  - per-leaf salt elements;
  - quotient masking;
  - FRI query count;
  - grinding.

Never use `SmallRng`, a fixed seed, timestamp, wallet key, note secret, or transcript value to seed proof masking outside deterministic tests.

The proof-generation API must accept an injected `CryptoRng` for tests and use OS entropy in the CLI.

## 8.3 Proof-commitment hash

Do not use a 32-byte MMCS digest while claiming a 100-bit quantum-oriented binding target.

Implement Plonky3-compatible:

```text
KeccakPair512Hasher
KeccakPair512Compression
KeccakPair512Challenger
```

For proof leaves:

```text
K512(
    PROOF_LEAF,
    byteLength_u32 || canonicalRowBytes || saltBytes
)
```

For proof-tree nodes:

```text
K512(
    PROOF_NODE,
    leftDigest_64 || rightDigest_64
)
```

The Merkle path position authenticates the row index. Matrix dimensions and widths are checked separately, matching the MMCS interface, rather than being smuggled into an incompatible leaf-hasher API.

The leaf input can span multiple Keccak rate blocks; only application hashes were deliberately kept to one block.

## 8.4 Transcript

Implement an explicit duplex-style transcript over a 64-byte state:

```text
state_0 = K512(TRANSCRIPT_INIT, parameterId || publicValues)

state_{i+1} =
    K512(TRANSCRIPT_ABSORB, state_i || typedMessage)

squeeze_i =
    K512(TRANSCRIPT_SQUEEZE, state_i || counter)
```

Every absorbed item includes:

- one-byte item type;
- four-byte length;
- canonical bytes.

Challenges are derived with rejection sampling into the required base or extension field. Modulo bias is prohibited unless quantitatively justified and frozen in the specification.

Rust and Solidity implementations must match byte-for-byte.

## 8.5 Security profiles

Provide three manifests:

### `dev`

- Very few queries.
- No meaningful security claim.
- Used for rapid tests.

### `ci`

- Moderate query count.
- Intended to catch integration failures.
- No production claim.

### `sepolia-v0.1`

- Target at least 100 bits under the project's documented, quantum-adjusted accounting.
- Exact values generated using Plonky3's security-analysis crate plus a project-specific report that accounts for:
  - AIR/DEEP soundness;
  - FRI decoding assumption;
  - challenge-field size;
  - number of openings;
  - MMCS collision security;
  - Fiat–Shamir/QROM caveat;
  - quantum square-root reduction in grinding cost;
  - multi-target use across many proofs.

No engineer may copy benchmark/default parameters into `sepolia-v0.1` without generating this report.

## 8.6 Circle FRI track

Circle FRI remains an optional post-v0.1 benchmark:

- port identical AIR semantics to M31;
- wait for or implement a reviewed hiding Circle PCS;
- retain the same Keccak transcript and 512-bit commitment policy;
- compare proof size, prover time, and Solidity gas.

A non-hiding Circle proof is not acceptable for a mixer.

---

## 9. Canonical proof formats

Native Rust structs are not the wire format.

## 9.1 Compact proof, `PQTCProofV1`

Define a strict binary codec:

```text
magic:                 8 bytes, "PQTCSTK1"
codecVersion:          u16
parameterId:           64 bytes
publicValuesCount:     u16
publicValues:          count * u32
trace metadata
commitment metadata
commitments
OOD/opening values
FRI round commitments
final polynomial
grinding witness
query count
pruned multiproof
query openings
end marker
```

Requirements:

- Big-endian wire integers.
- No optional fields.
- No duplicate encodings.
- Every count checked against the fixed manifest before allocation.
- Field elements strictly less than the modulus.
- No trailing bytes.
- Parser returns structured errors and never panics on untrusted input.
- Serialization round-trip tests in Rust and TypeScript.

## 9.2 Staged proof, `PQTCStagedProofV1`

For EVM staging, transform the compact proof into:

1. A canonical **header**, containing all transcript and query-independent data.
2. One independent **query bundle** per derived FRI query.

Each query bundle carries full authentication paths rather than relying on a shared pruned multiproof. This increases total bytes but allows one query to be verified independently in one transaction.

The conversion must not create a new proof. It is an alternate serialization of the same commitments, openings, and FRI checks.

---

## 10. Solidity architecture

## 10.1 Contract set

```text
contracts/src/
├── PQTCClassicPool.sol
├── PQTCVerificationRegistry.sol
├── PQTCVerifierRouter.sol
├── PQTCParameters.sol
├── libraries/
│   ├── Digest512.sol
│   ├── KeccakPair512.sol
│   ├── CanonicalCodec.sol
│   ├── BabyBear.sol
│   ├── BabyBearExt4.sol
│   └── Transcript512.sol
└── verifier/
    ├── StarkHeaderVerifier.sol
    ├── StarkQueryVerifier.sol
    ├── FriVerifier.sol
    ├── MmcsVerifier.sol
    ├── AirEvaluatorController.sol
    ├── AirEvaluatorKeccakTheta.sol
    ├── AirEvaluatorKeccakRhoPi.sol
    └── AirEvaluatorKeccakChiIota.sol
```

Every deployed runtime contract must remain below EIP-170's 24,576-byte runtime-code limit.

Verifier modules are immutable. The router stores their addresses and code hashes in `parameterId`.

## 10.2 Pool state

```solidity
struct Digest512 {
    bytes32 left;
    bytes32 right;
}

uint256 public immutable denomination;
uint8   public constant TREE_DEPTH = 20;
Digest512 public scope;
Digest512 public parameterId;

uint32 public nextIndex;
Digest512[20] internal filledSubtrees;
Digest512[21] internal zeros;

mapping(bytes32 => mapping(bytes32 => bool)) public commitments;
mapping(bytes32 => mapping(bytes32 => bool)) public nullifiers;
mapping(bytes32 => mapping(bytes32 => bool)) public knownRoots;

IPQTCVerifierRouter public immutable verifier;
IPQTCVerificationRegistry public immutable factRegistry;
```

Keeping all historical roots is acceptable for the testnet experiment and prevents a staged proof from expiring because of unrelated deposits. A production design should replace this with bounded history plus root pinning.

## 10.3 Deposit

```solidity
function deposit(Digest512 calldata commitment)
    external
    payable
    nonReentrant
```

Checks:

- `msg.value == denomination`.
- Commitment is not zero.
- Commitment has not been submitted.
- Tree is not full.

Effects:

- Insert using twenty `K512(APP_MERKLE_NODE, ...)` operations.
- Record commitment.
- Record new root in `knownRoots`.
- Increment `nextIndex`.
- Emit:

```solidity
event Deposit(
    bytes32 indexed commitmentLeft,
    bytes32 indexed commitmentRight,
    uint32 leafIndex,
    bytes32 rootLeft,
    bytes32 rootRight,
    uint256 timestamp
);
```

## 10.4 Withdrawal statement

```solidity
struct Withdrawal {
    Digest512 root;
    Digest512 nullifierHash;
    address payable recipient;
    address payable relayer;
    uint256 fee;
}
```

Checks:

- Root is known.
- Nullifier is unspent.
- Recipient is nonzero.
- `fee <= denomination`.
- If fee is nonzero, relayer is nonzero.
- Recomputed payout digest matches the proof public values.
- Proof or verified fact matches the immutable scope and parameter ID.

Effects, before external calls:

- Mark both nullifier halves as spent.

Interactions:

- Pay `denomination - fee` to recipient.
- Pay fee to relayer.
- Revert atomically if either transfer fails.

## 10.5 Direct withdrawal

```solidity
function withdrawDirect(
    Withdrawal calldata w,
    bytes calldata proof
) external nonReentrant
```

This path is enabled only if the full proof verifies below the transaction gas cap with margin.

## 10.6 Fact-based withdrawal

```solidity
function withdrawFromFact(
    Withdrawal calldata w
) external nonReentrant
```

Compute the canonical statement hash and require the fact registry to contain it.

The fact is reusable at the registry level but the nullifier is not, so the pool remains the double-spend authority.

---

## 11. EVM verifier strategy

## 11.1 Direct verifier target

Targets, not assumptions:

- Runtime code per module: `< 24,576 bytes`.
- Proof bytes: `< 96 KiB`.
- Verifier execution gas: `< 8,000,000`.
- Full direct withdrawal: `< 15,000,000`.
- No malformed proof can cause unbounded memory expansion or an out-of-gas loop.

The reference AIR may not meet these targets.

## 11.2 Mandatory staged verifier

The testnet release is considered successful even if verification spans multiple transactions.

### Session flow

#### `beginVerification`

```solidity
function beginVerification(
    bytes calldata header,
    PublicStatement calldata statement
) external payable returns (bytes32 sessionId)
```

It:

1. Checks a minimum anti-spam bond.
2. Parses the canonical header with fixed manifest bounds.
3. Checks parameter ID and public values.
4. Replays all query-independent transcript steps.
5. Validates grinding.
6. Validates final-polynomial and query-independent FRI/AIR checks.
7. Derives the complete ordered query-index list.
8. Stores:
   - statement hash;
   - 512-bit header hash;
   - query count;
   - completion bitmap;
   - expiry;
   - creator;
   - bond.

#### `verifyQueryBatch`

```solidity
function verifyQueryBatch(
    bytes32 sessionId,
    bytes calldata header,
    QueryBundle[] calldata bundles
) external
```

It:

1. Recomputes and matches the 512-bit header hash.
2. Replays enough transcript state to derive each expected query index.
3. Rejects duplicate or out-of-order query numbers.
4. Verifies:
   - trace and quotient openings;
   - hiding salts;
   - MMCS authentication paths;
   - DEEP composition relation;
   - every FRI fold;
   - final polynomial evaluation.
5. Marks each query bit complete.

Anyone may advance a session.

#### `finalizeVerification`

```solidity
function finalizeVerification(bytes32 sessionId) external
```

It:

- requires every query bit;
- records `facts[statementHash] = true`;
- closes the session;
- returns the bond to the creator.

#### `expireSession`

After expiry, anyone may delete abandoned session state and receive a bounded cleanup bounty.

### Staged-verifier targets

- Each transaction below 12,000,000 gas.
- Each query bundle below 32 KiB.
- No session writes proportional to proof bytes.
- At most two storage words per query bitmap block.
- Verification cannot transfer pool funds.
- Withdrawal remains atomic and separate.

### Why staging is acceptable for the experiment

The proof remains a single noninteractive proof. Staging merely partitions deterministic verification work and records completion. No verifier challenge is selected interactively on-chain, and no proof witness is revealed.

---

## 12. Solidity implementation rules

- Parse calldata directly; avoid nested `abi.decode`.
- Reject every noncanonical field encoding.
- Use checked bounds before every offset increment.
- Use `MCOPY` or assembly copying only after differential tests.
- No upgradeable proxies.
- No `delegatecall`.
- No verifier address setters.
- No admin pause over withdrawals.
- No arbitrary external calls from the pool.
- Use checks-effects-interactions and a reentrancy guard.
- Generated AIR evaluator source must be reproducible.
- Never manually “simplify” generated constraints without regenerating equivalence tests.

---

## 13. Prover, CLI, indexer, and SDK

## 13.1 Rust CLI

Commands:

```text
pqtc note new
pqtc deposit prepare
pqtc tree sync
pqtc tree prove-path
pqtc prove withdraw
pqtc verify native
pqtc proof expand-staged
pqtc verify submit-staged
pqtc withdraw direct
pqtc withdraw fact
pqtc benchmark
```

The CLI stores no note secret unless explicitly given an output path.

## 13.2 Note format

Use a versioned binary note encoded as base64url:

```text
magic             4 bytes: PQTN
version           u16
chainId           u64
pool              20 bytes
parameterId       64 bytes
nullifierSecret   32 bytes
trapdoor          32 bytes
checksum          32 bytes
```

The checksum is domain-separated Keccak over all prior note bytes. It is corruption detection, not authentication.

Human-facing prefix:

```text
pqtc-note-v1:<base64url>
```

## 13.3 Indexer

The indexer:

- reads `Deposit` logs;
- verifies the commitment, index, and emitted root by replaying insertion;
- handles reorgs by checkpointing block hash and rolling back;
- persists commitments and tree frontier;
- returns a Merkle path for a note commitment;
- refuses to prove against a root before a configurable confirmation count;
- supports at least two RPC endpoints and local cross-checking.

The user can always reconstruct the tree locally from events.

## 13.4 TypeScript SDK

The SDK must implement:

- canonical byte encodings;
- `KeccakPair512`;
- note generation;
- note parsing;
- commitment/nullifier derivation;
- Merkle insertion and path generation;
- payout digest;
- statement serialization;
- contract calldata generation.

Proof generation may remain Rust CLI-only for v0.1.

---

## 14. Repository layout

```text
/
├── Cargo.toml
├── Cargo.lock
├── rust-toolchain.toml
├── flake.nix
├── Dockerfile
├── justfile
├── crates/
│   ├── pqtc-spec/
│   ├── pqtc-hash/
│   ├── pqtc-merkle/
│   ├── pqtc-keccak-air-ref/
│   ├── pqtc-keccak-air-compact/
│   ├── pqtc-stark/
│   ├── pqtc-security/
│   ├── pqtc-proof-codec/
│   ├── pqtc-cli/
│   └── pqtc-indexer/
├── contracts/
│   ├── foundry.toml
│   ├── src/
│   ├── test/
│   └── script/
├── packages/
│   └── sdk/
├── parameters/
│   ├── dev/
│   ├── ci/
│   └── sepolia-v0.1/
├── test-vectors/
│   ├── hash/
│   ├── merkle/
│   ├── air/
│   ├── transcript/
│   └── proof/
├── benches/
├── deployments/
├── docs/
│   ├── protocol.md
│   ├── threat-model.md
│   ├── air-spec.md
│   ├── proof-format.md
│   ├── security-report.md
│   ├── verifier-design.md
│   ├── testnet-runbook.md
│   └── adr/
└── AGENTS.md
```

---

## 15. Toolchain policy

- Pin Rust using `rust-toolchain.toml`.
- Pin Plonky3 to an exact Git commit in every crate.
- Commit `Cargo.lock`.
- Pin Foundry in CI and Docker.
- Pin Node and package-manager versions.
- Build generated Solidity and parameter files in CI and fail if `git diff` is nonempty.
- Do not depend on a moving Git branch.
- Record all tool versions in the parameter manifest.
- Run both native and portable CPU test jobs; SIMD is an optimization, not correctness logic.

---

## 16. Milestone plan

## Phase 0 — Specification and feasibility spikes

### Deliverables

- `docs/protocol.md`.
- `docs/threat-model.md`.
- ADR-0001: KeccakPair512.
- ADR-0002: BabyBear^4 + hiding two-adic FRI.
- ADR-0003: staged verification fallback.
- Pinned Plonky3 commit.
- Small hiding-FRI proof generated and verified using:
  - BabyBear;
  - degree-4 extension;
  - Keccak transcript/MMCS.
- Tiny Solidity field arithmetic benchmark.
- Initial gas model.

### Required spike

Prove one Keccak-f permutation with hiding FRI and report:

- trace dimensions;
- proof bytes;
- prove time;
- native verify time;
- peak memory.

### Exit criteria

- Rust workspace and CI build reproducibly.
- Hiding proof changes across runs while both proofs verify.
- No secret-dependent values appear in public values or logs.
- The team accepts the staged verifier as the guaranteed testnet route.

---

## Phase 1 — Hash, note, and Merkle specification

### Deliverables

- `pqtc-hash`.
- `pqtc-merkle`.
- Solidity `KeccakPair512`.
- TypeScript parity implementation.
- Scope, note, nullifier, payout, zero, and node vectors.
- Incremental depth-20 tree.
- Note codec.

### Tests

- At least 1,000 randomized cross-language vectors.
- Boundary values for every integer encoding.
- Ethereum Keccak versus SHA3 confusion test.
- All fixed application messages verified to fit one Keccak rate block.
- Tree roots match after every insertion across Rust, TS, and Solidity.

### Exit criteria

- One canonical vector file is accepted byte-for-byte by all three languages.
- Mutating any domain tag, byte order, level, or digest half changes the expected result.
- Duplicate commitment handling is specified.

---

## Phase 2 — Plain reference AIR

### Deliverables

- Extended/monolithic reference Keccak AIR.
- Witness generator for 44 permutations.
- Constraint checker without STARK generation.
- Public-value layout.
- AIR mutation tests.

### Exit criteria

- Valid randomized witnesses satisfy every constraint.
- Each of the following independently causes rejection:
  - note secret;
  - trapdoor;
  - sibling;
  - path bit;
  - leaf index bit;
  - root limb;
  - nullifier limb;
  - payout limb;
  - padding byte;
  - operation tag;
  - level number.
- Rust reference, tree implementation, and AIR outputs agree.

---

## Phase 3 — Zero-knowledge STARK

### Deliverables

- Hiding-FRI prover and native verifier.
- 512-bit proof MMCS.
- 512-bit transcript.
- `dev`, `ci`, and draft `sepolia-v0.1` parameter manifests.
- Canonical compact proof codec.
- Native benchmark report.
- Empirical witness-hiding sanity tests.

### Required checks

- Two proofs of the same witness differ.
- Reusing a deterministic masking seed is impossible through production APIs.
- Malformed proof parsing never panics.
- Every transcript item is typed and length-delimited.
- Public-value reordering invalidates the proof.
- Proofs cannot be replayed under another parameter ID.

### Exit criteria

- Complete deposit witness produces a proof.
- Native verifier accepts it.
- At least 100 structured mutations are rejected.
- Security report accounts for every error source and does not call benchmark parameters secure.

---

## Phase 4 — Pool contract

### Deliverables

- Immutable `PQTCClassicPool`.
- Direct on-chain KeccakPair512 insertion.
- Unlimited testnet root recognition.
- Deposit and withdrawal state machine tests.
- Deployment script.

### Exit criteria

- Deposit root matches Rust/TS tree.
- Duplicate commitments revert.
- Unknown roots revert.
- Nullifier is marked before transfer.
- Reentrancy, failed-recipient, and forced-ETH tests pass.
- Pool has no owner, proxy, pause, verifier setter, or rescue function capable of moving pool assets.

---

## Phase 5 — Solidity verifier foundation

### Deliverables

- BabyBear library.
- BabyBear degree-4 extension.
- Transcript512.
- Proof codec/parser.
- 512-bit MMCS verifier.
- FRI fold verifier.
- Rust-generated fixtures for every module.

### Exit criteria

- Solidity and Rust agree on at least 10,000 random field operations.
- Transcript challenge vectors agree exactly.
- Every malformed encoding is rejected.
- MMCS accepts valid and rejects tampered paths.
- FRI accepts valid synthetic fixtures and rejects every mutated round.

---

## Phase 6 — AIR evaluator and complete native-EVM parity

### Deliverables

- Generated Solidity AIR evaluators split by phase.
- Full direct verifier on Anvil.
- Gas and bytecode report.
- Differential proof corpus.

### Exit criteria

- Every native-valid proof in the corpus is EVM-valid.
- Every native-invalid mutation is EVM-invalid.
- No module exceeds EIP-170.
- If direct verification fits below 15M total withdrawal gas, enable `withdrawDirect`.
- Otherwise, direct verification remains a benchmark and staged verification becomes the only testnet path.

---

## Phase 7 — Staged verification registry

### Deliverables

- Session/fact registry.
- Expanded staged-proof codec.
- Header verifier.
- Independent query-bundle verifier.
- Query bitmap.
- Bond, expiry, and cleanup mechanics.
- Fact-based pool withdrawal.

### Exit criteria

- Full proof completes over multiple Anvil transactions.
- No transaction exceeds 12M gas.
- Omitted, duplicated, reordered, or cross-session query bundles fail.
- A proof header from one statement cannot be paired with query bundles from another.
- A completed fact permits exactly one pool withdrawal because of nullifier state.
- An incomplete or expired session never permits withdrawal.

---

## Phase 8 — CLI, indexer, and relayer

### Deliverables

- Complete CLI workflow.
- Reorg-aware indexer.
- TypeScript SDK.
- Minimal relayer script.
- Local Anvil end-to-end script.

### Exit criteria

One command sequence can:

1. Deploy contracts.
2. Generate a note.
3. Deposit.
4. Index the deposit.
5. Generate a path and proof.
6. Verify natively.
7. Submit direct or staged verification.
8. Withdraw through a separate account.
9. Confirm balances and spent nullifier.

---

## Phase 9 — Hardening

### Deliverables

- Fuzzing.
- Property tests.
- Differential tests.
- Gas profiling.
- Static analysis.
- Slither report.
- Invariant tests.
- Reproducible Docker build.
- Draft external-review package.

### Exit criteria

- No unresolved critical/high finding.
- All parser fuzz targets run without panic.
- Contract invariant suite passes:
  - successful withdrawals never exceed successful deposits;
  - one nullifier pays at most once;
  - roots arise only from ordered deposits;
  - verifier facts cannot change payout fields;
  - verifier contracts are immutable.
- `security-report.md` clearly separates measured facts, assumptions, conjectured soundness, and unproven QROM composition.

---

## Phase 10 — Sepolia deployment and demonstration

### Deployment order

1. Parameter/constants contract, if used.
2. Field and verifier libraries/modules.
3. Verification registry.
4. Verifier router.
5. `PQTCClassicPool` with:
   - denomination: recommended `0.001 ether`;
   - tree depth: 20;
   - protocol version: 1;
   - immutable parameter ID.
6. Verify all source code on a public explorer and publish bytecode hashes.
7. Write `deployments/sepolia.json`.

### Demonstration dataset

- At least 16 deposits.
- Deposits sent from distinct funded accounts.
- Withdrawal recipient unrelated to depositor.
- Relayer unrelated to both.
- Wait a fixed confirmation depth before proof generation.

### Required public demonstration

Publish:

- Pool, router, registry, and verifier addresses.
- Parameter ID.
- Exact Git commit.
- Deposit transaction and leaf index.
- Root used.
- Proof SHA/Keccak digest.
- Verification transaction IDs.
- Withdrawal transaction ID.
- Proving time.
- peak prover memory;
- compact and staged proof byte counts;
- gas per stage and total gas;
- recipient/relayer balance deltas;
- rejection transaction/tests for:
  - double spend;
  - changed recipient;
  - changed fee;
  - changed root;
  - changed nullifier;
  - tampered query.

### Final testnet acceptance criteria

The experiment is complete only when:

- A locally generated note is deposited on Sepolia.
- A hiding STARK is generated against the resulting tree.
- The same proof passes the native verifier.
- EVM verification completes through the direct or staged path.
- The bound recipient receives exactly `denomination - fee`.
- The bound relayer receives exactly `fee`.
- The nullifier becomes permanently spent.
- A second withdrawal fails.
- All deployment artifacts and reproducible instructions are committed.

---

## 17. Test matrix

### Hash and encoding

- Every domain tag.
- Every branch byte.
- Maximum integer values.
- Incorrect endian order.
- Missing leading zero.
- Added trailing byte.
- Ethereum Keccak versus SHA3.
- 511/512-bit digest-half swaps.

### AIR

- Non-boolean path bit.
- Leaf index/path mismatch.
- Wrong sibling at each of 20 levels.
- Wrong level tag.
- Wrong Keccak padding.
- Wrong branch prefix.
- Wrong capacity initialization.
- Wrong round constant.
- Wrong output extraction.
- Unconstrained idle row.
- Modified public payout digest.

### Proof

- Truncated header.
- Oversized count.
- Noncanonical field element.
- Wrong extension coefficient order.
- Changed commitment.
- Changed OOD value.
- Changed quotient opening.
- Changed FRI challenge response.
- Changed final polynomial.
- Invalid grinding witness.
- Missing query.
- Duplicate query.
- Invalid hiding salt.
- Merkle path substitution.
- Extra trailing data.

### Contracts

- Wrong denomination.
- Duplicate commitment.
- Full tree.
- Unknown root.
- Already spent nullifier.
- Fee above denomination.
- Zero recipient.
- Failed ETH receiver.
- Reentrant recipient.
- Front-run by a third party.
- Fact for another pool.
- Fact for another parameter ID.
- Cross-chain replay.
- Cross-session query mixing.
- Session spam and expiry.
- Forced ETH balance.

---

## 18. Benchmarks and decision gates

Collect for every profile and AIR:

- Main/preprocessed trace width and height.
- Constraint degree.
- Number of Keccak permutations.
- Proving time.
- Peak resident memory.
- Native verify time.
- Compact proof bytes.
- Expanded staged proof bytes.
- Solidity deployment bytecode.
- Solidity runtime bytecode.
- Header verification gas.
- Per-query gas.
- Finalization gas.
- Pool withdrawal gas.
- Total calldata gas.
- Total staged gas.
- Number of transactions.

### Gate A — reference feasibility

Pass if a complete hiding proof verifies natively.

### Gate B — EVM feasibility

Pass if every stage stays below 12M gas and the full proof can be completed on Anvil.

### Gate C — testnet feasibility

Pass if the staged proof can be submitted on Sepolia without exceeding network transaction limits.

### Gate D — direct feasibility

Pass if the direct full withdrawal is below 15M gas and every module meets code-size limits.

Failure of Gate D does not block v0.1.

### Gate E — compact AIR

Proceed only if projected savings exceed the cost of maintaining the second AIR. Prefer measured proof/calldata reduction of at least 4×.

---

## 19. Agent work packages

Each package should be assigned independently only after its dependencies are merged.

| ID | Package | Depends on | Primary output |
|---|---|---|---|
| A | Protocol/specification | none | normative encodings and ADRs |
| B | Rust/TS/Solidity hash parity | A | hash and Merkle vectors |
| C | Hiding-FRI configuration | A | minimal ZK proof and security report scaffold |
| D | Reference AIR | B, C | valid withdrawal proof natively |
| E | Proof codec/transcript | C, D | canonical compact/staged formats |
| F | Pool contracts | B | deposits and tree on Anvil |
| G | Field/MMCS/FRI Solidity | C, E | verified lower-level proof modules |
| H | AIR evaluator generator | D, E, G | full Solidity verifier |
| I | Staged registry | E, G, H | fact from complete proof |
| J | CLI/indexer/SDK | B, D, E, F | end-to-end local workflow |
| K | Compact AIR | D | reduced proof path |
| L | Hardening/testnet | F, I, J | Sepolia release |

### Agent completion contract

Every work package must include:

- code;
- tests;
- documentation;
- benchmark deltas;
- generated vectors where applicable;
- no unresolved TODO in consensus-critical paths;
- an explicit list of assumptions;
- an ADR for any deviation.

---

## 20. Instructions for engineering agents

1. Treat `docs/protocol.md` and `parameters/*/manifest.bin` as authoritative.
2. Do not change:
   - domains;
   - byte order;
   - public-input order;
   - field;
   - extension;
   - AIR schedule;
   - FRI parameters;
   - proof codec;
   - expected verifier runtime code hashes;
   without an ADR and parameter-ID change.
3. Do not substitute:
   - Groth16;
   - KZG;
   - IPA;
   - pairing-based recursion;
   - an external trusted verifier service.
4. Do not call a non-hiding STARK proof private.
5. Do not use benchmark/default FRI settings for Sepolia.
6. Do not use deterministic RNG in production proof generation.
7. Do not hand-edit generated verifier constraints.
8. Do not optimize before producing cross-language vectors.
9. Do not answer parser failures with unchecked panics or unbounded allocations.
10. Do not describe the experiment as audited or production-safe.

---

## 21. Principal risks

| Risk | Consequence | Mitigation |
|---|---|---|
| Stock Keccak AIR is too wide | Very large proof/calldata | staged verifier; compact AIR track |
| Hiding FRI integration is incomplete | Witness leakage | mandatory ZK fixtures and review; no fallback to non-ZK |
| Parameter security is overstated | Forged proofs | generated term-by-term report and conservative profile |
| Fiat–Shamir/QROM gap | Invalid PQ claim | external cryptographic review; label assumptions |
| Solidity/native transcript mismatch | Valid proofs fail or invalid proofs pass | byte-exact vectors for every absorb/squeeze |
| AIR underconstraint | Pool drain | mutation tests, symbolic checks, external AIR audit |
| Proof parser bug | verifier bypass/DoS | strict codec, fuzzing, fixed bounds |
| Code-size ceiling | undeployable verifier | modular immutable verifier contracts |
| Transaction gas ceiling | undeployable direct proof | mandatory staged verification |
| Staged session mixing | forged completion | bind every stage to 512-bit header and statement hashes |
| Root ages out | valid proof unusable | retain all roots in testnet version |
| EVM hash and AIR hash differ | false membership | Solidity/Rust/AIR golden vectors |
| Plonky3 upstream changes | nondeterminism/regression | exact commit pin and manifest |
| Relayer metadata | reduced practical anonymity | unrelated relayer and timing guidance; outside proof claim |

---

## 22. Future work after v0.1

1. Compact microcoded Keccak AIR.
2. Hiding Circle FRI over M31.
3. WHIR comparison with the same AIR/public statement.
4. Batched deposit-root transitions.
5. Batched withdrawals and PQ proof aggregation.
6. Bounded root history with root pinning.
7. ERC-20 pools.
8. Browser/WASM prover.
9. Post-quantum encrypted note delivery.
10. Nova-style private balances and transfers.
11. Formal AIR verification.
12. Independent cryptographic and Solidity audits.

---

## 23. Definition of done

A repository following this plan is done when it contains a reproducible public Sepolia demonstration of:

```text
random note
    → KeccakPair512 commitment
    → fixed ETH deposit
    → KeccakPair512 Merkle inclusion
    → hiding FRI-based Keccak AIR proof
    → native verification
    → direct or staged EVM verification
    → fact-bound withdrawal
    → permanent nullifier rejection
```

The deliverable must not contain a pairing-based proof wrapper anywhere in the accepted path.

---

## 24. Primary implementation references

- Plonky3 repository and crates:  
  https://github.com/Plonky3/Plonky3

- Plonky3 Keccak AIR:  
  https://github.com/Plonky3/Plonky3/tree/main/keccak-air

- Plonky3 hiding FRI PCS:  
  https://github.com/Plonky3/Plonky3/blob/main/fri/src/hiding_pcs.rs

- Plonky3 hiding Merkle MMCS:  
  https://github.com/Plonky3/Plonky3/blob/main/merkle-tree/src/hiding_mmcs.rs

- Plonky3 security analysis:  
  https://github.com/Plonky3/Plonky3/tree/main/security

- Plonky3 Circle PCS, deferred until hiding support:  
  https://github.com/Plonky3/Plonky3/blob/main/circle/src/pcs.rs

- Original Tornado Cash withdrawal relation:  
  https://github.com/tornadocash/tornado-core/blob/master/circuits/withdraw.circom

- Original Tornado Cash pool state machine:  
  https://github.com/tornadocash/tornado-core/blob/master/contracts/Tornado.sol

- EIP-170 contract code-size limit:  
  https://eips.ethereum.org/EIPS/eip-170

- EIP-7623 calldata floor:  
  https://eips.ethereum.org/EIPS/eip-7623

- EIP-7825 transaction gas cap:  
  https://eips.ethereum.org/EIPS/eip-7825
````

</details>


# Appendix B — Current documentation and architecture records, verbatim

## `README.md`

- Bytes: 9,879
- SHA-256: `228cc72300077a972eaab8344dd335567064dde5930dd5cfa76fd834f0725911`

<details><summary>Complete file</summary>

````markdown
# PQ Tornado Classic

Experimental fixed-denomination privacy pool with a pairing-free, hiding Plonky3 STARK. Protocol v0.3 uses P2BB512-v1 application hashes and verifies one 32-query withdrawal proof in exactly two state-changing pool calls. Part A verifies query positions 0 through 15 and stores a compact consumer-bound checkpoint; part B verifies positions 16 through 31 inside the withdrawal and pays atomically.

This repository is unaudited, pre-deployment research software. No Sepolia or mainnet deployment is authorized or claimed, and no on-chain v0.3 transaction receipt exists. The current evidence is a local Foundry measurement with full pool-facing ABI calldata accounting, not a network receipt or audit.

The `sepolia-v0.3` security generator reports 107 conjectured bits under the random-words model, 37 bits under the proven unique-decoding bound, and 56 bits under the proven list-decoding bound (also the best proven bound). The conjectured and proven figures are not interchangeable: v0.3 is not a 100-bit proven design. P2BB512's capacity and one canonical field-secret each give approximately 123.6 bits against their corresponding generic quantum attacks, under idealized models. There is no structural quantum analysis of this Poseidon2 instance, and the custom Fiat–Shamir composition has no complete QROM proof. See `docs/security-report.md` and `docs/threat-model.md`.

## v0.3 protocol at a glance

- Application hashing: BabyBear Poseidon2 width 16, rate 4, capacity 12, $x^7$, 8 full and 13 partial rounds.
- Application digests: 16 canonical big-endian BabyBear `u32` elements (`Digest512`).
- Note secrets: each 32-byte nullifier secret and trapdoor is exactly eight canonical big-endian BabyBear `u32` limbs; noncanonical limbs are rejected, not reduced.
- Proof-only hashing: domain-separated KeccakPair512 for MMCS, transcript, and parameter manifests.
- Withdrawal AIR: 256 rows by 190 columns; nullifier first, note second; 240 application-hash permutations, 4 payout rows, and 12 padding rows.
- AIR accounting: 1,186 constraints, maximum degree 7, and 210 batched functions (`190 + 16 + 4`).
- Hiding/FRI: proof degree bits 9, log blowup 4, global height 13, nine binary rounds, four random codewords, eight salt elements per MMCS leaf, and commit/query grinding configured at 16 classical bits each.
- Queries: 32 transcript-derived positions, split 16/16 between two direct-calldata calls.
- Canonical global proof data: 9,208 bytes. The regenerated v3 fixture is 101,990 bytes for part A and 108,294 bytes for part B, 210,284 bytes total.
- Immutability: pool, registry, verifier, parameter ID, scope, denomination, tree depth, and protocol version have no upgrade or administrator path.

v0.3 is a clean incompatible cutover. Protocol, AIR, proof codec, verifier interface, and manifest versions are all 3. The note prefix is `pqtc-note-v3:`, proof magics are `PQTCPA03` and `PQTCPB03`, and the manifest magic is `PQTCPRM3`. Earlier notes, commitments, roots, proofs, facts, staged sessions, parameters, selectors, and profile names are rejected. There is no compatibility decoder, version-2 route, or three-transaction fallback.

## Measured gas status

The exact local Foundry full pool-facing measurement is:

| Call | Execution gas | Execution + standard intrinsic | Margin below EIP-7825 cap |
|---|---:|---:|---:|
| A: `beginWithdrawal` | 14,891,070 | 16,539,302 | 237,914 |
| B: `withdraw` and payment | 12,356,373 | 14,105,909 | 2,671,307 |

The per-transaction EIP-7825 cap is 16,777,216 gas. Both regenerated-proof calls are below it. The registry-only execution profile was 14,056,853 gas for A and 11,470,158 gas for B. A one-call deposit measured 13,991,021 execution gas; even a conservative all-nonzero intrinsic charge for its small 68-byte ABI calldata keeps it below the cap.

Under EIP-7623, the receipt charge for these ordinary calls is

```text
max(21,000 + standardCalldataGas + executionGas,
    21,000 + 10 * calldataTokens)
calldataTokens = zeroBytes + 4 * nonzeroBytes
standardCalldataGas = 4 * calldataTokens
```

The first branch governs both measured proof calls. The calldata floor is an alternative minimum for the whole transaction, not an amount added to execution. See `docs/gas-model.md` for exact calldata accounting and evidence boundaries.

## Pinned toolchain

- Rust 1.97.0
- Plonky3 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`
- Solidity 0.8.30
- Foundry 1.7.1
- Node 24 and pnpm 11

The reproducible container installs these versions:

```sh
docker build -t pqtc-release:test .
```

## Repository layout

- `crates/pqtc-spec`, `pqtc-hash`, `pqtc-merkle`: canonical v0.3 encodings, P2BB512-v1, proof-only KeccakPair512, notes, and depth-20 trees.
- `crates/pqtc-poseidon-air`: the 256-row, width-190 withdrawal AIR and witness relation.
- `crates/pqtc-stark`: hiding PCS, native prover/verifier, transcript, and canonical two-part codec.
- `crates/pqtc-security`: manifest-v3 generation and conjectured/proven security accounting.
- `crates/pqtc-indexer`, `pqtc-cli`: reorg-aware indexing and local user/prover workflow.
- `contracts/src`: immutable pool, two-part verification registry, verifier modules, and canonical hash/arithmetic libraries.
- `packages/sdk`: TypeScript note, hash, tree, calldata, receipt-binding, and relayer support.
- `script/LocalTwoPartE2E.s.sol` and `script/SubmitTwoPartProof.s.sol`: local exercise and existing-pool A/B submission. `DeploySepolia.s.sol` is not evidence of a deployment and is not an authorization to deploy.
- `parameters/sepolia-v0.3`: generated profile package.
- `test-vectors/verifier/v3`: canonical v3 proof fixtures.

## Build and test

```sh
cargo test --workspace --all-targets
cargo clippy --workspace --all-targets --all-features
pnpm install --frozen-lockfile
pnpm test
forge test
forge build --sizes
```

These commands establish local correctness, measurements, and code-size evidence only. They do not create Ethereum receipts, establish an audit, or authorize deployment.

## Local v0.3 workflow

Generate local parameter packages and inspect the v0.3 analysis and identifier:

```sh
cargo run -p pqtc-cli -- parameters-generate --out-dir parameters
cat parameters/sepolia-v0.3/security-analysis.json
cat parameters/sepolia-v0.3/parameter-id.txt
```

Generation is a review step, not a deployment instruction. A release manifest must contain reviewed expected runtime code hashes.

Generate and retain a version-3 note offline:

```sh
cargo run -p pqtc-cli -- note-new \
  --chain-id <local-chain-id> \
  --pool <local-pool-address> \
  --parameter-id "$(cat parameters/sepolia-v0.3/parameter-id.txt)" \
  --out note.txt
```

Prepare a commitment, synchronize independently supplied deposit histories, and build a confirmed path:

```sh
cargo run -p pqtc-cli -- deposit-prepare \
  --note "$(cat note.txt)" --scope <pool-scope> --out deposit.json
cargo run -p pqtc-cli -- tree-sync --scope <pool-scope> --confirmations 12 \
  --primary primary-blocks.json --secondary secondary-blocks.json --out tree.json
cargo run -p pqtc-cli -- tree-prove-path --snapshot tree.json \
  --commitment <commitment> --out path.json
```

Create two canonical proof parts with fresh hiding randomness and verify their joint native round trip:

```sh
cargo run -p pqtc-cli -- prove-withdraw \
  --statement statement.json --witness witness.json \
  --profile sepolia-v0.3 --out-dir withdrawal-proof
cargo run -p pqtc-cli -- verify-native \
  --statement statement.json \
  --part-a withdrawal-proof/part-a.pqtc \
  --part-b withdrawal-proof/part-b.pqtc \
  --profile sepolia-v0.3
```

`metadata.json` records the parameter ID, statement key, core proof ID, and both byte lengths. Native verification is necessary but is not an EVM receipt.

## Two-transaction submission lifecycle

A relayer constructs one stateful submission and must observe a successful, correctly bound part-A receipt before broadcasting part B:

```text
A: pool.beginWithdrawal(withdrawal, partA)
B: pool.withdraw(withdrawal, verificationId, partB)
```

The pool validates the withdrawal and reconstructs all 64 public values before each registry call. A calls registry `beginVerification`, whose `msg.sender` is the pool; the registry verifies positions 0 through 15 and stores the compact consumer-bound checkpoint. The A receipt must contain exactly one matching `VerificationStarted` event for the configured registry, pool consumer, statement key, and verification ID.

B repeats statement validation, completes positions 16 through 31 as the same bound consumer, consumes the checkpoint, marks the nullifier, and pays. Any verification or payment revert restores checkpoint, nullifier, and transfer state. A relayer must validate chain, registry, pool, parameter ID, statement, request deadline, ordering, receipt status, and event before returning or broadcasting B calldata.

No proof-byte deployment, expanded-query submission, fact publication, auxiliary verifier call, or three-call interim fallback is a live protocol path.

## Review boundary

Before any deployment proposal, reviewers still need one pinned candidate with regenerated manifest/security outputs, cross-language vectors, independent cryptographic and Solidity review, reviewed runtime hashes and code sizes, exact calldata evidence, and successful network receipts for both pool calls. The Foundry measurements above show that the current full ABI model fits EIP-7825; they do not replace Ethereum receipts. No Sepolia deployment or v0.3 receipt occurred.

The normative wire protocol is in `docs/protocol.md`, AIR shape in `docs/air-spec.md`, measured gas evidence in `docs/gas-model.md`, security claims in `docs/security-report.md`, and external audit boundary in `docs/external-review-scope.md`. ADR-0004 records the v0.3 design; earlier architecture ADRs are historical or superseded.
````

</details>

## `docs/air-spec.md`

- Bytes: 7,455
- SHA-256: `67a3554ef23d487a125c57991aaca9d95b0a7315e9ddb5ecdfd79c47ccb30f83`

<details><summary>Complete file</summary>

````markdown
# Reference Withdrawal AIR v3

## Shape

- Base field: BabyBear, modulus 2,013,265,921.
- Poseidon2: pinned Plonky3 width-16 permutation, $x^7$, 8 full and 13 partial rounds.
- Logical trace: 256 rows ($2^8$), width 190.
- Poseidon2 sub-AIR: 157 columns.
- Controller: 33 columns.
- Public values: 64 canonical BabyBear elements ordered `scope`, `root`, `nullifierHash`, `payoutDigest`.
- Generated constraints: 1,186.
- Maximum declared constraint degree: 7.
- Application-hash permutations: 240.

A Poseidon2 permutation is evaluated horizontally by the maintained 157-column Plonky3 sub-AIR, so one permutation occupies one row. This is not a multi-row round trace.

## Controller layout and WORK overlap

The controller columns immediately follow the Poseidon2 columns:

| Columns | Meaning |
|---|---|
| 5 | one-hot `NULLIFIER`, `NOTE`, `MERKLE`, `PAYOUT`, `PADDING` selectors |
| 4 | little-endian operation step bits |
| 5 | little-endian Merkle level bits |
| 1 | `isLastLevel` |
| 1 | `pathBit` |
| 1 | remaining leaf index |
| 16 | `WORK` |

Thus $157+5+4+5+1+1+1+16=190$.

`WORK` is deliberately lifetime-overlapped rather than split into secret, current-digest, and digit arrays:

- row 0 starts with the eight nullifier-secret field limbs in `WORK[0..8)` and zeros in `WORK[8..16)`;
- all nullifier rows carry those values unchanged into the note;
- note rows use those same eight limbs, while its final absorb and squeeze transitions replace the 16 `WORK` cells chunk-by-chunk with the commitment digest;
- each Merkle operation uses the 16 cells as the current digest, with the sibling supplied by the witness-side input lanes, then replaces `WORK` with the parent digest;
- payout and padding rows require all `WORK` cells to be zero.

The trapdoor is eight canonical field elements used only as the final two note absorb blocks. Because both secrets are canonical BabyBear limbs already, v3 needs no range-check digit columns. This overlap is security-critical: every transition that preserves or replaces `WORK` must be reviewed with the selector and step constraints.

## Exact row schedule

| Rows | Operation | Sponge work |
|---:|---|---|
| `0..8` | `NULLIFIER` | 6 rate-4 absorbs and 3 additional squeezes |
| `9..19` | `NOTE` | 8 absorbs and 3 additional squeezes |
| `20..239` | `APP_MERKLE_NODE`, levels `0..19` | 11 rows per level: 8 absorbs and 3 squeezes |
| `240..243` | payout public binding | four public rate blocks |
| `244..255` | canonical padding | zero Poseidon2 inputs |

Nullifier-first ordering lets the AIR carry the same eight secret limbs directly into the note and then reuse the complete `WORK` area for the commitment/current digest. The nullifier, note, and $20\times11$ Merkle rows total 240 application-hash permutations. Four payout rows and 12 padding rows complete the 256-row trace. The first row is nullifier step 0; the final row is padding.

For each application hash, step 0 fixes capacity cells to:

```text
state[4..9] = [1, domain, payloadByteLength, payloadElementCount, aux, 0]
state[10..15] = 0
```

Subsequent absorb rows carry all capacity lanes and add the next four fields to the rate. The final absorb yields digest elements 0 through 3; three more permutations yield elements 4 through 15. These constraints implement P2BB512-v1 exactly, including version, domain, byte length, field count, and Merkle-level auxiliary binding.

## Canonical secret and digest constraints

Scope, root, nullifier, payout, current-node, sibling, and commitment digests are 16 canonical fields. Each 32-byte nullifier secret or trapdoor is exactly eight big-endian canonical `u32` BabyBear fields. There is no reduction and no `u16` or base-8 decomposition in AIR v3.

The nullifier payload contains 16 scope fields followed by eight nullifier-secret fields, giving 24 fields and six absorbs. The note payload contains 16 scope fields, the same eight nullifier-secret fields, and eight trapdoor fields, giving 32 fields and eight absorbs. The first-row and transition constraints bind these exact shapes. A noncanonical secret cannot enter the native witness type or canonical external encodings.

The note digest becomes the initial Merkle `current`. At each level, boolean `pathBit` selects `current || sibling` or `sibling || current`. The auxiliary value equals the constrained five-bit level. Four output chunks assemble the 16-field digest without truncation.

## Leaf index and path

The witness supplies one `u32` leaf index, but the relation accepts only values below $2^{20}$. At Merkle level $i`, `pathBit` is bit $i` in little-endian order and the controller enforces:

```text
remainingIndex = pathBit + 2 * nextRemainingIndex
```

After level 19, `remainingIndex = pathBit`; the next row enters payout binding. This proves all path bits correspond to the private index and no higher bit is set.

## Public-value binding

Public values `0..15` are scope fields used by both nullifier and note hashing. Nullifier squeeze outputs bind `32..47`. The final Merkle squeeze binds root values `16..31`.

Rows `240..243` place payout public values `48..63` into four consecutive rate-4 inputs, zero the other 12 input lanes, and evaluate the same Poseidon2 sub-AIR. The payout digest is public; the pool separately derives it from recipient, relayer, and fee. All 64 public values are also transcript-bound.

## Constraint and batching accounting

The generated AIR exposes 1,186 constraints with maximum degree 7. These values must come from symbolic generation of the exact v3 source, not a hand-maintained estimate. Security analysis uses 210 batched functions:

```text
190 trace columns + 16 quotient chunks + 4 random columns = 210
```

Any column, constraint, degree, quotient, or random-column change requires regenerated security output, manifest, parameter ID, proof vectors, Solidity constants, and review.

## Hiding PCS and FRI profile

The AIR remains 256 logical rows with base degree bits 8. `HidingFriPcs` adds one degree bit to its committed masked representation: the proof reports degree bits 9 and commits over 512 trace-domain positions. This does not make the logical AIR a 512-row AIR.

For `sepolia-v0.3`, log blowup 4 gives global codeword log height $9+4=13`. Nine binary folds reduce it to final codeword height 4. The profile requires 32 queries, commit and query grinding configured at 16 classical bits each, four random masking codewords, and eight random salt fields per MMCS leaf.

Fresh masking and salt randomness must come from an operating-system-seeded CSPRNG. Deterministic randomness is test-only and must not be exposed by an operational proving API.

## Relation and negative checks

Before trace generation, the relation rejects a noncanonical statement or sibling digest, noncanonical secret limb, leaf index outside 20 bits, nonboolean or mismatched path bit, wrong nullifier, or wrong root. The AIR boundary must reject independent mutations of:

- nullifier-secret or trapdoor limbs and their reuse across operations;
- any sibling, current digest, path bit, leaf-index transition, or Merkle level;
- sponge version, domain, byte length, element count, auxiliary value, rate input, or carried state;
- any public scope, root, nullifier, or payout field;
- operation selectors, steps, `WORK` preservation/replacement, row transitions, or padding.

The maintained Plonky3 Poseidon2 sub-AIR is embedded without deleting or weakening its round constraints.
````

</details>

## `docs/external-review-scope.md`

- Bytes: 8,684
- SHA-256: `44ef178cddcf9c734a8bc39cd27c28704878983d4fb79a2967b603cd4e97cfe0`

<details><summary>Complete file</summary>

```markdown
# PQ Tornado Classic v0.3 External Review Scope

## Review boundary

This review covers the v0.3 pre-deployment research implementation. It does not authorize Sepolia or mainnet deployment or custody of material value. Local Foundry tests measure a one-call deposit and an exactly two-call withdrawal; no v0.3 Ethereum receipt or deployment exists.

The production profile reports 107 conjectured bits under the random-words model, 37 bits under the proven unique-decoding bound, and 56 bits under the proven list-decoding bound. Reviewers must keep those values distinct. They must also treat the approximate 123.6-bit generic quantum bounds for each canonical secret and the P2BB512 capacity, the absence of a structural Poseidon2 analysis, and the absence of a complete QROM composition proof as explicit caveats.

The review commit must pin Rust 1.97.0, Solidity 0.8.30, Foundry 1.7.1, Plonky3 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`, optimizer settings, Prague EVM semantics, and the exact regenerated v0.3 parameter and proof artifacts. A deployment candidate additionally needs reviewed runtime-code hashes, proof-part hashes, independent calldata measurements, and successful network receipts.

## In-scope components

- `crates/pqtc-spec`, `pqtc-hash`, and `pqtc-merkle`: canonical field secrets, P2BB512-v1, proof-only KeccakPair512, note codec, and depth-20 application tree.
- `crates/pqtc-poseidon-air`: 256-row, width-190 withdrawal relation, controller, trace generation, and Poseidon2 sub-AIR integration.
- `crates/pqtc-stark`: hiding PCS configuration, transcript, proof codec, canonical A/B partition, checkpoint construction, prover, and native verifier.
- `crates/pqtc-security`: manifest-v3 encoding, parameter ID, runtime-code commitments, and conjectured/proven security accounting.
- `contracts/src/libraries`: canonical decoding, BabyBear and extension arithmetic, P2BB512-v1, proof-only transcript/MMCS hashing, and statement construction.
- `contracts/src/verifier`: AIR/DEEP checks, query-batch multiproofs, nine-round binary FRI, and fixed-shape parsing.
- `contracts/src/PQTCVerificationRegistry.sol`: part-A verification, consumer-bound checkpoint, part-B continuation, replay rules, and rollback behavior.
- `contracts/src/PQTCClassicPool.sol`: deposits, root history, immutable scope, nullifiers, statement reconstruction, registry completion, payment atomicity, and reentrancy.
- `packages/sdk`, `crates/pqtc-indexer`, `pqtc-cli`, and relayer paths: canonical notes and hashes, reorg-aware witness construction, proof generation, native verification, two-call ordering, receipt/event binding, and calldata construction.
- Cross-language vectors and focused Solidity, Rust, and TypeScript tests for all of the above.

The removed v0.1 staged fact system and every v0.2 note, parameter, AIR, proof, selector, and profile are invalid. Review must flag any reachable compatibility decoder, alias, fact route, proof-data deployment, or third-call fallback.

## Required cryptographic invariants

1. P2BB512-v1 uses width 16, rate 4, capacity 12, $x^7$, 8 full rounds, 13 partial rounds, and the pinned constants in every language.
2. Each nullifier secret and trapdoor is eight independently and uniformly sampled canonical big-endian BabyBear `u32` limbs. Values at least 2,013,265,921 are rejected, never reduced.
3. Commitment payloads are `scope[16] || nullifierSecret[8] || trapdoor[8]`; nullifier payloads are `scope[16] || nullifierSecret[8]`. Domain, original byte length, element count, auxiliary value, digest encoding, and Merkle level are bound.
4. Scope commits to chain, pool, denomination, tree depth, protocol version 3, and the exact parameter ID.
5. A withdrawal proof binds the same canonical scope, root, nullifier, and payout digest reconstructed by the pool.
6. The AIR is exactly 256 rows by 190 columns: nullifier rows 0 through 8, note rows 9 through 19, Merkle rows 20 through 239, payout rows 240 through 243, and padding rows 244 through 255.
7. The derived AIR has 1,186 constraints, maximum degree 7, and 210 batched functions. Base trace degree bits 8 and hiding proof degree bits 9 remain distinct.
8. The v0.3 profile uses log blowup 4, global FRI height 13, nine binary folds, 32 queries, four fresh masking codewords, eight fresh salt elements per leaf, and 16-bit commit/query grinding.
9. The typed KeccakPair512 transcript binds the parameter ID, 64 public values, every global proof object, hiding opening, grinding witness, final polynomial, and all 32 query indices.
10. Query indices are transcript-derived. Duplicate indices and the sorted unique frontier have one canonical encoding and verification result.
11. Rust and Solidity agree on extension arithmetic, AIR/DEEP evaluation, MMCS leaf and node bytes, pruned frontier order, FRI folding, and final checks.
12. Security reporting states 107 conjectured, 37 proven UDR, and 56 proven LDR/best bits. It must not describe the profile as 100-bit proven security.

## Required transaction invariants

1. One canonical proof uses exactly two state-changing pool transactions: `beginWithdrawal` verifies query positions 0 through 15, and `withdraw` verifies positions 16 through 31 and pays.
2. `statementKey`, `globalDigest`, checkpoint digest, core proof ID, and consumer-specific verification ID use the exact domains and encodings in `docs/protocol.md`.
3. Part B cannot be accepted against a different part A, statement, parameter, profile, global object, challenge state, query schedule, or consumer.
4. The pool validates the withdrawal and derives public values before both calls. Part A stores a checkpoint only after its complete parsing, transcript, AIR/DEEP, MMCS, and query checks succeed.
5. The checkpoint stores fixed-size bindings, never proof calldata or expanded query objects. Registry consumer binding uses `msg.sender`, so the immutable pool is the consumer.
6. Completion deletes the checkpoint; the pool then marks the nullifier and pays in transaction B. Any revert restores checkpoint, nullifier, and balances together.
7. Direct B replay fails without a live checkpoint. Value replay fails the spent-nullifier check. An exact duplicate live A is idempotent and only donates work.
8. Reordered, truncated, oversized, noncanonical, mixed, or trailing-byte proof parts revert without partial state.
9. No proof shard, proof-data deployment, published fact, trusted verifier service, third verification call, administrator, or upgrade path is required.
10. Abandoned valid checkpoints remain a storage-denial-of-service concern. Cleanup or a quantified hard economic bound is a deployment prerequisite.

## Pool and parser invariants

Deposits accept exactly one denomination and one new, nonzero, canonical digest. Tree insertion must match the Rust and TypeScript depth-20 tree. Only known roots and unspent canonical nullifiers enter verification. Each successful withdrawal transfers exactly `denomination - fee` to the recipient and `fee` to the relayer. Failed or reentrant payment cannot spend a nullifier or consume a checkpoint. Forced ETH cannot authorize or enlarge a withdrawal.

Review every count, cursor increment, multiplication, allocation, loop bound, and memory access. Proof-controlled values must not select unbounded work. Pruned multiproofs require review for duplicate leaves, frontier underflow or overflow, sibling order, root ambiguity, and malleable counts.

## Reproduction and gas boundary

Reviewers must regenerate the manifests, security outputs, cross-language vectors, and a fresh 32-query hiding proof from the reviewed source. They must run the pinned workspace suites, mutation tests, static analysis, and `forge build --sizes`.

The current local full pool-facing ABI model measured:

| Call | Execution gas | Intrinsic-inclusive gas | EIP-7825 margin |
|---|---:|---:|---:|
| A: `beginWithdrawal` | 14,891,070 | 16,539,302 | 237,914 |
| B: `withdraw` and payment | 12,356,373 | 14,105,909 | 2,671,307 |

One deposit measured 13,991,021 execution gas and at most 14,013,109 with conservative intrinsic accounting. The regenerated proof fixture is 101,990 bytes for A and 108,294 bytes for B. Under EIP-7623, the transaction charge is the maximum of the standard execution path and calldata floor; the floor is not added to execution. The standard path governs both measured withdrawal calls.

Every runtime contract must remain below EIP-170's 24,576-byte limit. These local results are acceptance-test evidence, not receipts. Actual deployment readiness remains unresolved until independent cryptographic and Solidity review, reviewed runtime hashes, and successful network receipts exist.
```

</details>

## `docs/gas-model.md`

- Bytes: 4,382
- SHA-256: `d0618f05fd88455b32beb1ce222b63617a1993bb8591d051c2d511bd2b97902f`

<details><summary>Complete file</summary>

````markdown
# EVM Gas and Calldata Model for v0.3

## Evidence boundary

v0.3 uses exactly two state-changing pool calls for 32 transcript-derived queries: `beginWithdrawal` verifies positions 0 through 15; `withdraw` verifies positions 16 through 31, consumes the checkpoint, marks the nullifier, and pays atomically. Both proof parts are direct calldata. There is no proof-byte deployment, fact publication, auxiliary verification call, version-2 route, or three-call fallback.

The evidence below is local Foundry full pool-facing ABI accounting. It is not an Ethereum receipt, audit, production approval, or deployment record. No Sepolia deployment or v0.3 on-chain receipt exists.

## Proof and call shape

The production profile is `sepolia-v0.3`: AIR 256 by 190, proof degree bits 9, log blowup 4, nine binary FRI rounds, four random codewords, eight salts per MMCS leaf, and 16-bit commit/query grinding. Canonical global data is 9,208 bytes. The measured fixture sizes are:

| Artifact | Bytes |
|---|---:|
| part A | 101,990 |
| part B | 108,294 |
| total | 210,284 |

Frontier length depends on derived query collisions, so these are exact fixture measurements rather than universal fixed lengths.

## Full pool-facing Foundry measurement

The wrapper includes an extra external call and therefore conservatively accounts for direct pool execution.

| Call | Execution gas | Standard intrinsic | Execution + standard intrinsic | Margin below 16,777,216 |
|---|---:|---:|---:|---:|
| A: `beginWithdrawal` | 14,891,070 | 1,648,232 | **16,539,302** | **237,914** |
| B: `withdraw` including payment | 12,356,373 | 1,749,536 | **14,105,909** | **2,671,307** |

Registry-only execution measured 14,056,853 gas for A and 11,470,158 gas for B. Those diagnostics exclude the full pool boundary and do not replace the table above.

The complete measured ABI calldata accounting is:

| Call | Bytes | Zero | Nonzero | Calldata gas | Base + calldata intrinsic |
|---|---:|---:|---:|---:|---:|
| A | 102,308 | 808 | 101,500 | 1,627,232 | 1,648,232 |
| B | 108,644 | 814 | 107,830 | 1,728,536 | 1,749,536 |

Standard calldata pricing is 4 gas per zero byte and 16 per nonzero byte. Another proof may have another frontier length or byte distribution and must be measured independently.

## EIP-7623 formula

For these ordinary calls, with no creation or access list:

```text
T = zeroBytes + 4 * nonzeroBytes
standardPath = 21,000 + 4*T + executionGas
floorPath = 21,000 + 10*T
modeledReceiptGas = max(standardPath, floorPath)
```

The floor is an alternative minimum for the whole transaction. It is **not** added to execution. A has `T=406,808`, floor 4,089,080, and standard path 16,539,302. B has `T=432,134`, floor 4,342,340, and standard path 14,105,909. Therefore execution plus standard intrinsic—not execution plus the floor—governs both measured calls. Adding execution to the floor would double-count relative to EIP-7623.

EIP-7825 applies its 16,777,216 cap per transaction. The two modeled calls total 30,645,211 gas, but a low B cannot compensate for an over-cap A.

## Deposit

One complete `deposit` measured **13,991,021 execution gas**. Its static calldata is only a 4-byte selector and two 32-byte digest halves. Conservatively pricing all 68 bytes as nonzero gives intrinsic gas at most 22,088 and total modeled gas at most 14,013,109, at least 2,764,107 below EIP-7825. The EIP-7623 floor is smaller, so the standard path governs. This remains a local measurement, not a receipt.

## Operations and remaining evidence

A relayer must wait for a successful A receipt before broadcasting B, then validate chain, registry, pool consumer, parameter ID, statement key, verification ID, request deadline, status, and the matching `VerificationStarted` event. B uses that exact verification ID. A B revert restores checkpoint, nullifier, and payment state; transaction replacement does not add a protocol stage.

Before any deployment proposal, reviewers still need pinned compiler/optimizer/EVM settings, commit and parameter ID, runtime hashes and EIP-170 sizes, independently reproduced calldata measurements, parser-bound review, independent cryptographic and Solidity review, and actual successful network receipts demonstrating both calls and final state. Foundry can reject a candidate and supplies the current measured evidence; it cannot substitute for those receipts.
````

</details>

## `docs/protocol.md`

- Bytes: 17,010
- SHA-256: `7984b5c7a67641c513cea42b70a2ff43d8297afe3af2bf8b76e07e8d656d0538`

<details><summary>Complete file</summary>

````markdown
# PQ Tornado Classic Protocol v0.3

Status: normative design for the v0.3 research implementation. This document is not an audit, deployment record, or authorization to deploy.

## Fixed parameters

- Protocol version: `3` (`u32`, big-endian).
- Application hash: `P2BB512-v1`.
- Application Merkle tree: append-only, depth 20.
- Asset: native ETH; denomination immutable per pool.
- Base field: BabyBear, modulus $p=2,013,265,921$.
- Poseidon2 permutation: pinned Plonky3 `default_babybear_poseidon2_16`, width 16, rate 4, capacity 12, $x^7$, 8 full rounds, 13 partial rounds.
- Challenge field: degree-4 binomial extension of BabyBear.
- Withdrawal AIR: version 3, 256 rows, width 190, 64 public values, 1,186 constraints, maximum degree 7.
- `sepolia-v0.3` proof profile: proof degree bits 9, log blowup 4, global height 13, nine binary FRI rounds, 32 queries split 16/16, 16-bit commit grinding, 16-bit query grinding, four random codewords, and eight salt elements per MMCS leaf.
- Proof codec, verifier interface, and manifest versions: `3`.
- Plonky3 commit: `3152b14a89067c83775a8076cc262ffc48a1fd7c`.

The pool, verification registry, verifier modules, parameter identifier, denomination, tree depth, and protocol version are immutable. There is no owner, proxy, pause key, verifier setter, trusted relayer, trusted proof service, pairing, elliptic-curve trusted setup, or proof-fact service.

## Canonical values and bytes

All wire integers are unsigned, fixed-width, and big-endian. An address is exactly 20 bytes. A BabyBear element is exactly four bytes encoding an integer strictly less than $p$; reduction modulo $p$, short encodings, and alternative encodings are rejected. A degree-4 extension is four canonical base-field coefficients in coefficient order.

A `Digest512` is 64 bytes and exactly 16 canonical BabyBear elements:

```text
digest = element[0]_u32_be || ... || element[15]_u32_be
left   = elements 0..7
right  = elements 8..15
```

Each 32-byte nullifier secret and trapdoor is exactly eight canonical `u32_be` BabyBear limbs:

```text
secret = limb[0]_u32_be || ... || limb[7]_u32_be, each limb < p
```

Parsers reject an entire secret if any limb is not canonical. Random generation uses independent rejection sampling for every limb; it never reduces a 256-bit string modulo the field. A canonical secret has $8\log_2(p)\approx247.3$ bits of entropy when sampled uniformly. This representation removes byte-decomposition columns from the AIR and makes the native, Solidity, and AIR values identical.

Ordinary byte strings are converted to field elements as consecutive big-endian `u16` values. For an odd length, the final byte is the high byte of a final `u16` whose low byte is zero. Digests and canonical secrets are not passed through this byte conversion: they decode directly to canonical `u32` field elements.

The pool scope byte string is exactly:

```text
chainId_u64_be || pool_20 || denomination_u256_be || treeDepth_u8 ||
protocolVersion_u32_be || parameterId_64
```

It is 129 bytes and encodes to 65 `u16` field elements; the final element contains the last parameter-ID byte followed by `0x00`.

## P2BB512-v1 sponge

For domain byte `tag`, original byte length `byteLen`, auxiliary value `aux`, and canonical field payload `m[0..n)`, initialize 16 field elements to zero and set:

```text
state[4] = 1
state[5] = tag
state[6] = byteLen
state[7] = n
state[8] = aux
state[9..15] = 0
```

`byteLen`, `n`, and `aux` must be canonical BabyBear values. Split the payload into rate-4 blocks. Add each block to `state[0..3]` and apply the pinned permutation; unused rate positions of a final partial block remain unchanged. An empty payload applies one permutation. The explicit byte length and element count make the odd-byte rule and trailing zeros unambiguous.

The first output block is `state[0..3]`. Apply the permutation three more times and append `state[0..3]` after each permutation, yielding 16 canonical output elements. The P2BB512 sponge version remains 1; this primitive version is distinct from protocol version 3.

## Domains

| Tag | Name | Primitive |
|---:|---|---|
| `0x10` | `SCOPE` | P2BB512-v1 |
| `0x11` | `NOTE` | P2BB512-v1 |
| `0x12` | `NULLIFIER` | P2BB512-v1 |
| `0x13` | `EMPTY_LEAF` | P2BB512-v1 |
| `0x14` | `PAYOUT` | P2BB512-v1 |
| `0x15` | `STATEMENT` | P2BB512-v1 |
| `0x20` | `APP_MERKLE_NODE` | P2BB512-v1 |
| `0x40` | `PROOF_LEAF` | KeccakPair512, proof-only |
| `0x41` | `PROOF_NODE` | KeccakPair512, proof-only |
| `0x42` | `TRANSCRIPT_INIT` | KeccakPair512, proof-only |
| `0x43` | `TRANSCRIPT_ABSORB` | KeccakPair512, proof-only |
| `0x44` | `TRANSCRIPT_SQUEEZE` | KeccakPair512, proof-only |
| `0x45` | `PARAMETER_MANIFEST` | KeccakPair512, proof-only |

`KeccakPair512` is not standard Keccak-512:

```text
K512(tag, payload) =
    keccak256(0x00 || tag || payload) ||
    keccak256(0x01 || tag || payload)
```

Ethereum Keccak is used, not NIST SHA3. KeccakPair512 is confined to proof commitments, Fiat–Shamir, and the parameter identifier; it is not an application commitment, nullifier, Merkle, payout, or statement hash.

## Application hashes

The following calls fix both semantic messages and sponge metadata:

```text
scope = P2BB512(SCOPE, 129, 0,
    u16be(scopeBytes))                                      // 65 elements
commitment = P2BB512(NOTE, 128, 0,
    fields(scope) || fields8(nullifierSecret) ||
    fields8(trapdoor))                                      // 32 elements
nullifierHash = P2BB512(NULLIFIER, 96, 0,
    fields(scope) || fields8(nullifierSecret))              // 24 elements
zero[0] = P2BB512(EMPTY_LEAF, 64, 0, fields(scope))          // 16 elements
zero[level+1] = P2BB512(APP_MERKLE_NODE, 128, level,
    fields(zero[level]) || fields(zero[level]))              // 32 elements
node[level] = P2BB512(APP_MERKLE_NODE, 128, level,
    fields(left) || fields(right))                           // 32 elements
payoutDigest = P2BB512(PAYOUT, 72, 0,
    u16be(recipient_20 || relayer_20 || fee_u256_be))        // 36 elements
statementHash = P2BB512(STATEMENT, 256, 0,
    fields(scope) || fields(root) || fields(nullifierHash) ||
    fields(payoutDigest))                                    // 64 elements
parameterId = K512(PARAMETER_MANIFEST, manifest.bin)
```

The Merkle `level` auxiliary value is 0 for leaf-parent hashing and 19 for the root-producing hash. Changing order, encoding, lengths, domain, level, parameter ID, chain, pool, denomination, or protocol version changes the bound value.

## Canonical note encoding

A user-facing note is the ASCII prefix `pqtc-note-v3:` followed by unpadded RFC 4648 base64url of exactly 194 binary bytes:

| Offset | Value |
|---:|---|
| `0..4` | ASCII `PQTN` |
| `4..6` | version `3`, `u16_be` |
| `6..14` | chain ID, `u64_be` |
| `14..34` | pool address |
| `34..98` | parameter ID |
| `98..130` | nullifier secret: eight canonical `u32_be` limbs |
| `130..162` | trapdoor: eight canonical `u32_be` limbs |
| `162..194` | checksum |

The checksum is `keccak256(0x00 || NOTE || bytes[0..162])`, with `NOTE=0x11`. Parsers require the exact prefix, unpadded alphabet, decoded length, magic, version, checksum, and canonical secret limbs. The checksum detects corruption; it is neither encryption nor a password hash. Chain, pool, and parameter ID must match the intended immutable pool before use.

## Withdrawal relation and AIR schedule

The 64 public values are the 16 canonical fields of each digest in this order:

```text
scope || root || nullifierHash || payoutDigest
```

The witness is two canonical eight-limb secrets, one 20-bit leaf index, 20 little-endian path bits, and 20 sibling digests. The AIR derives the nullifier first, derives the note commitment second, verifies all 20 level-separated Merkle hashes, and binds payout public values. Its exact active schedule is:

| Rows | Operation | Permutations |
|---:|---|---:|
| `0..8` | `NULLIFIER` | 6 absorbs + 3 squeezes |
| `9..19` | `NOTE` | 8 absorbs + 3 squeezes |
| `20..239` | `APP_MERKLE_NODE`, levels 0 through 19 | 11 per level |
| `240..243` | payout public binding | 4 |
| `244..255` | canonical padding | 0 application work |

The first three regions contain 240 application-hash permutations. Four payout rows follow, then 12 padding rows. Width 190 is the maintained 157-column Poseidon2 sub-AIR plus five operation selectors, four step bits, five level bits, `isLastLevel`, `pathBit`, the remaining leaf index, and 16 `WORK` columns.

`WORK` deliberately overlaps lifetimes. During the nullifier and early note rows its first eight cells carry the nullifier-secret limbs. During the final note absorb/squeezes those same 16 cells are replaced chunk-by-chunk with the note digest. During each Merkle operation they hold the current digest and are replaced with the parent digest. Trapdoor limbs occur only as the note rows' canonical field deltas. This lifetime overlap is part of AIR v3 and is why separate secret/current/digit column groups are absent.

The AIR has 1,186 generated constraints and declared maximum degree 7. Security accounting batches 210 functions: 190 trace columns, 16 quotient chunks, and 4 random columns. See `docs/air-spec.md` for controller constraints.

## Proof-only commitments and transcript

A proof leaf over canonical field words is:

```text
K512(PROOF_LEAF, byteLength_u32_be || field[0]_u32_be || ...)
```

where `byteLength = 4 * fieldCount`. An internal proof node is `K512(PROOF_NODE, left_64 || right_64)`. The hiding MMCS appends eight random BabyBear salt elements per leaf; the v0.3 production profile uses four random codewords seeded from operating-system entropy.

The typed transcript state is 64 bytes:

```text
state0 = K512(TRANSCRIPT_INIT,
    parameterId_64 || publicValue[0]_u32_be || ... || publicValue[63]_u32_be)
state' = K512(TRANSCRIPT_ABSORB,
    state_64 || itemType_u8 || itemLength_u32_be || item)
block[counter] = K512(TRANSCRIPT_SQUEEZE, state_64 || counter_u64_be)
```

`itemType=1` encodes one canonical field element and `itemType=2` one proof commitment. Absorption clears buffered squeeze bytes and resets the counter. Base-field challenges rejection-sample canonical values after clearing the top bit of each big-endian `u32`; extension challenges sample four coefficients in order. Query sampling takes the requested low bits of a big-endian `u32` squeeze word. The pinned order covers degree metadata, commitments, public values, OOD openings, FRI commitments and witnesses, final polynomial, query proof-of-work witness, and all 32 indices.

## Canonical two-part proof envelope

Both proof parts have a 338-byte common prefix:

| Offset | Encoding |
|---:|---|
| `0..8` | ASCII `PQTCPA03` for A or `PQTCPB03` for B |
| `8..10` | proof version `3`, `u16_be` |
| `10` | profile: 0 dev, 1 CI, 3 `sepolia-v0.3` |
| `11` | proof degree bits, exactly 9 |
| `12` | binary FRI round count, exactly 9 |
| `13` | random-codeword count from manifest, 4 in production |
| `14..16` | total query count, `u16_be`, 32 in production |
| `16..80` | `parameterId` |
| `80..82` | public-value count, exactly 64 |
| `82..338` | 64 canonical `u32_be` public values |

`globalData` is exactly 9,208 bytes in this order:

1. trace, quotient, and random commitment roots (three 64-byte roots);
2. 190 trace-local and 190 trace-next extension openings;
3. `16 * 4` quotient extension openings and four random extension openings;
4. hiding openings for batches 0, 1, and 2 with shapes `1*1*r`, `1*2*r`, and `16*1*r`, where `r=4`;
5. nine FRI roots and nine canonical base-field commit proof-of-work witnesses;
6. one final-polynomial extension and one canonical base-field query proof-of-work witness.

Let `globalDigest = keccak256(globalData)`. After the common prefix:

```text
A = globalDigest_32 || globalData_9208 || checkpoint || halfA || 0x50414533
B = coreProofId_32 || globalDigest_32 || globalData_9208 || checkpoint || halfB || 0x50424533
```

A's global digest starts at offset 338. B's core proof ID occupies `338..370` and its global digest `370..402`. Both repeat byte-identical global data so B can perform its DEEP/MMCS checks without rerunning A's AIR and transcript work. The regenerated canonical v3 fixture sizes are 101,990 bytes for A and 108,294 bytes for B, 210,284 bytes total; pruned-frontier sizes are proof-dependent, so these are exact measured fixture sizes rather than a universal fixed-length claim.

Each half starts with `start_u16_be || count_u16_be` and exactly 16 derived indices. The production starts/counts are `(0,16)` and `(16,16)`. For the three input batches, matrix count/width pairs are `(1,8)`, `(1,194)`, and `(16,8)`, incorporating four random columns. Each batch encodes opened rows, eight field salts per matrix leaf, a `u32_be` pruned-digest count, and canonical frontier digests. Each of nine FRI rounds encodes one extension sibling and eight salts per query plus its canonical pruned frontier. No flags, indices, counts, widths, or round counts are caller-selectable.

## Statement, checkpoint, and consumer binding

The EVM keys are fixed-width Solidity ABI encodings:

```text
statementKey = keccak256(abi.encode(
    bytes32("PQTC.V3.STATEMENT"), parameterId.left, parameterId.right,
    publicValues[64]))
checkpointDigest = keccak256(abi.encode(
    bytes32("PQTC.V3.CHECKPOINT"), statementKey, keccak256(checkpointPayload)))
coreProofId = keccak256(abi.encode(
    bytes32("PQTC.V3.PROOF"), statementKey, keccak256(fullPartA)))
verificationId = keccak256(abi.encode(
    bytes32("PQTC.V3.VERIFICATION"), coreProofId, consumer))
```

The checkpoint begins with its digest. Its payload contains `globalDigest`; the 64-byte transcript state; `airAlpha`, `zeta`, `friAlpha`, and nine `friBeta` extensions; total query count and all derived indices; then the count and ascending set of unique indices. A stores only `consumer`, `statementKey`, `coreProofId`, `checkpointDigest`, and `globalDigest` under `verificationId`. It stores neither proof bytes nor expanded queries. `consumer` is registry `msg.sender`, never caller-selected calldata.

The registry API is:

```text
beginVerification(parameterId, publicValues[64], proofPartA) -> verificationId
completeVerification(verificationId, parameterId, publicValues[64], proofPartB) -> bool
```

A verifies positions 0 through 15 before storing state. B requires the same consumer, parameter, public values, statement key, core proof ID, global digest, and checkpoint; it verifies positions 16 through 31 and consumes the checkpoint. Exact duplicate live A is idempotent; mismatched collision data reverts.

## Pool lifecycle and atomicity

A deposit must equal the immutable denomination and contain a new, nonzero, canonical digest. It appends to the depth-20 tree and records the resulting root.

A withdrawal requires a known root, unspent canonical nullifier, nonzero recipient, fee no greater than denomination, and a nonzero relayer when fee is nonzero. The only proof lifecycle is:

```text
transaction A: pool.beginWithdrawal(withdrawal, proofPartA)
transaction B: pool.withdraw(withdrawal, verificationId, proofPartB)
```

A validates the statement and invokes the registry as the bound pool consumer. An operator must wait for a successful A receipt and validate its chain, registry, pool, parameter, statement, verification ID, event, and status before broadcasting B. B repeats validation, completes verification, consumes the checkpoint, marks the nullifier, and transfers the proof-bound recipient amount and relayer fee.

Checkpoint deletion, nullifier marking, and payments share EVM rollback. If verification or either payment reverts, all B state changes revert. An identical A front-run through the same pool donates work; another caller occupies another consumer namespace. A direct B replay has no checkpoint, and a value replay has a spent nullifier.

There is no consumed-proof tombstone. A successful proof's exact A could theoretically recreate registry state, but both pool entry points reject its spent nullifier before registry access. Other abandoned valid checkpoints remain a storage-griefing surface requiring bounded cleanup or a quantified bound before deployment.

No proof facts, bonds, SSTORE2/runtime-code proof shards, proof-data deployments, expanded query transactions, or third verification call are part of v0.3. The earlier three-call interim idea is not a live fallback.

## Version cutover and status

Protocol version 3 in scope, canonical field secrets, AIR v3, proof codec v3, verifier interface v3, manifest v3, the `sepolia-v0.3` profile, v3 magic/end markers, and v3 textual domains jointly invalidate all earlier notes, commitments, roots, nullifiers, proofs, facts, staged sessions, and parameter IDs. There is no alias, compatibility decoder, adapter, or state migration.

Adoption requires a fresh independently reviewed immutable deployment. No such Sepolia deployment occurred, and the local Foundry gas measurements are not Ethereum receipts.
````

</details>

## `docs/security-report.md`

- Bytes: 11,295
- SHA-256: `1f19df83bd433da38a9f4c6a0dc4fe77769105d69feaca4f77c79b38041583c7`

<details><summary>Complete file</summary>

```markdown
# PQ Tornado Classic v0.3 Security Report

## Report status

This is a pre-deployment security statement for the v0.3 research implementation. It is not an audit, production approval, deployment authorization, or on-chain evidence. No Sepolia deployment or v0.3 Ethereum receipt exists. The exact gas results in `docs/gas-model.md` are local Foundry measurements.

The security outputs below are generated for the implemented `sepolia-v0.3` profile. They are conditional on the stated models and must be regenerated whenever the AIR, parameters, transcript, codec, or code binding changes.

## Pinned v0.3 profile

| Parameter | v0.3 value |
|---|---:|
| Base field | BabyBear, modulus 2,013,265,921 |
| Application permutation | Poseidon2 width 16, rate 4, capacity 12, $x^7$ |
| Poseidon2 rounds | 8 full, 13 partial |
| Challenge extension | degree 4 |
| Logical AIR | 256 rows by 190 columns |
| Active application-hash permutations | 240 |
| Base AIR degree bits | 8 |
| Hiding proof degree bits | 9 |
| Maximum AIR constraint degree | 7 |
| AIR constraints | 1,186 |
| FRI log blowup | 4 |
| Global FRI log height | 13 |
| Binary FRI rounds | 9 |
| FRI queries | 32, split 16/16 |
| Final polynomial bound | 1 |
| Commit grinding | 16 configured classical bits |
| Query grinding | 16 configured classical bits |
| Random masking codewords | 4 |
| MMCS salt elements | 8 per leaf |
| Batched functions | 210 (`190 + 16 + 4`) |
| Conservative challenge-field budget | 120 bits |
| Quantum-adjusted MMCS cap | 128 bits |

The source-of-record package is `parameters/sepolia-v0.3`: `manifest.bin`, human-readable manifest JSON, `security-analysis.json`, and `parameter-id.txt`, all generated from the same source. Manifest magic is `PQTCPRM3`; manifest, AIR, protocol, proof codec, and verifier interface versions are 3. A release candidate must additionally pin reviewed expected runtime code hashes.

## Canonical field-secret security

Each 32-byte nullifier secret and trapdoor encodes eight independent canonical `u32_be` BabyBear elements. Any limb at least $p$ is rejected; implementations never reduce arbitrary bytes. Rejection sampling gives uniform independent limbs and approximately

$$8\log_2(2{,}013{,}265{,}921)\approx247.3\text{ bits}$$

of classical entropy per secret. Generic Grover search for one particular uniformly sampled secret therefore has an idealized work factor of approximately 123.6 bits, not 128 bits. The two secrets serve different inputs; their existence does not add their generic security levels into a 247-bit quantum claim.

The canonical-field representation was selected to remove in-AIR byte range decompositions and to make witness values identical across Rust, Solidity-facing encodings, and the AIR. Canonical parsing, unbiased generation, secret independence, and operating-system entropy are security requirements.

## Application-hash quantum ceiling

P2BB512-v1 uses 12 BabyBear capacity elements:

$$12\log_2(2{,}013{,}265{,}921)\approx370.9\text{ bits}.$$

Under an ideal-permutation model, generic Brassard–Høyer–Tapp quantum collision search gives an approximate capacity bound:

$$370.9/3\approx\mathbf{123.6\text{ bits}}.$$

This is a generic idealized ceiling, not a concrete proof and not a 256-bit security claim. There is no structural classical or quantum security analysis for the pinned BabyBear Poseidon2 width-16, 8-full/13-partial-round instance or for this sponge composition. Algebraic, differential, invariant, related-input, or future quantum attacks could lower the bound.

Domain, byte length, field count, auxiliary value, canonical encodings, Merkle level, and parameter-bound scope are mandatory. Removing or changing any one defines another construction.

## STARK soundness accounting

The generator derives 1,186 constraints and maximum degree 7 from `WithdrawalAir`, and sets the batched-function count to 210. It separately accounts for AIR random-linear-combination soundness, DEEP-ALI out-of-domain soundness, FRI query and commit phases, batched openings, challenge field, proof commitments, grinding, and quantum adjustments.

The generated production-profile outputs are:

| Analysis | Bits |
|---|---:|
| Random-words conjecture | **107** |
| Proven unique-decoding bound (UDR) | **37** |
| Proven list-decoding bound (LDR) | **56** |
| Best proven bound | **56** |

The 107-bit value clears a configured 100-bit target only under Plonky3's documented random-words conjecture. The proven bounds are 37 and 56 bits. This design must never be described as providing 100-bit proven security.

The 32-query profile is an explicit tradeoff. It reduces direct calldata and verifier work enough for the measured two-call EIP-7825 model while retaining a 107-bit conjectured estimate with log blowup 4 and the configured grinding. It lowers conservative proven decoding security to the values above. A reviewer who requires 100-bit proven soundness must reject this parameter set rather than relabel the conjectured estimate.

Each configured 16-bit proof-of-work site receives only the square-root-adjusted quantum credit used by the generator. Repeated proofs, many pools, and reused parameters create multi-target settings. No fixed bit estimate permits unlimited use. Any query, blowup, grinding, random-codeword, salt, AIR degree, constraint-count, or batching change requires complete regeneration and review.

## Hiding and zero knowledge

The logical trace is 256 rows with degree bits 8. `HidingFriPcs` commits a masked representation with degree bits 9. The production profile uses four random codewords, and `MerkleTreeHidingMmcs` uses eight salt fields per leaf.

Zero knowledge assumes correct Plonky3 hiding composition and fresh operating-system CSPRNG entropy for every proof. Deterministic masks, reused seeds, omitted random openings, or operational APIs exposing masking seeds are blockers. Hiding parameters do not automatically strengthen soundness, and soundness parameters do not prove hiding.

## KeccakPair512, Fiat–Shamir, and QROM limits

KeccakPair512 is used only for proof Merkle commitments, transcript operations, and `parameterId`. It concatenates two domain-separated Keccak-256 outputs; it is not standardized Keccak-512. Claims rely on correct Ethereum Keccak, collision/preimage resistance appropriate to each role, typed length-delimited encoding, and random-oracle-style transcript behavior.

The transcript binds parameter ID, all 64 public values, degree metadata, global commitments and openings, hiding openings, nine FRI commitments and proof-of-work witnesses, final polynomial, query proof-of-work witness, and all 32 derived query positions. However, no proof establishes this custom two-branch transcript or the complete STARK composition in the quantum random-oracle model. The 128-bit MMCS cap and quantum-adjusted grinding credits are model inputs, not a QROM composition proof.

## Two-part verifier security

Part A and B carry the same common header and byte-identical 9,208-byte global data. `statementKey` binds parameter ID and all 64 public values. `globalDigest` binds global proof bytes. The checkpoint digest binds the statement, global digest, transcript state, challenges, all indices, and the canonical sorted unique index set. `coreProofId` binds the full part A; `verificationId` binds that core ID to registry `msg.sender`.

Transaction A enters through pool `beginWithdrawal`, so the bound consumer is the immutable pool rather than caller-chosen calldata. A verifies positions 0 through 15 before storing a compact checkpoint. Only that pool can complete B, which must match all stored bindings and verifies positions 16 through 31. Query count, matrix shapes, rounds, salts, and pruned-frontier order are fixed. The regenerated fixture sizes are 101,990 bytes for A and 108,294 bytes for B; exact frontier length remains proof-dependent.

The construction assumes Rust and Solidity equivalence for transcript operations, extension arithmetic, AIR/DEEP evaluation, MMCS multiproofs, and FRI folding. Parser work and allocation must be bounded by manifest constants.

An identical A front-run through the same pool derives the same ID and donates work because an exact live duplicate is idempotent. Another caller has a separate namespace. Checkpoint consumption, nullifier marking, and transfer occur in B and roll back together. Direct B replay lacks a checkpoint; payment replay fails the spent-nullifier check.

There is no consumed-proof tombstone. The pool rejects a completed proof's spent nullifier before registry access, but other abandoned valid checkpoints are a storage-denial-of-service concern. A bounded cleanup design or quantified hard bound remains a deployment prerequisite.

## Parameter and code binding

Manifest v3 begins with `PQTCPRM3` and version 3. Its canonical binary encoding commits to:

- profile name, Plonky3 commit, Rust toolchain, field, and extension degree;
- AIR version and source hash;
- tree depth, protocol version, and trace height;
- FRI blowup, folding arity, query count, final bound, and grinding;
- random-codeword and MMCS-salt counts;
- proof codec and verifier interface versions;
- ordered expected runtime code hashes.

`parameterId = K512(PARAMETER_MANIFEST, manifest.bin)`. The immutable scope includes the ID; pool and registry hold it immutably. A source, parameter, compiler output, or runtime module change requires a new manifest, ID, proof package, notes, and deployment. All earlier protocol artifacts are invalid; no compatibility route or three-call fallback is authorized.

## Gas evidence and operational assumptions

The current evidence is the full pool-facing Foundry ABI model:

- A execution: 14,891,070 gas; execution plus standard intrinsic: 16,539,302; 237,914 below EIP-7825.
- B execution including completion/payment path: 12,356,373 gas; execution plus standard intrinsic: 14,105,909; 2,671,307 below EIP-7825.
- Registry-only execution profile: A 14,056,853; B 11,470,158.
- One-call deposit execution: 13,991,021; its small ABI intrinsic conservatively keeps it below the cap.

These are local measurements, not receipts. EIP-7623 applies a transaction-wide maximum between standard execution accounting and the calldata floor; the floor is not added to execution. No Sepolia transaction or deployment occurred.

Additional assumptions and blockers include:

- deployed bytecode must match an independently reviewed build and manifest hashes;
- canonical decoders, arithmetic, Poseidon2, transcript, MMCS, and the Rust/Solidity boundary require independent review;
- every runtime must fit EIP-170, and final transaction calldata must be independently reproduced;
- Ethereum consensus, EVM rollback/storage/account authorization, and native-ETH call semantics are assumed;
- indexer reorg handling and at least one honest source are operational assumptions;
- provers and relayers are untrusted and replaceable; censorship affects liveness;
- timing, transaction graph, fees, RPC traffic, recipient behavior, and anonymity-set quality can link users.

No audit or production approval is claimed. External cryptographic and Solidity review, final runtime hashes and code sizes, and actual network receipts remain requirements before any deployment proposal.
```

</details>

## `docs/threat-model.md`

- Bytes: 5,710
- SHA-256: `a59bef320a878ca4fef095d5335b34cc10b1a926d1ce5d802a4a7817cbe01709`

<details><summary>Complete file</summary>

```markdown
# Threat Model for v0.3

## Objective and status

PQ Tornado Classic v0.3 aims to prevent note recovery, ambiguous commitment opening, forged Merkle membership, withdrawal without the witness, payout substitution, and double spending, while hiding witness values beyond public-chain and network metadata.

This is unaudited, pre-deployment research. “Post-quantum” describes primitive choices and modeled generic attacks; it is not proof of the composed system. No Sepolia deployment or v0.3 receipt exists.

## Assets and invariants

- Each nullifier secret and trapdoor is eight independently sampled canonical BabyBear limbs (about 247.3 classical entropy bits each); noncanonical limbs are rejected, never reduced.
- P2BB512-v1 binds scope, note, nullifier, Merkle level/children, payout, and statement.
- Scope binds chain, pool, denomination, tree depth, protocol version 3, and parameter ID.
- AIR v3 binds the witness to 64 public fields: scope, root, nullifier, payout.
- Fresh hiding randomness prevents direct witness disclosure.
- A proof pays only its bound recipient/relayer and one denomination less fee; a nullifier pays once.
- A/B are one transcript and statement. A verifies query positions 0 through 15; B verifies 16 through 31.
- Failed B verification or payment rolls checkpoint, nullifier, balances, and transfers back together.
- No owner, upgrade key, trusted setup, prover, verifier service, or relayer can unilaterally move funds.

## Adversary capabilities

Malicious depositors, holders, provers, relayers, recipients, RPC sources, contracts, and block builders may submit malformed or noncanonical encodings; reorder, front-run, replay, mix, or abandon proof halves; target identifier or transcript confusion; exploit duplicate derived queries and multiproof frontiers; reenter or revert payments; provide reorganized histories; censor; or create valid abandoned checkpoints.

A caller cannot choose the 32 query indices after commitments: the transcript derives the entire schedule. Duplicate positions remain in the soundness schedule, while a sorted unique set determines canonical multiproof frontiers. Query count, AIR width, FRI rounds, matrix widths, and frontier traversal are manifest-bounded.

## Cryptographic assumptions and limits

P2BB512 uses Poseidon2 width 16, rate 4, capacity 12. Under an ideal-permutation model its $12\log_2(p)$ capacity gives an approximate 123.6-bit generic BHT quantum collision ceiling. One canonical secret similarly gives about 123.6 bits against idealized Grover search. These are not concrete proofs or additive claims.

There is no structural classical or quantum analysis for this Poseidon2 instance or sponge. Algebraic, differential, invariant, related-input, or future quantum attacks may lower security.

The `sepolia-v0.3` STARK profile has 1,186 degree-7 AIR constraints, 210 batched functions, log blowup 4, 32 queries, and configured 16-bit commit/query grinding. Generated security is **107 bits conjectured under random words, 37 bits proven UDR, and 56 bits proven LDR/best**. It is not 100-bit proven security; repeated proofs and multiple targets further matter.

KeccakPair512 is a custom two-branch Keccak-256 construction used only for proof commitments, transcript, and manifests. The complete Fiat–Shamir/STARK composition has no QROM proof. Generic Keccak estimates and the 128-bit MMCS accounting cap do not prove composition security.

Zero knowledge assumes correct `HidingFriPcs`/`MerkleTreeHidingMmcs`, four fresh codewords, eight fresh salt fields per leaf, and OS CSPRNG entropy. Deterministic or reused production randomness is invalid.

## Two-call and contract risks

A enters through the pool, which reconstructs the statement before registry `beginVerification`; registry `msg.sender` therefore binds the pool consumer. A stores only consumer, statement key, core proof ID, global digest, and checkpoint digest. B must match all bindings and only that pool may complete.

An identical A front-run through the same pool is idempotent work donation. Another caller has another consumer namespace. Completion deletes the checkpoint before success; the pool writes the nullifier before external calls. EVM rollback restores both contracts on failure. B replay lacks a checkpoint and payment replay meets a spent nullifier.

There is no consumed-proof tombstone. The pool rejects a completed proof before registry access, but other abandoned valid checkpoints remain a storage-griefing risk requiring bounded cleanup or a quantified hard bound before deployment.

Direct calldata can consume block space and incur high fees. The regenerated-proof Foundry model is below EIP-7825—A 16,539,302 and B 14,105,909 including standard intrinsic—but these are not receipts. EIP-7623 chooses the maximum of the standard execution path and calldata floor; it does not add the floor to execution.

## Operational assumptions and exclusions

Ethereum consensus, signatures, EVM semantics, storage, Keccak opcode correctness, and deployed bytecode matching reviewed source are assumed. Indexers must handle block-hash reorgs and use at least one honest cross-check source. Prover/relayer censorship affects liveness. Timing, gas bids, funding, RPC traffic, recipient behavior, telemetry, and anonymity-set quality can link users. Forced ETH does not authorize or enlarge withdrawals.

The protocol does not provide arbitrary balances, tokens, bridging, governance, upgrades, compliance filtering, recursion, private submission, network anonymity, endpoint availability, or lost-note recovery. Device compromise defeats privacy and authorization. There is no live earlier-version route or three-call fallback.
```

</details>

## `docs/adr/0001-keccak-pair-512.md`

- Bytes: 852
- SHA-256: `2a7b2a93b0e8efb475e5bb57ced20511bb1343aca244b2fd2eee82c471d7b78f`

<details><summary>Complete file</summary>

```markdown
# ADR-0001: KeccakPair512

Status: accepted

## Decision

Use `K512(tag, payload) = keccak256(0x00 || tag || payload) || keccak256(0x01 || tag || payload)` for all protocol digests. Freeze the domain tags and canonical big-endian encodings in `docs/protocol.md`.

## Rationale

Ethereum verifies Keccak-256 efficiently. Two independent domain-separated branches give a 512-bit digest without an elliptic-curve primitive and keep all application messages within one Keccak rate block. Standard Keccak-512 is not an EVM primitive and is not wire-compatible with this construction.

## Consequences

Every implementation must compare both halves. A tag, branch byte, byte order, or field-width change creates a new protocol and parameter ID. Proof hashing can process multiple rate blocks, but application hashing cannot use variable-width concatenation.
```

</details>

## `docs/adr/0002-babybear-hiding-fri.md`

- Bytes: 844
- SHA-256: `3ef1d2f75cb04cfc76070b347d55f83a19e649af7609bb4b3ef452c1d2f0a880`

<details><summary>Complete file</summary>

```markdown
# ADR-0002: BabyBear Degree-4 with Hiding Two-Adic FRI

Status: accepted

## Decision

Use BabyBear as the base field, its degree-4 binomial extension for challenges, and Plonky3 `HidingFriPcs` with `MerkleTreeHidingMmcs`. Pin Plonky3 to commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`.

## Rationale

The reference Keccak AIR uses 16-bit limbs, which fit BabyBear. BabyBear arithmetic fits EVM words. The degree-4 extension has about 120 bits of challenge space. Plonky3 supplies a reviewed hiding two-adic FRI path; its current Circle PCS is not hiding.

## Consequences

The prover must use operating-system entropy, random codewords, quotient masking, and eight BabyBear salt elements per committed leaf. A non-hiding PCS is invalid for withdrawals. Circle FRI remains deferred. Parameter changes require a new manifest and parameter ID.
```

</details>

## `docs/adr/0003-staged-verification.md`

- Bytes: 1,302
- SHA-256: `22aa0bca11ad5a14e445d5c843b3badd51229421fcdd356922e704bd7bf2e1f1`

<details><summary>Complete file</summary>

```markdown
# ADR-0003: Permissionless Staged Verification Fallback

Status: superseded by ADR-0004

## Historical decision

v0.1 selected a bonded, permissionless staged verifier because its 2,633-column Keccak AIR could not fit direct verification. A session parsed a header, absorbed OOD data from immutable runtime-code shards, accumulated AIR and quotient checks, reduced queries over hundreds of transactions, published a fact, and later allowed a separate pool withdrawal.

## Reason for supersession

That design required 128 public values, a 2,048-row Keccak AIR, proof-data deployments, SSTORE2-style runtime-code shards, 48 independently submitted query objects, a bonded session lifecycle, fact publication, and a separate withdrawal. The measured v0.1 flow used 818 successful transactions. These properties are incompatible with the current exactly-two-call requirement.

ADR-0004 replaces this route with P2BB512-v1 application hashing, a 256-row width-190 Poseidon2 AIR, 64 public values, 32 queries split 16/16, and one consumer-bound continuation checkpoint. There is no supported earlier-version fallback, compatibility selector, fact adapter, proof shard, or third verification call.

This ADR is retained only as historical rationale. It is not an implementation or operational recommendation.
```

</details>

## `docs/adr/0004-poseidon2-two-part-verification.md`

- Bytes: 5,208
- SHA-256: `eadd3921a4c4956da35c9fb9f1921f79b89a988012f355c06307c2c01db47f66`

<details><summary>Complete file</summary>

```markdown
# ADR-0004: P2BB512 and Two-Part Consumer-Bound Verification

Status: accepted for v0.3 implementation; external-review and deployment gates pending

Supersedes ADR-0003 and the application-hash portion of ADR-0001. KeccakPair512 remains accepted only for proof commitments, Fiat-Shamir, and parameter manifests.

## Decision

Use P2BB512-v1 for every application hash. It is the pinned BabyBear Poseidon2 width-16 permutation with rate 4, capacity 12, $x^7$, 8 full rounds, and 13 partial rounds. Its sponge capacity binds version, domain, original byte length, payload-element count, and an auxiliary value. Digests are 16 canonical big-endian BabyBear `u32` elements.

Encode each 32-byte nullifier secret and trapdoor as eight uniformly sampled canonical BabyBear limbs. The note commitment hashes `scope[16] || nullifierSecret[8] || trapdoor[8]`; the nullifier hashes `scope[16] || nullifierSecret[8]`. Reject noncanonical limbs rather than reducing them.

Use the 256-row, width-190 withdrawal AIR with 64 public values, 1,186 constraints, maximum degree 7, and hiding PCS proof degree bits 9. The 32-query `sepolia-v0.3` profile verifies one noninteractive proof in exactly two state-changing pool calls:

1. `beginWithdrawal` validates the statement, verifies query positions 0 through 15, and stores a compact checkpoint bound to the immutable pool, parameter, statement, global proof data, transcript continuation, proof ID, and derived query schedule.
2. `withdraw` repeats statement validation, verifies positions 16 through 31, consumes the checkpoint, marks the nullifier, and pays atomically.

Transport both canonical proof parts directly in calldata. Do not deploy proof bytes, publish a fact, add an auxiliary verifier transaction, or retain a three-call fallback. The registry has no trusted submitter; consumer binding, not submitter identity, controls completion.

## Rationale

The v0.1 Keccak AIR and staged verifier required 818 transactions and proof-data shards. The v0.2 48-query, width-230 design still exceeded the per-transaction gas cap. The v0.3 nullifier-first schedule overlaps witness workspace, reducing the AIR to width 190. A 32-query profile split 16/16 reduces verifier work and calldata enough for both pool-facing calls to fit EIP-7825 in the local full-ABI model.

The regenerated v0.3 fixture is 101,990 bytes for A and 108,294 bytes for B. A measured 16,539,302 gas including standard intrinsic accounting, 237,914 below the cap. B measured 14,105,909 including payment and intrinsic accounting, 2,671,307 below the cap. A deposit measures at most 14,013,109 under conservative intrinsic accounting. These are local Foundry results, not Ethereum receipts.

## Security consequences

- The protocol remains pairing-free and has no trusted setup, owner, trusted relayer, trusted prover, administrator, or upgrade path.
- Protocol, AIR, proof codec, verifier interface, manifest, notes, parameters, scope, and domains use version 3. Every earlier artifact is invalid.
- Hiding remains mandatory: four random codewords, eight salt elements per leaf, and fresh operating-system entropy for every proof.
- The base AIR has degree bits 8; the masked PCS proof has degree bits 9.
- Each canonical secret has approximately 247.3 bits of entropy and approximately 123.6 bits of idealized Grover work.
- P2BB512's 12-element capacity has an ideal-permutation generic BHT ceiling of approximately 123.6 bits. No structural classical or quantum proof exists for the pinned Poseidon2 instance.
- The custom KeccakPair512 transcript and complete Fiat-Shamir composition have no complete QROM proof.
- The q32 profile reports 107 conjectured bits, 37 proven UDR bits, and 56 proven LDR/best bits. It is not a 100-bit proven construction. Reducing from q48 lowers the conservative proven bounds; deployment requires explicit external acceptance of this tradeoff or a stronger design that preserves the transaction caps.
- Abandoned valid part-A checkpoints can consume storage. Cleanup or a quantified hard economic bound remains a deployment prerequisite.

## Atomicity and replay consequences

The registry derives a core proof ID from the statement and full part A, then derives a consumer-specific verification ID using `msg.sender`. Only the bound pool can complete part B. The checkpoint binds the parameter, statement, global digest, transcript state, challenges, indices, and proof ID. An exact live duplicate A is idempotent and donates work. Completion deletes the checkpoint before the pool marks the nullifier and performs external calls. Any verification, payment, or reentrancy revert restores both contracts. Direct B replay fails without a checkpoint; value replay fails the spent-nullifier check.

## Acceptance consequences

The local one-deposit and two-withdrawal-call gas gates pass, and every measured runtime remains below EIP-170. No deployment is authorized. Before a deployment proposal, reviewers must regenerate source-bound parameters and proofs, independently reproduce security and gas outputs, review runtime hashes, audit the cryptography and Solidity boundary, resolve checkpoint storage denial of service, and obtain successful network receipts.
```

</details>

## `benches/phase0-keccak.md`

- Bytes: 1,353
- SHA-256: `69c0a4f481959662343485560e9081f5dbce4f26fd80f92cc5548d45e990a729`

<details><summary>Complete file</summary>

````markdown
# Phase 0 Hiding-FRI Keccak Spike

Measured on Apple M4 Max, arm64 Darwin, release profile. Plonky3 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`; Rust 1.97.0. Command:

```text
/usr/bin/time -l cargo run --release -p pqtc-cli -- benchmark-keccak
```

| Metric | Result |
|---|---:|
| Active Keccak-f permutations | 1 |
| Trace rows | 32 |
| Keccak AIR columns | 2,633 |
| Canonical Postcard proof bytes | 115,199 |
| Prove time | 20 ms |
| Native verify time | 8 ms |
| Maximum resident set size | 12,255,232 bytes |

The proof uses BabyBear, its degree-4 extension, `HidingFriPcs`, four-byte canonical field leaves, eight random BabyBear salt elements per leaf, two random codewords in the `dev` profile, 512-bit Keccak-pair MMCS digests, and the typed 512-bit Keccak transcript. Two proofs made through one configuration differ and both verify.

This spike is a feasibility result, not a security result. The `dev` profile has two FRI queries and no grinding. Its proof is already larger than the direct-verifier target because the maintained reference Keccak AIR is wide. The result supports the staged-verifier decision: one query opens about 10.5 KiB of trace field data before authentication paths and FRI openings, which can fit the 32 KiB staged query target, while a complete compact proof is not expected to fit the 96 KiB direct target.
````

</details>


# Appendix C — Complete first-party implementation and tests, verbatim

Every Solidity source, script, test, helper contract, interface, and library is included in full. External imports are referenced but their external source is excluded. Rust and TypeScript first-party source and tests are also included in full.

## `contracts/src/PQTCClassicPool.sol`

- Bytes: 8,652
- SHA-256: `5ce4f94692e87922efd0584e543afc43937ad8647161dd4e3e16bb8a442c0fd0`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Digest512, Digest512Lib} from "./libraries/Digest512.sol";
import {P2BB512} from "./libraries/P2BB512.sol";
import {PQTCApplicationHash} from "./libraries/PQTCApplicationHash.sol";

interface IPQTCVerificationRegistry {
    function beginVerification(
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata proofPartA
    ) external returns (bytes32 verificationId);

    function completeVerification(
        bytes32 verificationId,
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata proofPartB
    ) external returns (bool);
}

/// Fixed-denomination, append-only, depth-20 native-ETH mixer pool.
/// The verification registry, parameter ID, denomination, and scope never change.
contract PQTCClassicPool {
    using Digest512Lib for Digest512;

    uint8 public constant TREE_DEPTH = 20;
    uint32 public constant PROTOCOL_VERSION = 3;
    uint32 public constant CAPACITY = uint32(1) << TREE_DEPTH;

    uint256 public immutable denomination;
    IPQTCVerificationRegistry public immutable verificationRegistry;
    Digest512 public scope;
    Digest512 public parameterId;
    uint32 public nextIndex;
    Digest512[20] internal filledSubtrees;
    Digest512[21] internal zeros;

    mapping(bytes32 => mapping(bytes32 => bool)) public commitments;
    mapping(bytes32 => mapping(bytes32 => bool)) public nullifiers;
    mapping(bytes32 => mapping(bytes32 => bool)) public knownRoots;

    uint256 private reentrancyState = 1;

    struct Withdrawal {
        Digest512 root;
        Digest512 nullifierHash;
        address payable recipient;
        address payable relayer;
        uint256 fee;
    }

    event Deposit(
        bytes32 indexed commitmentLeft,
        bytes32 indexed commitmentRight,
        uint32 leafIndex,
        bytes32 rootLeft,
        bytes32 rootRight,
        uint256 timestamp
    );
    event WithdrawalComplete(
        bytes32 indexed nullifierLeft,
        bytes32 indexed nullifierRight,
        address indexed recipient,
        address relayer,
        uint256 fee
    );

    error ReentrantCall();
    error InvalidDenomination();
    error InvalidDependency();
    error IncorrectDepositValue();
    error ZeroCommitment();
    error DuplicateCommitment();
    error TreeFull();
    error UnknownRoot();
    error NullifierSpent();
    error ZeroRecipient();
    error FeeExceedsDenomination();
    error ZeroRelayer();
    error InvalidProof();
    error TransferFailed();

    modifier nonReentrant() {
        if (reentrancyState != 1) revert ReentrantCall();
        reentrancyState = 2;
        _;
        reentrancyState = 1;
    }

    constructor(uint256 denomination_, Digest512 memory parameterId_, IPQTCVerificationRegistry verificationRegistry_) {
        if (denomination_ == 0) revert InvalidDenomination();
        if (parameterId_.isZero()) revert InvalidDependency();
        if (address(verificationRegistry_) == address(0)) revert InvalidDependency();
        denomination = denomination_;
        parameterId = parameterId_;
        verificationRegistry = verificationRegistry_;
        scope = PQTCApplicationHash.scope(
            uint64(block.chainid), address(this), denomination_, TREE_DEPTH, PROTOCOL_VERSION, parameterId_
        );

        zeros[0] = PQTCApplicationHash.emptyLeaf(scope);
        for (uint8 level = 0; level < TREE_DEPTH; level++) {
            filledSubtrees[level] = zeros[level];
            zeros[level + 1] = PQTCApplicationHash.merkleNode(level, zeros[level], zeros[level]);
        }
        Digest512 memory initialRoot = zeros[TREE_DEPTH];
        latestRoot = initialRoot;
        knownRoots[initialRoot.left][initialRoot.right] = true;
    }

    function deposit(Digest512 calldata commitment) external payable nonReentrant {
        if (msg.value != denomination) revert IncorrectDepositValue();
        P2BB512.toFields(commitment);
        if (commitment.left == bytes32(0) && commitment.right == bytes32(0)) revert ZeroCommitment();
        if (commitments[commitment.left][commitment.right]) revert DuplicateCommitment();
        uint32 leafIndex = nextIndex;
        if (leafIndex >= CAPACITY) revert TreeFull();

        Digest512 memory current = commitment;
        uint32 index = leafIndex;
        for (uint8 level = 0; level < TREE_DEPTH; level++) {
            if (index & 1 == 0) {
                filledSubtrees[level] = current;
                current = PQTCApplicationHash.merkleNode(level, current, zeros[level]);
            } else {
                current = PQTCApplicationHash.merkleNode(level, filledSubtrees[level], current);
            }
            index >>= 1;
        }

        commitments[commitment.left][commitment.right] = true;
        knownRoots[current.left][current.right] = true;
        nextIndex = leafIndex + 1;
        latestRoot = current;
        emit Deposit(commitment.left, commitment.right, leafIndex, current.left, current.right, block.timestamp);
    }

    function beginWithdrawal(Withdrawal calldata withdrawal, bytes calldata proofPartA)
        external
        nonReentrant
        returns (bytes32 verificationId)
    {
        uint32[64] memory values = _validatedPublicValues(withdrawal);
        return verificationRegistry.beginVerification(parameterId, values, proofPartA);
    }

    function withdraw(Withdrawal calldata withdrawal, bytes32 verificationId, bytes calldata proofPartB)
        external
        nonReentrant
    {
        uint32[64] memory values = _validatedPublicValues(withdrawal);
        if (!verificationRegistry.completeVerification(verificationId, parameterId, values, proofPartB)) {
            revert InvalidProof();
        }
        _completeWithdrawal(withdrawal);
    }

    function currentRoot() external view returns (Digest512 memory) {
        return latestRoot;
    }

    function zero(uint8 level) external view returns (Digest512 memory) {
        if (level > TREE_DEPTH) revert UnknownRoot();
        return zeros[level];
    }

    function _completeWithdrawal(Withdrawal calldata withdrawal) private {
        nullifiers[withdrawal.nullifierHash.left][withdrawal.nullifierHash.right] = true;
        uint256 recipientAmount = denomination - withdrawal.fee;
        (bool recipientPaid,) = withdrawal.recipient.call{value: recipientAmount}("");
        if (!recipientPaid) revert TransferFailed();
        if (withdrawal.fee != 0) {
            (bool relayerPaid,) = withdrawal.relayer.call{value: withdrawal.fee}("");
            if (!relayerPaid) revert TransferFailed();
        }
        emit WithdrawalComplete(
            withdrawal.nullifierHash.left,
            withdrawal.nullifierHash.right,
            withdrawal.recipient,
            withdrawal.relayer,
            withdrawal.fee
        );
    }

    function _validatedPublicValues(Withdrawal calldata withdrawal) private view returns (uint32[64] memory values) {
        uint32[16] memory rootFields = P2BB512.toFields(withdrawal.root);
        uint32[16] memory nullifierFields = P2BB512.toFields(withdrawal.nullifierHash);
        if (!knownRoots[withdrawal.root.left][withdrawal.root.right]) revert UnknownRoot();
        if (nullifiers[withdrawal.nullifierHash.left][withdrawal.nullifierHash.right]) revert NullifierSpent();
        if (withdrawal.recipient == address(0)) revert ZeroRecipient();
        if (withdrawal.fee > denomination) revert FeeExceedsDenomination();
        if (withdrawal.fee != 0 && withdrawal.relayer == address(0)) revert ZeroRelayer();
        Digest512 memory payout =
            PQTCApplicationHash.payoutDigest(withdrawal.recipient, withdrawal.relayer, withdrawal.fee);
        return _publicValues(rootFields, nullifierFields, payout);
    }

    function _publicValues(uint32[16] memory rootFields, uint32[16] memory nullifierFields, Digest512 memory payout)
        private
        view
        returns (uint32[64] memory values)
    {
        uint32[16] memory scopeFields = P2BB512.toFields(scope);
        uint32[16] memory payoutFields = P2BB512.toFields(payout);
        for (uint256 limb = 0; limb < 16; ++limb) {
            values[limb] = scopeFields[limb];
            values[16 + limb] = rootFields[limb];
            values[32 + limb] = nullifierFields[limb];
            values[48 + limb] = payoutFields[limb];
        }
    }

    // `knownRoots` intentionally retains all history. Track the latest root separately
    // without adding another public storage mapping lookup in deposits.
    Digest512 private latestRoot;
}
```

</details>

## `contracts/src/PQTCDomains.sol`

- Bytes: 731
- SHA-256: `82575864ba97c7c4045b5a0d9ea5ab2c7a672b3ceb79550433a8e907c7697025`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

library PQTCDomains {
    uint8 internal constant SCOPE = 0x10;
    uint8 internal constant NOTE = 0x11;
    uint8 internal constant NULLIFIER = 0x12;
    uint8 internal constant EMPTY_LEAF = 0x13;
    uint8 internal constant PAYOUT = 0x14;
    uint8 internal constant STATEMENT = 0x15;
    uint8 internal constant APP_MERKLE_NODE = 0x20;
    uint8 internal constant PROOF_LEAF = 0x40;
    uint8 internal constant PROOF_NODE = 0x41;
    uint8 internal constant TRANSCRIPT_INIT = 0x42;
    uint8 internal constant TRANSCRIPT_ABSORB = 0x43;
    uint8 internal constant TRANSCRIPT_SQUEEZE = 0x44;
    uint8 internal constant PARAMETER_MANIFEST = 0x45;
}
```

</details>

## `contracts/src/PQTCVerificationRegistry.sol`

- Bytes: 23,407
- SHA-256: `8553941eb44998dca5bd18cc6eeb7d016bb8cccfa334efb7f693a4a1575a4722`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBearExt4Packed as Ext} from "./libraries/BabyBearExt4Packed.sol";
import {CanonicalCodec} from "./libraries/CanonicalCodec.sol";
import {Digest512} from "./libraries/Digest512.sol";
import {PQTCProofCodec} from "./libraries/PQTCProofCodec.sol";
import {Transcript512} from "./libraries/Transcript512.sol";
import {PQTCAirStageVerifier} from "./verifier/PQTCAirStageVerifier.sol";
import {PQTCQueryVerifier} from "./verifier/PQTCQueryVerifier.sol";

/// Two-transaction verifier. Only a compact, consumer-bound checkpoint crosses transactions.
contract PQTCVerificationRegistry {
    uint256 private constant GLOBAL_DATA_BYTES = 9_208;
    uint256 private constant TRACE_WIDTH = 190;
    uint256 private constant RANDOM_CODEWORDS = 4;
    uint256 private constant QUOTIENT_EXTENSIONS = 64;
    uint256 private constant QUERY_COUNT = 32;
    uint256 private constant FRI_ROUNDS = 9;
    uint8 private constant AIR_SPLIT = 3;

    struct StoredCheckpoint {
        address consumer;
        bytes32 coreProofId;
        bytes32 statementKey;
        bytes32 checkpointDigest;
        bytes32 globalDigest;
        uint256 airAccumulator;
        uint8 airCursor;
        uint256 zetaAggregate;
        uint256 nextAggregate;
    }

    struct TranscriptCheckpoint {
        bytes32 digest;
        bytes32 globalDigest;
        Digest512 state;
        uint256 airAlpha;
        uint256 zeta;
        uint256 friAlpha;
        uint256[9] friBetas;
        uint32[32] queryIndices;
        uint256 cursor;
    }

    struct GlobalData {
        PQTCQueryVerifier.Context query;
        uint256[190] traceLocal;
        uint256[190] traceNext;
        uint256[64] quotient;
        uint32[9] friWitnesses;
        uint32 queryWitness;
        uint256 cursor;
    }

    bytes32 public immutable parameterLeft;
    bytes32 public immutable parameterRight;
    PQTCAirStageVerifier public immutable airVerifier;
    PQTCQueryVerifier public immutable queryVerifier;

    mapping(bytes32 => StoredCheckpoint) private checkpoints;

    event VerificationStarted(bytes32 indexed proofId, address indexed consumer, bytes32 indexed statementKey);
    event VerificationCompleted(bytes32 indexed proofId, address indexed consumer, bytes32 indexed statementKey);

    error ZeroAddress();
    error ParameterDisabled();
    error ProofAlreadyStarted();
    error UnknownProof();
    error UnauthorizedConsumer();
    error StatementMismatch();
    error GlobalDataMismatch();
    error InvalidCheckpoint();
    error InvalidTranscript();
    error InvalidGrindingWitness();

    constructor(PQTCAirStageVerifier airVerifier_, PQTCQueryVerifier queryVerifier_, Digest512 memory parameterId_) {
        if (address(airVerifier_) == address(0) || address(queryVerifier_) == address(0)) revert ZeroAddress();
        if (parameterId_.left == bytes32(0) && parameterId_.right == bytes32(0)) revert ParameterDisabled();
        airVerifier = airVerifier_;
        queryVerifier = queryVerifier_;
        parameterLeft = parameterId_.left;
        parameterRight = parameterId_.right;
    }

    function beginVerification(Digest512 calldata parameterId, uint32[64] calldata publicValues, bytes calldata partA)
        external
        returns (bytes32 proofId)
    {
        _requireParameter(parameterId);
        PQTCProofCodec.Common memory common =
            PQTCProofCodec.parseCommon(partA, PQTCProofCodec.PART_A_MAGIC, parameterId, publicValues);
        bytes32 statementKey = PQTCProofCodec.statementKey(parameterId, publicValues);
        uint256 cursor = common.cursor;
        bytes32 suppliedGlobalDigest;
        (suppliedGlobalDigest, cursor) = CanonicalCodec.readBytes32(partA, cursor);
        uint256 globalStart = cursor;
        GlobalData memory globals = _parseGlobalData(partA, cursor);
        cursor = globals.cursor;
        if (cursor - globalStart != GLOBAL_DATA_BYTES || keccak256(partA[globalStart:cursor]) != suppliedGlobalDigest) {
            revert GlobalDataMismatch();
        }
        TranscriptCheckpoint memory parsedCheckpoint = _parseCheckpoint(partA, cursor, statementKey);
        cursor = parsedCheckpoint.cursor;
        if (parsedCheckpoint.globalDigest != suppliedGlobalDigest) revert GlobalDataMismatch();
        _verifyTranscript(parameterId, publicValues, globals, parsedCheckpoint);
        _applyCheckpoint(globals.query, parsedCheckpoint);

        uint256[] memory local = new uint256[](TRACE_WIDTH);
        uint256[] memory next = new uint256[](TRACE_WIDTH);
        for (uint256 i; i < TRACE_WIDTH; ++i) {
            local[i] = globals.traceLocal[i];
            next[i] = globals.traceNext[i];
        }
        uint256 airAccumulator = airVerifier.evaluateRange(
            local, next, publicValues, parsedCheckpoint.zeta, parsedCheckpoint.airAlpha, 0, 0, AIR_SPLIT
        );
        uint256 zetaAggregate;
        uint256 nextAggregate;
        (cursor, zetaAggregate, nextAggregate) = queryVerifier.verifyFirstHalf(partA, cursor, globals.query);
        PQTCProofCodec.requireEnd(partA, cursor, PQTCProofCodec.PART_A_END);

        bytes32 coreProofId = keccak256(abi.encode(bytes32("PQTC.V3.PROOF"), statementKey, keccak256(partA)));
        proofId = keccak256(abi.encode(bytes32("PQTC.V3.VERIFICATION"), coreProofId, msg.sender));
        StoredCheckpoint storage existing = checkpoints[proofId];
        if (existing.consumer != address(0)) {
            if (
                existing.consumer != msg.sender || existing.coreProofId != coreProofId
                    || existing.statementKey != statementKey || existing.checkpointDigest != parsedCheckpoint.digest
                    || existing.globalDigest != suppliedGlobalDigest || existing.airAccumulator != airAccumulator
                    || existing.airCursor != AIR_SPLIT || existing.zetaAggregate != zetaAggregate
                    || existing.nextAggregate != nextAggregate
            ) revert ProofAlreadyStarted();
            emit VerificationStarted(proofId, msg.sender, statementKey);
            return proofId;
        }
        checkpoints[proofId] = StoredCheckpoint(
            msg.sender,
            coreProofId,
            statementKey,
            parsedCheckpoint.digest,
            suppliedGlobalDigest,
            airAccumulator,
            AIR_SPLIT,
            zetaAggregate,
            nextAggregate
        );
        emit VerificationStarted(proofId, msg.sender, statementKey);
    }

    function completeVerification(
        bytes32 proofId,
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata partB
    ) external returns (bool) {
        StoredCheckpoint memory stored = checkpoints[proofId];
        if (stored.consumer == address(0)) revert UnknownProof();
        if (msg.sender != stored.consumer) revert UnauthorizedConsumer();
        _requireParameter(parameterId);
        bytes32 statementKey = PQTCProofCodec.statementKey(parameterId, publicValues);
        if (statementKey != stored.statementKey) revert StatementMismatch();
        PQTCProofCodec.Common memory common =
            PQTCProofCodec.parseCommon(partB, PQTCProofCodec.PART_B_MAGIC, parameterId, publicValues);
        uint256 cursor = common.cursor;
        bytes32 encodedCoreProofId;
        (encodedCoreProofId, cursor) = CanonicalCodec.readBytes32(partB, cursor);
        if (encodedCoreProofId != stored.coreProofId) revert InvalidCheckpoint();
        bytes32 suppliedGlobalDigest;
        (suppliedGlobalDigest, cursor) = CanonicalCodec.readBytes32(partB, cursor);
        if (suppliedGlobalDigest != stored.globalDigest) revert GlobalDataMismatch();
        uint256 globalStart = cursor;
        GlobalData memory globals = _parseGlobalDataPartB(partB, cursor);
        cursor = globals.cursor;
        if (cursor - globalStart != GLOBAL_DATA_BYTES || keccak256(partB[globalStart:cursor]) != suppliedGlobalDigest) {
            revert GlobalDataMismatch();
        }
        TranscriptCheckpoint memory parsedCheckpoint = _parseCheckpoint(partB, cursor, statementKey);
        cursor = parsedCheckpoint.cursor;
        if (
            parsedCheckpoint.digest != stored.checkpointDigest || parsedCheckpoint.globalDigest != suppliedGlobalDigest
                || parsedCheckpoint.globalDigest != stored.globalDigest
        ) revert InvalidCheckpoint();
        _applyCheckpoint(globals.query, parsedCheckpoint);

        uint256[] memory local = new uint256[](TRACE_WIDTH);
        uint256[] memory next = new uint256[](TRACE_WIDTH);
        uint256[] memory quotient = new uint256[](QUOTIENT_EXTENSIONS);
        for (uint256 i; i < TRACE_WIDTH; ++i) {
            local[i] = globals.traceLocal[i];
            next[i] = globals.traceNext[i];
        }
        for (uint256 i; i < QUOTIENT_EXTENSIONS; ++i) {
            quotient[i] = globals.quotient[i];
        }
        if (stored.airCursor != AIR_SPLIT) revert InvalidCheckpoint();
        uint256 airAccumulator = airVerifier.evaluateRange(
            local,
            next,
            publicValues,
            parsedCheckpoint.zeta,
            parsedCheckpoint.airAlpha,
            stored.airAccumulator,
            stored.airCursor,
            7
        );
        airVerifier.requireValid(airAccumulator, quotient, parsedCheckpoint.zeta);

        // Deleting before the expensive verifier call makes re-entry impossible. Any later pool revert
        // reverts this deletion as part of the same transaction.
        delete checkpoints[proofId];
        cursor =
            queryVerifier.verifySecondHalf(partB, cursor, globals.query, stored.zetaAggregate, stored.nextAggregate);
        PQTCProofCodec.requireEnd(partB, cursor, PQTCProofCodec.PART_B_END);
        emit VerificationCompleted(proofId, msg.sender, statementKey);
        return true;
    }

    function checkpoint(bytes32 proofId)
        external
        view
        returns (address consumer, bytes32 statementKey, bytes32 checkpointDigest, bytes32 globalDigest)
    {
        StoredCheckpoint storage value = checkpoints[proofId];
        return (value.consumer, value.statementKey, value.checkpointDigest, value.globalDigest);
    }

    function _parseGlobalData(bytes calldata proof, uint256 cursor) private pure returns (GlobalData memory data) {
        Digest512 memory traceRoot;
        Digest512 memory quotientRoot;
        Digest512 memory randomRoot;
        (traceRoot, cursor) = CanonicalCodec.readDigest(proof, cursor);
        (quotientRoot, cursor) = CanonicalCodec.readDigest(proof, cursor);
        (randomRoot, cursor) = CanonicalCodec.readDigest(proof, cursor);
        data.query.inputRoots[0] = randomRoot;
        data.query.inputRoots[1] = traceRoot;
        data.query.inputRoots[2] = quotientRoot;

        for (uint256 i; i < TRACE_WIDTH; ++i) {
            (data.traceLocal[i], cursor) = _readExtension(proof, cursor);
            data.query.traceLocalAtZeta[i] = data.traceLocal[i];
        }
        for (uint256 i; i < TRACE_WIDTH; ++i) {
            (data.traceNext[i], cursor) = _readExtension(proof, cursor);
            data.query.traceNextAtZeta[i] = data.traceNext[i];
        }
        for (uint256 matrix; matrix < 16; ++matrix) {
            for (uint256 column; column < 4; ++column) {
                uint256 value;
                (value, cursor) = _readExtension(proof, cursor);
                data.quotient[matrix * 4 + column] = value;
                data.query.quotientAtZeta[matrix * 8 + column] = value;
            }
        }
        for (uint256 i; i < 4; ++i) {
            (data.query.randomAtZeta[i], cursor) = _readExtension(proof, cursor);
        }
        for (uint256 i; i < RANDOM_CODEWORDS; ++i) {
            (data.query.randomAtZeta[4 + i], cursor) = _readExtension(proof, cursor);
        }
        for (uint256 point; point < 2; ++point) {
            for (uint256 i; i < RANDOM_CODEWORDS; ++i) {
                uint256 value;
                (value, cursor) = _readExtension(proof, cursor);
                if (point == 0) data.query.traceLocalAtZeta[TRACE_WIDTH + i] = value;
                else data.query.traceNextAtZeta[TRACE_WIDTH + i] = value;
            }
        }
        for (uint256 matrix; matrix < 16; ++matrix) {
            for (uint256 i; i < RANDOM_CODEWORDS; ++i) {
                (data.query.quotientAtZeta[matrix * 8 + 4 + i], cursor) = _readExtension(proof, cursor);
            }
        }
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            (data.query.friRoots[round], cursor) = CanonicalCodec.readDigest(proof, cursor);
        }
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            (data.friWitnesses[round], cursor) = CanonicalCodec.readField(proof, cursor);
        }
        (data.query.finalPolynomial, cursor) = _readExtension(proof, cursor);
        (data.queryWitness, cursor) = CanonicalCodec.readField(proof, cursor);
        data.cursor = cursor;
    }

    function _parseGlobalDataPartB(bytes calldata proof, uint256 cursor) private pure returns (GlobalData memory data) {
        (data.query.inputRoots[1], cursor) = CanonicalCodec.readDigest(proof, cursor);
        (data.query.inputRoots[2], cursor) = CanonicalCodec.readDigest(proof, cursor);
        (data.query.inputRoots[0], cursor) = CanonicalCodec.readDigest(proof, cursor);
        for (uint256 i; i < TRACE_WIDTH; ++i) {
            (data.traceLocal[i], cursor) = _readExtension(proof, cursor);
        }
        for (uint256 i; i < TRACE_WIDTH; ++i) {
            (data.traceNext[i], cursor) = _readExtension(proof, cursor);
        }
        for (uint256 matrix; matrix < 16; ++matrix) {
            for (uint256 column; column < 4; ++column) {
                (data.quotient[matrix * 4 + column], cursor) = _readExtension(proof, cursor);
            }
        }
        uint256 skippedOodBytes = 80 * 16;
        if (cursor > proof.length || skippedOodBytes > proof.length - cursor) revert CanonicalCodec.Truncated();
        cursor += skippedOodBytes;
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            (data.query.friRoots[round], cursor) = CanonicalCodec.readDigest(proof, cursor);
        }
        uint256 skippedWitnessBytes = FRI_ROUNDS * 4;
        if (cursor > proof.length || skippedWitnessBytes > proof.length - cursor) revert CanonicalCodec.Truncated();
        cursor += skippedWitnessBytes;
        (data.query.finalPolynomial, cursor) = _readExtension(proof, cursor);
        (, cursor) = CanonicalCodec.readU32(proof, cursor);
        data.cursor = cursor;
    }

    function _parseCheckpoint(bytes calldata proof, uint256 cursor, bytes32 statementKey)
        private
        pure
        returns (TranscriptCheckpoint memory checkpointValue)
    {
        (checkpointValue.digest, cursor) = CanonicalCodec.readBytes32(proof, cursor);
        uint256 payloadStart = cursor;
        (checkpointValue.globalDigest, cursor) = CanonicalCodec.readBytes32(proof, cursor);
        (checkpointValue.state, cursor) = CanonicalCodec.readDigest(proof, cursor);
        (checkpointValue.airAlpha, cursor) = _readExtension(proof, cursor);
        (checkpointValue.zeta, cursor) = _readExtension(proof, cursor);
        (checkpointValue.friAlpha, cursor) = _readExtension(proof, cursor);
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            (checkpointValue.friBetas[round], cursor) = _readExtension(proof, cursor);
        }
        uint16 totalQueries;
        (totalQueries, cursor) = CanonicalCodec.readU16(proof, cursor);
        if (totalQueries != QUERY_COUNT) revert InvalidCheckpoint();
        for (uint256 i; i < QUERY_COUNT; ++i) {
            (checkpointValue.queryIndices[i], cursor) = CanonicalCodec.readU32(proof, cursor);
            if (checkpointValue.queryIndices[i] >= (uint32(1) << 13)) revert InvalidCheckpoint();
        }
        uint16 uniqueCount;
        (uniqueCount, cursor) = CanonicalCodec.readU16(proof, cursor);
        uint32[32] memory expectedUnique;
        uint256 expectedCount = _unique(checkpointValue.queryIndices, expectedUnique);
        if (uniqueCount != expectedCount) revert InvalidCheckpoint();
        for (uint256 i; i < expectedCount; ++i) {
            uint32 supplied;
            (supplied, cursor) = CanonicalCodec.readU32(proof, cursor);
            if (supplied != expectedUnique[i]) revert InvalidCheckpoint();
        }
        bytes32 expected =
            keccak256(abi.encode(bytes32("PQTC.V3.CHECKPOINT"), statementKey, keccak256(proof[payloadStart:cursor])));
        if (checkpointValue.digest != expected) revert InvalidCheckpoint();
        checkpointValue.cursor = cursor;
    }

    function _verifyTranscript(
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        GlobalData memory globals,
        TranscriptCheckpoint memory checkpointValue
    ) private pure {
        uint32[] memory values = new uint32[](64);
        for (uint256 i; i < 64; ++i) {
            values[i] = publicValues[i];
        }
        Transcript512.State memory transcript = Transcript512.initialize(parameterId, values);
        Transcript512.observeField(transcript, 9);
        Transcript512.observeField(transcript, 8);
        Transcript512.observeField(transcript, 0);
        Transcript512.observeCommitment(transcript, globals.query.inputRoots[1]);
        for (uint256 i; i < 64; ++i) {
            Transcript512.observeField(transcript, publicValues[i]);
        }
        uint256 airAlpha = _sampleExtension(transcript);
        Transcript512.observeCommitment(transcript, globals.query.inputRoots[2]);
        Transcript512.observeCommitment(transcript, globals.query.inputRoots[0]);
        uint256 zeta = _sampleExtension(transcript);
        _observeOod(transcript, globals.query);
        uint256 friAlpha = _sampleExtension(transcript);
        uint256[9] memory betas;
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            Transcript512.observeCommitment(transcript, globals.query.friRoots[round]);
            if (!Transcript512.checkWitness(transcript, 16, globals.friWitnesses[round])) {
                revert InvalidGrindingWitness();
            }
            betas[round] = _sampleExtension(transcript);
        }
        _observeExtension(transcript, globals.query.finalPolynomial);
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            Transcript512.observeField(transcript, 1);
        }
        if (!Transcript512.checkWitness(transcript, 16, globals.queryWitness)) revert InvalidGrindingWitness();
        uint32[32] memory indices;
        for (uint256 i; i < QUERY_COUNT; ++i) {
            indices[i] = uint32(Transcript512.sampleBits(transcript, 13));
        }
        if (
            checkpointValue.state.left != transcript.digest.left
                || checkpointValue.state.right != transcript.digest.right || checkpointValue.airAlpha != airAlpha
                || checkpointValue.zeta != zeta || checkpointValue.friAlpha != friAlpha
        ) revert InvalidTranscript();
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            if (checkpointValue.friBetas[round] != betas[round]) revert InvalidTranscript();
        }
        for (uint256 i; i < QUERY_COUNT; ++i) {
            if (checkpointValue.queryIndices[i] != indices[i]) revert InvalidTranscript();
        }
    }

    function _observeOod(Transcript512.State memory transcript, PQTCQueryVerifier.Context memory context) private pure {
        for (uint256 i; i < 8; ++i) {
            _observeExtension(transcript, context.randomAtZeta[i]);
        }
        for (uint256 i; i < TRACE_WIDTH + RANDOM_CODEWORDS; ++i) {
            _observeExtension(transcript, context.traceLocalAtZeta[i]);
        }
        for (uint256 i; i < TRACE_WIDTH + RANDOM_CODEWORDS; ++i) {
            _observeExtension(transcript, context.traceNextAtZeta[i]);
        }
        for (uint256 matrix; matrix < 16; ++matrix) {
            for (uint256 i; i < 8; ++i) {
                _observeExtension(transcript, context.quotientAtZeta[matrix * 8 + i]);
            }
        }
    }

    function _applyCheckpoint(PQTCQueryVerifier.Context memory context, TranscriptCheckpoint memory checkpointValue)
        private
        pure
    {
        context.zeta = checkpointValue.zeta;
        context.friAlpha = checkpointValue.friAlpha;
        context.friBetas = checkpointValue.friBetas;
        context.queryIndices = checkpointValue.queryIndices;
    }

    function _unique(uint32[32] memory indices, uint32[32] memory unique) private pure returns (uint256 count) {
        for (uint256 i; i < QUERY_COUNT; ++i) {
            uint32 value = indices[i];
            uint256 position;
            while (position < count && unique[position] < value) ++position;
            if (position < count && unique[position] == value) continue;
            for (uint256 move = count; move > position; --move) {
                unique[move] = unique[move - 1];
            }
            unique[position] = value;
            ++count;
        }
    }

    function _sampleExtension(Transcript512.State memory transcript) private pure returns (uint256) {
        uint32[4] memory value = Transcript512.sampleExt4(transcript);
        return Ext.fromCoefficients(value[0], value[1], value[2], value[3]);
    }

    function _observeExtension(Transcript512.State memory transcript, uint256 value) private pure {
        Ext.check(value);
        Transcript512.observeField(transcript, uint32(value));
        Transcript512.observeField(transcript, uint32(value >> 32));
        Transcript512.observeField(transcript, uint32(value >> 64));
        Transcript512.observeField(transcript, uint32(value >> 96));
    }

    function _readExtension(bytes calldata proof, uint256 cursor) private pure returns (uint256 value, uint256 next) {
        if (cursor > proof.length || 16 > proof.length - cursor) revert CanonicalCodec.Truncated();
        assembly ("memory-safe") {
            let word := calldataload(add(proof.offset, cursor))
            let mask := 0xffffffff
            let c0 := shr(224, word)
            let c1 := and(shr(192, word), mask)
            let c2 := and(shr(160, word), mask)
            let c3 := and(shr(128, word), mask)
            if iszero(and(and(lt(c0, 2013265921), lt(c1, 2013265921)), and(lt(c2, 2013265921), lt(c3, 2013265921)))) {
                mstore(0, shl(224, 0x65a81779))
                let badValue := c0
                if and(lt(c0, 2013265921), iszero(lt(c1, 2013265921))) { badValue := c1 }
                if and(and(lt(c0, 2013265921), lt(c1, 2013265921)), iszero(lt(c2, 2013265921))) {
                    badValue := c2
                }
                if and(
                    and(and(lt(c0, 2013265921), lt(c1, 2013265921)), lt(c2, 2013265921)),
                    iszero(lt(c3, 2013265921))
                ) {
                    badValue := c3
                }
                mstore(4, badValue)
                revert(0, 36)
            }
            value := or(or(c0, shl(32, c1)), or(shl(64, c2), shl(96, c3)))
        }
        next = cursor + 16;
    }

    function _requireParameter(Digest512 calldata parameterId) private view {
        if (parameterId.left != parameterLeft || parameterId.right != parameterRight) revert ParameterDisabled();
    }
}
```

</details>

## `contracts/src/libraries/BabyBear.sol`

- Bytes: 1,371
- SHA-256: `0b260468dfdd98e9a837165dbd61a2f908f15bed31e8e7fb285b0c6242ed5d63`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

library BabyBear {
    uint256 internal constant P = 2_013_265_921;

    error NonCanonicalField(uint256 value);
    error DivisionByZero();

    function check(uint256 value) internal pure returns (uint256) {
        if (value >= P) revert NonCanonicalField(value);
        return value;
    }

    function add(uint256 a, uint256 b) internal pure returns (uint256 c) {
        unchecked {
            c = a + b;
            if (c >= P) c -= P;
        }
    }

    function sub(uint256 a, uint256 b) internal pure returns (uint256) {
        unchecked {
            return a >= b ? a - b : a + P - b;
        }
    }

    function neg(uint256 a) internal pure returns (uint256) {
        return a == 0 ? 0 : P - a;
    }

    function mul(uint256 a, uint256 b) internal pure returns (uint256) {
        return mulmod(a, b, P);
    }

    function pow(uint256 base, uint256 exponent) internal pure returns (uint256 result) {
        result = 1;
        while (exponent != 0) {
            if (exponent & 1 != 0) result = mulmod(result, base, P);
            base = mulmod(base, base, P);
            exponent >>= 1;
        }
    }

    function inv(uint256 value) internal pure returns (uint256) {
        if (value == 0) revert DivisionByZero();
        return pow(value, P - 2);
    }
}
```

</details>

## `contracts/src/libraries/BabyBearExt4.sol`

- Bytes: 4,288
- SHA-256: `fa3063d15f60b4fde8570b23228a9d05fd90221fb40d3ba5b0eb153412da0e3f`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBear} from "./BabyBear.sol";

struct BabyBearExt4Value {
    uint256 c0;
    uint256 c1;
    uint256 c2;
    uint256 c3;
}

library BabyBearExt4 {
    uint256 internal constant NONRESIDUE = 11;

    function check(BabyBearExt4Value memory a) internal pure returns (BabyBearExt4Value memory) {
        BabyBear.check(a.c0);
        BabyBear.check(a.c1);
        BabyBear.check(a.c2);
        BabyBear.check(a.c3);
        return a;
    }

    function add(BabyBearExt4Value memory a, BabyBearExt4Value memory b)
        internal
        pure
        returns (BabyBearExt4Value memory)
    {
        return BabyBearExt4Value({
            c0: BabyBear.add(a.c0, b.c0),
            c1: BabyBear.add(a.c1, b.c1),
            c2: BabyBear.add(a.c2, b.c2),
            c3: BabyBear.add(a.c3, b.c3)
        });
    }

    function sub(BabyBearExt4Value memory a, BabyBearExt4Value memory b)
        internal
        pure
        returns (BabyBearExt4Value memory)
    {
        return BabyBearExt4Value({
            c0: BabyBear.sub(a.c0, b.c0),
            c1: BabyBear.sub(a.c1, b.c1),
            c2: BabyBear.sub(a.c2, b.c2),
            c3: BabyBear.sub(a.c3, b.c3)
        });
    }

    function mul(BabyBearExt4Value memory a, BabyBearExt4Value memory b)
        internal
        pure
        returns (BabyBearExt4Value memory r)
    {
        uint256 t0 = BabyBear.mul(a.c0, b.c0);
        uint256 t1 = BabyBear.add(BabyBear.mul(a.c0, b.c1), BabyBear.mul(a.c1, b.c0));
        uint256 t2 =
            BabyBear.add(BabyBear.add(BabyBear.mul(a.c0, b.c2), BabyBear.mul(a.c1, b.c1)), BabyBear.mul(a.c2, b.c0));
        uint256 t3 = BabyBear.add(
            BabyBear.add(BabyBear.add(BabyBear.mul(a.c0, b.c3), BabyBear.mul(a.c1, b.c2)), BabyBear.mul(a.c2, b.c1)),
            BabyBear.mul(a.c3, b.c0)
        );
        uint256 t4 =
            BabyBear.add(BabyBear.add(BabyBear.mul(a.c1, b.c3), BabyBear.mul(a.c2, b.c2)), BabyBear.mul(a.c3, b.c1));
        uint256 t5 = BabyBear.add(BabyBear.mul(a.c2, b.c3), BabyBear.mul(a.c3, b.c2));
        uint256 t6 = BabyBear.mul(a.c3, b.c3);
        r.c0 = BabyBear.add(t0, BabyBear.mul(NONRESIDUE, t4));
        r.c1 = BabyBear.add(t1, BabyBear.mul(NONRESIDUE, t5));
        r.c2 = BabyBear.add(t2, BabyBear.mul(NONRESIDUE, t6));
        r.c3 = t3;
    }

    function mulBase(BabyBearExt4Value memory a, uint256 b) internal pure returns (BabyBearExt4Value memory) {
        return BabyBearExt4Value({
            c0: BabyBear.mul(a.c0, b), c1: BabyBear.mul(a.c1, b), c2: BabyBear.mul(a.c2, b), c3: BabyBear.mul(a.c3, b)
        });
    }

    function fromBase(uint256 value) internal pure returns (BabyBearExt4Value memory) {
        return BabyBearExt4Value(BabyBear.check(value), 0, 0, 0);
    }

    function neg(BabyBearExt4Value memory a) internal pure returns (BabyBearExt4Value memory) {
        return BabyBearExt4Value(BabyBear.neg(a.c0), BabyBear.neg(a.c1), BabyBear.neg(a.c2), BabyBear.neg(a.c3));
    }

    function pow(BabyBearExt4Value memory base, uint256 exponentLow, uint256 exponentHigh)
        internal
        pure
        returns (BabyBearExt4Value memory result)
    {
        result = fromBase(1);
        while (exponentLow != 0 || exponentHigh != 0) {
            if (exponentLow & 1 != 0) result = mul(result, base);
            base = mul(base, base);
            exponentLow = (exponentLow >> 1) | (exponentHigh << 255);
            exponentHigh >>= 1;
        }
    }

    /// Inverse by exponentiation to p^4 - 2. The exponent is encoded as a
    /// little-endian 256-bit low limb and high limb.
    function inv(BabyBearExt4Value memory value) internal pure returns (BabyBearExt4Value memory) {
        check(value);
        if (value.c0 == 0 && value.c1 == 0 && value.c2 == 0 && value.c3 == 0) {
            revert BabyBear.DivisionByZero();
        }
        // (2_013_265_921^4 - 2), split into 256-bit limbs. The high limb is zero.
        return pow(value, 16_428_751_811_598_850_197_311_699_254_593_454_079, 0);
    }

    function equal(BabyBearExt4Value memory a, BabyBearExt4Value memory b) internal pure returns (bool) {
        return a.c0 == b.c0 && a.c1 == b.c1 && a.c2 == b.c2 && a.c3 == b.c3;
    }
}
```

</details>

## `contracts/src/libraries/BabyBearExt4Packed.sol`

- Bytes: 5,418
- SHA-256: `84440d8861592ac49c70600ea99ad3978a92e2cae55dfadc5720850bf3b0d874`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBear} from "./BabyBear.sol";

/// Degree-four BabyBear extension packed as four 32-bit little-endian lanes.
/// The unused high 128 bits must be zero. Arithmetic output is always canonical.
library BabyBearExt4Packed {
    uint256 private constant MASK = type(uint32).max;
    uint256 private constant NONRESIDUE = 11;

    error NonCanonicalExtension();

    function fromCoefficients(uint256 coefficient0, uint256 coefficient1, uint256 coefficient2, uint256 coefficient3)
        internal
        pure
        returns (uint256)
    {
        BabyBear.check(coefficient0);
        BabyBear.check(coefficient1);
        BabyBear.check(coefficient2);
        BabyBear.check(coefficient3);
        return _pack(coefficient0, coefficient1, coefficient2, coefficient3);
    }

    function check(uint256 a) internal pure returns (uint256) {
        if (a >> 128 != 0) revert NonCanonicalExtension();
        BabyBear.check(c0(a));
        BabyBear.check(c1(a));
        BabyBear.check(c2(a));
        BabyBear.check(c3(a));
        return a;
    }

    function c0(uint256 a) internal pure returns (uint256) {
        return a & MASK;
    }

    function c1(uint256 a) internal pure returns (uint256) {
        return (a >> 32) & MASK;
    }

    function c2(uint256 a) internal pure returns (uint256) {
        return (a >> 64) & MASK;
    }

    function c3(uint256 a) internal pure returns (uint256) {
        return (a >> 96) & MASK;
    }

    function fromBase(uint256 value) internal pure returns (uint256) {
        return BabyBear.check(value);
    }

    function add(uint256 a, uint256 b) internal pure returns (uint256 result) {
        assembly ("memory-safe") {
            let p := 2013265921
            let mask := 0xffffffff
            let r0 := addmod(and(a, mask), and(b, mask), p)
            let r1 := addmod(and(shr(32, a), mask), and(shr(32, b), mask), p)
            let r2 := addmod(and(shr(64, a), mask), and(shr(64, b), mask), p)
            let r3 := addmod(and(shr(96, a), mask), and(shr(96, b), mask), p)
            result := or(or(r0, shl(32, r1)), or(shl(64, r2), shl(96, r3)))
        }
    }

    function sub(uint256 a, uint256 b) internal pure returns (uint256 result) {
        assembly ("memory-safe") {
            let p := 2013265921
            let mask := 0xffffffff
            let r0 := addmod(and(a, mask), sub(p, and(b, mask)), p)
            let r1 := addmod(and(shr(32, a), mask), sub(p, and(shr(32, b), mask)), p)
            let r2 := addmod(and(shr(64, a), mask), sub(p, and(shr(64, b), mask)), p)
            let r3 := addmod(and(shr(96, a), mask), sub(p, and(shr(96, b), mask)), p)
            result := or(or(r0, shl(32, r1)), or(shl(64, r2), shl(96, r3)))
        }
    }

    function mulBase(uint256 a, uint256 b) internal pure returns (uint256 result) {
        assembly ("memory-safe") {
            let p := 2013265921
            let mask := 0xffffffff
            let r0 := mulmod(and(a, mask), b, p)
            let r1 := mulmod(and(shr(32, a), mask), b, p)
            let r2 := mulmod(and(shr(64, a), mask), b, p)
            let r3 := mulmod(and(shr(96, a), mask), b, p)
            result := or(or(r0, shl(32, r1)), or(shl(64, r2), shl(96, r3)))
        }
    }

    function mul(uint256 a, uint256 b) internal pure returns (uint256 result) {
        assembly ("memory-safe") {
            let p := 2013265921
            let mask := 0xffffffff
            let a0 := and(a, mask)
            let a1 := and(shr(32, a), mask)
            let a2 := and(shr(64, a), mask)
            let a3 := and(shr(96, a), mask)
            let b0 := and(b, mask)
            let b1 := and(shr(32, b), mask)
            let b2 := and(shr(64, b), mask)
            let b3 := and(shr(96, b), mask)

            let t4 := addmod(addmod(mulmod(a1, b3, p), mulmod(a2, b2, p), p), mulmod(a3, b1, p), p)
            let t5 := addmod(mulmod(a2, b3, p), mulmod(a3, b2, p), p)
            let r0 := addmod(mulmod(a0, b0, p), mulmod(11, t4, p), p)
            let r1 := addmod(addmod(mulmod(a0, b1, p), mulmod(a1, b0, p), p), mulmod(11, t5, p), p)
            let r2 :=
                addmod(
                    addmod(addmod(mulmod(a0, b2, p), mulmod(a1, b1, p), p), mulmod(a2, b0, p), p),
                    mulmod(11, mulmod(a3, b3, p), p),
                    p
                )
            let r3 :=
                addmod(
                    addmod(addmod(mulmod(a0, b3, p), mulmod(a1, b2, p), p), mulmod(a2, b1, p), p),
                    mulmod(a3, b0, p),
                    p
                )
            result := or(or(r0, shl(32, r1)), or(shl(64, r2), shl(96, r3)))
        }
    }

    function pow(uint256 base, uint256 exponent) internal pure returns (uint256 result) {
        result = 1;
        while (exponent != 0) {
            if (exponent & 1 != 0) result = mul(result, base);
            base = mul(base, base);
            exponent >>= 1;
        }
    }

    function _pack(uint256 a0, uint256 a1, uint256 a2, uint256 a3) private pure returns (uint256) {
        return a0 | (a1 << 32) | (a2 << 64) | (a3 << 96);
    }

    function inv(uint256 value) internal pure returns (uint256) {
        check(value);
        if (value == 0) revert BabyBear.DivisionByZero();
        return pow(value, 16_428_751_811_598_850_197_311_699_254_593_454_079);
    }
}
```

</details>

## `contracts/src/libraries/CanonicalCodec.sol`

- Bytes: 2,864
- SHA-256: `d5b52d20c25e1e88079016993877e588c15c020a3c19f7c9f7437ea938926929`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Digest512} from "./Digest512.sol";

library CanonicalCodec {
    uint32 internal constant BABY_BEAR_MODULUS = 2_013_265_921;

    error Truncated();
    error NonCanonicalField(uint32 value);
    error CountMismatch(uint256 expected, uint256 actual);
    error TrailingBytes();

    function readU8(bytes calldata data, uint256 cursor) internal pure returns (uint8 value, uint256 next) {
        _requireAvailable(data, cursor, 1);
        return (uint8(data[cursor]), cursor + 1);
    }

    function readU16(bytes calldata data, uint256 cursor) internal pure returns (uint16 value, uint256 next) {
        _requireAvailable(data, cursor, 2);
        assembly ("memory-safe") { value := shr(240, calldataload(add(data.offset, cursor))) }
        return (value, cursor + 2);
    }

    function readU32(bytes calldata data, uint256 cursor) internal pure returns (uint32 value, uint256 next) {
        _requireAvailable(data, cursor, 4);
        assembly ("memory-safe") { value := shr(224, calldataload(add(data.offset, cursor))) }
        return (value, cursor + 4);
    }

    function readU64(bytes calldata data, uint256 cursor) internal pure returns (uint64 value, uint256 next) {
        _requireAvailable(data, cursor, 8);
        assembly ("memory-safe") { value := shr(192, calldataload(add(data.offset, cursor))) }
        return (value, cursor + 8);
    }

    function readBytes32(bytes calldata data, uint256 cursor) internal pure returns (bytes32 value, uint256 next) {
        _requireAvailable(data, cursor, 32);
        assembly ("memory-safe") { value := calldataload(add(data.offset, cursor)) }
        return (value, cursor + 32);
    }

    function readDigest(bytes calldata data, uint256 cursor)
        internal
        pure
        returns (Digest512 memory value, uint256 next)
    {
        (value.left, cursor) = readBytes32(data, cursor);
        (value.right, next) = readBytes32(data, cursor);
    }

    function readField(bytes calldata data, uint256 cursor) internal pure returns (uint32 value, uint256 next) {
        (value, next) = readU32(data, cursor);
        if (value >= BABY_BEAR_MODULUS) revert NonCanonicalField(value);
    }

    function readCount(bytes calldata data, uint256 cursor, uint256 expected) internal pure returns (uint256 next) {
        uint32 actual;
        (actual, next) = readU32(data, cursor);
        if (actual != expected) revert CountMismatch(expected, actual);
    }

    function requireEnd(bytes calldata data, uint256 cursor) internal pure {
        if (cursor != data.length) revert TrailingBytes();
    }

    function _requireAvailable(bytes calldata data, uint256 cursor, uint256 length) private pure {
        if (cursor > data.length || length > data.length - cursor) revert Truncated();
    }
}
```

</details>

## `contracts/src/libraries/Digest512.sol`

- Bytes: 618
- SHA-256: `be41fb4d1d6ba6c2cd44ca3fe9d0b8515c4ca6a156b05342b9678a3e97cc9f75`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

struct Digest512 {
    bytes32 left;
    bytes32 right;
}

library Digest512Lib {
    function isZero(Digest512 memory value) internal pure returns (bool) {
        return value.left == bytes32(0) && value.right == bytes32(0);
    }

    function equal(Digest512 memory a, Digest512 memory b) internal pure returns (bool) {
        return a.left == b.left && a.right == b.right;
    }

    function key(Digest512 memory value) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(value.left, value.right));
    }
}
```

</details>

## `contracts/src/libraries/KeccakPair512.sol`

- Bytes: 1,214
- SHA-256: `2f526fcf9c2fd2ef889938260df6585392d90f6217c0abbcae38cd257090a7d8`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Digest512} from "./Digest512.sol";

library KeccakPair512 {
    function hash(uint8 tag, bytes memory payload) internal pure returns (Digest512 memory digest) {
        assembly ("memory-safe") {
            let savedLength := mload(payload)
            let start := add(payload, 0x1e)
            mstore8(start, 0)
            mstore8(add(start, 1), tag)
            mstore(digest, keccak256(start, add(savedLength, 2)))
            mstore8(start, 1)
            mstore(add(digest, 0x20), keccak256(start, add(savedLength, 2)))
            mstore(payload, savedLength)
        }
    }

    function hashCalldata(uint8 tag, bytes calldata payload) internal pure returns (Digest512 memory digest) {
        bytes memory message = new bytes(payload.length + 2);
        message[1] = bytes1(tag);
        assembly ("memory-safe") {
            calldatacopy(add(message, 0x22), payload.offset, payload.length)
            mstore(digest, keccak256(add(message, 0x20), mload(message)))
            mstore8(add(message, 0x20), 1)
            mstore(add(digest, 0x20), keccak256(add(message, 0x20), mload(message)))
        }
    }
}
```

</details>

## `contracts/src/libraries/P2BB512.sol`

- Bytes: 21,406
- SHA-256: `eac664c088b7acacd0401dc1714afaa3a7e6459a71b93b330f6c321c70139534`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Digest512} from "./Digest512.sol";

/// @notice P2BB512-v1: the pinned Plonky3 BabyBear Poseidon2 permutation and
/// a width-16, rate-4 application sponge.
library P2BB512 {
    uint256 internal constant P = 2_013_265_921;
    uint256 internal constant VERSION = 1;
    uint8 internal constant MERKLE_NODE_DOMAIN = 0x20;

    error NonCanonicalFieldElement(uint256 index, uint256 value);
    error NonCanonicalDigestLimb(uint256 index, uint256 value);

    // Plonky3 0.6.0, commit 3152b14a89067c83775a8076cc262ffc48a1fd7c.
    // Each word contains eight consecutive, big-endian u32 round constants.
    uint256 private constant EXTERNAL_0A = 0x69cbb6af46ad93f960a00f4e6b1297cd23189afe732e7bef72c246de2c941900;
    uint256 private constant EXTERNAL_0B = 0x0557eede1580496f3a3ea77b54f3f2710f49b02947872fe1221e2e361ab7202e;
    uint256 private constant EXTERNAL_1A = 0x487779a63851c9d838dc17c0209f8849268dcee8350c48da5b9ad32e0523272b;
    uint256 private constant EXTERNAL_1B = 0x3f89055b01e894b213ddedde1b2ef3347507d8b46ceeb94e52eb6ba250642905;
    uint256 private constant EXTERNAL_2A = 0x05453f3f06349efc6922787c04bfff9c768c714a3e9ff21a15737c9c2229c807;
    uint256 private constant EXTERNAL_2B = 0x0d47f88c097e0ecc27eadba02d7d29e43502aaa00f475fd729fbda49018afffd;
    uint256 private constant EXTERNAL_3A = 0x0315b6186d4497d11b171d9e52861abd2e5d05013ec8646c6e5f250a148ae8e6;
    uint256 private constant EXTERNAL_3B = 0x17f5fa4a3e66d2840051aa3b483f79132cfe5f15023427ca2cc783151e36ea47;
    uint256 private constant EXTERNAL_4A = 0x7290a80d6f7e5329598ec8a876a859a06559e868657b83af13271d3f1f876063;
    uint256 private constant EXTERNAL_4B = 0x0aeeae37706e9ca646400cee72a05c262c589c9e20bd37a76a2d3d1020523767;
    uint256 private constant EXTERNAL_5A = 0x5b8fe9c42aa501d61e01ac3e1448bc545ce5ad1c4918a14d2c46a83f4fcf6876;
    uint256 private constant EXTERNAL_5B = 0x61d8d5c86ddf4ff911fda4d302933a8f170eaf815a9c314f49a1259035ec52a1;
    uint256 private constant EXTERNAL_6A = 0x58eb16115e481e65367125c90eba33ba1fc28ded066399ad0cbec0ea75fd1af0;
    uint256 private constant EXTERNAL_6B = 0x50f5bf4e643d5f416f4fe7185b3cbbde1e3afb3e296fb02745e1547b4a8db2ab;
    uint256 private constant EXTERNAL_7A = 0x59986d1930bcdfa31db639321d7c282453b336810673b747038a98a32c5bce60;
    uint256 private constant EXTERNAL_7B = 0x351979cd5008fb73547bca78711af4813f93bf64644d987b3c8bcd87608758b8;

    uint256 private constant INTERNAL_A = 0x5a8053c0693be6393858867d19334f6b128f0fd84e2b1ccb61210ce03c318939;
    uint256 private constant INTERNAL_B = 0x0b5b2f222edb11d5213effdf0cac4606241af16d000000000000000000000000;

    /// @notice Applies default_babybear_poseidon2_16() to one canonical state.
    function permute(uint32[16] memory state) internal pure returns (uint32[16] memory result) {
        uint256[16] memory wide;
        for (uint256 i = 0; i < 16; ++i) {
            if (state[i] >= P) revert NonCanonicalFieldElement(i, state[i]);
            wide[i] = state[i];
        }
        _permute(wide);
        for (uint256 i = 0; i < 16; ++i) {
            result[i] = uint32(wide[i]);
        }
    }

    /// @notice Decodes sixteen big-endian u32 limbs and rejects noncanonical limbs.
    function toFields(Digest512 memory digest) internal pure returns (uint32[16] memory fields) {
        uint256 left = uint256(digest.left);
        uint256 right = uint256(digest.right);
        for (uint256 i = 0; i < 8; ++i) {
            uint32 value = uint32(left >> (224 - 32 * i));
            if (value >= P) revert NonCanonicalDigestLimb(i, value);
            fields[i] = value;
        }
        for (uint256 i = 0; i < 8; ++i) {
            uint32 value = uint32(right >> (224 - 32 * i));
            if (value >= P) revert NonCanonicalDigestLimb(i + 8, value);
            fields[i + 8] = value;
        }
    }

    /// @notice Encodes sixteen canonical BabyBear elements as big-endian u32 limbs.
    function fromFields(uint32[16] memory fields) internal pure returns (Digest512 memory digest) {
        uint256 left;
        uint256 right;
        for (uint256 i = 0; i < 8; ++i) {
            if (fields[i] >= P) revert NonCanonicalFieldElement(i, fields[i]);
            left |= uint256(fields[i]) << (224 - 32 * i);
        }
        for (uint256 i = 0; i < 8; ++i) {
            if (fields[i + 8] >= P) revert NonCanonicalFieldElement(i + 8, fields[i + 8]);
            right |= uint256(fields[i + 8]) << (224 - 32 * i);
        }
        digest = Digest512(bytes32(left), bytes32(right));
    }

    function hashEmpty(uint8 domainTag) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 0, 0, 0);
        _absorb(state, 0, 0, 0, 0);
        return _squeeze(state);
    }

    function hashFields16(uint8 domainTag, uint32[16] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 64, 16, 0);
        for (uint256 blockIndex = 0; blockIndex < 4; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _check4(elements, offset);
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashFields32(uint8 domainTag, uint32[32] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 128, 32, 0);
        for (uint256 blockIndex = 0; blockIndex < 8; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _check4(elements, offset);
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashFields48(uint8 domainTag, uint32[48] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 192, 48, 0);
        for (uint256 blockIndex = 0; blockIndex < 12; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _check4(elements, offset);
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashFields64(uint8 domainTag, uint32[64] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 256, 64, 0);
        for (uint256 blockIndex = 0; blockIndex < 16; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _check4(elements, offset);
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashU16s16(uint8 domainTag, uint16[16] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 32, 16, 0);
        for (uint256 blockIndex = 0; blockIndex < 4; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashU16s32(uint8 domainTag, uint16[32] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 64, 32, 0);
        for (uint256 blockIndex = 0; blockIndex < 8; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashU16s36(uint8 domainTag, uint16[36] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 72, 36, 0);
        for (uint256 blockIndex = 0; blockIndex < 9; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    /// @dev The 65th u16 stores an odd final byte in its high byte; its low byte must be zero.
    function hashU16s65Odd(uint8 domainTag, uint16[65] memory elements) internal pure returns (Digest512 memory) {
        if (elements[64] & 0xff != 0) revert NonCanonicalFieldElement(64, elements[64]);
        uint256[16] memory state = _initialState(domainTag, 129, 65, 0);
        for (uint256 blockIndex = 0; blockIndex < 16; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        _absorb(state, elements[64], 0, 0, 0);
        return _squeeze(state);
    }

    /// @notice Hashes left || right with the tree level bound in capacity aux.
    function merkleNode(uint8 level, Digest512 memory left, Digest512 memory right)
        internal
        pure
        returns (Digest512 memory)
    {
        uint256[16] memory state = _initialState(MERKLE_NODE_DOMAIN, 128, 32, level);
        _absorbDigest(state, left);
        _absorbDigest(state, right);
        return _squeeze(state);
    }

    function _initialState(uint8 domainTag, uint256 payloadByteLength, uint256 payloadElementCount, uint256 aux)
        private
        pure
        returns (uint256[16] memory state)
    {
        state[4] = VERSION;
        state[5] = domainTag;
        state[6] = payloadByteLength;
        state[7] = payloadElementCount;
        state[8] = aux;
    }

    function _absorb(uint256[16] memory state, uint256 a, uint256 b, uint256 c, uint256 d) private pure {
        state[0] = addmod(state[0], a, P);
        state[1] = addmod(state[1], b, P);
        state[2] = addmod(state[2], c, P);
        state[3] = addmod(state[3], d, P);
        _permute(state);
    }

    function _absorbDigest(uint256[16] memory state, Digest512 memory digest) private pure {
        _absorbPacked128(state, uint256(digest.left) >> 128, 0);
        _absorbPacked128(state, uint128(uint256(digest.left)), 4);
        _absorbPacked128(state, uint256(digest.right) >> 128, 8);
        _absorbPacked128(state, uint128(uint256(digest.right)), 12);
    }

    function _absorbPacked128(uint256[16] memory state, uint256 packed, uint256 index) private pure {
        uint256 a = uint32(packed >> 96);
        uint256 b = uint32(packed >> 64);
        uint256 c = uint32(packed >> 32);
        uint256 d = uint32(packed);
        if (a >= P) revert NonCanonicalDigestLimb(index, a);
        if (b >= P) revert NonCanonicalDigestLimb(index + 1, b);
        if (c >= P) revert NonCanonicalDigestLimb(index + 2, c);
        if (d >= P) revert NonCanonicalDigestLimb(index + 3, d);
        _absorb(state, a, b, c, d);
    }

    function _squeeze(uint256[16] memory state) private pure returns (Digest512 memory digest) {
        uint256 left = _rateWord(state) << 128;
        _permute(state);
        left |= _rateWord(state);
        _permute(state);
        uint256 right = _rateWord(state) << 128;
        _permute(state);
        right |= _rateWord(state);
        digest = Digest512(bytes32(left), bytes32(right));
    }

    function _rateWord(uint256[16] memory state) private pure returns (uint256 word) {
        assembly ("memory-safe") {
            word := or(
                or(shl(96, mload(state)), shl(64, mload(add(state, 32)))),
                or(shl(32, mload(add(state, 64))), mload(add(state, 96)))
            )
        }
    }

    function _permute(uint256[16] memory state) private pure {
        assembly ("memory-safe") {
            function sbox(x) -> y {
                let square := mulmod(x, x, 2013265921)
                let fourth := mulmod(square, square, 2013265921)
                y := mulmod(mulmod(fourth, square, 2013265921), x, 2013265921)
            }

            function externalLinear(s) {
                for { let offset := 0 } lt(offset, 512) { offset := add(offset, 128) } {
                    let x0 := mload(add(s, offset))
                    let x1 := mload(add(add(s, offset), 32))
                    let x2 := mload(add(add(s, offset), 64))
                    let x3 := mload(add(add(s, offset), 96))
                    // Every input is below P, so these unreduced sums are below 7P
                    // and cannot overflow a word. Reducing only the four outputs is
                    // equivalent to the M4 transform but avoids intermediate ADDMODs.
                    let total := add(add(x0, x1), add(x2, x3))
                    mstore(add(s, offset), mod(add(add(total, x0), add(x1, x1)), 2013265921))
                    mstore(add(add(s, offset), 32), mod(add(add(total, x1), add(x2, x2)), 2013265921))
                    mstore(add(add(s, offset), 64), mod(add(add(total, x2), add(x3, x3)), 2013265921))
                    mstore(add(add(s, offset), 96), mod(add(add(total, x3), add(x0, x0)), 2013265921))
                }

                // Four canonical terms sum to less than 4P.
                let sum0 :=
                    mod(add(add(mload(s), mload(add(s, 128))), add(mload(add(s, 256)), mload(add(s, 384)))), 2013265921)
                let sum1 :=
                    mod(
                        add(add(mload(add(s, 32)), mload(add(s, 160))), add(mload(add(s, 288)), mload(add(s, 416)))),
                        2013265921
                    )
                let sum2 :=
                    mod(
                        add(add(mload(add(s, 64)), mload(add(s, 192))), add(mload(add(s, 320)), mload(add(s, 448)))),
                        2013265921
                    )
                let sum3 :=
                    mod(
                        add(add(mload(add(s, 96)), mload(add(s, 224))), add(mload(add(s, 352)), mload(add(s, 480)))),
                        2013265921
                    )
                for { let offset := 0 } lt(offset, 512) { offset := add(offset, 128) } {
                    mstore(add(s, offset), addmod(mload(add(s, offset)), sum0, 2013265921))
                    mstore(add(add(s, offset), 32), addmod(mload(add(add(s, offset), 32)), sum1, 2013265921))
                    mstore(add(add(s, offset), 64), addmod(mload(add(add(s, offset), 64)), sum2, 2013265921))
                    mstore(add(add(s, offset), 96), addmod(mload(add(add(s, offset), 96)), sum3, 2013265921))
                }
            }

            function externalRound(s, first, second) {
                for { let i := 0 } lt(i, 8) { i := add(i, 1) } {
                    let shift := sub(224, mul(i, 32))
                    let offset := mul(i, 32)
                    mstore(
                        add(s, offset),
                        sbox(addmod(mload(add(s, offset)), and(shr(shift, first), 0xffffffff), 2013265921))
                    )
                    offset := add(offset, 256)
                    mstore(
                        add(s, offset),
                        sbox(addmod(mload(add(s, offset)), and(shr(shift, second), 0xffffffff), 2013265921))
                    )
                }
                externalLinear(s)
            }

            function internalLinear(s) {
                let partSum := 0
                for { let offset := 32 } lt(offset, 512) { offset := add(offset, 32) } {
                    partSum := add(partSum, mload(add(s, offset)))
                }
                // Fifteen canonical terms sum to less than 15P.
                partSum := mod(partSum, 2013265921)
                let x0 := mload(s)
                let sum := mod(add(partSum, x0), 2013265921)
                mstore(s, mod(add(partSum, sub(2013265921, x0)), 2013265921))
                mstore(add(s, 32), mod(add(sum, mload(add(s, 32))), 2013265921))
                mstore(add(s, 64), mod(add(add(sum, mload(add(s, 64))), mload(add(s, 64))), 2013265921))
                // Each product below is less than P^2, and adding sum remains
                // below 2^62, so ordinary multiplication cannot overflow.
                mstore(add(s, 96), mod(add(sum, mul(mload(add(s, 96)), 1006632961)), 2013265921))
                mstore(add(s, 128), mod(add(sum, mul(mload(add(s, 128)), 3)), 2013265921))
                mstore(add(s, 160), mod(add(sum, mul(mload(add(s, 160)), 4)), 2013265921))
                mstore(add(s, 192), mod(add(sum, mul(mload(add(s, 192)), 1006632960)), 2013265921))
                mstore(add(s, 224), mod(add(sum, mul(mload(add(s, 224)), 2013265918)), 2013265921))
                mstore(add(s, 256), mod(add(sum, mul(mload(add(s, 256)), 2013265917)), 2013265921))
                mstore(add(s, 288), mod(add(sum, mul(mload(add(s, 288)), 2005401601)), 2013265921))
                mstore(add(s, 320), mod(add(sum, mul(mload(add(s, 320)), 1509949441)), 2013265921))
                mstore(add(s, 352), mod(add(sum, mul(mload(add(s, 352)), 1761607681)), 2013265921))
                mstore(add(s, 384), mod(add(sum, mul(mload(add(s, 384)), 2013265906)), 2013265921))
                mstore(add(s, 416), mod(add(sum, mul(mload(add(s, 416)), 7864320)), 2013265921))
                mstore(add(s, 448), mod(add(sum, mul(mload(add(s, 448)), 125829120)), 2013265921))
                mstore(add(s, 480), mod(add(sum, mul(mload(add(s, 480)), 15)), 2013265921))
            }

            externalLinear(state)
            externalRound(
                state,
                0x69cbb6af46ad93f960a00f4e6b1297cd23189afe732e7bef72c246de2c941900,
                0x0557eede1580496f3a3ea77b54f3f2710f49b02947872fe1221e2e361ab7202e
            )
            externalRound(
                state,
                0x487779a63851c9d838dc17c0209f8849268dcee8350c48da5b9ad32e0523272b,
                0x3f89055b01e894b213ddedde1b2ef3347507d8b46ceeb94e52eb6ba250642905
            )
            externalRound(
                state,
                0x05453f3f06349efc6922787c04bfff9c768c714a3e9ff21a15737c9c2229c807,
                0x0d47f88c097e0ecc27eadba02d7d29e43502aaa00f475fd729fbda49018afffd
            )
            externalRound(
                state,
                0x0315b6186d4497d11b171d9e52861abd2e5d05013ec8646c6e5f250a148ae8e6,
                0x17f5fa4a3e66d2840051aa3b483f79132cfe5f15023427ca2cc783151e36ea47
            )

            for { let round := 0 } lt(round, 13) { round := add(round, 1) } {
                let constantValue
                switch lt(round, 8)
                case 1 {
                    constantValue := and(
                        shr(
                            sub(224, mul(round, 32)),
                            0x5a8053c0693be6393858867d19334f6b128f0fd84e2b1ccb61210ce03c318939
                        ),
                        0xffffffff
                    )
                }
                default {
                    constantValue := and(
                        shr(
                            sub(224, mul(sub(round, 8), 32)),
                            0x0b5b2f222edb11d5213effdf0cac4606241af16d000000000000000000000000
                        ),
                        0xffffffff
                    )
                }
                mstore(state, sbox(addmod(mload(state), constantValue, 2013265921)))
                internalLinear(state)
            }

            externalRound(
                state,
                0x7290a80d6f7e5329598ec8a876a859a06559e868657b83af13271d3f1f876063,
                0x0aeeae37706e9ca646400cee72a05c262c589c9e20bd37a76a2d3d1020523767
            )
            externalRound(
                state,
                0x5b8fe9c42aa501d61e01ac3e1448bc545ce5ad1c4918a14d2c46a83f4fcf6876,
                0x61d8d5c86ddf4ff911fda4d302933a8f170eaf815a9c314f49a1259035ec52a1
            )
            externalRound(
                state,
                0x58eb16115e481e65367125c90eba33ba1fc28ded066399ad0cbec0ea75fd1af0,
                0x50f5bf4e643d5f416f4fe7185b3cbbde1e3afb3e296fb02745e1547b4a8db2ab
            )
            externalRound(
                state,
                0x59986d1930bcdfa31db639321d7c282453b336810673b747038a98a32c5bce60,
                0x351979cd5008fb73547bca78711af4813f93bf64644d987b3c8bcd87608758b8
            )
        }
    }

    function _check4(uint32[16] memory elements, uint256 offset) private pure {
        for (uint256 i = 0; i < 4; ++i) {
            uint256 value = elements[offset + i];
            if (value >= P) revert NonCanonicalFieldElement(offset + i, value);
        }
    }

    function _check4(uint32[32] memory elements, uint256 offset) private pure {
        for (uint256 i = 0; i < 4; ++i) {
            uint256 value = elements[offset + i];
            if (value >= P) revert NonCanonicalFieldElement(offset + i, value);
        }
    }

    function _check4(uint32[48] memory elements, uint256 offset) private pure {
        for (uint256 i = 0; i < 4; ++i) {
            uint256 value = elements[offset + i];
            if (value >= P) revert NonCanonicalFieldElement(offset + i, value);
        }
    }

    function _check4(uint32[64] memory elements, uint256 offset) private pure {
        for (uint256 i = 0; i < 4; ++i) {
            uint256 value = elements[offset + i];
            if (value >= P) revert NonCanonicalFieldElement(offset + i, value);
        }
    }
}
```

</details>

## `contracts/src/libraries/PQTCApplicationHash.sol`

- Bytes: 7,317
- SHA-256: `add9a5b6a21f32216b9f87a64abd24c49710405d7a3f59f5d918824e2713fe5d`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {PQTCDomains} from "../PQTCDomains.sol";
import {Digest512} from "./Digest512.sol";
import {P2BB512} from "./P2BB512.sol";

/// @notice Canonical P2BB512-v1 application hashes.
/// Digests and note preimages are decoded as canonical big-endian u32
/// BabyBear elements; ordinary byte strings are absorbed as big-endian u16s.
library PQTCApplicationHash {
    uint32 private constant BABY_BEAR_MODULUS = 2_013_265_921;
    uint32 private constant P2BB512_VERSION = 1;

    error NonCanonicalNotePreimageLimb(uint256 index, uint256 value);

    function scope(
        uint64 chainId,
        address pool,
        uint256 denomination,
        uint8 treeDepth,
        uint32 protocolVersion,
        Digest512 memory parameterId
    ) internal pure returns (Digest512 memory) {
        // parameterId is a proof-system identifier, not an application field
        // digest, so scope binds its 64 raw bytes as u16 chunks.
        bytes memory payload = abi.encodePacked(
            chainId, pool, denomination, treeDepth, protocolVersion, parameterId.left, parameterId.right
        );
        uint16[65] memory elements;
        for (uint256 i = 0; i < 65; ++i) {
            uint256 byteIndex = i * 2;
            elements[i] = uint16(uint8(payload[byteIndex])) << 8;
            if (byteIndex + 1 < payload.length) elements[i] |= uint16(uint8(payload[byteIndex + 1]));
        }
        return P2BB512.hashU16s65Odd(PQTCDomains.SCOPE, elements);
    }

    function commitment(Digest512 memory poolScope, bytes32 nullifierSecret, bytes32 trapdoor)
        internal
        pure
        returns (Digest512 memory)
    {
        uint32[32] memory elements;
        uint32[16] memory scopeFields = P2BB512.toFields(poolScope);
        for (uint256 i = 0; i < 16; ++i) {
            elements[i] = scopeFields[i];
        }
        for (uint256 i = 0; i < 8; ++i) {
            elements[i + 16] = _notePreimageLimb(nullifierSecret, i, i);
            elements[i + 24] = _notePreimageLimb(trapdoor, i, i + 8);
        }
        return _hashFields32(PQTCDomains.NOTE, 128, elements);
    }

    function nullifierHash(Digest512 memory poolScope, bytes32 nullifierSecret)
        internal
        pure
        returns (Digest512 memory)
    {
        uint32[24] memory elements;
        uint32[16] memory scopeFields = P2BB512.toFields(poolScope);
        for (uint256 i = 0; i < 16; ++i) {
            elements[i] = scopeFields[i];
        }
        for (uint256 i = 0; i < 8; ++i) {
            elements[i + 16] = _notePreimageLimb(nullifierSecret, i, i);
        }
        return _hashFields24(PQTCDomains.NULLIFIER, 96, elements);
    }

    function emptyLeaf(Digest512 memory poolScope) internal pure returns (Digest512 memory) {
        return P2BB512.hashFields16(PQTCDomains.EMPTY_LEAF, P2BB512.toFields(poolScope));
    }

    function merkleNode(uint8 level, Digest512 memory left, Digest512 memory right)
        internal
        pure
        returns (Digest512 memory)
    {
        return P2BB512.merkleNode(level, left, right);
    }

    function payoutDigest(address recipient, address relayer, uint256 fee) internal pure returns (Digest512 memory) {
        uint16[36] memory elements;
        uint160 recipientBits = uint160(recipient);
        uint160 relayerBits = uint160(relayer);
        for (uint256 i = 0; i < 10; ++i) {
            elements[i] = uint16(recipientBits >> (144 - 16 * i));
            elements[i + 10] = uint16(relayerBits >> (144 - 16 * i));
        }
        for (uint256 i = 0; i < 16; ++i) {
            elements[i + 20] = uint16(fee >> (240 - 16 * i));
        }
        return P2BB512.hashU16s36(PQTCDomains.PAYOUT, elements);
    }

    function statementHash(
        Digest512 memory poolScope,
        Digest512 memory root,
        Digest512 memory nullifier,
        Digest512 memory payout
    ) internal pure returns (Digest512 memory) {
        uint32[64] memory elements;
        Digest512[4] memory digests;
        digests[0] = poolScope;
        digests[1] = root;
        digests[2] = nullifier;
        digests[3] = payout;
        for (uint256 digestIndex = 0; digestIndex < 4; ++digestIndex) {
            uint32[16] memory fields = P2BB512.toFields(digests[digestIndex]);
            for (uint256 limb = 0; limb < 16; ++limb) {
                elements[digestIndex * 16 + limb] = fields[limb];
            }
        }
        return P2BB512.hashFields64(PQTCDomains.STATEMENT, elements);
    }

    // NOTE and NULLIFIER absorb canonical u32 fields throughout. Their byte
    // lengths bind the original 64-byte scope and 32-byte preimage values.
    function _hashFields24(uint8 domainTag, uint32 payloadByteLength, uint32[24] memory elements)
        private
        pure
        returns (Digest512 memory)
    {
        uint32[16] memory state = _initialState(domainTag, payloadByteLength, 24);
        for (uint256 offset = 0; offset < 24; offset += 4) {
            state = _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function _hashFields32(uint8 domainTag, uint32 payloadByteLength, uint32[32] memory elements)
        private
        pure
        returns (Digest512 memory)
    {
        uint32[16] memory state = _initialState(domainTag, payloadByteLength, 32);
        for (uint256 offset = 0; offset < 32; offset += 4) {
            state = _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function _notePreimageLimb(bytes32 encoded, uint256 wordIndex, uint256 preimageIndex)
        private
        pure
        returns (uint32 value)
    {
        value = uint32(uint256(encoded) >> (224 - 32 * wordIndex));
        if (value >= BABY_BEAR_MODULUS) revert NonCanonicalNotePreimageLimb(preimageIndex, value);
    }

    function _initialState(uint8 domainTag, uint32 payloadByteLength, uint32 payloadElementCount)
        private
        pure
        returns (uint32[16] memory state)
    {
        state[4] = P2BB512_VERSION;
        state[5] = domainTag;
        state[6] = payloadByteLength;
        state[7] = payloadElementCount;
    }

    function _absorb(uint32[16] memory state, uint32 a, uint32 b, uint32 c, uint32 d)
        private
        pure
        returns (uint32[16] memory)
    {
        state[0] = uint32(addmod(state[0], a, BABY_BEAR_MODULUS));
        state[1] = uint32(addmod(state[1], b, BABY_BEAR_MODULUS));
        state[2] = uint32(addmod(state[2], c, BABY_BEAR_MODULUS));
        state[3] = uint32(addmod(state[3], d, BABY_BEAR_MODULUS));
        return P2BB512.permute(state);
    }

    function _squeeze(uint32[16] memory state) private pure returns (Digest512 memory) {
        uint32[16] memory output;
        for (uint256 blockIndex = 0; blockIndex < 4; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            output[offset] = state[0];
            output[offset + 1] = state[1];
            output[offset + 2] = state[2];
            output[offset + 3] = state[3];
            if (blockIndex != 3) state = P2BB512.permute(state);
        }
        return P2BB512.fromFields(output);
    }
}
```

</details>

## `contracts/src/libraries/PQTCProofCodec.sol`

- Bytes: 4,780
- SHA-256: `a4fd095958ca9c35268bb7a5b5da5950a09b0c3b4c5f50118fbeeb455d6f61bd`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {CanonicalCodec} from "./CanonicalCodec.sol";
import {Digest512} from "./Digest512.sol";

/// Strict reader for the PQTC v0.3 two-part proof framing.
library PQTCProofCodec {
    uint64 internal constant PART_A_MAGIC = 0x5051544350413033; // PQTCPA03
    uint64 internal constant PART_B_MAGIC = 0x5051544350423033; // PQTCPB03
    uint16 internal constant VERSION = 3;
    uint8 internal constant PROFILE_SEPOLIA_V03 = 3;
    uint8 internal constant PROOF_DEGREE_BITS = 9;
    uint8 internal constant BASE_DEGREE_BITS = 8;
    uint8 internal constant FRI_ROUNDS = 9;
    uint8 internal constant RANDOM_CODEWORDS = 4;
    uint16 internal constant QUERY_COUNT = 32;
    uint16 internal constant HALF_QUERY_COUNT = 16;
    uint16 internal constant PUBLIC_VALUES_COUNT = 64;
    uint32 internal constant PART_A_END = 0x50414533;
    uint32 internal constant PART_B_END = 0x50424533;
    uint32 internal constant BABY_BEAR_MODULUS = 2_013_265_921;

    struct Common {
        Digest512 parameterId;
        uint32[64] publicValues;
        uint256 cursor;
    }

    error InvalidMagic();
    error UnsupportedVersion();
    error UnsupportedProfile();
    error InvalidShape();
    error ParameterMismatch();
    error PublicValueMismatch(uint256 index);
    error InvalidEndMarker();

    function parseCommon(
        bytes calldata proof,
        uint64 expectedMagic,
        Digest512 calldata expectedParameterId,
        uint32[64] calldata expectedPublicValues
    ) internal pure returns (Common memory common) {
        uint256 cursor;
        uint64 magic;
        (magic, cursor) = CanonicalCodec.readU64(proof, cursor);
        if (magic != expectedMagic) revert InvalidMagic();
        uint16 version;
        (version, cursor) = CanonicalCodec.readU16(proof, cursor);
        if (version != VERSION) revert UnsupportedVersion();
        uint8 profile;
        (profile, cursor) = CanonicalCodec.readU8(proof, cursor);
        if (profile != PROFILE_SEPOLIA_V03) revert UnsupportedProfile();
        uint8 degreeBits;
        uint8 friRounds;
        uint8 randomCodewords;
        uint16 queries;
        (degreeBits, cursor) = CanonicalCodec.readU8(proof, cursor);
        (friRounds, cursor) = CanonicalCodec.readU8(proof, cursor);
        (randomCodewords, cursor) = CanonicalCodec.readU8(proof, cursor);
        (queries, cursor) = CanonicalCodec.readU16(proof, cursor);
        if (
            degreeBits != PROOF_DEGREE_BITS || degreeBits - 1 != BASE_DEGREE_BITS || friRounds != FRI_ROUNDS
                || randomCodewords != RANDOM_CODEWORDS || queries != QUERY_COUNT
        ) revert InvalidShape();
        (common.parameterId, cursor) = CanonicalCodec.readDigest(proof, cursor);
        if (
            common.parameterId.left != expectedParameterId.left || common.parameterId.right != expectedParameterId.right
        ) revert ParameterMismatch();
        uint16 publicCount;
        (publicCount, cursor) = CanonicalCodec.readU16(proof, cursor);
        if (publicCount != PUBLIC_VALUES_COUNT) revert InvalidShape();
        for (uint256 i; i < PUBLIC_VALUES_COUNT; ++i) {
            (common.publicValues[i], cursor) = CanonicalCodec.readField(proof, cursor);
            if (expectedPublicValues[i] >= BABY_BEAR_MODULUS) {
                revert CanonicalCodec.NonCanonicalField(expectedPublicValues[i]);
            }
            if (common.publicValues[i] != expectedPublicValues[i]) revert PublicValueMismatch(i);
        }
        common.cursor = cursor;
    }

    function statementKey(Digest512 calldata parameterId, uint32[64] calldata publicValues)
        internal
        pure
        returns (bytes32)
    {
        for (uint256 i; i < PUBLIC_VALUES_COUNT; ++i) {
            if (publicValues[i] >= BABY_BEAR_MODULUS) revert CanonicalCodec.NonCanonicalField(publicValues[i]);
        }
        return keccak256(abi.encode(bytes32("PQTC.V3.STATEMENT"), parameterId.left, parameterId.right, publicValues));
    }

    function requireHalfHeader(bytes calldata proof, uint256 cursor, uint16 expectedStart)
        internal
        pure
        returns (uint256 next)
    {
        uint16 start;
        uint16 count;
        (start, cursor) = CanonicalCodec.readU16(proof, cursor);
        (count, next) = CanonicalCodec.readU16(proof, cursor);
        if (start != expectedStart || count != HALF_QUERY_COUNT) revert InvalidShape();
    }

    function requireEnd(bytes calldata proof, uint256 cursor, uint32 expectedMarker) internal pure {
        uint32 marker;
        (marker, cursor) = CanonicalCodec.readU32(proof, cursor);
        if (marker != expectedMarker) revert InvalidEndMarker();
        CanonicalCodec.requireEnd(proof, cursor);
    }
}
```

</details>

## `contracts/src/libraries/Transcript512.sol`

- Bytes: 5,577
- SHA-256: `1928fc0fd636e900db5575bc85d5fc0d51ff6efcd6271e62871d0810ea7c35c1`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {PQTCDomains} from "../PQTCDomains.sol";
import {Digest512} from "./Digest512.sol";
import {KeccakPair512} from "./KeccakPair512.sol";

library Transcript512 {
    uint32 internal constant BABY_BEAR_MODULUS = 2_013_265_921;
    uint8 private constant FIELD_ITEM = 1;
    uint8 private constant COMMITMENT_ITEM = 2;

    struct State {
        Digest512 digest;
        bytes output;
        uint256 outputCursor;
        uint64 squeezeCounter;
        bytes scratch;
    }

    error InvalidField();
    error InvalidBitCount();
    error SqueezeCounterOverflow();

    function initialize(Digest512 memory parameterId, uint32[] memory publicValues)
        internal
        pure
        returns (State memory state)
    {
        bytes memory payload = new bytes(64 + publicValues.length * 4);
        assembly ("memory-safe") {
            mstore(add(payload, 0x20), mload(parameterId))
            mstore(add(payload, 0x40), mload(add(parameterId, 0x20)))
        }
        for (uint256 i; i < publicValues.length; ++i) {
            if (publicValues[i] >= BABY_BEAR_MODULUS) revert InvalidField();
            assembly ("memory-safe") {
                mstore(add(add(payload, 0x60), mul(i, 4)), shl(224, mload(add(add(publicValues, 0x20), mul(i, 0x20)))))
            }
        }
        state.digest = KeccakPair512.hash(PQTCDomains.TRANSCRIPT_INIT, payload);
        state.scratch = new bytes(160);
    }

    function observeField(State memory state, uint32 value) internal pure {
        if (value >= BABY_BEAR_MODULUS) revert InvalidField();
        _absorbField(state, value);
    }

    function observeCommitment(State memory state, Digest512 memory commitment) internal pure {
        _absorbCommitment(state, commitment);
    }

    function sampleField(State memory state) internal pure returns (uint32) {
        while (true) {
            uint32 value = _sampleU32(state) & 0x7fff_ffff;
            if (value < BABY_BEAR_MODULUS) return value;
        }
        revert InvalidField();
    }

    function sampleExt4(State memory state) internal pure returns (uint32[4] memory value) {
        for (uint256 i = 0; i < 4; i++) {
            value[i] = sampleField(state);
        }
    }

    function sampleBits(State memory state, uint256 bits) internal pure returns (uint256) {
        if (bits > 31) revert InvalidBitCount();
        if (bits == 0) return 0;
        return uint256(_sampleU32(state)) & ((uint256(1) << bits) - 1);
    }

    function checkWitness(State memory state, uint256 bits, uint32 witness) internal pure returns (bool) {
        if (bits == 0) return true;
        observeField(state, witness);
        return sampleBits(state, bits) == 0;
    }

    function _absorbField(State memory state, uint32 value) private pure {
        Digest512 memory digest = state.digest;
        bytes memory scratch = state.scratch;
        assembly ("memory-safe") {
            let start := add(scratch, 0x20)
            mstore8(start, 0)
            mstore8(add(start, 1), 0x43)
            mstore(add(start, 2), mload(digest))
            mstore(add(start, 34), mload(add(digest, 0x20)))
            mstore8(add(start, 66), 1)
            mstore(add(start, 67), shl(224, 4))
            mstore(add(start, 71), shl(224, value))
            mstore(digest, keccak256(start, 75))
            mstore8(start, 1)
            mstore(add(digest, 0x20), keccak256(start, 75))
        }
        state.digest = digest;
        _resetOutput(state);
    }

    function _absorbCommitment(State memory state, Digest512 memory commitment) private pure {
        Digest512 memory digest = state.digest;
        bytes memory scratch = state.scratch;
        assembly ("memory-safe") {
            let start := add(scratch, 0x20)
            mstore8(start, 0)
            mstore8(add(start, 1), 0x43)
            mstore(add(start, 2), mload(digest))
            mstore(add(start, 34), mload(add(digest, 0x20)))
            mstore8(add(start, 66), 2)
            mstore(add(start, 67), shl(224, 64))
            mstore(add(start, 71), mload(commitment))
            mstore(add(start, 103), mload(add(commitment, 0x20)))
            mstore(digest, keccak256(start, 135))
            mstore8(start, 1)
            mstore(add(digest, 0x20), keccak256(start, 135))
        }
        state.digest = digest;
        _resetOutput(state);
    }

    function _resetOutput(State memory state) private pure {
        state.output = "";
        state.outputCursor = 0;
        state.squeezeCounter = 0;
    }

    function _sampleU32(State memory state) private pure returns (uint32 value) {
        bytes memory four = new bytes(4);
        for (uint256 i = 0; i < 4; i++) {
            four[i] = _sampleByte(state);
        }
        assembly ("memory-safe") { value := shr(224, mload(add(four, 0x20))) }
    }

    function _sampleByte(State memory state) private pure returns (bytes1 value) {
        if (state.outputCursor == state.output.length) {
            if (state.squeezeCounter == type(uint64).max) revert SqueezeCounterOverflow();
            Digest512 memory blockDigest = KeccakPair512.hash(
                PQTCDomains.TRANSCRIPT_SQUEEZE,
                abi.encodePacked(state.digest.left, state.digest.right, state.squeezeCounter)
            );
            state.squeezeCounter++;
            state.output = abi.encodePacked(blockDigest.left, blockDigest.right);
            state.outputCursor = 0;
        }
        value = state.output[state.outputCursor++];
    }
}
```

</details>

## `contracts/src/verifier/AirEvaluatorPoseidon.sol`

- Bytes: 21,818
- SHA-256: `eb34d91b6c94c53c010078b6a90d7222841dddb5808d7d4021be3538b741e09e`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBearExt4Packed as Ext} from "../libraries/BabyBearExt4Packed.sol";

/// The constraint order is exactly pqtc_poseidon_air::WithdrawalAir::eval.
library AirEvaluatorPoseidon {
    uint256 internal constant WIDTH = 190;
    uint256 internal constant CONSTRAINTS = 1_186;
    uint256 private constant POSEIDON_WIDTH = 16;
    uint256 private constant POSEIDON_COLUMNS = 157;
    uint256 private constant OUTPUT = 141;
    uint256 private constant IS_NOTE = 157;
    uint256 private constant IS_NULLIFIER = 158;
    uint256 private constant IS_MERKLE = 159;
    uint256 private constant IS_PAYOUT = 160;
    uint256 private constant IS_PADDING = 161;
    uint256 private constant STEP_BITS = 162;
    uint256 private constant LEVEL_BITS = 166;
    uint256 private constant IS_LAST_LEVEL = 171;
    uint256 private constant PATH_BIT = 172;
    uint256 private constant INDEX = 173;
    uint256 private constant WORK = 174;

    uint256 private constant EXTERNAL_0A = 0x69cbb6af46ad93f960a00f4e6b1297cd23189afe732e7bef72c246de2c941900;
    uint256 private constant EXTERNAL_0B = 0x0557eede1580496f3a3ea77b54f3f2710f49b02947872fe1221e2e361ab7202e;
    uint256 private constant EXTERNAL_1A = 0x487779a63851c9d838dc17c0209f8849268dcee8350c48da5b9ad32e0523272b;
    uint256 private constant EXTERNAL_1B = 0x3f89055b01e894b213ddedde1b2ef3347507d8b46ceeb94e52eb6ba250642905;
    uint256 private constant EXTERNAL_2A = 0x05453f3f06349efc6922787c04bfff9c768c714a3e9ff21a15737c9c2229c807;
    uint256 private constant EXTERNAL_2B = 0x0d47f88c097e0ecc27eadba02d7d29e43502aaa00f475fd729fbda49018afffd;
    uint256 private constant EXTERNAL_3A = 0x0315b6186d4497d11b171d9e52861abd2e5d05013ec8646c6e5f250a148ae8e6;
    uint256 private constant EXTERNAL_3B = 0x17f5fa4a3e66d2840051aa3b483f79132cfe5f15023427ca2cc783151e36ea47;
    uint256 private constant EXTERNAL_4A = 0x7290a80d6f7e5329598ec8a876a859a06559e868657b83af13271d3f1f876063;
    uint256 private constant EXTERNAL_4B = 0x0aeeae37706e9ca646400cee72a05c262c589c9e20bd37a76a2d3d1020523767;
    uint256 private constant EXTERNAL_5A = 0x5b8fe9c42aa501d61e01ac3e1448bc545ce5ad1c4918a14d2c46a83f4fcf6876;
    uint256 private constant EXTERNAL_5B = 0x61d8d5c86ddf4ff911fda4d302933a8f170eaf815a9c314f49a1259035ec52a1;
    uint256 private constant EXTERNAL_6A = 0x58eb16115e481e65367125c90eba33ba1fc28ded066399ad0cbec0ea75fd1af0;
    uint256 private constant EXTERNAL_6B = 0x50f5bf4e643d5f416f4fe7185b3cbbde1e3afb3e296fb02745e1547b4a8db2ab;
    uint256 private constant EXTERNAL_7A = 0x59986d1930bcdfa31db639321d7c282453b336810673b747038a98a32c5bce60;
    uint256 private constant EXTERNAL_7B = 0x351979cd5008fb73547bca78711af4813f93bf64644d987b3c8bcd87608758b8;
    uint256 private constant INTERNAL_A = 0x5a8053c0693be6393858867d19334f6b128f0fd84e2b1ccb61210ce03c318939;
    uint256 private constant INTERNAL_B = 0x0b5b2f222edb11d5213effdf0cac4606241af16d000000000000000000000000;

    struct Fold {
        uint256 value;
        uint256 alpha;
    }

    uint8 internal constant SEGMENTS = 7;

    error InvalidInputWidth();
    error InvalidSegmentRange();

    function evaluate(
        uint256[] memory local,
        uint256[] memory next,
        uint256[] memory publicValues,
        uint256 isFirst,
        uint256 isLast,
        uint256 isTransition,
        uint256 alpha
    ) internal pure returns (uint256) {
        return evaluateRange(local, next, publicValues, isFirst, isLast, isTransition, alpha, 0, 0, SEGMENTS);
    }

    function evaluateRange(
        uint256[] memory local,
        uint256[] memory next,
        uint256[] memory publicValues,
        uint256 isFirst,
        uint256 isLast,
        uint256 isTransition,
        uint256 alpha,
        uint256 accumulator,
        uint8 start,
        uint8 end
    ) internal pure returns (uint256) {
        if (local.length != WIDTH || next.length != WIDTH || publicValues.length != 64) {
            revert InvalidInputWidth();
        }
        if (start > end || end > SEGMENTS) revert InvalidSegmentRange();
        Fold memory fold = Fold(accumulator, alpha);
        for (uint8 segment = start; segment < end; ++segment) {
            if (segment == 0) {
                _poseidon(fold, local);
            } else if (segment == 1) {
                _shape(fold, local, isFirst, isLast);
                _initial(fold, local);
            } else if (segment == 2) {
                _bindInputs(fold, local, publicValues);
                _metadata(fold, local, next, isTransition);
                _chainingPrivate(fold, local, next, publicValues, isTransition);
            } else if (segment == 3) {
                _chainingMerkle(fold, local, next, isTransition);
            } else if (segment == 4) {
                _workPrivate(fold, local, next, isTransition);
            } else if (segment == 5) {
                _workMerkle(fold, local, next, isTransition);
            } else {
                _outputs(fold, local, publicValues);
            }
        }
        return fold.value;
    }

    function _poseidon(Fold memory fold, uint256[] memory row) private pure {
        uint256[16] memory state;
        for (uint256 i; i < 16; ++i) {
            state[i] = row[i];
        }
        _externalLinear(state);
        for (uint256 round; round < 4; ++round) {
            (uint256 first, uint256 second) = _externalConstants(round);
            for (uint256 i; i < 16; ++i) {
                uint256 rc = i < 8 ? uint32(first >> (224 - 32 * i)) : uint32(second >> (224 - 32 * (i - 8)));
                state[i] = _pow7(Ext.add(state[i], Ext.fromBase(rc)));
            }
            _externalLinear(state);
            uint256 post = 16 + round * 16;
            for (uint256 i; i < 16; ++i) {
                _push(fold, Ext.sub(state[i], row[post + i]));
                state[i] = row[post + i];
            }
        }
        for (uint256 round; round < 13; ++round) {
            uint256 x = Ext.add(state[0], Ext.fromBase(_internalConstant(round)));
            x = _pow7(x);
            _push(fold, Ext.sub(x, row[80 + round]));
            state[0] = row[80 + round];
            _internalLinear(state);
        }
        for (uint256 round; round < 4; ++round) {
            (uint256 first, uint256 second) = _externalConstants(round + 4);
            for (uint256 i; i < 16; ++i) {
                uint256 rc = i < 8 ? uint32(first >> (224 - 32 * i)) : uint32(second >> (224 - 32 * (i - 8)));
                state[i] = _pow7(Ext.add(state[i], Ext.fromBase(rc)));
            }
            _externalLinear(state);
            uint256 post = 93 + round * 16;
            for (uint256 i; i < 16; ++i) {
                _push(fold, Ext.sub(state[i], row[post + i]));
                state[i] = row[post + i];
            }
        }
    }

    function _shape(Fold memory fold, uint256[] memory local, uint256 isFirst, uint256 isLast) private pure {
        uint256[7] memory selectors = [IS_NOTE, IS_NULLIFIER, IS_MERKLE, IS_PAYOUT, IS_PADDING, IS_LAST_LEVEL, PATH_BIT];
        for (uint256 i; i < selectors.length; ++i) {
            _push(fold, _bool(local[selectors[i]]));
        }
        for (uint256 i; i < 4; ++i) {
            _push(fold, _bool(local[STEP_BITS + i]));
        }
        for (uint256 i; i < 5; ++i) {
            _push(fold, _bool(local[LEVEL_BITS + i]));
        }
        uint256 sum = Ext.add(Ext.add(local[IS_NOTE], local[IS_NULLIFIER]), Ext.add(local[IS_MERKLE], local[IS_PAYOUT]));
        _push(fold, Ext.sub(Ext.add(sum, local[IS_PADDING]), Ext.fromBase(1)));
        _push(fold, Ext.sub(local[IS_LAST_LEVEL], Ext.mul(local[IS_MERKLE], _levelEq(local, 19))));
        uint256 notMerkle = Ext.sub(Ext.fromBase(1), local[IS_MERKLE]);
        _zero(fold, notMerkle, local[PATH_BIT]);
        _zero(fold, notMerkle, local[INDEX]);
        _eq(fold, isFirst, local[IS_NULLIFIER], Ext.fromBase(1));
        _zero(fold, isFirst, _stepValue(local));
        _zero(fold, isFirst, _levelValue(local));
        for (uint256 i = 8; i < 16; ++i) {
            _zero(fold, isFirst, local[WORK + i]);
        }
        _zero(fold, notMerkle, _levelValue(local));
        _zero(fold, local[IS_PADDING], _stepValue(local));
        _eq(fold, isLast, local[IS_PADDING], Ext.fromBase(1));
    }

    function _initial(Fold memory fold, uint256[] memory local) private pure {
        _initialRow(fold, local, IS_NULLIFIER, 0x12, 96, 24, false);
        _initialRow(fold, local, IS_NOTE, 0x11, 128, 32, false);
        _initialRow(fold, local, IS_MERKLE, 0x20, 128, 32, true);
    }

    function _bindInputs(Fold memory fold, uint256[] memory local, uint256[] memory publicValues) private pure {
        for (uint256 j; j < 4; ++j) {
            _eq(fold, Ext.mul(local[IS_NULLIFIER], _stepEq(local, 0)), local[j], publicValues[j]);
            _eq(fold, Ext.mul(local[IS_NOTE], _stepEq(local, 0)), local[j], publicValues[j]);
            uint256 c = Ext.mul(Ext.mul(local[IS_MERKLE], _stepEq(local, 0)), Ext.sub(Ext.fromBase(1), local[PATH_BIT]));
            _eq(fold, c, local[j], local[WORK + j]);
        }
        for (uint256 step; step < 4; ++step) {
            uint256 c = Ext.mul(local[IS_PAYOUT], _stepEq(local, step));
            for (uint256 j; j < 4; ++j) {
                _eq(fold, c, local[j], publicValues[48 + step * 4 + j]);
            }
            for (uint256 j = 4; j < 16; ++j) {
                _zero(fold, c, local[j]);
            }
        }
        uint256 empty = Ext.add(local[IS_PAYOUT], local[IS_PADDING]);
        for (uint256 j; j < 16; ++j) {
            _zero(fold, local[IS_PADDING], local[j]);
            _zero(fold, empty, local[WORK + j]);
        }
    }

    function _metadata(Fold memory fold, uint256[] memory l, uint256[] memory n, uint256 tr) private pure {
        uint256 one = Ext.fromBase(1);
        uint256 s = _stepValue(l);
        uint256 ns = _stepValue(n);
        uint256 lev = _levelValue(l);
        uint256 nl = _levelValue(n);

        uint256 c = Ext.mul(Ext.mul(tr, l[IS_NULLIFIER]), Ext.sub(one, _stepEq(l, 8)));
        _eq(fold, c, n[IS_NULLIFIER], one);
        _eq(fold, c, ns, Ext.add(s, one));
        c = Ext.mul(Ext.mul(tr, l[IS_NULLIFIER]), _stepEq(l, 8));
        _eq(fold, c, n[IS_NOTE], one);
        _zero(fold, c, ns);

        c = Ext.mul(Ext.mul(tr, l[IS_NOTE]), Ext.sub(one, _stepEq(l, 10)));
        _eq(fold, c, n[IS_NOTE], one);
        _eq(fold, c, ns, Ext.add(s, one));
        c = Ext.mul(Ext.mul(tr, l[IS_NOTE]), _stepEq(l, 10));
        _eq(fold, c, n[IS_MERKLE], one);
        _zero(fold, c, ns);
        _zero(fold, c, nl);

        c = Ext.mul(Ext.mul(tr, l[IS_MERKLE]), Ext.sub(one, _stepEq(l, 10)));
        _eq(fold, c, n[IS_MERKLE], one);
        _eq(fold, c, ns, Ext.add(s, one));
        _eq(fold, c, nl, lev);
        _eq(fold, c, n[PATH_BIT], l[PATH_BIT]);
        _eq(fold, c, n[INDEX], l[INDEX]);
        c = Ext.mul(Ext.mul(Ext.mul(tr, l[IS_MERKLE]), _stepEq(l, 10)), Ext.sub(one, l[IS_LAST_LEVEL]));
        _eq(fold, c, n[IS_MERKLE], one);
        _zero(fold, c, ns);
        _eq(fold, c, nl, Ext.add(lev, one));
        _eq(fold, c, l[INDEX], Ext.add(l[PATH_BIT], Ext.mulBase(n[INDEX], 2)));
        c = Ext.mul(Ext.mul(Ext.mul(tr, l[IS_MERKLE]), _stepEq(l, 10)), l[IS_LAST_LEVEL]);
        _eq(fold, c, n[IS_PAYOUT], one);
        _zero(fold, c, ns);
        _eq(fold, c, l[INDEX], l[PATH_BIT]);

        c = Ext.mul(Ext.mul(tr, l[IS_PAYOUT]), Ext.sub(one, _stepEq(l, 3)));
        _eq(fold, c, n[IS_PAYOUT], one);
        _eq(fold, c, ns, Ext.add(_stepValue(l), one));
        c = Ext.mul(Ext.mul(tr, l[IS_PAYOUT]), _stepEq(l, 3));
        _eq(fold, c, n[IS_PADDING], one);
        _zero(fold, c, ns);
        c = Ext.mul(tr, l[IS_PADDING]);
        _eq(fold, c, n[IS_PADDING], one);
        _zero(fold, c, ns);
    }

    function _chainingPrivate(
        Fold memory fold,
        uint256[] memory l,
        uint256[] memory n,
        uint256[] memory publicValues,
        uint256 tr
    ) private pure {
        for (uint256 step = 1; step < 6; ++step) {
            uint256 c = Ext.mul(Ext.mul(tr, n[IS_NULLIFIER]), _stepEq(n, step));
            for (uint256 j; j < 4; ++j) {
                uint256 payload = step < 4 ? publicValues[step * 4 + j] : n[WORK + (step - 4) * 4 + j];
                _eq(fold, c, n[j], Ext.add(l[OUTPUT + j], payload));
            }
            for (uint256 j = 4; j < 16; ++j) {
                _eq(fold, c, n[j], l[OUTPUT + j]);
            }
        }
        for (uint256 step = 6; step < 9; ++step) {
            _squeeze(fold, l, n, Ext.mul(Ext.mul(tr, n[IS_NULLIFIER]), _stepEq(n, step)));
        }
        for (uint256 step = 1; step < 8; ++step) {
            // Steps 6 and 7 leave exactly four rate deltas free for the eight
            // ephemeral trapdoor limbs; the twelve capacity lanes remain chained.
            uint256 c = Ext.mul(Ext.mul(tr, n[IS_NOTE]), _stepEq(n, step));
            if (step < 6) {
                for (uint256 j; j < 4; ++j) {
                    uint256 payload = step < 4 ? publicValues[step * 4 + j] : n[WORK + (step - 4) * 4 + j];
                    _eq(fold, c, n[j], Ext.add(l[OUTPUT + j], payload));
                }
            }
            for (uint256 j = 4; j < 16; ++j) {
                _eq(fold, c, n[j], l[OUTPUT + j]);
            }
        }
        for (uint256 step = 8; step < 11; ++step) {
            _squeeze(fold, l, n, Ext.mul(Ext.mul(tr, n[IS_NOTE]), _stepEq(n, step)));
        }
    }

    function _chainingMerkle(Fold memory fold, uint256[] memory l, uint256[] memory n, uint256 tr) private pure {
        for (uint256 step = 1; step < 8; ++step) {
            uint256 c = Ext.mul(Ext.mul(tr, n[IS_MERKLE]), _stepEq(n, step));
            for (uint256 j; j < 4; ++j) {
                uint256 k = step * 4 + j;
                uint256 side = k < 16 ? Ext.sub(Ext.fromBase(1), n[PATH_BIT]) : n[PATH_BIT];
                _eq(fold, Ext.mul(c, side), n[j], Ext.add(l[OUTPUT + j], n[WORK + (k % 16)]));
            }
            for (uint256 j = 4; j < 16; ++j) {
                _eq(fold, c, n[j], l[OUTPUT + j]);
            }
        }
        for (uint256 step = 8; step < 11; ++step) {
            _squeeze(fold, l, n, Ext.mul(Ext.mul(tr, n[IS_MERKLE]), _stepEq(n, step)));
        }
    }

    function _workPrivate(Fold memory fold, uint256[] memory l, uint256[] memory n, uint256 tr) private pure {
        for (uint256 i; i < 16; ++i) {
            _eq(fold, Ext.mul(tr, l[IS_NULLIFIER]), n[WORK + i], l[WORK + i]);
        }
        for (uint256 step; step < 11; ++step) {
            _workTransition(fold, l, n, Ext.mul(Ext.mul(tr, l[IS_NOTE]), _stepEq(l, step)), 7, step);
        }
    }

    function _workMerkle(Fold memory fold, uint256[] memory l, uint256[] memory n, uint256 tr) private pure {
        for (uint256 step; step < 10; ++step) {
            _workTransition(fold, l, n, Ext.mul(Ext.mul(tr, l[IS_MERKLE]), _stepEq(l, step)), 7, step);
        }
        uint256 c =
            Ext.mul(Ext.mul(Ext.mul(tr, l[IS_MERKLE]), _stepEq(l, 10)), Ext.sub(Ext.fromBase(1), l[IS_LAST_LEVEL]));
        _workTransition(fold, l, n, c, 7, 10);
    }

    function _outputs(Fold memory fold, uint256[] memory l, uint256[] memory publicValues) private pure {
        for (uint256 chunk; chunk < 4; ++chunk) {
            uint256 nc = Ext.mul(l[IS_NULLIFIER], _stepEq(l, 5 + chunk));
            uint256 rc = Ext.mul(Ext.mul(l[IS_MERKLE], l[IS_LAST_LEVEL]), _stepEq(l, 7 + chunk));
            for (uint256 j; j < 4; ++j) {
                _eq(fold, nc, l[OUTPUT + j], publicValues[32 + chunk * 4 + j]);
                _eq(fold, rc, l[OUTPUT + j], publicValues[16 + chunk * 4 + j]);
            }
        }
    }

    function _initialRow(
        Fold memory fold,
        uint256[] memory row,
        uint256 selector,
        uint256 tag,
        uint256 byteLength,
        uint256 elementCount,
        bool level
    ) private pure {
        uint256 c = Ext.mul(row[selector], _stepEq(row, 0));
        _eq(fold, c, row[4], Ext.fromBase(1));
        _eq(fold, c, row[5], Ext.fromBase(tag));
        _eq(fold, c, row[6], Ext.fromBase(byteLength));
        _eq(fold, c, row[7], Ext.fromBase(elementCount));
        if (level) _eq(fold, c, row[8], _levelValue(row));
        else _zero(fold, c, row[8]);
        for (uint256 i = 9; i < 16; ++i) {
            _zero(fold, c, row[i]);
        }
    }

    function _squeeze(Fold memory fold, uint256[] memory l, uint256[] memory n, uint256 c) private pure {
        for (uint256 j; j < 16; ++j) {
            _eq(fold, c, n[j], l[OUTPUT + j]);
        }
    }

    function _workTransition(
        Fold memory fold,
        uint256[] memory l,
        uint256[] memory n,
        uint256 c,
        uint256 first,
        uint256 step
    ) private pure {
        bool writes = step >= first && step < first + 4;
        uint256 chunk = writes ? step - first : type(uint256).max;
        for (uint256 i; i < 16; ++i) {
            uint256 expected = writes && chunk == i / 4 ? l[OUTPUT + (i % 4)] : l[WORK + i];
            _eq(fold, c, n[WORK + i], expected);
        }
    }

    function _stepEq(uint256[] memory row, uint256 value) private pure returns (uint256) {
        return _bitsEq(row, STEP_BITS, 4, value);
    }

    function _levelEq(uint256[] memory row, uint256 value) private pure returns (uint256) {
        return _bitsEq(row, LEVEL_BITS, 5, value);
    }

    function _bitsEq(uint256[] memory row, uint256 start, uint256 count, uint256 value)
        private
        pure
        returns (uint256 p)
    {
        p = Ext.fromBase(1);
        for (uint256 i; i < count; ++i) {
            uint256 factor = ((value >> i) & 1) == 1 ? row[start + i] : Ext.sub(Ext.fromBase(1), row[start + i]);
            p = Ext.mul(p, factor);
        }
    }

    function _stepValue(uint256[] memory row) private pure returns (uint256 value) {
        for (uint256 i; i < 4; ++i) {
            value = Ext.add(value, Ext.mulBase(row[STEP_BITS + i], uint256(1) << i));
        }
    }

    function _levelValue(uint256[] memory row) private pure returns (uint256 value) {
        for (uint256 i; i < 5; ++i) {
            value = Ext.add(value, Ext.mulBase(row[LEVEL_BITS + i], uint256(1) << i));
        }
    }

    function _externalLinear(uint256[16] memory state) private pure {
        for (uint256 group; group < 4; ++group) {
            uint256 i = group * 4;
            uint256 x0 = state[i];
            uint256 x1 = state[i + 1];
            uint256 x2 = state[i + 2];
            uint256 x3 = state[i + 3];
            uint256 t01 = Ext.add(x0, x1);
            uint256 t23 = Ext.add(x2, x3);
            uint256 total = Ext.add(t01, t23);
            uint256 with1 = Ext.add(total, x1);
            uint256 with3 = Ext.add(total, x3);
            state[i + 3] = Ext.add(with3, Ext.mulBase(x0, 2));
            state[i + 1] = Ext.add(with1, Ext.mulBase(x2, 2));
            state[i] = Ext.add(with1, t01);
            state[i + 2] = Ext.add(with3, t23);
        }
        uint256[4] memory sums;
        for (uint256 lane; lane < 4; ++lane) {
            sums[lane] = Ext.add(Ext.add(state[lane], state[lane + 4]), Ext.add(state[lane + 8], state[lane + 12]));
        }
        for (uint256 i; i < 16; ++i) {
            state[i] = Ext.add(state[i], sums[i % 4]);
        }
    }

    function _internalLinear(uint256[16] memory state) private pure {
        uint256 partSum;
        for (uint256 i = 1; i < 16; ++i) {
            partSum = Ext.add(partSum, state[i]);
        }
        uint256 sum = Ext.add(partSum, state[0]);
        state[0] = Ext.sub(partSum, state[0]);
        uint256[15] memory diagonal = [
            uint256(1),
            2,
            1_006_632_961,
            3,
            4,
            1_006_632_960,
            2_013_265_918,
            2_013_265_917,
            2_005_401_601,
            1_509_949_441,
            1_761_607_681,
            2_013_265_906,
            7_864_320,
            125_829_120,
            15
        ];
        for (uint256 i = 1; i < 16; ++i) {
            state[i] = Ext.add(sum, Ext.mulBase(state[i], diagonal[i - 1]));
        }
    }

    function _pow7(uint256 x) private pure returns (uint256) {
        uint256 square = Ext.mul(x, x);
        return Ext.mul(Ext.mul(Ext.mul(square, square), square), x);
    }

    function _internalConstant(uint256 round) private pure returns (uint256) {
        return round < 8 ? uint32(INTERNAL_A >> (224 - 32 * round)) : uint32(INTERNAL_B >> (224 - 32 * (round - 8)));
    }

    function _externalConstants(uint256 round) private pure returns (uint256 first, uint256 second) {
        if (round == 0) return (EXTERNAL_0A, EXTERNAL_0B);
        if (round == 1) return (EXTERNAL_1A, EXTERNAL_1B);
        if (round == 2) return (EXTERNAL_2A, EXTERNAL_2B);
        if (round == 3) return (EXTERNAL_3A, EXTERNAL_3B);
        if (round == 4) return (EXTERNAL_4A, EXTERNAL_4B);
        if (round == 5) return (EXTERNAL_5A, EXTERNAL_5B);
        if (round == 6) return (EXTERNAL_6A, EXTERNAL_6B);
        return (EXTERNAL_7A, EXTERNAL_7B);
    }

    function _push(Fold memory fold, uint256 constraint) private pure {
        fold.value = Ext.add(Ext.mul(fold.value, fold.alpha), constraint);
    }

    function _eq(Fold memory fold, uint256 condition, uint256 a, uint256 b) private pure {
        _push(fold, Ext.mul(condition, Ext.sub(a, b)));
    }

    function _zero(Fold memory fold, uint256 condition, uint256 value) private pure {
        _push(fold, Ext.mul(condition, value));
    }

    function _bool(uint256 value) private pure returns (uint256) {
        return Ext.mul(value, Ext.sub(value, Ext.fromBase(1)));
    }
}
```

</details>

## `contracts/src/verifier/FriVerifier.sol`

- Bytes: 2,062
- SHA-256: `01f91143211fd02db8b22ff8362196faba53aa131943a5b46ab2744462c2330b`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBear} from "../libraries/BabyBear.sol";
import {BabyBearExt4, BabyBearExt4Value} from "../libraries/BabyBearExt4.sol";

library FriVerifier {
    uint256 private constant TWO_ADIC_BASE = 0x1a427a41;
    uint256 private constant TWO_ADICITY = 27;
    uint256 private constant INVERSE_TWO = 1_006_632_961;

    error InvalidLogHeight();

    /// Plonky3 binary two-adic fold. `logHeight` is the height after this fold.
    function foldBinary(
        uint256 index,
        uint256 logHeight,
        BabyBearExt4Value memory beta,
        BabyBearExt4Value memory low,
        BabyBearExt4Value memory high
    ) internal pure returns (BabyBearExt4Value memory) {
        if (logHeight + 1 > TWO_ADICITY) revert InvalidLogHeight();
        uint256 generator = twoAdicGenerator(logHeight + 1);
        uint256 x = BabyBear.pow(generator, reverseBits(index, logHeight));
        uint256 inverseTwoX = BabyBear.mul(INVERSE_TWO, BabyBear.inv(x));
        BabyBearExt4Value memory evenPart = BabyBearExt4.mulBase(BabyBearExt4.add(low, high), INVERSE_TWO);
        BabyBearExt4Value memory oddPart =
            BabyBearExt4.mul(BabyBearExt4.mulBase(BabyBearExt4.sub(low, high), inverseTwoX), beta);
        return BabyBearExt4.add(evenPart, oddPart);
    }

    function twoAdicGenerator(uint256 logOrder) internal pure returns (uint256 value) {
        if (logOrder > TWO_ADICITY) revert InvalidLogHeight();
        value = TWO_ADIC_BASE;
        for (uint256 i = logOrder; i < TWO_ADICITY; i++) {
            value = BabyBear.mul(value, value);
        }
    }

    function reverseBits(uint256 value, uint256 bits) internal pure returns (uint256 reversed) {
        for (uint256 i = 0; i < bits; i++) {
            reversed = (reversed << 1) | ((value >> i) & 1);
        }
    }

    function equal(BabyBearExt4Value memory a, BabyBearExt4Value memory b) internal pure returns (bool) {
        return a.c0 == b.c0 && a.c1 == b.c1 && a.c2 == b.c2 && a.c3 == b.c3;
    }
}
```

</details>

## `contracts/src/verifier/MmcsVerifier.sol`

- Bytes: 9,328
- SHA-256: `950892ccf87e23f30083b3ea1d9689e8904b2770d25a280fed7b056010cced4d`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {CanonicalCodec} from "../libraries/CanonicalCodec.sol";
import {Digest512} from "../libraries/Digest512.sol";

/// Binary MMCS verification from a sorted/deduplicated Plonky3 pruned frontier.
library MmcsVerifier {
    uint256 private constant MAX_LEAVES = 16;
    uint256 private constant SALT_FIELDS = 8;

    error InvalidPathLength();
    error InvalidMultiproof();
    error ConflictingDuplicate();
    error MultiproofRootMismatch(bytes32 expectedLeft, bytes32 actualLeft, uint256 consumed, uint256 supplied);

    struct LeafWords {
        bytes32[16] lefts;
        bytes32[16] rights;
    }

    struct FrontierState {
        uint32[16] indices;
        bytes32[16] lefts;
        bytes32[16] rights;
        bytes scratch;
        uint256 count;
        uint256 cursor;
        uint256 consumed;
        uint256 supplied;
    }

    function hashBatchLeaf(
        bytes calldata proof,
        uint256 rowsOffset,
        uint256 saltsOffset,
        uint256 query,
        uint256 matrices,
        uint256 rowWidth
    ) internal pure returns (bytes32 left, bytes32 right) {
        uint256 fields = matrices * (rowWidth + SALT_FIELDS);
        bytes memory payload = new bytes(4 + fields * 4);
        assembly ("memory-safe") { mstore(add(payload, 0x20), shl(224, mul(fields, 4))) }
        uint256 out = 4;
        for (uint256 matrix; matrix < matrices; ++matrix) {
            uint256 row = rowsOffset + (query * matrices * rowWidth + matrix * rowWidth) * 4;
            uint256 salt = saltsOffset + (query * matrices * SALT_FIELDS + matrix * SALT_FIELDS) * 4;
            uint256 rowBytes = rowWidth * 4;
            assembly ("memory-safe") {
                calldatacopy(add(add(payload, 0x20), out), add(proof.offset, row), rowBytes)
            }
            out += rowBytes;
            assembly ("memory-safe") {
                calldatacopy(add(add(payload, 0x20), out), add(proof.offset, salt), 32)
            }
            out += 32;
        }
        return _hashLeafPayload(payload);
    }

    function hashFriLeaf(uint256 folded, uint256 sibling, uint256 index, bytes calldata proof, uint256 saltOffset)
        internal
        pure
        returns (Digest512 memory digest)
    {
        (digest.left, digest.right) = hashFriLeafWords(folded, sibling, index, proof, saltOffset);
    }

    function hashFriLeafWords(uint256 folded, uint256 sibling, uint256 index, bytes calldata proof, uint256 saltOffset)
        internal
        pure
        returns (bytes32 left, bytes32 right)
    {
        return _hashLeafPayload(encodeFriLeaf(folded, sibling, index, proof, saltOffset));
    }

    function encodeFriLeaf(uint256 folded, uint256 sibling, uint256 index, bytes calldata proof, uint256 saltOffset)
        internal
        pure
        returns (bytes memory payload)
    {
        payload = new bytes(68);
        uint256 low = index & 1 == 0 ? folded : sibling;
        uint256 high = index & 1 == 0 ? sibling : folded;
        assembly ("memory-safe") {
            let mask := 0xffffffff
            let data := add(payload, 0x20)
            mstore(data, shl(224, 64))
            mstore(
                add(data, 4),
                or(
                    or(shl(224, and(low, mask)), shl(192, and(shr(32, low), mask))),
                    or(shl(160, and(shr(64, low), mask)), shl(128, and(shr(96, low), mask)))
                )
            )
            mstore(
                add(data, 20),
                or(
                    or(shl(224, and(high, mask)), shl(192, and(shr(32, high), mask))),
                    or(shl(160, and(shr(64, high), mask)), shl(128, and(shr(96, high), mask)))
                )
            )
            calldatacopy(add(data, 36), add(proof.offset, saltOffset), 32)
        }
    }

    function verifyPruned(
        Digest512 memory expectedRoot,
        uint32[16] memory indices,
        LeafWords memory leaves,
        uint256 height,
        uint256 leafCount,
        bytes calldata proof,
        uint256 cursor
    ) internal pure returns (uint256 next) {
        if (leafCount == 0 || leafCount > MAX_LEAVES) revert InvalidMultiproof();
        if (height == 0 || height > 31) revert InvalidPathLength();
        FrontierState memory state;
        state.scratch = new bytes(160);
        (state.supplied, state.cursor) = CanonicalCodec.readU32(proof, cursor);
        for (uint256 query; query < leafCount; ++query) {
            uint32 index = indices[query];
            if (uint256(index) >= (uint256(1) << height)) revert InvalidPathLength();
            uint256 position;
            while (position < state.count && state.indices[position] < index) ++position;
            if (position < state.count && state.indices[position] == index) {
                if (state.lefts[position] != leaves.lefts[query] || state.rights[position] != leaves.rights[query]) {
                    revert ConflictingDuplicate();
                }
                continue;
            }
            for (uint256 move = state.count; move > position; --move) {
                state.indices[move] = state.indices[move - 1];
                state.lefts[move] = state.lefts[move - 1];
                state.rights[move] = state.rights[move - 1];
            }
            state.indices[position] = index;
            state.lefts[position] = leaves.lefts[query];
            state.rights[position] = leaves.rights[query];
            ++state.count;
        }
        for (uint256 level; level < height; ++level) {
            _reduceLevel(proof, state);
        }
        if (
            state.consumed != state.supplied || state.count != 1 || state.lefts[0] != expectedRoot.left
                || state.rights[0] != expectedRoot.right
        ) {
            revert MultiproofRootMismatch(expectedRoot.left, state.lefts[0], state.consumed, state.supplied);
        }
        return state.cursor;
    }

    function _reduceLevel(bytes calldata proof, FrontierState memory state) private pure {
        uint256 oldCount = state.count;
        uint256 parentCount;
        uint256 i;
        while (i < oldCount) {
            uint32 index = state.indices[i];
            bytes32 left0;
            bytes32 left1;
            bytes32 right0;
            bytes32 right1;
            if (index & 1 == 0) {
                left0 = state.lefts[i];
                left1 = state.rights[i];
                if (i + 1 < oldCount && state.indices[i + 1] == index + 1) {
                    right0 = state.lefts[i + 1];
                    right1 = state.rights[i + 1];
                    i += 2;
                } else {
                    (right0, right1) = _frontierWords(proof, state);
                    ++i;
                }
            } else {
                (left0, left1) = _frontierWords(proof, state);
                right0 = state.lefts[i];
                right1 = state.rights[i];
                ++i;
            }
            state.indices[parentCount] = index >> 1;
            (state.lefts[parentCount], state.rights[parentCount]) =
                _hashNodeWords(left0, left1, right0, right1, state.scratch);
            ++parentCount;
        }
        state.count = parentCount;
    }

    function hashNode(Digest512 memory left, Digest512 memory right) internal pure returns (Digest512 memory digest) {
        bytes memory scratch = new bytes(160);
        (digest.left, digest.right) = _hashNodeWords(left.left, left.right, right.left, right.right, scratch);
    }

    function _hashNodeWords(bytes32 left0, bytes32 left1, bytes32 right0, bytes32 right1, bytes memory scratch)
        private
        pure
        returns (bytes32 digest0, bytes32 digest1)
    {
        assembly ("memory-safe") {
            let start := add(scratch, 0x20)
            mstore8(start, 0)
            mstore8(add(start, 1), 0x41)
            mstore(add(start, 2), left0)
            mstore(add(start, 34), left1)
            mstore(add(start, 66), right0)
            mstore(add(start, 98), right1)
            digest0 := keccak256(start, 130)
            mstore8(start, 1)
            digest1 := keccak256(start, 130)
        }
    }

    function _frontierWords(bytes calldata proof, FrontierState memory state)
        private
        pure
        returns (bytes32 left, bytes32 right)
    {
        if (state.consumed >= state.supplied) revert InvalidMultiproof();
        if (state.cursor > proof.length || 64 > proof.length - state.cursor) revert CanonicalCodec.Truncated();
        uint256 cursor = state.cursor;
        assembly ("memory-safe") {
            left := calldataload(add(proof.offset, cursor))
            right := calldataload(add(add(proof.offset, cursor), 32))
        }
        state.cursor = cursor + 64;
        ++state.consumed;
    }

    function _hashLeafPayload(bytes memory payload) private pure returns (bytes32 left, bytes32 right) {
        assembly ("memory-safe") {
            let length := mload(payload)
            let start := add(payload, 0x1e)
            mstore8(start, 0)
            mstore8(add(start, 1), 0x40)
            left := keccak256(start, add(length, 2))
            mstore8(start, 1)
            right := keccak256(start, add(length, 2))
            mstore(payload, length)
        }
    }
}
```

</details>

## `contracts/src/verifier/PQTCAirStageVerifier.sol`

- Bytes: 3,547
- SHA-256: `4f810d9fe141236e5f19219c31dc225dba37e0f9657b20364bbb21ece7d16202`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBearExt4Packed as Ext} from "../libraries/BabyBearExt4Packed.sol";
import {AirEvaluatorPoseidon} from "./AirEvaluatorPoseidon.sol";
import {StarkOodVerifier} from "./StarkOodVerifier.sol";

/// Stateless v0.3 OOD verifier for the 190-column Poseidon withdrawal AIR.
contract PQTCAirStageVerifier {
    uint256 private constant WIDTH = 190;

    error InvalidOodShape();

    function evaluateRange(
        uint256[] calldata traceLocal,
        uint256[] calldata traceNext,
        uint32[64] calldata publicValues,
        uint256 zeta,
        uint256 alpha,
        uint256 accumulator,
        uint8 start,
        uint8 end
    ) external pure virtual returns (uint256) {
        if (traceLocal.length != WIDTH || traceNext.length != WIDTH) revert InvalidOodShape();
        uint256[] memory local = new uint256[](WIDTH);
        uint256[] memory next = new uint256[](WIDTH);
        uint256[] memory publicExt = new uint256[](64);
        for (uint256 i; i < WIDTH; ++i) {
            local[i] = Ext.check(traceLocal[i]);
            next[i] = Ext.check(traceNext[i]);
        }
        for (uint256 i; i < 64; ++i) {
            publicExt[i] = Ext.fromBase(publicValues[i]);
        }
        StarkOodVerifier.Selectors memory selectors = StarkOodVerifier.selectors(zeta);
        return AirEvaluatorPoseidon.evaluateRange(
            local,
            next,
            publicExt,
            selectors.isFirst,
            selectors.isLast,
            selectors.isTransition,
            Ext.check(alpha),
            Ext.check(accumulator),
            start,
            end
        );
    }

    function requireValid(uint256 folded, uint256[] calldata quotientOpenings, uint256 zeta)
        external
        pure
        returns (bool)
    {
        if (quotientOpenings.length != 64) revert InvalidOodShape();
        uint256[] memory quotient = new uint256[](64);
        for (uint256 i; i < 64; ++i) {
            quotient[i] = Ext.check(quotientOpenings[i]);
        }
        StarkOodVerifier.requireValid(Ext.check(folded), quotient, zeta);
        return true;
    }

    function verify(
        uint256[] calldata traceLocal,
        uint256[] calldata traceNext,
        uint256[] calldata quotientOpenings,
        uint32[64] calldata publicValues,
        uint256 zeta,
        uint256 alpha
    ) external pure returns (bool) {
        if (traceLocal.length != WIDTH || traceNext.length != WIDTH || quotientOpenings.length != 64) {
            revert InvalidOodShape();
        }
        uint256[] memory local = new uint256[](WIDTH);
        uint256[] memory next = new uint256[](WIDTH);
        uint256[] memory publicExt = new uint256[](64);
        for (uint256 i; i < WIDTH; ++i) {
            local[i] = Ext.check(traceLocal[i]);
            next[i] = Ext.check(traceNext[i]);
        }
        for (uint256 i; i < 64; ++i) {
            publicExt[i] = Ext.fromBase(publicValues[i]);
        }
        StarkOodVerifier.Selectors memory selectors = StarkOodVerifier.selectors(zeta);
        uint256 folded = AirEvaluatorPoseidon.evaluate(
            local, next, publicExt, selectors.isFirst, selectors.isLast, selectors.isTransition, Ext.check(alpha)
        );
        uint256[] memory quotient = new uint256[](64);
        for (uint256 i; i < 64; ++i) {
            quotient[i] = Ext.check(quotientOpenings[i]);
        }
        StarkOodVerifier.requireValid(folded, quotient, zeta);
        return true;
    }
}
```

</details>

## `contracts/src/verifier/PQTCQueryVerifier.sol`

- Bytes: 16,578
- SHA-256: `8c6316f1132875dc647cba0d51c4779c8b14d97cf904acea67f01577efffa92f`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBear} from "../libraries/BabyBear.sol";
import {BabyBearExt4Packed as Ext} from "../libraries/BabyBearExt4Packed.sol";
import {CanonicalCodec} from "../libraries/CanonicalCodec.sol";
import {Digest512} from "../libraries/Digest512.sol";
import {PQTCProofCodec} from "../libraries/PQTCProofCodec.sol";
import {FriVerifier} from "./FriVerifier.sol";
import {MmcsVerifier} from "./MmcsVerifier.sol";

/// Verifies one 16-query half using packed rows and deduplicated pruned MMCS frontiers.
contract PQTCQueryVerifier {
    uint256 private constant HALF = 16;
    uint256 private constant GLOBAL_LOG_HEIGHT = 13;
    uint256 private constant TRACE_WIDTH = 190;
    uint256 private constant RANDOM_CODEWORDS = 4;
    uint256 private constant SALT_FIELDS = 8;
    uint256 private constant MULTIPLICATIVE_GENERATOR = 31;
    uint256 private constant REDUCTION_TERMS = 524;

    struct Context {
        Digest512[3] inputRoots; // random, trace, quotient
        Digest512[9] friRoots;
        uint256 zeta;
        uint256 friAlpha;
        uint256 finalPolynomial;
        uint256[9] friBetas;
        uint256[8] randomAtZeta;
        uint256[194] traceLocalAtZeta;
        uint256[194] traceNextAtZeta;
        uint256[128] quotientAtZeta;
        uint32[32] queryIndices;
    }

    struct ReductionState {
        uint32[16] indices;
        uint256[16] atXAtZeta;
        uint256[16] atXAtNext;
        uint256[16] inverseZeta;
        uint256[16] inverseNext;
        uint256[16] reduced;
        uint256[524] alphaPowers;
        uint256 zetaAggregate;
        uint256 nextAggregate;
    }

    error InvalidQuery();
    error InvalidFinalPolynomial();

    function verifyFirstHalf(bytes calldata proof, uint256 cursor, Context calldata context)
        external
        pure
        virtual
        returns (uint256 next, uint256 zetaAggregate, uint256 nextAggregate)
    {
        return _verifyHalf(proof, cursor, 0, context, 0, 0, true);
    }

    function verifySecondHalf(
        bytes calldata proof,
        uint256 cursor,
        Context calldata context,
        uint256 zetaAggregate,
        uint256 nextAggregate
    ) external pure returns (uint256 next) {
        (next,,) = _verifyHalf(proof, cursor, uint16(HALF), context, zetaAggregate, nextAggregate, false);
    }

    function _verifyHalf(
        bytes calldata proof,
        uint256 cursor,
        uint16 expectedStart,
        Context calldata context,
        uint256 zetaAggregate,
        uint256 nextAggregate,
        bool computeAggregates
    ) private pure returns (uint256 next, uint256 computedZeta, uint256 computedNext) {
        cursor = PQTCProofCodec.requireHalfHeader(proof, cursor, expectedStart);
        ReductionState memory state;
        for (uint256 q; q < HALF; ++q) {
            (state.indices[q], cursor) = CanonicalCodec.readU32(proof, cursor);
            if (state.indices[q] != context.queryIndices[uint256(expectedStart) + q]) revert InvalidQuery();
        }
        state.alphaPowers[0] = 1;
        for (uint256 i = 1; i < REDUCTION_TERMS; ++i) {
            state.alphaPowers[i] = Ext.mul(state.alphaPowers[i - 1], context.friAlpha);
        }
        if (computeAggregates) {
            (state.zetaAggregate, state.nextAggregate) = _openingAggregates(context, state.alphaPowers);
        } else {
            state.zetaAggregate = Ext.check(zetaAggregate);
            state.nextAggregate = Ext.check(nextAggregate);
        }
        _batchInverses(state.indices, context.zeta, state.inverseZeta, state.inverseNext);
        cursor = _inputBatch(proof, cursor, state, 0, context);
        cursor = _inputBatch(proof, cursor, state, 1, context);
        cursor = _inputBatch(proof, cursor, state, 2, context);
        for (uint256 q; q < HALF; ++q) {
            state.reduced[q] = Ext.add(
                Ext.mul(Ext.sub(state.zetaAggregate, state.atXAtZeta[q]), state.inverseZeta[q]),
                Ext.mul(Ext.sub(state.nextAggregate, state.atXAtNext[q]), state.inverseNext[q])
            );
        }
        next = _fri(proof, cursor, state.indices, state.reduced, context);
        computedZeta = state.zetaAggregate;
        computedNext = state.nextAggregate;
    }

    function _inputBatch(
        bytes calldata proof,
        uint256 cursor,
        ReductionState memory state,
        uint256 batch,
        Context calldata context
    ) internal pure virtual returns (uint256 next) {
        uint256 matrices = batch == 2 ? 16 : 1;
        uint256 rowWidth = batch == 0 ? 8 : batch == 1 ? TRACE_WIDTH + RANDOM_CODEWORDS : 8;
        uint256 rowsOffset = cursor;
        uint256 rowBytes = HALF * matrices * rowWidth * 4;
        uint256 saltBytes = HALF * matrices * SALT_FIELDS * 4;
        if (cursor > proof.length || rowBytes + saltBytes > proof.length - cursor) {
            revert CanonicalCodec.Truncated();
        }
        _requireCanonicalRange(proof, rowsOffset, rowBytes);
        cursor += rowBytes;
        uint256 saltsOffset = cursor;
        _requireCanonicalRange(proof, saltsOffset, saltBytes);
        cursor += saltBytes;
        MmcsVerifier.LeafWords memory leaves;
        for (uint256 q; q < HALF; ++q) {
            (leaves.lefts[q], leaves.rights[q]) =
                MmcsVerifier.hashBatchLeaf(proof, rowsOffset, saltsOffset, q, matrices, rowWidth);
            _reduceBatch(proof, rowsOffset, q, batch, state);
        }
        return MmcsVerifier.verifyPruned(
            context.inputRoots[batch], state.indices, leaves, GLOBAL_LOG_HEIGHT, HALF, proof, cursor
        );
    }

    function _reduceBatch(
        bytes calldata proof,
        uint256 rowsOffset,
        uint256 query,
        uint256 batch,
        ReductionState memory state
    ) internal pure virtual {
        uint256 rowWidth = batch == 0 ? 8 : batch == 1 ? TRACE_WIDTH + RANDOM_CODEWORDS : 128;
        uint256 start = rowsOffset + query * rowWidth * 4;
        if (batch == 0) {
            state.atXAtZeta[query] = _dotProductBase(proof, start, state.alphaPowers, 0, 8);
            return;
        }
        if (batch == 1) {
            state.atXAtZeta[query] = Ext.add(
                state.atXAtZeta[query],
                _dotProductBase(proof, start, state.alphaPowers, 8, TRACE_WIDTH + RANDOM_CODEWORDS)
            );
            state.atXAtNext[query] = _dotProductBase(
                proof, start, state.alphaPowers, 8 + TRACE_WIDTH + RANDOM_CODEWORDS, TRACE_WIDTH + RANDOM_CODEWORDS
            );
            return;
        }
        state.atXAtZeta[query] = Ext.add(
            state.atXAtZeta[query],
            _dotProductBase(proof, start, state.alphaPowers, 8 + 2 * (TRACE_WIDTH + RANDOM_CODEWORDS), 128)
        );
    }

    function _requireCanonicalRange(bytes calldata proof, uint256 offset, uint256 length) private pure {
        assembly ("memory-safe") {
            let position := add(proof.offset, offset)
            let end := add(position, length)
            for {} lt(position, end) { position := add(position, 4) } {
                let value := shr(224, calldataload(position))
                if iszero(lt(value, 2013265921)) {
                    mstore(0, shl(224, 0x65a81779))
                    mstore(4, value)
                    revert(0, 36)
                }
            }
        }
    }

    function _dotProductBase(
        bytes calldata proof,
        uint256 rowOffset,
        uint256[524] memory powers,
        uint256 powerOffset,
        uint256 count
    ) private pure returns (uint256 result) {
        assembly ("memory-safe") {
            let p := 2013265921
            let mask := 0xffffffff
            let input := add(proof.offset, rowOffset)
            let power := add(powers, mul(powerOffset, 0x20))
            let end := add(power, mul(count, 0x20))
            let a0 := 0
            let a1 := 0
            let a2 := 0
            let a3 := 0
            for {} lt(power, end) {
                power := add(power, 0x20)
                input := add(input, 4)
            } {
                let scalar := shr(224, calldataload(input))
                let coefficient := mload(power)
                a0 := addmod(a0, mulmod(and(coefficient, mask), scalar, p), p)
                a1 := addmod(a1, mulmod(and(shr(32, coefficient), mask), scalar, p), p)
                a2 := addmod(a2, mulmod(and(shr(64, coefficient), mask), scalar, p), p)
                a3 := addmod(a3, mulmod(and(shr(96, coefficient), mask), scalar, p), p)
            }
            result := or(or(a0, shl(32, a1)), or(shl(64, a2), shl(96, a3)))
        }
    }

    function _openingAggregates(Context calldata context, uint256[524] memory alphaPowers)
        private
        pure
        returns (uint256 zetaAggregate, uint256 nextAggregate)
    {
        for (uint256 column; column < 8; ++column) {
            zetaAggregate = Ext.add(zetaAggregate, Ext.mul(alphaPowers[column], context.randomAtZeta[column]));
        }
        for (uint256 column; column < TRACE_WIDTH + RANDOM_CODEWORDS; ++column) {
            zetaAggregate = Ext.add(zetaAggregate, Ext.mul(alphaPowers[8 + column], context.traceLocalAtZeta[column]));
            nextAggregate = Ext.add(
                nextAggregate,
                Ext.mul(alphaPowers[8 + TRACE_WIDTH + RANDOM_CODEWORDS + column], context.traceNextAtZeta[column])
            );
        }
        for (uint256 matrix; matrix < 16; ++matrix) {
            for (uint256 column; column < 8; ++column) {
                uint256 position = 8 + 2 * (TRACE_WIDTH + RANDOM_CODEWORDS) + matrix * 8 + column;
                zetaAggregate =
                    Ext.add(zetaAggregate, Ext.mul(alphaPowers[position], context.quotientAtZeta[matrix * 8 + column]));
            }
        }
    }

    function _batchInverses(
        uint32[16] memory indices,
        uint256 zeta,
        uint256[16] memory inverseZeta,
        uint256[16] memory inverseNext
    ) private pure {
        uint256[32] memory denominators;
        uint256[32] memory prefixes;
        uint256 zetaNext = Ext.mulBase(zeta, FriVerifier.twoAdicGenerator(8));
        uint256 product = 1;
        for (uint256 q; q < HALF; ++q) {
            uint256 point = _queryPoint(indices[q]);
            denominators[q] = Ext.sub(zeta, point);
            denominators[HALF + q] = Ext.sub(zetaNext, point);
        }
        for (uint256 i; i < HALF * 2; ++i) {
            prefixes[i] = product;
            product = Ext.mul(product, denominators[i]);
        }
        uint256 inverseProduct = Ext.inv(product);
        for (uint256 reverse = HALF * 2; reverse > 0; --reverse) {
            uint256 i = reverse - 1;
            uint256 inverse = Ext.mul(inverseProduct, prefixes[i]);
            inverseProduct = Ext.mul(inverseProduct, denominators[i]);
            if (i < HALF) inverseZeta[i] = inverse;
            else inverseNext[i - HALF] = inverse;
        }
    }

    function _fri(
        bytes calldata proof,
        uint256 cursor,
        uint32[16] memory indices,
        uint256[16] memory folded,
        Context calldata context
    ) internal pure virtual returns (uint256 next) {
        for (uint256 round; round < 9; ++round) {
            cursor = _friRound(proof, cursor, indices, folded, context, round);
        }
        for (uint256 q; q < HALF; ++q) {
            if (folded[q] != context.finalPolynomial) revert InvalidFinalPolynomial();
        }
        return cursor;
    }

    function _friRound(
        bytes calldata proof,
        uint256 cursor,
        uint32[16] memory indices,
        uint256[16] memory folded,
        Context calldata context,
        uint256 round
    ) private pure returns (uint256) {
        uint256[16] memory siblings;
        for (uint256 q; q < HALF; ++q) {
            (siblings[q], cursor) = _readExtension(proof, cursor);
        }
        uint256 saltsOffset = cursor;
        uint256 saltBytes = HALF * SALT_FIELDS * 4;
        if (cursor > proof.length || saltBytes > proof.length - cursor) revert CanonicalCodec.Truncated();
        _requireCanonicalRange(proof, saltsOffset, saltBytes);
        cursor += saltBytes;
        uint32[16] memory parentIndices;
        MmcsVerifier.LeafWords memory leaves;
        uint256 logFoldedHeight = GLOBAL_LOG_HEIGHT - round - 1;
        for (uint256 q; q < HALF; ++q) {
            uint256 index = indices[q];
            (leaves.lefts[q], leaves.rights[q]) =
                MmcsVerifier.hashFriLeafWords(folded[q], siblings[q], index, proof, saltsOffset + q * SALT_FIELDS * 4);
            parentIndices[q] = uint32(index >> 1);
        }
        uint32[16] memory inverseTwoXs = _inverseFoldPoints(parentIndices, HALF, logFoldedHeight);
        cursor = MmcsVerifier.verifyPruned(
            context.friRoots[round], parentIndices, leaves, logFoldedHeight, HALF, proof, cursor
        );
        for (uint256 q; q < HALF; ++q) {
            uint256 index = indices[q];
            uint256 low = index & 1 == 0 ? folded[q] : siblings[q];
            uint256 high = index & 1 == 0 ? siblings[q] : folded[q];
            indices[q] = parentIndices[q];
            folded[q] = _fold(context.friBetas[round], low, high, inverseTwoXs[q]);
        }
        return cursor;
    }

    function _queryPoint(uint256 index) private pure returns (uint256) {
        uint256 generator = FriVerifier.twoAdicGenerator(GLOBAL_LOG_HEIGHT);
        return BabyBear.mul(
            MULTIPLICATIVE_GENERATOR, BabyBear.pow(generator, FriVerifier.reverseBits(index, GLOBAL_LOG_HEIGHT))
        );
    }

    function _fold(uint256 beta, uint256 low, uint256 high, uint256 inverseTwoX) private pure returns (uint256) {
        uint256 evenPart = Ext.mulBase(Ext.add(low, high), 1_006_632_961);
        uint256 oddPart = Ext.mul(Ext.mulBase(Ext.sub(low, high), inverseTwoX), beta);
        return Ext.add(evenPart, oddPart);
    }

    function _inverseFoldPoints(uint32[16] memory parentIndices, uint256 count, uint256 logHeight)
        private
        pure
        returns (uint32[16] memory inverses)
    {
        uint32[16] memory points;
        uint32[16] memory prefixes;
        uint256 generator = FriVerifier.twoAdicGenerator(logHeight + 1);
        uint256 order = uint256(1) << (logHeight + 1);
        uint256 exponentSum;
        uint256 product = 1;
        for (uint256 q; q < count; ++q) {
            uint256 exponent = FriVerifier.reverseBits(parentIndices[q], logHeight);
            uint32 point = uint32(BabyBear.pow(generator, exponent));
            points[q] = point;
            prefixes[q] = uint32(product);
            product = BabyBear.mul(product, point);
            exponentSum = (exponentSum + exponent) & (order - 1);
        }
        uint256 inverseProduct = BabyBear.pow(generator, (order - exponentSum) & (order - 1));
        for (uint256 reverse = count; reverse > 0; --reverse) {
            uint256 q = reverse - 1;
            inverses[q] = uint32(BabyBear.mul(1_006_632_961, BabyBear.mul(inverseProduct, prefixes[q])));
            inverseProduct = BabyBear.mul(inverseProduct, points[q]);
        }
    }

    function _readExtension(bytes calldata proof, uint256 cursor) private pure returns (uint256 value, uint256 next) {
        if (cursor > proof.length || 16 > proof.length - cursor) revert CanonicalCodec.Truncated();
        assembly ("memory-safe") {
            let word := calldataload(add(proof.offset, cursor))
            let mask := 0xffffffff
            let c0 := shr(224, word)
            let c1 := and(shr(192, word), mask)
            let c2 := and(shr(160, word), mask)
            let c3 := and(shr(128, word), mask)
            if iszero(and(and(lt(c0, 2013265921), lt(c1, 2013265921)), and(lt(c2, 2013265921), lt(c3, 2013265921)))) {
                mstore(0, shl(224, 0x65a81779))
                let badValue := c0
                if and(lt(c0, 2013265921), iszero(lt(c1, 2013265921))) { badValue := c1 }
                if and(and(lt(c0, 2013265921), lt(c1, 2013265921)), iszero(lt(c2, 2013265921))) {
                    badValue := c2
                }
                if and(
                    and(and(lt(c0, 2013265921), lt(c1, 2013265921)), lt(c2, 2013265921)),
                    iszero(lt(c3, 2013265921))
                ) {
                    badValue := c3
                }
                mstore(4, badValue)
                revert(0, 36)
            }
            value := or(or(c0, shl(32, c1)), or(shl(64, c2), shl(96, c3)))
        }
        next = cursor + 16;
    }
}
```

</details>

## `contracts/src/verifier/StarkOodVerifier.sol`

- Bytes: 4,709
- SHA-256: `9f44097ddc797d3bf0841584d68983696952aecaeaac79e15021115ed2251828`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBear} from "../libraries/BabyBear.sol";
import {BabyBearExt4Packed as Ext} from "../libraries/BabyBearExt4Packed.sol";
import {FriVerifier} from "./FriVerifier.sol";

/// Fixed-domain OOD arithmetic for the v0.2 256-row hiding withdrawal AIR.
library StarkOodVerifier {
    uint256 private constant TRACE_LOG_SIZE = 8;
    uint256 private constant QUOTIENT_LOG_SIZE = 12;
    uint256 private constant QUOTIENT_CHUNK_LOG_SIZE = 8;
    uint256 private constant QUOTIENT_CHUNKS = 16;
    uint256 private constant MULTIPLICATIVE_GENERATOR = 31;

    struct Selectors {
        uint256 isFirst;
        uint256 isLast;
        uint256 isTransition;
        uint256 invVanishing;
    }

    error InvalidQuotientShape();
    error OodEvaluationMismatch();

    function selectors(uint256 zeta) internal pure returns (Selectors memory result) {
        uint256 subgroupGenerator = FriVerifier.twoAdicGenerator(TRACE_LOG_SIZE);
        uint256 inverseGenerator = BabyBear.inv(subgroupGenerator);
        uint256 vanishing = Ext.sub(Ext.pow(zeta, uint256(1) << TRACE_LOG_SIZE), 1);
        uint256 firstDenominator = Ext.sub(zeta, 1);
        uint256 lastDenominator = Ext.sub(zeta, inverseGenerator);
        uint256 inverseProduct = Ext.inv(Ext.mul(Ext.mul(firstDenominator, lastDenominator), vanishing));
        result.isFirst = Ext.mul(vanishing, Ext.mul(Ext.mul(lastDenominator, vanishing), inverseProduct));
        result.isLast = Ext.mul(vanishing, Ext.mul(Ext.mul(firstDenominator, vanishing), inverseProduct));
        result.isTransition = lastDenominator;
        result.invVanishing = Ext.mul(Ext.mul(firstDenominator, lastDenominator), inverseProduct);
    }

    /// Each of 16 quotient chunks is represented by four extension-valued
    /// openings of its base-field coefficient polynomials.
    function recomposeQuotient(uint256[] memory quotientOpenings, uint256 zeta)
        internal
        pure
        returns (uint256 quotient)
    {
        if (quotientOpenings.length != QUOTIENT_CHUNKS * 4) revert InvalidQuotientShape();
        uint256 quotientGenerator = FriVerifier.twoAdicGenerator(QUOTIENT_LOG_SIZE);
        uint256[16] memory shifts;
        uint256[16] memory inverseShifts;
        uint256 shift = MULTIPLICATIVE_GENERATOR;
        for (uint256 i = 0; i < QUOTIENT_CHUNKS; i++) {
            shifts[i] = shift;
            inverseShifts[i] = BabyBear.inv(shift);
            shift = BabyBear.mul(shift, quotientGenerator);
        }
        uint256[16] memory vanishingAtZeta;
        uint256[17] memory prefixes;
        prefixes[0] = 1;
        for (uint256 i = 0; i < QUOTIENT_CHUNKS; i++) {
            vanishingAtZeta[i] = _vanishingWithInverse(zeta, inverseShifts[i], QUOTIENT_CHUNK_LOG_SIZE);
            prefixes[i + 1] = Ext.mul(prefixes[i], vanishingAtZeta[i]);
        }
        uint256 suffix = 1;
        for (uint256 reverse = QUOTIENT_CHUNKS; reverse > 0; reverse--) {
            uint256 i = reverse - 1;
            uint256 numerator = Ext.mul(prefixes[i], suffix);
            suffix = Ext.mul(vanishingAtZeta[i], suffix);
            uint256 denominator = 1;
            for (uint256 j = 0; j < QUOTIENT_CHUNKS; j++) {
                if (j == i) continue;
                uint256 ratio = BabyBear.mul(shifts[i], inverseShifts[j]);
                denominator = BabyBear.mul(
                    denominator, BabyBear.sub(BabyBear.pow(ratio, uint256(1) << QUOTIENT_CHUNK_LOG_SIZE), 1)
                );
            }
            uint256 weight = Ext.mulBase(numerator, BabyBear.inv(denominator));
            uint256 chunk = quotientOpenings[i * 4];
            uint256 basis = uint256(1) << 32;
            for (uint256 coefficient = 1; coefficient < 4; coefficient++) {
                chunk = Ext.add(chunk, Ext.mul(basis, quotientOpenings[i * 4 + coefficient]));
                basis = Ext.mul(basis, uint256(1) << 32);
            }
            quotient = Ext.add(quotient, Ext.mul(weight, chunk));
        }
    }

    function requireValid(uint256 foldedConstraints, uint256[] memory quotientOpenings, uint256 zeta) internal pure {
        Selectors memory domainSelectors = selectors(zeta);
        uint256 expected = recomposeQuotient(quotientOpenings, zeta);
        if (Ext.mul(foldedConstraints, domainSelectors.invVanishing) != expected) {
            revert OodEvaluationMismatch();
        }
    }

    function _vanishingWithInverse(uint256 point, uint256 inverseShift, uint256 logSize)
        private
        pure
        returns (uint256)
    {
        return Ext.sub(Ext.pow(Ext.mulBase(point, inverseShift), uint256(1) << logSize), 1);
    }
}
```

</details>

## `contracts/test/AirEvaluator.t.sol`

- Bytes: 6,849
- SHA-256: `b86a5482e0ac235548678866ffb97025e7e3a39f0ab584fafd175e09325d97ca`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {BabyBear} from "../src/libraries/BabyBear.sol";
import {AirEvaluatorPoseidon} from "../src/verifier/AirEvaluatorPoseidon.sol";
import {PQTCAirStageVerifier} from "../src/verifier/PQTCAirStageVerifier.sol";
import {StarkOodVerifier} from "../src/verifier/StarkOodVerifier.sol";

contract PoseidonAirHarness {
    function evaluate(
        uint256[] calldata localRaw,
        uint256[] calldata nextRaw,
        uint256[] calldata publicRaw,
        uint256 isFirst,
        uint256 isLast,
        uint256 isTransition,
        uint256 alpha
    ) external pure returns (uint256) {
        uint256[] memory local = localRaw;
        uint256[] memory next = nextRaw;
        uint256[] memory publicValues = publicRaw;
        return AirEvaluatorPoseidon.evaluate(local, next, publicValues, isFirst, isLast, isTransition, alpha);
    }

    function evaluateRange(
        uint256[] calldata localRaw,
        uint256[] calldata nextRaw,
        uint256[] calldata publicRaw,
        uint256 isFirst,
        uint256 isLast,
        uint256 isTransition,
        uint256 alpha,
        uint256 accumulator,
        uint8 start,
        uint8 end
    ) external pure returns (uint256) {
        uint256[] memory local = localRaw;
        uint256[] memory next = nextRaw;
        uint256[] memory publicValues = publicRaw;
        return AirEvaluatorPoseidon.evaluateRange(
            local, next, publicValues, isFirst, isLast, isTransition, alpha, accumulator, start, end
        );
    }
}

contract OodHarness {
    function selectors(uint256 zeta) external pure returns (uint256, uint256, uint256, uint256) {
        StarkOodVerifier.Selectors memory selected = StarkOodVerifier.selectors(zeta);
        return (selected.isFirst, selected.isLast, selected.isTransition, selected.invVanishing);
    }
}

contract AirEvaluatorTest is Test {
    PoseidonAirHarness private harness;

    function setUp() external {
        harness = new PoseidonAirHarness();
    }

    function testWithdrawalAirHasExactly190ColumnsAnd64PublicValues() external view {
        uint256[] memory local = new uint256[](190);
        uint256[] memory next = new uint256[](190);
        uint256[] memory publicValues = new uint256[](64);
        local[158] = 1; // nullifier selector; the other four row-kind selectors are zero.
        uint256 folded = harness.evaluate(local, next, publicValues, 0, 0, 0, 7);
        publicValues[0] = 1;
        uint256 mutated = harness.evaluate(local, next, publicValues, 0, 0, 0, 7);
        assertNotEq(folded, mutated, "64-field statement must be constrained by the AIR");
    }

    function testSegmentedEvaluationPreservesHornerOrder() external view {
        uint256[] memory local = new uint256[](190);
        uint256[] memory next = new uint256[](190);
        uint256[] memory publicValues = new uint256[](64);
        local[158] = 1;
        local[174] = 9;
        next[189] = 11;
        publicValues[7] = 13;
        uint256 whole = harness.evaluate(local, next, publicValues, 17, 19, 23, 29);
        uint256 first = harness.evaluateRange(local, next, publicValues, 17, 19, 23, 29, 0, 0, 3);
        uint256 second = harness.evaluateRange(local, next, publicValues, 17, 19, 23, 29, first, 3, 7);
        assertEq(second, whole);
    }

    function testRejectsLegacy230ColumnWithdrawalRows() external {
        uint256[] memory local = new uint256[](230);
        uint256[] memory next = new uint256[](230);
        uint256[] memory publicValues = new uint256[](64);
        vm.expectRevert(AirEvaluatorPoseidon.InvalidInputWidth.selector);
        harness.evaluate(local, next, publicValues, 0, 0, 0, 7);
    }

    function testRejectsLegacy128PublicValueStatement() external {
        uint256[] memory local = new uint256[](190);
        uint256[] memory next = new uint256[](190);
        uint256[] memory publicValues = new uint256[](128);
        vm.expectRevert(AirEvaluatorPoseidon.InvalidInputWidth.selector);
        harness.evaluate(local, next, publicValues, 0, 0, 0, 7);
    }

    function testAirEntryRejectsNoncanonicalOpenedField() external {
        PQTCAirStageVerifier verifier = new PQTCAirStageVerifier();
        uint256[] memory local = new uint256[](190);
        uint256[] memory next = new uint256[](190);
        uint256[] memory quotient = new uint256[](64);
        uint32[64] memory publicValues;
        local[0] = 2_013_265_921;
        vm.expectRevert(abi.encodeWithSelector(BabyBear.NonCanonicalField.selector, uint256(2_013_265_921)));
        verifier.verify(local, next, quotient, publicValues, 2, 3);
    }

    function testRustDifferentialAirVector() external view {
        string memory json = vm.readFile("test-vectors/verifier/v3.json");
        assertEq(vm.parseJsonUint(json, ".version"), 3);
        uint256[] memory local = _packedArray(json, ".air.local", 190);
        uint256[] memory next = _packedArray(json, ".air.next", 190);
        uint256[] memory publicValues = _packedArray(json, ".air.public_values", 64);
        uint256 actual = harness.evaluate(
            local,
            next,
            publicValues,
            _packed(json, ".air.is_first"),
            _packed(json, ".air.is_last"),
            _packed(json, ".air.is_transition"),
            _packed(json, ".air.alpha")
        );
        assertEq(actual, _packed(json, ".air.expected"), "Solidity AIR order differs from Rust");
    }

    function testTraceSelectorsUse256RowDomain() external {
        OodHarness ood = new OodHarness();
        (uint256 first, uint256 last, uint256 transition, uint256 inverseVanishing) = ood.selectors(2);
        assertTrue(first != 0);
        assertTrue(last != 0);
        assertTrue(transition != 0);
        assertTrue(inverseVanishing != 0);
    }

    function _packedArray(string memory json, string memory path, uint256 expectedLength)
        private
        pure
        returns (uint256[] memory packed)
    {
        uint256[][] memory coefficients = abi.decode(vm.parseJson(json, path), (uint256[][]));
        assertEq(coefficients.length, expectedLength);
        packed = new uint256[](expectedLength);
        for (uint256 i; i < expectedLength; ++i) {
            assertEq(coefficients[i].length, 4);
            packed[i] = coefficients[i][0] | (coefficients[i][1] << 32) | (coefficients[i][2] << 64)
                | (coefficients[i][3] << 96);
        }
    }

    function _packed(string memory json, string memory path) private pure returns (uint256 value) {
        uint256[] memory coefficients = vm.parseJsonUintArray(json, path);
        assertEq(coefficients.length, 4);
        value = coefficients[0] | (coefficients[1] << 32) | (coefficients[2] << 64) | (coefficients[3] << 96);
    }
}
```

</details>

## `contracts/test/BabyBear.t.sol`

- Bytes: 1,915
- SHA-256: `00cc49cfbd3fd201a2e0019cbfc4a120ef298fbbe8f1f7311e64c96cefe878d9`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {BabyBear} from "../src/libraries/BabyBear.sol";
import {BabyBearExt4, BabyBearExt4Value} from "../src/libraries/BabyBearExt4.sol";

contract BabyBearHarness {
    function add(uint256 a, uint256 b) external pure returns (uint256) {
        return BabyBear.add(a, b);
    }

    function sub(uint256 a, uint256 b) external pure returns (uint256) {
        return BabyBear.sub(a, b);
    }

    function mul(uint256 a, uint256 b) external pure returns (uint256) {
        return BabyBear.mul(a, b);
    }

    function extMul(BabyBearExt4Value calldata a, BabyBearExt4Value calldata b)
        external
        pure
        returns (BabyBearExt4Value memory)
    {
        return BabyBearExt4.mul(a, b);
    }
}

contract BabyBearTest is Test {
    uint256 private constant P = 2_013_265_921;
    BabyBearHarness private harness;

    function setUp() external {
        harness = new BabyBearHarness();
    }

    function testBoundaryArithmetic() external view {
        assertEq(harness.add(P - 1, P - 1), P - 2);
        assertEq(harness.sub(0, 1), P - 1);
        assertEq(harness.mul(P - 1, P - 1), 1);
    }

    function testExtMultiplicationReducesX4ToEleven() external view {
        BabyBearExt4Value memory x3 = BabyBearExt4Value(0, 0, 0, 1);
        BabyBearExt4Value memory x = BabyBearExt4Value(0, 1, 0, 0);
        BabyBearExt4Value memory result = harness.extMul(x3, x);
        assertEq(result.c0, 11);
        assertEq(result.c1, 0);
        assertEq(result.c2, 0);
        assertEq(result.c3, 0);
    }

    function testGasBaseFieldOperations() external {
        uint256 beforeGas = gasleft();
        harness.add(1_234_567, 7_654_321);
        harness.mul(1_234_567, 7_654_321);
        emit log_named_uint("base field add+mul gas", beforeGas - gasleft());
    }
}
```

</details>

## `contracts/test/HashVectors.t.sol`

- Bytes: 6,780
- SHA-256: `c1fb6dfe291acb0f7854ff1205d87ab343bcf00618e33fbf8724dca71c0603a3`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {Digest512} from "../src/libraries/Digest512.sol";
import {P2BB512} from "../src/libraries/P2BB512.sol";
import {PQTCApplicationHash} from "../src/libraries/PQTCApplicationHash.sol";

contract HashVectorsTest is Test {
    uint8 private constant DEPTH = 20;
    Digest512[20] private filledSubtrees;
    Digest512[21] private zeros;

    function testAllThousandV3ApplicationVectorsAndRoots() external {
        string memory json = vm.readFile("test-vectors/hash/v3.json");
        assertEq(vm.parseJsonUint(json, ".version"), 3);
        assertEq(vm.parseJsonUint(json, ".count"), 1_000);
        string memory first = ".vectors[0]";
        Digest512 memory parameterId = parseDigest(json, string.concat(first, ".parameter_id"));
        Digest512 memory poolScope = PQTCApplicationHash.scope(
            11_155_111, 0x1111111111111111111111111111111111111111, 0.001 ether, DEPTH, 3, parameterId
        );
        assertDigest(poolScope, parseDigest(json, string.concat(first, ".scope")));
        zeros[0] = PQTCApplicationHash.emptyLeaf(poolScope);
        for (uint8 level = 0; level < DEPTH; ++level) {
            filledSubtrees[level] = zeros[level];
            zeros[level + 1] = PQTCApplicationHash.merkleNode(level, zeros[level], zeros[level]);
        }

        for (uint256 i = 0; i < 1_000; ++i) {
            string memory base = string.concat(".vectors[", vm.toString(i), "]");
            bytes32 secret = vm.parseJsonBytes32(json, string.concat(base, ".nullifier_secret"));
            bytes32 trapdoor = vm.parseJsonBytes32(json, string.concat(base, ".trapdoor"));
            Digest512 memory noteCommitment = PQTCApplicationHash.commitment(poolScope, secret, trapdoor);
            assertDigest(noteCommitment, parseDigest(json, string.concat(base, ".commitment")));
            assertDigest(
                PQTCApplicationHash.nullifierHash(poolScope, secret),
                parseDigest(json, string.concat(base, ".nullifier_hash"))
            );
            assertDigest(
                PQTCApplicationHash.payoutDigest(
                    parseAddress(json, string.concat(base, ".recipient")),
                    parseAddress(json, string.concat(base, ".relayer")),
                    parseUint256(json, string.concat(base, ".fee"))
                ),
                parseDigest(json, string.concat(base, ".payout_digest"))
            );
            assertDigest(zeros[0], parseDigest(json, string.concat(base, ".zero_leaf")));
            assertDigest(
                PQTCApplicationHash.merkleNode(0, noteCommitment, zeros[0]),
                parseDigest(json, string.concat(base, ".level_zero_node"))
            );
            assertDigest(
                insert(noteCommitment, uint32(i)), parseDigest(json, string.concat(base, ".root_after_insert"))
            );
        }
    }

    function testNotePreimagesRequireCanonicalBigEndianU32Limbs() external {
        Digest512 memory poolScope = Digest512(bytes32(0), bytes32(0));
        bytes32 noncanonicalFirst = bytes32(uint256(2_013_265_921) << 224);
        bytes memory firstError = abi.encodeWithSelector(
            PQTCApplicationHash.NonCanonicalNotePreimageLimb.selector, uint256(0), uint256(2_013_265_921)
        );

        vm.expectRevert(firstError);
        this.hashCommitment(poolScope, noncanonicalFirst, bytes32(0));
        vm.expectRevert(firstError);
        this.hashNullifier(poolScope, noncanonicalFirst);

        bytes32 noncanonicalLast = bytes32(uint256(2_013_265_921));
        vm.expectRevert(
            abi.encodeWithSelector(
                PQTCApplicationHash.NonCanonicalNotePreimageLimb.selector, uint256(7), uint256(2_013_265_921)
            )
        );
        this.hashNullifier(poolScope, noncanonicalLast);
        Digest512 memory canonicalBoundary =
            PQTCApplicationHash.nullifierHash(poolScope, bytes32(uint256(2_013_265_920)));
        P2BB512.toFields(canonicalBoundary);

        bytes32 noncanonicalTrapdoor = bytes32(uint256(2_013_265_921) << 128);
        vm.expectRevert(
            abi.encodeWithSelector(
                PQTCApplicationHash.NonCanonicalNotePreimageLimb.selector, uint256(11), uint256(2_013_265_921)
            )
        );
        this.hashCommitment(poolScope, bytes32(0), noncanonicalTrapdoor);
    }

    function hashCommitment(Digest512 calldata poolScope, bytes32 nullifierSecret, bytes32 trapdoor)
        external
        pure
        returns (Digest512 memory)
    {
        return PQTCApplicationHash.commitment(poolScope, nullifierSecret, trapdoor);
    }

    function hashNullifier(Digest512 calldata poolScope, bytes32 nullifierSecret)
        external
        pure
        returns (Digest512 memory)
    {
        return PQTCApplicationHash.nullifierHash(poolScope, nullifierSecret);
    }

    function insert(Digest512 memory leaf, uint32 index) private returns (Digest512 memory current) {
        current = leaf;
        for (uint8 level = 0; level < DEPTH; ++level) {
            if (index & 1 == 0) {
                filledSubtrees[level] = current;
                current = PQTCApplicationHash.merkleNode(level, current, zeros[level]);
            } else {
                current = PQTCApplicationHash.merkleNode(level, filledSubtrees[level], current);
            }
            index >>= 1;
        }
    }

    function parseDigest(string memory json, string memory key) private pure returns (Digest512 memory value) {
        bytes memory encoded = vm.parseJsonBytes(json, key);
        assertEq(encoded.length, 64);
        assembly ("memory-safe") {
            mstore(value, mload(add(encoded, 0x20)))
            mstore(add(value, 0x20), mload(add(encoded, 0x40)))
        }
    }

    function parseAddress(string memory json, string memory key) private pure returns (address value) {
        bytes memory encoded = vm.parseJsonBytes(json, key);
        assertEq(encoded.length, 20);
        assembly ("memory-safe") { value := shr(96, mload(add(encoded, 0x20))) }
    }

    function parseUint256(string memory json, string memory key) private pure returns (uint256 value) {
        bytes memory encoded = vm.parseJsonBytes(json, key);
        assertEq(encoded.length, 32);
        assembly ("memory-safe") { value := mload(add(encoded, 0x20)) }
    }

    function assertDigest(Digest512 memory actual, Digest512 memory expected) private pure {
        uint32[16] memory actualFields = P2BB512.toFields(actual);
        uint32[16] memory expectedFields = P2BB512.toFields(expected);
        for (uint256 i = 0; i < 16; ++i) {
            assertEq(actualFields[i], expectedFields[i], "canonical digest limb");
        }
    }
}
```

</details>

## `contracts/test/P2BB512.t.sol`

- Bytes: 6,711
- SHA-256: `12de6c8ff8eb312c02e01be265dcf16d4307f2ebd5af6ed19f9205019cb19bba`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {Digest512} from "../src/libraries/Digest512.sol";
import {P2BB512} from "../src/libraries/P2BB512.sol";

contract P2BB512Harness {
    function permute(uint32[16] memory state) external pure returns (uint32[16] memory) {
        return P2BB512.permute(state);
    }

    function toFields(Digest512 memory digest) external pure returns (uint32[16] memory) {
        return P2BB512.toFields(digest);
    }

    function fromFields(uint32[16] memory fields) external pure returns (Digest512 memory) {
        return P2BB512.fromFields(fields);
    }

    function hashFields16(uint8 domainTag, uint32[16] memory elements) external pure returns (Digest512 memory) {
        return P2BB512.hashFields16(domainTag, elements);
    }

    function hashU16s16(uint8 domainTag, uint16[16] memory elements) external pure returns (Digest512 memory) {
        return P2BB512.hashU16s16(domainTag, elements);
    }

    function merkleNode(uint8 level, Digest512 memory left, Digest512 memory right)
        external
        pure
        returns (Digest512 memory)
    {
        return P2BB512.merkleNode(level, left, right);
    }

    function depth20(Digest512 memory leaf, Digest512[20] memory siblings)
        external
        pure
        returns (Digest512 memory current)
    {
        current = leaf;
        for (uint256 level = 0; level < 20; ++level) {
            current = P2BB512.merkleNode(uint8(level), current, siblings[level]);
        }
    }
}

contract P2BB512Test is Test {
    uint32 private constant P = 2_013_265_921;
    P2BB512Harness private harness;

    function setUp() external {
        harness = new P2BB512Harness();
    }

    /// Vector copied from the pinned Plonky3 BabyBear poseidon2.rs
    /// test_default_babybear_poseidon2_width_16 test.
    function testPinnedUpstreamPermutationVector() external view {
        uint32[16] memory input = [
            uint32(894848333),
            1437655012,
            1200606629,
            1690012884,
            71131202,
            1749206695,
            1717947831,
            120589055,
            19776022,
            42382981,
            1831865506,
            724844064,
            171220207,
            1299207443,
            227047920,
            1783754913
        ];
        uint32[16] memory expected = [
            uint32(516096821),
            90309867,
            1101817252,
            1660784290,
            360715097,
            1789519026,
            1788910906,
            563338433,
            319524748,
            1741414159,
            1650859320,
            894311162,
            1121347488,
            1692793758,
            1052633829,
            1344246938
        ];

        uint32[16] memory actual = harness.permute(input);
        for (uint256 i = 0; i < 16; ++i) {
            assertEq(actual[i], expected[i], "permutation limb");
        }
    }

    function testDigestBigEndianRoundTrip() external view {
        uint32[16] memory fields;
        for (uint32 i = 0; i < 16; ++i) {
            fields[i] = i;
        }

        Digest512 memory digest = harness.fromFields(fields);
        assertEq(digest.left, 0x0000000000000001000000020000000300000004000000050000000600000007);
        assertEq(digest.right, 0x00000008000000090000000a0000000b0000000c0000000d0000000e0000000f);

        uint32[16] memory decoded = harness.toFields(digest);
        for (uint256 i = 0; i < 16; ++i) {
            assertEq(decoded[i], fields[i], "digest limb");
        }
    }

    function testRejectsNonCanonicalDigestLimb() external {
        Digest512 memory malformed = Digest512(bytes32(uint256(P) << 224), bytes32(0));
        vm.expectRevert(abi.encodeWithSelector(P2BB512.NonCanonicalDigestLimb.selector, 0, P));
        harness.toFields(malformed);
    }

    function testMerkleRejectsNonCanonicalDigestLimb() external {
        Digest512 memory malformed = Digest512(bytes32(uint256(P) << 192), bytes32(0));
        Digest512 memory zero = Digest512(bytes32(0), bytes32(0));
        vm.expectRevert(abi.encodeWithSelector(P2BB512.NonCanonicalDigestLimb.selector, 1, P));
        harness.merkleNode(0, malformed, zero);
    }

    function testRejectsNonCanonicalPermutationInput() external {
        uint32[16] memory input;
        input[9] = P;
        vm.expectRevert(abi.encodeWithSelector(P2BB512.NonCanonicalFieldElement.selector, 9, P));
        harness.permute(input);
    }

    function testDomainAndLengthSeparation() external view {
        uint32[16] memory fields;
        uint16[16] memory u16s;
        for (uint16 i = 0; i < 16; ++i) {
            fields[i] = i + 1;
            u16s[i] = i + 1;
        }

        Digest512 memory fieldDomainA = harness.hashFields16(0x10, fields);
        Digest512 memory fieldDomainB = harness.hashFields16(0x11, fields);
        Digest512 memory shortEncoding = harness.hashU16s16(0x10, u16s);
        _assertDifferent(fieldDomainA, fieldDomainB, "domain tag must separate");
        _assertDifferent(fieldDomainA, shortEncoding, "payload byte length must separate");
    }

    function testMerkleAuxLevelSeparation() external view {
        uint32[16] memory leftFields;
        uint32[16] memory rightFields;
        for (uint32 i = 0; i < 16; ++i) {
            leftFields[i] = i + 1;
            rightFields[i] = i + 101;
        }
        Digest512 memory left = harness.fromFields(leftFields);
        Digest512 memory right = harness.fromFields(rightFields);

        Digest512 memory level0 = harness.merkleNode(0, left, right);
        Digest512 memory level1 = harness.merkleNode(1, left, right);
        _assertDifferent(level0, level1, "Merkle aux level must separate");
    }

    /// @dev Enforces the per-transaction budget for one complete depth-20 path.
    function testGasDepth20HashCeiling() external {
        uint32[16] memory fields;
        for (uint32 i = 0; i < 16; ++i) {
            fields[i] = i;
        }
        Digest512 memory leaf = harness.fromFields(fields);
        Digest512[20] memory siblings;
        for (uint256 i = 0; i < 20; ++i) {
            siblings[i] = leaf;
        }

        uint256 beforeGas = gasleft();
        harness.depth20(leaf, siblings);
        uint256 gasUsed = beforeGas - gasleft();
        emit log_named_uint("P2BB512 depth-20 hash gas", gasUsed);
        assertLe(gasUsed, 15_000_000, "depth-20 Merkle hashing exceeds 15M gas");
    }

    function _assertDifferent(Digest512 memory a, Digest512 memory b, string memory reason) private pure {
        assertTrue(a.left != b.left || a.right != b.right, reason);
    }
}
```

</details>

## `contracts/test/PQTCClassicPool.t.sol`

- Bytes: 18,661
- SHA-256: `0f7b47328a3668a5bb0caf1ef0459f0e39e59d2155004a30d529320e5c873d6e`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {PQTCClassicPool, IPQTCVerificationRegistry} from "../src/PQTCClassicPool.sol";
import {Digest512} from "../src/libraries/Digest512.sol";
import {P2BB512} from "../src/libraries/P2BB512.sol";
import {PQTCApplicationHash} from "../src/libraries/PQTCApplicationHash.sol";

contract PoolMockRegistry is IPQTCVerificationRegistry {
    struct Checkpoint {
        address consumer;
        Digest512 parameterId;
        bytes32 statementKey;
        bool pending;
    }

    mapping(bytes32 => Checkpoint) internal checkpoints;

    function beginVerification(
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata proofPartA
    ) external returns (bytes32 verificationId) {
        for (uint256 i = 0; i < 64; ++i) {
            if (publicValues[i] >= 2_013_265_921) revert();
        }
        bytes32 statementKey =
            keccak256(abi.encode(bytes32("PQTC.V3.STATEMENT"), parameterId.left, parameterId.right, publicValues));
        bytes32 coreProofId = keccak256(abi.encode(bytes32("PQTC.V3.PROOF"), statementKey, keccak256(proofPartA)));
        verificationId = keccak256(abi.encode(bytes32("PQTC.V3.VERIFICATION"), coreProofId, msg.sender));
        checkpoints[verificationId] = Checkpoint(msg.sender, parameterId, statementKey, true);
    }

    function pending(bytes32 proofId) external view returns (bool) {
        return checkpoints[proofId].pending;
    }

    function consumer(bytes32 verificationId) external view returns (address) {
        return checkpoints[verificationId].consumer;
    }

    function completeVerification(
        bytes32 proofId,
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata proofPartB
    ) external returns (bool) {
        Checkpoint storage checkpoint = checkpoints[proofId];
        if (
            !checkpoint.pending || checkpoint.consumer != msg.sender || checkpoint.parameterId.left != parameterId.left
                || checkpoint.parameterId.right != parameterId.right
                || keccak256(proofPartB) != keccak256("valid-part-b")
        ) return false;
        for (uint256 i = 0; i < 64; ++i) {
            if (publicValues[i] >= 2_013_265_921) return false;
        }
        bytes32 statementKey =
            keccak256(abi.encode(bytes32("PQTC.V3.STATEMENT"), parameterId.left, parameterId.right, publicValues));
        if (statementKey != checkpoint.statementKey) return false;

        delete checkpoints[proofId];
        return true;
    }
}

contract PaymentReceiver {
    receive() external payable {}
}

contract RejectPayment {
    receive() external payable {
        revert();
    }
}


contract ReentrantRecipient {
    PQTCClassicPool private pool;
    bytes32 private nestedProofId;
    PQTCClassicPool.Withdrawal private nestedWithdrawal;
    bool public attempted;
    bool public nestedSucceeded;
    bytes4 public nestedError;

    function arm(PQTCClassicPool pool_, bytes32 proofId_, PQTCClassicPool.Withdrawal memory withdrawal_) external {
        pool = pool_;
        nestedProofId = proofId_;
        nestedWithdrawal = withdrawal_;
    }

    receive() external payable {
        attempted = true;
        bytes memory callData =
            abi.encodeCall(PQTCClassicPool.withdraw, (nestedWithdrawal, nestedProofId, bytes("valid-part-b")));
        bytes memory reason;
        (nestedSucceeded, reason) = address(pool).call(callData);
        if (reason.length >= 4) {
            bytes4 selector;
            assembly ("memory-safe") { selector := mload(add(reason, 0x20)) }
            nestedError = selector;
        }
    }
}

contract PQTCClassicPoolTest is Test {
    uint256 private constant DENOMINATION = 1 ether;
    bytes32 private constant PROOF_ID = keccak256("proof");
    Digest512 private parameter = Digest512(bytes32(uint256(1)), bytes32(uint256(2)));
    PoolMockRegistry private registry;
    PQTCClassicPool private pool;

    function setUp() external {
        registry = new PoolMockRegistry();
        pool = new PQTCClassicPool(DENOMINATION, parameter, registry);
        vm.deal(address(this), 10 ether);
    }

    function testDeploymentUsesCanonicalProtocolV3Scope() external view {
        assertEq(pool.PROTOCOL_VERSION(), 3);
        Digest512 memory expected = PQTCApplicationHash.scope(
            uint64(block.chainid), address(pool), DENOMINATION, pool.TREE_DEPTH(), 3, parameter
        );
        Digest512 memory actual = _scope();
        assertEq(actual.left, expected.left);
        assertEq(actual.right, expected.right);
        P2BB512.toFields(actual);
    }

    function testMerkleNodeBindsLevel() external pure {
        Digest512 memory left = Digest512(bytes32(uint256(3)), bytes32(uint256(4)));
        Digest512 memory right = Digest512(bytes32(uint256(5)), bytes32(uint256(6)));
        Digest512 memory levelZero = PQTCApplicationHash.merkleNode(0, left, right);
        Digest512 memory levelOne = PQTCApplicationHash.merkleNode(1, left, right);
        assertTrue(levelZero.left != levelOne.left || levelZero.right != levelOne.right);
    }

    function testDepositFitsOneTransactionGasGate() external {
        Digest512 memory commitment = PQTCApplicationHash.commitment(_scope(), bytes32(uint256(3)), bytes32(uint256(4)));
        uint256 gasBefore = gasleft();
        pool.deposit{value: DENOMINATION}(commitment);
        uint256 executionGas = gasBefore - gasleft();
        assertLt(executionGas, 16_500_000, "deposit exceeds one-transaction execution gas gate");
        emit log_named_uint("deposit execution gas", executionGas);
    }

    function testDepositsMatchDepthTwentyPathsAndRetainRoots() external {
        Digest512 memory first = Digest512(bytes32(uint256(3)), bytes32(uint256(4)));
        Digest512 memory second = Digest512(bytes32(uint256(5)), bytes32(uint256(6)));
        Digest512 memory initial = pool.currentRoot();

        pool.deposit{value: DENOMINATION}(first);
        Digest512 memory expectedFirst = first;
        for (uint8 level = 0; level < 20; ++level) {
            expectedFirst = PQTCApplicationHash.merkleNode(level, expectedFirst, pool.zero(level));
        }
        Digest512 memory firstRoot = pool.currentRoot();
        assertEq(firstRoot.left, expectedFirst.left);
        assertEq(firstRoot.right, expectedFirst.right);

        pool.deposit{value: DENOMINATION}(second);
        Digest512 memory expectedSecond = PQTCApplicationHash.merkleNode(0, first, second);
        for (uint8 level = 1; level < 20; ++level) {
            expectedSecond = PQTCApplicationHash.merkleNode(level, expectedSecond, pool.zero(level));
        }
        Digest512 memory secondRoot = pool.currentRoot();
        assertEq(secondRoot.left, expectedSecond.left);
        assertEq(secondRoot.right, expectedSecond.right);
        assertTrue(pool.knownRoots(initial.left, initial.right));
        assertTrue(pool.knownRoots(firstRoot.left, firstRoot.right));
        assertTrue(pool.knownRoots(secondRoot.left, secondRoot.right));
        assertTrue(pool.commitments(first.left, first.right));
        assertTrue(pool.commitments(second.left, second.right));
        assertEq(pool.nextIndex(), 2);
    }

    function testDepositRejectsWrongValueZeroDuplicateAndNoncanonicalCommitment() external {
        Digest512 memory commitment = Digest512(bytes32(uint256(3)), bytes32(uint256(4)));
        vm.expectRevert(PQTCClassicPool.IncorrectDepositValue.selector);
        pool.deposit{value: DENOMINATION - 1}(commitment);
        vm.expectRevert(PQTCClassicPool.ZeroCommitment.selector);
        pool.deposit{value: DENOMINATION}(Digest512(bytes32(0), bytes32(0)));

        Digest512 memory noncanonical = Digest512(bytes32(uint256(2_013_265_921) << 224), bytes32(uint256(1)));
        vm.expectRevert(
            abi.encodeWithSelector(P2BB512.NonCanonicalDigestLimb.selector, uint256(0), uint256(2_013_265_921))
        );
        pool.deposit{value: DENOMINATION}(noncanonical);
        pool.deposit{value: DENOMINATION}(commitment);
        vm.expectRevert(PQTCClassicPool.DuplicateCommitment.selector);
        pool.deposit{value: DENOMINATION}(commitment);
    }

    function testAtomicWithdrawalPaysRecipientAndRelayerAndPreventsDoubleSpend() external {
        Digest512 memory root = _deposit();
        PaymentReceiver recipient = new PaymentReceiver();
        PaymentReceiver relayer = new PaymentReceiver();
        Digest512 memory nullifier = Digest512(bytes32(uint256(11)), bytes32(uint256(12)));
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(relayer)),
            fee: 0.1 ether
        });
        bytes32 verificationId = _begin(withdrawal);
        assertEq(registry.consumer(verificationId), address(pool));
        assertEq(_begin(withdrawal), verificationId);
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "wrong-part-b");
        assertTrue(registry.pending(verificationId));
        assertFalse(pool.nullifiers(nullifier.left, nullifier.right));

        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        assertEq(address(recipient).balance, 0.9 ether);
        assertEq(address(relayer).balance, 0.1 ether);
        assertTrue(pool.nullifiers(nullifier.left, nullifier.right));
        assertFalse(registry.pending(verificationId));
        vm.expectRevert(PQTCClassicPool.NullifierSpent.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
    }

    function testPaymentFailureRollsBackNullifierAndVerifierCompletion() external {
        Digest512 memory root = _deposit();
        RejectPayment recipient = new RejectPayment();
        Digest512 memory nullifier = Digest512(bytes32(uint256(21)), bytes32(uint256(22)));
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: 0
        });
        bytes32 verificationId = _begin(withdrawal);

        vm.expectRevert(PQTCClassicPool.TransferFailed.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        assertFalse(pool.nullifiers(nullifier.left, nullifier.right));
        assertTrue(registry.pending(verificationId));
        assertEq(address(pool).balance, DENOMINATION);
    }

    function testWithdrawalValidationPrecedesVerification() external {
        Digest512 memory root = _deposit();
        PaymentReceiver recipient = new PaymentReceiver();
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: Digest512(bytes32(uint256(31)), bytes32(uint256(32))),
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: DENOMINATION + 1
        });
        vm.expectRevert(PQTCClassicPool.FeeExceedsDenomination.selector);
        pool.beginWithdrawal(withdrawal, "valid-part-a");
        withdrawal.fee = 1;
        vm.expectRevert(PQTCClassicPool.ZeroRelayer.selector);
        pool.beginWithdrawal(withdrawal, "valid-part-a");
        withdrawal.fee = 0;
        withdrawal.root = Digest512(bytes32(uint256(71)), bytes32(uint256(72)));
        vm.expectRevert(PQTCClassicPool.UnknownRoot.selector);
        pool.beginWithdrawal(withdrawal, "valid-part-a");
        withdrawal.root = root;
        withdrawal.recipient = payable(address(0));
        vm.expectRevert(PQTCClassicPool.ZeroRecipient.selector);
        pool.beginWithdrawal(withdrawal, "valid-part-a");
        withdrawal.recipient = payable(address(recipient));
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, PROOF_ID, "valid-part-b");
    }

    function testWithdrawalRejectsNoncanonicalRootAndNullifierAtBoundary() external {
        Digest512 memory root = _deposit();
        PaymentReceiver recipient = new PaymentReceiver();
        Digest512 memory noncanonical = Digest512(bytes32(uint256(2_013_265_921) << 224), bytes32(uint256(1)));
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: noncanonical,
            nullifierHash: Digest512(bytes32(uint256(1)), bytes32(uint256(2))),
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: 0
        });
        bytes memory expectedError =
            abi.encodeWithSelector(P2BB512.NonCanonicalDigestLimb.selector, uint256(0), uint256(2_013_265_921));
        vm.expectRevert(expectedError);
        pool.beginWithdrawal(withdrawal, "valid-part-a");

        withdrawal.root = root;
        withdrawal.nullifierHash = noncanonical;
        vm.expectRevert(expectedError);
        pool.withdraw(withdrawal, PROOF_ID, "valid-part-b");
    }

    function testReentrancyGuardBlocksNestedIndependentWithdrawal() external {
        _deposit();
        Digest512 memory root = _depositDistinct();
        ReentrantRecipient recipient = new ReentrantRecipient();
        Digest512 memory outerNullifier = Digest512(bytes32(uint256(41)), bytes32(uint256(42)));
        Digest512 memory nestedNullifier = Digest512(bytes32(uint256(43)), bytes32(uint256(44)));
        PQTCClassicPool.Withdrawal memory outer = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: outerNullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: 0
        });
        PQTCClassicPool.Withdrawal memory nested = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nestedNullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: 0
        });
        bytes32 outerProofId = _begin(outer);
        bytes32 nestedProofId = _begin(nested);
        recipient.arm(pool, nestedProofId, nested);

        pool.withdraw(outer, outerProofId, "valid-part-b");
        assertTrue(recipient.attempted());
        assertFalse(recipient.nestedSucceeded());
        assertEq(recipient.nestedError(), PQTCClassicPool.ReentrantCall.selector);
        assertFalse(pool.nullifiers(nestedNullifier.left, nestedNullifier.right));
        assertTrue(registry.pending(nestedProofId));
        assertEq(address(pool).balance, DENOMINATION);
    }

    function testCheckpointBindsExactRootNullifierRecipientRelayerAndFee() external {
        Digest512 memory initialRoot = pool.currentRoot();
        Digest512 memory root = _deposit();
        PaymentReceiver recipient = new PaymentReceiver();
        PaymentReceiver changedRecipient = new PaymentReceiver();
        PaymentReceiver relayer = new PaymentReceiver();
        PaymentReceiver changedRelayer = new PaymentReceiver();
        Digest512 memory nullifier = Digest512(bytes32(uint256(61)), bytes32(uint256(62)));
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(relayer)),
            fee: 0.1 ether
        });
        bytes32 verificationId = _begin(withdrawal);

        withdrawal.recipient = payable(address(changedRecipient));
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        withdrawal.recipient = payable(address(recipient));

        withdrawal.relayer = payable(address(changedRelayer));
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        withdrawal.relayer = payable(address(relayer));

        withdrawal.fee = 0.2 ether;
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        withdrawal.fee = 0.1 ether;

        withdrawal.root = initialRoot;
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        withdrawal.root = root;

        withdrawal.nullifierHash = Digest512(bytes32(uint256(63)), bytes32(uint256(64)));
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        withdrawal.nullifierHash = nullifier;

        assertTrue(registry.pending(verificationId));
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        assertEq(address(recipient).balance, 0.9 ether);
        assertEq(address(relayer).balance, 0.1 ether);
        assertTrue(pool.nullifiers(nullifier.left, nullifier.right));
    }

    function testForcedEtherCannotIncreaseWithdrawalAmount() external {
        Digest512 memory root = _deposit();
        vm.deal(address(pool), address(pool).balance + 2 ether);
        PaymentReceiver recipient = new PaymentReceiver();
        Digest512 memory nullifier = Digest512(bytes32(uint256(51)), bytes32(uint256(52)));
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: 0
        });
        bytes32 verificationId = _begin(withdrawal);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        assertEq(address(recipient).balance, DENOMINATION);
        assertEq(address(pool).balance, 2 ether);
    }

    function _begin(PQTCClassicPool.Withdrawal memory withdrawal) private returns (bytes32 verificationId) {
        return pool.beginWithdrawal(withdrawal, "valid-part-a");
    }

    function _deposit() private returns (Digest512 memory) {
        pool.deposit{value: DENOMINATION}(Digest512(bytes32(uint256(7)), bytes32(uint256(8))));
        return pool.currentRoot();
    }

    function _depositDistinct() private returns (Digest512 memory) {
        pool.deposit{value: DENOMINATION}(Digest512(bytes32(uint256(9)), bytes32(uint256(10))));
        return pool.currentRoot();
    }

    function _scope() private view returns (Digest512 memory value) {
        (value.left, value.right) = pool.scope();
    }
}
```

</details>

## `contracts/test/PQTCClassicPoolInvariant.t.sol`

- Bytes: 5,009
- SHA-256: `32e4ab2d4c317d3633abe33ba51d76eca836c5ad2aad46d23b08e5c439240edf`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {StdInvariant} from "forge-std/StdInvariant.sol";
import {Test} from "forge-std/Test.sol";
import {PQTCClassicPool, IPQTCVerificationRegistry} from "../src/PQTCClassicPool.sol";
import {Digest512} from "../src/libraries/Digest512.sol";

contract InvariantRegistry is IPQTCVerificationRegistry {
    struct Checkpoint {
        address consumer;
        Digest512 parameterId;
        bytes32 statementKey;
    }

    mapping(bytes32 => Checkpoint) private checkpoints;

    function beginVerification(
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata proofPartA
    ) external returns (bytes32 verificationId) {
        for (uint256 i = 0; i < 64; ++i) {
            if (publicValues[i] >= 2_013_265_921) revert();
        }
        bytes32 statementKey =
            keccak256(abi.encode(bytes32("PQTC.V3.STATEMENT"), parameterId.left, parameterId.right, publicValues));
        bytes32 coreProofId = keccak256(abi.encode(bytes32("PQTC.V3.PROOF"), statementKey, keccak256(proofPartA)));
        verificationId = keccak256(abi.encode(bytes32("PQTC.V3.VERIFICATION"), coreProofId, msg.sender));
        checkpoints[verificationId] = Checkpoint(msg.sender, parameterId, statementKey);
    }

    function completeVerification(
        bytes32 proofId,
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata
    ) external returns (bool) {
        Checkpoint storage checkpoint = checkpoints[proofId];
        if (
            checkpoint.consumer != msg.sender || checkpoint.parameterId.left != parameterId.left
                || checkpoint.parameterId.right != parameterId.right
        ) return false;
        for (uint256 i = 0; i < 64; ++i) {
            if (publicValues[i] >= 2_013_265_921) return false;
        }
        bytes32 statementKey =
            keccak256(abi.encode(bytes32("PQTC.V3.STATEMENT"), parameterId.left, parameterId.right, publicValues));
        if (statementKey != checkpoint.statementKey) return false;
        delete checkpoints[proofId];
        return true;
    }
}

contract PoolInvariantHandler {
    uint256 private constant DENOMINATION = 1 ether;

    PQTCClassicPool public immutable pool;

    uint256 public totalDeposited;
    uint256 public totalWithdrawn;
    uint256 public actionNonce;
    Digest512 public lastNullifier;

    constructor(PQTCClassicPool pool_) {
        pool = pool_;
    }

    receive() external payable {}

    function deposit(uint256) external {
        uint256 nonce = ++actionNonce;
        Digest512 memory commitment = Digest512(bytes32(nonce), bytes32(nonce + 1));
        pool.deposit{value: DENOMINATION}(commitment);
        totalDeposited += DENOMINATION;
    }

    function withdraw(uint256) external {
        if (address(pool).balance < DENOMINATION) return;

        uint256 nonce = ++actionNonce;
        Digest512 memory nullifier = Digest512(bytes32(nonce), bytes32(nonce + 1));
        Digest512 memory root = pool.currentRoot();
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nullifier,
            recipient: payable(address(this)),
            relayer: payable(address(0)),
            fee: 0
        });
        bytes32 verificationId = pool.beginWithdrawal(withdrawal, abi.encode(nonce));
        pool.withdraw(withdrawal, verificationId, "");

        lastNullifier = nullifier;
        totalWithdrawn += DENOMINATION;
    }
}

contract PQTCClassicPoolInvariantTest is StdInvariant, Test {
    uint256 private constant DENOMINATION = 1 ether;

    PQTCClassicPool private pool;
    PoolInvariantHandler private handler;

    function setUp() external {
        Digest512 memory parameter = Digest512(bytes32(uint256(1)), bytes32(uint256(2)));
        InvariantRegistry registry = new InvariantRegistry();
        pool = new PQTCClassicPool(DENOMINATION, parameter, registry);
        handler = new PoolInvariantHandler(pool);
        vm.deal(address(handler), 1_000_000 ether);

        bytes4[] memory selectors = new bytes4[](2);
        selectors[0] = handler.deposit.selector;
        selectors[1] = handler.withdraw.selector;
        targetSelector(FuzzSelector({addr: address(handler), selectors: selectors}));
        targetContract(address(handler));
    }

    function invariantPoolBalanceMatchesNetDeposits() external view {
        assertEq(address(pool).balance, handler.totalDeposited() - handler.totalWithdrawn());
    }

    function invariantWithdrawalsNeverExceedDeposits() external view {
        assertLe(handler.totalWithdrawn(), handler.totalDeposited());
    }

    function invariantLastWithdrawalNullifierRemainsSpent() external view {
        if (handler.totalWithdrawn() == 0) return;
        (bytes32 left, bytes32 right) = handler.lastNullifier();
        assertTrue(pool.nullifiers(left, right));
    }
}
```

</details>

## `contracts/test/StagedVerifier.t.sol`

- Bytes: 18,228
- SHA-256: `f8a5707247dfe5b4eb98da42eaf353073e71256db8c9f97e6b5c4237c824c125`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {CanonicalCodec} from "../src/libraries/CanonicalCodec.sol";
import {Digest512} from "../src/libraries/Digest512.sol";
import {P2BB512} from "../src/libraries/P2BB512.sol";
import {PQTCAirStageVerifier} from "../src/verifier/PQTCAirStageVerifier.sol";
import {PQTCQueryVerifier} from "../src/verifier/PQTCQueryVerifier.sol";
import {PQTCVerificationRegistry} from "../src/PQTCVerificationRegistry.sol";
import {IPQTCVerificationRegistry, PQTCClassicPool} from "../src/PQTCClassicPool.sol";

contract FixturePool is PQTCClassicPool {
    constructor(Digest512 memory parameterId_, IPQTCVerificationRegistry registry_)
        PQTCClassicPool(1, parameterId_, registry_)
    {}

    function installFixture(Digest512 calldata scope_, Digest512 calldata root_) external {
        scope = scope_;
        knownRoots[root_.left][root_.right] = true;
    }
}

contract NoopAirStageVerifier is PQTCAirStageVerifier {
    function evaluateRange(
        uint256[] calldata,
        uint256[] calldata,
        uint32[64] calldata,
        uint256,
        uint256,
        uint256 accumulator,
        uint8,
        uint8
    ) external pure override returns (uint256) {
        return accumulator;
    }
}

contract NoopQueryVerifier is PQTCQueryVerifier {
    function verifyFirstHalf(bytes calldata proof, uint256, Context calldata)
        external
        pure
        override
        returns (uint256, uint256, uint256)
    {
        return (proof.length - 4, 0, 0);
    }
}

contract FriSkippingQueryVerifier is PQTCQueryVerifier {
    function _fri(bytes calldata proof, uint256, uint32[16] memory, uint256[16] memory, Context calldata)
        internal
        pure
        virtual
        override
        returns (uint256)
    {
        return proof.length - 4;
    }
}

contract SkipInputQueryVerifier is FriSkippingQueryVerifier {
    function _inputBatch(bytes calldata proof, uint256 cursor, ReductionState memory, uint256 batch, Context calldata)
        internal
        pure
        override
        returns (uint256)
    {
        uint256 matrices = batch == 2 ? 16 : 1;
        uint256 rowWidth = batch == 0 ? 8 : batch == 1 ? 194 : 8;
        cursor += 16 * matrices * rowWidth * 4;
        cursor += 16 * matrices * 8 * 4;
        uint32 frontierCount;
        (frontierCount, cursor) = CanonicalCodec.readU32(proof, cursor);
        return cursor + uint256(frontierCount) * 64;
    }
}

contract NoReductionQueryVerifier is FriSkippingQueryVerifier {
    function _reduceBatch(bytes calldata, uint256, uint256, uint256, ReductionState memory) internal pure override {}
}

contract CompactVerifierTest is Test {
    uint256 private constant EIP_7825_GAS_LIMIT = 16_777_216;
    uint256 private constant A_CHECKPOINT_OFFSET = 338 + 32 + 9_208;
    uint256 private constant B_CHECKPOINT_OFFSET = 338 + 32 + 32 + 9_208;

    bytes private partA;
    bytes private partB;
    Digest512 private parameterId;
    uint32[64] private publicValues;
    PQTCVerificationRegistry private registry;

    function setUp() external {
        partA = vm.readFileBinary("test-vectors/verifier/v3/part-a.pqtc");
        partB = vm.readFileBinary("test-vectors/verifier/v3/part-b.pqtc");
        (parameterId, publicValues) = _common(partA);
        registry = new PQTCVerificationRegistry(new PQTCAirStageVerifier(), new PQTCQueryVerifier(), parameterId);
    }

    function measureA(
        PQTCVerificationRegistry target,
        Digest512 calldata parameter,
        uint32[64] calldata values,
        bytes calldata proof
    ) external returns (uint256 used, bytes32 proofId) {
        uint256 beforeGas = gasleft();
        proofId = target.beginVerification(parameter, values, proof);
        used = beforeGas - gasleft();
    }

    function measureB(
        PQTCVerificationRegistry target,
        bytes32 proofId,
        Digest512 calldata parameter,
        uint32[64] calldata values,
        bytes calldata proof
    ) external returns (uint256 used) {
        uint256 beforeGas = gasleft();
        target.completeVerification(proofId, parameter, values, proof);
        used = beforeGas - gasleft();
    }

    function measurePoolA(FixturePool target, PQTCClassicPool.Withdrawal calldata withdrawal, bytes calldata proof)
        external
        returns (uint256 used, bytes32 proofId)
    {
        uint256 beforeGas = gasleft();
        proofId = target.beginWithdrawal(withdrawal, proof);
        used = beforeGas - gasleft();
    }

    function measurePoolB(
        FixturePool target,
        PQTCClassicPool.Withdrawal calldata withdrawal,
        bytes32 proofId,
        bytes calldata proof
    ) external returns (uint256 used) {
        uint256 beforeGas = gasleft();
        target.withdraw(withdrawal, proofId, proof);
        used = beforeGas - gasleft();
    }

    function testCanonicalV3ProofCompletesInExactlyTwoPoolFacingGasBoundedCalls() external {
        FixturePool pool = new FixturePool(parameterId, IPQTCVerificationRegistry(address(registry)));
        PQTCClassicPool.Withdrawal memory withdrawal = _fixtureWithdrawal();
        pool.installFixture(_digestAt(0), withdrawal.root);
        vm.deal(address(pool), 1);

        (uint256 partAExecutionGas, bytes32 proofId) = this.measurePoolA(pool, withdrawal, partA);
        bytes32 statementKey =
            keccak256(abi.encode(bytes32("PQTC.V3.STATEMENT"), parameterId.left, parameterId.right, publicValues));
        bytes32 coreProofId = keccak256(abi.encode(bytes32("PQTC.V3.PROOF"), statementKey, keccak256(partA)));
        assertEq(proofId, keccak256(abi.encode(bytes32("PQTC.V3.VERIFICATION"), coreProofId, address(pool))));
        uint256 partBExecutionGas = this.measurePoolB(pool, withdrawal, proofId, partB);
        uint256 partATransactionGas =
            _transactionGas(partAExecutionGas, abi.encodeCall(PQTCClassicPool.beginWithdrawal, (withdrawal, partA)));
        uint256 partBTransactionGas =
            _transactionGas(partBExecutionGas, abi.encodeCall(PQTCClassicPool.withdraw, (withdrawal, proofId, partB)));
        assertLe(partATransactionGas, EIP_7825_GAS_LIMIT, "part A complete ABI transaction exceeds EIP-7825");
        assertLe(partBTransactionGas, EIP_7825_GAS_LIMIT, "part B complete ABI transaction exceeds EIP-7825");
        emit log_named_uint("compact verifier part A execution gas", partAExecutionGas);
        emit log_named_uint("compact verifier part A transaction gas", partATransactionGas);
        emit log_named_uint("compact verifier part B execution gas", partBExecutionGas);
        emit log_named_uint("compact verifier part B transaction gas", partBTransactionGas);
    }

    function testGasProfileV3VerifierComponents() external {
        NoopAirStageVerifier noopAir = new NoopAirStageVerifier();
        PQTCAirStageVerifier realAir = new PQTCAirStageVerifier();
        PQTCVerificationRegistry baseline = new PQTCVerificationRegistry(noopAir, new NoopQueryVerifier(), parameterId);
        PQTCVerificationRegistry withAir = new PQTCVerificationRegistry(realAir, new NoopQueryVerifier(), parameterId);
        PQTCVerificationRegistry prepared =
            new PQTCVerificationRegistry(noopAir, new SkipInputQueryVerifier(), parameterId);
        PQTCVerificationRegistry committed =
            new PQTCVerificationRegistry(noopAir, new NoReductionQueryVerifier(), parameterId);
        PQTCVerificationRegistry reduced =
            new PQTCVerificationRegistry(noopAir, new FriSkippingQueryVerifier(), parameterId);
        PQTCVerificationRegistry queried = new PQTCVerificationRegistry(noopAir, new PQTCQueryVerifier(), parameterId);

        (uint256 parsingGas,) = this.measureA(baseline, parameterId, publicValues, partA);
        (uint256 airCumulative,) = this.measureA(withAir, parameterId, publicValues, partA);
        (uint256 preparedCumulative,) = this.measureA(prepared, parameterId, publicValues, partA);
        (uint256 committedCumulative,) = this.measureA(committed, parameterId, publicValues, partA);
        (uint256 reducedCumulative,) = this.measureA(reduced, parameterId, publicValues, partA);
        (uint256 queriedCumulative,) = this.measureA(queried, parameterId, publicValues, partA);

        emit log_named_uint("profile parsing transcript storage", parsingGas);
        emit log_named_uint("profile AIR first segment", airCumulative - parsingGas);
        emit log_named_uint("profile alpha inverse shared OOD", preparedCumulative - parsingGas);
        emit log_named_uint("profile input MMCS", committedCumulative - preparedCumulative);
        emit log_named_uint("profile DEEP X reductions", reducedCumulative - committedCumulative);
        emit log_named_uint("profile nine FRI rounds", queriedCumulative - reducedCumulative);

        PQTCVerificationRegistry complete = new PQTCVerificationRegistry(realAir, new PQTCQueryVerifier(), parameterId);
        (uint256 actualA, bytes32 proofId) = this.measureA(complete, parameterId, publicValues, partA);
        uint256 actualB = this.measureB(complete, proofId, parameterId, publicValues, partB);
        emit log_named_uint("profile actual A execution", actualA);
        emit log_named_uint("profile actual B execution", actualB);
    }

    function testCompletionIsOneUse() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        registry.completeVerification(proofId, parameterId, publicValues, partB);
        vm.expectRevert(PQTCVerificationRegistry.UnknownProof.selector);
        registry.completeVerification(proofId, parameterId, publicValues, partB);
    }

    function testIdenticalPartAIsIdempotentWhileCheckpointExists() external {
        bytes32 first = registry.beginVerification(parameterId, publicValues, partA);
        bytes32 second = registry.beginVerification(parameterId, publicValues, partA);
        assertEq(first, second);
    }

    function testPartBIsBoundToConsumer() external {
        address consumer = address(0xBEEF);
        vm.prank(consumer);
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        vm.expectRevert(PQTCVerificationRegistry.UnauthorizedConsumer.selector);
        registry.completeVerification(proofId, parameterId, publicValues, partB);
    }

    function testRejectsMixedPartProofId() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        bytes memory mixed = partB;
        mixed[338] = bytes1(uint8(mixed[338]) ^ 1);
        vm.expectRevert(PQTCVerificationRegistry.InvalidCheckpoint.selector);
        registry.completeVerification(proofId, parameterId, publicValues, mixed);
    }

    function testRejectsDifferentStatementAtCompletion() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        uint32[64] memory other = publicValues;
        other[0] = other[0] == 0 ? 1 : 0;
        vm.expectRevert(PQTCVerificationRegistry.StatementMismatch.selector);
        registry.completeVerification(proofId, parameterId, other, partB);
    }

    function testRejectsTranscriptBoundGlobalMutation() external {
        bytes memory mutated = partA;
        mutated[370] = bytes1(uint8(mutated[370]) ^ 1); // first byte of trace root

        vm.expectRevert(PQTCVerificationRegistry.GlobalDataMismatch.selector);
        registry.beginVerification(parameterId, publicValues, mutated);
    }

    function testRejectsSecondPartGlobalMutation() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        bytes memory mutated = partB;
        mutated[402] = bytes1(uint8(mutated[402]) ^ 1); // first byte of part B trace root
        vm.expectRevert(PQTCVerificationRegistry.GlobalDataMismatch.selector);
        registry.completeVerification(proofId, parameterId, publicValues, mutated);
    }

    function testRejectsNoncanonicalHeaderField() external {
        bytes memory malformed = partA;
        _putU32(malformed, 82, 2_013_265_921);
        vm.expectRevert(abi.encodeWithSelector(CanonicalCodec.NonCanonicalField.selector, uint32(2_013_265_921)));
        registry.beginVerification(parameterId, publicValues, malformed);
    }

    function testFixtureSplitsAllQueriesIntoOrderedHalves() external view {
        uint256 halfA = _halfOffset(partA, A_CHECKPOINT_OFFSET);
        uint256 halfB = _halfOffset(partB, B_CHECKPOINT_OFFSET);
        assertEq(_u16(partA, halfA), 0);
        assertEq(_u16(partA, halfA + 2), 16);
        assertEq(_u16(partB, halfB), 16);
        assertEq(_u16(partB, halfB + 2), 16);
    }

    function testRejectsReorderedFirstHalfQueries() external {
        bytes memory reordered = partA;
        _swapDistinctIndices(reordered, _halfOffset(reordered, A_CHECKPOINT_OFFSET) + 4);
        vm.expectRevert(PQTCQueryVerifier.InvalidQuery.selector);
        registry.beginVerification(parameterId, publicValues, reordered);
    }

    function testRejectsReorderedSecondHalfQueries() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        bytes memory reordered = partB;
        uint256 half = _halfOffset(reordered, B_CHECKPOINT_OFFSET);
        _swapDistinctIndices(reordered, half + 4);
        vm.expectRevert(PQTCQueryVerifier.InvalidQuery.selector);
        registry.completeVerification(proofId, parameterId, publicValues, reordered);
    }

    function testRejectsMalformedPrunedFrontier() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        bytes memory malformed = partB;
        uint256 half = _halfOffset(malformed, B_CHECKPOINT_OFFSET);
        uint256 firstFrontierCount = half + 4 + 16 * 4 + 16 * 8 * 4 + 16 * 8 * 4;
        _putU32(malformed, firstFrontierCount, type(uint32).max);
        vm.expectRevert();
        registry.completeVerification(proofId, parameterId, publicValues, malformed);
    }

    function _halfOffset(bytes memory proof, uint256 checkpointOffset) private pure returns (uint256) {
        uint16 uniqueCount = _u16(proof, checkpointOffset + 450);
        return checkpointOffset + 452 + uint256(uniqueCount) * 4;
    }

    function _swapDistinctIndices(bytes memory proof, uint256 indicesOffset) private pure {
        uint32 first = _u32(proof, indicesOffset);
        for (uint256 i = 1; i < 16; ++i) {
            uint256 offset = indicesOffset + i * 4;
            uint32 candidate = _u32(proof, offset);
            if (candidate != first) {
                _putU32(proof, indicesOffset, candidate);
                _putU32(proof, offset, first);
                return;
            }
        }
        revert("fixture has no distinct second-half query indices");
    }

    function _common(bytes memory proof) private pure returns (Digest512 memory parameter, uint32[64] memory values) {
        assembly ("memory-safe") {
            mstore(parameter, mload(add(proof, 0x30)))
            mstore(add(parameter, 0x20), mload(add(proof, 0x50)))
        }
        for (uint256 i; i < 64; ++i) {
            values[i] = _u32(proof, 82 + i * 4);
        }
    }

    function _fixtureWithdrawal() private view returns (PQTCClassicPool.Withdrawal memory withdrawal) {
        withdrawal = PQTCClassicPool.Withdrawal({
            root: _digestAt(16),
            nullifierHash: _digestAt(32),
            recipient: payable(address(0x0505050505050505050505050505050505050505)),
            relayer: payable(address(0x0606060606060606060606060606060606060606)),
            fee: 0
        });
    }

    function testRejectsFriSaltMutationAtRegeneratedOffset() external {
        bytes memory mutated = partA;
        uint256 saltOffset = _firstFriSaltOffset(mutated, A_CHECKPOINT_OFFSET);
        uint32 salt = _u32(mutated, saltOffset);
        _putU32(mutated, saltOffset, salt == 0 ? 1 : salt - 1);
        vm.expectRevert();
        registry.beginVerification(parameterId, publicValues, mutated);
    }

    function _firstFriSaltOffset(bytes memory proof, uint256 checkpointOffset) private pure returns (uint256) {
        uint256 cursor = _halfOffset(proof, checkpointOffset) + 4 + 16 * 4;
        cursor = _skipInputBatch(proof, cursor, 1, 8);
        cursor = _skipInputBatch(proof, cursor, 1, 194);
        cursor = _skipInputBatch(proof, cursor, 16, 8);
        return cursor + 16 * 16;
    }

    function _skipInputBatch(bytes memory proof, uint256 cursor, uint256 matrices, uint256 rowWidth)
        private
        pure
        returns (uint256)
    {
        cursor += 16 * matrices * rowWidth * 4 + 16 * matrices * 8 * 4;
        uint32 frontierCount = _u32(proof, cursor);
        return cursor + 4 + uint256(frontierCount) * 64;
    }

    function _digestAt(uint256 offset) private view returns (Digest512 memory) {
        uint32[16] memory fields;
        for (uint256 i; i < 16; ++i) {
            fields[i] = publicValues[offset + i];
        }
        return P2BB512.fromFields(fields);
    }

    function _u16(bytes memory data, uint256 offset) private pure returns (uint16 value) {
        assembly ("memory-safe") { value := shr(240, mload(add(add(data, 0x20), offset))) }
    }

    function _u32(bytes memory data, uint256 offset) private pure returns (uint32 value) {
        assembly ("memory-safe") { value := shr(224, mload(add(add(data, 0x20), offset))) }
    }

    // The measured wrapper includes an extra CALL, so this is a conservative upper bound
    // on execution plus the exact intrinsic cost of the pool-facing ABI calldata.
    function _transactionGas(uint256 executionGas, bytes memory callData) private pure returns (uint256 total) {
        total = 21_000 + executionGas;
        for (uint256 i; i < callData.length; ++i) {
            total += callData[i] == bytes1(0) ? 4 : 16;
        }
    }

    function _putU32(bytes memory data, uint256 offset, uint32 value) private pure {
        data[offset] = bytes1(uint8(value >> 24));
        data[offset + 1] = bytes1(uint8(value >> 16));
        data[offset + 2] = bytes1(uint8(value >> 8));
        data[offset + 3] = bytes1(uint8(value));
    }
}
```

</details>

## `contracts/test/VerifierFoundation.t.sol`

- Bytes: 6,851
- SHA-256: `d1b96f53fb4443bf981b6553ea745fe78d5fe1239cb369d6feb1e5afcaf4555f`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {CanonicalCodec} from "../src/libraries/CanonicalCodec.sol";
import {Digest512} from "../src/libraries/Digest512.sol";
import {PQTCProofCodec} from "../src/libraries/PQTCProofCodec.sol";
import {FriVerifier} from "../src/verifier/FriVerifier.sol";
import {MmcsVerifier} from "../src/verifier/MmcsVerifier.sol";

contract VerifierFoundationHarness {
    function parseCommon(bytes calldata proof, Digest512 calldata parameterId, uint32[64] calldata values)
        external
        pure
        returns (uint256)
    {
        return PQTCProofCodec.parseCommon(proof, PQTCProofCodec.PART_A_MAGIC, parameterId, values).cursor;
    }

    function statementKey(Digest512 calldata parameterId, uint32[64] calldata values) external pure returns (bytes32) {
        return PQTCProofCodec.statementKey(parameterId, values);
    }

    function requirePartAEnd(bytes calldata proof) external pure {
        PQTCProofCodec.requireEnd(proof, 0, PQTCProofCodec.PART_A_END);
    }

    function verifyRepeatedLeaf(
        Digest512 calldata root,
        uint32 index,
        Digest512 calldata leaf,
        bytes calldata frontier,
        uint256 height,
        uint256 leafCount
    ) external pure returns (uint256) {
        uint32[16] memory indices;
        MmcsVerifier.LeafWords memory leaves;
        for (uint256 i; i < 16; ++i) {
            indices[i] = index;
            leaves.lefts[i] = leaf.left;
            leaves.rights[i] = leaf.right;
        }
        return MmcsVerifier.verifyPruned(root, indices, leaves, height, leafCount, frontier, 0);
    }

    function node(Digest512 calldata left, Digest512 calldata right) external pure returns (Digest512 memory) {
        return MmcsVerifier.hashNode(left, right);
    }

    function reverseBits(uint256 value, uint256 bits) external pure returns (uint256) {
        return FriVerifier.reverseBits(value, bits);
    }
}

contract VerifierFoundationTest is Test {
    VerifierFoundationHarness private harness;
    Digest512 private parameter;
    uint32[64] private values;

    function setUp() external {
        harness = new VerifierFoundationHarness();
        parameter = Digest512(bytes32(uint256(1)), bytes32(uint256(2)));
        for (uint256 i; i < 64; ++i) {
            values[i] = uint32(i + 1);
        }
    }

    function testV3CommonHeaderIsStrictAndCanonical() external view {
        bytes memory encoded = _header(values);
        assertEq(harness.parseCommon(encoded, parameter, values), 338);
    }

    function testRejectsV2Magic() external {
        bytes memory encoded = _header(values);
        bytes8 oldMagic = bytes8("PQTCPA02");
        assembly ("memory-safe") { mstore(add(encoded, 0x20), oldMagic) }
        vm.expectRevert(PQTCProofCodec.InvalidMagic.selector);
        harness.parseCommon(encoded, parameter, values);
    }

    function testRejectsV2Version() external {
        bytes memory encoded = _header(values);
        encoded[8] = bytes1(uint8(0));
        encoded[9] = bytes1(uint8(2));
        vm.expectRevert(PQTCProofCodec.UnsupportedVersion.selector);
        harness.parseCommon(encoded, parameter, values);
    }

    function testRejectsV2ProfileTag() external {
        bytes memory encoded = _header(values);
        encoded[10] = bytes1(uint8(2));
        vm.expectRevert(PQTCProofCodec.UnsupportedProfile.selector);
        harness.parseCommon(encoded, parameter, values);
    }

    function testRejectsV2QueryCount() external {
        bytes memory encoded = _header(values);
        encoded[14] = bytes1(uint8(0));
        encoded[15] = bytes1(uint8(48));
        vm.expectRevert(PQTCProofCodec.InvalidShape.selector);
        harness.parseCommon(encoded, parameter, values);
    }

    function testV3EndMarkerIsStrict() external view {
        harness.requirePartAEnd(hex"50414533");
    }

    function testRejectsV2EndMarker() external {
        vm.expectRevert(PQTCProofCodec.InvalidEndMarker.selector);
        harness.requirePartAEnd(hex"50414532");
    }

    function testRejectsNonCanonicalPublicField() external {
        uint32[64] memory malformed = values;
        malformed[7] = 2_013_265_921;
        bytes memory encoded = _header(malformed);
        vm.expectRevert(abi.encodeWithSelector(CanonicalCodec.NonCanonicalField.selector, uint32(2_013_265_921)));
        harness.parseCommon(encoded, parameter, malformed);
    }

    function testStatementKeyUsesStandardAbiEncoding() external view {
        bytes32 expected = keccak256(abi.encode(bytes32("PQTC.V3.STATEMENT"), parameter.left, parameter.right, values));
        assertEq(harness.statementKey(parameter, values), expected);
    }

    function testDeduplicatedPrunedProofAcceptsRepeatedIndex() external view {
        Digest512 memory leaf = Digest512(bytes32(uint256(11)), bytes32(uint256(12)));
        Digest512 memory sibling0 = Digest512(bytes32(uint256(21)), bytes32(uint256(22)));
        Digest512 memory sibling1 = Digest512(bytes32(uint256(31)), bytes32(uint256(32)));
        Digest512 memory parent = harness.node(leaf, sibling0);
        Digest512 memory root = harness.node(parent, sibling1);
        bytes memory frontier =
            abi.encodePacked(uint32(2), sibling0.left, sibling0.right, sibling1.left, sibling1.right);
        assertEq(harness.verifyRepeatedLeaf(root, 0, leaf, frontier, 2, 16), frontier.length);
    }

    function testPrunedProofRejectsMalformedFrontier() external {
        Digest512 memory leaf = Digest512(bytes32(uint256(11)), bytes32(uint256(12)));
        Digest512 memory root = leaf;
        bytes memory frontier = abi.encodePacked(uint32(0));
        vm.expectRevert(MmcsVerifier.InvalidMultiproof.selector);
        harness.verifyRepeatedLeaf(root, 0, leaf, frontier, 2, 16);
    }

    function testPrunedProofRejectsLeafCountAboveHalf() external {
        Digest512 memory leaf = Digest512(bytes32(uint256(11)), bytes32(uint256(12)));
        vm.expectRevert(MmcsVerifier.InvalidMultiproof.selector);
        harness.verifyRepeatedLeaf(leaf, 0, leaf, hex"", 1, 17);
    }

    function testReverseBitsUsesOnlyRequestedWidth() external view {
        assertEq(harness.reverseBits(0x0d, 4), 0x0b);
        assertEq(harness.reverseBits(0x10d, 4), 0x0b);
    }

    function _header(uint32[64] memory publicValues) private view returns (bytes memory out) {
        out = abi.encodePacked(
            bytes8("PQTCPA03"),
            uint16(3),
            uint8(3),
            uint8(9),
            uint8(9),
            uint8(4),
            uint16(32),
            parameter.left,
            parameter.right,
            uint16(64)
        );
        for (uint256 i; i < 64; ++i) {
            out = bytes.concat(out, bytes4(publicValues[i]));
        }
    }
}
```

</details>

## `crates/pqtc-cli/Cargo.toml`

- Bytes: 864
- SHA-256: `3d74f02bf0059aeefab6b752e93a986ab20e415e59c9ebcea94db77ce90f948c`

<details><summary>Complete file</summary>

```toml
[package]
name = "pqtc-cli"
version.workspace = true
edition.workspace = true
license.workspace = true
rust-version.workspace = true

[[bin]]
name = "pqtc"
path = "src/main.rs"

[dependencies]
anyhow.workspace = true
clap.workspace = true
hex.workspace = true
p3-air.workspace = true
p3-baby-bear.workspace = true
p3-challenger.workspace = true
p3-commit.workspace = true
p3-field.workspace = true
p3-symmetric.workspace = true
p3-matrix.workspace = true
p3-uni-stark.workspace = true
pqtc-hash = { path = "../pqtc-hash" }
pqtc-indexer = { path = "../pqtc-indexer" }
pqtc-poseidon-air = { path = "../pqtc-poseidon-air" }
pqtc-security = { path = "../pqtc-security" }
pqtc-spec = { path = "../pqtc-spec" }
pqtc-merkle = { path = "../pqtc-merkle" }
pqtc-stark = { path = "../pqtc-stark" }
serde.workspace = true
serde_json.workspace = true

[lints]
workspace = true
```

</details>

## `crates/pqtc-cli/src/main.rs`

- Bytes: 41,315
- SHA-256: `33237faccaa91f93981a5a7f799a4f0748c40cd83f3fe39d38e240b690355a94`

<details><summary>Complete file</summary>

```rust
use std::{fs, path::PathBuf, time::Instant};

use anyhow::{Context, Result, bail};
use clap::{Parser, Subcommand};
use p3_air::{Air, RowWindow};
use p3_baby_bear::BabyBear;
use p3_challenger::{CanObserve, CanSample, CanSampleBits};
use p3_commit::PolynomialSpace;
use p3_field::{
    BasedVectorSpace, PrimeCharacteristicRing, PrimeField32, coset::TwoAdicMultiplicativeCoset,
};
use p3_matrix::{dense::RowMajorMatrixView, stack::VerticalPair};
use p3_symmetric::MerkleCap;
use p3_uni_stark::{VerifierConstraintFolder, recompose_quotient_from_chunks};
use pqtc_hash::{
    Note, commitment, digest_to_elements, empty_leaf, keccak256, merkle_node, nullifier_hash,
    payout_digest, scope,
};
use pqtc_indexer::{IndexedBlock, Indexer, IndexerSnapshot};
use pqtc_merkle::MerkleTree;
use pqtc_poseidon_air::{NUM_WITHDRAWAL_COLS, TRACE_HEIGHT, WithdrawalAir, WithdrawalWitness};
use pqtc_security::{ParameterManifest, analyze_profile};
use pqtc_spec::{
    CanonicalSecret, Digest512, PROTOCOL_VERSION, PUBLIC_VALUES_COUNT, ScopeInput, TREE_DEPTH,
    WithdrawalStatement,
};
use pqtc_stark::{
    Challenge, Config, SecurityProfile,
    codec::{COMMON_HEADER_BYTES, decode_proof_parts, encode_proof_parts},
    crypto::{Transcript512, digest_words, proof_leaf_digest, proof_node_digest},
    prove_withdrawal, verify_withdrawal, withdrawal_config_from_os_entropy,
};
use serde::Serialize;

#[derive(Parser)]
#[command(name = "pqtc", version, about = "PQ Tornado Classic research CLI")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Generate a note from operating-system entropy.
    NoteNew {
        #[arg(long)]
        chain_id: u64,
        #[arg(long)]
        pool: String,
        #[arg(long)]
        parameter_id: String,
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Generate canonical parameter manifests.
    ParametersGenerate {
        #[arg(long, default_value = "parameters")]
        out_dir: PathBuf,
    },
    /// Generate the canonical 1,000-case cross-language vector corpus.
    VectorsGenerate {
        #[arg(long, default_value = "test-vectors/hash/v3.json")]
        out: PathBuf,
    },
    /// Generate Rust fixtures for Solidity verifier modules.
    VerifierVectorsGenerate {
        #[arg(long, default_value = "test-vectors/verifier/v3.json")]
        out: PathBuf,
    },
    /// Prove and verify the complete reference withdrawal AIR.
    BenchmarkWithdrawal {
        #[arg(long, default_value = "dev")]
        profile: String,
        #[arg(long)]
        out_dir: Option<PathBuf>,
        /// Emit one natively verified proof without benchmark mutation checks.
        #[arg(long, default_value_t = false)]
        fixture_only: bool,
    },

    /// Prepare a deposit commitment and nullifier from an encoded note.
    DepositPrepare {
        #[arg(long)]
        note: String,
        #[arg(long)]
        scope: String,
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Replay cross-checked deposit blocks and persist an index snapshot.
    TreeSync {
        #[arg(long)]
        scope: String,
        #[arg(long, default_value_t = 12)]
        confirmations: u64,
        #[arg(long)]
        primary: PathBuf,
        #[arg(long)]
        secondary: PathBuf,
        #[arg(long)]
        out: PathBuf,
    },
    /// Produce a confirmed Merkle path from a persisted snapshot.
    TreeProvePath {
        #[arg(long)]
        snapshot: PathBuf,
        #[arg(long)]
        commitment: String,
        #[arg(long)]
        out: PathBuf,
    },
    /// Generate canonical two-part withdrawal proof payloads from JSON inputs.
    ProveWithdraw {
        #[arg(long)]
        statement: PathBuf,
        #[arg(long)]
        witness: PathBuf,
        #[arg(long, default_value = "sepolia-v0.3")]
        profile: String,
        #[arg(long)]
        out_dir: PathBuf,
    },
    /// Verify canonical two-part withdrawal proof payloads without EVM execution.
    VerifyNative {
        #[arg(long)]
        statement: PathBuf,
        #[arg(long)]
        part_a: PathBuf,
        #[arg(long)]
        part_b: PathBuf,
        #[arg(long, default_value = "sepolia-v0.3")]
        profile: String,
    },
}

fn main() -> Result<()> {
    match Cli::parse().command {
        Command::NoteNew {
            chain_id,
            pool,
            parameter_id,
            out,
        } => {
            let note = Note::generate(
                chain_id,
                parse_hex::<20>(&pool)?,
                Digest512::from_bytes(parse_hex::<64>(&parameter_id)?),
            );
            let encoded = note.encode();
            if let Some(path) = out {
                fs::write(&path, encoded.as_bytes())
                    .with_context(|| format!("write {}", path.display()))?;
            } else {
                println!("{encoded}");
            }
        }
        Command::ParametersGenerate { out_dir } => {
            for profile in ["dev", "ci", "sepolia-v0.3"] {
                let manifest = ParameterManifest::profile(profile);
                let directory = out_dir.join(profile);
                fs::create_dir_all(&directory)?;
                fs::write(
                    directory.join("security-analysis.json"),
                    serde_json::to_vec_pretty(&analyze_profile(profile))?,
                )?;
                fs::write(directory.join("manifest.bin"), manifest.encode_binary()?)?;
                fs::write(
                    directory.join("manifest.json"),
                    serde_json::to_vec_pretty(&manifest)?,
                )?;
                fs::write(
                    directory.join("parameter-id.txt"),
                    format!("{}\n", manifest.id()?),
                )?;
            }
        }
        Command::VectorsGenerate { out } => generate_vectors(&out)?,
        Command::VerifierVectorsGenerate { out } => generate_verifier_vectors(&out)?,
        Command::BenchmarkWithdrawal {
            profile,
            out_dir,
            fixture_only,
        } => {
            let security_profile = parse_security_profile(&profile)?;
            let parameter = ParameterManifest::profile(&profile).id()?;
            let scope = Digest512 {
                left: [1; 32],
                right: [2; 32],
            };
            let nullifier_secret = CanonicalSecret::from_limbs([3; 8])?;
            let trapdoor = CanonicalSecret::from_limbs([4; 8])?;
            let leaf = commitment(scope, nullifier_secret, trapdoor);
            let mut tree = MerkleTree::new(scope);
            let (leaf_index, root) = tree.insert(leaf)?;
            let path = tree.path(leaf_index)?;
            let statement = WithdrawalStatement {
                scope,
                root,
                nullifier_hash: nullifier_hash(scope, nullifier_secret),
                payout_digest: payout_digest([5; 20], [6; 20], [0; 32]),
            };
            let witness = WithdrawalWitness {
                nullifier_secret,
                trapdoor,
                leaf_index,
                path_bits: path.path_bits(),
                siblings: path.siblings,
            };
            let config = withdrawal_config_from_os_entropy(security_profile, parameter, statement);
            let start = Instant::now();
            let first = prove_withdrawal(&config, statement, &witness)?;
            let prove_time = start.elapsed();
            let first_parts = encode_proof_parts(&first, security_profile, parameter, statement)?;
            if let Some(directory) = out_dir {
                fs::create_dir_all(&directory)?;
                fs::write(directory.join("part-a.pqtc"), &first_parts.part_a.bytes)?;
                fs::write(directory.join("part-b.pqtc"), &first_parts.part_b.bytes)?;
            }
            let decoded = decode_proof_parts(
                &first_parts.part_a.bytes,
                &first_parts.part_b.bytes,
                security_profile,
                parameter,
                statement,
            )?;
            let first_encoded_len = first_parts.part_a.bytes.len() + first_parts.part_b.bytes.len();
            if fixture_only {
                if !verify_withdrawal(&config, statement, &decoded) {
                    bail!("native verifier rejected generated withdrawal proof");
                }
                println!("proof_part_a_bytes={}", first_parts.part_a.bytes.len());
                println!("proof_part_b_bytes={}", first_parts.part_b.bytes.len());
                println!("proof_bytes={first_encoded_len}");
                println!("prove_ms={}", prove_time.as_millis());
                println!("canonical_roundtrip_verified=true");
                return Ok(());
            }
            let second = prove_withdrawal(&config, statement, &witness)?;
            let second_parts = encode_proof_parts(&second, security_profile, parameter, statement)?;
            if first_parts.part_a.bytes == second_parts.part_a.bytes
                && first_parts.part_b.bytes == second_parts.part_b.bytes
            {
                bail!("hiding prover emitted identical proofs for the same witness");
            }
            let first_valid = verify_withdrawal(&config, statement, &first);
            let second_valid = verify_withdrawal(&config, statement, &second);
            let decoded_valid = verify_withdrawal(&config, statement, &decoded);
            if !(first_valid && second_valid && decoded_valid) {
                bail!(
                    "native verifier rejected generated withdrawal proof: first={first_valid} second={second_valid} decoded={decoded_valid}"
                );
            }
            let wrong_parameter = Digest512 {
                left: [0xa5; 32],
                right: [0x5a; 32],
            };
            if decode_proof_parts(
                &first_parts.part_a.bytes,
                &first_parts.part_b.bytes,
                security_profile,
                wrong_parameter,
                statement,
            )
            .is_ok()
            {
                bail!("proof decoder accepted a mismatched parameter ID");
            }
            let mut reordered_public = first_parts.part_a.bytes.clone();
            let public_offset =
                COMMON_HEADER_BYTES - PUBLIC_VALUES_COUNT * core::mem::size_of::<u32>();
            for byte in 0..core::mem::size_of::<u32>() {
                reordered_public.swap(
                    public_offset + byte,
                    public_offset + (PUBLIC_VALUES_COUNT / 4) * core::mem::size_of::<u32>() + byte,
                );
            }
            if decode_proof_parts(
                &reordered_public,
                &first_parts.part_b.bytes,
                security_profile,
                parameter,
                statement,
            )
            .is_ok()
            {
                bail!("proof decoder accepted reordered public values");
            }
            for mutation in 0..100 {
                let mut part_a = first_parts.part_a.bytes.clone();
                let mut part_b = first_parts.part_b.bytes.clone();
                let corrupted = if mutation & 1 == 0 {
                    &mut part_a
                } else {
                    &mut part_b
                };
                let index = mutation * (corrupted.len() - 1) / 99;
                corrupted[index] ^= 1 << (mutation % 8);
                if let Ok(candidate) =
                    decode_proof_parts(&part_a, &part_b, security_profile, parameter, statement)
                {
                    if verify_withdrawal(&config, statement, &candidate) {
                        bail!("mutated proof {mutation} verified");
                    }
                }
            }
            let verify_time = start.elapsed();
            println!("trace_rows={TRACE_HEIGHT}");
            println!("trace_width={NUM_WITHDRAWAL_COLS}");
            println!("proof_part_a_bytes={}", first_parts.part_a.bytes.len());
            println!("proof_part_b_bytes={}", first_parts.part_b.bytes.len());
            println!("proof_bytes={first_encoded_len}");
            println!(
                "opened_trace_local={} opened_trace_next={} quotient_chunks={} quotient_chunk_width={} random_openings={}",
                first.opened_values.trace_local.len(),
                first.opened_values.trace_next.as_ref().map_or(0, Vec::len),
                first.opened_values.quotient_chunks.len(),
                first
                    .opened_values
                    .quotient_chunks
                    .first()
                    .map_or(0, Vec::len),
                first.opened_values.random.as_ref().map_or(0, Vec::len),
            );
            println!(
                "fri_rounds={} fri_inputs={} fri_final_poly={}",
                first.opening_proof.1.commit_phase_commits.len(),
                first.opening_proof.1.input_openings.len(),
                first.opening_proof.1.final_poly.len(),
            );
            for (input, opening) in first.opening_proof.1.input_openings.iter().enumerate() {
                let row_widths: Vec<usize> = opening
                    .opened_values
                    .first()
                    .map(|matrices| matrices.iter().map(Vec::len).collect())
                    .unwrap_or_default();
                println!(
                    "fri_input_{input}_queries={} matrix_widths={row_widths:?} salts_per_query={} path_hashes={}",
                    opening.opened_values.len(),
                    opening.opening_proof.0.first().map_or(0, Vec::len),
                    opening.opening_proof.1.sibling_hashes.len(),
                );
            }
            let hiding = &first.opening_proof.0;
            println!(
                "hiding_shapes={:?}",
                hiding
                    .iter()
                    .map(|round| round
                        .iter()
                        .map(|matrix| matrix.iter().map(Vec::len).collect::<Vec<_>>())
                        .collect::<Vec<_>>())
                    .collect::<Vec<_>>(),
            );
            println!("prove_ms={}", prove_time.as_millis());
            println!("verify_and_mutations_ms={}", verify_time.as_millis());
            println!("same_witness_proofs_differ=true");
            println!("canonical_roundtrip_verified=true");
            println!("structured_mutations_rejected=100");
        }
        Command::DepositPrepare { note, scope, out } => {
            let note = Note::parse(&note)?;
            let pool_scope = parse_application_digest(&scope)?;
            let prepared = serde_json::json!({
                "commitment": commitment(pool_scope, note.nullifier_secret, note.trapdoor).to_string(),
                "nullifier_hash": nullifier_hash(pool_scope, note.nullifier_secret).to_string(),
            });
            let encoded = serde_json::to_vec_pretty(&prepared)?;
            if let Some(path) = out {
                fs::write(path, encoded)?;
            } else {
                println!("{}", String::from_utf8(encoded).expect("JSON is UTF-8"));
            }
        }
        Command::TreeSync {
            scope,
            confirmations,
            primary,
            secondary,
            out,
        } => {
            let primary: Vec<IndexedBlock> = serde_json::from_slice(&fs::read(primary)?)?;
            let secondary: Vec<IndexedBlock> = serde_json::from_slice(&fs::read(secondary)?)?;
            if primary.len() != secondary.len() {
                bail!("RPC endpoint block counts differ");
            }
            let mut indexer = Indexer::new(parse_application_digest(&scope)?, confirmations)?;
            for (block, corroboration) in primary.into_iter().zip(&secondary) {
                indexer.apply_cross_checked(block, corroboration)?;
            }
            fs::write(out, serde_json::to_vec_pretty(&indexer.snapshot())?)?;
        }
        Command::TreeProvePath {
            snapshot,
            commitment,
            out,
        } => {
            let snapshot: IndexerSnapshot = serde_json::from_slice(&fs::read(snapshot)?)?;
            let indexer = Indexer::from_snapshot(snapshot)?;
            let (root, path) = indexer.confirmed_path(parse_application_digest(&commitment)?)?;
            fs::write(
                out,
                serde_json::to_vec_pretty(&serde_json::json!({
                    "root": root,
                    "path": path,
                }))?,
            )?;
        }
        Command::ProveWithdraw {
            statement,
            witness,
            profile,
            out_dir,
        } => {
            let statement: WithdrawalStatement = serde_json::from_slice(&fs::read(statement)?)?;
            validate_statement(statement)?;
            let witness: WithdrawalWitness = serde_json::from_slice(&fs::read(witness)?)?;
            let security_profile = parse_security_profile(&profile)?;
            let parameter = ParameterManifest::profile(&profile).id()?;
            let config = withdrawal_config_from_os_entropy(security_profile, parameter, statement);
            let proof = prove_withdrawal(&config, statement, &witness)?;
            if !verify_withdrawal(&config, statement, &proof) {
                bail!("native verification failed after proving");
            }
            let encoded = encode_proof_parts(&proof, security_profile, parameter, statement)?;
            fs::create_dir_all(&out_dir)?;
            fs::write(out_dir.join("part-a.pqtc"), &encoded.part_a.bytes)?;
            fs::write(out_dir.join("part-b.pqtc"), &encoded.part_b.bytes)?;
            fs::write(
                out_dir.join("metadata.json"),
                serde_json::to_vec_pretty(&serde_json::json!({
                    "version": PROTOCOL_VERSION,
                    "profile": profile,
                    "parameter_id": parameter.to_string(),
                    "statement_key": hex_value(&encoded.part_a.statement_key),
                    "proof_id": hex_value(&encoded.part_a.proof_id),
                    "part_a_bytes": encoded.part_a.bytes.len(),
                    "part_b_bytes": encoded.part_b.bytes.len(),
                }))?,
            )?;
        }
        Command::VerifyNative {
            statement,
            part_a,
            part_b,
            profile,
        } => {
            let statement: WithdrawalStatement = serde_json::from_slice(&fs::read(statement)?)?;
            validate_statement(statement)?;
            let security_profile = parse_security_profile(&profile)?;
            let parameter = ParameterManifest::profile(&profile).id()?;
            let part_a = fs::read(part_a)?;
            let part_b = fs::read(part_b)?;
            let proof =
                decode_proof_parts(&part_a, &part_b, security_profile, parameter, statement)?;
            let config = withdrawal_config_from_os_entropy(security_profile, parameter, statement);
            if !verify_withdrawal(&config, statement, &proof) {
                bail!("proof is invalid");
            }
            println!("valid=true");
        }
    }
    Ok(())
}

fn parse_hex<const N: usize>(value: &str) -> Result<[u8; N]> {
    let value = value.strip_prefix("0x").unwrap_or(value);
    let bytes = hex::decode(value).context("invalid hex")?;
    if bytes.len() != N {
        bail!("expected {N} bytes, got {}", bytes.len());
    }
    Ok(bytes.try_into().expect("length checked"))
}

fn parse_application_digest(value: &str) -> Result<Digest512> {
    let digest = Digest512::from_bytes(parse_hex::<64>(value)?);
    validate_application_digest(digest)?;
    Ok(digest)
}

fn validate_statement(statement: WithdrawalStatement) -> Result<()> {
    for (name, digest) in [
        ("scope", statement.scope),
        ("root", statement.root),
        ("nullifier_hash", statement.nullifier_hash),
        ("payout_digest", statement.payout_digest),
    ] {
        validate_application_digest(digest)
            .with_context(|| format!("{name} is not a canonical P2BB512 digest"))?;
    }
    Ok(())
}

fn validate_application_digest(digest: Digest512) -> Result<()> {
    if digest_to_elements(digest).is_none() {
        bail!("digest contains a noncanonical BabyBear limb");
    }
    Ok(())
}

fn parse_security_profile(value: &str) -> Result<SecurityProfile> {
    match value {
        "dev" => Ok(SecurityProfile::Dev),
        "ci" => Ok(SecurityProfile::Ci),
        "sepolia-v0.3" => Ok(SecurityProfile::SepoliaV03),
        _ => bail!("unknown security profile: {value}"),
    }
}

#[derive(Serialize)]
struct VectorFile {
    version: u16,
    count: usize,
    vectors: Vec<HashVector>,
}

#[derive(Serialize)]
struct HashVector {
    index: u32,
    chain_id: String,
    pool: String,
    denomination: String,
    parameter_id: String,
    scope: String,
    nullifier_secret: String,
    trapdoor: String,
    commitment: String,
    nullifier_hash: String,
    recipient: String,
    relayer: String,
    fee: String,
    payout_digest: String,
    zero_leaf: String,
    level_zero_node: String,
    root_after_insert: String,
}

fn generate_vectors(path: &PathBuf) -> Result<()> {
    let chain_id = 11_155_111u64;
    let pool = [0x11; 20];
    let denomination = u256(1_000_000_000_000_000);
    let parameter = ParameterManifest::profile("dev").id()?;
    let scope_input = ScopeInput {
        chain_id,
        pool,
        denomination,
        tree_depth: TREE_DEPTH,
        protocol_version: PROTOCOL_VERSION,
        parameter_id: parameter,
    };
    let pool_scope = scope(scope_input);
    let zero_leaf = empty_leaf(pool_scope);
    let mut tree = MerkleTree::new(pool_scope);
    let mut vectors = Vec::with_capacity(1_000);
    for index in 0..1_000u32 {
        let nullifier_secret = deterministic_secret(b"pqtc-nullifier-vector", index)?;
        let trapdoor = deterministic_secret(b"pqtc-trapdoor-vector", index)?;
        let note_commitment = commitment(pool_scope, nullifier_secret, trapdoor);
        let nullifier = nullifier_hash(pool_scope, nullifier_secret);
        let recipient_seed = deterministic_bytes(b"pqtc-recipient-vector", index);
        let relayer_seed = deterministic_bytes(b"pqtc-relayer-vector", index);
        let recipient: [u8; 20] = recipient_seed[12..].try_into().expect("fixed slice");
        let relayer: [u8; 20] = relayer_seed[12..].try_into().expect("fixed slice");
        let fee = u256(u128::from(index) * 1_000_000_000);
        let payout = payout_digest(recipient, relayer, fee);
        let level_zero_node = merkle_node(0, note_commitment, zero_leaf);
        let (_, root) = tree.insert(note_commitment)?;
        vectors.push(HashVector {
            index,
            chain_id: chain_id.to_string(),
            pool: hex_value(&pool),
            denomination: hex_value(&denomination),
            parameter_id: parameter.to_string(),
            scope: pool_scope.to_string(),
            nullifier_secret: nullifier_secret.to_string(),
            trapdoor: trapdoor.to_string(),
            commitment: note_commitment.to_string(),
            nullifier_hash: nullifier.to_string(),
            recipient: hex_value(&recipient),
            relayer: hex_value(&relayer),
            fee: hex_value(&fee),
            payout_digest: payout.to_string(),
            zero_leaf: zero_leaf.to_string(),
            level_zero_node: level_zero_node.to_string(),
            root_after_insert: root.to_string(),
        });
    }
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(
        path,
        serde_json::to_vec_pretty(&VectorFile {
            version: PROTOCOL_VERSION as u16,
            count: vectors.len(),
            vectors,
        })?,
    )?;
    Ok(())
}

fn deterministic_bytes(label: &[u8], index: u32) -> [u8; 32] {
    let mut input = Vec::with_capacity(label.len() + 4);
    input.extend_from_slice(label);
    input.extend_from_slice(&index.to_be_bytes());
    keccak256(&input)
}

fn deterministic_secret(label: &[u8], index: u32) -> Result<CanonicalSecret> {
    let mut input = Vec::with_capacity(label.len() + 9);
    input.extend_from_slice(label);
    input.extend_from_slice(&index.to_be_bytes());
    let limb_offset = input.len();
    input.extend_from_slice(&[0; 5]);
    let limbs = core::array::from_fn(|limb| {
        input[limb_offset] = limb as u8;
        let mut attempt = 0u32;
        loop {
            input[limb_offset + 1..].copy_from_slice(&attempt.to_be_bytes());
            let candidate =
                u32::from_be_bytes(keccak256(&input)[..4].try_into().expect("fixed slice"));
            if candidate < pqtc_spec::BABY_BEAR_MODULUS {
                break candidate;
            }
            attempt = attempt.wrapping_add(1);
        }
    });
    CanonicalSecret::from_limbs(limbs).map_err(Into::into)
}

fn u256(value: u128) -> [u8; 32] {
    let mut out = [0u8; 32];
    out[16..].copy_from_slice(&value.to_be_bytes());
    out
}

fn hex_value(bytes: &[u8]) -> String {
    format!("0x{}", hex::encode(bytes))
}

#[derive(Serialize)]
struct VerifierVectorFile {
    version: u16,
    fields: Vec<FieldVector>,
    extensions: Vec<ExtensionVector>,
    transcripts: Vec<TranscriptVector>,
    mmcs: Vec<MmcsVector>,
    fri_folds: Vec<FriFoldVector>,
    air: AirVector,
}

#[derive(Serialize)]
struct FieldVector {
    a: u32,
    b: u32,
    add: u32,
    sub: u32,
    mul: u32,
    inv_a: u32,
}

#[derive(Serialize)]
struct ExtensionVector {
    a: [u32; 4],
    b: [u32; 4],
    add: [u32; 4],
    sub: [u32; 4],
    mul: [u32; 4],
}

#[derive(Serialize)]
struct TranscriptVector {
    parameter_id: String,
    public_values: Vec<u32>,
    observed_field: u32,
    observed_commitment: String,
    challenges: Vec<u32>,
    bits14: usize,
}

#[derive(Serialize)]
struct MmcsVector {
    root: String,
    leaf_values: Vec<u32>,
    leaf_index: usize,
    siblings: Vec<String>,
}

#[derive(Serialize)]
struct FriFoldVector {
    index: usize,
    log_height: usize,
    beta: [u32; 4],
    low: [u32; 4],
    high: [u32; 4],
    expected: [u32; 4],
}

#[derive(Serialize)]
struct AirVector {
    local: Vec<[u32; 4]>,
    next: Vec<[u32; 4]>,
    public_values: Vec<[u32; 4]>,
    is_first: [u32; 4],
    is_last: [u32; 4],
    is_transition: [u32; 4],
    alpha: [u32; 4],
    expected: [u32; 4],
    zeta: [u32; 4],
    selectors: [[u32; 4]; 4],
    quotient_openings: Vec<[u32; 4]>,
    quotient: [u32; 4],
}

fn generate_air_vector() -> AirVector {
    let local: Vec<Challenge> = (0..NUM_WITHDRAWAL_COLS)
        .map(|index| ext_from_array(deterministic_ext(b"pqtc-air-local", index as u32)))
        .collect();
    let next: Vec<Challenge> = (0..NUM_WITHDRAWAL_COLS)
        .map(|index| ext_from_array(deterministic_ext(b"pqtc-air-next", index as u32)))
        .collect();
    let public_base: Vec<BabyBear> = (0..PUBLIC_VALUES_COUNT as u32)
        .map(|index| BabyBear::from_u32(deterministic_ext(b"pqtc-air-public", index)[0]))
        .collect();
    let is_first = ext_from_array(deterministic_ext(b"pqtc-air-first", 0));
    let is_last = ext_from_array(deterministic_ext(b"pqtc-air-last", 0));
    let is_transition = ext_from_array(deterministic_ext(b"pqtc-air-transition", 0));
    let alpha = ext_from_array(deterministic_ext(b"pqtc-air-alpha", 0));

    let main = VerticalPair::new(
        RowMajorMatrixView::new_row(&local),
        RowMajorMatrixView::new_row(&next),
    );
    let preprocessed = VerticalPair::new(
        RowMajorMatrixView::new(&[], 0),
        RowMajorMatrixView::new(&[], 0),
    );
    let mut folder: VerifierConstraintFolder<'_, Config> = VerifierConstraintFolder {
        main,
        preprocessed,
        preprocessed_window: RowWindow::from_two_rows(&[], &[]),
        periodic_values: &[],
        public_values: &public_base,
        is_first_row: is_first,
        is_last_row: is_last,
        is_transition,
        alpha,
        accumulator: Challenge::ZERO,
    };
    WithdrawalAir::default().eval(&mut folder);
    let zeta = ext_from_array(deterministic_ext(b"pqtc-air-zeta", 0));
    let trace_domain =
        TwoAdicMultiplicativeCoset::new(BabyBear::ONE, 8).expect("valid trace domain");
    let domain_selectors = trace_domain.selectors_at_point(zeta);
    let proof_trace_domain =
        TwoAdicMultiplicativeCoset::new(BabyBear::ONE, 9).expect("valid hiding trace domain");
    let quotient_domains = proof_trace_domain
        .try_create_disjoint_domain(1 << 13)
        .expect("valid quotient domain")
        .split_domains(16);
    let quotient_chunks: Vec<Vec<Challenge>> = (0..16)
        .map(|chunk| {
            (0..4)
                .map(|coefficient| {
                    ext_from_array(deterministic_ext(
                        b"pqtc-air-quotient",
                        (chunk * 4 + coefficient) as u32,
                    ))
                })
                .collect()
        })
        .collect();
    let quotient =
        recompose_quotient_from_chunks::<Config>(&quotient_domains, &quotient_chunks, zeta);
    AirVector {
        local: local.iter().copied().map(ext_to_array).collect(),
        next: next.iter().copied().map(ext_to_array).collect(),
        public_values: public_base
            .iter()
            .map(|value| [value.as_canonical_u32(), 0, 0, 0])
            .collect(),
        is_first: ext_to_array(is_first),
        is_last: ext_to_array(is_last),
        is_transition: ext_to_array(is_transition),
        alpha: ext_to_array(alpha),
        expected: ext_to_array(folder.accumulator),
        zeta: ext_to_array(zeta),
        selectors: [
            ext_to_array(domain_selectors.is_first_row),
            ext_to_array(domain_selectors.is_last_row),
            ext_to_array(domain_selectors.is_transition),
            ext_to_array(domain_selectors.inv_vanishing),
        ],
        quotient_openings: quotient_chunks
            .into_iter()
            .flatten()
            .map(ext_to_array)
            .collect(),
        quotient: ext_to_array(quotient),
    }
}

fn ext_from_array(coefficients: [u32; 4]) -> Challenge {
    Challenge::from_basis_coefficients_fn(|index| BabyBear::from_u32(coefficients[index]))
}

fn ext_to_array(value: Challenge) -> [u32; 4] {
    let coefficients: &[BabyBear] = value.as_basis_coefficients_slice();
    core::array::from_fn(|index| coefficients[index].as_canonical_u32())
}

fn generate_verifier_vectors(path: &PathBuf) -> Result<()> {
    const P: u64 = 2_013_265_921;
    let mut fields = Vec::with_capacity(10_000);
    for index in 0..10_000u32 {
        let a = u32::from_be_bytes(
            deterministic_bytes(b"pqtc-field-a", index)[..4]
                .try_into()
                .unwrap(),
        ) % (P as u32 - 1)
            + 1;
        let b = u32::from_be_bytes(
            deterministic_bytes(b"pqtc-field-b", index)[..4]
                .try_into()
                .unwrap(),
        ) % P as u32;
        fields.push(FieldVector {
            a,
            b,
            add: ((u64::from(a) + u64::from(b)) % P) as u32,
            sub: ((u64::from(a) + P - u64::from(b)) % P) as u32,
            mul: ((u64::from(a) * u64::from(b)) % P) as u32,
            inv_a: bb_pow(a, P - 2),
        });
    }

    let mut extensions = Vec::with_capacity(1_000);
    for index in 0..1_000u32 {
        let a = deterministic_ext(b"pqtc-ext-a", index);
        let b = deterministic_ext(b"pqtc-ext-b", index);
        extensions.push(ExtensionVector {
            a,
            b,
            add: core::array::from_fn(|i| bb_add(a[i], b[i])),
            sub: core::array::from_fn(|i| bb_sub(a[i], b[i])),
            mul: ext_mul(a, b),
        });
    }

    let mut transcripts = Vec::with_capacity(32);
    for index in 0..32u32 {
        let parameter_id = Digest512::from_bytes(
            [
                deterministic_bytes(b"pqtc-transcript-parameter-left", index),
                deterministic_bytes(b"pqtc-transcript-parameter-right", index),
            ]
            .concat()
            .try_into()
            .unwrap(),
        );
        let public_values: Vec<u32> = (0..8)
            .map(|item| {
                u32::from_be_bytes(
                    deterministic_bytes(b"pqtc-transcript-public", index * 8 + item)[..4]
                        .try_into()
                        .unwrap(),
                ) % P as u32
            })
            .collect();
        let public_fields: Vec<BabyBear> = public_values
            .iter()
            .copied()
            .map(BabyBear::from_u32)
            .collect();
        let observed_field = fields[index as usize].a;
        let observed_commitment = Digest512::from_bytes(
            [
                deterministic_bytes(b"pqtc-transcript-commitment-left", index),
                deterministic_bytes(b"pqtc-transcript-commitment-right", index),
            ]
            .concat()
            .try_into()
            .unwrap(),
        );
        let mut transcript = Transcript512::new(parameter_id, &public_fields);
        transcript.observe(BabyBear::from_u32(observed_field));
        transcript.observe(MerkleCap::<BabyBear, [u64; 8]>::new(vec![digest_words(
            observed_commitment,
        )]));
        let challenges = (0..8)
            .map(|_| {
                let value: BabyBear = transcript.sample();
                value.as_canonical_u32()
            })
            .collect();
        let bits14 = transcript.sample_bits(14);
        transcripts.push(TranscriptVector {
            parameter_id: parameter_id.to_string(),
            public_values,
            observed_field,
            observed_commitment: observed_commitment.to_string(),
            challenges,
            bits14,
        });
    }

    let mut mmcs = Vec::with_capacity(16);
    for fixture in 0..16u32 {
        let width = 1 + fixture as usize % 8;
        let leaves: Vec<Vec<u32>> = (0..64u32)
            .map(|leaf| {
                (0..width)
                    .map(|column| {
                        u32::from_be_bytes(
                            deterministic_bytes(
                                b"pqtc-mmcs",
                                fixture * 10_000 + leaf * 16 + column as u32,
                            )[..4]
                                .try_into()
                                .unwrap(),
                        ) % P as u32
                    })
                    .collect()
            })
            .collect();
        let mut layer: Vec<Digest512> = leaves
            .iter()
            .map(|values| proof_leaf_digest(values))
            .collect();
        let leaf_index = (fixture as usize * 13 + 7) % 64;
        let leaf_values = leaves[leaf_index].clone();
        let mut current_index = leaf_index;
        let mut siblings = Vec::with_capacity(6);
        while layer.len() > 1 {
            siblings.push(layer[current_index ^ 1].to_string());
            layer = layer
                .chunks_exact(2)
                .map(|pair| proof_node_digest(pair[0], pair[1]))
                .collect();
            current_index >>= 1;
        }
        mmcs.push(MmcsVector {
            root: layer[0].to_string(),
            leaf_values,
            leaf_index,
            siblings,
        });
    }

    let mut fri_folds = Vec::with_capacity(1_000);
    for index in 0..1_000u32 {
        let log_height = 1 + index as usize % 15;
        let domain_index = (index as usize * 7919) & ((1usize << log_height) - 1);
        let beta = deterministic_ext(b"pqtc-fri-beta", index);
        let low = deterministic_ext(b"pqtc-fri-low", index);
        let high = deterministic_ext(b"pqtc-fri-high", index);
        fri_folds.push(FriFoldVector {
            index: domain_index,
            log_height,
            beta,
            low,
            high,
            expected: fri_fold(domain_index, log_height, beta, low, high),
        });
    }
    let air = generate_air_vector();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(
        path,
        serde_json::to_vec_pretty(&VerifierVectorFile {
            version: PROTOCOL_VERSION as u16,
            fields,
            extensions,
            transcripts,
            mmcs,
            fri_folds,
            air,
        })?,
    )?;
    Ok(())
}

fn bb_add(a: u32, b: u32) -> u32 {
    ((u64::from(a) + u64::from(b)) % 2_013_265_921) as u32
}
fn bb_sub(a: u32, b: u32) -> u32 {
    ((u64::from(a) + 2_013_265_921 - u64::from(b)) % 2_013_265_921) as u32
}
fn bb_mul(a: u32, b: u32) -> u32 {
    ((u64::from(a) * u64::from(b)) % 2_013_265_921) as u32
}
fn bb_pow(mut base: u32, mut exponent: u64) -> u32 {
    let mut result = 1;
    while exponent != 0 {
        if exponent & 1 != 0 {
            result = bb_mul(result, base);
        }
        base = bb_mul(base, base);
        exponent >>= 1;
    }
    result
}
fn deterministic_ext(label: &[u8], index: u32) -> [u32; 4] {
    let bytes = deterministic_bytes(label, index);
    core::array::from_fn(|coefficient| {
        u32::from_be_bytes(
            bytes[coefficient * 4..coefficient * 4 + 4]
                .try_into()
                .unwrap(),
        ) % 2_013_265_921
    })
}
fn ext_mul(a: [u32; 4], b: [u32; 4]) -> [u32; 4] {
    let t0 = bb_mul(a[0], b[0]);
    let t1 = bb_add(bb_mul(a[0], b[1]), bb_mul(a[1], b[0]));
    let t2 = bb_add(
        bb_add(bb_mul(a[0], b[2]), bb_mul(a[1], b[1])),
        bb_mul(a[2], b[0]),
    );
    let t3 = bb_add(
        bb_add(
            bb_add(bb_mul(a[0], b[3]), bb_mul(a[1], b[2])),
            bb_mul(a[2], b[1]),
        ),
        bb_mul(a[3], b[0]),
    );
    let t4 = bb_add(
        bb_add(bb_mul(a[1], b[3]), bb_mul(a[2], b[2])),
        bb_mul(a[3], b[1]),
    );
    let t5 = bb_add(bb_mul(a[2], b[3]), bb_mul(a[3], b[2]));
    let t6 = bb_mul(a[3], b[3]);
    [
        bb_add(t0, bb_mul(11, t4)),
        bb_add(t1, bb_mul(11, t5)),
        bb_add(t2, bb_mul(11, t6)),
        t3,
    ]
}
fn fri_fold(
    index: usize,
    log_height: usize,
    beta: [u32; 4],
    low: [u32; 4],
    high: [u32; 4],
) -> [u32; 4] {
    let mut generator = 0x1a42_7a41;
    for _ in log_height + 1..27 {
        generator = bb_mul(generator, generator);
    }
    let mut reversed = 0usize;
    for bit in 0..log_height {
        reversed = (reversed << 1) | ((index >> bit) & 1);
    }
    let x = bb_pow(generator, reversed as u64);
    let inverse_two_x = bb_mul(1_006_632_961, bb_pow(x, 2_013_265_919));
    let even: [u32; 4] = core::array::from_fn(|i| bb_mul(bb_add(low[i], high[i]), 1_006_632_961));
    let odd_base: [u32; 4] =
        core::array::from_fn(|i| bb_mul(bb_sub(low[i], high[i]), inverse_two_x));
    let odd = ext_mul(odd_base, beta);
    core::array::from_fn(|i| bb_add(even[i], odd[i]))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn application_digest_parser_rejects_noncanonical_limb() {
        let mut bytes = [0u8; 64];
        bytes[..4].copy_from_slice(&pqtc_spec::BABY_BEAR_MODULUS.to_be_bytes());
        assert!(parse_application_digest(&hex::encode(bytes)).is_err());
    }

    #[test]
    fn security_profile_parser_accepts_v3_and_rejects_v2() {
        assert_eq!(
            parse_security_profile("sepolia-v0.3").unwrap(),
            SecurityProfile::SepoliaV03
        );
        assert!(parse_security_profile("sepolia-v0.2").is_err());
    }

    #[test]
    fn deterministic_vector_secrets_are_canonical_big_endian_limbs() {
        let secret = deterministic_secret(b"pqtc-test-secret", 7).unwrap();
        assert!(
            secret
                .limbs()
                .iter()
                .all(|&limb| limb < pqtc_spec::BABY_BEAR_MODULUS)
        );
        assert_eq!(
            secret.to_string().parse::<CanonicalSecret>().unwrap(),
            secret
        );
    }

    #[test]
    fn witness_json_rejects_noncanonical_secret_limbs() {
        let secret = CanonicalSecret::from_limbs([1; 8]).unwrap();
        let witness = WithdrawalWitness {
            nullifier_secret: secret,
            trapdoor: secret,
            leaf_index: 0,
            path_bits: [0; TREE_DEPTH as usize],
            siblings: [Digest512::ZERO; TREE_DEPTH as usize],
        };
        let mut json = serde_json::to_value(witness).unwrap();
        json["nullifier_secret"] = serde_json::Value::String(format!(
            "0x{:08x}{}",
            pqtc_spec::BABY_BEAR_MODULUS,
            "00".repeat(28)
        ));
        assert!(serde_json::from_value::<WithdrawalWitness>(json).is_err());
    }

    #[test]
    fn statement_validation_checks_all_sixty_four_limbs() {
        let canonical = Digest512::ZERO;
        let mut bytes = [0u8; 64];
        bytes[60..].copy_from_slice(&pqtc_spec::BABY_BEAR_MODULUS.to_be_bytes());
        let noncanonical = Digest512::from_bytes(bytes);
        let statement = WithdrawalStatement {
            scope: canonical,
            root: canonical,
            nullifier_hash: canonical,
            payout_digest: noncanonical,
        };
        assert_eq!(statement.public_values().len(), 64);
        assert!(validate_statement(statement).is_err());
    }
}
```

</details>

## `crates/pqtc-hash/Cargo.toml`

- Bytes: 439
- SHA-256: `b1e69d03afb27cfbb30dfe53ab0892378d15481b53ec3efb129b9cc4c90ece61`

<details><summary>Complete file</summary>

```toml
[package]
name = "pqtc-hash"
version.workspace = true
edition.workspace = true
license.workspace = true
rust-version.workspace = true

[dependencies]
base64.workspace = true
hex.workspace = true
p3-baby-bear.workspace = true
p3-field.workspace = true
p3-symmetric.workspace = true
pqtc-spec = { path = "../pqtc-spec" }
rand.workspace = true
serde.workspace = true
sha3.workspace = true
thiserror.workspace = true

[lints]
workspace = true
```

</details>

## `crates/pqtc-hash/src/lib.rs`

- Bytes: 23,669
- SHA-256: `44d0e1f817ffbfd92c65ffee0bb34eb1b5002c4fcce7f88fee75e3661a5266f6`

<details><summary>Complete file</summary>

```rust
//! Poseidon2/BabyBear application hashes, proof-only Keccak hashes, and the versioned note codec.

use std::sync::LazyLock;

use base64::{Engine as _, engine::general_purpose::URL_SAFE_NO_PAD};
use p3_baby_bear::{BabyBear, Poseidon2BabyBear, default_babybear_poseidon2_16};
use p3_field::{PrimeCharacteristicRing, PrimeField32, integers::QuotientMap};
use p3_symmetric::Permutation;
use pqtc_spec::{
    CanonicalError, CanonicalSecret, Digest512, ScopeInput, WithdrawalStatement, domains,
};
use rand::{CryptoRng, Rng};
use sha3::{Digest as _, Keccak256};
use thiserror::Error;

pub const NOTE_PREFIX: &str = "pqtc-note-v3:";
const NOTE_MAGIC: [u8; 4] = *b"PQTN";
const NOTE_VERSION: u16 = 3;
const NOTE_BODY_LEN: usize = 162;
const NOTE_BINARY_LEN: usize = NOTE_BODY_LEN + 32;
const P2BB512_WIDTH: usize = 16;
const P2BB512_RATE: usize = 4;
const P2BB512_VERSION: u32 = 1;

static P2BB512_PERMUTATION: LazyLock<Poseidon2BabyBear<P2BB512_WIDTH>> =
    LazyLock::new(default_babybear_poseidon2_16);

#[must_use]
pub fn keccak256(bytes: &[u8]) -> [u8; 32] {
    Keccak256::digest(bytes).into()
}

#[must_use]
pub fn k512(tag: u8, payload: &[u8]) -> Digest512 {
    let mut left = Keccak256::new();
    left.update([0, tag]);
    left.update(payload);
    let mut right = Keccak256::new();
    right.update([1, tag]);
    right.update(payload);
    Digest512 {
        left: left.finalize().into(),
        right: right.finalize().into(),
    }
}

/// Hashes canonical field elements with the protocol P2BB512 sponge.
///
/// # Panics
///
/// Panics when a framing value is not canonical in the `BabyBear` field or
/// when the payload length exceeds `u32::MAX`.
#[must_use]
pub fn p2bb512(tag: u8, payload_byte_length: u32, aux: u32, payload: &[BabyBear]) -> Digest512 {
    let payload_element_count =
        u32::try_from(payload.len()).expect("P2BB512 payload element count exceeds u32");
    let mut state = [BabyBear::ZERO; P2BB512_WIDTH];
    state[P2BB512_RATE] = BabyBear::new(P2BB512_VERSION);
    state[P2BB512_RATE + 1] = BabyBear::new(u32::from(tag));
    state[P2BB512_RATE + 2] = BabyBear::from_canonical_checked(payload_byte_length)
        .expect("P2BB512 payload byte length is not canonical BabyBear");
    state[P2BB512_RATE + 3] = BabyBear::from_canonical_checked(payload_element_count)
        .expect("P2BB512 payload element count is not canonical BabyBear");
    state[P2BB512_RATE + 4] =
        BabyBear::from_canonical_checked(aux).expect("P2BB512 aux is not canonical BabyBear");

    if payload.is_empty() {
        P2BB512_PERMUTATION.permute_mut(&mut state);
    } else {
        for block in payload.chunks(P2BB512_RATE) {
            for (rate, &element) in state[..P2BB512_RATE].iter_mut().zip(block) {
                *rate += element;
            }
            P2BB512_PERMUTATION.permute_mut(&mut state);
        }
    }

    let mut output = [BabyBear::ZERO; P2BB512_WIDTH];
    for block_index in 0..(P2BB512_WIDTH / P2BB512_RATE) {
        if block_index != 0 {
            P2BB512_PERMUTATION.permute_mut(&mut state);
        }
        let start = block_index * P2BB512_RATE;
        output[start..start + P2BB512_RATE].copy_from_slice(&state[..P2BB512_RATE]);
    }
    elements_to_digest(output)
}

#[must_use]
pub fn digest_to_elements(digest: Digest512) -> Option<[BabyBear; P2BB512_WIDTH]> {
    let bytes = digest.to_bytes();
    let mut elements = [BabyBear::ZERO; P2BB512_WIDTH];
    for (element, bytes) in elements.iter_mut().zip(bytes.chunks_exact(4)) {
        let [a, b, c, d] = bytes else {
            unreachable!("chunks_exact(4) only yields four-byte chunks");
        };
        let value = u32::from_be_bytes([*a, *b, *c, *d]);
        *element = BabyBear::from_canonical_checked(value)?;
    }
    Some(elements)
}

#[must_use]
pub fn elements_to_digest(elements: [BabyBear; P2BB512_WIDTH]) -> Digest512 {
    let mut bytes = [0u8; 64];
    for (&element, output) in elements.iter().zip(bytes.chunks_exact_mut(4)) {
        output.copy_from_slice(&element.as_canonical_u32().to_be_bytes());
    }
    Digest512::from_bytes(bytes)
}

fn encode_bytes(bytes: &[u8], output: &mut [BabyBear]) {
    assert_eq!(output.len(), bytes.len().div_ceil(2));
    for (chunk, element) in bytes.chunks(2).zip(output) {
        let value = u16::from_be_bytes([chunk[0], chunk.get(1).copied().unwrap_or(0)]);
        *element = BabyBear::new(u32::from(value));
    }
}

fn canonical_digest(digest: Digest512) -> [BabyBear; P2BB512_WIDTH] {
    digest_to_elements(digest).expect("P2BB512 digest contains a noncanonical BabyBear element")
}

fn secret_elements(secret: CanonicalSecret) -> [BabyBear; CanonicalSecret::LIMB_COUNT] {
    secret.into_limbs().map(BabyBear::new)
}

#[must_use]
pub fn scope(input: ScopeInput) -> Digest512 {
    let encoded = input.encode();
    let mut payload = [BabyBear::ZERO; 65];
    encode_bytes(&encoded, &mut payload);
    p2bb512(domains::SCOPE, 129, 0, &payload)
}

#[must_use]
pub fn commitment(
    scope: Digest512,
    nullifier_secret: CanonicalSecret,
    trapdoor: CanonicalSecret,
) -> Digest512 {
    let mut payload = [BabyBear::ZERO; 32];
    payload[..16].copy_from_slice(&canonical_digest(scope));
    payload[16..24].copy_from_slice(&secret_elements(nullifier_secret));
    payload[24..].copy_from_slice(&secret_elements(trapdoor));
    p2bb512(domains::NOTE, 128, 0, &payload)
}

#[must_use]
pub fn nullifier_hash(scope: Digest512, nullifier_secret: CanonicalSecret) -> Digest512 {
    let mut payload = [BabyBear::ZERO; 24];
    payload[..16].copy_from_slice(&canonical_digest(scope));
    payload[16..].copy_from_slice(&secret_elements(nullifier_secret));
    p2bb512(domains::NULLIFIER, 96, 0, &payload)
}

#[must_use]
pub fn empty_leaf(scope: Digest512) -> Digest512 {
    let payload = canonical_digest(scope);
    p2bb512(domains::EMPTY_LEAF, 64, 0, &payload)
}

#[must_use]
pub fn merkle_node(level: u8, left: Digest512, right: Digest512) -> Digest512 {
    let mut payload = [BabyBear::ZERO; 32];
    payload[..16].copy_from_slice(&canonical_digest(left));
    payload[16..].copy_from_slice(&canonical_digest(right));
    p2bb512(domains::APP_MERKLE_NODE, 128, u32::from(level), &payload)
}

#[must_use]
pub fn payout_digest(recipient: [u8; 20], relayer: [u8; 20], fee: [u8; 32]) -> Digest512 {
    let mut encoded = [0u8; 72];
    encoded[..20].copy_from_slice(&recipient);
    encoded[20..40].copy_from_slice(&relayer);
    encoded[40..].copy_from_slice(&fee);
    let mut payload = [BabyBear::ZERO; 36];
    encode_bytes(&encoded, &mut payload);
    p2bb512(domains::PAYOUT, 72, 0, &payload)
}

#[must_use]
pub fn statement_hash(statement: WithdrawalStatement) -> Digest512 {
    let mut payload = [BabyBear::ZERO; 64];
    for (output, digest) in payload.chunks_exact_mut(16).zip([
        statement.scope,
        statement.root,
        statement.nullifier_hash,
        statement.payout_digest,
    ]) {
        output.copy_from_slice(&canonical_digest(digest));
    }
    p2bb512(domains::STATEMENT, 256, 0, &payload)
}

#[must_use]
pub fn parameter_id(manifest: &[u8]) -> Digest512 {
    k512(domains::PARAMETER_MANIFEST, manifest)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Note {
    pub chain_id: u64,
    pub pool: [u8; 20],
    pub parameter_id: Digest512,
    pub nullifier_secret: CanonicalSecret,
    pub trapdoor: CanonicalSecret,
}

impl Note {
    /// Generates a note with two independently sampled canonical secrets using
    /// operating-system randomness.
    #[must_use]
    pub fn generate(chain_id: u64, pool: [u8; 20], parameter_id: Digest512) -> Self {
        Self {
            chain_id,
            pool,
            parameter_id,
            nullifier_secret: CanonicalSecret::generate(),
            trapdoor: CanonicalSecret::generate(),
        }
    }

    /// Generates a note with two independently sampled canonical secrets using
    /// the supplied cryptographic RNG.
    pub fn random<R: CryptoRng + Rng>(
        chain_id: u64,
        pool: [u8; 20],
        parameter_id: Digest512,
        rng: &mut R,
    ) -> Self {
        Self {
            chain_id,
            pool,
            parameter_id,
            nullifier_secret: CanonicalSecret::random_with(rng),
            trapdoor: CanonicalSecret::random_with(rng),
        }
    }

    #[must_use]
    pub fn encode_binary(self) -> [u8; NOTE_BINARY_LEN] {
        let mut out = [0u8; NOTE_BINARY_LEN];
        out[..4].copy_from_slice(&NOTE_MAGIC);
        out[4..6].copy_from_slice(&NOTE_VERSION.to_be_bytes());
        out[6..14].copy_from_slice(&self.chain_id.to_be_bytes());
        out[14..34].copy_from_slice(&self.pool);
        out[34..98].copy_from_slice(&self.parameter_id.to_bytes());
        out[98..130].copy_from_slice(&self.nullifier_secret.to_bytes());
        out[130..162].copy_from_slice(&self.trapdoor.to_bytes());
        let checksum = note_checksum(&out[..NOTE_BODY_LEN]);
        out[NOTE_BODY_LEN..].copy_from_slice(&checksum);
        out
    }

    #[must_use]
    pub fn encode(self) -> String {
        format!(
            "{NOTE_PREFIX}{}",
            URL_SAFE_NO_PAD.encode(self.encode_binary())
        )
    }

    /// Parses and validates a canonical encoded note.
    ///
    /// # Errors
    ///
    /// Returns [`NoteError`] when the prefix, base64, length, magic, version,
    /// checksum, or either secret encoding is invalid.
    pub fn parse(encoded: &str) -> Result<Self, NoteError> {
        let value = encoded.strip_prefix(NOTE_PREFIX).ok_or(NoteError::Prefix)?;
        let bytes = URL_SAFE_NO_PAD
            .decode(value)
            .map_err(|_| NoteError::Base64)?;
        if bytes.len() != NOTE_BINARY_LEN {
            return Err(NoteError::Length {
                actual: bytes.len(),
            });
        }
        if bytes[..4] != NOTE_MAGIC {
            return Err(NoteError::Magic);
        }
        if u16::from_be_bytes([bytes[4], bytes[5]]) != NOTE_VERSION {
            return Err(NoteError::Version);
        }
        if bytes[NOTE_BODY_LEN..] != note_checksum(&bytes[..NOTE_BODY_LEN]) {
            return Err(NoteError::Checksum);
        }
        let mut pool = [0u8; 20];
        pool.copy_from_slice(&bytes[14..34]);
        let mut parameter = [0u8; 64];
        parameter.copy_from_slice(&bytes[34..98]);
        let mut nullifier_secret_bytes = [0u8; CanonicalSecret::BYTE_LEN];
        nullifier_secret_bytes.copy_from_slice(&bytes[98..130]);
        let nullifier_secret =
            CanonicalSecret::from_bytes(nullifier_secret_bytes).map_err(NoteError::Secret)?;
        let mut trapdoor_bytes = [0u8; CanonicalSecret::BYTE_LEN];
        trapdoor_bytes.copy_from_slice(&bytes[130..162]);
        let trapdoor = CanonicalSecret::from_bytes(trapdoor_bytes).map_err(NoteError::Secret)?;
        Ok(Self {
            chain_id: u64::from_be_bytes([
                bytes[6], bytes[7], bytes[8], bytes[9], bytes[10], bytes[11], bytes[12], bytes[13],
            ]),
            pool,
            parameter_id: Digest512::from_bytes(parameter),
            nullifier_secret,
            trapdoor,
        })
    }
}

fn note_checksum(body: &[u8]) -> [u8; 32] {
    let mut hash = Keccak256::new();
    hash.update([0, domains::NOTE]);
    hash.update(body);
    hash.finalize().into()
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum NoteError {
    #[error("note prefix is not pqtc-note-v3")]
    Prefix,
    #[error("note payload is not canonical base64url")]
    Base64,
    #[error("note length must be {NOTE_BINARY_LEN} bytes, got {actual}")]
    Length { actual: usize },
    #[error("note magic is invalid")]
    Magic,
    #[error("note version is unsupported")]
    Version,
    #[error("note checksum is invalid")]
    Checksum,
    #[error("note secret is not canonical: {0}")]
    Secret(CanonicalError),
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::{SeedableRng, rngs::StdRng};

    fn digest_with_offset(offset: u32) -> Digest512 {
        elements_to_digest(core::array::from_fn(|index| {
            BabyBear::new(offset + u32::try_from(index).expect("index fits u32"))
        }))
    }

    fn repeated_secret(byte: u8) -> CanonicalSecret {
        CanonicalSecret::from_bytes([byte; CanonicalSecret::BYTE_LEN])
            .expect("repeated-byte fixture is canonical")
    }

    #[test]
    fn k512_is_ethereum_keccak_and_remains_proof_only() {
        assert_eq!(
            hex::encode(keccak256(b"")),
            "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
        );
        assert_ne!(
            hex::encode(keccak256(b"")),
            "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a"
        );
        assert_eq!(
            parameter_id(b"manifest"),
            k512(domains::PARAMETER_MANIFEST, b"manifest")
        );

        let payload = [BabyBear::new(7), BabyBear::new(9)];
        assert_ne!(
            k512(domains::SCOPE, &[0, 7, 0, 9]),
            p2bb512(domains::SCOPE, 4, 0, &payload)
        );
    }

    #[test]
    fn p2bb512_is_deterministic_and_binds_domain_and_lengths() {
        let payload = core::array::from_fn::<_, 5, _>(|index| {
            BabyBear::new(u32::try_from(index).expect("index fits u32"))
        });
        let baseline = p2bb512(domains::SCOPE, 9, 0, &payload);
        assert_eq!(baseline, p2bb512(domains::SCOPE, 9, 0, &payload));
        assert_ne!(baseline, p2bb512(domains::NOTE, 9, 0, &payload));
        assert_ne!(baseline, p2bb512(domains::SCOPE, 10, 0, &payload));

        let mut extra_element = payload.to_vec();
        extra_element.push(BabyBear::ZERO);
        assert_ne!(baseline, p2bb512(domains::SCOPE, 9, 0, &extra_element));
        assert!(digest_to_elements(baseline).is_some());
        assert_eq!(
            hex::encode(baseline.to_bytes()),
            "683e24183b7b8e38192b953f0cb670ac637d03f6311b44f17458f2eb5ca9dc901d7bcacd1146c2774c97f80b0fd111e7270e6fe038bcbfec2103b6f644a96520"
        );
        let mut permutation_input =
            core::array::from_fn(|index| BabyBear::new(u32::try_from(index).expect("index fits")));
        P2BB512_PERMUTATION.permute_mut(&mut permutation_input);
        assert_eq!(
            permutation_input.map(|element| element.as_canonical_u32()),
            [
                1_906_786_279,
                1_737_026_427,
                1_959_749_225,
                700_325_316,
                1_638_050_605,
                1_021_608_788,
                1_726_691_001,
                1_761_127_344,
                1_552_405_120,
                417_318_995,
                36_799_261,
                1_215_172_152,
                614_923_223,
                1_300_746_575,
                957_311_597,
                304_856_115,
            ]
        );
        let payload_0_to_15: [BabyBear; 16] =
            core::array::from_fn(|index| BabyBear::new(u32::try_from(index).expect("index fits")));
        assert_eq!(
            hex::encode(p2bb512(domains::SCOPE, 32, 0, &payload_0_to_15).to_bytes()),
            "192285c83ad82d235f4020c4185fb99a5d7a4574217a7fa5097c082c4c905cfd69df098f455618e612d7819f26e68e4d5ff4842c4d5177ae479caee05752c4bd"
        );
    }

    #[test]
    fn digest_elements_round_trip_canonically_in_halves() {
        let elements = core::array::from_fn(|index| {
            BabyBear::from_canonical_checked(
                BabyBear::ORDER_U32 - 1 - u32::try_from(index).expect("index fits u32"),
            )
            .expect("value is canonical")
        });
        let digest = elements_to_digest(elements);
        assert_eq!(&digest.left[..4], &(BabyBear::ORDER_U32 - 1).to_be_bytes());
        assert_eq!(&digest.right[..4], &(BabyBear::ORDER_U32 - 9).to_be_bytes());
        assert_eq!(digest_to_elements(digest), Some(elements));

        let mut noncanonical = digest.to_bytes();
        noncanonical[..4].copy_from_slice(&BabyBear::ORDER_U32.to_be_bytes());
        let noncanonical = Digest512::from_bytes(noncanonical);
        assert_eq!(digest_to_elements(noncanonical), None);
        assert!(std::panic::catch_unwind(|| empty_leaf(noncanonical)).is_err());
    }

    #[test]
    fn note_round_trip_and_corruption_detection() {
        let mut rng = StdRng::seed_from_u64(7);
        let note = Note::random(
            11_155_111,
            [3; 20],
            Digest512 {
                left: [4; 32],
                right: [5; 32],
            },
            &mut rng,
        );
        let encoded = note.encode();
        assert!(encoded.starts_with("pqtc-note-v3:"));
        assert_eq!(Note::parse(&encoded), Ok(note));

        let canonical_binary = note.encode_binary();
        assert_eq!(&canonical_binary[4..6], &3u16.to_be_bytes());

        let v2_prefix = encoded.replacen("pqtc-note-v3:", "pqtc-note-v2:", 1);
        assert_eq!(Note::parse(&v2_prefix), Err(NoteError::Prefix));

        let mut v2_binary = canonical_binary;
        v2_binary[4..6].copy_from_slice(&2u16.to_be_bytes());
        let checksum = note_checksum(&v2_binary[..NOTE_BODY_LEN]);
        v2_binary[NOTE_BODY_LEN..].copy_from_slice(&checksum);
        let v2_version = format!("{NOTE_PREFIX}{}", URL_SAFE_NO_PAD.encode(v2_binary));
        assert_eq!(Note::parse(&v2_version), Err(NoteError::Version));

        let mut corrupted_binary = canonical_binary;
        corrupted_binary[100] ^= 1;
        let bad = format!("{NOTE_PREFIX}{}", URL_SAFE_NO_PAD.encode(corrupted_binary));
        assert_eq!(Note::parse(&bad), Err(NoteError::Checksum));

        let mut noncanonical_binary = canonical_binary;
        noncanonical_binary[98..102].copy_from_slice(&BabyBear::ORDER_U32.to_be_bytes());
        let checksum = note_checksum(&noncanonical_binary[..NOTE_BODY_LEN]);
        noncanonical_binary[NOTE_BODY_LEN..].copy_from_slice(&checksum);
        let noncanonical = format!(
            "{NOTE_PREFIX}{}",
            URL_SAFE_NO_PAD.encode(noncanonical_binary)
        );
        assert!(matches!(
            Note::parse(&noncanonical),
            Err(NoteError::Secret(CanonicalError::NonCanonicalField {
                value: BabyBear::ORDER_U32
            }))
        ));
    }

    #[test]
    fn canonical_scope_schema_is_big_endian_u16_and_length_bound() {
        let input = ScopeInput {
            chain_id: u64::MAX,
            pool: [0xff; 20],
            denomination: [0xff; 32],
            tree_depth: u8::MAX,
            protocol_version: u32::MAX,
            parameter_id: Digest512 {
                left: [0xff; 32],
                right: [0xfe; 32],
            },
        };
        let encoded = input.encode();
        assert_eq!(&encoded[..8], &u64::MAX.to_be_bytes());
        assert_eq!(&encoded[28..60], &[0xff; 32]);
        assert_eq!(&encoded[61..65], &u32::MAX.to_be_bytes());

        let mut payload = [BabyBear::ZERO; 65];
        encode_bytes(&encoded, &mut payload);
        assert_eq!(payload[64].as_canonical_u32(), 0xfe00);
        assert_eq!(scope(input), p2bb512(domains::SCOPE, 129, 0, &payload));
    }

    #[test]
    fn application_hashes_are_canonical_and_deterministic() {
        let scope_input = ScopeInput {
            chain_id: 11_155_111,
            pool: [1; 20],
            denomination: [2; 32],
            tree_depth: 20,
            protocol_version: 3,
            parameter_id: parameter_id(b"manifest"),
        };
        let scope_digest = scope(scope_input);
        let nullifier_secret = repeated_secret(3);
        let trapdoor = repeated_secret(4);
        let commitment_digest = commitment(scope_digest, nullifier_secret, trapdoor);
        let nullifier_digest = nullifier_hash(scope_digest, nullifier_secret);
        let empty_digest = empty_leaf(scope_digest);
        let root = merkle_node(0, commitment_digest, empty_digest);
        let payout = payout_digest([5; 20], [6; 20], [7; 32]);
        let statement = WithdrawalStatement {
            scope: scope_digest,
            root,
            nullifier_hash: nullifier_digest,
            payout_digest: payout,
        };
        let statement_digest = statement_hash(statement);

        for digest in [
            scope_digest,
            commitment_digest,
            nullifier_digest,
            empty_digest,
            root,
            payout,
            statement_digest,
        ] {
            assert!(digest_to_elements(digest).is_some());
        }
        assert_eq!(scope_digest, scope(scope_input));
        assert_eq!(
            commitment_digest,
            commitment(scope_digest, nullifier_secret, trapdoor)
        );
        assert_eq!(statement_digest, statement_hash(statement));
    }

    #[test]
    fn every_secret_limb_is_binding() {
        let scope_digest = p2bb512(domains::SCOPE, 0, 0, &[]);
        let zero = CanonicalSecret::from_limbs([0; CanonicalSecret::LIMB_COUNT]).unwrap();
        let baseline_commitment = commitment(scope_digest, zero, zero);
        let baseline_nullifier = nullifier_hash(scope_digest, zero);

        for index in 0..CanonicalSecret::LIMB_COUNT {
            let mut limbs = [0; CanonicalSecret::LIMB_COUNT];
            limbs[index] = 1;
            let changed = CanonicalSecret::from_limbs(limbs).unwrap();
            assert_ne!(
                commitment(scope_digest, changed, zero),
                baseline_commitment,
                "nullifier-secret limb {index} did not affect commitment"
            );
            assert_ne!(
                commitment(scope_digest, zero, changed),
                baseline_commitment,
                "trapdoor limb {index} did not affect commitment"
            );
            assert_ne!(
                nullifier_hash(scope_digest, changed),
                baseline_nullifier,
                "nullifier-secret limb {index} did not affect nullifier"
            );
        }
    }

    #[test]
    fn canonical_v3_application_vector() {
        let scope_digest = scope(ScopeInput {
            chain_id: 11_155_111,
            pool: [1; 20],
            denomination: [2; 32],
            tree_depth: 20,
            protocol_version: 3,
            parameter_id: parameter_id(b"manifest"),
        });
        let nullifier_secret = CanonicalSecret::from_limbs([3, 5, 7, 11, 13, 17, 19, 23]).unwrap();
        let trapdoor = CanonicalSecret::from_limbs([29, 31, 37, 41, 43, 47, 53, 59]).unwrap();

        assert_eq!(
            hex::encode(scope_digest.to_bytes()),
            "29d774fa067d5844644966e1326483b24085e8fe771fdf570d64b61815b83cdf31d6b62414ead4750956548b6643d0831fdba8e822e0ada718ffd4d3470a56c7"
        );
        assert_eq!(
            hex::encode(commitment(scope_digest, nullifier_secret, trapdoor).to_bytes()),
            "174026330a3b3def58a2547403d04234035843a84b7814a330ff65e4049592cc69da09314cc70f0d6ead8d1d38a5dd2f45f5e9741b7e063f24acd369233a1979"
        );
        assert_eq!(
            hex::encode(nullifier_hash(scope_digest, nullifier_secret).to_bytes()),
            "703e079c63caf3b65227079e3201df600319e2fb294395ae278a63183b0b8fe2078b9d397692e1e14e7952cd3f80d97301a420444d733f0b2fb440fc18deaba6"
        );
    }
    #[test]
    fn merkle_level_order_and_digest_halves_are_binding() {
        let a = digest_with_offset(1);
        let b = digest_with_offset(101);
        assert_ne!(merkle_node(0, a, b), merkle_node(1, a, b));
        assert_ne!(merkle_node(0, a, b), merkle_node(0, b, a));

        let mut changed = digest_to_elements(a).expect("digest is canonical");
        changed[8] += BabyBear::ONE;
        let changed_right_half = elements_to_digest(changed);
        assert_ne!(merkle_node(0, a, b), merkle_node(0, changed_right_half, b));
    }
}
```

</details>

## `crates/pqtc-indexer/Cargo.toml`

- Bytes: 309
- SHA-256: `2cc72f6eb0f2af8e1ecdf14df0336cc2613f4da55c5350f9e1bcd554f24c462b`

<details><summary>Complete file</summary>

```toml
[package]
name = "pqtc-indexer"
version.workspace = true
edition.workspace = true
license.workspace = true
rust-version.workspace = true

[dependencies]
pqtc-merkle = { path = "../pqtc-merkle" }
pqtc-spec = { path = "../pqtc-spec" }
serde.workspace = true
thiserror.workspace = true

[lints]
workspace = true
```

</details>

## `crates/pqtc-indexer/src/lib.rs`

- Bytes: 10,178
- SHA-256: `30f34740b54c72a7eb2d22c9443e0b44ab9688911dc1ecbc494e4e71cd8c9479`

<details><summary>Complete file</summary>

```rust
//! Reorg-aware deposit-log replay and Merkle-path construction.

use pqtc_merkle::{MerklePath, MerkleTree};
use pqtc_spec::{Digest512, PROTOCOL_VERSION};
use serde::{Deserialize, Serialize};
use thiserror::Error;

pub const SNAPSHOT_VERSION: u16 = PROTOCOL_VERSION as u16;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DepositLog {
    pub commitment: Digest512,
    pub leaf_index: u32,
    pub root: Digest512,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexedBlock {
    pub number: u64,
    pub hash: [u8; 32],
    pub parent_hash: [u8; 32],
    pub deposits: Vec<DepositLog>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexerSnapshot {
    pub version: u16,
    pub scope: Digest512,
    pub confirmations: u64,
    pub blocks: Vec<IndexedBlock>,
}

#[derive(Clone, Debug)]
pub struct Indexer {
    scope: Digest512,
    confirmations: u64,
    blocks: Vec<IndexedBlock>,
    tree: MerkleTree,
}

impl Indexer {
    /// Constructs an indexer after validating the canonical P2BB512 scope.
    ///
    /// # Errors
    ///
    /// Returns [`IndexError::NonCanonicalDigest`] for a noncanonical scope.
    pub fn new(scope: Digest512, confirmations: u64) -> Result<Self, IndexError> {
        Ok(Self {
            scope,
            confirmations,
            blocks: Vec::new(),
            tree: MerkleTree::try_new(scope).map_err(|_| IndexError::NonCanonicalDigest)?,
        })
    }

    pub fn apply_block(&mut self, block: IndexedBlock) -> Result<(), IndexError> {
        if let Some(tip) = self.blocks.last() {
            if block.parent_hash != tip.hash {
                let ancestor = self
                    .blocks
                    .iter()
                    .position(|candidate| candidate.hash == block.parent_hash)
                    .ok_or(IndexError::UnknownParent)?;
                self.blocks.truncate(ancestor + 1);
                self.rebuild()?;
            }
            let expected = self.blocks.last().expect("ancestor retained").number + 1;
            if block.number != expected {
                return Err(IndexError::NonSequentialBlock {
                    expected,
                    actual: block.number,
                });
            }
        }
        self.apply_deposits(&block.deposits)?;
        self.blocks.push(block);
        Ok(())
    }

    pub fn confirmed_path(
        &self,
        commitment: Digest512,
    ) -> Result<(Digest512, MerklePath), IndexError> {
        let tip = self.blocks.last().ok_or(IndexError::NoBlocks)?.number;
        let deposit = self
            .blocks
            .iter()
            .flat_map(|block| block.deposits.iter().map(move |log| (block.number, log)))
            .find(|(_, log)| log.commitment == commitment)
            .ok_or(IndexError::UnknownCommitment)?;
        if tip.saturating_sub(deposit.0) < self.confirmations {
            return Err(IndexError::Unconfirmed);
        }
        Ok((
            self.tree.root(),
            self.tree
                .path(deposit.1.leaf_index)
                .map_err(|_| IndexError::UnknownCommitment)?,
        ))
    }

    #[must_use]
    pub fn tip(&self) -> Option<(u64, [u8; 32])> {
        self.blocks.last().map(|block| (block.number, block.hash))
    }

    #[must_use]
    pub fn snapshot(&self) -> IndexerSnapshot {
        IndexerSnapshot {
            version: SNAPSHOT_VERSION,
            scope: self.scope,
            confirmations: self.confirmations,
            blocks: self.blocks.clone(),
        }
    }

    pub fn from_snapshot(snapshot: IndexerSnapshot) -> Result<Self, IndexError> {
        if snapshot.version != SNAPSHOT_VERSION {
            return Err(IndexError::UnsupportedSnapshot(snapshot.version));
        }
        let mut indexer = Self::new(snapshot.scope, snapshot.confirmations)?;
        for block in snapshot.blocks {
            indexer.apply_block(block)?;
        }
        Ok(indexer)
    }

    pub fn apply_cross_checked(
        &mut self,
        primary: IndexedBlock,
        secondary: &IndexedBlock,
    ) -> Result<(), IndexError> {
        if &primary != secondary {
            return Err(IndexError::RpcMismatch(primary.number));
        }
        self.apply_block(primary)
    }

    fn apply_deposits(&mut self, deposits: &[DepositLog]) -> Result<(), IndexError> {
        for log in deposits {
            let (index, root) = self
                .tree
                .insert(log.commitment)
                .map_err(|_| IndexError::InvalidDeposit)?;
            if index != log.leaf_index || root != log.root {
                return Err(IndexError::EventMismatch { index });
            }
        }
        Ok(())
    }

    fn rebuild(&mut self) -> Result<(), IndexError> {
        self.tree = MerkleTree::try_new(self.scope).map_err(|_| IndexError::NonCanonicalDigest)?;
        let deposits: Vec<_> = self
            .blocks
            .iter()
            .flat_map(|block| block.deposits.clone())
            .collect();
        self.apply_deposits(&deposits)
    }
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum IndexError {
    #[error("application digest contains a noncanonical BabyBear limb")]
    NonCanonicalDigest,
    #[error("block parent is not in the retained chain")]
    UnknownParent,
    #[error("expected block {expected}, got {actual}")]
    NonSequentialBlock { expected: u64, actual: u64 },
    #[error("deposit event at leaf {index} does not match replay")]
    EventMismatch { index: u32 },
    #[error("deposit is invalid")]
    InvalidDeposit,
    #[error("no blocks have been indexed")]
    NoBlocks,
    #[error("commitment is not indexed")]
    UnknownCommitment,
    #[error("deposit has not reached the configured confirmation depth")]
    Unconfirmed,
    #[error("unsupported index snapshot version {0}")]
    UnsupportedSnapshot(u16),
    #[error("RPC endpoints disagree at block {0}")]
    RpcMismatch(u64),
}

#[cfg(test)]
mod tests {
    use super::*;

    fn digest(n: u8) -> Digest512 {
        Digest512 {
            left: [n; 32],
            right: [n + 1; 32],
        }
    }

    #[test]
    fn rolls_back_to_known_parent_and_replays() {
        let scope = digest(1);
        let mut source = MerkleTree::new(scope);
        let leaf_a = digest(3);
        let (index_a, root_a) = source.insert(leaf_a).unwrap();
        let block_a = IndexedBlock {
            number: 10,
            hash: [10; 32],
            parent_hash: [9; 32],
            deposits: vec![DepositLog {
                commitment: leaf_a,
                leaf_index: index_a,
                root: root_a,
            }],
        };
        let mut indexer = Indexer::new(scope, 0).unwrap();
        indexer.apply_block(block_a).unwrap();
        let leaf_b = digest(4);
        let (index_b, root_b) = source.insert(leaf_b).unwrap();
        indexer
            .apply_block(IndexedBlock {
                number: 11,
                hash: [11; 32],
                parent_hash: [10; 32],
                deposits: vec![DepositLog {
                    commitment: leaf_b,
                    leaf_index: index_b,
                    root: root_b,
                }],
            })
            .unwrap();

        let mut fork = MerkleTree::new(scope);
        fork.insert(leaf_a).unwrap();
        let leaf_c = digest(5);
        let (index_c, root_c) = fork.insert(leaf_c).unwrap();
        indexer
            .apply_block(IndexedBlock {
                number: 11,
                hash: [12; 32],
                parent_hash: [10; 32],
                deposits: vec![DepositLog {
                    commitment: leaf_c,
                    leaf_index: index_c,
                    root: root_c,
                }],
            })
            .unwrap();
        assert!(indexer.confirmed_path(leaf_b).is_err());
        assert_eq!(indexer.confirmed_path(leaf_c).unwrap().0, root_c);
    }

    #[test]
    fn snapshot_replays_and_rpc_cross_check_rejects_disagreement() {
        let scope = digest(7);
        let mut source = MerkleTree::new(scope);
        let leaf = digest(9);
        let (leaf_index, root) = source.insert(leaf).unwrap();
        let block = IndexedBlock {
            number: 1,
            hash: [1; 32],
            parent_hash: [0; 32],
            deposits: vec![DepositLog {
                commitment: leaf,
                leaf_index,
                root,
            }],
        };
        let mut indexer = Indexer::new(scope, 0).unwrap();
        indexer.apply_cross_checked(block.clone(), &block).unwrap();
        let snapshot = indexer.snapshot();
        assert_eq!(snapshot.version, 3);
        let restored = Indexer::from_snapshot(snapshot).unwrap();
        assert_eq!(restored.confirmed_path(leaf).unwrap().0, root);
        let mut conflicting = block.clone();
        conflicting.hash = [2; 32];
        assert_eq!(
            indexer.apply_cross_checked(block, &conflicting),
            Err(IndexError::RpcMismatch(1))
        );
    }

    #[test]
    fn rejects_v2_snapshot_and_noncanonical_digests() {
        let scope = digest(1);
        let snapshot = IndexerSnapshot {
            version: 2,
            scope,
            confirmations: 0,
            blocks: Vec::new(),
        };
        assert!(matches!(
            Indexer::from_snapshot(snapshot),
            Err(IndexError::UnsupportedSnapshot(2))
        ));

        let mut bytes = [0u8; 64];
        bytes[..4].copy_from_slice(&pqtc_spec::BABY_BEAR_MODULUS.to_be_bytes());
        let invalid = Digest512::from_bytes(bytes);
        assert!(matches!(
            Indexer::new(invalid, 0),
            Err(IndexError::NonCanonicalDigest)
        ));

        let mut indexer = Indexer::new(scope, 0).unwrap();
        let block = IndexedBlock {
            number: 1,
            hash: [1; 32],
            parent_hash: [0; 32],
            deposits: vec![DepositLog {
                commitment: invalid,
                leaf_index: 0,
                root: Digest512::ZERO,
            }],
        };
        assert_eq!(indexer.apply_block(block), Err(IndexError::InvalidDeposit));
    }
}
```

</details>

## `crates/pqtc-merkle/Cargo.toml`

- Bytes: 373
- SHA-256: `b2d2a8a9e78c6f0edddd6c629b7bdc49cf4428b43fc241aa60dcb20956cc0647`

<details><summary>Complete file</summary>

```toml
[package]
name = "pqtc-merkle"
version.workspace = true
edition.workspace = true
license.workspace = true
rust-version.workspace = true

[dependencies]
pqtc-hash = { path = "../pqtc-hash" }
pqtc-spec = { path = "../pqtc-spec" }
serde.workspace = true
thiserror.workspace = true

[dev-dependencies]
hex.workspace = true
serde_json.workspace = true

[lints]
workspace = true
```

</details>

## `crates/pqtc-merkle/src/lib.rs`

- Bytes: 8,027
- SHA-256: `e88b08bede72a6c3d12b582d6bdb2e4f0f073719469a5383579605dcea164609`

<details><summary>Complete file</summary>

```rust
//! Append-only depth-20 P2BB512 application Merkle tree.

use pqtc_hash::{digest_to_elements, empty_leaf, merkle_node};
use pqtc_spec::{Digest512, TREE_DEPTH};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use thiserror::Error;

pub const CAPACITY: u32 = 1 << TREE_DEPTH;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct MerklePath {
    pub leaf_index: u32,
    pub siblings: [Digest512; TREE_DEPTH as usize],
}

impl MerklePath {
    #[must_use]
    pub fn root(&self, leaf: Digest512) -> Digest512 {
        let mut current = leaf;
        for (level, sibling) in self.siblings.iter().enumerate() {
            current = if self.leaf_index & (1 << level) == 0 {
                merkle_node(level_u8(level), current, *sibling)
            } else {
                merkle_node(level_u8(level), *sibling, current)
            };
        }
        current
    }

    #[must_use]
    pub fn path_bits(&self) -> [u8; TREE_DEPTH as usize] {
        core::array::from_fn(|level| ((self.leaf_index >> level) & 1) as u8)
    }
}

#[derive(Clone, Debug)]
pub struct MerkleTree {
    zeros: [Digest512; TREE_DEPTH as usize + 1],
    filled_subtrees: [Digest512; TREE_DEPTH as usize],
    leaves: Vec<Digest512>,
    commitments: HashSet<Digest512>,
    root: Digest512,
}

impl MerkleTree {
    /// Constructs a tree for a canonical P2BB512 scope.
    ///
    /// # Panics
    ///
    /// Panics when `scope` contains a noncanonical `BabyBear` limb. Untrusted
    /// inputs must use [`Self::try_new`].
    #[must_use]
    pub fn new(scope: Digest512) -> Self {
        Self::try_new(scope).expect("Merkle scope contains a noncanonical BabyBear limb")
    }

    /// Constructs a tree after validating every scope limb.
    ///
    /// # Errors
    ///
    /// Returns [`MerkleError::NonCanonicalDigest`] for a noncanonical scope.
    pub fn try_new(scope: Digest512) -> Result<Self, MerkleError> {
        ensure_canonical(scope)?;
        let mut zeros = [Digest512::ZERO; TREE_DEPTH as usize + 1];
        zeros[0] = empty_leaf(scope);
        for level in 0..TREE_DEPTH as usize {
            zeros[level + 1] = merkle_node(level_u8(level), zeros[level], zeros[level]);
        }
        Ok(Self {
            filled_subtrees: core::array::from_fn(|level| zeros[level]),
            leaves: Vec::new(),
            commitments: HashSet::new(),
            root: zeros[TREE_DEPTH as usize],
            zeros,
        })
    }

    #[must_use]
    pub const fn root(&self) -> Digest512 {
        self.root
    }

    #[must_use]
    pub fn len(&self) -> u32 {
        u32::try_from(self.leaves.len()).unwrap_or(u32::MAX)
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.leaves.is_empty()
    }

    #[must_use]
    pub fn zeros(&self) -> &[Digest512; TREE_DEPTH as usize + 1] {
        &self.zeros
    }

    /// Inserts one unique nonzero commitment and returns its index and new root.
    ///
    /// # Errors
    ///
    /// Returns [`MerkleError`] when the commitment is zero or duplicated, or
    /// when the tree is full.
    pub fn insert(&mut self, leaf: Digest512) -> Result<(u32, Digest512), MerkleError> {
        ensure_canonical(leaf)?;
        if leaf.is_zero() {
            return Err(MerkleError::ZeroCommitment);
        }
        if self.leaves.len() >= CAPACITY as usize {
            return Err(MerkleError::Full);
        }
        if !self.commitments.insert(leaf) {
            return Err(MerkleError::DuplicateCommitment);
        }

        let leaf_index = u32::try_from(self.leaves.len()).map_err(|_| MerkleError::Full)?;
        let mut current = leaf;
        let mut index = leaf_index;
        for level in 0..TREE_DEPTH as usize {
            if index & 1 == 0 {
                self.filled_subtrees[level] = current;
                current = merkle_node(level_u8(level), current, self.zeros[level]);
            } else {
                current = merkle_node(level_u8(level), self.filled_subtrees[level], current);
            }
            index >>= 1;
        }
        self.leaves.push(leaf);
        self.root = current;
        Ok((leaf_index, current))
    }

    /// Returns the authentication path for an inserted leaf.
    ///
    /// # Errors
    ///
    /// Returns [`MerkleError::UnknownLeaf`] when `leaf_index` is not present.
    pub fn path(&self, leaf_index: u32) -> Result<MerklePath, MerkleError> {
        if leaf_index as usize >= self.leaves.len() {
            return Err(MerkleError::UnknownLeaf { index: leaf_index });
        }
        let mut siblings = [Digest512::ZERO; TREE_DEPTH as usize];
        let mut nodes = self.leaves.clone();
        let mut index = leaf_index as usize;
        for (level, sibling) in siblings.iter_mut().enumerate() {
            *sibling = nodes.get(index ^ 1).copied().unwrap_or(self.zeros[level]);
            if nodes.len() & 1 == 1 {
                nodes.push(self.zeros[level]);
            }
            nodes = nodes
                .chunks_exact(2)
                .map(|pair| merkle_node(level_u8(level), pair[0], pair[1]))
                .collect();
            index >>= 1;
        }
        let path = MerklePath {
            leaf_index,
            siblings,
        };
        debug_assert_eq!(path.root(self.leaves[leaf_index as usize]), self.root);
        Ok(path)
    }

    #[must_use]
    pub fn leaf(&self, index: u32) -> Option<Digest512> {
        self.leaves.get(index as usize).copied()
    }
}

fn level_u8(level: usize) -> u8 {
    u8::try_from(level).unwrap_or_default()
}

fn ensure_canonical(digest: Digest512) -> Result<(), MerkleError> {
    digest_to_elements(digest)
        .map(|_| ())
        .ok_or(MerkleError::NonCanonicalDigest)
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum MerkleError {
    #[error("digest contains a noncanonical BabyBear limb")]
    NonCanonicalDigest,
    #[error("commitment cannot be zero")]
    ZeroCommitment,
    #[error("commitment already exists")]
    DuplicateCommitment,
    #[error("tree is full")]
    Full,
    #[error("leaf index {index} is not present")]
    UnknownLeaf { index: u32 },
}

#[cfg(test)]
mod tests {
    use super::*;

    fn digest(n: u8) -> Digest512 {
        Digest512 {
            left: [n; 32],
            right: [n.wrapping_add(1); 32],
        }
    }

    #[test]
    fn roots_and_paths_match_after_every_insert() {
        let mut tree = MerkleTree::new(digest(9));
        for i in 1..=64 {
            let leaf = digest(i);
            let (index, root) = tree.insert(leaf).unwrap();
            assert_eq!(tree.path(index).unwrap().root(leaf), root);
            for prior in 0..=index {
                assert_eq!(
                    tree.path(prior).unwrap().root(tree.leaf(prior).unwrap()),
                    root
                );
            }
        }
    }

    #[test]
    fn rejects_zero_duplicate_and_unknown_leaf() {
        let mut tree = MerkleTree::new(digest(9));
        assert_eq!(
            tree.insert(Digest512::ZERO),
            Err(MerkleError::ZeroCommitment)
        );
        tree.insert(digest(1)).unwrap();
        assert_eq!(
            tree.insert(digest(1)),
            Err(MerkleError::DuplicateCommitment)
        );
        assert_eq!(tree.path(1), Err(MerkleError::UnknownLeaf { index: 1 }));
    }

    #[test]
    fn merkle_node_is_bound_to_its_level() {
        let left = digest(1);
        let right = digest(2);
        assert_ne!(merkle_node(0, left, right), merkle_node(1, left, right));
    }

    #[test]
    fn rejects_noncanonical_scope_and_commitment() {
        let mut bytes = [0u8; 64];
        bytes[..4].copy_from_slice(&pqtc_spec::BABY_BEAR_MODULUS.to_be_bytes());
        let invalid = Digest512::from_bytes(bytes);
        assert!(matches!(
            MerkleTree::try_new(invalid),
            Err(MerkleError::NonCanonicalDigest)
        ));
        let mut tree = MerkleTree::new(digest(1));
        assert_eq!(tree.insert(invalid), Err(MerkleError::NonCanonicalDigest));
    }
}
```

</details>

## `crates/pqtc-poseidon-air/Cargo.toml`

- Bytes: 603
- SHA-256: `9adea4eb899121cad7fd644aa9af75f6c73f0ca51c39a17767b24d7d600f7afb`

<details><summary>Complete file</summary>

```toml
[package]
name = "pqtc-poseidon-air"
version.workspace = true
edition.workspace = true
license.workspace = true
rust-version.workspace = true

[dependencies]
p3-air.workspace = true
p3-baby-bear.workspace = true
p3-field.workspace = true
p3-matrix.workspace = true
p3-poseidon2.workspace = true
p3-poseidon2-air.workspace = true
p3-symmetric.workspace = true
p3-uni-stark.workspace = true
pqtc-hash = { path = "../pqtc-hash" }
pqtc-spec = { path = "../pqtc-spec" }
serde.workspace = true
thiserror.workspace = true

[dev-dependencies]
pqtc-merkle = { path = "../pqtc-merkle" }

[lints]
workspace = true
```

</details>

## `crates/pqtc-poseidon-air/src/air.rs`

- Bytes: 23,561
- SHA-256: `feb6d3a9949b69b55acc20e9b8826e0086bef1f9f7ae296df8ed4cafc61a3c53`

<details><summary>Complete file</summary>

```rust
#![allow(
    clippy::many_single_char_names,
    clippy::needless_pass_by_value,
    clippy::needless_range_loop,
    clippy::too_many_arguments,
    clippy::too_many_lines
)]

use core::borrow::Borrow;

use p3_air::{Air, AirBuilder, BaseAir, ConstraintReport, WindowAccess, check_all_constraints};
use p3_baby_bear::{
    BABYBEAR_POSEIDON2_HALF_FULL_ROUNDS, BABYBEAR_POSEIDON2_PARTIAL_ROUNDS_16,
    BABYBEAR_POSEIDON2_RC_16_EXTERNAL_FINAL, BABYBEAR_POSEIDON2_RC_16_EXTERNAL_INITIAL,
    BABYBEAR_POSEIDON2_RC_16_INTERNAL, BABYBEAR_S_BOX_DEGREE, BabyBear,
    GenericPoseidon2LinearLayersBabyBear, default_babybear_poseidon2_16,
};
use p3_field::PrimeCharacteristicRing;
use p3_matrix::{Matrix, dense::RowMajorMatrix};
use p3_poseidon2_air::{
    Poseidon2Air, Poseidon2Cols, RoundConstants, generate_trace_rows, num_cols,
};
use p3_symmetric::Permutation;
use p3_uni_stark::SubAirBuilder;
use pqtc_hash::digest_to_elements;
use pqtc_spec::{PUBLIC_VALUES_COUNT, WithdrawalStatement, domains};

use crate::{RelationError, WithdrawalWitness, check_witness, public_values};

const WIDTH: usize = 16;
const RATE: usize = 4;
const REGS: usize = 0;
const HALF: usize = BABYBEAR_POSEIDON2_HALF_FULL_ROUNDS;
const PARTIAL: usize = BABYBEAR_POSEIDON2_PARTIAL_ROUNDS_16;
type InnerAir = Poseidon2Air<
    BabyBear,
    GenericPoseidon2LinearLayersBabyBear,
    WIDTH,
    BABYBEAR_S_BOX_DEGREE,
    REGS,
    HALF,
    PARTIAL,
>;
type InnerCols<T> = Poseidon2Cols<T, WIDTH, BABYBEAR_S_BOX_DEGREE, REGS, HALF, PARTIAL>;

pub const NUM_POSEIDON_COLS: usize =
    num_cols::<WIDTH, BABYBEAR_S_BOX_DEGREE, REGS, HALF, PARTIAL>();
pub(crate) const IS_NOTE: usize = NUM_POSEIDON_COLS;
pub(crate) const IS_NULLIFIER: usize = IS_NOTE + 1;
pub(crate) const IS_MERKLE: usize = IS_NULLIFIER + 1;
pub(crate) const IS_PAYOUT: usize = IS_MERKLE + 1;
pub(crate) const IS_PADDING: usize = IS_PAYOUT + 1;
pub(crate) const STEP_BITS: usize = IS_PADDING + 1;
pub(crate) const LEVEL_BITS: usize = STEP_BITS + 4;
pub(crate) const IS_LAST_LEVEL: usize = LEVEL_BITS + 5;
pub(crate) const PATH_BIT: usize = IS_LAST_LEVEL + 1;
pub(crate) const INDEX: usize = PATH_BIT + 1;
pub(crate) const WORK: usize = INDEX + 1;
pub const NUM_WITHDRAWAL_COLS: usize = WORK + 16;
pub const NUM_CONSTRAINTS: usize = 1_186;
pub const ACTIVE_PERMUTATIONS: usize = 240;
pub const TRACE_HEIGHT: usize = 256;
pub const MAX_CONSTRAINT_DEGREE: usize = 7;
const _: () = assert!(NUM_POSEIDON_COLS == 157);
const _: () = assert!(NUM_WITHDRAWAL_COLS == 190);
const _: () = assert!(PUBLIC_VALUES_COUNT == 64);

/// Returns the identity column index for a Poseidon input.
///
/// # Panics
///
/// Panics when `index` is outside the 16-column permutation width.
#[must_use]
pub const fn poseidon_input(index: usize) -> usize {
    assert!(index < WIDTH);
    index
}
fn constants() -> RoundConstants<BabyBear, WIDTH, HALF, PARTIAL> {
    RoundConstants::new(
        BABYBEAR_POSEIDON2_RC_16_EXTERNAL_INITIAL,
        BABYBEAR_POSEIDON2_RC_16_INTERNAL,
        BABYBEAR_POSEIDON2_RC_16_EXTERNAL_FINAL,
    )
}

#[derive(Clone)]
pub struct WithdrawalAir {
    poseidon: InnerAir,
}
impl Default for WithdrawalAir {
    fn default() -> Self {
        Self {
            poseidon: Poseidon2Air::new(constants()),
        }
    }
}
impl BaseAir<BabyBear> for WithdrawalAir {
    fn width(&self) -> usize {
        NUM_WITHDRAWAL_COLS
    }
    fn num_public_values(&self) -> usize {
        PUBLIC_VALUES_COUNT
    }
    fn max_constraint_degree(&self) -> Option<usize> {
        Some(MAX_CONSTRAINT_DEGREE)
    }
}

impl<AB: AirBuilder<F = BabyBear>> Air<AB> for WithdrawalAir {
    fn eval(&self, builder: &mut AB) {
        {
            let mut sub =
                SubAirBuilder::<_, InnerAir, BabyBear>::new(builder, 0..NUM_POSEIDON_COLS);
            self.poseidon.eval(&mut sub);
        }
        let main = builder.main();
        let local = main.current_slice();
        let next = main.next_slice();
        let lp: &InnerCols<AB::Var> = local[..NUM_POSEIDON_COLS].borrow();
        let np: &InnerCols<AB::Var> = next[..NUM_POSEIDON_COLS].borrow();
        let output = &lp.ending_full_rounds[HALF - 1].post;
        let public = builder.public_values().to_vec();

        for &c in &[
            IS_NOTE,
            IS_NULLIFIER,
            IS_MERKLE,
            IS_PAYOUT,
            IS_PADDING,
            IS_LAST_LEVEL,
            PATH_BIT,
        ] {
            builder.assert_bool(local[c]);
        }
        for c in STEP_BITS..STEP_BITS + 4 {
            builder.assert_bool(local[c]);
        }
        for c in LEVEL_BITS..LEVEL_BITS + 5 {
            builder.assert_bool(local[c]);
        }
        builder.assert_eq(
            local[IS_NOTE]
                + local[IS_NULLIFIER]
                + local[IS_MERKLE]
                + local[IS_PAYOUT]
                + local[IS_PADDING],
            AB::Expr::ONE,
        );
        builder.assert_eq(
            local[IS_LAST_LEVEL],
            AB::Expr::from(local[IS_MERKLE]) * level_eq::<AB>(local, 19),
        );
        builder
            .when(AB::Expr::ONE - local[IS_MERKLE])
            .assert_zero(local[PATH_BIT]);
        builder
            .when(AB::Expr::ONE - local[IS_MERKLE])
            .assert_zero(local[INDEX]);

        let mut first = builder.when_first_row();
        first.assert_one(local[IS_NULLIFIER]);
        first.assert_zero(step_value::<AB>(local));
        first.assert_zero(level_value::<AB>(local));
        for i in 8..16 {
            first.assert_zero(local[WORK + i]);
        }
        builder
            .when(AB::Expr::ONE - local[IS_MERKLE])
            .assert_zero(level_value::<AB>(local));
        builder
            .when(local[IS_PADDING])
            .assert_zero(step_value::<AB>(local));
        let mut last = builder.when_last_row();
        last.assert_one(local[IS_PADDING]);

        initial_row(
            builder,
            local,
            lp,
            IS_NULLIFIER,
            domains::NULLIFIER,
            96,
            24,
            false,
        );
        initial_row(builder, local, lp, IS_NOTE, domains::NOTE, 128, 32, false);
        initial_row(
            builder,
            local,
            lp,
            IS_MERKLE,
            domains::APP_MERKLE_NODE,
            128,
            32,
            true,
        );

        for j in 0..RATE {
            builder
                .when(AB::Expr::from(local[IS_NULLIFIER]) * step_eq::<AB>(local, 0))
                .assert_eq(lp.inputs[j], public[j]);
            builder
                .when(AB::Expr::from(local[IS_NOTE]) * step_eq::<AB>(local, 0))
                .assert_eq(lp.inputs[j], public[j]);
            builder
                .when(
                    AB::Expr::from(local[IS_MERKLE])
                        * step_eq::<AB>(local, 0)
                        * (AB::Expr::ONE - local[PATH_BIT]),
                )
                .assert_eq(lp.inputs[j], local[WORK + j]);
        }
        for step in 0..4 {
            let c = AB::Expr::from(local[IS_PAYOUT]) * step_eq::<AB>(local, step);
            for j in 0..RATE {
                builder
                    .when(c.clone())
                    .assert_eq(lp.inputs[j], public[48 + step * RATE + j]);
            }
            for j in RATE..WIDTH {
                builder.when(c.clone()).assert_zero(lp.inputs[j]);
            }
        }
        for j in 0..WIDTH {
            builder.when(local[IS_PADDING]).assert_zero(lp.inputs[j]);
            builder
                .when(local[IS_PAYOUT] + local[IS_PADDING])
                .assert_zero(local[WORK + j]);
        }

        let tr = builder.is_transition();
        metadata(builder, local, next, tr.clone());
        chaining(builder, next, lp, np, &public, tr.clone());

        for i in 0..16 {
            builder
                .when(tr.clone() * local[IS_NULLIFIER])
                .assert_eq(next[WORK + i], local[WORK + i]);
        }
        for step in 0..11 {
            work_transition(
                builder,
                local,
                next,
                output,
                tr.clone() * local[IS_NOTE] * step_eq::<AB>(local, step),
                7,
                step,
            );
        }
        for step in 0..10 {
            work_transition(
                builder,
                local,
                next,
                output,
                tr.clone() * local[IS_MERKLE] * step_eq::<AB>(local, step),
                7,
                step,
            );
        }
        work_transition(
            builder,
            local,
            next,
            output,
            tr.clone()
                * local[IS_MERKLE]
                * step_eq::<AB>(local, 10)
                * (AB::Expr::ONE - local[IS_LAST_LEVEL]),
            7,
            10,
        );

        for chunk in 0..4 {
            let nc = AB::Expr::from(local[IS_NULLIFIER]) * step_eq::<AB>(local, 5 + chunk);
            let rc = AB::Expr::from(local[IS_MERKLE])
                * local[IS_LAST_LEVEL]
                * step_eq::<AB>(local, 7 + chunk);
            for j in 0..RATE {
                builder
                    .when(nc.clone())
                    .assert_eq(output[j], public[32 + chunk * RATE + j]);
                builder
                    .when(rc.clone())
                    .assert_eq(output[j], public[16 + chunk * RATE + j]);
            }
        }
    }
}

fn initial_row<AB: AirBuilder<F = BabyBear>>(
    b: &mut AB,
    r: &[AB::Var],
    p: &InnerCols<AB::Var>,
    selector: usize,
    tag: u8,
    bytes: u32,
    elements: u32,
    level: bool,
) {
    let c = AB::Expr::from(r[selector]) * step_eq::<AB>(r, 0);
    b.when(c.clone()).assert_eq(p.inputs[4], BabyBear::ONE);
    b.when(c.clone())
        .assert_eq(p.inputs[5], BabyBear::from_u8(tag));
    b.when(c.clone())
        .assert_eq(p.inputs[6], BabyBear::from_u32(bytes));
    b.when(c.clone())
        .assert_eq(p.inputs[7], BabyBear::from_u32(elements));
    if level {
        b.when(c.clone())
            .assert_eq(p.inputs[8], level_value::<AB>(r));
    } else {
        b.when(c.clone()).assert_zero(p.inputs[8]);
    }
    for i in 9..WIDTH {
        b.when(c.clone()).assert_zero(p.inputs[i]);
    }
}

fn metadata<AB: AirBuilder<F = BabyBear>>(b: &mut AB, l: &[AB::Var], n: &[AB::Var], tr: AB::Expr) {
    let s = step_value::<AB>(l);
    let ns = step_value::<AB>(n);
    let lev = level_value::<AB>(l);
    let nl = level_value::<AB>(n);

    let c = tr.clone() * l[IS_NULLIFIER] * (AB::Expr::ONE - step_eq::<AB>(l, 8));
    b.when(c.clone()).assert_one(n[IS_NULLIFIER]);
    b.when(c).assert_eq(ns.clone(), s.clone() + AB::Expr::ONE);
    let c = tr.clone() * l[IS_NULLIFIER] * step_eq::<AB>(l, 8);
    b.when(c.clone()).assert_one(n[IS_NOTE]);
    b.when(c).assert_zero(ns.clone());

    let c = tr.clone() * l[IS_NOTE] * (AB::Expr::ONE - step_eq::<AB>(l, 10));
    b.when(c.clone()).assert_one(n[IS_NOTE]);
    b.when(c).assert_eq(ns.clone(), s.clone() + AB::Expr::ONE);
    let c = tr.clone() * l[IS_NOTE] * step_eq::<AB>(l, 10);
    b.when(c.clone()).assert_one(n[IS_MERKLE]);
    b.when(c.clone()).assert_zero(ns.clone());
    b.when(c).assert_zero(nl.clone());

    let c = tr.clone() * l[IS_MERKLE] * (AB::Expr::ONE - step_eq::<AB>(l, 10));
    b.when(c.clone()).assert_one(n[IS_MERKLE]);
    b.when(c.clone()).assert_eq(ns.clone(), s + AB::Expr::ONE);
    b.when(c.clone()).assert_eq(nl.clone(), lev.clone());
    b.when(c.clone()).assert_eq(n[PATH_BIT], l[PATH_BIT]);
    b.when(c).assert_eq(n[INDEX], l[INDEX]);
    let c = tr.clone() * l[IS_MERKLE] * step_eq::<AB>(l, 10) * (AB::Expr::ONE - l[IS_LAST_LEVEL]);
    b.when(c.clone()).assert_one(n[IS_MERKLE]);
    b.when(c.clone()).assert_zero(ns.clone());
    b.when(c.clone()).assert_eq(nl, lev + AB::Expr::ONE);
    b.when(c)
        .assert_eq(l[INDEX], l[PATH_BIT] + AB::Expr::TWO * n[INDEX]);
    let c = tr.clone() * l[IS_MERKLE] * step_eq::<AB>(l, 10) * l[IS_LAST_LEVEL];
    b.when(c.clone()).assert_one(n[IS_PAYOUT]);
    b.when(c.clone()).assert_zero(ns.clone());
    b.when(c).assert_eq(l[INDEX], l[PATH_BIT]);

    let c = tr.clone() * l[IS_PAYOUT] * (AB::Expr::ONE - step_eq::<AB>(l, 3));
    b.when(c.clone()).assert_one(n[IS_PAYOUT]);
    b.when(c)
        .assert_eq(ns.clone(), step_value::<AB>(l) + AB::Expr::ONE);
    let c = tr.clone() * l[IS_PAYOUT] * step_eq::<AB>(l, 3);
    b.when(c.clone()).assert_one(n[IS_PADDING]);
    b.when(c).assert_zero(ns.clone());
    let c = tr * l[IS_PADDING];
    b.when(c.clone()).assert_one(n[IS_PADDING]);
    b.when(c).assert_zero(ns);
}

fn chaining<AB: AirBuilder<F = BabyBear>>(
    b: &mut AB,
    n: &[AB::Var],
    lp: &InnerCols<AB::Var>,
    np: &InnerCols<AB::Var>,
    public: &[AB::PublicVar],
    tr: AB::Expr,
) {
    let out = &lp.ending_full_rounds[HALF - 1].post;

    for step in 1..6 {
        let c = tr.clone() * n[IS_NULLIFIER] * step_eq::<AB>(n, step);
        for j in 0..RATE {
            let payload: AB::Expr = if step < 4 {
                public[step * RATE + j].into()
            } else {
                AB::Expr::from(n[WORK + (step - 4) * RATE + j])
            };
            b.when(c.clone())
                .assert_eq(np.inputs[j], AB::Expr::from(out[j]) + payload);
        }
        for j in RATE..WIDTH {
            b.when(c.clone()).assert_eq(np.inputs[j], out[j]);
        }
    }
    for step in 6..9 {
        squeeze(
            b,
            np,
            out,
            tr.clone() * n[IS_NULLIFIER] * step_eq::<AB>(n, step),
        );
    }

    for step in 1..8 {
        let c = tr.clone() * n[IS_NOTE] * step_eq::<AB>(n, step);
        // On steps 6 and 7 the four unconstrained rate deltas are exactly the
        // eight trapdoor limbs; all twelve capacity lanes are still chained below.
        for j in 0..RATE {
            if step < 4 {
                let payload: AB::Expr = public[step * RATE + j].into();
                b.when(c.clone())
                    .assert_eq(np.inputs[j], AB::Expr::from(out[j]) + payload);
            } else if step < 6 {
                b.when(c.clone())
                    .assert_eq(np.inputs[j], out[j] + n[WORK + (step - 4) * RATE + j]);
            }
        }
        for j in RATE..WIDTH {
            b.when(c.clone()).assert_eq(np.inputs[j], out[j]);
        }
    }
    for step in 8..11 {
        squeeze(b, np, out, tr.clone() * n[IS_NOTE] * step_eq::<AB>(n, step));
    }

    for step in 1..8 {
        let c = tr.clone() * n[IS_MERKLE] * step_eq::<AB>(n, step);
        for j in 0..RATE {
            let k = step * RATE + j;
            let cc = if k < 16 {
                c.clone() * (AB::Expr::ONE - n[PATH_BIT])
            } else {
                c.clone() * n[PATH_BIT]
            };
            b.when(cc)
                .assert_eq(np.inputs[j], AB::Expr::from(out[j]) + n[WORK + k % 16]);
        }
        for j in RATE..WIDTH {
            b.when(c.clone()).assert_eq(np.inputs[j], out[j]);
        }
    }
    for step in 8..11 {
        squeeze(
            b,
            np,
            out,
            tr.clone() * n[IS_MERKLE] * step_eq::<AB>(n, step),
        );
    }
}
fn squeeze<AB: AirBuilder<F = BabyBear>>(
    b: &mut AB,
    np: &InnerCols<AB::Var>,
    out: &[AB::Var; WIDTH],
    c: AB::Expr,
) {
    for j in 0..WIDTH {
        b.when(c.clone()).assert_eq(np.inputs[j], out[j]);
    }
}
fn work_transition<AB: AirBuilder<F = BabyBear>>(
    b: &mut AB,
    l: &[AB::Var],
    n: &[AB::Var],
    out: &[AB::Var; WIDTH],
    c: AB::Expr,
    first: usize,
    step: usize,
) {
    let chunk = step.checked_sub(first).filter(|&x| x < 4);
    for i in 0..16 {
        if chunk == Some(i / RATE) {
            b.when(c.clone()).assert_eq(n[WORK + i], out[i % RATE]);
        } else {
            b.when(c.clone()).assert_eq(n[WORK + i], l[WORK + i]);
        }
    }
}
fn step_eq<AB: AirBuilder>(r: &[AB::Var], v: usize) -> AB::Expr {
    bits_eq::<AB>(&r[STEP_BITS..STEP_BITS + 4], v)
}
fn level_eq<AB: AirBuilder>(r: &[AB::Var], v: usize) -> AB::Expr {
    bits_eq::<AB>(&r[LEVEL_BITS..LEVEL_BITS + 5], v)
}
fn bits_eq<AB: AirBuilder>(bits: &[AB::Var], v: usize) -> AB::Expr {
    bits.iter().enumerate().fold(AB::Expr::ONE, |p, (i, x)| {
        p * if (v >> i) & 1 == 1 {
            AB::Expr::from(*x)
        } else {
            AB::Expr::ONE - *x
        }
    })
}
fn step_value<AB: AirBuilder>(r: &[AB::Var]) -> AB::Expr {
    bit_value::<AB>(&r[STEP_BITS..STEP_BITS + 4])
}
fn level_value<AB: AirBuilder>(r: &[AB::Var]) -> AB::Expr {
    bit_value::<AB>(&r[LEVEL_BITS..LEVEL_BITS + 5])
}
fn bit_value<AB: AirBuilder>(bits: &[AB::Var]) -> AB::Expr {
    bits.iter().enumerate().fold(AB::Expr::ZERO, |s, (i, x)| {
        s + AB::Expr::from_usize(1 << i) * *x
    })
}

#[derive(Clone, Copy)]
enum Kind {
    Note,
    Nullifier,
    Merkle,
}
#[derive(Clone)]
struct ControllerRow {
    kind: Kind,
    step: usize,
    level: usize,
    path_bit: u8,
    index: u32,
    work: [BabyBear; 16],
}

#[allow(clippy::too_many_arguments)]
fn append_hash(
    inputs: &mut Vec<[BabyBear; WIDTH]>,
    rows: &mut Vec<ControllerRow>,
    perm: &impl Permutation<[BabyBear; WIDTH]>,
    kind: Kind,
    tag: u8,
    bytes: u32,
    aux: u32,
    payload: &[BabyBear],
    level: usize,
    path_bit: u8,
    index: u32,
    work: &mut [BabyBear; 16],
    update_work: bool,
) {
    debug_assert_eq!(payload.len() % RATE, 0);
    let absorb = payload.len() / RATE;
    let mut state = [BabyBear::ZERO; WIDTH];
    state[4] = BabyBear::ONE;
    state[5] = BabyBear::from_u8(tag);
    state[6] = BabyBear::from_u32(bytes);
    state[7] = BabyBear::from_usize(payload.len());
    state[8] = BabyBear::from_u32(aux);
    for step in 0..absorb {
        for j in 0..RATE {
            state[j] += payload[step * RATE + j];
        }
        inputs.push(state);
        rows.push(ControllerRow {
            kind,
            step,
            level,
            path_bit,
            index,
            work: *work,
        });
        perm.permute_mut(&mut state);
        if update_work && step + 1 == absorb {
            work[..RATE].copy_from_slice(&state[..RATE]);
        }
    }
    for squeeze in 1..4 {
        let step = absorb + squeeze - 1;
        inputs.push(state);
        rows.push(ControllerRow {
            kind,
            step,
            level,
            path_bit,
            index,
            work: *work,
        });
        perm.permute_mut(&mut state);
        if update_work {
            work[squeeze * RATE..(squeeze + 1) * RATE].copy_from_slice(&state[..RATE]);
        }
    }
}

/// Generates the canonical withdrawal execution trace.
///
/// # Errors
///
/// Returns [`RelationError`] when the witness does not satisfy the withdrawal
/// relation or contains a noncanonical digest.
///
/// # Panics
///
/// Panics only if fixed protocol dimensions are internally inconsistent.
pub fn generate_withdrawal_trace(
    statement: WithdrawalStatement,
    witness: &WithdrawalWitness,
) -> Result<RowMajorMatrix<BabyBear>, RelationError> {
    check_witness(statement, witness)?;
    let perm = default_babybear_poseidon2_16();
    let scope = digest_to_elements(statement.scope).expect("checked scope");
    let secret = (*witness.nullifier_secret.limbs()).map(BabyBear::from_u32);
    let trapdoor = (*witness.trapdoor.limbs()).map(BabyBear::from_u32);
    let mut inputs = Vec::with_capacity(TRACE_HEIGHT);
    let mut rows = Vec::with_capacity(ACTIVE_PERMUTATIONS);
    let mut work = [BabyBear::ZERO; 16];
    work[..8].copy_from_slice(&secret);
    let mut payload = Vec::with_capacity(32);

    payload.extend_from_slice(&scope);
    payload.extend_from_slice(&secret);
    append_hash(
        &mut inputs,
        &mut rows,
        &perm,
        Kind::Nullifier,
        domains::NULLIFIER,
        96,
        0,
        &payload,
        0,
        0,
        0,
        &mut work,
        false,
    );

    payload.clear();
    payload.extend_from_slice(&scope);
    payload.extend_from_slice(&secret);
    payload.extend_from_slice(&trapdoor);
    append_hash(
        &mut inputs,
        &mut rows,
        &perm,
        Kind::Note,
        domains::NOTE,
        128,
        0,
        &payload,
        0,
        0,
        0,
        &mut work,
        true,
    );

    let mut remaining = witness.leaf_index;
    for level in 0..20 {
        let sibling = digest_to_elements(witness.siblings[level]).expect("checked sibling");
        let bit = witness.path_bits[level];
        payload.clear();
        if bit == 0 {
            payload.extend_from_slice(&work);
            payload.extend_from_slice(&sibling);
        } else {
            payload.extend_from_slice(&sibling);
            payload.extend_from_slice(&work);
        }
        append_hash(
            &mut inputs,
            &mut rows,
            &perm,
            Kind::Merkle,
            domains::APP_MERKLE_NODE,
            128,
            u32::try_from(level).map_err(|_| RelationError::LeafIndexOutOfRange)?,
            &payload,
            level,
            bit,
            remaining,
            &mut work,
            true,
        );
        remaining >>= 1;
    }
    assert_eq!(inputs.len(), ACTIVE_PERMUTATIONS);
    assert_eq!(rows.len(), ACTIVE_PERMUTATIONS);
    let pv = public_values(statement);
    for step in 0..4 {
        let mut input = [BabyBear::ZERO; WIDTH];
        input[..RATE].copy_from_slice(&pv[48 + step * RATE..48 + (step + 1) * RATE]);
        inputs.push(input);
    }
    inputs.resize(TRACE_HEIGHT, [BabyBear::ZERO; WIDTH]);
    let pt = generate_trace_rows::<
        BabyBear,
        GenericPoseidon2LinearLayersBabyBear,
        WIDTH,
        BABYBEAR_S_BOX_DEGREE,
        REGS,
        HALF,
        PARTIAL,
    >(inputs, &constants(), 0);
    let mut trace = RowMajorMatrix::new(
        BabyBear::zero_vec(TRACE_HEIGHT * NUM_WITHDRAWAL_COLS),
        NUM_WITHDRAWAL_COLS,
    );
    for ri in 0..TRACE_HEIGHT {
        let source = pt.row_slice(ri).expect("row");
        let row = &mut trace.values[ri * NUM_WITHDRAWAL_COLS..(ri + 1) * NUM_WITHDRAWAL_COLS];
        row[..NUM_POSEIDON_COLS].copy_from_slice(&source);
        if ri < ACTIVE_PERMUTATIONS {
            write_controller(row, &rows[ri]);
        } else if ri < ACTIVE_PERMUTATIONS + 4 {
            row[IS_PAYOUT] = BabyBear::ONE;
            write_bits(row, STEP_BITS, ri - ACTIVE_PERMUTATIONS, 4);
        } else {
            row[IS_PADDING] = BabyBear::ONE;
        }
    }
    Ok(trace)
}

fn write_controller(row: &mut [BabyBear], s: &ControllerRow) {
    row[match s.kind {
        Kind::Note => IS_NOTE,
        Kind::Nullifier => IS_NULLIFIER,
        Kind::Merkle => IS_MERKLE,
    }] = BabyBear::ONE;
    write_bits(row, STEP_BITS, s.step, 4);
    write_bits(row, LEVEL_BITS, s.level, 5);
    row[IS_LAST_LEVEL] = BabyBear::from_bool(matches!(s.kind, Kind::Merkle) && s.level == 19);
    row[PATH_BIT] = BabyBear::from_u8(s.path_bit);
    row[INDEX] = BabyBear::from_u32(s.index);
    row[WORK..WORK + 16].copy_from_slice(&s.work);
}
fn write_bits(row: &mut [BabyBear], start: usize, value: usize, bits: usize) {
    for bit in 0..bits {
        row[start + bit] = BabyBear::from_bool((value >> bit) & 1 == 1);
    }
}
#[must_use]
pub fn evaluate_constraints(
    trace: &RowMajorMatrix<BabyBear>,
    public: &[BabyBear],
    max_failures: Option<usize>,
) -> ConstraintReport {
    check_all_constraints(&WithdrawalAir::default(), trace, public, max_failures)
}
```

</details>

## `crates/pqtc-poseidon-air/src/lib.rs`

- Bytes: 14,715
- SHA-256: `5a25c94d811f4e6004634af887baa5f4c8b53ead18a33db4e0a8868a45811c26`

<details><summary>Complete file</summary>

```rust
//! Plain-reference P2BB512-v1 withdrawal relation.

pub mod air;

pub use air::{
    ACTIVE_PERMUTATIONS, MAX_CONSTRAINT_DEGREE, NUM_CONSTRAINTS, NUM_POSEIDON_COLS,
    NUM_WITHDRAWAL_COLS, TRACE_HEIGHT, WithdrawalAir, evaluate_constraints,
    generate_withdrawal_trace,
};

use p3_baby_bear::BabyBear;
use p3_field::PrimeCharacteristicRing;
use pqtc_hash::{commitment, digest_to_elements, nullifier_hash};
use pqtc_spec::{CanonicalSecret, Digest512, TREE_DEPTH, WithdrawalStatement};
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Private data for the fixed-depth withdrawal relation.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct WithdrawalWitness {
    pub nullifier_secret: CanonicalSecret,
    pub trapdoor: CanonicalSecret,
    pub leaf_index: u32,
    pub path_bits: [u8; TREE_DEPTH as usize],
    pub siblings: [Digest512; TREE_DEPTH as usize],
}

impl WithdrawalWitness {
    #[must_use]
    pub fn commitment(&self, scope: Digest512) -> Digest512 {
        commitment(scope, self.nullifier_secret, self.trapdoor)
    }
}

/// Checks the non-polynomial input preconditions and the plain withdrawal relation.
///
/// # Errors
///
/// Returns [`RelationError`] when the statement or witness is noncanonical or
/// does not satisfy the withdrawal relation.
pub fn check_witness(
    statement: WithdrawalStatement,
    witness: &WithdrawalWitness,
) -> Result<(), RelationError> {
    for (name, digest) in [
        ("scope", statement.scope),
        ("root", statement.root),
        ("nullifier", statement.nullifier_hash),
        ("payout", statement.payout_digest),
    ] {
        if digest_to_elements(digest).is_none() {
            return Err(RelationError::NonCanonicalDigest(name));
        }
    }
    if witness.leaf_index >= 1 << TREE_DEPTH {
        return Err(RelationError::LeafIndexOutOfRange);
    }
    for (level, (&bit, sibling)) in witness.path_bits.iter().zip(&witness.siblings).enumerate() {
        if bit > 1 {
            return Err(RelationError::NonBooleanPathBit { level, value: bit });
        }
        if bit != ((witness.leaf_index >> level) & 1) as u8 {
            return Err(RelationError::PathIndexMismatch { level });
        }
        if digest_to_elements(*sibling).is_none() {
            return Err(RelationError::NonCanonicalSibling { level });
        }
    }
    if nullifier_hash(statement.scope, witness.nullifier_secret) != statement.nullifier_hash {
        return Err(RelationError::NullifierMismatch);
    }
    let mut current = witness.commitment(statement.scope);
    for (level, (&bit, sibling)) in witness.path_bits.iter().zip(&witness.siblings).enumerate() {
        let level = u8::try_from(level).map_err(|_| RelationError::LeafIndexOutOfRange)?;
        current = if bit == 0 {
            pqtc_hash::merkle_node(level, current, *sibling)
        } else {
            pqtc_hash::merkle_node(level, *sibling, current)
        };
    }
    if current != statement.root {
        return Err(RelationError::RootMismatch);
    }
    Ok(())
}

/// Converts the four statement digests to the AIR's 64 public `BabyBear` values.
///
/// # Panics
///
/// Panics when a statement digest contains a noncanonical field element.
pub fn public_values(statement: WithdrawalStatement) -> [BabyBear; 64] {
    let mut values = [BabyBear::ZERO; 64];
    for (chunk, digest) in values.chunks_exact_mut(16).zip([
        statement.scope,
        statement.root,
        statement.nullifier_hash,
        statement.payout_digest,
    ]) {
        chunk.copy_from_slice(
            &digest_to_elements(digest)
                .expect("withdrawal statement contains a non-canonical digest"),
        );
    }
    values
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum RelationError {
    #[error("{0} digest contains a non-canonical BabyBear element")]
    NonCanonicalDigest(&'static str),
    #[error("Merkle sibling at level {level} contains a non-canonical BabyBear element")]
    NonCanonicalSibling { level: usize },
    #[error("leaf index is not a 20-bit value")]
    LeafIndexOutOfRange,
    #[error("path bit {level} has non-boolean value {value}")]
    NonBooleanPathBit { level: usize, value: u8 },
    #[error("path bit {level} does not equal the leaf-index bit")]
    PathIndexMismatch { level: usize },
    #[error("computed nullifier does not equal the public nullifier")]
    NullifierMismatch,
    #[error("computed Merkle root does not equal the public root")]
    RootMismatch,
}

#[cfg(test)]
mod tests {
    use p3_air::{
        BaseAir,
        symbolic::{AirLayout, get_max_constraint_degree, get_symbolic_constraints},
    };
    use p3_field::PrimeCharacteristicRing;
    use p3_matrix::Matrix;
    use pqtc_hash::{commitment, nullifier_hash, payout_digest};
    use pqtc_merkle::MerkleTree;

    use super::*;
    use crate::air::{
        INDEX, IS_MERKLE, IS_NOTE, IS_NULLIFIER, IS_PADDING, IS_PAYOUT, LEVEL_BITS, PATH_BIT,
        STEP_BITS, WORK, poseidon_input,
    };

    fn fixture() -> (WithdrawalStatement, WithdrawalWitness) {
        let scope = pqtc_hash::p2bb512(pqtc_spec::domains::SCOPE, 0, 0, &[]);
        let secret = CanonicalSecret::from_bytes([3; 32]).unwrap();
        let trapdoor = CanonicalSecret::from_bytes([4; 32]).unwrap();
        let leaf = commitment(scope, secret, trapdoor);
        let mut tree = MerkleTree::new(scope);
        let (leaf_index, root) = tree.insert(leaf).unwrap();
        let path = tree.path(leaf_index).unwrap();
        (
            WithdrawalStatement {
                scope,
                root,
                nullifier_hash: nullifier_hash(scope, secret),
                payout_digest: payout_digest([5; 20], [6; 20], [0; 32]),
            },
            WithdrawalWitness {
                nullifier_secret: secret,
                trapdoor,
                leaf_index,
                path_bits: path.path_bits(),
                siblings: path.siblings,
            },
        )
    }

    fn statement_for_witness(
        scope: Digest512,
        payout_digest: Digest512,
        witness: &WithdrawalWitness,
    ) -> WithdrawalStatement {
        let mut root = witness.commitment(scope);
        for (level, (&bit, sibling)) in witness.path_bits.iter().zip(&witness.siblings).enumerate()
        {
            root = if bit == 0 {
                pqtc_hash::merkle_node(level as u8, root, *sibling)
            } else {
                pqtc_hash::merkle_node(level as u8, *sibling, root)
            };
        }
        WithdrawalStatement {
            scope,
            root,
            nullifier_hash: nullifier_hash(scope, witness.nullifier_secret),
            payout_digest,
        }
    }

    fn rejected(trace: &p3_matrix::dense::RowMajorMatrix<BabyBear>, public: &[BabyBear]) -> bool {
        !evaluate_constraints(trace, public, Some(1)).is_ok()
    }

    #[test]
    fn valid_witness_has_fixed_secure_shape() {
        let (statement, witness) = fixture();
        let trace = generate_withdrawal_trace(statement, &witness).unwrap();
        assert_eq!(trace.height(), TRACE_HEIGHT);
        assert_eq!(trace.width(), NUM_WITHDRAWAL_COLS);
        assert_eq!(WithdrawalAir::default().width(), NUM_WITHDRAWAL_COLS);
        assert_eq!(NUM_WITHDRAWAL_COLS, 190);
        assert_eq!(ACTIVE_PERMUTATIONS, 240);
        assert_eq!(NUM_CONSTRAINTS, 1_186);
        assert_eq!(MAX_CONSTRAINT_DEGREE, 7);
        assert!(evaluate_constraints(&trace, &public_values(statement), None).is_ok());
    }
    #[test]
    fn row_schedule_and_commitment_overwrite_are_exact() {
        let (statement, witness) = fixture();
        let trace = generate_withdrawal_trace(statement, &witness).unwrap();
        let row = |index: usize| trace.row_slice(index).unwrap();
        for (index, selector) in [
            (0, IS_NULLIFIER),
            (8, IS_NULLIFIER),
            (9, IS_NOTE),
            (19, IS_NOTE),
            (20, IS_MERKLE),
            (239, IS_MERKLE),
            (240, IS_PAYOUT),
            (243, IS_PAYOUT),
            (244, IS_PADDING),
            (255, IS_PADDING),
        ] {
            assert_eq!(
                row(index)[selector],
                BabyBear::ONE,
                "wrong selector on row {index}"
            );
        }
        let secret = (*witness.nullifier_secret.limbs()).map(BabyBear::from_u32);
        for index in 0..=16 {
            assert_eq!(&row(index)[WORK..WORK + 8], &secret);
            assert_eq!(&row(index)[WORK + 8..WORK + 16], &[BabyBear::ZERO; 8]);
        }
        for chunk in 0..4 {
            let destination_row = 17 + chunk;
            assert_eq!(
                &row(destination_row)[WORK + chunk * 4..WORK + (chunk + 1) * 4],
                &row(destination_row - 1)[141..145],
                "commitment chunk {chunk} was not assembled"
            );
        }
        for index in 240..TRACE_HEIGHT {
            assert_eq!(&row(index)[WORK..WORK + 16], &[BabyBear::ZERO; 16]);
        }
    }

    #[test]
    fn symbolic_report_matches_declared_shape() {
        let air = WithdrawalAir::default();
        let layout = AirLayout::from_air::<BabyBear>(&air);
        assert_eq!(
            get_symbolic_constraints::<BabyBear, _>(&air, layout).len(),
            NUM_CONSTRAINTS
        );
        assert_eq!(
            get_max_constraint_degree::<BabyBear, _>(&air, layout, TRACE_HEIGHT),
            MAX_CONSTRAINT_DEGREE
        );
    }

    #[test]
    fn every_private_limb_and_work_column_is_constrained() {
        let (statement, witness) = fixture();
        let baseline = generate_withdrawal_trace(statement, &witness).unwrap();
        let public = public_values(statement);

        for limb in 0..8 {
            for (row, name) in [
                (4 + limb / 4, "nullifier secret"),
                (13 + limb / 4, "note secret"),
            ] {
                let mut trace = baseline.clone();
                trace.values[row * NUM_WITHDRAWAL_COLS + poseidon_input(limb % 4)] += BabyBear::ONE;
                assert!(rejected(&trace, &public), "{name} limb {limb} was free");
            }
            let mut trace = baseline.clone();
            trace.values[(15 + limb / 4) * NUM_WITHDRAWAL_COLS + poseidon_input(limb % 4)] +=
                BabyBear::ONE;
            assert!(rejected(&trace, &public), "trapdoor limb {limb} was free");
        }

        for column in 0..16 {
            for row in [0, 8, 9, 19, 20] {
                let mut trace = baseline.clone();
                trace.values[row * NUM_WITHDRAWAL_COLS + WORK + column] += BabyBear::ONE;
                assert!(
                    rejected(&trace, &public),
                    "WORK[{column}] was free on row {row}"
                );
            }
        }
    }

    #[test]
    fn every_secret_limb_is_used_by_both_private_hashes() {
        let (original, witness) = fixture();
        for limb in 0..CanonicalSecret::LIMB_COUNT {
            let mut changed = witness.clone();
            let mut limbs = changed.nullifier_secret.into_limbs();
            limbs[limb] += 1;
            changed.nullifier_secret = CanonicalSecret::from_limbs(limbs).unwrap();
            let changed_statement =
                statement_for_witness(original.scope, original.payout_digest, &changed);
            let trace = generate_withdrawal_trace(changed_statement, &changed).unwrap();

            let mut old_nullifier = changed_statement;
            old_nullifier.nullifier_hash = original.nullifier_hash;
            assert!(
                rejected(&trace, &public_values(old_nullifier)),
                "secret limb {limb} was absent from the nullifier hash"
            );
            let mut old_commitment = changed_statement;
            old_commitment.root = original.root;
            assert!(
                rejected(&trace, &public_values(old_commitment)),
                "secret limb {limb} was absent from the note commitment"
            );
        }
    }

    #[test]
    fn every_trapdoor_delta_changes_the_note_commitment() {
        let (original, witness) = fixture();
        for limb in 0..CanonicalSecret::LIMB_COUNT {
            let mut changed = witness.clone();
            let mut limbs = changed.trapdoor.into_limbs();
            limbs[limb] += 1;
            changed.trapdoor = CanonicalSecret::from_limbs(limbs).unwrap();
            let changed_statement =
                statement_for_witness(original.scope, original.payout_digest, &changed);
            let trace = generate_withdrawal_trace(changed_statement, &changed).unwrap();
            assert!(
                rejected(&trace, &public_values(original)),
                "trapdoor limb {limb} did not affect the note commitment"
            );
        }
    }

    #[test]
    fn operation_and_merkle_boundaries_are_constrained() {
        let (statement, witness) = fixture();
        let baseline = generate_withdrawal_trace(statement, &witness).unwrap();
        let public = public_values(statement);
        let mut boundaries = vec![
            (8, "nullifier/note"),
            (19, "note/merkle"),
            (239, "merkle/payout"),
            (243, "payout/padding"),
        ];
        boundaries.extend((0..19).map(|level| (20 + level * 11 + 10, "Merkle level")));
        for (row, name) in boundaries {
            let mut trace = baseline.clone();
            trace.values[(row + 1) * NUM_WITHDRAWAL_COLS + STEP_BITS] += BabyBear::ONE;
            assert!(
                rejected(&trace, &public),
                "{name} boundary after row {row} was free"
            );
        }
        for (row, column, name) in [
            (9, LEVEL_BITS, "note level"),
            (20, PATH_BIT, "path bit"),
            (20, LEVEL_BITS, "level"),
            (20, INDEX, "leaf index"),
            (21, poseidon_input(0), "sibling"),
            (244, poseidon_input(0), "padding"),
            (244, LEVEL_BITS, "padding level"),
            (244, WORK, "padding work"),
        ] {
            let mut trace = baseline.clone();
            trace.values[row * NUM_WITHDRAWAL_COLS + column] += BabyBear::ONE;
            assert!(rejected(&trace, &public), "mutation was accepted: {name}");
        }
    }

    #[test]
    fn every_public_field_is_bound() {
        let (statement, witness) = fixture();
        let trace = generate_withdrawal_trace(statement, &witness).unwrap();
        let public = public_values(statement);
        for index in 0..64 {
            let mut mutated = public;
            mutated[index] += BabyBear::ONE;
            assert!(
                rejected(&trace, &mutated),
                "public field {index} was not bound"
            );
        }
    }
}
```

</details>

## `crates/pqtc-security/Cargo.toml`

- Bytes: 499
- SHA-256: `ccd74b00cf0342facf98c04aca8a4fd5f8b87d063316f6435ebcfcce092d22dd`

<details><summary>Complete file</summary>

```toml
[package]
name = "pqtc-security"
version.workspace = true
edition.workspace = true
license.workspace = true
rust-version.workspace = true

[dependencies]
p3-air.workspace = true
p3-baby-bear.workspace = true
p3-field.workspace = true
p3-security.workspace = true
p3-uni-stark.workspace = true
pqtc-poseidon-air = { path = "../pqtc-poseidon-air" }
pqtc-hash = { path = "../pqtc-hash" }
pqtc-spec = { path = "../pqtc-spec" }
serde.workspace = true
thiserror.workspace = true

[lints]
workspace = true
```

</details>

## `crates/pqtc-security/src/lib.rs`

- Bytes: 13,741
- SHA-256: `53e97ad9b4da7a472393f681ae86e1ec1a370efd805812d626424df9f2b41df7`

<details><summary>Complete file</summary>

```rust
//! Canonical parameter manifests and conservative security accounting.

use p3_air::symbolic::AirLayout;
use p3_baby_bear::BabyBear;
use p3_field::extension::BinomialExtensionField;
use p3_security::fri::FriRegime;
use p3_uni_stark::{ConjecturedSecurity, ProvenSecurity, StarkSecurityParams};
use pqtc_hash::{keccak256, parameter_id};
use pqtc_poseidon_air::{NUM_WITHDRAWAL_COLS, TRACE_HEIGHT, WithdrawalAir};
use pqtc_spec::{Digest512, PLONKY3_COMMIT, PROTOCOL_VERSION, TREE_DEPTH};
use serde::{Deserialize, Serialize};
use thiserror::Error;

pub const MANIFEST_MAGIC: [u8; 8] = *b"PQTCPRM3";
pub const MANIFEST_VERSION: u16 = 3;

pub const CHALLENGE_FIELD_BITS: usize = 120;
pub const QUANTUM_ADJUSTED_MMCS_BITS: usize = 128;
pub const BATCHED_FUNCTIONS: usize = NUM_WITHDRAWAL_COLS + 16 + 4;
pub const PROOF_DEGREE_BITS: usize = 9;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct SecurityAnalysis {
    pub conjectured_bits: usize,
    pub proven_unique_decoding_bits: usize,
    pub proven_list_decoding_bits: usize,
    pub proven_bits: usize,
    pub challenge_field_bits: usize,
    pub quantum_adjusted_mmcs_bits: usize,
    pub batched_functions: usize,
    pub air_constraints: usize,
    pub air_max_constraint_degree: usize,
}

#[must_use]
pub fn analyze_profile(name: &str) -> SecurityAnalysis {
    analyze_manifest(&ParameterManifest::profile(name))
}

#[must_use]
pub fn analyze_manifest(manifest: &ParameterManifest) -> SecurityAnalysis {
    let fri = FriRegime {
        log_blowup: usize::from(manifest.fri_log_blowup),
        num_queries: usize::from(manifest.fri_query_count),
        log_final_poly_len: 0,
        max_log_arity: usize::from(manifest.fri_max_log_arity),
        commit_pow_bits: usize::from(manifest.commit_grinding_bits) / 2,
        query_pow_bits: usize::from(manifest.query_grinding_bits) / 2,
    };
    let air = WithdrawalAir::default();
    let mut parameters =
        StarkSecurityParams::from_air::<BabyBear, BinomialExtensionField<BabyBear, 4>, _>(
            fri,
            &air,
            AirLayout::from_air::<BabyBear>(&air),
            CHALLENGE_FIELD_BITS,
            QUANTUM_ADJUSTED_MMCS_BITS,
            2,
        );
    parameters.num_batched_functions = BATCHED_FUNCTIONS;
    let air_constraints = parameters.num_constraints;
    let air_max_constraint_degree = parameters.air_max_constraint_degree;
    let conjectured = ConjecturedSecurity::compute_from_params(&parameters, PROOF_DEGREE_BITS);
    let proven = ProvenSecurity::compute_from_proof(PROOF_DEGREE_BITS, &parameters);
    SecurityAnalysis {
        conjectured_bits: conjectured.security_bits,
        proven_unique_decoding_bits: proven.unique_decoding_bits,
        proven_list_decoding_bits: proven.list_decoding_bits,
        proven_bits: proven.security_bits(),
        challenge_field_bits: CHALLENGE_FIELD_BITS,
        quantum_adjusted_mmcs_bits: QUANTUM_ADJUSTED_MMCS_BITS,
        batched_functions: BATCHED_FUNCTIONS,
        air_constraints,
        air_max_constraint_degree,
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ParameterManifest {
    pub profile: String,
    pub plonky3_commit: String,
    pub rust_toolchain: String,
    pub field: String,
    pub extension_degree: u8,
    pub air_version: u16,
    pub air_source_hash: [u8; 32],
    pub tree_depth: u8,
    pub protocol_version: u32,
    pub trace_height: u32,
    pub fri_log_blowup: u8,
    pub fri_max_log_arity: u8,
    pub fri_query_count: u16,
    pub fri_final_polynomial_bound: u32,
    pub commit_grinding_bits: u8,
    pub query_grinding_bits: u8,
    pub random_codeword_count: u8,
    pub mmcs_salt_elements: u8,
    pub proof_codec_version: u16,
    pub verifier_interface_version: u16,
    pub expected_runtime_code_hashes: Vec<[u8; 32]>,
}

fn air_source_hash() -> [u8; 32] {
    let mut component_hashes = [0u8; 64];
    component_hashes[..32].copy_from_slice(&keccak256(include_bytes!(
        "../../pqtc-poseidon-air/src/lib.rs"
    )));
    component_hashes[32..].copy_from_slice(&keccak256(include_bytes!(
        "../../pqtc-poseidon-air/src/air.rs"
    )));
    keccak256(&component_hashes)
}

impl ParameterManifest {
    #[must_use]
    pub fn profile(name: &str) -> Self {
        let (blowup, queries, commit_pow, query_pow, random) = match name {
            "dev" => (3, 2, 0, 0, 2),
            "ci" => (3, 16, 4, 4, 4),
            "sepolia-v0.3" => (4, 32, 16, 16, 4),
            _ => panic!("unknown parameter profile"),
        };
        Self {
            profile: name.to_owned(),
            plonky3_commit: PLONKY3_COMMIT.to_owned(),
            rust_toolchain: "1.97.0".to_owned(),
            field: "BabyBear(2013265921)".to_owned(),
            extension_degree: 4,
            air_source_hash: air_source_hash(),
            air_version: 3,
            tree_depth: TREE_DEPTH,
            protocol_version: PROTOCOL_VERSION,
            trace_height: TRACE_HEIGHT as u32,
            fri_log_blowup: blowup,
            fri_max_log_arity: 1,
            fri_query_count: queries,
            fri_final_polynomial_bound: 1,
            commit_grinding_bits: commit_pow,
            query_grinding_bits: query_pow,
            random_codeword_count: random,
            mmcs_salt_elements: 8,
            proof_codec_version: 3,
            verifier_interface_version: 3,
            expected_runtime_code_hashes: Vec::new(),
        }
    }

    pub fn validate(&self) -> Result<(), ManifestError> {
        let expected_profile = match self.profile.as_str() {
            "dev" => (3, 2, 0, 0, 2),
            "ci" => (3, 16, 4, 4, 4),
            "sepolia-v0.3" => (4, 32, 16, 16, 4),
            _ => return Err(ManifestError::Profile),
        };
        if self.plonky3_commit != PLONKY3_COMMIT {
            return Err(ManifestError::Plonky3Commit);
        }
        if self.air_source_hash != air_source_hash() {
            return Err(ManifestError::AirSourceHash);
        }
        if self.air_version != 3
            || self.tree_depth != TREE_DEPTH
            || self.protocol_version != PROTOCOL_VERSION
            || self.proof_codec_version != 3
            || self.verifier_interface_version != 3
        {
            return Err(ManifestError::Protocol);
        }
        if self.trace_height != TRACE_HEIGHT as u32 {
            return Err(ManifestError::TraceHeight);
        }
        if self.field != "BabyBear(2013265921)" || self.extension_degree != 4 {
            return Err(ManifestError::Parameters);
        }
        if self.mmcs_salt_elements != 8 || self.random_codeword_count != expected_profile.4 {
            return Err(ManifestError::Hiding);
        }
        if self.fri_max_log_arity != 1
            || self.fri_final_polynomial_bound != 1
            || self.fri_query_count == 0
        {
            return Err(ManifestError::Parameters);
        }
        if self.profile == "sepolia-v0.3" && analyze_manifest(self).conjectured_bits < 100 {
            return Err(ManifestError::Security);
        }
        if (
            self.fri_log_blowup,
            self.fri_query_count,
            self.commit_grinding_bits,
            self.query_grinding_bits,
            self.random_codeword_count,
        ) != expected_profile
        {
            return Err(ManifestError::Parameters);
        }
        Ok(())
    }

    /// Conservative proven-security floor from Plonky3's round-by-round bound.
    #[must_use]
    pub fn conservative_quantum_bits(&self) -> u16 {
        analyze_manifest(self)
            .proven_bits
            .try_into()
            .unwrap_or(u16::MAX)
    }

    /// Deployment target under Plonky3's documented random-words conjecture.
    #[must_use]
    pub fn target_quantum_bits(&self) -> u16 {
        analyze_manifest(self)
            .conjectured_bits
            .try_into()
            .unwrap_or(u16::MAX)
    }

    pub fn encode_binary(&self) -> Result<Vec<u8>, ManifestError> {
        self.validate()?;
        let mut out = Vec::new();
        out.extend_from_slice(&MANIFEST_MAGIC);
        put_u16(&mut out, MANIFEST_VERSION);
        put_string(&mut out, &self.profile)?;
        put_string(&mut out, &self.plonky3_commit)?;
        put_string(&mut out, &self.rust_toolchain)?;
        put_string(&mut out, &self.field)?;
        out.push(self.extension_degree);
        put_u16(&mut out, self.air_version);
        out.extend_from_slice(&self.air_source_hash);
        out.push(self.tree_depth);
        out.extend_from_slice(&self.protocol_version.to_be_bytes());
        out.extend_from_slice(&self.trace_height.to_be_bytes());
        out.push(self.fri_log_blowup);
        out.push(self.fri_max_log_arity);
        put_u16(&mut out, self.fri_query_count);
        out.extend_from_slice(&self.fri_final_polynomial_bound.to_be_bytes());
        out.push(self.commit_grinding_bits);
        out.push(self.query_grinding_bits);
        out.push(self.random_codeword_count);
        out.push(self.mmcs_salt_elements);
        put_u16(&mut out, self.proof_codec_version);
        put_u16(&mut out, self.verifier_interface_version);
        put_u16(
            &mut out,
            self.expected_runtime_code_hashes
                .len()
                .try_into()
                .map_err(|_| ManifestError::Length)?,
        );
        for hash in &self.expected_runtime_code_hashes {
            out.extend_from_slice(hash);
        }
        Ok(out)
    }

    pub fn id(&self) -> Result<Digest512, ManifestError> {
        Ok(parameter_id(&self.encode_binary()?))
    }
}

fn put_u16(out: &mut Vec<u8>, value: u16) {
    out.extend_from_slice(&value.to_be_bytes());
}
fn put_string(out: &mut Vec<u8>, value: &str) -> Result<(), ManifestError> {
    put_u16(
        out,
        value.len().try_into().map_err(|_| ManifestError::Length)?,
    );
    out.extend_from_slice(value.as_bytes());
    Ok(())
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum ManifestError {
    #[error("unknown profile")]
    Profile,
    #[error("Plonky3 commit differs from the protocol pin")]
    Plonky3Commit,
    #[error("AIR source hash differs from the v0.3 withdrawal AIR")]
    AirSourceHash,
    #[error("protocol constants differ from v0.3")]
    Protocol,
    #[error("trace height is invalid")]
    TraceHeight,
    #[error("hiding parameters are not canonical")]
    Hiding,
    #[error("profile parameters are not canonical")]
    Parameters,
    #[error("sepolia profile does not meet the conjectured 100-bit target")]
    Security,
    #[error("manifest field is too long")]
    Length,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn profiles_encode_deterministically() {
        for name in ["dev", "ci", "sepolia-v0.3"] {
            let manifest = ParameterManifest::profile(name);
            assert_eq!(
                manifest.encode_binary().unwrap(),
                manifest.encode_binary().unwrap()
            );
            assert!(!manifest.id().unwrap().is_zero());
        }
    }

    #[test]
    fn sepolia_accounting_reaches_documented_conjectured_target() {
        let manifest = ParameterManifest::profile("sepolia-v0.3");
        let analysis = analyze_profile("sepolia-v0.3");
        assert_eq!(analysis.conjectured_bits, 107);
        assert_eq!(analysis.proven_unique_decoding_bits, 37);
        assert_eq!(analysis.proven_list_decoding_bits, 56);
        assert_eq!(analysis.proven_bits, 56);
        assert_eq!(NUM_WITHDRAWAL_COLS, 190);
        assert_eq!(analysis.batched_functions, 210);
        assert_eq!(analysis.air_constraints, 1_186);
        assert_eq!(analysis.air_max_constraint_degree, 7);
        assert_eq!(manifest.target_quantum_bits(), 107);
        assert_eq!(manifest.conservative_quantum_bits(), 56);
    }

    #[test]
    fn sepolia_manifest_pins_v3_q32_hiding_profile() {
        let manifest = ParameterManifest::profile("sepolia-v0.3");
        assert_eq!(MANIFEST_MAGIC, *b"PQTCPRM3");
        assert_eq!(MANIFEST_VERSION, 3);
        assert_eq!(manifest.air_version, 3);
        assert_eq!(manifest.protocol_version, 3);
        assert_eq!(manifest.proof_codec_version, 3);
        assert_eq!(manifest.verifier_interface_version, 3);
        assert_eq!(manifest.fri_log_blowup, 4);
        assert_eq!(manifest.fri_query_count, 32);
        assert_eq!(manifest.commit_grinding_bits, 16);
        assert_eq!(manifest.query_grinding_bits, 16);
        assert_eq!(manifest.random_codeword_count, 4);
        assert_eq!(manifest.mmcs_salt_elements, 8);
        assert_eq!(manifest.validate(), Ok(()));
    }

    #[test]
    fn sepolia_manifest_rejects_sub_hundred_bit_actual_parameters() {
        let mut manifest = ParameterManifest::profile("sepolia-v0.3");
        manifest.fri_query_count = 1;
        assert!(analyze_manifest(&manifest).conjectured_bits < 100);
        assert_eq!(manifest.validate(), Err(ManifestError::Security));
    }

    #[test]
    fn manifest_rejects_non_v3_protocol_and_codec_versions() {
        let mut manifest = ParameterManifest::profile("dev");
        manifest.protocol_version = 2;
        assert_eq!(manifest.validate(), Err(ManifestError::Protocol));

        let mut manifest = ParameterManifest::profile("dev");
        manifest.air_version = 2;
        assert_eq!(manifest.validate(), Err(ManifestError::Protocol));

        let mut manifest = ParameterManifest::profile("dev");
        manifest.proof_codec_version = 2;
        assert_eq!(manifest.validate(), Err(ManifestError::Protocol));

        let mut manifest = ParameterManifest::profile("dev");
        manifest.verifier_interface_version = 2;
        assert_eq!(manifest.validate(), Err(ManifestError::Protocol));
    }
}
```

</details>

## `crates/pqtc-spec/Cargo.toml`

- Bytes: 343
- SHA-256: `e9976f9d7be608ed6e03612383489cbdcfca7f08176db8b3f01c12f8cb51b901`

<details><summary>Complete file</summary>

```toml
[package]
name = "pqtc-spec"
version.workspace = true
edition.workspace = true
license.workspace = true
rust-version.workspace = true

[dependencies]
hex.workspace = true
rand.workspace = true
serde.workspace = true
thiserror.workspace = true

[dev-dependencies]
postcard.workspace = true
serde_json.workspace = true

[lints]
workspace = true
```

</details>

## `crates/pqtc-spec/src/domains.rs`

- Bytes: 529
- SHA-256: `b020c104d76dac15ef912c8a0891c6eb3e18b61865eed131b5b606ef3d3ec63f`

<details><summary>Complete file</summary>

```rust
//! Normative one-byte protocol domains. Changing any value changes the protocol.

pub const SCOPE: u8 = 0x10;
pub const NOTE: u8 = 0x11;
pub const NULLIFIER: u8 = 0x12;
pub const EMPTY_LEAF: u8 = 0x13;
pub const PAYOUT: u8 = 0x14;
pub const STATEMENT: u8 = 0x15;
pub const APP_MERKLE_NODE: u8 = 0x20;

pub const PROOF_LEAF: u8 = 0x40;
pub const PROOF_NODE: u8 = 0x41;
pub const TRANSCRIPT_INIT: u8 = 0x42;
pub const TRANSCRIPT_ABSORB: u8 = 0x43;
pub const TRANSCRIPT_SQUEEZE: u8 = 0x44;
pub const PARAMETER_MANIFEST: u8 = 0x45;
```

</details>

## `crates/pqtc-spec/src/lib.rs`

- Bytes: 13,445
- SHA-256: `0f6d38b4e028d8162390454fddc6d72d440a6750c1e84ef80655066142d56ec5`

<details><summary>Complete file</summary>

```rust
//! Canonical protocol types and encodings for PQ Tornado Classic v0.3.

pub mod domains;

use core::{fmt, str::FromStr};
use rand::{CryptoRng, Rng, RngExt, TryRng};
use serde::{
    Deserialize, Deserializer, Serialize, Serializer,
    de::{Error as _, SeqAccess, Visitor},
    ser::SerializeTuple,
};
use thiserror::Error;

pub const PROTOCOL_VERSION: u32 = 3;
pub const TREE_DEPTH: u8 = 20;
pub const BABY_BEAR_MODULUS: u32 = 2_013_265_921;
pub const PUBLIC_VALUES_COUNT: usize = 64;
pub const PLONKY3_COMMIT: &str = "3152b14a89067c83775a8076cc262ffc48a1fd7c";

/// A 32-byte secret encoded as eight canonical big-endian `BabyBear` limbs.
///
/// Construction always validates that every limb is strictly less than
/// [`BABY_BEAR_MODULUS`]. Random construction samples full-width `u32` values
/// and rejects out-of-field candidates, so it introduces no modulo bias.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct CanonicalSecret([u32; 8]);

impl CanonicalSecret {
    pub const BYTE_LEN: usize = 32;
    pub const LIMB_COUNT: usize = 8;

    /// Validates eight field limbs.
    ///
    /// # Errors
    ///
    /// Returns [`CanonicalError::NonCanonicalField`] for the first limb that
    /// is not a canonical `BabyBear` value.
    pub fn from_limbs(limbs: [u32; Self::LIMB_COUNT]) -> Result<Self, CanonicalError> {
        for &value in &limbs {
            if value >= BABY_BEAR_MODULUS {
                return Err(CanonicalError::NonCanonicalField { value });
            }
        }
        Ok(Self(limbs))
    }

    /// Decodes and validates eight big-endian field limbs.
    ///
    /// # Errors
    ///
    /// Returns [`CanonicalError::NonCanonicalField`] for the first limb that
    /// is not a canonical `BabyBear` value.
    pub fn from_bytes(bytes: [u8; Self::BYTE_LEN]) -> Result<Self, CanonicalError> {
        let mut limbs = [0u32; Self::LIMB_COUNT];
        for (limb, chunk) in limbs.iter_mut().zip(bytes.chunks_exact(4)) {
            let [a, b, c, d] = chunk else {
                unreachable!("chunks_exact(4) only yields four-byte chunks");
            };
            *limb = decode_field([*a, *b, *c, *d])?;
        }
        Ok(Self(limbs))
    }

    /// Samples eight independent, uniform `BabyBear` limbs from `rng`.
    pub fn random_with<R: CryptoRng + Rng + ?Sized>(rng: &mut R) -> Self {
        let limbs = core::array::from_fn(|_| {
            loop {
                let candidate: u32 = rng.random();
                if candidate < BABY_BEAR_MODULUS {
                    break candidate;
                }
            }
        });
        Self(limbs)
    }

    /// Samples eight independent, uniform `BabyBear` limbs directly from the
    /// operating system.
    ///
    /// # Panics
    ///
    /// Panics when operating-system randomness is unavailable.
    #[must_use]
    pub fn generate() -> Self {
        let limbs = core::array::from_fn(|_| {
            loop {
                let candidate = rand::rngs::SysRng
                    .try_next_u32()
                    .expect("operating-system randomness is unavailable");
                if candidate < BABY_BEAR_MODULUS {
                    break candidate;
                }
            }
        });
        Self(limbs)
    }

    #[must_use]
    pub const fn limbs(&self) -> &[u32; Self::LIMB_COUNT] {
        &self.0
    }

    #[must_use]
    pub const fn into_limbs(self) -> [u32; Self::LIMB_COUNT] {
        self.0
    }

    #[must_use]
    pub fn to_bytes(self) -> [u8; Self::BYTE_LEN] {
        let mut bytes = [0u8; Self::BYTE_LEN];
        for (&limb, output) in self.0.iter().zip(bytes.chunks_exact_mut(4)) {
            output.copy_from_slice(&limb.to_be_bytes());
        }
        bytes
    }
}

impl TryFrom<&[u8]> for CanonicalSecret {
    type Error = CanonicalError;

    fn try_from(bytes: &[u8]) -> Result<Self, Self::Error> {
        let bytes: [u8; Self::BYTE_LEN] = bytes.try_into().map_err(|_| CanonicalError::Length {
            expected: Self::BYTE_LEN,
            actual: bytes.len(),
        })?;
        Self::from_bytes(bytes)
    }
}

impl TryFrom<[u8; CanonicalSecret::BYTE_LEN]> for CanonicalSecret {
    type Error = CanonicalError;

    fn try_from(bytes: [u8; CanonicalSecret::BYTE_LEN]) -> Result<Self, Self::Error> {
        Self::from_bytes(bytes)
    }
}

impl fmt::Debug for CanonicalSecret {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("CanonicalSecret(REDACTED)")
    }
}

impl fmt::Display for CanonicalSecret {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "0x{}", hex::encode(self.to_bytes()))
    }
}

impl FromStr for CanonicalSecret {
    type Err = CanonicalError;

    fn from_str(encoded: &str) -> Result<Self, Self::Err> {
        let hex = encoded
            .strip_prefix("0x")
            .ok_or(CanonicalError::InvalidSecretEncoding)?;
        if hex.len() != Self::BYTE_LEN * 2 {
            return Err(CanonicalError::Length {
                expected: Self::BYTE_LEN * 2,
                actual: hex.len(),
            });
        }
        let mut bytes = [0u8; Self::BYTE_LEN];
        hex::decode_to_slice(hex, &mut bytes).map_err(|_| CanonicalError::InvalidSecretEncoding)?;
        Self::from_bytes(bytes)
    }
}

impl Serialize for CanonicalSecret {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        if serializer.is_human_readable() {
            serializer.serialize_str(&self.to_string())
        } else {
            let mut tuple = serializer.serialize_tuple(Self::BYTE_LEN)?;
            for byte in self.to_bytes() {
                tuple.serialize_element(&byte)?;
            }
            tuple.end()
        }
    }
}

struct CanonicalSecretVisitor;

impl<'de> Visitor<'de> for CanonicalSecretVisitor {
    type Value = CanonicalSecret;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a canonical 0x-prefixed 32-byte BabyBear secret")
    }

    fn visit_str<E: serde::de::Error>(self, value: &str) -> Result<Self::Value, E> {
        value.parse().map_err(E::custom)
    }

    fn visit_seq<A: SeqAccess<'de>>(self, mut sequence: A) -> Result<Self::Value, A::Error> {
        let mut bytes = [0u8; CanonicalSecret::BYTE_LEN];
        for (index, byte) in bytes.iter_mut().enumerate() {
            *byte = sequence
                .next_element()?
                .ok_or_else(|| A::Error::invalid_length(index, &self))?;
        }
        CanonicalSecret::from_bytes(bytes).map_err(A::Error::custom)
    }
}

impl<'de> Deserialize<'de> for CanonicalSecret {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        if deserializer.is_human_readable() {
            deserializer.deserialize_str(CanonicalSecretVisitor)
        } else {
            deserializer.deserialize_tuple(Self::BYTE_LEN, CanonicalSecretVisitor)
        }
    }
}

#[derive(Clone, Copy, Default, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Digest512 {
    pub left: [u8; 32],
    pub right: [u8; 32],
}

impl Digest512 {
    pub const ZERO: Self = Self {
        left: [0; 32],
        right: [0; 32],
    };

    #[must_use]
    pub fn to_bytes(self) -> [u8; 64] {
        let mut out = [0; 64];
        out[..32].copy_from_slice(&self.left);
        out[32..].copy_from_slice(&self.right);
        out
    }

    #[must_use]
    pub fn from_bytes(bytes: [u8; 64]) -> Self {
        let mut left = [0; 32];
        let mut right = [0; 32];
        left.copy_from_slice(&bytes[..32]);
        right.copy_from_slice(&bytes[32..]);
        Self { left, right }
    }

    #[must_use]
    pub fn is_zero(&self) -> bool {
        *self == Self::ZERO
    }
}

impl fmt::Debug for Digest512 {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "0x{}", hex::encode(self.to_bytes()))
    }
}

impl fmt::Display for Digest512 {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "0x{}", hex::encode(self.to_bytes()))
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ScopeInput {
    pub chain_id: u64,
    pub pool: [u8; 20],
    pub denomination: [u8; 32],
    pub tree_depth: u8,
    pub protocol_version: u32,
    pub parameter_id: Digest512,
}

impl ScopeInput {
    #[must_use]
    pub fn encode(self) -> [u8; 129] {
        let mut out = [0; 129];
        out[..8].copy_from_slice(&self.chain_id.to_be_bytes());
        out[8..28].copy_from_slice(&self.pool);
        out[28..60].copy_from_slice(&self.denomination);
        out[60] = self.tree_depth;
        out[61..65].copy_from_slice(&self.protocol_version.to_be_bytes());
        out[65..].copy_from_slice(&self.parameter_id.to_bytes());
        out
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct WithdrawalStatement {
    pub scope: Digest512,
    pub root: Digest512,
    pub nullifier_hash: Digest512,
    pub payout_digest: Digest512,
}

impl WithdrawalStatement {
    #[must_use]
    pub fn public_values(self) -> [u32; PUBLIC_VALUES_COUNT] {
        let mut values = [0u32; PUBLIC_VALUES_COUNT];
        let digests = [
            self.scope,
            self.root,
            self.nullifier_hash,
            self.payout_digest,
        ];
        let mut cursor = 0;
        for digest in digests {
            for half in [digest.left, digest.right] {
                for limb in half.chunks_exact(4) {
                    values[cursor] = u32::from_be_bytes([limb[0], limb[1], limb[2], limb[3]]);
                    cursor += 1;
                }
            }
        }
        values
    }
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum CanonicalError {
    #[error("field element {value} is not canonical")]
    NonCanonicalField { value: u32 },
    #[error("invalid byte length: expected {expected}, got {actual}")]
    Length { expected: usize, actual: usize },
    #[error("secret must be 0x-prefixed hexadecimal")]
    InvalidSecretEncoding,
}

/// Decodes one canonical big-endian `BabyBear` field element.
///
/// # Errors
///
/// Returns [`CanonicalError::NonCanonicalField`] when the integer is not less
/// than the `BabyBear` modulus.
pub fn decode_field(bytes: [u8; 4]) -> Result<u32, CanonicalError> {
    let value = u32::from_be_bytes(bytes);
    if value >= BABY_BEAR_MODULUS {
        return Err(CanonicalError::NonCanonicalField { value });
    }
    Ok(value)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn statement_uses_big_endian_thirty_two_bit_field_elements() {
        let mut digest = Digest512::ZERO;
        digest.left[0..4].copy_from_slice(&[0x12, 0x34, 0xab, 0xcd]);
        let values = WithdrawalStatement {
            scope: digest,
            root: Digest512::ZERO,
            nullifier_hash: Digest512::ZERO,
            payout_digest: Digest512::ZERO,
        }
        .public_values();
        assert_eq!(values[0], 0x1234_abcd);
        assert_eq!(values[1], 0);
    }

    #[test]
    fn field_codec_rejects_modulus() {
        assert_eq!(
            decode_field((BABY_BEAR_MODULUS - 1).to_be_bytes()),
            Ok(BABY_BEAR_MODULUS - 1)
        );
        assert!(matches!(
            decode_field(BABY_BEAR_MODULUS.to_be_bytes()),
            Err(CanonicalError::NonCanonicalField { .. })
        ));
    }

    #[test]
    fn canonical_secret_round_trips_binary_text_and_serde() {
        let limbs =
            core::array::from_fn(|index| u32::try_from(index).expect("small index") * 0x0102_0304);
        let secret = CanonicalSecret::from_limbs(limbs).unwrap();
        let bytes = secret.to_bytes();
        assert_eq!(CanonicalSecret::from_bytes(bytes), Ok(secret));
        assert_eq!(secret.to_string().parse(), Ok(secret));
        assert_eq!(core::mem::size_of::<CanonicalSecret>(), 32);

        let json = serde_json::to_string(&secret).unwrap();
        assert_eq!(
            serde_json::from_str::<CanonicalSecret>(&json).unwrap(),
            secret
        );
        let binary = postcard::to_allocvec(&secret).unwrap();
        assert_eq!(binary, bytes);
        assert_eq!(
            postcard::from_bytes::<CanonicalSecret>(&binary).unwrap(),
            secret
        );
        assert!(
            CanonicalSecret::generate()
                .limbs()
                .iter()
                .all(|&limb| limb < BABY_BEAR_MODULUS)
        );
    }

    #[test]
    fn canonical_secret_rejects_every_noncanonical_boundary() {
        for limb in 0..CanonicalSecret::LIMB_COUNT {
            let mut bytes = [0u8; CanonicalSecret::BYTE_LEN];
            bytes[limb * 4..limb * 4 + 4].copy_from_slice(&BABY_BEAR_MODULUS.to_be_bytes());
            assert!(matches!(
                CanonicalSecret::from_bytes(bytes),
                Err(CanonicalError::NonCanonicalField {
                    value: BABY_BEAR_MODULUS
                })
            ));
            assert!(CanonicalSecret::try_from(bytes.as_slice()).is_err());
            assert!(
                format!("0x{}", hex::encode(bytes))
                    .parse::<CanonicalSecret>()
                    .is_err()
            );
            let json = format!("\"0x{}\"", hex::encode(bytes));
            assert!(serde_json::from_str::<CanonicalSecret>(&json).is_err());
            assert!(postcard::from_bytes::<CanonicalSecret>(&bytes).is_err());
        }
    }
}
```

</details>

## `crates/pqtc-stark/Cargo.toml`

- Bytes: 638
- SHA-256: `4d132001a27feb07a0ebe848adfbacbc6b3928eab7229d05d494247f8f751e0b`

<details><summary>Complete file</summary>

```toml
[package]
name = "pqtc-stark"
version.workspace = true
edition.workspace = true
license.workspace = true
rust-version.workspace = true

[dependencies]
p3-baby-bear.workspace = true
p3-challenger.workspace = true
p3-commit.workspace = true
p3-dft.workspace = true
p3-field.workspace = true
p3-fri.workspace = true
p3-keccak.workspace = true
p3-merkle-tree.workspace = true
p3-symmetric.workspace = true
p3-uni-stark.workspace = true
pqtc-hash = { path = "../pqtc-hash" }
pqtc-poseidon-air = { path = "../pqtc-poseidon-air" }
pqtc-spec = { path = "../pqtc-spec" }
rand.workspace = true
thiserror.workspace = true


[lints]
workspace = true
```

</details>

## `crates/pqtc-stark/src/codec.rs`

- Bytes: 41,763
- SHA-256: `006e0183d2a259075003ec73e6d2199160cba9a2148b08d46b9611de30d69d94`

<details><summary>Complete file</summary>

```rust
//! Canonical two-transaction calldata codec for Poseidon withdrawal proofs.
//! Fixed dimensions are implicit; query authentication paths stay pruned and
//! are independently deduplicated for each transaction's query half.

use std::collections::BTreeSet;

use p3_challenger::{CanObserve, CanSampleBits, FieldChallenger, GrindingChallenger};
use p3_commit::OpenedValues as PcsOpenedValues;
use p3_field::{BasedVectorSpace, PrimeCharacteristicRing, PrimeField32};
use p3_fri::FriProof;
use p3_symmetric::MerkleCap;
use p3_uni_stark::{Commitments, OpenedValues, Proof};
use pqtc_hash::keccak256;
use pqtc_poseidon_air::{NUM_WITHDRAWAL_COLS, TRACE_HEIGHT};
use pqtc_spec::{BABY_BEAR_MODULUS, Digest512, PUBLIC_VALUES_COUNT, WithdrawalStatement};
use thiserror::Error;

use crate::crypto::Transcript512;
use crate::query::{HalfFriRound, HalfInput, QueryHalf, merge_queries, split_queries};
use crate::{Challenge, Config, SecurityProfile, StarkProof, Val};

pub const PROOF_PART_VERSION: u16 = 3;
pub const PROOF_PART_A_MAGIC: [u8; 8] = *b"PQTCPA03";
pub const PROOF_PART_B_MAGIC: [u8; 8] = *b"PQTCPB03";
const PART_A_END: u32 = 0x5041_4533;
const PART_B_END: u32 = 0x5042_4533;
const STATEMENT_DOMAIN: &[u8] = b"PQTC.V3.STATEMENT";
const CHECKPOINT_DOMAIN: &[u8] = b"PQTC.V3.CHECKPOINT";
const PROOF_ID_DOMAIN: &[u8] = b"PQTC.V3.PROOF";
const QUOTIENT_CHUNKS: usize = 16;
const EXTENSION_DEGREE: usize = 4;
const MMCS_SALT_ELEMENTS: usize = 8;
const FRI_ROUNDS: usize = 9;
const FIELD_BYTES: usize = 4;
const CHALLENGE_BYTES: usize = EXTENSION_DEGREE * FIELD_BYTES;
const COMMITMENT_BYTES: usize = 8 * 8;
const DIGEST_BYTES: usize = 64;
const MAX_PATH_HASHES: usize = 4_096;

pub const COMMON_HEADER_BYTES: usize =
    8 + 2 + 4 + 2 + DIGEST_BYTES + 2 + PUBLIC_VALUES_COUNT * FIELD_BYTES;
const fn global_data_bytes(random_codewords: usize) -> usize {
    3 * COMMITMENT_BYTES
        + (2 * NUM_WITHDRAWAL_COLS + QUOTIENT_CHUNKS * EXTENSION_DEGREE + EXTENSION_DEGREE)
            * CHALLENGE_BYTES
        + (1 + 2 + QUOTIENT_CHUNKS) * random_codewords * CHALLENGE_BYTES
        + FRI_ROUNDS * COMMITMENT_BYTES
        + FRI_ROUNDS * FIELD_BYTES
        + CHALLENGE_BYTES
        + FIELD_BYTES
}
pub const GLOBAL_DATA_BYTES: usize = global_data_bytes(4);
const _: () = assert!(COMMON_HEADER_BYTES == 338);
pub const PRODUCTION_QUERY_COUNT: usize = 32;
pub const PRODUCTION_HALF_QUERY_COUNT: usize = PRODUCTION_QUERY_COUNT / 2;
const _: () = assert!(SecurityProfile::SepoliaV03.fri().2 == PRODUCTION_QUERY_COUNT);
const _: () = assert!(TRACE_HEIGHT == 256);
const _: () = assert!(GLOBAL_DATA_BYTES == 9_208);

type Digest = [u64; 8];
type Commitment = MerkleCap<Val, Digest>;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ProofShape {
    pub query_count: usize,
    pub log_blowup: usize,
    pub random_codewords: usize,
}
impl ProofShape {
    #[must_use]
    pub fn for_profile(profile: SecurityProfile) -> Self {
        let (log_blowup, _, query_count, _, _) = profile.fri();
        Self {
            query_count,
            log_blowup,
            random_codewords: profile.random_codewords(),
        }
    }
    #[must_use]
    pub const fn degree_bits(self) -> usize {
        TRACE_HEIGHT.ilog2() as usize + 1
    }
    pub const fn fri_rounds(self) -> usize {
        FRI_ROUNDS
    }
    pub(crate) const fn input_matrix_width(self, batch: usize) -> usize {
        match batch {
            0 => EXTENSION_DEGREE + self.random_codewords,
            1 => NUM_WITHDRAWAL_COLS + self.random_codewords,
            2 => EXTENSION_DEGREE + self.random_codewords,
            _ => 0,
        }
    }
    pub(crate) const fn input_matrix_count(self, batch: usize) -> usize {
        match batch {
            0 | 1 => 1,
            2 => QUOTIENT_CHUNKS,
            _ => 0,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TranscriptCheckpoint {
    pub digest: [u8; 32],
    pub global_digest: [u8; 32],
    pub state: Digest512,
    pub air_alpha: Challenge,
    pub zeta: Challenge,
    pub fri_alpha: Challenge,
    pub fri_betas: Vec<Challenge>,
    pub query_indices: Vec<u32>,
    pub unique_query_indices: Vec<u32>,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProofPartA {
    pub bytes: Vec<u8>,
    pub proof_id: [u8; 32],
    pub statement_key: [u8; 32],
    pub checkpoint: TranscriptCheckpoint,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProofPartB {
    pub bytes: Vec<u8>,
    pub proof_id: [u8; 32],
    pub checkpoint_digest: [u8; 32],
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EncodedProofParts {
    pub part_a: ProofPartA,
    pub part_b: ProofPartB,
}

#[must_use]
pub fn statement_key(parameter_id: Digest512, statement: WithdrawalStatement) -> [u8; 32] {
    let mut abi = Vec::with_capacity((3 + PUBLIC_VALUES_COUNT) * 32);
    put_abi_word(&mut abi, STATEMENT_DOMAIN);
    abi.extend_from_slice(&parameter_id.left);
    abi.extend_from_slice(&parameter_id.right);
    for value in statement.public_values() {
        abi.extend_from_slice(&[0; 28]);
        put_u32(&mut abi, value);
    }
    keccak256(&abi)
}

pub fn encode_proof_parts(
    proof: &StarkProof,
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
) -> Result<EncodedProofParts, StarkCodecError> {
    let part_a = encode_proof_part_a(proof, profile, parameter_id, statement)?;
    let part_b = encode_proof_part_b(proof, profile, parameter_id, statement, &part_a)?;
    Ok(EncodedProofParts { part_a, part_b })
}
pub fn encode_proof_part_a(
    proof: &StarkProof,
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
) -> Result<ProofPartA, StarkCodecError> {
    ensure_canonical_statement(statement)?;
    let shape = ProofShape::for_profile(profile);
    validate_shape(proof, shape)?;
    let global = encode_global(proof, shape)?;
    let global_digest = keccak256(&global);
    let checkpoint = derive_checkpoint(proof, profile, parameter_id, statement, global_digest)?;
    let halves = split_queries(proof, shape, &checkpoint)?;
    let mut out = Vec::new();
    put_header(
        &mut out,
        PROOF_PART_A_MAGIC,
        profile,
        shape,
        parameter_id,
        statement,
    )?;
    out.extend_from_slice(&global_digest);
    out.extend_from_slice(&global);
    put_checkpoint(&mut out, &checkpoint)?;
    put_half(&mut out, &halves[0])?;
    put_u32(&mut out, PART_A_END);
    let key = statement_key(parameter_id, statement);
    let proof_id = derive_proof_id(key, &out);
    Ok(ProofPartA {
        bytes: out,
        proof_id,
        statement_key: key,
        checkpoint,
    })
}
pub fn encode_proof_part_b(
    proof: &StarkProof,
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
    part_a: &ProofPartA,
) -> Result<ProofPartB, StarkCodecError> {
    ensure_canonical_statement(statement)?;
    let shape = ProofShape::for_profile(profile);
    validate_shape(proof, shape)?;
    let key = statement_key(parameter_id, statement);
    if part_a.statement_key != key || part_a.proof_id != derive_proof_id(key, &part_a.bytes) {
        return Err(StarkCodecError::CrossPartBinding);
    }
    let global = encode_global(proof, shape)?;
    let global_digest = keccak256(&global);
    let checkpoint = derive_checkpoint(proof, profile, parameter_id, statement, global_digest)?;
    if checkpoint != part_a.checkpoint {
        return Err(StarkCodecError::CrossPartBinding);
    }
    let halves = split_queries(proof, shape, &checkpoint)?;
    let mut out = Vec::new();
    put_header(
        &mut out,
        PROOF_PART_B_MAGIC,
        profile,
        shape,
        parameter_id,
        statement,
    )?;
    out.extend_from_slice(&part_a.proof_id);
    out.extend_from_slice(&global_digest);
    out.extend_from_slice(&global);
    put_checkpoint(&mut out, &checkpoint)?;
    put_half(&mut out, &halves[1])?;
    put_u32(&mut out, PART_B_END);
    Ok(ProofPartB {
        bytes: out,
        proof_id: part_a.proof_id,
        checkpoint_digest: checkpoint.digest,
    })
}

pub fn decode_proof_parts(
    part_a: &[u8],
    part_b: &[u8],
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
) -> Result<StarkProof, StarkCodecError> {
    let shape = ProofShape::for_profile(profile);
    let mut a = Reader::new(part_a);
    a.header(PROOF_PART_A_MAGIC, profile, shape, parameter_id, statement)?;
    let a_digest = a.take::<32>()?;
    let (global_a, raw_a) = a.global(shape, profile)?;
    if keccak256(raw_a) != a_digest {
        return Err(StarkCodecError::GlobalDigest);
    }
    let cp_a = a.checkpoint(shape)?;
    validate_checkpoint_digest(&cp_a, parameter_id, statement)?;
    if cp_a.global_digest != a_digest {
        return Err(StarkCodecError::GlobalDigest);
    }
    let half_a = a.half(shape, 0)?;
    if a.u32()? != PART_A_END {
        return Err(StarkCodecError::EndMarker);
    }
    a.finish()?;
    let proof_id = derive_proof_id(statement_key(parameter_id, statement), part_a);

    let mut b = Reader::new(part_b);
    b.header(PROOF_PART_B_MAGIC, profile, shape, parameter_id, statement)?;
    if b.take::<32>()? != proof_id {
        return Err(StarkCodecError::CrossPartBinding);
    }
    let b_digest = b.take::<32>()?;
    let (_global_b, raw_b) = b.global(shape, profile)?;
    if b_digest != a_digest || raw_b != raw_a || keccak256(raw_b) != b_digest {
        return Err(StarkCodecError::GlobalDigest);
    }
    let cp_b = b.checkpoint(shape)?;
    if cp_b != cp_a {
        return Err(StarkCodecError::CrossPartBinding);
    }
    let half_b = b.half(shape, shape.query_count / 2)?;
    if b.u32()? != PART_B_END {
        return Err(StarkCodecError::EndMarker);
    }
    b.finish()?;
    let mut proof = global_a.into_proof(shape);
    merge_queries(&mut proof, shape, &cp_a, [half_a, half_b])?;
    validate_shape(&proof, shape)?;
    if derive_checkpoint(&proof, profile, parameter_id, statement, a_digest)? != cp_a {
        return Err(StarkCodecError::TranscriptCheckpoint);
    }
    Ok(proof)
}

struct GlobalData {
    commitments: Commitments<Commitment>,
    opened: OpenedValues<Challenge>,
    hiding: PcsOpenedValues<Challenge>,
    commits: Vec<Commitment>,
    pow: Vec<Val>,
    final_poly: Vec<Challenge>,
    query_pow: Val,
}
impl GlobalData {
    fn into_proof(self, shape: ProofShape) -> StarkProof {
        Proof::<Config> {
            commitments: self.commitments,
            opened_values: self.opened,
            opening_proof: (
                self.hiding,
                FriProof {
                    commit_phase_commits: self.commits,
                    commit_pow_witnesses: self.pow,
                    input_openings: Vec::new(),
                    commit_phase_openings: Vec::new(),
                    final_poly: self.final_poly,
                    query_pow_witness: self.query_pow,
                },
            ),
            degree_bits: shape.degree_bits(),
        }
    }
}
fn encode_global(proof: &StarkProof, shape: ProofShape) -> Result<Vec<u8>, StarkCodecError> {
    let expected_len = global_data_bytes(shape.random_codewords);
    let mut out = Vec::with_capacity(expected_len);
    put_cap(&mut out, &proof.commitments.trace)?;
    put_cap(&mut out, &proof.commitments.quotient_chunks)?;
    put_cap(
        &mut out,
        proof
            .commitments
            .random
            .as_ref()
            .ok_or(StarkCodecError::Shape("random commitment"))?,
    )?;
    put_exts(&mut out, &proof.opened_values.trace_local);
    put_exts(
        &mut out,
        proof
            .opened_values
            .trace_next
            .as_ref()
            .ok_or(StarkCodecError::Shape("trace next"))?,
    );
    for chunk in &proof.opened_values.quotient_chunks {
        put_exts(&mut out, chunk);
    }
    put_exts(
        &mut out,
        proof
            .opened_values
            .random
            .as_ref()
            .ok_or(StarkCodecError::Shape("random opening"))?,
    );
    for round in &proof.opening_proof.0 {
        for matrix in round {
            for point in matrix {
                put_exts(&mut out, point);
            }
        }
    }
    for cap in &proof.opening_proof.1.commit_phase_commits {
        put_cap(&mut out, cap)?;
    }
    for &w in &proof.opening_proof.1.commit_pow_witnesses {
        put_val(&mut out, w);
    }
    put_exts(&mut out, &proof.opening_proof.1.final_poly);
    put_val(&mut out, proof.opening_proof.1.query_pow_witness);
    if out.len() != expected_len {
        return Err(StarkCodecError::Shape("global data bytes"));
    }
    Ok(out)
}

fn derive_checkpoint(
    proof: &StarkProof,
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
    global_digest: [u8; 32],
) -> Result<TranscriptCheckpoint, StarkCodecError> {
    let shape = ProofShape::for_profile(profile);
    let pv = crate::withdrawal_public_values(statement);
    let mut t = Transcript512::new(parameter_id, &pv);
    t.observe(Val::from_usize(proof.degree_bits));
    t.observe(Val::from_usize(proof.degree_bits - 1));
    t.observe(Val::ZERO);
    t.observe(proof.commitments.trace.clone());
    t.observe_slice(&pv);
    let air_alpha = t.sample_algebra_element();
    t.observe(proof.commitments.quotient_chunks.clone());
    t.observe(
        proof
            .commitments
            .random
            .clone()
            .ok_or(StarkCodecError::Shape("random commitment"))?,
    );
    let zeta = t.sample_algebra_element();
    let h = &proof.opening_proof.0;
    t.observe_algebra_slice(&joined(
        proof
            .opened_values
            .random
            .as_ref()
            .ok_or(StarkCodecError::Shape("random opening"))?,
        &h[0][0][0],
    ));
    t.observe_algebra_slice(&joined(&proof.opened_values.trace_local, &h[1][0][0]));
    t.observe_algebra_slice(&joined(
        proof
            .opened_values
            .trace_next
            .as_ref()
            .ok_or(StarkCodecError::Shape("trace next"))?,
        &h[1][0][1],
    ));
    for (i, chunk) in proof.opened_values.quotient_chunks.iter().enumerate() {
        t.observe_algebra_slice(&joined(chunk, &h[2][i][0]));
    }
    let fri_alpha = t.sample_algebra_element();
    let (_, _, q, commit_pow, query_pow) = profile.fri();
    let mut fri_betas = Vec::with_capacity(shape.fri_rounds());
    for (cap, &w) in proof
        .opening_proof
        .1
        .commit_phase_commits
        .iter()
        .zip(&proof.opening_proof.1.commit_pow_witnesses)
    {
        t.observe(cap.clone());
        if !t.check_witness(commit_pow, w) {
            return Err(StarkCodecError::InvalidCommitPow);
        }
        fri_betas.push(t.sample_algebra_element());
    }
    t.observe_algebra_slice(&proof.opening_proof.1.final_poly);
    for _ in 0..shape.fri_rounds() {
        t.observe(Val::ONE);
    }
    if !t.check_witness(query_pow, proof.opening_proof.1.query_pow_witness) {
        return Err(StarkCodecError::InvalidQueryPow);
    }
    let state = t.state();
    let bits = proof.degree_bits + shape.log_blowup;
    let query_indices = (0..q)
        .map(|_| t.sample_bits(bits) as u32)
        .collect::<Vec<_>>();
    let unique_query_indices = sorted_unique(&query_indices);
    let mut cp = TranscriptCheckpoint {
        digest: [0; 32],
        global_digest,
        state,
        air_alpha,
        zeta,
        fri_alpha,
        fri_betas,
        query_indices,
        unique_query_indices,
    };
    cp.digest = checkpoint_digest(statement_key(parameter_id, statement), &cp)?;
    Ok(cp)
}
fn joined(a: &[Challenge], b: &[Challenge]) -> Vec<Challenge> {
    a.iter().chain(b).copied().collect()
}
fn sorted_unique(v: &[u32]) -> Vec<u32> {
    v.iter()
        .copied()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}
fn checkpoint_digest(
    key: [u8; 32],
    cp: &TranscriptCheckpoint,
) -> Result<[u8; 32], StarkCodecError> {
    let mut payload = Vec::new();
    put_checkpoint_payload(&mut payload, cp)?;
    let mut abi = Vec::with_capacity(96);
    put_abi_word(&mut abi, CHECKPOINT_DOMAIN);
    abi.extend_from_slice(&key);
    abi.extend_from_slice(&keccak256(&payload));
    Ok(keccak256(&abi))
}
fn validate_checkpoint_digest(
    cp: &TranscriptCheckpoint,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
) -> Result<(), StarkCodecError> {
    if checkpoint_digest(statement_key(parameter_id, statement), cp)? == cp.digest {
        Ok(())
    } else {
        Err(StarkCodecError::TranscriptCheckpoint)
    }
}
fn derive_proof_id(key: [u8; 32], part_a: &[u8]) -> [u8; 32] {
    let mut abi = Vec::with_capacity(96);
    put_abi_word(&mut abi, PROOF_ID_DOMAIN);
    abi.extend_from_slice(&key);
    abi.extend_from_slice(&keccak256(part_a));
    keccak256(&abi)
}
fn ensure_canonical_statement(statement: WithdrawalStatement) -> Result<(), StarkCodecError> {
    if let Some(value) = statement
        .public_values()
        .into_iter()
        .find(|&value| value >= BABY_BEAR_MODULUS)
    {
        Err(StarkCodecError::NonCanonicalField { value })
    } else {
        Ok(())
    }
}

fn validate_shape(proof: &StarkProof, s: ProofShape) -> Result<(), StarkCodecError> {
    if proof.degree_bits != s.degree_bits() {
        return Err(StarkCodecError::Shape("degree bits"));
    }
    for cap in [
        &proof.commitments.trace,
        &proof.commitments.quotient_chunks,
        proof
            .commitments
            .random
            .as_ref()
            .ok_or(StarkCodecError::Shape("random commitment"))?,
    ] {
        if cap.num_roots() != 1 {
            return Err(StarkCodecError::Shape("cap"));
        }
    }
    if proof.opened_values.trace_local.len() != NUM_WITHDRAWAL_COLS
        || proof.opened_values.trace_next.as_ref().map(Vec::len) != Some(NUM_WITHDRAWAL_COLS)
        || proof.opened_values.quotient_chunks.len() != QUOTIENT_CHUNKS
        || proof
            .opened_values
            .quotient_chunks
            .iter()
            .any(|x| x.len() != 4)
        || proof.opened_values.random.as_ref().map(Vec::len) != Some(4)
        || proof.opened_values.preprocessed_local.is_some()
        || proof.opened_values.preprocessed_next.is_some()
    {
        return Err(StarkCodecError::Shape("OOD"));
    }
    let h = &proof.opening_proof.0;
    let points = [vec![1], vec![2], vec![1; 16]];
    if h.len() != 3 {
        return Err(StarkCodecError::Shape("hiding"));
    }
    for (r, expected) in h.iter().zip(points) {
        if r.len() != expected.len() {
            return Err(StarkCodecError::Shape("hiding"));
        }
        for (m, n) in r.iter().zip(expected) {
            if m.len() != n || m.iter().any(|p| p.len() != s.random_codewords) {
                return Err(StarkCodecError::Shape("hiding"));
            }
        }
    }
    let fri = &proof.opening_proof.1;
    if fri.commit_phase_commits.len() != s.fri_rounds()
        || fri.commit_pow_witnesses.len() != s.fri_rounds()
        || fri.commit_phase_openings.len() != s.fri_rounds()
        || fri.input_openings.len() != 3
        || fri.final_poly.len() != 1
    {
        return Err(StarkCodecError::Shape("FRI"));
    }
    for (batch, input) in fri.input_openings.iter().enumerate() {
        let m = s.input_matrix_count(batch);
        let w = s.input_matrix_width(batch);
        if input.opened_values.len() != s.query_count
            || input.opening_proof.0.len() != s.query_count
            || input
                .opened_values
                .iter()
                .any(|q| q.len() != m || q.iter().any(|r| r.len() != w))
            || input
                .opening_proof
                .0
                .iter()
                .any(|q| q.len() != m || q.iter().any(|x| x.len() != 8))
            || input.opening_proof.1.sibling_hashes.len() > MAX_PATH_HASHES
        {
            return Err(StarkCodecError::Shape("input multiproof"));
        }
    }
    for round in &fri.commit_phase_openings {
        if round.log_arity != 1
            || round.sibling_values.len() != s.query_count
            || round.sibling_values.iter().any(|x| x.len() != 1)
            || round.opening_proof.0.len() != s.query_count
            || round
                .opening_proof
                .0
                .iter()
                .any(|q| q.len() != 1 || q[0].len() != 8)
            || round.opening_proof.1.sibling_hashes.len() > MAX_PATH_HASHES
        {
            return Err(StarkCodecError::Shape("FRI multiproof"));
        }
    }
    Ok(())
}

fn put_header(
    out: &mut Vec<u8>,
    magic: [u8; 8],
    profile: SecurityProfile,
    s: ProofShape,
    parameter: Digest512,
    statement: WithdrawalStatement,
) -> Result<(), StarkCodecError> {
    out.extend_from_slice(&magic);
    put_u16(out, PROOF_PART_VERSION);
    out.push(profile_tag(profile));
    out.push(s.degree_bits() as u8);
    out.push(s.fri_rounds() as u8);
    out.push(s.random_codewords as u8);
    put_u16(out, s.query_count as u16);
    out.extend_from_slice(&parameter.to_bytes());
    put_u16(out, PUBLIC_VALUES_COUNT as u16);
    for v in statement.public_values() {
        if v >= BABY_BEAR_MODULUS {
            return Err(StarkCodecError::NonCanonicalField { value: v });
        }
        put_u32(out, v);
    }
    Ok(())
}
const fn profile_tag(p: SecurityProfile) -> u8 {
    match p {
        SecurityProfile::Dev => 0,
        SecurityProfile::Ci => 1,
        SecurityProfile::SepoliaV03 => 3,
    }
}
fn put_abi_word(out: &mut Vec<u8>, v: &[u8]) {
    out.extend_from_slice(v);
    out.resize(out.len() + 32 - v.len(), 0);
}
fn put_u16(out: &mut Vec<u8>, v: u16) {
    out.extend_from_slice(&v.to_be_bytes());
}
fn put_u32(out: &mut Vec<u8>, v: u32) {
    out.extend_from_slice(&v.to_be_bytes());
}
fn put_val(out: &mut Vec<u8>, v: Val) {
    put_u32(out, v.as_canonical_u32());
}
fn put_ext(out: &mut Vec<u8>, v: Challenge) {
    for &x in v.as_basis_coefficients_slice() {
        put_val(out, x);
    }
}
fn put_exts(out: &mut Vec<u8>, v: &[Challenge]) {
    for &x in v {
        put_ext(out, x);
    }
}
fn put_digest(out: &mut Vec<u8>, d: Digest) {
    for w in d {
        out.extend_from_slice(&w.to_be_bytes());
    }
}
fn put_cap(out: &mut Vec<u8>, c: &Commitment) -> Result<(), StarkCodecError> {
    if c.num_roots() != 1 {
        return Err(StarkCodecError::Shape("cap"));
    }
    put_digest(out, c.roots()[0]);
    Ok(())
}
fn put_checkpoint(out: &mut Vec<u8>, cp: &TranscriptCheckpoint) -> Result<(), StarkCodecError> {
    out.extend_from_slice(&cp.digest);
    put_checkpoint_payload(out, cp)
}
fn put_checkpoint_payload(
    out: &mut Vec<u8>,
    cp: &TranscriptCheckpoint,
) -> Result<(), StarkCodecError> {
    out.extend_from_slice(&cp.global_digest);
    out.extend_from_slice(&cp.state.to_bytes());
    put_ext(out, cp.air_alpha);
    put_ext(out, cp.zeta);
    put_ext(out, cp.fri_alpha);
    for &x in &cp.fri_betas {
        put_ext(out, x);
    }
    put_u16(out, cp.query_indices.len() as u16);
    for &x in &cp.query_indices {
        put_u32(out, x);
    }
    put_u16(out, cp.unique_query_indices.len() as u16);
    for &x in &cp.unique_query_indices {
        put_u32(out, x);
    }
    Ok(())
}
fn put_half(out: &mut Vec<u8>, h: &QueryHalf) -> Result<(), StarkCodecError> {
    put_u16(out, h.start as u16);
    put_u16(out, h.indices.len() as u16);
    for &i in &h.indices {
        put_u32(out, i);
    }
    for input in &h.inputs {
        put_rows(out, &input.opened_values);
        put_rows(out, &input.salts);
        put_hashes(out, &input.sibling_hashes)?;
    }
    for round in &h.fri_rounds {
        for q in &round.sibling_values {
            put_exts(out, q);
        }
        put_rows(out, &round.salts);
        put_hashes(out, &round.sibling_hashes)?;
    }
    Ok(())
}
fn put_rows(out: &mut Vec<u8>, qs: &[Vec<Vec<Val>>]) {
    for q in qs {
        for row in q {
            for &x in row {
                put_val(out, x);
            }
        }
    }
}
fn put_hashes(out: &mut Vec<u8>, hs: &[[u64; 8]]) -> Result<(), StarkCodecError> {
    put_u32(
        out,
        u32::try_from(hs.len()).map_err(|_| StarkCodecError::Length)?,
    );
    for &h in hs {
        put_digest(out, h);
    }
    Ok(())
}

struct Reader<'a> {
    bytes: &'a [u8],
    cursor: usize,
}
impl<'a> Reader<'a> {
    const fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, cursor: 0 }
    }
    fn take<const N: usize>(&mut self) -> Result<[u8; N], StarkCodecError> {
        let end = self
            .cursor
            .checked_add(N)
            .ok_or(StarkCodecError::Truncated)?;
        let v = self
            .bytes
            .get(self.cursor..end)
            .ok_or(StarkCodecError::Truncated)?;
        self.cursor = end;
        Ok(v.try_into().expect("length"))
    }
    fn u8(&mut self) -> Result<u8, StarkCodecError> {
        Ok(self.take::<1>()?[0])
    }
    fn u16(&mut self) -> Result<u16, StarkCodecError> {
        Ok(u16::from_be_bytes(self.take()?))
    }
    fn u32(&mut self) -> Result<u32, StarkCodecError> {
        Ok(u32::from_be_bytes(self.take()?))
    }
    fn val(&mut self) -> Result<Val, StarkCodecError> {
        let v = self.u32()?;
        if v >= BABY_BEAR_MODULUS {
            Err(StarkCodecError::NonCanonicalField { value: v })
        } else {
            Ok(Val::from_u32(v))
        }
    }
    fn ext(&mut self) -> Result<Challenge, StarkCodecError> {
        let c = [self.val()?, self.val()?, self.val()?, self.val()?];
        Ok(Challenge::from_basis_coefficients_fn(|i| c[i]))
    }
    fn exts(&mut self, n: usize) -> Result<Vec<Challenge>, StarkCodecError> {
        (0..n).map(|_| self.ext()).collect()
    }
    fn digest(&mut self) -> Result<Digest, StarkCodecError> {
        let mut d = [0; 8];
        for w in &mut d {
            *w = u64::from_be_bytes(self.take()?);
        }
        Ok(d)
    }
    fn cap(&mut self) -> Result<Commitment, StarkCodecError> {
        Ok(MerkleCap::new(vec![self.digest()?]))
    }
    fn header(
        &mut self,
        magic: [u8; 8],
        profile: SecurityProfile,
        s: ProofShape,
        parameter: Digest512,
        statement: WithdrawalStatement,
    ) -> Result<(), StarkCodecError> {
        if self.take::<8>()? != magic {
            return Err(StarkCodecError::Magic);
        }
        if self.u16()? != PROOF_PART_VERSION {
            return Err(StarkCodecError::Version);
        }
        if self.u8()? != profile_tag(profile) {
            return Err(StarkCodecError::Profile);
        }
        if self.u8()? as usize != s.degree_bits()
            || self.u8()? as usize != s.fri_rounds()
            || self.u8()? as usize != s.random_codewords
            || self.u16()? as usize != s.query_count
        {
            return Err(StarkCodecError::Shape("header"));
        }
        if Digest512::from_bytes(self.take()?) != parameter {
            return Err(StarkCodecError::ParameterId);
        }
        if self.u16()? as usize != PUBLIC_VALUES_COUNT {
            return Err(StarkCodecError::PublicValues);
        }
        let mut pv = [0; PUBLIC_VALUES_COUNT];
        for x in &mut pv {
            *x = self.u32()?;
            if *x >= BABY_BEAR_MODULUS {
                return Err(StarkCodecError::NonCanonicalField { value: *x });
            }
        }
        if pv != statement.public_values() {
            return Err(StarkCodecError::PublicValues);
        }
        Ok(())
    }
    fn global(
        &mut self,
        s: ProofShape,
        profile: SecurityProfile,
    ) -> Result<(GlobalData, &'a [u8]), StarkCodecError> {
        let start = self.cursor;
        let commitments = Commitments {
            trace: self.cap()?,
            quotient_chunks: self.cap()?,
            random: Some(self.cap()?),
        };
        let opened = OpenedValues {
            trace_local: self.exts(NUM_WITHDRAWAL_COLS)?,
            trace_next: Some(self.exts(NUM_WITHDRAWAL_COLS)?),
            preprocessed_local: None,
            preprocessed_next: None,
            quotient_chunks: (0..16).map(|_| self.exts(4)).collect::<Result<_, _>>()?,
            random: Some(self.exts(4)?),
        };
        let points = [vec![1], vec![2], vec![1; 16]];
        let mut hiding = Vec::new();
        for ps in points {
            let mut r = Vec::new();
            for n in ps {
                let mut m = Vec::new();
                for _ in 0..n {
                    m.push(self.exts(s.random_codewords)?);
                }
                r.push(m);
            }
            hiding.push(r);
        }
        let commits = (0..s.fri_rounds())
            .map(|_| self.cap())
            .collect::<Result<_, _>>()?;
        let pow = (0..s.fri_rounds())
            .map(|_| self.val())
            .collect::<Result<_, _>>()?;
        let final_poly = self.exts(1 << profile.fri().1)?;
        let query_pow = self.val()?;
        if self.cursor - start != global_data_bytes(s.random_codewords) {
            return Err(StarkCodecError::Shape("global data bytes"));
        }
        Ok((
            GlobalData {
                commitments,
                opened,
                hiding,
                commits,
                pow,
                final_poly,
                query_pow,
            },
            &self.bytes[start..self.cursor],
        ))
    }
    fn checkpoint(&mut self, s: ProofShape) -> Result<TranscriptCheckpoint, StarkCodecError> {
        let digest = self.take()?;
        let global_digest = self.take()?;
        let state = Digest512::from_bytes(self.take()?);
        let air_alpha = self.ext()?;
        let zeta = self.ext()?;
        let fri_alpha = self.ext()?;
        let fri_betas = self.exts(s.fri_rounds())?;
        if self.u16()? as usize != s.query_count {
            return Err(StarkCodecError::QueryOrder);
        }
        let query_indices = (0..s.query_count)
            .map(|_| self.u32())
            .collect::<Result<Vec<_>, _>>()?;
        let n = self.u16()? as usize;
        if n > s.query_count {
            return Err(StarkCodecError::QueryOrder);
        }
        let unique_query_indices = (0..n).map(|_| self.u32()).collect::<Result<Vec<_>, _>>()?;
        if unique_query_indices != sorted_unique(&query_indices) {
            return Err(StarkCodecError::QueryOrder);
        }
        Ok(TranscriptCheckpoint {
            digest,
            global_digest,
            state,
            air_alpha,
            zeta,
            fri_alpha,
            fri_betas,
            query_indices,
            unique_query_indices,
        })
    }
    fn rows(
        &mut self,
        q: usize,
        m: usize,
        w: usize,
    ) -> Result<Vec<Vec<Vec<Val>>>, StarkCodecError> {
        (0..q)
            .map(|_| {
                (0..m)
                    .map(|_| (0..w).map(|_| self.val()).collect())
                    .collect()
            })
            .collect()
    }
    fn hashes(&mut self) -> Result<Vec<[u64; 8]>, StarkCodecError> {
        let n = self.u32()? as usize;
        if n > MAX_PATH_HASHES {
            return Err(StarkCodecError::Length);
        }
        (0..n).map(|_| self.digest()).collect()
    }
    fn half(&mut self, s: ProofShape, expected_start: usize) -> Result<QueryHalf, StarkCodecError> {
        let start = self.u16()? as usize;
        let q = self.u16()? as usize;
        if start != expected_start || q != s.query_count / 2 {
            return Err(StarkCodecError::QueryOrder);
        }
        let indices = (0..q).map(|_| self.u32()).collect::<Result<Vec<_>, _>>()?;
        let mut inputs = Vec::new();
        for batch in 0..3 {
            inputs.push(HalfInput {
                opened_values: self.rows(
                    q,
                    s.input_matrix_count(batch),
                    s.input_matrix_width(batch),
                )?,
                salts: self.rows(q, s.input_matrix_count(batch), MMCS_SALT_ELEMENTS)?,
                sibling_hashes: self.hashes()?,
            });
        }
        let mut fri_rounds = Vec::new();
        for _ in 0..s.fri_rounds() {
            let sibling_values = (0..q).map(|_| self.exts(1)).collect::<Result<_, _>>()?;
            fri_rounds.push(HalfFriRound {
                sibling_values,
                salts: self.rows(q, 1, 8)?,
                sibling_hashes: self.hashes()?,
            });
        }
        Ok(QueryHalf {
            start,
            indices,
            inputs,
            fri_rounds,
        })
    }
    fn finish(self) -> Result<(), StarkCodecError> {
        if self.cursor == self.bytes.len() {
            Ok(())
        } else {
            Err(StarkCodecError::TrailingBytes)
        }
    }
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum StarkCodecError {
    #[error("proof part is truncated")]
    Truncated,
    #[error("invalid proof part magic")]
    Magic,
    #[error("unsupported proof part version")]
    Version,
    #[error("security profile mismatch")]
    Profile,
    #[error("parameter ID mismatch")]
    ParameterId,
    #[error("public values mismatch")]
    PublicValues,
    #[error("parts are not bound to one proof")]
    CrossPartBinding,
    #[error("global proof data digest mismatch")]
    GlobalDigest,
    #[error("invalid transcript checkpoint")]
    TranscriptCheckpoint,
    #[error("noncanonical query order")]
    QueryOrder,
    #[error("invalid commitment grinding witness")]
    InvalidCommitPow,
    #[error("invalid query grinding witness")]
    InvalidQueryPow,
    #[error("invalid proof shape: {0}")]
    Shape(&'static str),
    #[error("field element {value} is noncanonical")]
    NonCanonicalField { value: u32 },
    #[error("proof component length is out of bounds")]
    Length,
    #[error("invalid part end marker")]
    EndMarker,
    #[error("trailing bytes")]
    TrailingBytes,
}

#[cfg(test)]
mod tests {
    use super::*;
    use pqtc_hash::{commitment, empty_leaf, merkle_node, nullifier_hash, p2bb512, payout_digest};
    use pqtc_spec::{CanonicalSecret, TREE_DEPTH, domains};
    use rand::{SeedableRng, rngs::StdRng};
    #[test]
    fn statement_key_matches_static_abi_shape() {
        let p = Digest512 {
            left: [1; 32],
            right: [2; 32],
        };
        let s = WithdrawalStatement {
            scope: Digest512::ZERO,
            root: Digest512::ZERO,
            nullifier_hash: Digest512::ZERO,
            payout_digest: Digest512::ZERO,
        };
        let mut abi = Vec::new();
        put_abi_word(&mut abi, STATEMENT_DOMAIN);
        abi.extend_from_slice(&p.left);
        abi.extend_from_slice(&p.right);
        for _ in 0..64 {
            abi.extend_from_slice(&[0; 32]);
        }
        assert_eq!(statement_key(p, s), keccak256(&abi));
    }
    #[test]
    fn malformed_field_rejected() {
        let bytes = BABY_BEAR_MODULUS.to_be_bytes();
        assert_eq!(
            Reader::new(&bytes).val(),
            Err(StarkCodecError::NonCanonicalField {
                value: BABY_BEAR_MODULUS
            })
        );
    }
    #[test]
    fn duplicate_queries_sort_and_dedup() {
        assert_eq!(sorted_unique(&[9, 2, 9, 4, 2]), vec![2, 4, 9]);
    }
    #[test]
    fn proof_id_binds_part_and_statement() {
        assert_ne!(
            derive_proof_id([1; 32], b"a"),
            derive_proof_id([1; 32], b"b")
        );
        assert_ne!(
            derive_proof_id([1; 32], b"a"),
            derive_proof_id([2; 32], b"a")
        );
    }

    fn canonical_limbs(value: u32) -> CanonicalSecret {
        CanonicalSecret::from_limbs([value; CanonicalSecret::LIMB_COUNT])
            .expect("small fixture limbs are canonical")
    }

    fn withdrawal_fixture() -> (WithdrawalStatement, crate::WithdrawalWitness) {
        let scope = p2bb512(domains::SCOPE, 0, 0, &[]);
        let secret = canonical_limbs(3);
        let trapdoor = canonical_limbs(4);
        let leaf = commitment(scope, secret, trapdoor);
        let mut zeros = [Digest512::ZERO; TREE_DEPTH as usize];
        zeros[0] = empty_leaf(scope);
        for level in 1..TREE_DEPTH as usize {
            zeros[level] = merkle_node((level - 1) as u8, zeros[level - 1], zeros[level - 1]);
        }
        let mut root = leaf;
        for (level, &sibling) in zeros.iter().enumerate() {
            root = merkle_node(level as u8, root, sibling);
        }
        (
            WithdrawalStatement {
                scope,
                root,
                nullifier_hash: nullifier_hash(scope, secret),
                payout_digest: payout_digest([5; 20], [6; 20], [0; 32]),
            },
            crate::WithdrawalWitness {
                nullifier_secret: secret,
                trapdoor,
                leaf_index: 0,
                path_bits: [0; TREE_DEPTH as usize],
                siblings: zeros,
            },
        )
    }

    #[test]
    fn production_shape_is_q32_split_16_with_v3_dimensions() {
        let shape = ProofShape::for_profile(SecurityProfile::SepoliaV03);
        assert_eq!(shape.query_count, PRODUCTION_QUERY_COUNT);
        assert_eq!(shape.query_count / 2, PRODUCTION_HALF_QUERY_COUNT);
        assert_eq!(shape.log_blowup, 4);
        assert_eq!(shape.random_codewords, 4);
        assert_eq!(shape.fri_rounds(), 9);
        assert_eq!(COMMON_HEADER_BYTES, 338);
        assert_eq!(profile_tag(SecurityProfile::SepoliaV03), 3);
        assert_eq!(GLOBAL_DATA_BYTES, 9_208);

        let mut header = Vec::new();
        put_header(
            &mut header,
            PROOF_PART_A_MAGIC,
            SecurityProfile::SepoliaV03,
            shape,
            Digest512::ZERO,
            WithdrawalStatement {
                scope: Digest512::ZERO,
                root: Digest512::ZERO,
                nullifier_hash: Digest512::ZERO,
                payout_digest: Digest512::ZERO,
            },
        )
        .unwrap();
        assert_eq!(header.len(), COMMON_HEADER_BYTES);
        assert_eq!(header[10], 3);
        assert_eq!(
            u16::from_be_bytes(header[14..16].try_into().unwrap()) as usize,
            PRODUCTION_QUERY_COUNT
        );
    }
    #[test]
    fn two_parts_round_trip_bind_and_verify_natively() {
        let (statement, witness) = withdrawal_fixture();
        let parameter_id = statement.scope;
        let public = crate::withdrawal_public_values(statement);
        let config = crate::build_config(
            SecurityProfile::Dev,
            parameter_id,
            &public,
            StdRng::seed_from_u64(1),
            StdRng::seed_from_u64(2),
        );
        let proof = crate::prove_withdrawal(&config, statement, &witness).expect("valid witness");
        let parts =
            encode_proof_parts(&proof, SecurityProfile::Dev, parameter_id, statement).unwrap();
        assert_eq!(&parts.part_a.bytes[..8], &PROOF_PART_A_MAGIC);
        assert_eq!(&parts.part_b.bytes[..8], &PROOF_PART_B_MAGIC);
        assert_eq!(
            u16::from_be_bytes(parts.part_a.bytes[8..10].try_into().unwrap()),
            PROOF_PART_VERSION
        );
        assert_eq!(parts.part_a.checkpoint.query_indices.len(), 2);
        let decoded = decode_proof_parts(
            &parts.part_a.bytes,
            &parts.part_b.bytes,
            SecurityProfile::Dev,
            parameter_id,
            statement,
        )
        .unwrap();
        assert!(crate::verify_withdrawal(&config, statement, &decoded));

        let mut wrong_b = parts.part_b.bytes.clone();
        wrong_b[COMMON_HEADER_BYTES] ^= 1;
        assert!(matches!(
            decode_proof_parts(
                &parts.part_a.bytes,
                &wrong_b,
                SecurityProfile::Dev,
                parameter_id,
                statement,
            ),
            Err(StarkCodecError::CrossPartBinding)
        ));

        let mut mutated_a = parts.part_a.bytes.clone();
        mutated_a[COMMON_HEADER_BYTES + 32] ^= 1;
        assert!(matches!(
            decode_proof_parts(
                &mutated_a,
                &parts.part_b.bytes,
                SecurityProfile::Dev,
                parameter_id,
                statement,
            ),
            Err(StarkCodecError::GlobalDigest)
        ));

        let truncated_b = &parts.part_b.bytes[..parts.part_b.bytes.len() - 1];
        assert!(matches!(
            decode_proof_parts(
                &parts.part_a.bytes,
                truncated_b,
                SecurityProfile::Dev,
                parameter_id,
                statement,
            ),
            Err(StarkCodecError::Truncated)
        ));

        let mut noncanonical_a = parts.part_a.bytes.clone();
        noncanonical_a[COMMON_HEADER_BYTES - PUBLIC_VALUES_COUNT * FIELD_BYTES
            ..COMMON_HEADER_BYTES - PUBLIC_VALUES_COUNT * FIELD_BYTES + FIELD_BYTES]
            .copy_from_slice(&BABY_BEAR_MODULUS.to_be_bytes());
        assert!(matches!(
            decode_proof_parts(
                &noncanonical_a,
                &parts.part_b.bytes,
                SecurityProfile::Dev,
                parameter_id,
                statement,
            ),
            Err(StarkCodecError::NonCanonicalField { .. })
        ));

        let mut trailing_b = parts.part_b.bytes.clone();
        trailing_b.push(0);
        assert!(matches!(
            decode_proof_parts(
                &parts.part_a.bytes,
                &trailing_b,
                SecurityProfile::Dev,
                parameter_id,
                statement,
            ),
            Err(StarkCodecError::TrailingBytes)
        ));
    }
}
```

</details>

## `crates/pqtc-stark/src/crypto.rs`

- Bytes: 9,976
- SHA-256: `4ca0894b4172e8b53d7efed35064426e99c5770cdd4f895dae8aa29ed312091a`

<details><summary>Complete file</summary>

```rust
use std::collections::VecDeque;

use p3_baby_bear::BabyBear;
use p3_challenger::{
    CanFinalizeDigest, CanObserve, CanSample, CanSampleBits, CanSampleUniformBits, FieldChallenger,
    GrindingChallenger, ResamplingError,
};
use p3_field::{BasedVectorSpace, PrimeCharacteristicRing, PrimeField32};
use p3_symmetric::{CryptographicHasher, MerkleCap, PseudoCompressionFunction};
use pqtc_hash::k512;
use pqtc_spec::{BABY_BEAR_MODULUS, Digest512, domains};

pub const DIGEST_WORDS: usize = 8;
const FIELD_ITEM: u8 = 1;
const COMMITMENT_ITEM: u8 = 2;

#[derive(Clone, Copy, Debug, Default)]
pub struct ProofLeafHasher;

impl CryptographicHasher<BabyBear, [u64; DIGEST_WORDS]> for ProofLeafHasher {
    fn hash_iter<I>(&self, input: I) -> [u64; DIGEST_WORDS]
    where
        I: IntoIterator<Item = BabyBear>,
    {
        let values: Vec<_> = input.into_iter().collect();
        digest_words(hash_leaf(values.iter().map(PrimeField32::as_canonical_u32)))
    }
}

impl<const N: usize> CryptographicHasher<[BabyBear; N], [[u64; N]; DIGEST_WORDS]>
    for ProofLeafHasher
{
    fn hash_iter<I>(&self, input: I) -> [[u64; N]; DIGEST_WORDS]
    where
        I: IntoIterator<Item = [BabyBear; N]>,
    {
        let values: Vec<_> = input.into_iter().collect();
        let lane_digests: [[u64; DIGEST_WORDS]; N] = core::array::from_fn(|lane| {
            digest_words(hash_leaf(
                values.iter().map(|packed| packed[lane].as_canonical_u32()),
            ))
        });
        core::array::from_fn(|word| core::array::from_fn(|lane| lane_digests[lane][word]))
    }
}

fn hash_leaf(values: impl IntoIterator<Item = u32>) -> Digest512 {
    let fields: Vec<u32> = values.into_iter().collect();
    let byte_len = u32::try_from(
        fields
            .len()
            .checked_mul(4)
            .expect("leaf byte length overflow"),
    )
    .expect("leaf byte length exceeds u32");
    let mut payload = Vec::with_capacity(4 + byte_len as usize);
    payload.extend_from_slice(&byte_len.to_be_bytes());
    for value in fields {
        payload.extend_from_slice(&value.to_be_bytes());
    }
    k512(domains::PROOF_LEAF, &payload)
}
#[must_use]
pub fn proof_leaf_digest(values: &[u32]) -> Digest512 {
    hash_leaf(values.iter().copied())
}

#[derive(Clone, Copy, Debug, Default)]
pub struct ProofNodeCompressor;

impl PseudoCompressionFunction<[u64; DIGEST_WORDS], 2> for ProofNodeCompressor {
    fn compress(&self, input: [[u64; DIGEST_WORDS]; 2]) -> [u64; DIGEST_WORDS] {
        digest_words(hash_node(input.map(words_digest)))
    }
}

impl<const N: usize> PseudoCompressionFunction<[[u64; N]; DIGEST_WORDS], 2>
    for ProofNodeCompressor
{
    fn compress(&self, input: [[[u64; N]; DIGEST_WORDS]; 2]) -> [[u64; N]; DIGEST_WORDS] {
        let lane_digests: [[u64; DIGEST_WORDS]; N] = core::array::from_fn(|lane| {
            let children = core::array::from_fn(|child| {
                words_digest(core::array::from_fn(|word| input[child][word][lane]))
            });
            digest_words(hash_node(children))
        });
        core::array::from_fn(|word| core::array::from_fn(|lane| lane_digests[lane][word]))
    }
}

fn hash_node(children: [Digest512; 2]) -> Digest512 {
    let mut payload = [0u8; 128];
    payload[..64].copy_from_slice(&children[0].to_bytes());
    payload[64..].copy_from_slice(&children[1].to_bytes());
    k512(domains::PROOF_NODE, &payload)
}
#[must_use]
pub fn proof_node_digest(left: Digest512, right: Digest512) -> Digest512 {
    hash_node([left, right])
}

#[must_use]
pub fn digest_words(digest: Digest512) -> [u64; DIGEST_WORDS] {
    let bytes = digest.to_bytes();
    core::array::from_fn(|i| {
        u64::from_be_bytes(bytes[i * 8..i * 8 + 8].try_into().expect("word range"))
    })
}

#[must_use]
pub fn words_digest(words: [u64; DIGEST_WORDS]) -> Digest512 {
    let mut bytes = [0u8; 64];
    for (chunk, word) in bytes.chunks_exact_mut(8).zip(words) {
        chunk.copy_from_slice(&word.to_be_bytes());
    }
    Digest512::from_bytes(bytes)
}

/// Explicit 512-bit, typed, length-delimited Fiat-Shamir transcript.
#[derive(Clone, Debug)]
pub struct Transcript512 {
    state: Digest512,
    output: VecDeque<u8>,
    squeeze_counter: u64,
}

impl Transcript512 {
    #[must_use]
    pub fn new(parameter_id: Digest512, public_values: &[BabyBear]) -> Self {
        let mut payload = Vec::with_capacity(64 + public_values.len() * 4);
        payload.extend_from_slice(&parameter_id.to_bytes());
        for value in public_values {
            payload.extend_from_slice(&value.as_canonical_u32().to_be_bytes());
        }
        Self {
            state: k512(domains::TRANSCRIPT_INIT, &payload),
            output: VecDeque::new(),
            squeeze_counter: 0,
        }
    }

    fn absorb(&mut self, item_type: u8, bytes: &[u8]) {
        let len = u32::try_from(bytes.len()).expect("transcript item exceeds u32");
        let mut payload = Vec::with_capacity(64 + 1 + 4 + bytes.len());
        payload.extend_from_slice(&self.state.to_bytes());
        payload.push(item_type);
        payload.extend_from_slice(&len.to_be_bytes());
        payload.extend_from_slice(bytes);
        self.state = k512(domains::TRANSCRIPT_ABSORB, &payload);
        self.output.clear();
        self.squeeze_counter = 0;
    }

    fn sample_byte(&mut self) -> u8 {
        if self.output.is_empty() {
            let mut payload = [0u8; 72];
            payload[..64].copy_from_slice(&self.state.to_bytes());
            payload[64..].copy_from_slice(&self.squeeze_counter.to_be_bytes());
            self.squeeze_counter = self
                .squeeze_counter
                .checked_add(1)
                .expect("squeeze counter overflow");
            self.output
                .extend(k512(domains::TRANSCRIPT_SQUEEZE, &payload).to_bytes());
        }
        self.output.pop_front().expect("squeeze fills output")
    }

    #[must_use]
    pub const fn state(&self) -> Digest512 {
        self.state
    }
}

impl CanObserve<BabyBear> for Transcript512 {
    fn observe(&mut self, value: BabyBear) {
        self.absorb(FIELD_ITEM, &value.as_canonical_u32().to_be_bytes());
    }
}

impl CanObserve<MerkleCap<BabyBear, [u64; DIGEST_WORDS]>> for Transcript512 {
    fn observe(&mut self, cap: MerkleCap<BabyBear, [u64; DIGEST_WORDS]>) {
        self.observe(&cap);
    }
}

impl CanObserve<&MerkleCap<BabyBear, [u64; DIGEST_WORDS]>> for Transcript512 {
    fn observe(&mut self, cap: &MerkleCap<BabyBear, [u64; DIGEST_WORDS]>) {
        let mut bytes = Vec::with_capacity(cap.roots().len() * 64);
        for root in cap.roots() {
            for word in root {
                bytes.extend_from_slice(&word.to_be_bytes());
            }
        }
        self.absorb(COMMITMENT_ITEM, &bytes);
    }
}

impl<EF: BasedVectorSpace<BabyBear>> CanSample<EF> for Transcript512 {
    fn sample(&mut self) -> EF {
        EF::from_basis_coefficients_fn(|_| {
            loop {
                let value =
                    u32::from_be_bytes(core::array::from_fn(|_| self.sample_byte())) & 0x7fff_ffff;
                if value < BABY_BEAR_MODULUS {
                    return BabyBear::new(value);
                }
            }
        })
    }
}

impl CanSampleBits<usize> for Transcript512 {
    fn sample_bits(&mut self, bits: usize) -> usize {
        assert!(bits < usize::BITS as usize);
        assert!(bits <= 31);
        let value = u32::from_be_bytes(core::array::from_fn(|_| self.sample_byte())) as usize;
        value & ((1usize << bits) - 1)
    }
}

impl CanSampleUniformBits<BabyBear> for Transcript512 {
    fn sample_uniform_bits<const RESAMPLE: bool>(
        &mut self,
        bits: usize,
    ) -> Result<usize, ResamplingError> {
        Ok(self.sample_bits(bits))
    }
}

impl GrindingChallenger for Transcript512 {
    type Witness = BabyBear;

    fn grind(&mut self, bits: usize) -> Self::Witness {
        if bits == 0 {
            return BabyBear::ZERO;
        }
        let initial = self.clone();
        for value in 0..BABY_BEAR_MODULUS {
            let witness = BabyBear::new(value);
            let mut trial = initial.clone();
            if trial.check_witness(bits, witness) {
                *self = trial;
                return witness;
            }
        }
        panic!("no grinding witness found")
    }
}

impl FieldChallenger<BabyBear> for Transcript512 {}

impl CanFinalizeDigest for Transcript512 {
    type Digest = [u8; 64];
    fn finalize(self) -> Self::Digest {
        self.state.to_bytes()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use p3_challenger::{CanObserve, CanSample};

    #[test]
    fn transcript_is_typed_and_deterministic() {
        let mut a = Transcript512::new(Digest512::ZERO, &[]);
        let mut b = a.clone();
        a.observe(BabyBear::new(1));
        b.observe(BabyBear::new(1));
        assert_eq!(a.state(), b.state());
        let ca: BabyBear = a.sample();
        let cb: BabyBear = b.sample();
        assert_eq!(ca, cb);
    }
    #[test]
    fn grinding_matches_single_witness_verification() {
        let mut prover = Transcript512::new(Digest512::ZERO, &[]);
        prover.observe(BabyBear::new(7));
        let mut verifier = prover.clone();
        let witness = prover.grind(8);
        assert!(verifier.check_witness(8, witness));
        let prover_sample: BabyBear = prover.sample();
        let verifier_sample: BabyBear = verifier.sample();
        assert_eq!(prover_sample, verifier_sample);
    }

    #[test]
    fn digest_halves_both_affect_nodes() {
        let a = digest_words(Digest512 {
            left: [1; 32],
            right: [2; 32],
        });
        let b = digest_words(Digest512 {
            left: [3; 32],
            right: [4; 32],
        });
        let baseline = ProofNodeCompressor.compress([a, b]);
        let mut changed = a;
        changed[7] ^= 1;
        assert_ne!(baseline, ProofNodeCompressor.compress([changed, b]));
    }
}
```

</details>

## `crates/pqtc-stark/src/lib.rs`

- Bytes: 4,465
- SHA-256: `eb0166dccf6fe1e8cdcd59f8a94dcfda058dbc4fd73bf5f7925b160c66d6b967`

<details><summary>Complete file</summary>

```rust
//! Hiding two-adic FRI proving for the Poseidon2 withdrawal AIR.

pub mod codec;
pub mod crypto;
mod query;

use p3_baby_bear::BabyBear;
use p3_commit::ExtensionMmcs;
use p3_dft::Radix2DitParallel;
use p3_field::extension::BinomialExtensionField;
use p3_fri::{FriParameters, HidingFriPcs};
use p3_merkle_tree::MerkleTreeHidingMmcs;
use p3_uni_stark::{Proof, StarkConfig, prove, verify};
pub use pqtc_poseidon_air::{RelationError, WithdrawalWitness};
use pqtc_poseidon_air::{WithdrawalAir, generate_withdrawal_trace, public_values};
use pqtc_spec::{Digest512, WithdrawalStatement};
use rand::{SeedableRng, rngs::StdRng};

use crate::crypto::{DIGEST_WORDS, ProofLeafHasher, ProofNodeCompressor, Transcript512};

pub type Val = BabyBear;
pub type Challenge = BinomialExtensionField<Val, 4>;
type Packing = [Val; p3_keccak::VECTOR_LEN];
type DigestPacking = [u64; p3_keccak::VECTOR_LEN];
pub type ValMmcs = MerkleTreeHidingMmcs<
    Packing,
    DigestPacking,
    ProofLeafHasher,
    ProofNodeCompressor,
    StdRng,
    2,
    DIGEST_WORDS,
    8,
>;
pub type ChallengeMmcs = ExtensionMmcs<Val, Challenge, ValMmcs>;
pub type Dft = Radix2DitParallel<Val>;
pub type Pcs = HidingFriPcs<Val, Dft, ValMmcs, ChallengeMmcs, StdRng>;
pub type Config = StarkConfig<Pcs, Challenge, Transcript512>;
pub type StarkProof = Proof<Config>;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SecurityProfile {
    Dev,
    Ci,
    SepoliaV03,
}

impl SecurityProfile {
    #[must_use]
    pub const fn fri(self) -> (usize, usize, usize, usize, usize) {
        match self {
            Self::Dev => (3, 0, 2, 0, 0),
            Self::Ci => (3, 0, 16, 4, 4),
            Self::SepoliaV03 => (4, 0, 32, 16, 16),
        }
    }

    #[must_use]
    pub const fn random_codewords(self) -> usize {
        match self {
            Self::Dev => 2,
            Self::Ci | Self::SepoliaV03 => 4,
        }
    }
}

/// Constructs a proving or verification configuration from operating-system entropy.
/// No deterministic seed is exposed by the production API.
#[must_use]
pub fn config_from_os_entropy(
    profile: SecurityProfile,
    parameter_id: Digest512,
    public_values: &[Val],
) -> Config {
    let mut os_rng = rand::rng();
    let mmcs_rng = StdRng::from_rng(&mut os_rng);
    let pcs_rng = StdRng::from_rng(&mut os_rng);
    build_config(profile, parameter_id, public_values, mmcs_rng, pcs_rng)
}

fn build_config(
    profile: SecurityProfile,
    parameter_id: Digest512,
    public_values: &[Val],
    mmcs_rng: StdRng,
    pcs_rng: StdRng,
) -> Config {
    let leaf_hash = ProofLeafHasher;
    let compress = ProofNodeCompressor;
    let val_mmcs = ValMmcs::new(leaf_hash, compress, 0, mmcs_rng);
    let challenge_mmcs = ChallengeMmcs::new(val_mmcs.clone());
    let dft = Dft::default();
    let (log_blowup, log_final_poly_len, num_queries, commit_pow, query_pow) = profile.fri();
    let fri_params = FriParameters {
        log_blowup,
        log_final_poly_len,
        max_log_arity: 1,
        num_queries,
        commit_proof_of_work_bits: commit_pow,
        query_proof_of_work_bits: query_pow,
        mmcs: challenge_mmcs,
    };
    let pcs = Pcs::new(
        dft,
        val_mmcs,
        fri_params,
        profile.random_codewords(),
        pcs_rng,
    );
    let challenger = Transcript512::new(parameter_id, public_values);
    Config::new(pcs, challenger)
}
#[must_use]
pub fn withdrawal_public_values(
    statement: WithdrawalStatement,
) -> [Val; pqtc_spec::PUBLIC_VALUES_COUNT] {
    public_values(statement)
}

#[must_use]
pub fn withdrawal_config_from_os_entropy(
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
) -> Config {
    config_from_os_entropy(profile, parameter_id, &withdrawal_public_values(statement))
}

pub fn prove_withdrawal(
    config: &Config,
    statement: WithdrawalStatement,
    witness: &WithdrawalWitness,
) -> Result<StarkProof, RelationError> {
    let trace = generate_withdrawal_trace(statement, witness)?;
    let public_values = withdrawal_public_values(statement);
    Ok(prove(
        config,
        &WithdrawalAir::default(),
        trace,
        &public_values,
    ))
}

#[must_use]
pub fn verify_withdrawal(
    config: &Config,
    statement: WithdrawalStatement,
    proof: &StarkProof,
) -> bool {
    let public_values = withdrawal_public_values(statement);
    verify(config, &WithdrawalAir::default(), proof, &public_values).is_ok()
}
```

</details>

## `crates/pqtc-stark/src/query.rs`

- Bytes: 19,575
- SHA-256: `feb1b778459660babee3a199cab968f6403874df0a97d1a524baee5f3c8640a2`

<details><summary>Complete file</summary>

```rust
use std::collections::{BTreeMap, BTreeSet};

use p3_field::{BasedVectorSpace, Field, PrimeCharacteristicRing, PrimeField32, TwoAdicField};
use p3_fri::{BatchMultiOpening, CommitPhaseMultiStep};
use p3_merkle_tree::PrunedMerklePaths;
use p3_symmetric::MerkleCap;
use pqtc_spec::Digest512;

use crate::codec::{ProofShape, StarkCodecError, TranscriptCheckpoint};
use crate::crypto::{digest_words, proof_leaf_digest, proof_node_digest, words_digest};
use crate::{Challenge, StarkProof, Val};

#[derive(Clone)]
pub(crate) struct QueryHalf {
    pub start: usize,
    pub indices: Vec<u32>,
    pub inputs: Vec<HalfInput>,
    pub fri_rounds: Vec<HalfFriRound>,
}
#[derive(Clone)]
pub(crate) struct HalfInput {
    pub opened_values: Vec<Vec<Vec<Val>>>,
    pub salts: Vec<Vec<Vec<Val>>>,
    pub sibling_hashes: Vec<[u64; 8]>,
}
#[derive(Clone)]
pub(crate) struct HalfFriRound {
    pub sibling_values: Vec<Vec<Challenge>>,
    pub salts: Vec<Vec<Vec<Val>>>,
    pub sibling_hashes: Vec<[u64; 8]>,
}

pub(crate) fn split_queries(
    proof: &StarkProof,
    shape: ProofShape,
    cp: &TranscriptCheckpoint,
) -> Result<[QueryHalf; 2], StarkCodecError> {
    let count = cp.query_indices.len();
    let split = count / 2;
    if split == 0 || split * 2 != count {
        return Err(StarkCodecError::Shape("query halves"));
    }
    let log_height = proof.degree_bits + shape.log_blowup;
    let roots = input_roots(proof)?;
    let mut input_paths = Vec::with_capacity(3);
    for (opening, root) in proof.opening_proof.1.input_openings.iter().zip(roots) {
        input_paths.push(expand_paths(
            &cp.query_indices,
            &input_leaves(&opening.opened_values, &opening.opening_proof.0)?,
            &opening.opening_proof.1,
            log_height,
            commitment_root(root)?,
        )?);
    }
    let (round_indices, round_leaves) = fri_round_leaves(proof, shape, cp)?;
    let mut fri_paths = Vec::with_capacity(shape.fri_rounds());
    for round in 0..shape.fri_rounds() {
        fri_paths.push(expand_paths(
            &round_indices[round],
            &round_leaves[round],
            &proof.opening_proof.1.commit_phase_openings[round]
                .opening_proof
                .1,
            log_height - round - 1,
            commitment_root(&proof.opening_proof.1.commit_phase_commits[round])?,
        )?);
    }
    let build = |start: usize, end: usize| -> Result<QueryHalf, StarkCodecError> {
        let qs: Vec<usize> = (start..end).collect();
        let mut inputs = Vec::with_capacity(3);
        for (batch, opening) in proof.opening_proof.1.input_openings.iter().enumerate() {
            inputs.push(HalfInput {
                opened_values: qs
                    .iter()
                    .map(|&q| opening.opened_values[q].clone())
                    .collect(),
                salts: qs
                    .iter()
                    .map(|&q| opening.opening_proof.0[q].clone())
                    .collect(),
                sibling_hashes: prune_paths(
                    &qs.iter().map(|&q| cp.query_indices[q]).collect::<Vec<_>>(),
                    &qs.iter()
                        .map(|&q| input_paths[batch][q].clone())
                        .collect::<Vec<_>>(),
                )?,
            });
        }
        let mut fri_rounds = Vec::with_capacity(shape.fri_rounds());
        for round in 0..shape.fri_rounds() {
            let opening = &proof.opening_proof.1.commit_phase_openings[round];
            fri_rounds.push(HalfFriRound {
                sibling_values: qs
                    .iter()
                    .map(|&q| opening.sibling_values[q].clone())
                    .collect(),
                salts: qs
                    .iter()
                    .map(|&q| opening.opening_proof.0[q].clone())
                    .collect(),
                sibling_hashes: prune_paths(
                    &qs.iter()
                        .map(|&q| round_indices[round][q])
                        .collect::<Vec<_>>(),
                    &qs.iter()
                        .map(|&q| fri_paths[round][q].clone())
                        .collect::<Vec<_>>(),
                )?,
            });
        }
        Ok(QueryHalf {
            start,
            indices: cp.query_indices[start..end].to_vec(),
            inputs,
            fri_rounds,
        })
    };
    Ok([build(0, split)?, build(split, count)?])
}

pub(crate) fn merge_queries(
    proof: &mut StarkProof,
    shape: ProofShape,
    cp: &TranscriptCheckpoint,
    halves: [QueryHalf; 2],
) -> Result<(), StarkCodecError> {
    let split = shape.query_count / 2;
    if halves[0].start != 0
        || halves[1].start != split
        || halves[0].indices != cp.query_indices[..split]
        || halves[1].indices != cp.query_indices[split..]
    {
        return Err(StarkCodecError::QueryOrder);
    }
    let log_height = proof.degree_bits + shape.log_blowup;
    let roots = input_roots(proof)?;
    let mut inputs = Vec::with_capacity(3);
    for batch in 0..3 {
        let mut values = halves[0].inputs[batch].opened_values.clone();
        values.extend_from_slice(&halves[1].inputs[batch].opened_values);
        let mut salts = halves[0].inputs[batch].salts.clone();
        salts.extend_from_slice(&halves[1].inputs[batch].salts);
        let mut paths = Vec::with_capacity(shape.query_count);
        for half in &halves {
            paths.extend(expand_paths(
                &half.indices,
                &input_leaves(&half.inputs[batch].opened_values, &half.inputs[batch].salts)?,
                &PrunedMerklePaths {
                    sibling_hashes: half.inputs[batch].sibling_hashes.clone(),
                },
                log_height,
                commitment_root(roots[batch])?,
            )?);
        }
        inputs.push(BatchMultiOpening {
            opened_values: values,
            opening_proof: (
                salts,
                PrunedMerklePaths {
                    sibling_hashes: prune_paths(&cp.query_indices, &paths)?,
                },
            ),
        });
    }
    proof.opening_proof.1.input_openings = inputs;
    let skeleton = (0..shape.fri_rounds())
        .map(|round| {
            let mut values = halves[0].fri_rounds[round].sibling_values.clone();
            values.extend_from_slice(&halves[1].fri_rounds[round].sibling_values);
            let mut salts = halves[0].fri_rounds[round].salts.clone();
            salts.extend_from_slice(&halves[1].fri_rounds[round].salts);
            CommitPhaseMultiStep {
                log_arity: 1,
                sibling_values: values,
                opening_proof: (
                    salts,
                    PrunedMerklePaths {
                        sibling_hashes: Vec::new(),
                    },
                ),
            }
        })
        .collect();
    proof.opening_proof.1.commit_phase_openings = skeleton;
    let (round_indices, round_leaves) = fri_round_leaves(proof, shape, cp)?;
    let mut rounds = Vec::with_capacity(shape.fri_rounds());
    for round in 0..shape.fri_rounds() {
        let mut values = halves[0].fri_rounds[round].sibling_values.clone();
        values.extend_from_slice(&halves[1].fri_rounds[round].sibling_values);
        let mut salts = halves[0].fri_rounds[round].salts.clone();
        salts.extend_from_slice(&halves[1].fri_rounds[round].salts);
        let mut paths = Vec::with_capacity(shape.query_count);
        for (half_no, half) in halves.iter().enumerate() {
            let range = if half_no == 0 {
                0..split
            } else {
                split..shape.query_count
            };
            paths.extend(expand_paths(
                &round_indices[round][range.clone()],
                &round_leaves[round][range],
                &PrunedMerklePaths {
                    sibling_hashes: half.fri_rounds[round].sibling_hashes.clone(),
                },
                log_height - round - 1,
                commitment_root(&proof.opening_proof.1.commit_phase_commits[round])?,
            )?);
        }
        rounds.push(CommitPhaseMultiStep {
            log_arity: 1,
            sibling_values: values,
            opening_proof: (
                salts,
                PrunedMerklePaths {
                    sibling_hashes: prune_paths(&round_indices[round], &paths)?,
                },
            ),
        });
    }
    proof.opening_proof.1.commit_phase_openings = rounds;
    Ok(())
}

fn input_roots(proof: &StarkProof) -> Result<[&MerkleCap<Val, [u64; 8]>; 3], StarkCodecError> {
    Ok([
        proof
            .commitments
            .random
            .as_ref()
            .ok_or(StarkCodecError::Shape("random commitment"))?,
        &proof.commitments.trace,
        &proof.commitments.quotient_chunks,
    ])
}
fn input_leaves(
    values: &[Vec<Vec<Val>>],
    salts: &[Vec<Vec<Val>>],
) -> Result<Vec<Digest512>, StarkCodecError> {
    if values.len() != salts.len() {
        return Err(StarkCodecError::Shape("input salts"));
    }
    values
        .iter()
        .zip(salts)
        .map(|(rows, ss)| {
            if rows.len() != ss.len() {
                return Err(StarkCodecError::Shape("input salts"));
            }
            let mut leaf = Vec::new();
            for (row, salt) in rows.iter().zip(ss) {
                leaf.extend(row.iter().map(PrimeField32::as_canonical_u32));
                leaf.extend(salt.iter().map(PrimeField32::as_canonical_u32));
            }
            Ok(proof_leaf_digest(&leaf))
        })
        .collect()
}
fn fri_round_leaves(
    proof: &StarkProof,
    shape: ProofShape,
    cp: &TranscriptCheckpoint,
) -> Result<(Vec<Vec<u32>>, Vec<Vec<Digest512>>), StarkCodecError> {
    let log_height = proof.degree_bits + shape.log_blowup;
    let reduced = reduced_openings(proof, cp, log_height)?;
    let mut indices = vec![vec![0; shape.query_count]; shape.fri_rounds()];
    let mut leaves = vec![Vec::with_capacity(shape.query_count); shape.fri_rounds()];
    for query in 0..shape.query_count {
        let mut folded = reduced[query];
        let mut index = cp.query_indices[query] as usize;
        for round in 0..shape.fri_rounds() {
            let sibling =
                proof.opening_proof.1.commit_phase_openings[round].sibling_values[query][0];
            let (low, high) = if index & 1 == 0 {
                (folded, sibling)
            } else {
                (sibling, folded)
            };
            let salt = &proof.opening_proof.1.commit_phase_openings[round]
                .opening_proof
                .0[query][0];
            let mut leaf = Vec::with_capacity(16);
            leaf.extend(ext_fields(low));
            leaf.extend(ext_fields(high));
            leaf.extend(salt.iter().map(PrimeField32::as_canonical_u32));
            index >>= 1;
            indices[round][query] = index as u32;
            leaves[round].push(proof_leaf_digest(&leaf));
            folded = fold_binary(
                index,
                log_height - round - 1,
                cp.fri_betas[round],
                low,
                high,
            );
        }
        if folded != proof.opening_proof.1.final_poly[0] {
            return Err(StarkCodecError::Shape("FRI final polynomial"));
        }
    }
    Ok((indices, leaves))
}
fn reduced_openings(
    proof: &StarkProof,
    cp: &TranscriptCheckpoint,
    log_height: usize,
) -> Result<Vec<Challenge>, StarkCodecError> {
    let hiding = &proof.opening_proof.0;
    let zeta_next = cp.zeta * Val::two_adic_generator(proof.degree_bits - 1);
    let mut result = Vec::with_capacity(cp.query_indices.len());
    for (query, &index) in cp.query_indices.iter().enumerate() {
        let x = Val::GENERATOR
            * Val::two_adic_generator(log_height)
                .exp_u64(reverse_bits(index as usize, log_height) as u64);
        let mut power = Challenge::ONE;
        let mut reduced = Challenge::ZERO;
        for batch in 0..3 {
            let matrices = if batch == 2 { 16 } else { 1 };
            for matrix in 0..matrices {
                let points = if batch == 0 {
                    vec![(
                        cp.zeta,
                        with_hidden(
                            proof
                                .opened_values
                                .random
                                .as_ref()
                                .ok_or(StarkCodecError::Shape("random opening"))?,
                            &hiding[0][0][0],
                        ),
                    )]
                } else if batch == 1 {
                    vec![
                        (
                            cp.zeta,
                            with_hidden(&proof.opened_values.trace_local, &hiding[1][0][0]),
                        ),
                        (
                            zeta_next,
                            with_hidden(
                                proof
                                    .opened_values
                                    .trace_next
                                    .as_ref()
                                    .ok_or(StarkCodecError::Shape("trace next"))?,
                                &hiding[1][0][1],
                            ),
                        ),
                    ]
                } else {
                    vec![(
                        cp.zeta,
                        with_hidden(
                            &proof.opened_values.quotient_chunks[matrix],
                            &hiding[2][matrix][0],
                        ),
                    )]
                };
                let row = &proof.opening_proof.1.input_openings[batch].opened_values[query][matrix];
                for (point, at_point) in points {
                    if row.len() != at_point.len() {
                        return Err(StarkCodecError::Shape("reduced opening"));
                    }
                    let inverse = (point - x).inverse();
                    for (&at_x, at_z) in row.iter().zip(at_point) {
                        reduced += power * (at_z - at_x) * inverse;
                        power *= cp.fri_alpha;
                    }
                }
            }
        }
        result.push(reduced);
    }
    Ok(result)
}
fn with_hidden(public: &[Challenge], hidden: &[Challenge]) -> Vec<Challenge> {
    public.iter().chain(hidden).copied().collect()
}
fn ext_fields(value: Challenge) -> impl Iterator<Item = u32> {
    let coefficients: &[Val] = value.as_basis_coefficients_slice();
    coefficients
        .iter()
        .map(PrimeField32::as_canonical_u32)
        .collect::<Vec<_>>()
        .into_iter()
}
fn fold_binary(
    index: usize,
    log_height: usize,
    beta: Challenge,
    low: Challenge,
    high: Challenge,
) -> Challenge {
    let x = Val::two_adic_generator(log_height + 1).exp_u64(reverse_bits(index, log_height) as u64);
    let inv = Val::TWO.inverse() * x.inverse();
    (low + high) * Val::TWO.inverse() + (low - high) * inv * beta
}
fn reverse_bits(value: usize, bits: usize) -> usize {
    (0..bits).fold(0, |out, bit| (out << 1) | ((value >> bit) & 1))
}
fn commitment_root(cap: &MerkleCap<Val, [u64; 8]>) -> Result<Digest512, StarkCodecError> {
    cap.roots()
        .first()
        .copied()
        .map(words_digest)
        .ok_or(StarkCodecError::Shape("Merkle root"))
}
fn expand_paths(
    indices: &[u32],
    leaves: &[Digest512],
    pruned: &PrunedMerklePaths<u64, 8>,
    height: usize,
    root: Digest512,
) -> Result<Vec<Vec<Digest512>>, StarkCodecError> {
    if indices.len() != leaves.len() {
        return Err(StarkCodecError::Shape("multiproof leaves"));
    }
    let mut nodes = BTreeMap::new();
    for (&index, &leaf) in indices.iter().zip(leaves) {
        if let Some(old) = nodes.insert(index as usize, leaf)
            && old != leaf
        {
            return Err(StarkCodecError::Shape("duplicate query opening"));
        }
    }
    let unique: Vec<usize> = nodes.keys().copied().collect();
    let mut paths: BTreeMap<usize, Vec<Digest512>> = unique
        .iter()
        .map(|&i| (i, Vec::with_capacity(height)))
        .collect();
    let mut cursor = 0;
    for level in 0..height {
        let groups: Vec<usize> = nodes
            .keys()
            .map(|i| i >> 1)
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        let mut complete = nodes.clone();
        for &group in &groups {
            for child in [group << 1, (group << 1) | 1] {
                if let std::collections::btree_map::Entry::Vacant(entry) = complete.entry(child) {
                    let sibling = pruned
                        .sibling_hashes
                        .get(cursor)
                        .copied()
                        .ok_or(StarkCodecError::Shape("pruned multiproof"))?;
                    cursor += 1;
                    entry.insert(words_digest(sibling));
                }
            }
        }
        for &leaf in &unique {
            paths
                .get_mut(&leaf)
                .expect("known leaf")
                .push(complete[&((leaf >> level) ^ 1)]);
        }
        nodes = groups
            .into_iter()
            .map(|group| {
                (
                    group,
                    proof_node_digest(complete[&(group << 1)], complete[&((group << 1) | 1)]),
                )
            })
            .collect();
    }
    if cursor != pruned.sibling_hashes.len()
        || nodes.len() != 1
        || nodes.values().next().copied() != Some(root)
    {
        return Err(StarkCodecError::Shape("pruned multiproof root"));
    }
    Ok(indices
        .iter()
        .map(|i| paths[&(*i as usize)].clone())
        .collect())
}
fn prune_paths(
    indices: &[u32],
    paths: &[Vec<Digest512>],
) -> Result<Vec<[u64; 8]>, StarkCodecError> {
    if indices.len() != paths.len() {
        return Err(StarkCodecError::Shape("multiproof paths"));
    }
    let mut nodes = BTreeMap::<usize, usize>::new();
    for (slot, &index) in indices.iter().enumerate() {
        if let Some(&old) = nodes.get(&(index as usize)) {
            if paths[old] != paths[slot] {
                return Err(StarkCodecError::Shape("duplicate query path"));
            }
        } else {
            nodes.insert(index as usize, slot);
        }
    }
    let height = paths.first().map_or(0, Vec::len);
    if paths.iter().any(|p| p.len() != height) {
        return Err(StarkCodecError::Shape("multiproof path height"));
    }
    let mut out = Vec::new();
    for level in 0..height {
        let groups: Vec<usize> = nodes
            .keys()
            .map(|i| i >> 1)
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        for &group in &groups {
            match (nodes.get(&(group << 1)), nodes.get(&((group << 1) | 1))) {
                (Some(&slot), None) | (None, Some(&slot)) => {
                    out.push(digest_words(paths[slot][level]))
                }
                (Some(_), Some(_)) => {}
                (None, None) => unreachable!(),
            }
        }
        nodes = groups
            .into_iter()
            .map(|group| {
                let slot = nodes
                    .get(&(group << 1))
                    .or_else(|| nodes.get(&((group << 1) | 1)))
                    .copied()
                    .expect("group member");
                (group, slot)
            })
            .collect();
    }
    Ok(out)
}
```

</details>

## `packages/sdk/package.json`

- Bytes: 768
- SHA-256: `2fcc6919b555985d6405b809f6fc128ca5c2bf521a677b5bcb395c4d87e2a4bd`

<details><summary>Complete file</summary>

```json
{
  "name": "@pqtc/sdk",
  "version": "0.3.0",
  "private": true,
  "type": "module",
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "import": "./dist/index.js"
    },
    "./relayer": {
      "types": "./dist/relayer.d.ts",
      "import": "./dist/relayer.js"
    },
    "./domains": {
      "types": "./dist/domains.d.ts",
      "import": "./dist/domains.js"
    }
  },
  "types": "./dist/index.d.ts",
  "bin": {
    "pqtc-relayer": "./dist/relayer.js"
  },
  "scripts": {
    "build": "tsc -p tsconfig.json",
    "test": "pnpm build && node --test test/*.test.ts",
    "relay": "node dist/relayer.js"
  },
  "dependencies": {
    "@noble/hashes": "2.0.1"
  },
  "devDependencies": {
    "@types/node": "24.7.2",
    "typescript": "5.9.3"
  }
}
```

</details>

## `packages/sdk/src/domains.ts`

- Bytes: 1,461
- SHA-256: `291575c9a6389628f9187c49bc1d9f350788ad9943132327e98ade2bdc0a5db0`

<details><summary>Complete file</summary>

```typescript
/** Poseidon2/BabyBear domains for protocol-v3 application statements. */
export const applicationDomains = Object.freeze({
  SCOPE: 0x10,
  NOTE: 0x11,
  NULLIFIER: 0x12,
  EMPTY_LEAF: 0x13,
  PAYOUT: 0x14,
  STATEMENT: 0x15,
  APP_MERKLE_NODE: 0x20,
} as const);

/** KeccakPair512 domains retained only by the proof system and parameter manifest. */
export const proofDomains = Object.freeze({
  PROOF_LEAF: 0x40,
  PROOF_NODE: 0x41,
  TRANSCRIPT_INIT: 0x42,
  TRANSCRIPT_ABSORB: 0x43,
  TRANSCRIPT_SQUEEZE: 0x44,
  PARAMETER_MANIFEST: 0x45,
} as const);

/** Keccak coordination labels for the v3 two-part proof protocol. */
export const coordinationDomains = Object.freeze({
  STATEMENT: "PQTC.V3.STATEMENT",
  PROOF: "PQTC.V3.PROOF",
  CHECKPOINT: "PQTC.V3.CHECKPOINT",
  VERIFICATION: "PQTC.V3.VERIFICATION",
} as const);

export const domains = Object.freeze({ ...applicationDomains, ...proofDomains });

export type ApplicationDomain = typeof applicationDomains[keyof typeof applicationDomains];
export type ProofDomain = typeof proofDomains[keyof typeof proofDomains];

export function isApplicationDomain(value: number): value is ApplicationDomain {
  return (value >= applicationDomains.SCOPE && value <= applicationDomains.STATEMENT)
    || value === applicationDomains.APP_MERKLE_NODE;
}

export function isProofDomain(value: number): value is ProofDomain {
  return value >= proofDomains.PROOF_LEAF && value <= proofDomains.PARAMETER_MANIFEST;
}
```

</details>

## `packages/sdk/src/index.ts`

- Bytes: 23,917
- SHA-256: `ad783a94010a598b27d372e7274a96a07ed9a867a8d636ec872775ea6ac34a71`

<details><summary>Complete file</summary>

```typescript
import { randomBytes } from "node:crypto";
import { keccak_256 } from "@noble/hashes/sha3.js";
import { coordinationDomains, domains } from "./domains.js";

export { coordinationDomains, domains };
export const TREE_DEPTH = 20;
export const PROTOCOL_VERSION = 3;
export const BABY_BEAR_MODULUS = 2_013_265_921;
export type Digest512 = Readonly<{ left: Uint8Array; right: Uint8Array }>;
export type Address = Uint8Array;

const NOTE_PREFIX = "pqtc-note-v3:";
const NOTE_LENGTH = 194;
const textEncoder = new TextEncoder();
const P = 2_013_265_921n;

const EXTERNAL_INITIAL = [
  [
    0x69cbb6afn, 0x46ad93f9n, 0x60a00f4en, 0x6b1297cdn, 0x23189afen, 0x732e7befn, 0x72c246den, 0x2c941900n,
    0x0557eeden, 0x1580496fn, 0x3a3ea77bn, 0x54f3f271n, 0x0f49b029n, 0x47872fe1n, 0x221e2e36n, 0x1ab7202en,
  ],
  [
    0x487779a6n, 0x3851c9d8n, 0x38dc17c0n, 0x209f8849n, 0x268dcee8n, 0x350c48dan, 0x5b9ad32en, 0x0523272bn,
    0x3f89055bn, 0x01e894b2n, 0x13ddedden, 0x1b2ef334n, 0x7507d8b4n, 0x6ceeb94en, 0x52eb6ba2n, 0x50642905n,
  ],
  [
    0x05453f3fn, 0x06349efcn, 0x6922787cn, 0x04bfff9cn, 0x768c714an, 0x3e9ff21an, 0x15737c9cn, 0x2229c807n,
    0x0d47f88cn, 0x097e0eccn, 0x27eadba0n, 0x2d7d29e4n, 0x3502aaa0n, 0x0f475fd7n, 0x29fbda49n, 0x018afffdn,
  ],
  [
    0x0315b618n, 0x6d4497d1n, 0x1b171d9en, 0x52861abdn, 0x2e5d0501n, 0x3ec8646cn, 0x6e5f250an, 0x148ae8e6n,
    0x17f5fa4an, 0x3e66d284n, 0x0051aa3bn, 0x483f7913n, 0x2cfe5f15n, 0x023427can, 0x2cc78315n, 0x1e36ea47n,
  ],
] as const;

const EXTERNAL_FINAL = [
  [
    0x7290a80dn, 0x6f7e5329n, 0x598ec8a8n, 0x76a859a0n, 0x6559e868n, 0x657b83afn, 0x13271d3fn, 0x1f876063n,
    0x0aeeae37n, 0x706e9ca6n, 0x46400ceen, 0x72a05c26n, 0x2c589c9en, 0x20bd37a7n, 0x6a2d3d10n, 0x20523767n,
  ],
  [
    0x5b8fe9c4n, 0x2aa501d6n, 0x1e01ac3en, 0x1448bc54n, 0x5ce5ad1cn, 0x4918a14dn, 0x2c46a83fn, 0x4fcf6876n,
    0x61d8d5c8n, 0x6ddf4ff9n, 0x11fda4d3n, 0x02933a8fn, 0x170eaf81n, 0x5a9c314fn, 0x49a12590n, 0x35ec52a1n,
  ],
  [
    0x58eb1611n, 0x5e481e65n, 0x367125c9n, 0x0eba33ban, 0x1fc28dedn, 0x066399adn, 0x0cbec0ean, 0x75fd1af0n,
    0x50f5bf4en, 0x643d5f41n, 0x6f4fe718n, 0x5b3cbbden, 0x1e3afb3en, 0x296fb027n, 0x45e1547bn, 0x4a8db2abn,
  ],
  [
    0x59986d19n, 0x30bcdfa3n, 0x1db63932n, 0x1d7c2824n, 0x53b33681n, 0x0673b747n, 0x038a98a3n, 0x2c5bce60n,
    0x351979cdn, 0x5008fb73n, 0x547bca78n, 0x711af481n, 0x3f93bf64n, 0x644d987bn, 0x3c8bcd87n, 0x608758b8n,
  ],
] as const;

const INTERNAL = [
  0x5a8053c0n, 0x693be639n, 0x3858867dn, 0x19334f6bn, 0x128f0fd8n, 0x4e2b1ccbn, 0x61210ce0n,
  0x3c318939n, 0x0b5b2f22n, 0x2edb11d5n, 0x213effdfn, 0x0cac4606n, 0x241af16dn,
] as const;

const INTERNAL_DIAGONAL = [
  2_013_265_919n, 1n, 2n, 1_006_632_961n, 3n, 4n, 1_006_632_960n, 2_013_265_918n,
  2_013_265_917n, 2_005_401_601n, 1_509_949_441n, 1_761_607_681n, 2_013_265_906n,
  7_864_320n, 125_829_120n, 15n,
] as const;

function concat(...parts: Uint8Array[]): Uint8Array {
  const length = parts.reduce((sum, part) => sum + part.length, 0);
  const out = new Uint8Array(length);
  let cursor = 0;
  for (const part of parts) { out.set(part, cursor); cursor += part.length; }
  return out;
}

function sized(bytes: Uint8Array, length: number, name: string): Uint8Array {
  if (bytes.length !== length) throw new RangeError(`${name} must be ${length} bytes`);
  return bytes;
}

function integer(value: bigint, length: number): Uint8Array {
  if (value < 0n || value >= 1n << BigInt(length * 8)) throw new RangeError(`integer does not fit ${length} bytes`);
  const out = new Uint8Array(length);
  for (let i = length - 1; i >= 0; i--) { out[i] = Number(value & 0xffn); value >>= 8n; }
  return out;
}

export function digestBytes(digest: Digest512): Uint8Array {
  return concat(sized(digest.left, 32, "digest.left"), sized(digest.right, 32, "digest.right"));
}

export function digestFromBytes(bytes: Uint8Array): Digest512 {
  sized(bytes, 64, "digest");
  return { left: bytes.slice(0, 32), right: bytes.slice(32) };
}

export function digestEqual(a: Digest512, b: Digest512): boolean {
  const aa = digestBytes(a); const bb = digestBytes(b);
  let difference = 0;
  for (let i = 0; i < aa.length; i++) difference |= aa[i]! ^ bb[i]!;
  return difference === 0;
}

function add(a: bigint, b: bigint): bigint {
  return (a + b) % P;
}


function mul(a: bigint, b: bigint): bigint {
  return (a * b) % P;
}

function sbox(value: bigint): bigint {
  const square = mul(value, value);
  const fourth = mul(square, square);
  return mul(mul(fourth, square), value);
}

function externalLinearLayer(state: bigint[]): void {
  for (let offset = 0; offset < 16; offset += 4) {
    const x0 = state[offset]!;
    const x1 = state[offset + 1]!;
    const x2 = state[offset + 2]!;
    const x3 = state[offset + 3]!;
    const t01 = add(x0, x1);
    const t23 = add(x2, x3);
    const t0123 = add(t01, t23);
    const t01123 = add(t0123, x1);
    const t01233 = add(t0123, x3);
    state[offset] = add(t01123, t01);
    state[offset + 1] = add(t01123, add(x2, x2));
    state[offset + 2] = add(t01233, t23);
    state[offset + 3] = add(t01233, add(x0, x0));
  }
  const sums = [0n, 0n, 0n, 0n];
  for (let i = 0; i < 16; i++) sums[i & 3] = add(sums[i & 3]!, state[i]!);
  for (let i = 0; i < 16; i++) state[i] = add(state[i]!, sums[i & 3]!);
}

function externalRounds(state: bigint[], constants: readonly (readonly bigint[])[]): void {
  for (const round of constants) {
    for (let i = 0; i < 16; i++) state[i] = sbox(add(state[i]!, round[i]!));
    externalLinearLayer(state);
  }
}

export function poseidon2BabyBear16(input: ArrayLike<number>): Uint32Array {
  if (input.length !== 16) throw new RangeError("Poseidon2 state must contain 16 elements");
  const state = new Array<bigint>(16);
  for (let index = 0; index < state.length; index++) {
    const value = input[index]!;
    if (!Number.isInteger(value) || value < 0 || value >= BABY_BEAR_MODULUS) {
      throw new RangeError(`state element ${index} is not canonical`);
    }
    state[index] = BigInt(value);
  }
  externalLinearLayer(state);
  externalRounds(state, EXTERNAL_INITIAL);
  for (const constant of INTERNAL) {
    state[0] = sbox(add(state[0]!, constant));
    let sum = 0n;
    for (const value of state) sum = add(sum, value);
    for (let i = 0; i < 16; i++) state[i] = add(sum, mul(state[i]!, INTERNAL_DIAGONAL[i]!));
  }
  externalRounds(state, EXTERNAL_FINAL);
  return Uint32Array.from(state, (value) => Number(value));
}

export function digestElements(digest: Digest512, name = "digest"): Uint32Array {
  const bytes = digestBytes(digest);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const elements = new Uint32Array(16);
  for (let i = 0; i < elements.length; i++) {
    const value = view.getUint32(i * 4, false);
    if (value >= BABY_BEAR_MODULUS) throw new RangeError(`${name} element ${i} is not canonical`);
    elements[i] = value;
  }
  return elements;
}

export function digestFromElements(elements: ArrayLike<number>): Digest512 {
  if (elements.length !== 16) throw new RangeError("digest must contain 16 elements");
  const bytes = new Uint8Array(64);
  const view = new DataView(bytes.buffer);
  for (let i = 0; i < elements.length; i++) {
    const value = elements[i]!;
    if (!Number.isInteger(value) || value < 0 || value >= BABY_BEAR_MODULUS) {
      throw new RangeError(`digest element ${i} is not canonical`);
    }
    view.setUint32(i * 4, value, false);
  }
  return digestFromBytes(bytes);
}

function byteElements(bytes: Uint8Array): number[] {
  const elements = new Array<number>(Math.ceil(bytes.length / 2));
  for (let i = 0; i < elements.length; i++) elements[i] = (bytes[i * 2]! << 8) | (bytes[i * 2 + 1] ?? 0);
  return elements;
}

export type CanonicalSecret = ArrayLike<number | bigint>;

function secretElements(secret: CanonicalSecret, name: string): number[] {
  if (secret.length !== 8) throw new RangeError(`${name} must contain 8 limbs`);
  const elements = new Array<number>(8);
  for (let index = 0; index < elements.length; index++) {
    const input = secret[index]!;
    if (
      (typeof input === "number" && (!Number.isInteger(input) || input < 0 || input >= BABY_BEAR_MODULUS))
      || (typeof input === "bigint" && (input < 0n || input >= P))
      || (typeof input !== "number" && typeof input !== "bigint")
    ) {
      throw new RangeError(`${name} limb ${index} is not canonical`);
    }
    elements[index] = Number(input);
  }
  return elements;
}

export function secretBytes(secret: CanonicalSecret, name = "secret"): Uint8Array {
  const elements = secretElements(secret, name);
  const bytes = new Uint8Array(32);
  const view = new DataView(bytes.buffer);
  for (let index = 0; index < elements.length; index++) view.setUint32(index * 4, elements[index]!, false);
  return bytes;
}

export function secretFromBytes(bytes: Uint8Array, name = "secret"): Uint32Array {
  sized(bytes, 32, name);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const secret = new Uint32Array(8);
  for (let index = 0; index < secret.length; index++) {
    const limb = view.getUint32(index * 4, false);
    if (limb >= BABY_BEAR_MODULUS) throw new RangeError(`${name} limb ${index} is not canonical`);
    secret[index] = limb;
  }
  return secret;
}

export function randomSecret(): Uint32Array {
  const secret = new Uint32Array(8);
  let accepted = 0;
  while (accepted < secret.length) {
    const entropy = randomBytes(64);
    const view = new DataView(entropy.buffer, entropy.byteOffset, entropy.byteLength);
    for (let offset = 0; offset < entropy.length && accepted < secret.length; offset += 4) {
      const candidate = view.getUint32(offset, false);
      if (candidate < BABY_BEAR_MODULUS) secret[accepted++] = candidate;
    }
  }
  return secret;
}

export function p2bb512(tag: number, payloadByteLength: number, aux: number, payload: ArrayLike<number>): Digest512 {
  if (!Number.isInteger(tag) || tag < 0 || tag > 255) throw new RangeError("tag must be one byte");
  if (!Number.isInteger(payloadByteLength) || payloadByteLength < 0 || payloadByteLength >= BABY_BEAR_MODULUS) {
    throw new RangeError("payload byte length is not canonical");
  }
  if (!Number.isInteger(aux) || aux < 0 || aux >= BABY_BEAR_MODULUS) throw new RangeError("aux is not canonical");
  if (!Number.isSafeInteger(payload.length) || payload.length < 0 || payload.length >= BABY_BEAR_MODULUS) {
    throw new RangeError("payload element count is not canonical");
  }
  const state = new Uint32Array(16);
  state[4] = 1;
  state[5] = tag;
  state[6] = payloadByteLength;
  state[7] = payload.length;
  state[8] = aux;
  const blocks = Math.max(1, Math.ceil(payload.length / 4));
  for (let block = 0; block < blocks; block++) {
    for (let i = 0; i < 4; i++) {
      const index = block * 4 + i;
      const value = index < payload.length ? payload[index]! : 0;
      if (!Number.isInteger(value) || value < 0 || value >= BABY_BEAR_MODULUS) {
        throw new RangeError(`payload element ${index} is not canonical`);
      }
      state[i] = Number((BigInt(state[i]!) + BigInt(value)) % P);
    }
    state.set(poseidon2BabyBear16(state));
  }
  const output = new Uint32Array(16);
  for (let block = 0; block < 4; block++) {
    output.set(state.subarray(0, 4), block * 4);
    if (block !== 3) state.set(poseidon2BabyBear16(state));
  }
  return digestFromElements(output);
}

export function k512(tag: number, payload: Uint8Array): Digest512 {
  if (!Number.isInteger(tag) || tag < 0 || tag > 255) throw new RangeError("tag must be one byte");
  return {
    left: keccak_256(concat(Uint8Array.of(0, tag), payload)),
    right: keccak_256(concat(Uint8Array.of(1, tag), payload)),
  };
}

export interface ScopeInput {
  chainId: bigint;
  pool: Address;
  denomination: bigint;
  treeDepth?: number;
  protocolVersion?: number;
  parameterId: Digest512;
}

export function scope(input: ScopeInput): Digest512 {
  const depth = input.treeDepth ?? TREE_DEPTH;
  const version = input.protocolVersion ?? PROTOCOL_VERSION;
  const payload = concat(
    integer(input.chainId, 8), sized(input.pool, 20, "pool"), integer(input.denomination, 32),
    integer(BigInt(depth), 1), integer(BigInt(version), 4), digestBytes(input.parameterId),
  );
  return p2bb512(domains.SCOPE, payload.length, 0, byteElements(payload));
}

export function commitment(
  poolScope: Digest512,
  nullifierSecret: CanonicalSecret,
  trapdoor: CanonicalSecret,
): Digest512 {
  return p2bb512(domains.NOTE, 128, 0, [
    ...digestElements(poolScope, "scope"),
    ...secretElements(nullifierSecret, "nullifierSecret"),
    ...secretElements(trapdoor, "trapdoor"),
  ]);
}

export function nullifierHash(poolScope: Digest512, nullifierSecret: CanonicalSecret): Digest512 {
  return p2bb512(domains.NULLIFIER, 96, 0, [
    ...digestElements(poolScope, "scope"),
    ...secretElements(nullifierSecret, "nullifierSecret"),
  ]);
}

export function emptyLeaf(poolScope: Digest512): Digest512 {
  return p2bb512(domains.EMPTY_LEAF, 64, 0, digestElements(poolScope, "scope"));
}

export function merkleNode(level: number, left: Digest512, right: Digest512): Digest512 {
  if (!Number.isInteger(level) || level < 0 || level >= TREE_DEPTH) throw new RangeError("invalid Merkle level");
  return p2bb512(domains.APP_MERKLE_NODE, 128, level, [...digestElements(left, "left"), ...digestElements(right, "right")]);
}

export function payoutDigest(recipient: Address, relayer: Address, fee: bigint): Digest512 {
  const payload = concat(sized(recipient, 20, "recipient"), sized(relayer, 20, "relayer"), integer(fee, 32));
  return p2bb512(domains.PAYOUT, payload.length, 0, byteElements(payload));
}

export interface WithdrawalStatement {
  scope: Digest512;
  root: Digest512;
  nullifierHash: Digest512;
  payoutDigest: Digest512;
}

export function statementHash(statement: WithdrawalStatement): Digest512 {
  const elements = [
    ...digestElements(statement.scope, "scope"),
    ...digestElements(statement.root, "root"),
    ...digestElements(statement.nullifierHash, "nullifierHash"),
    ...digestElements(statement.payoutDigest, "payoutDigest"),
  ];
  return p2bb512(domains.STATEMENT, 256, 0, elements);
}

export function publicValues(statement: WithdrawalStatement): Uint32Array {
  const out = new Uint32Array(64);
  out.set(digestElements(statement.scope, "scope"), 0);
  out.set(digestElements(statement.root, "root"), 16);
  out.set(digestElements(statement.nullifierHash, "nullifierHash"), 32);
  out.set(digestElements(statement.payoutDigest, "payoutDigest"), 48);
  return out;
}
const PROOF_MAGIC = new TextEncoder().encode("PQTCSTK3");
const PROOF_END = Uint8Array.of(0x50, 0x51, 0x45, 0x4e);
const MAX_STARK_PAYLOAD_BYTES = 2 * 1024 * 1024;
const PUBLIC_VALUES_COUNT = 64;

export interface CompactProofV3 {
  parameterId: Digest512;
  publicValues: Uint32Array;
  starkPayload: Uint8Array;
}

export function encodeCompactProof(proof: CompactProofV3): Uint8Array {
  if (proof.publicValues.length !== PUBLIC_VALUES_COUNT) throw new RangeError("public value count must be 64");
  if (proof.starkPayload.length > MAX_STARK_PAYLOAD_BYTES) throw new RangeError("STARK payload is too large");
  const parameter = digestBytes(proof.parameterId);
  if (parameter.every((byte) => byte === 0)) throw new Error("parameter ID cannot be zero");
  const fields = new Uint8Array(PUBLIC_VALUES_COUNT * 4);
  const fieldView = new DataView(fields.buffer);
  for (let i = 0; i < PUBLIC_VALUES_COUNT; i++) {
    const value = proof.publicValues[i]!;
    if (value >= BABY_BEAR_MODULUS) throw new RangeError(`field element ${value} is not canonical`);
    fieldView.setUint32(i * 4, value, false);
  }
  return concat(
    PROOF_MAGIC,
    integer(3n, 2),
    parameter,
    integer(BigInt(PUBLIC_VALUES_COUNT), 2),
    fields,
    integer(BigInt(proof.starkPayload.length), 4),
    proof.starkPayload,
    PROOF_END,
  );
}

export function decodeCompactProof(bytes: Uint8Array): CompactProofV3 {
  const fixedPrefix = 8 + 2 + 64 + 2 + PUBLIC_VALUES_COUNT * 4 + 4;
  if (bytes.length < fixedPrefix + 4) throw new Error("proof is truncated");
  let cursor = 0;
  const take = (length: number): Uint8Array => {
    const end = cursor + length;
    if (!Number.isSafeInteger(end) || end > bytes.length) throw new Error("proof is truncated");
    const value = bytes.slice(cursor, end);
    cursor = end;
    return value;
  };
  const readU16 = (): number => new DataView(take(2).buffer).getUint16(0, false);
  const readU32 = (): number => new DataView(take(4).buffer).getUint32(0, false);
  if (!equalBytes(take(8), PROOF_MAGIC)) throw new Error("invalid proof magic");
  if (readU16() !== 3) throw new Error("unsupported proof codec version");
  const parameterId = digestFromBytes(take(64));
  if (digestBytes(parameterId).every((byte) => byte === 0)) throw new Error("parameter ID cannot be zero");
  if (readU16() !== PUBLIC_VALUES_COUNT) throw new Error("public value count must be 64");
  const values = take(PUBLIC_VALUES_COUNT * 4);
  const valueView = new DataView(values.buffer, values.byteOffset, values.byteLength);
  const publicValues = new Uint32Array(PUBLIC_VALUES_COUNT);
  for (let i = 0; i < PUBLIC_VALUES_COUNT; i++) {
    const value = valueView.getUint32(i * 4, false);
    if (value >= BABY_BEAR_MODULUS) throw new Error(`field element ${value} is not canonical`);
    publicValues[i] = value;
  }
  const payloadLength = readU32();
  if (payloadLength > MAX_STARK_PAYLOAD_BYTES) throw new Error("STARK payload is too large");
  const starkPayload = take(payloadLength);
  if (!equalBytes(take(4), PROOF_END)) throw new Error("invalid proof end marker");
  if (cursor !== bytes.length) throw new Error("proof has trailing bytes");
  return { parameterId, publicValues, starkPayload };
}


export interface Note {
  chainId: bigint;
  pool: Address;
  parameterId: Digest512;
  nullifierSecret: CanonicalSecret;
  trapdoor: CanonicalSecret;
}

export function newNote(chainId: bigint, pool: Address, parameterId: Digest512): Note {
  return { chainId, pool: sized(pool, 20, "pool").slice(), parameterId, nullifierSecret: randomSecret(), trapdoor: randomSecret() };
}

export function encodeNote(note: Note): string {
  const body = concat(
    textEncoder.encode("PQTN"), integer(3n, 2), integer(note.chainId, 8), sized(note.pool, 20, "pool"),
    digestBytes(note.parameterId), secretBytes(note.nullifierSecret, "nullifierSecret"), secretBytes(note.trapdoor, "trapdoor"),
  );
  const checksum = keccak_256(concat(Uint8Array.of(0, domains.NOTE), body));
  return NOTE_PREFIX + Buffer.from(concat(body, checksum)).toString("base64url");
}

export function parseNote(encoded: string): Note {
  if (!encoded.startsWith(NOTE_PREFIX)) throw new Error("invalid note prefix");
  const payload = encoded.slice(NOTE_PREFIX.length);
  if (!/^[A-Za-z0-9_-]+$/.test(payload)) throw new Error("invalid note encoding");
  const bytes = new Uint8Array(Buffer.from(payload, "base64url"));
  if (Buffer.from(bytes).toString("base64url") !== payload) throw new Error("noncanonical note encoding");
  if (bytes.length !== NOTE_LENGTH) throw new Error("invalid note length");
  if (new TextDecoder().decode(bytes.slice(0, 4)) !== "PQTN") throw new Error("invalid note magic");
  if (bytes[4] !== 0 || bytes[5] !== 3) throw new Error("unsupported note version");
  const expected = keccak_256(concat(Uint8Array.of(0, domains.NOTE), bytes.slice(0, 162)));
  if (!equalBytes(expected, bytes.slice(162))) throw new Error("invalid note checksum");
  let chainId = 0n;
  for (const byte of bytes.slice(6, 14)) chainId = (chainId << 8n) | BigInt(byte);
  return {
    chainId,
    pool: bytes.slice(14, 34),
    parameterId: digestFromBytes(bytes.slice(34, 98)),
    nullifierSecret: secretFromBytes(bytes.slice(98, 130), "nullifierSecret"),
    trapdoor: secretFromBytes(bytes.slice(130, 162), "trapdoor"),
  };
}

export class NoteSecretTracker {
  private readonly nullifierSecrets = new Set<string>();

  register(note: Note): void {
    const key = Buffer.from(secretBytes(note.nullifierSecret, "nullifierSecret")).toString("hex");
    if (this.nullifierSecrets.has(key)) throw new Error("nullifier secret was already used locally");
    this.nullifierSecrets.add(key);
  }
}

function equalBytes(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let difference = 0;
  for (let i = 0; i < a.length; i++) difference |= a[i]! ^ b[i]!;
  return difference === 0;
}

export interface MerklePath { leafIndex: number; siblings: Digest512[] }

export class MerkleTree {
  readonly zeros: Digest512[];
  readonly leaves: Digest512[] = [];
  readonly filledSubtrees: Digest512[];
  private readonly commitmentKeys = new Set<string>();
  root: Digest512;

  constructor(poolScope: Digest512) {
    this.zeros = [emptyLeaf(poolScope)];
    for (let level = 0; level < TREE_DEPTH; level++) this.zeros.push(merkleNode(level, this.zeros[level]!, this.zeros[level]!));
    this.filledSubtrees = this.zeros.slice(0, TREE_DEPTH);
    this.root = this.zeros[TREE_DEPTH]!;
  }

  insert(leaf: Digest512): Readonly<{ leafIndex: number; root: Digest512 }> {
    const key = Buffer.from(digestBytes(leaf)).toString("hex");
    if (/^0+$/.test(key)) throw new Error("zero commitment");
    if (this.commitmentKeys.has(key)) throw new Error("duplicate commitment");
    if (this.leaves.length >= 1 << TREE_DEPTH) throw new Error("tree full");
    const leafIndex = this.leaves.length;
    let current = leaf; let index = leafIndex;
    for (let level = 0; level < TREE_DEPTH; level++) {
      if ((index & 1) === 0) { this.filledSubtrees[level] = current; current = merkleNode(level, current, this.zeros[level]!); }
      else current = merkleNode(level, this.filledSubtrees[level]!, current);
      index >>= 1;
    }
    this.commitmentKeys.add(key); this.leaves.push(leaf); this.root = current;
    return { leafIndex, root: current };
  }

  path(leafIndex: number): MerklePath {
    if (!Number.isInteger(leafIndex) || leafIndex < 0 || leafIndex >= this.leaves.length) throw new RangeError("unknown leaf");
    const siblings: Digest512[] = [];
    let nodes = this.leaves.slice(); let index = leafIndex;
    for (let level = 0; level < TREE_DEPTH; level++) {
      siblings.push(nodes[index ^ 1] ?? this.zeros[level]!);
      if ((nodes.length & 1) === 1) nodes.push(this.zeros[level]!);
      const parents: Digest512[] = [];
      for (let i = 0; i < nodes.length; i += 2) parents.push(merkleNode(level, nodes[i]!, nodes[i + 1]!));
      nodes = parents; index >>= 1;
    }
    return { leafIndex, siblings };
  }
}

export function rootFromPath(leaf: Digest512, path: MerklePath): Digest512 {
  if (path.siblings.length !== TREE_DEPTH) throw new RangeError("path must have 20 siblings");
  let current = leaf;
  for (let level = 0; level < TREE_DEPTH; level++) current = (path.leafIndex & (1 << level)) === 0
    ? merkleNode(level, current, path.siblings[level]!)
    : merkleNode(level, path.siblings[level]!, current);
  return current;
}



function selector(signature: string): Uint8Array {
  return keccak_256(textEncoder.encode(signature)).slice(0, 4);
}

export function encodeDepositCalldata(noteCommitment: Digest512): Uint8Array {
  return concat(
    selector("deposit((bytes32,bytes32))"),
    sized(noteCommitment.left, 32, "commitment.left"),
    sized(noteCommitment.right, 32, "commitment.right"),
  );
}


export function hex(bytes: Uint8Array): `0x${string}` {
  return `0x${Buffer.from(bytes).toString("hex")}`;
}

export function bytesFromHex(value: string, expectedLength?: number): Uint8Array {
  if (!/^0x[0-9a-fA-F]*$/.test(value) || value.length % 2 !== 0) throw new TypeError("invalid hex");
  const bytes = Uint8Array.from(Buffer.from(value.slice(2), "hex"));
  if (expectedLength !== undefined) sized(bytes, expectedLength, "hex value");
  return bytes;
}
```

</details>

## `packages/sdk/src/relayer.ts`

- Bytes: 26,676
- SHA-256: `8452c16486935ec7974e8c58b752e1928a63f3bdc77a02c0d259cdb2d36f34ed`

<details><summary>Complete file</summary>

```typescript
#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { keccak_256 } from "@noble/hashes/sha3.js";
import { coordinationDomains } from "./domains.js";
import {
  BABY_BEAR_MODULUS,
  PROTOCOL_VERSION,
  bytesFromHex,
  digestBytes,
  digestEqual,
  digestFromBytes,
  hex,
  payoutDigest,
  publicValues,
  statementHash,
  type Digest512,
} from "./index.js";

export const RELAYER_REQUEST_VERSION = PROTOCOL_VERSION;
const UINT64_LIMIT = 1n << 64n;
const UINT256_LIMIT = 1n << 256n;
const TEXT_ENCODER = new TextEncoder();
const STATEMENT_KEY_LABEL = TEXT_ENCODER.encode(coordinationDomains.STATEMENT);
const PROOF_ID_LABEL = TEXT_ENCODER.encode(coordinationDomains.PROOF);
const CHECKPOINT_LABEL = TEXT_ENCODER.encode(coordinationDomains.CHECKPOINT);
const VERIFICATION_ID_LABEL = TEXT_ENCODER.encode(coordinationDomains.VERIFICATION);
const PROOF_PART_A_MAGIC = TEXT_ENCODER.encode("PQTCPA03");
const PROOF_PART_B_MAGIC = TEXT_ENCODER.encode("PQTCPB03");
const PROOF_COMMON_HEADER_BYTES = 338;
const GLOBAL_DATA_BYTES = 9_208;
const QUERY_COUNT = 32;
const HALF_QUERY_COUNT = 16;
const FRI_ROUNDS = 9;
const CHECKPOINT_FIXED_BYTES = 452;
const PART_A_END = "0x50414533";
const PART_B_END = "0x50424533";
const VERIFICATION_STARTED_TOPIC = hex(keccak_256(TEXT_ENCODER.encode(
  "VerificationStarted(bytes32,address,bytes32)",
)));

export interface WithdrawalRequestV3 {
  version: 3;
  chainId: string;
  pool: string;
  registry: string;
  scope: string;
  parameterId: string;
  root: string;
  nullifierHash: string;
  recipient: string;
  relayer: string;
  fee: string;
  deadline: string;
  statementId: string;
  publicValues: number[];
  proof: {
    partA: string;
    partB: string;
  };
}

export interface RelayerPolicy {
  chainId: bigint;
  pool: string;
  registry: string;
  scope: string;
  parameterId: string;
  denomination: bigint;
  relayer: string;
}

export interface RelayerTransaction {
  readonly phase: "A" | "B";
  readonly order: 1 | 2;
  readonly from: `0x${string}`;
  readonly to: `0x${string}`;
  readonly data: `0x${string}`;
}

export interface TransactionReceipt {
  status: string | number;
  to: string | null;
  logs: ReadonlyArray<{
    address: string;
    topics: readonly string[];
  }>;
}

type JsonRecord = Record<string, unknown>;

type ValidatedRequest = Readonly<{
  pool: `0x${string}`;
  registry: `0x${string}`;
  parameterId: Digest512;
  root: Digest512;
  nullifierHash: Digest512;
  recipient: Uint8Array;
  relayer: Uint8Array;
  relayerHex: `0x${string}`;
  fee: bigint;
  deadline: bigint;
  publicValues: Uint32Array;
  statementKey: `0x${string}`;
  proofPartA: Uint8Array;
  proofPartB: Uint8Array;
  verificationId: Uint8Array;
}>;

function concat(...parts: readonly Uint8Array[]): Uint8Array {
  const length = parts.reduce((sum, part) => sum + part.length, 0);
  const output = new Uint8Array(length);
  let cursor = 0;
  for (const part of parts) {
    output.set(part, cursor);
    cursor += part.length;
  }
  return output;
}

function uintWord(value: bigint): Uint8Array {
  if (value < 0n || value >= UINT256_LIMIT) throw new RangeError("integer does not fit an ABI word");
  const output = new Uint8Array(32);
  for (let index = output.length - 1; index >= 0; index--) {
    output[index] = Number(value & 0xffn);
    value >>= 8n;
  }
  return output;
}

function abiAddress(address: Uint8Array): Uint8Array {
  const output = new Uint8Array(32);
  output.set(address, 12);
  return output;
}

function abiBytes(bytes: Uint8Array): Uint8Array {
  const padded = new Uint8Array(Math.ceil(bytes.length / 32) * 32);
  padded.set(bytes);
  return concat(uintWord(BigInt(bytes.length)), padded);
}

function functionSelector(signature: string): Uint8Array {
  return keccak_256(TEXT_ENCODER.encode(signature)).slice(0, 4);
}

function asRecord(value: unknown, name: string): JsonRecord {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new TypeError(`${name} must be an object`);
  }
  return value as JsonRecord;
}

function requireExactKeys(record: JsonRecord, expected: readonly string[], name: string): void {
  for (const key of Object.keys(record)) {
    if (!expected.includes(key)) throw new Error(`${name} contains unsupported field ${key}`);
  }
  for (const key of expected) {
    if (!(key in record)) throw new Error(`${name} is missing ${key}`);
  }
}

function requireString(value: unknown, name: string): string {
  if (typeof value !== "string") throw new TypeError(`${name} must be a string`);
  return value;
}

function unsignedDecimal(value: unknown, name: string, limit: bigint): bigint {
  const text = requireString(value, name);
  if (!/^(0|[1-9][0-9]*)$/.test(text)) throw new TypeError(`${name} must be canonical unsigned decimal`);
  const parsed = BigInt(text);
  if (parsed >= limit) throw new RangeError(`${name} is out of range`);
  return parsed;
}

function address(value: unknown, name: string, allowZero = false): { bytes: Uint8Array; hex: `0x${string}` } {
  const bytes = bytesFromHex(requireString(value, name), 20);
  if (!allowZero && bytes.every((byte) => byte === 0)) throw new Error(`${name} cannot be zero`);
  return { bytes, hex: hex(bytes) };
}

function canonicalDigest(value: unknown, name: string, allowZero = true): Digest512 {
  const bytes = bytesFromHex(requireString(value, name), 64);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let nonzero = false;
  for (let index = 0; index < 16; index++) {
    const limb = view.getUint32(index * 4, false);
    if (limb >= BABY_BEAR_MODULUS) throw new RangeError(`${name} limb ${index} is not canonical`);
    nonzero ||= limb !== 0;
  }
  if (!allowZero && !nonzero) throw new Error(`${name} cannot be zero`);
  return digestFromBytes(bytes);
}
function proofDigest(value: unknown, name: string, allowZero = true): Digest512 {
  const bytes = bytesFromHex(requireString(value, name), 64);
  if (!allowZero && bytes.every((byte) => byte === 0)) throw new Error(`${name} cannot be zero`);
  return digestFromBytes(bytes);
}

function digestHex(digest: Digest512): `0x${string}` {
  return hex(digestBytes(digest));
}

function sameBytes(left: Uint8Array, right: Uint8Array): boolean {
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index++) difference |= left[index]! ^ right[index]!;
  return difference === 0;
}

function parsePublicValues(value: unknown): Uint32Array {
  if (!Array.isArray(value) || value.length !== 64) throw new Error("publicValues must contain 64 elements");
  const output = new Uint32Array(64);
  for (let index = 0; index < value.length; index++) {
    const limb = value[index];
    if (!Number.isInteger(limb) || (limb as number) < 0 || (limb as number) >= BABY_BEAR_MODULUS) {
      throw new RangeError(`publicValues[${index}] is not canonical`);
    }
    output[index] = limb as number;
  }
  return output;
}

function abiPublicValues(values: Uint32Array): Uint8Array {
  if (values.length !== 64) throw new Error("public values must contain 64 elements");
  const words = new Uint8Array(64 * 32);
  const view = new DataView(words.buffer);
  for (let index = 0; index < values.length; index++) {
    const value = values[index]!;
    if (value >= BABY_BEAR_MODULUS) throw new RangeError(`public value ${index} is not canonical`);
    view.setUint32(index * 32 + 28, value, false);
  }
  return words;
}

export function deriveStatementKey(parameterId: Digest512, values: Uint32Array): `0x${string}` {
  const canonicalParameterId = proofDigest(digestHex(parameterId), "parameterId", false);
  const label = new Uint8Array(32);
  label.set(STATEMENT_KEY_LABEL);
  return hex(keccak_256(concat(label, digestBytes(canonicalParameterId), abiPublicValues(values))));
}
export function deriveCoreProofId(statementKey: string, proofPartA: Uint8Array): `0x${string}` {
  const label = new Uint8Array(32);
  label.set(PROOF_ID_LABEL);
  return hex(keccak_256(concat(
    label,
    bytesFromHex(statementKey, 32),
    keccak_256(proofPartA),
  )));
}

export function deriveVerificationId(coreProofId: string, consumer: string): `0x${string}` {
  const label = new Uint8Array(32);
  label.set(VERIFICATION_ID_LABEL);
  return hex(keccak_256(concat(
    label,
    bytesFromHex(coreProofId, 32),
    abiAddress(address(consumer, "consumer").bytes),
  )));
}

function parseProofPart(
  value: unknown,
  expectedKind: "A" | "B",
  expectedParameterId: Digest512,
  expectedPublicValues: Uint32Array,
  expectedStatementKey: `0x${string}`,
): {
  payload: Uint8Array;
  globalDigest: Uint8Array;
  checkpointDigest: Uint8Array;
  proofId?: Uint8Array;
} {
  const name = `proof.part${expectedKind}`;
  const payload = bytesFromHex(requireString(value, name));
  const proofIdBytes = expectedKind === "B" ? 32 : 0;
  const globalDigestOffset = PROOF_COMMON_HEADER_BYTES + proofIdBytes;
  const globalDataOffset = globalDigestOffset + 32;
  const checkpointOffset = globalDataOffset + GLOBAL_DATA_BYTES;
  if (payload.length < checkpointOffset + CHECKPOINT_FIXED_BYTES + 4 + HALF_QUERY_COUNT * 4 + 4) {
    throw new Error(`${name} is truncated`);
  }
  const magic = expectedKind === "A" ? PROOF_PART_A_MAGIC : PROOF_PART_B_MAGIC;
  if (!sameBytes(payload.subarray(0, 8), magic)) {
    throw new Error(`${name} has wrong magic or the proof parts were swapped`);
  }
  const endMarker = expectedKind === "A" ? PART_A_END : PART_B_END;
  if (hex(payload.subarray(payload.length - 4)) !== endMarker) throw new Error(`${name} has invalid end marker`);
  const view = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  if (view.getUint16(8, false) !== RELAYER_REQUEST_VERSION) throw new Error(`${name} must use proof version 3`);
  if (view.getUint8(10) !== 3) throw new Error(`${name} must use the v0.3 security profile`);
  if (
    view.getUint8(11) !== 9
    || view.getUint8(12) !== FRI_ROUNDS
    || view.getUint8(13) !== 4
  ) {
    throw new Error(`${name} has unsupported proof shape`);
  }
  if (view.getUint16(14, false) !== QUERY_COUNT) throw new Error(`${name} must contain 32 queries`);
  const parameterId = proofDigest(hex(payload.slice(16, 80)), `${name}.parameterId`, false);
  if (!digestEqual(parameterId, expectedParameterId)) throw new Error(`${name} parameter ID mismatch`);
  if (view.getUint16(80, false) !== 64) throw new Error(`${name} public value count must be 64`);
  for (let index = 0; index < 64; index++) {
    const limb = view.getUint32(82 + index * 4, false);
    if (limb >= BABY_BEAR_MODULUS) throw new Error(`${name} public value ${index} is not canonical`);
    if (limb !== expectedPublicValues[index]) throw new Error(`${name} statement public values mismatch`);
  }

  const globalDigest = payload.slice(globalDigestOffset, globalDataOffset);
  const globalData = payload.slice(globalDataOffset, checkpointOffset);
  if (!sameBytes(keccak_256(globalData), globalDigest)) {
    throw new Error(`${name} global data digest mismatch`);
  }

  const checkpointDigest = payload.slice(checkpointOffset, checkpointOffset + 32);
  const checkpointGlobalDigest = payload.slice(checkpointOffset + 32, checkpointOffset + 64);
  if (!sameBytes(checkpointGlobalDigest, globalDigest)) {
    throw new Error(`${name} checkpoint does not bind global data`);
  }
  if (view.getUint16(checkpointOffset + 320, false) !== QUERY_COUNT) {
    throw new Error(`${name} checkpoint must contain 32 queries`);
  }
  const queryIndices = new Uint32Array(QUERY_COUNT);
  for (let index = 0; index < QUERY_COUNT; index++) {
    const queryIndex = view.getUint32(checkpointOffset + 322 + index * 4, false);
    if (queryIndex >= 1 << 13) throw new Error(`${name} checkpoint query index is out of range`);
    queryIndices[index] = queryIndex;
  }
  const uniqueCount = view.getUint16(checkpointOffset + 450, false);
  if (uniqueCount > QUERY_COUNT) throw new Error(`${name} checkpoint unique-query count is invalid`);
  const halfOffset = checkpointOffset + CHECKPOINT_FIXED_BYTES + uniqueCount * 4;
  if (payload.length < halfOffset + 4 + HALF_QUERY_COUNT * 4 + 4) throw new Error(`${name} is truncated`);

  const expectedUnique = [...new Set(queryIndices)].sort((left, right) => left - right);
  if (uniqueCount !== expectedUnique.length) throw new Error(`${name} checkpoint unique queries are invalid`);
  for (let index = 0; index < uniqueCount; index++) {
    if (view.getUint32(checkpointOffset + CHECKPOINT_FIXED_BYTES + index * 4, false) !== expectedUnique[index]) {
      throw new Error(`${name} checkpoint unique queries are invalid`);
    }
  }

  const expectedHalfStart = expectedKind === "A" ? 0 : HALF_QUERY_COUNT;
  if (
    view.getUint16(halfOffset, false) !== expectedHalfStart
    || view.getUint16(halfOffset + 2, false) !== HALF_QUERY_COUNT
  ) {
    throw new Error(`${name} must contain the ${expectedKind === "A" ? "first" : "second"} 16 queries`);
  }
  for (let index = 0; index < HALF_QUERY_COUNT; index++) {
    if (
      view.getUint32(halfOffset + 4 + index * 4, false)
      !== queryIndices[expectedHalfStart + index]
    ) {
      throw new Error(`${name} half-query indices do not match its checkpoint`);
    }
  }

  const checkpointPayload = payload.slice(checkpointOffset + 32, halfOffset);
  const paddedCheckpointLabel = new Uint8Array(32);
  paddedCheckpointLabel.set(CHECKPOINT_LABEL);
  const expectedCheckpointDigest = keccak_256(concat(
    paddedCheckpointLabel,
    bytesFromHex(expectedStatementKey, 32),
    keccak_256(checkpointPayload),
  ));
  if (!sameBytes(checkpointDigest, expectedCheckpointDigest)) {
    throw new Error(`${name} checkpoint digest mismatch`);
  }

  if (expectedKind === "A") return { payload, globalDigest, checkpointDigest };
  const proofId = payload.slice(PROOF_COMMON_HEADER_BYTES, PROOF_COMMON_HEADER_BYTES + 32);
  if (proofId.every((byte) => byte === 0)) throw new Error(`${name} proof ID cannot be zero`);
  return { payload, globalDigest, checkpointDigest, proofId };
}

function validateRequest(input: unknown, policy: RelayerPolicy, nowSeconds: bigint): ValidatedRequest {
  const request = asRecord(input, "request");
  requireExactKeys(request, [
    "version", "chainId", "pool", "registry", "scope", "parameterId", "root", "nullifierHash",
    "recipient", "relayer", "fee", "deadline", "statementId", "publicValues", "proof",
  ], "request");
  if (request.version !== RELAYER_REQUEST_VERSION) throw new Error("protocol version 3 is required");

  const chainId = unsignedDecimal(request.chainId, "chainId", UINT64_LIMIT);
  if (chainId !== policy.chainId) throw new Error("request chain does not match connected chain");
  const requestPool = address(request.pool, "pool");
  const policyPool = address(policy.pool, "configured pool");
  if (!sameBytes(requestPool.bytes, policyPool.bytes)) throw new Error("request pool does not match configured pool");
  const requestRegistry = address(request.registry, "registry");
  const policyRegistry = address(policy.registry, "configured registry");
  if (!sameBytes(requestRegistry.bytes, policyRegistry.bytes)) throw new Error("request registry does not match pool registry");

  const requestScope = canonicalDigest(request.scope, "scope");
  const policyScope = canonicalDigest(policy.scope, "configured scope");
  if (!digestEqual(requestScope, policyScope)) throw new Error("request scope does not match pool scope");
  const parameterId = proofDigest(request.parameterId, "parameterId", false);
  const policyParameterId = proofDigest(policy.parameterId, "configured parameterId", false);
  if (!digestEqual(parameterId, policyParameterId)) throw new Error("request parameter ID does not match pool parameter ID");

  const root = canonicalDigest(request.root, "root");
  const nullifierHash = canonicalDigest(request.nullifierHash, "nullifierHash");
  const parsedRecipient = address(request.recipient, "recipient");
  const parsedRelayer = address(request.relayer, "relayer");
  const configuredRelayer = address(policy.relayer, "configured relayer");
  if (!sameBytes(parsedRelayer.bytes, configuredRelayer.bytes)) {
    throw new Error("request relayer does not match configured relayer");
  }
  if (sameBytes(parsedRecipient.bytes, parsedRelayer.bytes)) {
    throw new Error("recipient must be independent from relayer");
  }

  const fee = unsignedDecimal(request.fee, "fee", UINT256_LIMIT);
  if (policy.denomination <= 0n || policy.denomination >= UINT256_LIMIT) throw new Error("invalid pool denomination");
  if (fee > policy.denomination) throw new Error("fee exceeds pool denomination");
  const deadline = unsignedDecimal(request.deadline, "deadline", UINT64_LIMIT);
  if (deadline <= nowSeconds) throw new Error("request deadline has expired");

  const statement = {
    scope: requestScope,
    root,
    nullifierHash,
    payoutDigest: payoutDigest(parsedRecipient.bytes, parsedRelayer.bytes, fee),
  };
  const expectedStatementId = statementHash(statement);
  const suppliedStatementId = canonicalDigest(request.statementId, "statementId");
  if (!digestEqual(suppliedStatementId, expectedStatementId)) throw new Error("statement ID mismatch");

  const suppliedPublicValues = parsePublicValues(request.publicValues);
  const expectedPublicValues = publicValues(statement);
  for (let index = 0; index < expectedPublicValues.length; index++) {
    if (suppliedPublicValues[index] !== expectedPublicValues[index]) {
      throw new Error("public values do not match withdrawal statement");
    }
  }

  const proof = asRecord(request.proof, "proof");
  requireExactKeys(proof, ["partA", "partB"], "proof");
  const statementKey = deriveStatementKey(parameterId, expectedPublicValues);
  const partA = parseProofPart(proof.partA, "A", parameterId, expectedPublicValues, statementKey);
  const coreProofId = bytesFromHex(deriveCoreProofId(statementKey, partA.payload), 32);
  const partB = parseProofPart(proof.partB, "B", parameterId, expectedPublicValues, statementKey);
  if (partB.proofId === undefined || !sameBytes(partB.proofId, coreProofId)) {
    throw new Error("proof.partB core proof ID does not bind proof.partA");
  }
  if (!sameBytes(partA.globalDigest, partB.globalDigest)) {
    throw new Error("proof parts have mismatched global data digest");
  }
  if (!sameBytes(partA.checkpointDigest, partB.checkpointDigest)) {
    throw new Error("proof parts have mismatched checkpoint digests");
  }

  return Object.freeze({
    pool: requestPool.hex,
    registry: requestRegistry.hex,
    parameterId,
    root,
    nullifierHash,
    recipient: parsedRecipient.bytes,
    relayer: parsedRelayer.bytes,
    relayerHex: parsedRelayer.hex,
    fee,
    deadline,
    publicValues: expectedPublicValues,
    statementKey,
    proofPartA: partA.payload,
    proofPartB: partB.payload,
    verificationId: bytesFromHex(deriveVerificationId(hex(coreProofId), requestPool.hex), 32),
  });
}

function encodeWithdrawalFields(request: ValidatedRequest): Uint8Array {
  return concat(
    digestBytes(request.root),
    digestBytes(request.nullifierHash),
    abiAddress(request.recipient),
    abiAddress(request.relayer),
    uintWord(request.fee),
  );
}

function encodeBeginWithdrawal(request: ValidatedRequest): Uint8Array {
  return concat(
    functionSelector("beginWithdrawal(((bytes32,bytes32),(bytes32,bytes32),address,address,uint256),bytes)"),
    encodeWithdrawalFields(request),
    uintWord(8n * 32n),
    abiBytes(request.proofPartA),
  );
}

function encodeWithdrawal(request: ValidatedRequest, verificationId: Uint8Array): Uint8Array {
  return concat(
    functionSelector("withdraw(((bytes32,bytes32),(bytes32,bytes32),address,address,uint256),bytes32,bytes)"),
    encodeWithdrawalFields(request),
    verificationId,
    uintWord(9n * 32n),
    abiBytes(request.proofPartB),
  );
}

function verificationIdFromReceipt(receipt: TransactionReceipt, request: ValidatedRequest): Uint8Array {
  if (!(receipt.status === 1 || receipt.status === "0x1" || receipt.status === "0x01")) {
    throw new Error("part A transaction did not succeed");
  }
  if (receipt.to === null || address(receipt.to, "receipt.to").hex !== request.pool) {
    throw new Error("part A receipt is not from the configured pool transaction");
  }
  const matchingLogs = receipt.logs.filter((log) => {
    if (address(log.address, "receipt log address").hex !== request.registry) return false;
    return log.topics[0]?.toLowerCase() === VERIFICATION_STARTED_TOPIC.toLowerCase();
  });
  if (matchingLogs.length !== 1) throw new Error("part A receipt must contain exactly one VerificationStarted event");
  const topics = matchingLogs[0]!.topics;
  if (topics.length !== 4) throw new Error("malformed VerificationStarted event");
  const verificationId = bytesFromHex(topics[1]!, 32);
  if (!sameBytes(verificationId, request.verificationId)) {
    throw new Error("VerificationStarted verification ID does not match proof and consumer");
  }
  if (verificationId.every((byte) => byte === 0)) throw new Error("verification ID cannot be zero");
  const consumerWord = bytesFromHex(topics[2]!, 32);
  if (!consumerWord.slice(0, 12).every((byte) => byte === 0)) throw new Error("event consumer is not canonical");
  if (!sameBytes(consumerWord.slice(12), bytesFromHex(request.pool, 20))) {
    throw new Error("VerificationStarted consumer does not match pool");
  }
  if (hex(bytesFromHex(topics[3]!, 32)) !== request.statementKey) {
    throw new Error("VerificationStarted statement key mismatch");
  }
  return verificationId;
}

/**
 * Stateful two-transaction withdrawal builder. Part B cannot be produced until a successful,
 * statement-bound part A receipt has been supplied, and no third transaction can be produced.
 */
export class WithdrawalSubmission {
  readonly #request: ValidatedRequest;
  #stage: 0 | 1 | 2 = 0;

  private constructor(request: ValidatedRequest) {
    this.#request = request;
  }

  static create(input: unknown, policy: RelayerPolicy, nowSeconds = BigInt(Math.floor(Date.now() / 1000))): WithdrawalSubmission {
    return new WithdrawalSubmission(validateRequest(input, policy, nowSeconds));
  }

  partA(): RelayerTransaction {
    if (this.#stage !== 0) throw new Error("part A must be the first and only first-phase transaction");
    this.#stage = 1;
    return Object.freeze({
      phase: "A",
      order: 1,
      from: this.#request.relayerHex,
      to: this.#request.pool,
      data: hex(encodeBeginWithdrawal(this.#request)),
    });
  }

  partB(receipt: TransactionReceipt, nowSeconds = BigInt(Math.floor(Date.now() / 1000))): RelayerTransaction {
    if (this.#stage !== 1) throw new Error("part B requires part A to be submitted first");
    if (this.#request.deadline <= nowSeconds) throw new Error("request deadline expired before part B");
    const verificationId = verificationIdFromReceipt(receipt, this.#request);
    this.#stage = 2;
    return Object.freeze({
      phase: "B",
      order: 2,
      from: this.#request.relayerHex,
      to: this.#request.pool,
      data: hex(encodeWithdrawal(this.#request, verificationId)),
    });
  }
}

let rpcId = 0;
async function rpc<T>(rpcUrl: string, method: string, params: unknown[]): Promise<T> {
  const response = await fetch(rpcUrl, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: ++rpcId, method, params }),
  });
  if (!response.ok) throw new Error(`RPC HTTP ${response.status}`);
  const envelope = await response.json() as { result?: T; error?: { message: string } };
  if (envelope.error) throw new Error(envelope.error.message);
  if (envelope.result === undefined) throw new Error(`RPC ${method} returned no result`);
  return envelope.result;
}

async function ethCall(rpcUrl: string, to: string, signature: string): Promise<Uint8Array> {
  const result = await rpc<string>(rpcUrl, "eth_call", [{ to, data: hex(functionSelector(signature)) }, "latest"]);
  return bytesFromHex(result);
}

async function waitForReceipt(rpcUrl: string, transactionHash: string): Promise<TransactionReceipt> {
  for (;;) {
    const receipt = await rpc<TransactionReceipt | null>(rpcUrl, "eth_getTransactionReceipt", [transactionHash]);
    if (receipt !== null) return receipt;
    const { promise, resolve } = Promise.withResolvers<void>();
    setTimeout(resolve, 1_000);
    await promise;
  }
}

function requestAddress(input: unknown, field: "pool"): `0x${string}` {
  const request = asRecord(input, "request");
  return address(request[field], field).hex;
}

export async function runRelayerCli(argv = process.argv.slice(2), environment = process.env): Promise<void> {
  const [requestPath] = argv;
  const rpcUrl = environment.RPC_URL;
  const relayer = environment.RELAYER_FROM;
  if (!requestPath || !rpcUrl || !relayer) {
    throw new Error("usage: RPC_URL=... RELAYER_FROM=0x... pqtc-relayer request.json");
  }
  const input: unknown = JSON.parse(await readFile(requestPath, "utf8"));
  const pool = requestAddress(input, "pool");
  const [chainHex, scopeResult, parameterResult, denominationResult, registryResult] = await Promise.all([
    rpc<string>(rpcUrl, "eth_chainId", []),
    ethCall(rpcUrl, pool, "scope()"),
    ethCall(rpcUrl, pool, "parameterId()"),
    ethCall(rpcUrl, pool, "denomination()"),
    ethCall(rpcUrl, pool, "verificationRegistry()"),
  ]);
  if (scopeResult.length !== 64 || parameterResult.length !== 64 || denominationResult.length !== 32 || registryResult.length !== 32) {
    throw new Error("pool returned malformed protocol metadata");
  }
  if (!registryResult.slice(0, 12).every((byte) => byte === 0)) throw new Error("pool returned noncanonical registry address");
  const submission = WithdrawalSubmission.create(input, {
    chainId: BigInt(chainHex),
    pool,
    registry: hex(registryResult.slice(12)),
    scope: hex(scopeResult),
    parameterId: hex(parameterResult),
    denomination: BigInt(hex(denominationResult)),
    relayer,
  });
  const partA = submission.partA();
  const partAHash = await rpc<string>(rpcUrl, "eth_sendTransaction", [{ from: partA.from, to: partA.to, data: partA.data }]);
  const receipt = await waitForReceipt(rpcUrl, partAHash);
  const partB = submission.partB(receipt);
  const partBHash = await rpc<string>(rpcUrl, "eth_sendTransaction", [{ from: partB.from, to: partB.to, data: partB.data }]);
  process.stdout.write(`${JSON.stringify({ partA: partAHash, partB: partBHash })}\n`);
}

const isMain = process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) await runRelayerCli();
```

</details>

## `packages/sdk/test/domains.test.ts`

- Bytes: 1,336
- SHA-256: `dba50f5867f7c3b008974e2b1571076addb3994b5131ced916f48d46ab789ca4`

<details><summary>Complete file</summary>

```typescript
import assert from "node:assert/strict";
import test from "node:test";

import {
  applicationDomains,
  domains,
  coordinationDomains,
  isApplicationDomain,
  isProofDomain,
  proofDomains,
} from "../dist/domains.js";

test("protocol-v3 application, proof, and coordination hash domains stay separated", () => {
  const application = Object.values(applicationDomains);
  const proof = Object.values(proofDomains);
  assert.equal(application.length, 7);
  assert.equal(application.some((domain) => proof.includes(domain)), false);
  assert.equal(proof.length, 6);
  for (const domain of application) {
    assert.equal(isApplicationDomain(domain), true);
    assert.equal(isProofDomain(domain), false);
  }
  for (const domain of proof) {
    assert.equal(isProofDomain(domain), true);
    assert.equal(isApplicationDomain(domain), false);
  }
  assert.deepEqual(domains, { ...applicationDomains, ...proofDomains });
  assert.deepEqual(coordinationDomains, {
    STATEMENT: "PQTC.V3.STATEMENT",
    PROOF: "PQTC.V3.PROOF",
    CHECKPOINT: "PQTC.V3.CHECKPOINT",
    VERIFICATION: "PQTC.V3.VERIFICATION",
  });
  assert.equal(Object.isFrozen(applicationDomains), true);
  assert.equal(Object.isFrozen(proofDomains), true);
  assert.equal(Object.isFrozen(coordinationDomains), true);
  assert.equal(Object.isFrozen(domains), true);
});
```

</details>

## `packages/sdk/test/relayer.test.ts`

- Bytes: 13,966
- SHA-256: `1341666c147255bb3530179af23e16c80596d20a0fa8a17b42c69f93f01b630d`

<details><summary>Complete file</summary>

```typescript
import assert from "node:assert/strict";
import test from "node:test";
import { keccak_256 } from "@noble/hashes/sha3.js";

import {
  BABY_BEAR_MODULUS,
  bytesFromHex,
  digestBytes,
  digestFromBytes,
  hex,
  payoutDigest,
  publicValues,
  statementHash,
} from "../dist/index.js";
import {
  WithdrawalSubmission,
  deriveCoreProofId,
  deriveStatementKey,
  deriveVerificationId,
  type RelayerPolicy,
  type TransactionReceipt,
  type WithdrawalRequestV3,
} from "../dist/relayer.js";

const encoder = new TextEncoder();
const POOL = "0x1111111111111111111111111111111111111111";
const REGISTRY = "0x2222222222222222222222222222222222222222";
const RECIPIENT = "0x3333333333333333333333333333333333333333";
const RELAYER = "0x4444444444444444444444444444444444444444";
const VERIFICATION_STARTED_TOPIC = hex(keccak_256(encoder.encode(
  "VerificationStarted(bytes32,address,bytes32)",
)));

function digest(seed: number): `0x${string}` {
  const bytes = new Uint8Array(64);
  const view = new DataView(bytes.buffer);
  for (let index = 0; index < 16; index++) view.setUint32(index * 4, seed + index, false);
  return hex(bytes);
}
function selector(signature: string): `0x${string}` {
  return hex(keccak_256(encoder.encode(signature)).slice(0, 4));
}
function proofPart(
  kind: "A" | "B",
  parameterId: string,
  values: Uint32Array,
  statementKey: string,
  coreProofId?: string,
): `0x${string}` {
  const commonLength = 338;
  const globalLength = 9_208;
  const queryCount = 32;
  const halfCount = 16;
  const checkpointLength = 452 + queryCount * 4;
  const proofIdLength = kind === "B" ? 32 : 0;
  const bytes = new Uint8Array(
    commonLength + proofIdLength + 32 + globalLength + checkpointLength + 4 + halfCount * 4 + 1 + 4,
  );
  const view = new DataView(bytes.buffer);
  bytes.set(encoder.encode(kind === "A" ? "PQTCPA03" : "PQTCPB03"));
  view.setUint16(8, 3, false);
  view.setUint8(10, 3);
  view.setUint8(11, 9);
  view.setUint8(12, 9);
  view.setUint8(13, 4);
  view.setUint16(14, queryCount, false);
  bytes.set(bytesFromHex(parameterId, 64), 16);
  view.setUint16(80, 64, false);
  for (let index = 0; index < values.length; index++) view.setUint32(82 + index * 4, values[index]!, false);

  if (kind === "B") bytes.set(bytesFromHex(coreProofId!, 32), commonLength);
  const globalDigestOffset = commonLength + proofIdLength;
  const globalDataOffset = globalDigestOffset + 32;
  const globalData = new Uint8Array(globalLength);
  for (let index = 0; index < globalData.length; index++) globalData[index] = index & 0xff;
  const globalDigest = keccak_256(globalData);
  bytes.set(globalDigest, globalDigestOffset);
  bytes.set(globalData, globalDataOffset);

  const checkpointOffset = globalDataOffset + globalLength;
  bytes.set(globalDigest, checkpointOffset + 32);
  view.setUint16(checkpointOffset + 320, queryCount, false);
  for (let index = 0; index < queryCount; index++) {
    view.setUint32(checkpointOffset + 322 + index * 4, index, false);
  }
  view.setUint16(checkpointOffset + 450, queryCount, false);
  for (let index = 0; index < queryCount; index++) {
    view.setUint32(checkpointOffset + 452 + index * 4, index, false);
  }
  const checkpointEnd = checkpointOffset + checkpointLength;
  const checkpointLabel = new Uint8Array(32);
  checkpointLabel.set(encoder.encode("PQTC.V3.CHECKPOINT"));
  bytes.set(
    keccak_256(Buffer.concat([
      checkpointLabel,
      bytesFromHex(statementKey, 32),
      keccak_256(bytes.slice(checkpointOffset + 32, checkpointEnd)),
    ])),
    checkpointOffset,
  );

  view.setUint16(checkpointEnd, kind === "A" ? 0 : halfCount, false);
  view.setUint16(checkpointEnd + 2, halfCount, false);
  for (let index = 0; index < halfCount; index++) {
    view.setUint32(checkpointEnd + 4 + index * 4, (kind === "A" ? 0 : halfCount) + index, false);
  }
  bytes.set(
    bytesFromHex(kind === "A" ? "0x50414533" : "0x50424533"),
    bytes.length - 4,
  );
  return hex(bytes);
}

function makeFixture(): {
  request: WithdrawalRequestV3;
  policy: RelayerPolicy;
  statementKey: `0x${string}`;
  verificationId: `0x${string}`;
} {
  const scope = digest(10);
  const parameterId = `0x${"ff".repeat(64)}`;
  const root = digest(50);
  const nullifierHash = digest(70);
  const statement = {
    scope: digestFromBytes(bytesFromHex(scope, 64)),
    root: digestFromBytes(bytesFromHex(root, 64)),
    nullifierHash: digestFromBytes(bytesFromHex(nullifierHash, 64)),
    payoutDigest: payoutDigest(bytesFromHex(RECIPIENT, 20), bytesFromHex(RELAYER, 20), 7n),
  };
  const statementId = hex(digestBytes(statementHash(statement)));
  const values = publicValues(statement);
  const statementKey = deriveStatementKey(digestFromBytes(bytesFromHex(parameterId, 64)), values);
  const partA = proofPart("A", parameterId, values, statementKey);
  const coreProofId = deriveCoreProofId(statementKey, bytesFromHex(partA));
  const verificationId = deriveVerificationId(coreProofId, POOL);
  return {
    request: {
      version: 3,
      chainId: "11155111",
      pool: POOL,
      registry: REGISTRY,
      scope,
      parameterId,
      root,
      nullifierHash,
      recipient: RECIPIENT,
      relayer: RELAYER,
      fee: "7",
      deadline: "2000",
      statementId,
      publicValues: [...values],
      proof: { partA, partB: proofPart("B", parameterId, values, statementKey, coreProofId) },
    },
    policy: {
      chainId: 11_155_111n,
      pool: POOL,
      registry: REGISTRY,
      scope,
      parameterId,
      denomination: 100n,
      relayer: RELAYER,
    },
    statementKey,
    verificationId,
  };
}

function receipt(statementKey: string, verificationId: string, overrides: Partial<TransactionReceipt> = {}): TransactionReceipt {
  return {
    status: "0x1",
    to: POOL,
    logs: [{
      address: REGISTRY,
      topics: [
        VERIFICATION_STARTED_TOPIC,
        verificationId,
        `0x${"00".repeat(12)}${POOL.slice(2)}`,
        statementKey,
      ],
    }],
    ...overrides,
  };
}

test("withdrawal submission exposes exactly two ordered transactions", () => {
  const { request, policy, statementKey, verificationId } = makeFixture();
  const submission = WithdrawalSubmission.create(request, policy, 1_000n);

  assert.throws(() => submission.partB(receipt(statementKey, verificationId), 1_000n), /requires part A/);
  const partA = submission.partA();
  assert.deepEqual({ phase: partA.phase, order: partA.order, to: partA.to }, {
    phase: "A", order: 1, to: POOL,
  });
  assert.equal(
    partA.data.slice(0, 10),
    selector("beginWithdrawal(((bytes32,bytes32),(bytes32,bytes32),address,address,uint256),bytes)"),
  );
  assert.throws(() => submission.partA(), /first-phase/);

  const partB = submission.partB(receipt(statementKey, verificationId), 1_000n);
  assert.deepEqual({ phase: partB.phase, order: partB.order, to: partB.to }, {
    phase: "B", order: 2, to: POOL,
  });
  assert.equal(
    partB.data.slice(0, 10),
    selector("withdraw(((bytes32,bytes32),(bytes32,bytes32),address,address,uint256),bytes32,bytes)"),
  );
  assert.ok(partB.data.includes(verificationId.slice(2)));
  assert.throws(() => submission.partB(receipt(statementKey, verificationId), 1_000n), /requires part A/);
});

test("swapped proof parts are rejected before calldata is returned", () => {
  const { request, policy } = makeFixture();
  const swapped = structuredClone(request);
  [swapped.proof.partA, swapped.proof.partB] = [swapped.proof.partB, swapped.proof.partA];
  assert.throws(() => WithdrawalSubmission.create(swapped, policy, 1_000n), /swapped/);
});

test("each proof part authenticates its exact 9208-byte globals and 16-query half", () => {
  const { request, policy } = makeFixture();
  const badGlobal = structuredClone(request);
  const partA = bytesFromHex(badGlobal.proof.partA);
  partA[338 + 32 + 9_207] ^= 1;
  badGlobal.proof.partA = hex(partA);
  assert.throws(() => WithdrawalSubmission.create(badGlobal, policy, 1_000n), /global data digest mismatch/);

  const badQueryCount = structuredClone(request);
  const badHeader = bytesFromHex(badQueryCount.proof.partA);
  new DataView(badHeader.buffer).setUint16(14, 48, false);
  badQueryCount.proof.partA = hex(badHeader);
  assert.throws(() => WithdrawalSubmission.create(badQueryCount, policy, 1_000n), /32 queries/);

  const badHalf = structuredClone(request);
  const badHalfBytes = bytesFromHex(badHalf.proof.partB);
  const partBHalfOffset = 338 + 32 + 32 + 9_208 + 452 + 32 * 4;
  new DataView(badHalfBytes.buffer).setUint16(partBHalfOffset, 0, false);
  badHalf.proof.partB = hex(badHalfBytes);
  assert.throws(() => WithdrawalSubmission.create(badHalf, policy, 1_000n), /second 16 queries/);
});

test("statement and receipt bindings are checked before part B calldata", () => {
  const { request, policy, statementKey, verificationId } = makeFixture();
  const mismatched = structuredClone(request);
  const mismatchedPartB = bytesFromHex(mismatched.proof.partB);
  const view = new DataView(mismatchedPartB.buffer);
  view.setUint32(82, view.getUint32(82, false) + 1, false);
  mismatched.proof.partB = hex(mismatchedPartB);
  assert.throws(() => WithdrawalSubmission.create(mismatched, policy, 1_000n), /statement public values mismatch/);

  const wrongParameter = structuredClone(request);
  const parameterPartB = bytesFromHex(wrongParameter.proof.partB);
  parameterPartB[16] ^= 1;
  wrongParameter.proof.partB = hex(parameterPartB);
  assert.throws(() => WithdrawalSubmission.create(wrongParameter, policy, 1_000n), /parameter ID mismatch/);

  const submission = WithdrawalSubmission.create(request, policy, 1_000n);
  submission.partA();
  assert.throws(
    () => submission.partB(receipt(statementKey, `0x${"99".repeat(32)}`), 1_000n),
    /verification ID does not match/,
  );
  assert.throws(
    () => submission.partB(receipt(`0x${"99".repeat(32)}`, verificationId), 1_000n),
    /statement key mismatch/,
  );
  assert.doesNotThrow(() => submission.partB(receipt(statementKey, verificationId), 1_000n));
});

test("part B requires the successful pool receipt and exact registry event", () => {
  const { request, policy, statementKey, verificationId } = makeFixture();
  const malformed: Array<[TransactionReceipt, RegExp]> = [
    [receipt(statementKey, verificationId, { status: "0x0" }), /did not succeed/],
    [receipt(statementKey, verificationId, { to: RECIPIENT }), /configured pool transaction/],
    [receipt(statementKey, verificationId, {
      logs: [{
        address: POOL,
        topics: [
          VERIFICATION_STARTED_TOPIC,
          verificationId,
          `0x${"00".repeat(12)}${POOL.slice(2)}`,
          statementKey,
        ],
      }],
    }), /exactly one VerificationStarted/],
    [receipt(statementKey, verificationId, {
      logs: [{
        address: REGISTRY,
        topics: [
          VERIFICATION_STARTED_TOPIC,
          verificationId,
          `0x${"00".repeat(12)}${RELAYER.slice(2)}`,
          statementKey,
        ],
      }],
    }), /consumer does not match pool/],
  ];
  for (const [candidate, expected] of malformed) {
    const submission = WithdrawalSubmission.create(request, policy, 1_000n);
    submission.partA();
    assert.throws(() => submission.partB(candidate, 1_000n), expected);
  }
});

test("noncanonical digest and public-value limbs are rejected", () => {
  const { request, policy } = makeFixture();
  const noncanonicalDigest = structuredClone(request);
  const bytes = bytesFromHex(noncanonicalDigest.root, 64);
  new DataView(bytes.buffer).setUint32(7 * 4, BABY_BEAR_MODULUS, false);
  noncanonicalDigest.root = hex(bytes);
  assert.throws(() => WithdrawalSubmission.create(noncanonicalDigest, policy, 1_000n), /limb 7 is not canonical/);

  const noncanonicalValues = structuredClone(request);
  noncanonicalValues.publicValues[12] = BABY_BEAR_MODULUS;
  assert.throws(() => WithdrawalSubmission.create(noncanonicalValues, policy, 1_000n), /publicValues\[12\] is not canonical/);

  const noncanonicalProof = structuredClone(request);
  const partA = bytesFromHex(noncanonicalProof.proof.partA);
  new DataView(partA.buffer).setUint32(82 + 12 * 4, BABY_BEAR_MODULUS, false);
  noncanonicalProof.proof.partA = hex(partA);
  assert.throws(() => WithdrawalSubmission.create(noncanonicalProof, policy, 1_000n), /public value 12 is not canonical/);
});

test("v2 requests, v2 proofs, and staged transaction fields are rejected", () => {
  const { request, policy } = makeFixture();
  const v2 = { ...request, version: 2 };
  assert.throws(() => WithdrawalSubmission.create(v2, policy, 1_000n), /protocol version 3/);
  const v2Proof = structuredClone(request);
  const partA = bytesFromHex(v2Proof.proof.partA);
  partA.set(encoder.encode("PQTCPA02"));
  new DataView(partA.buffer).setUint16(8, 2, false);
  v2Proof.proof.partA = hex(partA);
  assert.throws(() => WithdrawalSubmission.create(v2Proof, policy, 1_000n), /magic|proof version 3/);
  const staged = { ...request, transactions: [{ to: REGISTRY, data: "0x" }] };
  assert.throws(() => WithdrawalSubmission.create(staged, policy, 1_000n), /unsupported field transactions/);
});

test("chain, pool, scope, payout, fee, relayer, and deadline policy checks remain strict", () => {
  const { request, policy } = makeFixture();
  const cases: Array<[string, WithdrawalRequestV3, RegExp]> = [
    ["chain", { ...request, chainId: "1" }, /connected chain/],
    ["pool", { ...request, pool: RECIPIENT }, /configured pool/],
    ["scope", { ...request, scope: digest(101) }, /pool scope/],
    ["recipient", { ...request, recipient: RELAYER }, /independent/],
    ["relayer", { ...request, relayer: RECIPIENT }, /configured relayer/],
    ["fee", { ...request, fee: "101" }, /fee exceeds/],
    ["deadline", { ...request, deadline: "1000" }, /expired/],
  ];
  for (const [name, candidate, expected] of cases) {
    assert.throws(() => WithdrawalSubmission.create(candidate, policy, 1_000n), expected, name);
  }
});
```

</details>

## `packages/sdk/test/vectors.test.ts`

- Bytes: 9,671
- SHA-256: `7b8718e9f0bc9d8b8c22edf5cdf6c4a141e9a0a52cf345ff9fa28743c17226b2`

<details><summary>Complete file</summary>

```typescript
import assert from "node:assert/strict";
import test from "node:test";
import { keccak_256 } from "@noble/hashes/sha3.js";

import {
  BABY_BEAR_MODULUS,
  MerkleTree,
  NoteSecretTracker,
  commitment,
  decodeCompactProof,
  digestBytes,
  digestElements,
  digestEqual,
  digestFromBytes,
  domains,
  emptyLeaf,
  encodeCompactProof,
  encodeDepositCalldata,
  encodeNote,
  hex,
  k512,
  merkleNode,
  newNote,
  nullifierHash,
  p2bb512,
  parseNote,
  payoutDigest,
  poseidon2BabyBear16,
  publicValues,
  rootFromPath,
  secretBytes,
  secretFromBytes,
  scope,
  statementHash,
} from "../dist/index.js";

test("matches the pinned Plonky3 BabyBear width-16 permutation", () => {
  const input = Array.from({ length: 16 }, (_, index) => index);
  const expected = [
    1906786279, 1737026427, 1959749225, 700325316, 1638050605, 1021608788, 1726691001,
    1761127344, 1552405120, 417318995, 36799261, 1215172152, 614923223, 1300746575,
    957311597, 304856115,
  ];
  assert.deepEqual([...poseidon2BabyBear16(input)], expected);
  assert.equal(
    hex(digestBytes(p2bb512(domains.SCOPE, 32, 0, input))),
    "0x192285c83ad82d235f4020c4185fb99a5d7a4574217a7fa5097c082c4c905cfd69df098f455618e612d7819f26e68e4d5ff4842c4d5177ae479caee05752c4bd",
  );
});

test("P2BB512 digests are canonical and bind domain, byte length, and auxiliary level", () => {
  const payload = [0x0102, 0x0300];
  const digest = p2bb512(domains.NOTE, 3, 0, payload);
  assert.equal(digestBytes(digest).length, 64);
  assert.deepEqual([...digestElements(digest)], [...digestElements(digestFromBytes(digestBytes(digest)))]);
  for (const element of digestElements(digest)) assert.ok(element < BABY_BEAR_MODULUS);

  assert.equal(digestEqual(digest, p2bb512(domains.NULLIFIER, 3, 0, payload)), false);
  assert.equal(digestEqual(digest, p2bb512(domains.NOTE, 4, 0, payload)), false);
  assert.equal(digestEqual(digest, p2bb512(domains.NOTE, 3, 1, payload)), false);

  const noncanonicalBytes = new Uint8Array(64);
  new DataView(noncanonicalBytes.buffer).setUint32(0, BABY_BEAR_MODULUS, false);
  assert.throws(() => emptyLeaf(digestFromBytes(noncanonicalBytes)), /not canonical/);
});

test("application helpers use canonical digest elements and bind Merkle levels", () => {
  const parameterId = {
    left: new Uint8Array(32).fill(0xa5),
    right: new Uint8Array(32).fill(0x5a),
  };
  const poolScope = scope({
    chainId: 11_155_111n,
    pool: new Uint8Array(20).fill(1),
    denomination: 1_000_000_000_000_000_000n,
    parameterId,
  });
  const noteSecret = new Uint32Array(8).fill(2);
  const noteTrapdoor = new Uint32Array(8).fill(3);
  const noteCommitment = commitment(poolScope, noteSecret, noteTrapdoor);
  const nullifier = nullifierHash(poolScope, noteSecret);
  const zero = emptyLeaf(poolScope);
  assert.equal(digestEqual(merkleNode(0, noteCommitment, zero), merkleNode(1, noteCommitment, zero)), false);

  const tree = new MerkleTree(poolScope);
  const inserted = tree.insert(noteCommitment);
  assert.ok(digestEqual(rootFromPath(noteCommitment, tree.path(inserted.leafIndex)), inserted.root));

  const payout = payoutDigest(new Uint8Array(20).fill(4), new Uint8Array(20).fill(5), 7n);
  const statement = { scope: poolScope, root: inserted.root, nullifierHash: nullifier, payoutDigest: payout };
  assert.equal(publicValues(statement).length, 64);
  assert.equal(digestBytes(statementHash(statement)).length, 64);
  for (const value of publicValues(statement)) assert.ok(value < BABY_BEAR_MODULUS);

  const previousVersion = scope({
    chainId: 11_155_111n,
    pool: new Uint8Array(20).fill(1),
    denomination: 1_000_000_000_000_000_000n,
    protocolVersion: 2,
    parameterId,
  });
  assert.equal(digestEqual(poolScope, previousVersion), false);
});

test("v3 application hashes match the Rust canonical-secret vector", () => {
  const parameterId = k512(domains.PARAMETER_MANIFEST, new TextEncoder().encode("manifest"));
  const poolScope = scope({
    chainId: 11_155_111n,
    pool: new Uint8Array(20).fill(1),
    denomination: BigInt(`0x${"02".repeat(32)}`),
    parameterId,
  });
  const nullifierSecret = Uint32Array.of(3, 5, 7, 11, 13, 17, 19, 23);
  const trapdoor = Uint32Array.of(29, 31, 37, 41, 43, 47, 53, 59);
  assert.equal(
    hex(digestBytes(poolScope)),
    "0x29d774fa067d5844644966e1326483b24085e8fe771fdf570d64b61815b83cdf31d6b62414ead4750956548b6643d0831fdba8e822e0ada718ffd4d3470a56c7",
  );
  assert.equal(
    hex(digestBytes(commitment(poolScope, nullifierSecret, trapdoor))),
    "0x174026330a3b3def58a2547403d04234035843a84b7814a330ff65e4049592cc69da09314cc70f0d6ead8d1d38a5dd2f45f5e9741b7e063f24acd369233a1979",
  );
  assert.equal(
    hex(digestBytes(nullifierHash(poolScope, nullifierSecret))),
    "0x703e079c63caf3b65227079e3201df600319e2fb294395ae278a63183b0b8fe2078b9d397692e1e14e7952cd3f80d97301a420444d733f0b2fb440fc18deaba6",
  );
});

test("note codec v3 uses eight canonical BabyBear limbs and detects corruption", () => {
  const note = {
    chainId: 11_155_111n,
    pool: new Uint8Array(20).fill(1),
    parameterId: { left: new Uint8Array(32).fill(2), right: new Uint8Array(32).fill(3) },
    nullifierSecret: Uint32Array.of(0, 1, 0x01020304, BABY_BEAR_MODULUS - 1, 5, 6, 7, 8),
    trapdoor: Uint32Array.of(9, 10, 11, 12, 13, 14, 15, 16),
  };
  const encoded = encodeNote(note);
  assert.ok(encoded.startsWith("pqtc-note-v3:"));
  assert.deepEqual(parseNote(encoded), note);
  assert.deepEqual(secretFromBytes(secretBytes(note.nullifierSecret)), note.nullifierSecret);
  assert.equal(
    hex(secretBytes(Uint32Array.of(0x01020304, 0, 1, 2, 3, 4, 5, BABY_BEAR_MODULUS - 1))),
    "0x0102030400000000000000010000000200000003000000040000000578000000",
  );
  assert.deepEqual(
    secretFromBytes(secretBytes([0n, 1n, 2n, 3n, 4n, 5n, 6n, 7n])),
    Uint32Array.of(0, 1, 2, 3, 4, 5, 6, 7),
  );
  const raw = Buffer.from(encoded.slice("pqtc-note-v3:".length), "base64url");
  raw[100]! ^= 1;
  assert.throws(() => parseNote(`pqtc-note-v3:${raw.toString("base64url")}`), /checksum/);
  assert.throws(() => parseNote(encoded.replace("pqtc-note-v3:", "pqtc-note-v2:")), /prefix/);
  const noncanonicalRaw = Buffer.from(encoded.slice("pqtc-note-v3:".length), "base64url");
  new DataView(
    noncanonicalRaw.buffer,
    noncanonicalRaw.byteOffset,
    noncanonicalRaw.byteLength,
  ).setUint32(98, BABY_BEAR_MODULUS, false);
  noncanonicalRaw.set(
    keccak_256(Buffer.concat([Uint8Array.of(0, domains.NOTE), noncanonicalRaw.subarray(0, 162)])),
    162,
  );
  assert.throws(
    () => parseNote(`pqtc-note-v3:${noncanonicalRaw.toString("base64url")}`),
    /nullifierSecret limb 0 is not canonical/,
  );
  assert.throws(() => encodeNote({ ...note, nullifierSecret: new Uint32Array(32).fill(4) }), /8 limbs/);
  assert.throws(
    () => encodeNote({ ...note, trapdoor: [0, 1, 2, 3, 4, 5, 6, BABY_BEAR_MODULUS] }),
    /limb 7 is not canonical/,
  );
  const tracker = new NoteSecretTracker();
  tracker.register(note);
  assert.throws(() => tracker.register({ ...note, trapdoor: new Uint32Array(8).fill(9) }), /already used/);
});

test("new notes rejection-sample canonical secrets", () => {
  const parameterId = { left: new Uint8Array(32).fill(1), right: new Uint8Array(32).fill(2) };
  for (let index = 0; index < 64; index++) {
    const note = newNote(1n, new Uint8Array(20).fill(3), parameterId);
    assert.equal(note.nullifierSecret.length, 8);
    assert.equal(note.trapdoor.length, 8);
    for (let limb = 0; limb < 8; limb++) {
      assert.ok(Number(note.nullifierSecret[limb]) < BABY_BEAR_MODULUS);
      assert.ok(Number(note.trapdoor[limb]) < BABY_BEAR_MODULUS);
    }
  }
});

test("integer boundaries and proof-only Keccak branches remain binding", () => {
  const parameterId = { left: new Uint8Array(32).fill(1), right: new Uint8Array(32).fill(2) };
  assert.doesNotThrow(() => scope({ chainId: (1n << 64n) - 1n, pool: new Uint8Array(20), denomination: (1n << 256n) - 1n, parameterId }));
  assert.throws(() => scope({ chainId: 1n << 64n, pool: new Uint8Array(20), denomination: 0n, parameterId }), /does not fit/);
  const value = k512(domains.PROOF_LEAF, new Uint8Array());
  assert.notDeepEqual(value.left, value.right);
});

test("compact proof v3 envelope round-trips 64 canonical public values", () => {
  const proof = {
    parameterId: {
      left: new Uint8Array(32).fill(0x11),
      right: new Uint8Array(32).fill(0x22),
    },
    publicValues: new Uint32Array(64).fill(1234),
    starkPayload: Uint8Array.of(1, 2, 3, 4, 5),
  };
  const encoded = encodeCompactProof(proof);
  assert.equal(new TextDecoder().decode(encoded.slice(0, 8)), "PQTCSTK3");
  assert.deepEqual(decodeCompactProof(encoded), proof);
  assert.deepEqual(encodeCompactProof(decodeCompactProof(encoded)), encoded);
  for (let length = 0; length < encoded.length; length++) {
    assert.throws(() => decodeCompactProof(encoded.slice(0, length)));
  }
  const v2 = encoded.slice();
  v2.set(new TextEncoder().encode("PQTCSTK2"));
  new DataView(v2.buffer).setUint16(8, 2, false);
  assert.throws(() => decodeCompactProof(v2), /magic|version/);
  assert.throws(() => decodeCompactProof(new Uint8Array([...encoded, 0])), /trailing/);
  const noncanonical = { ...proof, publicValues: proof.publicValues.slice() };
  noncanonical.publicValues[0] = BABY_BEAR_MODULUS;
  assert.throws(() => encodeCompactProof(noncanonical), /not canonical/);
});

test("deposit calldata uses canonical tuple ABI", () => {
  const digest = digestFromBytes(new Uint8Array(64));
  const deposit = encodeDepositCalldata(digest);
  assert.equal(hex(deposit.slice(0, 4)), "0xdc39710f");
  assert.equal(deposit.length, 4 + 64);
});
```

</details>

## `packages/sdk/tsconfig.json`

- Bytes: 347
- SHA-256: `a2ff4eb744682b923b5b2d6791abe5f04f21fb8d3ea12c1f2e452fa9de44a95a`

<details><summary>Complete file</summary>

```json
{
  "compilerOptions": {
    "target": "ES2024",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "declaration": true,
    "outDir": "dist",
    "rootDir": "src",
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "verbatimModuleSyntax": true
  },
  "include": ["src/**/*.ts"]
}
```

</details>

## `script/DeploySepolia.s.sol`

- Bytes: 2,031
- SHA-256: `67e244bb058b1d15ac3a25657323dd2b27413be2a09b4afccbc1e811a0c3497d`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Script} from "forge-std/Script.sol";
import {Digest512} from "../contracts/src/libraries/Digest512.sol";
import {PQTCAirStageVerifier} from "../contracts/src/verifier/PQTCAirStageVerifier.sol";
import {PQTCQueryVerifier} from "../contracts/src/verifier/PQTCQueryVerifier.sol";
import {PQTCVerificationRegistry} from "../contracts/src/PQTCVerificationRegistry.sol";
import {PQTCClassicPool} from "../contracts/src/PQTCClassicPool.sol";

contract DeploySepolia is Script {
    uint256 private constant SEPOLIA_CHAIN_ID = 11_155_111;
    error WrongChain(uint256 actual);

    event Deployment(
        address indexed pool,
        address indexed registry,
        address indexed airVerifier,
        address queryVerifier,
        bytes32 parameterLeft,
        bytes32 parameterRight,
        uint256 denomination
    );

    function run()
        external
        returns (
            PQTCClassicPool pool,
            PQTCVerificationRegistry registry,
            PQTCAirStageVerifier airVerifier,
            PQTCQueryVerifier queryVerifier
        )
    {
        if (block.chainid != SEPOLIA_CHAIN_ID) revert WrongChain(block.chainid);
        Digest512 memory parameterId =
            Digest512(vm.envBytes32("PARAMETER_ID_LEFT"), vm.envBytes32("PARAMETER_ID_RIGHT"));
        uint256 denomination = vm.envOr("DENOMINATION_WEI", uint256(0.001 ether));

        vm.startBroadcast();
        airVerifier = new PQTCAirStageVerifier();
        queryVerifier = new PQTCQueryVerifier();
        registry = new PQTCVerificationRegistry(airVerifier, queryVerifier, parameterId);
        pool = new PQTCClassicPool(denomination, parameterId, registry);
        emit Deployment(
            address(pool),
            address(registry),
            address(airVerifier),
            address(queryVerifier),
            parameterId.left,
            parameterId.right,
            denomination
        );
        vm.stopBroadcast();
    }

}
```

</details>

## `script/LocalTwoPartE2E.s.sol`

- Bytes: 1,503
- SHA-256: `c0d158b63f18523af68059b8a3fb9e8110a09d7477b0f7b82ac0bd25ff28db8d`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Script} from "forge-std/Script.sol";
import {Digest512} from "../contracts/src/libraries/Digest512.sol";
import {PQTCClassicPool} from "../contracts/src/PQTCClassicPool.sol";

/// Submits the canonical v3 proof parts to an existing local pool in exactly two transactions.
contract LocalTwoPartE2E is Script {
    function run() external returns (PQTCClassicPool pool, bytes32 verificationId) {
        pool = PQTCClassicPool(vm.envAddress("POOL"));
        bytes memory partA = vm.readFileBinary("test-vectors/verifier/v3/part-a.pqtc");
        bytes memory partB = vm.readFileBinary("test-vectors/verifier/v3/part-b.pqtc");
        PQTCClassicPool.Withdrawal memory withdrawal = _withdrawal();

        vm.startBroadcast();
        verificationId = pool.beginWithdrawal(withdrawal, partA);
        pool.withdraw(withdrawal, verificationId, partB);
        vm.stopBroadcast();
    }

    function _withdrawal() private view returns (PQTCClassicPool.Withdrawal memory withdrawal) {
        withdrawal.root = Digest512(vm.envBytes32("ROOT_LEFT"), vm.envBytes32("ROOT_RIGHT"));
        withdrawal.nullifierHash =
            Digest512(vm.envBytes32("NULLIFIER_HASH_LEFT"), vm.envBytes32("NULLIFIER_HASH_RIGHT"));
        withdrawal.recipient = payable(vm.envAddress("RECIPIENT"));
        withdrawal.relayer = payable(vm.envOr("RELAYER", address(0)));
        withdrawal.fee = vm.envOr("FEE_WEI", uint256(0));
    }
}
```

</details>

## `script/SubmitTwoPartProof.s.sol`

- Bytes: 1,550
- SHA-256: `5f17ea132ecf68d43021e0af7b25d56e55896072e805079c7a460c5a094398fc`

<details><summary>Complete file</summary>

```solidity
// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Script} from "forge-std/Script.sol";
import {Digest512} from "../contracts/src/libraries/Digest512.sol";
import {PQTCClassicPool} from "../contracts/src/PQTCClassicPool.sol";

/// Submits one v3 two-part proof to an existing pool in exactly two transactions.
contract SubmitTwoPartProof is Script {
    function run() external returns (bytes32 verificationId) {
        PQTCClassicPool pool = PQTCClassicPool(vm.envAddress("POOL"));
        string memory proofDir = vm.envString("PROOF_DIR");
        bytes memory partA = vm.readFileBinary(string.concat(proofDir, "/part-a.pqtc"));
        bytes memory partB = vm.readFileBinary(string.concat(proofDir, "/part-b.pqtc"));
        PQTCClassicPool.Withdrawal memory withdrawal = _withdrawal();

        vm.startBroadcast();
        verificationId = pool.beginWithdrawal(withdrawal, partA);
        pool.withdraw(withdrawal, verificationId, partB);
        vm.stopBroadcast();
    }


    function _withdrawal() private view returns (PQTCClassicPool.Withdrawal memory withdrawal) {
        withdrawal.root = Digest512(vm.envBytes32("ROOT_LEFT"), vm.envBytes32("ROOT_RIGHT"));
        withdrawal.nullifierHash =
            Digest512(vm.envBytes32("NULLIFIER_HASH_LEFT"), vm.envBytes32("NULLIFIER_HASH_RIGHT"));
        withdrawal.recipient = payable(vm.envAddress("RECIPIENT"));
        withdrawal.relayer = payable(vm.envOr("RELAYER", address(0)));
        withdrawal.fee = vm.envOr("FEE_WEI", uint256(0));
    }
}
```

</details>


# Appendix D — Complete build, workspace, CI, and deployment-template configuration

## `Cargo.toml`

- Bytes: 2,987
- SHA-256: `9d778f1990372273a2ab57884211f109e64ebbdbe687c24a754a7feb37220a09`

<details><summary>Complete file</summary>

```toml
[workspace]
resolver = "2"
members = [
  "crates/pqtc-spec",
  "crates/pqtc-hash",
  "crates/pqtc-merkle",
  "crates/pqtc-poseidon-air",
  "crates/pqtc-stark",
  "crates/pqtc-security",
  "crates/pqtc-indexer",
  "crates/pqtc-cli",
]

[workspace.package]
version = "0.3.0"
edition = "2024"
license = "MIT OR Apache-2.0"
rust-version = "1.97"

[workspace.dependencies]
alloy = { version = "1.0.38", default-features = false }
anyhow = "1.0.100"
base64 = "0.22.1"
bincode = "2.0.1"
clap = { version = "4.5.48", features = ["derive"] }
hex = "0.4.3"
rand = "0.10.0"
rand_core = "0.10.0"
postcard = { version = "1.1.3", features = ["alloc"] }
serde = { version = "1.0.228", features = ["derive"] }
serde_json = "1.0.145"
sha3 = "0.10.8"
thiserror = "2.0.17"
tokio = { version = "1.47.1", features = ["macros", "rt-multi-thread"] }

# Plonky3 is pinned. Do not replace rev with a branch or tag.
p3-air = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-baby-bear = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-challenger = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-commit = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-dft = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-field = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-fri = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-keccak = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-keccak-air = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-poseidon2 = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-poseidon2-air = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-matrix = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-merkle-tree = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-symmetric = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-security = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }
p3-uni-stark = { git = "https://github.com/Plonky3/Plonky3.git", rev = "3152b14a89067c83775a8076cc262ffc48a1fd7c" }

[profile.release]
lto = "thin"
codegen-units = 1

[workspace.lints.rust]
unsafe_code = "deny"
unused_must_use = "deny"

[workspace.lints.clippy]
all = { level = "warn", priority = -1 }
pedantic = { level = "warn", priority = -1 }
module_name_repetitions = "allow"
```

</details>

## `Cargo.lock`

- Bytes: 26,145
- SHA-256: `90baf448290d9d08679388376d1627c83cc11edde23f56cdb77bac40d9831324`

<details><summary>Complete file</summary>

```text
# This file is automatically @generated by Cargo.
# It is not intended for manual editing.
version = 4

[[package]]
name = "anstream"
version = "1.0.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "824a212faf96e9acacdbd09febd34438f8f711fb84e09a8916013cd7815ca28d"
dependencies = [
 "anstyle",
 "anstyle-parse",
 "anstyle-query",
 "anstyle-wincon",
 "colorchoice",
 "is_terminal_polyfill",
 "utf8parse",
]

[[package]]
name = "anstyle"
version = "1.0.14"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "940b3a0ca603d1eade50a4846a2afffd5ef57a9feac2c0e2ec2e14f9ead76000"

[[package]]
name = "anstyle-parse"
version = "1.0.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "52ce7f38b242319f7cabaa6813055467063ecdc9d355bbb4ce0c68908cd8130e"
dependencies = [
 "utf8parse",
]

[[package]]
name = "anstyle-query"
version = "1.1.5"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "40c48f72fd53cd289104fc64099abca73db4166ad86ea0b4341abe65af83dadc"
dependencies = [
 "windows-sys",
]

[[package]]
name = "anstyle-wincon"
version = "3.0.11"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "291e6a250ff86cd4a820112fb8898808a366d8f9f58ce16d1f538353ad55747d"
dependencies = [
 "anstyle",
 "once_cell_polyfill",
 "windows-sys",
]

[[package]]
name = "anyhow"
version = "1.0.104"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "330a5ed07fa54e4702c9d6c4174f74427fc0ef6e214bbd677ae50a5099946470"

[[package]]
name = "atomic-polyfill"
version = "1.0.3"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "8cf2bce30dfe09ef0bfaef228b9d414faaf7e563035494d7fe092dba54b300f4"
dependencies = [
 "critical-section",
]

[[package]]
name = "autocfg"
version = "1.5.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "f2032f911046de80f0a198e0901378627c33f59ea0ac00e363d481118bd70a53"

[[package]]
name = "base64"
version = "0.22.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "72b3254f16251a8381aa12e40e3c4d2f0199f8c6508fbecb9d91f575e0fbb8c6"

[[package]]
name = "block-buffer"
version = "0.10.4"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "3078c7629b62d3f0439517fa394996acacc5cbc91c5a20d8c658e77abd503a71"
dependencies = [
 "generic-array",
]

[[package]]
name = "byteorder"
version = "1.5.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "1fd0f2584146f6f2ef48085050886acf353beff7305ebd1ae69500e27c67f64b"

[[package]]
name = "cfg-if"
version = "1.0.4"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "9330f8b2ff13f34540b44e946ef35111825727b38d33286ef986142615121801"

[[package]]
name = "chacha20"
version = "0.10.2"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "65c35e4b699c7e15ccbe7ee35c005e4fc0a278d22238a2857e6ce2dadeda1b06"
dependencies = [
 "cfg-if",
 "cpufeatures 0.3.1",
 "rand_core",
]

[[package]]
name = "clap"
version = "4.6.6"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "473c7e07f409a8d772161724aa8db6a765a2532a70f9667eeb7b49d3d02fbdca"
dependencies = [
 "clap_builder",
 "clap_derive",
]

[[package]]
name = "clap_builder"
version = "4.6.6"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "7b48fea5a88e9ae728a2dcbedbfc0e730f7d60da42e1cb049a83c9fb8b789889"
dependencies = [
 "anstream",
 "anstyle",
 "clap_lex",
 "strsim",
]

[[package]]
name = "clap_derive"
version = "4.6.4"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "d012d2b9d65aca7f18f4d9878a045bc17899bba951561ba5ec3c2ba1eed9a061"
dependencies = [
 "heck",
 "proc-macro2",
 "quote",
 "syn 3.0.4",
]

[[package]]
name = "clap_lex"
version = "1.1.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "c8d4a3bb8b1e0c1050499d1815f5ab16d04f0959b233085fb31653fbfc9d98f9"

[[package]]
name = "cobs"
version = "0.3.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "0fa961b519f0b462e3a3b4a34b64d119eeaca1d59af726fe450bbba07a9fc0a1"
dependencies = [
 "thiserror",
]

[[package]]
name = "colorchoice"
version = "1.0.5"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "1d07550c9036bf2ae0c684c4297d503f838287c83c53686d05370d0e139ae570"

[[package]]
name = "cpufeatures"
version = "0.2.17"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "59ed5838eebb26a2bb2e58f6d5b5316989ae9d08bab10e0e6d103e656d1b0280"
dependencies = [
 "libc",
]

[[package]]
name = "cpufeatures"
version = "0.3.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "5ca28b0ae3115b884660db4118d803791fd6756b6e88f39c0f3f7859060d7566"
dependencies = [
 "libc",
]

[[package]]
name = "critical-section"
version = "1.2.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "790eea4361631c5e7d22598ecd5723ff611904e3344ce8720784c93e3d83d40b"

[[package]]
name = "crunchy"
version = "0.2.4"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "460fbee9c2c2f33933d720630a6a0bac33ba7053db5344fac858d4b8952d77d5"

[[package]]
name = "crypto-common"
version = "0.1.7"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "78c8292055d1c1df0cce5d180393dc8cce0abec0a7102adb6c7b1eef6016d60a"
dependencies = [
 "generic-array",
 "typenum",
]

[[package]]
name = "digest"
version = "0.10.7"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "9ed9a281f7bc9b7576e61468ba615a66a5c8cfdff42420a70aa82701a3b1e292"
dependencies = [
 "block-buffer",
 "crypto-common",
]

[[package]]
name = "either"
version = "1.18.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "252afb9ae5eaa683babdc6a068b3f5726eb19e05070c731f9b2a23a7c3e8ed34"

[[package]]
name = "embedded-io"
version = "0.4.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "ef1a6892d9eef45c8fa6b9e0086428a2cca8491aca8f787c534a3d6d0bcb3ced"

[[package]]
name = "embedded-io"
version = "0.6.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "edd0f118536f44f5ccd48bcb8b111bdc3de888b58c74639dfb034a357d0f206d"

[[package]]
name = "generic-array"
version = "0.14.7"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "85649ca51fd72272d7821adaf274ad91c288277713d9c18820d8499a7ff69e9a"
dependencies = [
 "typenum",
 "version_check",
]

[[package]]
name = "getrandom"
version = "0.4.3"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "300e883d756b2e4ec94e02791f39b04b522276138852cfc41d9fb7e904106099"
dependencies = [
 "cfg-if",
 "libc",
 "r-efi",
 "rand_core",
]

[[package]]
name = "hash32"
version = "0.2.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "b0c35f58762feb77d74ebe43bdbc3210f09be9fe6742234d573bacc26ed92b67"
dependencies = [
 "byteorder",
]

[[package]]
name = "heapless"
version = "0.7.17"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "cdc6457c0eb62c71aac4bc17216026d8410337c4126773b9c5daba343f17964f"
dependencies = [
 "atomic-polyfill",
 "hash32",
 "rustc_version",
 "serde",
 "spin 0.9.9",
 "stable_deref_trait",
]

[[package]]
name = "heck"
version = "0.5.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "2304e00983f87ffb38b55b444b5e3b60a884b5d30c0fca7d82fe33449bbe55ea"

[[package]]
name = "hex"
version = "0.4.3"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "7f24254aa9a54b5c858eaee2f5bccdb46aaf0e486a595ed5fd8f86ba55232a70"

[[package]]
name = "is_terminal_polyfill"
version = "1.70.2"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "a6cb138bb79a146c1bd460005623e142ef0181e3d0219cb493e02f7d08a35695"

[[package]]
name = "itertools"
version = "0.15.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "8b4baf93f58d4425749ca49a51c50ebab072c5df6994d08fed93541c331481dc"
dependencies = [
 "either",
]

[[package]]
name = "itoa"
version = "1.0.18"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "8f42a60cbdf9a97f5d2305f08a87dc4e09308d1276d28c869c684d7777685682"

[[package]]
name = "keccak"
version = "0.1.6"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "cb26cec98cce3a3d96cbb7bced3c4b16e3d13f27ec56dbd62cbc8f39cfb9d653"
dependencies = [
 "cpufeatures 0.2.17",
]

[[package]]
name = "libc"
version = "0.2.189"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "3eaf3ede3fee6db1a4c2ee091bf8a8b4dccdc6d17f656fb07896ee72867612f2"

[[package]]
name = "libm"
version = "0.2.16"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "b6d2cec3eae94f9f509c767b45932f1ada8350c4bdb85af2fcab4a3c14807981"

[[package]]
name = "lock_api"
version = "0.4.14"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "224399e74b87b5f3557511d98dff8b14089b3dadafcab6bb93eab67d3aace965"
dependencies = [
 "scopeguard",
]

[[package]]
name = "memchr"
version = "2.8.3"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "cf8baf1c55e62ffcace7a9f06f4bd9cd3f0c4beb022d3b367256b91b87513d98"

[[package]]
name = "num-bigint"
version = "0.5.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "93e7820bc0a80a0238e650327316f929ba18d5be054b647490a3a6a339f3e7c0"
dependencies = [
 "num-integer",
 "num-traits",
]

[[package]]
name = "num-integer"
version = "0.1.47"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "7ce2d95d4b3734dc35aa2f45e1aa22cd416814592a4f9d9205e11affd5b8e10b"
dependencies = [
 "num-traits",
]

[[package]]
name = "num-traits"
version = "0.2.19"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "071dfc062690e90b734c0b2273ce72ad0ffa95f0c74596bc250dcfd960262841"
dependencies = [
 "autocfg",
]

[[package]]
name = "once_cell_polyfill"
version = "1.70.2"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "384b8ab6d37215f3c5301a95a4accb5d64aa607f1fcb26a11b5303878451b4fe"

[[package]]
name = "p3-air"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "p3-field",
 "p3-matrix",
 "serde",
 "tracing",
]

[[package]]
name = "p3-baby-bear"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "p3-field",
 "p3-mds",
 "p3-monty-31",
 "p3-poseidon1",
 "p3-poseidon2",
 "p3-symmetric",
 "rand",
]

[[package]]
name = "p3-challenger"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "p3-field",
 "p3-maybe-rayon",
 "p3-symmetric",
 "p3-util",
 "tracing",
]

[[package]]
name = "p3-commit"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "itertools",
 "p3-dft",
 "p3-field",
 "p3-matrix",
 "p3-multilinear-util",
 "p3-util",
 "serde",
]

[[package]]
name = "p3-dft"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "itertools",
 "p3-field",
 "p3-matrix",
 "p3-maybe-rayon",
 "p3-util",
 "spin 0.12.3",
 "tracing",
]

[[package]]
name = "p3-field"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "itertools",
 "num-bigint",
 "p3-maybe-rayon",
 "p3-util",
 "paste",
 "rand",
 "serde",
 "tracing",
]

[[package]]
name = "p3-fri"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "itertools",
 "p3-challenger",
 "p3-commit",
 "p3-dft",
 "p3-field",
 "p3-matrix",
 "p3-maybe-rayon",
 "p3-security",
 "p3-util",
 "rand",
 "serde",
 "spin 0.12.3",
 "thiserror",
 "tracing",
]

[[package]]
name = "p3-keccak"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "p3-symmetric",
 "p3-util",
 "tiny-keccak",
]

[[package]]
name = "p3-matrix"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "itertools",
 "p3-field",
 "p3-maybe-rayon",
 "p3-util",
 "rand",
 "serde",
 "tracing",
]

[[package]]
name = "p3-maybe-rayon"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"

[[package]]
name = "p3-mds"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "p3-dft",
 "p3-field",
 "p3-symmetric",
 "p3-util",
 "rand",
]

[[package]]
name = "p3-merkle-tree"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "itertools",
 "p3-commit",
 "p3-field",
 "p3-matrix",
 "p3-maybe-rayon",
 "p3-symmetric",
 "p3-util",
 "rand",
 "serde",
 "spin 0.12.3",
 "thiserror",
 "tracing",
]

[[package]]
name = "p3-monty-31"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "itertools",
 "num-bigint",
 "p3-dft",
 "p3-field",
 "p3-matrix",
 "p3-maybe-rayon",
 "p3-mds",
 "p3-poseidon1",
 "p3-poseidon2",
 "p3-symmetric",
 "p3-util",
 "paste",
 "rand",
 "serde",
 "spin 0.12.3",
 "tracing",
]

[[package]]
name = "p3-multilinear-util"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "itertools",
 "p3-field",
 "p3-matrix",
 "p3-maybe-rayon",
 "p3-util",
 "rand",
 "serde",
 "tracing",
]

[[package]]
name = "p3-poseidon1"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "p3-field",
 "p3-mds",
 "p3-symmetric",
 "rand",
]

[[package]]
name = "p3-poseidon2"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "p3-field",
 "p3-mds",
 "p3-symmetric",
 "p3-util",
 "rand",
]

[[package]]
name = "p3-poseidon2-air"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "p3-air",
 "p3-field",
 "p3-matrix",
 "p3-maybe-rayon",
 "p3-poseidon2",
 "rand",
 "tracing",
]

[[package]]
name = "p3-security"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "libm",
 "p3-air",
 "p3-field",
 "p3-util",
 "serde",
]

[[package]]
name = "p3-symmetric"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "itertools",
 "p3-field",
 "p3-util",
 "serde",
]

[[package]]
name = "p3-uni-stark"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "itertools",
 "libm",
 "p3-air",
 "p3-challenger",
 "p3-commit",
 "p3-field",
 "p3-matrix",
 "p3-maybe-rayon",
 "p3-security",
 "p3-util",
 "serde",
 "thiserror",
 "tracing",
]

[[package]]
name = "p3-util"
version = "0.6.0"
source = "git+https://github.com/Plonky3/Plonky3.git?rev=3152b14a89067c83775a8076cc262ffc48a1fd7c#3152b14a89067c83775a8076cc262ffc48a1fd7c"
dependencies = [
 "p3-maybe-rayon",
 "serde",
]

[[package]]
name = "paste"
version = "1.0.15"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "57c0d7b74b563b49d38dae00a0c37d4d6de9b432382b2892f0574ddcae73fd0a"

[[package]]
name = "pin-project-lite"
version = "0.2.17"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "a89322df9ebe1c1578d689c92318e070967d1042b512afbe49518723f4e6d5cd"

[[package]]
name = "postcard"
version = "1.1.3"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "6764c3b5dd454e283a30e6dfe78e9b31096d9e32036b5d1eaac7a6119ccb9a24"
dependencies = [
 "cobs",
 "embedded-io 0.4.0",
 "embedded-io 0.6.1",
 "heapless",
 "serde",
]

[[package]]
name = "pqtc-cli"
version = "0.3.0"
dependencies = [
 "anyhow",
 "clap",
 "hex",
 "p3-air",
 "p3-baby-bear",
 "p3-challenger",
 "p3-commit",
 "p3-field",
 "p3-matrix",
 "p3-symmetric",
 "p3-uni-stark",
 "pqtc-hash",
 "pqtc-indexer",
 "pqtc-merkle",
 "pqtc-poseidon-air",
 "pqtc-security",
 "pqtc-spec",
 "pqtc-stark",
 "serde",
 "serde_json",
]

[[package]]
name = "pqtc-hash"
version = "0.3.0"
dependencies = [
 "base64",
 "hex",
 "p3-baby-bear",
 "p3-field",
 "p3-symmetric",
 "pqtc-spec",
 "rand",
 "serde",
 "sha3",
 "thiserror",
]

[[package]]
name = "pqtc-indexer"
version = "0.3.0"
dependencies = [
 "pqtc-merkle",
 "pqtc-spec",
 "serde",
 "thiserror",
]

[[package]]
name = "pqtc-merkle"
version = "0.3.0"
dependencies = [
 "hex",
 "pqtc-hash",
 "pqtc-spec",
 "serde",
 "serde_json",
 "thiserror",
]

[[package]]
name = "pqtc-poseidon-air"
version = "0.3.0"
dependencies = [
 "p3-air",
 "p3-baby-bear",
 "p3-field",
 "p3-matrix",
 "p3-poseidon2",
 "p3-poseidon2-air",
 "p3-symmetric",
 "p3-uni-stark",
 "pqtc-hash",
 "pqtc-merkle",
 "pqtc-spec",
 "serde",
 "thiserror",
]

[[package]]
name = "pqtc-security"
version = "0.3.0"
dependencies = [
 "p3-air",
 "p3-baby-bear",
 "p3-field",
 "p3-security",
 "p3-uni-stark",
 "pqtc-hash",
 "pqtc-poseidon-air",
 "pqtc-spec",
 "serde",
 "thiserror",
]

[[package]]
name = "pqtc-spec"
version = "0.3.0"
dependencies = [
 "hex",
 "postcard",
 "rand",
 "serde",
 "serde_json",
 "thiserror",
]

[[package]]
name = "pqtc-stark"
version = "0.3.0"
dependencies = [
 "p3-baby-bear",
 "p3-challenger",
 "p3-commit",
 "p3-dft",
 "p3-field",
 "p3-fri",
 "p3-keccak",
 "p3-merkle-tree",
 "p3-symmetric",
 "p3-uni-stark",
 "pqtc-hash",
 "pqtc-poseidon-air",
 "pqtc-spec",
 "rand",
 "thiserror",
]

[[package]]
name = "proc-macro2"
version = "1.0.107"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "985e7ec9bb745e6ce6535b544d84d6cd6f7ad8bd711c398938ae983b91a766d9"
dependencies = [
 "unicode-ident",
]

[[package]]
name = "quote"
version = "1.0.47"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "1fbf4db142a473a8d80c26bbf18454ed458bf8d26c8219c331daecfdbd079001"
dependencies = [
 "proc-macro2",
]

[[package]]
name = "r-efi"
version = "6.0.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "f8dcc9c7d52a811697d2151c701e0d08956f92b0e24136cf4cf27b57a6a0d9bf"

[[package]]
name = "rand"
version = "0.10.2"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "c7f5fa3a058cd35567ef9bfa5e75732bee0f9e4c55fa90477bef2dfcdbc4be80"
dependencies = [
 "chacha20",
 "getrandom",
 "rand_core",
]

[[package]]
name = "rand_core"
version = "0.10.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "63b8176103e19a2643978565ca18b50549f6101881c443590420e4dc998a3c69"

[[package]]
name = "rustc_version"
version = "0.4.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "cfcb3a22ef46e85b45de6ee7e79d063319ebb6594faafcf1c225ea92ab6e9b92"
dependencies = [
 "semver",
]

[[package]]
name = "scopeguard"
version = "1.2.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "94143f37725109f92c262ed2cf5e59bce7498c01bcc1502d7b9afe439a4e9f49"

[[package]]
name = "semver"
version = "1.0.28"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "8a7852d02fc848982e0c167ef163aaff9cd91dc640ba85e263cb1ce46fae51cd"

[[package]]
name = "serde"
version = "1.0.229"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "4148590afebada386688f18773da617792bf2ef03ffc1e4cbd2b1d45b023e0ba"
dependencies = [
 "serde_core",
 "serde_derive",
]

[[package]]
name = "serde_core"
version = "1.0.229"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "67dca2c9c51e58a4791a4b1ed58308b39c64224d349a935ab5039aa360942a48"
dependencies = [
 "serde_derive",
]

[[package]]
name = "serde_derive"
version = "1.0.229"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "e7a5d71263a5a7d47b41f6b3f06ba276f10cc18b0931f1799f710578e2309348"
dependencies = [
 "proc-macro2",
 "quote",
 "syn 3.0.4",
]

[[package]]
name = "serde_json"
version = "1.0.151"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "c841b55ecdae098c80dcae9cf767f6f8a0c2cdb3416bbef72181df4d0fe73f14"
dependencies = [
 "itoa",
 "memchr",
 "serde",
 "serde_core",
 "zmij",
]

[[package]]
name = "sha3"
version = "0.10.9"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "77fd7028345d415a4034cf8777cd4f8ab1851274233b45f84e3d955502d93874"
dependencies = [
 "digest",
 "keccak",
]

[[package]]
name = "spin"
version = "0.9.9"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "3763264f6b73151db08c50ff20d7d8a0b8796e021cdea7ceedad07b80155fa0e"
dependencies = [
 "lock_api",
]

[[package]]
name = "spin"
version = "0.12.3"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "0134f9043ed38b087ac4f7d4af44c79e2c9e5094421fe3164f435ce585953b10"
dependencies = [
 "lock_api",
]

[[package]]
name = "stable_deref_trait"
version = "1.2.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "6ce2be8dc25455e1f91df71bfa12ad37d7af1092ae736f3a6cd0e37bc7810596"

[[package]]
name = "strsim"
version = "0.11.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "7da8b5736845d9f2fcb837ea5d9e2628564b3b043a70948a3f0b778838c5fb4f"

[[package]]
name = "syn"
version = "2.0.119"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "872831b642d1a07999a962a351ed35b955ea2cfc8f3862091e2a240a84f17297"
dependencies = [
 "proc-macro2",
 "quote",
 "unicode-ident",
]

[[package]]
name = "syn"
version = "3.0.4"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "e6275cddf4610d1775e6d1fe9469b2e77d0f39fd98fb7450901b821e0c53649f"
dependencies = [
 "proc-macro2",
 "quote",
 "unicode-ident",
]

[[package]]
name = "thiserror"
version = "2.0.20"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "ec86235f5fcc2a73650310756d2ac5b138a5780bbbdfae3eeccec992c435ba4f"
dependencies = [
 "thiserror-impl",
]

[[package]]
name = "thiserror-impl"
version = "2.0.20"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "bc04cd3e1236dd4a98afca4569f2deb3f120e5422a4023be2cb683f8486292af"
dependencies = [
 "proc-macro2",
 "quote",
 "syn 3.0.4",
]

[[package]]
name = "tiny-keccak"
version = "2.0.2"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "2c9d3793400a45f954c52e73d068316d76b6f4e36977e3fcebb13a2721e80237"
dependencies = [
 "crunchy",
]

[[package]]
name = "tracing"
version = "0.1.44"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "63e71662fa4b2a2c3a26f570f037eb95bb1f85397f3cd8076caed2f026a6d100"
dependencies = [
 "pin-project-lite",
 "tracing-attributes",
 "tracing-core",
]

[[package]]
name = "tracing-attributes"
version = "0.1.31"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "7490cfa5ec963746568740651ac6781f701c9c5ea257c58e057f3ba8cf69e8da"
dependencies = [
 "proc-macro2",
 "quote",
 "syn 2.0.119",
]

[[package]]
name = "tracing-core"
version = "0.1.36"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "db97caf9d906fbde555dd62fa95ddba9eecfd14cb388e4f491a66d74cd5fb79a"

[[package]]
name = "typenum"
version = "1.20.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "b6f5e870be6c3b371b77fe0ee0bafb859fa4964b4404c27de1d380043c4dda20"

[[package]]
name = "unicode-ident"
version = "1.0.24"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "e6e4313cd5fcd3dad5cafa179702e2b244f760991f45397d14d4ebf38247da75"

[[package]]
name = "utf8parse"
version = "0.2.2"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "06abde3611657adf66d383f00b093d7faecc7fa57071cce2578660c9f1010821"

[[package]]
name = "version_check"
version = "0.9.5"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "0b928f33d975fc6ad9f86c8f283853ad26bdd5b10b7f1542aa2fa15e2289105a"

[[package]]
name = "windows-link"
version = "0.2.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "f0805222e57f7521d6a62e36fa9163bc891acd422f971defe97d64e70d0a4fe5"

[[package]]
name = "windows-sys"
version = "0.61.2"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "ae137229bcbd6cdf0f7b80a31df61766145077ddf49416a728b02cb3921ff3fc"
dependencies = [
 "windows-link",
]

[[package]]
name = "zmij"
version = "1.0.23"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "29666d0abbfad1e3dc4dcf6144730dd3a3ab225bbbdac83319345b1b44ccfc1b"
```

</details>

## `rust-toolchain.toml`

- Bytes: 86
- SHA-256: `d5de56d1101f9e3ba0d694a777665be841781229b16408c262294e4de9d2ca85`

<details><summary>Complete file</summary>

```toml
[toolchain]
channel = "1.97.0"
components = ["clippy", "rustfmt"]
profile = "minimal"
```

</details>

## `package.json`

- Bytes: 241
- SHA-256: `3d18ce247e42001dc97453441a3ceb6c817f9ffbc32bb8bb9474e1323237df38`

<details><summary>Complete file</summary>

```json
{
  "name": "pq-tornado-classic",
  "private": true,
  "packageManager": "pnpm@11.20.0",
  "engines": {
    "node": "24.19.0"
  },
  "scripts": {
    "build": "pnpm --filter @pqtc/sdk build",
    "test": "pnpm --filter @pqtc/sdk test"
  }
}
```

</details>

## `pnpm-lock.yaml`

- Bytes: 1,229
- SHA-256: `78d9240a9f922c4a48f3e5196a5cc01689902fb89047ab1c1a585d82e877b124`

<details><summary>Complete file</summary>

```yaml
lockfileVersion: '9.0'

settings:
  autoInstallPeers: true
  excludeLinksFromLockfile: false

importers:

  .: {}

  packages/sdk:
    dependencies:
      '@noble/hashes':
        specifier: 2.0.1
        version: 2.0.1
    devDependencies:
      '@types/node':
        specifier: 24.7.2
        version: 24.7.2
      typescript:
        specifier: 5.9.3
        version: 5.9.3

packages:

  '@noble/hashes@2.0.1':
    resolution: {integrity: sha512-XlOlEbQcE9fmuXxrVTXCTlG2nlRXa9Rj3rr5Ue/+tX+nmkgbX720YHh0VR3hBF9xDvwnb8D2shVGOwNx+ulArw==}
    engines: {node: '>= 20.19.0'}

  '@types/node@24.7.2':
    resolution: {integrity: sha512-/NbVmcGTP+lj5oa4yiYxxeBjRivKQ5Ns1eSZeB99ExsEQ6rX5XYU1Zy/gGxY/ilqtD4Etx9mKyrPxZRetiahhA==}

  typescript@5.9.3:
    resolution: {integrity: sha512-jl1vZzPDinLr9eUt3J/t7V6FgNEw9QjvBPdysz9KfQDD41fQrC2Y4vKQdiaUpFT4bXlb1RHhLpp8wtm6M5TgSw==}
    engines: {node: '>=14.17'}
    hasBin: true

  undici-types@7.14.0:
    resolution: {integrity: sha512-QQiYxHuyZ9gQUIrmPo3IA+hUl4KYk8uSA7cHrcKd/l3p1OTpZcM0Tbp9x7FAtXdAYhlasd60ncPpgu6ihG6TOA==}

snapshots:

  '@noble/hashes@2.0.1': {}

  '@types/node@24.7.2':
    dependencies:
      undici-types: 7.14.0

  typescript@5.9.3: {}

  undici-types@7.14.0: {}
```

</details>

## `pnpm-workspace.yaml`

- Bytes: 77
- SHA-256: `ee6a4b6691e63b740bb61c6a161005d28c84aa73350aad505722f35d234dd48e`

<details><summary>Complete file</summary>

```yaml
packages:
  - "packages/*"
allowBuilds:
  esbuild: set this to true or false
```

</details>

## `.node-version`

- Bytes: 8
- SHA-256: `7e8a2fa94951112b894a3dbe3d05efef5e9263741fa49125f0a70f40fedab4cc`

<details><summary>Complete file</summary>

```text
24.19.0
```

</details>

## `foundry.toml`

- Bytes: 470
- SHA-256: `04c59dc1a416c14a3c77c5035c8ddaf1d09c70de840287ef7235abb71971abf0`

<details><summary>Complete file</summary>

```toml
[profile.default]
src = "contracts/src"
test = "contracts/test"
script = "contracts/script"
out = "out"
libs = ["lib"]
solc = "0.8.30"
evm_version = "prague"
optimizer = true
optimizer_runs = 200
via_ir = true
bytecode_hash = "none"
fs_permissions = [
    { access = "read", path = "./test-vectors" },
    { access = "read", path = "./target" },
    { access = "read", path = "./staged-proof" },
]
gas_limit = 9_223_372_036_854_775_807

[invariant]
runs = 64
depth = 16
```

</details>

## `foundry.lock`

- Bytes: 128
- SHA-256: `6b182f57b5c5615131465941411dac80a778d554bd4a796bd28749b9b752d6f0`

<details><summary>Complete file</summary>

```text
{
  "lib/forge-std": {
    "tag": {
      "name": "v1.16.2",
      "rev": "bf647bd6046f2f7da30d0c2bf435e5c76a780c1b"
    }
  }
}
```

</details>

## `Dockerfile`

- Bytes: 677
- SHA-256: `029b379e196b00124d0b3e491b0bf1fc7536173bcb7b3032283235fca737fcc1`

<details><summary>Complete file</summary>

```dockerfile
FROM node:24.19.0-bookworm AS node

FROM rust:1.97.0-bookworm

ARG FOUNDRY_VERSION=v1.7.1
ARG PNPM_VERSION=11.20.0

COPY --from=node /usr/local /usr/local
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global "pnpm@${PNPM_VERSION}" \
    && curl -fsSL https://foundry.paradigm.xyz | bash \
    && /root/.foundry/bin/foundryup --install "${FOUNDRY_VERSION}"

ENV PATH="/root/.foundry/bin:${PATH}"
WORKDIR /workspace
COPY . .
RUN cargo test --workspace --locked \
    && pnpm install --frozen-lockfile \
    && pnpm test \
    && forge build --sizes \
    && forge test
```

</details>

## `.dockerignore`

- Bytes: 79
- SHA-256: `ad3290270c84b9c314069d480cc730971e48e665e9a5232f97a91802a35d43d5`

<details><summary>Complete file</summary>

```text
.git
.github
broadcast
cache
out
target
node_modules
packages/*/dist
.DS_Store
```

</details>

## `.gitignore`

- Bytes: 225
- SHA-256: `c0267a6bb5ec02664e536eab8de433be17b6df0717dd351e2739d046a945e42c`

<details><summary>Complete file</summary>

```text
# Compiler files
cache/
out/

# Commonly ignored directories
.logs/
.ignore/

# Ignores development broadcast logs
!/broadcast
/broadcast/*/31337/
/broadcast/**/dry-run/

# Docs
docs/

# Dotenv file
.env
.env.*
!.env.example
```

</details>

## `.gitmodules`

- Bytes: 97
- SHA-256: `172e0d1d79e557e903f2d87805acade91d1186b07f54ff9992100d296e2c3117`

<details><summary>Complete file</summary>

```text
[submodule "lib/forge-std"]
	path = lib/forge-std
	url = https://github.com/foundry-rs/forge-std
```

</details>

## `.github/workflows/test.yml`

- Bytes: 1,302
- SHA-256: `c2819dc468d9638c7f8d57ebdf4453b60649c189ac252f3eeba5881410bd071a`

<details><summary>Complete file</summary>

```yaml
name: CI

permissions: {}

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  check:
    name: Rust and Foundry
    runs-on: ubuntu-24.04
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false
          submodules: recursive
      - uses: pnpm/action-setup@v4
        with:
          version: 11.20.0
      - uses: actions/setup-node@v6
        with:
          node-version: 24.19.0
          cache: pnpm
      - name: Install JavaScript dependencies
        run: pnpm install --frozen-lockfile
      - name: Test TypeScript SDK
        run: pnpm test

      - name: Install Rust
        run: rustup show

      - name: Test Rust workspace
        run: cargo test --workspace --locked
      - name: Check Rust formatting
        run: cargo fmt --all --check
      - name: Lint Rust workspace
        run: cargo clippy --workspace --all-targets --locked

      - name: Install Foundry
        uses: foundry-rs/foundry-toolchain@v1
        with:
          version: v1.7.1
      - name: Show Forge version
        run: forge --version

      - name: Run Forge fmt
        run: forge fmt --check

      - name: Run Forge build
        run: forge build --sizes

      - name: Run Forge tests
        run: forge test -vvv
```

</details>

## `requirements-slither.txt`

- Bytes: 25
- SHA-256: `9e32d3699cccc3ea7b6c55a26e31b5a7bf3dda92638d1d06ab2807fbf1555e6d`

<details><summary>Complete file</summary>

```text
slither-analyzer==0.11.5
```

</details>

## `deployments/sepolia.template.json`

- Bytes: 923
- SHA-256: `103a90ced8e716808b94477d83ff67858f1c4442a6c363eeba378e97e0f3ced1`

<details><summary>Complete file</summary>

```json
{
  "schema_version": 3,
  "protocol_version": 3,
  "network": "ethereum-sepolia",
  "chain_id": 11155111,
  "git_commit": null,
  "parameter_profile": "sepolia-v0.3",
  "parameter_id": null,
  "denomination_wei": "1000000000000000",
  "contracts": {
    "air_verifier": null,
    "query_verifier": null,
    "verification_registry": null,
    "pool": null
  },
  "constructor_arguments": {
    "verification_registry": {
      "air_verifier": null,
      "query_verifier": null,
      "parameter_id": null
    },
    "pool": {
      "denomination_wei": "1000000000000000",
      "parameter_id": null,
      "verification_registry": null
    }
  },
  "runtime_code_hashes": {
    "air_verifier": null,
    "query_verifier": null,
    "verification_registry": null,
    "pool": null
  },
  "deployment_transactions": [],
  "source_verification": {
    "explorer": "https://sepolia.etherscan.io",
    "verified": false
  }
}
```

</details>

## `deployments/sepolia-demo.template.json`

- Bytes: 1,206
- SHA-256: `1e00d622d5e5b392537aaa4ac17a0df9cd4c1436734d1e825f737fe4b25d2067`

<details><summary>Complete file</summary>

```json
{
  "schema_version": 3,
  "protocol_version": 3,
  "network": "ethereum-sepolia",
  "chain_id": 11155111,
  "git_commit": null,
  "parameter_profile": "sepolia-v0.3",
  "parameter_id": null,
  "contracts": {
    "air_verifier": null,
    "query_verifier": null,
    "verification_registry": null,
    "pool": null
  },
  "deposit_confirmation_depth": 12,
  "deposits": [],
  "selected_deposit_transaction": null,
  "selected_leaf_index": null,
  "withdrawal_root": null,
  "proof": {
    "part_a_sha256": null,
    "part_b_sha256": null,
    "part_a_bytes": null,
    "part_b_bytes": null,
    "proving_time_ms": null,
    "peak_prover_memory_bytes": null
  },
  "verification_id": null,
  "transactions": {
    "begin_withdrawal": null,
    "withdraw": null
  },
  "gas": {
    "begin_withdrawal": null,
    "withdraw": null,
    "total": null
  },
  "recipient": null,
  "relayer": null,
  "fee_wei": null,
  "recipient_balance_delta_wei": null,
  "relayer_balance_delta_wei": null,
  "rejections": {
    "double_spend": null,
    "changed_recipient": null,
    "changed_fee": null,
    "changed_root": null,
    "changed_nullifier": null,
    "tampered_part_a": null,
    "tampered_part_b": null
  }
}
```

</details>


# Appendix E — Generated parameter manifests and security outputs

## `parameters/ci/manifest.bin`

- Bytes: 148
- SHA-256: `31d86f7c1cba14f02c376aae8c9d23f16e754ea0f039e90817adf3b6ebdf8112`
- Complete binary hex:

```text
5051544350524d330003000263690028333135326231346138393036376338333737356138303736636332363266666334386131666437630006312e39372e30001442616279426561722832303133323635393231290400033a737527ee317debc44dd7dda24468b0e496411a977e80103bb5982a8f7d44a2140000000300000100030100100000000104040408000300030000
```

## `parameters/ci/manifest.json`

- Bytes: 891
- SHA-256: `781c5ee70cbf7607a54d809262d0f28c4b3ec48f4e044c7409524e4fd603677b`

<details><summary>Complete file</summary>

```json
{
  "profile": "ci",
  "plonky3_commit": "3152b14a89067c83775a8076cc262ffc48a1fd7c",
  "rust_toolchain": "1.97.0",
  "field": "BabyBear(2013265921)",
  "extension_degree": 4,
  "air_version": 3,
  "air_source_hash": [
    58,
    115,
    117,
    39,
    238,
    49,
    125,
    235,
    196,
    77,
    215,
    221,
    162,
    68,
    104,
    176,
    228,
    150,
    65,
    26,
    151,
    126,
    128,
    16,
    59,
    181,
    152,
    42,
    143,
    125,
    68,
    162
  ],
  "tree_depth": 20,
  "protocol_version": 3,
  "trace_height": 256,
  "fri_log_blowup": 3,
  "fri_max_log_arity": 1,
  "fri_query_count": 16,
  "fri_final_polynomial_bound": 1,
  "commit_grinding_bits": 4,
  "query_grinding_bits": 4,
  "random_codeword_count": 4,
  "mmcs_salt_elements": 8,
  "proof_codec_version": 3,
  "verifier_interface_version": 3,
  "expected_runtime_code_hashes": []
}
```

</details>

## `parameters/ci/parameter-id.txt`

- Bytes: 131
- SHA-256: `14ee74d203c34e6c2c4d74442afa45c3c1ff85de74735a2207730fe71ca81444`

<details><summary>Complete file</summary>

```text
0x81d3f6199ee3127acb81c16c28d4cddba6c5281f1c11d1e261aec64b4756c5f829d8550583dcd0edb3962af37a477cd26b860c10c1eadc357d577d3f60f50510
```

</details>

## `parameters/ci/security-analysis.json`

- Bytes: 278
- SHA-256: `a17ccc27ff3684d528489a43779389f9cff2a2bcd087d85960a39c36fe001447`

<details><summary>Complete file</summary>

```json
{
  "conjectured_bits": 49,
  "proven_unique_decoding_bits": 15,
  "proven_list_decoding_bits": 25,
  "proven_bits": 25,
  "challenge_field_bits": 120,
  "quantum_adjusted_mmcs_bits": 128,
  "batched_functions": 210,
  "air_constraints": 1186,
  "air_max_constraint_degree": 7
}
```

</details>

## `parameters/dev/manifest.bin`

- Bytes: 149
- SHA-256: `2a057502d5157799eeabad5269cf77127e9382d0e0b8d63b235f7f523c58b86a`
- Complete binary hex:

```text
5051544350524d33000300036465760028333135326231346138393036376338333737356138303736636332363266666334386131666437630006312e39372e30001442616279426561722832303133323635393231290400033a737527ee317debc44dd7dda24468b0e496411a977e80103bb5982a8f7d44a2140000000300000100030100020000000100000208000300030000
```

## `parameters/dev/manifest.json`

- Bytes: 891
- SHA-256: `1efbaf8674058400220e34bbf4d1095a90e302e329d7f73c3945826d45f466aa`

<details><summary>Complete file</summary>

```json
{
  "profile": "dev",
  "plonky3_commit": "3152b14a89067c83775a8076cc262ffc48a1fd7c",
  "rust_toolchain": "1.97.0",
  "field": "BabyBear(2013265921)",
  "extension_degree": 4,
  "air_version": 3,
  "air_source_hash": [
    58,
    115,
    117,
    39,
    238,
    49,
    125,
    235,
    196,
    77,
    215,
    221,
    162,
    68,
    104,
    176,
    228,
    150,
    65,
    26,
    151,
    126,
    128,
    16,
    59,
    181,
    152,
    42,
    143,
    125,
    68,
    162
  ],
  "tree_depth": 20,
  "protocol_version": 3,
  "trace_height": 256,
  "fri_log_blowup": 3,
  "fri_max_log_arity": 1,
  "fri_query_count": 2,
  "fri_final_polynomial_bound": 1,
  "commit_grinding_bits": 0,
  "query_grinding_bits": 0,
  "random_codeword_count": 2,
  "mmcs_salt_elements": 8,
  "proof_codec_version": 3,
  "verifier_interface_version": 3,
  "expected_runtime_code_hashes": []
}
```

</details>

## `parameters/dev/parameter-id.txt`

- Bytes: 131
- SHA-256: `b3de16a9fd29c3a238f141b2b7182e7a9a76cecccfdb3fa17d948bf7a2a6d189`

<details><summary>Complete file</summary>

```text
0x64c702cf8c74fc0015622ad2805d6d5fa9bede3129e184b886ad8c8b13105b04103ca423b8aa60e559ab43b91f6544d2b3f94f88d9e4d57246ad66761a36f646
```

</details>

## `parameters/dev/security-analysis.json`

- Bytes: 274
- SHA-256: `c627f1d404bc5b64333226dddf7d8e3ee2869855d7ed506c7930c63583c3e6ba`

<details><summary>Complete file</summary>

```json
{
  "conjectured_bits": 5,
  "proven_unique_decoding_bits": 1,
  "proven_list_decoding_bits": 2,
  "proven_bits": 2,
  "challenge_field_bits": 120,
  "quantum_adjusted_mmcs_bits": 128,
  "batched_functions": 210,
  "air_constraints": 1186,
  "air_max_constraint_degree": 7
}
```

</details>

## `parameters/sepolia-v0.3/manifest.bin`

- Bytes: 158
- SHA-256: `3c4233b4e316d6725abb416eb78fa543ca987c4dc487ada7e67c463e5ad0d21e`
- Complete binary hex:

```text
5051544350524d330003000c7365706f6c69612d76302e330028333135326231346138393036376338333737356138303736636332363266666334386131666437630006312e39372e30001442616279426561722832303133323635393231290400033a737527ee317debc44dd7dda24468b0e496411a977e80103bb5982a8f7d44a2140000000300000100040100200000000110100408000300030000
```

## `parameters/sepolia-v0.3/manifest.json`

- Bytes: 903
- SHA-256: `0d891caaddfc6d954655e15cf86e90ed99825c9f060df907c3afabab695b1c42`

<details><summary>Complete file</summary>

```json
{
  "profile": "sepolia-v0.3",
  "plonky3_commit": "3152b14a89067c83775a8076cc262ffc48a1fd7c",
  "rust_toolchain": "1.97.0",
  "field": "BabyBear(2013265921)",
  "extension_degree": 4,
  "air_version": 3,
  "air_source_hash": [
    58,
    115,
    117,
    39,
    238,
    49,
    125,
    235,
    196,
    77,
    215,
    221,
    162,
    68,
    104,
    176,
    228,
    150,
    65,
    26,
    151,
    126,
    128,
    16,
    59,
    181,
    152,
    42,
    143,
    125,
    68,
    162
  ],
  "tree_depth": 20,
  "protocol_version": 3,
  "trace_height": 256,
  "fri_log_blowup": 4,
  "fri_max_log_arity": 1,
  "fri_query_count": 32,
  "fri_final_polynomial_bound": 1,
  "commit_grinding_bits": 16,
  "query_grinding_bits": 16,
  "random_codeword_count": 4,
  "mmcs_salt_elements": 8,
  "proof_codec_version": 3,
  "verifier_interface_version": 3,
  "expected_runtime_code_hashes": []
}
```

</details>

## `parameters/sepolia-v0.3/parameter-id.txt`

- Bytes: 131
- SHA-256: `dc13595b449af2270a79cc8c95d7454f32788e8ca9c0e9aab0f28c1b577521c1`

<details><summary>Complete file</summary>

```text
0x35adfcc070249bb0393c2fd45f0bbd48ef03cbfc08070d03335eaf952975e62ab7bc82ead4f8c1f1c39b3372be85195853134dfc9d24f43b97a5e0454ea07779
```

</details>

## `parameters/sepolia-v0.3/security-analysis.json`

- Bytes: 279
- SHA-256: `790d06863695a6ce591454d564af1822659802f8433bef24f80bfdfd2151458d`

<details><summary>Complete file</summary>

```json
{
  "conjectured_bits": 107,
  "proven_unique_decoding_bits": 37,
  "proven_list_decoding_bits": 56,
  "proven_bits": 56,
  "challenge_field_bits": 120,
  "quantum_adjusted_mmcs_bits": 128,
  "batched_functions": 210,
  "air_constraints": 1186,
  "air_max_constraint_degree": 7
}
```

</details>


# Appendix F — Verification command record

The final verification sequence used the following commands. Output facts are summarized in Sections 2, 12, 14, and 15.

```sh
cargo run -q -p pqtc-cli -- parameters-generate --out-dir parameters
cargo run -q -p pqtc-cli -- vectors-generate --out test-vectors/hash/v3.json
cargo run -q -p pqtc-cli -- verifier-vectors-generate --out test-vectors/verifier/v3.json
cargo run -q -p pqtc-cli -- benchmark-withdrawal \
  --profile sepolia-v0.3 \
  --out-dir test-vectors/verifier/v3 \
  --fixture-only

# A second parameter generation into a temporary directory was compared with:
diff -ru parameters <temporary-parameter-directory>

cargo test --workspace --all-targets --locked
cargo clippy --workspace --all-targets --all-features --locked
pnpm build
pnpm test
forge clean
forge test -vv
forge lint
forge build --sizes
docker build -t pqtc-release:test .
```

Observed final totals:

```text
Rust:       47 passed
TypeScript: 18 passed
Solidity:   63 passed across 8 suites
Invariants: 3 passed; 64 runs and 1,024 calls per invariant
Docker:     build and all embedded checks passed
```

# End of report

This report deliberately ends with source and evidence rather than a deployment recommendation. The correct current disposition is: operational research gate passed; external cryptographic/security and worst-case gas gates unresolved; deployment not authorized.
