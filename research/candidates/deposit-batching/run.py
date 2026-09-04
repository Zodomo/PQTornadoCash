#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from model import BATCH_SIZES, Deposit, ModelProofBackend, NoProofBackend, Queue, Reject

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DIRECT = ROOT / "research/candidates/v03-baseline/gas/measured-summary.json"
SP10 = ROOT / "research/candidates/hash-compression-common/gas/results.json"
OUT = HERE / "outputs/results.json"


def identity(value: int) -> bytes:
    return value.to_bytes(20, "big")


def commitment(value: int) -> bytes:
    return hashlib.sha512(b"SP12-COMMITMENT" + value.to_bytes(8, "big")).digest()


def populate(queue: Queue, count: int, now: int = 1000) -> list[Deposit]:
    return [queue.enqueue(commitment(i), identity(i + 1), identity(i + 1001), queue.denomination, now + i) for i in range(count)]


def must_reject(label: str, action) -> str:
    try:
        action()
    except Reject:
        return label
    raise AssertionError(f"safety mutation accepted: {label}")


def mutation_suite(batch: int) -> dict[str, object]:
    rejects = []

    queue = Queue(10**18, 3600, "refund", ModelProofBackend)
    rows = populate(queue, batch)
    statement = queue.expected_statement(batch)
    proof = ModelProofBackend.proof(statement)
    rejects.append(must_reject("omission", lambda: queue.finalize(identity(9000), rows[:-1], statement, proof)))
    rejects.append(must_reject("reorder", lambda: queue.finalize(identity(9000), [rows[1], rows[0], *rows[2:]], statement, proof)))
    substituted = list(rows)
    substituted[-1] = replace(rows[-1], deposit_id=b"x" * 32)
    rejects.append(must_reject("substitution", lambda: queue.finalize(identity(9000), substituted, statement, proof)))
    duplicated = list(rows)
    duplicated[-1] = duplicated[0]
    rejects.append(must_reject("duplicate", lambda: queue.finalize(identity(9000), duplicated, statement, proof)))
    rejects.append(must_reject("prefix_commitment", lambda: queue.finalize(identity(9000), rows, replace(statement, prefix_commitment=b"z" * 32), proof)))
    rejects.append(must_reject("new_root", lambda: queue.finalize(identity(9000), rows, replace(statement, new_root=b"z" * 64), proof)))
    rejects.append(must_reject("proof", lambda: queue.finalize(identity(9000), rows, statement, b"bad")))
    rejects.append(must_reject("queue_domain", lambda: queue.finalize(identity(9000), rows, replace(statement, queue_domain=b"q" * 32), proof)))
    rejects.append(must_reject("unsupported_count", lambda: queue.expected_statement(7)))
    rejects.append(must_reject("wrong_denomination", lambda: queue.enqueue(commitment(99999), identity(1), identity(2), 1, 9999)))
    rejects.append(must_reject("zero_commitment", lambda: queue.enqueue(bytes(64), identity(1), identity(2), queue.denomination, 9999)))
    rejects.append(must_reject("duplicate_enqueue", lambda: queue.enqueue(rows[0].commitment, identity(1), identity(2), queue.denomination, 9999)))

    transferred = queue.finalize(identity(0xBEEF), rows, statement, proof)
    if transferred != batch * queue.denomination or queue.pending or queue.custody != 0:
        raise AssertionError("valid canonical transition did not settle")
    rejects.append(must_reject("replay", lambda: queue.finalize(identity(0xBEEF), rows, statement, proof)))

    stopped = Queue(10**18, 3600, "refund", NoProofBackend)
    stopped_rows = populate(stopped, batch)
    stopped_statement = stopped.expected_statement(batch)
    rejects.append(must_reject("missing_real_backend", lambda: stopped.finalize(identity(1), stopped_rows, stopped_statement, b"")))
    return {
        "batch_size": batch,
        "mutations_rejected": rejects,
        "valid_model_transition": "PASS",
        "permissionless_finalizer": "PASS_ARBITRARY_CALLER",
        "production_backend": "NOT_EVALUATED",
    }


def escape_suite() -> dict[str, str]:
    refund = Queue(7, 10, "refund", ModelProofBackend)
    populate(refund, 2, 100)
    must_reject("early_refund", lambda: refund.escape_head(identity(5), 109))
    if refund.escape_head(identity(999), 110) != "REFUNDED_HEAD" or refund.custody != 7:
        raise AssertionError("refund escape invariant")

    forced = Queue(7, 10, "forced_single", ModelProofBackend)
    populate(forced, 2, 100)
    old = forced.accumulator_root
    must_reject("early_forced_single", lambda: forced.escape_head(identity(6), 109))
    if forced.escape_head(identity(999), 110) != "FORCED_SINGLE_HEAD":
        raise AssertionError("forced escape failed")
    if forced.accumulator_index != 1 or forced.accumulator_root == old or forced.custody != 7:
        raise AssertionError("forced escape invariant")
    return {"refund": "PASS_PERMISSIONLESS_AFTER_TIMEOUT", "forced_single": "PASS_PERMISSIONLESS_AFTER_TIMEOUT"}


