#!/usr/bin/env python3
"""Build and reconcile an exact proof-byte and ABI-calldata ledger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


class LedgerError(ValueError):
    """A byte ledger cannot be reconciled."""


def _section_map(sections: Mapping[str, object]) -> dict[str, int]:
    result: dict[str, int] = {}
    for name, size in sections.items():
        if not isinstance(name, str) or not name:
            raise LedgerError("section names must be nonempty strings")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise LedgerError(f"section {name!r} must have a nonnegative integer size")
        result[name] = size
    if not result:
        raise LedgerError("at least one proof section is required")
    return dict(sorted(result.items()))


def build_ledger(
    raw_proof: bytes,
    abi_calldata: bytes,
    sections: Mapping[str, object],
) -> dict[str, Any]:
    """Count bytes and reject any section or zero/nonzero mismatch."""
    normalized = _section_map(sections)
    raw_size = len(raw_proof)
    abi_size = len(abi_calldata)
    section_total = sum(normalized.values())
    if section_total != raw_size:
        raise LedgerError(
            f"proof sections total {section_total} bytes, raw proof is {raw_size} bytes"
        )
    if abi_size < raw_size:
        raise LedgerError(
            f"ABI calldata ({abi_size} bytes) cannot be shorter than raw proof ({raw_size} bytes)"
        )
    zero = abi_calldata.count(0)
    nonzero = abi_size - zero
    if zero + nonzero != abi_size:
        raise LedgerError("internal zero/nonzero byte count failed to reconcile")

    return {
        "raw_proof_bytes": raw_size,
        "abi_calldata_bytes": abi_size,
        "zero_bytes": zero,
        "nonzero_bytes": nonzero,
        "abi_overhead_bytes": abi_size - raw_size,
        "sections": normalized,
        "section_total_bytes": section_total,
        "reconciliation": {
            "sections_equal_raw_proof": True,
            "zero_plus_nonzero_equals_abi": True,
        },
    }


def load_sections(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LedgerError(f"cannot read sections JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LedgerError("sections JSON must be an object mapping names to byte counts")
    if "sections" in value:
        value = value["sections"]
        if not isinstance(value, dict):
            raise LedgerError("the sections member must be an object")
    return value


class _MachineParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(json.dumps({"ok": False, "error": {"code": "INVALID_ARGUMENTS", "message": message}}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)


def _parser() -> argparse.ArgumentParser:
    parser = _MachineParser(description=__doc__)
    parser.add_argument("--raw-proof", type=Path, required=True)
    parser.add_argument("--abi-calldata", type=Path, required=True)
    parser.add_argument("--sections", type=Path, required=True, help="JSON object of proof section byte counts")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = build_ledger(
            args.raw_proof.read_bytes(),
            args.abi_calldata.read_bytes(),
            load_sections(args.sections),
        )
        text = json.dumps({"ok": True, "result": result}, sort_keys=True, indent=2) + "\n"
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    except (LedgerError, OSError) as exc:
        print(json.dumps({"ok": False, "error": {"code": "LEDGER_RECONCILIATION_FAILED", "message": str(exc)}}, sort_keys=True), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
