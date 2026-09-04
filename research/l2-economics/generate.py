#!/usr/bin/env python3
"""Reproduce every retained SP-71 L2 economics result from offline inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from l2_model import (
    FAMILIES,
    NETWORKS,
    PAYLOAD_KIB,
    byte_gas,
    keccak256,
    op_projection,
    payload,
    research_address,
    signed_eip1559,
    unavailable_projection,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RESULTS = HERE / "results"
BASELINE = REPO / "research" / "summaries" / "v03-distribution.csv"


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def csv_text(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def scenarios() -> list[dict[str, Any]]:
    document = json.loads((HERE / "scenarios.json").read_text())
    shared = document["shared_synthetic_parameters"]
    return [{**shared, **entry} for entry in document["scenarios"]]


def transaction_rows() -> tuple[list[dict[str, Any]], dict[tuple[str, str, int], tuple[bytes, dict[str, int]]]]:
    rows: list[dict[str, Any]] = []
    raw: dict[tuple[str, str, int], tuple[bytes, dict[str, int]]] = {}
    for network, config in NETWORKS.items():
        for family in FAMILIES:
            for kib in PAYLOAD_KIB:
                data = payload(family, kib * 1024)
                gas = byte_gas(data)
                tx = signed_eip1559(config["chain_id"], config["tx_gas_limit"], data)
                raw[(network, family, kib)] = (tx, gas)
                rows.append({
                    "network": network,
                    "chain_id": config["chain_id"],
                    "payload_family": family,
                    "payload_kib": kib,
                    "calldata_bytes": len(data),
                    "payload_sha256": hashlib.sha256(data).hexdigest(),
                    "payload_keccak256": "0x" + keccak256(data).hex(),
                    **gas,
                    "tx_type": "EIP-1559_TYPE_2",
                    "tx_nonce": 7,
                    "tx_gas_limit": config["tx_gas_limit"],
                    "signed_tx_bytes": len(tx),
                    "signed_tx_keccak256": "0x" + keccak256(tx).hex(),
                    "ordinary_sequencer_size_limit_bytes": config["signed_size_limit"],
                    "admission_projection": "PROJECTED_SIZE_ADMISSIBLE" if len(tx) <= config["signed_size_limit"] else "PROJECTED_SIZE_REJECTED",
                    "gas_limit_feasibility": "PROJECTED_NO_OP_GAS_LIMIT_FEASIBLE" if gas["no_op_calldata_gas"] <= config["tx_gas_limit"] else "PROJECTED_NO_OP_GAS_LIMIT_INFEASIBLE",
                    "verifier_execution": "NOT_EVALUATED_NO_LOCAL_VERIFIER_RECEIPT",
                })
    return rows, raw


def fee_rows(raw: dict[tuple[str, str, int], tuple[bytes, dict[str, int]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (network, family, kib), (tx, gas) in raw.items():
        for scenario in scenarios():
            projection = op_projection(tx, gas["no_op_calldata_gas"], scenario) if network == "op-mainnet" else unavailable_projection(network, gas["no_op_calldata_gas"], scenario)
            rows.append({
                "classification": "PROJECTION",
                "price_provenance": "SYNTHETIC_OFFLINE_INPUT_NOT_LIVE",
                "network": network,
                "payload_family": family,
                "payload_kib": kib,
                "scenario_id": scenario["id"],
                "l1_base_fee_wei": scenario["l1_base_fee_wei"],
                "l1_blob_base_fee_wei": scenario["l1_blob_base_fee_wei"],
                "l2_base_fee_wei": scenario["l2_base_fee_wei"],
                "op_l1_base_fee_scalar": scenario["op_l1_base_fee_scalar"],
                "op_l1_blob_fee_scalar": scenario["op_l1_blob_fee_scalar"],
                "op_da_footprint_gas_scalar": scenario["op_da_footprint_gas_scalar"],
                "arbitrum_price_per_unit_wei": scenario["arbitrum_price_per_unit_wei"],
                "scroll_exec_scalar": scenario["scroll_exec_scalar"],
                "scroll_blob_scalar": scenario["scroll_blob_scalar"],
                **projection,
            })
    return rows


def baseline_rows() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    with BASELINE.open(newline="") as handle:
        for source in csv.DictReader(handle):
            calldata = int(source["abi_calldata_bytes"])
            zero = int(source["zero_bytes"])
            nonzero = int(source["nonzero_bytes"])
            floor = 21_000 + 10 * (zero + 4 * nonzero)
            for network, config in NETWORKS.items():
                for implementation, column in (("evm-a", "evm_a_total_gas"), ("evm-b", "evm_b_total_gas")):
                    measured_total = int(source[column])
                    output.append({
                        "hardware_profile": "H1_LOCAL_APPLE_M4_MAX_MEASURED_SOURCE",
                        "run_id": source["run_id"],
                        "kind": source["kind"],
                        "case_id": source["case_id"],
                        "network": network,
                        "implementation": implementation,
                        "abi_calldata_bytes": calldata,
                        "calldata_zero_bytes": zero,
                        "calldata_nonzero_bytes": nonzero,
                        "eip7623_floor_gas": floor,
                        "source_measured_total_gas": measured_total,
                        "ordinary_sequencer_size_limit_bytes": config["signed_size_limit"],
                        "size_feasibility": "REJECTED_SOURCE_PROVEN_CALLDATA_ALONE_EXCEEDS_SIGNED_TX_LIMIT" if calldata > config["signed_size_limit"] else "NOT_EVALUATED_EXACT_BASELINE_SIGNED_TX_UNAVAILABLE",
                        "tx_gas_limit_model": config["tx_gas_limit"],
                        "gas_limit_feasibility": "PROJECTED_FEASIBLE_FROM_SOURCE_TOTAL" if measured_total <= config["tx_gas_limit"] else "PROJECTED_INFEASIBLE_FROM_SOURCE_TOTAL",
                        "combined_ordinary_admission_projection": "PROJECTED_REJECTED_SIZE",
                        "pqtc_l2_receipt_evidence": "NOT_EVALUATED_NO_SELECTED_L2_VERIFIER_RECEIPT",
                    })
    return output


def build_artifacts() -> dict[str, str]:
    transactions, raw = transaction_rows()
    fees = fee_rows(raw)
    baseline = baseline_rows()
    tx_fields = list(transactions[0])
    fee_fields = list(fees[0])
    baseline_fields = list(baseline[0])
    summary = {
        "schema": "pqtc-sp71-l2-results-v1",
        "snapshot_date": "2026-09-04",
        "generator": "research/l2-economics/generate.py",
        "package_status": "INCOMPLETE_REQUIRED_NETWORK_MEASUREMENTS",
        "admission_sweep_gate": "FAIL",
        "SP71_product_gate": "NOT_EVALUATED_NOT_PASSED",
        "SP71_product_gate_blockers": [
            "NO_EXACT_SELECTED_L2_VERIFIER_RECEIPTS",
            "NO_LIVE_COST_RATIO",
            "NO_APPLICATION_SEMANTICS_EVIDENCE",
        ],
        "required_network_measurements": {
            "ethereum_local_testnet": "NOT_EVALUATED_EXACT_VERIFIER_UNAVAILABLE",
            "op_family_testnet": "NOT_EVALUATED_EXACT_VERIFIER_UNAVAILABLE",
            "arbitrum_family_testnet": "NOT_EVALUATED_EXACT_VERIFIER_UNAVAILABLE",
        },
        "research_signer_address": research_address(),
        "research_private_key_classification": "PUBLIC_ANVIL_HARDHAT_TEST_KEY_NEVER_PRODUCTION",
        "payload_transaction_rows": len(transactions),
        "fee_projection_rows": len(fees),
        "baseline_feasibility_rows": len(baseline),
        "ordinary_210_kib_verdict": {network: "PROJECTED_SIZE_REJECTED" for network in NETWORKS},
        "ordinary_80_kib_verdict": {network: "PROJECTED_SIZE_ADMISSIBLE" for network in NETWORKS},
        "pqtc_receipt_evidence": "NOT_EVALUATED_NO_SELECTED_L2_VERIFIER_RECEIPT",
        "local_admission_receipts": "NOT_EVALUATED_INDEPENDENT_REPRODUCTION_TASK",
        "fee_labels": "PROJECTION_USING_SYNTHETIC_INPUTS_NOT_LIVE",
        "compression": {
            "op_fastlz": "EVALUATED_PINNED_SOURCE_PORT",
            "arbitrum_brotli_level_1": "NOT_EVALUATED_MISSING_PINNED_NITRO_EXECUTABLE",
            "scroll_feynman_zstd": "NOT_EVALUATED_MISSING_PINNED_DA_CODEC_V8_EXECUTABLE",
        },
        "hardware_profiles": {
            "H1": "MEASURED_LOCAL_APPLE_M4_MAX_BASELINE_DISTRIBUTION",
            "H2": "NOT_EVALUATED_CI_8_CORE_32_GIB_PROFILE_UNAVAILABLE",
            "H3": "NOT_EVALUATED_COMMODITY_16_CORE_64_GIB_PROFILE_UNAVAILABLE",
        },
    }
    return {
        "transactions.csv": csv_text(tx_fields, transactions),
        "fee-projections.csv": csv_text(fee_fields, fees),
        "baseline-feasibility.csv": csv_text(baseline_fields, baseline),
        "summary.json": canonical_json(summary),
    }


def write_or_check(check: bool) -> None:
    artifacts = build_artifacts()
    if check:
        mismatches = [name for name, content in artifacts.items() if not (RESULTS / name).exists() or (RESULTS / name).read_text() != content]
        if mismatches:
            raise SystemExit("generated artifact mismatch: " + ", ".join(mismatches))
        return
    RESULTS.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        (RESULTS / name).write_text(content)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail unless retained results are byte-for-byte reproducible")
    args = parser.parse_args()
    write_or_check(args.check)


if __name__ == "__main__":
    main()
