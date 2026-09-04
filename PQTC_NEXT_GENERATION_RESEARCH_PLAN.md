# PQ Tornado Classic — Next-Generation Research Program

**Status:** research directive; pre-specification; not a deployment authorization  
**Prepared:** 2026-09-04  
**Starting implementation:** PQ Tornado Classic v0.3, as documented in `ENGINEERING_REPORT.md` dated 2026-09-03  
**Primary objective:** determine, with reproducible measurements and explicit security accounting, whether a post-quantum-oriented Tornado Classic withdrawal can be verified in one Ethereum transaction with useful cost and defensible security; otherwise identify the best robust two-transaction or alternative deployment architecture  
**Required final output:** `NEXT_GENERATION_RESEARCH_REPORT.md` plus the machine-readable evidence bundle defined in this document  
**Not an objective:** implement or deploy a new custody protocol before the research report has been reviewed and a separate engineering specification has been approved

---

## 0. How to use this document

This document is a research program, not a new protocol specification. It is intended to be handed to engineering agents and human engineers who will run narrowly scoped experiments, preserve all negative results, and return a common evidence package. No spike may silently become the new protocol.

The team must follow four rules throughout the program:

1. **Freeze v0.3 as the reference baseline.** Do not improve it in place. Tag the exact reviewed snapshot and conduct every experiment on isolated branches or worktrees.
2. **Measure before integrating.** A promising primitive, AIR, field, PCS, transcript, or compression layer must pass its own spike gates before it is incorporated into an end-to-end candidate.
3. **Keep security labels precise.** “Pairing-free,” “hash-based,” “PQ-oriented,” “zero knowledge,” “100-bit conjectured,” and “100-bit proven” are different claims. Never substitute one for another.
4. **Return raw evidence.** The final report must include unsuccessful candidates, full parameter manifests, exact proof bytes or regenerators, gas traces, run-level JSON, source commits, and assumptions. A prose conclusion without the underlying data does not complete this program.

The work should end with enough evidence to write a new engineering plan. It should **not** end with a partially integrated v0.4 pool whose architectural choices were made opportunistically during implementation.

---

## 1. Executive mandate

The existing v0.3 implementation proves that an entirely pairing-free, transparent, witness-hiding proof can be verified by EVM contracts without a trusted verifier service. It also proves that the current construction is too close to Ethereum’s operational ceilings and does not yet support the intended security claim.

The next work must answer the following decision question:

> Can a Tornado Classic-style fixed-denomination withdrawal, with application-level post-quantum-oriented commitments and a genuinely witness-hiding hash/code-based proof, be executed atomically in one Ethereum transaction with a defensible security target and useful cost?

The preferred result is a one-transaction withdrawal. A robust two-transaction design remains acceptable as a fallback only if it has substantial gas margin, bounded state, and materially lower total cost than v0.3. If neither is attainable on Ethereum L1, the report must identify whether the limiting factor is:

- the application hash;
- the arithmetization;
- the low-degree test or polynomial commitment scheme;
- the transcript and commitment hash;
- the EVM arithmetic model;
- proof calldata;
- contract-size/deployment limits;
- the requirement for zero knowledge;
- the selected security target;
- or Ethereum L1 itself.

The team must not regain one-transaction UX by merely lowering the FRI query count, reducing digest security, removing witness hiding, introducing an elliptic-curve wrapper, trusting an off-chain verifier, or relying on a proposed Ethereum upgrade that is not active.

---

## 2. Evidence basis and current baseline

### 2.1 Source of truth

The starting source is `ENGINEERING_REPORT.md`, snapshot 2026-09-03. It describes a pre-deployment, unaudited implementation with no Sepolia or mainnet receipts. The report embeds the implementation, tests, build configuration, protocol documents, ADRs, manifests, and the original engineering plan.

The following values are the baseline to reproduce before new work begins:

| Property | v0.3 baseline |
|---|---:|
| Pool model | fixed-denomination native ETH, one note per withdrawal |
| Application tree | binary, depth 20 |
| Application hash | P2BB512-v1, BabyBear Poseidon2 width 16, rate 4, capacity 12 |
| Application digest | 16 BabyBear elements / 64 encoded bytes |
| Withdrawal AIR | 256 rows × 190 columns |
| Constraints | 1,186 |
| Maximum constraint degree | 7 |
| Application-hash permutations | 240 |
| Merkle-path permutations | 220 |
| Batched opening functions | 210 |
| Proof system | hiding Plonky3 STARK, BabyBear degree-four extension, two-adic FRI |
| Production-profile queries | 32, split 16/16 |
| Proof part A | 101,990 bytes |
| Proof part B | 108,294 bytes |
| Total proof parts | 210,284 bytes |
| Deposit modeled gas | at most 14,013,109 |
| Withdrawal A modeled gas | 16,539,302 |
| Withdrawal B modeled gas | 14,105,909 |
| A margin below EIP-7825 | 237,914 |
| Reported conjectured soundness | 107 bits under random-words model |
| Reported proven UDR | 37 bits |
| Reported proven LDR / best proven | 56 bits |
| Network evidence | none |

### 2.2 Chronology that must remain visible

The report must preserve the lessons from all three builds:

- **v0.1:** the reference Keccak AIR was approximately 2,633 columns wide. A complete staged withdrawal required proof-data shards, a fact lifecycle, and 818 successful state-changing transactions. This established feasibility of the relation but failed operationally.
- **v0.2:** moving application hashing to P2BB512 reduced the relation to 256 rows × 230 columns and used 48 queries, but the two pool-facing calls remained approximately 21.65M and 20.87M gas.
- **v0.3:** lifetime reuse reduced width to 190 and the query count to 32. The resulting calls fit the transaction cap locally, but part A has only 237,914 gas of measured margin and the best generated proven soundness bound is 56 bits.

Negative results are first-class data. No future report may present only the latest successful profile.

### 2.3 Current structural bottlenecks

The research program begins with five working hypotheses:

1. **The application sponge is overgeneralized.** A binary Merkle node consumes 32 digest fields through a rate-four sponge and emits 16 fields through four rate blocks. That costs eight absorb permutations and three additional squeeze permutations: eleven Poseidon2 permutations per node and 220 for a depth-20 path.
2. **The AIR is too wide for the EVM.** One complete Poseidon2 permutation is evaluated horizontally in a 157-column sub-AIR. The complete 190-column trace creates large row openings and 210 batched functions.
3. **The transcript is overly granular.** Hundreds of individual field observations are absorbed through separate KeccakPair512 state transitions rather than typed phase-level frames.
4. **The q32 profile crossed the gas gate by weakening conservative soundness.** A different relation or PCS must create enough efficiency to restore security, rather than relying on fewer queries.
5. **Proof calldata is an independent future constraint.** Prospective calldata-floor repricings can make a data-heavy proof impossible even when verifier execution becomes cheap.

These are hypotheses to test, not conclusions to force.

---

## 3. Non-negotiable scope and prohibited shortcuts

### 3.1 Cryptographic boundary

An accepted next-build candidate must not rely on:

- elliptic-curve discrete logarithms;
- pairings;
- KZG;
- IPA;
- Groth16;
- a PLONK/KZG or Halo-style wrapper;
- a trusted setup;
- a trusted verifier service;
- an administrator who can substitute the verifier;
- an optimistic fraud window as the sole proof of validity;
- or a classical signature assumption for note ownership inside the anonymity set.

Ordinary finite-field arithmetic is allowed. Using a field that is also used by an elliptic curve does not by itself introduce an elliptic-curve assumption; the commitment and proof construction determine the assumption.

### 3.2 Privacy boundary

Every candidate that could become a mixer withdrawal path must provide witness hiding for:

- nullifier secret;
- trapdoor;
- note commitment opening;
- leaf index;
- path bits;
- sibling nodes;
- intermediate hash states;
- and any proof-system randomness that could reveal the witness.

A non-hiding FRI, WHIR, STIR, Flock, Spartan, or recursive proof can be benchmarked only as a lower-bound or architecture experiment. It cannot pass the candidate gate merely because it is succinct or sound.

### 3.3 Product semantics

Unless a spike explicitly studies an alternative product architecture, retain:

- native ETH;
- one immutable denomination per pool;
- one commitment per deposit;
- one note spent per withdrawal;
- a public nullifier;
- a public recipient, relayer, and fee;
- a 20-level membership capacity or a documented equivalent capacity;
- permissionless proving and submission;
- no owner, proxy, verifier setter, pause key, or rescue path capable of moving pool funds;
- atomic nullifier consumption and payout in the final value-moving transaction.

### 3.4 UX constraints

The research target is:

- **Deposit:** one user transaction.
- **Preferred withdrawal:** one value-moving transaction containing complete verification.
- **Fallback withdrawal:** no more than two user/relayer transactions, with the second transaction completing verification and paying atomically.

Background batch-finalization transactions may be studied only where they are permissionless, do not require users to reveal notes, and have an explicit liveness/refund model. They do not count as user withdrawal transactions, but their latency and trust effects must be reported.

### 3.5 Prohibited optimization practices

Do not:

- reduce security parameters solely to fit a gas target;
- call a conjectural estimate a proven bound;
- omit batched-opening terms from the security report;
- quote upstream benchmark numbers as project measurements;
- extrapolate a one-permutation benchmark linearly without building the complete relation;
- infer zero knowledge from randomized proof bytes;
- hand-edit generated constraints without regenerating equivalence evidence;
- compare raw proof bytes for one candidate against ABI calldata bytes for another;
- rely on gas refunds to fit a transaction cap;
- rely on EIP-7954 or another proposed code-size increase for deployability;
- hide a failed candidate by removing it from the final report;
- or integrate an experimental primitive into custody code before its spike gate passes.

---

## 4. Terminology and result classifications

Use the following labels consistently.

### 4.1 `BENCHMARK_ONLY`

A component or proof that measures performance but lacks one or more required properties, such as zero knowledge, complete statement binding, EVM verification, or an accepted security analysis.

### 4.2 `PQ_ORIENTED_RESEARCH`

The construction avoids known Shor-vulnerable assumptions and uses symmetric/hash/code-based security arguments, but its exact composed security has not been independently accepted.

### 4.3 `SECURITY_QUALIFIED_CANDIDATE`

A candidate may receive this label only if one of the following is true:

1. the best applicable conservative theorem-derived bound is at least 100 bits after all composition, batching, multi-target, and quantum adjustments; or
2. an independent cryptographic reviewer provides a written concrete-security analysis accepting a different model at at least 100 bits and explicitly explains why lower generic theorem bounds are not the operative estimate.

Engineers may compute and present estimates, but may not self-award this label solely from a random-words conjecture.

### 4.4 `ONE_TX_FEASIBLE`

The complete pool-facing withdrawal, including exact ABI calldata, statement validation, proof verification, nullifier storage, recipient payment, relayer payment, and all external calls, meets the one-transaction gate in Section 6 under the required gas scenarios.

### 4.5 `ROBUST_TWO_TX_FEASIBLE`

The complete A/B flow meets the two-transaction gate, has bounded checkpoint state, and has a recovery path for abandoned A transactions.

### 4.6 `NEXT_BUILD_FINALIST`

A candidate that is security-qualified or has a clear path to qualification, passes correctness and hiding gates, meets either the one- or robust-two-transaction envelope, has measured prover UX, and has no unresolved architectural blocker that would require another proof-system rewrite.

---

## 5. Decision targets and quantitative gates

### 5.1 Ethereum hard limits and design margins

Model the following independently:

- EIP-7825 maximum transaction gas: 16,777,216.
- EIP-170 current runtime code-size limit: 24,576 bytes.
- EIP-3860 current initcode limit and metering.
- EIP-7623 current calldata floor.
- EIP-7976 64-gas-per-byte floor scenario.
- EIP-8311 96-gas-per-byte floor scenario.

EIP-7976 and EIP-8311 are scenario tests unless and until active on the target network. The project must not design only for today’s floor when proof bytes are a dominant resource.

### 5.2 One-transaction gate

A candidate passes the **hard one-transaction research gate** only if all of the following hold:

| Metric | Hard research gate | Preferred target | Stretch target |
|---|---:|---:|---:|
| Complete withdrawal transaction gas, current schedule | ≤14.0M | ≤10.0M | ≤6.0M |
| Complete withdrawal transaction gas, 64/64 floor scenario | ≤14.0M | ≤10.0M | ≤6.0M |
| Complete withdrawal transaction gas, 96/96 floor scenario | ≤14.0M | ≤10.0M | ≤6.0M |
| Exact ABI calldata | ≤80 KiB | ≤64 KiB | ≤48 KiB |
| Largest runtime module under current EIP-170 | ≤22,000 B | ≤20,000 B | ≤16,000 B |
| Deployment transaction for each module | ≤14.0M | ≤10.0M | ≤6.0M |
| Worst-case bound | required | required | required |

The 14M ceiling deliberately leaves at least 2.77M gas below EIP-7825. Passing at 16.6M does not count as robust feasibility.

### 5.3 Two-transaction gate

A fallback passes only if:

| Metric | Hard gate | Preferred target |
|---|---:|---:|
| Maximum of A and B, current and 64/96 scenarios | ≤12.0M | ≤10.0M |
| Total A+B gas | ≤20.0M | ≤14.0M |
| Total A+B ABI calldata | ≤128 KiB | ≤96 KiB |
| Live checkpoint storage per withdrawal | fixed and bounded | one or two slots preferred |
| Abandoned state | expiry + permissionless cleanup | no permanent state |
| Value movement | only in B, atomically after full verification | same |

A two-call construction that merely fits each call but costs approximately 30M gas, as v0.3 does, is not a next-build finalist.

### 5.4 Deposit and deployment gates

