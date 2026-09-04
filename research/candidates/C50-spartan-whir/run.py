#!/usr/bin/env python3
"""Exact-pin source checks and upstream reproductions for C50."""

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
    initialize_submodules,
    require_contains,
    run_recorded,
    run_checked,
    run_sequence_recorded,
    tracked_files,
    verify_hashes,
    write_json,
)

NATIVE_REPOSITORY = "https://github.com/ethereum/spartan-whir.git"
NATIVE_COMMIT = "f525cddea38bb605304d3a8e6394dda10ac64b4a"
SOLIDITY_REPOSITORY = "https://github.com/ethereum/sol-spartan-whir.git"
SOLIDITY_COMMIT = "b381a9091568d1a4a52b50d0b27488a767051faf"
EXPORT_REPOSITORY = "https://github.com/alxkzmn/spartan-whir-export.git"
EXPORT_COMMIT = "ec7c24f451f208debf86144d45bb3441e9d85cc4"
DEPENDENCY_CONTROL_REPOSITORY = "https://github.com/privacy-ethereum/sol-whir.git"
DEPENDENCY_CONTROL_COMMIT = "b719b97b5961ac1c1679383b31e55439a26682f9"
FORGE_STD_REPOSITORY = "https://github.com/foundry-rs/forge-std.git"
FORGE_STD_COMMIT = "035de35f5e366c8d6ed142aec4ccb57fe2dd87d4"
SOLADY_REPOSITORY = "https://github.com/Vectorized/solady.git"
SOLADY_COMMIT = "513f581675374706dbe947284d6b12d19ce35a2a"

NATIVE_HASHES = [
    {"path": "README.md", "sha256": "f24b1efa028def2cca4962a646f7aa25c6bc892c9749febad5ead2318d414c49"},
    {"path": "src/poseidon.rs", "sha256": "893ed2475dd9fee42ffe85c271c004f24001e17460bd3168aaff039955ddc2e2"},
    {"path": "examples/end_to_end.rs", "sha256": "472466b4cfdb561ab980ff3df9411aa6de1fe8399f8c5620be75c6b61c7dc952"},
]
SOLIDITY_HASHES = [
    {"path": "README.md", "sha256": "ee810796b973bf64a58ee432333269235e3de545571367e20d1d7d3ca56d6d5f"},
    {"path": "test/FixtureDecode_lir6_ff5_rsv1.t.sol", "sha256": "95481d156a0429c707ac4974a25dccf77c04302abd942dfe0f2bae1990602a39"},
    {"path": ".agents/skills/tx-gas-benchmarking/scripts/run_tx_gas_benchmark.sh", "sha256": "2da79e4aa2d41e8a6b876f0a176baceb6fb5afd8cd19525420b06c0be0ab9ea6"},
]
EXPORT_HASHES = [
    {"path": "README.md", "sha256": "6a082485d5e294782a779be8ac44c774ecb486912230c08fe2ae72c8a5b9c4cf"}
]
DEPENDENCY_CONTROL_HASHES = [
    {"path": ".gitmodules", "sha256": "7f003f2e63268e30c9af3a3e7e06be7eaf672cda69c8cc1b905ecc9131f759c1"}
]
FORGE_STD_HASHES = [
    {"path": "src/Test.sol", "sha256": "242f2494d264bf00515b7bfcb5a3e6cbc3e737d03795105cbf19f68d8b640dd9"},
    {"path": "src/Script.sol", "sha256": "c4de2ae936fa7bb4f4250a3908c6bce7acdc84034156cb252fdc2d9a1c020012"},
    {"path": "src/StdJson.sol", "sha256": "0211b47e93dbeb6a7de6112470a77137038ed73b79b015847f013e49fcd7511f"},
]
SOLADY_HASHES = [
    {"path": "src/utils/LibSort.sol", "sha256": "ff6fa9e5021aeab6c1491e6f9ae123bf4cc20e4813e9f661640741ef6296e446"}
]


