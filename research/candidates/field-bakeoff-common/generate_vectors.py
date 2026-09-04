#!/usr/bin/env python3
"""Generate SP-40 arithmetic vectors. This script makes no performance claims."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SEED = 0x535034304649454C
MIX = 0x9E3779B97F4A7C15
MASK64 = (1 << 64) - 1
SPECS = {
    "F0": {"p": 2013265921, "d": 4, "shape": "binomial", "w": 11, "baseBytes": 4},
    "F1": {"p": 2130706433, "d": 4, "shape": "binomial", "w": 3, "baseBytes": 4},
    "F2": {"p": 2130706433, "d": 5, "shape": "quintic-trinomial", "w": None, "baseBytes": 4},
    "F3": {"p": 18446744069414584321, "d": 2, "shape": "binomial", "w": 7, "baseBytes": 8},
    "F4": {"p": 2147483647, "d": 4, "shape": "qm31", "w": None, "baseBytes": 4},
    "F5": {"p": 21888242871839275222246405745257275088548364400416034343698204186575808495617, "d": 1, "shape": "base", "w": None, "baseBytes": 32},
}


def base(spec: dict, index: int) -> int:
    x = (SEED + ((index + 1) * MIX)) & MASK64
    return ((x ^ (x >> 29) ^ ((x << 17) & MASK64)) | 1) % spec["p"]


def ext(spec: dict, offset: int) -> list[int]:
    return [base(spec, offset + i) for i in range(spec["d"])]


def add(spec: dict, a: list[int], b: list[int]) -> list[int]:
    p = spec["p"]
    return [(x + y) % p for x, y in zip(a, b, strict=True)]


def sub(spec: dict, a: list[int], b: list[int]) -> list[int]:
    p = spec["p"]
    return [(x - y) % p for x, y in zip(a, b, strict=True)]


def cmul(p: int, a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    return ((a[0] * b[0] - a[1] * b[1]) % p, (a[0] * b[1] + a[1] * b[0]) % p)


def mul(spec: dict, a: list[int], b: list[int]) -> list[int]:
    p, d, shape = spec["p"], spec["d"], spec["shape"]
    if shape == "base":
        return [(a[0] * b[0]) % p]
    if shape == "qm31":
        ab = cmul(p, (a[0], a[1]), (b[0], b[1]))
        cd = cmul(p, (a[2], a[3]), (b[2], b[3]))
        cross1 = cmul(p, (a[0], a[1]), (b[2], b[3]))
        cross2 = cmul(p, (a[2], a[3]), (b[0], b[1]))
        return [
            (ab[0] + 2 * cd[0] - cd[1]) % p,
            (ab[1] + cd[0] + 2 * cd[1]) % p,
            (cross1[0] + cross2[0]) % p,
            (cross1[1] + cross2[1]) % p,
        ]
    conv = [0] * (2 * d - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            conv[i + j] = (conv[i + j] + x * y) % p
    if shape == "binomial":
        for k in range(2 * d - 2, d - 1, -1):
            conv[k - d] = (conv[k - d] + conv[k] * spec["w"]) % p
    else:
        for k in range(8, 4, -1):
            conv[k - 5] = (conv[k - 5] + conv[k]) % p
            conv[k - 3] = (conv[k - 3] - conv[k]) % p
    return conv[:d]


def scale(spec: dict, a: list[int], b: int) -> list[int]:
    return [(x * b) % spec["p"] for x in a]


def power(spec: dict, a: list[int], exponent: int) -> list[int]:
    result = [1] + [0] * (spec["d"] - 1)
    while exponent:
        if exponent & 1:
            result = mul(spec, result, a)
        exponent >>= 1
        if exponent:
            a = mul(spec, a, a)
    return result


def inverse(spec: dict, a: list[int]) -> list[int]:
    if not any(a):
        raise ZeroDivisionError
    return power(spec, a, spec["p"] ** spec["d"] - 2)


def dot(spec: dict, n: int) -> list[int]:
    acc = [0] * spec["d"]
    for i in range(n):
        acc = add(spec, acc, scale(spec, ext(spec, 100 + i * spec["d"]), base(spec, 500 + i)))
    return acc


def batch_checksum(spec: dict, n: int, extension: bool) -> list[int]:
    acc = [0] * spec["d"]
    for i in range(n):
        value = ext(spec, 900 + i * spec["d"]) if extension else [base(spec, 700 + i)]
        inv = inverse(spec, value) if extension else [pow(value[0], spec["p"] - 2, spec["p"])]
        if extension:
            acc = add(spec, acc, inv)
        else:
            acc[0] = (acc[0] + inv[0]) % spec["p"]
    return acc


def polynomial(spec: dict) -> list[int]:
    point = ext(spec, 1800)
    acc = [0] * spec["d"]
    for i in range(63, -1, -1):
        acc = add(spec, mul(spec, acc, point), ext(spec, 1200 + i * spec["d"]))
    return acc


def fold(spec: dict) -> list[int]:
    low, high, beta = ext(spec, 2000), ext(spec, 2100), ext(spec, 2200)
    x = base(spec, 2300)
    inv_two = pow(2, spec["p"] - 2, spec["p"])
    inv_two_x = pow((2 * x) % spec["p"], spec["p"] - 2, spec["p"])
    return add(spec, scale(spec, add(spec, low, high), inv_two), mul(spec, beta, scale(spec, sub(spec, low, high), inv_two_x)))


def vector(candidate: str, spec: dict) -> dict:
    p, d = spec["p"], spec["d"]
    a, b = base(spec, 1), base(spec, 2)
    ea, eb = ext(spec, 10), ext(spec, 30)
    raw_a = a.to_bytes(spec["baseBytes"], "big").hex()
    abi_a = a.to_bytes(32, "big").hex()
    sample = [base(spec, 3000 + i) for i in range(4096)]
    return {
        "schemaVersion": "sp40-deterministic-v1",
        "candidateId": candidate,
        "generator": {"seed": f"0x{SEED:016x}", "mixer": "wrapping-u64: ((seed+(i+1)*0x9e3779b97f4a7c15) xor >>29 xor <<17) or 1"},
        "field": {"modulus": str(p), "extensionDegree": d, "shape": spec["shape"], "nonresidue": spec["w"]},
        "base": {"a": str(a), "b": str(b), "add": str((a+b)%p), "sub": str((a-b)%p), "mul": str((a*b)%p), "square": str((a*a)%p), "inverse": str(pow(a,p-2,p)), "power65537": str(pow(a,65537,p))},
        "extension": {"a": list(map(str,ea)), "b": list(map(str,eb)), "add": list(map(str,add(spec,ea,eb))), "sub": list(map(str,sub(spec,ea,eb))), "mul": list(map(str,mul(spec,ea,eb))), "square": list(map(str,mul(spec,ea,ea))), "inverse": list(map(str,inverse(spec,ea))), "power65537": list(map(str,power(spec,ea,65537))), "mulBase": list(map(str,scale(spec,ea,a)))},
        "dotProducts": {str(n): list(map(str,dot(spec,n))) for n in (32,64,128,256)},
        "batchInverseChecksums": {str(n): {"base": list(map(str,batch_checksum(spec,n,False))), "extension": list(map(str,batch_checksum(spec,n,True)))} for n in (16,32,64)},
        "polynomialEvaluation64": list(map(str,polynomial(spec))),
        "binaryFold": list(map(str,fold(spec))),
        "distribution": {"sampleCount": len(sample), "zeroCount": sample.count(0), "nonzeroCount": len(sample)-sample.count(0)},
        "encoding": {"canonicalBaseBytes": spec["baseBytes"], "canonicalExtensionBytes": spec["baseBytes"]*d, "rawBigEndianA": raw_a, "abiWordA": abi_a, "abiExtensionBytes": 32*d},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    all_vectors = {}
    for candidate, spec in SPECS.items():
        data = vector(candidate, spec)
        all_vectors[candidate] = data
        path = args.root / candidate / "vectors.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n")
    common = args.root / "field-bakeoff-common" / "vectors"
    common.mkdir(parents=True, exist_ok=True)
    (common / "all.json").write_text(json.dumps(all_vectors, indent=2) + "\n")


if __name__ == "__main__":
    main()
