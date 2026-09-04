#!/usr/bin/env python3
"""Evaluate explicit R2-09 prerequisite evidence, never promote a historical smoke."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REQUIREMENTS = {
    "flock_veil": ["upstream_supported_m21_config", "exact_keccak44_control_verified", "exact_glue_relation", "complete_hiding_construction"],
    "stir": ["concrete_hiding_construction_or_zk_inner_composition", "compatible_application_relation"],
    "circle": ["concrete_hiding_construction_or_zk_inner_composition", "compatible_application_relation_and_field"],
    "recursion": ["complete_exact_inner_hiding_proof", "adequate_exact_inner_soundness", "direct_verification_measured_bottleneck", "compatible_verifier_of_exact_inner_not_fibonacci", "both_layer_error_and_transcript_accounting", "proof_only_outer_witness_inventory", "outer_privacy_composition_argument"],
    "aggregation": ["complete_individual_hiding_proof", "plausible_outer_proof_path", "proofs_and_public_statements_only", "all_payouts_nullifiers_and_failure_handling"],
    "l2_exact_candidate": ["exact_candidate_payload"],
    "hardware_expansion": ["complete_native_candidate_proof"],
}
HISTORICAL = {
    "flock_veil": "research/candidates/C70-flock-veil/batch-capacity.json",
    "stir": "research/candidates/C30-stir/manifest.json",
    "circle": "research/candidates/C40-circle/manifest.json",
    "recursion": "research/candidates/C60-recursion/manifest.json",
    "aggregation": "research/aggregation/manifest.json",
}


def evaluate(document):
    unknown = set(document) - set(REQUIREMENTS)
    if unknown:
        raise ValueError(f"unknown branches: {sorted(unknown)}")
    rows = []
    for branch, required in REQUIREMENTS.items():
        supplied = document.get(branch, {})
        if set(supplied) - set(required):
            raise ValueError(f"unknown prerequisite for {branch}")
        facts = {}
        for key in required:
            fact = supplied.get(key)
            if fact is None:
                facts[key] = {"satisfied": None, "evidence": None}
                continue
            if not isinstance(fact, dict) or fact.get("satisfied") not in (True, False, None):
                raise ValueError(f"invalid evidence fact: {branch}.{key}")
            if fact.get("satisfied") is not None:
                artifact = fact.get("artifact")
                if not artifact or not isinstance(fact.get("sha256"), str) or not fact.get("scope"):
                    raise ValueError(f"non-null claims need artifact, sha256 and scope: {branch}.{key}")
                path = (ROOT / artifact).resolve()
                if not path.is_relative_to(ROOT / "research") or not path.is_file():
                    raise ValueError("evidence must be an explicit research artifact")
                if hashlib.sha256(path.read_bytes()).hexdigest() != fact["sha256"]:
                    raise ValueError(f"changed evidence artifact: {artifact}")
            facts[key] = fact
        entered = all(facts[key].get("satisfied") is True for key in required)
        rows.append({"branch": branch, "gate_status": "ENTERABLE_NOT_EXECUTED" if entered else "NOT_ENTERED",
                     "measurement_status": "NOT_EVALUATED", "decision_status": "CONTINUE_EXPERIMENT" if entered else "NOT_READY_FOR_BUILD_SELECTION",
                     "architecture_failed": None, "prerequisites": facts,
                     "unmet_or_unknown": [k for k in required if facts[k].get("satisfied") is not True],
                     "historical_anchor": HISTORICAL.get(branch), "performance": None})
    rows.append({"branch": "l2_retained_baseline_diagnostic", "gate_status": "ENTERABLE_NOT_EXECUTED",
                 "measurement_status": "NOT_EVALUATED", "decision_status": "CONTINUE_EXPERIMENT",
                 "architecture_failed": None, "historical_anchor": "research/r2/conditional/inputs.json",
                 "reason": "Exact retained A/B proof and ABI bytes are available; only local source-pinned envelope diagnostic authorized."})
    return {"schema": "pqtc.r2.conditional-gates.v1", "policy": "research/r2/governance/evidence-policy.json",
            "evidence_semantics": "Supplied hash-bound scoped claims are recorded, not independently certified by this evaluator. No claim is inferred from a filename, upstream smoke, or a missing measurement.",
            "rows": rows,
            "source_watch": {"stir": "Historical Plonky3 3152b14a89067c83775a8076cc262ffc48a1fd7c TwoAdicStirPcs non-hiding control remains non-private.",
                             "circle": "Historical same-pin CirclePcs non-hiding API and field mismatch; missing hiding is not architecture failure.",
                             "recursion": "Historical 34e3a2c3837834a7bf98a0b65063e0180e7fbb7b Fibonacci --zk ignored; upstream P3 0.7 vs baseline 0.6. Never counted as exact PQTC recursion.",
                             "veil": "Historical 6d7ee5c091ad19e957a5faa5869de8739a76aa78 KoalaBear-degree4 stacked PCS is not Flock binary-field Ligerito."},
            "aggregation_schedule_if_entered": [2, 4, 8],
            "outer_witness_policy": {"allowed": ["already-hiding inner proofs", "public statements and verification data"],
                                     "forbidden": ["note secrets", "unmasked application traces", "cross-user raw witnesses"]},
            "recursion_soundness_note": "Recursion cannot strengthen a forgeable inner proof; account for both layers before entry."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, help="optional explicit per-branch prerequisite records; absent facts remain null")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(json.loads(args.evidence.read_text()) if args.evidence else {})
    output = args.output.resolve()
    if not output.is_relative_to(HERE):
        parser.error("output must remain under research/r2/conditional")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
