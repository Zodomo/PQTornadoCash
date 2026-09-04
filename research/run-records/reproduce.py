#!/usr/bin/env python3
"""One-command, fail-closed interface for the retained research evidence ledger."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACTIONS = {
    "generate": [],
    "check": ["--check"],
    "validate": ["--validate-only"],
}


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if len(values) != 1 or values[0] not in ACTIONS:
        print(json.dumps({
            "ok": False,
            "error": {
                "code": "UNSUPPORTED_REPRODUCTION_ACTION",
                "requested": values,
                "supported": sorted(ACTIONS),
                "reason": "Only deterministic ledger generation, byte checking, and validation are supported; benchmark reruns require their source harnesses and are not silently substituted.",
            },
        }, sort_keys=True), file=sys.stderr)
        return 2
    action = values[0]
    try:
        completed = subprocess.run([sys.executable, str(HERE / "generate.py"), *ACTIONS[action]], cwd=HERE.parents[1])
    except OSError as exc:
        print(json.dumps({"ok": False, "error": {"code": "GENERATOR_UNAVAILABLE", "message": str(exc)}}, sort_keys=True), file=sys.stderr)
        return 2
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
