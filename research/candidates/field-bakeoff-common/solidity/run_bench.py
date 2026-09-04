#!/usr/bin/env python3
"""Run the isolated Foundry gas snapshots and write machine-readable evidence."""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
from pathlib import Path

LABEL = re.compile(r"(F[0-5]/op\d+/n\d+):\s*(\d+)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "outputs" / "solidity-latest.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    command = ["forge", "test", "--root", str(root), "--match-test", "testGasSnapshots", "-vv"]
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if completed.returncode != 0:
        print(completed.stdout, end="")
        raise SystemExit(completed.returncode)
    measurements = [
        {"label": match.group(1), "gas": int(match.group(2))}
        for match in LABEL.finditer(completed.stdout)
    ]
    if len(measurements) != 162:
        raise SystemExit(f"expected 162 gas measurements, found {len(measurements)}")
    forge_version = subprocess.run(["forge", "--version"], text=True, stdout=subprocess.PIPE, check=True).stdout.strip()
    report = {
        "schemaVersion": "sp40-solidity-gas-v1",
        "benchmarkOnly": True,
        "completeProofClaimed": False,
        "command": command,
        "forgeVersion": forge_version,
        "platform": platform.platform(),
        "compiler": {"solc": "0.8.30", "evmVersion": "prague", "optimizer": True, "optimizerRuns": 200, "viaIr": True},
        "measurementDefinition": "gasleft delta around an external pure kernel call; includes deterministic input construction and ABI return; excludes transaction intrinsic gas and calldata pricing",
        "measurements": measurements,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(args.out)


if __name__ == "__main__":
    main()
