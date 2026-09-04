// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Digest512} from "pqtc/libraries/Digest512.sol";
import {PQTCApplicationHash} from "pqtc/libraries/PQTCApplicationHash.sol";

/// @notice Research-only accumulator harness. It is not pool/custody code.
contract H0BinaryAccumulator {
    uint8 public constant DEPTH = 20;
    uint32 public constant CAPACITY = uint32(1) << DEPTH;
    uint8 public constant HISTORY = 64;

    Digest512 public scope;
    Digest512 public latestRoot;
    Digest512[20] internal filledSubtrees;
    Digest512[21] internal zeros;
    Digest512[64] internal rootRing;
    mapping(bytes32 => mapping(bytes32 => bool)) public knownRoots;
    uint32 public nextIndex;
    bool public immutable boundedHistory;

    error TreeFull();

    constructor(Digest512 memory scope_, bool boundedHistory_) {
        scope = scope_;
        boundedHistory = boundedHistory_;
        zeros[0] = PQTCApplicationHash.emptyLeaf(scope_);
        for (uint8 level; level < DEPTH; ++level) {
            filledSubtrees[level] = zeros[level];
            zeros[level + 1] = PQTCApplicationHash.merkleNode(level, zeros[level], zeros[level]);
        }
        latestRoot = zeros[DEPTH];
        if (boundedHistory_) rootRing[0] = latestRoot;
        else knownRoots[latestRoot.left][latestRoot.right] = true;
    }

    function insert(Digest512 calldata leaf) external returns (Digest512 memory current) {
        uint32 leafIndex = nextIndex;
        if (leafIndex >= CAPACITY) revert TreeFull();
        current = leaf;
        uint32 index = leafIndex;
        for (uint8 level; level < DEPTH; ++level) {
            if (index & 1 == 0) {
                filledSubtrees[level] = current;
                current = PQTCApplicationHash.merkleNode(level, current, zeros[level]);
            } else {
                current = PQTCApplicationHash.merkleNode(level, filledSubtrees[level], current);
            }
            index >>= 1;
        }
        nextIndex = leafIndex + 1;
        latestRoot = current;
        if (boundedHistory) rootRing[(leafIndex + 1) % HISTORY] = current;
        else knownRoots[current.left][current.right] = true;
    }

    /// @dev Synthetic state is benchmark plumbing only; it makes no root-provenance claim.
    function researchLoadSyntheticIndex(uint32 index) external {
        if (index > CAPACITY) revert TreeFull();
        nextIndex = index;
        for (uint8 level; level < DEPTH; ++level) filledSubtrees[level] = zeros[level];
    }

    function zero(uint8 level) external view returns (Digest512 memory) {
        return zeros[level];
    }
}
