#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from model import (
    ACTIVE_GAS_CAP,
    CHECKPOINT_STRUCT_SLOTS,
    ROBUST_CALL_GATE,
    ROBUST_TOTAL_GATE,
    SPLITS,
    WORST_LIVE_SLOTS_PER_CHECKPOINT,
    Bindings,
    ModelVerifier,
    Pool,
    Reject,
    StateMachine,
    digest,
    expect_reject,
    nullifier_key,
    storage_schedule,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V03_PROFILE = ROOT / "research/candidates/V9/outputs/benchmark.json"
V03_PROFILE_SHA256 = "c87a4c686012f87a2bdecf1f6a3ff91b612ba72cc8840838c14469a04dad325d"
OUT = HERE / "outputs/results.json"
SOURCE_HASHES = HERE / "source-hashes.json"
TTL_BLOCKS = 256
BLOCK_TIME_SECONDS_PROJECTION = 12


def fixture(proof_seed: int = 500, continuation_seed: int = 600):
    pool = Pool(TTL_BLOCKS, 12)
    nullifier = digest(1)
    root = digest(100)
    root2 = digest(200)
    pool.install_root(root)
    pool.install_root(root2)
    bindings = pool.bindings(
        nullifier,
        root,
        "recipient",
        1,
        digest(300),
        digest(400),
        digest(proof_seed),
        digest(continuation_seed),
    )
    key = nullifier_key(nullifier)
    return pool, nullifier, root, root2, bindings, key


