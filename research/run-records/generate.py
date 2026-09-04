#!/usr/bin/env python3
"""Generate and validate the research benchmark-run evidence ledger and Appendix B tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUNS = ROOT / "research" / "runs"
SUMMARIES = ROOT / "research" / "summaries"
SCHEMA_PATH = ROOT / "benchmark-run.schema.json"
PROFILE_PATH = ROOT / "research" / "harness" / "hardware-detect" / "h1-m4-max.json"
REPORT_LIB = ROOT / "research" / "harness" / "report-generator"
sys.path.insert(0, str(REPORT_LIB))
from keccak import Keccak256, self_test as keccak_self_test  # type: ignore  # noqa: E402
from schema_validator import load_json, validate_document  # type: ignore  # noqa: E402

COMMIT_FALLBACK = "aff4d015f3f092b71f7c63071c884f8819ca05aa"
TIMESTAMP_FALLBACK = "2026-09-04T19:33:36Z"
GAS_NAMES = ("ACTIVE_EIP7623", "FUTURE_EIP7976_64_64", "DRAFT_EIP8311_96_96")
RELATION_HEADER = ("candidate_id", "table_id", "logical_rows", "padded_rows", "base_degree_bits", "hiding_degree_bits", "trace_width", "preprocessed_width", "constraint_count", "max_degree", "quotient_chunks", "batched_functions", "rotations", "active_rows", "padding_rows")
PROOF_HEADER = ("candidate_id", "run_id", "raw_proof_bytes", "abi_calldata_bytes", "header_bytes", "statement_bytes", "global_bytes", "query_row_bytes", "salt_bytes", "frontier_bytes", "ldt_bytes", "final_bytes", "continuation_bytes", "abi_overhead_bytes", "zero_bytes", "nonzero_bytes")
EVM_HEADER = ("candidate_id", "run_id", "operation", "execution_gas", "standard_intrinsic", "eip7623_floor", "eip7623_total", "eip7976_floor", "eip7976_total", "eip8311_floor", "eip8311_total", "tx_cap_margin", "runtime_bytes", "initcode_bytes", "deployment_gas")
PROVER_HEADER = ("candidate_id", "run_id", "hardware_id", "threads", "cold_or_warm", "wall_ms", "cpu_ms", "peak_rss_bytes", "proof_bytes", "native_verify_ms", "success")
SECURITY_HEADER = ("candidate_id", "profile", "term", "model", "formula_source", "input_summary", "classical_bits", "quantum_bits", "proven_or_conjectural", "multi_target_count", "binding", "notes")
INDEX_HEADER = ("run_id", "candidate_id", "spike_id", "success", "gate_status", "failure_reason", "record_path", "record_sha256", "record_keccak256", "artifact_paths", "artifact_sha256", "artifact_keccak256")


class GenerationError(RuntimeError):
    pass


def read_json(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def file_digests(data: bytes) -> tuple[str, str]:
    k = Keccak256()
    k.update(data)
    return hashlib.sha256(data).hexdigest(), k.hexdigest()


def git_value(*args: str, fallback: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return fallback
    return result.stdout.strip() or fallback


def source_identity() -> tuple[dict[str, Any], str]:
    commit = git_value("rev-parse", "HEAD", fallback=COMMIT_FALLBACK)
    timestamp = datetime.fromisoformat(
        git_value("show", "-s", "--format=%cI", "HEAD", fallback=TIMESTAMP_FALLBACK).replace("Z", "+00:00")
    ).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
            text=True, capture_output=True, check=True,
        ).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        dirty = True
    return {"repository": "PQTornado", "commit": commit, "dirty": dirty, "branch_or_tag": None, "submodules": {}}, timestamp


def canonical_environment() -> tuple[dict[str, Any], dict[str, Any]]:
    profile = read_json("research/harness/hardware-detect/h1-m4-max.json")
    h = profile["hardware"]
    conditions = profile["benchmarkConditions"]
    os_data = profile["operatingSystem"]
    hardware = {
        "hardware_id": h["hardware_id"], "cpu_model": h["cpu_model"],
        "physical_cores": h["physical_cores"], "logical_cores": h["logical_cores"],
        "ram_bytes": h["ram_bytes"], "os": f"{os_data['name']} {os_data['version']} ({os_data['build']})",
        "kernel": os_data["kernel"], "architecture": h["architecture"],
        "cpu_features": h["cpu_features"], "threads_used": conditions["parallel_thread_count_default"],
        "allocator": conditions["allocator"], "power_mode": conditions["power_mode"],
        "cpu_affinity": conditions["cpu_affinity"],
    }
    t = profile["toolchain"]
    toolchain = {
        "rustc": t["rustc"], "cargo": t["cargo"], "solc": t["solc"], "foundry": t["foundry"],
        "node": t["node"], "package_manager": t["package_manager"], "evm_revision": t["evm_revision"],
        "rustflags": t["rustflags"], "solc_optimizer_runs": t["solc_optimizer_runs"], "via_ir": t["via_ir"],
        "container_image_digest": "sha256:" + t["container_platform_manifest_sha256"],
    }
    return hardware, toolchain


def artifact(relative: str, description: str | None = None) -> dict[str, Any]:
    path = ROOT / relative
    if not path.is_file():
        raise GenerationError(f"retained artifact is missing: {relative}")
    data = path.read_bytes()
    sha, keccak = file_digests(data)
    suffix = path.suffix.lower()
    media = {".json": "application/json", ".csv": "text/csv", ".txt": "text/plain", ".log": "text/plain"}.get(suffix, "application/octet-stream")
    return {"path": relative, "bytes": len(data), "media_type": media, "digests": {"sha256": sha, "keccak256": keccak}, "description": description}


def empty_scenarios() -> list[dict[str, Any]]:
    return [{"name": name, "floor_gas": 0, "total_gas": 0, "tx_cap_margin": 0, "floor_is_binding": False} for name in GAS_NAMES]


def base_record(candidate: str, spike: str, kind: str, paths: list[str], success: bool = True,
                gate: str = "BENCHMARK_ONLY", failure: str | None = None,
                timestamp: str | None = None) -> dict[str, Any]:
    git, commit_timestamp = source_identity()
    hardware, toolchain = canonical_environment()
    run_id = f"research-{spike.lower().replace('-', '')}-{candidate.lower()}-{kind}"
    descriptions = {paths[0]: "Primary retained evidence for this run"}
    all_paths = [*paths, "research/harness/hardware-detect/h1-m4-max.json"]
    return {
        "schema_version": "1", "run_id": run_id, "candidate_id": candidate, "spike_id": spike,
        "timestamp_utc": timestamp or commit_timestamp, "git": git, "toolchain": toolchain, "hardware": hardware,
        "protocol": {"semantic_version": "research-non-finalist", "asset": "native ETH", "denomination_wei": "1000000000000000000", "tree_depth": 20, "tree_arity": 2, "case_id": kind, "transaction_shape": "OTHER", "scenario_status": "NOT_EVALUATED_UNLESS_SOURCE_ARTIFACT_STATES_OTHERWISE"},
        "relation": {"kind": "OTHER", "logical_rows": 0, "padded_rows": 0, "trace_width": 0, "preprocessed_width": 0, "constraint_count": 0, "max_degree": 0, "quotient_chunks": 0, "batched_functions": 0, "base_degree_bits": 0, "hiding_degree_bits": 0, "active_rows": 0, "padding_rows": 0, "measurement_status": "NOT_EVALUATED_SCHEMA_V1_STRUCTURAL_ZEROS_EXCLUDED_FROM_SUMMARIES"},
        "proof_system": {"name": "NOT_EVALUATED", "base_field": "NOT_EVALUATED", "challenge_field": "NOT_EVALUATED", "hiding": False, "hiding_construction": None, "trusted_setup": False, "classical_wrapper": False, "transcript": "NOT_EVALUATED"},
        "security": {"classification": "BENCHMARK_ONLY", "terms": [], "lowest_accepted_bits": None, "qrom_status": "NOT_EVALUATED", "zk_status": "NOT_EVALUATED", "external_review": None},
        "prover": {"success": success, "cold_or_warm": "NOT_APPLICABLE", "wall_ms": None, "cpu_ms": None, "peak_rss_bytes": None, "native_verify_ms": None, "phase_ms": {}, "measurement_status": "NOT_EVALUATED"},
        "proof_bytes": {"raw_proof_bytes": 0, "abi_calldata_bytes": 0, "zero_bytes": 0, "nonzero_bytes": 0, "sections": {}, "measurement_status": "NOT_APPLICABLE_NO_PROOF_OUTPUT"},
        "evm": {"measured": False, "client": "NOT_EVALUATED", "client_version": "NOT_EVALUATED", "chain_config_hash": None, "execution_gas": 0, "standard_intrinsic_gas": 0, "receipt_gas_used": 0, "transaction_gas_limit": 0, "gas_scenarios": empty_scenarios(), "runtime_bytes": 0, "initcode_bytes": 0, "deployment_gas": 0, "component_gas": {}, "transaction_hash": None, "receipt_block": None, "measurement_status": "NOT_EVALUATED_SCHEMA_V1_STRUCTURAL_ZEROS_EXCLUDED_FROM_SUMMARIES"},
        "artifacts": [artifact(path, descriptions.get(path)) for path in dict.fromkeys(all_paths)],
        "result": {"success": success, "gate_status": gate, "failure_reason": failure, "confounders": [], "notes": ["Non-finalist research evidence; zero-valued schema-v1 sentinels marked NOT_EVALUATED are never emitted as measurements."]},
    }


def security_term(name: str, classical: float | None, quantum: float | None, model: str,
                  source: str | None = None, binding: bool = False, status: str = "HEURISTIC",
                  notes: list[str] | None = None, input_summary: str = "") -> dict[str, Any]:
    term_notes = list(notes or [])
    if input_summary:
        term_notes.append(f"inputs:{input_summary}")
    return {"name": name, "model": model, "formula_source": source, "classical_bits": classical,
            "quantum_bits": quantum, "proven_or_conjectural": status, "multi_target_count_log2": None,
            "binding": binding, "omitted_terms": [], "proof_status": status,
            "assumptions": [], "theorem_regime": "CONDITIONAL", "notes": term_notes}


def set_proof(record: dict[str, Any], size: int, status: str, unique: int | None = None) -> None:
    proof = record["proof_bytes"]
    proof.update({"raw_proof_bytes": size, "sections": {"research_canonical_raw": size}, "measurement_status": status})
    if unique is not None:
        proof["unique_query_indices"] = unique
    proof["abi_calldata_status"] = "NOT_EVALUATED_NO_PRODUCTION_CODEC"


def set_component_evm(record: dict[str, Any], components: dict[str, int], runtime: int | None = None,
                      initcode: int | None = None, deployment: int | None = None) -> None:
    evm = record["evm"]
    evm.update({"measured": True, "client": "Foundry local EVM", "component_gas": dict(sorted(components.items())),
                "measurement_status": "MEASURED_COMPONENTS_ONLY_NO_COMPLETE_TRANSACTION_OR_CALLDATA_SCHEDULE"})
    if runtime is not None:
        evm["runtime_bytes"] = runtime
        evm["runtime_bytes_status"] = "MEASURED"
    if initcode is not None:
        evm["initcode_bytes"] = initcode
        evm["initcode_bytes_status"] = "MEASURED"
    if deployment is not None:
        evm["deployment_gas"] = deployment
        evm["deployment_gas_status"] = "MEASURED"


def sp10_records() -> list[dict[str, Any]]:
    native_path = "research/candidates/hash-compression-common/native/distributions.json"
    gas_path = "research/candidates/hash-compression-common/gas/results.json"
    security_path = "research/candidates/hash-compression-common/security/analytical-ceilings.json"
    native = read_json(native_path)
    gas = read_json(gas_path)
    analytical = {row["candidate"]: row for row in read_json(security_path)["candidates"]}
    by_candidate: dict[str, list[dict[str, Any]]] = {}
    for row in native["distributions"]:
        by_candidate.setdefault(row["candidate"], []).append(row)
    records: list[dict[str, Any]] = []
    for candidate in sorted(by_candidate):
        r = base_record(candidate, "SP-10", "native", [native_path, security_path])
        r["prover"]["measurement_status"] = native["classification"]
        r["prover"]["diagnostic_distributions_ns"] = [
            {key: value for key, value in row.items() if key != "raw_ns"}
            for row in by_candidate[candidate]
        ]
        r["result"]["confounders"] = list(native["protocolGaps"])
        a = analytical[candidate]
        if "idealClassicalCollisionBits" in a:
            r["security"]["terms"] = [
                security_term("ideal-collision-ceiling", a["idealClassicalCollisionBits"], a["genericQuantumCollisionCeilingBits"], "generic black-box ceiling", binding=True, notes=["Necessary ceiling only; not a qualification result."], input_summary=f"fieldModulus={a['fieldModulus']};width={a['width']};outputFields={a['outputFields']}"),
                security_term("ideal-hidden-part-ceiling", a["idealClassicalHiddenPartBits"], a["genericQuantumHiddenPartGroverCeilingBits"], "generic black-box ceiling", notes=["Necessary ceiling only; structural attacks are outside this model."], input_summary=f"fieldModulus={a['fieldModulus']};width={a['width']};outputFields={a['outputFields']}"),
            ]
        records.append(r)
        values = gas[candidate]
        components = {k: v for k, v in values.items() if isinstance(v, int) and not isinstance(v, bool) and (k.endswith("Gas") or k.endswith("InsertionGas") or k.endswith("RootUpdateGas"))}
        if components:
            g = base_record(candidate, "SP-10", "gas", [gas_path])
            set_component_evm(g, components, values.get("runtimeBytes"), values.get("initcodeBytes"))
            g["result"]["notes"].append(values.get("completeDirectDepositStatus", "NOT_EVALUATED"))
            records.append(g)
    return records


def harness_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    merkle_path = "research/candidates/merkle-shape/outputs/foundry-gas.json"
    merkle = read_json(merkle_path)
    bounded = merkle["bounded_insert_gas_0_255"]
    m = base_record("SP-11", "SP-11", "foundry-gas", [merkle_path, "research/candidates/merkle-shape/outputs/results.json"])
    set_component_evm(m, {"bounded_insert_min": min(bounded), "bounded_insert_median": int(statistics.median(bounded)), "bounded_insert_max": max(bounded)}, merkle["bounded_runtime_bytes"], deployment=merkle["bounded_deployment_gas"])
    m["evm"]["source_sample_count"] = len(bounded)
    records.append(m)

    deposit_path = "research/candidates/deposit-batching/outputs/foundry-gas.json"
    deposit = read_json(deposit_path)
    enqueue = deposit["enqueue_gas"]
    d = base_record("SP-12", "SP-12", "foundry-gas", [deposit_path, "research/candidates/deposit-batching/outputs/results.json"])
    set_component_evm(d, {"enqueue_min": min(enqueue), "enqueue_median": int(statistics.median(enqueue)), "enqueue_max": max(enqueue)})
    d["evm"]["source_sample_count"] = len(enqueue)
    records.append(d)

    digest_path = "research/digest-width/outputs/foundry-gas.json"
    digest = read_json(digest_path)
    dw = base_record("SP-13", "SP-13", "digest-width-gas", [digest_path, "research/digest-width/results.json"])
    components: dict[str, int] = {}
    for variant in digest["variants"]:
        for key in ("hash_only_call_gas", "storage_only_cold_call_gas", "hash_and_storage_cold_call_gas"):
            components[f"{variant['id']}.{key}"] = variant[key]
    set_component_evm(dw, components)
    dw["result"]["notes"].append("Cross-cutting SP-13 digest-width microbenchmark retained with the requested spike ledger.")
    records.append(dw)
    return records


def sp31_records() -> list[dict[str, Any]]:
    records = []
    for candidate in [f"V{i}" for i in range(1, 10)]:
        path = f"research/candidates/{candidate}/outputs/benchmark.json"
        data = read_json(path)
        r = base_record(candidate, "SP-31", "isolated-benchmark", [path])
        set_component_evm(r, {key: value for key, value in data["solidityMeasured"].items() if isinstance(value, int) and not isinstance(value, bool)})
        r["prover"]["measurement_status"] = data["nativeDiagnosticClassification"]
        r["prover"]["diagnostic_metrics"] = data["nativeDiagnostic"]
        r["result"]["confounders"] = [data["measurementScope"]]
        if data["noMicrobenchmarkSumClaim"] is not None:
            r["result"]["confounders"].append(str(data["noMicrobenchmarkSumClaim"]))
        records.append(r)
    return records


def sp40_records() -> list[dict[str, Any]]:
    native_path = "research/candidates/field-bakeoff-common/outputs/native-latest.json"
    gas_path = "research/candidates/field-bakeoff-common/outputs/solidity-latest.json"
    native = read_json(native_path)
    gas = read_json(gas_path)
    candidates = {row["candidateId"]: row for row in native["candidates"]}
    measurements: dict[str, dict[str, int]] = {candidate: {} for candidate in candidates}
    for row in gas["measurements"]:
        candidate = row["label"].split("/", 1)[0]
        measurements[candidate][row["label"]] = row["gas"]
    records = []
    for candidate in sorted(candidates):
        r = base_record(candidate, "SP-40", "field-benchmark", [native_path, gas_path])
        set_component_evm(r, measurements[candidate])
        r["prover"]["measurement_status"] = native["measurementClassification"]
        r["prover"]["peak_rss_bytes"] = native["processPeakRssBytes"]
        r["prover"]["diagnostic_metrics"] = candidates[candidate]["measurements"]
        r["proof_system"].update({"name": "FIELD_KERNEL_ONLY", "base_field": candidates[candidate]["baseField"], "challenge_field": candidates[candidate]["challengeField"]})
        r["result"]["confounders"] = [native["timingCaveat"], gas["measurementDefinition"]]
        records.append(r)
    return records


def fri_security_terms(profile: str) -> list[dict[str, Any]]:
    path = f"research/fri-pareto/outputs/security/{profile}.json"
    data = read_json(path)
    scenarios = data.get("multi_target_scenarios", [])
    if not scenarios:
        return []
    scenario = scenarios[0]
    regime = next((value for value in scenario.values() if isinstance(value, dict) and isinstance(value.get("terms"), list)), None)
    if not regime:
        return []
    terms = []
    for item in regime["terms"]:
        if not item.get("applies", True):
            continue
        binding = item.get("binding", {})
        terms.append({
            "name": item["term"], "model": regime.get("regime", "conditional FRI model"),
            "formula_source": item.get("formula_source"), "classical_bits": item.get("classical_bits"),
            "quantum_bits": item.get("quantum_bits"), "proven_or_conjectural": "CONJECTURAL",
            "multi_target_count_log2": regime.get("target_count_log2"),
            "binding": bool(binding.get("classical") or binding.get("quantum")),
            "omitted_terms": item.get("omissions", []), "proof_status": item.get("proof_status", "conditional"),
            "assumptions": item.get("omissions", []), "theorem_regime": "CONDITIONAL",
            "notes": [item.get("formula", ""), "inputs:" + json.dumps(item.get("inputs", {}), sort_keys=True, separators=(",", ":"))],
        })
    return terms


def backend_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    profiles = ["b4-q32-c16x16-f0-r4", "b4-q48-c16x16-f0-r4", "b3-q111-c16x16-f0-r4"]
    for profile in profiles:
        measurement_path = f"research/fri-pareto/outputs/anchors/{profile}/measurements.json"
        security_path = f"research/fri-pareto/outputs/security/{profile}.json"
        data = read_json(measurement_path)
        sec_terms = fri_security_terms(profile)
        sec_data = read_json(security_path)
        manifest = sec_data["manifest"]
        for rep in data["repetitions"]:
            r = base_record("C10-fri", "SP-50", f"{profile}-r{rep['repetition']}", [measurement_path, security_path])
            r["relation"].update({"kind": "AIR", "logical_rows": manifest["logical_trace_height"], "padded_rows": 1 << manifest["proof_degree_bits"], "trace_width": manifest["relation_width"], "constraint_count": manifest["num_constraints"], "max_degree": manifest["max_constraint_degree"], "quotient_chunks": manifest["quotient_chunks"], "batched_functions": manifest["num_batched_functions"], "base_degree_bits": manifest["proof_degree_bits"] - manifest["hiding_degree_padding_bits"], "hiding_degree_bits": manifest["proof_degree_bits"], "active_rows": manifest["logical_trace_height"], "padding_rows": (1 << manifest["proof_degree_bits"]) - manifest["logical_trace_height"], "measurement_status": "SOURCE_BOUND_RESEARCH_RELATION", "measured_fields": ["logical_rows", "padded_rows", "base_degree_bits", "hiding_degree_bits", "trace_width", "constraint_count", "max_degree", "quotient_chunks", "batched_functions", "active_rows", "padding_rows"]})
            r["proof_system"].update({"name": "C10 hiding FRI research anchor", "base_field": "BabyBear", "challenge_field": "degree-4 extension", "challenge_field_bits": manifest["challenge_field_bits"], "pcs_or_ldt": "FRI", "hiding": True, "hiding_construction": "random functions and degree padding", "query_count": rep["configured_queries"], "log_blowup": manifest["fri_log_blowup"], "commit_grinding_bits_configured": manifest["commit_grinding_bits"], "query_grinding_bits_configured": manifest["query_grinding_bits"], "transcript": "KeccakPair512 research transcript"})
            r["prover"].update({"success": rep["native_verified"], "cold_or_warm": "NOT_APPLICABLE", "wall_ms": rep["prove_ms"], "peak_rss_bytes": rep["process_peak_rss_bytes"], "native_verify_ms": rep["native_verify_ms"], "measurement_status": "MEASURED_NATIVE_RESEARCH_CODEC"})
            set_proof(r, rep["research_canonical_raw_bytes"], "MEASURED_RESEARCH_CODEC_NO_ABI", rep["unique_query_indices"])
            if rep["repetition"] == 0:
                r["security"].update({"classification": "PQ_ORIENTED_RESEARCH", "terms": sec_terms, "lowest_accepted_bits": None, "qrom_status": sec_data["classification"], "zk_status": "RESEARCH_HIDING_NOT_QUALIFIED"})
            r["result"]["notes"].append(data["parameterBindingWarning"])
            records.append(r)

    c20_path = "research/candidates/C20-hvzk-whir/outputs/latest.json"
    c20 = read_json(c20_path)
    for index, run in enumerate(c20["runs"]):
        r = base_record("C20", "SP-51", f"native-r{index}", [c20_path])
        r["proof_system"].update({"name": "HidingWhirPcs upstream smoke", "base_field": "KoalaBear", "challenge_field": "degree-4 extension", "pcs_or_ldt": "WHIR", "hiding": True, "hiding_construction": "HidingWhirPcs", "transcript": "upstream diagnostic"})
        r["relation"].update({"kind": "OTHER", "logical_rows": c20["proxy_geometry"]["polynomial_elements"], "padded_rows": c20["proxy_geometry"]["polynomial_elements"], "trace_width": c20["proxy_geometry"]["num_variables"], "measurement_status": "UPSTREAM_PROXY_GEOMETRY_NOT_PQTC", "measured_fields": ["logical_rows", "padded_rows", "trace_width"]})
        r["prover"].update({"success": run["verified"], "wall_ms": run["prover_time_ns"] / 1_000_000, "peak_rss_bytes": c20["peak_rss_bytes"], "native_verify_ms": run["native_verify_time_ns"] / 1_000_000, "measurement_status": c20["measurement_label"]})
        set_proof(r, run["proof_bytes"], "MEASURED_UPSTREAM_CODEC_NO_ABI")
        if index == 0:
            q = c20["security_report"]["query_round"]["with_pow"]
            r["security"].update({"classification": "PQ_ORIENTED_RESEARCH", "terms": [security_term("query-round", q["bits"], q["bits"], "upstream conditional security report", binding=True, status="PROVEN", notes=["Upstream diagnostic base case only; not end-to-end PQTC."], input_summary="target_bits=32")], "lowest_accepted_bits": None, "qrom_status": "MISSING_EXACT_TRANSCRIPT_REDUCTION", "zk_status": "UPSTREAM_HIDING_DIAGNOSTIC"})
        r["result"].update({"gate_status": "DEFERRED", "notes": r["result"]["notes"] + [c20["evidence_class"]]})
        records.append(r)

    c30_path = "research/candidates/C30-stir/outputs/latest.json"
    c30 = read_json(c30_path)
    r = base_record("C30", "SP-52", "native", [c30_path])
    r["proof_system"].update({"name": "TwoAdicStirPcs upstream smoke", "base_field": "BabyBear", "challenge_field": "degree-4 extension", "pcs_or_ldt": "STIR", "hiding": False, "transcript": "upstream diagnostic"})
    r["relation"].update({"logical_rows": c30["proxy_geometry"]["polynomial_elements"], "padded_rows": c30["proxy_geometry"]["polynomial_elements"], "trace_width": c30["proxy_geometry"]["matrix_width"], "measurement_status": "UPSTREAM_PROXY_GEOMETRY_NOT_PQTC", "measured_fields": ["logical_rows", "padded_rows", "trace_width"]})
    r["prover"].update({"success": c30["verified"], "wall_ms": c30["open_time_ns"] / 1_000_000, "peak_rss_bytes": c30["peak_rss_bytes"], "native_verify_ms": c30["native_verify_time_ns"] / 1_000_000, "measurement_status": c30["measurement_label"]})
    set_proof(r, c30["proof_bytes"], "MEASURED_UPSTREAM_CODEC_NO_ABI")
    records.append(r)

    failures = [
        ("C50", "SP-60", "native-failed", "research/candidates/C50-spartan-whir/outputs/native/result.json", "NOT_EVALUATED: missing circom prerequisite", "2026-09-04T18:27:51.218433Z"),
        ("C50", "SP-60", "gas-failed", "research/candidates/C50-spartan-whir/outputs/solidity-gas/result.json", "UNEXECUTABLE_UPSTREAM_HARNESS_AT_PIN: target_contract array is unbound", "2026-09-04T18:42:34.239045Z"),
        ("C70", "SP-62", "historical-benchmark-failed", "research/candidates/C70-flock-veil/outputs/flock-benchmark/result.json", "Pinned batch-44 benchmark panicked because no Ligerito m=21 fast-profile security configuration exists", "2026-09-04T18:32:41.539514Z"),
    ]
    for candidate, spike, kind, path, reason, timestamp in failures:
        data = read_json(path)
        extra = [item["path"] for item in data.get("logs", {}).values() if (ROOT / item["path"]).is_file()]
        if candidate == "C50" and kind == "native-failed":
            extra = [step_log["path"] for step in data.get("steps", []) for step_log in step.get("logs", {}).values() if (ROOT / step_log["path"]).is_file()]
        failed = base_record(candidate, spike, kind, [path, *extra], success=False, gate="FAIL", failure=reason, timestamp=timestamp)
        failed["result"]["notes"].append(data.get("execution_status", "NOT_EVALUATED"))
        records.append(failed)

    c60_path = "research/candidates/C60-recursion/outputs/architecture-smoke/result.json"
    c60 = read_json(c60_path)
    c60_logs = [item["path"] for item in c60["logs"].values()]
    rec = base_record("C60", "SP-61", "architecture-smoke", [c60_path, *c60_logs], timestamp=c60["started_at"])
    rec["relation"].update({"kind": "RECURSIVE", "measurement_status": "TOY_FIBONACCI_NOT_PQTC"})
    rec["proof_system"].update({"name": "Plonky3 recursion architecture smoke", "base_field": "BabyBear", "challenge_field": "NOT_RECORDED", "hiding": True, "hiding_construction": "upstream --zk architecture smoke", "transcript": "Poseidon1"})
    rec["result"].update({"gate_status": "DEFERRED", "notes": rec["result"]["notes"] + [c60["dependency_gate"], c60["pqtc_classification"]]})
    records.append(rec)
    return records


def product_harness_records() -> list[dict[str, Any]]:
    records = []
    aggregation_path = "research/aggregation/outputs/foundry-components.json"
    a = read_json(aggregation_path)
    components: dict[str, int] = {"successful_pull_claim": a["successful_pull_claim_gas"]}
    for index, n in enumerate(a["N"]):
        components[f"N{n}.nullifier"] = a["nullifier_component_gas"][index]
        components[f"N{n}.same_user_pull_credit"] = a["same_user_pull_credit_gas"][index]
        components[f"N{n}.unrelated_user_pull_credit"] = a["unrelated_user_pull_credit_gas"][index]
    r = base_record("SP-70", "SP-70", "foundry-components", [aggregation_path, "research/aggregation/outputs/results.json"])
    set_component_evm(r, components)
    r["evm"]["calldata_floor_metrics"] = {f"N{n}": {"bytes": a["public_only_calldata_bytes"][i], "zero_bytes": a["public_only_calldata_zero_bytes"][i], "nonzero_bytes": a["public_only_calldata_nonzero_bytes"][i], "active_floor": a["public_only_active_calldata_floor"][i], "uniform64_floor": a["public_only_uniform64_calldata_floor"][i], "uniform96_floor": a["public_only_uniform96_calldata_floor"][i]} for i, n in enumerate(a["N"])}
    r["result"].update({"gate_status": "DEFERRED", "notes": r["result"]["notes"] + [a["measurement_class"], a["calldata_scope"]]})
    records.append(r)

    state_path = "research/two-call-state/outputs/harness-gas.json"
    state = read_json(state_path)
    s = base_record("SP-72", "SP-72", "foundry-harness", [state_path, "research/two-call-state/outputs/results.json"])
    set_component_evm(s, {"part_a": state["part_a_gas"], "part_b_gross": state["part_b_gross_gas"], "cleanup_gross": state["cleanup_gross_gas"]})
    s["result"].update({"gate_status": "FAIL", "success": False, "failure_reason": "Harness-only projection exceeds the complete two-call gate; full verifier path is NOT_EVALUATED", "notes": s["result"]["notes"] + [state["scope"]]})
    s["prover"]["success"] = False
    records.append(s)
    return records


def generate_new_records() -> list[dict[str, Any]]:
    records = [*sp10_records(), *harness_records(), *sp31_records(), *sp40_records(), *backend_records(), *product_harness_records()]
    records.sort(key=lambda row: row["run_id"])
    ids = [row["run_id"] for row in records]
    if len(ids) != len(set(ids)):
        raise GenerationError("duplicate generated run_id")
    return records


def csv_bytes(header: Iterable[str], rows: Iterable[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(header), lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: "" if value is None else value for key, value in row.items()})
    return output.getvalue().encode("utf-8")


def record_source(path: str, data: bytes) -> tuple[str, str, str]:
    sha, keccak = file_digests(data)
    return path, sha, keccak


def appendix_outputs(records_with_sources: list[tuple[dict[str, Any], str, bytes]]) -> dict[str, bytes]:
    relation_rows: list[dict[str, Any]] = []
    proof_rows: list[dict[str, Any]] = []
    evm_rows: list[dict[str, Any]] = []
    prover_rows: list[dict[str, Any]] = []
    security_rows: list[dict[str, Any]] = []
    index_rows: list[dict[str, Any]] = []
    relation_seen: set[tuple[str, tuple[Any, ...]]] = set()
    for record, path, data in sorted(records_with_sources, key=lambda item: item[0]["run_id"]):
        run_id = record["run_id"]
        source_path, source_sha, source_keccak = record_source(path, data)
        arts = record["artifacts"]
        index_rows.append({
            "run_id": run_id, "candidate_id": record["candidate_id"], "spike_id": record["spike_id"],
            "success": str(record["result"]["success"]).lower(), "gate_status": record["result"]["gate_status"],
            "failure_reason": record["result"].get("failure_reason"), "record_path": source_path,
            "record_sha256": source_sha, "record_keccak256": source_keccak,
            "artifact_paths": json.dumps([a["path"] for a in arts], separators=(",", ":")),
            "artifact_sha256": json.dumps([a["digests"]["sha256"] for a in arts], separators=(",", ":")),
            "artifact_keccak256": json.dumps([a["digests"]["keccak256"] for a in arts], separators=(",", ":")),
        })
        relation = record["relation"]
        measured_fields = relation.get("measured_fields")
        include_relation = measured_fields is not None or "measurement_status" not in relation
        if include_relation:
            fields = set(measured_fields or RELATION_HEADER[2:])
            values = tuple(relation.get(k, "") if k in fields else "" for k in RELATION_HEADER[2:])
            key = (record["candidate_id"], values)
            if key not in relation_seen:
                relation_seen.add(key)
                relation_rows.append({"candidate_id": record["candidate_id"], "table_id": f"run:{run_id};artifact:{source_path};sha256:{source_sha}", **{k: relation.get(k) if k in fields else None for k in RELATION_HEADER[2:]}})
        proof = record["proof_bytes"]
        if not str(proof.get("measurement_status", "")).startswith(("NOT_EVALUATED", "NOT_APPLICABLE")):
            sections = proof.get("sections", {})
            proof_rows.append({
                "candidate_id": record["candidate_id"], "run_id": run_id,
                "raw_proof_bytes": proof["raw_proof_bytes"],
                "abi_calldata_bytes": proof["abi_calldata_bytes"] if "MEASURED" in str(proof.get("abi_calldata_status", "MEASURED")) else None,
                "header_bytes": sections.get("header"), "statement_bytes": sections.get("statement"), "global_bytes": sections.get("global"),
                "query_row_bytes": sections.get("query_rows"), "salt_bytes": sections.get("salts"), "frontier_bytes": sections.get("frontier"),
                "ldt_bytes": sections.get("ldt"), "final_bytes": sections.get("final"), "continuation_bytes": sections.get("continuation"),
                "abi_overhead_bytes": (proof["abi_calldata_bytes"] - proof["raw_proof_bytes"]) if proof["abi_calldata_bytes"] >= proof["raw_proof_bytes"] and "MEASURED" in str(proof.get("abi_calldata_status", "MEASURED")) else None,
                "zero_bytes": proof["zero_bytes"] if "MEASURED" in str(proof.get("abi_calldata_status", "MEASURED")) else None,
                "nonzero_bytes": proof["nonzero_bytes"] if "MEASURED" in str(proof.get("abi_calldata_status", "MEASURED")) else None,
            })
        evm = record["evm"]
        if evm.get("measured"):
            components = evm.get("component_gas", {})
            for operation, gas in sorted(components.items()):
                evm_rows.append({"candidate_id": record["candidate_id"], "run_id": run_id, "operation": operation, "execution_gas": gas,
                                 "standard_intrinsic": None, "eip7623_floor": None, "eip7623_total": None, "eip7976_floor": None,
                                 "eip7976_total": None, "eip8311_floor": None, "eip8311_total": None, "tx_cap_margin": None,
                                 "runtime_bytes": evm["runtime_bytes"] if evm.get("runtime_bytes_status") == "MEASURED" else None,
                                 "initcode_bytes": evm["initcode_bytes"] if evm.get("initcode_bytes_status") == "MEASURED" else None,
                                 "deployment_gas": evm["deployment_gas"] if evm.get("deployment_gas_status") == "MEASURED" else None})
            if not components and evm.get("measurement_status", "").startswith("MEASURED"):
                scenarios = {s["name"]: s for s in evm["gas_scenarios"]}
                evm_rows.append(transaction_row(record, run_id, "transaction", evm, scenarios))
        prover = record["prover"]
        if prover.get("wall_ms") is not None or prover.get("native_verify_ms") is not None:
            prover_rows.append({"candidate_id": record["candidate_id"], "run_id": run_id, "hardware_id": record["hardware"]["hardware_id"],
                                "threads": record["hardware"].get("threads_used"), "cold_or_warm": prover["cold_or_warm"], "wall_ms": prover.get("wall_ms"),
                                "cpu_ms": prover.get("cpu_ms"), "peak_rss_bytes": prover.get("peak_rss_bytes"), "proof_bytes": proof["raw_proof_bytes"],
                                "native_verify_ms": prover.get("native_verify_ms"), "success": str(prover["success"]).lower()})
        for term in record["security"]["terms"]:
            count = term.get("multi_target_count_log2")
            term_notes = term.get("notes", [])
            input_summary = next((note[7:] for note in term_notes if note.startswith("inputs:")), "")
            public_notes = [note for note in term_notes if not note.startswith("inputs:")]
            security_rows.append({"candidate_id": record["candidate_id"], "profile": f"run:{run_id};artifact:{source_path};sha256:{source_sha}",
                                  "term": term["name"], "model": term["model"], "formula_source": term.get("formula_source"),
                                  "input_summary": input_summary, "classical_bits": term.get("classical_bits"), "quantum_bits": term.get("quantum_bits"),
                                  "proven_or_conjectural": term["proven_or_conjectural"], "multi_target_count": None if count is None else f"2^{count}",
                                  "binding": str(term["binding"]).lower(), "notes": " | ".join(public_notes + term.get("omitted_terms", []))})
    return {
        "research/summaries/relation-geometry.csv": csv_bytes(RELATION_HEADER, relation_rows),
        "research/summaries/proof-ledger.csv": csv_bytes(PROOF_HEADER, proof_rows),
        "research/summaries/evm-gas.csv": csv_bytes(EVM_HEADER, evm_rows),
        "research/summaries/prover.csv": csv_bytes(PROVER_HEADER, prover_rows),
        "research/summaries/security.csv": csv_bytes(SECURITY_HEADER, security_rows),
        "research/summaries/run-index.csv": csv_bytes(INDEX_HEADER, index_rows),
    }


def transaction_row(record: dict[str, Any], run_id: str, operation: str, evm: dict[str, Any], scenarios: dict[str, dict[str, Any]]) -> dict[str, Any]:
    active, future, draft = (scenarios[name] for name in GAS_NAMES)
    return {"candidate_id": record["candidate_id"], "run_id": run_id, "operation": operation,
            "execution_gas": evm["execution_gas"], "standard_intrinsic": evm["standard_intrinsic_gas"],
            "eip7623_floor": active["floor_gas"], "eip7623_total": active["total_gas"],
            "eip7976_floor": future["floor_gas"], "eip7976_total": future["total_gas"],
            "eip8311_floor": draft["floor_gas"], "eip8311_total": draft["total_gas"],
            "tx_cap_margin": active["tx_cap_margin"], "runtime_bytes": evm["runtime_bytes"],
            "initcode_bytes": evm.get("initcode_bytes"), "deployment_gas": evm.get("deployment_gas")}


def v03_sources() -> list[tuple[dict[str, Any], str, bytes]]:
    paths = sorted(RUNS.glob("v03-*.json"))
    if len(paths) != 60:
        raise GenerationError(f"expected exactly 60 authoritative v03 records, found {len(paths)}")
    result = []
    for path in paths:
        data = path.read_bytes()
        record = json.loads(data)
        result.append((record, path.relative_to(ROOT).as_posix(), data))
    return result


def add_v03_appendix_rows(outputs: dict[str, bytes], v03: list[tuple[dict[str, Any], str, bytes]], all_sources: list[tuple[dict[str, Any], str, bytes]]) -> dict[str, bytes]:
    # appendix_outputs already handles v03 canonical fields; add explicit part-B transaction rows afterward.
    generated = appendix_outputs(all_sources)
    rows = list(csv.DictReader(io.StringIO(generated["research/summaries/evm-gas.csv"].decode())))
    for record, _, _ in v03:
        evm = record["evm"]
        if not evm.get("measured"):
            continue
        scenarios_a = {s["name"]: s for s in evm["gas_scenarios"]}
        rows.append(transaction_row(record, record["run_id"], "WITHDRAW_A", evm, scenarios_a))
        if "part_b_gas_scenarios" in evm:
            scenarios_b = {s["name"]: s for s in evm["part_b_gas_scenarios"]}
            b = deepcopy(evm)
            b["execution_gas"] = evm["component_gas"]["pool_b_execution"]
            b["standard_intrinsic_gas"] = evm["component_gas"]["pool_b_standard_intrinsic"]
            rows.append(transaction_row(record, record["run_id"], "WITHDRAW_B", b, scenarios_b))
    generated["research/summaries/evm-gas.csv"] = csv_bytes(EVM_HEADER, sorted(rows, key=lambda row: (row["run_id"], row["operation"])))
    return generated


def validate_records(sources: list[tuple[dict[str, Any], str, bytes]]) -> None:
    schema = load_json(SCHEMA_PATH)
    seen: set[str] = set()
    for record, path, _ in sources:
        if path.startswith("research/runs/research-"):
            errors = validate_document(record, schema)
            if errors:
                raise GenerationError(f"{path}: schema validation failed: {json.dumps(errors, sort_keys=True)}")
        if record["run_id"] in seen:
            raise GenerationError(f"duplicate run_id: {record['run_id']}")
        seen.add(record["run_id"])
        scenarios = record["evm"]["gas_scenarios"]
        names = [item["name"] for item in scenarios]
        if len(names) != 3 or set(names) != set(GAS_NAMES):
            raise GenerationError(f"{record['run_id']}: gas_scenarios must contain the exact three schedules")
        if record["evm"].get("measured") and not record["evm"].get("component_gas"):
            if any(item["total_gas"] == 0 for item in scenarios):
                raise GenerationError(f"{record['run_id']}: measured transaction is missing an exact gas schedule")
        if path.startswith("research/runs/research-"):
            for item in record["artifacts"]:
                current = artifact(item["path"])
                if current["bytes"] != item["bytes"] or current["digests"] != item["digests"]:
                    raise GenerationError(f"{record['run_id']}: artifact digest mismatch for {item['path']}")


def excluded_manifest_path(relative: str) -> bool:
    parts = Path(relative).parts
    return (relative == "research/run-records/evidence-manifest.json" or
            any(part in {"build", "cache", ".cache", "__pycache__", "target", "user-move", "user-moves"} for part in parts) or
            any(part.startswith(".moved") for part in parts))


def manifest_bytes(expected: dict[str, bytes], source_paths: set[str]) -> bytes:
    paths = set(source_paths)
    paths.update(expected)
    paths.update({"benchmark-run.schema.json", "research/harness/hardware-detect/h1-m4-max.json", "research/run-records/generate.py", "research/run-records/reproduce.py"})
    entries = []
    for relative in sorted(paths):
        if excluded_manifest_path(relative):
            continue
        data = expected.get(relative)
        if data is None:
            path = ROOT / relative
            if not path.is_file():
                raise GenerationError(f"manifest input missing: {relative}")
            data = path.read_bytes()
        sha, keccak = file_digests(data)
        entries.append({"path": relative, "bytes": len(data), "sha256": sha, "keccak256": keccak})
    return json_bytes({"schema": "pqtc-research-evidence-manifest-v1", "self_excluded": True,
                       "excluded_path_classes": ["manifest itself", "build", "cache", "target", "user-move"],
                       "entries": entries})


def expected_outputs() -> tuple[dict[str, bytes], list[tuple[dict[str, Any], str, bytes]]]:
    new_records = generate_new_records()
    outputs: dict[str, bytes] = {}
    new_sources: list[tuple[dict[str, Any], str, bytes]] = []
    for record in new_records:
        relative = f"research/runs/{record['run_id']}.json"
        data = json_bytes(record)
        outputs[relative] = data
        new_sources.append((record, relative, data))
    v03 = v03_sources()
    all_sources = [*v03, *new_sources]
    validate_records(all_sources)
    outputs.update(add_v03_appendix_rows({}, v03, all_sources))
    artifact_paths = {item["path"] for record in new_records for item in record["artifacts"]}
    outputs["research/run-records/evidence-manifest.json"] = manifest_bytes(outputs, artifact_paths)
    return outputs, all_sources


def stale_generated(expected: dict[str, bytes]) -> list[str]:
    expected_paths = set(expected)
    actual = {path.relative_to(ROOT).as_posix() for path in RUNS.glob("research-*.json")}
    actual.update(path.relative_to(ROOT).as_posix() for path in SUMMARIES.glob("*.csv") if path.name != "v03-distribution.csv")
    actual_manifest = HERE / "evidence-manifest.json"
    if actual_manifest.exists():
        actual.add(actual_manifest.relative_to(ROOT).as_posix())
    return sorted(actual - expected_paths)


def write_outputs(outputs: dict[str, bytes]) -> None:
    for relative, data in sorted(outputs.items()):
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for relative in stale_generated(outputs):
        (ROOT / relative).unlink()


def check_outputs(outputs: dict[str, bytes]) -> None:
    failures = []
    for relative, expected in sorted(outputs.items()):
        path = ROOT / relative
        if not path.is_file():
            failures.append({"path": relative, "reason": "MISSING"})
        elif path.read_bytes() != expected:
            failures.append({"path": relative, "reason": "BYTE_MISMATCH"})
    failures.extend({"path": path, "reason": "STALE_GENERATED_OUTPUT"} for path in stale_generated(outputs))
    if failures:
        raise GenerationError(json.dumps({"code": "NONDETERMINISTIC_OR_STALE_OUTPUT", "failures": failures}, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed outputs are byte-identical")
    parser.add_argument("--validate-only", action="store_true", help="validate current generated and v03 records without writing")
    args = parser.parse_args(argv)
    try:
        keccak_self_test()
        outputs, sources = expected_outputs()
        if args.validate_only:
            current = []
            for record, path, expected in sources:
                if path.startswith("research/runs/research-"):
                    disk = (ROOT / path).read_bytes()
                    current.append((json.loads(disk), path, disk))
                else:
                    current.append((record, path, expected))
            validate_records(current)
        elif args.check:
            check_outputs(outputs)
        else:
            write_outputs(outputs)
        print(json.dumps({"ok": True, "mode": "validate" if args.validate_only else "check" if args.check else "generate", "new_run_records": sum(1 for path in outputs if path.startswith("research/runs/research-")), "authoritative_v03_records": 60, "outputs": len(outputs)}, sort_keys=True))
        return 0
    except (GenerationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": {"code": "EVIDENCE_LEDGER_FAILED", "message": str(exc)}}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
