#!/usr/bin/env python3
"""Exhaustive finite-state model for PQTC's abstract two-call controller.

This model is deliberately semi-formal.  It does not execute Solidity, parse proof
bytes, model EVM call frames, or prove the cryptographic protocol.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from itertools import product
from pathlib import Path
import json
from typing import Any, Iterable


PACKAGE = Path(__file__).resolve().parent


@dataclass(frozen=True, order=True)
class Checkpoint:
    consumer: int
    statement: int
    core: int
    global_digest: int
    checkpoint_digest: int


@dataclass(frozen=True, order=True)
class State:
    checkpoint: Checkpoint | None = None
    nullifier_spent: bool = False
    completed_count: int = 0


@dataclass(frozen=True)
class Action:
    kind: str
    caller: int
    statement: int
    core: int
    global_digest: int
    checkpoint_digest: int
    pool_guards_ok: bool
    common_parser_ok: bool = True
    second_half_ok: bool = True
    recipient_transfer_ok: bool = True
    relayer_transfer_ok: bool = True

    def incoming_checkpoint(self) -> Checkpoint:
        return Checkpoint(
            self.caller,
            self.statement,
            self.core,
            self.global_digest,
            self.checkpoint_digest,
        )


@dataclass(frozen=True)
class Outcome:
    success: bool
    reason: str
    state: State


DEFAULT_FLAGS = {
    "allow_spent_nullifier": False,
    "keep_checkpoint_after_success": False,
    "non_atomic_failure": False,
    "overwrite_checkpoint": False,
    "skip_consumer_binding": False,
    "skip_global_binding": False,
    "skip_second_half_verification": False,
    "skip_statement_binding": False,
}


def fail(state: State, reason: str, dirty_state: State | None = None) -> Outcome:
    return Outcome(False, reason, state if dirty_state is None else dirty_state)


def transition(state: State, action: Action, mutation: dict[str, bool] | None = None) -> Outcome:
    flags = DEFAULT_FLAGS | (mutation or {})
    spent_blocked = state.nullifier_spent and not flags["allow_spent_nullifier"]

    if action.kind == "begin":
        if not action.pool_guards_ok:
            return fail(state, "POOL_GUARD")
        if spent_blocked:
            return fail(state, "NULLIFIER_SPENT")
        incoming = action.incoming_checkpoint()
        if state.checkpoint is None:
            return Outcome(True, "CHECKPOINT_CREATED", replace(state, checkpoint=incoming))
        if state.checkpoint == incoming:
            return Outcome(True, "IDEMPOTENT_BEGIN", state)
        if flags["overwrite_checkpoint"]:
            return Outcome(True, "CHECKPOINT_OVERWRITTEN", replace(state, checkpoint=incoming))
        return fail(state, "PROOF_ALREADY_STARTED")

    if action.kind != "complete":
        raise ValueError(f"unknown action kind: {action.kind}")
    if not action.pool_guards_ok:
        return fail(state, "POOL_GUARD")
    if spent_blocked:
        return fail(state, "NULLIFIER_SPENT")
    checkpoint = state.checkpoint
    if checkpoint is None:
        return fail(state, "UNKNOWN_PROOF")
    if action.caller != checkpoint.consumer and not flags["skip_consumer_binding"]:
        return fail(state, "UNAUTHORIZED_CONSUMER")
    if action.statement != checkpoint.statement and not flags["skip_statement_binding"]:
        return fail(state, "STATEMENT_MISMATCH")
    if action.core != checkpoint.core:
        return fail(state, "CORE_PROOF_MISMATCH")
    if action.global_digest != checkpoint.global_digest and not flags["skip_global_binding"]:
        return fail(state, "GLOBAL_DATA_MISMATCH")
    if action.checkpoint_digest != checkpoint.checkpoint_digest:
        return fail(state, "CHECKPOINT_MISMATCH")
    if not action.common_parser_ok:
        return fail(state, "COMMON_PARSE_OR_BINDING_FAILURE")

    deleted = replace(state, checkpoint=None)
    if not action.second_half_ok and not flags["skip_second_half_verification"]:
        dirty = deleted if flags["non_atomic_failure"] else None
        return fail(state, "SECOND_HALF_FAILURE", dirty)

    spent = replace(deleted, nullifier_spent=True)
    if not action.recipient_transfer_ok or not action.relayer_transfer_ok:
        dirty = spent if flags["non_atomic_failure"] else None
        return fail(state, "TRANSFER_FAILURE", dirty)

    final_checkpoint = checkpoint if flags["keep_checkpoint_after_success"] else None
    return Outcome(
        True,
        "COMPLETED",
        State(final_checkpoint, True, state.completed_count + 1),
    )


def actions() -> tuple[Action, ...]:
    values = (0, 1)
    generated: list[Action] = []
    for caller, statement, core, global_digest, checkpoint_digest, guard in product(values, repeat=6):
        generated.append(
            Action("begin", caller, statement, core, global_digest, checkpoint_digest, bool(guard))
        )
    for fields in product(values, repeat=10):
        caller, statement, core, global_digest, checkpoint_digest, guard, common, second, recipient, relayer = fields
        generated.append(
            Action(
                "complete",
                caller,
                statement,
                core,
                global_digest,
                checkpoint_digest,
                bool(guard),
                bool(common),
                bool(second),
                bool(recipient),
                bool(relayer),
            )
        )
    return tuple(generated)


def invariant_violations(state: State, action: Action, outcome: Outcome) -> set[str]:
    violations: set[str] = set()
    checkpoint = state.checkpoint

    if not outcome.success and outcome.state != state:
        violations.add("failed_transition_is_atomic")
    if outcome.state.completed_count > 1:
        violations.add("at_most_one_completion_per_nullifier")
    if state.nullifier_spent and outcome.success:
        violations.add("spent_nullifier_blocks_begin_and_complete")

    if action.kind == "begin":
        if outcome.success and not action.pool_guards_ok:
            violations.add("begin_requires_pool_guards")
        if outcome.success and state.nullifier_spent:
            violations.add("begin_requires_unspent_nullifier")
        incoming = action.incoming_checkpoint()
        if checkpoint is not None and checkpoint != incoming:
            if outcome.success or outcome.state != state:
                violations.add("existing_checkpoint_cannot_be_overwritten")
        if (
            checkpoint == incoming
            and action.pool_guards_ok
            and not state.nullifier_spent
            and (not outcome.success or outcome.state != state)
        ):
            violations.add("exact_begin_retry_is_idempotent")
        return violations

    if outcome.success:
        if checkpoint is None:
            violations.add("complete_requires_checkpoint")
        else:
            if action.caller != checkpoint.consumer:
                violations.add("complete_requires_bound_consumer")
            if action.statement != checkpoint.statement:
                violations.add("complete_requires_bound_statement")
            if action.core != checkpoint.core:
                violations.add("complete_requires_bound_core_proof")
            if action.global_digest != checkpoint.global_digest:
                violations.add("complete_requires_bound_global_data")
            if action.checkpoint_digest != checkpoint.checkpoint_digest:
                violations.add("complete_requires_bound_checkpoint")
        if not action.pool_guards_ok:
            violations.add("complete_requires_pool_guards")
        if not action.common_parser_ok:
            violations.add("complete_requires_common_parser")
        if not action.second_half_ok:
            violations.add("complete_requires_second_half_verification")
        if not action.recipient_transfer_ok or not action.relayer_transfer_ok:
            violations.add("complete_requires_successful_transfers")
        if outcome.state.checkpoint is not None:
            violations.add("successful_complete_consumes_checkpoint")
        if not outcome.state.nullifier_spent:
            violations.add("successful_complete_spends_nullifier")
        if outcome.state.completed_count != state.completed_count + 1:
            violations.add("successful_complete_records_once")
    return violations


def state_json(state: State) -> dict[str, Any]:
    return asdict(state)


def action_json(action: Action) -> dict[str, Any]:
    return asdict(action)


def outcome_json(outcome: Outcome) -> dict[str, Any]:
    return {"success": outcome.success, "reason": outcome.reason, "state": state_json(outcome.state)}


def reachable_closure(all_actions: Iterable[Action]) -> tuple[list[State], dict[State, list[dict[str, Any]]]]:
    initial = State()
    states = [initial]
    seen = {initial}
    paths: dict[State, list[dict[str, Any]]] = {initial: []}
    cursor = 0
    while cursor < len(states):
        state = states[cursor]
        cursor += 1
        for action in all_actions:
            outcome = transition(state, action)
            if outcome.success and outcome.state not in seen:
                seen.add(outcome.state)
                states.append(outcome.state)
                paths[outcome.state] = paths[state] + [
                    {"action": action_json(action), "outcome": outcome_json(outcome)}
                ]
    return states, paths


def load_mutations() -> list[dict[str, Any]]:
    document = json.loads((PACKAGE / "mutations.json").read_text(encoding="utf-8"))
    return document["mutations"]


def evaluate() -> dict[str, Any]:
    all_actions = actions()
    states, paths = reachable_closure(all_actions)
    reference_violations: dict[str, int] = {}
    reference_witnesses: list[dict[str, Any]] = []

    for state in states:
        for action in all_actions:
            outcome = transition(state, action)
            found = invariant_violations(state, action, outcome)
            for invariant in sorted(found):
                reference_violations[invariant] = reference_violations.get(invariant, 0) + 1
                if len(reference_witnesses) < 10:
                    reference_witnesses.append(
                        {
                            "invariant": invariant,
                            "pathToState": paths[state],
                            "state": state_json(state),
                            "action": action_json(action),
                            "outcome": outcome_json(outcome),
                        }
                    )

    mutation_results: list[dict[str, Any]] = []
    for mutation in load_mutations():
        violation_counts: dict[str, int] = {}
        first_witness: dict[str, Any] | None = None
        for state in states:
            for action in all_actions:
                outcome = transition(state, action, mutation["flags"])
                found = invariant_violations(state, action, outcome)
                for invariant in sorted(found):
                    violation_counts[invariant] = violation_counts.get(invariant, 0) + 1
                    if first_witness is None and invariant == mutation["expectedInvariant"]:
                        first_witness = {
                            "invariant": invariant,
                            "pathToState": paths[state],
                            "state": state_json(state),
                            "action": action_json(action),
                            "outcome": outcome_json(outcome),
                        }
        detected = mutation["expectedInvariant"] in violation_counts
        mutation_results.append(
            {
                "id": mutation["id"],
                "description": mutation["description"],
                "expectedInvariant": mutation["expectedInvariant"],
                "detected": detected,
                "violationCounts": dict(sorted(violation_counts.items())),
                "witness": first_witness,
            }
        )

    reference_pass = not reference_violations
    all_mutations_detected = all(result["detected"] for result in mutation_results)
    return {
        "schemaVersion": 1,
        "qualification": "SEMI_FORMAL_ABSTRACT_MODEL_NOT_PROTOCOL_PROOF",
        "model": {
            "finiteDomains": {
                "consumer": [0, 1],
                "statement": [0, 1],
                "coreProof": [0, 1],
                "globalDigest": [0, 1],
                "checkpointDigest": [0, 1],
                "booleanGuards": [False, True],
                "proofSlots": 1,
                "nullifiers": 1,
            },
            "reachability": "least fixed point from an empty checkpoint and unspent nullifier under reference transitions",
            "abstractions": [
                "Identifiers are equality classes, not hashes or byte strings.",
                "Parser, verifier, pool guards, and transfers are nondeterministic booleans.",
                "EVM revert is modeled as atomic restoration of all cross-call state.",
                "Cryptography, gas, concurrency, calldata layout, and liveness are outside the model.",
            ],
        },
        "counts": {
            "actions": len(all_actions),
            "reachableStates": len(states),
            "referenceTransitionsChecked": len(states) * len(all_actions),
            "mutations": len(mutation_results),
            "mutantTransitionsChecked": len(states) * len(all_actions) * len(mutation_results),
        },
        "reference": {
            "status": "PASS" if reference_pass else "FAIL",
            "violationCounts": dict(sorted(reference_violations.items())),
            "witnesses": reference_witnesses,
        },
        "mutations": mutation_results,
        "summary": {
            "status": "PASS" if reference_pass and all_mutations_detected else "FAIL",
            "referencePass": reference_pass,
            "allMutationsDetected": all_mutations_detected,
            "detectedMutations": sum(result["detected"] for result in mutation_results),
            "formalVerificationClaim": False,
            "protocolProofClaim": False,
        },
    }
