#!/usr/bin/env python3
"""Deterministic accumulator semantics for SP-11.

The SHA-512 compressor is deliberately a model oracle, not PQTC's H0. It lets the
shape, frontier, root-history, and witness relations execute without presenting a
benchmark-only or unreviewed compressor as custody-safe.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha512
from math import ceil, log
from typing import Iterable

Digest = bytes


def model_leaf(data: bytes) -> Digest:
    return sha512(b"PQTC.SP11.MODEL.LEAF.V1\x00" + data).digest()


def model_compress(arity: int, level: int, children: Iterable[Digest]) -> Digest:
    values = tuple(children)
    if arity not in (2, 4, 8) or len(values) != arity:
        raise ValueError("unsupported arity or child count")
    if any(len(value) != 64 for value in values):
        raise ValueError("digest must be 64 bytes")
    return sha512(
        b"PQTC.SP11.MODEL.NODE.V1\x00"
        + bytes((arity,))
        + level.to_bytes(2, "big")
        + b"".join(values)
    ).digest()


@dataclass(frozen=True)
class Shape:
    arity: int
    depth: int

    @property
    def capacity(self) -> int:
        return self.arity**self.depth

    @property
    def witness_bytes(self) -> int:
        return self.depth * (self.arity - 1) * 64

    @property
    def relation_hashes(self) -> int:
        return self.depth

    @property
    def binary_fold_hashes(self) -> int:
        return self.depth * (self.arity - 1)

    @staticmethod
    def preserving_capacity(arity: int, binary_depth: int = 20) -> "Shape":
        depth = ceil(binary_depth * log(2, arity))
        shape = Shape(arity, depth)
        if shape.capacity < 1 << binary_depth:
            raise AssertionError("capacity loss")
        return shape


class Accumulator:
    """Incremental arity-2/4/8 tree with exact logical frontier transitions."""

    def __init__(self, shape: Shape, zero_leaf: Digest, history_limit: int | None):
        if len(zero_leaf) != 64:
            raise ValueError("zero leaf must be 64 bytes")
        if history_limit is not None and history_limit < 1:
            raise ValueError("history limit must be positive")
        self.shape = shape
        self.zeros = [zero_leaf]
        for level in range(shape.depth):
            self.zeros.append(model_compress(shape.arity, level, [self.zeros[-1]] * shape.arity))
        self.frontier: list[list[Digest | None]] = [
            [None] * (shape.arity - 1) for _ in range(shape.depth)
        ]
        self.next_index = 0
        self.root = self.zeros[-1]
        self.history_limit = history_limit
        self.roots = [self.root]

    def insert(self, leaf: Digest) -> dict[str, int | str]:
        if len(leaf) != 64:
            raise ValueError("leaf must be 64 bytes")
        if self.next_index >= self.shape.capacity:
            raise OverflowError("tree full")
        original_index = self.next_index
        index = original_index
        current = leaf
        frontier_writes = 0
        for level in range(self.shape.depth):
            digit = index % self.shape.arity
            prior = self.frontier[level]
            if any(prior[slot] is None for slot in range(digit)):
                raise AssertionError("frontier invariant broken")
            children = [prior[slot] for slot in range(digit)]
            children.append(current)
            children.extend([self.zeros[level]] * (self.shape.arity - digit - 1))
            if digit < self.shape.arity - 1:
                prior[digit] = current
                frontier_writes += 1
            current = model_compress(self.shape.arity, level, children)  # type: ignore[arg-type]
            index //= self.shape.arity
        self.next_index += 1
        self.root = current
        if self.history_limit is None:
            self.roots.append(current)
            history_slots = 1
        else:
            if len(self.roots) < self.history_limit:
                self.roots.append(current)
            else:
                self.roots[self.next_index % self.history_limit] = current
            history_slots = 2
        return {
            "index": original_index,
            "frontier_writes": frontier_writes,
            "root_history_slot_writes": history_slots,
            "relation_hashes": self.shape.relation_hashes,
            "root": current.hex(),
        }


def recompute_padded_root(shape: Shape, zero_leaf: Digest, leaves: list[Digest]) -> Digest:
    """Independent sparse-level recomputation used for incremental parity."""
    if len(leaves) > shape.capacity:
        raise OverflowError("tree full")
    zeros = [zero_leaf]
    for level in range(shape.depth):
        zeros.append(model_compress(shape.arity, level, [zeros[-1]] * shape.arity))
    nodes = list(leaves)
    for level in range(shape.depth):
        parent_count = max(1, ceil(len(nodes) / shape.arity))
        next_nodes = []
        for parent in range(parent_count):
            children = nodes[parent * shape.arity : (parent + 1) * shape.arity]
            children += [zeros[level]] * (shape.arity - len(children))
            next_nodes.append(model_compress(shape.arity, level, children))
        nodes = next_nodes
    return nodes[0] if nodes else zeros[-1]


def synthetic_transition(shape: Shape, next_index: int) -> dict[str, int | bool]:
    """Exact control/storage counts for an insertion attempt at a synthetic index."""
    if not 0 <= next_index <= shape.capacity:
        raise ValueError("synthetic index outside capacity")
    if next_index == shape.capacity:
        return {
            "index": next_index,
            "accepted": False,
            "frontier_writes": 0,
            "frontier_live_slots_before": 0,
            "relation_hashes": 0,
            "binary_fold_hashes": 0,
        }
    index = next_index
    frontier_writes = 0
    nonzero_frontier_slots = 0
    for _ in range(shape.depth):
        digit = index % shape.arity
        nonzero_frontier_slots += digit
        frontier_writes += int(digit < shape.arity - 1)
        index //= shape.arity
    return {
        "index": next_index,
        "accepted": True,
        "frontier_writes": frontier_writes,
        "frontier_live_slots_before": nonzero_frontier_slots,
        "relation_hashes": shape.relation_hashes,
        "binary_fold_hashes": shape.binary_fold_hashes,
    }
