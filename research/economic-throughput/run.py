#!/usr/bin/env python3
"""Deterministic section-19 economic and throughput model.

The canonical run is offline, uses Decimal/Fraction arithmetic, validates every
pinned source and exact calldata artifact, and never obtains live prices/state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "research" / "economic-throughput"
DEFAULT_CONFIG = PACKAGE / "assumptions.json"
PIN_FILE = PACKAGE / "source-hashes.json"
RUN_PATHS = tuple(
    [f"research/runs/v03-corpus-{i:02d}.json" for i in range(1, 31)]
    + [f"research/runs/v03-fixed-{i:02d}.json" for i in range(1, 31)]
)
EXTERNAL_SOURCES = (
    "PQTC_NEXT_GENERATION_RESEARCH_PLAN.md",
    "research/summaries/v03-distribution.csv",
    "research/candidates/v03-baseline/gas/measured-summary.json",
    "research/aggregation/outputs/results.json",
    "research/l2-economics/results/summary.json",
    "research/l2-economics/scenarios.json",
    "research/prover-operations/results.json",
    "research/gas-rules/rules.json",
    "research/gas-rules/sources.json",
    "research/economic-throughput/assumptions.json",
) + RUN_PATHS
SCHEDULE_IDS = (
    "ACTIVE_EIP7623",
    "FUTURE_EIP7976_64_64",
    "DRAFT_EIP8311_96_96",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(), parse_float=Decimal)


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def rounded_fraction(value: Fraction, places: int) -> str:
    with localcontext() as context:
        context.prec = max(80, places + 40)
        decimal = Decimal(value.numerator) / Decimal(value.denominator)
        quantum = Decimal(1).scaleb(-places)
        return format(decimal.quantize(quantum, rounding=ROUND_HALF_EVEN), f".{places}f")


def fraction_decimal(value: Fraction) -> str:
    denominator = value.denominator
    while denominator % 2 == 0:
        denominator //= 2
    while denominator % 5 == 0:
        denominator //= 5
    if denominator != 1:
        raise ValueError(f"non-terminating decimal requested for {fraction_text(value)}")
    with localcontext() as context:
        context.prec = 100
        return decimal_text(Decimal(value.numerator) / Decimal(value.denominator))


def median(values: list[int | Decimal]) -> Fraction:
    ordered = sorted(Fraction(value) for value in values)
    count = len(ordered)
    if not count:
        raise ValueError("median of empty input")
    middle = count // 2
    if count % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def distribution(values: list[int | Decimal], unit: str) -> dict[str, Any]:
    fractions = [Fraction(value) for value in values]
    return {
        "count": len(fractions),
        "unit": unit,
        "minimum": fraction_decimal(min(fractions)),
        "median": fraction_decimal(median(values)),
        "maximum": fraction_decimal(max(fractions)),
    }


def write_source_pins() -> None:
    dump_json(
        PIN_FILE,
        {
            "algorithm": "sha256",
            "schema": "pqtc-section19-source-hashes-v1",
            "files": {path: sha256(ROOT / path) for path in EXTERNAL_SOURCES},
            "run_record_count": len(RUN_PATHS),
        },
    )


def validate_source_pins() -> dict[str, Any]:
    pins = load_json(PIN_FILE)
    if pins.get("algorithm") != "sha256":
        raise ValueError("source-hashes.json algorithm must be sha256")
    expected = pins.get("files", {})
    if set(expected) != set(EXTERNAL_SOURCES):
        raise ValueError("source-hashes.json file set does not match model source set")
    mismatches = []
    for relative in EXTERNAL_SOURCES:
        actual = sha256(ROOT / relative)
        if actual != expected[relative]:
            mismatches.append({"path": relative, "expected": expected[relative], "actual": actual})
    if mismatches:
        raise ValueError(f"source hash mismatch: {mismatches}")
    return pins


def find_artifact(run: dict[str, Any], suffix: str) -> dict[str, Any]:
    matches = [artifact for artifact in run["artifacts"] if artifact["path"].endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"expected one {suffix} artifact for {run['run_id']}")
    return matches[0]


def calldata_metrics(run: dict[str, Any], suffix: str) -> dict[str, int]:
    artifact = find_artifact(run, suffix)
    path = ROOT / artifact["path"]
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != artifact["digests"]["sha256"]:
        raise ValueError(f"embedded calldata hash mismatch: {artifact['path']}")
    if len(payload) != artifact["bytes"]:
        raise ValueError(f"embedded calldata length mismatch: {artifact['path']}")
    zero = payload.count(0)
    return {"bytes": len(payload), "zero": zero, "nonzero": len(payload) - zero}


def validate_schedule(
    run_id: str,
    rows: list[dict[str, Any]],
    calldata: dict[str, int],
    execution_gas: int,
    schedules: dict[str, dict[str, Any]],
) -> dict[str, dict[str, int | bool]]:
    by_id = {row["name"]: row for row in rows}
    if set(by_id) != set(SCHEDULE_IDS):
        raise ValueError(f"unexpected gas schedules for {run_id}: {sorted(by_id)}")
    standard_intrinsic = 21000 + 4 * calldata["zero"] + 16 * calldata["nonzero"]
    regular_total = execution_gas + standard_intrinsic
    result: dict[str, dict[str, int | bool]] = {}
    for schedule_id in SCHEDULE_IDS:
        schedule = schedules[schedule_id]
        floor = (
            21000
            + schedule["zero_byte_floor_gas"] * calldata["zero"]
            + schedule["nonzero_byte_floor_gas"] * calldata["nonzero"]
        )
        total = max(regular_total, floor)
        row = by_id[schedule_id]
        expected = (row["floor_gas"], row["total_gas"], row["floor_is_binding"])
        actual = (floor, total, floor > regular_total)
        if expected != actual:
            raise ValueError(f"gas schedule mismatch for {run_id}/{schedule_id}: {expected} != {actual}")
        result[schedule_id] = {
            "floor_gas": floor,
            "total_gas": total,
            "floor_is_binding": floor > regular_total,
        }
    return result


def load_and_validate_runs(config: dict[str, Any]) -> list[dict[str, Any]]:
    schedule_config = {row["id"]: row for row in config["gas_schedules"]}
    if tuple(schedule_config) != SCHEDULE_IDS:
        raise ValueError("configured gas schedules must be the ordered active/64/96 set")
    runs = []
    for relative in RUN_PATHS:
        run = load_json(ROOT / relative)
        run_id = Path(relative).stem
        if run.get("run_id") != run_id or run.get("candidate_id") != "C00/v03-baseline":
            raise ValueError(f"identity mismatch in {relative}")
        if run["git"]["commit"] != "00f829001999ee66da6fd5161c4c205c07d0b937":
            raise ValueError(f"baseline commit mismatch in {relative}")
        part_a = calldata_metrics(run, "part-a.calldata")
        part_b = calldata_metrics(run, "part-b.calldata")
        evm = run["evm"]
        a_schedules = validate_schedule(
            run_id,
            evm["gas_scenarios"],
            part_a,
            evm["component_gas"]["pool_a_execution"],
            schedule_config,
        )
        b_schedules = validate_schedule(
            run_id,
            evm["part_b_gas_scenarios"],
            part_b,
            evm["component_gas"]["pool_b_execution"],
            schedule_config,
        )
        if part_a["bytes"] + part_b["bytes"] != run["proof_bytes"]["abi_calldata_bytes"]:
            raise ValueError(f"combined calldata mismatch in {relative}")
        runs.append(
            {
                "run_id": run_id,
                "wall_ms": run["prover"]["wall_ms"],
                "proof_only_ms": run["prover"]["proof_only_ms"],
                "calldata_bytes": part_a["bytes"] + part_b["bytes"],
                "part_a_calldata_bytes": part_a["bytes"],
                "part_b_calldata_bytes": part_b["bytes"],
                "schedules": {
                    schedule_id: {
                        "part_a_gas": a_schedules[schedule_id]["total_gas"],
                        "part_b_gas": b_schedules[schedule_id]["total_gas"],
                        "complete_gas": a_schedules[schedule_id]["total_gas"]
                        + b_schedules[schedule_id]["total_gas"],
                        "part_a_floor_binding": a_schedules[schedule_id]["floor_is_binding"],
                        "part_b_floor_binding": b_schedules[schedule_id]["floor_is_binding"],
                    }
                    for schedule_id in SCHEDULE_IDS
                },
            }
        )
    return runs


def validate_distribution_csv(runs: list[dict[str, Any]]) -> None:
    by_id = {run["run_id"]: run for run in runs}
    with (ROOT / "research/summaries/v03-distribution.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 60 or set(row["run_id"] for row in rows) != set(by_id):
        raise ValueError("baseline distribution must contain the exact 60-run set")
    for row in rows:
        run = by_id[row["run_id"]]
        active = run["schedules"]["ACTIVE_EIP7623"]
        checks = {
            "candidate_id": "C00/v03-baseline",
            "prove_wall_ms": Decimal(run["wall_ms"]),
            "proof_only_ms": Decimal(run["proof_only_ms"]),
            "abi_calldata_bytes": run["calldata_bytes"],
            "evm_a_total_gas": active["part_a_gas"],
            "evm_b_total_gas": active["part_b_gas"],
            "gate_status": "FAIL",
        }
        for field, expected in checks.items():
            actual: Any = row[field]
            if isinstance(expected, Decimal):
                actual = Decimal(actual)
            elif isinstance(expected, int):
                actual = int(actual)
            if actual != expected:
                raise ValueError(f"distribution mismatch {row['run_id']}/{field}: {actual} != {expected}")


def cost_sensitivity(gas: Fraction, prices: list[str], usd: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    eth_usd = Fraction(Decimal(usd["eth_usd"])) if usd["status"] == "EVALUATED_PINNED_OFFLINE_SOURCE" else None
    for price_text in prices:
        price_gwei = Fraction(Decimal(price_text))
        price_wei = price_gwei * 1_000_000_000
        if price_wei.denominator != 1:
            raise ValueError("gas price must resolve to an integer number of wei")
        cost_wei = gas * price_wei
        if cost_wei.denominator != 1:
            raise ValueError("representative gas-price product must resolve to integer wei")
        row: dict[str, Any] = {
            "effective_gas_price_gwei": price_text,
            "cost_wei": cost_wei.numerator,
            "cost_eth": fraction_decimal(cost_wei / 10**18),
        }
        if eth_usd is None:
            row["cost_usd"] = "NOT_EVALUATED"
        else:
            usd_cost = cost_wei * eth_usd / 10**18
            row["cost_usd"] = {
                "exact_fraction": fraction_text(usd_cost),
                "decimal_8_rounded": rounded_fraction(usd_cost, 8),
            }
        rows.append(row)
    return rows


def validate_usd(config: dict[str, Any], config_path: Path) -> dict[str, Any]:
    price = config["usd_example"]
    fields = ("eth_usd", "price_timestamp_utc", "source_artifact", "source_sha256", "source_description")
    populated = [price[field] is not None for field in fields]
    if not any(populated):
        return {
            "status": "NOT_EVALUATED_NO_PINNED_PRICE_SOURCE",
            "configurable_offline_input": fields,
            "separation": "USD_PRICE_IS_OPERATIONAL_SENSITIVITY_AND_NEVER_A_CRYPTOGRAPHIC_GATE_INPUT",
        }
    if not all(populated):
        raise ValueError("USD example requires every price/source field or all-null fields")
    source = Path(price["source_artifact"])
    if not source.is_absolute():
        source = (config_path.parent / source).resolve()
    actual = sha256(source)
    if actual != price["source_sha256"]:
        raise ValueError("USD source artifact SHA-256 mismatch")
    return {
        "status": "EVALUATED_PINNED_OFFLINE_SOURCE",
        "eth_usd": decimal_text(Decimal(price["eth_usd"])),
        "price_timestamp_utc": price["price_timestamp_utc"],
        "source_artifact": str(source),
        "source_sha256": actual,
        "source_description": price["source_description"],
        "separation": "USD_PRICE_IS_OPERATIONAL_SENSITIVITY_AND_NEVER_A_CRYPTOGRAPHIC_GATE_INPUT",
    }


def gas_model(runs: list[dict[str, Any]], config: dict[str, Any], usd: dict[str, Any]) -> dict[str, Any]:
    schedule_config = {row["id"]: row for row in config["gas_schedules"]}
    schedules: list[dict[str, Any]] = []
    for schedule_id in SCHEDULE_IDS:
        a_values = [run["schedules"][schedule_id]["part_a_gas"] for run in runs]
        b_values = [run["schedules"][schedule_id]["part_b_gas"] for run in runs]
        complete_values = [run["schedules"][schedule_id]["complete_gas"] for run in runs]
        cap = config["transaction_gas_limit_max"]
        eligible = [
            run
            for run in runs
            if run["schedules"][schedule_id]["part_a_gas"] <= cap
            and run["schedules"][schedule_id]["part_b_gas"] <= cap
        ]
        block_rows = []
        p50_complete = median(complete_values)
        for block_limit in config["block_gas_limits"]:
            packings = [
                {
                    "run_id": run["run_id"],
                    "withdrawals": block_limit // run["schedules"][schedule_id]["complete_gas"],
                    "calldata_bytes": (
                        block_limit // run["schedules"][schedule_id]["complete_gas"]
                    )
                    * run["calldata_bytes"],
                    "gas": run["schedules"][schedule_id]["complete_gas"],
                }
                for run in eligible
            ]
            max_withdrawals = max(row["withdrawals"] for row in packings)
            withdrawal_witness = min(
                (row for row in packings if row["withdrawals"] == max_withdrawals),
                key=lambda row: (row["gas"], row["run_id"]),
            )
            calldata_witness = max(packings, key=lambda row: (row["calldata_bytes"], row["run_id"]))
            conservative_gas = max(run["schedules"][schedule_id]["complete_gas"] for run in eligible)
            conservative_count = block_limit // conservative_gas
            share = p50_complete / block_limit
            block_rows.append(
                {
                    "block_gas_limit": block_limit,
                    "p50_complete_withdrawal_block_share": {
                        "exact_fraction": fraction_text(share),
                        "percent_12_rounded": rounded_fraction(share * 100, 12),
                    },
                    "observed_eligible_best_case": {
                        "max_completed_withdrawals": max_withdrawals,
                        "witness_run_id": withdrawal_witness["run_id"],
                        "witness_complete_gas": withdrawal_witness["gas"],
                        "calldata_bytes_for_that_packing": withdrawal_witness["calldata_bytes"],
                    },
                    "maximum_calldata_over_observed_eligible_packings": {
                        "bytes": calldata_witness["calldata_bytes"],
                        "withdrawals": calldata_witness["withdrawals"],
                        "witness_run_id": calldata_witness["run_id"],
                    },
                    "observed_eligible_conservative": {
                        "completed_withdrawals": conservative_count,
                        "gas_bound_per_withdrawal": conservative_gas,
                        "meaning": "capacity guaranteed only across the 51 transaction-cap-eligible committed baseline records",
                    },
                }
            )
        schedule = schedule_config[schedule_id]
        schedules.append(
            {
                "id": schedule_id,
                "status": schedule["status"],
                "floor_coefficients": {
                    "zero_byte_gas": schedule["zero_byte_floor_gas"],
                    "nonzero_byte_gas": schedule["nonzero_byte_floor_gas"],
                },
                "floor_binding_counts": {
                    "part_a": sum(run["schedules"][schedule_id]["part_a_floor_binding"] for run in runs),
                    "part_b": sum(run["schedules"][schedule_id]["part_b_floor_binding"] for run in runs),
                },
                "gas": {
                    "part_a": distribution(a_values, "gas"),
                    "part_b": distribution(b_values, "gas"),
                    "complete_two_call_withdrawal": distribution(complete_values, "gas"),
                },
                "transaction_cap": {
                    "cap": cap,
                    "eligible_run_count": len(eligible),
                    "ineligible_run_count": len(runs) - len(eligible),
                    "status": "FAIL_OBSERVED_PART_A_EXCEEDS_CAP" if len(eligible) != len(runs) else "PASS_OBSERVED_SAMPLE",
                },
                "blocks": block_rows,
            }
        )
    active = next(row for row in schedules if row["id"] == "ACTIVE_EIP7623")
    path_gas = {
        "part_a_p50": median([run["schedules"]["ACTIVE_EIP7623"]["part_a_gas"] for run in runs]),
        "part_b_p50": median([run["schedules"]["ACTIVE_EIP7623"]["part_b_gas"] for run in runs]),
        "complete_two_call_p50": median(
            [run["schedules"]["ACTIVE_EIP7623"]["complete_gas"] for run in runs]
        ),
    }
    return {
        "method": "EXACT_COMMITTED_CALLDATA_AND_MEASURED_EXECUTION; ALTERNATE_STANDALONE_FLOOR_MAXIMUM",
        "schedule_warning": "64/64 is scheduled but unactivated and 96/96 is an unscheduled draft; neither is labeled active or a complete Amsterdam composition.",
        "schedules": schedules,
        "active_schedule_cost_sensitivity": [
            {
                "path": name,
                "representative_gas": fraction_decimal(gas),
                "representative": "LINEAR_INTERPOLATED_P50_OF_60_COMMITTED_RECORDS",
                "rows": cost_sensitivity(gas, config["effective_gas_price_gwei"], usd),
            }
            for name, gas in path_gas.items()
        ],
        "calldata": {
            "complete_two_call_withdrawal": distribution([run["calldata_bytes"] for run in runs], "bytes"),
            "part_a": distribution([run["part_a_calldata_bytes"] for run in runs], "bytes"),
            "part_b": distribution([run["part_b_calldata_bytes"] for run in runs], "bytes"),
        },
    }


def throughput_model(runs: list[dict[str, Any]]) -> dict[str, Any]:
    wall = [Decimal(run["wall_ms"]) for run in runs]
    total_ms = sum((Fraction(value) for value in wall), Fraction(0))
    aggregate_rate = Fraction(len(wall) * 1000, 1) / total_ms
    median_rate = Fraction(1000, 1) / median(wall)
    return {
        "H1": {
            "hardware_id": "H1-MAC16-5-M4MAX-48G",
            "status": "PARTIALLY_MEASURED_WARM_ONLY",
            "warm_run_count": 60,
            "wall_ms": distribution(wall, "milliseconds"),
            "derived_sequential_throughput": {
                "aggregate_exact_proofs_per_second": fraction_text(aggregate_rate),
                "aggregate_proofs_per_second_12_rounded": rounded_fraction(aggregate_rate, 12),
                "reciprocal_of_median_exact_proofs_per_second": fraction_text(median_rate),
                "reciprocal_of_median_proofs_per_second_12_rounded": rounded_fraction(median_rate, 12),
                "classification": "DERIVED_FROM_SEQUENTIAL_WARM_WALL_TIMES_NOT_A_CONCURRENT_LOAD_TEST",
            },
            "cold": "NOT_EVALUATED",
            "neon_code_path_execution": "NOT_EVALUATED",
        },
        "H2": "NOT_EVALUATED_NO_COMMITTED_MEASUREMENTS",
        "H3": "NOT_EVALUATED_NO_COMMITTED_MEASUREMENTS",
    }


def relayer_model(runs: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    p50_gas = median([run["schedules"]["ACTIVE_EIP7623"]["complete_gas"] for run in runs])
    lower_bound = cost_sensitivity(
        p50_gas,
        config["effective_gas_price_gwei"],
        {"status": "NOT_EVALUATED_NO_PINNED_PRICE_SOURCE"},
    )
    relayer = config["relayer"]
    missing = [
        key
        for key in (
            "non_gas_cost_wei",
            "capital_and_risk_cost_wei",
            "withdrawal_denomination_wei",
            "prover_machine_hourly_usd",
            "l2_fee_input",
        )
        if relayer[key] is None
    ]
    return {
        "status": "NOT_EVALUATED_MISSING_OPERATIONAL_FEE_INPUTS",
        "missing_inputs": missing,
        "formula": {
            "network_cost_wei": "gas_used * effective_gas_price_wei + l2_fee_wei",
            "full_break_even_wei": "network_cost_wei + non_gas_cost_wei + capital_and_risk_cost_wei + prover_cost_wei",
            "fee_fraction_of_withdrawal": "full_break_even_wei / withdrawal_denomination_wei",
            "prover_cost_conversion": "prover_wall_hours * prover_machine_hourly_usd / eth_usd, requiring separately pinned USD inputs",
        },
        "gas_only_lower_bound_sensitivity": {
            "representative": "ACTIVE_EIP7623_COMPLETE_TWO_CALL_LINEAR_INTERPOLATED_P50",
            "gas": fraction_decimal(p50_gas),
            "rows": lower_bound,
            "warning": "This excludes L2/data fees, non-gas operations, capital, risk, failed transactions, and prover machine cost and is not a quoted relayer fee.",
        },
    }


def context_evidence() -> dict[str, Any]:
    aggregation = load_json(ROOT / "research/aggregation/outputs/results.json")
    l2 = load_json(ROOT / "research/l2-economics/results/summary.json")
    operations = load_json(ROOT / "research/prover-operations/results.json")
    gas_rules = load_json(ROOT / "research/gas-rules/rules.json")
    if aggregation["status"] != "STOP_BY_DEPENDENCY":
        raise ValueError("aggregation status changed")
    if operations["gate"]["status"] != "FAIL" or operations["gate"]["finalistSelected"] is not False:
        raise ValueError("prover operations finalist/gate state changed")
    if gas_rules["calculator"]["defaults"]["transaction_gas_limit_max"] != 16777216:
        raise ValueError("gas-rule transaction cap changed")
    return {
        "aggregation": {
            "status": aggregation["status"],
            "gate": aggregation["decision"]["gate"],
            "external_cryptographic_acceptance": aggregation["decision"]["external_cryptographic_acceptance"],
            "role": "CONTEXT_ONLY_NO_MEASURED_FULL_AGGREGATION_INCLUDED",
        },
        "l2": {
            "fee_labels": l2["fee_labels"],
            "pqtc_receipt_evidence": l2["pqtc_receipt_evidence"],
            "H2": l2["hardware_profiles"]["H2"],
            "H3": l2["hardware_profiles"]["H3"],
            "role": "CONTEXT_ONLY_SYNTHETIC_FEE_PROJECTIONS_EXCLUDED_FROM_L1_BASELINE_COST_TABLE",
        },
        "prover_operations_gate": operations["gate"],
        "gas_rules": {
            "active_profile": gas_rules["calculator"]["default_profile"],
            "transaction_cap": gas_rules["calculator"]["defaults"]["transaction_gas_limit_max"],
            "alternate_floor_status": [
                {
                    "id": item["id"],
                    "activation_class": item["activation_class"],
                    "may_be_labeled_active": item["may_be_labeled_active"],
                }
                for item in gas_rules["calculator"]["calldata_floor_scenarios"]
            ],
        },
    }


def validate_result(result: dict[str, Any]) -> None:
    if result["finalist_count"] != 0 or result["finalists"] != []:
        raise ValueError("section-19 result must have no finalist rows")
    if result["finalist_gate"] != "NOT_APPLICABLE_NO_FINALIST":
        raise ValueError("incorrect finalist gate")
    baseline = result["non_finalist_context"][0]
    if baseline["disposition"] != "NON_FINALIST_CONTEXT":
        raise ValueError("baseline disposition must remain NON_FINALIST_CONTEXT")
    if baseline["weighted_result"] != "NOT_COMPUTED_NON_FINALIST":
        raise ValueError("baseline must not receive a weighted passing result")
    if result["separation"]["volatile_inputs_in_cryptographic_gate"] is not False:
        raise ValueError("volatile inputs entered cryptographic gate")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=PACKAGE / "outputs")
    parser.add_argument("--refresh-source-hashes", action="store_true")
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = load_json(config_path)
    if args.refresh_source_hashes:
        if config_path != DEFAULT_CONFIG.resolve():
            raise ValueError("source pins may only be refreshed with the canonical assumptions.json")
        write_source_pins()
    pins = validate_source_pins()
    usd = validate_usd(config, config_path)
    runs = load_and_validate_runs(config)
    validate_distribution_csv(runs)
    result = {
        "schema": "pqtc-section19-economic-throughput-result-v1",
        "snapshot_date": config["snapshot_date"],
        "status": "COMPLETE_NON_FINALIST_CONTEXT_ONLY",
        "finalist_count": 0,
        "finalists": [],
        "finalist_gate": "NOT_APPLICABLE_NO_FINALIST",
        "section19_obligation": "VACUOUS_NO_FINALIST_ROWS_EXIST",
        "source_hashes_sha256": sha256(PIN_FILE),
        "config": {
            "path": str(config_path.relative_to(ROOT)) if config_path.is_relative_to(ROOT) else str(config_path),
            "sha256": sha256(config_path),
            "arithmetic": "PYTHON_DECIMAL_AND_FRACTION_NO_BINARY_FLOAT",
        },
        "usd_example": usd,
        "non_finalist_context": [
            {
                "candidate_id": "C00/v03-baseline",
                "disposition": "NON_FINALIST_CONTEXT",
                "security_qualified": False,
                "finalist_selected": False,
                "gate_status": "FAIL",
                "weighted_result": "NOT_COMPUTED_NON_FINALIST",
                "must_not_receive_passing_weighted_result": True,
                "gas_and_block_model": gas_model(runs, config, usd),
                "prover_throughput": throughput_model(runs),
                "relayer_break_even": relayer_model(runs, config),
            }
        ],
        "cross_cutting_context": context_evidence(),
        "separation": {
            "volatile_inputs_in_cryptographic_gate": False,
            "cryptographic_gate_inputs": [],
            "operational_sensitivity_inputs": [
                "effective gas price",
                "synthetic block gas limit",
                "optional pinned ETH/USD price",
                "relayer operational costs",
            ],
            "external_cryptographic_acceptance": "OPEN",
            "live_chain_state": "NOT_EVALUATED",
            "live_price": "NOT_EVALUATED",
        },
        "reproducibility": {
            "command": "python3 research/economic-throughput/run.py",
            "source_pin_count": len(pins["files"]),
            "validated_run_records": len(runs),
            "validated_exact_calldata_artifacts": len(runs) * 2,
        },
    }
    validate_result(result)
    output_dir = args.output_dir.resolve()
    dump_json(output_dir / "results.json", result)
    with (output_dir / "cost-sensitivity.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["disposition", "candidate_id", "path", "gas", "effective_gas_price_gwei", "cost_wei", "cost_eth", "cost_usd"])
        model = result["non_finalist_context"][0]["gas_and_block_model"]
        for path in model["active_schedule_cost_sensitivity"]:
            for row in path["rows"]:
                usd_cell = row["cost_usd"] if isinstance(row["cost_usd"], str) else row["cost_usd"]["decimal_8_rounded"]
                writer.writerow([
                    "NON_FINALIST_CONTEXT",
                    "C00/v03-baseline",
                    path["path"],
                    path["representative_gas"],
                    row["effective_gas_price_gwei"],
                    row["cost_wei"],
                    row["cost_eth"],
                    usd_cell,
                ])
    status = {
        "schema": "pqtc-section19-status-v1",
        "status": result["status"],
        "finalist_count": 0,
        "finalist_gate": "NOT_APPLICABLE_NO_FINALIST",
        "baseline_disposition": "NON_FINALIST_CONTEXT",
        "baseline_gate": "FAIL",
        "weighted_result": "NOT_COMPUTED_NON_FINALIST",
        "usd_examples": usd["status"],
        "H1": "PARTIALLY_MEASURED_WARM_ONLY",
        "H2": "NOT_EVALUATED_NO_COMMITTED_MEASUREMENTS",
        "H3": "NOT_EVALUATED_NO_COMMITTED_MEASUREMENTS",
        "fees": "NOT_EVALUATED_MISSING_OPERATIONAL_FEE_INPUTS",
        "aggregation": "STOP_BY_DEPENDENCY",
        "external_cryptographic_acceptance": "OPEN",
    }
    dump_json(PACKAGE / "status.json", status)
    print(f"wrote {output_dir / 'results.json'} and {output_dir / 'cost-sensitivity.csv'}")


if __name__ == "__main__":
    main()