| Metric | Hard research gate | Preferred target | Stretch target |
|---|---:|---:|---:|
| User deposit transaction | ≤4.0M | ≤2.0M | ≤500k |
| Direct 20-level insertion hash permutations | ≤40 | ≤22 | ≤20 |
| Pool deployment transaction | ≤14.0M | ≤8.0M | ≤4.0M |
| Zero-tree initialization | precomputed or demonstrably within deployment budget | precomputed | code-embedded/derived cheaply |

A one-transaction deposit at 14M technically fits but does not satisfy the intended “remotely good UX” objective.

### 5.5 Prover UX gates

Report results on the hardware classes in Section 8. A finalist should aim for:

| Metric | Hard research gate | Preferred target | Stretch target |
|---|---:|---:|---:|
| Median proof time, commodity 8-core x86-64 | ≤120 s | ≤30 s | ≤10 s |
| p95 proof time, commodity system | ≤180 s | ≤60 s | ≤20 s |
| Peak RSS, commodity system | ≤8 GiB | ≤4 GiB | ≤2 GiB |
| Native verification | ≤1 s | ≤250 ms | ≤100 ms |
| Deterministic setup/precomputation | documented and reusable | <1 minute | <10 seconds |

A slower candidate may remain in the report if it is uniquely strong on security or EVM cost, but it cannot be described as good UX without an explicit proving-service or precomputation model and its privacy implications.

### 5.6 Security gate

A finalist must satisfy all of the following:

- no Shor-vulnerable assumption in the accepted proof path;
- witness hiding with fresh cryptographic randomness;
- note-preimage and nullifier-preimage target of at least 100 quantum-adjusted bits under the stated model;
- commitment and accumulator binding target of at least 100 quantum-adjusted bits after multi-target accounting;
- proof soundness target of at least 100 bits under an accepted complete model;
- all transcript challenges sampled after the claims they bind;
- every proof/continuation identifier analyzed for the required collision, second-preimage, or preimage property;
- no unquantified truncation of proof Merkle digests;
- exact-instance analysis for any arithmetization-friendly permutation and mode;
- complete statement binding to pool scope, root, nullifier, recipient, relayer, and fee;
- and an explicit QROM status statement.

---

## 6. Calldata-floor sensitivity

Proof size must be treated as a first-class design metric. The following table illustrates only the floor component for proposed uniform 64/96-gas-per-byte scenarios; it excludes execution and other transaction data.

| Calldata size | 64 gas/byte floor incl. 21k | 96 gas/byte floor incl. 21k |
|---:|---:|---:|
| 48 KiB | 3,166,728 | 4,739,592 |
| 64 KiB | 4,215,304 | 6,312,456 |
| 80 KiB | 5,263,880 | 7,885,320 |
| 96 KiB | 6,312,456 | 9,458,184 |
| 128 KiB | 8,409,608 | 12,603,912 |
| 160 KiB | 10,506,760 | 15,749,640 |
| 192 KiB | 12,603,912 | 18,895,368 |
| v0.3 total proof parts, 210,284 B | 13,479,176 | 20,208,264 |

A combined v0.3-sized proof could not fit one transaction under a 96-gas-per-byte floor even with zero verifier execution. Every proof-system comparison must therefore include future-floor sensitivity.

---

## 7. Experiment governance

### 7.1 Branch policy

Create and preserve:

```text
refs/tags/pqtc-v0.3-research-baseline
research/common-bench
research/security-model
research/hash-compression
research/air-geometry
research/transcript-verifier
research/field-bakeoff
research/fri-pareto
research/hvzk-whir
research/spartan-whir
research/recursion
research/stir
research/flock
research/aggregation
research/deposit-batching
research/two-call-state
research/l2-economics
research/report-synthesis
```

A branch may contain throwaway benchmark code, but its final commit must build reproducibly or be marked `ARCHIVED_FAILED` with a reason.

### 7.2 ADR policy

Every material candidate receives an ADR, even if rejected. ADRs must contain:

- hypothesis;
- exact construction;
- assumptions;
- alternatives considered;
- measurements;
- gate result;
- reason accepted, rejected, or deferred;
- compatibility consequences;
- and any cryptographic review still required.

### 7.3 Independence policy

The engineer who implements a soundness-critical AIR or hash mode must not be the only person who validates it. At minimum:

- one implementer;
- one independent code reviewer;
- one independent benchmark/reproduction owner;
- and, for finalist cryptography, one external or organizationally independent cryptographic reviewer.

### 7.4 No silent protocol inheritance

A spike may reuse v0.3 code only where the reuse is declared. Every candidate manifest must state which of the following are inherited, modified, or replaced:

- note entropy and encoding;
- application digest;
- hash mode;
- tree arity/depth;
- public statement;
- AIR or R1CS relation;
- base/challenge field;
- PCS/LDT;
- hiding construction;
- proof MMCS;
- transcript;
- proof codec;
- EVM verifier;
- checkpoint model;
- and deployment manifest.

---

## 8. Common benchmark corpus

All serious candidates must prove the same **logical withdrawal semantics**, even where their application hashes produce different roots. Comparisons are invalid if each team chooses an easier witness, smaller tree, fewer statement fields, or different value-moving behavior.

### 8.1 Backend-neutral semantic witness

Define a backend-neutral record:

```text
SemanticWithdrawalWitness {
    corpusVersion
    caseId
    chainId
    poolAddress
    denomination
    protocolSemanticVersion
    treeDepth
    nullifierSecretBytes
    trapdoorBytes
    leafIndex
    pathBits[treeDepth]
    siblingSeeds[treeDepth]
    recipient
    relayer
    fee
}
```

`nullifierSecretBytes`, `trapdoorBytes`, and `siblingSeeds` are deterministic corpus inputs, not necessarily the final candidate’s field encoding. Each candidate must document its unbiased map from corpus bytes to canonical secret or digest material. Mapping failure or rejection is recorded, not silently reduced.

### 8.2 Required case classes

The common corpus must include at least 256 semantic cases distributed across:

- leaf indices `0`, `1`, `2`, `3`;
- indices immediately below, at, and above powers of two;
- maximum 20-bit index `2^20 - 1` using a synthetic full path;
- all-zero path bits;
- all-one path bits;
- alternating `0101…` and `1010…` paths;
- random paths;
- repeated sibling prefixes;
- high and low canonical field values;
- secrets requiring rejection sampling retries;
- fee `0`;
- fee equal to the denomination;
- small and large nonzero fees;
- recipient/relayer addresses containing many zero bytes;
- recipient/relayer addresses containing few zero bytes;
- and at least 128 fully random cases.

The corpus must also contain invalid mutations for every field and relation boundary.

### 8.3 Candidate-specific derivation

For each candidate, generate:

```text
CandidateDerivedCase {
    candidateId
    caseId
    scope
    commitment
    nullifier
    zeroNodes[]
    siblings[]
    intermediateParents[]
    root
    payoutBinding
    publicStatement
    privateWitnessEncoding
}
```

The derived record must be reproducible from the semantic corpus and candidate manifest. The candidate must not edit the semantic source case to make its encoding convenient.

### 8.4 Proof corpus

For each end-to-end candidate:

- Generate at least 30 fresh hiding proofs for one fixed witness to measure randomness-driven variation.
- Generate at least one proof for every valid semantic corpus case supported by the candidate.
- Generate at least 100 structured proof mutations.
- Generate cross-candidate proofs for at least 32 common case IDs.
- Preserve compact proof bytes, ABI calldata, parsed section lengths, and proof hashes.
- Preserve the exact random-seed source policy, but never publish live production secret material.

Deterministic proof randomness may be used in a clearly separated test-only build to produce cross-language vectors. It must be impossible to select through the operational proving API.

### 8.5 Tree-history corpus

Create deposit sequences of lengths:

```text
0, 1, 2, 3, 4, 7, 8, 15, 16, 31, 32, 63, 64,
255, 256, 1023, 1024, 4095, 4096
```

For larger capacities where executing every deposit is expensive, generate reference snapshots and paths off-chain, then verify selected inserts and roots on-chain. Include insert positions that maximize and minimize filled-subtree writes.

---

## 9. Measurement methodology

### 9.1 Hardware classes

Every candidate that reaches native proving must be measured on at least three classes:

| Class | Purpose | Minimum description |
|---|---|---|
| H1 continuity | compare with prior M4 Max work | exact Apple model, performance/efficiency cores, RAM, macOS version |
| H2 commodity | approximate ordinary user hardware | 6–12 physical-core x86-64 or ARM64, 16–32 GiB RAM |
| H3 high-end | characterize best practical local proving | 24+ physical cores, 64+ GiB RAM |

Optional but valuable:

- H4 portable scalar build without AVX-512/NEON-specific acceleration;
- H5 WASM/browser build;
- H6 GPU-assisted build where the protocol remains identical.

Record:

- CPU model and microcode;
- physical/logical cores;
- RAM type and capacity;
- OS and kernel;
- power mode;
- compiler and linker versions;
- `RUSTFLAGS` and target features;
- parallel thread count;
- allocator configuration;
- CPU affinity;
- thermal state where observable;
- and whether other benchmark jobs were running.

### 9.2 Statistical protocol

For microbenchmarks:

- one warm-up phase;
- at least 100 measured iterations for operations above 1 ms;
- enough iterations to exceed 10 seconds total for smaller operations;
- report median, p90, p95, p99, minimum, maximum, mean, and standard deviation.

For complete proof generation:

- at least 30 runs on H1 and H2 for finalists;
- at least 10 runs for early candidates;
- fresh hiding randomness each run;
- report wall time, CPU time, peak RSS, total allocated bytes if available, and output size.

Never present the fastest of several runs as the primary result. Upstream “best of N” numbers may be reproduced for compatibility but must be labeled separately.

### 9.3 EVM execution environments

At minimum run:

1. Foundry/Anvil using the exact target EVM revision.
2. One independent execution client in a local devnet, such as geth, Nethermind, reth, Besu, Erigon, or ethrex, with the exact fork rules.
3. The designated public testnet only for finalists and only after explicit authorization.

Record the client commit, chain config, block gas limit, transaction gas limit, base fee, hardfork activation, and RPC method used.

### 9.4 Complete transaction measurement

For every user-facing operation collect:

- raw transaction bytes;
- signed transaction hash in network tests;
- ABI calldata bytes;
- zero and nonzero calldata bytes;
- standard intrinsic gas;
- applicable calldata floor;
- execution gas before and after refunds;
- receipt `gasUsed`;
- transaction gas limit;
- call trace;
- opcode histogram;
- memory high-water mark if the client exposes it;
- cold/warm storage-access counts;
- external-call count;
- log bytes;
- contract runtime code sizes;
- initcode sizes;
- and code-deposit gas.

Function-level `gasleft()` deltas are diagnostic only. The gate uses a complete top-level transaction.

### 9.5 Gas schedule scenarios

Implement a single canonical calculator that reports:

```text
ACTIVE_EIP7623
SCENARIO_EIP7976_64_PER_BYTE
SCENARIO_EIP8311_96_PER_BYTE
```

For every proof transaction provide all three results. The simulator must include creation-specific costs where relevant. If a proposed EIP changes before the report is finalized, preserve the old scenario and add the new one rather than rewriting historical results.

### 9.6 Proof-size decomposition

Every proof must produce a byte ledger:

```text
common header
parameter/version binding
public statement
commitment roots
OOD openings
masking openings
quotient openings
query indices
input rows
MMCS salts
MMCS frontiers
FRI/WHIR/STIR round objects
final polynomial/base case
grinding witnesses
continuation data
ABI head/tail/padding
other
```

Report raw proof bytes and exact ABI call bytes separately.

### 9.7 Verifier cost decomposition

Instrument at least:

- parsing and canonicality;
- transcript absorption and squeezing;
- challenge sampling/rejection;
- AIR/R1CS constraint evaluation;
- quotient/DEEP reductions;
- alpha-power or Horner accumulation;
- inversions and exponentiations;
- input commitment authentication;
- FRI/WHIR/STIR folding;
- final polynomial/base-case checks;
- checkpoint storage/cleanup;
- pool statement validation;
- nullifier storage;
- payout calls;
- and event emission.

Use both isolated component harnesses and the complete transaction. Isolated components must not be summed as a substitute for the full call because memory expansion, warm accesses, inlining, and compiler behavior are nonlinear.

### 9.8 Prover cost decomposition

Instrument:

- witness construction;
- application hashing;
- trace generation;
- LDE/FFT/NTT;
- commitments;
- masking;
- quotient construction;
- OOD openings;
- query generation;
- low-degree proof;
- proof serialization;
- and optional recursion/aggregation.

For parallel implementations, report scaling at 1, 2, 4, 8, 16, and maximum physical-core counts where hardware permits.

---

## 10. Security analysis methodology

### 10.1 Required separation of claims

Every candidate security report must distinguish:

- **primitive-family rationale:** why the primitive is expected to resist quantum algorithms better than discrete-log constructions;
- **generic attack ceilings:** Grover, BHT/collision, multi-target, and exhaustive-search estimates;
- **structural cryptanalysis:** exact attacks against the selected field, width, matrix, S-box, rounds, and mode;
- **proof-system theorem bounds:** proven UDR/LDR or corresponding PCS/sumcheck bounds;
- **heuristic/conjectural estimates:** including every omitted term;
- **Fiat–Shamir/QROM status:** theorem, reduction, assumption, or open question;
- **zero-knowledge theorem status:** which protocol components are hidden and under what randomness assumptions;
- **implementation assurance:** tests, differential vectors, formal proofs, and audits;
- **operational privacy:** metadata not hidden by the proof.

### 10.2 Independent soundness calculator

Do not rely on one library function. Build or adapt an independent calculator that consumes the candidate manifest and emits a term-by-term report. It must include:

- trace/domain size;
- constraint count and degree;
- number of committed/batched functions;
- DEEP or sumcheck terms;
- query-phase soundness;
- commit-phase soundness;
- final polynomial/base-case soundness;
- challenge-field ceiling;
- commitment collision security;
- grinding at each site;
- quantum adjustment to grinding;
- multi-target adjustment;
- and composition across inner/outer proofs where applicable.