def attack_suite() -> dict[str, dict[str, str]]:
    outcomes: dict[str, dict[str, str]] = {}

    pool, nullifier, root, _, bindings, key = fixture()
    pool.begin(1, nullifier, bindings, ModelVerifier.proof("A", 12, key, bindings))
    alternate = pool.bindings(nullifier, root, "recipient", 1, digest(300), digest(400), digest(501), digest(600))
    code = expect_reject(
        "ACTIVE_CHECKPOINT",
        lambda: pool.begin(2, nullifier, alternate, ModelVerifier.proof("A", 12, key, alternate)),
    )
    assert len(pool.machine.checkpoints) == 1
    outcomes["many_valid_part_a_one_note"] = {"status": "PASS_REJECTED", "reason": code}

    pool, _, _, _, bindings, key = fixture()
    code = expect_reject(
        "UNAUTHORIZED_CONSUMER",
        lambda: pool.machine.begin("ATTACKER", 1, key, bindings, ModelVerifier.proof("A", 12, key, bindings)),
    )
    outcomes["direct_registry_arbitrary_consumer"] = {"status": "PASS_REJECTED", "reason": code}

    pool, nullifier, _, _, bindings, key = fixture()
    proof_a = ModelVerifier.proof("A", 12, key, bindings)
    proof_b = ModelVerifier.proof("B", 12, key, bindings)
    pool.begin(1, nullifier, bindings, proof_a)
    code = expect_reject(
        "CHECKPOINT_EXPIRED",
        lambda: pool.complete(1 + TTL_BLOCKS, nullifier, bindings, proof_b, "recipient", 1),
    )
    pool.machine.cleanup(1 + TTL_BLOCKS, key)
    expect_reject(
        "UNKNOWN_CHECKPOINT",
        lambda: pool.complete(1 + TTL_BLOCKS, nullifier, bindings, proof_b, "recipient", 1),
    )
    outcomes["expired_proof_replay"] = {"status": "PASS_REJECTED", "reason": code}

    pool, nullifier, _, root2, bindings, key = fixture()
    pool.begin(1, nullifier, bindings, ModelVerifier.proof("A", 12, key, bindings))
    replacement = pool.bindings(nullifier, root2, "recipient", 1, digest(300), digest(400), digest(502), digest(602))
    pool.begin(1 + TTL_BLOCKS, nullifier, replacement, ModelVerifier.proof("A", 12, key, replacement))
    racer = pool.bindings(nullifier, root2, "recipient", 1, digest(300), digest(400), digest(503), digest(603))
    code = expect_reject(
        "ACTIVE_CHECKPOINT",
        lambda: pool.begin(2 + TTL_BLOCKS, nullifier, racer, ModelVerifier.proof("A", 12, key, racer)),
    )
    outcomes["replacement_race"] = {"status": "PASS_FIRST_VALID_WINS", "reason": code}

    pool, nullifier, _, _, bindings, key = fixture()
    proof_a = ModelVerifier.proof("A", 12, key, bindings)
    first_expiry = pool.begin(1, nullifier, bindings, proof_a)
    second_expiry = pool.begin(2, nullifier, bindings, proof_a)
    assert first_expiry == second_expiry and len(pool.machine.checkpoints) == 1
    pool.complete(3, nullifier, bindings, ModelVerifier.proof("B", 12, key, bindings), "recipient", 1)
    assert pool.transfers == {"recipient": 1}
    outcomes["exact_part_a_front_run"] = {"status": "PASS_IDEMPOTENT", "reason": "RECIPIENT_STATEMENT_BOUND"}

    pool, nullifier, root, _, bindings, key = fixture()
    pool.begin(1, nullifier, bindings, ModelVerifier.proof("A", 12, key, bindings))
    mixed = pool.bindings(nullifier, root, "recipient", 1, digest(300), digest(400), digest(500), digest(604))
    code = expect_reject(
        "BINDING_MISMATCH",
        lambda: pool.complete(2, nullifier, mixed, ModelVerifier.proof("B", 12, key, mixed), "recipient", 1),
    )
    assert key in pool.machine.checkpoints
    outcomes["mixed_a_b_proofs"] = {"status": "PASS_REJECTED", "reason": code}

    pool, nullifier, root, _, bindings, key = fixture()
    pool.begin(1, nullifier, bindings, ModelVerifier.proof("A", 12, key, bindings))
    code = expect_reject("ROOT_PINNED", lambda: pool.age_root(root))
    pool.machine.cleanup(1 + TTL_BLOCKS, key)
    pool.age_root(root)
    outcomes["root_aging"] = {"status": "PASS_PINNED_UNTIL_CLEANUP", "reason": code}

    pool, nullifier, _, _, bindings, key = fixture()
    pool.begin(1, nullifier, bindings, ModelVerifier.proof("A", 12, key, bindings))

    def reject_payment() -> None:
        raise Reject("PAYMENT_REVERT")

    code = expect_reject(
        "PAYMENT_REVERT",
        lambda: pool.complete(
            2,
            nullifier,
            bindings,
            ModelVerifier.proof("B", 12, key, bindings),
            "recipient",
            1,
            reject_payment,
        ),
    )
    assert key in pool.machine.checkpoints and key not in pool.spent
    outcomes["part_b_payment_revert"] = {"status": "PASS_ATOMIC_ROLLBACK", "reason": code}

    pool, nullifier, _, _, bindings, key = fixture()
    proof_b = ModelVerifier.proof("B", 12, key, bindings)
    pool.begin(1, nullifier, bindings, ModelVerifier.proof("A", 12, key, bindings))
    reentry_code = ""

    def reenter() -> None:
        nonlocal reentry_code
        reentry_code = expect_reject(
            "REENTRANT_CALL",
            lambda: pool.complete(2, nullifier, bindings, proof_b, "recipient", 1),
        )

    pool.complete(2, nullifier, bindings, proof_b, "recipient", 1, reenter)
    assert reentry_code == "REENTRANT_CALL" and pool.transfers == {"recipient": 1}
    outcomes["reentrancy"] = {"status": "PASS_REJECTED", "reason": reentry_code}

    pool, nullifier, _, root2, bindings, key = fixture()
    pool.begin(1, nullifier, bindings, ModelVerifier.proof("A", 12, key, bindings))
    code = expect_reject("CHECKPOINT_NOT_EXPIRED", lambda: pool.machine.cleanup(TTL_BLOCKS, key))
    pool.machine.cleanup(1 + TTL_BLOCKS, key)
    replacement = pool.bindings(nullifier, root2, "recipient", 1, digest(300), digest(400), digest(505), digest(605))
    pool.begin(2 + TTL_BLOCKS, nullifier, replacement, ModelVerifier.proof("A", 12, key, replacement))
    outcomes["cleanup_front_run"] = {"status": "PASS_BOUNDARY_ENFORCED", "reason": code}

    assert len(outcomes) == 10
    return outcomes


