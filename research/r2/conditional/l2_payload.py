#!/usr/bin/env python3
"""Offline exact proof transport diagnostics. Never sends a transaction."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def diagnose(payloads=None):
    pins = json.loads((HERE / "inputs.json").read_text())
    for name, expected in pins["files"].items():
        if digest((ROOT / name).read_bytes()) != expected:
            raise ValueError(f"frozen historical input changed: {name}")
    sys.path.insert(0, str(ROOT / "research/l2-economics"))
    import l2_model as model
    source = ROOT / "research/l2-economics"
    rules = json.loads((source / "matrix.json").read_text())
    scenarios = json.loads((source / "scenarios.json").read_text())
    if payloads is not None:
        return diagnose_native_payloads(payloads, model, rules, scenarios, pins, source)
    folder = ROOT / "research/candidates/v03-baseline/proofs" / pins["run_id"]
    metadata = json.loads((folder / "proof-metadata.json").read_text())
    with (ROOT / "research/summaries/v03-distribution.csv").open() as f:
        gas_row = next(row for row in csv.DictReader(f) if row["run_id"] == pins["run_id"])
    parts = []
    for index, part in enumerate(("a", "b")):
        proof = (folder / f"part-{part}.pqtc").read_bytes()
        calldata = (folder / f"part-{part}.calldata").read_bytes()
        words = 8 + index
        offset = int.from_bytes(calldata[4+(words-1)*32:4+words*32], "big")
        length = int.from_bytes(calldata[4+offset:36+offset], "big")
        if offset != words*32 or length != len(proof) or calldata[36+offset:36+offset+length] != proof:
            raise ValueError(f"part {part}: exact retained ABI does not embed retained proof")
        if len(calldata) != 36+offset+((length+31)//32)*32 or any(calldata[36+offset+length:]):
            raise ValueError(f"part {part}: noncanonical ABI padding")
        if model.keccak256(calldata).hex() != metadata[f"calldata_{part}"]["keccak256"]:
            raise ValueError(f"part {part}: metadata mismatch")
        parts.append({"part": part, "raw_proof_bytes": len(proof), "proof_sha256": digest(proof),
                      "abi_calldata_bytes": len(calldata), "abi_sha256": digest(calldata),
                      "abi_selector": calldata[:4].hex(), "data": calldata,
                      "historical_ethereum_total_gas": int(gas_row[f"evm_{part}_total_gas"])})
    rows = []
    for network, config in model.NETWORKS.items():
        network_rows = []
        for index, part in enumerate(parts):
            data = part["data"]
            # The retained signer has a fixed public test key and no network API.
            # Adjacent nonces model an ordered two-call sequence, not replacements.
            model.NONCE = 7 + index
            tx = model.signed_eip1559(config["chain_id"], config["tx_gas_limit"], data)
            gas = model.byte_gas(data)
            fees = []
            for entry in scenarios["scenarios"]:
                scenario = {**scenarios["shared_synthetic_parameters"], **entry}
                projected = (model.op_projection(tx, gas["no_op_calldata_gas"], scenario)
                             if network == "op-mainnet" else model.unavailable_projection(network, gas["no_op_calldata_gas"], scenario))
                fees.append({"scenario_id": entry["id"], "measurement_status": "UNCALIBRATED_PROJECTION",
                             "scope": "no-code calldata sink, NOT verifier user cost", **projected})
            network_rows.append({**{k:v for k,v in part.items() if k != "data"}, **gas,
                "nonce": model.NONCE, "signed_tx_bytes": len(tx), "signed_tx_sha256": digest(tx),
                "signed_envelope_status": "MEASURED", "tx_gas_limit": config["tx_gas_limit"],
                "source_size_admissible": len(tx) <= config["signed_size_limit"],
                "source_no_op_gas_fits": gas["no_op_calldata_gas"] <= config["tx_gas_limit"],
                "historical_ethereum_gas_fits_chain_scenario": part["historical_ethereum_total_gas"] <= config["tx_gas_limit"],
                "configured_node_admission": None, "authorized_receipt": None, "exact_l2_verifier_gas": None,
                "fee_scenarios": fees})
        combined = b"".join(part["data"] for part in parts)
        model.NONCE = 7
        combined_tx = model.signed_eip1559(config["chain_id"], config["tx_gas_limit"], combined)
        combined_fees = []
        for index, entry in enumerate(scenarios["scenarios"]):
            scenario = {**scenarios["shared_synthetic_parameters"], **entry}
            cfee = (model.op_projection(combined_tx, model.byte_gas(combined)["no_op_calldata_gas"], scenario)
                    if network == "op-mainnet" else model.unavailable_projection(network, model.byte_gas(combined)["no_op_calldata_gas"], scenario))
            split = [r["fee_scenarios"][index]["total_fee_wei"] for r in network_rows]
            combined_fees.append({"scenario_id": entry["id"], "split_no_op_total_fee_wei": sum(split) if all(v is not None for v in split) else None,
                                  "combined_transport_only_no_op_total_fee_wei": cfee["total_fee_wei"]})
        rows.append({"network": network, "source_rules": rules["networks"][network], "parts": network_rows,
            "split_totals": {"raw_proof_bytes": sum(p["raw_proof_bytes"] for p in parts),
                "abi_calldata_bytes": len(combined), "signed_tx_bytes_sum": sum(r["signed_tx_bytes"] for r in network_rows),
                "both_transactions_source_size_admissible": all(r["source_size_admissible"] for r in network_rows),
                "both_historical_gas_totals_fit_per_tx_scenario": all(r["historical_ethereum_gas_fits_chain_scenario"] for r in network_rows),
                "historical_ethereum_total_gas_sum": sum(p["historical_ethereum_total_gas"] for p in parts),
                "same_block_admission": None},
            "combined_transport_control": {"classification": "CONCATENATED_EXACT_A_B_CALLDATA_NOT_AN_EXECUTABLE_COMBINED_ABI",
                "abi_bytes_concatenated": len(combined), "signed_tx_bytes": len(combined_tx),
                "signed_tx_sha256": digest(combined_tx), "source_size_admissible": len(combined_tx) <= config["signed_size_limit"],
                "complete_combined_verifier_gas": None}, "fee_comparison": combined_fees})
    return {"schema": "pqtc.r2.conditional-l2.v1", "origin": pins["origin"], "run_id": pins["run_id"],
        "inputs": pins, "chain_source_pins": json.loads((source / "sources.json").read_text()),
        "synthetic_fee_inputs": scenarios, "measurement_status": "MEASURED",
        "measurement_scope": "local bytes and deterministic signatures only; source admission and all fees are projections",
        "signer": {"address": model.research_address(), "key": "universally public Anvil account 0, never funded",
                   "destination": model.RESEARCH_TO.hex(), "value_wei": 0, "priority_cap_wei": model.MAX_PRIORITY_FEE_PER_GAS,
                   "fee_cap_wei": model.MAX_FEE_PER_GAS, "access_list": [], "network_calls": 0},
        "caveats": ["Historical Ethereum gas is not an L2 receipt or L2 gas measurement.",
                    "Two separate transaction size tests; their total is never compared to one transaction cap.",
                    "Two calls incur two intrinsic floors and two fee rounding/compression operations.",
                    "Scroll same-block aggregate payload limit is separate; sequential blocks are allowed in this diagnostic.",
                    "Raw signed bytes are not persisted and no RPC/broadcast facility exists.",
                    "Missing pinned Nitro/Scroll compression leaves fee totals null; no substitute compressor.",
                    "Size admission alone does not establish affordable/private/sound withdrawals."], "networks": rows}


def diagnose_native_payloads(manifest, model, rules, scenarios, pins, source):
    entries = manifest["payloads"]
    if not entries:
        raise ValueError("at least one exact native payload is required")
    payloads = []
    for entry in entries:
        path = (ROOT / entry["artifact"]).resolve()
        if not path.is_relative_to(ROOT / "research") or not path.is_file():
            raise ValueError("payload must be an explicit research artifact")
        if entry["codec"] not in ("postcard-1.1.3-full-native-proof", "research-canonical-raw"):
            raise ValueError("only declared native transport codecs are supported; this is not an ABI adapter")
        data = path.read_bytes()
        if not data or digest(data) != entry["sha256"]:
            raise ValueError(f"empty or changed exact payload: {entry['artifact']}")
        networks = []
        for network, config in model.NETWORKS.items():
            # Independent single-payload alternatives, not a split transaction sequence.
            model.NONCE = 7
            tx = model.signed_eip1559(config["chain_id"], config["tx_gas_limit"], data)
            gas = model.byte_gas(data)
            fees = []
            for item in scenarios["scenarios"]:
                scenario = {**scenarios["shared_synthetic_parameters"], **item}
                projected = (model.op_projection(tx, gas["no_op_calldata_gas"], scenario)
                             if network == "op-mainnet" else model.unavailable_projection(network, gas["no_op_calldata_gas"], scenario))
                fees.append({"scenario_id": item["id"], "measurement_status": "UNCALIBRATED_PROJECTION",
                             "scope": "native proof as raw calldata to no-code sink, NOT an EVM verifier call", **projected})
            networks.append({"network": network, "source_rules": rules["networks"][network], **gas,
                "raw_transport_calldata_bytes": len(data), "abi_calldata_bytes": None,
                "signed_tx_bytes": len(tx), "signed_tx_sha256": digest(tx), "nonce": 7,
                "tx_gas_limit": config["tx_gas_limit"],
                "source_size_admissible": len(tx) <= config["signed_size_limit"],
                "source_no_op_gas_fits": gas["no_op_calldata_gas"] <= config["tx_gas_limit"],
                "configured_node_admission": None, "authorized_receipt": None,
                "exact_l2_verifier_gas": None, "actual_data_fee_wei": None, "fee_scenarios": fees})
        payloads.append({**entry, "raw_proof_bytes": len(data), "raw_proof_keccak256": model.keccak256(data).hex(),
                         "classification": "EXACT_NATIVE_PROOF_TRANSPORT_NOT_EVM_ABI", "networks": networks})
    return {"schema": "pqtc.r2.conditional-native-l2.v1", "measurement_status": "MEASURED",
        "measurement_scope": "exact bytes, byte gas and local deterministic signed-envelope sizes only",
        "payload_manifest": manifest, "source_inputs": pins,
        "chain_source_pins": json.loads((source / "sources.json").read_text()),
        "synthetic_fee_inputs": scenarios,
        "signer": {"address": model.research_address(), "key": "universally public Anvil account 0, never funded",
                   "destination": model.RESEARCH_TO.hex(), "value_wei": 0, "network_calls": 0},
        "abi_status": "NOT_IMPLEMENTED_FOR_THESE_NATIVE_CODECS",
        "reopen_condition": "Exact EVM proof codec and verifier ABI adapter, then source-pinned local node admission and actual data-fee implementation; no public network authorization is implied.",
        "caveats": ["No ABI selector, public-statement encoding or verifier decoder is supplied.",
                    "Postcard/research raw bytes are transport controls, not valid EVM verifier calls.",
                    "Source size and no-code gas fit are projections, not node admission or receipt evidence.",
                    "OP fee numbers are uncalibrated synthetic projections; unsupported Nitro/Scroll fees stay null.",
                    "Signed transaction bytes are not persisted; no RPC or broadcast interface exists."],
        "payloads": payloads}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--payloads", type=Path, help="hash-bound native payload manifest; omitted runs retained A/B ABI diagnostic")
    args = parser.parse_args()
    payloads = json.loads(args.payloads.read_text()) if args.payloads else None
    output = args.output.resolve()
    if not output.is_relative_to(HERE):
        parser.error("output must remain under research/r2/conditional")
    if output.exists():
        parser.error("output already exists; choose a fresh resume-* path")
    result = diagnose(payloads)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
