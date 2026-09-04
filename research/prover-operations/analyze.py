#!/usr/bin/env python3
"""Deterministically audit SP-73 evidence in the 60 frozen v0.3 run records."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUNS = ROOT / "research/runs"
RUN_SCHEMA = ROOT / "benchmark-run.schema.json"
RESULT_SCHEMA = HERE / "result.schema.json"
HARDWARE_PROFILE = ROOT / "research/harness/hardware-detect/h1-m4-max.json"
BASELINE_README = ROOT / "research/candidates/v03-baseline/README.md"
BASELINE_GENERATOR = ROOT / "research/candidates/v03-baseline/scripts/generate-all.py"
PLAN = ROOT / "PQTC_NEXT_GENERATION_RESEARCH_PLAN.md"
SCHEMA_VALIDATOR = ROOT / "research/harness/report-generator/schema_validator.py"
RESULTS = HERE / "results.json"
SOURCE_HASHES = HERE / "source-hashes.json"
EXPECTED_COMMIT = "00f829001999ee66da6fd5161c4c205c07d0b937"
EXPECTED_RUN_IDS = [
    f"v03-{kind}-{index:02d}"
    for kind in ("corpus", "fixed")
    for index in range(1, 31)
]


def load_json(path: Path, *, decimals: bool = False) -> Any:
    kwargs: dict[str, Any] = {"parse_constant": lambda value: (_ for _ in ()).throw(ValueError(f"non-JSON constant {value}"))}
    if decimals:
        kwargs["parse_float"] = Decimal
    with path.open(encoding="utf-8") as stream:
        return json.load(stream, **kwargs)


def load_validator():
    spec = importlib.util.spec_from_file_location("pqtc_schema_validator", SCHEMA_VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load schema validator: {SCHEMA_VALIDATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_document


def fail(message: str) -> None:
    raise ValueError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(document: Any) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def distribution(values: list[Decimal]) -> dict[str, Any]:
    require(bool(values), "cannot summarize an empty measured distribution")
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2

    def nearest_rank(fraction: Decimal) -> Decimal:
        return ordered[math.ceil(fraction * len(ordered)) - 1]

    with localcontext() as context:
        context.prec = 50
        mean = sum(ordered) / len(ordered)
        variance = sum((value - mean) ** 2 for value in ordered) / len(ordered)
        standard_deviation = variance.sqrt()
        quantum = Decimal("0.000000000001")
        rounded_mean = mean.quantize(quantum, rounding=ROUND_HALF_EVEN)
        rounded_standard_deviation = standard_deviation.quantize(quantum, rounding=ROUND_HALF_EVEN)
    return {
        "count": len(ordered),
        "minimum": decimal_text(ordered[0]),
        "median": decimal_text(median),
        "p90_nearest_rank": decimal_text(nearest_rank(Decimal("0.90"))),
        "p95_nearest_rank": decimal_text(nearest_rank(Decimal("0.95"))),
        "p99_nearest_rank": decimal_text(nearest_rank(Decimal("0.99"))),
        "maximum": decimal_text(ordered[-1]),
        "mean_rounded_12_places": decimal_text(rounded_mean),
        "population_standard_deviation_rounded_12_places": decimal_text(rounded_standard_deviation),
    }


def integer_distribution(values: list[int]) -> dict[str, Any]:
    decimal_summary = distribution([Decimal(value) for value in values])
    integer_keys = {
        "minimum", "median", "p90_nearest_rank", "p95_nearest_rank",
        "p99_nearest_rank", "maximum",
    }
    return {
        key: int(value) if key in integer_keys else value
        for key, value in decimal_summary.items()
    }


def source_paths(run_paths: list[Path]) -> list[Path]:
    return sorted([
        RUN_SCHEMA,
        HARDWARE_PROFILE,
        BASELINE_README,
        BASELINE_GENERATOR,
        PLAN,
        SCHEMA_VALIDATOR,
        *run_paths,
    ])


def source_hash_document(run_paths: list[Path]) -> dict[str, Any]:
    return {
        "schemaVersion": "1",
        "studyId": "SP-73",
        "algorithm": "sha256",
        "baselineSourceCommitRecordedByRuns": EXPECTED_COMMIT,
        "files": {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in source_paths(run_paths)
        },
    }


def validate_artifacts(record: dict[str, Any], run_id: str) -> tuple[int, int]:
    artifacts = record["artifacts"]
    require(len(artifacts) == 8, f"{run_id}: expected 8 retained artifacts")
    expected_suffixes = {
        "statement.json", "witness.json", "derived-case.json", "mapping.json",
        "part-a.pqtc", "part-b.pqtc", "part-a.calldata", "part-b.calldata",
    }
    suffixes = {Path(item["path"]).name for item in artifacts}
    require(suffixes == expected_suffixes, f"{run_id}: unexpected artifact set")
    total = 0
    for item in artifacts:
        relative = Path(item["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, f"{run_id}: unsafe artifact path")
        require(relative.parts[:4] == ("research", "candidates", "v03-baseline", "proofs"), f"{run_id}: artifact outside baseline proof tree")
        require(len(relative.parts) == 6 and relative.parts[4] == run_id, f"{run_id}: artifact path/run mismatch")
        path = ROOT / relative
        require(path.is_file(), f"{run_id}: missing artifact {relative.as_posix()}")
        size = path.stat().st_size
        require(size == item["bytes"], f"{run_id}: byte count mismatch for {relative.as_posix()}")
        require(sha256(path) == item["digests"]["sha256"], f"{run_id}: SHA-256 mismatch for {relative.as_posix()}")
        total += size
    return len(artifacts), total


def validate_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], int, int]:
    paths = sorted(RUNS.glob("v03-*.json"))
    require([path.stem for path in paths] == EXPECTED_RUN_IDS, "research/runs must contain exactly v03-{corpus,fixed}-01..30")
    validate_document = load_validator()
    schema = load_json(RUN_SCHEMA)
    records: list[dict[str, Any]] = []
    decimal_records: list[dict[str, Any]] = []
    artifact_count = 0
    artifact_bytes = 0
    seen: set[str] = set()
    for path in paths:
        record = load_json(path)
        errors = validate_document(record, schema)
        require(not errors, f"{path.relative_to(ROOT)}: benchmark-run schema errors: {errors}")
        exact = load_json(path, decimals=True)
        run_id = record["run_id"]
        require(run_id == path.stem and run_id not in seen, f"{path.name}: invalid or duplicate run_id")
        seen.add(run_id)
        require(record["candidate_id"] == "C00/v03-baseline", f"{run_id}: candidate drift")
        require(record["spike_id"] == "SP-00", f"{run_id}: source spike drift")
        require(record["git"]["commit"] == EXPECTED_COMMIT, f"{run_id}: baseline commit drift")
        require(record["result"]["success"] is True and record["prover"]["success"] is True, f"{run_id}: unsuccessful source run")
        require(record["proof_system"]["trusted_setup"] is False, f"{run_id}: trusted-setup flag drift")
        require(record["prover"]["cold_or_warm"] in {"COLD", "WARM"}, f"{run_id}: unknown thermal classification")
        proof = record["proof_bytes"]
        require(proof["raw_proof_bytes"] == proof["zero_bytes"] + proof["nonzero_bytes"], f"{run_id}: raw proof byte accounting mismatch")
        require(proof["abi_calldata_bytes"] == proof["calldata_zero_bytes"] + proof["calldata_nonzero_bytes"], f"{run_id}: calldata byte accounting mismatch")
        require(sum(proof["sections"].values()) == proof["raw_proof_bytes"], f"{run_id}: proof section accounting mismatch")
        by_name = {Path(item["path"]).name: item["bytes"] for item in record["artifacts"]}
        require(by_name["part-a.pqtc"] + by_name["part-b.pqtc"] == proof["raw_proof_bytes"], f"{run_id}: serialized proof size mismatch")
        require(by_name["part-a.calldata"] + by_name["part-b.calldata"] == proof["abi_calldata_bytes"], f"{run_id}: upload/calldata size mismatch")
        count, size = validate_artifacts(record, run_id)
        artifact_count += count
        artifact_bytes += size
        records.append(record)
        decimal_records.append(exact)

    profile = load_json(HARDWARE_PROFILE)
    require(profile["schemaVersion"] == "1" and profile["hardwareClass"] == "H1_CONTINUITY", "invalid H1 hardware profile")
    hw = profile["hardware"]
    require(hw["architecture"] == "arm64" and "NEON" in hw["cpu_features"], "H1 profile is not Apple ARM64/NEON")
    unavailable = {
        item["hardwareClass"]: item["status"]
        for item in profile["unavailableRequiredClasses"]
    }
    require(
        unavailable == {
            "H2_COMMODITY": "UNAVAILABLE_IN_CURRENT_EXECUTION_ENVIRONMENT",
            "H3_HIGH_END": "UNAVAILABLE_IN_CURRENT_EXECUTION_ENVIRONMENT",
        },
        "H1 profile no longer establishes exact H2/H3 unavailability",
    )
    for record in records:
        observed = record["hardware"]
        require(observed["architecture"] == hw["architecture"], f"{record['run_id']}: H1 architecture mismatch")
        require(observed["cpu_model"] == hw["cpu_model"], f"{record['run_id']}: H1 CPU mismatch")
        require(observed["physical_cores"] == hw["physical_cores"], f"{record['run_id']}: H1 physical-core mismatch")
        require(observed["logical_cores"] == hw["logical_cores"], f"{record['run_id']}: H1 logical-core mismatch")
        require(observed["ram_bytes"] == hw["ram_bytes"], f"{record['run_id']}: H1 RAM mismatch")
    return records, decimal_records, profile, artifact_count, artifact_bytes


def measured_or_not(records: list[dict[str, Any]], key: str) -> str:
    return "MEASURED" if all(record["prover"].get(key) is not None for record in records) else "NOT_EVALUATED"


def build_results() -> tuple[dict[str, Any], list[Path]]:
    records, exact, profile, artifact_count, artifact_bytes = validate_records()
    run_paths = sorted(RUNS.glob("v03-*.json"))
    warm = [record for record in exact if record["prover"]["cold_or_warm"] == "WARM"]
    cold = [record for record in exact if record["prover"]["cold_or_warm"] == "COLD"]
    require(len(warm) == 60 and not cold, "committed baseline classification changed; review SP-73 conclusions")

    per_run = []
    for record in exact:
        artifact_total = sum(item["bytes"] for item in record["artifacts"])
        per_run.append({
            "runId": record["run_id"],
            "classification": record["prover"]["cold_or_warm"],
            "wallMs": decimal_text(record["prover"]["wall_ms"]),
            "proofOnlyMs": decimal_text(record["prover"]["proof_only_ms"]),
            "nativeVerifyMs": decimal_text(record["prover"]["native_verify_ms"]),
            "peakRssBytes": record["prover"]["peak_rss_bytes"],
            "rawProofBytes": record["proof_bytes"]["raw_proof_bytes"],
            "abiCalldataBytes": record["proof_bytes"]["abi_calldata_bytes"],
            "retainedArtifactBytes": artifact_total,
        })

    result: dict[str, Any] = {
        "schemaVersion": "1",
        "studyId": "SP-73",
        "candidateId": "C00/v03-baseline",
        "evidenceDisposition": "BASELINE_OPERATIONS_ONLY_NO_FINALIST",
        "inputValidation": {
            "status": "PASS",
            "benchmarkRunSchema": "benchmark-run.schema.json",
            "sourceRecordsValidated": len(records),
            "expectedSourceRecords": 60,
            "artifactsSizeAndSha256Validated": artifact_count,
            "artifactBytesValidated": artifact_bytes,
            "runIdsUniqueAndComplete": True,
            "baselineCommitUniform": EXPECTED_COMMIT,
            "hardwareProfile": "research/harness/hardware-detect/h1-m4-max.json",
        },
        "h1": {
            "status": "PARTIALLY_MEASURED",
            "hardwareClass": profile["hardwareClass"],
            "profileHardwareId": profile["hardware"]["hardware_id"],
            "runRecordHardwareId": records[0]["hardware"]["hardware_id"],
            "profileAndRecordsMatchOn": ["architecture", "cpu_model", "physical_cores", "logical_cores", "ram_bytes"],
            "arm64NeonHardwareCapability": "MEASURED_BY_HARDWARE_PROFILE",
            "neonCodePathExecution": "NOT_EVALUATED",
            "cold": {
                "status": "NOT_EVALUATED",
                "count": len(cold),
                "reason": "No committed run is classified COLD.",
            },
            "warm": {
                "status": "MEASURED",
                "count": len(warm),
                "wallMs": distribution([record["prover"]["wall_ms"] for record in warm]),
                "proofOnlyMs": distribution([record["prover"]["proof_only_ms"] for record in warm]),
                "nativeVerifyMs": distribution([record["prover"]["native_verify_ms"] for record in warm]),
                "peakRssBytes": integer_distribution([record["prover"]["peak_rss_bytes"] for record in warm]),
            },
        },
        "platformsAndBuilds": [
            {"id": "H1_APPLE_ARM64_NEON", "status": "PARTIALLY_MEASURED", "reason": "Sixty warm runs match the H1 Apple M4 Max profile; cold timing and explicit NEON code-path selection are absent."},
            {"id": "H2_COMMODITY_X86_64_AVX2", "status": "NOT_EVALUATED", "reason": "The committed hardware profile marks H2 unavailable and no H2 run record exists."},
            {"id": "H3_HIGH_END_X86_64_AVX512", "status": "NOT_EVALUATED", "reason": "The committed hardware profile marks H3 unavailable and no H3 run record exists."},
            {"id": "SCALAR_PORTABLE", "status": "NOT_EVALUATED", "reason": "No scalar/portable build record or feature-selection evidence exists."},
            {"id": "AVX2_CODE_PATH", "status": "NOT_EVALUATED", "reason": "No x86-64/AVX2 build or run record exists."},
            {"id": "AVX512_CODE_PATH", "status": "NOT_EVALUATED", "reason": "No x86-64/AVX-512 build or run record exists."},
            {"id": "WASM_BROWSER", "status": "NOT_EVALUATED", "reason": "No WASM/browser proof or witness-generation evidence exists; this platform is optional for the SP-73 gate."},
        ],
        "workflows": {
            "setupAndPrecomputation": {"status": "NOT_EVALUATED", "trustedSetupRequired": False, "reason": "The proof system records trusted_setup=false, but setup/precomputation duration and retained cache bytes were not measured."},
            "cancellation": {"status": "NOT_EVALUATED", "reason": "No cancellation attempt, latency, cleanup, or partial-output record exists."},
            "progress": {"status": "NOT_EVALUATED", "reason": "No machine-readable or human progress event stream is retained."},
            "memoryPressure": {"status": "NOT_EVALUATED", "reason": "Peak RSS is measured, but no constrained-memory, swap, OOM, or pressure test exists."},
            "crashRecovery": {"status": "NOT_EVALUATED", "reason": "No checkpoint format, fault injection, resume run, or deterministic resumed-output comparison exists."},
            "cpuTime": {"status": measured_or_not(records, "cpu_ms"), "reason": "All 60 prover.cpu_ms fields are null."},
            "diskUsage": {
                "status": "PARTIALLY_MEASURED",
                "retainedArtifactBytes": artifact_bytes,
                "retainedArtifacts": artifact_count,
                "perRunBytes": integer_distribution([item["retainedArtifactBytes"] for item in per_run]),
                "unmeasured": ["temporary prover files", "build cache", "precomputation cache", "peak free-space requirement"],
            },
            "serializationAndUpload": {
                "status": "MEASURED_BYTES_ONLY",
                "rawProofBytes": integer_distribution([item["rawProofBytes"] for item in per_run]),
                "abiCalldataBytes": integer_distribution([item["abiCalldataBytes"] for item in per_run]),
                "totalRawProofBytes": sum(item["rawProofBytes"] for item in per_run),
                "totalAbiCalldataBytes": sum(item["abiCalldataBytes"] for item in per_run),
                "serializationTime": "NOT_EVALUATED",
                "uploadTime": "NOT_EVALUATED",
                "networkTransport": "NOT_EVALUATED",
            },
        },
        "cliWorkflow": {
            "status": "SPECIFICATION_ONLY_NOT_IMPLEMENTED",
            "gateCredit": False,
            "specification": "research/prover-operations/cli-workflow.json",
            "reason": "The baseline research generator is reproducible but destructive and batch-oriented; no packaged end-user CLI demonstrates prepare/prove/cancel/resume/progress/upload.",
        },
        "operationalPrivacy": {
            "status": "REVIEWED_WITH_OPEN_PRODUCTION_GAPS",
            "review": "research/prover-operations/privacy-review.json",
            "crossUserAggregatorWitnessPolicy": "PROOFS_AND_PUBLIC_STATEMENTS_ONLY_NEVER_WITNESSES",
            "productionWitnessService": "NOT_PROPOSED",
            "secureWitnessIsolation": "NOT_EVALUATED",
            "attestation": "NOT_EVALUATED",
            "productionLocalFallback": "NOT_EVALUATED",
        },
        "gate": {
            "status": "FAIL",
            "rule": "A finalist must have complete H1/H2/H3 measurements and a practical CLI workflow.",
            "blockingIds": [
                "H1_COLD_MISSING", "H2_COMPLETE_MEASUREMENTS_MISSING", "H3_COMPLETE_MEASUREMENTS_MISSING",
                "PRACTICAL_CLI_NOT_IMPLEMENTED", "SETUP_PRECOMPUTATION_MISSING", "CANCELLATION_MISSING",
                "PROGRESS_MISSING", "MEMORY_PRESSURE_MISSING", "CRASH_RECOVERY_MISSING",
            ],
            "securityQualified": False,
            "finalistSelected": False,
        },
        "perRun": per_run,
    }
    return result, run_paths


def validate_result(result: dict[str, Any]) -> None:
    validate_document = load_validator()
    errors = validate_document(result, load_json(RESULT_SCHEMA))
    require(not errors, f"generated result schema errors: {errors}")
    require(result["inputValidation"]["sourceRecordsValidated"] == 60, "result record count drift")
    require(result["h1"]["warm"]["count"] == 60 and result["h1"]["cold"]["count"] == 0, "result cold/warm count drift")
    require(result["gate"]["status"] == "FAIL", "SP-73 gate must fail while H2/H3 are absent")
    require(len(result["perRun"]) == 60, "result per-run count drift")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="replace retained deterministic outputs")
    args = parser.parse_args()
    try:
        result, run_paths = build_results()
        validate_result(result)
        hashes = source_hash_document(run_paths)
        if args.write:
            RESULTS.write_bytes(json_bytes(result))
            SOURCE_HASHES.write_bytes(json_bytes(hashes))
        else:
            require(RESULTS.is_file(), "results.json is missing; run with --write")
            require(SOURCE_HASHES.is_file(), "source-hashes.json is missing; run with --write")
            require(RESULTS.read_bytes() == json_bytes(result), "results.json is stale; inspect inputs, then run with --write")
            require(load_json(SOURCE_HASHES) == hashes, "source-hashes.json does not match committed inputs")
        print(f"validated_source_records=60 validated_artifacts={result['inputValidation']['artifactsSizeAndSha256Validated']} output_schema=PASS gate=FAIL")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"SP-73 validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
