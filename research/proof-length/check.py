#!/usr/bin/env python3
"""Deterministically audit v0.3 proof lengths and pruned Merkle frontiers."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CORPUS = ROOT / "research/candidates/v03-baseline/proofs"
CANONICAL = ROOT / "test-vectors/verifier/v3"
MEASURED = ROOT / "research/candidates/v03-baseline/gas/measured-summary.json"

Q = 32
HALF_Q = 16
DEGREE_BITS = 9
LOG_BLOWUP = 4
LOG_HEIGHT = DEGREE_BITS + LOG_BLOWUP
FRI_ROUNDS = 9
RANDOM_CODEWORDS = 4
DIGEST_BYTES = 64
GLOBAL_BYTES = 9_208
FIELD_MODULUS = 2_013_265_921
END = {"A": 0x50414533, "B": 0x50424533}
MAGIC = {"A": b"PQTCPA03", "B": b"PQTCPB03"}
INPUT_DIMS = ((1, 8), (1, 194), (16, 8))


class ParseError(ValueError):
    pass


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, n: int) -> bytes:
        end = self.pos + n
        if n < 0 or end > len(self.data):
            raise ParseError(f"truncated at {self.pos}, need {n} bytes")
        value = self.data[self.pos:end]
        self.pos = end
        return value

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack(">H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack(">I", self.take(4))[0]


def frontier_length(indices: list[int], height: int) -> int:
    """Exact digest count emitted by query.rs::prune_paths."""
    if not indices or any(i < 0 or i >= 1 << height for i in indices):
        raise ParseError("indices outside non-empty Merkle domain")
    nodes = set(indices)
    total = 0
    for _ in range(height):
        groups = {i >> 1 for i in nodes}
        total += sum(((g << 1) in nodes) ^ (((g << 1) | 1) in nodes) for g in groups)
        nodes = groups
    if nodes != {0}:
        raise ParseError("indices do not converge to one root")
    return total


def expected_frontiers(indices: list[int]) -> dict[str, Any]:
    input_frontier = frontier_length(indices, LOG_HEIGHT)
    fri = [
        frontier_length([i >> (round_no + 1) for i in indices], LOG_HEIGHT - round_no - 1)
        for round_no in range(FRI_ROUNDS)
    ]
    return {
        "input_batches": [input_frontier] * 3,
        "fri_rounds": fri,
        "total_digests": 3 * input_frontier + sum(fri),
    }


def collision_profile(indices: list[int]) -> dict[str, list[int]]:
    distinct = [len({i >> shift for i in indices}) for shift in range(LOG_HEIGHT)]
    return {
        "distinct_nodes_by_right_shift_0_through_12": distinct,
        "collisions_among_16_positions_by_right_shift_0_through_12": [
            HALF_Q - count for count in distinct
        ],
    }


def parse_part(data: bytes, kind: str, peer_checkpoint: dict[str, Any] | None = None) -> dict[str, Any]:
    r = Reader(data)
    ledger: dict[str, int] = {
        "format_and_shape_header": 16,
        "parameter_binding": 64,
        "public_statement": 258,
        "proof_id_binding": 32 if kind == "B" else 0,
        "global_digest": 32,
        "commitment_roots": 192,
        "ood_openings": 7_168,
        "masking_openings": 1_216,
        "fri_commitments": 576,
        "grinding_witnesses": 40,
        "final_polynomial": 16,
        "checkpoint_binding_state_challenges": 320,
        "checkpoint_query_indices": 0,
        "half_query_indices": 68,
        "input_rows": 21_120,
        "mmcs_salts": 13_824,
        "frontier_length_prefixes": 48,
        "mmcs_frontier_digests": 0,
        "fri_sibling_values": 2_304,
        "end_marker": 4,
        "other_unknown": 0,
    }

    if r.take(8) != MAGIC[kind] or r.u16() != 3:
        raise ParseError(f"{kind}: magic/version")
    tags = (r.u8(), r.u8(), r.u8(), r.u8(), r.u16())
    if tags != (3, DEGREE_BITS, FRI_ROUNDS, RANDOM_CODEWORDS, Q):
        raise ParseError(f"{kind}: shape header {tags}")
    r.take(64)
    if r.u16() != 64:
        raise ParseError(f"{kind}: public value count")
    public_values = [r.u32() for _ in range(64)]
    if any(v >= FIELD_MODULUS for v in public_values):
        raise ParseError(f"{kind}: non-canonical public value")
    if r.pos != 338:
        raise ParseError(f"{kind}: common header size")

    if kind == "B":
        r.take(32)
    r.take(32)
    global_start = r.pos
    r.take(GLOBAL_BYTES)
    if r.pos - global_start != GLOBAL_BYTES:
        raise ParseError(f"{kind}: global bytes")

    r.take(32 + 32 + 64 + (3 + FRI_ROUNDS) * 16)
    if r.u16() != Q:
        raise ParseError(f"{kind}: checkpoint query count")
    query_indices = [r.u32() for _ in range(Q)]
    if any(i >= 1 << LOG_HEIGHT for i in query_indices):
        raise ParseError(f"{kind}: query index outside {1 << LOG_HEIGHT}")
    unique_count = r.u16()
    unique_indices = [r.u32() for _ in range(unique_count)]
    if unique_indices != sorted(set(query_indices)):
        raise ParseError(f"{kind}: non-canonical unique query set")
    ledger["checkpoint_query_indices"] = 132 + 4 * unique_count
    checkpoint = {"query_indices": query_indices, "unique_indices": unique_indices}
    if peer_checkpoint is not None and checkpoint != peer_checkpoint:
        raise ParseError("A/B checkpoint query mismatch")

    expected_start = 0 if kind == "A" else HALF_Q
    start, half_count = r.u16(), r.u16()
    if (start, half_count) != (expected_start, HALF_Q):
        raise ParseError(f"{kind}: half header")
    half_indices = [r.u32() for _ in range(HALF_Q)]
    if half_indices != query_indices[expected_start:expected_start + HALF_Q]:
        raise ParseError(f"{kind}: half/checkpoint index mismatch")
    expected = expected_frontiers(half_indices)

    observed_inputs: list[int] = []
    for matrices, width in INPUT_DIMS:
        r.take(HALF_Q * matrices * width * 4)
        r.take(HALF_Q * matrices * 8 * 4)
        count = r.u32()
        r.take(count * DIGEST_BYTES)
        observed_inputs.append(count)
    observed_fri: list[int] = []
    for _ in range(FRI_ROUNDS):
        r.take(HALF_Q * 16)
        r.take(HALF_Q * 8 * 4)
        count = r.u32()
        r.take(count * DIGEST_BYTES)
        observed_fri.append(count)
    if observed_inputs != expected["input_batches"] or observed_fri != expected["fri_rounds"]:
        raise ParseError(
            f"{kind}: frontier mismatch observed={observed_inputs, observed_fri} expected={expected}"
        )
    frontier_total = sum(observed_inputs) + sum(observed_fri)
    ledger["mmcs_frontier_digests"] = frontier_total * DIGEST_BYTES
    if r.u32() != END[kind]:
        raise ParseError(f"{kind}: end marker")
    if r.pos != len(data):
        raise ParseError(f"{kind}: trailing {len(data) - r.pos} bytes")
    if sum(ledger.values()) != len(data):
        raise ParseError(f"{kind}: ledger sums to {sum(ledger.values())}, file has {len(data)}")

    zeros = data.count(0)
    return {
        "kind": kind,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "zero_bytes": zeros,
        "nonzero_bytes": len(data) - zeros,
        "standard_intrinsic_if_payload_were_tx_data": 21_000 + 4 * zeros + 16 * (len(data) - zeros),
        "active_eip7623_floor_if_payload_were_tx_data": 21_000 + 10 * zeros + 40 * (len(data) - zeros),
        "uniform_64_floor_if_payload_were_tx_data": 21_000 + 64 * len(data),
        "uniform_96_floor_if_payload_were_tx_data": 21_000 + 96 * len(data),
        "unique_full_queries": unique_count,
        "half_unique_queries": len(set(half_indices)),
        "indices": half_indices,
        "collision_profile": collision_profile(half_indices),
        "frontiers": {
            "input_batches": observed_inputs,
            "fri_rounds": observed_fri,
            "total_digests": frontier_total,
            "bytes": frontier_total * DIGEST_BYTES,
        },
        "ledger": ledger,
        "checkpoint": checkpoint,
    }


def parse_pair(directory: Path, run_id: str) -> dict[str, Any]:
    a_data = (directory / "part-a.pqtc").read_bytes()
    b_data = (directory / "part-b.pqtc").read_bytes()
    a = parse_part(a_data, "A")
    b = parse_part(b_data, "B", a["checkpoint"])
    result: dict[str, Any] = {
        "run_id": run_id,
        "part_a": {k: v for k, v in a.items() if k != "checkpoint"},
        "part_b": {k: v for k, v in b.items() if k != "checkpoint"},
        "raw_proof_bytes": len(a_data) + len(b_data),
        "full_unique_queries": len(a["checkpoint"]["unique_indices"]),
        "cross_part_checkpoint_match": True,
    }
    metadata_path = directory / "proof-metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
        if metadata["part_a"]["bytes"] != len(a_data) or metadata["part_b"]["bytes"] != len(b_data):
            raise ParseError(f"{run_id}: metadata proof length mismatch")
        if metadata["query_indices"] != a["checkpoint"]["query_indices"]:
            raise ParseError(f"{run_id}: metadata query mismatch")
        result["baseline_metadata_native_verified"] = metadata["native_verified"]
        result["baseline_metadata_codec_roundtrip_verified"] = metadata["codec_roundtrip_verified"]
        for kind, key in (("a", "calldata_a"), ("b", "calldata_b")):
            calldata = (directory / f"part-{kind}.calldata").read_bytes()
            if metadata[key]["bytes"] != len(calldata):
                raise ParseError(f"{run_id}: metadata calldata length mismatch")
            z = calldata.count(0)
            result[f"part_{kind}"]["abi_calldata"] = {
                "bytes": len(calldata),
                "zero_bytes": z,
                "nonzero_bytes": len(calldata) - z,
                "standard_intrinsic": 21_000 + 4 * z + 16 * (len(calldata) - z),
                "active_eip7623_floor": 21_000 + 10 * z + 40 * (len(calldata) - z),
                "uniform_64_floor": 21_000 + 64 * len(calldata),
                "uniform_96_floor": 21_000 + 96 * len(calldata),
            }
        gas_log = ROOT / "research/candidates/v03-baseline/gas/evm" / f"{run_id}.trace.log"
        text = gas_log.read_text()
        metrics = {
            key: int(value)
            for key, value in re.findall(r"V03_POOL_([AB]_(?:EXECUTION_GAS|STANDARD_INTRINSIC_GAS|CALLDATA_BYTES)): ([0-9]+)", text)
        }
        for kind in ("a", "b"):
            upper = kind.upper()
            calldata_costs = result[f"part_{kind}"]["abi_calldata"]
            if metrics[f"{upper}_CALLDATA_BYTES"] != calldata_costs["bytes"]:
                raise ParseError(f"{run_id}: trace calldata length mismatch")
            if metrics[f"{upper}_STANDARD_INTRINSIC_GAS"] != calldata_costs["standard_intrinsic"]:
                raise ParseError(f"{run_id}: trace standard intrinsic mismatch")
            execution = metrics[f"{upper}_EXECUTION_GAS"]
            regular_total = execution + calldata_costs["standard_intrinsic"]
            active_total = max(regular_total, calldata_costs["active_eip7623_floor"])
            result[f"part_{kind}"]["measured_pool_transaction"] = {
                "execution_gas": execution,
                "regular_execution_plus_standard_intrinsic": regular_total,
                "active_eip7623_gas_used": active_total,
                "uniform_64_gas_used_same_execution_projection": max(
                    regular_total, calldata_costs["uniform_64_floor"]
                ),
                "uniform_96_gas_used_same_execution_projection": max(
                    regular_total, calldata_costs["uniform_96_floor"]
                ),
                "eip7825_cap": 1 << 24,
                "eip7825_pass": active_total <= 1 << 24,
            }
    return result


def frontier_weights() -> list[int]:
    # A missing sibling at original level l is carried by all three input batches
    # and by FRI rounds r for which r + 1 <= l.
    return [3 + min(FRI_ROUNDS, level) for level in range(LOG_HEIGHT)]


@lru_cache(maxsize=None)
def tree_extreme(height: int, leaves: int, maximize: bool) -> int:
    """Exhaustive binary-tree DP over every feasible child occupancy split."""
    if leaves < 0 or leaves > 1 << height or (height == 0 and leaves != 1):
        raise ValueError("infeasible occupancy")
    if height == 0:
        return 0
    child_capacity = 1 << (height - 1)
    candidates: list[int] = []
    low = max(0, leaves - child_capacity)
    high = min(child_capacity, leaves)
    for left in range(low, high + 1):
        right = leaves - left
        if left == 0:
            child_score = tree_extreme(height - 1, right, maximize)
        elif right == 0:
            child_score = tree_extreme(height - 1, left, maximize)
        else:
            child_score = tree_extreme(height - 1, left, maximize) + tree_extreme(height - 1, right, maximize)
        boundary = frontier_weights()[height - 1] if (left == 0) ^ (right == 0) else 0
        candidates.append(child_score + boundary)
    return (max if maximize else min)(candidates)


def formula_extreme(indices: list[int]) -> int:
    return expected_frontiers(indices)["total_digests"]


def theoretical() -> dict[str, Any]:
    by_unique = []
    for n in range(1, HALF_Q + 1):
        by_unique.append({
            "unique_leaves": n,
            "minimum_frontier_digests_dp": tree_extreme(LOG_HEIGHT, n, False),
            "maximum_frontier_digests_dp": tree_extreme(LOG_HEIGHT, n, True),
        })
    min_digests = min(x["minimum_frontier_digests_dp"] for x in by_unique)
    max_digests = max(x["maximum_frontier_digests_dp"] for x in by_unique)
    # Witnesses independently verify both extrema with the direct codec-equivalent formula.
    min_witness = list(range(HALF_Q))
    max_witness = [block << 9 for block in range(HALF_Q)]
    max_witness_b = [index | 1 for index in max_witness]
    if (
        formula_extreme(min_witness) != min_digests
        or formula_extreme(max_witness) != max_digests
        or formula_extreme(max_witness_b) != max_digests
        or len(set(max_witness + max_witness_b)) != Q
    ):
        raise AssertionError("DP/direct frontier disagreement")

    def proof_part(kind: str, digests: int, full_unique: int) -> dict[str, int]:
        base = 47_398 if kind == "A" else 47_430
        raw = base + 4 * full_unique + DIGEST_BYTES * digests
        abi_base = 292 if kind == "A" else 324
        calldata = abi_base + ((raw + 31) // 32) * 32
        return {
            "raw_proof_bytes": raw,
            "abi_calldata_bytes": calldata,
            "abi_padding_bytes": calldata - abi_base - raw,
            "standard_intrinsic_lower_all_zero": 21_000 + 4 * calldata,
            "standard_intrinsic_upper_all_nonzero": 21_000 + 16 * calldata,
            "active_eip7623_floor_lower_all_zero": 21_000 + 10 * calldata,
            "active_eip7623_floor_upper_all_nonzero": 21_000 + 40 * calldata,
            "uniform_64_floor": 21_000 + 64 * calldata,
            "uniform_96_floor": 21_000 + 96 * calldata,
        }

    return {
        "method": "exact exhaustive dynamic program over all feasible occupied-leaf counts in both children at each of 13 binary-tree levels",
        "frontier_digest_weights_by_original_level": frontier_weights(),
        "by_unique_leaf_count": by_unique,
        "minimum": {
            "half_frontier_digests": min_digests,
            "witness_query_indices": min_witness,
            "joint_half_witnesses": [min_witness, min_witness],
            "collision_profile": collision_profile(min_witness),
            "input_frontier_digests_each": 9,
            "fri_frontier_digests_by_round": [9, 9, 9, 9, 8, 7, 6, 5, 4],
            "part_a": proof_part("A", min_digests, 16),
            "part_b": proof_part("B", min_digests, 16),
            "pair_raw_proof_bytes": proof_part("A", min_digests, 16)["raw_proof_bytes"] + proof_part("B", min_digests, 16)["raw_proof_bytes"],
            "pair_abi_calldata_bytes": proof_part("A", min_digests, 16)["abi_calldata_bytes"] + proof_part("B", min_digests, 16)["abi_calldata_bytes"],
        },
        "maximum": {
            "half_frontier_digests": max_digests,
            "witness_query_indices": max_witness,
            "joint_half_witnesses": [
                max_witness,
                max_witness_b,
            ],
            "collision_profile": collision_profile(max_witness),
            "input_frontier_digests_each": 144,
            "fri_frontier_digests_by_round": [128, 112, 96, 80, 64, 48, 32, 16, 0],
            "part_a": proof_part("A", max_digests, 32),
            "part_b": proof_part("B", max_digests, 32),
            "pair_raw_proof_bytes": proof_part("A", max_digests, 32)["raw_proof_bytes"] + proof_part("B", max_digests, 32)["raw_proof_bytes"],
            "pair_abi_calldata_bytes": proof_part("A", max_digests, 32)["abi_calldata_bytes"] + proof_part("B", max_digests, 32)["abi_calldata_bytes"],
        },
    }


def mutation_checks(sample: Path) -> list[dict[str, Any]]:
    original = sample.read_bytes()
    parsed = parse_part(original, "A")
    cases: list[tuple[str, bytes]] = []
    cases.append(("truncated", original[:-1]))
    cases.append(("trailing_byte", original + b"\x00"))
    magic = bytearray(original); magic[0] ^= 1; cases.append(("magic_flip", bytes(magic)))
    end = bytearray(original); end[-1] ^= 1; cases.append(("end_marker_flip", bytes(end)))
    # First half index begins after header, global digest/data, and variable checkpoint.
    unique = parsed["unique_full_queries"]
    half_index_offset = 338 + 32 + GLOBAL_BYTES + 452 + 4 * unique + 4
    mismatch = bytearray(original)
    mismatch[half_index_offset + 3] ^= 1
    cases.append(("half_checkpoint_index_mismatch", bytes(mismatch)))
    outcomes = []
    for name, mutated in cases:
        rejected = False
        reason = None
        try:
            parse_part(mutated, "A")
        except ParseError as exc:
            rejected = True
            reason = str(exc)
        if not rejected:
            raise AssertionError(f"mutation accepted: {name}")
        outcomes.append({"mutation": name, "rejected": True, "reason": reason})
    return outcomes


def extrema(records: list[dict[str, Any]], path: tuple[str, ...]) -> dict[str, Any]:
    def get(record: dict[str, Any]) -> int:
        value: Any = record
        for key in path:
            value = value[key]
        return int(value)
    values = [(get(record), record["run_id"]) for record in records]
    lo, hi = min(v for v, _ in values), max(v for v, _ in values)
    return {
        "min": lo,
        "min_run_ids": [run_id for value, run_id in values if value == lo],
        "max": hi,
        "max_run_ids": [run_id for value, run_id in values if value == hi],
    }


def source_hashes() -> dict[str, Any]:
    paths = [
        "crates/pqtc-stark/src/codec.rs",
        "crates/pqtc-stark/src/query.rs",
        "crates/pqtc-stark/src/lib.rs",
        "contracts/src/libraries/PQTCProofCodec.sol",
        "contracts/src/verifier/PQTCQueryVerifier.sol",
        "research/candidates/v03-baseline/gas/measured-summary.json",
        "old_reports/ENGINEERING_REPORT.md",
        "test-vectors/verifier/v3/part-a.pqtc",
        "test-vectors/verifier/v3/part-b.pqtc",
        "research/proof-length/check.py",
    ]
    for proof_dir in sorted(p for p in CORPUS.iterdir() if p.is_dir() and p.name.startswith("v03-")):
        for name in ("part-a.pqtc", "part-b.pqtc", "part-a.calldata", "part-b.calldata", "proof-metadata.json"):
            paths.append(str((proof_dir / name).relative_to(ROOT)))
        paths.append(f"research/candidates/v03-baseline/gas/evm/{proof_dir.name}.trace.log")
    records = []
    for relative in paths:
        data = (ROOT / relative).read_bytes()
        records.append({"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return {"schema_version": 1, "hash": "sha256", "sources": records}


def build_results() -> dict[str, Any]:
    directories = sorted(p for p in CORPUS.iterdir() if p.is_dir() and p.name.startswith("v03-"))
    records = [parse_pair(path, path.name) for path in directories]
    if len(records) != 60:
        raise AssertionError(f"expected 60 retained proofs, found {len(records)}")
    canonical = parse_pair(CANONICAL, "engineering-report-canonical")
    canonical["reported_pool_transaction_measurement"] = {
        "source": "old_reports/ENGINEERING_REPORT.md lines 72-88",
        "part_a": {
            "execution_gas": 14_891_070,
            "standard_intrinsic": 1_648_232,
            "modeled_transaction_gas": 16_539_302,
        },
        "part_b": {
            "execution_gas": 12_356_373,
            "standard_intrinsic": 1_749_536,
            "modeled_transaction_gas": 14_105_909,
        },
        "status": "MEASURED_REPORT_VALUE_NOT_RECONSTRUCTED: canonical full ABI calldata is not retained beside the two raw proof fixtures",
    }
    measured = json.loads(MEASURED.read_text())
    if measured["native_pass_count"] != 60 or measured["part_a_eip7825_fail_count"] != 9:
        raise AssertionError("baseline measured-summary acceptance counts changed")
    a_breach_ids = [
        record["run_id"] for record in records
        if not record["part_a"]["measured_pool_transaction"]["eip7825_pass"]
    ]
    b_breach_ids = [
        record["run_id"] for record in records
        if not record["part_b"]["measured_pool_transaction"]["eip7825_pass"]
    ]
    if len(a_breach_ids) != 9 or b_breach_ids:
        raise AssertionError("per-record active EIP-7825 breach set disagrees with baseline summary")
    theory = theoretical()
    observed = {
        "part_a_bytes": extrema(records, ("part_a", "bytes")),
        "part_b_bytes": extrema(records, ("part_b", "bytes")),
        "pair_raw_proof_bytes": extrema(records, ("raw_proof_bytes",)),
        "part_a_frontier_digests": extrema(records, ("part_a", "frontiers", "total_digests")),
        "part_b_frontier_digests": extrema(records, ("part_b", "frontiers", "total_digests")),
        "part_a_abi_calldata_bytes": extrema(records, ("part_a", "abi_calldata", "bytes")),
        "part_b_abi_calldata_bytes": extrema(records, ("part_b", "abi_calldata", "bytes")),
        "part_a_standard_intrinsic": extrema(records, ("part_a", "abi_calldata", "standard_intrinsic")),
        "part_b_standard_intrinsic": extrema(records, ("part_b", "abi_calldata", "standard_intrinsic")),
        "part_a_active_floor": extrema(records, ("part_a", "abi_calldata", "active_eip7623_floor")),
        "part_b_active_floor": extrema(records, ("part_b", "abi_calldata", "active_eip7623_floor")),
        "part_a_uniform_64_floor": extrema(records, ("part_a", "abi_calldata", "uniform_64_floor")),
        "part_b_uniform_64_floor": extrema(records, ("part_b", "abi_calldata", "uniform_64_floor")),
        "part_a_uniform_96_floor": extrema(records, ("part_a", "abi_calldata", "uniform_96_floor")),
        "part_b_uniform_96_floor": extrema(records, ("part_b", "abi_calldata", "uniform_96_floor")),
        "part_a_uniform_64_same_execution_total_projection": extrema(records, ("part_a", "measured_pool_transaction", "uniform_64_gas_used_same_execution_projection")),
        "part_b_uniform_64_same_execution_total_projection": extrema(records, ("part_b", "measured_pool_transaction", "uniform_64_gas_used_same_execution_projection")),
        "part_a_uniform_96_same_execution_total_projection": extrema(records, ("part_a", "measured_pool_transaction", "uniform_96_gas_used_same_execution_projection")),
        "part_b_uniform_96_same_execution_total_projection": extrema(records, ("part_b", "measured_pool_transaction", "uniform_96_gas_used_same_execution_projection")),
    }
    half_records = [record[f"part_{kind}"] for record in records for kind in ("a", "b")]
    collision_summary = []
    for shift in range(LOG_HEIGHT):
        counts = [
            half["collision_profile"]["distinct_nodes_by_right_shift_0_through_12"][shift]
            for half in half_records
        ]
        collision_summary.append({
            "right_shift": shift,
            "minimum_distinct_nodes": min(counts),
            "maximum_distinct_nodes": max(counts),
            "halves_with_at_least_one_collision": sum(count < HALF_Q for count in counts),
        })
    full_query_collision_runs = [
        {"run_id": record["run_id"], "unique_of_32": record["full_unique_queries"]}
        for record in records
        if record["full_unique_queries"] < Q
    ]
    return {
        "schema_version": 1,
        "study": "v0.3-proof-length-frontiers",
        "classification": {
            "measured": "retained proof bytes, calldata byte distributions, and baseline execution/gas summary",
            "exact_derived": "codec ledger, frontier formulas, exhaustive-DP extrema, ABI sizes and byte-only floors",
            "projection": "uniform 64/96 floors and any theoretical-extreme transaction values; no execution was measured at theoretical extrema",
        },
        "geometry": {
            "query_count": Q,
            "split": [HALF_Q, HALF_Q],
            "degree_bits": DEGREE_BITS,
            "log_blowup": LOG_BLOWUP,
            "input_merkle_height": LOG_HEIGHT,
            "input_batches": 3,
            "input_dimensions_matrices_by_width": [[m, w] for m, w in INPUT_DIMS],
            "fri_rounds": FRI_ROUNDS,
            "fri_merkle_heights": list(range(12, 3, -1)),
            "digest_bytes": DIGEST_BYTES,
        },
        "exact_formulas": {
            "unique_nodes": "U_l(S) = |{i >> l : i in S}|",
            "frontier": "F_h(S) = sum_{l=0}^{h-1}(2*U_{l+1}-U_l) = 2 + sum_{l=1}^{h-1}U_l-U_0 for nonempty S subset [0,2^h)",
            "half_frontier": "T(S)=3*F_13(S)+sum_{r=0}^{8}F_{12-r}({i>>(r+1):i in S})",
            "half_frontier_expanded": "T=24-3U_0+2U_1+3U_2+4U_3+5U_4+6U_5+7U_6+8U_7+9U_8+10U_9+12U_10+12U_11+12U_12",
            "part_a_raw_bytes": "47398 + 4*u + 64*T_A",
            "part_b_raw_bytes": "47430 + 4*u + 64*T_B",
            "checkpoint_bytes": "452 + 4*u",
            "half_bytes_including_end": "37368 + 64*T",
            "abi_a_bytes": "292 + 32*ceil(part_a_raw_bytes/32)",
            "abi_b_bytes": "324 + 32*ceil(part_b_raw_bytes/32)",
            "standard_intrinsic": "21000 + 4*z + 16*n",
            "active_eip7623_floor": "21000 + 10*z + 40*n",
            "uniform_64_floor_projection": "21000 + 64*(z+n)",
            "uniform_96_floor_projection": "21000 + 96*(z+n)",
        },
        "retained_corpus": {
            "proof_count": len(records),
            "structural_parse_and_byte_ledger_pass_count": len(records),
            "baseline_metadata_native_verified_count": sum(bool(r["baseline_metadata_native_verified"]) for r in records),
            "baseline_metadata_codec_roundtrip_verified_count": sum(bool(r["baseline_metadata_codec_roundtrip_verified"]) for r in records),
            "observed_extrema": observed,
            "collision_summary_across_120_halves": collision_summary,
            "full_query_collision_runs": full_query_collision_runs,
            "records": records,
        },
        "canonical_report_fixture": canonical,
        "theoretical_extrema": theory,
        "mutation_checks": mutation_checks(CANONICAL / "part-a.pqtc"),
        "measured_execution_evidence": {
            "source": "research/candidates/v03-baseline/gas/measured-summary.json",
            "native_pass_count": measured["native_pass_count"],
            "foundry_ab_pass_count": measured["foundry_ab_pass_count"],
            "part_a_eip7825_fail_count": measured["part_a_eip7825_fail_count"],
            "part_b_eip7825_fail_count": measured["part_b_eip7825_fail_count"],
            "part_a_eip7825_breach_run_ids": a_breach_ids,
            "part_b_eip7825_breach_run_ids": b_breach_ids,
            "recorded_fact": "9/60 active part-A transactions breach the 2^24 specified-gas-limit cap; 0/60 part-B transactions breach it",
            "part_a_total_distribution": measured["distributions"]["a_total"],
            "part_b_total_distribution": measured["distributions"]["b_total"],
        },
        "worst_case_gate": {
            "proof_size": "PASS_EXACT_CODEC_BOUND",
            "max_pair_raw_proof_bytes": theory["maximum"]["pair_raw_proof_bytes"],
            "max_part_raw_proof_bytes": max(theory["maximum"]["part_a"]["raw_proof_bytes"], theory["maximum"]["part_b"]["raw_proof_bytes"]),
            "max_part_abi_calldata_bytes": max(theory["maximum"]["part_a"]["abi_calldata_bytes"], theory["maximum"]["part_b"]["abi_calldata_bytes"]),
            "active_full_transaction": "FAIL_MEASURED_CORPUS: 9/60 part-A transactions exceed EIP-7825",
            "theoretical_frontier_full_transaction": "NOT_EVALUATED: exact maximum byte/floor bounds are derived, but execution gas was not measured for an extremal-frontier proof and is not assumed constant",
            "uniform_64_96": "FLOOR_ONLY_PROJECTION: values include exact ABI byte maxima but exclude execution; they do not establish transaction-gate passage",
        },
        "unknown_components": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write deterministic result and source-hash JSON")
    args = parser.parse_args()
    results = build_results()
    hashes = source_hashes()
    serialized_results = json.dumps(results, indent=2, sort_keys=True) + "\n"
    serialized_hashes = json.dumps(hashes, indent=2, sort_keys=True) + "\n"
    if args.write:
        (OUT / "results.json").write_text(serialized_results)
        (OUT / "source-hashes.json").write_text(serialized_hashes)
    else:
        if (OUT / "results.json").read_text() != serialized_results:
            raise AssertionError("results.json is stale; regenerate with --write")
        if (OUT / "source-hashes.json").read_text() != serialized_hashes:
            raise AssertionError("source-hashes.json is stale; regenerate with --write")
    print(json.dumps({
        "retained_proofs": results["retained_corpus"]["proof_count"],
        "canonical_fixture": True,
        "mutation_checks": len(results["mutation_checks"]),
        "observed": results["retained_corpus"]["observed_extrema"],
        "theoretical_min_frontier": results["theoretical_extrema"]["minimum"]["half_frontier_digests"],
        "theoretical_max_frontier": results["theoretical_extrema"]["maximum"]["half_frontier_digests"],
        "part_a_active_cap_breaches": results["measured_execution_evidence"]["part_a_eip7825_fail_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
