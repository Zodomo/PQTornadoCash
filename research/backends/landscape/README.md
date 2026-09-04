# Backend Landscape Source Research

Research cutoff: **2026-09-04**.

This directory records source research for backend spikes. It is **not measured evidence**, a security qualification, or candidate acceptance. The source researcher ran **no build, test, benchmark, formatter, or reproduction command**. Every command below is an entrypoint identified from pinned upstream source; every quoted time, size, or gas value is an upstream claim rather than a PQTC result.

Machine-readable dispositions are in [`matrix.json`](matrix.json). Exact pins, quotations, source URLs, paths, line ranges, license gates, negative results, and breaking changes are in [`sources.json`](sources.json). Bracketed source IDs below resolve to records in `sources.json`.

## Status semantics

- `PASS`: published construction plus public implementation can build the native PQTC relation without designing a new hiding protocol. It does not imply an EVM verifier or an on-chain pass.
- `BENCHMARK_ONLY`: only a clearly labeled non-hiding lower-bound measurement is allowed.
- `DEFERRED`: plausible theory exists, but a required implementation, composition, verifier, or theorem is missing.
- `STOP`: the named route cannot satisfy the spike as currently published.

## Dispositions

| Spike | Candidate | Status | Durable reason |
|---|---|---:|---|
| SP-51 | HVZK-WHIR | `PASS` | The composable HVZK construction and complete pinned Plonky3 hiding pipeline exist. Advance the native implementation attempt; an EVM verifier and exact-transcript QROM argument do not yet exist. [S1–S4] |
| SP-52 | STIR | `BENCHMARK_ONLY` | Pinned `TwoAdicStirPcs` is explicitly non-hiding (`ZK = false`); the separate implementation is an unreviewed academic prototype. [S6–S8] |
| SP-53 | Circle-FRI | `DEFERRED` | The paper gives a randomization route, but postpones the non-interactive treatment, and pinned `CirclePcs` is non-hiding. [S9–S11] |
| SP-60 native | full-ZK Spartan-WHIR | `PASS` | Full-ZK DirectSparse and Spark APIs exist natively. This is a native sub-spike only; exact PQTC R1CS shape, licensing, EVM, and QROM obligations remain. [S12–S14, S33] |
| SP-60 EVM | `sol-spartan-whir` | `DEFERRED` | The checked-in proof is standalone plain WHIR wrapped in placeholder Spartan fields. Its numbers are **not Spartan and not PQTC**. [S15–S17] |
| SP-61 | Plonky3 recursion | `DEFERRED` | The inspected tree uses Plonky3 0.7.0, the Keccak example remains non-ZK, and in-circuit WHIR mirrors ordinary rather than hiding WHIR. [S18–S21] |
| SP-62 | Flock batch-44 | `STOP` | Flock is non-ZK, has no EVM verifier, and **current Flock removed Keccak** at `0f0d63268e1373c585251e95152b3a6943e2d818`. [S22–S24] |
| SP-62 research | VEIL over Flock | `DEFERRED` | VEIL is experimental HVZK research over a concrete KoalaBear/stacked-Basefold adapter, not Flock's binary-field stack, and has no EVM backend or concrete QROM theorem. [S28–S32] |

## Constraints that control implementation

### HVZK-WHIR

Pinned Plonky3 `3152b14a89067c83775a8076cc262ffc48a1fd7c` implements `HidingWhirPcs` as a multilinear PCS. It requires a two-adic base field, two-adic extension field, DFT, MMCS, challenger, and `CryptoRng`; it is not a drop-in univariate PCS. Predictable proving randomness defeats masking. The upstream security helper reports only diagnostic base-case RBR terms and does not certify the compiled PCS or preceding reductions. [S2–S5]

No hiding-WHIR Solidity verifier matching this proof shape was located. Porting must include the complete masked transcript and proof shape rather than reuse the archived/plain-WHIR codec. An independent composed soundness and binding budget is required before claiming a concrete security level. [S2–S4, S15–S17]

### STIR and Circle-FRI