Cross-check the result against upstream tooling. Disagreement is a blocker until explained.

### 10.3 Plonky3 conjectured-result correction

The pinned Plonky3 security source states that the random-words conjectural path does not model `num_batched_functions` and is optimistic relative to the proven path for batched openings. Therefore:

- do not present v0.3’s 107-bit figure as complete soundness accounting;
- explicitly state that its 210-function batching term is omitted by that conjectural path;
- reproduce q32 and q48 with the independent calculator;
- and require any future conjectural estimate to disclose which terms remain unmodeled.

### 10.4 Hash-mode worksheet

For every application hash/compression candidate record:

```text
field
field bit length
permutation family/version
state width
rate/capacity if sponge
input width if compression
output field count
output encoded bytes
S-box
full/partial rounds
linear layers/matrices
round-constant derivation
mode of operation
feed-forward rule
truncation rule
domain separation
length separation
level separation
preimage estimate
second-preimage estimate
collision estimate
quantum generic estimates
multi-target assumptions
known applicable attacks
known inapplicable attacks with justification
external review status
```

A 512-bit carrier does not imply 256 quantum collision bits. Security is limited by the actual mode, capacity, output width, and structural attacks.

### 10.5 Continuation and identifier analysis

For each of the following, state whether security requires collision, chosen-prefix collision, second-preimage, or preimage resistance:

- statement key;
- global-data digest;
- checkpoint digest;
- proof ID;
- verification ID;
- parameter ID;
- runtime/deployment manifest ID;
- note checksum;
- and any aggregation/batch ID.

The v0.3 use of single Keccak-256 in A/B continuation binding must be analyzed. Unless a reduction establishes that only a stronger preimage-style property is needed, benchmark a KeccakPair512 replacement and treat a generic 256-bit quantum collision ceiling as a potential system-level limitation.

### 10.6 Zero-knowledge evidence

For each candidate provide:

- the theorem or paper section establishing hiding;
- the exact implementation path;
- randomness quantity and source;
- simulator or indistinguishability tests where supported;
- proof-shape dependence on witness;
- query-collision behavior;
- malformed-input behavior;
- timing/memory side-channel observations;
- and whether recursion or aggregation changes the argument.

“Two proofs differ” is a sanity check, not a zero-knowledge proof.

### 10.7 Multi-target scenarios

Report security under at least these lifetime scenarios:

```text
one proof / one pool
2^20 proofs across one parameter set
2^32 proofs across one parameter set
2^40 proofs across multiple pools or chains
```

The report must state how the target count affects each relevant preimage, collision, grinding, and soundness term. Do not assume all terms degrade identically.

---

## 11. Repository and evidence layout

Create this structure without deleting the existing repository layout:

```text
research/
├── README.md
├── common-corpus/
│   ├── semantic-cases.json
│   ├── invalid-mutations.json
│   ├── corpus-manifest.json
│   └── generators/
├── harness/
│   ├── benchctl/
│   ├── gas-schedules/
│   ├── proof-ledger/
│   ├── hardware-detect/
│   └── report-generator/
├── candidates/
│   └── <candidate-id>/
│       ├── README.md
│       ├── ADR.md
│       ├── manifest.json
│       ├── assumptions.md
│       ├── source-hashes.json
│       ├── vectors/
│       ├── proofs/
│       ├── gas/
│       ├── native/
│       ├── security/
│       └── status.json
├── runs/
│   └── <run-id>.json
├── summaries/
│   ├── all-runs.csv
│   ├── candidate-summary.csv
│   ├── pareto.json
│   └── gate-status.json
├── external-baselines/
├── advisories/
├── cryptanalysis/
└── final/
    ├── NEXT_GENERATION_RESEARCH_REPORT.md
    ├── EXECUTIVE_MATRIX.csv
    ├── UNRESOLVED_QUESTIONS.md
    └── evidence-manifest.json
```

Every generated artifact must have SHA-256 and Keccak-256 hashes in `evidence-manifest.json`.

---

## 12. Program sequencing

The spikes are organized into waves. A later wave may begin only when its required inputs exist; independent work may proceed in parallel.

```text
Wave 0: baseline and measurement discipline
  SP-00 Baseline reproduction
  SP-01 Security-accounting reconstruction
  SP-02 Advisory and source-applicability matrix

Wave 1: attack the current structural costs
  SP-10 Fixed-length application compression
  SP-11 Merkle shape and direct-deposit design
  SP-12 Deposit batching/root-transition alternative
  SP-20 AIR geometry and degree
  SP-30 Transcript redesign
  SP-31 Verifier arithmetic and codec optimization
  SP-40 Field/extension bakeoff

Wave 2: proof-backend alternatives
  SP-50 FRI parameter Pareto sweep
  SP-51 HVZK-WHIR
  SP-52 STIR lower-bound/hiding readiness
  SP-53 Circle/hiding watch track
  SP-60 Structured Spartan-WHIR
  SP-61 Recursive PQ compression
  SP-62 Flock + zero-knowledge track

Wave 3: product-level alternatives and integration
  SP-70 Individual-proof aggregation and batch withdrawals
  SP-71 L2 execution/economics
  SP-72 Robust two-transaction state machine
  SP-73 Prover UX and deployment operations
  SP-80 Integrated finalist prototypes

Wave 4: synthesis
  SP-90 Pareto analysis
  SP-91 Independent reproduction
  SP-92 Final research report
```

Wave 2 must use the best relation candidates produced by Wave 1. Do not benchmark proof systems only on toy Fibonacci or a different hash relation and infer PQTC performance.

---

# Part II — Required research spikes

## SP-00 — Freeze and reproduce the v0.3 baseline

### Purpose

Create a trustworthy comparison point. No candidate result is meaningful until the report’s v0.3 measurements and artifacts can be regenerated from the frozen source.

### Hypothesis

The report accurately describes a reproducible local build, but its single canonical proof is insufficient to establish worst-case gas or proof-size behavior.

### Required work

1. Tag the exact source snapshot as `pqtc-v0.3-research-baseline`.
2. Verify every source and generated-artifact hash listed in the engineering report.
3. Rebuild from a clean container using the pinned:
   - Rust toolchain;
   - Plonky3 commit;
   - Solidity compiler;
   - Foundry version;
   - Node and package-manager versions;
   - optimizer configuration;
   - and EVM revision.
4. Re-run the documented Rust, TypeScript, Solidity, invariant, lint, code-size, and Docker tests.
5. Regenerate all parameter packages twice and byte-compare them.
6. Generate at least 30 fresh q32 hiding proofs for one fixed witness and at least 30 proofs across distinct witnesses.
7. Execute complete A/B pool-facing transactions for all generated proofs.
8. Measure pool and verifier deployment transactions, including constructor work and code-deposit cost.
9. Create an opcode-level and component-level profile for deposit, A, and B.
10. Run the same proof transactions on a second local execution client.

### Required data

For each proof and transaction:

- proof part sizes;
- global-data and frontier sizes;
- number of unique query indices;
- zero/nonzero byte counts;
- calldata tokens;
- execution gas;
- active floor gas;
- 64/96 scenario gas;
- total transaction gas;
- gas margin;
- transaction success/failure;
- and proof-generation time/RSS.

For deployment:

- initcode bytes;
- runtime bytes;
- constructor execution gas;
- code-deposit gas;
- total creation transaction gas;
- and whether the transaction fits EIP-7825.

### Correctness checks

- All regenerated proofs verify natively and on EVM.
- Every report mutation test still fails.
- Repeated proofs differ due to fresh masking.
- Rust and Solidity transcript values agree.
- The exact top-level ABI payload used for gas measurement is committed.

### Deliverables

```text
research/candidates/v03-baseline/
research/runs/v03-*.json
research/summaries/v03-distribution.csv
research/candidates/v03-baseline/deployment-gas.md
research/candidates/v03-baseline/opcode-profile.md
```

### Gate

**Pass:** all source hashes match; all suites reproduce; median gas is within 1% of the report; every discrepancy above 1% is explained; at least 60 fresh proofs have complete run records; deployment gas is known.  
**Conditional:** build reproduces but gas differs due to a documented compiler/client change; preserve both profiles.  
**Fail:** source snapshot cannot regenerate the reported parameter ID/proof behavior, or native/EVM verification diverges. Stop all comparative work until resolved.

---

## SP-01 — Reconstruct soundness and PQ security accounting independently

### Purpose

Replace headline security numbers with an auditable term-by-term model that can grade every future candidate.

### Hypothesis

The v0.3 `107-bit` conjectural figure is optimistic because the pinned Plonky3 conjectural path omits the batched-opening function count, while the `56-bit` proven result is conservative but applicable. A better relation/PCS may restore a defensible 100-bit target without reducing queries.

### Required work

1. Read the exact pinned Plonky3 security implementation and cited papers.
2. Implement an independent security calculator or a checked translation of the formulas.
3. Reproduce v0.3 q32 and v0.2 q48 term by term.
4. Explain every difference from Plonky3 output.
5. Include all 210 batched functions in applicable terms.
6. Model:
   - UDR;
   - LDR;
   - random-words conjecture;
   - AIR random-linear-combination error;
   - DEEP-ALI error;
   - batched-opening proximity error;
   - FRI commit/query phases;
   - challenge-field cap;
   - MMCS binding;
   - grinding;
   - quantum grinding adjustment;
   - and multi-target use.
7. Produce profiles targeting 80, 100, 112, and 128 bits for each relation supplied by later spikes.
8. Add exact composition support for recursive and aggregated proofs.
9. Document whether proof-of-work is treated as classical cost, quantum cost, or both.
10. Request independent cryptographic review of the calculator before any candidate is labeled security-qualified.

### Required data presentation

For every profile emit both JSON and a human-readable table:

| Term | Formula/source | Inputs | Classical bits | Quantum-adjusted bits | Proven/conjectural | Binding? |
|---|---|---:|---:|---:|---|---|

Also emit a “security bottleneck” list ordered from lowest to highest bit level.

### Required negative tests

- Removing batched functions must visibly change the applicable result.
- Doubling target proof count must affect multi-target terms where expected.
- Reducing challenge-field degree must lower the challenge ceiling.
- Increasing queries must not accidentally lower reported security.
- Invalid or unbuildable degree/blowup combinations must be rejected.
- ZK degree padding must be accounted for separately from logical AIR height.

### Deliverables

```text
research/security-model/
├── README.md
├── calculator/
├── formulas.md
├── v03-q32.json
├── v02-q48.json
├── cross-check.md
├── multi-target.md
└── external-review-request.md
```

### Gate

**Pass:** independent calculations reproduce upstream results or explain differences; the omission in the conjectural batch term is documented; candidate manifests can be graded automatically; one independent reviewer accepts the implementation methodology.  
**Fail:** no consistent model can be produced. In that case all security numbers remain unqualified, and no next-build finalist may be selected.

---

## SP-02 — Plonky3 advisory and source-applicability matrix

### Purpose

Determine whether known upstream issues are fixed, inapplicable, or accidentally reintroduced by the custom prover, transcript, codec, and Solidity verifier.

### Required advisory set

At minimum assess:

- purported opened values not included in transcript;
- missing FRI size checks;
- missing final-polynomial degree check;
- variable-length sponge collision issue;
- MultiField32Challenger transcript malleability/entropy loss;
- native verifier panic behavior on malformed proofs;
- and every advisory published before final report freeze.

### Required work

For each advisory:

1. Identify upstream affected versions and patch commit.
2. Determine whether the pinned Plonky3 commit contains the patch.
3. Identify every analogous project code path.
4. Write a regression test that would fail if the issue existed.
5. State whether the native prover, native verifier, Solidity verifier, or all are affected.
6. Record residual assumptions.

### Deliverable table

| Advisory | Upstream affected path | Pinned status | Custom analogous path | Regression test | Result | Residual risk |
|---|---|---|---|---|---|---|

### Gate

**Pass:** every advisory has a disposition and executable regression test where applicable.  
**Fail:** any high-severity issue is applicable or uncertain in the accepted path. No candidate integration proceeds until resolved.

---

## SP-10 — Fixed-length application compression

### Purpose

Replace the current general-purpose P2BB512 sponge/XOF in fixed-size application roles with a smaller, explicitly analyzed fixed-length compression design.

### Core hypothesis

A unified width-24 or width-32 Poseidon2 compression mode can reduce the withdrawal relation from 240 application permutations to approximately 22–44 and reduce direct deposit hashing by roughly an order of magnitude, while retaining a post-quantum-oriented binding target.

### Important boundary

This spike is cryptographic design work. Do not invent a compression function, truncate outputs, or select rounds solely from gas measurements. Begin from published Poseidon2 compression constructions and exact current cryptanalysis. Every candidate is `BENCHMARK_ONLY` until its mode and parameters receive independent review.

### Candidate matrix

Implement at least the following conceptual candidates. Exact layouts must be written in ADRs before code.

| ID | Permutation | Digest fields | Intended node cost | Purpose |
|---|---|---:|---:|---|
| H0 | current width-16 sponge | 16 | 11 permutations | baseline |
| H1 | width-16 fixed compression, output below security target | ≤7 | 1 | performance negative control only |
| H2 | reviewed width-16 multi-permutation wide-output construction | 10–12 | 2–4 | determine whether preserving width 16 is competitive |
| H3 | width-24 feed-forward compression | 10 | 1 | faster/smaller candidate, narrow security margin |
| H4 | width-24 feed-forward compression | 11 | 1 | stronger width-24 candidate |
| H5 | width-32 unified compression | 12 | 1 | primary candidate |
| H6 | width-32 compression | 14 or 15 | 1 for nodes, possibly >1 for notes | conservative-output comparator |
| H7 | one mature non-Poseidon algebraic comparator | project-selected | measured | avoid a Poseidon-only local optimum |

