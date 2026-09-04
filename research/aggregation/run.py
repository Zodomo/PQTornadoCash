#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from model import (
    BATCH_SIZES,
    DENOMINATION,
    PROOF_DESIGNS,
    SCHEDULING_POLICIES,
    USER_TOPOLOGIES,
    Aggregator,
    BuiltBatch,
    FixedWindowBatcher,
    ModelIndividualProofBackend,
    ProofSubmission,
    PublicStatement,
    Reject,
    Settlement,
    ThresholdBatcher,
    mutate_statement,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "outputs/results.json"
BASELINE = ROOT / "research/candidates/v03-baseline/gas/measured-summary.json"
TOTAL_REASON = "MISSING_ACCEPTED_HIDING_INNER_AND_OUTER_PROOF_METRICS; COMPONENTS_ARE_NOT_ADDITIVE_FULL_SETTLEMENT"


def address(value: int) -> bytes:
    return value.to_bytes(20, "big")


def digest(label: bytes, value: int) -> bytes:
    return hashlib.sha512(label + value.to_bytes(8, "big")).digest()


def submissions(count: int, topology: str, offset: int = 0) -> list[ProofSubmission]:
    rows: list[ProofSubmission] = []
    for i in range(count):
        value = offset + i + 1
        statement = PublicStatement(
            root=digest(b"SP70-ROOT", value % 3),
            nullifier=digest(b"SP70-NULLIFIER", value),
            recipient=address(0x1000 if topology == "SAME_USER_MULTI_NOTE" else 0x1000 + value),
            relayer=address(0x2000 if topology == "SAME_USER_MULTI_NOTE" else 0x2000 + value),
            fee=10**16,
        )
        proof = ModelIndividualProofBackend.prove_locally(statement, b"user-local-note-witness-" + value.to_bytes(8, "big"))
        rows.append(ProofSubmission(statement, proof))
    return rows


def build_with(identity: int, rows: list[ProofSubmission], count: int) -> tuple[Aggregator, BuiltBatch]:
    aggregator = Aggregator(address(identity))
    if not all(aggregator.submit(row) for row in rows):
        raise AssertionError("valid model submission rejected")
    return aggregator, aggregator.build(count)


def must_reject(label: str, action) -> str:
    try:
        action()
    except Reject:
        return label
    raise AssertionError(f"attack accepted: {label}")


