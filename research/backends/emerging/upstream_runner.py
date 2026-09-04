#!/usr/bin/env python3
"""Small, dependency-free helpers for exact-pin upstream reproductions."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


class ReproductionError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_checked(argv: Sequence[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        list(argv),
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        command = " ".join(argv)
        raise ReproductionError(
            f"command failed ({completed.returncode}): {command}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed.stdout.strip()


def checkout_exact(repository: str, commit: str, destination: Path) -> Path:
    """Create or verify a detached, tracked-clean checkout at one exact commit."""
    destination = destination.resolve()
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        run_checked(
            ["git", "clone", "--filter=blob:none", "--no-checkout", repository, str(destination)]
        )
    if not (destination / ".git").is_dir():
        raise ReproductionError(f"not a git checkout: {destination}")

    origin = run_checked(["git", "remote", "get-url", "origin"], destination)
    accepted_origins = {repository, repository.removesuffix(".git"), repository.removesuffix(".git") + ".git"}
    if origin not in accepted_origins:
        raise ReproductionError(f"origin mismatch for {destination}: {origin!r}")

    run_checked(["git", "fetch", "--force", "--depth", "1", "origin", commit], destination)
    run_checked(["git", "checkout", "--detach", "--force", "FETCH_HEAD"], destination)
    head = run_checked(["git", "rev-parse", "HEAD"], destination)
    if head != commit:
        raise ReproductionError(f"pin mismatch: expected {commit}, got {head}")
    if subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=destination).returncode != 0:
        raise ReproductionError(f"tracked files are modified in {destination}")
    return destination


def verify_hashes(root: Path, entries: Iterable[Mapping[str, str]]) -> list[dict[str, str]]:
    checked: list[dict[str, str]] = []
    for entry in entries:
        relative = entry["path"]
        expected = entry["sha256"]
        path = root / relative
        if not path.is_file():
            raise ReproductionError(f"missing pinned source file: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise ReproductionError(
                f"source hash mismatch for {path}: expected {expected}, got {actual}"
            )
        checked.append({"path": relative, "sha256": actual})
    return checked


def require_contains(path: Path, needles: Iterable[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            raise ReproductionError(f"expected source marker missing from {path}: {needle!r}")


def require_absent(root: Path, relative_paths: Iterable[str]) -> None:
    present = [relative for relative in relative_paths if (root / relative).exists()]
    if present:
        raise ReproductionError(f"paths expected to be absent are present: {present}")


def tracked_files(root: Path) -> list[str]:
    output = run_checked(["git", "ls-files"], root)
    return output.splitlines() if output else []


def initialize_submodules(root: Path) -> list[dict[str, str]]:
    """Initialize every gitlink recursively and return its exact checked-out commit."""
    if not (root / ".gitmodules").is_file():
        return []
    run_checked(["git", "submodule", "sync", "--recursive"], root)
    run_checked(["git", "submodule", "update", "--init", "--recursive"], root)
    output = run_checked(["git", "submodule", "status", "--recursive"], root)
    initialized: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line or line[0] != " ":
            raise ReproductionError(f"submodule is not pinned at its recorded gitlink: {line!r}")
        commit, path, *_ = line[1:].split()
        initialized.append({"path": path, "commit": commit})
    return initialized


def run_recorded(
    argv: Sequence[str],
    cwd: Path,
    output_dir: Path,
    result: dict,
    *,
    display_command: str | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> dict:
    """Run one command, retain logs, and always emit a machine-readable result."""
    output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    started_at = utc_now()
    command = display_command or " ".join(argv)
    stdout_path = output_dir / "stdout.log"
    stderr_path = output_dir / "stderr.log"
    try:
        completed = subprocess.run(
            list(argv), cwd=cwd, env=env, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError as error:
        stdout_path.write_bytes(b"")
        stderr_path.write_text(f"{error}\n", encoding="utf-8")
        blocker = {
            "kind": "MISSING_PREREQUISITE",
            "executable": error.filename or argv[0],
        }
        result.update(
            {
                "command": command,
                "started_at": started_at,
                "finished_at": utc_now(),
                "execution_status": "NOT_EVALUATED",
                "blocker": blocker,
                "logs": {
                    "stdout": {"path": str(stdout_path), "sha256": sha256_file(stdout_path)},
                    "stderr": {"path": str(stderr_path), "sha256": sha256_file(stderr_path)},
                },
            }
        )
        write_json(output_dir / "result.json", result)
        raise ReproductionError(
            f"missing prerequisite executable: {blocker['executable']}; see {stderr_path}"
        ) from None
    finished_at = utc_now()
    stdout_path.write_bytes(completed.stdout)
    stderr_path.write_bytes(completed.stderr)
    execution_status = "COMPLETED" if completed.returncode == 0 else "FAILED"
    result.update(
        {
            "command": command,
            "started_at": started_at,
            "finished_at": finished_at,
            "execution_status": execution_status,
            "exit_code": completed.returncode,
            "logs": {
                "stdout": {"path": str(stdout_path), "sha256": sha256_file(stdout_path)},
                "stderr": {"path": str(stderr_path), "sha256": sha256_file(stderr_path)},
            },
        }
    )
    write_json(output_dir / "result.json", result)
    if completed.returncode != 0:
        raise ReproductionError(
            f"reproduction command failed with exit code {completed.returncode}; "
            f"see {stdout_path} and {stderr_path}"
        )
    return result


def run_sequence_recorded(
    commands: Sequence[Sequence[str]],
    cwd: Path,
    output_dir: Path,
    result: dict,
    *,
    display_commands: Sequence[str] | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> dict:
    """Run an ordered command sequence and preserve a separate log for each step."""
    output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    started_at = utc_now()
    steps: list[dict[str, object]] = []
    overall_exit = 0
    for index, argv in enumerate(commands, start=1):
        display = (
            display_commands[index - 1]
            if display_commands is not None
            else " ".join(argv)
        )
        stdout_path = output_dir / f"step-{index:02d}.stdout.log"
        stderr_path = output_dir / f"step-{index:02d}.stderr.log"
        try:
            completed = subprocess.run(
                list(argv), cwd=cwd, env=env, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except FileNotFoundError as error:
            stdout_path.write_bytes(b"")
            stderr_path.write_text(f"{error}\n", encoding="utf-8")
            blocker = {
                "kind": "MISSING_PREREQUISITE",
                "executable": error.filename or argv[0],
            }
            steps.append(
                {
                    "command": display,
                    "execution_status": "NOT_EVALUATED",
                    "blocker": blocker,
                    "logs": {
                        "stdout": {"path": str(stdout_path), "sha256": sha256_file(stdout_path)},
                        "stderr": {"path": str(stderr_path), "sha256": sha256_file(stderr_path)},
                    },
                }
            )
            result.update(
                {
                    "commands": list(display_commands)
                    if display_commands is not None
                    else [" ".join(command) for command in commands],
                    "started_at": started_at,
                    "finished_at": utc_now(),
                    "execution_status": "NOT_EVALUATED",
                    "blocker": blocker,
                    "steps": steps,
                }
            )
            write_json(output_dir / "result.json", result)
            raise ReproductionError(
                f"missing prerequisite executable: {blocker['executable']}; see {stderr_path}"
            ) from None
        stdout_path.write_bytes(completed.stdout)
        stderr_path.write_bytes(completed.stderr)
        step_status = "COMPLETED" if completed.returncode == 0 else "FAILED"
        steps.append(
            {
                "command": display,
                "execution_status": step_status,
                "exit_code": completed.returncode,
                "logs": {
                    "stdout": {"path": str(stdout_path), "sha256": sha256_file(stdout_path)},
                    "stderr": {"path": str(stderr_path), "sha256": sha256_file(stderr_path)},
                },
            }
        )
        if completed.returncode != 0:
            overall_exit = completed.returncode
            break
    result.update(
        {
            "commands": list(display_commands)
            if display_commands is not None
            else [" ".join(command) for command in commands],
            "started_at": started_at,
            "finished_at": utc_now(),
            "exit_code": overall_exit,
            "steps": steps,
        }
    )
    result["execution_status"] = "COMPLETED" if overall_exit == 0 else "FAILED"
    write_json(output_dir / "result.json", result)
    if overall_exit != 0:
        failed = steps[-1]
        raise ReproductionError(
            f"reproduction step failed with exit code {overall_exit}: {failed['command']}; "
            f"see {failed['logs']}"
        )
    return result


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
