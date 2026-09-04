# Cross-cutting section 13: proof commitment and digest width

## Verdict

**NO_ADOPTION.** This packet does not change frozen v0.3 and does not security-qualify any candidate. KeccakPair-512 is the comparison baseline, not a newly approved construction. The 384- and 320-bit variants are **`STOP_PENDING_EXTERNAL_ANALYSIS`** and are not described as reviewed. Single-Keccak-256 is a nonqualifying lower bound.

The reason is separable from performance: no retained evidence gives the two-branch variants a complete construction reduction, all-uses/QROM analysis, and independent external review. In addition, 256 bits has only a nominal single-target generic BHT exponent of `256/3` (floor 85), below the project's 100-bit quantum-adjusted binding target.

## Exact byte constructions

Let `K(x) = keccak256(x)`, `t` be exactly one unsigned byte, and `m` be exact canonical payload bytes. Each Keccak branch hashes:

```text
branch_u8 || tag_u8 || payload
```

There is no implicit ABI offset, ABI length, delimiter, or padding in the hashed bytes. Branch values are `0x00` and `0x01`.

| Variant | Serialized digest, in byte order | Exact truncation |
|---|---|---|
| KeccakPair-512 | `K(00 || t || m) || K(01 || t || m)` | None; 32 bytes from each branch |
| two-branch 384 | `K(00 || t || m)[0:24] || K(01 || t || m)[0:24]` | Retain the leftmost/MSB 24 bytes of each result; discard each 8-byte suffix |
| two-branch 320 | `K(00 || t || m)[0:20] || K(01 || t || m)[0:20]` | Retain the leftmost/MSB 20 bytes of each result; discard each 12-byte suffix |
| single-Keccak-256 lower bound | `K(00 || t || m)` | None; branch one is not evaluated |

Slices are zero-based half-open byte ranges. Truncation happens independently before concatenation; no cross-branch bit packing is permitted. Solidity tests assert these rules against direct `keccak256(abi.encodePacked(...))` and assert zeroed discarded suffixes in fixed storage words.

## Exact width matrix

The authentication path is a depth-20 binary sibling path: 20 digests, excluding leaf, root, index, direction bits, framing, and ABI padding. If its direction bitmap is separately minimally byte-aligned, it adds exactly 3 bytes. The binary-node microbenchmark hashes `left_digest || right_digest` with proof-node tag `0x41`.

| Variant | Digest bytes | Depth-20 siblings | With 3-byte directions | Node payload | Framed bytes/branch | Keccak calls/node | Optimal fixed slots | Unused allocated bytes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 512 | 64 | 1,280 | 1,283 | 128 | 130 | 2 | 2 | 0 |
| 384 | 48 | 960 | 963 | 96 | 98 | 2 | 2 | 16 |
| 320 | 40 | 800 | 803 | 80 | 82 | 2 | 2 | 24 |
| 256 lower bound | 32 | 640 | 643 | 64 | 66 | 1 | 1 | 0 |

These are **exact width-component counts, not full-protocol measurements**. In particular, 384 and 320 save path/calldata bytes but do not save fixed EVM storage slots relative to 512.

The exact Prague opcode schedule component for those framed node inputs is:

| Variant | Framed 32-byte words/branch | `KECCAK256` gas/branch | `KECCAK256` gas/digest | Cold zero→nonzero `SSTORE` gas/digest |
|---|---:|---:|---:|---:|
| 512 | 5 | 60 | 120 | 44,200 |
| 384 | 4 | 54 | 108 | 44,200 |
| 320 | 3 | 48 | 96 | 44,200 |
| 256 lower bound | 3 | 48 | 48 | 22,100 |

These are **exact EVM opcode-component microbenchmarks, not Solidity-call or full-protocol gas**: `KECCAK256` is `30 + 6 * ceil(input_bytes/32)`, and a cold zero-to-nonzero `SSTORE` is 22,100 gas per slot. Memory expansion, copying, truncation masks, ABI handling, calls, transaction intrinsic gas, calldata gas, and surrounding protocol work are excluded. The canonical Solidity harness captures those local implementation overheads separately.

## Generic quantum calculations

For nominal digest width `n` and `M = 2^m` security-relevant digest outputs over the protocol lifetime, the configurable calculator reports:

```text
multi-instance BHT collision projection:  2^((n - m) / 3) queries
multi-target Grover preimage projection:   2^((n - m) / 2) queries
accidental collision union bound:          M(M - 1) / 2^(n + 1)
```

Negative exponents are clamped to zero. `M` counts digest outputs; the output separately reports `M * branch_count` underlying Keccak invocations. These are generic random-oracle **PROJECTIONS**, with constants and implementation resources omitted. They are neither reductions nor accepted security levels. The two-branch shared-message construction especially needs independent analysis before nominal combined width can be relied upon.