def source_hashes() -> dict[str, object]:
    paths = [
        "model.py", "run.py", "ingest-foundry.py", "manifest.json",
        "result.schema.json", "assumptions.json", "negative-results.json", "ADR.md", "README.md",
        "solidity/foundry.toml", "solidity/src/PermissionlessDepositQueue.sol",
        "solidity/test/QueueGas.t.sol", "solidity/run-gas.sh",
    ]
    files = {
        relative: "sha256:" + hashlib.sha256((HERE / relative).read_bytes()).hexdigest()
        for relative in paths
    }
    dependencies = {
        relative: "sha256:" + hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in (
            "research/candidates/v03-baseline/gas/measured-summary.json",
            "research/candidates/hash-compression-common/gas/results.json",
            "lib/forge-std/src/Test.sol",
        )
    }
    return {"schema": "sp12-source-hashes-v1", "files": files, "dependencies": dependencies}


def main() -> None:
    baseline = json.loads(DIRECT.read_text())
    sp10 = json.loads(SP10.read_text())
    direct_gas = baseline["reproduced_deposit_execution_gas"]
    if direct_gas != 13_991_021 or baseline["deposit_measurement_status"] != "PASS_EXACT_REPORT_MATCH":
        raise AssertionError("frozen direct-deposit gas evidence changed")
    if sp10.get("schema") != "sp10-gas-results-v2" or sp10["H0"]["completeDirectDepositGas"] != direct_gas:
        raise AssertionError("final SP-10 H0/direct baseline disagreement")
    mutations = [mutation_suite(batch) for batch in BATCH_SIZES]
    escapes = escape_suite()
    rates = (0.01, 0.1, 1.0, 10.0)
    latency = [
        {
            "batch_size": batch,
            "arrival_rate_per_second": rate,
            "average_wait_to_fill_seconds": (batch - 1) / (2 * rate),
            "oldest_wait_to_fill_seconds": (batch - 1) / rate,
            "measurement_class": "ANALYTIC_POISSON_EXPECTATION_NOT_TIMING_MEASUREMENT",
        }
        for batch in BATCH_SIZES for rate in rates
    ]
    result = {
        "schema": "sp12-deposit-batching-v1",
        "candidate": "SP-12",
        "status": "DEFERRED_STOP_NO_TRUSTLESS_TRANSITION_PROOF_BACKEND",
        "batch_sizes": list(BATCH_SIZES),
        "canonical_order": "STRICT_QUEUE_PREFIX_BY_MONOTONIC_SEQUENCE",
        "finalization_authority": "PERMISSIONLESS_NO_PRIVILEGED_KEY",
        "transition_relation": {
            "public_fields": ["queue_domain", "old_root", "new_root", "prefix_commitment", "start_index", "count", "queue_epoch"],
            "deterministic_model": "PASS",
            "model_proof": "MODEL_ORACLE_NOT_A_PCS",
            "real_proof_backend": "NOT_EVALUATED",
            "proof_bytes": None,
            "proving_time": None,
            "verification_time": None,
            "peak_rss": None,
        },
        "safety": {"batch_results": mutations, "escape_paths": escapes, "all_mutations_reject": True},
        "costs": {
            "direct_v03_deposit_gas": {
                "value": direct_gas,
                "measurement_class": "EXACT_RETAINED_FOUNDRY",
                "source": "research/candidates/v03-baseline/gas/measured-summary.json",
                "sp10_crosscheck_source": "research/candidates/hash-compression-common/gas/results.json",
                "sp10_crosscheck_status": "PASS_EXACT_MATCH",
            },
            "queue_user_deposit_gas": {"value": None, "status": "NOT_EVALUATED", "measurement_class": "NOT_EVALUATED"},
            "batch_finalizer_gas": {str(batch): None for batch in BATCH_SIZES},
            "batch_finalizer_status": "NOT_EVALUATED_NO_PROOF_BACKEND",
            "logical_state": {
                "per_enqueue_new_struct_slots": 4,
                "per_enqueue_duplicate_guard_slots": 1,
                "shared_array_length_slot_write": 1,
                "head_and_sequence_counter_writes": "finalization_or_escape_only",
                "measurement_class": "EXACT_SOLIDITY_STORAGE_LAYOUT_MODEL",
            },
            "griefing": {
                "attacker_principal_per_entry_wei": 10**18,
                "attacker_transactions": "enqueue plus optional timeout escape",
                "residual": "Queue flooding and capital lock remain; canonical checks prevent reorder/substitution and timeout bounds operator withholding.",
            },
        },
        "arrival_latency": latency,
        "economics": {
            str(batch): {
                "amortized_gas_per_deposit": None,
                "break_even_vs_direct": "NOT_EVALUATED",
                "reason": "queue enqueue and trustless batch-finalization gas are both required",
            }
            for batch in BATCH_SIZES
        },
        "foundry_harness": {
            "command": "cd research/candidates/deposit-batching/solidity && ./run-gas.sh",
            "status": "PREPARED_NOT_RUN",
            "scope": "queue user enqueue only; no fake transition verifier",
        },
        "decision": {
            "candidate": "DEFERRED/STOP",
            "promotion_requires": ["measured positive amortized gas break-even", "real trustless proof backend"],
            "operator_assumption": "NONE; no trusted or always-online operator",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (HERE / "source-hashes.json").write_text(json.dumps(source_hashes(), indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