def safety_suite(count: int, topology: str) -> dict[str, Any]:
    source = submissions(count + 1, topology, count * 100)
    aggregator, built = build_with(0xA001, source, count)
    settlement = Settlement()
    recipient_before = built.statements[0].recipient
    credits_expected = count * DENOMINATION
    settled = settlement.settle(address(0xDEAD), built)  # arbitrary front-run caller
    if settled != built.batch_id or sum(settlement.credits.values()) != credits_expected:
        raise AssertionError("settlement conservation failed")
    if recipient_before not in settlement.credits:
        raise AssertionError("front-run changed recipient")

    rejects = [must_reject("replay_or_spent_nullifier", lambda: settlement.settle(address(0xBEEF), built))]
    for field, value in (
        ("recipient", address(0x7777)),
        ("relayer", address(0x8888)),
        ("fee", 0),
        ("root", digest(b"MUTATED-ROOT", count)),
        ("nullifier", digest(b"MUTATED-NULLIFIER", count)),
    ):
        fresh = Settlement()
        rejects.append(must_reject(f"alter_{field}", lambda f=field, v=value, s=fresh: s.settle(address(1), mutate_statement(built, 0, **{f: v}))))

    if count > 1:
        reordered = replace(built, statements=tuple(reversed(built.statements)))
        rejects.append(must_reject("noncanonical_order", lambda: Settlement().settle(address(1), reordered)))

    duplicate_source = submissions(max(count, 2), topology, 50_000 + count)
    if count == 1:
        duplicate_rows = [duplicate_source[0]]
    else:
        duplicate_statement = replace(duplicate_source[1].statement, nullifier=duplicate_source[0].statement.nullifier)
        duplicate_rows = [duplicate_source[0], ProofSubmission(duplicate_statement, ModelIndividualProofBackend.prove_locally(duplicate_statement, b"second-local-witness")), *duplicate_source[2:count]]
    _, duplicate_batch = build_with(0xA002, duplicate_rows, count)
    if count > 1:
        rejects.append(must_reject("duplicate_nullifier_before_payout", lambda: Settlement().settle(address(2), duplicate_batch)))

    # A malformed individual proof is rejected before batch construction, while
    # every good submission remains usable by either permissionless aggregator.
    bad = ProofSubmission(source[-1].statement, b"bad")
    if aggregator.submit(bad):
        raise AssertionError("bad individual proof entered accepted set")
    second, rebuilt = build_with(0xA003, source, count)
    if second.identity == aggregator.identity or rebuilt.batch_id != built.batch_id:
        raise AssertionError("permissionless rebuild failed")

    unfilled = Aggregator(address(0xA004))
    for row in source[: max(0, count - 1)]:
        unfilled.submit(row)
    rejects.append(must_reject("unfilled_threshold", lambda: unfilled.build(count)))

    # A rejecting payee cannot roll back settlement and can retry the pull claim.
    payee = next(iter(settlement.credits))
    credit = settlement.credits[payee]
    rejects.append(must_reject("rejecting_receiver_claim", lambda: settlement.claim(payee, False)))
    if settlement.credits[payee] != credit or settlement.claim(payee, True) != credit:
        raise AssertionError("pull-payment recovery failed")

    return {
        "N": count,
        "user_topology": topology,
        "model_result": "PASS",
        "attacks_rejected": rejects,
        "front_run_result": "CALLER_CANNOT_REDIRECT_BOUND_PULL_CREDITS",
        "bad_proof_recovery": "BAD_SUBMISSION_EXCLUDED; GOOD_PROOFS_REMAIN_REBATCHABLE",
        "censorship_recovery": "SAME_PROOF_PACKAGE_ACCEPTED_BY_SECOND_PERMISSIONLESS_AGGREGATOR",
        "unfilled_batch_exit": "NONCUSTODIAL_SUBMISSION; USER_RETAINS_INDIVIDUAL_PATH",
        "payout_failure": "FAILED_PULL_CLAIM_RETAINS_CREDIT_FOR_RETRY",
        "privacy_boundary": "AGGREGATOR_API_RECEIVED_PROOF_SUBMISSION_ONLY",
        "proof_metadata_linkage": "NOT_EVALUATED_NO_ACCEPTED_ZERO_KNOWLEDGE_PROOF",
    }


def scheduling_suite(count: int) -> dict[str, Any]:
    rows = submissions(count, "UNRELATED_USERS", 80_000 + count)

    threshold_aggregator = Aggregator(address(0xB001))
    threshold = ThresholdBatcher(count, threshold_aggregator)
    for row in rows[:-1]:
        threshold_aggregator.submit(row)
    before_threshold = must_reject("threshold_not_met", threshold.trigger)
    threshold_aggregator.submit(rows[-1])
    threshold_batch = threshold.trigger()

    fixed_aggregator = Aggregator(address(0xB002))
    for row in rows:
        fixed_aggregator.submit(row)
    fixed = FixedWindowBatcher(count, opened_at=1_000, duration=300, aggregator=fixed_aggregator)
    early_close = must_reject("fixed_window_early_close", lambda: fixed.close(1_299))
    fixed_batch = fixed.close(1_300)

    alternate = Aggregator(address(0xB003))
    for row in rows:
        alternate.submit(row)
    alternate_batch = alternate.build(count)
    if threshold_batch.batch_id != fixed_batch.batch_id or fixed_batch.batch_id != alternate_batch.batch_id:
        raise AssertionError("policy or aggregator identity changed canonical batch")
    return {
        "N": count,
        "threshold_triggered": {"before_threshold": before_threshold, "at_threshold": "BUILT_IMMEDIATELY"},
        "fixed_window": {"deadline": 1_300, "early_close": early_close, "at_deadline": "BUILT"},
        "permissionless_multiple_aggregators": "IDENTICAL_CANONICAL_BATCH_FROM_THREE_UNREGISTERED_IDENTITIES",
        "submission_exclusivity": "NONE",
    }