| Width | Single-target BHT | Single-target Grover | BHT at `M=2^16` | BHT at `M=2^24` | BHT at `M=2^64` |
|---:|---:|---:|---:|---:|---:|
| 512 | `512/3` (floor 170) | 256 | `496/3` (165) | `488/3` (162) | `448/3` (149) |
| 384 | 128 | 192 | `368/3` (122) | 120 | `320/3` (106) |
| 320 | `320/3` (106) | 160 | `304/3` (101) | `296/3` (98) | `256/3` (85) |
| 256 | `256/3` (85) | 128 | 80 | `232/3` (77) | 64 |

The complete retained sweep covers `m = 0,16,24,32,40,48,56,64`. The 320-bit nominal BHT projection falls below 100 bits once `m > 20`, but it remains stopped even below that volume because generic arithmetic is not construction acceptance. The 384-bit projection's larger margin likewise does not clear its reduction/review gate.

## Construction, reduction, and review matrix

| Variant | Construction | Reduction | Independent review | Decision |
|---|---|---|---|---|
| KeccakPair-512 | Implemented frozen v0.3 baseline | Open: no complete two-branch composition/QROM reduction | Open; not security-accepted here | `NO_ADOPTION_BASELINE_ONLY` |
| two-branch 384 | Exact research prototype specified | Open: no two-branch truncation reduction | **Not reviewed** | `STOP_PENDING_EXTERNAL_ANALYSIS` |
| two-branch 320 | Exact research prototype specified | Open: no two-branch truncation reduction | **Not reviewed** | `STOP_PENDING_EXTERNAL_ANALYSIS` |
| single-Keccak-256 | Research negative control | Generic BHT failure already dispositive | Not submitted | `REJECT_NONQUALIFYING_LOWER_BOUND` |

External analysis must cover exact framing/truncation, combined collision and second-preimage behavior, correlated and multi-target uses, application/MMCS/transcript/identifier contexts, and QROM composition. Nothing in this packet substitutes for that work.

## Solidity gas/storage harness

`solidity/src/DigestWidthHarness.sol` implements all four exact constructions plus fixed-word storage. `solidity/test/DigestWidthGas.t.sol` contains parity/truncation tests and one canonical node microbenchmark per width. `solidity/foundry.toml` pins:

- solc 0.8.30;
- Prague EVM;
- optimizer enabled, 200 runs;
- via-IR enabled.

The gas delta is `gasleft()` immediately before minus `gasleft()` immediately after one low-level EVM call. Each row retains hash-only, storage-only, and hash-plus-storage results. Storage-only and combined cases use fresh contracts and untouched zero slots, so the transition is cold zero-to-nonzero. Deployment, transaction intrinsic gas, L1 calldata gas, and surrounding protocol work are excluded.

Every such number is labeled **`SOLIDITY_MICROBENCHMARK_NOT_FULL_PROTOCOL`**. `results.json` separately records full-protocol gas as `NOT_EVALUATED_NO_FULL_PROTOCOL_VARIANT_IMPLEMENTATION`; microbenchmarks are never summed or presented as complete transaction projections.

Canonical gas generation command, to be run from the repository root:

```sh
forge test --root research/digest-width/solidity --match-contract DigestWidthGasTest --match-test testCanonicalProfileMicrobenchmark -vv
python3 research/digest-width/run.py --write
```

The test retains `outputs/foundry-gas.json`; `run.py` rejects a mismatched schema/profile/variant set before incorporating it. `foundry-result-schema.json` defines that output. Until the canonical test is executed, gas cells remain explicitly `NOT_MEASURED_RUN_CANONICAL_FOUNDRY_HARNESS`, never projected or fabricated.

## Deterministic runner and retained outputs

```sh
# Check the default retained result byte-for-byte.
python3 research/digest-width/run.py

# Regenerate after the canonical gas harness.
python3 research/digest-width/run.py --write

# Explore another lifetime volume without overwriting the default result.
python3 research/digest-width/run.py --target-log2 20 --target-log2 48
```

The runner uses only the Python standard library, exact integer/rational arithmetic, sorted JSON keys, and deterministic inputs. It validates matrix cardinality, depth-20 path arithmetic, the mandatory 320/384 stop verdicts, and the 256-bit generic failure. It prints the SHA-256 of the computed JSON. `result-schema.json` defines `results.json`; `foundry-result-schema.json` defines the conditional retained gas artifact.

## Evidence boundary

This package is section 13 only. It does not modify production contracts, choose an application hash, change proof MMCS/transcript formats, implement a full verifier/pool variant, forecast production volume, claim live-chain evidence, or close external cryptographic review. `source-hashes.json` pins the plan, frozen KeccakPair source, and predecessor V7 width evidence used as inputs.