H1 may not be used in a mixer; it establishes the lower gas bound for one-permutation hashing.

### Primary width-32 hypothesis

Test, but do not pre-approve, a design in which one width-32 permutation handles every application role with a 12-field digest:

```text
Merkle node candidate input:
    left[12] || right[12] || domain || level || version || shape || zero[4]

Note candidate input:
    scope[12] || nullifierSecret[8] || trapdoor[8]
    || domain || version || shape || zero

Nullifier candidate input:
    scope[12] || nullifierSecret[8]
    || domain || version || shape || zero[...] 

Candidate output:
    Tr_12(P(x) + x), or the exact reviewed Poseidon2 compression rule
```

This layout is only a research hypothesis. The final input/output lane assignment must be justified against published mode requirements and applicable attacks.

### Generic security worksheet for candidate output widths

Use these only as idealized ceilings before structural and mode analysis. For BabyBear, `log2(p) ≈ 30.91`:

| Output fields | Approx. output bits | Generic BHT quantum collision ceiling | Interpretation |
|---:|---:|---:|---|
| 7 | 216.4 | 72.1 bits | performance lower bound; fails target |
| 10 | 309.1 | 103.0 bits | very narrow target margin |
| 11 | 340.0 | 113.3 bits | moderate generic margin |
| 12 | 370.9 | 123.6 bits | preferred minimum for conservative comparison |
| 14 | 432.7 | 144.2 bits | wider output, higher state/storage cost |

The Poseidon2 paper's fixed-length compression discussion includes classical conditions of the form `p^n >= 2^(2κ)` for output width and `p^(t-n) >= 2^κ` for the hidden state. Engineers must not treat those classical conditions as a complete quantum proof; the cryptanalysis packet must adapt the target model explicitly.

### Required design questions

For every candidate answer:

- Does the construction use sponge or compression mode?
- Is feed-forward required?
- Which input lanes are truncated into output?
- How are domain, protocol version, operation shape, tree level, and payload length bound?
- Can two semantic operations share the same state shape?
- Is the output wide enough after generic quantum collision and multi-target accounting?
- Is the remaining unobserved state large enough for the compression theorem?
- Are round counts valid for the exact field/width/matrix/mode?
- Which 2025–2026 algebraic attacks apply?
- Does the candidate use upstream constants or newly generated constants?
- How are constants independently regenerated and verified?
- Does one candidate support scope, note, nullifier, empty leaf, Merkle node, and any statement hash without ad hoc exceptions?

### Implementation stages

#### Stage A — primitive-only

Implement the permutation and compression in Rust and Solidity. Generate at least 10,000 cross-language vectors, including all canonical field boundaries and domain/level mutations.

#### Stage B — application roles

Implement scope, note, nullifier, empty leaf, node, and optional statement binding. Preserve separate domain tags and fixed-width schemas.

#### Stage C — direct tree

Implement a depth-20 incremental tree harness and compare roots in Rust, TypeScript, and Solidity.

#### Stage D — relation projection

Count exact application permutations for one withdrawal, active rows for proposed AIRs, and estimated proof cost. Do not yet build the full proof unless the primitive gate passes.

### Required measurements

For each candidate:

- field operations per round and per permutation;
- full/partial rounds;
- Solidity gas per permutation;
- gas per compression;
- gas per note commitment;
- gas per nullifier;
- gas per Merkle node;
- gas for 20-level insertion with no storage;
- gas for full deposit including storage;
- constructor zero-tree cost;
- runtime and initcode bytes;
- Rust throughput single-threaded and parallel;
- expected AIR permutation count;
- digest bytes and storage slots;
- generic classical and quantum estimates;
- exact attack applicability;
- and external review status.

### Correctness and misuse tests

- left/right child swap changes the parent;
- changing level changes the parent;
- changing operation domain changes the output;
- changing protocol version changes the output;
- all noncanonical inputs are rejected;
- no alternate byte/field encoding is accepted;
- no length-extension ambiguity exists;
- output lane order is identical across languages;
- constant generation is reproducible;
- and the application role cannot be reinterpreted under another role.

### Gate

A candidate proceeds to AIR work only if:

- it reduces Merkle-node permutations by at least 5× versus H0;
- a complete direct deposit is projected or measured below 4M gas;
- digest binding reaches at least the 100-bit quantum-oriented project target under the stated generic model;
- no known structural attack is projected below that target;
- exact mode/parameters are documented;
- and an independent reviewer agrees that the candidate is worth deeper analysis.

**Preferred pass:** approximately one permutation per node, no more than 24 total application permutations per withdrawal, and deposit below 2M gas.  
**Stop:** any candidate with less than 100-bit target, ambiguous mode security, nonreproducible constants, or no meaningful advantage over H0.

---

## SP-11 — Merkle shape, digest width, and direct-deposit design

### Purpose

Determine the cheapest accumulator design that preserves the desired anonymity-set capacity and binding target.

### Required variants

At minimum compare:

1. binary depth-20 tree with the best SP-10 compression;
2. binary tree with a narrower digest candidate, where security-qualified;
3. higher-arity tree only if an exact one- or two-permutation compressor can hold all children at the required output security;
4. bounded root history versus unlimited historical roots;
5. precomputed zero tree versus constructor-computed zeros;
6. filled-subtree storage layouts using packed or code-embedded constants.

Do not reduce tree capacity merely to improve the benchmark without presenting that as a separate product tradeoff.

### Required measurements

- tree depth and capacity;
- hashes/permutations per insert and path;
- storage reads/writes per position class;
- best/worst insert gas;
- root-history gas and state growth;
- zero-tree deployment cost;
- proof witness bytes;
- AIR/R1CS membership cost;
- and effect on anonymity-set semantics.

### Position sweep

Measure inserts at all low indices `0..255` and at synthetic positions around every power of two through `2^20`. Report worst observed and analytically worst storage transition.

### Gate

Retain binary depth 20 unless an alternative provides at least 20% end-to-end withdrawal improvement or 30% deposit improvement without reducing security/capacity or materially increasing audit complexity. A tiny hash-count win does not justify a new tree arity.

---

## SP-12 — Permissionless batched deposit-root transitions

### Purpose

Establish a fallback if direct on-chain insertion remains expensive after fixed compression.

### Hypothesis

Users can deposit cheaply into a canonical commitment queue, while permissionless provers amortize a PQ root-transition proof over many deposits. This can reduce user deposit gas without trusting an updater, at the cost of finalization latency and a second proof relation.

### Required designs

Compare at least:

- direct insertion baseline;
- queue batches of 8, 16, 32, 64, and 256 commitments;
- fixed-cadence and size-triggered finalization;
- permissionless finalizer with no privileged key;
- timeout/refund or forced-single-insert fallback;
- proof verifying `oldRoot + orderedCommitments -> newRoot`;
- and whether the transition proof can share the withdrawal verifier/PCS.

### Safety requirements

- Commitment order must be canonical and on-chain committed.
- No finalizer can omit, reorder, or substitute a queued commitment.
- User funds cannot be trapped permanently by absent finalizers.
- Refunds must not create duplicate live commitments or break accounting.
- A queued but unfinalized commitment cannot be withdrawn.
- The proof path remains PQ-oriented and hiding is not required for public deposit data unless private metadata is introduced.

### Required measurements

- user deposit gas;
- finalization gas total and per leaf;
- transition proof bytes;
- proving time/RSS;
- minimum economical batch size;
- expected finalization latency under several arrival rates;
- griefing costs;
- forced-fallback cost;
- and state growth.

### Gate

Proceed only if direct deposits remain above 2M gas or the batched design reduces user deposit gas by at least 60% and amortized total gas by at least 30%. Reject any design requiring a trusted or always-online operator.

---

## SP-20 — AIR geometry and constraint-degree redesign

### Purpose

Find the trace geometry that minimizes **complete EVM verification cost**, rather than merely minimizing native trace height.

### Core hypothesis

A taller, narrower, lower-degree AIR can be substantially cheaper than v0.3’s 256×190 horizontal AIR because each low-degree query opens fewer fields, the number of batched functions falls, quotient degree/chunks shrink, and EVM extension-field accumulation becomes smaller.

### Baseline

The v0.3 AIR evaluates one complete width-16 Poseidon2 permutation in one row using a 157-column maintained sub-AIR. It is prover-friendly but creates:

- 190 trace columns;
- 210 batched functions;
- degree-seven constraints;
- sixteen quotient chunks;
- and wide query openings.

### Required candidate families

Use the winning SP-10 application primitive. Implement at least:

#### A0 — Existing horizontal reference

Keep one full permutation per row. This is the correctness reference and may use an upstream maintained AIR.

#### A1 — Full-round vertical, all S-boxes parallel

Carry permutation state across rows. One row evaluates a full or partial round. Use explicit intermediates for `x²`, `x⁴`, and `x⁷`.

#### A2 — Lane-serialized vertical

Carry the full state but evaluate only a fixed number of S-box lanes per row. Sweep lane parallelism:

```text
1, 2, 4, 8, 16, full width
```

The objective is a Pareto frontier between width and height.

#### A3 — Multi-table relation

Separate:

- a controller/path table;
- an application-compression table;
- optional fixed/preprocessed round tables;
- and a linking permutation/lookup argument.

This candidate is worthwhile only if the linking argument costs less than carrying controller and hash state together.

#### A4 — Backend-neutral structured relation

Express the same fixed-compression relation in a structure suitable for Spartan/WHIR or another multilinear backend. This is not required to share the AIR implementation, but it must share canonical vectors and semantics.

### Degree decomposition

Do not retain degree-seven S-box constraints merely because Poseidon2 uses `x^7`. At minimum benchmark:

```text
a = x * x
b = a * a
c = b * a
y = c * x
```

or another checked decomposition using degree-two/three constraints. Record:

- extra columns;
- extra rows;
- maximum degree;
- quotient degree;
- quotient chunks;
- and total verifier cost.

The candidate with the fewest constraints is not necessarily the cheapest proof.

### Round-constant and selector handling

Compare:

- ordinary trace columns;
- preprocessed columns committed once;
- verifier-derived constants;
- code-embedded constants;
- and hardcoded selector polynomials.

A fixed column does not become free merely because it is public. Record whether it adds commitments/openings and how the EVM obtains it.

### Required geometry sweep

For every lane-parallelism and table design report:

| Metric | Required |
|---|---|
| logical rows | yes |
| padded rows | yes |
| base degree bits | yes |
| hiding degree bits | yes |
| trace width by table | yes |
| preprocessed width | yes |
| constraint count | yes |
| maximum degree | yes |
| quotient degree/chunks | yes |
| batched functions | yes |
| transition rotations | yes |
| active vs padding rows | yes |
| estimated query-open bytes | yes |
| actual proof bytes | for finalists |
| native proving time/RSS | for finalists |
| EVM AIR/DEEP gas | for finalists |

### Required correctness strategy

1. Define a plain reference compression and withdrawal function.
2. Generate candidate traces from the same derived corpus case.
3. Validate every constraint without generating a proof.
4. Compare all intermediate compression outputs.
5. Mutate every witness group, selector, round constant, S-box intermediate, state lane, path bit, level, and output.
6. Differentially compare Rust symbolic evaluation with generated Solidity evaluation.
7. Use constraint-coverage instrumentation to show which tests activate each constraint family.
8. Preserve a machine-readable column-lifetime map.

### Solidity projection

Before building the complete proof verifier, generate an OOD AIR evaluator and measure:

- gas per constraint family;
- gas per opened trace column;
- gas per quotient chunk;
- memory allocation/copying;
- and code size.

### Gate

A new AIR family proceeds to PCS integration only if it:

- preserves the complete relation;
- lowers maximum degree or clearly compensates for it elsewhere;
- reduces opened trace bytes by at least 3× versus v0.3 **or** reduces projected total verifier gas by at least 35%;
- reduces batched functions materially from 210;
- and has no uncovered workspace or selector transition.

**Preferred pass:** no more than 80 main-trace columns, no more than eight quotient chunks, maximum degree three, and projected one-proof calldata below 100 KiB at a security profile stronger than q32.  
**Stop:** a taller AIR whose proof becomes larger or more expensive after padding/FRI, even if its row width is lower.

---

## SP-21 — Structured relation and repeated-computation decomposition

### Purpose

Create a backend-neutral representation that exposes repeated hash/compression structure to multilinear systems rather than flattening it into an unstructured generic constraint matrix.

### Required work

Represent one withdrawal as:

```text
22-ish repeated application-compression invocations
+ fixed input/output glue
+ 20 path-order selections
+ leaf-index/path consistency
+ public statement binding
```

for the SP-10 finalist. Preserve explicit repetition metadata:

- one repeated compression circuit/function `F`;
- batch size;
- per-instance inputs/outputs;
- glue relation `G`;
- and public/private partition.

Produce:

- AIR form;
- R1CS/CCS form;
- Boolean form where relevant;
- nonzero count;
- variable count;
- repeated-block count;
- glue constraint count;
- and memory layout.

### Required tests

The structured relation and AIR reference must accept/reject the same corpus cases. Mutation tests must target both the repeated block and glue.

### Gate

Proceed to Spartan-WHIR or Flock only if the structure is retained by the proving API. Reject a generic reduction that expands the relation so much that the repeated-function advantage disappears.

---

## SP-30 — Fiat–Shamir transcript batching and continuation binding

### Purpose

Reduce the v0.3 transcript/parsing baseline while preserving challenge order, typed encodings, and post-quantum-oriented binding.

### Core hypothesis

Absorbing complete typed arrays at each challenge boundary can replace hundreds of short KeccakPair512 transitions with dozens of larger Keccak operations and remove a substantial fraction of the approximately 2.93M parsing/transcript/storage baseline.

### Transcript boundary graph