def prepare_solidity(workspace: Path) -> tuple[Path, dict[str, object]]:
    root = checkout_exact(
        SOLIDITY_REPOSITORY,
        SOLIDITY_COMMIT,
        workspace / "sources" / "sol-spartan-whir-b381",
    )
    verify_hashes(root, SOLIDITY_HASHES)
    control = checkout_exact(
        DEPENDENCY_CONTROL_REPOSITORY,
        DEPENDENCY_CONTROL_COMMIT,
        workspace / "sources" / "sol-whir-b719-dependency-control",
    )
    verify_hashes(control, DEPENDENCY_CONTROL_HASHES)
    gitlinks = {}
    for relative, expected in {
        "lib/forge-std": FORGE_STD_COMMIT,
        "lib/solady": SOLADY_COMMIT,
    }.items():
        fields = run_checked(["git", "ls-tree", "HEAD", "--", relative], control).split()
        if len(fields) < 4 or fields[0] != "160000" or fields[2] != expected:
            raise ReproductionError(
                f"dependency control gitlink mismatch for {relative}: {fields}"
            )
        gitlinks[relative] = expected

    forge_std = checkout_exact(
        FORGE_STD_REPOSITORY,
        FORGE_STD_COMMIT,
        root / "lib" / "forge-std",
    )
    solady = checkout_exact(
        SOLADY_REPOSITORY,
        SOLADY_COMMIT,
        root / "lib" / "solady",
    )
    evidence = {
        "pin_source": {
            "repository": DEPENDENCY_CONTROL_REPOSITORY.removesuffix(".git"),
            "commit": DEPENDENCY_CONTROL_COMMIT,
            "gitlinks": gitlinks,
        },
        "upstream_root_submodules": initialize_submodules(root),
        "dependencies": {
            "forge_std": {
                "repository": FORGE_STD_REPOSITORY.removesuffix(".git"),
                "commit": FORGE_STD_COMMIT,
                "verified_files": verify_hashes(forge_std, FORGE_STD_HASHES),
                "recursive_submodules": initialize_submodules(forge_std),
            },
            "solady": {
                "repository": SOLADY_REPOSITORY.removesuffix(".git"),
                "commit": SOLADY_COMMIT,
                "verified_files": verify_hashes(solady, SOLADY_HASHES),
                "recursive_submodules": initialize_submodules(solady),
            },
        },
    }
    return root, evidence


def source_check(workspace: Path, output: Path) -> None:
    native = checkout_exact(NATIVE_REPOSITORY, NATIVE_COMMIT, workspace / "sources" / "spartan-whir-f525cd")
    solidity, dependency_evidence = prepare_solidity(workspace)
    exporter = checkout_exact(EXPORT_REPOSITORY, EXPORT_COMMIT, workspace / "sources" / "spartan-whir-export-ec7c")
    checked = {
        "native": verify_hashes(native, NATIVE_HASHES),
        "solidity": verify_hashes(solidity, SOLIDITY_HASHES),
        "exporter": verify_hashes(exporter, EXPORT_HASHES),
    }
    require_contains(
        native / "README.md",
        ["| Full ZK |  Implemented | Implemented |", "PoseidonZkProvingKey", "prove_with_rng"],
    )
    require_contains(
        native / "src" / "poseidon.rs",
        ["pub fn setup(", "pub fn prove(", "pub fn verify("],
    )
    require_contains(
        solidity / "test" / "FixtureDecode_lir6_ff5_rsv1.t.sol",
        ["Spartan placeholder proof", "empty public inputs", "zero witness commitment"],
    )
    require_contains(
        exporter / "README.md",
        ["standalone WHIR Solidity line", "intentionally does not depend", "Placeholder Spartan proof"],
    )
    license_names = {"license", "license.md", "license.txt", "copying", "copying.md", "copying.txt"}
    license_files = {
        "native": [p for p in tracked_files(native) if Path(p).parent == Path(".") and Path(p).name.lower() in license_names],
        "solidity": [p for p in tracked_files(solidity) if Path(p).parent == Path(".") and Path(p).name.lower() in license_names],
    }
    if license_files["native"] or license_files["solidity"]:
        raise ReproductionError(f"license gate changed; inspect explicit files: {license_files}")
    write_json(
        output / "result.json",
        {
            "schema_version": 1,
            "candidate_id": "C50",
            "run_type": "source_check",
            "evidence_origin": "LOCAL_SOURCE_CHECK_OF_PINNED_UPSTREAM",
            "pqtc_classification": "NOT_PQTC_NO_EXACT_RELATION",
            "gate_status": {"native_full_zk_maturity": "PASS", "full_evm_spartan": "DEFERRED"},
            "pins": {
                "native": NATIVE_COMMIT,
                "solidity": SOLIDITY_COMMIT,
                "exporter": EXPORT_COMMIT,
                "dependency_control": DEPENDENCY_CONTROL_COMMIT,
                "forge_std": FORGE_STD_COMMIT,
                "solady": SOLADY_COMMIT,
            },
            "verified_files": checked,
            "solidity_dependencies": dependency_evidence,
            "license_gate": "BLOCKED_FOR_COPY_OR_REDISTRIBUTION",
            "top_level_license_files": license_files,
        },
    )


def fenced_block(readme: str, preceding: str, language: str) -> str:
    marker = preceding + "\n\n```" + language + "\n"
    start = readme.find(marker)
    if start < 0:
        raise ReproductionError(f"cannot locate upstream README block after {preceding!r}")
    start += len(marker)
    end = readme.find("\n```", start)
    if end < 0:
        raise ReproductionError(f"unterminated upstream README block after {preceding!r}")
    return readme[start:end] + "\n"


