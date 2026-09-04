#!/usr/bin/env python3
"""Unified command line controller for the PQTC research harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_HARNESS = Path(__file__).resolve().parents[1]
for _directory in ("gas-schedules", "proof-ledger", "hardware-detect", "report-generator"):
    sys.path.insert(0, str(_HARNESS / _directory))

from gas_schedules import DEFAULT_TX_CAP, GasScheduleError, byte_counts, calculate_scenarios
from hardware_detect import DetectionError, detect_environment
from keccak import self_test as keccak_self_test
from proof_ledger import LedgerError, build_ledger, load_sections
from report_generator import (
    ReportError,
    generate_manifest,
    generate_summaries,
    repository_root,
    validate_run,
    verify_manifest,
)
from schema_validator import SchemaLoadError


class MachineParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(json.dumps({"ok": False, "error": {"code": "INVALID_ARGUMENTS", "message": message}}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)


def _path(root: Path, supplied: Path) -> Path:
    return supplied if supplied.is_absolute() else root / supplied


def _parser() -> argparse.ArgumentParser:
    parser = MachineParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="repository root (auto-detected by default)")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=MachineParser)

    gas = commands.add_parser("gas", aliases=["gas-schedules"], help="calculate all canonical calldata-floor scenarios")
    gas_source = gas.add_mutually_exclusive_group(required=True)
    gas_source.add_argument("--calldata", type=Path)
    gas_source.add_argument("--calldata-hex")
    gas_source.add_argument("--byte-counts", action="store_true")
    gas.add_argument("--zero-bytes", type=int)
    gas.add_argument("--nonzero-bytes", type=int)
    gas.add_argument("--execution-gas", type=int, required=True)
    gas.add_argument("--contract-creation", action="store_true")
    gas.add_argument("--tx-cap", type=int, default=DEFAULT_TX_CAP)

    ledger = commands.add_parser("ledger", aliases=["proof-ledger"], help="build and reconcile proof and ABI byte counts")
    ledger.add_argument("--raw-proof", type=Path, required=True)
    ledger.add_argument("--abi-calldata", type=Path, required=True)
    ledger.add_argument("--sections", type=Path, required=True)

    detect = commands.add_parser("detect", aliases=["hardware-detect"], help="detect hardware and toolchain versions")
    detect.add_argument("--evm-revision", required=True)
    detect.add_argument("--strict-tools", action="store_true")

    validate = commands.add_parser("validate-run", help="validate a benchmark run against the root schema")
    validate.add_argument("run", type=Path)
    validate.add_argument("--schema", type=Path)

    manifest = commands.add_parser("manifest", help="generate a deterministic evidence manifest")
    manifest.add_argument("inputs", nargs="+", type=Path)
    manifest.add_argument("--output", type=Path, required=True)

    verify = commands.add_parser("verify-manifest", help="verify all evidence manifest files and digests")
    verify.add_argument("manifest", type=Path)

    summary = commands.add_parser("summary", aliases=["report"], help="validate run records and generate deterministic CSV")
    summary.add_argument("inputs", nargs="+", type=Path)
    summary.add_argument("--output", type=Path, required=True)
    summary.add_argument("--candidate-output", type=Path)
    summary.add_argument("--schema", type=Path)

    commands.add_parser("keccak-self-test", help="check the Ethereum Keccak-256 empty-string vector")
    return parser


def _gas(args: argparse.Namespace, root: Path) -> dict[str, Any]:
    if args.calldata is not None:
        zero, nonzero = byte_counts(_path(root, args.calldata).read_bytes())
    elif args.calldata_hex is not None:
        try:
            data = bytes.fromhex(args.calldata_hex.removeprefix("0x"))
        except ValueError as exc:
            raise GasScheduleError(f"invalid calldata hex: {exc}") from exc
        zero, nonzero = byte_counts(data)
    else:
        if args.zero_bytes is None or args.nonzero_bytes is None:
            raise GasScheduleError("--byte-counts requires --zero-bytes and --nonzero-bytes")
        zero, nonzero = args.zero_bytes, args.nonzero_bytes
    return calculate_scenarios(
        zero,
        nonzero,
        args.execution_gas,
        is_contract_creation=args.contract_creation,
        tx_cap=args.tx_cap,
    )


def dispatch(args: argparse.Namespace, root: Path) -> tuple[dict[str, Any], int]:
    if args.command in {"gas", "gas-schedules"}:
        return _gas(args, root), 0
    if args.command in {"ledger", "proof-ledger"}:
        return build_ledger(
            _path(root, args.raw_proof).read_bytes(),
            _path(root, args.abi_calldata).read_bytes(),
            load_sections(_path(root, args.sections)),
        ), 0
    if args.command in {"detect", "hardware-detect"}:
        result = detect_environment(args.evm_revision)
        if args.strict_tools:
            required = {name: reason for name, reason in result["detection"]["unavailable_tools"].items() if name in {"rustc", "solc", "foundry"}}
            if required:
                raise DetectionError("required tools unavailable: " + ", ".join(sorted(required)))
        return result, 0
    if args.command == "validate-run":
        schema = _path(root, args.schema) if args.schema else root / "benchmark-run.schema.json"
        _, errors = validate_run(_path(root, args.run), schema)
        return {"valid": not errors, "errors": errors}, 0 if not errors else 2
    if args.command == "manifest":
        return generate_manifest(args.inputs, args.output, root), 0
    if args.command == "verify-manifest":
        result = verify_manifest(_path(root, args.manifest), root)
        return result, 0 if result["valid"] else 2
    if args.command in {"summary", "report"}:
        schema = _path(root, args.schema) if args.schema else root / "benchmark-run.schema.json"
        return generate_summaries(args.inputs, args.output, args.candidate_output, schema, root), 0
    keccak_self_test()
    return {"ethereum_keccak256_empty": "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"}, 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = args.root.resolve() if args.root else repository_root()
        result, exit_code = dispatch(args, root)
    except (DetectionError, GasScheduleError, LedgerError, ReportError, SchemaLoadError, OSError, UnicodeError) as exc:
        print(json.dumps({"ok": False, "error": {"code": "HARNESS_OPERATION_FAILED", "message": str(exc)}}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({"ok": exit_code == 0, "result": result}, sort_keys=True, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
