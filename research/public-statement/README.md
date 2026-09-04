# v0.3 public-statement minimization study

## Outcome

**Proceed only with the minimal packing variant as research; stop the aggressive variant.** The minimal variant retains all 64 ordered BabyBear values after decoding and changes only the registry ABI from `uint32[64]` to eight fixed `bytes32` words. It needs a new layout/version and is **not v0.3 compatible**. The aggressive 16-field statement-digest variant remains stopped until its AIR is implemented, its hash/leakage consequences are analyzed, and the complete construction is independently audited and passes the project security gate. This package provides no security or deployment qualification.

`python3 research/public-statement/check.py` is the executable gate. It accepts all 256 common semantic cases, rejects all 48 checked-in invalid mutations with their expected reasons, and rejects 33 valid cross-binding mutations over three layouts. SHA-512 is used only as a deterministic dependency oracle; it is not a proposed candidate hash or mapping.

## Frozen v0.3 map

`field-map.json` contains one row for every index 0 through 63. Each row records semantic source, AIR edge, transcript and codec handling, ABI representation, pool check, state/payout consequence, and a disposition in both variants.

| Public indices | Meaning | Semantic source | AIR binding | Pool/state consumer |
|---|---|---|---|---|
| 0–15 | scope digest | `chainId`, pool/consumer address, denomination, depth 20, protocol version 3, parameter ID | limbs 0–3 enter the first NOTE and NULLIFIER rows; limbs 4–15 enter their chained absorption. Each limb has two source-level gated equality emissions. | pool recomputes immutable `scope`; separates consumers, chains, pool parameters, note commitments, and nullifiers |
| 16–31 | Merkle root digest | note commitment from scope + nullifier secret + trapdoor; path bits/index; 20 sibling digests; level tags | final level-19 Merkle squeeze equals the 16 public limbs, one source-level gated equality per limb | digest canonicality and `knownRoots`; selects retained deposit state |
| 32–47 | nullifier hash digest | scope + nullifier secret | NULLIFIER squeeze equals the 16 public limbs, one source-level gated equality per limb | checked unspent, then inserted into `nullifiers` before payout calls; replay/one-spend identity |
| 48–63 | payout digest | recipient + relayer + 256-bit fee | four PAYOUT absorption rows equal the 16 public limbs, one source-level gated equality per limb | recipient/fee/relayer checks, then recipient receives `denomination-fee` and relayer receives `fee` |

No field is an AIR trace column. v0.3 has exactly 64 AIR public inputs, 190 trace columns, 1,186 constraints, and 80 source-level public-equality emissions (32 scope, 16 root, 16 nullifier, 16 payout). Removing a public input therefore does not by itself prove any trace-column or total-constraint saving.

## End-to-end binding

1. `WithdrawalStatement::public_values` emits the four digests in the order scope, root, nullifier, payout and each digest as sixteen canonical big-endian `u32` limbs.
2. The withdrawal AIR consumes all four groups as described above. The checked-in AIR mutation test changes every public index and requires rejection.
3. Rust `Transcript512` initializes from parameter ID plus ordered canonical public values. The Solidity transcript initializes identically and observes the same 64 values again after the first two query input roots. Any packing must unpack before this sequence; reordering is not equivalent.
4. Each proof part common header contains a count of 64 and 256 public-value bytes, checks canonicality, and compares them to the expected statement. `statementKey` commits the statement domain, parameter ID, and ABI-expanded ordered values. Part B must match the Part A key.
5. `PQTCClassicPool` reconstructs all values. It checks root membership, nullifier availability, recipient, fee, and conditional relayer validity before verification. Completion checks the same statement, consumes the nullifier, and performs the bound transfers.

The consumer is the pool address inside scope. Chain, consumer, denomination, tree depth, protocol version, and parameter ID are consequently note/nullifier domain inputs, not optional metadata. Root protects state membership. Nullifier protects replay. Payout protects all three transfer controls. None may be silently removed.

## Alternatives and dispositions

| Operation | Scope 0–15 | Root 16–31 | Nullifier 32–47 | Payout 48–63 | Decision |
|---|---|---|---|---|---|
| remove | loses note/nullifier consumer domain | loses proven state root | loses one-spend identity | loses transfer authorization | reject all |
| derive at pool boundary | pool can recompute, but verifier/AIR must still receive identical values | supplied root must still pass `knownRoots` | supplied nullifier must still pass spent-state checks | pool already recomputes from request | no statement reduction; potentially an ABI wrapper only |
| pack eight `u32be` per `bytes32` | retain and unpack | retain and unpack | retain and unpack | retain and unpack | **minimal research variant** |
| reorder | no byte saving; changes AIR/transcript/codec meaning | same | same | same | reject without a new domain/version and complete migration |
| commit all four digests to one 512-bit algebraic digest | constrain preimage | constrain preimage | constrain preimage | constrain preimage | **aggressive; stopped** |

### Minimal safe research variant

Use `bytes32[8]`, with field `8w+j` in bits `255-32j .. 224-32j`, then range-check each decoded lane `< 2,013,265,921` and feed the original 64-value order to AIR, transcript, codec logic, and statement key. Exact ABI payload falls from 2,048 bytes (`uint32[64]`, one ABI word per element) to 256 bytes per registry call, a 1,792-byte reduction. The proof headers and AIR are unchanged. Calldata gas is content-dependent and is not measured here. A new selector, codec/layout version, statement domain, and parameter manifest are mandatory; compatibility with v0.3 is false.

### Aggressive variant

Expose only a 16-field, 512-bit algebraic statement digest and constrain all 64 original fields as its ordered, versioned preimage while retaining their existing relation edges. Public-value bytes in each proof header would fall from 256 to 64 (exact 192-byte reduction). A `bytes32[2]` ABI argument would occupy 64 rather than 2,048 bytes (exact 1,984-byte reduction); together with one proof header, that is 2,176 bytes per registry call. These are byte-count consequences, not gas measurements.

The current rate-4 `hashFields64` schedule performs 16 absorption permutations and three additional squeezes. Adding that structure naively to the AIR is **PROJECTED** at 19 active permutations; 240 existing active rows plus 19 exceed the 256-row trace. Constraint delta, trace shape, prover/verifier cost, leakage, collision/preimage assumptions, and gas are unresolved. The variant must not proceed without an implemented constrained preimage, domain-separated transcript/codec, full mutation suite, leakage review, independent audit, and security-gate approval.

## Reproducibility

Run:

```sh
python3 research/public-statement/check.py
```

Use `--write` only to regenerate `results.json` and `field-map.json`. `source-hashes.json` pins the exact frozen sources and corpus consumed by this study. `results.json` labels computed measurements, exact source facts, and projections separately.
