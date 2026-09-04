#!/usr/bin/env python3
"""Generate the backend-neutral PQTC semantic corpus using only Python's stdlib."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

CORPUS_VERSION = 1
TREE_DEPTH = 20
CASE_COUNT = 256
FULLY_RANDOM_CASE_COUNT = 128
SEED = bytes.fromhex("ab84f7821e9d3c5b3906c89bb6385f4fb4a4c6a5fb684977b85dcae88c5c9781")
GENERATOR_VERSION = "1.0.0"
TREE_HISTORY_LENGTHS = (0, 1, 2, 3, 4, 7, 8, 15, 16, 31, 32, 63, 64, 255, 256, 1023, 1024, 4095, 4096)
OUTPUT_NAMES = ("semantic-cases.json", "invalid-mutations.json")

MAPPING_RESPONSIBILITY = {
    "owner": "candidate implementation",
    "requirement": (
        "Treat nullifierSecretBytes, trapdoorBytes, siblingSeeds, and rejection-sampling draws as byte strings. "
        "Each candidate MUST document and implement an unbiased map to its own canonical field, secret, or digest "
        "domain; it MUST record every rejected draw and mapping failure and MUST NOT silently apply modular reduction."
    ),
    "nonChoice": (
        "This corpus deliberately specifies no candidate field modulus, endianness, hash-to-field algorithm, "
        "commitment hash, or candidate-specific encoding."
    ),
}


def deterministic_bytes(label: str, length: int) -> bytes:
    """Return a domain-separated SHA-256 counter stream."""
    out = bytearray()
    counter = 0
    label_bytes = label.encode("utf-8")
    while len(out) < length:
        out.extend(hashlib.sha256(b"PQTC-CORPUS-V1\x00" + SEED + b"\x00" + label_bytes + counter.to_bytes(4, "big")).digest())
        counter += 1
    return bytes(out[:length])


def hex_bytes(value: bytes) -> str:
    return "0x" + value.hex()


def path_bits(index: int) -> list[int]:
    return [(index >> level) & 1 for level in range(TREE_DEPTH)]


def nonzero_address(label: str) -> str:
    raw = bytearray(deterministic_bytes(label, 20))
    for offset, value in enumerate(raw):
        if value == 0:
            raw[offset] = (offset % 254) + 1
    return hex_bytes(bytes(raw))


def classes_for_index(index: int) -> list[str]:
    classes: list[str] = []
    if index in (0, 1, 2, 3):
        classes.append(f"leaf-index-{index}")
    if index == (1 << TREE_DEPTH) - 1:
        classes.extend(("leaf-index-maximum-20-bit", "path-all-one"))
    if index == 0:
        classes.append("path-all-zero")
    if path_bits(index) == [level % 2 for level in range(TREE_DEPTH)]:
        classes.append("path-alternating-0101")
    if path_bits(index) == [1 - (level % 2) for level in range(TREE_DEPTH)]:
        classes.append("path-alternating-1010")
    for exponent in range(1, TREE_DEPTH):
        power = 1 << exponent
        if index == power - 1:
            classes.append("leaf-index-power-minus-one")
        elif index == power:
            classes.append("leaf-index-power")
        elif index == power + 1:
            classes.append("leaf-index-power-plus-one")
    return classes


def structured_indices() -> list[int]:
    indices = [0, 1, 2, 3, (1 << TREE_DEPTH) - 1, 0xAAAAA, 0x55555]
    for exponent in range(1, TREE_DEPTH):
        power = 1 << exponent
        indices.extend((power - 1, power, power + 1))
    while len(indices) < CASE_COUNT - FULLY_RANDOM_CASE_COUNT:
        ordinal = len(indices)
        indices.append(int.from_bytes(deterministic_bytes(f"structured-index/{ordinal}", 4), "big") & ((1 << TREE_DEPTH) - 1))
    return indices


def rejection_metadata(case_id: str, target_field: str) -> dict[str, Any]:
    return {
        "targetField": target_field,
        "drawWidthBytes": 32,
        "draws": [
            "0x" + "ff" * 32,
            "0x" + "ff" * 31 + "fe",
            hex_bytes(deterministic_bytes(f"{case_id}/rejection-terminal", 32)),
        ],
        "trigger": "two-leading-maximal-unsigned-draws",
        "candidateObligation": (
            "Apply the candidate's documented unbiased admissibility rule in order; record the accepted draw index, "
            "all retries, or an explicit mapping failure. The corpus does not declare a field modulus."
        ),
    }


def make_case(ordinal: int, index: int, fully_random: bool) -> dict[str, Any]:
    case_id = f"swc-v1-{ordinal:03d}"
    classes = classes_for_index(index)
    classes.append("fully-random" if fully_random else "structured")
    if fully_random:
        classes.append("path-random")

    if fully_random:
        chain_id = 1 + int.from_bytes(deterministic_bytes(f"{case_id}/chain", 4), "big")
        denomination = 1 + int.from_bytes(deterministic_bytes(f"{case_id}/denomination", 12), "big")
        fee = int.from_bytes(deterministic_bytes(f"{case_id}/fee", 12), "big") % (denomination + 1)
        pool = hex_bytes(deterministic_bytes(f"{case_id}/pool", 20))
        recipient = hex_bytes(deterministic_bytes(f"{case_id}/recipient", 20))
        relayer = hex_bytes(deterministic_bytes(f"{case_id}/relayer", 20))
    else:
        chain_id = (1, 11155111, 42161, 10, 8453)[ordinal % 5]
        denomination = (10**18, 10**17, 5 * 10**18, 2**64)[ordinal % 4]
        fee = 1 + int.from_bytes(deterministic_bytes(f"{case_id}/fee", 8), "big") % denomination
        pool = hex_bytes(deterministic_bytes(f"{case_id}/pool", 20))
        recipient = hex_bytes(deterministic_bytes(f"{case_id}/recipient", 20))
        relayer = hex_bytes(deterministic_bytes(f"{case_id}/relayer", 20))

    nullifier = deterministic_bytes(f"{case_id}/nullifier", 32)
    trapdoor = deterministic_bytes(f"{case_id}/trapdoor", 32)
    siblings = [hex_bytes(deterministic_bytes(f"{case_id}/sibling/{level}", 32)) for level in range(TREE_DEPTH)]
    generation: dict[str, Any] = {
        "mode": "fully-random" if fully_random else "structured",
        "source": "sha256-counter-v1",
        "derivationLabel": case_id,
    }

    if ordinal == 7:
        repeated = hex_bytes(deterministic_bytes(f"{case_id}/repeated-prefix", 32))
        siblings[:8] = [repeated] * 8
        classes.append("repeated-sibling-prefix")
    if ordinal == 8:
        nullifier = bytes(32)
        classes.append("low-field-byte-value")
    if ordinal == 9:
        trapdoor = b"\x00" * 31 + b"\x01"
        classes.append("low-field-byte-value")
    if ordinal == 10:
        nullifier = b"\xff" * 32
        classes.append("high-field-byte-value")
    if ordinal == 11:
        trapdoor = b"\xff" * 31 + b"\xfe"
        classes.append("high-field-byte-value")
    if 12 <= ordinal <= 15:
        target = "nullifierSecretBytes" if ordinal % 2 == 0 else "trapdoorBytes"
        trigger = rejection_metadata(case_id, target)
        generation["rejectionSamplingTrigger"] = trigger
        first_draw = bytes.fromhex(trigger["draws"][0][2:])
        if target == "nullifierSecretBytes":
            nullifier = first_draw
        else:
            trapdoor = first_draw
        classes.append("rejection-sampling-retry-trigger")
    if ordinal == 16:
        fee = 0
        classes.append("fee-zero")
    if ordinal == 17:
        fee = denomination
        classes.append("fee-equals-denomination")
    if ordinal == 18:
        fee = 1
        classes.append("fee-small-nonzero")
    if ordinal == 19:
        fee = denomination - 1
        classes.append("fee-large-nonzero")
    if ordinal == 20:
        recipient = "0x" + "00" * 19 + "01"
        classes.append("recipient-many-zero-bytes")
    if ordinal == 21:
        relayer = "0x" + "00" * 18 + "0102"
        classes.append("relayer-many-zero-bytes")
    if ordinal == 22:
        recipient = nonzero_address(f"{case_id}/recipient-nonzero")
        classes.append("recipient-few-zero-bytes")
    if ordinal == 23:
        relayer = nonzero_address(f"{case_id}/relayer-nonzero")
        classes.append("relayer-few-zero-bytes")

    return {
        "corpusVersion": CORPUS_VERSION,
        "caseId": case_id,
        "chainId": str(chain_id),
        "poolAddress": pool,
        "denomination": str(denomination),
        "protocolSemanticVersion": "pqtc-withdrawal-semantics-v1",
        "treeDepth": TREE_DEPTH,
        "nullifierSecretBytes": hex_bytes(nullifier),
        "trapdoorBytes": hex_bytes(trapdoor),
        "leafIndex": index,
        "pathBits": path_bits(index),
        "siblingSeeds": siblings,
        "recipient": recipient,
        "relayer": relayer,
        "fee": str(fee),
        "caseClasses": sorted(set(classes)),
        "generationMetadata": generation,
    }


def make_tree_history_sequences() -> list[dict[str, Any]]:
    sequences = []
    for length in TREE_HISTORY_LENGTHS:
        if length == 0:
            selected: list[dict[str, Any]] = []
        else:
            maximum_carry = (1 << (length.bit_length() - 1)) - 1
            selected = [
                {
                    "insertIndex": 0,
                    "binaryCarryClass": "minimum",
                    "trailingOneBitsBeforeInsert": 0,
                }
            ]
            if maximum_carry != 0:
                selected.append(
                    {
                        "insertIndex": maximum_carry,
                        "binaryCarryClass": "maximum-within-sequence",
                        "trailingOneBitsBeforeInsert": maximum_carry.bit_length(),
                    }
                )
        sequences.append(
            {
                "sequenceId": f"tree-history-v1-{length:04d}",
                "length": length,
                "treeDepth": TREE_DEPTH,
                "depositInputDerivation": {
                    "source": "sha256-counter-v1",
                    "labelTemplate": f"tree-history-v1-{length:04d}/deposit/{{insertIndex}}",
                    "bytesPerDeposit": 64,
                },
                "selectedInsertPositions": selected,
                "selectionMeaning": (
                    "Positions use binary carry depth as a backend-neutral proxy for minimum and maximum "
                    "filled-subtree update work; candidates must record their actual writes."
                ),
            }
        )
    return sequences


def semantic_document() -> dict[str, Any]:
    structured = structured_indices()
    cases = []
    for ordinal in range(CASE_COUNT):
        fully_random = ordinal >= CASE_COUNT - FULLY_RANDOM_CASE_COUNT
        if fully_random:
            index = int.from_bytes(deterministic_bytes(f"swc-v1-{ordinal:03d}/leaf-index", 4), "big") & ((1 << TREE_DEPTH) - 1)
        else:
            index = structured[ordinal]
        cases.append(make_case(ordinal, index, fully_random))
    return {
        "corpusVersion": CORPUS_VERSION,
        "recordType": "SemanticWithdrawalWitnessCorpus",
        "encoding": {
            "byteStrings": "lowercase 0x-prefixed hexadecimal",
            "unsignedIntegers": "base-10 strings except treeDepth, leafIndex, and path bits",
            "pathBitOrder": "least-significant index bit first; pathBits[level] selects the node side at that level",
            "addresses": "20-byte lowercase 0x-prefixed hexadecimal; no checksum semantics",
        },
        "candidateMappingResponsibility": MAPPING_RESPONSIBILITY,
        "treeHistorySequences": make_tree_history_sequences(),
        "cases": cases,
    }


def mutation(mutation_id: str, base: str, field: str, boundary: str, error_code: str, operations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "mutationId": mutation_id,
        "baseCaseId": base,
        "semanticField": field,
        "boundary": boundary,
        "operations": operations,
        "expectedOutcome": {"valid": False, "errorCode": error_code},
    }


def invalid_document() -> dict[str, Any]:
    base = "swc-v1-024"
    m: list[dict[str, Any]] = []
    add = lambda field, boundary, code, ops: m.append(mutation(f"invalid-v1-{len(m):03d}", base, field, boundary, code, ops))
    replace = lambda path, value: [{"op": "replace", "path": path, "value": value}]
    remove = lambda path: [{"op": "remove", "path": path}]

    add("corpusVersion", "unsupported-version", "UNSUPPORTED_CORPUS_VERSION", replace("/corpusVersion", 2))
    add("corpusVersion", "missing", "MISSING_CORPUS_VERSION", remove("/corpusVersion"))
    add("caseId", "empty", "INVALID_CASE_ID", replace("/caseId", ""))
    add("caseId", "uniqueness", "DUPLICATE_CASE_ID", replace("/caseId", "swc-v1-025"))
    add("chainId", "zero", "CHAIN_ID_OUT_OF_RANGE", replace("/chainId", "0"))
    add("chainId", "non-decimal", "INVALID_CHAIN_ID_ENCODING", replace("/chainId", "1e3"))
    add("poolAddress", "short", "INVALID_POOL_ADDRESS_LENGTH", replace("/poolAddress", "0x" + "00" * 19))
    add("poolAddress", "long", "INVALID_POOL_ADDRESS_LENGTH", replace("/poolAddress", "0x" + "00" * 21))
    add("poolAddress", "non-hex", "INVALID_POOL_ADDRESS_ENCODING", replace("/poolAddress", "0x" + "gg" * 20))
    add("denomination", "zero", "DENOMINATION_OUT_OF_RANGE", replace("/denomination", "0"))
    add("denomination", "non-decimal", "INVALID_DENOMINATION_ENCODING", replace("/denomination", "-1"))
    add("protocolSemanticVersion", "empty", "INVALID_PROTOCOL_SEMANTIC_VERSION", replace("/protocolSemanticVersion", ""))
    add("protocolSemanticVersion", "unsupported", "UNSUPPORTED_PROTOCOL_SEMANTIC_VERSION", replace("/protocolSemanticVersion", "pqtc-withdrawal-semantics-v2"))
    add("treeDepth", "below-required", "INVALID_TREE_DEPTH", replace("/treeDepth", 19))
    add("treeDepth", "above-required", "INVALID_TREE_DEPTH", replace("/treeDepth", 21))
    add("nullifierSecretBytes", "short", "INVALID_NULLIFIER_SECRET_LENGTH", replace("/nullifierSecretBytes", "0x" + "00" * 31))
    add("nullifierSecretBytes", "long", "INVALID_NULLIFIER_SECRET_LENGTH", replace("/nullifierSecretBytes", "0x" + "00" * 33))
    add("nullifierSecretBytes", "non-hex", "INVALID_NULLIFIER_SECRET_ENCODING", replace("/nullifierSecretBytes", "0x" + "zz" * 32))
    add("trapdoorBytes", "short", "INVALID_TRAPDOOR_LENGTH", replace("/trapdoorBytes", "0x" + "00" * 31))
    add("trapdoorBytes", "long", "INVALID_TRAPDOOR_LENGTH", replace("/trapdoorBytes", "0x" + "00" * 33))
    add("trapdoorBytes", "non-hex", "INVALID_TRAPDOOR_ENCODING", replace("/trapdoorBytes", "0x" + "zz" * 32))
    add("leafIndex", "below-zero", "LEAF_INDEX_OUT_OF_RANGE", replace("/leafIndex", -1))
    add("leafIndex", "at-capacity", "LEAF_INDEX_OUT_OF_RANGE", replace("/leafIndex", 1 << TREE_DEPTH))
    add("leafIndex", "path-relation", "LEAF_INDEX_PATH_MISMATCH", replace("/leafIndex", 25))
    add("pathBits", "short", "PATH_LENGTH_MISMATCH", [{"op": "remove", "path": "/pathBits/19"}])
    add("pathBits", "long", "PATH_LENGTH_MISMATCH", [{"op": "add", "path": "/pathBits/-", "value": 0}])
    add("pathBits", "non-bit", "INVALID_PATH_BIT", replace("/pathBits/0", 2))
    add("pathBits", "leaf-index-relation", "LEAF_INDEX_PATH_MISMATCH", replace("/pathBits/0", 0))
    add("siblingSeeds", "short", "SIBLING_COUNT_MISMATCH", [{"op": "remove", "path": "/siblingSeeds/19"}])
    add("siblingSeeds", "long", "SIBLING_COUNT_MISMATCH", [{"op": "add", "path": "/siblingSeeds/-", "value": "0x" + "00" * 32}])
    add("siblingSeeds", "element-short", "INVALID_SIBLING_SEED_LENGTH", replace("/siblingSeeds/0", "0x" + "00" * 31))
    add("siblingSeeds", "element-long", "INVALID_SIBLING_SEED_LENGTH", replace("/siblingSeeds/0", "0x" + "00" * 33))
    add("siblingSeeds", "element-non-hex", "INVALID_SIBLING_SEED_ENCODING", replace("/siblingSeeds/0", "0x" + "zz" * 32))
    add("recipient", "short", "INVALID_RECIPIENT_LENGTH", replace("/recipient", "0x" + "00" * 19))
    add("recipient", "long", "INVALID_RECIPIENT_LENGTH", replace("/recipient", "0x" + "00" * 21))
    add("recipient", "non-hex", "INVALID_RECIPIENT_ENCODING", replace("/recipient", "0x" + "gg" * 20))
    add("relayer", "short", "INVALID_RELAYER_LENGTH", replace("/relayer", "0x" + "00" * 19))
    add("relayer", "long", "INVALID_RELAYER_LENGTH", replace("/relayer", "0x" + "00" * 21))
    add("relayer", "non-hex", "INVALID_RELAYER_ENCODING", replace("/relayer", "0x" + "gg" * 20))
    add("fee", "below-zero", "FEE_OUT_OF_RANGE", replace("/fee", "-1"))
    add("fee", "above-denomination", "FEE_EXCEEDS_DENOMINATION", replace("/fee", "1000000000000000001"))
    add("fee", "non-decimal", "INVALID_FEE_ENCODING", replace("/fee", "1e3"))
    add("treeDepth/pathBits", "relation-short", "PATH_LENGTH_MISMATCH", replace("/treeDepth", 21))
    add("treeDepth/pathBits", "relation-long", "PATH_LENGTH_MISMATCH", replace("/treeDepth", 19))
    add("treeDepth/siblingSeeds", "relation-short", "SIBLING_COUNT_MISMATCH", replace("/treeDepth", 21))
    add("treeDepth/siblingSeeds", "relation-long", "SIBLING_COUNT_MISMATCH", replace("/treeDepth", 19))
    add("leafIndex/treeDepth", "exclusive-upper-bound", "LEAF_INDEX_OUT_OF_RANGE", replace("/leafIndex", 1 << TREE_DEPTH))
    base_fee = 1 + int.from_bytes(deterministic_bytes(f"{base}/fee", 8), "big") % (10**18)
    assert base_fee > 1
    add("fee/denomination", "strictly-above", "FEE_EXCEEDS_DENOMINATION", replace("/denomination", str(base_fee - 1)))

    return {
        "corpusVersion": CORPUS_VERSION,
        "recordType": "SemanticWithdrawalInvalidMutations",
        "application": "Apply operations as RFC 6902 JSON Patch to the named base case; validate the resulting semantic witness.",
        "negativeOutcomePolicy": "Every listed mutation MUST be rejected with the listed stable error category; no normalization or silent reduction is permitted.",
        "mutations": m,
    }


# Keccak-f[1600] constants for Ethereum Keccak-256 (legacy 0x01 suffix, not NIST SHA3-256).
_ROUND_CONSTANTS = (
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
)
_ROTATION = (
    (0, 36, 3, 41, 18),
    (1, 44, 10, 45, 2),
    (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56),
    (27, 20, 39, 8, 14),
)
_MASK64 = (1 << 64) - 1


def _rol64(value: int, shift: int) -> int:
    return value if shift == 0 else ((value << shift) | (value >> (64 - shift))) & _MASK64


def _keccak_f1600(state: list[int]) -> None:
    for rc in _ROUND_CONSTANTS:
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol64(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] ^= d[x]
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rol64(state[x + 5 * y], _ROTATION[x][y])
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] = b[x + 5 * y] ^ ((~b[(x + 1) % 5 + 5 * y]) & b[(x + 2) % 5 + 5 * y])
        state[0] ^= rc


def ethereum_keccak256(data: bytes) -> str:
    rate = 136
    padded = bytearray(data)
    padded.append(0x01)
    padded.extend(b"\x00" * ((rate - (len(padded) % rate) - 1) % rate))
    padded.append(0x80)
    state = [0] * 25
    for offset in range(0, len(padded), rate):
        block = padded[offset:offset + rate]
        for lane in range(rate // 8):
            state[lane] ^= int.from_bytes(block[lane * 8:lane * 8 + 8], "little")
        _keccak_f1600(state)
    digest = bytearray()
    while len(digest) < 32:
        for lane in range(rate // 8):
            digest.extend(state[lane].to_bytes(8, "little"))
        if len(digest) < 32:
            _keccak_f1600(state)
    return bytes(digest[:32]).hex()


def json_bytes(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def digest_object(data: bytes) -> dict[str, str]:
    return {"sha256": hashlib.sha256(data).hexdigest(), "keccak256": ethereum_keccak256(data)}


def assert_hex(value: str, byte_length: int) -> None:
    assert len(value) == 2 + byte_length * 2 and value.startswith("0x")
    assert value[2:] == value[2:].lower()
    bytes.fromhex(value[2:])


def apply_patch_operations(document: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    result = json.loads(json.dumps(document))
    for operation in operations:
        tokens = [token.replace("~1", "/").replace("~0", "~") for token in operation["path"].split("/")[1:]]
        assert tokens
        parent: Any = result
        for token in tokens[:-1]:
            parent = parent[int(token)] if isinstance(parent, list) else parent[token]
        final = tokens[-1]
        if operation["op"] == "replace":
            if isinstance(parent, list):
                parent[int(final)] = operation["value"]
            else:
                assert final in parent
                parent[final] = operation["value"]
        elif operation["op"] == "remove":
            if isinstance(parent, list):
                parent.pop(int(final))
            else:
                del parent[final]
        elif operation["op"] == "add":
            if isinstance(parent, list):
                if final == "-":
                    parent.append(operation["value"])
                else:
                    parent.insert(int(final), operation["value"])
            else:
                parent[final] = operation["value"]
        else:
            raise AssertionError(f"unsupported mutation operation: {operation['op']}")
    return result


def self_check(semantic: dict[str, Any], invalid: dict[str, Any]) -> dict[str, Any]:
    assert ethereum_keccak256(b"") == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert ethereum_keccak256(b"abc") == "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"
    cases = semantic["cases"]
    assert len(cases) == CASE_COUNT
    ids = [case["caseId"] for case in cases]
    assert len(set(ids)) == CASE_COUNT
    assert sum(case["generationMetadata"]["mode"] == "fully-random" for case in cases) >= FULLY_RANDOM_CASE_COUNT

    all_classes = Counter(item for case in cases for item in case["caseClasses"])
    required_classes = {
        "leaf-index-0", "leaf-index-1", "leaf-index-2", "leaf-index-3",
        "leaf-index-power-minus-one", "leaf-index-power", "leaf-index-power-plus-one",
        "leaf-index-maximum-20-bit", "path-all-zero", "path-all-one",
        "path-alternating-0101", "path-alternating-1010", "repeated-sibling-prefix",
        "low-field-byte-value", "high-field-byte-value", "rejection-sampling-retry-trigger",
        "fee-zero", "fee-equals-denomination", "fee-small-nonzero", "fee-large-nonzero",
        "recipient-many-zero-bytes", "relayer-many-zero-bytes",
        "recipient-few-zero-bytes", "relayer-few-zero-bytes", "fully-random", "path-random",
    }
    assert not required_classes.difference(all_classes)

    by_index = {case["leafIndex"] for case in cases}
    for exponent in range(1, TREE_DEPTH):
        power = 1 << exponent
        assert {power - 1, power, power + 1}.issubset(by_index)
    for case in cases:
        assert case["corpusVersion"] == CORPUS_VERSION
        assert case["treeDepth"] == TREE_DEPTH
        assert 0 <= case["leafIndex"] < 1 << TREE_DEPTH
        assert len(case["pathBits"]) == TREE_DEPTH
        assert case["pathBits"] == path_bits(case["leafIndex"])
        assert len(case["siblingSeeds"]) == TREE_DEPTH
        assert all(bit in (0, 1) for bit in case["pathBits"])
        assert_hex(case["nullifierSecretBytes"], 32)
        assert_hex(case["trapdoorBytes"], 32)
        assert_hex(case["poolAddress"], 20)
        assert_hex(case["recipient"], 20)
        assert_hex(case["relayer"], 20)
        for seed in case["siblingSeeds"]:
            assert_hex(seed, 32)
        assert int(case["chainId"]) > 0
        assert int(case["denomination"]) > 0
        assert 0 <= int(case["fee"]) <= int(case["denomination"])
        classes = set(case["caseClasses"])
        if "fee-zero" in classes:
            assert int(case["fee"]) == 0
        if "fee-equals-denomination" in classes:
            assert case["fee"] == case["denomination"]
        if "fee-small-nonzero" in classes:
            assert int(case["fee"]) == 1
        if "fee-large-nonzero" in classes:
            assert int(case["fee"]) == int(case["denomination"]) - 1
        if "recipient-many-zero-bytes" in classes:
            assert bytes.fromhex(case["recipient"][2:]).count(0) >= 16
        if "relayer-many-zero-bytes" in classes:
            assert bytes.fromhex(case["relayer"][2:]).count(0) >= 16
        if "recipient-few-zero-bytes" in classes:
            assert bytes.fromhex(case["recipient"][2:]).count(0) == 0
        if "relayer-few-zero-bytes" in classes:
            assert bytes.fromhex(case["relayer"][2:]).count(0) == 0
        if "repeated-sibling-prefix" in classes:
            assert len(set(case["siblingSeeds"][:8])) == 1
        if "low-field-byte-value" in classes:
            assert min(int(case["nullifierSecretBytes"][2:], 16), int(case["trapdoorBytes"][2:], 16)) <= 1
        if "high-field-byte-value" in classes:
            assert max(int(case["nullifierSecretBytes"][2:], 16), int(case["trapdoorBytes"][2:], 16)) >= (1 << 256) - 2
        if "rejection-sampling-retry-trigger" in classes:
            trigger = case["generationMetadata"]["rejectionSamplingTrigger"]
            assert len(trigger["draws"]) >= 3
            assert trigger["draws"][0] == "0x" + "ff" * 32
            assert case[trigger["targetField"]] == trigger["draws"][0]

    histories = semantic["treeHistorySequences"]
    assert tuple(item["length"] for item in histories) == TREE_HISTORY_LENGTHS
    for history in histories:
        length = history["length"]
        selected = history["selectedInsertPositions"]
        if length == 0:
            assert selected == []
        else:
            assert selected[0]["insertIndex"] == 0
            assert all(0 <= item["insertIndex"] < length for item in selected)
            maximum_carry = (1 << (length.bit_length() - 1)) - 1
            assert selected[-1]["insertIndex"] == maximum_carry
    semantic_fields = {
        "corpusVersion", "caseId", "chainId", "poolAddress", "denomination",
        "protocolSemanticVersion", "treeDepth", "nullifierSecretBytes", "trapdoorBytes",
        "leafIndex", "pathBits", "siblingSeeds", "recipient", "relayer", "fee",
    }
    mutations = invalid["mutations"]
    mutated_fields = {item["semanticField"] for item in mutations}
    assert semantic_fields.issubset(mutated_fields)
    assert len({item["mutationId"] for item in mutations}) == len(mutations)
    required_relations = {
        "treeDepth/pathBits", "treeDepth/siblingSeeds", "leafIndex/treeDepth", "fee/denomination"
    }
    assert required_relations.issubset(mutated_fields)
    cases_by_id = {case["caseId"]: case for case in cases}
    for item in mutations:
        assert item["expectedOutcome"]["valid"] is False
        base_case = cases_by_id[item["baseCaseId"]]
        assert apply_patch_operations(base_case, item["operations"]) != base_case

    return {
        "counts": {
            "semanticCases": len(cases),
            "fullyRandomCases": all_classes["fully-random"],
            "structuredCases": all_classes["structured"],
            "invalidMutations": len(mutations),
            "treeHistorySequences": len(histories),
            "rejectionSamplingTriggerCases": all_classes["rejection-sampling-retry-trigger"],
        },
        "coverage": {
            "caseClassCounts": dict(sorted(all_classes.items())),
            "invalidMutationFieldCounts": dict(sorted(Counter(item["semanticField"] for item in mutations).items())),
            "powerOfTwoBoundaryExponents": list(range(1, TREE_DEPTH)),
            "treeHistoryLengths": list(TREE_HISTORY_LENGTHS),
        },
    }


def build_outputs(script_path: Path) -> dict[str, bytes]:
    semantic = semantic_document()
    invalid = invalid_document()
    checks = self_check(semantic, invalid)
    first = {"semantic-cases.json": json_bytes(semantic), "invalid-mutations.json": json_bytes(invalid)}
    second = {"semantic-cases.json": json_bytes(semantic_document()), "invalid-mutations.json": json_bytes(invalid_document())}
    assert first == second, "in-process deterministic regeneration failed"

    source = script_path.read_bytes()
    manifest = {
        "corpusVersion": CORPUS_VERSION,
        "recordType": "SemanticCorpusManifest",
        "generator": {
            "path": "research/common-corpus/generators/generate.py",
            "version": GENERATOR_VERSION,
            "runtime": "Python 3 standard library; no locale, clock, OS-randomness, or network inputs",
            "sourceDigests": digest_object(source),
        },
        "reproducibility": {
            "command": "python3 research/common-corpus/generators/generate.py --check",
            "writeCommand": "python3 research/common-corpus/generators/generate.py",
            "seedHex": SEED.hex(),
            "deterministicByteGenerator": "SHA-256(domain || seed || label || uint32be(counter))",
            "jsonSerialization": "UTF-8, sorted keys, two-space indentation, ensure_ascii=true, LF final newline",
        },
        "counts": checks["counts"],
        "coverage": checks["coverage"],
        "artifactDigests": {name: digest_object(data) for name, data in first.items()},
        "candidateMappingResponsibility": MAPPING_RESPONSIBILITY,
        "digestAlgorithms": {
            "sha256": "FIPS 180-4 SHA-256",
            "keccak256": "Ethereum Keccak-256 with legacy domain suffix 0x01; explicitly not NIST SHA3-256",
        },
    }
    return {**first, "corpus-manifest.json": json_bytes(manifest)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify checked-in outputs without modifying them")
    parser.add_argument("--output-dir", type=Path, help="write to this directory instead of the generator's parent")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    output_dir = args.output_dir.resolve() if args.output_dir else script_path.parent.parent
    outputs = build_outputs(script_path)
    if args.check:
        mismatches = []
        for name, expected in outputs.items():
            path = output_dir / name
            if not path.is_file() or path.read_bytes() != expected:
                mismatches.append(name)
        if mismatches:
            parser.error("missing or stale generated outputs: " + ", ".join(mismatches))
        print(f"verified {CASE_COUNT} semantic cases and {len(invalid_document()['mutations'])} invalid mutations")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        (output_dir / name).write_bytes(data)
    print(f"generated {', '.join(outputs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