def verifier_projection() -> dict[str, object]:
    raw = V03_PROFILE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != V03_PROFILE_SHA256:
        raise AssertionError("retained V9 profile hash mismatch")
    document = json.loads(raw)
    source_rows = document["completeTransactionProjected"]["rows"]
    found_splits = {tuple(row["split"]) for row in source_rows}
    if found_splits != set(SPLITS):
        raise AssertionError("retained profile does not contain the required split sweep")

    rows = []
    for row in source_rows:
        scenario_totals = {}
        all_calls = []
        all_pair_totals = []
        for scenario in ("active", "uniform64", "uniform96"):
            a_gas, b_gas = row["totalGas"][scenario]
            scenario_totals[scenario] = {"part_a": a_gas, "part_b": b_gas, "total": a_gas + b_gas}
            all_calls.extend((a_gas, b_gas))
            all_pair_totals.append(a_gas + b_gas)
        call_margin = ROBUST_CALL_GATE - max(all_calls)
        total_margin = ROBUST_TOTAL_GATE - max(all_pair_totals)
        rows.append({
            "split": row["split"],
            "air_placement": row["airPlacement"],
            "classification": "PROJECTION_RETAINED_V03_COMPONENT_MODEL",
            "totals": scenario_totals,
            "call_gate_margin": call_margin,
            "total_gate_margin": total_margin,
            "arithmetic_gate": "PASS" if call_margin >= 0 and total_margin >= 0 else "FAIL",
        })
    best = max(rows, key=lambda value: (value["call_gate_margin"], value["total_gate_margin"]))
    return {
        "classification": "PROJECTION_ONLY",
        "source": "research/candidates/V9/outputs/benchmark.json",
        "source_sha256": V03_PROFILE_SHA256,
        "source_full_path_status": document["completeTransactionMeasured"],
        "rows": rows,
        "best_minimum_margin": {
            "split": best["split"],
            "air_placement": best["air_placement"],
            "call_gate_margin": best["call_gate_margin"],
            "total_gate_margin": best["total_gate_margin"],
        },
        "arithmetic_gate": "FAIL",
        "integrated_full_path_gate": "NOT_EVALUATED",
        "reason": "No SP-72 integration with the frozen verifier/proof fixture exists; retained V9 rows are projections, not measurements.",
    }


def growth_model(projection: dict[str, object]) -> dict[str, object]:
    rows = projection["rows"]
    cheapest_part_a = min(
        scenario["part_a"]
        for row in rows
        for scenario in row["totals"].values()
    )
    per_block = ACTIVE_GAS_CAP // cheapest_part_a
    ttl_bound = per_block * TTL_BLOCKS
    budgets = []
    for budget_eth in (1, 10, 100):
        for gas_price_gwei in (10, 20, 50):
            count = (budget_eth * 10**18) // (cheapest_part_a * gas_price_gwei * 10**9)
            budgets.append({
                "budget_eth": budget_eth,
                "gas_price_gwei": gas_price_gwei,
                "max_distinct_valid_part_a": count,
                "checkpoint_attributable_live_slots": count * WORST_LIVE_SLOTS_PER_CHECKPOINT,
                "logical_live_slots_including_shared_counter": count * WORST_LIVE_SLOTS_PER_CHECKPOINT + (1 if count else 0),
                "logical_live_bytes_including_shared_counter": (count * WORST_LIVE_SLOTS_PER_CHECKPOINT + (1 if count else 0)) * 32,
            })
    return {
        "classification": "PROJECTION_FROM_RETAINED_V03_PART_A_GAS",
        "attack_preconditions": ["distinct unspent nullifiers", "valid Part A proofs", "transactions included"],
        "cheapest_projected_part_a_gas": cheapest_part_a,
        "active_transaction_gas_cap": ACTIVE_GAS_CAP,
        "max_creations_per_block_under_cap": per_block,
        "ttl_blocks": TTL_BLOCKS,
        "unbudgeted_ttl_window_max_checkpoints": ttl_bound,
        "unbudgeted_ttl_window_checkpoint_attributable_slots": ttl_bound * WORST_LIVE_SLOTS_PER_CHECKPOINT,
        "unbudgeted_ttl_window_logical_slots_including_shared_counter": ttl_bound * WORST_LIVE_SLOTS_PER_CHECKPOINT + (1 if ttl_bound else 0),
        "unbudgeted_ttl_window_logical_bytes_including_shared_counter": (ttl_bound * WORST_LIVE_SLOTS_PER_CHECKPOINT + (1 if ttl_bound else 0)) * 32,
        "budgets": budgets,
        "note": "Counts include the one shared activeCheckpointCount slot when nonzero; trie/database overhead is excluded and one nullifier cannot contribute more than one live checkpoint.",
    }