def measurement_row(count: int, design: str, topology: str) -> dict[str, Any]:
    if design == "RECURSIVE_BINARY_TREE":
        structure = {
            "tree_depth": count.bit_length() - 1,
            "leaf_individual_proofs": count,
            "internal_aggregation_nodes": count - 1,
            "class": "EXACT_COMBINATORIAL_STRUCTURE_NOT_PROOF_BENCHMARK",
        }
    elif design == "FLAT_OUTER_PROOF":
        structure = {
            "outer_relation_individual_verifications": count,
            "outer_relation_depth": 1,
            "class": "EXACT_COMBINATORIAL_STRUCTURE_NOT_PROOF_BENCHMARK",
        }
    else:
        structure = {
            "initial_accumulators": 1 if count else 0,
            "sequential_fold_steps": max(0, count - 1),
            "individual_instances_absorbed": count,
            "class": "EXACT_COMBINATORIAL_STRUCTURE_NOT_PROOF_BENCHMARK",
        }
    return {
        "N": count,
        "proof_design": design,
        "user_topology": topology,
        "design_structure": structure,
        "outer_proof_bytes": None,
        "outer_proof_bytes_status": "NOT_EVALUATED_NO_ACCEPTED_HIDING_INNER_PROOF",
        "aggregate_proving_time_ms": None,
        "aggregate_peak_rss_bytes": None,
        "aggregate_verification_time_ms": None,
        "verifier_gas": None,
        "proof_metrics_status": "NOT_EVALUATED",
        "settlement_execution_gas": None,
        "full_calldata_bytes": None,
        "full_calldata_zero_bytes": None,
        "full_calldata_nonzero_bytes": None,
        "payout_component_gas": None,
        "nullifier_component_gas": None,
        "public_only_calldata_bytes": None,
        "successful_pull_claim_gas": None,
        "component_status": "NOT_EVALUATED_FOUNDRY_HARNESS_PREPARED",
        "total_gas": {"active_eip7623_10_40": None, "uniform_64": None, "uniform_96": None},
        "total_reason": TOTAL_REASON,
        "gas_per_withdrawal": None,
        "failure_recovery_gas": None,
        "minimum_economical_N": None,
        "gate": "STOP_BY_DEPENDENCY",
    }


def validate_result(result: dict[str, Any]) -> None:
    if result.get("schema") != "sp70-aggregation-results-v1":
        raise Reject("wrong result schema")
    if result.get("batch_sizes") != list(BATCH_SIZES):
        raise Reject("incomplete N grid")
    scheduling = result.get("scheduling_results")
    if not isinstance(scheduling, list) or [row.get("N") for row in scheduling] != list(BATCH_SIZES):
        raise Reject("incomplete scheduling grid")
    safety = result.get("safety")
    safety_keys = {(row.get("N"), row.get("user_topology")) for row in safety} if isinstance(safety, list) else set()
    if safety_keys != {(n, topology) for n in BATCH_SIZES for topology in USER_TOPOLOGIES}:
        raise Reject("incomplete safety grid")
    rows = result.get("measurements")
    expected = len(BATCH_SIZES) * len(PROOF_DESIGNS) * len(USER_TOPOLOGIES)
    if not isinstance(rows, list) or len(rows) != expected:
        raise Reject("incomplete measurement matrix")
    keys = {(row.get("N"), row.get("proof_design"), row.get("user_topology")) for row in rows}
    expected_keys = {(n, design, topology) for n in BATCH_SIZES for design in PROOF_DESIGNS for topology in USER_TOPOLOGIES}
    if keys != expected_keys:
        raise Reject("measurement matrix keys incomplete")
    for row in rows:
        totals = row.get("total_gas")
        if not isinstance(totals, dict) or set(totals) != {"active_eip7623_10_40", "uniform_64", "uniform_96"}:
            raise Reject("invalid total schedules")
        complete_terms = all(
            isinstance(row.get(field), int) and row[field] >= 0
            for field in ("outer_proof_bytes", "verifier_gas", "settlement_execution_gas", "full_calldata_bytes", "full_calldata_zero_bytes", "full_calldata_nonzero_bytes")
        )
        if any(value is not None for value in totals.values()) and not complete_terms:
            raise Reject("incomplete metrics masquerading as totals")
        if not complete_terms:
            if any(value is not None for value in totals.values()) or row.get("gas_per_withdrawal") is not None or row.get("total_reason") != TOTAL_REASON:
                raise Reject("missing metrics must retain null totals and reason")
        if row.get("gate") != "STOP_BY_DEPENDENCY":
            raise Reject("aggregation gate must stop by dependency")
    if result.get("decision", {}).get("individual_path_requirement") != "REQUIRED; AGGREGATION_CANNOT_REPLACE_IT":
        raise Reject("individual path requirement missing")


