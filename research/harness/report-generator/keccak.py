"""Small streaming Ethereum Keccak-256 implementation using only Python."""

from __future__ import annotations

from typing import Iterable

_MASK64 = (1 << 64) - 1
_RATE = 136
_ROTATIONS = (
    0, 1, 62, 28, 27,
    36, 44, 6, 55, 20,
    3, 10, 43, 25, 39,
    41, 45, 15, 21, 8,
    18, 2, 61, 56, 14,
)
_ROUND_CONSTANTS = (
    0x0000000000000001, 0x0000000000008082,
    0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088,
    0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B,
    0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080,
    0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080,
    0x0000000080000001, 0x8000000080008008,
)
_EMPTY_DIGEST = "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def _rol(value: int, shift: int) -> int:
    if shift == 0:
        return value
    return ((value << shift) | (value >> (64 - shift))) & _MASK64


def _permutation(state: list[int]) -> None:
    for rc in _ROUND_CONSTANTS:
        columns = [
            state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20]
            for x in range(5)
        ]
        for x in range(5):
            delta = columns[(x - 1) % 5] ^ _rol(columns[(x + 1) % 5], 1)
            for y in range(5):
                state[x + 5 * y] ^= delta

        moved = [0] * 25
        for x in range(5):
            for y in range(5):
                moved[y + 5 * ((2 * x + 3 * y) % 5)] = _rol(
                    state[x + 5 * y], _ROTATIONS[x + 5 * y]
                )
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] = (
                    moved[x + 5 * y]
                    ^ ((~moved[(x + 1) % 5 + 5 * y]) & moved[(x + 2) % 5 + 5 * y])
                ) & _MASK64
        state[0] ^= rc


def _absorb_block(state: list[int], block: bytes | bytearray) -> None:
    for lane in range(_RATE // 8):
        start = lane * 8
        state[lane] ^= int.from_bytes(block[start:start + 8], "little")
    _permutation(state)


class Keccak256:
    """A hashlib-like streaming Ethereum Keccak-256 hasher."""

    digest_size = 32
    block_size = _RATE
    name = "keccak256"

    def __init__(self, data: bytes = b"") -> None:
        self._state = [0] * 25
        self._pending = bytearray()
        if data:
            self.update(data)

    def update(self, data: bytes | bytearray | memoryview) -> "Keccak256":
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("Keccak256.update() requires a bytes-like object")
        self._pending.extend(data)
        consumed = 0
        while len(self._pending) - consumed >= _RATE:
            _absorb_block(self._state, self._pending[consumed:consumed + _RATE])
            consumed += _RATE
        if consumed:
            del self._pending[:consumed]
        return self

    def copy(self) -> "Keccak256":
        duplicate = Keccak256()
        duplicate._state = self._state.copy()
        duplicate._pending = self._pending.copy()
        return duplicate

    def digest(self) -> bytes:
        state = self._state.copy()
        final = self._pending.copy()
        final.append(0x01)  # Keccak domain separator; SHA3 uses 0x06.
        final.extend(b"\x00" * (_RATE - len(final)))
        final[-1] ^= 0x80
        _absorb_block(state, final)
        return b"".join(lane.to_bytes(8, "little") for lane in state)[: self.digest_size]

    def hexdigest(self) -> str:
        return self.digest().hex()


def keccak256(data: bytes) -> bytes:
    return Keccak256(data).digest()


def hash_chunks(chunks: Iterable[bytes]) -> str:
    hasher = Keccak256()
    for chunk in chunks:
        hasher.update(chunk)
    return hasher.hexdigest()


def self_test() -> None:
    actual = Keccak256().hexdigest()
    if actual != _EMPTY_DIGEST:
        raise RuntimeError(f"Ethereum Keccak-256 self-test failed: {actual}")