Before changing code, produce a directed graph showing:

```text
claim/object observed
    -> challenge sampled
    -> later object depending on challenge
```

No batching may move a claim across a challenge boundary. Adjacent items may be grouped only where the protocol samples no challenge between them.

### Required transcript candidates

#### T0 — v0.3 field-by-field baseline

One typed absorb per base-field or commitment item.

#### T1 — typed array absorb

```text
state' = K512(
    TRANSCRIPT_ABSORB,
    state || itemType || elementCount || byteLength || canonicalArrayBytes
)
```

One transition per logical array or protocol object.

#### T2 — item digest plus state transition

```text
itemDigest = K512(TRANSCRIPT_ITEM, type || count || bytes)
state'     = K512(TRANSCRIPT_ABSORB_DIGEST, state || type || count || itemDigest)
```

This may simplify calldata slicing and transcript proofs at the cost of an extra pair of hashes per group.

#### T3 — challenge-boundary frame

Absorb all adjacent protocol objects before one challenge in a single fixed grammar:

```text
frameVersion || frameType || objectCount ||
    objectType || objectLength || objectBytes || ...
```

### Required continuation changes

Benchmark replacing security-critical single-Keccak identifiers with full-width bindings:

- `statementKey`;
- `globalDigest`;
- `checkpointDigest`;
- `coreProofId`;
- and any A/B continuation ID.

A mapping may use one 32-byte storage key, but the stored/checked continuation must retain the full accepted digest where collision resistance is required.

### Challenge sampling

For every candidate document:

- output stream construction;
- counter semantics;
- rejection sampling;
- endian order;
- base vs extension sampling;
- bit-query sampling;
- reset behavior after absorb;
- and domain separation.

No modulo reduction unless quantitatively justified and protocol-versioned.

### Required measurements

- number of Keccak-256 invocations by phase;
- bytes hashed by phase;
- memory allocations/copies;
- transcript gas;
- parser gas;
- runtime code size;
- proof bytes changed;
- Rust proving/verification delta;
- and full transaction delta.

### Required vectors and tests

- one vector after every absorb and squeeze;
- Rust/Solidity/TypeScript parity;
- object reordering;
- array truncation;
- count mismatch;
- ambiguous trailing zeros;
- item-type substitution;
- challenge-before-claim regression;
- branch-half swaps;
- and A/B cross-proof mixing.

### Gate

A transcript candidate proceeds if it:

- preserves exact binding order;
- has a simple canonical grammar;
- saves at least 1.0M gas in the v0.3 verifier or at least 20% of transcript/parsing cost in the redesigned verifier;
- does not increase proof calldata materially;
- and has an external-review-ready transcript specification.

**Preferred pass:** at least 1.5M full-path gas savings and full-width continuation bindings.  
**Stop:** batching that obscures challenge boundaries or relies on ambiguous concatenation.

---

## SP-31 — Verifier arithmetic, memory, codec, and MMCS optimization

### Purpose

Measure local verifier improvements independently from the larger AIR/PCS redesign, so they can be applied to whichever finalist wins.

### Required optimization experiments

Each item must be benchmarked separately and then in combination.

#### V1 — Streaming alpha accumulation

Replace materialization of hundreds of alpha powers with Horner-style or streamed accumulation where protocol order permits. Compare memory, multiplication count, and gas.

#### V2 — Checked inverse witnesses

Allow the proof to supply selected inverses and verify `d * dInv = 1` instead of exponentiating in the EVM. Include the added calldata under all floor scenarios. Test:

- DEEP denominators;
- batch inversions;
- FRI fold points;
- selector denominators;
- and quotient recomposition denominators.

Do not supply an inverse where zero is legal or where the protocol requires proving nonzero separately.

#### V3 — Fused canonical parse and dot product

Canonicality-check each field as it is consumed into the dot product, avoiding a separate full pass.

#### V4 — Eliminate memory copies

Measure calldata-native evaluators, fixed-size packed structures, and bounded scratch memory instead of copying trace arrays between registry and verifier modules.

#### V5 — Fixed constant and power tables

Benchmark code-embedded constants, derived constants, and calldata-provided checked constants. Account for code size and deployment gas.

#### V6 — Query-point computation

Compare exponentiation, incremental generation, proof-supplied checked points, and small fixed tables.

#### V7 — MMCS frontier and digest width

Measure:

- current binary pruned frontier;
- exact worst-case frontier;
- Merkle caps;
- alternative cap heights;
- 512-bit digests;
- and only externally reviewed 384/320-bit truncation candidates.

A single 256-bit digest is a performance lower bound, not an accepted 100-bit quantum-collision candidate.

#### V8 — Canonical proof codec

Compare:

- current 32-bit-per-BabyBear encoding;
- safe 31-bit packing;
- section-level compression with cheap EVM decompression;
- omission of values that are transcript-derived rather than prover-selected;
- and removal of duplicated global data in a one-transaction verifier.

The codec must remain uniquely decodable and bounded before allocation or loops.

#### V9 — Query split optimizer

For the robust two-call path, evaluate every split compatible with the verifier, not only 16/16:

```text
8/24, 10/22, 12/20, 13/19, 14/18, 15/17, 16/16
```

Also vary AIR-segment placement. Optimize the minimum gas margin, not equal query count.

### Required data

For each optimization report:

- baseline and changed opcode counts;
- execution gas;
- calldata delta;
- active/64/96 total-gas delta;
- runtime byte delta;
- proof byte delta;
- prover/native-verifier delta;
- new assumptions;
- and differential-test count.

### Gate

Keep an individual optimization only if it saves at least 2% of complete verifier gas, removes a known security risk, or materially reduces worst-case proof bytes. Micro-optimizations below 2% may be grouped only if they simplify code rather than add audit surface.

The combined package should target at least 1.5M gas savings against the same relation/proof profile. It cannot by itself be assumed to make v0.3 one-transaction feasible.

---

## SP-40 — Base-field and challenge-field bakeoff

### Purpose

Reopen the field decision now that the original BabyBear rationale—efficient 16-bit limbs for Keccak—no longer controls the application relation.

### Candidate set

At minimum benchmark:

| ID | Base field | Challenge field | Reason |
|---|---|---|---|
| F0 | BabyBear | degree 4 | current baseline, 4-byte base elements |
| F1 | KoalaBear | degree 4 | 31-bit alternative with strong Plonky3 support |
| F2 | KoalaBear | degree 5 where backend supports it | larger challenge space; current Spartan-WHIR reference point |
| F3 | Goldilocks | degree 2 | 16-byte extension with two coefficients instead of four |
| F4 | Mersenne31 / complex extension | backend-specific | Circle/WHIR and optimized 31-bit arithmetic path |
| F5 | one high-two-adicity large prime with no extension | base field challenge | test EVM `addmod`/`mulmod` against calldata cost |

A candidate can be removed after microbench gates, but the reason must be recorded.

### Stage A — arithmetic microbench

Implement identical operations in Rust and Solidity:

- base add/sub/mul/square/inverse/power;
- extension add/sub/mul/square/inverse;
- extension × base;
- 32/64/128/256-term dot products;
- batch inversion for 16/32/64 values;
- polynomial evaluation;
- and FRI/WHIR fold kernels.

### Stage B — encoding and calldata

Report:

- bytes per base element;
- bytes per extension element;
- canonicality-check gas;
- zero/nonzero distribution;
- ABI/raw encoding;
- and 64/96 floor cost per opened row.

### Stage C — proving primitives

Measure:

- FFT/NTT throughput;
- LDE throughput;
- Poseidon2 or selected application-permutation throughput;
- PCS commit/open/verify;
- parallel scaling;
- and peak memory.

### Stage D — relation prototype

Port the top AIR geometry to the best two field stacks. Generate a complete hiding proof and EVM-verify enough of it to produce a reliable total-cost projection; finalists require full verification.

### Security requirements

For every field stack report:

- base modulus bits;
- extension degree and irreducible polynomial;
- challenge-space bits;
- conservative entropy budget;
- two-adicity/domain limits;
- Poseidon2 parameter availability;
- field-specific attacks;
- and exact proof-system compatibility.

### Gate

A field stack proceeds if it is nondominated across:

- complete proof bytes;
- EVM execution gas;
- prover time;
- soundness ceiling;
- and implementation maturity.

Do not choose the fastest native prover if extension arithmetic makes the EVM verifier worse. Do not choose the smallest calldata if the challenge field cannot support the target.

---

## SP-50 — Hiding FRI parameter Pareto sweep

### Purpose

Determine whether an optimized relation can retain hiding FRI while restoring security and fitting one transaction, and identify the true Pareto frontier rather than selecting q32 ad hoc.

### Inputs

Use:

- the top one or two SP-10 application primitives;
- the top one or two SP-20 AIR geometries;
- the winning SP-30 transcript candidate;
- and the top field stacks from SP-40.

### Required parameter dimensions

Sweep at least:

```text
query count:             24, 32, 40, 48, 56, 64
log blowup:              3, 4, 5, 6
maximum folding arity:   supported values producing 2-, 4-, 8-, and 16-way folds
final polynomial length: 1, 4, 16, 64, and backend-recommended values
commit grinding:         0, 8, 16, 24, 32 configured classical bits
query grinding:          0, 8, 16, 24, 32 configured classical bits
random codewords:        every reviewed hiding-compatible value around 2–8
MMCS salts:              every reviewed hiding-compatible value around 4–12 fields
Merkle cap height:       0 and candidate cap heights
```

Do not run the full Cartesian product blindly. Build an analytical filter that removes:

- unbuildable degree/blowup combinations;
- profiles below the challenge-field ceiling;
- profiles that fail the selected security model;
- profiles whose estimated proof floor already exceeds transaction limits;
- and profiles dominated by another configuration.

Then fully benchmark the surviving frontier.

### Required security output

For every profile retain:

- all raw parameters;
- proven UDR/LDR;
- conjectural estimates with omitted terms listed;
- challenge-field cap;
- MMCS cap;
- multi-target result;
- quantum-adjusted grinding;
- and the binding term.

No profile passes solely because the random-words result exceeds 100.

### Required performance output

- complete proof bytes and byte ledger;
- native proving time/RSS;
- native verify time;
- EVM execution projection;
- complete EVM transaction for finalists;
- calldata under active/64/96 schedules;
- runtime code size;
- and deployment gas.

### Grinding analysis

For each nonzero grinding value measure:

- median and tail iterations;
- actual wall time on H1/H2/H3;
- parallelization behavior;
- whether commit-round grinding is repeated at multiple sites;
- and the exact quantum credit assigned.

A proof profile that fits on-chain only by adding minutes of grinding does not provide acceptable UX.

### Gate

**One-tx FRI pass:** at least one complete hiding profile clears the accepted 100-bit security gate and all one-transaction gates.  
**Robust two-tx pass:** at least one 100-bit profile clears the robust two-transaction gates and materially improves total cost over v0.3.  
**Fail:** every security-qualified profile exceeds 14M in one call and 20M total in two calls. In that case hiding FRI remains a baseline, not the next-build backend.

---

## SP-51 — HVZK-WHIR as an alternative PCS/IOPP

### Purpose

Test whether the newly available honest-verifier zero-knowledge WHIR path can reduce query count, proof size, and EVM work enough to outperform hiding FRI for the optimized PQTC relation.

### Current external context to verify at spike start

As of this plan’s preparation, Plonky3’s HVZK-WHIR tracking issue reports all six implementation sub-issues complete. This is evidence of availability, not an audit or proof of production suitability. Pin the exact commit actually used and inspect the code path rather than relying on issue status.

### Required stages

#### Stage A — upstream reproduction

1. Pin a Plonky3 commit containing the complete HVZK-WHIR implementation.
2. Run all upstream tests, including simulator/hiding tests.
3. Identify the exact `ZK`/hiding API and randomness requirements.
4. Record known issues and unsupported configurations.
5. Produce a minimal hiding proof and verify it natively.

#### Stage B — optimized AIR integration

Use the best SP-20 AIR without changing its logical relation. Generate a complete PQTC withdrawal proof with HVZK-WHIR.

#### Stage C — canonical codec and transcript

Define a strict versioned codec and Keccak-based or otherwise PQ-oriented Fiat–Shamir transcript compatible with EVM verification. Do not assume the native serializer is suitable.

#### Stage D — EVM verifier

Implement enough Solidity verification to measure the real hot path, then complete the verifier for any candidate that meets the projection gate. Reuse audited patterns from current WHIR Solidity efforts only where protocol-compatible.

### Required parameter sweep

Sweep:

- field/challenge choices supported by HVZK-WHIR;
- code rates;
- folding schedules;
- OOD sample count;
- WHIR rounds;
- query counts per round;
- base-case size;
- proof-of-work;
- mask-oracle parameters;
- commitment hash/digest width;
- and any code-switching parameters.

### Required measurements

- proof bytes by section;
- number of commitment roots;
- number and size of queried rows/fibers;
- sumcheck rounds and field operations;
- code-switching cost;
- mask-oracle overhead;
- prover time/RSS;
- native verify time;
- Solidity execution gas by phase;
- exact ABI calldata;
- active/64/96 gas;
- runtime/initcode size;
- and deployment gas.

### Required hiding evidence

- cite exact theorem/construction;
- map every mask oracle to implementation code;
- verify fresh OS randomness;
- run repeated-proof and simulator tests;
- test malformed proof behavior;
- and explain Fiat–Shamir composition from HVZK to NIZK in the project transcript.

### Gate

Proceed to integrated finalist status only if:

- a complete PQTC proof is hiding;
- accepted security reaches at least 100 bits;
- exact ABI calldata is ≤80 KiB or clearly trends below FRI;
- projected complete EVM verification is ≤12M before final integration;
- no runtime module fundamentally exceeds current EIP-170 after modularization;
- and prover UX is measured.

