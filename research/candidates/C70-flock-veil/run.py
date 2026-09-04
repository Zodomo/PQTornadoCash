#!/usr/bin/env python3
"""Historical Flock benchmark and VEIL source gates for C70."""

from __future__ import annotations

import argparse
import json
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
    require_absent,
    require_contains,
    run_recorded,
    tracked_files,
    verify_hashes,
    write_json,
)

FLOCK_REPOSITORY = "https://github.com/succinctlabs/flock.git"
FLOCK_RELEASE_COMMIT = "43f0eee06d887d87ad25d72614cbc2b17fe91430"
FLOCK_KECCAK_PARENT = "c2d0c2485a54f7b7694e19f4f59730ffde3405cf"
FLOCK_KECCAK_REMOVAL = "0f0d63268e1373c585251e95152b3a6943e2d818"
VEIL_REPOSITORY = "https://github.com/succinctlabs/sp1.git"
VEIL_COMMIT = "6d7ee5c091ad19e957a5faa5869de8739a76aa78"

HISTORICAL_HASHES = [
    {"path": "crates/flock-prover/benches/keccak3_proof.rs", "sha256": "965b64f1783814e62afee1a281fbbb33987d86555f3b3f0f5a25f23095f0c616"},
    {"path": "crates/flock-prover/src/r1cs_hashes/keccak3.rs", "sha256": "f3bc3f7cdf477078a135b70b0eeee470d062b5be38bf075e5a59f7efa9dd14bf"},
    {"path": "crates/flock-prover/src/prover.rs", "sha256": "b5cf6523e987ae7e0ba23aaf07a3a3c089e3e724a8cec7b5a90a98b9f4641f7b"},
    {"path": "crates/flock-core/src/pcs/ligerito.rs", "sha256": "1e607b05604c5eb37cd68d9db57a56eb3e44f2e2680f056e4e86e3235494b4a5"},
]
RELEASE_HASHES = [
    {"path": "README.md", "sha256": "76b0b7dc0d73e8b46efb5f7c5f988e9bb8201350d1c871e8ae21cf39e1534ac6"}
]
REMOVAL_HASHES = [
    {"path": "README.md", "sha256": "bd30762ecd358ff16f2989166727c5dba5de345d92fcf8ca92398d51978e46b4"}
]
VEIL_HASHES = [
    {"path": "slop/crates/veil/README.md", "sha256": "4e40ce525b683fb636a18589509a6d54f3aa8d8d47b488bedb791daa1c3073c8"},
    {"path": "slop/crates/veil/src/zk/stacked_pcs/mod.rs", "sha256": "4723733d119b008f0f67618c0196b63ce2e544adf6030df45a260e4000ec53e8"},
]
RETIRED_PATHS = [
    "crates/flock-prover/benches/keccak_proof.rs",
    "crates/flock-prover/benches/keccak3_proof.rs",
    "crates/flock-prover/src/r1cs_hashes/keccak.rs",
    "crates/flock-prover/src/r1cs_hashes/keccak3.rs",
]


def checkout_historical(workspace: Path) -> Path:
    root = checkout_exact(FLOCK_REPOSITORY, FLOCK_KECCAK_PARENT, workspace / "sources" / "flock-c2d0")
    verify_hashes(root, HISTORICAL_HASHES)
    return root