def native_example(workspace: Path, output: Path) -> None:
    root = checkout_exact(NATIVE_REPOSITORY, NATIVE_COMMIT, workspace / "sources" / "spartan-whir-f525cd")
    verify_hashes(root, NATIVE_HASHES)
    readme = (root / "README.md").read_text(encoding="utf-8")
    (root / "example.circom").write_text(
        fenced_block(readme, "Create `example.circom`:", "circom"), encoding="utf-8"
    )
    (root / "input.json").write_text(
        fenced_block(readme, "Create `input.json`:", "json"), encoding="utf-8"
    )
    commands = [
        ["mkdir", "-p", "build"],
        ["circom", "example.circom", "--prime", "koalabear", "--r1cs", "--c", "-o", "build"],
        ["make", "-C", "build/example_cpp"],
        ["build/example_cpp/example", "input.json", "build/example.wtns"],
        ["cargo", "run", "--release", "--features", "parallel", "--example", "end_to_end", "--", "setup", "build/example.r1cs", "build/proving-key.bin", "build/verifying-key.bin"],
        ["cargo", "run", "--release", "--features", "parallel", "--example", "end_to_end", "--", "prove", "build/proving-key.bin", "build/example.wtns", "build/proof.bin", "build/public-inputs.bin"],
        ["cargo", "run", "--release", "--features", "parallel", "--example", "end_to_end", "--", "verify", "build/verifying-key.bin", "build/public-inputs.bin", "build/proof.bin"],
    ]
    run_sequence_recorded(
        commands,
        root,
        output,
        {
            "schema_version": 1,
            "candidate_id": "C50",
            "run_type": "native_full_zk_end_to_end",
            "evidence_origin": "LOCAL_REPRODUCTION_OF_PINNED_UPSTREAM",
            "pqtc_classification": "NOT_PQTC_NO_EXACT_RELATION",
            "gate_status": "PASS_IMPLEMENTATION_MATURITY_ONLY",
            "pin": NATIVE_COMMIT,
            "license_gate": "BLOCKED_FOR_COPY_OR_REDISTRIBUTION",
            "relation": "UPSTREAM_README_EXAMPLE_NOT_FROZEN_H0",
        },
    )


def solidity_reproduction(workspace: Path, output: Path, gas: bool) -> None:
    root, dependency_evidence = prepare_solidity(workspace)
    if gas:
        argv = [
            "bash",
            ".agents/skills/tx-gas-benchmarking/scripts/run_tx_gas_benchmark.sh",
            "script/WhirBlobNativeTxBenchmark_k22_jb100_ext5_lir4_ff4_rsv3_pow28.s.sol",
        ]
        run_recorded(
            argv,
            root,
            output,
            {
                "schema_version": 1,
                "candidate_id": "C50",
                "run_type": "standalone_solidity_whir_gas",
                "evidence_origin": "LOCAL_REPRODUCTION_OF_PINNED_UPSTREAM",
                "pqtc_classification": "STANDALONE_WHIR_NOT_SPARTAN_NOT_PQTC",
                "gate_status": "DEFERRED_FULL_EVM_SPARTAN",
                "reproduction_disposition": "UNEXECUTABLE_UPSTREAM_HARNESS_AT_PIN",
                "gas_measurement_status": "NOT_EVALUATED",
                "expected_failure": "UNBOUND_TARGET_CONTRACT_ARRAY_AT_LINE_95",
                "pin": SOLIDITY_COMMIT,
                "license_gate": "BLOCKED_FOR_COPY_OR_REDISTRIBUTION",
                "solidity_dependencies": dependency_evidence,
            },
        )
    else:
        run_sequence_recorded(
            [["forge", "build"], ["forge", "test"]],
            root,
            output,
            {
                "schema_version": 1,
                "candidate_id": "C50",
                "run_type": "standalone_solidity_whir",
                "evidence_origin": "LOCAL_REPRODUCTION_OF_PINNED_UPSTREAM",
                "pqtc_classification": "STANDALONE_WHIR_NOT_SPARTAN_NOT_PQTC",
                "reproduction_disposition": "PASS_STANDALONE_WHIR_BUILD_TESTS_ONLY",
                "gate_status": "DEFERRED_FULL_EVM_SPARTAN",
                "pin": SOLIDITY_COMMIT,
                "license_gate": "BLOCKED_FOR_COPY_OR_REDISTRIBUTION",
                "solidity_dependencies": dependency_evidence,
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["source-check", "native", "solidity", "solidity-gas"])
    parser.add_argument("--workspace", type=Path, default=Path(tempfile.gettempdir()) / "pqtornado-emerging")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.workspace / "results" / "C50" / args.action
    try:
        if args.action == "source-check":
            source_check(args.workspace, output)
        elif args.action == "native":
            native_example(args.workspace, output)
        else:
            solidity_reproduction(args.workspace, output, args.action == "solidity-gas")
    except ReproductionError as error:
        print(f"C50 reproduction failed: {error}", file=sys.stderr)
        return 1
    print(output / "result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
