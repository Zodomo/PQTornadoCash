#!/usr/bin/env python3
"""Deterministically assemble and verify the external cryptanalysis review packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST_PATH = HERE / "manifest.json"
OUTPUT_PATH = HERE / "REVIEW_PACKET.md"
STATUS_PATH = HERE / "status.json"
EXPECTED_TOPICS = {
    "exact_field_and_matrices",
    "round_constants_and_derivation",
    "modes",
    "domain_layouts",
    "truncation",
    "threat_properties",
    "lifetime_invocation_sensitivity",
    "quantum_target",
    "pinned_attack_sources",
    "project_calculations",
    "open_questions",
}
EXPECTED_CHECKLIST = {
    "algebraic_attacks",
    "subspace_trails",
    "round_skipping",
    "invariants_and_related_inputs",
    "sponge_versus_compression",
    "feed_forward_and_truncation",
    "domain_and_level_injection",
    "multi_target_security",
}
REQUIRED_HEADINGS = {
    "## 1. Scope and disposition",
    "## 2. Exact fields, permutations, matrices, and constants",
    "## 3. Modes, outputs, truncation, and domain layouts",
    "## 4. SP-30 transcript and continuation binding",
    "## 5. Threat properties and model boundary",
    "## 6. Quantum target, project calculations, and lifetime sensitivity",
    "## 7. Pinned attack and theorem sources",
    "## 8. Reviewer checklist and requested deliverable",
    "## 9. Open questions and blocking evidence",
    "## 10. Hash-pinned local evidence",
}


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(manifest: dict) -> list[str]:
    errors: list[str] = []
    if manifest.get("classification") != "INTERNAL_PACKET_READY_EXTERNAL_REVIEW_OPEN":
        errors.append("classification must remain INTERNAL_PACKET_READY_EXTERNAL_REVIEW_OPEN")
    if manifest.get("candidate_disposition") != "NO_AIR_CANDIDATE":
        errors.append("candidate disposition must remain NO_AIR_CANDIDATE")
    if manifest.get("security_qualified") is not False:
        errors.append("security_qualified must be false")
    if manifest.get("external_review_complete") is not False:
        errors.append("external_review_complete must be false")
    if set(manifest.get("required_topics", [])) != EXPECTED_TOPICS:
        errors.append("required_topics does not exactly cover plan section 17")
    if set(manifest.get("reviewer_checklist", [])) != EXPECTED_CHECKLIST:
        errors.append("reviewer_checklist does not exactly cover plan section 17")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    source_paths: set[str] = set()
    for source in manifest.get("local_sources", []):
        source_id = source.get("id")
        relative = source.get("path")
        expected = source.get("sha256")
        if not isinstance(source_id, str) or source_id in seen_ids:
            errors.append(f"invalid or duplicate source id: {source_id!r}")
        else:
            seen_ids.add(source_id)
        if not isinstance(relative, str) or relative in seen_paths:
            errors.append(f"invalid or duplicate source path: {relative!r}")
            continue
        seen_paths.add(relative)
        source_paths.add(relative)
        path = (ROOT / relative).resolve()
        try:
            path.relative_to(ROOT)
        except ValueError:
            errors.append(f"source escapes repository: {relative}")
            continue
        if not path.is_file():
            errors.append(f"missing source: {relative}")
            continue
        if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
            errors.append(f"invalid sha256 for {relative}")
            continue
        actual = sha256(path)
        if actual != expected:
            errors.append(f"sha256 mismatch for {relative}: expected {expected}, got {actual}")

    vector = manifest.get("compressed_vector_package", {})
    vector_path = vector.get("path")
    if vector.get("reference_only_do_not_duplicate") is not True:
        errors.append("compressed vector package must be reference-only")
    if vector_path not in source_paths or vector.get("metadata") not in source_paths:
        errors.append("compressed vector package and metadata must be hash-pinned local sources")
    vector_source = next((s for s in manifest.get("local_sources", []) if s.get("path") == vector_path), None)
    if vector_source is None or vector_source.get("sha256") != vector.get("sha256"):
        errors.append("compressed vector package digest disagrees with local source pin")
    metadata_path = ROOT / str(vector.get("metadata", ""))
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("artifact") != vector_path:
            errors.append("vector metadata artifact path disagrees with manifest")
        if metadata.get("compressed", {}).get("sha256") != vector.get("sha256"):
            errors.append("vector metadata compressed digest disagrees with manifest")

    for source in manifest.get("external_sources", []):
        if source.get("retained_at") not in source_paths:
            errors.append(f"external source retention path is not hash-pinned: {source.get('id')}")
        if re.fullmatch(r"https://[^\s]+", str(source.get("url", ""))) is None:
            errors.append(f"invalid external source URL: {source.get('id')}")
        if not str(source.get("status", "")).endswith(("OPEN", "ONLY", "SOURCE")) and source.get("status") not in {
            "CONDITIONAL_THEOREM_SOURCE",
            "CONJECTURAL_SOURCE_EXCLUDED_FROM_TARGET_RECOMMENDATIONS",
        }:
            errors.append(f"external source status is not explicitly limited: {source.get('id')}")
    return errors


def render(manifest: dict) -> str:
    external_rows = "\n".join(
        f"| {item['id']} | {item['citation']} | {item['url']} | `{item['status']}` |"
        for item in manifest["external_sources"]
    )
    local_rows = "\n".join(
        f"| `{item['id']}` | `{item['path']}` | `{item['sha256']}` |"
        for item in manifest["local_sources"]
    )
    text = f"""# PQTornado hash and transcript external-review packet

