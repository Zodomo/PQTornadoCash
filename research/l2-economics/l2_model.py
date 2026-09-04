#!/usr/bin/env python3
"""Deterministic byte, admission, gas-floor, and fee-projection primitives for SP-71."""

from __future__ import annotations

import hashlib
import hmac
from functools import lru_cache
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "research" / "harness" / "report-generator"))
from keccak import keccak256  # type: ignore  # repository-pinned helper

SECP256K1_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
SECP256K1_G = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)
# Anvil/Hardhat account 0: deliberately public and never suitable for custody or production.
RESEARCH_PRIVATE_KEY = 0xAC0974BEC39A17E36BA4A6B4D238FF944BACB478CBED5EFCAE784D7BF4F2FF80
RESEARCH_TO = bytes.fromhex("1111111111111111111111111111111111111111")
NONCE = 7
VALUE_WEI = 0
MAX_PRIORITY_FEE_PER_GAS = 1_000_000_000
MAX_FEE_PER_GAS = 30_000_000_000
PAYLOAD_KIB = (80, 90, 110, 116, 120, 128, 160, 210)
FAMILIES = ("seeded-incompressible", "repeated")
NETWORKS: dict[str, dict[str, int]] = {
    "op-mainnet": {"chain_id": 10, "signed_size_limit": 128 * 1024, "tx_gas_limit": 1 << 24, "block_gas_limit": 40_000_000},
    "arbitrum-one": {"chain_id": 42161, "signed_size_limit": 95_000, "tx_gas_limit": 32_000_000, "block_gas_limit": 32_000_000},
    "scroll-mainnet": {"chain_id": 534352, "signed_size_limit": 116_736, "tx_gas_limit": 10_000_000, "block_gas_limit": 10_000_000},
}


