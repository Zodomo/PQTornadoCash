#!/usr/bin/env python3
"""R2-06 evidence migration, structural calibration and assumption-separated Pareto sets.

Run `python3 research/r2/models/model.py --check` for deterministic boundary checks.
No model prediction authorizes elimination, deployment, or cryptographic qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from codec import byte_model, c10_counts, canonical_v3_model, frontier_work, parse_c10, postcard_model, validate_baseline_ledger

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REGIMES = ("fixed_unqualified", "no_johnson_condition", "conditional_johnson", "externally_reviewed")
FEATURES = ("fixed", "queries", "merkle_hashes", "opened_base_elements", "fold_units")


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def historical_anchors() -> dict:
    """Explicit frozen historical sources; never read a changing R2 output tree."""
    rows, seen = [], set()
    for profile, q, b in (("b4-q32-c16x16-f0-r4", 32, 4), ("b4-q48-c16x16-f0-r4", 48, 4),
                           ("b3-q111-c16x16-f0-r4", 111, 3)):
        path = ROOT/"research/fri-pareto/outputs/anchors"/profile/"measurements.json"
        data = load(path)
        shape = {"queries": q, "trace_width": 190, "quotient_chunks": 16, "random_codewords": 4,
                 "fri_log_arities": [1]*9, "final_poly_len": 1, "cap_height": 0}
        for rep in data["repetitions"]:
            identity = rep["proof_identity_keccak256"]
            if identity in seen:
                raise ValueError("duplicate retained anchor identity")
            seen.add(identity)
            counts = c10_counts(shape, rep["input_frontier_digests"], rep["fri_frontier_digests"])
            exact = byte_model(counts)
            rows.append({"profile_id": profile, "repetition": rep["repetition"], "historical": True,
                         "source": str(path.relative_to(ROOT)), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "proof_identity_keccak256": identity, "measurement_status": "MEASURED",
                         "native_verified_historically": rep["native_verified"], "native_reverified_here": False,
                         "measured_bytes": rep["research_canonical_raw_bytes"], "structural_bytes": exact["total_bytes"],
                         "byte_residual": rep["research_canonical_raw_bytes"]-exact["total_bytes"],
                         "lower_bound_omitting_frontier": byte_model(counts, False)["total_bytes"],
                         "prove_ms": rep["prove_ms"], "complete_transaction_gas": None,
                         "physical_feasibility": "UNKNOWN", "codec": "PQTCC10R1"})
    return {"schema": "pqtc.r2.models.historical-anchors.v1", "rows": rows,
            "formula_validated_on_retained_lengths": all(r["byte_residual"] == 0 for r in rows),
            "fitted_gas": None, "gas_model_status": "NOT_EVALUATED",
            "reason": "Three historical native configurations have no measured alternative EVM workload. No gas coefficients can be fitted.",
            "historical_timings": "Retained two repetitions include first-use effects; not rerun, warmed, or duplicated into new samples."}


def migration(source: Path) -> dict:
    raw = source.read_bytes()
    old = json.loads(raw)
    rows = []
    for index, row in enumerate(old["rows"]):
        projection = row.get("projection", {})
        measured = projection.get("completeTransactionMeasured") is True
        gas = projection.get("completeTransactionGas") if measured else None
        # Historical source has no complete transactions. Preserve actual future observations if supplied.
        rows.append({"source_row": index, "profile_id": row["profileId"], "original_row": row,
                     "original_gate": row.get("gateStatus"),
                     "measurement_status": "MEASURED" if measured and gas is not None else "NOT_EVALUATED",
                     "complete_transaction_gas": gas,
                     "physical_feasibility": "UNKNOWN",
                     "model_status": "UNCALIBRATED_PROJECTION" if projection else "NOT_EVALUATED",
                     "historical_modeled_gate": ("PROJECTED_PASS" if projection.get("planGate", {}).get("robustTwoTransactionProjectedPass") else "PROJECTED_FAIL") if projection else None,
                     "transaction_status": "UNKNOWN", "qualification": "NOT_QUALIFIED",
                     "reason": "Historical not-measured => TWO_TX_FAIL is not performance evidence; projected gate preserved separately."})
    return {"schema": "pqtc.r2.models.migration.v1", "source": str(source),
            "source_sha256": hashlib.sha256(raw).hexdigest(), "historical": True, "rows": rows,
            "source_status": "read_only_original_rows_preserved",
            "source_defects": {"status": "research/fri-pareto/run.py:134-138",
                               "exponential_verifier_multiplier": "research/fri-pareto/run.py:103-107",
                               "hand_chosen_byte_coefficients": "research/fri-pareto/run.py:81-97"}}


def evm_work(shape: dict, query_indices: list[int]) -> dict:
    """Operation counts, not gas. Domain exponent is ONLY reported as prover work."""
    depth = shape["degree_bits"] + shape["log_blowup"]
    cap = shape.get("cap_height", 0)
    q = len(query_indices)
    input_work = frontier_work(query_indices, depth, cap)
    widths = shape["input_matrix_widths"]
    opened = q * sum(sum(batch) for batch in widths)
    merkle = len(widths) * input_work["internal_hashes"]
    folds = 0
    indices = query_indices[:]
    rounds = []
    for log_arity in shape["fri_log_arities"]:
        if not 1 <= log_arity <= 4:
            raise ValueError("unsupported fold arity")
        depth -= log_arity
        indices = [i >> log_arity for i in indices]
        work = frontier_work(indices, depth, cap)
        merkle += work["internal_hashes"]
        arity = 1 << log_arity
        # Arity*log2(arity) butterfly work proxy, calibrated per implementation, not exact multiplication count.
        folds += q * arity * log_arity
        rounds.append({"depth": depth, "arity": arity, **work})
    return {"features": dict(zip(FEATURES, (1, q, merkle, opened, folds))),
            "fri_rounds": rounds, "input_depth": shape["degree_bits"] + shape["log_blowup"],
            "prover_lde_rows": 1 << (shape["degree_bits"] + shape["log_blowup"]),
            "state_and_payout_gas": None, "complete_transaction_gas": None,
            "fixed_overhead": "intercept within exact AIR/transcript/codec implementation group",
            "fold_units_kind": "structural_work_proxy_not_exact_EVM_opcode_count"}


def least_squares(xs: list[list[float]], ys: list[float]) -> list[float]:
    """Small QR fit; reject rank-deficient designs instead of inventing coefficients."""
    n, p = len(xs), len(xs[0])
    if n <= p:
        raise ValueError("need more independent training profiles than fitted coefficients")
    columns = [[row[j] for row in xs] for j in range(p)]
    scales = [max(abs(v) for v in column) for column in columns]
    if any(s == 0 for s in scales):
        raise ValueError("unidentifiable zero feature")
    orthogonal, upper = [], [[0.0]*p for _ in range(p)]
    for j, col in enumerate(columns):
        v = [x/scales[j] for x in col]
        for i, basis in enumerate(orthogonal):
            upper[i][j] = sum(x*y for x, y in zip(basis, v))
            v = [x-upper[i][j]*y for x, y in zip(v, basis)]
        norm = math.sqrt(sum(x*x for x in v))
        if norm < 1e-9:
            raise ValueError("rank-deficient observed design")
        upper[j][j] = norm
        orthogonal.append([x/norm for x in v])
    rhs = [sum(x*y for x, y in zip(col, ys)) for col in orthogonal]
    beta = [0.0]*p
    for i in reversed(range(p)):
        beta[i] = (rhs[i]-sum(upper[i][j]*beta[j] for j in range(i+1, p)))/upper[i][i]
    return [x/s for x, s in zip(beta, scales)]


def calibration(rows: list[dict], feature_names: list[str], target: str) -> dict:
    if not feature_names or any(f not in FEATURES for f in feature_names):
        raise ValueError("declare justified structural features explicitly")
    identities = [r["proof_sha256"] for r in rows]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate proof rows are not independent samples")
    if any(r["measurement_status"] != "MEASURED" or r.get(target) is None for r in rows):
        raise ValueError("calibration accepts only actual measured target values")
    groups = {(r["relation"], r["codec"], r["regime"], r["implementation_id"], r["metric_scope"]) for r in rows}
    if len(groups) != 1:
        raise ValueError("do not pool relation/codec/regime/implementation/measurement scopes")
    train = [r for r in rows if r["split"] == "train"]
    held = [r for r in rows if r["split"] == "held_out"]
    if len(train) + len(held) != len(rows) or not held:
        raise ValueError("predeclared held-out evidence required")
    train_profiles = {r["profile_id"] for r in train}
    if train_profiles & {r["profile_id"] for r in held}:
        raise ValueError("held-out profile leaks into training repetitions")
    # Profile medians avoid pseudo-replicating repeated proofs as extra design points.
    import statistics
    xs, ys = [], []
    for profile in sorted(train_profiles):
        reps = [r for r in train if r["profile_id"] == profile]
        xs.append([statistics.median(r["features"][f] for r in reps) for f in feature_names])
        ys.append(statistics.median(r[target] for r in reps))
    base = {"schema": "pqtc.r2.models.calibration.v1", "target": target, "features": feature_names,
            "group": list(next(iter(groups))), "training_profiles": sorted(train_profiles),
            "held_out_profiles": sorted({r["profile_id"] for r in held}),
            "elimination_authorized": False, "complete_transaction_gas": None}
    try:
        beta = least_squares(xs, ys)
    except (ValueError, IndexError) as error:
        return {**base, "measurement_status": "UNCALIBRATED_PROJECTION", "reason": str(error),
                "coefficients": None, "held_out_residuals": []}
    domain = {f: [min(row[j] for row in xs), max(row[j] for row in xs)] for j, f in enumerate(feature_names)}
    residuals = []
    for r in rows:
        inside = all(lo <= r["features"][f] <= hi for f, (lo, hi) in domain.items())
        prediction = sum(b*r["features"][f] for b, f in zip(beta, feature_names)) if inside else None
        residuals.append({"proof_sha256": r["proof_sha256"], "profile_id": r["profile_id"], "split": r["split"],
                          "observed": r[target], "prediction": prediction,
                          "measurement_status": "CALIBRATED_PROJECTION" if inside else "OUT_OF_MODEL_DOMAIN",
                          "residual": r[target]-prediction if prediction is not None else None})
    valid = [r for r in residuals if r["split"] == "held_out" and r["residual"] is not None]
    return {**base, "measurement_status": "CALIBRATED_PROJECTION" if valid else "OUT_OF_MODEL_DOMAIN",
            "coefficients": dict(zip(feature_names, beta)), "observed_domain": domain,
            "domain_rule": "closed training feature intervals within exact group; no extrapolation; prioritization only",
            "residuals": residuals, "held_out_residuals": [r for r in residuals if r["split"] == "held_out"],
            "held_out_rmse": math.sqrt(sum(r["residual"]**2 for r in valid)/len(valid)) if valid else None,
            "held_out_max_absolute_error": max((abs(r["residual"]) for r in valid), default=None)}


def pareto(rows: list[dict], metrics: list[str]) -> dict:
    outputs = []
    for regime in REGIMES:
        for status in ("MEASURED", "CALIBRATED_PROJECTION", "UNCALIBRATED_PROJECTION"):
            candidates = [r for r in rows if r["regime"] == regime and r["measurement_status"] == status]
            eligible = [r for r in candidates if all(r.get(m) is not None for m in metrics)]
            frontier = [r for r in eligible if not any(
                all(o[m] <= r[m] for m in metrics) and any(o[m] < r[m] for m in metrics) for o in eligible)]
            outputs.append({"regime": regime, "measurement_status": status, "minimized_metrics": metrics,
                            "frontier_ids": [r["id"] for r in frontier],
                            "missing_metric_ids": [r["id"] for r in candidates if r not in eligible]})
    return {"schema": "pqtc.r2.models.pareto.v1", "sets": outputs, "qualification": "NOT_QUALIFIED",
            "unknown_complete_transactions_never_ranked_as_zero": True}


def field_continuation(inventories: list[dict]) -> dict:
    """Quantified entry decision, never a six-way scalar-kernel ranking."""
    narrow = [r for r in inventories if r.get("complete_native_verified") is True and r.get("narrow_relation") is True]
    measured = [r for r in narrow if r.get("nonoverlapping_evm_arithmetic_gas") is not None and r.get("evm_execution_gas")]
    fractions = [{"id": r["id"], "arithmetic_gas": r["nonoverlapping_evm_arithmetic_gas"],
                  "execution_gas": r["evm_execution_gas"],
                  "arithmetic_fraction": r["nonoverlapping_evm_arithmetic_gas"]/r["evm_execution_gas"],
                  "max_total_speedup_if_arithmetic_free": (r["evm_execution_gas"]/(r["evm_execution_gas"]-r["nonoverlapping_evm_arithmetic_gas"]))
                    if r["evm_execution_gas"] > r["nonoverlapping_evm_arithmetic_gas"] else None} for r in measured]
    if any(not 0 <= row["arithmetic_fraction"] <= 1 for row in fractions):
        raise ValueError("arithmetic attribution must be a nonoverlapping execution subset")
    warranted = any(r["arithmetic_fraction"] >= 0.25 for r in fractions)
    return {"schema": "pqtc.r2.models.field-decision.v1", "entered_candidates": 0,
            "maximum_candidates": 1, "narrow_complete_proof_count": len(narrow),
            "usable_nonoverlapping_evm_inventories": len(measured), "quantified_inventory": fractions,
            "entry_policy": "Measured narrow-relation arithmetic >=25% of execution before a field port; threshold is scheduling policy, not theorem.",
            "decision": "CONTINUE_EXPERIMENT" if warranted else "NOT_READY_FOR_BUILD_SELECTION",
            "status": "NOT_EVALUATED", "selected_alternative": None,
            "reason": ("One extension continuation is quantitatively warranted, but no complete alternate proof/EVM workload supplied; not entered." if warranted else
                       "Not entered: no measured arithmetic bottleneck meeting the declared threshold. Missing inventories are not evidence of field efficiency."),
            "required_if_entered": ["supported independently checked irreducible polynomial and basis", "complete hiding native proof",
                                    "warmup dot-product inversion and actual-arity FRI-fold workloads", "EVM arithmetic and codec measurements",
                                    "new constants/encoding/cryptanalysis or explicit nonnative cost for changed base field"],
            "historical_F0_F5": "diagnostic only, not candidate-ranking evidence"}


def checks():
    assert frontier_work([0, 1], 3)["frontier_digests"] == 2
    assert frontier_work([0, 0], 3)["frontier_digests"] == 3
    assert frontier_work([0, 1], 3, 2)["frontier_digests"] == 0
    c = canonical_v3_model({"queries": 32, "unique_queries": 32, "random_codewords": 4})
    assert c["measurement_status"] == "EXACT_ANALYTICAL_BOUND"
    exact = canonical_v3_model({"queries": 32, "unique_queries": 32, "random_codewords": 4,
                               "half_frontier_digests": [[1]*12, [2]*12]})
    assert exact["total_bytes"] - c["total_bytes"] == 36*64
    assert sum(v for k, v in exact["parts"][0]["sections"].items() if k.startswith("repeated_global_")) == 9208
    assert math.isclose(least_squares([[1, 0], [1, 1], [1, 2]], [3, 5, 7])[0], 3)
    try:
        least_squares([[1, 2], [1, 2], [1, 2]], [1, 2, 3])
    except ValueError:
        pass
    else:
        raise AssertionError("rank-deficient gas fit accepted")
    rows = [{"id": "unknown", "regime": "fixed_unqualified", "measurement_status": "MEASURED", "gas": None}]
    assert pareto(rows, ["gas"])["sets"][0]["frontier_ids"] == []
    scalar_ledger = {"name": "unsigned-scalars", "bytes": 4, "children": []}
    pc = postcard_model(b"\x00\x7f\x80\x01", scalar_ledger)
    assert pc["scalar_width_histogram"][1] == 2 and pc["scalar_width_histogram"][2] == 1
    assert pc["lower_bound"]["bytes"] == 3
    try:
        postcard_model(b"\x80\x00", {"name": "bad-varint", "bytes": 2, "children": []})
    except ValueError:
        pass
    else:
        raise AssertionError("noncanonical postcard varint accepted")
    print("R2-06 structural, frontier, rank, and unknown-value checks passed")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    p.add_argument("--historical", action="store_true")
    p.add_argument("--migration", type=Path)
    p.add_argument("--proof", type=Path)
    p.add_argument("--canonical-shape", type=Path)
    p.add_argument("--baseline-ledger", type=Path)
    p.add_argument("--fit", type=Path)
    p.add_argument("--features", default="fixed,merkle_hashes,opened_base_elements,fold_units")
    p.add_argument("--target", default="evm_execution_gas")
    p.add_argument("--pareto", type=Path)
    p.add_argument("--metrics", default="proof_bytes,prove_ms")
    p.add_argument("--field-inventory", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.check:
        checks()
        return
    if args.historical:
        result = historical_anchors()
    elif args.migration:
        result = migration(args.migration)
    elif args.proof:
        result = parse_c10(args.proof.read_bytes())
    elif args.canonical_shape:
        result = canonical_v3_model(load(args.canonical_shape))
    elif args.baseline_ledger:
        result = validate_baseline_ledger(load(args.baseline_ledger))
    elif args.fit:
        result = calibration(load(args.fit), args.features.split(","), args.target)
    elif args.pareto:
        result = pareto(load(args.pareto), args.metrics.split(","))
    elif args.field_inventory:
        result = field_continuation(load(args.field_inventory))
    else:
        p.error("select --check or one input operation")
    if not args.output:
        p.error("--output required")
    dump(args.output, result)


if __name__ == "__main__":
    main()