**Packet:** `{manifest['packet_id']}`  
**Classification:** `{manifest['classification']}`  
**Candidate disposition:** `{manifest['candidate_disposition']}`  
**Security-qualified:** `false`  
**Independent cryptographic acceptance:** `OPEN`

## 1. Scope and disposition

This is a compact handoff of committed SP-10 compression, SP-30 transcript, digest-width, and independent security-model evidence. It is ready to be read externally; it is not an approval of a primitive, transcript, proof system, AIR, or custody path. There are zero security-qualified finalists, so no AIR candidate can be attached to an accepted hash/transcript stack. Baselines and controls remain context only and are not promoted.

Every numeric security value below is either an idealized generic projection or a calculator output carrying its stated theorem/conjecture conditions. No structural-security lower bound, Fiat-Shamir/QROM reduction, zero-knowledge theorem, composition theorem, deployment approval, live-chain observation, or external acceptance is claimed. Familiarity or adoption of a primitive is not evidence.

The project gate is at least 100 quantum-adjusted bits for note/nullifier preimage, commitment/accumulator binding after multi-target accounting, and proof soundness under an accepted complete model. Exact-instance analysis and explicit QROM status are mandatory. This packet does not satisfy that gate; it asks reviewers what would be required to do so.

## 2. Exact fields, permutations, matrices, and constants

### Poseidon2 research instances H1/H3/H4/H5/H6

