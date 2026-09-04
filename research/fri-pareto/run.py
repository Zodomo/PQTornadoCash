#!/usr/bin/env python3
"""Regenerate SP-50 manifests/projections and, unless requested otherwise, fresh anchors."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import importlib.util
import itertools
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GRID = HERE / "grid.json"
MANIFESTS = HERE / "manifests"
OUTPUTS = HERE / "outputs"
CALCULATOR = ROOT / "research/security-model/calculator/security_calculator.py"
PROVER = ROOT / "research/candidates/C10-fri/Cargo.toml"
FIXED_INPUT = ROOT / "research/candidates/v03-baseline/proofs/v03-fixed-01"
BASELINE = ROOT / "research/candidates/v03-baseline/gas/measured-summary.json"
CAP = 1 << 24

OMISSIONS = [
    "The custom KeccakPair512 transcript and full Fiat-Shamir transform have no complete QROM proof.",
    "The MMCS cap is a supplied assumption, not structural cryptanalysis.",
    "External cryptographic review, correlated-agreement review, transcript review, MMCS review, and advisory closure remain open or failed.",
    "This manifest is a C10 research sweep point and is not a production parameter registration.",
]


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def manifest(point: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    m = dict(base)
    m.update({
        "profile_id": f"C10-{point['id']}",
        "fri_log_blowup": point["logBlowup"],
        "fri_num_queries": point["queries"],
        "fri_log_final_poly_len": point["logFinalPoly"],
        "commit_grinding_bits": point["commitPow"],
        "query_grinding_bits": point["queryPow"],
        "hiding_random_functions": point["randomCodewords"],
        "num_batched_functions": base["relation_width"] + base["quotient_chunks"] + point["randomCodewords"],
        "omissions": OMISSIONS,
    })
    return m


def calculator(mpath: Path) -> tuple[dict[str, Any] | None, str | None]:
    run = subprocess.run(
        [sys.executable, str(CALCULATOR), "calculate", str(mpath), "--format", "json"],
        text=True, capture_output=True,
    )
    if run.returncode:
        return None, run.stderr.strip()
    report = json.loads(run.stdout)
    return report, None


def projection(point: dict[str, Any], baseline: dict[str, Any], gates: dict[str, Any]) -> dict[str, Any]:
    q = point["queries"]
    b = point["logBlowup"]
    r = point["randomCodewords"]
    final_log = point["logFinalPoly"]
    fold_factor = point.get("foldFactor", 2)
    salt_elements = point.get("saltElements", 8)
    cap_height = point.get("capHeight", 0)
    log_arity = int(math.log2(fold_factor))
    rounds = math.ceil((9 - final_log) / log_arity)
    base_proof = baseline["distributions"]["raw_proof_bytes"]["p50"]
    query_component = 5904 * q
    fixed_component = 20012
    blowup_component = (b - 4) * q * 12 * 64
    hiding_component = (r - 4) * (q * 19 * 4 + 19 * 16)
    final_component = ((1 << final_log) - 1) * 16
    fold_component = (rounds - 9) * q * (16 + 4 * salt_elements + 64)
    salt_component = (salt_elements - 8) * q * (3 + rounds) * 4
    cap_component = (2**cap_height - 1) * (3 + rounds) * 2 * 64 - cap_height * q * (3 + rounds) * 64
    proof_bytes = max(0, round(fixed_component + query_component + blowup_component + hiding_component + final_component + fold_component + salt_component + cap_component))
    ratio_a = 108326 / 212204
    part_a = round(proof_bytes * ratio_a)
    part_b = proof_bytes - part_a
    calldata_a = part_a + 318
    calldata_b = part_b + 350
    complete_calldata = calldata_a + calldata_b
    zero_fraction = baseline["distributions"]["zero_bytes"]["p50"] / base_proof
    zeros_a = round(calldata_a * zero_fraction)
    zeros_b = round(calldata_b * zero_fraction)
    nonzeros_a = calldata_a - zeros_a
    nonzeros_b = calldata_b - zeros_b
    q_scale = q / 32
    domain_scale = 2 ** (b - 4)
    fold_scale = rounds / 9
    regular_a = round(baseline["distributions"]["a_total"]["p50"] * q_scale * (0.35 + 0.65 * domain_scale) * (0.55 + 0.45 * fold_scale))
    regular_b = round(baseline["distributions"]["b_total"]["p50"] * q_scale * (0.35 + 0.65 * domain_scale) * (0.55 + 0.45 * fold_scale))

    def scenarios(z: int, n: int, regular: int) -> dict[str, Any]:
        floors = {
            "active_eip7623_10_40": 21000 + 10 * z + 40 * n,
            "scheduled_unactivated_64_64": 21000 + 64 * (z + n),
            "draft_unscheduled_96_96": 21000 + 96 * (z + n),
        }
        return {key: {"calldataFloorGas": value, "projectedGas": max(regular, value), "planGateMargin": None} for key, value in floors.items()}

    gas_a = scenarios(zeros_a, nonzeros_a, regular_a)
    gas_b = scenarios(zeros_b, nonzeros_b, regular_b)
    scenario_checks = {}
    for scenario in gates["scenarios"]:
        a = gas_a[scenario]["projectedGas"]
        b_gas = gas_b[scenario]["projectedGas"]
        gas_a[scenario]["planGateMargin"] = gates["twoTransactionPartAGasMax"] - a
        gas_b[scenario]["planGateMargin"] = gates["twoTransactionPartBGasMax"] - b_gas
        scenario_checks[scenario] = {
            "partAPasses": a <= gates["twoTransactionPartAGasMax"],
            "partBPasses": b_gas <= gates["twoTransactionPartBGasMax"],
            "totalProjectedGas": a + b_gas,
            "totalPasses": a + b_gas <= gates["twoTransactionTotalGasMax"],
        }
    projected_robust_two = complete_calldata <= gates["completeCalldataBytesMax"] and all(
        check["partAPasses"] and check["partBPasses"] and check["totalPasses"] for check in scenario_checks.values()
    )
    complete_transaction_gas = None
    exact_complete_transaction_measured = False
    one_tx_pass = exact_complete_transaction_measured and complete_transaction_gas <= gates["oneTransactionCompleteCallGasMax"]
    two_tx_pass = exact_complete_transaction_measured and projected_robust_two
    tx_status = "ONE_TX_PASS" if one_tx_pass else ("ONE_TX_FAIL" if two_tx_pass else "TWO_TX_FAIL")
    prove_ms = round(baseline["distributions"]["prove_wall_ms"]["p50"] * (0.50 + 0.50 * domain_scale) * (0.70 + 0.30 * q_scale) * (0.65 + 0.35 * fold_scale), 3)
    rss = round(baseline["distributions"]["peak_rss_bytes"]["p50"] * (0.60 + 0.40 * domain_scale))
    return {
        "evidenceClass": "PROJECTED_BASELINE_REGRESSION_NOT_MEASURED",
        "formulaVersion": 2,
        "baseline": {"runs": 60, "proofBytesP50": base_proof, "q": 32, "logBlowup": 4},
        "productionCodecProofBytes": proof_bytes,
        "partABytes": part_a, "partBBytes": part_b,
        "abiCalldataABytes": calldata_a, "abiCalldataBBytes": calldata_b,
        "completeCalldataBytes": complete_calldata,
        "projectedProverMs": prove_ms, "projectedPeakRssBytes": rss,
        "gasA": gas_a, "gasB": gas_b,
        "completeTransactionGas": complete_transaction_gas,
        "completeTransactionMeasured": exact_complete_transaction_measured,
        "planGate": {
            "oneTransactionCompleteCallGasMax": gates["oneTransactionCompleteCallGasMax"],
            "oneTransactionPass": one_tx_pass,
            "robustTwoTransactionProjectedPass": projected_robust_two,
            "robustTwoTransactionPass": two_tx_pass,
            "completeCalldataPass": complete_calldata <= gates["completeCalldataBytesMax"],
            "scenarioChecks": scenario_checks,
            "nullOrUnmeasuredFailClosed": True,
        },
        "transactionShapeStatus": tx_status,
    }


def dominates(a: dict[str, Any], b: dict[str, Any]) -> bool:
    # More generated-proven bits is better. Bytes, time, RSS, both transaction
    # sizes, and both transactions under every named gas scenario are minimized;
    # this is equivalent to maximizing the corresponding cap margins.
    scenarios = ("active_eip7623_10_40", "scheduled_unactivated_64_64", "draft_unscheduled_96_96")
    def minimized(row: dict[str, Any]) -> list[float]:
        p = row["projection"]
        values = [p[k] for k in ("productionCodecProofBytes", "projectedProverMs", "projectedPeakRssBytes", "partABytes", "partBBytes")]
        for scenario in scenarios:
            values.extend((p["gasA"][scenario]["projectedGas"], p["gasB"][scenario]["projectedGas"]))
        return values
    amin = minimized(a)
    bmin = minimized(b)
    better_or_equal = a["bestGeneratedProvenBits"] >= b["bestGeneratedProvenBits"] and all(x <= y for x, y in zip(amin, bmin))
    strictly = a["bestGeneratedProvenBits"] > b["bestGeneratedProvenBits"] or any(x < y for x, y in zip(amin, bmin))
    return better_or_equal and strictly


def analytical_filter(grid: dict[str, Any], base: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    dimensions = grid["analyticalCartesian"]
    finals = dimensions["finalPolynomialLengths"]
    dimension_lists = [
        dimensions["queries"], dimensions["logBlowup"], dimensions["foldFactors"], finals,
        dimensions["commitGrindingBits"], dimensions["queryGrindingBits"],
        dimensions["reviewedHidingRandomCodewords"], dimensions["mmcsSaltElements"],
        dimensions["capHeights"],
    ]
    exact_count = math.prod(len(values) for values in dimension_lists)
    spec = importlib.util.spec_from_file_location("sp50_security_calculator", CALCULATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load independent security calculator")
    calculator_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(calculator_module)
    upper_security_cache: dict[tuple[int, ...], dict[str, Any]] = {}
    exact_security_cache: dict[tuple[int, ...], dict[str, Any]] = {}
    counts = {
        "unbuildable": 0, "security_below_100": 0, "challenge_ceiling": 0,
        "proof_floor": 0, "dominated": 0, "retained": 0,
    }
    build_reasons: dict[str, int] = {}
    proof_survivors: list[dict[str, Any]] = []
    near_misses: list[dict[str, Any]] = []
    proof_floor_misses: list[dict[str, Any]] = []

    def generated_best(q: int, blowup: int, log_arity: int, final_log: int, commit_pow: int, query_pow: int, random_words: int) -> dict[str, Any]:
        security_point = {
            "id": "analytical", "queries": q, "logBlowup": blowup,
            "commitPow": commit_pow, "queryPow": query_pow,
            "logFinalPoly": final_log, "randomCodewords": random_words,
        }
        m = manifest(security_point, base)
        m["fri_max_log_arity"] = log_arity
        validated = calculator_module.validate_manifest(m)
        udr = calculator_module._udr(validated)
        ldr = calculator_module._ldr(validated)
        selected = udr if udr["quantum_bits"] >= ldr["quantum_bits"] else ldr
        value = max(udr["quantum_bits"], ldr["quantum_bits"])
        return {
            "quantum_bits": round(value, 9),
            "floor_quantum_bits": math.floor(value),
            "quantum_proof_status": selected["proof_status"],
        }
    for q, blowup, fold, final, commit_pow, query_pow, random_words, salts, cap_height in itertools.product(*dimension_lists):
        log_arity = int(math.log2(fold))
        final_log = final["logLength"]
        available_fold_depth = 9 + blowup - final_log
        reason = None
        if 7 > 2**blowup:
            reason = "constraint_degree_exceeds_zk_blowup_limit"
        elif log_arity > available_fold_depth:
            reason = "fold_arity_exceeds_available_depth"
        elif cap_height > 9 + blowup:
            reason = "cap_height_exceeds_lde_height"
        elif random_words < 1 or salts < 1:
            reason = "not_complete_hiding"
        if reason is not None:
            counts["unbuildable"] += 1
            build_reasons[reason] = build_reasons.get(reason, 0) + 1
            continue
        upper_key = (q, blowup, log_arity, final_log, random_words)
        upper = upper_security_cache.get(upper_key)
        if upper is None:
            try:
                upper = generated_best(q, blowup, log_arity, final_log, 32, 32, random_words)
            except Exception as error:
                counts["unbuildable"] += 1
                key = f"calculator_rejected:{error}"
                build_reasons[key] = build_reasons.get(key, 0) + 1
                continue
            upper_security_cache[upper_key] = upper
        point = {
            "queries": q, "logBlowup": blowup, "foldFactor": fold,
            "finalPolynomialId": final["id"], "logFinalPoly": final_log,
            "commitPow": commit_pow, "queryPow": query_pow,
            "randomCodewords": random_words, "saltElements": salts, "capHeight": cap_height,
        }
        projected = projection(point, baseline, grid["planGates"])
        if upper["floor_quantum_bits"] < 100:
            counts["security_below_100"] += 1
            if commit_pow == 32 and query_pow == 32 and salts == 8 and cap_height == 0:
                near_misses.append({
                    "parameters": point, "bestGeneratedProvenBits": upper["floor_quantum_bits"],
                    "bestGeneratedProvenBitsExact": upper["quantum_bits"],
                    "generatedProofStatus": upper["quantum_proof_status"],
                    "projectedCompleteCalldataBytes": projected["completeCalldataBytes"],
                    "gateStatus": projected["transactionShapeStatus"],
                    "rejection": "security_below_100_even_at_maximum_grid_grinding",
                })
                near_misses.sort(key=lambda row: (-row["bestGeneratedProvenBitsExact"], row["projectedCompleteCalldataBytes"]))
                del near_misses[24:]
            continue
        exact_key = (q, blowup, log_arity, final_log, commit_pow, query_pow, random_words)
        best = exact_security_cache.get(exact_key)
        if best is None:
            best = generated_best(q, blowup, log_arity, final_log, commit_pow, query_pow, random_words)
            exact_security_cache[exact_key] = best
        bits = best["floor_quantum_bits"]
        if bits < 100:
            counts["security_below_100"] += 1
            if salts == 8 and cap_height == 0:
                near_misses.append({
                    "parameters": point, "bestGeneratedProvenBits": bits,
                    "bestGeneratedProvenBitsExact": best["quantum_bits"],
                    "generatedProofStatus": best["quantum_proof_status"],
                    "projectedCompleteCalldataBytes": projected["completeCalldataBytes"],
                    "gateStatus": projected["transactionShapeStatus"],
                    "rejection": "security_below_100",
                })
                near_misses.sort(key=lambda row: (-row["bestGeneratedProvenBitsExact"], row["projectedCompleteCalldataBytes"]))
                del near_misses[24:]
            continue
        if best["quantum_bits"] >= base["challenge_field_bits"]:
            counts["challenge_ceiling"] += 1
            continue
        if projected["completeCalldataBytes"] > grid["planGates"]["completeCalldataBytesMax"]:
            counts["proof_floor"] += 1
            proof_floor_misses.append({
                "profileId": f"q{q}-b{blowup}-fold{fold}-final{final['id']}-cg{commit_pow}-qg{query_pow}-r{random_words}-s{salts}-cap{cap_height}",
                "parameters": point, "bestGeneratedProvenBits": bits,
                "bestGeneratedProvenBitsExact": best["quantum_bits"],
                "generatedProofStatus": best["quantum_proof_status"],
                "projectedCompleteCalldataBytes": projected["completeCalldataBytes"],
                "projectedCalldataOverageBytes": projected["completeCalldataBytes"] - grid["planGates"]["completeCalldataBytesMax"],
                "gateStatus": projected["transactionShapeStatus"],
                "rejection": "proof_floor_complete_calldata_over_128kib",
                "projection": projected,
            })
            continue
        profile_id = (
            f"q{q}-b{blowup}-fold{fold}-final{final['id']}-"
            f"cg{commit_pow}-qg{query_pow}-r{random_words}-s{salts}-cap{cap_height}"
        )
        proof_survivors.append({
            "profileId": profile_id, "parameters": point,
            "bestGeneratedProvenBits": bits,
            "bestGeneratedProvenBitsExact": best["quantum_bits"],
            "generatedProofStatus": best["quantum_proof_status"],
            "projection": projected,
            "gateStatus": projected["transactionShapeStatus"],
            "securityQualified": False,
        })
    proof_floor_frontier: list[dict[str, Any]] = []
    for candidate in proof_floor_misses:
        if any(dominates(existing, candidate) for existing in proof_floor_frontier):
            continue
        proof_floor_frontier = [existing for existing in proof_floor_frontier if not dominates(candidate, existing)]
        proof_floor_frontier.append(candidate)
    proof_floor_frontier.sort(key=lambda row: (row["projectedCalldataOverageBytes"], -row["bestGeneratedProvenBitsExact"], row["profileId"]))
    proof_floor_misses = proof_floor_frontier
    frontier: list[dict[str, Any]] = []
    for candidate in proof_survivors:
        if any(dominates(existing, candidate) for existing in frontier):
            continue
        frontier = [existing for existing in frontier if not dominates(candidate, existing)]
        frontier.append(candidate)
    counts["retained"] = len(frontier)
    counts["dominated"] = len(proof_survivors) - len(frontier)
    if sum(counts.values()) != exact_count:
        raise RuntimeError(f"analytical filter accounting mismatch: {counts} != {exact_count}")
    return {
        "schemaVersion": 1,
        "classification": "RESEARCH_ONLY_NOT_SECURITY_QUALIFIED",
        "dimensions": dimensions,
        "dimensionCardinalities": {
            "queries": 7, "logBlowup": 4, "foldFactors": 4, "finalPolynomialLengths": 5,
            "commitGrindingBits": 5, "queryGrindingBits": 5, "reviewedHidingRandomCodewords": 4,
            "mmcsSaltElements": 3, "capHeights": 3,
        },
        "cartesianCountFormula": "7*4*4*5*5*5*4*3*3=504000",
        "exactCartesianCount": exact_count,
        "securityCalculatorEvaluations": len(upper_security_cache) + len(exact_security_cache),
        "securityFilterMethod": "Independent calculator UDR/LDR at the grid-maximum 32/32 grinding first; when that generated-proven upper bound is below 100, all 25 lower-grinding combinations reject without redundant evaluation.",
        "filterOrder": ["unbuildable", "security_below_100", "challenge_ceiling", "proof_floor", "dominated", "retained"],
        "filterDefinitions": {
            "unbuildable": {"predicate": "degree > 2^blowup, fold log arity > available depth, cap > LDE height, or non-hiding parameters", "rejectionCount": counts["unbuildable"]},
            "security_below_100": {"predicate": "independent-calculator generated best-proven floor < 100", "rejectionCount": counts["security_below_100"]},
            "challenge_ceiling": {"predicate": "generated best-proven exact bits reaches the 120-bit challenge ceiling", "rejectionCount": counts["challenge_ceiling"]},
            "proof_floor": {"predicate": "projected complete calldata exceeds 131072 bytes", "rejectionCount": counts["proof_floor"]},
            "dominated": {"predicate": "another surviving point is no worse in generated-proven bits, bytes, time, RSS, A/B shape, and active/64/96 gas and strictly better in at least one", "rejectionCount": counts["dominated"]},
        },
        "retainedRejectedFrontierProfiles": proof_floor_misses,
        "rejectionCounts": counts,
        "unbuildableReasons": build_reasons,
        "retainedProfiles": sorted(frontier, key=lambda row: (-row["bestGeneratedProvenBitsExact"], row["projection"]["completeCalldataBytes"], row["profileId"])),
        "nearMisses": near_misses,
        "exactPlanGates": grid["planGates"],
        "retainedGateSummary": {
            "oneTransactionPass": 0,
            "robustTwoTransactionPass": 0,
            "twoTransactionFail": sum(row["gateStatus"] == "TWO_TX_FAIL" for row in proof_floor_misses),
            "reason": "Null/unmeasured complete-transaction gas cannot pass; projected values are bounds only.",
        },
        "winner": None,
        "securityQualifiedProfiles": 0,
    }


def generate_metadata() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    grid = load(GRID)
    base = load((HERE / grid["baseManifest"]).resolve())
    baseline = load((HERE / grid["baselineDistribution"]).resolve())
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    security_dir = OUTPUTS / "security"
    security_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for point in grid["profiles"]:
        m = manifest(point, base)
        mpath = MANIFESTS / f"{point['id']}.json"
        dump(mpath, m)
        report, error = calculator(mpath)
        buildable = error is None
        expected = point.get("expectedBuildable", True)
        if buildable != expected:
            raise RuntimeError(f"{point['id']}: buildability mismatch: {error or 'unexpected success'}")
        if error:
            rows.append({"profileId": point["id"], "buildable": False, "rejection": error, "securityQualified": False})
            continue
        dump(security_dir / f"{point['id']}.json", report)
        best = report["single_target"]["best_proven"]
        projected = projection(point, baseline, grid["planGates"])
        bits = best["floor_quantum_bits"]
        security_status = "SECURITY_BELOW_100" if bits < 100 else "GENERATED_PROVEN_FLOOR_AT_LEAST_100"
        gate = projected["transactionShapeStatus"]
        rows.append({
            "profileId": point["id"], "buildable": True,
            "parameters": point,
            "bestGeneratedProvenBits": bits,
            "bestGeneratedProvenBitsExact": best["quantum_bits"],
            "generatedProofStatus": best["quantum_proof_status"],
            "conditionalAssumptions": best["conditional_assumptions"],
            "securityReport": f"security/{point['id']}.json",
            "projection": projected,
            "securityStatus": security_status,
            "gateStatus": gate,
            "securityQualified": False,
        })
    q32_floor = next(r["bestGeneratedProvenBits"] for r in rows if r["profileId"] == "b4-q32-c16x16-f0-r4")
    q48_floor = next(r["bestGeneratedProvenBits"] for r in rows if r["profileId"] == "b4-q48-c16x16-f0-r4")
    if (q32_floor, q48_floor) != (56, 81):
        raise RuntimeError(f"security-model floor regression: q32={q32_floor}, q48={q48_floor}")
    below = next(r["bestGeneratedProvenBits"] for r in rows if r["profileId"] == "b3-q110-c16x16-f0-r4")
    minimum = next(r["bestGeneratedProvenBits"] for r in rows if r["profileId"] == "b3-q111-c16x16-f0-r4")
    if below >= 100 or minimum < 100:
        raise RuntimeError(f"calculator minimum-100 regression: b3q110={below}, b3q111={minimum}")
    q32_row = next(r for r in rows if r["profileId"] == "b4-q32-c16x16-f0-r4")
    if q32_row["gateStatus"] != "TWO_TX_FAIL":
        raise RuntimeError(f"q32 exact-plan gate regression: {q32_row['gateStatus']}")
    eligible = [row for row in rows if row.get("buildable") and row.get("bestGeneratedProvenBits", 0) >= 100]
    remaining = list(eligible)
    fronts: list[list[str]] = []
    rank = 1
    while remaining:
        front_rows = [a for a in remaining if not any(dominates(b, a) for b in remaining if b is not a)]
        fronts.append([row["profileId"] for row in front_rows])
        for row in front_rows:
            row["paretoRank"] = rank
            row["nondominated"] = rank == 1
        remaining = [row for row in remaining if row not in front_rows]
        rank += 1
    frontier = fronts[0] if fronts else []
    result = {
        "schemaVersion": 1,
        "classification": "RESEARCH_ONLY_NOT_SECURITY_QUALIFIED",
        "calculator": str(CALCULATOR.relative_to(ROOT)),
        "baselineDistribution": str(BASELINE.relative_to(ROOT)),
        "projectionStatus": "All broad-grid proof, timing, RSS, ABI, and gas values are PROJECTED; only fresh anchor files are measured.",
        "q32Floor": q32_floor,
        "q48Floor": q48_floor,
        "minimum100Profile": "b3-q111-c16x16-f0-r4",
        "nondominatedProfiles": frontier,
        "paretoFronts": fronts,
        "winner": None,
        "winnerStatus": "TWO_TX_FAIL" if eligible and all(r["gateStatus"] == "TWO_TX_FAIL" for r in eligible) else "NO_SECURITY_QUALIFIED_WINNER",
        "rows": rows,
    }
    dump(OUTPUTS / "score-table.json", result)
    csv_path = OUTPUTS / "score-table.csv"
    with csv_path.open("w", newline="") as handle:
        fields = ["profile_id", "buildable", "best_generated_proven_bits", "security_status", "pareto_rank", "proof_bytes", "prover_ms", "peak_rss_bytes", "part_a_active_gas", "part_b_active_gas", "active_margin", "gate_status", "security_qualified"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            p = row.get("projection", {})
            gas_a = p.get("gasA", {}).get("active_eip7623_10_40", {})
            gas_b = p.get("gasB", {}).get("active_eip7623_10_40", {})
            writer.writerow({
                "profile_id": row["profileId"], "buildable": row["buildable"],
                "best_generated_proven_bits": row.get("bestGeneratedProvenBits", ""),
                "security_status": row.get("securityStatus", ""),
                "pareto_rank": row.get("paretoRank", ""),
                "proof_bytes": p.get("productionCodecProofBytes", ""), "prover_ms": p.get("projectedProverMs", ""),
                "peak_rss_bytes": p.get("projectedPeakRssBytes", ""), "part_a_active_gas": gas_a.get("projectedGas", ""),
                "part_b_active_gas": gas_b.get("projectedGas", ""), "active_margin": min(gas_a.get("planGateMargin", 12000000), gas_b.get("planGateMargin", 12000000)) if p else "",
                "gate_status": row.get("gateStatus", "UNBUILDABLE"), "security_qualified": False,
            })
    dump(OUTPUTS / "analytical-filter.json", analytical_filter(grid, base, baseline))
    return grid, rows


def run_anchors(grid: dict[str, Any], repetitions: int) -> None:
    for profile in grid["anchorProfiles"]:
        out = OUTPUTS / "anchors" / profile
        command = [
            "cargo", "run", "--release", "--manifest-path", str(PROVER), "--target-dir", str(HERE / ".target"), "--",
            "--manifest", str(MANIFESTS / f"{profile}.json"), "--input", str(FIXED_INPUT), "--out", str(out), "--repetitions", str(repetitions),
        ]
        run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        dump(out / "runner.json", {"command": command, "returnCode": run.returncode, "stdout": run.stdout, "stderr": run.stderr})
        if run.returncode:
            raise RuntimeError(f"anchor {profile} failed closed; see {out / 'runner.json'}")

def summarize_anchors(grid: dict[str, Any]) -> None:
    summaries = []
    for profile in grid["anchorProfiles"]:
        out = OUTPUTS / "anchors" / profile
        runner = load(out / "runner.json")
        if runner["returnCode"] != 0:
            raise RuntimeError(f"cannot accept failed anchor {profile}")
        measured = load(out / "measurements.json")
        reps = measured["repetitions"]
        identities = {rep["proof_identity_keccak256"] for rep in reps}
        if len(reps) < 2 or len(identities) != len(reps) or not all(rep["native_verified"] for rep in reps):
            raise RuntimeError(f"anchor {profile} failed fresh/native verification invariants")
        summary = {
            "profileId": profile,
            "evidenceClass": "MEASURED_NATIVE_RESEARCH_CODEC",
            "repetitions": len(reps),
            "proofsDiffer": measured["proofsDiffer"],
            "researchCanonicalRawBytes": [rep["research_canonical_raw_bytes"] for rep in reps],
            "proveMs": [rep["prove_ms"] for rep in reps],
            "nativeVerifyMs": [rep["native_verify_ms"] for rep in reps],
            "peakRssBytes": [rep["process_peak_rss_bytes"] for rep in reps],
            "uniqueQueryIndices": [rep["unique_query_indices"] for rep in reps],
            "inputFrontierDigests": [rep["input_frontier_digests"] for rep in reps],
            "friFrontierDigests": [rep["fri_frontier_digests"] for rep in reps],
            "abiAndEvmStatus": "PROJECTED_ONLY: no production codec/profile tag or verifier exists for C10",
            "measurement": f"anchors/{profile}/measurements.json",
        }
        summaries.append(summary)
    dump(OUTPUTS / "anchors-summary.json", {
        "schemaVersion": 1,
        "classification": "RESEARCH_ONLY_NOT_SECURITY_QUALIFIED",
        "anchors": summaries,
    })



def write_hashes() -> None:
    paths = [
        GRID, HERE / "run.py", HERE / "ADR.md", HERE / "status.json", HERE / "assumptions.md",
        HERE / "negative-results.json", PROVER, PROVER.parent / "Cargo.lock", PROVER.parent / "src/main.rs", CALCULATOR, BASELINE,
        ROOT / "Cargo.toml", ROOT / "Cargo.lock", ROOT / "crates/pqtc-stark/src/lib.rs",
        ROOT / "crates/pqtc-stark/src/crypto.rs", ROOT / "crates/pqtc-poseidon-air/src/air.rs",
        ROOT / "crates/pqtc-poseidon-air/src/lib.rs", ROOT / "research/gas-rules/rules.json",
    ]
    paths += sorted(MANIFESTS.glob("*.json"))
    records = []
    for path in paths:
        if path.exists():
            records.append({"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    dump(HERE / "source-hashes.json", {"schemaVersion": 1, "algorithm": "sha256", "files": records})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-only", action="store_true", help="regenerate manifests, calculator reports, projections, and hashes without proving")
    parser.add_argument("--repetitions", type=int, default=2)
    args = parser.parse_args()
    if args.repetitions < 2:
        parser.error("--repetitions must be at least 2")
    grid, _ = generate_metadata()
    if not args.metadata_only:
        run_anchors(grid, args.repetitions)
        summarize_anchors(grid)
    write_hashes()
    print(json.dumps({"ok": True, "metadata": "research/fri-pareto/outputs/score-table.json", "freshAnchors": not args.metadata_only, "securityQualified": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
