// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {CanonicalCodec} from "../libraries/CanonicalCodec.sol";
import {Digest512} from "../libraries/Digest512.sol";

/// Binary MMCS verification from a sorted/deduplicated Plonky3 pruned frontier.
library MmcsVerifier {
    uint256 private constant MAX_LEAVES = 16;
    uint256 private constant SALT_FIELDS = 8;

    error InvalidPathLength();
    error InvalidMultiproof();
    error ConflictingDuplicate();
    error MultiproofRootMismatch(bytes32 expectedLeft, bytes32 actualLeft, uint256 consumed, uint256 supplied);

    struct LeafWords {
        bytes32[16] lefts;
        bytes32[16] rights;
    }

    struct FrontierState {
        uint32[16] indices;
        bytes32[16] lefts;
        bytes32[16] rights;
        bytes scratch;
        uint256 count;
        uint256 cursor;
        uint256 consumed;
        uint256 supplied;
    }

    function hashBatchLeaf(
        bytes calldata proof,
        uint256 rowsOffset,
        uint256 saltsOffset,
        uint256 query,
        uint256 matrices,
        uint256 rowWidth
    ) internal pure returns (bytes32 left, bytes32 right) {
        uint256 fields = matrices * (rowWidth + SALT_FIELDS);
        bytes memory payload = new bytes(4 + fields * 4);
        assembly ("memory-safe") { mstore(add(payload, 0x20), shl(224, mul(fields, 4))) }
        uint256 out = 4;
        for (uint256 matrix; matrix < matrices; ++matrix) {
            uint256 row = rowsOffset + (query * matrices * rowWidth + matrix * rowWidth) * 4;
            uint256 salt = saltsOffset + (query * matrices * SALT_FIELDS + matrix * SALT_FIELDS) * 4;
            uint256 rowBytes = rowWidth * 4;
            assembly ("memory-safe") {
                calldatacopy(add(add(payload, 0x20), out), add(proof.offset, row), rowBytes)
            }
            out += rowBytes;
            assembly ("memory-safe") {
                calldatacopy(add(add(payload, 0x20), out), add(proof.offset, salt), 32)
            }
            out += 32;
        }
        return _hashLeafPayload(payload);
    }

    function hashFriLeaf(uint256 folded, uint256 sibling, uint256 index, bytes calldata proof, uint256 saltOffset)
        internal
        pure
        returns (Digest512 memory digest)
    {
        (digest.left, digest.right) = hashFriLeafWords(folded, sibling, index, proof, saltOffset);
    }

    function hashFriLeafWords(uint256 folded, uint256 sibling, uint256 index, bytes calldata proof, uint256 saltOffset)
        internal
        pure
        returns (bytes32 left, bytes32 right)
    {
        return _hashLeafPayload(encodeFriLeaf(folded, sibling, index, proof, saltOffset));
    }

    function encodeFriLeaf(uint256 folded, uint256 sibling, uint256 index, bytes calldata proof, uint256 saltOffset)
        internal
        pure
        returns (bytes memory payload)
    {
        payload = new bytes(68);
        uint256 low = index & 1 == 0 ? folded : sibling;
        uint256 high = index & 1 == 0 ? sibling : folded;
        assembly ("memory-safe") {
            let mask := 0xffffffff
            let data := add(payload, 0x20)
            mstore(data, shl(224, 64))
            mstore(
                add(data, 4),
                or(
                    or(shl(224, and(low, mask)), shl(192, and(shr(32, low), mask))),
                    or(shl(160, and(shr(64, low), mask)), shl(128, and(shr(96, low), mask)))
                )
            )
            mstore(
                add(data, 20),
                or(
                    or(shl(224, and(high, mask)), shl(192, and(shr(32, high), mask))),
                    or(shl(160, and(shr(64, high), mask)), shl(128, and(shr(96, high), mask)))
                )
            )
            calldatacopy(add(data, 36), add(proof.offset, saltOffset), 32)
        }
    }

    function verifyPruned(
        Digest512 memory expectedRoot,
        uint32[16] memory indices,
        LeafWords memory leaves,
        uint256 height,
        uint256 leafCount,
        bytes calldata proof,
        uint256 cursor
    ) internal pure returns (uint256 next) {
        if (leafCount == 0 || leafCount > MAX_LEAVES) revert InvalidMultiproof();
        if (height == 0 || height > 31) revert InvalidPathLength();
        FrontierState memory state;
        state.scratch = new bytes(160);
        (state.supplied, state.cursor) = CanonicalCodec.readU32(proof, cursor);
        for (uint256 query; query < leafCount; ++query) {
            uint32 index = indices[query];
            if (uint256(index) >= (uint256(1) << height)) revert InvalidPathLength();
            uint256 position;
            while (position < state.count && state.indices[position] < index) ++position;
            if (position < state.count && state.indices[position] == index) {
                if (state.lefts[position] != leaves.lefts[query] || state.rights[position] != leaves.rights[query]) {
                    revert ConflictingDuplicate();
                }
                continue;
            }
            for (uint256 move = state.count; move > position; --move) {
                state.indices[move] = state.indices[move - 1];
                state.lefts[move] = state.lefts[move - 1];
                state.rights[move] = state.rights[move - 1];
            }
            state.indices[position] = index;
            state.lefts[position] = leaves.lefts[query];
            state.rights[position] = leaves.rights[query];
            ++state.count;
        }
        for (uint256 level; level < height; ++level) {
            _reduceLevel(proof, state);
        }
        if (
            state.consumed != state.supplied || state.count != 1 || state.lefts[0] != expectedRoot.left
                || state.rights[0] != expectedRoot.right
        ) {
            revert MultiproofRootMismatch(expectedRoot.left, state.lefts[0], state.consumed, state.supplied);
        }
        return state.cursor;
    }

    function _reduceLevel(bytes calldata proof, FrontierState memory state) private pure {
        uint256 oldCount = state.count;
        uint256 parentCount;
        uint256 i;
        while (i < oldCount) {
            uint32 index = state.indices[i];
            bytes32 left0;
            bytes32 left1;
            bytes32 right0;
            bytes32 right1;
            if (index & 1 == 0) {
                left0 = state.lefts[i];
                left1 = state.rights[i];
                if (i + 1 < oldCount && state.indices[i + 1] == index + 1) {
                    right0 = state.lefts[i + 1];
                    right1 = state.rights[i + 1];
                    i += 2;
                } else {
                    (right0, right1) = _frontierWords(proof, state);
                    ++i;
                }
            } else {
                (left0, left1) = _frontierWords(proof, state);
                right0 = state.lefts[i];
                right1 = state.rights[i];
                ++i;
            }
            state.indices[parentCount] = index >> 1;
            (state.lefts[parentCount], state.rights[parentCount]) =
                _hashNodeWords(left0, left1, right0, right1, state.scratch);
            ++parentCount;
        }
        state.count = parentCount;
    }

    function hashNode(Digest512 memory left, Digest512 memory right) internal pure returns (Digest512 memory digest) {
        bytes memory scratch = new bytes(160);
        (digest.left, digest.right) = _hashNodeWords(left.left, left.right, right.left, right.right, scratch);
    }

    function _hashNodeWords(bytes32 left0, bytes32 left1, bytes32 right0, bytes32 right1, bytes memory scratch)
        private
        pure
        returns (bytes32 digest0, bytes32 digest1)
    {
        assembly ("memory-safe") {
            let start := add(scratch, 0x20)
            mstore8(start, 0)
            mstore8(add(start, 1), 0x41)
            mstore(add(start, 2), left0)
            mstore(add(start, 34), left1)
            mstore(add(start, 66), right0)
            mstore(add(start, 98), right1)
            digest0 := keccak256(start, 130)
            mstore8(start, 1)
            digest1 := keccak256(start, 130)
        }
    }

    function _frontierWords(bytes calldata proof, FrontierState memory state)
        private
        pure
        returns (bytes32 left, bytes32 right)
    {
        if (state.consumed >= state.supplied) revert InvalidMultiproof();
        if (state.cursor > proof.length || 64 > proof.length - state.cursor) revert CanonicalCodec.Truncated();
        uint256 cursor = state.cursor;
        assembly ("memory-safe") {
            left := calldataload(add(proof.offset, cursor))
            right := calldataload(add(add(proof.offset, cursor), 32))
        }
        state.cursor = cursor + 64;
        ++state.consumed;
    }

    function _hashLeafPayload(bytes memory payload) private pure returns (bytes32 left, bytes32 right) {
        assembly ("memory-safe") {
            let length := mload(payload)
            let start := add(payload, 0x1e)
            mstore8(start, 0)
            mstore8(add(start, 1), 0x40)
            left := keccak256(start, add(length, 2))
            mstore8(start, 1)
            right := keccak256(start, add(length, 2))
            mstore(payload, length)
        }
    }
}