- Field: BabyBear `F_p`, `p = 2013265921 = 0x78000001`; one canonical lane is an unsigned 32-bit integer `< p`, serialized as four-byte big-endian. S-box: `x^7`.
- Pinned implementation source: Plonky3 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`. Widths and schedules are `t=16: RF=8, RP=13`; `t=24: RF=8, RP=21`; `t=32: RF=8, RP=30`. The eight full rounds are four initial and four final full rounds.
- Exact external layer: apply `M4` to each consecutive four-lane block, where
  `M4(a,b,c,d)=(2a+3b+c+d, a+2b+3c+d, a+b+2c+3d, 3a+b+c+2d)` in `F_p`; then, for each residue class `j mod 4`, add the sum of the post-`M4` lanes in that class to every lane in that class. This is the pinned Plonky3 external tensor construction, not an unspecified MDS matrix.
- Exact internal layer: after applying `x^7` to lane zero plus its internal round constant, let `s=sum_i x_i`; output lane `i` is `s + diagonal[i]*x_i` in `F_p`. The exact width-specific diagonal arrays are in the pinned constants artifact; the executable formula is in the TypeScript reference lines implementing `external` and `poseidon2`.
- Exact constants: all flattened initial, internal, final, and diagonal arrays for widths 16/24/32 are in `sp10-constants`. The derivation checker requires the exact Plonky3 commit, invokes `poseidon2/generate_constants.py --field babybear --width W --format json --skip-matrix`, and compares initial/internal/final constants. The diagonal is the pinned upstream optimized internal matrix data.
- Important evidence limit: the prior constant-comparison result is `NOT_RETAINED`. The script and literals are pinned, but this packet does not convert that into a completed independent regeneration claim. A reviewer should rerun it from a separately obtained checkout and retain the result.

### H0 and H7 context

- H0 is the frozen width-16 BabyBear Poseidon2 sponge/XOF baseline, not feed-forward compression. It absorbs four lanes per permutation and emits 16 fields over four four-lane blocks. Its exact initialization/absorption is pinned in `sp10-rust`. It is `BASELINE_ONLY_NOT_SECURITY_ACCEPTED`.
- H7 is the published RPO-M31 comparator: `p=2147483647`, width 24, rate 16, capacity 8, seven rounds plus a concluding linear/constants step, S-box exponents 5 and inverse 1717986917. Its circulant MDS first row and SHAKE-derived round constants are in `sp10-constants`; seed `RPO‑M31:p=2147483647,m=24,c=8,n=7`, `SHAKE256`, five-byte little-endian draws reduced modulo `p`. H7 remains a sponge comparator and has not been converted into a compressor.

## 3. Modes, outputs, truncation, and domain layouts

Poseidon2 research compression is exactly `C_{{t,d}}(x) = Trunc_d(P_t(x)+x)`, where addition is lane-wise in BabyBear and `Trunc_d` retains the first `d` lanes. Feed-forward is therefore present on every retained lane; no other lane is output. The review must not transfer a sponge argument to this compression mode or vice versa.

| ID | Exact mode / output | Exact tested layout or stop | Current label |
|---|---|---|---|
| H0 | width-16 sponge/XOF; 16 fields | state lanes 0..3 rate; lane 4 version=1; lane 5 H0 tag (`1`,`0x11`,`0x12`,`0x20`); lane 6 byte length; lane 7 field count; lane 8 level; remaining lanes zero initially | `BASELINE_ONLY_NOT_SECURITY_ACCEPTED` |
| H1 | `C_{{16,7}}`; first 7 feed-forward lanes | primitive negative control only; no application layout | negative control; about 72.116 ideal BHT bits |
| H2 | no construction | no reviewed width-16 multi-permutation wide-output mode was located or implemented | `STOPPED_NO_REVIEWED_MODE` |
| H3 | `C_{{24,10}}`; 40 bytes | node-shaped state: `left[10] || right[10] || role || version || shape || level`; no spare lanes | `BENCHMARK_ONLY`; layout incomplete |
| H4 | `C_{{24,11}}`; 44 bytes | application stopped: `left[11] || right[11] || 4 controls` needs 26 lanes | `PRIMITIVE_ONLY_LAYOUT_FAIL` |
| H5 | `C_{{32,12}}`; 48 bytes | node-shaped state: `left[12] || right[12] || role || version || shape || level || zero[4]` | `BENCHMARK_ONLY`; width-32 exact review absent |
| H6 | `C_{{32,14}}`; 56 bytes | node-shaped state: `left[14] || right[14] || role || version || shape || level`; no spare lanes | `BENCHMARK_ONLY`; width-32 exact review absent |
| H7 | RPO-M31 sponge; first 16 rate lanes, 64 bytes | absorbed message `role || version || shape || level || payload`; zero padding; capacity lane 16 contains `16-final_block_length` | published sponge comparator only |

For non-H0 layouts the control tuple is four distinct field lanes: `role` (`Primitive=1, Note=2, Nullifier=3, Node=4`), `protocol_version=1`, `shape=payload field count`, `level`. Child order is positional: left then right. The current non-H0 application harness requires payload length `2d`; thus its note/nullifier labels are primitive/layout microbenchmarks, not complete frozen semantic roles. Specifically, the note omits protocol scope, semantic secret/trapdoor widths are replaced by `d`, and scope, empty-leaf, and statement roles are not completely evaluated. These omissions prevent treating domain-layout tests as application security evidence.

The compressed vector bundle is referenced, not copied: `{manifest['compressed_vector_package']['path']}`, compressed SHA-256 `{manifest['compressed_vector_package']['sha256']}`. Its metadata records 18,146 Rust/TypeScript matches, only eight Solidity anchors, full three-language parity `NOT_EVALUATED`, misuse suite `NOT_EVALUATED`, and constant comparison `NOT_RETAINED`.

Digest-width side study, kept separate from Poseidon compression:

| Construction | Exact branch layout / truncation | Status |
|---|---|---|
| KeccakPair512 | `K(0x00 || tag_u8 || payload) || K(0x01 || tag_u8 || payload)`; retain both 32-byte outputs in branch order | `NO_ADOPTION_BASELINE_ONLY`, not security accepted |
| pair-trunc-384 | retain bytes `[0:24]` (MSB 192 bits) independently from each branch, branch 0 then branch 1 | `STOP_PENDING_EXTERNAL_ANALYSIS` |
| pair-trunc-320 | retain bytes `[0:20]` (MSB 160 bits) independently from each branch, branch 0 then branch 1 | `STOP_PENDING_EXTERNAL_ANALYSIS` |
| single-Keccak-256 | retain branch 0's full 32 bytes; branch 1 absent | `REJECT_NONQUALIFYING_LOWER_BOUND` |

Here `tag` is exactly one byte and payload is exact caller-supplied canonical bytes; no ABI encoding, implicit length, delimiter, or padding is inserted. Independence and combined binding of the two Keccak branches have no retained reduction, so nominal concatenated width is not acceptance evidence.

## 4. SP-30 transcript and continuation binding

Primitive: `K512(tag,payload) = Keccak256(0x00 || tag || payload) || Keccak256(0x01 || tag || payload)`. Digests are 64 bytes, left half then right half. Integers and canonical BabyBear fields are fixed-width big-endian; extension values are four canonical base coefficients in basis order. Domains are `INIT=0x42`, `ABSORB=0x43`, `SQUEEZE=0x44`, `FIELD=0x01`, `COMMITMENT=0x02`, `FIELD_ARRAY=0x03`, `ITEM_DIGEST=0x45`, `BOUNDARY_FRAME=0x46`. Versions are the nine ASCII bytes `PQTCT0-01` through `PQTCT3-01`.

- T0: one framed scalar/commitment absorb; the production-compatibility initialization reproduces v0.3 and is a control only.
- T1: typed array `u32(count) || count*field32`, with type and byte length in the state transition.
- T2: full typed item is first K512-digested, then its 64-byte digest is K512-absorbed into state.
- T3: before each challenge, absorb exactly one pending boundary frame: `version9 || u32(item_count) || u32(encoded_bytes_len) || (type8 || u32(payload_len) || payload)*`. A frame cannot cross a challenge boundary.

Squeeze blocks are `K512(SQUEEZE, state64 || u64(counter))`, counter starts at zero, bytes are consumed left-to-right, and every absorb clears buffered output and resets the counter. A base challenge repeatedly takes `BE32(next4) & 0x7fffffff`, accepting only values `< p`; there is no modulo reduction. An extension challenge takes four base challenges. A `b<=31` bit challenge is `BE32(next4) & (2^b-1)`.

The exact v0.3 claim-to-challenge graph is normative in `sp30-spec` and machine-readable in `sp30-graph`: B0 degree/base-degree/preprocessed-width/trace/public values before `air_alpha`; B1 quotient/random commitments before `zeta`; B2 all named openings before `fri_alpha`; each B3 commitment and PoW witness before its PoW result and `fri_beta`; B4 final polynomial/log arities/query witness before query PoW and 32 query indices. T3 frames exactly these boundaries and may not merge them.

The proposed continuation specification keeps full 64-byte parameter/statement/commitment/transcript values authoritative. A 32-byte `statement_key` is lookup-only; records must retain and compare full values. `global_digest`, `core_proof_digest`, `checkpoint_digest`, and `proof_id` are explicitly framed in `sp30-spec`, including A positions 0–15 and B positions 16–31. However, the implementation still has bytes32 identifiers, an overwriteable single-slot lookup, and hashed-record comparison. Therefore the full-width continuation redesign is incomplete.

T3 is only `T3_EXTERNAL_REVIEW_ONLY`. Primitive APIs do not enforce the claim/boundary state machine; premature sampling remains possible. The TypeScript misuse oracle uses out-of-band labels, Rust/Solidity mutation and cross-language parity were not run, and full-path EVM delta is unmeasured. No QROM, transcript-composition, STARK soundness, zero-knowledge, or custody claim follows from exact framing.

## 5. Threat properties and model boundary

| Property reviewers must resolve | Exact object | Current evidence / boundary |
|---|---|---|
| Collision / target collision | each `C_{{t,d}}`, H0/H7 sponge output, Keccak pair/truncations, transcript/continuation identifiers | Generic output-width arithmetic only; no instantiated lower bound or complete two-branch reduction |
| Preimage / second preimage | note, nullifier, Merkle node, statement/global/checkpoint/proof identifiers | Feed-forward and constrained/fixed input lanes can change the algebraic problem; identifier-specific required property remains to be reduced |
| Algebraic attacks | BabyBear, `x^7`, exact widths, external tensor, internal diagonal, RF/RP, mode constraints | 2025 subspace/Groebner corrections and 2026 operation-mode attacks are relevant; no candidate is cleared |
| Related input / invariants | shared permutation across role/version/shape/level schemas and left/right/level mutations | Injective-looking lane placement is not a proof that invariant subspaces or related-domain trails are absent |
| Transcript binding | K512 state machine, typed grammar, exact challenge graph | Grammar/order are specified; enforced state machine, composed collision argument, and QROM Fiat-Shamir reduction remain open |
| Multi-target | lifetime notes/nullifiers/nodes/digests/proofs across pools, parameters, and chains | Counts are unknown; sensitivity only. Digest-output targets, raw primitive calls, proof-forgery targets, and grinding sites must not be conflated |
| Soundness | v0.3 q32 AIR/FRI manifest | Calculator is independently translated but yields an unreviewed, low result and has stated conditional/conjectural limits; it performs no hash/transcript structural analysis |
| Zero knowledge | proof system and transcript | Not graded by these artifacts; padding is accounting input, not a theorem |

Known structural evidence must be read narrowly. The 2025 subspace-trail work corrects the original Groebner model; feed-forward changes equations but not their number or degree, and regularity can fail. The 2026 skipping-class work explicitly uses operation-mode constraints and the `P_{{t/4}} tensor M4` structure. Retained exact skips are H1 `t=16,d=7: [1]^1+[7]^3+[49]^3`, H3 `t=24,d=10: [1]^2+[7]^2+[49]^6`, and H4 `t=24,d=11: [1]^1+[7]^3+[49]^7`. Width 32 is outside the original Poseidon2 width-through-24 specification and the exact 2026 investigated set; applicability is plausible, not established. Reported attack speedups are not accepted bit-security estimates.

## 6. Quantum target, project calculations, and lifetime sensitivity

The minimum project target is 100 quantum-adjusted bits under a stated, accepted complete model. Generic values below omit constants, quantum circuit depth, fault tolerance, memory, parallelism, and oracle-construction cost. They are ceilings/sensitivity projections, not achieved attacks or security lower bounds.

SP-10 ideal arithmetic uses `log2(p) ~= 30.9069`. For `d` retained fields, ideal BHT collision ceiling is `d*log2(p)/3`; the hidden-state Grover ceiling shown by the project is `(t-d)*log2(p)/2`. Results: H1 `(72.116,139.081)`, H3 `(103.023,216.348)`, H4 `(113.325,200.895)`, H5 `(123.628,309.069)`, H6 `(144.232,278.162)` bits respectively. H3 has about three ideal collision bits above target before multi-target or structural accounting. H5/H6 arithmetic does not cure missing width-32 analysis.

SP-10's retained operation-count projection for one note, one nullifier, and a depth-20 authentication path is H0 `240` permutations, H3/H5/H6 `22`, and H7 `66`; H1/H2/H4 application paths are stopped. For `W` executions of exactly that research shape, the sensitivity is respectively `240W`, `22W`, or `66W` permutation calls. This is not a production lifetime forecast or complete relation measurement: the non-H0 semantic layouts are incomplete and no value of `W` is accepted. A depth-20 synthetic root update separately performs 20 node hashes but is not a complete direct deposit.

Digest-width lifetime model lets `M=2^m` count security-relevant digest outputs, not raw Keccak invocations. It projects BHT work as `2^((n-m)/3)` and Grover preimage/second-preimage work as `2^((n-m)/2)`, clamped at zero. The retained sweep is `m=0,16,24,32,40,48,56,64`; paired constructions make `2M` raw Keccak calls and the single branch makes `M`.

| nominal n | BHT floor bits at m = 0/16/24/32/40/48/56/64 | Grover floor bits at same m | raw-call multiplier | status |
|---:|---|---|---:|---|
| 512 | 170/165/162/160/157/154/152/149 | 256/248/244/240/236/232/228/224 | 2M | baseline only |
| 384 | 128/122/120/117/114/112/109/106 | 192/184/180/176/172/168/164/160 | 2M | stopped |
| 320 | 106/101/98/96/93/90/88/85 | 160/152/148/144/140/136/132/128 | 2M | stopped |
| 256 | 85/80/77/74/72/69/66/64 | 128/120/116/112/108/104/100/96 | M | rejected lower bound |

For the instrumented non-rejection transcript graph path, deterministic TypeScript instrumentation counted K512 calls T0/T1/T2/T3 as `4428/126/220/58`; because each K512 makes two Keccak-256 invocations, that is `8856/252/440/116` underlying calls per instrumented proof. Across `N` proofs, multiply these counts by `N`; discarded prover grinding trials and an integrated full verifier path are outside this count. Fewer calls are performance evidence only, never soundness evidence.

The independent v0.3 q32 calculator manifest fixes trace height 256, proof degree 512 after one hiding-padding bit, width 190, 1,186 constraints, maximum degree 7, 16 quotient chunks, four hiding functions, 210 batched functions, blowup 16, 32 queries, and 16-bit commit/query grinding. Its single-target best reported quantum value is `56.201226486` bits from LDR and is conditional on Johnson mutual correlated agreement; UDR reports `37.190582247`. Under proof-forgery target counts `2^0/2^20/2^32/2^40`, UDR is `37.1906/17.1906/5.1906/0`, and conditional LDR is `56.2012/36.2012/24.2012/16.2012`. Random-words is conjectural, omits batched-opening proximity for the actual 210 functions, and is excluded from target recommendations. These values independently rule out finalist status; they do not establish an attack or validate the hash/transcript.

## 7. Pinned attack and theorem sources

All source identifiers below were already retained by the project evidence named in the manifest. URLs identify review inputs; this assembler does not fetch them and their presence is not acceptance.

| ID | Citation and requested scope | URL | Retained status |
|---|---|---|---|
{external_rows}

## 8. Reviewer checklist and requested deliverable

Reviewers should return a signed/versioned result tied to this packet ID, every local SHA-256 pin, and the external source versions. For each item, state `PASS`, `FAIL`, `DEFER`, or `NOT_EVALUATED`, with attack model, exact instance, work factor, assumptions, and reproducible calculation. An unqualified family-level conclusion is not responsive.

- [ ] **Algebraic preimage/collision attacks:** write the constrained-lane systems for every enabled role and every `(field,t,d,matrix,S-box,RF,RP,mode)`; cover collision, target collision, preimage, and second preimage.
- [ ] **Subspace trails:** test exact external tensor/internal diagonal plus constants and constrained inputs; state whether 2025 corrected-model regularity/conjecture conditions hold.
- [ ] **Round skipping:** reproduce retained width-16/24 skips and determine width-32 applicability and complexity; do not extrapolate by width alone.
- [ ] **Invariants/related inputs:** analyze shared permutation use across roles, versions, shapes, levels, child order, fixed zeros, payload constraints, and cross-domain/cross-version relations.
- [ ] **Sponge versus compression:** give separate arguments for H0/H7 sponge behavior, Poseidon2 feed-forward compression, and K512 transcript/Keccak pair composition.
- [ ] **Feed-forward/truncation:** assess first-lane `P(x)+x`, unobserved state, exact output lane choice, 384/320 independent branch-prefix truncation, and whether classical compression conditions adapt to the quantum target.
- [ ] **Domain/level injection:** verify role/version/shape/level lane injection, H0 tag differences, T0–T3 version/domain grammar, boundary flushing, and inability to cross semantic or challenge boundaries.
- [ ] **Multi-target security:** use defensible lifetime populations for notes, nullifiers, nodes, transcript states, proof identifiers, and proof-forgery targets; identify which terms degrade and avoid applying one formula indiscriminately.

Requested bottom line: identify exact candidates/roles that fail immediately, those that need more evidence, and any instance worth a new packet. Do not authorize integration or deployment from this packet alone.

## 9. Open questions and blocking evidence

1. What are the best algebraic collision, preimage, and second-preimage attacks for each constrained H3/H4/H5/H6 role, including feed-forward and first-lane truncation?
2. Does the skipping-class method apply to `t=32` with the exact pinned external tensor and diagonals? What are concrete complexities at `d=12` and `d=14`?
3. Are there invariant subspaces, weak affine spaces, or related-input trails induced by role/version/shape/level lanes, H5 zero lanes, child swaps, level increments, or shared permutation/constants?
4. Does `Trunc_d(P(x)+x)` retain the claimed ideal behavior when many lanes are fixed or semantically related? Which theorem assumptions fail for each role?
5. Can the two domain-separated Keccak branches be reduced to the claimed combined collision/preimage properties, including after per-branch 384/320 truncation and under chosen-prefix/related-input use?
6. Which exact property is required for each statement key, global digest, checkpoint digest, core-proof digest, proof ID, verification ID, parameter ID, and future batch ID? Is a 32-byte lookup index safe only with authoritative full-width comparison?
7. Can a typed claim/boundary state machine enforce the normative SP-30 graph in Rust, Solidity, and TypeScript, and can serialized mutation/cross-language vectors demonstrate equivalence?
8. What QROM theorem or explicit assumption applies to K512 absorb/squeeze, rejection sampling, grinding, framed batching, continuation, and the complete Fiat-Shamir transform?
9. What defensible lifetime populations replace sensitivity variables for digest outputs, raw primitive calls, proofs, pools, parameter sets, and chains? Which are adversarially selectable targets?
10. Can independently regenerated constants and matrices be retained with reviewer signatures, and can full three-language/misuse vector coverage be completed without changing the exact instance?
11. What accepted complete AIR/FRI profile reaches 100 bits once batching, MMCS binding, transcript/QROM, grinding, multi-target, and composition are all included? Current q32 evidence reaches no such candidate.
12. Which zero-knowledge theorem covers the final protocol, randomness, hiding codewords, transcript interaction, and any aggregation? Current evidence does not grade it.

Until these questions are resolved, retain `INTERNAL_PACKET_READY_EXTERNAL_REVIEW_OPEN`, `NO_AIR_CANDIDATE`, every candidate stop/fail/defer label, and zero security-qualified candidates.

## 10. Hash-pinned local evidence

All paths are repository-relative. The checker requires each file to exist and match SHA-256 before accepting a deterministic packet comparison.

| ID | Local path | SHA-256 |
|---|---|---|
{local_rows}
"""
    return text.strip() + "\n"


def render_status(manifest: dict, packet_sha256: str) -> bytes:
    status = {
        "schema": "pqtc-external-cryptanalysis-review-status-v1",
        "packet_id": manifest["packet_id"],
        "classification": manifest["classification"],
        "candidate_disposition": manifest["candidate_disposition"],
        "security_qualified_candidate_count": 0,
        "external_review_complete": False,
        "integration_authorized": False,
        "deployment_authorized": False,
        "coverage": {
            "required_topics": len(manifest["required_topics"]),
            "required_topics_complete": True,
            "reviewer_checklist_items": len(manifest["reviewer_checklist"]),
            "reviewer_checklist_complete": True,
            "hash_pinned_local_sources": len(manifest["local_sources"]),
            "retained_external_source_pins": len(manifest["external_sources"]),
            "compressed_vectors_referenced_not_duplicated": True,
        },
        "packet": {
            "path": manifest["assembled_output"],
            "sha256": packet_sha256,
        },
        "verification": {
            "command": manifest["check_command"],
            "result": "PASS",
            "all_local_paths_and_hashes_resolve": True,
            "deterministic_assembly_matches": True,
        },
        "open_gates": [
            "independent external cryptographic review",
            "exact constrained-lane algebraic analysis",
            "width-32 round-skip applicability and complexity",
            "complete two-branch Keccak composition and truncation reduction",
            "full SP-30 claim-boundary state-machine enforcement",
            "Rust/Solidity/TypeScript mutation and parity execution",
            "complete continuation binding implementation",
            "Fiat-Shamir/QROM and zero-knowledge status",
            "accepted complete >=100-bit AIR/FRI profile",
            "defensible protocol-lifetime multi-target populations",
        ],
    }
    return (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def validate_rendered(packet: str) -> list[str]:
    errors: list[str] = []
    for heading in REQUIRED_HEADINGS:
        if heading not in packet:
            errors.append(f"missing required heading: {heading}")
    for label in ("INTERNAL_PACKET_READY_EXTERNAL_REVIEW_OPEN", "NO_AIR_CANDIDATE"):
        if label not in packet:
            errors.append(f"missing disposition label: {label}")
    if "widely used" in packet.lower():
        errors.append("packet contains forbidden popularity argument")
    if packet.count("cross-language.json.zst") != 2:
        errors.append("compressed vectors must be referenced once in prose and once in the source table")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    errors = validate_manifest(manifest)
    packet = render(manifest)
    errors.extend(validate_rendered(packet))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    expected = packet.encode("utf-8")
    packet_hash = hashlib.sha256(expected).hexdigest()
    expected_status = render_status(manifest, packet_hash)
    if args.write:
        OUTPUT_PATH.write_bytes(expected)
        STATUS_PATH.write_bytes(expected_status)
        print(json.dumps({"result": "WROTE", "path": str(OUTPUT_PATH.relative_to(ROOT)), "sha256": packet_hash}, sort_keys=True))
        return 0

    if not OUTPUT_PATH.is_file():
        print(f"ERROR: missing assembled packet: {OUTPUT_PATH.relative_to(ROOT)}", file=sys.stderr)
        return 1
    if OUTPUT_PATH.read_bytes() != expected:
        print("ERROR: assembled packet is stale; run with --write", file=sys.stderr)
        return 1
    if not STATUS_PATH.is_file() or STATUS_PATH.read_bytes() != expected_status:
        print("ERROR: machine-readable status is stale; run with --write", file=sys.stderr)
        return 1
    print(json.dumps({"result": "PASS", "sources": len(manifest["local_sources"]), "packet_sha256": packet_hash}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
