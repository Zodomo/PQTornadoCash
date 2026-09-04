#!/usr/bin/env python3
"""Deterministic, fail-closed controller for the PQTC research evidence package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PACKAGE = Path(__file__).resolve().parent
DEFAULT_ROOT = PACKAGE.parents[1]
DEFAULT_REGISTRY = PACKAGE / "command-registry.json"
DEFAULT_MANIFEST = PACKAGE / "evidence-manifest.json"
WORK = PACKAGE / ".work"
UNAVAILABLE = "NOT_AVAILABLE_NO_ELIGIBLE_FINALIST"
ACTIONS = ("build", "corpus", "prove", "verify-native", "verify-evm", "security", "report")
MINIMUM_CANDIDATES = {"C00", "C01", "C10", "C11", "C12", "C20", "C21", "C22", "C23", "C30", "C40"}
EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".cache", "cache", "target", "out", "old_plans", "old_reports",
    ".work", ".tmp", "tmp", "temp",
}
EXCLUDED_NAMES = {".DS_Store", "evidence-manifest.json"}
EXCLUDED_SUFFIXES = (".tmp", ".temp", ".swp", "~")
SAFE_ENV_KEYS = {
    "PATH", "HOME", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL", "LC_CTYPE",
    "CARGO_HOME", "RUSTUP_HOME", "RUST_BACKTRACE", "SSL_CERT_FILE", "SSL_CERT_DIR",
    "NIX_PATH", "NIX_PROFILES", "TERM",
}


class ReproductionError(Exception):
    def __init__(self, code: str, message: str, details: Any | None = None):
        super().__init__(message)
        self.code = code
        self.details = details


class MachineParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        emit_error("INVALID_ARGUMENTS", message)
        raise SystemExit(2)


@dataclass(frozen=True)
class Command:
    argv: tuple[str, ...]
    cwd: Path
    env: tuple[tuple[str, str], ...] = ()

    def document(self, root: Path) -> dict[str, Any]:
        try:
            cwd = self.cwd.relative_to(root).as_posix() or "."
        except ValueError:
            cwd = str(self.cwd)
        prefix = [f"{key}={value}" for key, value in self.env]
        return {
            "argv": list(self.argv),
            "cwd": cwd,
            "env": dict(self.env),
            "shell": shlex.join([*prefix, *self.argv]),
        }


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def emit(value: Any) -> None:
    sys.stdout.write(canonical_json(value))


def emit_error(code: str, message: str, details: Any | None = None) -> None:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    sys.stderr.write(canonical_json({"error": error, "ok": False}))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ReproductionError("PATH_OUTSIDE_REPOSITORY", f"path is outside repository: {path}") from exc


def is_excluded(root: Path, path: Path, manifest_path: Path) -> bool:
    resolved = path.resolve()
    if resolved == manifest_path.resolve():
        return True
    rel = resolved.relative_to(root.resolve())
    if any(part in EXCLUDED_DIRS for part in rel.parts[:-1]):
        return True
    if rel.name in EXCLUDED_NAMES or rel.name.startswith(".env"):
        return True
    return any(rel.name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)


def collect_files(root: Path, inputs: Iterable[Path], manifest_path: Path) -> list[Path]:
    files: set[Path] = set()
    for supplied in inputs:
        path = supplied if supplied.is_absolute() else root / supplied
        path = path.resolve()
        relative(root, path)
        if not path.exists():
            raise ReproductionError("MANIFEST_INPUT_MISSING", f"manifest input does not exist: {relative(root, path)}")
        candidates = [path] if path.is_file() else path.rglob("*")
        for candidate in candidates:
            if candidate.is_file() and not candidate.is_symlink() and not is_excluded(root, candidate, manifest_path):
                files.add(candidate.resolve())
    return sorted(files, key=lambda item: relative(root, item))


def generate_manifest(root: Path, inputs: list[Path], output: Path) -> dict[str, Any]:
    files = collect_files(root, inputs, output)
    roots = sorted(relative(root, (item if item.is_absolute() else root / item)) for item in inputs)
    return {
        "schema": "pqtc.reproduction.evidence-manifest.v1",
        "hashAlgorithm": "sha256",
        "inventoryPolicy": "PINNED_FILES_ALLOW_ADDITIONS",
        "roots": roots,
        "exclusions": {
            "directories": sorted(EXCLUDED_DIRS),
            "names": sorted(EXCLUDED_NAMES),
            "secretNames": [".env", ".env.*"],
            "temporarySuffixes": list(EXCLUDED_SUFFIXES),
            "manifestExcludesItself": True,
        },
        "files": [
            {"path": relative(root, path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in files
        ],
    }


def load_json(path: Path, code: str = "INVALID_JSON") -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReproductionError("FILE_NOT_FOUND", f"file not found: {path}") from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReproductionError(code, f"invalid JSON in {path}: {exc}") from exc


def validate_manifest_shape(document: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["manifest must be an object"]
    if document.get("schema") != "pqtc.reproduction.evidence-manifest.v1":
        errors.append("unexpected manifest schema")
    if document.get("hashAlgorithm") != "sha256":
        errors.append("hashAlgorithm must be sha256")
    rows = document.get("files")
    if not isinstance(rows, list):
        return [*errors, "files must be an array"]
    prior = ""
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"files[{index}] must be an object")
            continue
        path = row.get("path")
        digest = row.get("sha256")
        size = row.get("bytes")
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in Path(path).parts:
            errors.append(f"files[{index}].path is not a safe relative path")
            continue
        if path in seen:
            errors.append(f"duplicate path: {path}")
        if prior and path <= prior:
            errors.append(f"files are not strictly sorted at: {path}")
        seen.add(path)
        prior = path
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            errors.append(f"invalid sha256 for: {path}")
        if not isinstance(size, int) or size < 0:
            errors.append(f"invalid byte count for: {path}")
    return errors


def verify_manifest(root: Path, path: Path) -> dict[str, Any]:
    document = load_json(path, "INVALID_EVIDENCE_MANIFEST")
    errors = validate_manifest_shape(document)
    checked = 0
    for row in document.get("files", []) if isinstance(document, dict) else []:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            continue
        artifact = (root / row["path"]).resolve()
        try:
            relative(root, artifact)
        except ReproductionError as exc:
            errors.append(str(exc))
            continue
        if is_excluded(root, artifact, path):
            errors.append(f"excluded path is present in manifest: {row['path']}")
            continue
        if not artifact.is_file() or artifact.is_symlink():
            errors.append(f"missing regular file: {row['path']}")
            continue
        checked += 1
        actual_size = artifact.stat().st_size
        actual_digest = sha256_file(artifact)
        if actual_size != row.get("bytes"):
            errors.append(f"byte count mismatch: {row['path']}")
        if actual_digest != row.get("sha256"):
            errors.append(f"sha256 mismatch: {row['path']}")
    return {"checkedFiles": checked, "errors": errors, "manifest": relative(root, path), "valid": not errors}


def validate_registry(document: Any, root: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(document, dict) or document.get("schema") != "pqtc.reproduction.command-registry.v1":
        return ["unexpected command registry schema"]
    candidates = document.get("candidates")
    components = document.get("components")
    if not isinstance(candidates, dict):
        return ["candidates must be an object"]
    if not isinstance(components, dict):
        errors.append("components must be an object")
        components = {}
    missing = sorted(MINIMUM_CANDIDATES - set(candidates))
    if missing:
        errors.append("missing minimum candidates: " + ", ".join(missing))
    for candidate_id, candidate in candidates.items():
        if not isinstance(candidate, dict):
            errors.append(f"candidate {candidate_id} must be an object")
            continue
        if candidate.get("eligibleFinalist") is not False:
            errors.append(f"candidate {candidate_id} must be marked non-finalist")
        actions = candidate.get("actions")
        if not isinstance(actions, dict):
            errors.append(f"candidate {candidate_id} has no actions")
            continue
        for action in ACTIONS:
            value = actions.get(action)
            if value not in {"AVAILABLE", UNAVAILABLE}:
                errors.append(f"candidate {candidate_id} action {action} has invalid availability")
        entrypoints = candidate.get("actionEntrypoints")
        prerequisites = candidate.get("prerequisites")
        if not isinstance(entrypoints, dict) or set(entrypoints) != set(ACTIONS):
            errors.append(f"candidate {candidate_id} must map every action entrypoint")
        if not isinstance(prerequisites, dict) or set(prerequisites) != set(ACTIONS):
            errors.append(f"candidate {candidate_id} must map every action prerequisite")
        if isinstance(entrypoints, dict):
            for action in ACTIONS:
                commands = entrypoints.get(action)
                if not isinstance(commands, list):
                    errors.append(f"candidate {candidate_id} action {action} entrypoints must be an array")
                elif actions.get(action) == "AVAILABLE" and not commands:
                    errors.append(f"candidate {candidate_id} available action {action} has no entrypoint")
                elif actions.get(action) == UNAVAILABLE and commands:
                    errors.append(f"candidate {candidate_id} unavailable action {action} has an entrypoint")
        for artifact in candidate.get("pinnedArtifacts", []):
            if not isinstance(artifact, str) or artifact.startswith("/") or ".." in Path(artifact).parts:
                errors.append(f"candidate {candidate_id} has unsafe artifact path")
    for component_id, component in components.items():
        if not isinstance(component, dict) or not component.get("package") or not component.get("entrypoints"):
            errors.append(f"component {component_id} lacks package or entrypoints")
            continue
        package = root / component["package"]
        if not package.exists():
            errors.append(f"component {component_id} package missing: {component['package']}")
    return errors


def load_registry(root: Path) -> dict[str, Any]:
    document = load_json(DEFAULT_REGISTRY, "INVALID_COMMAND_REGISTRY")
    errors = validate_registry(document, root)
    if errors:
        raise ReproductionError("INVALID_COMMAND_REGISTRY", "command registry validation failed", errors)
    return document


def command(argv: list[str], root: Path, cwd: str = ".", env: dict[str, str] | None = None) -> Command:
    return Command(tuple(argv), (root / cwd).resolve(), tuple(sorted((env or {}).items())))


def c00_jobs(root: Path, cases: str, runs: int) -> list[dict[str, Any]]:
    document = load_json(root / "research/candidates/v03-baseline/vectors/derived/jobs.json")
    jobs = document.get("jobs", [])
    fixed = [job for job in jobs if job.get("kind") == "fixed-baseline"]
    corpus = [job for job in jobs if job.get("kind") == "semantic-corpus"]
    if cases == "fixed":
        selected = fixed
    elif cases == "corpus":
        selected = corpus
    else:
        selected = [item for pair in zip(fixed, corpus) for item in pair]
    if runs < 1:
        raise ReproductionError("INVALID_ARGUMENTS", "--runs must be positive")
    if runs > len(selected):
        raise ReproductionError("INSUFFICIENT_CANONICAL_CASES", f"requested {runs} runs, but case set {cases} has {len(selected)}")
    return selected[:runs]


def action_commands(args: argparse.Namespace, root: Path, registry: dict[str, Any]) -> list[Command]:
    candidate = registry["candidates"].get(args.candidate)
    if candidate is None:
        raise ReproductionError("UNKNOWN_CANDIDATE", f"unknown candidate: {args.candidate}")
    availability = candidate["actions"][args.command]
    if availability != "AVAILABLE":
        raise ReproductionError(UNAVAILABLE, f"{args.command} is unavailable for {args.candidate}: no eligible integrated finalist exists", {
            "candidate": args.candidate,
            "action": args.command,
            "status": availability,
        })
    python = "python3"
    baseline = "research/candidates/v03-baseline"
    binary = f"{baseline}/native/target/release/v03-baseline-reproducer"
    if args.candidate == "C01" and args.command == "security":
        return [command([python, "research/security-model/calculator/security_calculator.py", "calculate", "research/security-model/manifests/v02-style-q48-width190.json", "--format", "json"], root)]
    if args.candidate != "C00":
        raise ReproductionError(UNAVAILABLE, f"{args.command} is unavailable for {args.candidate}: no eligible integrated finalist exists")
    if args.command == "build":
        return [command(["cargo", "build", "--locked", "--offline", "--release", "--manifest-path", f"{baseline}/native/Cargo.toml"], root)]
    if args.command == "corpus":
        return [command([binary, "prepare", "--corpus", "research/common-corpus/semantic-cases.json", "--out", "research/reproduction/.work/C00/corpus"], root)]
    if args.command == "prove":
        commands: list[Command] = []
        for job in c00_jobs(root, args.cases, args.runs):
            commands.append(command([
                binary, "prove", "--input", f"research/reproduction/.work/C00/corpus/{job['input']}",
                "--out", f"research/reproduction/.work/C00/proofs/{job['run_id']}",
            ], root))
        return commands
    if args.command == "verify-native":
        if not args.all:
            raise ReproductionError("INVALID_ARGUMENTS", "verify-native requires --all")
        jobs = c00_jobs(root, "all", 60)
        return [command([
            binary, "verify", "--input", f"{baseline}/vectors/derived/{job['input']}",
            "--proof", f"{baseline}/proofs/{job['run_id']}",
        ], root) for job in jobs]
    if args.command == "verify-evm":
        if args.client != "anvil":
            raise ReproductionError("LIVE_CHAIN_FORBIDDEN", "only the local Foundry/Anvil execution client is permitted")
        jobs = c00_jobs(root, "all", 60)
        return [command([
            "forge", "test", "--root", ".", "--match-test",
            "testArbitraryGeneratedFixtureThroughCompletePoolCalls", "-vvvv",
        ], root, f"{baseline}/evm", {"V03_FIXTURE_DIR": f"../proofs/{job['run_id']}"}) for job in jobs]
    if args.command == "security":
        return [command([python, "research/security-model/calculator/security_calculator.py", "calculate", "research/security-model/manifests/v03-q32.json", "--format", "json"], root)]
    if args.command == "report":
        runs = sorted((root / "research/runs").glob("v03-*.json"))
        if len(runs) != 60:
            raise ReproductionError("PINNED_RUN_SET_INCOMPLETE", f"expected 60 authoritative v03 run records, found {len(runs)}")
        return [command([
            python, "research/harness/benchctl/benchctl.py", "summary",
            *[relative(root, item) for item in runs],
            "--output", "research/reproduction/.work/C00/gas-and-proof-summary.csv",
            "--candidate-output", "research/reproduction/.work/C00/candidate-summary.csv",
            "--schema", "benchmark-run.schema.json",
        ], root)]
    raise ReproductionError("INVALID_ARGUMENTS", f"unknown action: {args.command}")


def sanitized_environment(extra: tuple[tuple[str, str], ...]) -> dict[str, str]:
    clean = {key: value for key, value in os.environ.items() if key in SAFE_ENV_KEYS}
    clean.update(extra)
    clean["PQTC_REPRODUCTION_NO_LIVE_CHAIN"] = "1"
    return clean


def execute_commands(commands: list[Command], root: Path, dry_run: bool) -> list[dict[str, Any]]:
    documents = [item.document(root) for item in commands]
    if dry_run:
        return [{**item, "executed": False} for item in documents]
    results: list[dict[str, Any]] = []
    for spec, item in zip(commands, documents):
        executable = spec.argv[0]
        if "/" in executable:
            executable_path = (spec.cwd / executable).resolve() if not Path(executable).is_absolute() else Path(executable)
            if not executable_path.exists():
                raise ReproductionError("PREREQUISITE_MISSING", f"executable not found: {executable}")
        elif shutil.which(executable, path=sanitized_environment(spec.env).get("PATH")) is None:
            raise ReproductionError("PREREQUISITE_MISSING", f"required tool is unavailable: {executable}")
        completed = subprocess.run(
            list(spec.argv), cwd=spec.cwd, env=sanitized_environment(spec.env),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False, check=False,
        )
        record = {
            **item,
            "executed": True,
            "returnCode": completed.returncode,
            "stdoutBytes": len(completed.stdout),
            "stdoutSha256": hashlib.sha256(completed.stdout).hexdigest(),
            "stderrBytes": len(completed.stderr),
            "stderrSha256": hashlib.sha256(completed.stderr).hexdigest(),
        }
        results.append(record)
        if completed.returncode != 0:
            raise ReproductionError("COMMAND_FAILED", f"command failed with exit {completed.returncode}: {item['shell']}", {
                "command": record,
                "stdout": completed.stdout.decode("utf-8", "replace")[-8192:],
                "stderr": completed.stderr.decode("utf-8", "replace")[-8192:],
            })
    return results


def verify_fresh_proofs(root: Path, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    proof_ids: set[str] = set()
    for job in jobs:
        generated = WORK / "C00/proofs" / job["run_id"] / "proof-metadata.json"
        retained = root / "research/candidates/v03-baseline/proofs" / job["run_id"] / "proof-metadata.json"
        metadata = load_json(generated)
        original = load_json(retained)
        if metadata.get("entropy_source") != "operating-system entropy through pqtc_stark::withdrawal_config_from_os_entropy; no caller seed":
            raise ReproductionError("HIDING_PROOF_NOT_ESTABLISHED", f"unexpected entropy source for {job['run_id']}")
        if metadata.get("native_verified") is not True or metadata.get("codec_roundtrip_verified") is not True:
            raise ReproductionError("PROOF_VERIFICATION_FAILED", f"proof was not verified and codec-round-tripped: {job['run_id']}")
        proof_id = metadata.get("proof_id")
        if not isinstance(proof_id, str) or proof_id == original.get("proof_id") or proof_id in proof_ids:
            raise ReproductionError("FRESHNESS_CHECK_FAILED", f"proof is not fresh and distinct: {job['run_id']}")
        proof_ids.add(proof_id)
    return {"freshDistinctProofs": len(proof_ids), "hidingEntropy": "OPERATING_SYSTEM", "nativeVerified": True}


def verify_candidate_pins(root: Path, registry: dict[str, Any], candidate_ids: list[str], manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path, "INVALID_EVIDENCE_MANIFEST")
    pins = {row["path"]: row for row in manifest.get("files", []) if isinstance(row, dict) and isinstance(row.get("path"), str)}
    checked: list[str] = []
    errors: list[str] = []
    for candidate_id in candidate_ids:
        candidate = registry["candidates"].get(candidate_id)
        if candidate is None:
            errors.append(f"unknown candidate: {candidate_id}")
            continue
        for artifact in candidate["pinnedArtifacts"]:
            row = pins.get(artifact)
            path = root / artifact
            if row is None:
                errors.append(f"artifact is not pinned by evidence manifest: {artifact}")
            elif not path.is_file():
                errors.append(f"pinned artifact missing: {artifact}")
            elif path.stat().st_size != row.get("bytes") or sha256_file(path) != row.get("sha256"):
                errors.append(f"pinned artifact mismatch: {artifact}")
            else:
                checked.append(artifact)
    return {"candidates": candidate_ids, "checkedArtifacts": sorted(set(checked)), "errors": errors, "valid": not errors}


def all_safe(root: Path, registry: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    manifest_result = verify_manifest(root, manifest_path)
    pins_result = verify_candidate_pins(root, registry, sorted(registry["candidates"]), manifest_path)
    package_json = [
        "research/reproduction/manifest.json", "research/reproduction/status.json",
        "research/reproduction/assumptions.json", "research/reproduction/negative-results.json",
        "research/reproduction/command-registry.json",
        "research/reproduction/schemas/command-registry.schema.json",
        "research/reproduction/schemas/evidence-manifest.schema.json",
        "research/reproduction/schemas/result.schema.json",
    ]
    json_errors: list[str] = []
    for item in package_json:
        try:
            load_json(root / item)
        except ReproductionError as exc:
            json_errors.append(str(exc))
    errors = [*manifest_result["errors"], *pins_result["errors"], *json_errors]
    return {
        "mode": "ALL_SAFE_READ_ONLY",
        "liveChainActions": 0,
        "secretInputs": 0,
        "subprocesses": 0,
        "manifest": manifest_result,
        "candidatePins": pins_result,
        "jsonDocumentsChecked": len(package_json),
        "errors": errors,
        "valid": not errors,
    }


def parser() -> MachineParser:
    value = MachineParser(description=__doc__)
    value.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    sub = value.add_subparsers(dest="command", required=True, parser_class=MachineParser)

    registry = sub.add_parser("registry", help="print the validated candidate/action registry")
    registry.add_argument("--candidate")

    manifest = sub.add_parser("manifest", help="generate the deterministic evidence manifest")
    manifest.add_argument("--input", action="append", type=Path, dest="inputs")
    manifest.add_argument("--output", type=Path, default=DEFAULT_MANIFEST)

    verify_manifest_parser = sub.add_parser("verify-manifest", help="verify pinned evidence hashes")
    verify_manifest_parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)

    verify = sub.add_parser("verify", help="verify candidate pinned artifacts")
    verify.add_argument("--candidate", required=True)
    verify.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)

    sub.add_parser("all-safe", help="perform only read-only, offline, non-secret verification")

    for name in ACTIONS:
        action = sub.add_parser(name)
        action.add_argument("--candidate", required=True)
        if name == "prove":
            action.add_argument("--cases", choices=("fixed", "corpus", "all"), required=True)
            action.add_argument("--runs", type=int, required=True)
        elif name == "verify-native":
            action.add_argument("--all", action="store_true")
        elif name == "verify-evm":
            action.add_argument("--client", choices=("anvil",), required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    dry_run = False
    while "--dry-run" in arguments:
        arguments.remove("--dry-run")
        dry_run = True
    args = parser().parse_args(arguments)
    root = args.root.resolve()
    try:
        registry = load_registry(root)
        if args.command == "registry":
            result = registry if args.candidate is None else registry["candidates"].get(args.candidate)
            if result is None:
                raise ReproductionError("UNKNOWN_CANDIDATE", f"unknown candidate: {args.candidate}")
            emit({"ok": True, "result": result})
            return 0
        if args.command == "manifest":
            output = args.output if args.output.is_absolute() else root / args.output
            inputs = args.inputs or [Path("benchmark-run.schema.json"), Path("PQTC_NEXT_GENERATION_RESEARCH_PLAN.md"), Path("research")]
            if dry_run:
                cli = ["python3", "research/reproduction/reproduce.py", "manifest"]
                for item in inputs:
                    cli.extend(["--input", str(item)])
                cli.extend(["--output", relative(root, output)])
                emit({"ok": True, "result": {"dryRun": True, "commands": [command(cli, root).document(root)]}})
                return 0
            document = generate_manifest(root, inputs, output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(canonical_json(document), encoding="utf-8")
            emit({"ok": True, "result": {"files": len(document["files"]), "output": relative(root, output), "sha256": sha256_file(output)}})
            return 0
        if args.command == "verify-manifest":
            path = args.manifest if args.manifest.is_absolute() else root / args.manifest
            if dry_run:
                emit({"ok": True, "result": {"dryRun": True, "commands": [command(["python3", "research/reproduction/reproduce.py", "verify-manifest", relative(root, path)], root).document(root)]}})
                return 0
            result = verify_manifest(root, path)
            emit({"ok": result["valid"], "result": result})
            return 0 if result["valid"] else 2
        if args.command == "verify":
            path = args.manifest if args.manifest.is_absolute() else root / args.manifest
            if dry_run:
                cli = ["python3", "research/reproduction/reproduce.py", "verify", "--candidate", args.candidate, "--manifest", relative(root, path)]
                emit({"ok": True, "result": {"dryRun": True, "commands": [command(cli, root).document(root)]}})
                return 0
            candidate_ids = sorted(registry["candidates"]) if args.candidate == "all" else [args.candidate]
            result = verify_candidate_pins(root, registry, candidate_ids, path)
            emit({"ok": result["valid"], "result": result})
            return 0 if result["valid"] else 2
        if args.command == "all-safe":
            if dry_run:
                emit({"ok": True, "result": {"dryRun": True, "commands": [command(["python3", "research/reproduction/reproduce.py", "all-safe"], root).document(root)]}})
                return 0
            result = all_safe(root, registry, root / "research/reproduction/evidence-manifest.json")
            emit({"ok": result["valid"], "result": result})
            return 0 if result["valid"] else 2
        commands = action_commands(args, root, registry)
        results = execute_commands(commands, root, dry_run)
        result: dict[str, Any] = {
            "action": args.command,
            "candidate": args.candidate,
            "dryRun": dry_run,
            "commands": results,
            "executedCommands": 0 if dry_run else len(results),
        }
        if args.command == "prove" and not dry_run:
            result["proofs"] = verify_fresh_proofs(root, c00_jobs(root, args.cases, args.runs))
        emit({"ok": True, "result": result})
        return 0
    except ReproductionError as exc:
        emit_error(exc.code, str(exc), exc.details)
        return 2
    except OSError as exc:
        emit_error("IO_ERROR", str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