def source_check(workspace: Path, output: Path) -> None:
    historical = checkout_historical(workspace)
    release = checkout_exact(FLOCK_REPOSITORY, FLOCK_RELEASE_COMMIT, workspace / "sources" / "flock-43f0")
    removal = checkout_exact(FLOCK_REPOSITORY, FLOCK_KECCAK_REMOVAL, workspace / "sources" / "flock-0f0d")
    veil = checkout_exact(VEIL_REPOSITORY, VEIL_COMMIT, workspace / "sources" / "sp1-veil-6d7e")
    require_contains(
        historical / "crates" / "flock-prover" / "benches" / "keccak3_proof.rs",
        ["KECCAK3_KS", "bench_3wide_report(k, 3)"],
    )
    require_contains(
        historical / "crates" / "flock-prover" / "src" / "r1cs_hashes" / "keccak3.rs",
        ["n_keccaks.div_ceil(N_SUB)", "n.next_power_of_two()", "padding the final", "all-zero input state"],
    )
    require_contains(
        historical / "crates" / "flock-core" / "src" / "pcs" / "ligerito.rs",
        [
            "profile_configs!(22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35)",
            "no security config registered for (m={m}, profile={})",
        ],
    )
    require_absent(
        historical,
        ["crates/flock-core/configs/ligerito/m21_fast.toml"],
    )
    verify_hashes(release, RELEASE_HASHES)
    require_contains(release / "README.md", ["R1CS-over-GF(2)", "Ligerito", "binary field"])
    verify_hashes(removal, REMOVAL_HASHES)
    require_absent(removal, RETIRED_PATHS)
    evm_paths = [
        path
        for path in tracked_files(removal)
        if Path(path).suffix.lower() in {".sol", ".yul"}
        or "evm" in {part.lower() for part in Path(path).parts}
    ]
    if evm_paths:
        raise ReproductionError(f"EVM source gate changed; inspect paths: {evm_paths}")
    verify_hashes(veil, VEIL_HASHES)
    require_contains(
        veil / "slop" / "crates" / "veil" / "README.md",
        ["experimental, proof-of-concept code", "has not been audited"],
    )
    require_contains(
        veil / "slop" / "crates" / "veil" / "src" / "zk" / "stacked_pcs" / "mod.rs",
        ["KoalaBearDegree4Duplex", "ZkStackedPcsProof", "ZkStackedPcsVerifier"],
    )

    landscape = json.loads((RESEARCH / "backends" / "landscape" / "sources.json").read_text(encoding="utf-8"))
    paper_record = next(record for record in landscape["sources"] if record["id"] == "S22")
    if "not zero-knowledge" not in paper_record["quotation"]:
        raise ReproductionError("frozen Flock paper record no longer states the non-ZK limitation")

    write_json(
        output / "result.json",
        {
            "schema_version": 1,
            "candidate_id": "C70",
            "run_type": "source_check",
            "evidence_origin": "LOCAL_SOURCE_CHECK_OF_PINNED_UPSTREAM",
            "pqtc_classification": "NOT_PQTC",
            "gate_status": {"flock": "STOP", "veil": "DEFERRED"},
            "pins": {
                "flock_release": FLOCK_RELEASE_COMMIT,
                "flock_keccak_parent": FLOCK_KECCAK_PARENT,
                "flock_keccak_removal": FLOCK_KECCAK_REMOVAL,
                "veil": VEIL_COMMIT,
            },
            "keccak_current": False,
            "zero_knowledge": False,
            "evm_verifier": False,
            "evm_paths": evm_paths,
            "historical_batch_44_reproduction": {
                "disposition": "UNEXECUTABLE_AT_PIN",
                "expected_failure": "MISSING_LIGERITO_M21_FAST_SECURITY_CONFIG",
                "published_measurement": False,
            },
            "batch_capacity": {
                "requested_permutations": 44,
                "three_wide_blocks": 15,
                "rounded_slots": 16,
                "capacity_permutations": 48,
                "dummy_zero_permutations": 4,
                "evidence_label": "UPSTREAM_BASELINE_NOT_PQTC",
                "derivation": "ceil(44/3)=15 blocks; next power of two is 16; 16*3=48 slots; 48-44=4 valid all-zero permutations",
            },
            "veil_adapter": "KOALABEAR_DEGREE4_STACKED_PCS_NOT_FLOCK_BINARY_FIELD_LIGERITO",
            "verified_files": {
                "historical": verify_hashes(historical, HISTORICAL_HASHES),
                "release": verify_hashes(release, RELEASE_HASHES),
                "removal": verify_hashes(removal, REMOVAL_HASHES),
                "veil": verify_hashes(veil, VEIL_HASHES),
            },
        },
    )


def flock_benchmark(workspace: Path, output: Path) -> None:
    root = checkout_historical(workspace)
    run_recorded(
        ["cargo", "bench", "--bench", "keccak3_proof"],
        root,
        output,
        {
            "schema_version": 1,
            "candidate_id": "C70",
            "run_type": "historical_flock_keccak3_batch_44",
            "evidence_origin": "LOCAL_REPRODUCTION_OF_PINNED_UPSTREAM",
            "pqtc_classification": "UPSTREAM_BASELINE_NOT_PQTC",
            "gate_status": "STOP",
            "reproduction_disposition": "UNEXECUTABLE_AT_PIN",
            "expected_failure": "MISSING_LIGERITO_M21_FAST_SECURITY_CONFIG",
            "pin": FLOCK_KECCAK_PARENT,
            "zero_knowledge": False,
            "evm_verifier": False,
            "requested_permutations": 44,
            "capacity_permutations": 48,
            "dummy_zero_permutations": 4,
            "harness_trial_selection_if_executable": "BEST_OF_3_UPSTREAM_HARNESS",
        },
        display_command="KECCAK3_KS=44 cargo bench --bench keccak3_proof",
        extra_env={"KECCAK3_KS": "44"},
    )


def veil_poc(workspace: Path, output: Path, example: str) -> None:
    root = checkout_exact(VEIL_REPOSITORY, VEIL_COMMIT, workspace / "sources" / "sp1-veil-6d7e")
    verify_hashes(root, VEIL_HASHES)
    run_recorded(
        ["cargo", "run", "--release", "-p", "slop-veil", "--example", example],
        root,
        output,
        {
            "schema_version": 1,
            "candidate_id": "C70",
            "run_type": f"veil_poc_{example}",
            "evidence_origin": "LOCAL_REPRODUCTION_OF_PINNED_UPSTREAM",
            "pqtc_classification": "EXPERIMENTAL_UPSTREAM_POC_NOT_PQTC",
            "gate_status": "DEFERRED",
            "pin": VEIL_COMMIT,
            "adapter": "KOALABEAR_DEGREE4_STACKED_PCS_NOT_FLOCK",
            "custom_integration": False,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["source-check", "flock-benchmark", "veil-poc"])
    parser.add_argument("--example", choices=["root", "mle_eval", "zerocheck"], default="root")
    parser.add_argument("--workspace", type=Path, default=Path(tempfile.gettempdir()) / "pqtornado-emerging")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    suffix = args.example if args.action == "veil-poc" else args.action
    output = args.output or args.workspace / "results" / "C70" / suffix
    try:
        if args.action == "source-check":
            source_check(args.workspace, output)
        elif args.action == "flock-benchmark":
            flock_benchmark(args.workspace, output)
        else:
            veil_poc(args.workspace, output, args.example)
    except ReproductionError as error:
        print(f"C70 reproduction failed: {error}", file=sys.stderr)
        return 1
    print(output / "result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
