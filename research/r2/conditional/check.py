#!/usr/bin/env python3
"""Consumer-level checks over Main's executed local diagnostic outputs."""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from gates import evaluate

HERE = Path(__file__).resolve().parent


def main():
    matrix = evaluate({})
    conditional = [row for row in matrix["rows"] if row["branch"] != "l2_retained_baseline_diagnostic"]
    assert all(row["gate_status"] == "NOT_ENTERED" and row["architecture_failed"] is None for row in conditional)
    assert all(fact["satisfied"] is None for row in conditional for fact in row["prerequisites"].values())
    result = json.loads((HERE / "outputs/l2.json").read_text())
    for network in result["networks"]:
        a, b = network["parts"]
        assert a["nonce"] + 1 == b["nonce"]
        assert a["abi_calldata_bytes"] > a["raw_proof_bytes"]
        assert b["abi_calldata_bytes"] > b["raw_proof_bytes"]
        assert network["split_totals"]["signed_tx_bytes_sum"] == a["signed_tx_bytes"] + b["signed_tx_bytes"]
        assert network["split_totals"]["both_transactions_source_size_admissible"] == (a["source_size_admissible"] and b["source_size_admissible"])
        assert network["combined_transport_control"]["complete_combined_verifier_gas"] is None
        assert a["exact_l2_verifier_gas"] is None and b["authorized_receipt"] is None
        for index, fees in enumerate(network["fee_comparison"]):
            left = a["fee_scenarios"][index]["total_fee_wei"]
            right = b["fee_scenarios"][index]["total_fee_wei"]
            assert fees["split_no_op_total_fee_wei"] == (left + right if left is not None and right is not None else None)
        # Exact fixed-01 bytes: split fits OP/Scroll size rules while concatenation does not.
        if network["network"] in ("op-mainnet", "scroll-mainnet"):
            assert network["split_totals"]["both_transactions_source_size_admissible"]
            assert not network["combined_transport_control"]["source_size_admissible"]
        else:
            assert not network["split_totals"]["both_transactions_source_size_admissible"]
            assert all(fee["split_no_op_total_fee_wei"] is None for fee in network["fee_comparison"])
    print("conditional unknown gates and exact split/combined transport boundaries checked")


if __name__ == "__main__":
    main()
