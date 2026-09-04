#!/usr/bin/env python3
"""Exact-pin source checks and architecture smoke for C60."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
RESEARCH = PACKAGE.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(RESEARCH / "backends" / "emerging"))

from upstream_runner import (  # noqa: E402
    ReproductionError,
    checkout_exact,
    require_contains,
    run_recorded,
    verify_hashes,
    write_json,
)

REPOSITORY = "https://github.com/Plonky3/Plonky3-recursion.git"
COMMIT = "34e3a2c3837834a7bf98a0b65063e0180e7fbb7b"
MANDATED_PLONKY3_VERSION = "0.6.0"
HASHES = [
    {"path": "README.md", "sha256": "c4fd900e21009c20d25b7272f1af1ba31fef721120aefd2b8424eae41e2a6694"},
    {"path": "Cargo.toml", "sha256": "049da0859398c87c1bfc6ad2566116b3f6b32b34f71dada1385bc658c5e7f38d"},
    {"path": "recursion/examples/recursive_fibonacci.rs", "sha256": "22ec9ed3bdcd8efe508a2c5f6e695af2969a28eac6bdda7760e8fbdef077f9a6"},
    {"path": "recursion/examples/recursive_keccak.rs", "sha256": "8940894929ec5b7b7d9f8bb61f819fb642a289925e4bdfee1ab127616c84e006"},
    {"path": "recursion/src/pcs/whir/verifier.rs", "sha256": "39e52bce5e188b5fe64203e5c6f32cd624ff6ea54054dc5d9fb59a4baa46df8d"},
]


def prepare(workspace: Path) -> Path:
    root = checkout_exact(REPOSITORY, COMMIT, workspace / "sources" / "plonky3-recursion-34e3")
    verify_hashes(root, HASHES)
    return root


def source_check(workspace: Path, output: Path) -> None:
    root = prepare(workspace)
    require_contains(root / "Cargo.toml", ['p3-air = "0.7.0"', 'p3-whir = "0.7.0"'])
    require_contains(
        root / "recursion" / "examples" / "recursive_keccak.rs",
        [
            "The base Keccak layer always uses non-ZK uni-stark",
            "The --zk flag has no",
            "effect for recursive_keccak",
            "All recursive layers will",
            "use non-ZK config.",
        ],
    )
    require_contains(
        root / "recursion" / "src" / "pcs" / "whir" / "verifier.rs",
        [
            "mirrors `WhirVerifier::verify`",
            "not the full PCS adapter",
            "belongs in items G/H/I and is passed in by the caller",
        ],
    )
    write_json(
        output / "result.json",
        {
            "schema_version": 1,
            "candidate_id": "C60",
            "run_type": "source_check",
            "evidence_origin": "LOCAL_SOURCE_CHECK_OF_PINNED_UPSTREAM",
            "pqtc_classification": "NOT_PQTC_ARCHITECTURE_EVIDENCE_ONLY",
            "gate_status": "DEFERRED",
            "pin": COMMIT,
            "dependency_gate": {
                "mandated": MANDATED_PLONKY3_VERSION,
                "upstream_recursion": "0.7.0",
                "compatible": False,
            },
            "recursive_keccak_zk": False,
            "recursive_keccak_zk_flag_effect": "NONE",
            "in_circuit_whir": "ORDINARY_WHIR_VERIFIER_NOT_HIDING_PCS_ADAPTER",
            "verified_files": verify_hashes(root, HASHES),
        },
    )


def architecture_smoke(workspace: Path, output: Path) -> None:
    root = prepare(workspace)
    command = [
        "cargo",
        "run",
        "--profile",
        "optimized",
        "--example",
        "recursive_fibonacci",
        "--",
        "--field",
        "baby-bear",
        "--hash",
        "poseidon1",
        "--n",
        "1000",
        "--num-recursive-layers",
        "5",
        "--zk",
    ]
    run_recorded(
        command,
        root,
        output,
        {
            "schema_version": 1,
            "candidate_id": "C60",
            "run_type": "recursive_fibonacci_zk_architecture_smoke",
            "evidence_origin": "LOCAL_REPRODUCTION_OF_PINNED_UPSTREAM",
            "pqtc_classification": "UPSTREAM_ARCHITECTURE_SMOKE_NOT_PQTC",
            "gate_status": "DEFERRED",
            "pin": COMMIT,
            "relation": "TOY_FIBONACCI_NOT_PQTC",
            "dependency_gate": "PLONKY3_0_7_INCOMPATIBLE_WITH_MANDATED_0_6",
            "evm_verifier": False,
        },
        display_command="cargo run --profile optimized --example recursive_fibonacci -- --field baby-bear --hash poseidon1 --n 1000 --num-recursive-layers 5 --zk",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["source-check", "architecture-smoke"])
    parser.add_argument("--workspace", type=Path, default=Path(tempfile.gettempdir()) / "pqtornado-emerging")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.workspace / "results" / "C60" / args.action
    try:
        if args.action == "source-check":
            source_check(args.workspace, output)
        else:
            architecture_smoke(args.workspace, output)
    except ReproductionError as error:
        print(f"C60 reproduction failed: {error}", file=sys.stderr)
        return 1
    print(output / "result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