def harness_measurement() -> dict[str, object]:
    path = HERE / "outputs/harness-gas.json"
    if not path.exists():
        return {
            "status": "NOT_MEASURED",
            "classification": "MEASUREMENT_OUTPUT_ABSENT",
            "command": "cd research/two-call-state/solidity && forge test --match-test testMeasureRetainedHarnessOverhead",
            "scope": "state harness plus binding mock; excludes v0.3 verifier",
        }
    result = json.loads(path.read_text())
    if result.get("schema") != "sp72-foundry-harness-gas-v1":
        raise AssertionError("unexpected harness measurement schema")
    return {"status": "MEASURED", **result}


def write_source_hashes() -> None:
    files = [
        "ADR.md",
        "README.md",
        "assumptions.json",
        "attacks.json",
        "invariants.json",
        "manifest.json",
        "model.py",
        "negative-results.json",
        "output-plan.json",
        "result.schema.json",
        "run.py",
        "solidity/foundry.toml",
        "solidity/src/RobustTwoCallState.sol",
        "solidity/test/RobustTwoCallState.t.sol",
        "status.json",
        "transitions.json",
    ]
    hashes = {
        path: hashlib.sha256((HERE / path).read_bytes()).hexdigest()
        for path in files
    }
    document = {
        "schema": "sp72-source-hashes-v1",
        "files": hashes,
        "dependencies": {
            "research/candidates/V9/outputs/benchmark.json": V03_PROFILE_SHA256,
        },
    }
    SOURCE_HASHES.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")


def main() -> None:
    attacks = attack_suite()
    projection = verifier_projection()
    storage = storage_schedule()
    result = {
        "schema": "sp72-two-call-state-results-v1",
        "candidate": "SP-72",
        "status": "FAIL_PROJECTION_AND_NOT_EVALUATED_FULL_PATH",
        "security_qualified": False,
        "state_machine": {
            "executable_model": "model.py",
            "solidity_harness": "solidity/src/RobustTwoCallState.sol",
            "transition_table": "transitions.json",
            "invariants": "invariants.json",
            "attacks_passed": len(attacks),
            "attacks_total": 10,
        },
        "attacks": attacks,
        "storage": {
            "checkpoint_struct_slots": CHECKPOINT_STRUCT_SLOTS,
            "incremental_root_pin_slots_worst_case": 1,
            "live_slots_per_checkpoint_worst_case": WORST_LIVE_SLOTS_PER_CHECKPOINT,
            "fixed_size_only": True,
            "proof_bytes_stored": False,
            "reusable_fact_stored": False,
            "gas_schedule": storage,
        },
        "harness_overhead": harness_measurement(),
        "verifier_profile": projection,
        "live_state_growth": growth_model(projection),
        "recovery_latency": {
            "exact_blocks": TTL_BLOCKS,
            "wall_clock_classification": "PROJECTION",
            "assumed_seconds_per_block": BLOCK_TIME_SECONDS_PROJECTION,
            "projected_seconds": TTL_BLOCKS * BLOCK_TIME_SECONDS_PROJECTION,
            "permissionless_action_at_block": "created_at + ttl_blocks",
        },
        "gate": {
            "active_gas_cap": ACTIVE_GAS_CAP,
            "part_a_and_b_limit": ROBUST_CALL_GATE,
            "total_limit": ROBUST_TOTAL_GATE,
            "projection_arithmetic": "FAIL",
            "integrated_exact_full_path": "NOT_EVALUATED",
            "external_cryptographic_acceptance": "OPEN",
            "decision": "DO_NOT_PROMOTE",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_source_hashes()
    print(json.dumps({
        "attacks": f"{len(attacks)}/10",
        "projection_gate": "FAIL",
        "full_path": "NOT_EVALUATED",
        "output": str(OUT.relative_to(ROOT)),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
