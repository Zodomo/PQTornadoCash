#!/usr/bin/env python3
"""Deterministic SP-13 digest-width calculator and retained-result checker."""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_TARGET_LOG2 = (0, 16, 24, 32, 40, 48, 56, 64)
PROFILE = {
    "solc_version": "0.8.30",
    "evm_version": "prague",
    "optimizer": True,
    "optimizer_runs": 200,
    "via_ir": True,
}
VARIANTS = (
    {
        "id": "keccak-pair-512",
        "width_bits": 512,
        "branch_count": 2,
        "branch_output_bits": 256,
        "construction": "K(0x00 || tag_u8 || payload) || K(0x01 || tag_u8 || payload)",
        "truncation": "NONE; retain all 32 bytes of each branch in branch order",
        "construction_status": "IMPLEMENTED_FROZEN_V03",
        "reduction_status": "OPEN_NO_COMPLETE_TWO_BRANCH_COMPOSITION_OR_QROM_REDUCTION",
        "review_status": "OPEN_NOT_SECURITY_ACCEPTED",
        "verdict": "NO_ADOPTION_BASELINE_ONLY",
    },
    {
        "id": "keccak-pair-trunc-384",
        "width_bits": 384,
        "branch_count": 2,
        "branch_output_bits": 192,
        "construction": "prefix_24(K(0x00 || tag_u8 || payload)) || prefix_24(K(0x01 || tag_u8 || payload))",
        "truncation": "For each 32-byte Keccak output, retain bytes [0:24] (the leftmost/MSB 192 bits), discard bytes [24:32], then concatenate branch 0 before branch 1",
        "construction_status": "SPECIFIED_RESEARCH_PROTOTYPE_ONLY",
        "reduction_status": "OPEN_NO_TWO_BRANCH_TRUNCATION_REDUCTION",
        "review_status": "NOT_REVIEWED_EXTERNAL_ANALYSIS_REQUIRED",
        "verdict": "STOP_PENDING_EXTERNAL_ANALYSIS",
    },
    {
        "id": "keccak-pair-trunc-320",
        "width_bits": 320,
        "branch_count": 2,
        "branch_output_bits": 160,
        "construction": "prefix_20(K(0x00 || tag_u8 || payload)) || prefix_20(K(0x01 || tag_u8 || payload))",
        "truncation": "For each 32-byte Keccak output, retain bytes [0:20] (the leftmost/MSB 160 bits), discard bytes [20:32], then concatenate branch 0 before branch 1",
        "construction_status": "SPECIFIED_RESEARCH_PROTOTYPE_ONLY",
        "reduction_status": "OPEN_NO_TWO_BRANCH_TRUNCATION_REDUCTION",
        "review_status": "NOT_REVIEWED_EXTERNAL_ANALYSIS_REQUIRED",
        "verdict": "STOP_PENDING_EXTERNAL_ANALYSIS",
    },
    {
        "id": "single-keccak-256-lower-bound",
        "width_bits": 256,
        "branch_count": 1,
        "branch_output_bits": 256,
        "construction": "K(0x00 || tag_u8 || payload)",
        "truncation": "NONE; retain all 32 bytes of branch 0; branch 1 is not evaluated",
        "construction_status": "IMPLEMENTED_RESEARCH_NEGATIVE_CONTROL",
        "reduction_status": "NOT_APPLICABLE_TO_REJECTION_GENERIC_BHT_BOUND_ALREADY_FAILS",
        "review_status": "NOT_SUBMITTED_NONQUALIFYING_LOWER_BOUND",
        "verdict": "REJECT_NONQUALIFYING_LOWER_BOUND",
    },
)


def fraction_record(value: Fraction) -> dict[str, Any]:
    text = str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    return {
        "log2_queries_projection": text,
        "floor_log2_queries": value.numerator // value.denominator,
        "measurement_class": "GENERIC_ATTACK_MODEL_PROJECTION_NOT_A_SECURITY_PROOF",
    }


