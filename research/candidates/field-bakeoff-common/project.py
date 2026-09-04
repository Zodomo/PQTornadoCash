#!/usr/bin/env python3
"""Project encoding floors and optional measured-kernel relation costs; never a proof estimate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

WIDTHS = {
    "F0": (4, 16),
    "F1": (4, 16),
    "F2": (4, 20),
    "F3": (8, 16),
    "F4": (4, 16),
    "F5": (32, 32),
}


def floor(rows: int, columns: int, width: int, zero_gas: int, nonzero_gas: int) -> dict:
    size = rows * columns * width
    return {
        "bytes": size,
        "allZeroCalldataGasFloor": size * zero_gas,
        "allNonzeroCalldataGasCeiling": size * nonzero_gas,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry", type=Path, default=Path(__file__).with_name("geometry-input.json"))
    parser.add_argument("--geometry-key", default="frozenV03")
    parser.add_argument("--rows", type=int, help="override rows with the selected SP-20 geometry")
    parser.add_argument("--columns", type=int, help="override columns with the selected SP-20 geometry")
    parser.add_argument("--opened-rows", type=int, nargs="+", help="override opened-row scenarios")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "outputs" / "projection-latest.json")
    args = parser.parse_args()
    document = json.loads(args.geometry.read_text())
    geometry = document[args.geometry_key] if args.geometry_key in document else document
    rows = int(args.rows if args.rows is not None else geometry["rows"])
    columns = int(args.columns if args.columns is not None else geometry["columns"])
    opened = list(map(int, args.opened_rows if args.opened_rows is not None else geometry["openedRowScenarios"]))
    schedule = document.get("calldataSchedule", {"zeroByteGas": 4, "nonzeroByteGas": 16, "abiWordBytes": 32})
    try:
        geometry_source = str(args.geometry.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        geometry_source = str(args.geometry)
    result = {
        "schemaVersion": "sp40-relation-projection-v1",
        "benchmarkOnly": True,
        "completeProofProjection": False,
        "geometrySource": geometry_source,
        "geometryKey": args.geometry_key,
        "geometry": {"rows": rows, "columns": columns, "openedRowScenarios": opened},
        "exclusions": [
            "authentication paths and digests",
            "FRI/PCS openings and commitments",
            "proof envelope and transcript",
            "EVM memory expansion and transaction intrinsic gas",
            "constraint operation counts (not frozen for alternate fields)",
        ],
        "relationArithmeticProjection": {
            "status": "SYMBOLIC_UNTIL_ALTERNATE_FIELD_PORT_IS_COUNTED",
            "formula": "sum(operationCount[op] * measuredUnitCost[candidate][op])",
            "requiredOperationCounts": [
                "base_add", "base_sub", "base_mul", "base_square", "base_inverse", "base_power",
                "extension_add", "extension_sub", "extension_mul", "extension_square",
                "extension_inverse", "extension_power", "extension_mul_base",
                "dot_product_by_length", "batch_inverse_by_length", "polynomial_evaluation", "fold"
            ],
            "reason": "The frozen relation fixes 190 columns and 1186 constraints, not an implementation-independent arithmetic operation count. Reusing BabyBear verifier counts for another field would fabricate a projection."
        },
        "candidates": {},
    }
    for candidate, (base_width, extension_width) in WIDTHS.items():
        entry = {
            "canonicalBaseBytes": base_width,
            "canonicalExtensionBytes": extension_width,
            "fullTraceRawBase": floor(rows, columns, base_width, schedule["zeroByteGas"], schedule["nonzeroByteGas"]),
            "fullTraceAbiBase": {"bytes": rows * columns * schedule["abiWordBytes"]},
            "openedRows": {},
        }
        for count in opened:
            entry["openedRows"][str(count)] = {
                "rawBase": floor(count, columns, base_width, schedule["zeroByteGas"], schedule["nonzeroByteGas"]),
                "rawExtension": floor(count, columns, extension_width, schedule["zeroByteGas"], schedule["nonzeroByteGas"]),
                "abiBaseBytes": count * columns * schedule["abiWordBytes"],
                "abiExtensionCoefficientBytes": count * columns * (extension_width // base_width) * schedule["abiWordBytes"],
            }
        result["candidates"][candidate] = entry
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(args.out)


if __name__ == "__main__":
    main()
