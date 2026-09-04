# SP-30 v0.3 transcript research specification

Status: research-only. Every construction in this document is `BENCHMARK_ONLY`; none is integrated into custody code. The production comparison point is repository v0.3 with Plonky3 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`.

## 1. Primitive and integers

`K512(tag, payload) = Keccak256(0x00 || tag || payload) || Keccak256(0x01 || tag || payload)`.

All integers and canonical BabyBear values are unsigned, fixed-width, big-endian. `u16`, `u32`, and `u64` occupy 2, 4, and 8 bytes. The BabyBear modulus is `p = 2013265921 = 0x78000001`; decoding rejects values `>= p`. A digest is always 64 bytes, left half followed by right half. An extension value is exactly four canonical base-field coefficients in basis order. A commitment is one 64-byte Merkle-cap root.

Tags shared with v0.3 are `INIT=0x42`, `ABSORB=0x43`, `SQUEEZE=0x44`. Research item tags are `FIELD=0x01`, `COMMITMENT=0x02`, `FIELD_ARRAY=0x03`, `ITEM_DIGEST=0x45`, and `BOUNDARY_FRAME=0x46`. Candidate version identifiers are the ASCII strings `PQTCT0-01`, `PQTCT1-01`, `PQTCT2-01`, and `PQTCT3-01`; research candidates include their identifier in initialization and therefore cannot collide with production or each other. T0 additionally emits a production-compatibility mode whose initialization is byte-for-byte v0.3.

## 2. Versioned grammars

Lengths count bytes unless a field is named `count`. No implicit padding, ABI encoding, platform-sized integer, concatenated variable-length list, or noncanonical value is allowed.

### T0 — field-by-field baseline

Production-compatible initialization:

`state := K512(INIT, parameter_digest[64] || public_values[64] each field32)`

Versioned research initialization:

`state := K512(INIT, version[9] || parameter_digest[64] || u32(public_count) || public_values)`

Each scalar field is a distinct item:

`state := K512(ABSORB, state[64] || FIELD || u32(4) || field32)`

Each commitment is a distinct item:

`state := K512(ABSORB, state[64] || COMMITMENT || u32(64) || digest64)`

T0 is the control: the compatibility mode exactly reproduces `Transcript512` initialization and absorbs.

### T1 — typed-array absorb

Initialization uses the versioned form above. Scalar fields retain the T0 scalar rule. A logical field or extension array is absorbed once:

`array_payload := u32(count) || count * field32`

`state := K512(ABSORB, state[64] || FIELD_ARRAY || u32(len(array_payload)) || array_payload)`

Empty arrays are encoded with count zero and byte length four. Commitments retain the T0 commitment rule. Arrays are formed only from a single protocol claim (`public_values`, one opening slice, `final_poly`, or `log_arities`); arrays from distinct claims are never merged.

### T2 — item digest plus state

Initialization uses the versioned form. Each logical item uses the same canonical item payload as T1: scalar `field32`, commitment `digest64`, or array `u32(count)||fields`. First hash the complete typed item, then hash it into the state:

`item_digest := K512(ITEM_DIGEST, version[9] || type8 || u32(payload_len) || payload)`

`state := K512(ABSORB, state[64] || item_digest[64])`

The item type and length appear inside the item digest. No caller-supplied digest is accepted by the typed API.

### T3 — challenge-boundary frame

Initialization uses the versioned form. Claims are encoded exactly as T1 items and appended to a pending frame:

`encoded_item := type8 || u32(payload_len) || payload`

Immediately before any squeeze, the nonempty pending frame is absorbed once:

`frame_payload := version[9] || u32(item_count) || u32(encoded_bytes_len) || encoded_items`

`state := K512(BOUNDARY_FRAME, state[64] || frame_payload)`

A squeeze with an empty frame is permitted and continues the existing squeeze stream. Absorbing after squeezing clears buffered output and resets the squeeze block counter, exactly as v0.3. A frame MUST be flushed before the first byte of every challenge or proof-of-work check. The primitive enforces flushing in every sample operation; the graph driver/strict decoder enforces that all claims required by that boundary arrived before the sample. Thus no frame crosses a challenge boundary and a challenge-before-claim sequence rejects.

## 3. Squeeze and rejection sampling

For all candidates, when the output queue is empty:

`block := K512(SQUEEZE, state[64] || u64(counter)); counter := counter + 1`

Bytes are consumed from the left of `block`. An absorb/frame flush clears the queue and resets `counter=0`.

A base-field challenge repeatedly consumes four bytes, computes `x = BE32(bytes) & 0x7fffffff`, accepts iff `x < p`, and otherwise consumes the next four bytes. No reduction modulo `p` is allowed. An extension challenge samples four base-field challenges in basis order. A `b`-bit challenge (`0 <= b <= 31`) consumes four bytes and returns `BE32(bytes) & (2^b-1)` (with zero for `b=0`). The v0.3 proof uses `b=16` for each commit PoW check, `b=8` for query PoW, and `b=13` for each query index.

A nonzero-bit PoW witness is first absorbed as a scalar field and then a bit challenge is sampled and required to equal zero. A zero-bit witness is neither absorbed nor squeezed, matching pinned Plonky3 `GrindingChallenger::check_witness`.

## 4. Exact v0.3 claim-to-challenge graph

The table is normative. `F` means one scalar field item, `C` one commitment item, and `A[n]` one logical array of `n` base fields (T0 expands it to `n` field items). `E[n]` contains `4n` base fields. The graph uses production shape: degree bits 9, base degree bits 8, no preprocessed trace, 190 trace columns, 16 quotient chunks, four hiding codewords, nine binary FRI rounds, and 32 queries.

| Boundary | Claims absorbed since prior boundary, in exact order | Challenge/output |
|---|---|---|
| init | full parameter digest (64 bytes), full statement public values (64 canonical fields) | state only |
| B0 | `degree_bits=9 F`; `base_degree_bits=8 F`; `preprocessed_width=0 F`; `trace_commit C`; `public_values A[64]` | `air_alpha E[1]` |
| B1 | `quotient_commit C`; `random_commit C` | `zeta E[1]` |
| B2 | `random_opening E[4] || hiding[batch0,matrix0,point0] E[4]` as one opening claim; `trace_local E[190] || hiding[batch1,matrix0,point0] E[4]`; `trace_next E[190] || hiding[batch1,matrix0,point1] E[4]`; for chunk `0..15`, `quotient_chunk E[4] || hiding[batch2,chunk,point0] E[4]` | `fri_alpha E[1]` |
| B3.r, r=0..8 | `fri_commit[r] C`; `commit_pow_witness[r] F` | `commit_pow_bits[r] bits16 == 0`; then `fri_beta[r] E[1]` from the same post-witness squeeze stream |
| B4 | `final_poly E[1]`; nine `log_arity=1 F`; `query_pow_witness F` | `query_pow_bits bits8 == 0`; then 32 `query_index bits13` from the same stream |

There are no transcript claims in query authentication paths after query indices are sampled. In T1/T2, the B2 claim widths in base fields are 32, 776, 776, and sixteen arrays of 32. `final_poly` is an array of four fields; log arities are one array of nine fields in T1/T2 and nine items in T0. T3 frames exactly B0, B1, B2, each witness-only B3 sub-boundary, and B4 up to the query-PoW challenge; it must not combine adjacent rows of this table.

## 5. Full-width binding and A/B continuation

The transcript never substitutes a 32-byte lookup key for a 64-byte protocol digest. Statement initialization uses the complete parameter digest and all 64 statement fields. Commitments and state use both 32-byte halves. Global data and core proof remain their complete canonical byte strings.

For lookup only:

`statement_key = Keccak256(abi_word("PQTC.V3.STATEMENT") || parameter_left || parameter_right || 64 * abi_word(public_field))`.

`global_digest = Keccak256(global_bytes)` and `core_proof_digest = Keccak256(core_proof_bytes)`.

The persistent lookup record at `statement_key` stores `parameter_left`, `parameter_right`, the four full statement digests (eight halves), `global_digest`, `core_proof_digest`, and presence. A lookup succeeds only after recomputing the key from those stored full-width values and comparing every supplied full-width value. The key is an index, never the authoritative value.

Checkpoint payload is exactly: `global_digest[32] || transcript_state[64] || air_alpha E || zeta E || fri_alpha E || fri_betas[9] E || u16(query_count) || query_indices[count] u32 || u16(unique_count) || unique_indices[unique_count] u32`. Then:

`checkpoint_digest = Keccak256(abi_word("PQTC.V3.CHECKPOINT") || statement_key || Keccak256(checkpoint_payload))`.

Part A contains its full header, `global_digest`, full `global_bytes`, checkpoint digest and payload, full first query half, and end marker. `proof_id = Keccak256(abi_word("PQTC.V3.PROOF") || statement_key || Keccak256(part_a_bytes))`. Part B contains its full header, `proof_id`, `global_digest`, a second full copy of `global_bytes`, the identical checkpoint, full second query half, and end marker. Verification rejects a part pair unless headers/statements, proof ID, full global bytes, global digest, checkpoint payload/digest, half start/count/index positions, and final reconstructed proof all agree. Half A covers query positions 0–15 and half B 16–31; halves are not interchangeable.

## 6. Required rejection behavior

Decoders reject: any noncanonical field/extension coefficient; unknown type/version; wrong fixed width; declared count/length mismatch; trailing bytes or zeros; reordered items; truncated items/frames; type substitution; squeezing a challenge before all claims for its boundary are present; swapped digest halves; swapped A/B halves; and any statement/global/checkpoint/core-proof/part from another proof. Every rejection is structural or equality-based; no security property is inferred from a 32-byte key alone.

## 7. Security status

These candidates only measure transcript encodings. They do not establish Fiat–Shamir soundness in the QROM, collision security for a composed protocol, STARK security, zero knowledge, or custody safety. T0 compatibility is an implementation equivalence claim only. Selection is conditional on cross-language agreement, mutation rejection, measured full-path benefit, and external cryptographic review. Until all gates pass, the only permitted classification is `BENCHMARK_ONLY`.
