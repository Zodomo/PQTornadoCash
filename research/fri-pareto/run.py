#!/usr/bin/env python3
"""Regenerate SP-50 manifests/projections and, unless requested otherwise, fresh anchors."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
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


def projection(point: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    q = point["queries"]
    b = point["logBlowup"]
    r = point["randomCodewords"]
    final_log = point["logFinalPoly"]
    base_proof = baseline["distributions"]["raw_proof_bytes"]["p50"]
    # Measured q32 center plus explicit linear components. The 5,904 byte/query
    # coefficient separates a 20,012-byte duplicated-global intercept from the
    # q32 median. Blowup adds one 64-byte digest per query for each of three
    # input frontiers and nine FRI frontiers. Hiding adds 4-byte leaf values in
    # 19 batches plus 16-byte global openings; the final polynomial is extension fields.
    query_component = 5904 * q
    fixed_component = 20012
    blowup_component = (b - 4) * q * 12 * 64
    hiding_component = (r - 4) * (q * 19 * 4 + 19 * 16)
    final_component = ((1 << final_log) - 1) * 16
    proof_bytes = max(0, round(fixed_component + query_component + blowup_component + hiding_component + final_component))
    ratio_a = 108326 / 212204
    part_a = round(proof_bytes * ratio_a)
    part_b = proof_bytes - part_a
    calldata_a = part_a + 318
    calldata_b = part_b + 350
    zero_fraction = baseline["distributions"]["zero_bytes"]["p50"] / base_proof
    zeros_a = round(calldata_a * zero_fraction)
    zeros_b = round(calldata_b * zero_fraction)
    nonzeros_a = calldata_a - zeros_a
    nonzeros_b = calldata_b - zeros_b
    q_scale = q / 32
    domain_scale = 2 ** (b - 4)
    regular_a = round(baseline["distributions"]["a_total"]["p50"] * q_scale * (0.35 + 0.65 * domain_scale))
    regular_b = round(baseline["distributions"]["b_total"]["p50"] * q_scale * (0.35 + 0.65 * domain_scale))

    def scenarios(z: int, n: int, regular: int) -> dict[str, Any]:
        floors = {
            "active_eip7623_10_40": 21000 + 10 * z + 40 * n,
            "scheduled_unactivated_64_64": 21000 + 64 * (z + n),
            "draft_unscheduled_96_96": 21000 + 96 * (z + n),
        }
        return {key: {"calldataFloorGas": value, "projectedGas": max(regular, value), "eip7825Margin": CAP - max(regular, value)} for key, value in floors.items()}

    gas_a = scenarios(zeros_a, nonzeros_a, regular_a)
    gas_b = scenarios(zeros_b, nonzeros_b, regular_b)
    active_a = gas_a["active_eip7623_10_40"]["projectedGas"]
    active_b = gas_b["active_eip7623_10_40"]["projectedGas"]
    combined = active_a + active_b - 21000
    if active_a > CAP or active_b > CAP:
        tx_status = "TWO_TX_FAIL"
    elif combined > CAP:
        tx_status = "ONE_TX_FAIL"
    else:
        tx_status = "ONE_TX_PASS"
    prove_ms = round(baseline["distributions"]["prove_wall_ms"]["p50"] * (0.50 + 0.50 * domain_scale) * (0.70 + 0.30 * q_scale), 3)
    rss = round(baseline["distributions"]["peak_rss_bytes"]["p50"] * (0.60 + 0.40 * domain_scale))
    return {
        "evidenceClass": "PROJECTED_BASELINE_REGRESSION_NOT_MEASURED",
        "formulaVersion": 1,
        "baseline": {"runs": 60, "proofBytesP50": base_proof, "q": 32, "logBlowup": 4},
        "productionCodecProofBytes": proof_bytes,
        "partABytes": part_a,
        "partBBytes": part_b,
        "abiCalldataABytes": calldata_a,
        "abiCalldataBBytes": calldata_b,
        "projectedProverMs": prove_ms,
        "projectedPeakRssBytes": rss,
        "gasA": gas_a,
        "gasB": gas_b,
        "activeCombinedOneTransactionGas": combined,
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
        projected = projection(point, baseline)
        bits = best["floor_quantum_bits"]
        if bits < 100:
            gate = "SECURITY_BELOW_100"
        else:
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
        fields = ["profile_id", "buildable", "best_generated_proven_bits", "pareto_rank", "proof_bytes", "prover_ms", "peak_rss_bytes", "part_a_active_gas", "part_b_active_gas", "active_margin", "gate_status", "security_qualified"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            p = row.get("projection", {})
            gas_a = p.get("gasA", {}).get("active_eip7623_10_40", {})
            gas_b = p.get("gasB", {}).get("active_eip7623_10_40", {})
            writer.writerow({
                "profile_id": row["profileId"], "buildable": row["buildable"],
                "best_generated_proven_bits": row.get("bestGeneratedProvenBits", ""),
                "pareto_rank": row.get("paretoRank", ""),
                "proof_bytes": p.get("productionCodecProofBytes", ""), "prover_ms": p.get("projectedProverMs", ""),
                "peak_rss_bytes": p.get("projectedPeakRssBytes", ""), "part_a_active_gas": gas_a.get("projectedGas", ""),
                "part_b_active_gas": gas_b.get("projectedGas", ""), "active_margin": min(gas_a.get("eip7825Margin", CAP), gas_b.get("eip7825Margin", CAP)) if p else "",
                "gate_status": row.get("gateStatus", "UNBUILDABLE"), "security_qualified": False,
            })
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
