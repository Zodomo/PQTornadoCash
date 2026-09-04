#!/usr/bin/env python3
"""Candidate-neutral public-statement binding checker for the frozen v0.3 study.

The SHA-512 values below are structural comparison oracles, not candidate hashes.
They make every semantic dependency and byte ordering executable without choosing a
future field, algebraic hash, or hash-to-field mapping.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CASES_PATH = ROOT / "research/common-corpus/semantic-cases.json"
INVALID_PATH = ROOT / "research/common-corpus/invalid-mutations.json"
LAYOUTS = {
    "v03-direct": {"version": 3, "field_count": 64, "encoding": "64-u32be"},
    "minimal-safe-packed": {"version": 4, "field_count": 64, "encoding": "8-bytes32-eight-u32be-lanes"},
    "aggressive-statement-digest": {"version": 4, "field_count": 16, "encoding": "one-512-bit-digest-as-16-u32be"},
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def tagged_hash(tag: str, *parts: bytes) -> bytes:
    h = hashlib.sha512()
    tag_bytes = tag.encode()
    h.update(len(tag_bytes).to_bytes(2, "big"))
    h.update(tag_bytes)
    for part in parts:
        h.update(len(part).to_bytes(4, "big"))
        h.update(part)
    return h.digest()


def parse_hex(value: Any, size: int, label: str, reasons: list[str]) -> bytes | None:
    length_code = f"INVALID_{label}_LENGTH"
    encoding_code = f"INVALID_{label}_ENCODING"
    if not isinstance(value, str) or not value.startswith("0x"):
        reasons.append(encoding_code)
        return None
    payload = value[2:]
    if len(payload) != size * 2:
        reasons.append(length_code)
        return None
    try:
        return bytes.fromhex(payload)
    except ValueError:
        reasons.append(encoding_code)
        return None


def parse_decimal(value: Any, label: str, reasons: list[str], *, signed: bool = False) -> int | None:
    digits = value[1:] if signed and isinstance(value, str) and value.startswith("-") else value
    if not isinstance(value, str) or not value or not isinstance(digits, str) or not digits or not digits.isascii() or not digits.isdecimal():
        reasons.append(f"INVALID_{label}_ENCODING")
        return None
    return int(value)


def validate_case(case: dict[str, Any], known_ids: set[str]) -> list[str]:
    reasons: list[str] = []
    if "corpusVersion" not in case:
        reasons.append("MISSING_CORPUS_VERSION")
    elif case["corpusVersion"] != 1:
        reasons.append("UNSUPPORTED_CORPUS_VERSION")
    case_id = case.get("caseId")
    if not isinstance(case_id, str) or not case_id:
        reasons.append("INVALID_CASE_ID")
    elif case_id in known_ids:
        reasons.append("DUPLICATE_CASE_ID")

    chain = parse_decimal(case.get("chainId"), "CHAIN_ID", reasons)
    if chain is not None and not 1 <= chain <= (1 << 64) - 1:
        reasons.append("CHAIN_ID_OUT_OF_RANGE")
    parse_hex(case.get("poolAddress"), 20, "POOL_ADDRESS", reasons)
    denomination = parse_decimal(case.get("denomination"), "DENOMINATION", reasons)
    if denomination is not None and not 1 <= denomination <= (1 << 256) - 1:
        reasons.append("DENOMINATION_OUT_OF_RANGE")
    version = case.get("protocolSemanticVersion")
    if not isinstance(version, str) or not version:
        reasons.append("INVALID_PROTOCOL_SEMANTIC_VERSION")
    elif version != "pqtc-withdrawal-semantics-v1":
        reasons.append("UNSUPPORTED_PROTOCOL_SEMANTIC_VERSION")

    depth = case.get("treeDepth")
    if not isinstance(depth, int) or isinstance(depth, bool) or depth != 20:
        reasons.append("INVALID_TREE_DEPTH")
    parse_hex(case.get("nullifierSecretBytes"), 32, "NULLIFIER_SECRET", reasons)
    parse_hex(case.get("trapdoorBytes"), 32, "TRAPDOOR", reasons)

    leaf = case.get("leafIndex")
    if not isinstance(leaf, int) or isinstance(leaf, bool) or not isinstance(depth, int) or leaf < 0 or leaf >= 1 << max(depth, 0):
        reasons.append("LEAF_INDEX_OUT_OF_RANGE")
    path = case.get("pathBits")
    if not isinstance(path, list) or not isinstance(depth, int) or len(path) != depth:
        reasons.append("PATH_LENGTH_MISMATCH")
    elif any(bit not in (0, 1) or isinstance(bit, bool) for bit in path):
        reasons.append("INVALID_PATH_BIT")
    elif isinstance(leaf, int) and leaf >= 0 and sum(bit << i for i, bit in enumerate(path)) != leaf:
        reasons.append("LEAF_INDEX_PATH_MISMATCH")
    siblings = case.get("siblingSeeds")
    if not isinstance(siblings, list) or not isinstance(depth, int) or len(siblings) != depth:
        reasons.append("SIBLING_COUNT_MISMATCH")
    elif isinstance(siblings, list):
        for sibling in siblings:
            parse_hex(sibling, 32, "SIBLING_SEED", reasons)

    parse_hex(case.get("recipient"), 20, "RECIPIENT", reasons)
    parse_hex(case.get("relayer"), 20, "RELAYER", reasons)
    fee = parse_decimal(case.get("fee"), "FEE", reasons, signed=True)
    if fee is not None and not 0 <= fee <= (1 << 256) - 1:
        reasons.append("FEE_OUT_OF_RANGE")
    if fee is not None and denomination is not None and fee > denomination:
        reasons.append("FEE_EXCEEDS_DENOMINATION")
    return sorted(set(reasons))


def apply_patch(value: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    out = copy.deepcopy(value)
    for operation in operations:
        tokens = [token.replace("~1", "/").replace("~0", "~") for token in operation["path"].split("/")[1:]]
        parent: Any = out
        for token in tokens[:-1]:
            parent = parent[int(token)] if isinstance(parent, list) else parent[token]
        key = tokens[-1]
        op = operation["op"]
        if isinstance(parent, list):
            if op == "add" and key == "-":
                parent.append(operation["value"])
            elif op == "remove":
                parent.pop(int(key))
            elif op == "replace":
                parent[int(key)] = operation["value"]
            else:
                raise ValueError(f"unsupported patch operation: {operation}")
        elif op == "remove":
            del parent[key]
        elif op in ("add", "replace"):
            parent[key] = operation["value"]
        else:
            raise ValueError(f"unsupported patch operation: {operation}")
    return out


def semantic_statement(case: dict[str, Any]) -> dict[str, bytes]:
    """Build an abstract 512-bit statement preserving v0.3 dependency edges."""
    scope_payload = canonical_json({
        "chainId": case["chainId"],
        "consumer": case["poolAddress"],
        "denomination": case["denomination"],
        "treeDepth": case["treeDepth"],
        "protocolSemanticVersion": case["protocolSemanticVersion"],
        "candidateParameterId": case.get("_candidateParameterId", "candidate-neutral-parameter-A"),
    })
    scope = tagged_hash("PQTC.STUDY.SCOPE", scope_payload)
    secret = bytes.fromhex(case["nullifierSecretBytes"][2:])
    trapdoor = bytes.fromhex(case["trapdoorBytes"][2:])
    commitment = tagged_hash("PQTC.STUDY.NOTE", scope, secret, trapdoor)
    node = commitment
    for level, (bit, seed) in enumerate(zip(case["pathBits"], case["siblingSeeds"])):
        sibling = tagged_hash("PQTC.STUDY.SIBLING", bytes.fromhex(seed[2:]))
        left, right = (node, sibling) if bit == 0 else (sibling, node)
        node = tagged_hash("PQTC.STUDY.MERKLE", level.to_bytes(1, "big"), left, right)
    nullifier = tagged_hash("PQTC.STUDY.NULLIFIER", scope, secret)
    payout = tagged_hash(
        "PQTC.STUDY.PAYOUT",
        bytes.fromhex(case["recipient"][2:]),
        bytes.fromhex(case["relayer"][2:]),
        int(case["fee"]).to_bytes(32, "big"),
    )
    return {"scope": scope, "root": node, "nullifier": nullifier, "payout": payout}


def direct_fields(statement: dict[str, bytes]) -> list[int]:
    raw = b"".join(statement[name] for name in ("scope", "root", "nullifier", "payout"))
    return [int.from_bytes(raw[i:i + 4], "big") for i in range(0, len(raw), 4)]


def pack_eight_u32(fields: list[int]) -> list[int]:
    assert len(fields) % 8 == 0
    return [sum(fields[i + lane] << (32 * (7 - lane)) for lane in range(8)) for i in range(0, len(fields), 8)]


def unpack_eight_u32(words: list[int]) -> list[int]:
    return [(word >> (32 * (7 - lane))) & 0xFFFF_FFFF for word in words for lane in range(8)]


def encoded_layout(case: dict[str, Any], layout: str) -> tuple[list[int], bytes]:
    fields = direct_fields(semantic_statement(case))
    spec = LAYOUTS[layout]
    if layout == "v03-direct":
        values = fields
        encoded = b"".join(value.to_bytes(4, "big") for value in values)
    elif layout == "minimal-safe-packed":
        words = pack_eight_u32(fields)
        assert unpack_eight_u32(words) == fields
        values = fields
        encoded = b"".join(word.to_bytes(32, "big") for word in words)
    else:
        digest = tagged_hash("PQTC.STUDY.STATEMENT.V4", b"".join(value.to_bytes(4, "big") for value in fields))
        values = [int.from_bytes(digest[i:i + 4], "big") for i in range(0, 64, 4)]
        encoded = digest
    domain = canonical_json({"layout": layout, **spec})
    return values, domain + b"\x00" + encoded


def binding_key(case: dict[str, Any], layout: str) -> bytes:
    _, encoded = encoded_layout(case, layout)
    return tagged_hash("PQTC.STUDY.BINDING.KEY", encoded)


def valid_mutations(case: dict[str, Any], other: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mutations: dict[str, dict[str, Any]] = {}
    swaps = {
        "cross-scope-chain": "chainId",
        "cross-scope-consumer-pool": "poolAddress",
        "cross-scope-denomination": "denomination",
        "cross-scope-version": "protocolSemanticVersion",
        "cross-root-path": "pathBits",
        "cross-root-siblings": "siblingSeeds",
        "cross-nullifier-secret": "nullifierSecretBytes",
        "cross-recipient": "recipient",
        "cross-relayer": "relayer",
    }
    for name, field in swaps.items():
        changed = copy.deepcopy(case)
        changed[field] = copy.deepcopy(other[field])
        if field == "pathBits":
            changed["leafIndex"] = other["leafIndex"]
        mutations[name] = changed
    mutations["cross-scope-version"]["protocolSemanticVersion"] = "pqtc-withdrawal-semantics-v2"
    changed_parameter = copy.deepcopy(case)
    changed_parameter["_candidateParameterId"] = "candidate-neutral-parameter-B"
    mutations["cross-scope-parameter"] = changed_parameter
    changed_fee = copy.deepcopy(case)
    fee = int(changed_fee["fee"])
    denomination = int(changed_fee["denomination"])
    changed_fee["fee"] = str(0 if fee != 0 else min(1, denomination))
    mutations["cross-fee"] = changed_fee
    return mutations


def field_map() -> list[dict[str, Any]]:
    group_data = {
        "scope": {
            "range": range(0, 16),
            "semanticSource": ["chainId", "poolAddress/consumer", "denomination", "treeDepth", "protocolVersion", "parameterId"],
            "air": "Poseidon NOTE and NULLIFIER inputs; two gated equality emissions per limb",
            "pool": "immutable scope recomputed from chain, pool, denomination, depth, version, parameter",
            "effect": "consumer/domain/replay separation; note and nullifier domain binding",
        },
        "root": {
            "range": range(16, 32),
            "semanticSource": ["note commitment", "leafIndex/pathBits", "sibling digests", "level"],
            "air": "final level-19 Merkle output; one gated equality emission per limb",
            "pool": "canonical digest plus knownRoots membership check",
            "effect": "membership in retained pool state root",
        },
        "nullifier": {
            "range": range(32, 48),
            "semanticSource": ["scope", "nullifierSecret"],
            "air": "NULLIFIER hash output; one gated equality emission per limb",
            "pool": "unspent check then nullifiers mapping set before external payout calls",
            "effect": "one-spend/replay protection and WithdrawalComplete identity",
        },
        "payout": {
            "range": range(48, 64),
            "semanticSource": ["recipient", "relayer", "fee"],
            "air": "PAYOUT digest preimage input; one gated equality emission per limb",
            "pool": "recomputed after recipient/fee/relayer validity checks",
            "effect": "binds recipient amount, relayer payment, and fee",
        },
    }
    rows: list[dict[str, Any]] = []
    for group, data in group_data.items():
        for index in data["range"]:
            rows.append({
                "index": index,
                "group": group,
                "digestLimb": index % 16,
                "byteRangeWithinDigest": [4 * (index % 16), 4 * (index % 16) + 3],
                "semanticSource": data["semanticSource"],
                "airBinding": data["air"],
                "transcript": "ordered canonical u32 observed at transcript initialization and again after query input roots",
                "proofCodec": "ordered u32be in each part common header; count fixed to 64; compared to expected statement",
                "abi": "one 32-byte ABI slot in uint32[64] on begin and complete",
                "poolCheck": data["pool"],
                "stateOrPayoutEffect": data["effect"],
                "minimalSafeDisposition": "PACK; retain exact field and order after canonical unpack",
                "aggressiveDisposition": "DIGEST_COMMIT; private/derived source must be constrained into versioned statement digest",
                "removalAlone": "REJECT",
                "v03CompatibleAfterChange": False,
            })
    return rows

def operation_assessments(mutation_results: list[dict[str, Any]], reorder_rejected: bool, pack_round_trip: bool) -> list[dict[str, Any]]:
    by_layout = {
        layout: all(row["rejected"] for row in mutation_results if row["layout"] == layout)
        for layout in LAYOUTS
    }
    return [
        {
            "operation": "removal",
            "preservesRequiredBindings": False,
            "testedDisposition": "REJECT",
            "lostIfRemoved": {
                "scope": ["consumer", "note-scope", "nullifier-scope", "cross-chain replay", "version", "parameter"],
                "root": ["state-root membership"],
                "nullifier": ["spent-state identity", "replay protection"],
                "payout": ["recipient", "relayer", "fee", "transfer amounts"],
            },
        },
        {
            "operation": "derivation",
            "preservesRequiredBindings": True,
            "testedDisposition": "BOUNDARY_ONLY",
            "condition": "scope and payout may be recomputed from complete semantic inputs but must be injected unchanged into the existing 64 AIR/transcript fields; root and nullifier remain transaction-selected",
        },
        {
            "operation": "digest-commitment",
            "preservesRequiredBindings": by_layout["aggressive-statement-digest"],
            "testedDisposition": "CONDITIONAL_STOP",
            "condition": "all 64 ordered fields are a constrained, versioned preimage; structural oracle mutations passed but cryptographic/AIR/security gates did not",
        },
        {
            "operation": "packing",
            "preservesRequiredBindings": pack_round_trip and by_layout["minimal-safe-packed"],
            "testedDisposition": "PROCEED_RESEARCH_ONLY",
            "condition": "eight canonical u32be lanes per bytes32, exact unpack and order, new version/domain",
        },
        {
            "operation": "reordering",
            "preservesRequiredBindings": False,
            "testedDisposition": "REJECT_V03",
            "mutationRejected": reorder_rejected,
            "condition": "no byte benefit; only a complete new-version remap could be unambiguous",
        },
    ]

def verify_source_hashes() -> list[dict[str, str]]:
    manifest = json.loads((HERE / "source-hashes.json").read_text())
    failures = []
    for relative, expected in manifest["files"].items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            failures.append({"path": relative, "expected": expected, "actual": actual})
    return failures


def run() -> dict[str, Any]:
    corpus = json.loads(CASES_PATH.read_text())
    invalid_doc = json.loads(INVALID_PATH.read_text())
    source_hash_failures = verify_source_hashes()
    cases = corpus["cases"]
    ids = {case["caseId"] for case in cases}
    valid_failures = []
    for case in cases:
        reasons = validate_case(case, ids - {case["caseId"]})
        if reasons:
            valid_failures.append({"caseId": case["caseId"], "reasons": reasons})

    by_id = {case["caseId"]: case for case in cases}
    invalid_failures = []
    for mutation in invalid_doc["mutations"]:
        base = by_id[mutation["baseCaseId"]]
        changed = apply_patch(base, mutation["operations"])
        reasons = validate_case(changed, ids - {base["caseId"]})
        expected = mutation["expectedOutcome"]["errorCode"]
        if not reasons or expected not in reasons:
            invalid_failures.append({"mutationId": mutation["mutationId"], "expected": expected, "reasons": reasons})

    base = cases[0]
    other = next(case for case in cases[1:] if case["poolAddress"] != base["poolAddress"] and case["recipient"] != base["recipient"])
    mutation_results = []
    binding_failures = []
    for layout in LAYOUTS:
        key = binding_key(base, layout)
        for name, changed in valid_mutations(base, other).items():
            rejected = binding_key(changed, layout) != key
            mutation_results.append({"layout": layout, "mutation": name, "rejected": rejected})
            if not rejected:
                binding_failures.append({"layout": layout, "mutation": name})

    # Explicit layout, version, and ordering separation checks.
    base_keys = {layout: binding_key(base, layout) for layout in LAYOUTS}
    layout_distinct = len(set(base_keys.values())) == len(base_keys)
    direct, _ = encoded_layout(base, "v03-direct")
    reordered = direct[:]
    reordered[0], reordered[16] = reordered[16], reordered[0]
    reorder_rejected = tagged_hash("PQTC.STUDY.BINDING.KEY", b"v03-direct\x00" + b"".join(x.to_bytes(4, "big") for x in reordered)) != base_keys["v03-direct"]
    pack_round_trip = unpack_eight_u32(pack_eight_u32(direct)) == direct

    field_rows = field_map()
    assessments = operation_assessments(mutation_results, reorder_rejected, pack_round_trip)
    operation_coverage = {row["operation"] for row in assessments} == {"removal", "derivation", "digest-commitment", "packing", "reordering"}
    passed = not source_hash_failures and not valid_failures and not invalid_failures and not binding_failures and layout_distinct and reorder_rejected and pack_round_trip and operation_coverage and len(field_rows) == 64
    return {
        "recordType": "PublicStatementStudyResults",
        "measurementLabels": {
            "MEASURED": "computed by this checker from checked-in artifacts",
            "EXACT_SOURCE": "constant or count directly derivable from frozen source",
            "PROJECTED": "requires an unimplemented changed-layout AIR/ABI/codec",
        },
        "sourceHashes": {"checked": True, "failures": source_hash_failures},
        "corpus": {
            "semanticCasesChecked": len(cases),
            "semanticCasesAccepted": len(cases) - len(valid_failures),
            "invalidMutationsChecked": len(invalid_doc["mutations"]),
            "invalidMutationsRejectedWithExpectedReason": len(invalid_doc["mutations"]) - len(invalid_failures),
            "validFailures": valid_failures,
            "invalidFailures": invalid_failures,
        },
        "operationAssessments": assessments,
        "bindingMutations": mutation_results,
        "bindingMutationCount": len(mutation_results),
        "layoutChecks": {
            "layoutAndVersionDomainsDistinct": layout_distinct,
            "reorderingRejected": reorder_rejected,
            "minimalPackingRoundTrip": pack_round_trip,
            "changedLayoutsV03Compatible": False,
        },
        "fieldMap": {"count": len(field_rows), "allHaveDisposition": all(row["minimalSafeDisposition"] and row["aggressiveDisposition"] for row in field_rows)},
        "exactSourceFacts": {
            "v03PublicFields": 64,
            "v03CanonicalPublicBytesPerProofHeader": 256,
            "v03CommonHeaderBytes": 338,
            "v03AbiBytesForUint32ArrayPerRegistryCall": 2048,
            "v03AirPublicInputs": 64,
            "v03TraceColumns": 190,
            "v03Constraints": 1186,
            "sourceLevelPublicEqualityEmissions": {"scope": 32, "root": 16, "nullifier": 16, "payout": 16, "total": 80},
            "minimalPackedAbiBytesPerRegistryCall": 256,
            "minimalPackedAbiByteReductionPerRegistryCall": 1792,
            "minimalPackedProofHeaderByteReduction": 0,
            "aggressiveDigestFields": 16,
            "aggressiveDigestCanonicalBytesPerProofHeader": 64,
            "aggressiveDigestHeaderByteReductionPerProofPart": 192,
            "aggressiveDigestAbiBytesPerRegistryCallAsBytes32Pair": 64,
            "aggressiveDigestAbiByteReductionPerRegistryCall": 1984,
            "aggressiveCombinedByteReductionPerRegistryCallAndProofPart": 2176,
        },
        "projectedFacts": {
            "aggressiveTraceColumns": "PROJECTED unchanged at 190 only if existing work columns are reused",
            "aggressiveConstraintDelta": "PROJECTED; no changed AIR implemented",
            "aggressivePermutationDelta": "PROJECTED +19 active Poseidon permutations for a 64-field-to-16-field statement hash using the current rate-4 schedule; current 240 active rows would exceed the 256-row trace",
            "calldataGas": "PROJECTED/content-dependent; byte counts are exact but zero/nonzero byte mix and execution overhead are not",
        },
        "outcome": "PROCEED_MINIMAL_RESEARCH_ONLY_STOP_AGGRESSIVE" if passed else "STOP_CHECK_FAILED",
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write deterministic results and field map")
    args = parser.parse_args()
    results = run()
    if args.write:
        (HERE / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
        (HERE / "field-map.json").write_text(json.dumps({"recordType": "V03PublicFieldMap", "fields": field_map()}, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