**Preferred pass:** ≤64 KiB calldata and ≤8M complete transaction gas.  
**Stop:** native proof is larger than the best hiding-FRI proof by >20%, the ZK path is incomplete, or the EVM verifier projection is not competitive.

---

## SP-52 — STIR performance lower bound and hiding-readiness study

### Purpose

Determine whether STIR’s lower query complexity offers enough proof-size advantage to justify waiting for or implementing a hiding construction.

### Current boundary

The current Plonky3 `TwoAdicStirPcs` path identified during review reports `ZK = false`. Therefore, a present non-hiding STIR proof is `BENCHMARK_ONLY` and cannot be used as a mixer proof.

### Required work

1. Pin the current STIR implementation and confirm its ZK status in source.
2. Reproduce a comparable FRI/STIR benchmark on the optimized relation or a faithful polynomial-opening proxy.
3. Match security models as closely as possible.
4. Measure proof size, query count, prover time, native verify time, and EVM operation count.
5. Investigate:
   - whether a reviewed hiding STIR construction now exists;
   - whether HVZK code techniques can be applied;
   - whether STIR can be used as a non-hiding outer proof over an already-ZK inner proof without leaking more than the inner proof;
   - and what formal composition argument is required.

### Gate

Do not implement a full Solidity STIR verifier unless the non-hiding lower bound improves proof bytes by at least 1.5× or projected gas by at least 30% versus the best FRI candidate. Even then, it remains deferred until a reviewed hiding path or accepted outer-proof privacy argument exists.

---

## SP-53 — Circle-FRI and emerging PCS watch track

### Purpose

Avoid locking the next build to a backend that is superseded during research, while preventing moving-target churn.

### Required work

At program start and report freeze, record the status of:

- hiding Circle FRI/Circle PCS;
- Mersenne31-compatible ZK code constructions;
- new Plonky3 FRI/STIR/WHIR releases;
- and other transparent hash/code-based PCS implementations with EVM-oriented verification.

A non-hiding implementation may be benchmarked as a lower bound but cannot pass.

### Gate

Promote an emerging PCS into a full spike only if it has:

- public source;
- a precise security paper;
- a working native prover and verifier;
- a documented hiding construction;
- a compatible field/application relation;
- and a credible EVM verification path.

Otherwise include it in `DEFERRED_TECHNOLOGY.md` with the reason.

---

## SP-60 — Structured Spartan-WHIR route

### Purpose

Test a multilinear/R1CS architecture that has already demonstrated materially lower Solidity verification gas and calldata than v0.3 on another workload, while preserving the PQTC relation and zero-knowledge requirement.

### External reference baseline

The current `privacy-ethereum/sol-spartan-whir` repository reports, for one 100.0145-bit Johnson-bound KoalaBear/quintic target:

- 54,436 bytes of native-blob call calldata;
- approximately 5.65M complete transaction gas;
- approximately 4.77M verifier execution gas;
- approximately 274 seconds proving time;
- and a monolithic runtime above current EIP-170.

These are external reference numbers. The team must reproduce them on its own hardware and may not infer PQTC performance directly.

### Required stages

#### Stage A — external baseline reproduction

- Pin exact exporter and Solidity verifier commits.
- Regenerate fixtures.
- Reproduce security, calldata, gas, prover time, and code size.
- Record any discrepancy.

#### Stage B — structured PQTC relation

Use SP-21 to express the optimized application-compression relation as repeated structured constraints. Avoid a generic sparse-matrix closure that destroys repeated-block structure.

#### Stage C — privacy qualification

Establish whether the exact Spartan-WHIR stack is zero knowledge. Where it is not natively ZK, evaluate an HVZK-WHIR or VEIL-style transformation. The candidate cannot pass on succinctness alone.

#### Stage D — Solidity verifier

Build a modular verifier under current EIP-170. Measure cross-contract call overhead and deployment gas. Do not assume a proposed 64 KiB code-size EIP.

### Required measurements

- variables, constraints, nonzeros;
- repeated-block and glue sizes;
- sumcheck rounds;
- multilinear opening parameters;
- proof bytes;
- prover time/RSS;
- native verification;
- exact EVM gas and calldata;
- code size by module;
- deployment gas;
- hiding overhead;
- accepted security;
- and comparison against FRI/WHIR on the same semantic corpus.

### Gate

A Spartan-WHIR candidate advances if:

- complete statement and witness semantics are preserved;
- zero knowledge is established;
- accepted security is at least 100 bits;
- exact transaction gas is projected ≤10M and calldata ≤80 KiB;
- modules can be made deployable under current EIP-170;
- and proving time is either within the UX gate or has a credible optimization/precomputation path.

A proof that verifies cheaply but takes several minutes must be reported accurately; it may still be a finalist if no other candidate matches its EVM/security profile.

---

## SP-61 — Recursive transparent proof compression

### Purpose

Determine whether verifying a large inner hiding proof inside a smaller outer transparent proof can create a one-transaction EVM verifier without an elliptic-curve wrapper.

### Candidate inner proofs

Test in order:

1. current v0.3 q32 proof, only to establish recursion feasibility;
2. strongest security-qualified optimized hiding-FRI proof;
3. best HVZK-WHIR or structured proof if available.

### Required outer-proof properties

- transparent/hash/code-based;
- no KZG, IPA, pairing, or trusted setup;
- complete binding to inner verifier parameters and public statement;
- accepted security accounting for both layers;
- and a documented privacy composition argument.

### Privacy branches

Evaluate separately:

#### RZK — outer proof is also hiding

This is the conservative path.

#### RPUBLIC-INNER-ZK — outer proof is non-hiding but its only private witness is an already zero-knowledge inner proof

This may be safe because revealing information about an already-ZK proof need not reveal the original witness, but it requires an explicit formal argument. It cannot be accepted by intuition alone.

### Required work

- Build the recursive verifier circuit/trace.
- Count inner-proof objects and hash operations.
- Choose an internal recursion-friendly transcript/MMCS without weakening outer EVM binding.
- Generate one recursive proof.
- Measure additional recursion layers if proof size shrinks further.
- Implement or adapt the outer Solidity verifier.
- Verify statement and parameter binding across layers.

### Required measurements

- inner proof bytes;
- recursive-circuit rows/width/constraints;
- outer proof bytes;
- recursion proving time/RSS;
- outer native verify time;
- EVM gas/calldata/code size;
- total security composition;
- and privacy theorem status.

### Gate

A recursive candidate advances if:

- outer proof ≤80 KiB;
- complete EVM transaction ≤10M projected and ≤14M measured;
- no classical wrapper exists anywhere;
- composition security reaches the accepted target;
- and proving time is no more than 5× the best nonrecursive candidate or is justified by a separate proving service model.

**Stop:** recursion increases proof size, verifier gas, or prover time without crossing the one-transaction boundary.

---

## SP-62 — Flock, conventional hashes, and lightweight ZK compilation

### Purpose

Revisit the original Keccak-based application relation using a proof system specifically optimized for repeated Boolean hash computations, rather than proving Keccak through a 2,633-column prime-field AIR.

### Core hypothesis

Flock’s batch-R1CS architecture may make the original 44-Keccak-permutation Tornado relation practical to prove. Its present suitability depends on adding zero knowledge and finding an EVM-verifiable outer or native proof.

### Required stages

#### Stage A — exact small-batch reproduction

Pin the Flock paper/repository version and benchmark batch sizes:

```text
44, 88, 176, 352, 704, 1024
```

Do not quote large-batch throughput for a 44-permutation withdrawal without measuring the fixed overhead at 44.

#### Stage B — original Classic relation

Implement:

- two KeccakPair512 note branches;
- two nullifier branches;
- forty Merkle-node branches;
- private path-direction selection;
- fixed Ethereum Keccak padding;
- root/nullifier/payout statement binding;
- and complete glue constraints.

#### Stage C — zero knowledge

Establish the exact current Flock ZK status. If the base system is non-ZK, integrate or prototype a VEIL-style transformation or another reviewed hiding compiler. Measure the actual overhead; do not import paper percentages from a different field/instance as project results.

#### Stage D — EVM route

Evaluate:

1. direct Solidity verification over Flock’s binary field;
2. an outer HVZK-WHIR/transparent recursive proof;
3. a recursion tower supplied by the Flock implementation;
4. and any source-pinned EVM verifier work.

Binary-field carryless multiplication is fast on CPUs with suitable instructions but not natively cheap in the EVM. Measure rather than assume.

### Required measurements

- Boolean/R1CS constraints per Keccak;
- glue constraints;
- proof bytes before/after ZK;
- proving time/RSS at each batch size;
- native verify time;
- binary-field operation count;
- EVM gas projection and measured kernels;
- outer-proof overhead;
- code size;
- accepted security;
- and privacy status.

### Cross-user warning

Flock batching raw hash computations across unrelated users would require the batch prover to receive their note witnesses. That breaks mixer privacy unless a separate MPC/blinding/individual-proof aggregation layer exists. This spike concerns one user’s withdrawal or proof aggregation, not centralized raw-witness collection.

### Gate

Flock advances only if:

- the exact 44-permutation relation proves efficiently;
- a reviewed zero-knowledge path is implemented or concretely available;
- a credible one-transaction EVM route is demonstrated or projected below 10M;
- and total proof bytes fit the calldata gate.

Without ZK or EVM verification, record Flock as a promising inner prover and stop before protocol integration.

---

## SP-70 — Proof aggregation and batched withdrawals

### Purpose

Determine whether individual withdrawals that remain moderately expensive can be aggregated into one PQ-oriented settlement proof without giving an aggregator users’ raw note witnesses.

### Required privacy architecture

The default model must be:

```text
user i generates an individual zero-knowledge proof locally
        ↓
aggregator receives proofs + public statements, not note secrets
        ↓
aggregator proves/combines validity of N individual proofs
        ↓
one settlement transaction consumes N nullifiers and executes N payouts
```

A centralized prover that receives raw note witnesses is a separate trusted model and does not pass.

### Batch sizes

Benchmark:

```text
N = 1, 2, 4, 8, 16, 32, 64
```

Stop increasing when payout calldata or EVM call cost dominates.

### Required designs

Compare:

- recursive binary proof tree;
- flat batch verification inside one outer proof;
- proof folding where PQ-oriented and hiding;
- same-user multi-note aggregation;
- unrelated-user proof aggregation;
- fixed batch window;
- threshold-triggered batch;
- and permissionless multiple aggregators.

### Required safety/liveness analysis

- Aggregator cannot alter recipient, relayer, fee, root, or nullifier.
- One bad proof cannot invalidate other users without a recovery path.
- Users can leave an unfilled or censored batch.
- Duplicate nullifiers are rejected before payout.
- Payout failure policy is explicit: atomic whole batch, pull payments, or isolated claims.
- Aggregator cannot learn deposit linkage from proofs beyond public metadata.
- Batch identifiers and ordering are canonical.
- Front-running cannot redirect payments.

### Required measurements

For each N:

- aggregate proof bytes;
- proof-generation time/RSS;
- verifier gas;
- payout/nullifier gas;
- exact calldata;
- active/64/96 total gas;
- gas per withdrawal;
- latency under several arrival rates;
- failure recovery cost;
- and minimum economical N.

### Gate

Aggregation is product-relevant if:

- individual users never reveal raw witnesses to the aggregator;
- accepted security and ZK are preserved;
- total settlement transaction fits ≤14M;
- amortized gas is ≤1M per withdrawal at N≥16 or improves the best individual path by at least 70%;
- and there is a permissionless/censorship-resistant fallback.

Aggregation cannot replace the requirement for at least one functional individual-withdrawal path.

---

## SP-71 — L2 execution and data-fee economics

### Purpose

Determine whether the same application-level PQ proof becomes economically practical on EVM rollups even if Ethereum L1 remains expensive.

### Scope

Measure at least:

- Ethereum local/testnet baseline;
- one OP Stack testnet;
- one Arbitrum-family testnet;
- and one materially different EVM rollup where verifier opcodes are supported.

Pin exact network/fork versions at measurement time. Do not assume one chain’s gas number maps to another’s fee.

### Required measurements

- execution gas;
- L1 data fee or equivalent;
- compressed transaction bytes;
- sequencer fee;
- total native-token and USD-equivalent cost at timestamped price inputs;
- block/transaction gas limits;
- contract-size limits;
- calldata compression behavior;
- proof inclusion latency;
- finality/withdrawal assumptions;
- and any opcode/precompile differences.

### Security boundary

Report separately:

- application proof PQ properties;
- rollup proving/fraud system assumptions;
- sequencer censorship;
- bridge/canonical asset assumptions;
- and L1 settlement.

An L2 deployment may preserve the application-level anonymity proof while changing custody and liveness assumptions.

### Gate

Promote an L2 route if it reduces user cost by at least 90% and preserves the intended application-level proof semantics. It is a deployment strategy, not evidence that the L1 verifier is efficient.

---

## SP-72 — Robust two-transaction verifier state machine

### Purpose

Design a safe fallback that materially improves v0.3’s state and gas margins while keeping exactly two user/relayer transactions.

### Required fixes to study

1. **One active checkpoint per statement or nullifier.** Do not key unlimited live checkpoints solely by randomized Part A proof bytes.
2. **Consumer restriction.** Bind a registry to one immutable pool or an explicit immutable consumer set.
3. **Expiry.** Every checkpoint expires after a bounded block/time interval.
4. **Permissionless cleanup.** Anyone can delete expired state; economics are explicit.
5. **Replacement.** A user can replace an expired/failed Part A without permanently losing the note.
6. **Root pinning.** If root history is bounded, an active checkpoint pins its root until completion/expiry.
7. **Full-width bindings.** Use the accepted digest width for statement/global/checkpoint/proof continuation.
8. **Asymmetric split.** Select the split that maximizes minimum gas margin.
9. **No reusable fact.** B completes proof verification and value movement atomically.
10. **No proof-byte storage.** Store only fixed-size continuation state.