def security_projection(bits: int, target_log2: int) -> dict[str, Any]:
    # The multi-instance BHT heuristic solves M q^3 / 2^n ~= 1. Grover search
    # against M target outputs solves M q^2 / 2^n ~= 1. Both are projections.
    bht = max(Fraction(0), Fraction(bits - target_log2, 3))
    grover = max(Fraction(0), Fraction(bits - target_log2, 2))
    invocations = 1 << target_log2
    return {
        "target_digest_outputs": invocations,
        "target_digest_outputs_log2": target_log2,
        "generic_bht_collision": fraction_record(bht),
        "generic_grover_preimage_or_second_preimage": fraction_record(grover),
        "classical_accidental_collision_union_bound": {
            "numerator": invocations * (invocations - 1),
            "denominator": 1 << (bits + 1),
            "formula": "M*(M-1)/2^(n+1)",
            "measurement_class": "EXACT_RATIONAL_UNION_BOUND_NOT_FULL_PROTOCOL",
        },
    }


def read_gas() -> tuple[str, dict[str, Any] | None]:
    path = ROOT / "outputs" / "foundry-gas.json"
    if not path.exists():
        return "NOT_MEASURED_RUN_CANONICAL_FOUNDRY_HARNESS", None
    gas = json.loads(path.read_text())
    if gas.get("schema") != "pqtc-sp13-foundry-gas-v1":
        raise ValueError("unexpected Foundry gas schema")
    if gas.get("compiler_profile") != PROFILE:
        raise ValueError("Foundry output does not bind the canonical compiler profile")
    expected = {v["id"] for v in VARIANTS}
    rows = gas.get("variants")
    if not isinstance(rows, list) or {row.get("id") for row in rows} != expected:
        raise ValueError("Foundry output does not contain exactly the four variants")
    integer_fields = ("hash_only_call_gas", "storage_only_cold_call_gas", "hash_and_storage_cold_call_gas")
    for row in rows:
        if row.get("measurement_scope") != "SOLIDITY_MICROBENCHMARK_NOT_FULL_PROTOCOL":
            raise ValueError("gas row is not explicitly scoped as a microbenchmark")
        for field in integer_fields:
            if not isinstance(row.get(field), int) or row[field] <= 0:
                raise ValueError(f"invalid {field} for {row.get('id')}")
    return "MEASURED_CANONICAL_FOUNDRY_MICROBENCHMARK", gas


