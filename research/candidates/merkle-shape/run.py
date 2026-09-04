#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from model import Accumulator, Shape, model_leaf, recompute_padded_root, synthetic_transition

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GAS = ROOT / "research/candidates/hash-compression-common/gas/results.json"
CORPUS = ROOT / "test-vectors/hash/v3.json"
OUT = HERE / "outputs/results.json"


def digest(text: str) -> bytes:
    value = bytes.fromhex(text.removeprefix("0x"))
    if len(value) != 64:
        raise AssertionError("corpus digest is not 64 bytes")
    return value


def source_hashes() -> dict[str, object]:
    paths = [
        "model.py", "run.py", "ingest-foundry.py", "manifest.json",
        "result.schema.json", "assumptions.json", "negative-results.json", "ADR.md", "README.md",
        "solidity/foundry.toml", "solidity/src/ResearchAccumulators.sol",
        "solidity/test/AccumulatorGas.t.sol", "solidity/test/CorpusParity.t.sol",
        "solidity/run-gas.sh", "solidity/run-parity.sh",
    ]
    rows = {
        relative: "sha256:" + hashlib.sha256((HERE / relative).read_bytes()).hexdigest()
        for relative in paths
    }
    external = [
        "contracts/src/libraries/PQTCApplicationHash.sol",
        "contracts/src/libraries/P2BB512.sol",
        "contracts/src/libraries/Digest512.sol",
        "lib/forge-std/src/Test.sol",
        "test-vectors/hash/v3.json",
        "research/candidates/hash-compression-common/gas/results.json",
    ]
    dependency_rows = {
        relative: "sha256:" + hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in external
    }
    return {"schema": "sp11-source-hashes-v1", "files": rows, "dependencies": dependency_rows}


def add_storage_counts(
    row: dict[str, int | bool], shape: Shape, history: int | None
) -> dict[str, int | bool]:
    if not row["accepted"]:
        row.update({
            "evm_storage_slot_writes": 0,
            "persistent_state_growth_slots": 0,
        })
        return row
    index = int(row["index"])
    frontier_writes = int(row["frontier_writes"])
    history_writes = 1 if history is None else 2
    row["evm_storage_slot_writes"] = 1 + 2 * frontier_writes + 1 + 2 + history_writes
    # New conceptual slots: guard, first frontier digest writes, index, and history.
    first_frontier = sum(
        1
        for level in range(shape.depth)
        if index % (shape.arity ** level) == 0
        and index // (shape.arity ** level) < shape.arity - 1
    )
    history_growth = 1 if history is None else (2 if index + 1 < history else 0)
    row["persistent_state_growth_slots"] = (
        1 + 2 * first_frontier + int(index == 0) + history_growth
    )
    return row



def must_reject(label: str, action, error: type[BaseException]) -> str:
    try:
        action()
    except error:
        return label
    raise AssertionError(f"safety mutation accepted: {label}")
