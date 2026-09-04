#!/usr/bin/env python3
"""Deterministic SP-72 state and gas model; not a cryptographic verifier."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256, sha512
from typing import Callable


class Reject(ValueError):
    pass


Digest512 = tuple[bytes, bytes]


def digest(seed: int) -> Digest512:
    return (seed.to_bytes(32, "big"), (seed + 1).to_bytes(32, "big"))


def digest_key(value: Digest512) -> bytes:
    return sha256(b"SP72-DIGEST-KEY" + value[0] + value[1]).digest()


def nullifier_key(value: Digest512) -> bytes:
    return sha256(b"PQTC.SP72.NULLIFIER.KEY.V1" + value[0] + value[1]).digest()


@dataclass(frozen=True)
class Bindings:
    statement: Digest512
    global_data: Digest512
    checkpoint: Digest512
    proof: Digest512
    continuation: Digest512
    root: Digest512

    def encode(self) -> bytes:
        return b"".join(limb for value in (
            self.statement,
            self.global_data,
            self.checkpoint,
            self.proof,
            self.continuation,
            self.root,
        ) for limb in value)

    def validate(self) -> None:
        for value in (
            self.statement,
            self.global_data,
            self.checkpoint,
            self.proof,
            self.continuation,
            self.root,
        ):
            if len(value[0]) != 32 or len(value[1]) != 32 or value == (bytes(32), bytes(32)):
                raise Reject("INVALID_BINDING")


@dataclass(frozen=True)
class Checkpoint:
    created_at: int
    expires_at: int
    split: int
    bindings: Bindings


class ModelVerifier:
    """Binding oracle for state tests only; never evidence of proof-system security."""

    @staticmethod
    def proof(part: str, split: int, key: bytes, bindings: Bindings) -> bytes:
        return sha256(b"SP72-MODEL-" + part.encode() + bytes([split]) + key + bindings.encode()).digest()

    @classmethod
    def verify(cls, part: str, split: int, key: bytes, bindings: Bindings, proof: bytes) -> bool:
        return proof == cls.proof(part, split, key, bindings)


class StateMachine:
    def __init__(self, consumer: str, ttl_blocks: int, split: int):
        if not consumer or ttl_blocks <= 0 or split < 8 or split > 16:
            raise Reject("INVALID_CONFIGURATION")
        self.consumer = consumer
        self.ttl_blocks = ttl_blocks
        self.split = split
        self.checkpoints: dict[bytes, Checkpoint] = {}
        self.root_pins: dict[bytes, int] = {}

    def begin(self, caller: str, now: int, key: bytes, bindings: Bindings, proof_a: bytes) -> int:
        self._consumer(caller)
        bindings.validate()
        current = self.checkpoints.get(key)
        if current is not None and now < current.expires_at:
            if current.bindings != bindings:
                raise Reject("ACTIVE_CHECKPOINT")
            return current.expires_at
        if current is not None:
            self._erase(key)
        if not ModelVerifier.verify("A", self.split, key, bindings, proof_a):
            raise Reject("INVALID_PROOF")
        expires_at = now + self.ttl_blocks
        self.checkpoints[key] = Checkpoint(now, expires_at, self.split, bindings)
        root_key = digest_key(bindings.root)
        self.root_pins[root_key] = self.root_pins.get(root_key, 0) + 1
        return expires_at

    def complete(self, caller: str, now: int, key: bytes, bindings: Bindings, proof_b: bytes) -> None:
        self._consumer(caller)
        current = self.checkpoints.get(key)
        if current is None:
            raise Reject("UNKNOWN_CHECKPOINT")
        if now >= current.expires_at:
            raise Reject("CHECKPOINT_EXPIRED")
        if current.bindings != bindings:
            raise Reject("BINDING_MISMATCH")
        if not ModelVerifier.verify("B", self.split, key, bindings, proof_b):
            raise Reject("INVALID_PROOF")
        self._erase(key)

    def cleanup(self, now: int, key: bytes) -> None:
        current = self.checkpoints.get(key)
        if current is None:
            raise Reject("UNKNOWN_CHECKPOINT")
        if now < current.expires_at:
            raise Reject("CHECKPOINT_NOT_EXPIRED")
        self._erase(key)

    def pinned(self, root: Digest512) -> bool:
        return self.root_pins.get(digest_key(root), 0) != 0

    def _erase(self, key: bytes) -> None:
        checkpoint = self.checkpoints.pop(key)
        root_key = digest_key(checkpoint.bindings.root)
        count = self.root_pins[root_key] - 1
        if count:
            self.root_pins[root_key] = count
        else:
            del self.root_pins[root_key]

    def _consumer(self, caller: str) -> None:
        if caller != self.consumer:
            raise Reject("UNAUTHORIZED_CONSUMER")


class Pool:
    def __init__(self, ttl_blocks: int, split: int):
        self.identity = "POOL"
        self.machine = StateMachine(self.identity, ttl_blocks, split)
        self.known_roots: set[Digest512] = set()
        self.spent: set[bytes] = set()
        self.locked = False
        self.transfers: dict[str, int] = {}

    def install_root(self, root: Digest512) -> None:
        self.known_roots.add(root)

    def age_root(self, root: Digest512) -> None:
        if root not in self.known_roots:
            raise Reject("UNKNOWN_ROOT")
        if self.machine.pinned(root):
            raise Reject("ROOT_PINNED")
        self.known_roots.remove(root)

    def bindings(
        self,
        nullifier: Digest512,
        root: Digest512,
        recipient: str,
        amount: int,
        global_data: Digest512,
        checkpoint: Digest512,
        proof: Digest512,
        continuation: Digest512,
    ) -> Bindings:
        payload = (
            b"PQTC.SP72.STATEMENT.V1"
            + nullifier[0]
            + nullifier[1]
            + root[0]
            + root[1]
            + recipient.encode()
            + amount.to_bytes(32, "big")
        )
        statement_raw = sha512(payload).digest()
        return Bindings(
            (statement_raw[:32], statement_raw[32:]),
            global_data,
            checkpoint,
            proof,
            continuation,
            root,
        )

    def begin(self, now: int, nullifier: Digest512, bindings: Bindings, proof_a: bytes) -> int:
        self._enter()
        try:
            key = nullifier_key(nullifier)
            if bindings.root not in self.known_roots:
                raise Reject("UNKNOWN_ROOT")
            if key in self.spent:
                raise Reject("NULLIFIER_SPENT")
            return self.machine.begin(self.identity, now, key, bindings, proof_a)
        finally:
            self.locked = False

    def complete(
        self,
        now: int,
        nullifier: Digest512,
        bindings: Bindings,
        proof_b: bytes,
        recipient: str,
        amount: int,
        payment: Callable[[], None] | None = None,
    ) -> None:
        self._enter()
        key = nullifier_key(nullifier)
        snapshot_checkpoint = self.machine.checkpoints.get(key)
        snapshot_pins = dict(self.machine.root_pins)
        try:
            if key in self.spent:
                raise Reject("NULLIFIER_SPENT")
            self.machine.complete(self.identity, now, key, bindings, proof_b)
            self.spent.add(key)
            if payment is not None:
                payment()
            self.transfers[recipient] = self.transfers.get(recipient, 0) + amount
        except Exception:
            self.spent.discard(key)
            if snapshot_checkpoint is not None:
                self.machine.checkpoints[key] = snapshot_checkpoint
            self.machine.root_pins = snapshot_pins
            raise
        finally:
            self.locked = False

    def _enter(self) -> None:
        if self.locked:
            raise Reject("REENTRANT_CALL")
        self.locked = True


def expect_reject(code: str, action: Callable[[], object]) -> str:
    try:
        action()
    except Reject as error:
        if str(error) != code:
            raise AssertionError(f"expected {code}, got {error}") from error
        return code
    raise AssertionError(f"expected rejection: {code}")


SPLITS = ((8, 24), (10, 22), (12, 20), (13, 19), (14, 18), (15, 17), (16, 16))
ACTIVE_GAS_CAP = 2**24
ROBUST_CALL_GATE = 12_000_000
ROBUST_TOTAL_GATE = 20_000_000
CHECKPOINT_STRUCT_SLOTS = 13
WORST_INCREMENTAL_ROOT_PIN_SLOTS = 1
WORST_LIVE_SLOTS_PER_CHECKPOINT = CHECKPOINT_STRUCT_SLOTS + WORST_INCREMENTAL_ROOT_PIN_SLOTS


def storage_schedule() -> dict[str, object]:
    # Exact Prague/EIP-2200/2929/3529 opcode accounting for documented warm/cold assumptions.
    cold_sstore_set = 20_000 + 2_100
    warm_sstore_reset = 5_000
    cold_sload_then_warm_reset = 2_100 + 5_000
    create = 20_000 + 12 * cold_sstore_set + 2 * (2_100 + 20_000)
    complete_delete = 13 * warm_sstore_reset + 2 * cold_sload_then_warm_reset
    cleanup_delete = 3 * warm_sstore_reset + 10 * (warm_sstore_reset + 2_100) + 2 * cold_sload_then_warm_reset
    return {
        "classification": "EXACT_PROTOCOL_SCHEDULE_MODEL",
        "fork": "Prague",
        "assumptions": [
            "all 13 checkpoint words are nonzero",
            "new checkpoint mapping words are cold; metadata was warmed by existence read",
            "new distinct root pin and active-count words are cold-read then warm-written",
            "complete matched all checkpoint words before delete",
            "cleanup warmed metadata and both root words before delete",
        ],
        "sstore_set_zero_to_nonzero": 20_000,
        "cold_slot_surcharge": 2_100,
        "sstore_reset_nonzero_to_zero_gross": 5_000,
        "clear_refund_accrual": 4_800,
        "part_a_storage_gas": create,
        "part_b_delete_storage_gas_gross": complete_delete,
        "cleanup_delete_storage_gas_gross": cleanup_delete,
        "delete_refund_accrual_15_words": 15 * 4_800,
        "cap_accounting_uses_refund": False,
    }
