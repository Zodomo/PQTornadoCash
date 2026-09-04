#!/usr/bin/env python3
"""Deterministic SP-12 queue and public transition-relation semantics.

Hashes are model-domain SHA-512/SHA-256 values. ModelProofBackend proves only that
these executable semantics are self-consistent; it is not a PCS/STARK proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256, sha512

BATCH_SIZES = (8, 16, 32, 64, 256)


class Reject(ValueError):
    pass


@dataclass(frozen=True)
class Deposit:
    deposit_id: bytes
    commitment: bytes
    depositor: bytes
    refund_address: bytes
    amount: int
    enqueued_at: int
    sequence: int

    def encode(self) -> bytes:
        return (
            self.deposit_id + self.commitment + self.depositor + self.refund_address
            + self.amount.to_bytes(32, "big") + self.enqueued_at.to_bytes(8, "big")
            + self.sequence.to_bytes(8, "big")
        )


@dataclass(frozen=True)
class TransitionStatement:
    queue_domain: bytes
    old_root: bytes
    new_root: bytes
    prefix_commitment: bytes
    start_index: int
    count: int
    queue_epoch: int

    def encode(self) -> bytes:
        return (
            b"PQTC.SP12.PUBLIC.TRANSITION.V1\x00" + self.queue_domain
            + self.old_root + self.new_root + self.prefix_commitment
            + self.start_index.to_bytes(8, "big") + self.count.to_bytes(4, "big")
            + self.queue_epoch.to_bytes(8, "big")
        )


class ModelProofBackend:
    """Executable relation oracle; intentionally not a cryptographic proof backend."""

    name = "MODEL_ORACLE_NOT_A_PCS"

    @staticmethod
    def proof(statement: TransitionStatement) -> bytes:
        return sha256(b"PQTC.SP12.MODEL.PROOF.V1\x00" + statement.encode()).digest()

    @staticmethod
    def verify(statement: TransitionStatement, proof: bytes) -> bool:
        return proof == ModelProofBackend.proof(statement)


class NoProofBackend:
    name = "NOT_EVALUATED"

    @staticmethod
    def verify(statement: TransitionStatement, proof: bytes) -> bool:
        return False


def prefix_commitment(deposits: list[Deposit]) -> bytes:
    return sha256(
        b"PQTC.SP12.CANONICAL.PREFIX.V1\x00"
        + len(deposits).to_bytes(4, "big")
        + b"".join(deposit.encode() for deposit in deposits)
    ).digest()


def transition_root(old_root: bytes, start_index: int, deposits: list[Deposit]) -> bytes:
    if len(old_root) != 64:
        raise Reject("old root must be 64 bytes")
    current = old_root
    for offset, deposit in enumerate(deposits):
        current = sha512(
            b"PQTC.SP12.MODEL.ACCUMULATE.V1\x00"
            + (start_index + offset).to_bytes(8, "big") + current + deposit.commitment
        ).digest()
    return current


class Queue:
    def __init__(self, denomination: int, timeout: int, escape: str, backend: object):
        if denomination <= 0 or timeout <= 0:
            raise Reject("invalid queue parameters")
        if escape not in ("refund", "forced_single"):
            raise Reject("unsupported escape mode")
        self.denomination = denomination
        self.timeout = timeout
        self.escape = escape
        self.backend = backend
        self.queue_domain = sha256(
            b"PQTC.SP12.QUEUE.DOMAIN.V1\x00" + denomination.to_bytes(32, "big")
            + timeout.to_bytes(8, "big") + escape.encode("ascii")
        ).digest()
        self.pending: list[Deposit] = []
        self.seen_commitments: set[bytes] = set()
        self.next_sequence = 0
        self.accumulator_index = 0
        self.accumulator_root = sha512(b"PQTC.SP12.MODEL.EMPTY.ROOT.V1").digest()
        self.queue_epoch = 0
        self.custody = 0
        self.refunds: dict[bytes, int] = {}

    def enqueue(self, commitment: bytes, depositor: bytes, refund_address: bytes, amount: int, now: int) -> Deposit:
        if len(commitment) != 64 or commitment == bytes(64):
            raise Reject("invalid commitment")
        if len(depositor) != 20 or len(refund_address) != 20 or refund_address == bytes(20):
            raise Reject("invalid address")
        if amount != self.denomination:
            raise Reject("wrong denomination")
        if commitment in self.seen_commitments:
            raise Reject("duplicate commitment")
        sequence = self.next_sequence
        deposit_id = sha256(
            b"PQTC.SP12.DEPOSIT.V1\x00" + sequence.to_bytes(8, "big") + commitment
            + depositor + refund_address + amount.to_bytes(32, "big") + now.to_bytes(8, "big")
        ).digest()
        deposit = Deposit(deposit_id, commitment, depositor, refund_address, amount, now, sequence)
        self.pending.append(deposit)
        self.seen_commitments.add(commitment)
        self.next_sequence += 1
        self.custody += amount
        return deposit

    def expected_statement(self, count: int) -> TransitionStatement:
        if count not in BATCH_SIZES or len(self.pending) < count:
            raise Reject("unsupported or unavailable batch")
        selected = self.pending[:count]
        return TransitionStatement(
            self.queue_domain,
            self.accumulator_root,
            transition_root(self.accumulator_root, self.accumulator_index, selected),
            prefix_commitment(selected),
            self.accumulator_index,
            count,
            self.queue_epoch,
        )

    def finalize(
        self,
        caller: bytes,
        claimed: list[Deposit],
        statement: TransitionStatement,
        proof: bytes,
    ) -> int:
        if len(caller) != 20:
            raise Reject("invalid permissionless caller identity")
        if statement.count not in BATCH_SIZES or len(claimed) != statement.count:
            raise Reject("invalid batch size")
        if len(self.pending) < statement.count:
            raise Reject("insufficient queue")
        canonical = self.pending[: statement.count]
        if [row.deposit_id for row in claimed] != [row.deposit_id for row in canonical]:
            raise Reject("not the canonical queue prefix")
        if len({row.deposit_id for row in claimed}) != len(claimed):
            raise Reject("duplicate deposit in batch")
        expected = self.expected_statement(statement.count)
        if statement != expected:
            raise Reject("public transition statement mismatch")
        if not self.backend.verify(statement, proof):
            raise Reject("transition proof rejected")
        del self.pending[: statement.count]
        self.accumulator_root = statement.new_root
        self.accumulator_index += statement.count
        self.queue_epoch += 1
        value = statement.count * self.denomination
        self.custody -= value
        return value

    def escape_head(self, caller: bytes, now: int) -> str:
        if len(caller) != 20 or not self.pending:
            raise Reject("invalid escape call")
        head = self.pending[0]
        if now < head.enqueued_at + self.timeout:
            raise Reject("timeout not reached")
        if self.escape == "refund":
            self.pending.pop(0)
            self.custody -= head.amount
            self.refunds[head.refund_address] = self.refunds.get(head.refund_address, 0) + head.amount
            self.queue_epoch += 1
            return "REFUNDED_HEAD"
        old = self.accumulator_root
        self.accumulator_root = transition_root(old, self.accumulator_index, [head])
        self.accumulator_index += 1
        self.pending.pop(0)
        self.custody -= head.amount
        self.queue_epoch += 1
        return "FORCED_SINGLE_HEAD"
