#!/usr/bin/env python3
"""Deterministic SP-70 proof-only aggregation and pull-settlement model.

The SHA-256 tokens below are executable relation oracles, not cryptographic
proofs. In particular they establish neither soundness nor zero knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Iterable

BATCH_SIZES = (1, 2, 4, 8, 16, 32, 64)
PROOF_DESIGNS = ("RECURSIVE_BINARY_TREE", "FLAT_OUTER_PROOF", "PQ_HIDING_FOLDING")
USER_TOPOLOGIES = ("SAME_USER_MULTI_NOTE", "UNRELATED_USERS")
SCHEDULING_POLICIES = ("FIXED_WINDOW", "THRESHOLD_TRIGGERED", "PERMISSIONLESS_MULTIPLE_AGGREGATORS")
DENOMINATION = 10**18


class Reject(ValueError):
    pass


def _u(value: int, size: int) -> bytes:
    if value < 0 or value >= 1 << (8 * size):
        raise Reject("integer outside canonical width")
    return value.to_bytes(size, "big")


@dataclass(frozen=True)
class PublicStatement:
    root: bytes
    nullifier: bytes
    recipient: bytes
    relayer: bytes
    fee: int

    def encode(self) -> bytes:
        if len(self.root) != 64 or len(self.nullifier) != 64:
            raise Reject("root and nullifier must be 64 bytes")
        if len(self.recipient) != 20 or self.recipient == bytes(20):
            raise Reject("recipient must be a nonzero address")
        if len(self.relayer) != 20:
            raise Reject("relayer must be an address")
        if self.fee < 0 or self.fee > DENOMINATION:
            raise Reject("fee exceeds denomination")
        if self.fee and self.relayer == bytes(20):
            raise Reject("nonzero fee requires relayer")
        if self.nullifier == bytes(64):
            raise Reject("zero nullifier")
        return self.root + self.nullifier + self.recipient + self.relayer + _u(self.fee, 32)

    def key(self) -> bytes:
        return sha256(b"PQTC.SP70.PUBLIC.STATEMENT.V1\x00" + self.encode()).digest()


@dataclass(frozen=True)
class ProofSubmission:
    """The aggregator-facing API: public statement plus opaque proof only."""

    statement: PublicStatement
    proof: bytes


class ModelIndividualProofBackend:
    """Deterministic oracle for model tests; not an accepted proof backend."""

    name = "MODEL_ORACLE_NOT_A_PROOF"

    @staticmethod
    def prove_locally(statement: PublicStatement, private_witness: bytes) -> bytes:
        if not private_witness:
            raise Reject("local prover requires a private witness")
        # The witness is consumed only by this user-local method and is never
        # stored in ProofSubmission or exposed to Aggregator.
        witness_commitment = sha256(b"PQTC.SP70.MODEL.WITNESS.V1\x00" + private_witness).digest()
        return sha256(b"PQTC.SP70.MODEL.INDIVIDUAL.PROOF.V1\x00" + statement.encode() + witness_commitment).digest() + witness_commitment

    @staticmethod
    def verify(statement: PublicStatement, proof: bytes) -> bool:
        if len(proof) != 64:
            return False
        witness_commitment = proof[32:]
        expected = sha256(b"PQTC.SP70.MODEL.INDIVIDUAL.PROOF.V1\x00" + statement.encode() + witness_commitment).digest()
        return proof[:32] == expected


class ModelOuterProofBackend:
    """Batch-binding oracle only; not recursive, folding, hiding, or PQ evidence."""

    name = "MODEL_BATCH_BINDING_ORACLE_NOT_AN_OUTER_PROOF"

    @staticmethod
    def prove(batch_id: bytes, accepted_individual_proofs: Iterable[bytes]) -> bytes:
        proofs = tuple(accepted_individual_proofs)
        return sha256(b"PQTC.SP70.MODEL.OUTER.V1\x00" + batch_id + _u(len(proofs), 2) + b"".join(proofs)).digest()

    @staticmethod
    def verify(batch_id: bytes, accepted_individual_proofs: Iterable[bytes], proof: bytes) -> bool:
        return proof == ModelOuterProofBackend.prove(batch_id, accepted_individual_proofs)


def batch_id(statements: Iterable[PublicStatement]) -> bytes:
    rows = tuple(statements)
    if len(rows) not in BATCH_SIZES:
        raise Reject("unsupported batch size")
    keys = tuple(row.key() for row in rows)
    if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
        raise Reject("statements must have unique canonical key order")
    accumulator = sha256(b"PQTC.SP70.CANONICAL.BATCH.V1\x00" + _u(len(rows), 2)).digest()
    for key in keys:
        accumulator = sha256(accumulator + key).digest()
    return accumulator


@dataclass(frozen=True)
class BuiltBatch:
    statements: tuple[PublicStatement, ...]
    individual_proofs: tuple[bytes, ...]
    batch_id: bytes
    outer_proof: bytes


class Aggregator:
    """Permissionless proof-only combiner. Its API has no witness parameter."""

    def __init__(self, identity: bytes):
        if len(identity) != 20:
            raise Reject("invalid aggregator identity")
        self.identity = identity
        self.accepted: dict[bytes, ProofSubmission] = {}
        self.rejected: list[bytes] = []

    def submit(self, submission: ProofSubmission) -> bool:
        key = submission.statement.key()
        if not ModelIndividualProofBackend.verify(submission.statement, submission.proof):
            self.rejected.append(key)
            return False
        self.accepted[key] = submission
        return True

    def build(self, count: int) -> BuiltBatch:
        if count not in BATCH_SIZES or len(self.accepted) < count:
            raise Reject("threshold not met")
        selected = tuple(self.accepted[key] for key in sorted(self.accepted)[:count])
        statements = tuple(row.statement for row in selected)
        proofs = tuple(row.proof for row in selected)
        identifier = batch_id(statements)
        return BuiltBatch(statements, proofs, identifier, ModelOuterProofBackend.prove(identifier, proofs))


class ThresholdBatcher:
    """Builds immediately once its public target is met."""

    def __init__(self, target: int, aggregator: Aggregator):
        if target not in BATCH_SIZES:
            raise Reject("unsupported threshold")
        self.target = target
        self.aggregator = aggregator

    def trigger(self) -> BuiltBatch:
        return self.aggregator.build(self.target)


class FixedWindowBatcher:
    """Closes at a public deadline; submissions remain nonexclusive."""

    def __init__(self, target: int, opened_at: int, duration: int, aggregator: Aggregator):
        if target not in BATCH_SIZES or opened_at < 0 or duration <= 0:
            raise Reject("invalid fixed window")
        self.target = target
        self.deadline = opened_at + duration
        self.aggregator = aggregator

    def close(self, now: int) -> BuiltBatch:
        if now < self.deadline:
            raise Reject("window still open")
        return self.aggregator.build(self.target)


class Settlement:
    """Atomic nullifier consumption plus pull credits under model verification."""

    def __init__(self):
        self.spent: set[bytes] = set()
        self.credits: dict[bytes, int] = {}
        self.settled_batches: list[bytes] = []

    def settle(self, caller: bytes, built: BuiltBatch) -> bytes:
        if len(caller) != 20:
            raise Reject("invalid permissionless caller")
        identifier = batch_id(built.statements)
        if identifier != built.batch_id:
            raise Reject("batch identifier mismatch")
        if len(built.individual_proofs) != len(built.statements):
            raise Reject("proof/statement cardinality mismatch")
        if not ModelOuterProofBackend.verify(identifier, built.individual_proofs, built.outer_proof):
            raise Reject("outer binding rejected")
        nullifiers = [row.nullifier for row in built.statements]
        if len(set(nullifiers)) != len(nullifiers):
            raise Reject("duplicate nullifier in batch")
        if any(nullifier in self.spent for nullifier in nullifiers):
            raise Reject("spent nullifier")

        # All checks precede any state update. Pull credits avoid recipient code
        # invalidating settlement; a failed claim leaves the credit recoverable.
        for row in built.statements:
            self.spent.add(row.nullifier)
            self.credits[row.recipient] = self.credits.get(row.recipient, 0) + DENOMINATION - row.fee
            if row.fee:
                self.credits[row.relayer] = self.credits.get(row.relayer, 0) + row.fee
        self.settled_batches.append(identifier)
        return identifier

    def claim(self, payee: bytes, receiver_accepts: bool) -> int:
        amount = self.credits.get(payee, 0)
        if amount == 0:
            raise Reject("no pull credit")
        if not receiver_accepts:
            raise Reject("receiver rejected; credit retained")
        del self.credits[payee]
        return amount


def mutate_statement(built: BuiltBatch, index: int, **changes: object) -> BuiltBatch:
    rows = list(built.statements)
    rows[index] = replace(rows[index], **changes)
    rows.sort(key=PublicStatement.key)
    return replace(built, statements=tuple(rows))