def build(target_logs: tuple[int, ...]) -> dict[str, Any]:
    gas_status, gas = read_gas()
    gas_by_id = {} if gas is None else {row["id"]: row for row in gas["variants"]}
    rows = []
    for variant in VARIANTS:
        bits = variant["width_bits"]
        digest_bytes = bits // 8
        branch_count = variant["branch_count"]
        framed_bytes = 2 + 2 * digest_bytes
        framed_words = (framed_bytes + 31) // 32
        storage_slots = (digest_bytes + 31) // 32
        rows.append({
            **variant,
            "digest_bytes": digest_bytes,
            "depth_20_authentication_path": {
                "sibling_count": 20,
                "sibling_digest_bytes": digest_bytes,
                "path_bytes": 20 * digest_bytes,
                "direction_bits_bytes_if_separately_byte_aligned": 3,
                "path_bytes_including_separate_direction_bitmap": 20 * digest_bytes + 3,
                "measurement_scope": "EXACT_WIDTH_COMPONENT_NOT_FULL_PROTOCOL",
                "excludes": ["leaf", "root", "index", "length prefixes", "ABI padding", "proof framing"],
            },
            "canonical_binary_node_payload": {
                "encoding": "left_digest_bytes || right_digest_bytes, with no length prefix or padding",
                "payload_bytes": 2 * digest_bytes,
                "framed_keccak_input_bytes_per_branch": framed_bytes,
                "keccak_invocations_per_node": branch_count,
                "measurement_scope": "EXACT_HASH_MICROBENCHMARK_INPUT_NOT_FULL_PROTOCOL",
            },
            "optimal_fixed_storage": {
                "storage_slots": storage_slots,
                "allocated_bytes": storage_slots * 32,
                "unused_bytes": storage_slots * 32 - digest_bytes,
                "measurement_scope": "EXACT_STORAGE_LAYOUT_COMPONENT_NOT_FULL_PROTOCOL",
            },
            "prague_opcode_gas_components": {
                "keccak256_words_per_branch": framed_words,
                "keccak256_gas_per_branch": 30 + 6 * framed_words,
                "keccak256_gas_per_digest": branch_count * (30 + 6 * framed_words),
                "cold_zero_to_nonzero_sstore_gas_per_slot": 22100,
                "cold_zero_to_nonzero_sstore_gas_per_digest": storage_slots * 22100,
                "measurement_scope": "EXACT_EVM_OPCODE_COMPONENT_MICROBENCHMARK_NOT_FULL_PROTOCOL",
                "excludes": ["memory expansion", "copying", "masking", "ABI", "CALL", "transaction intrinsic gas", "calldata gas", "surrounding protocol"],
            },
            "gas_microbenchmark": gas_by_id.get(variant["id"], {
                "status": gas_status,
                "hash_only_call_gas": None,
                "storage_only_cold_call_gas": None,
                "hash_and_storage_cold_call_gas": None,
                "measurement_scope": "SOLIDITY_MICROBENCHMARK_NOT_FULL_PROTOCOL",
            }),
            "full_protocol_gas": {
                "value": None,
                "status": "NOT_EVALUATED_NO_FULL_PROTOCOL_VARIANT_IMPLEMENTATION",
                "measurement_scope": "FULL_PROTOCOL",
                "microbenchmark_sum_claim": False,
            },
            "security": {
                "target_quantum_bits": 100,
                "single_target": security_projection(bits, 0),
                "protocol_lifetime_sensitivity": [
                    {
                        **security_projection(bits, target_log2),
                        "underlying_keccak_invocations": (1 << target_log2) * branch_count,
                    }
                    for target_log2 in target_logs
                ],
                "model_scope": "Generic random-oracle projections only; excludes structural, composition, correlated-branch, domain-reuse, QROM Fiat-Shamir, and protocol reductions",
            },
        })
    return {
        "schema": "pqtc-sp13-digest-width-results-v1",
        "study": "cross-cutting-section-13-digest-width",
        "decision": "NO_ADOPTION",
        "decision_reason": "No variant has both an accepted complete security argument and the required independent external review; 320/384 remain stopped and 256 fails the 100-bit generic quantum-collision target even at one target.",
        "canonical_encoding": {
            "tag": "exactly one unsigned byte",
            "branch_frame": "branch_u8 || tag_u8 || payload",
            "branch_values": [0, 1],
            "payload": "exact caller-supplied bytes; no implicit ABI encoding, length, delimiter, or padding is hashed",
            "digest_serialization": "concatenate retained branch bytes in ascending branch order",
        },
        "compiler_profile": PROFILE,
        "gas_measurement_status": gas_status,
        "all_costs_policy": "Byte/storage and Prague opcode-component counts are exact integers. Solidity call gas is an exact gasleft delta only when retained Foundry output is present. Security work factors are explicitly labeled projections.",
        "variants": rows,
    }


def validate(result: dict[str, Any], target_logs: tuple[int, ...]) -> None:
    if result["decision"] != "NO_ADOPTION" or len(result["variants"]) != 4:
        raise ValueError("decision or matrix cardinality changed")
    expected_paths = {512: 1280, 384: 960, 320: 800, 256: 640}
    for row in result["variants"]:
        if row["depth_20_authentication_path"]["path_bytes"] != expected_paths[row["width_bits"]]:
            raise ValueError("depth-20 path arithmetic mismatch")
        if len(row["security"]["protocol_lifetime_sensitivity"]) != len(target_logs):
            raise ValueError("lifetime sensitivity row count mismatch")
    stopped = {row["width_bits"]: row["verdict"] for row in result["variants"]}
    if stopped[384] != "STOP_PENDING_EXTERNAL_ANALYSIS" or stopped[320] != "STOP_PENDING_EXTERNAL_ANALYSIS":
        raise ValueError("320/384 stop verdict must not change")
    if result["variants"][3]["security"]["single_target"]["generic_bht_collision"]["floor_log2_queries"] >= 100:
        raise ValueError("256-bit lower bound unexpectedly qualifies")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-log2", action="append", type=int, dest="target_logs")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    target_logs = tuple(sorted(set(args.target_logs or DEFAULT_TARGET_LOG2)))
    if not target_logs or target_logs[0] < 0 or target_logs[-1] > 128:
        raise SystemExit("target log2 values must be in [0,128]")
    result = build(target_logs)
    validate(result, target_logs)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.write:
        (ROOT / "results.json").write_text(encoded)
    elif (ROOT / "results.json").exists() and target_logs == DEFAULT_TARGET_LOG2:
        retained = (ROOT / "results.json").read_text()
        if retained != encoded:
            raise SystemExit("retained results.json is stale; run with --write")
    print(hashlib.sha256(encoded.encode()).hexdigest())


if __name__ == "__main__":
    main()
