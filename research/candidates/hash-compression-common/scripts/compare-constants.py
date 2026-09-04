#!/usr/bin/env python3
"""Regenerate Grain/SHAKE constants and compare pinned literals."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

COMMIT = "3152b14a89067c83775a8076cc262ffc48a1fd7c"

def fail(message: str) -> None:
    print(json.dumps({"ok": False, "error": message}, sort_keys=True), file=sys.stderr)
    raise SystemExit(2)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plonky3", type=Path, required=True, help="checkout at the pinned commit")
    parser.add_argument("--constants", type=Path, default=Path(__file__).resolve().parents[1] / "constants/pinned.json")
    args = parser.parse_args()
    root = args.plonky3.resolve()
    actual_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, text=True, capture_output=True).stdout.strip()
    if actual_commit != COMMIT: fail(f"checkout is {actual_commit}, expected {COMMIT}")
    pinned = json.loads(args.constants.read_text())
    compared = {}
    generator = root / "poseidon2/generate_constants.py"
    for width in (16, 24, 32):
        process = subprocess.run([sys.executable, str(generator), "--field", "babybear", "--width", str(width), "--format", "json", "--skip-matrix"], check=True, text=True, capture_output=True)
        generated = json.loads(process.stdout)
        expected = pinned["poseidon2"][str(width)]
        sections = {
            "initial": [int(value, 16) for row in generated["external_initial"] for value in row],
            "internal": [int(value, 16) for value in generated["internal"]],
            "final": [int(value, 16) for row in generated["external_final"] for value in row],
        }
        for name, values in sections.items():
            if values != expected[name]: fail(f"Poseidon2 width {width} {name} mismatch")
        compared[f"poseidon2-{width}"] = {"constants": sum(map(len, [sections["initial"], sections["internal"], sections["final"]])), "sha256": hashlib.sha256(process.stdout.encode()).hexdigest()}
    seed = pinned["rpoM31"]["seed"].encode()
    count = 2 * 24 * 7 + 24
    stream = hashlib.shake_256(seed).digest(5 * count)
    generated_rpo = [int.from_bytes(stream[i:i+5], "little") % 2147483647 for i in range(0, len(stream), 5)]
    if generated_rpo != pinned["rpoM31"]["roundConstants"]: fail("RPO-M31 SHAKE constants mismatch")
    compared["rpo-m31"] = {"constants": count, "shake256StreamSha256": hashlib.sha256(stream).hexdigest()}
    print(json.dumps({"ok": True, "commit": COMMIT, "compared": compared}, sort_keys=True, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
