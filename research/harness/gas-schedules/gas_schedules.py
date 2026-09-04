#!/usr/bin/env python3
"""Canonical calldata-floor gas scenarios for benchmark records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_TX_GAS = 21_000
STANDARD_TOKEN_COST = 4
CREATION_GAS = 32_000
INITCODE_WORD_COST = 2
DEFAULT_TX_CAP = 16_777_216

SCENARIOS = (
    ("ACTIVE_EIP7623", "weighted_tokens", 10),
    ("SCENARIO_EIP7976_64_PER_BYTE", "bytes", 64),
    ("SCENARIO_EIP8311_96_PER_BYTE", "bytes", 96),
)


class GasScheduleError(ValueError):
    """An invalid gas-schedule input."""


def _nonnegative(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GasScheduleError(f"{name} must be a nonnegative integer")
    return value


def byte_counts(data: bytes) -> tuple[int, int]:
    zero = data.count(0)
    return zero, len(data) - zero


def calculate_scenarios(
    zero_bytes: int,
    nonzero_bytes: int,
    execution_gas: int,
    *,
    is_contract_creation: bool = False,
    tx_cap: int = DEFAULT_TX_CAP,
) -> dict[str, Any]:
    """Return EIP-7623, EIP-7976 and EIP-8311 transaction gas models.

    ``execution_gas`` is EVM execution gas after refunds. For contract creation,
    EIP-3860 word metering and the 32,000 creation charge are included only in
    the standard branch of the transaction-wide maximum, as specified by
    EIP-7623.
    """
    zero_bytes = _nonnegative("zero_bytes", zero_bytes)
    nonzero_bytes = _nonnegative("nonzero_bytes", nonzero_bytes)
    execution_gas = _nonnegative("execution_gas", execution_gas)
    tx_cap = _nonnegative("tx_cap", tx_cap)
    if not isinstance(is_contract_creation, bool):
        raise GasScheduleError("is_contract_creation must be boolean")

    calldata_bytes = zero_bytes + nonzero_bytes
    calldata_tokens = zero_bytes + 4 * nonzero_bytes
    initcode_words = (calldata_bytes + 31) // 32 if is_contract_creation else 0
    creation_intrinsic = (
        CREATION_GAS + INITCODE_WORD_COST * initcode_words
        if is_contract_creation
        else 0
    )
    standard_calldata_gas = STANDARD_TOKEN_COST * calldata_tokens
    standard_intrinsic_gas = (
        BASE_TX_GAS + standard_calldata_gas + creation_intrinsic
    )
    standard_total_gas = standard_intrinsic_gas + execution_gas

    scenarios: list[dict[str, Any]] = []
    for name, basis, rate in SCENARIOS:
        floor_data_gas = (
            rate * calldata_tokens if basis == "weighted_tokens" else rate * calldata_bytes
        )
        floor_gas = BASE_TX_GAS + floor_data_gas
        total_gas = max(standard_total_gas, floor_gas)
        scenarios.append(
            {
                "name": name,
                "floor_gas": floor_gas,
                "total_gas": total_gas,
                "tx_cap_margin": tx_cap - total_gas,
                "floor_is_binding": floor_gas > standard_total_gas,
            }
        )

    return {
        "zero_bytes": zero_bytes,
        "nonzero_bytes": nonzero_bytes,
        "calldata_bytes": calldata_bytes,
        "calldata_tokens": calldata_tokens,
        "execution_gas": execution_gas,
        "is_contract_creation": is_contract_creation,
        "initcode_words": initcode_words,
        "creation_intrinsic_gas": creation_intrinsic,
        "standard_calldata_gas": standard_calldata_gas,
        "standard_intrinsic_gas": standard_intrinsic_gas,
        "standard_total_gas": standard_total_gas,
        "tx_cap": tx_cap,
        "gas_scenarios": scenarios,
    }


class _MachineParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(json.dumps({"ok": False, "error": {"code": "INVALID_ARGUMENTS", "message": message}}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)


def _parser() -> argparse.ArgumentParser:
    parser = _MachineParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--calldata", type=Path, help="binary calldata or initcode")
    source.add_argument("--calldata-hex", help="hex calldata, with optional 0x prefix")
    source.add_argument("--byte-counts", action="store_true", help="use --zero-bytes/--nonzero-bytes")
    parser.add_argument("--zero-bytes", type=int)
    parser.add_argument("--nonzero-bytes", type=int)
    parser.add_argument("--execution-gas", type=int, required=True)
    parser.add_argument("--contract-creation", action="store_true")
    parser.add_argument("--tx-cap", type=int, default=DEFAULT_TX_CAP)
    return parser


def _error(message: str) -> int:
    print(json.dumps({"ok": False, "error": {"code": "INVALID_GAS_INPUT", "message": message}}, sort_keys=True), file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.calldata is not None:
            zero, nonzero = byte_counts(args.calldata.read_bytes())
        elif args.calldata_hex is not None:
            text = args.calldata_hex.removeprefix("0x")
            try:
                data = bytes.fromhex(text)
            except ValueError as exc:
                raise GasScheduleError(f"invalid calldata hex: {exc}") from exc
            zero, nonzero = byte_counts(data)
        else:
            if args.zero_bytes is None or args.nonzero_bytes is None:
                raise GasScheduleError("--byte-counts requires --zero-bytes and --nonzero-bytes")
            zero, nonzero = args.zero_bytes, args.nonzero_bytes
        result = calculate_scenarios(
            zero,
            nonzero,
            args.execution_gas,
            is_contract_creation=args.contract_creation,
            tx_cap=args.tx_cap,
        )
    except (GasScheduleError, OSError) as exc:
        return _error(str(exc))
    print(json.dumps({"ok": True, "result": result}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
