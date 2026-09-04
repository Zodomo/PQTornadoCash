#!/usr/bin/env python3
"""Detect benchmark hardware and toolchain details without third-party packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Sequence


class DetectionError(RuntimeError):
    """Environment detection could not produce required benchmark metadata."""


def _run(command: Sequence[str]) -> tuple[str | None, str | None]:
    executable = shutil.which(command[0])
    if executable is None:
        return None, "not found on PATH"
    try:
        process = subprocess.run(
            [executable, *command[1:]],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    output = " ".join(process.stdout.strip().splitlines())
    if process.returncode != 0:
        return None, f"exit {process.returncode}: {output}"
    return output or "UNKNOWN_VERSION", None


def _sysctl(name: str) -> str | None:
    value, error = _run(("sysctl", "-n", name))
    return value if error is None and value != "UNKNOWN_VERSION" else None


def _linux_cpu_info() -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as stream:
            for line in stream:
                key, separator, value = line.partition(":")
                if separator and key.strip() not in result:
                    result[key.strip()] = value.strip()
    except OSError:
        pass
    return result


def _positive(value: str | int | None, fallback: int) -> int:
    try:
        parsed = int(value) if value is not None else 0
    except ValueError:
        parsed = 0
    return parsed if parsed > 0 else fallback


def detect_hardware() -> dict[str, Any]:
    system = platform.system()
    logical = os.cpu_count() or 1
    cpu_model = platform.processor().strip()
    features: list[str] = []
    physical = logical
    ram_bytes = 0

    if system == "Darwin":
        cpu_model = _sysctl("machdep.cpu.brand_string") or cpu_model
        physical = _positive(_sysctl("hw.physicalcpu"), logical)
        logical = _positive(_sysctl("hw.logicalcpu"), logical)
        ram_bytes = _positive(_sysctl("hw.memsize"), 0)
        feature_text = " ".join(
            filter(None, (_sysctl("machdep.cpu.features"), _sysctl("machdep.cpu.leaf7_features")))
        )
        features = sorted(set(feature_text.lower().split()))
    elif system == "Linux":
        info = _linux_cpu_info()
        cpu_model = info.get("model name") or info.get("Hardware") or cpu_model
        features = sorted(set((info.get("flags") or info.get("Features") or "").split()))
        try:
            with open("/proc/meminfo", encoding="ascii") as stream:
                for line in stream:
                    if line.startswith("MemTotal:"):
                        ram_bytes = int(line.split()[1]) * 1024
                        break
        except (OSError, ValueError, IndexError):
            pass
    if ram_bytes <= 0:
        try:
            ram_bytes = int(os.sysconf("SC_PHYS_PAGES")) * int(os.sysconf("SC_PAGE_SIZE"))
        except (AttributeError, OSError, ValueError):
            ram_bytes = 1

    cpu_model = cpu_model or "UNKNOWN"
    identity = {
        "cpu_model": cpu_model,
        "physical_cores": physical,
        "logical_cores": logical,
        "ram_bytes": ram_bytes,
        "os": f"{system} {platform.release()}",
        "architecture": platform.machine() or "UNKNOWN",
    }
    hardware_id = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return {
        "hardware_id": hardware_id,
        **identity,
        "kernel": platform.version(),
        "cpu_features": features,
        "threads_used": logical,
        "allocator": None,
        "power_mode": None,
        "cpu_affinity": None,
    }


def detect_toolchain(evm_revision: str) -> tuple[dict[str, Any], dict[str, str]]:
    if not evm_revision:
        raise DetectionError("evm_revision must be nonempty")
    commands = {
        "rustc": ("rustc", "--version"),
        "cargo": ("cargo", "--version"),
        "solc": ("solc", "--version"),
        "foundry": ("forge", "--version"),
        "node": ("node", "--version"),
    }
    values: dict[str, str | None] = {}
    unavailable: dict[str, str] = {}
    for name, command in commands.items():
        value, error = _run(command)
        values[name] = value
        if error is not None:
            unavailable[name] = error

    package_manager: str | None = None
    for command in (("pnpm", "--version"), ("npm", "--version"), ("yarn", "--version"), ("bun", "--version")):
        value, error = _run(command)
        if error is None:
            package_manager = f"{command[0]} {value}"
            break

    toolchain: dict[str, Any] = {
        "rustc": values["rustc"] or "UNAVAILABLE",
        "cargo": values["cargo"] or "UNAVAILABLE",
        "solc": values["solc"] or "UNAVAILABLE",
        "foundry": values["foundry"] or "UNAVAILABLE",
        "node": values["node"],
        "package_manager": package_manager,
        "evm_revision": evm_revision,
        "rustflags": os.environ.get("RUSTFLAGS", "").split(),
        "container_image_digest": os.environ.get("CONTAINER_IMAGE_DIGEST"),
    }
    return toolchain, dict(sorted(unavailable.items()))


def detect_environment(evm_revision: str) -> dict[str, Any]:
    toolchain, unavailable = detect_toolchain(evm_revision)
    return {
        "hardware": detect_hardware(),
        "toolchain": toolchain,
        "detection": {
            "complete": not unavailable,
            "unavailable_tools": unavailable,
        },
    }


class _MachineParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(json.dumps({"ok": False, "error": {"code": "INVALID_ARGUMENTS", "message": message}}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)


def _parser() -> argparse.ArgumentParser:
    parser = _MachineParser(description=__doc__)
    parser.add_argument("--evm-revision", required=True)
    parser.add_argument("--strict-tools", action="store_true", help="fail if a required schema tool is unavailable")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = detect_environment(args.evm_revision)
        missing_required = {
            key: value
            for key, value in result["detection"]["unavailable_tools"].items()
            if key in {"rustc", "solc", "foundry"}
        }
        if args.strict_tools and missing_required:
            raise DetectionError("required tools unavailable: " + ", ".join(sorted(missing_required)))
    except DetectionError as exc:
        print(json.dumps({"ok": False, "error": {"code": "DETECTION_FAILED", "message": str(exc)}}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "result": result}, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