### Attack simulations

- many valid Part A proofs for one note with different hiding randomness;
- direct registry calls by arbitrary consumers;
- expired proof replay;
- replacement races;
- exact Part A front-run;
- mixed A/B proofs;
- root aging;
- B payment revert;
- reentrancy;
- and cleanup front-running.

### Required measurements

- storage slots per checkpoint;
- Part A SSTORE cost;
- Part B delete/refund behavior without relying on refunds for caps;
- cleanup gas;
- worst live-state growth under rational attack budgets;
- A/B gas across all split candidates;
- and user recovery latency.

### Gate

A robust two-call candidate passes only if:

- each call is ≤12M under active/64/96 scenarios;
- total ≤20M;
- no permanent abandoned state exists;
- one note cannot create unbounded concurrent checkpoints;
- B remains atomic;
- and all replay/mixing tests fail safely.

---

## SP-73 — Prover UX, portability, and operational privacy

### Purpose

Ensure the selected proof is usable outside the development machine and does not improve on-chain UX by creating an unacceptable off-chain experience.

### Required platforms

- Apple ARM64 with NEON;
- commodity x86-64 with AVX2 but not necessarily AVX-512;
- high-end x86-64 with AVX-512 where available;
- scalar/portable build;
- optional WASM/browser proof or witness generation.

### Required workflows

Measure:

- cold first proof;
- warm repeated proof;
- precomputation/setup;
- proof cancellation;
- progress reporting;
- memory pressure;
- disk usage;
- deterministic crash recovery;
- and proof serialization/upload.

### Privacy review

Document whether proving requires:

- sending witness data to a service;
- remote memory/compute;
- telemetry;
- RPC queries that reveal commitment interest;
- or a centralized path provider.

Any proving-service proposal must describe secure witness isolation, attestation assumptions, and a local fallback.

### Gate

A finalist must have complete H1/H2/H3 measurements and a practical CLI workflow. Browser/mobile proving is optional; unexplained multi-minute latency or >8 GiB memory on H2 is a blocker for a “good UX” claim.

---

## SP-80 — Integrated finalist prototypes

### Purpose

Build only the smallest complete end-to-end prototypes needed to validate the top architectural combinations before writing the next engineering specification.

### Required candidate bundles

At least the following combinations must be considered. Only bundles that pass their component gates need full implementation.

#### Bundle A — optimized Poseidon2 compression + vertical AIR + hiding FRI

```text
fixed-length application compression
    → narrow low-degree AIR
    → batched Keccak transcript
    → hiding FRI Pareto profile
    → direct Solidity verifier
```

#### Bundle B — optimized compression/AIR + HVZK-WHIR

```text
same application semantics
    → best AIR geometry
    → HVZK-WHIR
    → modular Solidity verifier
```

#### Bundle C — structured relation + Spartan-WHIR/HVZK

```text
fixed compression
    → repeated structured R1CS/CCS
    → Spartan/sumcheck
    → hiding WHIR/VEIL path
    → modular Solidity verifier
```

#### Bundle D — optimized inner proof + transparent recursion

```text
best hiding inner proof
    → recursive verification relation
    → small transparent outer proof
    → one-tx Solidity verifier
```

#### Bundle E — Keccak relation + Flock + ZK/outer compression

Longer-horizon alternative. Build fully only if SP-62 passes.

#### Bundle F — robust two-call fallback

Use the strongest security-qualified proof that cannot fit one call, with SP-72 state handling.

### Minimum complete prototype

Network validation for a finalist should use a verifier/payment harness with immaterial test value. Do not deploy a public custody pool or solicit third-party deposits as part of this research program without separate authorization.

A bundle is complete only when it includes:

- note generation;
- commitment/nullifier derivation;
- depth-20 tree/path;
- full witness construction;
- hiding proof generation;
- native verification;
- canonical proof codec;
- Solidity proof verification;
- pool statement reconstruction;
- nullifier consumption;
- recipient/relayer payout in a harness;
- exact ABI transaction measurement;
- and source-bound parameter manifest.

A partial verifier plus spreadsheet projection is insufficient for a finalist.

### Gate

At least one bundle must reach a complete prototype or the report must conclude that the current research frontier did not produce a viable next build. Do not force a winner.

---

# Part III — Cross-cutting investigations

## 13. Proof commitment and digest-width study

Application digests and proof-MMCS digests need not have the same width, but both require explicit security targets.

Benchmark:

- 512-bit KeccakPair;
- reviewed 384-bit two-branch truncation;
- reviewed 320-bit two-branch truncation;
- and 256-bit single Keccak as a nonqualifying lower bound.

For each report:

- authentication-path bytes;
- hash gas;
- generic quantum collision estimate;
- multi-target adjustment;
- construction proof/reduction status;
- and exact truncation rule.

Do not adopt 320/384-bit variants without independent analysis of the two-branch construction and all places the digest is used.

---

## 14. Public statement minimization

The proof must bind scope, root, nullifier, recipient, relayer, and fee. It need not hash public payout data inside the private relation if transcript/public-input binding already establishes the same semantics.

Compare:

1. v0.3 Poseidon payout digest in the AIR;
2. raw recipient/relayer/fee limbs as public values;
3. an EVM-computed KeccakPair payout digest supplied as public input;
4. direct transcript binding outside the application trace.

Measure public-value count, AIR rows/columns, transcript work, calldata, and statement clarity. The pool must independently reconstruct the exact public statement.

Gate: choose the simplest construction that removes private-trace work without weakening binding or creating field/byte ambiguity.

---

## 15. Parameter ID and runtime-code binding without circularity

The v0.3 manifest supports runtime hashes but generated profiles leave them empty. A parameter ID that commits to runtime code which embeds the same parameter ID can be self-referential.

Research and specify a two-layer identity:

```text
proofSystemId:
    application relation
    field/extension
    PCS/LDT
    transcript
    proof codec
    verifier interface
    stateless verifier module source/code identities where non-circular

deploymentManifestId:
    proofSystemId
    exact pool/registry/module runtime hashes
    constructor arguments
    addresses
    compiler/optimizer/EVM settings
```

The scope should bind the identity needed to prevent proof/relation substitution, while deployment tooling separately proves that the deployed bytecode matches the reviewed manifest.

Required deliverable: a dependency graph showing no hash cycle.

---

## 16. Worst-case frontier and proof-length analysis

Do not use p95 or the largest of 30 proofs as a worst-case theorem.

For each Merkle/MMCS multiproof format:

1. derive a combinatorial upper bound from tree height and query count;
2. account for duplicate query indices at every FRI/WHIR round;
3. construct query multisets maximizing and minimizing frontier size;
4. generate valid proof fixtures matching or approaching those bounds;
5. measure gas and calldata;
6. include zero/nonzero byte extremes where constructible.

The complete transaction gate uses the proven/conservative upper bound, not the median proof.

---

## 17. Hash and transcript cryptanalysis packet

Prepare one compact packet for external cryptographers containing:

- exact field and matrices;
- round constants and derivation scripts;
- mode definition;
- state layouts by domain;
- output/truncation;
- threat properties;
- expected number of hash invocations over protocol lifetime;
- quantum target;
- known attack papers;
- project calculations;
- and open questions.

Ask reviewers specifically to assess:

- algebraic preimage/collision attacks;
- subspace trails;
- round skipping;
- invariant/related-input behavior;
- compression versus sponge mode;
- feed-forward and truncation;
- domain/level injection;
- and multi-target security.

“Poseidon2 is widely used” is not a sufficient review conclusion.

---

## 18. Formal and semi-formal assurance

For finalists, investigate:

- machine-generated AIR/R1CS from a single source;
- symbolic constraint coverage;
- Lean/Coq/Isabelle proof of application relation or critical hash framing;
- SMT checks for finite controller transitions;
- proof-codec parser verification;
- and equivalence between Rust and Solidity arithmetic.

Full formal verification is not required to finish the research program, but the report must identify which parts are amenable and estimate the cost for the next build.

---

## 19. Economic and throughput model

For every finalist calculate:

- gas at 0.1, 0.5, 1, 5, 10, and 50 gwei;
- ETH cost;
- timestamped USD examples with price source clearly marked;
- block share under several block gas limits;
- maximum withdrawals per block;
- calldata bytes per block;
- prover throughput per machine;
- and relayer fee needed to break even.

Do not mix volatile price assumptions into the cryptographic gate. Present them as operational sensitivity.

---

# Part IV — Synthesis and final decision procedure

## 20. Candidate scorecards

Every candidate receives one scorecard. The scorecard must present raw metrics first and any weighted score second.

### 20.1 Mandatory scorecard fields

```text
Candidate identity
Protocol semantics
Application hash/compression
Digest width
Tree shape
Arithmetization
Field/challenge field
PCS/LDT
Hiding construction
Proof MMCS/transcript
Security profile
Proof bytes
ABI calldata
Prover performance by hardware
Native verifier performance
EVM gas by component
Complete transaction gas under three schedules
Runtime/initcode/deployment gas
State growth
Checkpoint behavior
Implementation maturity
External review status
Known blockers
Gate status
```

### 20.2 Pareto analysis

Plot candidates on at least these axes:

- accepted security bits vs one-transaction gas;
- accepted security bits vs proof bytes;
- proof bytes vs execution gas;
- prover time vs transaction gas;
- deposit gas vs withdrawal gas;
- runtime code size vs verifier gas;
- implementation complexity vs performance;
- and total gas vs amortized gas under aggregation.

A candidate dominated on all relevant axes should not be selected because it has a higher subjective score.

### 20.3 Secondary weighted score

After presenting Pareto frontiers, calculate a secondary score using disclosed weights. Suggested starting weights:

| Category | Weight |
|---|---:|
| Security confidence and completeness | 25% |
| One-transaction feasibility and margin | 20% |
| Total user gas/economic cost | 15% |
| Proof bytes/future-floor robustness | 10% |
| Prover UX | 10% |
| Audit and implementation complexity | 10% |
| Deposit efficiency | 5% |
| Upstream maturity/maintainability | 5% |

Provide sensitivity with at least three alternative weight sets. The weighted score cannot override a hard gate.

---

## 21. Required decision outcomes

The final report must choose one of the following outcomes, with evidence.

### Outcome A — one-transaction next build is justified

Requirements:

- at least one `NEXT_BUILD_FINALIST` passes the one-transaction gate;
- a security qualification path is complete or narrowly scoped;
- proof and verifier are fully implemented enough to validate gas;
- no unresolved architecture rewrite is required;
- and the recommended build can be described in a separate engineering plan.

### Outcome B — robust two-transaction next build is justified

Requirements:

- no one-transaction candidate passes;
- at least one candidate passes the robust two-transaction gate;
- total cost is materially below v0.3;
- state is bounded;
- and the report explains what prevents one-call verification.

### Outcome C — aggregation/L2 should become the product strategy

Requirements:

- individual L1 verification remains economically poor;
- an aggregation or L2 route has strong measured economics;
- an individual fallback remains possible;
- and the changed trust/latency model is fully documented.

### Outcome D — no new full build yet

Choose this honestly if:

- no candidate clears security and operation gates;
- exact hash/PCS review is unresolved;
- proof systems remain non-hiding;
- or all EVM paths require another fundamental research breakthrough.

The program succeeds by producing a correct negative conclusion. It does not require selecting a build.

---

## 22. Stop rules

Stop a candidate immediately when any of the following is established:

- it relies on a prohibited classical wrapper;
- it is non-hiding and no concrete hiding path exists;
- generic or structural security falls below the target;
- its proof floor alone exceeds the transaction cap;
- its verifier requires an unavailable precompile;
- its runtime cannot be modularized under current EIP-170 without changing semantics;
- its complete relation destroys the toy-benchmark advantage;
- its prover cannot run within available memory and has no practical service model;
- it is strictly dominated by another candidate;
- or the amount of new consensus-critical custom cryptography is disproportionate to the measured gain.

Record the stop point, supporting data, and whether a future upstream development could revive the candidate.

---

## 23. Required final research report

The engineers must return one standalone document:

```text
research/final/NEXT_GENERATION_RESEARCH_REPORT.md
```

It must be understandable without reading commit history or private discussions.

### 23.1 Required table of contents

1. Executive conclusion
2. Scope and evidence boundary
3. Reproducibility manifest
4. v0.1–v0.3 baseline chronology
5. Baseline reproduction results
6. Security model and corrected v0.3 interpretation
7. Common benchmark corpus
8. Application hash/compression experiments
9. Merkle/deposit experiments
10. AIR geometry experiments
11. Transcript/verifier experiments
12. Field/extension experiments
13. Hiding FRI Pareto results
14. HVZK-WHIR results
15. STIR/Circle readiness results
16. Spartan-WHIR results
17. Recursive proof results
18. Flock/VEIL results
19. Aggregation results
20. Robust two-call state-machine results
21. L2/economic results
22. Prover UX results
23. Security and cryptanalysis review
24. Advisory applicability matrix
25. Candidate Pareto frontiers
26. One-transaction feasibility conclusion
27. Two-transaction fallback conclusion
28. Recommended next-build architecture, if any
29. Rejected/deferred candidates
30. Unresolved decisions
31. Raw evidence index
32. Reproduction instructions

### 23.2 Executive conclusion requirements

The first two pages must state:

- whether one-transaction verification appears feasible;
- best candidate and exact measured envelope;
- security status and lowest binding term;
- deposit cost;
- proof bytes;
- prover latency/RSS;
- current/future gas-floor results;
- code/deployment status;
- whether a full new engineering plan is warranted;
- and the three largest unresolved risks.

### 23.3 Per-spike result card

Every spike section begins with:

