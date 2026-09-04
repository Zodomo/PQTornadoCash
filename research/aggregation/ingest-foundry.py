#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from model import BATCH_SIZES
from run import source_hashes, validate_result

HERE = Path(__file__).resolve().parent
RAW = HERE / "outputs/foundry-components.json"
RESULT = HERE / "outputs/results.json"
STATUS = HERE / "status.json"


def positive_grid(raw: dict[str, object], key: str) -> list[int]:
    values = raw.get(key)
    if not isinstance(values, list) or len(values) != len(BATCH_SIZES):
        raise SystemExit(f"{key}: incomplete N grid")
    if any(type(value) is not int or value <= 0 for value in values):
        raise SystemExit(f"{key}: expected positive exact integers")
    return values


def main() -> None:
    raw = json.loads(RAW.read_text())
    if raw.get("schema") != "sp70-foundry-components-v1" or raw.get("N") != list(BATCH_SIZES):
        raise SystemExit("unexpected or incomplete Foundry component schema")
    nullifier = positive_grid(raw, "nullifier_component_gas")
    unrelated = positive_grid(raw, "unrelated_user_pull_credit_gas")
    same_user = positive_grid(raw, "same_user_pull_credit_gas")
    sizes = positive_grid(raw, "public_only_calldata_bytes")
    zero = positive_grid(raw, "public_only_calldata_zero_bytes")
    nonzero = positive_grid(raw, "public_only_calldata_nonzero_bytes")
    active = positive_grid(raw, "public_only_active_calldata_floor")
    uniform64 = positive_grid(raw, "public_only_uniform64_calldata_floor")
    uniform96 = positive_grid(raw, "public_only_uniform96_calldata_floor")
    claim = raw.get("successful_pull_claim_gas")
    if type(claim) is not int or claim <= 0:
        raise SystemExit("successful pull claim gas must be a positive exact integer")
    for i, size in enumerate(sizes):
        if zero[i] + nonzero[i] != size:
            raise SystemExit("calldata byte counts do not sum")
        if active[i] != 21_000 + 10 * zero[i] + 40 * nonzero[i]:
            raise SystemExit("active EIP-7623 calldata floor mismatch")
        if uniform64[i] != 21_000 + 64 * size or uniform96[i] != 21_000 + 96 * size:
            raise SystemExit("uniform calldata scenario mismatch")

    result = json.loads(RESULT.read_text())
    index = {n: i for i, n in enumerate(BATCH_SIZES)}
    for row in result["measurements"]:
        i = index[row["N"]]
        row["nullifier_component_gas"] = nullifier[i]
        row["payout_component_gas"] = same_user[i] if row["user_topology"] == "SAME_USER_MULTI_NOTE" else unrelated[i]
        row["public_only_calldata_bytes"] = sizes[i]
        row["public_only_calldata_zero_bytes"] = zero[i]
        row["public_only_calldata_nonzero_bytes"] = nonzero[i]
        row["public_only_calldata_floors"] = {
            "active_eip7623_10_40": active[i],
            "uniform_64": uniform64[i],
            "uniform_96": uniform96[i],
        }
        row["successful_pull_claim_gas"] = claim
        row["component_status"] = "PASS_EXACT_ISOLATED_FOUNDRY_COMPONENTS"
        # Intentionally leave full calldata, verifier, proving, complete
        # settlement, totals, gas/withdrawal, and recovery totals null.
    result["foundry_harness"]["status"] = "PASS_EXACT_ISOLATED_COMPONENTS_NOT_FULL_BENCHMARK"
    validate_result(result)
    RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    status = json.loads(STATUS.read_text())
    status["settlement_components"] = "PASS_EXACT_ISOLATED_FOUNDRY_COMPONENTS"
    status["full_aggregation_benchmark"] = "NOT_EVALUATED"
    STATUS.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    (HERE / "source-hashes.json").write_text(json.dumps(source_hashes(), indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
