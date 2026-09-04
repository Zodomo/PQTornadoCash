#!/usr/bin/env python3
"""Dispatch one exact-pin candidate source check without running benchmarks."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1]
RUNNERS = {
    "C50": RESEARCH / "candidates" / "C50-spartan-whir" / "run.py",
    "C60": RESEARCH / "candidates" / "C60-recursion" / "run.py",
    "C70": RESEARCH / "candidates" / "C70-flock-veil" / "run.py",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", choices=sorted(RUNNERS))
    parser.add_argument("--workspace", type=Path, default=Path(tempfile.gettempdir()) / "pqtornado-emerging")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.workspace / "results" / args.candidate / "source-check"
    return subprocess.run(
        [
            sys.executable,
            str(RUNNERS[args.candidate]),
            "source-check",
            "--workspace",
            str(args.workspace),
            "--output",
            str(output),
        ],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