def rlp(value: int | bytes | list[Any]) -> bytes:
    if isinstance(value, int):
        if value < 0:
            raise ValueError("RLP integers must be non-negative")
        return rlp(b"" if value == 0 else value.to_bytes((value.bit_length() + 7) // 8, "big"))
    if isinstance(value, list):
        payload = b"".join(rlp(item) for item in value)
        return _rlp_prefix(len(payload), 0xC0, 0xF7) + payload
    if len(value) == 1 and value[0] < 0x80:
        return value
    return _rlp_prefix(len(value), 0x80, 0xB7) + value


def _rlp_prefix(length: int, short_base: int, long_base: int) -> bytes:
    if length <= 55:
        return bytes((short_base + length,))
    encoded = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes((long_base + len(encoded),)) + encoded


def _point_add(p1: tuple[int, int] | None, p2: tuple[int, int] | None) -> tuple[int, int] | None:
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 != y2 or y1 == 0):
        return None
    if p1 == p2:
        slope = (3 * x1 * x1) * pow(2 * y1, -1, SECP256K1_P)
    else:
        slope = (y2 - y1) * pow(x2 - x1, -1, SECP256K1_P)
    slope %= SECP256K1_P
    x3 = (slope * slope - x1 - x2) % SECP256K1_P
    return x3, (slope * (x1 - x3) - y1) % SECP256K1_P


def _point_mul(scalar: int, point: tuple[int, int] = SECP256K1_G) -> tuple[int, int] | None:
    result = None
    addend: tuple[int, int] | None = point
    while scalar:
        if scalar & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        scalar >>= 1
    return result


def research_address() -> str:
    public = _point_mul(RESEARCH_PRIVATE_KEY)
    assert public is not None
    x, y = public
    return "0x" + keccak256(x.to_bytes(32, "big") + y.to_bytes(32, "big"))[-20:].hex()


def _rfc6979(message_hash: bytes, private_key: int) -> int:
    key = private_key.to_bytes(32, "big")
    v = b"\x01" * 32
    k = b"\x00" * 32
    k = hmac.new(k, v + b"\x00" + key + message_hash, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    k = hmac.new(k, v + b"\x01" + key + message_hash, hashlib.sha256).digest()
    v = hmac.new(k, v, hashlib.sha256).digest()
    while True:
        v = hmac.new(k, v, hashlib.sha256).digest()
        candidate = int.from_bytes(v, "big")
        if 1 <= candidate < SECP256K1_N:
            return candidate
        k = hmac.new(k, v + b"\x00", hashlib.sha256).digest()
        v = hmac.new(k, v, hashlib.sha256).digest()


def sign_hash(message_hash: bytes) -> tuple[int, int, int]:
    z = int.from_bytes(message_hash, "big")
    nonce = _rfc6979(message_hash, RESEARCH_PRIVATE_KEY)
    point = _point_mul(nonce)
    assert point is not None
    r = point[0] % SECP256K1_N
    s = (pow(nonce, -1, SECP256K1_N) * (z + r * RESEARCH_PRIVATE_KEY)) % SECP256K1_N
    parity = point[1] & 1
    if s > SECP256K1_N // 2:
        s = SECP256K1_N - s
        parity ^= 1
    return parity, r, s


def payload(family: str, size: int) -> bytes:
    if family == "seeded-incompressible":
        return hashlib.shake_256(f"SP-71|{family}|{size}|2026-09-04".encode()).digest(size)
    if family == "repeated":
        pattern = b"PQT-SP71-REPEATED-WITNESS|"
        return (pattern * ((size + len(pattern) - 1) // len(pattern)))[:size]
    raise ValueError(f"unknown payload family: {family}")


def signed_eip1559(chain_id: int, gas_limit: int, data: bytes) -> bytes:
    unsigned: list[Any] = [
        chain_id,
        NONCE,
        MAX_PRIORITY_FEE_PER_GAS,
        MAX_FEE_PER_GAS,
        gas_limit,
        RESEARCH_TO,
        VALUE_WEI,
        data,
        [],
    ]
    digest = keccak256(b"\x02" + rlp(unsigned))
    parity, r, s = sign_hash(digest)
    return b"\x02" + rlp(unsigned + [parity, r, s])


def byte_gas(data: bytes) -> dict[str, int]:
    zero = data.count(0)
    nonzero = len(data) - zero
    tokens = zero + 4 * nonzero
    regular_intrinsic = 21_000 + 4 * zero + 16 * nonzero
    floor = 21_000 + 10 * tokens
    return {
        "calldata_zero_bytes": zero,
        "calldata_nonzero_bytes": nonzero,
        "eip7623_tokens": tokens,
        "regular_intrinsic_gas": regular_intrinsic,
        "eip7623_floor_gas": floor,
        "no_op_calldata_gas": max(regular_intrinsic, floor),
    }


def _read_u32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], "little")


def _fastlz_hash(value: int) -> int:
    return ((value * 2654435769) >> 19) & 8191


def _literal_encoded_size(run: int) -> int:
    return run + (run + 31) // 32


def _match_encoded_size(length: int) -> int:
    size = 0
    while length > 262:
        size += 3
        length -= 262
    return size + (2 if length < 7 else 3)
def _match2_encoded_size(length: int, distance: int) -> int:
    encoded_distance = distance - 1
    if encoded_distance < 8191:
        return 2 if length < 7 else 3 + (length - 7) // 255
    return 4 if length < 7 else 5 + (length - 7) // 255




@lru_cache(maxsize=64)
def fastlz_compressed_size(data: bytes) -> int:
    """Exact size from pinned fastlz_compress, including its 64 KiB level switch."""
    length = len(data)
    if length < 4:
        return _literal_encoded_size(length)
    level2 = length >= 65_536
    table = [0] * 8192
    ip = 2
    anchor = 0
    ip_bound = length - 4
    ip_limit = length - 13
    output_size = 0
    while ip < ip_limit:
        while True:
            sequence = _read_u32(data, ip) & 0xFFFFFF
            slot = _fastlz_hash(sequence)
            reference = table[slot]
            table[slot] = ip
            distance = ip - reference
            distance_limit = 73_725 if level2 else 8_192
            comparison = (_read_u32(data, reference) & 0xFFFFFF) if distance < distance_limit else 0x1000000
            if ip >= ip_limit:
                break
            ip += 1
            if sequence == comparison:
                break
        if ip >= ip_limit:
            break
        ip -= 1
        if level2 and distance >= 8191 and (data[reference + 3] != data[ip + 3] or data[reference + 4] != data[ip + 4]):
            ip += 1
            continue
        if ip > anchor:
            output_size += _literal_encoded_size(ip - anchor)
        p = reference + 3
        q = ip + 3
        if data[p:p + 4] == data[q:q + 4]:
            p += 4
            q += 4
        while q < ip_bound:
            different = data[p] != data[q]
            p += 1
            q += 1
            if different:
                break
        match_length = p - (reference + 3)
        output_size += _match2_encoded_size(match_length, distance) if level2 else _match_encoded_size(match_length)
        ip += match_length
        sequence = _read_u32(data, ip)
        table[_fastlz_hash(sequence & 0xFFFFFF)] = ip
        ip += 1
        sequence >>= 8
        table[_fastlz_hash(sequence)] = ip
        ip += 1
        anchor = ip
    return output_size + _literal_encoded_size(length - anchor)


def op_projection(tx: bytes, no_op_gas: int, scenario: dict[str, int]) -> dict[str, int | str]:
    fastlz_size = fastlz_compressed_size(tx)
    estimated_size_scaled = max(100_000_000, -42_585_600 + 836_500 * fastlz_size)
    fee_scaled = 16 * scenario["op_l1_base_fee_scalar"] * scenario["l1_base_fee_wei"] + scenario["op_l1_blob_fee_scalar"] * scenario["l1_blob_base_fee_wei"]
    l1_fee = estimated_size_scaled * fee_scaled // 1_000_000_000_000
    da_usage = max(100, (-42_585_600 + 836_500 * fastlz_size) // 1_000_000)
    da_footprint = da_usage * scenario["op_da_footprint_gas_scalar"]
    execution_fee = no_op_gas * (scenario["l2_base_fee_wei"] + scenario["priority_fee_wei"])
    operator_fee = no_op_gas * scenario["op_operator_fee_scalar"] * 100 + scenario["op_operator_fee_constant_wei"]
    return {
        "estimator_status": "EVALUATED_PINNED_FASTLZ",
        "fastlz_size_bytes": fastlz_size,
        "op_estimated_size_scaled": estimated_size_scaled,
        "op_da_footprint_gas": da_footprint,
        "execution_fee_wei": execution_fee,
        "l1_data_fee_wei": l1_fee,
        "operator_fee_wei": operator_fee,
        "total_fee_wei": execution_fee + l1_fee + operator_fee,
    }


def unavailable_projection(network: str, no_op_gas: int, scenario: dict[str, int]) -> dict[str, int | str | None]:
    reason = {
        "arbitrum-one": "NOT_EVALUATED_MISSING_PINNED_NITRO_BROTLI_LEVEL_1_EXECUTABLE",
        "scroll-mainnet": "NOT_EVALUATED_MISSING_PINNED_SCROLL_DA_CODEC_V8_ZSTD_EXECUTABLE",
    }[network]
    return {
        "estimator_status": reason,
        "execution_fee_wei": no_op_gas * (scenario["l2_base_fee_wei"] + scenario["priority_fee_wei"]),
        "l1_data_fee_wei": None,
        "operator_fee_wei": None,
        "total_fee_wei": None,
    }