def source_hashes() -> dict[str, Any]:
    files = (
        "README.md", "ADR.md", "manifest.json", "assumptions.json", "status.json",
        "negative-results.json", "result.schema.json", "model.py", "run.py", "ingest-foundry.py",
        "solidity/foundry.toml", "solidity/run-gas.sh", "solidity/src/ProofOnlyBatchSettlement.sol",
        "solidity/test/SettlementGas.t.sol",
    )
    dependencies = (
        "PQTC_NEXT_GENERATION_RESEARCH_PLAN.md",
        "research/candidates/v03-baseline/gas/measured-summary.json",
    )
    return {
        "schema": "sp70-source-hashes-v1",
        "hash": "sha256",
        "files": {name: "sha256:" + hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in files},
        "dependencies": {name: "sha256:" + hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in dependencies},
    }


def main() -> None:
    baseline = json.loads(BASELINE.read_text())
    individual = {
        "source": "research/candidates/v03-baseline/gas/measured-summary.json",
        "candidate": baseline["candidate_id"],
        "part_a_total_gas_p50": baseline["distributions"]["a_total"]["p50"],
        "part_b_total_gas_p50": baseline["distributions"]["b_total"]["p50"],
        "role": "FROZEN_COMPARATOR_ONLY_NOT_AGGREGATION_INPUT",
    }
    safety = [safety_suite(n, topology) for n in BATCH_SIZES for topology in USER_TOPOLOGIES]
    scheduling = [scheduling_suite(n) for n in BATCH_SIZES]
    measurements = [measurement_row(n, design, topology) for n in BATCH_SIZES for design in PROOF_DESIGNS for topology in USER_TOPOLOGIES]
    rates = (0.01, 0.1, 1.0, 10.0)
    latency = []
    for n in BATCH_SIZES:
        for rate in rates:
            latency.extend((
                {
                    "policy": "THRESHOLD_TRIGGERED", "N": n, "arrival_rate_per_second": rate,
                    "oldest_fill_wait_seconds": (n - 1) / rate,
                    "average_member_fill_wait_seconds": (n - 1) / (2 * rate),
                    "class": "ANALYTIC_POISSON_EXPECTATION_NOT_MEASUREMENT",
                },
                {
                    "policy": "FIXED_WINDOW", "N": n, "arrival_rate_per_second": rate,
                    "window_seconds": 300, "expected_arrivals_per_window": 300 * rate,
                    "maximum_policy_wait_seconds": 300,
                    "class": "POLICY_BOUND_AND_ARRIVAL_MODEL_NOT_MEASUREMENT",
                },
            ))
    result = {
        "schema": "sp70-aggregation-results-v1",
        "candidate": "SP-70",
        "status": "STOP_BY_DEPENDENCY",
        "batch_sizes": list(BATCH_SIZES),
        "proof_designs": list(PROOF_DESIGNS),
        "user_topologies": list(USER_TOPOLOGIES),
        "scheduling_policies": list(SCHEDULING_POLICIES),
        "privacy_architecture": {
            "user": "GENERATES_INDIVIDUAL_ZERO_KNOWLEDGE_PROOF_LOCALLY",
            "aggregator_input": ["OPAQUE_INDIVIDUAL_PROOF", "PUBLIC_STATEMENT"],
            "aggregator_forbidden_input": ["NOTE_SECRET", "MERKLE_PATH", "TRAPDOOR", "RAW_WITNESS"],
            "settlement": "ONE_TRANSACTION_CONSUMES_N_NULLIFIERS_AND_CREATES_N_PULL_PAYOUTS",
            "model_boundary": "SHA256 MODEL TOKENS ARE NOT PROOFS OR ZK EVIDENCE",
        },
        "canonicalization": "STRICT_ASCENDING_UNIQUE_PUBLIC_STATEMENT_HASH; DOMAIN_SEPARATED_BATCH_HASH_CHAIN_BINDS_CHAIN_POOL_DENOMINATION_IN_SOLIDITY",
        "payout_policy": "PULL_PAYMENTS; ATOMIC_VERIFY_AND_CREDIT; CLAIM_FAILURE_RETAINS_CREDIT",
        "individual_comparator": individual,
        "safety": safety,
        "scheduling_results": scheduling,
        "measurements": measurements,
        "latency_models": latency,
        "recovery": {
            "bad_individual_proof": "REJECT_BEFORE_BATCH; KEEP_OTHER_PROOFS",
            "failed_outer_or_raced_nullifier": "ATOMIC_REVERT; REBUILD_EXCLUDING_BAD_OR_SPENT_ENTRY",
            "unfilled_or_censored": "NONEXCLUSIVE_NONCUSTODIAL_SUBMISSION_TO_ANOTHER_AGGREGATOR_OR_INDIVIDUAL_PATH",
            "failed_payout": "PULL_CREDIT_REMAINS; PAYEE_RETRIES CLAIM",
            "ordering": "CANONICAL SORT MAKES BATCH_ID UNIQUE FOR A SET; DUPLICATE KEYS REJECTED",
        },
        "foundry_harness": {
            "command": "cd research/aggregation/solidity && ./run-gas.sh",
            "status": "PREPARED_NOT_RUN",
            "retained_raw_output": "research/aggregation/outputs/foundry-components.json",
            "measurement_scope": "EXACT NULLIFIER, PULL-CREDIT PAYOUT, SUCCESSFUL CLAIM, AND EMPTY-OUTER-PROOF PUBLIC CALLDATA COMPONENTS; NEVER A FULL AGGREGATION BENCHMARK",
            "compiler": {"solc": "0.8.30", "evm": "prague", "optimizer": True, "optimizer_runs": 200, "via_ir": True},
        },
        "schema_guard": "PASS_COUNTERFEIT_TOTAL_REJECTED",
        "decision": {
            "gate": "STOP_BY_DEPENDENCY",
            "active_transaction_cap": 2**24,
            "product_gate": "TOTAL_SETTLEMENT_LE_14M_AND_GAS_PER_WITHDRAWAL_LE_1M_AT_N_GE_16_OR_GE_70_PERCENT_IMPROVEMENT",
            "blockers": ["accepted hiding individual proof", "accepted PQ-oriented outer aggregation/folding proof", "measured outer prover and verifier", "complete full-transaction calldata and execution"],
            "individual_path_requirement": "REQUIRED; AGGREGATION_CANNOT_REPLACE_IT",
            "external_cryptographic_acceptance": "OPEN",
        },
    }
    validate_result(result)
    counterfeit = json.loads(json.dumps(result))
    counterfeit["measurements"][0]["total_gas"]["active_eip7623_10_40"] = 1
    try:
        validate_result(counterfeit)
    except Reject as exc:
        if str(exc) != "incomplete metrics masquerading as totals":
            raise
    else:
        raise AssertionError("schema guard accepted counterfeit total")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    status_path = HERE / "status.json"
    status = json.loads(status_path.read_text())
    status["deterministic_model"] = "PASS"
    status["safety_liveness"] = "PASS_EXECUTABLE_MODEL"
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
    (HERE / "source-hashes.json").write_text(json.dumps(source_hashes(), indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
