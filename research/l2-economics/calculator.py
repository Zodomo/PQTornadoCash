#!/usr/bin/env python3
"""Calculate one deterministic SP-71 offline L2 projection as JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from l2_model import NETWORKS, byte_gas, keccak256, op_projection, payload, signed_eip1559, unavailable_projection

HERE = Path(__file__).resolve().parent


def merged_scenario(scenario_id: str) -> dict[str, int | str]:
    document = json.loads((HERE / "scenarios.json").read_text())
    selected = next((item for item in document["scenarios"] if item["id"] == scenario_id), None)
    if selected is None:
        raise ValueError(f"unknown scenario: {scenario_id}")
    return {**document["shared_synthetic_parameters"], **selected}


def calculate(network: str, family: str, kib: int, scenario_id: str) -> dict[str, object]:
    network_config = NETWORKS[network]
    data = payload(family, kib * 1024)
    gas = byte_gas(data)
    tx = signed_eip1559(network_config["chain_id"], network_config["tx_gas_limit"], data)
    scenario = merged_scenario(scenario_id)
    fee = op_projection(tx, gas["no_op_calldata_gas"], scenario) if network == "op-mainnet" else unavailable_projection(network, gas["no_op_calldata_gas"], scenario)
    return {
        "classification": "PROJECTION",
        "price_provenance": "SYNTHETIC_OFFLINE_INPUT_NOT_LIVE",
        "network": network,
        "payload_family": family,
        "payload_kib": kib,
        "signed_tx_bytes": len(tx),
        "signed_tx_keccak256": "0x" + keccak256(tx).hex(),
        "size_limit_bytes": network_config["signed_size_limit"],
        "admission_projection": "PROJECTED_SIZE_ADMISSIBLE" if len(tx) <= network_config["signed_size_limit"] else "PROJECTED_SIZE_REJECTED",
        **gas,
        "scenario": scenario,
        "fees": fee,
        "pqtc_receipt_evidence": "NOT_EVALUATED_NO_LOCAL_VERIFIER_RECEIPT",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", choices=sorted(NETWORKS), required=True)
    parser.add_argument("--family", choices=("seeded-incompressible", "repeated"), required=True)
    parser.add_argument("--kib", type=int, required=True)
    parser.add_argument("--scenario-id", default="l1-10gwei-blob-10wei")
    args = parser.parse_args()
    print(json.dumps(calculate(args.network, args.family, args.kib, args.scenario_id), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
