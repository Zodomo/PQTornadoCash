#!/usr/bin/env python3
"""Run focused defensive regressions for the Plonky3 advisory applicability matrix."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

PIN = "3152b14a89067c83775a8076cc262ffc48a1fd7c"
PATCHES = {
    "GHSA-vrmm-4mm5-38vm": "b5ec4d96bc752e78990db0707f6b60c4f3d9930a",
    "GHSA-m23j-cj9m-ppg9": "367f76133c3e614f65e856ef21c4963237d6907d",
    "GHSA-f69f-5fx9-w9r9": "e784f44924e12a5a6799f3b03c18d1fa6b1a111e",
    "GHSA-3g92-f9ch-qjcm": "5c1dc1d64c0516a8911bbf3ea40f173c21d6ae47",
    "GHSA-vj64-rjf3-w3v7": "5ac9b5ffb899606f97f9663d9853c48524f00402",
}


def run(name: str, command: list[str], root: Path) -> dict:
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    return {
        "name": name,
        "command": command,
        "exitCode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdoutSha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderrSha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def source_checks(root: Path) -> list[dict]:
    cargo = (root / "Cargo.toml").read_text()
    codec = (root / "crates/pqtc-stark/src/codec.rs").read_text()
    crypto = (root / "crates/pqtc-stark/src/crypto.rs").read_text()
    registry = (root / "contracts/src/PQTCVerificationRegistry.sol").read_text()
    checks = {
        "plonky3-pin-exact": cargo.count(f'rev = "{PIN}"') == 16,
        "codec-final-polynomial-exact-length": "fri.final_poly.len() != 1" in codec,
        "codec-exact-end-of-input": "TrailingBytes" in codec and "Truncated" in codec,
        "codec-cross-part-binding": "CrossPartBinding" in codec,
        "typed-length-bound-transcript": "payload.push(item_type)" in crypto and "len.to_be_bytes()" in crypto,
        "full-width-transcript-state": "payload.extend_from_slice(&self.state.to_bytes())" in crypto,
        "solidity-ood-before-fri-alpha": re.search(r"_observeOod\(transcript, globals\.query\);\s*uint256 friAlpha\s*=", registry) is not None,
        "native-catch-unwind-boundary": "catch_unwind" in (root / "crates/pqtc-stark/src/lib.rs").read_text(),
    }
    return [{"name": name, "passed": passed} for name, passed in sorted(checks.items())]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, default=Path("research/advisories/regression-results.json"))
    args = parser.parse_args()
    root = args.root.resolve()

    commands = [
        ("rust-codec-roundtrip-and-shape", ["cargo", "test", "--locked", "--offline", "-p", "pqtc-stark", "codec::tests::two_parts_round_trip_bind_and_verify_natively", "--", "--exact"]),
        ("rust-noncanonical-field", ["cargo", "test", "--locked", "--offline", "-p", "pqtc-stark", "codec::tests::malformed_field_rejected", "--", "--exact"]),
        ("rust-typed-transcript", ["cargo", "test", "--locked", "--offline", "-p", "pqtc-stark", "crypto::tests::transcript_is_typed_and_deterministic", "--", "--exact"]),
        ("rust-full-width-digest", ["cargo", "test", "--locked", "--offline", "-p", "pqtc-stark", "crypto::tests::digest_halves_both_affect_nodes", "--", "--exact"]),
        ("rust-serialized-structured-mutations", ["cargo", "run", "--locked", "--offline", "--release", "-q", "-p", "pqtc-cli", "--", "benchmark-withdrawal", "--profile", "dev"]),
        ("solidity-transcript-shape-mutations", ["forge", "test", "--offline", "--match-contract", "CompactVerifierTest", "--match-test", "testRejects"]),
    ]
    results = [run(name, command, root) for name, command in commands]
    static = source_checks(root)
    result = {
        "schemaVersion": "1",
        "timestampUtc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "plonky3Pin": PIN,
        "upstreamPatchCommits": PATCHES,
        "sourceChecks": static,
        "behavioralChecks": results,
        "allExecutedChecksPassed": all(item["passed"] for item in results) and all(item["passed"] for item in static if item["name"] != "native-catch-unwind-boundary"),
        "unresolved": [
            "The pinned upstream README states that native verification may panic on malformed in-memory proof objects.",
            "PQTC has no catch_unwind boundary around verify_withdrawal; native-catch-unwind-boundary is expected to fail until a later engineering specification addresses it.",
            "The frozen source cannot be edited by this research regression package; serialized decoder mutations do not prove panic-freedom for every constructible StarkProof object."
        ],
        "gateResult": "FAIL" if not any(item["name"] == "native-catch-unwind-boundary" and item["passed"] for item in static) else "PASS",
    }
    output = (root / args.output).resolve() if not args.output.is_absolute() else args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output.relative_to(root)), "gateResult": result["gateResult"], "allExecutedChecksPassed": result["allExecutedChecksPassed"]}, sort_keys=True))
    return 0 if result["allExecutedChecksPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