`TwoAdicStirPcs` requires two-adic field structure and sets `ZK = false`. `CirclePcs` requires a `ComplexExtendable` value field and also sets `ZK = false`. Neither inspected implementation supports a private PQTC proof. STIR is admissible only as a non-hiding lower-bound benchmark; Circle-FRI remains deferred pending the hiding implementation, matching verifier, and transcript theorem. [S6–S11]

### Native full-ZK Spartan-WHIR

Pinned `ethereum/spartan-whir` `f525cddea38bb605304d3a8e6394dda10ac64b4a` exposes full-ZK DirectSparse and Spark over generic KoalaBear R1CS. Quartic, quintic, and octic extensions are available; the published target range is 80–123 bits due to the eight-element Poseidon digest budget. Default proving uses OS-seeded `StdRng`, while injected entropy must implement `Rng + CryptoRng`. There is no special repeated-block PQTC relation API, so the exact R1CS and public-input semantics must be built and audited. [S12–S14]

The repository lacks clear license metadata at the inspected pin. Obtain an explicit license grant before copying or redistributing it. Native `PASS` does not imply an EVM result. [S12–S14]

### `sol-spartan-whir` is standalone WHIR

The exporter intentionally does not depend on current `spartan-whir`. Its fixture has empty public inputs, a zero witness commitment, placeholder outer/inner sumchecks, and one real plain-WHIR PCS proof. Therefore its 100-bit quintic schedule and all headline figures are **standalone WHIR**, not full Spartan, not hiding, and not PQTC. [S15–S17]

The upstream README reports 54,436 calldata bytes, 5,646,080 transaction gas, 4,768,744 execution gas, 5,454,992 Foundry gas, and 274.163664792 seconds prover time. These values must remain labeled as upstream standalone-WHIR baselines. The inspected monolithic high-security verifier variants exceed EIP-170. [S17]

Like native `spartan-whir`, the Solidity repository has no detected GitHub license or complete LICENSE file at the inspected revision; a README trailing `MIT` is not an adequate redistribution grant. See license gate `L5` in `sources.json`.

### Recursion

Pinned recursion commit `34e3a2c3837834a7bf98a0b65063e0180e7fbb7b` depends on Plonky3 0.7.0, breaking direct dependency compatibility with the mandated Plonky3 0.6.0 pin. Its Keccak base and recursion layers remain non-ZK even when `--zk` is supplied. Its in-circuit WHIR verifier mirrors ordinary `WhirVerifier`, not `HidingWhirPcs`, and leaves adapter transcript work to the caller. Aggregation is currently 2-to-1 rather than arbitrary arity. Treat any numbers as architecture benchmarks, not privacy-qualified evidence. [S18–S21]

### Flock batch-44 and VEIL

Flock works over Boolean R1CS and a Ligerito PCS over $\mathbb{F}_{2^{128}}$, but the paper says the implementation provides succinctness and not zero knowledge. Current Flock ships BLAKE3 and SHA-256 end-to-end paths; commit `0f0d63268e1373c585251e95152b3a6943e2d818` removed Keccak and all of its only consumers. No official Solidity/Yul/EVM verifier was located. [S22–S24]

The historical Keccak parent is `c2d0c2485a54f7b7694e19f4f59730ffde3405cf`. For 44 inputs, its three-wide harness computes 15 blocks, rounds to 16 slots, and adds four valid all-zero Keccak permutations, proving capacity 48. It publishes no batch-44 result; the entrypoint below is only a historical non-hiding baseline. [S25–S27]

VEIL does not rescue this route. Its PoC is experimental and unaudited, and its concrete adapter is KoalaBear degree-4 plus stacked Basefold rather than Flock's binary-field Ligerito/transcript. A binary-field zk-PCS adapter, Flock verifier compiler, transcript binding, soundness analysis, and EVM backend are missing. [S28–S32]

## QROM obligations

None of the inspected implementation-specific transcripts has a located concrete QROM reduction. HVZK is an interactive honest-verifier property; Fiat–Shamir, malicious-verifier, recursion-composition, and post-quantum claims must be established for the exact transcript, hash, parameter set, and composition used by PQTC. A `ZK` flag, RBR error report, or phrase such as “post-quantum” or “plausibly post-quantum” is not a substitute. [S1, S3–S4, S6, S10, S13, S18–S20, S22, S28, S30]