def apply_foundry_artifact(result: dict[str, object]) -> dict[str, object]:
    path = HERE / "outputs/foundry-gas.json"
    if not path.exists():
        return {
            "gas_sweep": "NOT_EVALUATED_COMPLETE_TRANSACTIONS",
            "foundry_artifact_sha256": None,
        }
    raw = json.loads(path.read_text())
    if raw.get("schema") != "sp11-foundry-gas-v1":
        raise AssertionError("unexpected SP-11 Foundry artifact schema")
    if raw.get("measurement_class") != "ISOLATED_CALL_GASLEFT_DIAGNOSTIC":
        raise AssertionError("SP-11 Foundry artifact has an unsafe measurement label")
    if raw.get("indices_0_255") != list(range(256)):
        raise AssertionError("SP-11 Foundry sweep is not exactly 0..255")
    expected_boundaries = [value for k in range(21) for value in ((1 << k) - 1, 1 << k)]
    if raw.get("boundary_indices") != expected_boundaries:
        raise AssertionError("SP-11 Foundry boundary set is incomplete")
    if raw.get("boundary_insert_accepted") != [True] * 41 + [False]:
        raise AssertionError("SP-11 capacity boundary behavior mismatch")
    for variant, key, deployment_key, runtime_key in (
        (result["variants"][0], "unbounded_insert_gas_0_255", "unbounded_deployment_gas", "unbounded_runtime_bytes"),
        (result["variants"][1], "bounded_insert_gas_0_255", "bounded_deployment_gas", "bounded_runtime_bytes"),
    ):
        values = raw.get(key)
        if not isinstance(values, list) or len(values) != 256 or any(
            not isinstance(value, int) or value <= 0 for value in values
        ):
            raise AssertionError("invalid SP-11 isolated call diagnostic")
        variant["foundry_gas"]["isolated_call_diagnostic"] = {
            "status": "PASS_ISOLATED_GASLEFT_DIAGNOSTIC",
            "measurement_class": "ISOLATED_CALL_GASLEFT_DIAGNOSTIC_NOT_TRANSACTION_GAS",
            "samples": values,
            "best": min(values),
            "worst": max(values),
            "omitted_components": ["transaction_intrinsic_gas", "calldata_gas", "EIP-7623_floor", "receipt"],
        }
        variant["foundry_gas"]["deployment_diagnostic"] = {
            "value": raw[deployment_key],
            "runtime_bytes": raw[runtime_key],
            "measurement_class": "INTERNAL_NEW_EXPRESSION_DIAGNOSTIC_NOT_DEPLOYMENT_TRANSACTION",
        }
    result["foundry_harness"].update({
        "status": "PASS_ISOLATED_DIAGNOSTICS_COMPLETE_TRANSACTIONS_NOT_EVALUATED",
        "retained_output": "outputs/foundry-gas.json",
        "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "boundary_diagnostic": {
            "indices": raw["boundary_indices"],
            "gasleft_deltas": raw["unbounded_boundary_gas"],
            "accepted": raw["boundary_insert_accepted"],
            "measurement_class": "ISOLATED_CALL_GASLEFT_DIAGNOSTIC_NOT_TRANSACTION_GAS",
        },
        "complete_transaction_gas": {
            "status": "NOT_EVALUATED",
            "omitted_components": ["transaction_intrinsic_gas", "calldata_gas", "EIP-7623_floor", "receipt"],
        },
    })
    return {
        "gas_sweep": "PASS_ISOLATED_DIAGNOSTIC_COMPLETE_TRANSACTIONS_NOT_EVALUATED",
        "foundry_artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }

def apply_parity_artifact(result: dict[str, object]) -> dict[str, object]:
    path = HERE / "outputs/foundry-parity.json"
    if not path.exists():
        result["corpus"]["h0_root_recomputation"] = "NOT_EVALUATED"
        return {
            "h0_corpus_parity": "NOT_EVALUATED",
            "foundry_parity_artifact_sha256": None,
        }
    raw = json.loads(path.read_text())
    expected_corpus_hash = "0x" + hashlib.sha256(CORPUS.read_bytes()).hexdigest()
    expected = {
        "schema": "sp11-foundry-parity-v1",
        "profile": "solc-0.8.30_prague_viaIR_optimizer-runs-200",
        "cases": 1000,
        "status": "PASS",
        "corpus_sha256": expected_corpus_hash,
    }
    if raw != expected:
        raise AssertionError("SP-11 Foundry parity artifact failed strict validation")
    artifact_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    result["corpus"]["h0_root_recomputation"] = "PASS_EXACT_FOUNDRY_1000_OF_1000"
    result["corpus"]["foundry_parity"] = {
        **raw,
        "retained_output": "outputs/foundry-parity.json",
        "artifact_sha256": artifact_hash,
    }
    result["foundry_harness"]["parity_status"] = "PASS_EXACT_FOUNDRY_1000_OF_1000"
    return {
        "h0_corpus_parity": "PASS_EXACT_FOUNDRY_1000_OF_1000",
        "foundry_parity_artifact_sha256": artifact_hash,
    }



def write_json_atomic(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)



def main() -> None:
    gas = json.loads(GAS.read_text())
    corpus = json.loads(CORPUS.read_text())
    if corpus["version"] != 3 or corpus["count"] != 1000 or len(corpus["vectors"]) != 1000:
        raise AssertionError("frozen v0.3 corpus identity/count changed")
    if [row["index"] for row in corpus["vectors"]] != list(range(1000)):
        raise AssertionError("corpus order/index mismatch")
    commitments = [digest(row["commitment"]) for row in corpus["vectors"]]
    h0_roots = [digest(row["root_after_insert"]) for row in corpus["vectors"]]
    if len(set(h0_roots)) != 1000:
        raise AssertionError("frozen H0 root sequence contains a duplicate")

    shapes = [Shape.preserving_capacity(arity) for arity in (2, 4, 8)]
    model_parity = []
    for shape in shapes:
        zero = model_leaf(b"frozen-v0.3-scope-model-zero")
        tree = Accumulator(shape, zero, 64)
        leaves: list[bytes] = []
        for commitment in commitments[:256]:
            leaf = model_leaf(commitment)
            leaves.append(leaf)
            tree.insert(leaf)
            if tree.root != recompute_padded_root(shape, zero, leaves):
                raise AssertionError(f"incremental/full parity failure for arity {shape.arity}")
        model_parity.append({
            "arity": shape.arity,
            "cases": 256,
            "status": "PASS_MODEL_COMPRESSOR_ONLY",
            "final_root": "0x" + tree.root.hex(),
        })

    history_zero = model_leaf(b"history-zero")
    unbounded = Accumulator(shapes[0], history_zero, None)
    bounded = Accumulator(shapes[0], history_zero, 64)
    initial_root = unbounded.root
    for index in range(80):
        leaf = model_leaf(b"history-leaf" + index.to_bytes(4, "big"))
        unbounded.insert(leaf)
        bounded.insert(leaf)
    if len(unbounded.roots) != 81 or initial_root not in unbounded.roots:
        raise AssertionError("unbounded root retention failed")
    if len(bounded.roots) != 64 or initial_root in bounded.roots:
        raise AssertionError("bounded root eviction failed")
    root_history_semantics = {
        "unbounded": "PASS_RETAINS_ALL_81_ROOTS",
        "bounded_64": "PASS_EVICTS_INITIAL_AFTER_64_INSERTIONS",
        "latest_root_parity": "PASS" if bounded.root == unbounded.root else "FAIL",
    }
    if bounded.root != unbounded.root:
        raise AssertionError("history policy changed accumulator root")

    safety_rejections = [
        must_reject("synthetic_index_over_capacity", lambda: synthetic_transition(shapes[0], (1 << 20) + 1), ValueError),
        must_reject("invalid_zero_digest", lambda: Accumulator(shapes[0], b"short", 64), ValueError),
        must_reject("invalid_history_bound", lambda: Accumulator(shapes[0], history_zero, 0), ValueError),
    ]
    tiny = Accumulator(Shape(2, 1), history_zero, None)
    tiny.insert(model_leaf(b"tiny-0"))
    tiny.insert(model_leaf(b"tiny-1"))
    safety_rejections.append(must_reject("tree_full", lambda: tiny.insert(model_leaf(b"tiny-2")), OverflowError))

    boundary_indices = sorted({
        value for k in range(21) for value in ((1 << k) - 1, 1 << k)
        if value <= (1 << 20)
    })
    variants = []
    definitions = [
        ("B20_UNBOUNDED_CONSTRUCTOR_STORAGE", shapes[0], None, "constructor_storage"),
        ("B20_BOUNDED64_CONSTRUCTOR_STORAGE", shapes[0], 64, "constructor_storage"),
        ("B20_BOUNDED64_PRECOMPUTED_STORAGE", shapes[0], 64, "precomputed_storage"),
        ("B20_BOUNDED64_CODE_CONSTANTS", shapes[0], 64, "packed_code_blob"),
        ("Q4_D10_BOUNDED64_CODE_CONSTANTS", shapes[1], 64, "packed_code_blob"),
        ("O8_D7_BOUNDED64_CODE_CONSTANTS", shapes[2], 64, "packed_code_blob"),
    ]
    for name, shape, history, zeros in definitions:
        sweep = [add_storage_counts(synthetic_transition(shape, index), shape, history) for index in range(256)]
        boundaries = [
            add_storage_counts(synthetic_transition(shape, index), shape, history)
            for index in boundary_indices if index <= shape.capacity
        ]
        variants.append({
            "id": name,
            "arity": shape.arity,
            "depth": shape.depth,
            "capacity": shape.capacity,
            "capacity_vs_required": shape.capacity - (1 << 20),
            "root_history": "unbounded_mapping" if history is None else {"bounded_ring": history},
            "zero_strategy": zeros,
            "zero_storage_slots_exact": 2 * (shape.depth + 1) if zeros != "packed_code_blob" else 0,
            "packed_code_constant_bytes_exact": 64 * (shape.depth + 1) if zeros == "packed_code_blob" else 0,
            "zero_strategy_feasibility": (
                "FAIL_SCOPE_DEPENDENT_H0_ZEROS"
                if shape.arity == 2 and zeros != "constructor_storage"
                else "MODEL_ONLY_NO_ACCEPTED_COMPRESSOR"
                if shape.arity > 2
                else "PASS"
            ),
            "witness_bytes_exact": shape.witness_bytes,
            "relation_hash_count_exact": shape.relation_hashes,
            "binary_fold_hash_count_if_used_exact": shape.binary_fold_hashes,
            "storage_transition_model": {
                "measurement_class": "EXACT_LOGICAL_MODEL",
                "sweep_0_255": sweep,
                "power_of_two_boundaries": boundaries,
                "best_frontier_writes": min(row["frontier_writes"] for row in sweep),
                "worst_frontier_writes": max(row["frontier_writes"] for row in sweep),
            },
            "foundry_gas": {
                "complete_transaction": {"status": "NOT_EVALUATED", "best": None, "worst": None},
                "isolated_call_diagnostic": {"status": "NOT_EVALUATED", "best": None, "worst": None},
            },
            "security_gate": "PASS_H0_ONLY" if shape.arity == 2 else "FAIL_NO_ACCEPTED_ARITY_COMPRESSOR",
        })

    h0 = gas["H0"]
    result = {
        "schema": "sp11-merkle-shape-v1",
        "candidate": "SP-11",
        "status": "STOP_HIGHER_ARITY_SECURITY_GATE; RETAIN_BINARY_DEPTH20",
        "default": "B20_UNBOUNDED_CONSTRUCTOR_STORAGE",
        "required_capacity": 1 << 20,
        "corpus": {
            "path": "test-vectors/hash/v3.json",
            "sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
            "records_validated": 1000,
            "h0_expected_root_sequence_integrity": "PASS_FORMAT_ORDER_UNIQUENESS",
            "h0_root_recomputation": "NOT_EVALUATED",
            "model_incremental_vs_independent_full_tree": model_parity,
        },
        "root_history_semantics": root_history_semantics,
        "safety": {"all_mutations_reject": True, "mutations_rejected": safety_rejections},
        "final_sp10_exact_measurements": {
            "measurement_class": "EXACT_RETAINED_SP10_FOUNDRY",
            "source": "research/candidates/hash-compression-common/gas/results.json",
            "H0": {key: h0[key] for key in (
                "completeDirectDepositGas", "compressionGas", "nodeGas",
                "depth20ComputeOnlyInsertionGas", "syntheticDepth20RootUpdateGas",
                "zeroTreeConstructorGas", "runtimeBytes", "initcodeBytes"
            )},
            "H3_H5_H6": {
                key: {field: gas[key][field] for field in ("nodeGas", "syntheticDepth20RootUpdateGas")}
                for key in ("H3", "H5", "H6")
            },
            "qualification": "H3_H5_H6_BENCHMARK_ONLY_NOT_SECURITY_APPROVAL",
        },
        "variants": variants,
        "foundry_harness": {
            "command": "cd research/candidates/merkle-shape/solidity && ./run-gas.sh",
            "corpus_parity_command": "cd research/candidates/merkle-shape/solidity && ./run-parity.sh",
            "status": "PREPARED_NOT_RUN",
            "measurements": ["insert_0_through_255", "2^k-1_and_2^k_k_le_20", "deployment", "runtime_bytes"],
        },
        "decision": {
            "capacity_gate": "PASS_ALL",
            "higher_arity_security_gate": "FAIL",
            "custody_finalist": "BINARY_DEPTH20_H0_UNCHANGED",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    status_updates = apply_foundry_artifact(result)
    status_updates.update(apply_parity_artifact(result))
    status_path = HERE / "status.json"
    status = json.loads(status_path.read_text())
    status.update(status_updates)
    status["complete_transaction_gas"] = "NOT_EVALUATED"
    write_json_atomic(OUT, result)
    write_json_atomic(status_path, status)
    write_json_atomic(HERE / "source-hashes.json", source_hashes())
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
