#!/usr/bin/env python3
"""Validate runs, hash evidence, verify manifests, and generate CSV summaries."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence

from keccak import Keccak256, self_test as keccak_self_test
from schema_validator import SchemaLoadError, load_json, validate_document

_CHUNK_SIZE = 1024 * 1024
_SCENARIO_COLUMNS = {
    "ACTIVE_EIP7623": "gas_active",
    "SCENARIO_EIP7976_64_PER_BYTE": "gas_64",
    "SCENARIO_EIP8311_96_PER_BYTE": "gas_96",
}
_MEDIA_TYPES = {
    ".csv": "text/csv",
    ".json": "application/json",
    ".txt": "text/plain",
    ".bin": "application/octet-stream",
}
_RUN_FIELDS = (
    "schema_version", "run_id", "candidate_id", "spike_id", "timestamp_utc",
    "case_id", "success", "gate_status", "failure_reason", "confounders", "notes",
    "security_classification", "lowest_accepted_bits", "prover_success", "cold_or_warm",
    "prover_wall_ms", "prover_p50_ms", "prover_p95_ms", "prover_p99_ms",
    "peak_rss_bytes", "native_verify_ms", "raw_proof_bytes", "abi_calldata_bytes",
    "zero_bytes", "nonzero_bytes", "execution_gas", "receipt_gas_used", "gas_active",
    "gas_64", "gas_96", "runtime_bytes", "deployment_gas", "hardware_id", "threads_used",
    "artifacts", "source_run_path", "source_run_sha256", "source_run_keccak256",
)
_CANDIDATE_FIELDS = (
    "candidate_id", "run_count", "successful_run_count", "failed_run_count",
    "gate_statuses", "failure_reasons", "min_proof_bytes", "min_gas_active",
    "min_gas_64", "min_gas_96", "min_prover_p50_ms", "source_run_ids",
)


class ReportError(ValueError):
    """A report input or output is invalid."""


def repository_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "benchmark-run.schema.json").is_file():
            return candidate
    raise ReportError("cannot locate repository root containing benchmark-run.schema.json")


def _hash_file(path: Path) -> tuple[int, str, str]:
    sha = hashlib.sha256()
    keccak = Keccak256()
    size = 0
    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(_CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                sha.update(chunk)
                keccak.update(chunk)
    except OSError as exc:
        raise ReportError(f"cannot hash {path}: {exc}") from exc
    return size, sha.hexdigest(), keccak.hexdigest()


def _relative_file(path: Path, root: Path) -> tuple[Path, str]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ReportError(f"path is outside repository root: {path}") from exc
    if not resolved.is_file():
        raise ReportError(f"not a regular file: {path}")
    return resolved, relative.as_posix()


def _collect_files(inputs: Sequence[Path], root: Path) -> list[Path]:
    root = root.resolve()
    files: dict[str, Path] = {}
    for supplied in inputs:
        path = supplied if supplied.is_absolute() else root / supplied
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ReportError(f"input is outside repository root: {supplied}") from exc
        if resolved.is_dir():
            candidates = (item for item in resolved.rglob("*") if item.is_file())
        elif resolved.is_file():
            candidates = (resolved,)
        else:
            raise ReportError(f"input does not exist: {supplied}")
        for candidate in candidates:
            absolute, relative = _relative_file(candidate, root)
            files[relative] = absolute
    return [files[name] for name in sorted(files)]


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def generate_manifest(inputs: Sequence[Path], output: Path, root: Path) -> dict[str, Any]:
    keccak_self_test()
    root = root.resolve()
    output_path = output if output.is_absolute() else root / output
    output_path = output_path.resolve()
    try:
        output_relative = output_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ReportError("manifest output must be inside repository root") from exc

    artifacts: list[dict[str, Any]] = []
    for file_path in _collect_files(inputs, root):
        relative = file_path.relative_to(root).as_posix()
        if file_path == output_path:
            continue
        size, sha256, keccak256 = _hash_file(file_path)
        media_type = _MEDIA_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
        artifacts.append(
            {
                "path": relative,
                "bytes": size,
                "media_type": media_type,
                "digests": {"sha256": sha256, "keccak256": keccak256},
                "description": None,
            }
        )
    artifacts.sort(key=lambda item: item["path"])
    manifest = {
        "manifest_version": "1",
        "artifacts": artifacts,
        "excluded": [{"path": output_relative, "reason": "self_reference"}],
    }
    _atomic_text(output_path, json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return manifest


def verify_manifest(path: Path, root: Path) -> dict[str, Any]:
    keccak_self_test()
    manifest = load_json(path)
    if not isinstance(manifest, dict) or manifest.get("manifest_version") != "1":
        raise ReportError("manifest_version must equal '1'")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ReportError("manifest artifacts must be an array")
    failures: list[dict[str, str]] = []
    seen: set[str] = set()
    prior = ""
    verified = 0
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            failures.append({"path": f"artifacts[{index}]", "reason": "entry is not an object"})
            continue
        relative = artifact.get("path")
        if not isinstance(relative, str) or not relative:
            failures.append({"path": f"artifacts[{index}]", "reason": "invalid path"})
            continue
        if relative in seen:
            failures.append({"path": relative, "reason": "duplicate path"})
            continue
        seen.add(relative)
        if prior and relative < prior:
            failures.append({"path": relative, "reason": "artifacts are not sorted by path"})
        prior = relative
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            failures.append({"path": relative, "reason": "path escapes repository root"})
            continue
        if not candidate.is_file():
            failures.append({"path": relative, "reason": "file is missing"})
            continue
        expected_size = artifact.get("bytes")
        digests = artifact.get("digests")
        if not isinstance(digests, dict):
            failures.append({"path": relative, "reason": "digests must be an object"})
            continue
        expected_sha = digests.get("sha256")
        expected_keccak = digests.get("keccak256")
        if not isinstance(expected_sha, str) or not isinstance(expected_keccak, str):
            failures.append({"path": relative, "reason": "both digests must be strings"})
            continue
        if not all(len(value) == 64 and value == value.lower() and set(value) <= set("0123456789abcdef") for value in (expected_sha, expected_keccak)):
            failures.append({"path": relative, "reason": "digests must be lowercase 64-hex"})
            continue
        size, sha256, keccak256 = _hash_file(candidate)
        differences = []
        if expected_size != size:
            differences.append("bytes")
        if expected_sha != sha256:
            differences.append("sha256")
        if expected_keccak != keccak256:
            differences.append("keccak256")
        if differences:
            failures.append({"path": relative, "reason": "mismatch: " + ", ".join(differences)})
        else:
            verified += 1
    return {"valid": not failures, "verified_artifacts": verified, "failures": failures}


def validate_run(path: Path, schema_path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    schema = load_json(schema_path)
    document = load_json(path)
    if not isinstance(schema, dict):
        raise ReportError("benchmark schema root must be an object")
    errors = validate_document(document, schema)
    return document, errors


def _json_cell(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _scenario_totals(evm: dict[str, Any]) -> dict[str, Any]:
    totals = {column: "" for column in _SCENARIO_COLUMNS.values()}
    for scenario in evm.get("gas_scenarios", []):
        name = scenario.get("name")
        column = _SCENARIO_COLUMNS.get(name)
        if column is not None:
            totals[column] = scenario.get("total_gas", "")
    return totals


def _run_row(run: dict[str, Any], path: Path, root: Path) -> dict[str, Any]:
    prover = run["prover"]
    distribution = prover.get("distribution", {})
    proof = run["proof_bytes"]
    evm = run["evm"]
    result = run["result"]
    security = run["security"]
    hardware = run["hardware"]
    size, sha256, keccak256 = _hash_file(path)
    del size
    row: dict[str, Any] = {
        "schema_version": run["schema_version"],
        "run_id": run["run_id"],
        "candidate_id": run["candidate_id"],
        "spike_id": run["spike_id"],
        "timestamp_utc": run["timestamp_utc"],
        "case_id": run["protocol"]["case_id"],
        "success": str(result["success"]).lower(),
        "gate_status": result["gate_status"],
        "failure_reason": result.get("failure_reason") or "",
        "confounders": _json_cell(result.get("confounders", [])),
        "notes": _json_cell(result.get("notes", [])),
        "security_classification": security["classification"],
        "lowest_accepted_bits": security["lowest_accepted_bits"] if security["lowest_accepted_bits"] is not None else "",
        "prover_success": str(prover["success"]).lower(),
        "cold_or_warm": prover["cold_or_warm"],
        "prover_wall_ms": prover["wall_ms"] if prover["wall_ms"] is not None else "",
        "prover_p50_ms": distribution.get("p50") if distribution.get("p50") is not None else "",
        "prover_p95_ms": distribution.get("p95") if distribution.get("p95") is not None else "",
        "prover_p99_ms": distribution.get("p99") if distribution.get("p99") is not None else "",
        "peak_rss_bytes": prover["peak_rss_bytes"] if prover["peak_rss_bytes"] is not None else "",
        "native_verify_ms": prover["native_verify_ms"] if prover["native_verify_ms"] is not None else "",
        "raw_proof_bytes": proof["raw_proof_bytes"],
        "abi_calldata_bytes": proof["abi_calldata_bytes"],
        "zero_bytes": proof["zero_bytes"],
        "nonzero_bytes": proof["nonzero_bytes"],
        "execution_gas": evm["execution_gas"],
        "receipt_gas_used": evm["receipt_gas_used"],
        "runtime_bytes": evm["runtime_bytes"],
        "deployment_gas": evm.get("deployment_gas", ""),
        "hardware_id": hardware["hardware_id"],
        "threads_used": hardware.get("threads_used", ""),
        "artifacts": _json_cell(run["artifacts"]),
        "source_run_path": path.resolve().relative_to(root.resolve()).as_posix(),
        "source_run_sha256": sha256,
        "source_run_keccak256": keccak256,
        **_scenario_totals(evm),
    }
    return row


def _csv_text(rows: Iterable[dict[str, Any]], fields: Sequence[str]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def generate_summaries(
    inputs: Sequence[Path],
    all_runs_output: Path,
    candidate_output: Path | None,
    schema_path: Path,
    root: Path,
) -> dict[str, int]:
    root = root.resolve()
    files = [path for path in _collect_files(inputs, root) if path.suffix == ".json"]
    if not files:
        raise ReportError("no JSON run records found")
    rows: list[dict[str, Any]] = []
    validation_failures: list[dict[str, Any]] = []
    run_ids: set[str] = set()
    for path in files:
        run, errors = validate_run(path, schema_path)
        relative = path.relative_to(root).as_posix()
        if errors:
            validation_failures.append({"path": relative, "errors": errors})
            continue
        run_id = run["run_id"]
        if run_id in run_ids:
            validation_failures.append({"path": relative, "errors": [{"path": "$.run_id", "keyword": "unique", "message": f"duplicate run_id {run_id!r}"}]})
            continue
        run_ids.add(run_id)
        rows.append(_run_row(run, path, root))
    if validation_failures:
        raise ReportError("invalid run records: " + _json_cell(validation_failures))
    rows.sort(key=lambda row: (str(row["candidate_id"]), str(row["run_id"]), str(row["source_run_path"])))
    all_path = all_runs_output if all_runs_output.is_absolute() else root / all_runs_output
    _atomic_text(all_path, _csv_text(rows, _RUN_FIELDS))

    candidate_count = 0
    if candidate_output is not None:
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            groups.setdefault(str(row["candidate_id"]), []).append(row)
        candidates: list[dict[str, Any]] = []
        metric_pairs = (
            ("min_proof_bytes", "raw_proof_bytes"),
            ("min_gas_active", "gas_active"),
            ("min_gas_64", "gas_64"),
            ("min_gas_96", "gas_96"),
            ("min_prover_p50_ms", "prover_p50_ms"),
        )
        for candidate_id in sorted(groups):
            group = groups[candidate_id]
            item: dict[str, Any] = {
                "candidate_id": candidate_id,
                "run_count": len(group),
                "successful_run_count": sum(row["success"] == "true" for row in group),
                "failed_run_count": sum(row["success"] != "true" for row in group),
                "gate_statuses": _json_cell(sorted({str(row["gate_status"]) for row in group})),
                "failure_reasons": _json_cell(sorted({str(row["failure_reason"]) for row in group if row["failure_reason"]})),
                "source_run_ids": _json_cell(sorted(str(row["run_id"]) for row in group)),
            }
            for output_name, input_name in metric_pairs:
                values = [row[input_name] for row in group if row[input_name] != ""]
                item[output_name] = min(values) if values else ""
            candidates.append(item)
        candidate_path = candidate_output if candidate_output.is_absolute() else root / candidate_output
        _atomic_text(candidate_path, _csv_text(candidates, _CANDIDATE_FIELDS))
        candidate_count = len(candidates)
    return {"runs": len(rows), "candidates": candidate_count}


class _MachineParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(json.dumps({"ok": False, "error": {"code": "INVALID_ARGUMENTS", "message": message}}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)


def _parser() -> argparse.ArgumentParser:
    parser = _MachineParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True, parser_class=_MachineParser)
    validate = subcommands.add_parser("validate-run")
    validate.add_argument("run", type=Path)
    validate.add_argument("--schema", type=Path)
    manifest = subcommands.add_parser("manifest")
    manifest.add_argument("inputs", type=Path, nargs="+")
    manifest.add_argument("--output", type=Path, required=True)
    verify = subcommands.add_parser("verify-manifest")
    verify.add_argument("manifest", type=Path)
    summary = subcommands.add_parser("summary")
    summary.add_argument("inputs", type=Path, nargs="+")
    summary.add_argument("--output", type=Path, required=True)
    summary.add_argument("--candidate-output", type=Path)
    summary.add_argument("--schema", type=Path)
    subcommands.add_parser("keccak-self-test")
    parser.add_argument("--root", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = args.root.resolve() if args.root else repository_root()
        schema = getattr(args, "schema", None) or root / "benchmark-run.schema.json"
        if args.command == "validate-run":
            _, errors = validate_run(args.run, schema)
            result: dict[str, Any] = {"valid": not errors, "errors": errors}
            exit_code = 0 if not errors else 2
        elif args.command == "manifest":
            result = generate_manifest(args.inputs, args.output, root)
            exit_code = 0
        elif args.command == "verify-manifest":
            result = verify_manifest(args.manifest, root)
            exit_code = 0 if result["valid"] else 2
        elif args.command == "summary":
            result = generate_summaries(args.inputs, args.output, args.candidate_output, schema, root)
            exit_code = 0
        else:
            keccak_self_test()
            result = {"ethereum_keccak256_empty": "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"}
            exit_code = 0
    except (ReportError, SchemaLoadError, OSError) as exc:
        print(json.dumps({"ok": False, "error": {"code": "REPORT_OPERATION_FAILED", "message": str(exc)}}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({"ok": exit_code == 0, "result": result}, sort_keys=True, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