## Reproduction entrypoints — identified, not executed

The source researcher ran none of these commands.

| Candidate | Pinned entrypoint | Permitted interpretation |
|---|---|---|
| HVZK-WHIR | `cargo test -p p3-whir` | Upstream package behavior, not EVM qualification |
| HVZK-WHIR | `cargo bench -p p3-whir --bench zk_overhead` | Upstream hiding-overhead harness |
| STIR | `cargo test -p p3-stir` | Non-hiding upstream behavior |
| STIR | `cargo bench -p p3-stir --bench stir_pcs` | `BENCHMARK_ONLY` lower bound |
| Circle-FRI | `cargo test -p p3-circle` | Non-hiding because `ZK = false`; candidate remains deferred |
| Native Spartan-WHIR | `cargo run --release --features parallel --example end_to_end -- setup build/example.r1cs build/proving-key.bin build/verifying-key.bin` | Native full-ZK setup using `PoseidonZk*` [S33] |
| Native Spartan-WHIR | `cargo run --release --features parallel --example end_to_end -- prove build/proving-key.bin build/example.wtns build/proof.bin build/public-inputs.bin` | Native full-ZK proof generation [S33] |
| Native Spartan-WHIR | `cargo run --release --features parallel --example end_to_end -- verify build/verifying-key.bin build/public-inputs.bin build/proof.bin` | Native verification [S33] |
| Standalone Solidity WHIR | `forge build && forge test` | Standalone WHIR only; never label Spartan/PQTC |
| Standalone Solidity WHIR | `bash .agents/skills/tx-gas-benchmarking/scripts/run_tx_gas_benchmark.sh script/WhirBlobNativeTxBenchmark_k22_jb100_ext5_lir4_ff4_rsv3_pow28.s.sol` | Standalone-WHIR gas baseline only |
| Recursion | `cargo run --profile optimized --example recursive_fibonacci -- --field baby-bear --hash poseidon1 --n 1000 --num-recursive-layers 5 --zk` | Limited hiding-FRI architecture demonstration [S18] |
| Recursion negative control | `cargo run --profile optimized --example recursive_keccak -- --zk` | Remains non-ZK; `--zk` has no effect [S19] |
| Historical Flock parent | `KECCAK3_KS=44 cargo bench --bench keccak3_proof` | Best-of-three, non-hiding capacity-48 baseline after checkout of `c2d0c2485a54f7b7694e19f4f59730ffde3405cf` [S25–S27] |
| VEIL | `cargo run --release -p slop-veil --example root` | Experimental PoC only [S31–S32] |
| VEIL | `cargo run --release -p slop-veil --example mle_eval` | Experimental PoC only [S31–S32] |
| VEIL | `cargo run --release -p slop-veil --example zerocheck` | Experimental PoC only [S31–S32] |

## Pin, license, and cutover gates

`sources.json` is authoritative for exact pins and gates. The implementation-significant cutovers are:

1. Recursion moved to Plonky3 0.7.0 while the required HVZK-WHIR pin is 0.6.0. [S5, S21]
2. Current Flock removed Keccak; batch-44 exists only at the historical parent. [S24–S27]
3. Stwo development moved to `starkware-libs/proving`; do not base current conclusions only on the older Stwo tree.
4. `spartan-whir-export` severed dependency on current `spartan-whir`; the checked Spartan fixtures are placeholders around plain WHIR. [S15–S16]
5. `privacy-ethereum/sol-whir` is archived and tied to an older plain-WHIR proof format.

Plonky3, Plonky3-recursion, Flock, and SP1/VEIL declare `MIT OR Apache-2.0`; the STIR reference carries MIT and Apache-2.0 files; current Starkware `proving` is Apache-2.0; archived `sol-whir` is MIT. The two `ethereum/*spartan-whir` repositories remain blocked for copying or redistribution until an explicit license grant is obtained. No CVE/GHSA fixed range is relied upon by this package.