| Field | Content |
|---|---|
| Spike ID | |
| Hypothesis | |
| Candidate IDs | |
| Source commits | |
| Completed scope | |
| Omitted scope | |
| Gate result | PASS / CONDITIONAL / FAIL / DEFERRED |
| Primary evidence | |
| Security status | |
| Operational status | |
| Recommendation | |

Then include:

- methodology;
- exact implementation;
- raw results;
- confidence intervals/distributions;
- comparison with baseline;
- confounders;
- failures;
- interpretation;
- and links/paths to raw artifacts.

### 23.4 Required summary tables

#### Candidate master table

| Candidate | Hash | AIR/R1CS | PCS | ZK | Accepted security | Proof B | Tx gas current | Tx gas 64 | Tx gas 96 | Deposit gas | Prove p50 | RSS | Runtime max | Gate |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

#### Security table

| Candidate | Primitive generic | Structural review | Proven proof bound | Conjectural proof estimate | Batch term included | QROM | ZK theorem | Multi-target result | Lowest term |
|---|---:|---|---:|---:|---|---|---|---:|---|

#### Gas decomposition table

| Candidate | Parse/transcript | AIR/R1CS | Openings | LDT/PCS | MMCS | State/payout | Calldata | Floor binding? | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|

#### Proof byte ledger

| Candidate | Header | Statement | Global | Queries | Paths/frontiers | Salts/masks | LDT | Final | ABI overhead | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|

#### Prover table

| Candidate | Hardware | Threads | Cold/warm | p50 | p95 | p99 | CPU s | RSS | Proof B |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|

### 23.5 Required negative-results section

List every stopped candidate with:

- reason;
- last completed stage;
- measurements;
- whether failure was security, privacy, gas, calldata, code size, prover UX, complexity, or maturity;
- and what future change could make it worth revisiting.

### 23.6 Required recommendation language

Use one of:

- `RECOMMEND_FULL_ENGINEERING_PLAN`
- `RECOMMEND_ADDITIONAL_TARGETED_RESEARCH`
- `RECOMMEND_ROBUST_TWO_TX_BUILD`
- `RECOMMEND_AGGREGATION_OR_L2_STRATEGY`
- `RECOMMEND_STOPPING_CURRENT_LINEAGE`

Do not write “looks promising” without selecting a status and listing the exact missing gate.

---

## 24. Machine-readable run record

Every benchmark run must satisfy the companion JSON schema. At minimum store:

```json
{
  "schema_version": "1",
  "run_id": "...",
  "candidate_id": "...",
  "spike_id": "...",
  "timestamp_utc": "...",
  "git": {
    "repository": "...",
    "commit": "...",
    "dirty": false,
    "submodules": {}
  },
  "toolchain": {},
  "hardware": {},
  "protocol": {},
  "application_hash": {},
  "relation": {},
  "proof_system": {},
  "security": {},
  "prover": {},
  "proof_bytes": {},
  "evm": {},
  "artifacts": [],
  "notes": []
}
```

No summary CSV may contain data that cannot be traced back to a run record and artifact hash.

---

## 25. Reproduction package

The final evidence package must support:

```sh
# Verify source/artifact hashes
./research/harness/benchctl verify-manifest research/final/evidence-manifest.json

# Rebuild selected candidate
./research/harness/benchctl build --candidate <id>

# Generate semantic/derived corpus
./research/harness/benchctl corpus --candidate <id>

# Generate N fresh hiding proofs
./research/harness/benchctl prove --candidate <id> --cases <set> --runs 30

# Verify natively
./research/harness/benchctl verify-native --candidate <id> --all

# Run complete EVM transactions
./research/harness/benchctl verify-evm --candidate <id> --client anvil

# Recompute security
./research/harness/benchctl security --candidate <id>

# Recompute gas scenarios and report tables
./research/harness/benchctl report --candidate <id>
```

Commands may differ, but equivalent one-command workflows are required.

---

## 26. Agent work packages

Assign work by expertise and preserve independent review.

| Package | Scope | Depends on | Primary output |
|---|---|---|---|
| R-A | baseline freeze/reproduction | none | SP-00 evidence |
| R-B | security calculator | none | SP-01 model |
| R-C | advisory matrix | R-A | SP-02 |
| R-D | application compression | R-A, R-B | SP-10 candidates |
| R-E | Merkle/deposit | R-D | SP-11/12 |
| R-F | AIR geometry | R-D | SP-20/21 |
| R-G | transcript and continuation | R-A, R-B | SP-30 |
| R-H | verifier arithmetic/codec | R-A | SP-31 |
| R-I | field bakeoff | R-B | SP-40 |
| R-J | FRI sweep | R-F, R-G, R-I | SP-50 |
| R-K | HVZK-WHIR | R-F, R-G, R-I | SP-51 |
| R-L | STIR/Circle watch | R-F | SP-52/53 |
| R-M | Spartan-WHIR | R-D, R-I, R-B | SP-60 |
| R-N | recursion | top inner proof | SP-61 |
| R-O | Flock/VEIL | R-B | SP-62 |
| R-P | aggregation | R-N or finalist proof | SP-70 |
| R-Q | L2 economics | integrated candidates | SP-71 |
| R-R | robust A/B state | R-G, R-H | SP-72 |
| R-S | UX/portability | all native finalists | SP-73 |
| R-T | integrated prototypes | passed components | SP-80 |
| R-U | independent reproduction | finalists | SP-91 |
| R-V | final report | all | SP-92 |

### Agent completion contract

Every package must include:

- source code or a documented no-code analysis;
- tests;
- exact commits and toolchains;
- raw run records;
- artifact hashes;
- benchmark distributions;
- security assumptions;
- gate result;
- negative results;
- open questions;
- and an ADR.

No unresolved `TODO`, mocked verifier, skipped constraint, disabled hiding, or hand-entered result may appear in a passing package.

---

## 27. Review checkpoints

Conduct formal internal reviews at these points:

### Checkpoint 1 — baseline accepted

After SP-00 through SP-02. Freeze the measurement and security methodology before comparing candidates.

### Checkpoint 2 — relation finalists

After SP-10, SP-20, SP-30, and SP-40. Select no more than three relation/field/transcript combinations for complete proof-backend work.

### Checkpoint 3 — backend finalists

After SP-50 through SP-62. Select no more than three complete backend paths for integration.

### Checkpoint 4 — product architecture

After SP-70 through SP-73. Decide whether individual L1, robust two-call, aggregation, or L2 is the likely product path.

### Checkpoint 5 — report freeze

Independent reproduction must finish before the report is signed. Freeze all source commits and generated artifacts.

At each checkpoint, publish minutes and the candidate decisions. Do not let parallel branches silently merge because their authors prefer them.

---

## 28. Definition of done

This research program is complete when the repository contains:

1. A frozen and independently reproduced v0.3 baseline.
2. A corrected, independent security-accounting model.
3. An advisory-applicability matrix.
4. At least three fixed-length application-hash/compression candidates, including a width-32 unified candidate.
5. A measured direct-deposit path with deployment gas.
6. A vertical/narrow AIR Pareto sweep.
7. A batched transcript and full-width continuation-binding experiment.
8. A field/extension bakeoff.
9. A complete hiding-FRI parameter frontier.
10. A complete HVZK-WHIR investigation.
11. Documented STIR/Circle readiness.
12. A structured Spartan-WHIR investigation.
13. A recursive compression investigation.
14. A Flock/zero-knowledge investigation.
15. Aggregation and L2 economic models.
16. A robust two-call state-machine design.
17. Prover performance on representative hardware.
18. At least one complete integrated finalist prototype, or a justified conclusion that none passes.
19. Complete run-level JSON, proof ledgers, gas traces, source/artifact hashes, and reproduction commands.
20. `NEXT_GENERATION_RESEARCH_REPORT.md` selecting one of the required outcomes.

The program does **not** authorize a v0.4 deployment. Its completion authorizes only the drafting of a separate engineering specification based on the reviewed evidence.

---

# Appendix A — Minimum candidate matrix

The final report must contain rows for at least the following, even where the result is `NOT_RUN` with a justified gate failure.

| Candidate | Hash relation | AIR/R1CS | Backend | Required status |
|---|---|---|---|---|
| C00 | v0.3 P2BB512 | 256×190 horizontal | hiding FRI q32 | reproduced |
| C01 | v0.3 P2BB512 | 256×190 horizontal | hiding FRI q48 | security/gas comparator |
| C10 | width-24 compression | best vertical | hiding FRI | measured if hash passes |
| C11 | width-32/12-field compression | best vertical | hiding FRI | required |
| C12 | width-32/12-field compression | second AIR geometry | hiding FRI | required |
| C20 | top relation | best AIR | HVZK-WHIR | required investigation |
| C21 | top relation | structured R1CS/CCS | Spartan-WHIR + ZK | required investigation |
| C22 | top inner proof | recursive verifier | transparent outer | required investigation |
| C23 | original Keccak relation | Flock repeated R1CS | Flock + ZK/outer | required investigation |
| C30 | best individual proof | aggregate proof | batch N=16 | required if recursion exists |
| C40 | best non-one-tx proof | two-call verifier | bounded checkpoint | required fallback |

---

# Appendix B — Minimum data tables per candidate

## B.1 Relation geometry

```csv
candidate_id,table_id,logical_rows,padded_rows,base_degree_bits,hiding_degree_bits,trace_width,preprocessed_width,constraint_count,max_degree,quotient_chunks,batched_functions,rotations,active_rows,padding_rows
```

## B.2 Proof ledger

```csv
candidate_id,run_id,raw_proof_bytes,abi_calldata_bytes,header_bytes,statement_bytes,global_bytes,query_row_bytes,salt_bytes,frontier_bytes,ldt_bytes,final_bytes,continuation_bytes,abi_overhead_bytes,zero_bytes,nonzero_bytes
```

## B.3 EVM gas

```csv
candidate_id,run_id,operation,execution_gas,standard_intrinsic,eip7623_floor,eip7623_total,eip7976_floor,eip7976_total,eip8311_floor,eip8311_total,tx_cap_margin,runtime_bytes,initcode_bytes,deployment_gas
```

## B.4 Prover

```csv
candidate_id,run_id,hardware_id,threads,cold_or_warm,wall_ms,cpu_ms,peak_rss_bytes,proof_bytes,native_verify_ms,success
```

## B.5 Security

```csv
candidate_id,profile,term,model,formula_source,input_summary,classical_bits,quantum_bits,proven_or_conjectural,multi_target_count,binding,notes
```

---

# Appendix C — Research references and current status anchors

All rapidly changing references must be rechecked and pinned at spike start. The following are starting points, not substitutes for source review.

## Ethereum execution constraints

- EIP-170, contract code size: https://eips.ethereum.org/EIPS/eip-170
- EIP-3860, initcode limit/metering: https://eips.ethereum.org/EIPS/eip-3860
- EIP-7623, calldata floor: https://eips.ethereum.org/EIPS/eip-7623
- EIP-7825, per-transaction gas cap: https://eips.ethereum.org/EIPS/eip-7825
- EIP-7976, prospective 64/64 calldata floor: https://eips.ethereum.org/EIPS/eip-7976
- EIP-8311, draft 96/96 calldata floor: https://eips.ethereum.org/EIPS/eip-8311
- EIP-7954, proposed code-size increase; do not rely on it: https://eips.ethereum.org/EIPS/eip-7954

## Application hashes and cryptanalysis

- Poseidon2 paper, ePrint 2023/323: https://eprint.iacr.org/2023/323
- Poseidon/Neptune subspace-trail cryptanalysis, ToSC 2025: https://doi.org/10.46586/tosc.v2025.i2.34-86
- Poseidon initiative and attack survey: https://www.poseidon-initiative.info/
- “Skipping Class” Poseidon2/Poseidon2b attack work, ePrint 2026/306: https://eprint.iacr.org/2026/306

## Plonky3 and proof backends

- Plonky3: https://github.com/Plonky3/Plonky3
- Plonky3 security advisories: https://github.com/Plonky3/Plonky3/security/advisories
- HVZK-WHIR tracking issue: https://github.com/Plonky3/Plonky3/issues/1590
- Plonky3 recursion: https://github.com/Plonky3/Plonky3-recursion
- STIR paper: https://doi.org/10.1007/978-3-031-68403-6_12
- STIR reference implementation: https://github.com/WizardOfMenlo/stir

## Multilinear/Boolean alternatives

- Solidity Spartan-WHIR verifier: https://github.com/privacy-ethereum/sol-spartan-whir
- Solidity WHIR verifier: https://github.com/privacy-ethereum/sol-whir
- Flock paper: https://arxiv.org/abs/2607.27491
- Flock implementation: https://github.com/succinctlabs/flock
- VEIL paper, ePrint 2026/683: https://eprint.iacr.org/2026/683
- VEIL formalization experiment: https://github.com/succinctlabs/veil-formal-verification

---

# Appendix D — Research handoff checklist

Before returning the package for review, verify:

- [ ] `ENGINEERING_REPORT.md` baseline facts are reproduced or discrepancies explained.
- [ ] Every candidate has a unique ID and immutable manifest.
- [ ] Every passing proof is genuinely hiding.
- [ ] Every security number states proven/conjectural status.
- [ ] Batched-function terms are not silently omitted.
- [ ] All three calldata-floor schedules are reported.
- [ ] Complete top-level transaction gas, not only internal call gas, is reported.
- [ ] Deployment gas and code size are reported.
- [ ] Worst-case proof/frontier bounds are present.
- [ ] Prover p50/p95/RSS is measured on representative hardware.
- [ ] Every stopped candidate is retained.
- [ ] All source and artifact hashes are in the evidence manifest.
- [ ] Independent reproduction has been performed for finalists.
- [ ] No candidate relies on a classical proof wrapper.
- [ ] No candidate relies on a non-hiding proof.
- [ ] No one-transaction claim uses less than the accepted security target.
- [ ] The final report selects one required outcome.
- [ ] No deployment or full new build is implied without a subsequent engineering specification.

