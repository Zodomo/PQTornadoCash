// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;
import "./Poseidon16Candidates.sol";

/// Current v0.3 width-16/rate-4 P2BB512 framing, retained only as a benchmark control.
contract H0Sponge is H1Poseidon2 {
    function _hash(uint256 role, uint256 level, uint256[] memory payload) internal view returns (uint256[] memory output) {
        uint256[] memory state = new uint256[](16);
        state[4] = 1;
        state[5] = role;
        state[6] = payload.length * 4;
        state[7] = payload.length;
        state[8] = level;
        if (payload.length == 0) state = _permutation(state);
        else {
            for (uint256 offset; offset < payload.length; offset += 4) {
                uint256 end = offset + 4 < payload.length ? offset + 4 : payload.length;
                for (uint256 i = offset; i < end; ++i) {
                    if (payload[i] >= P) revert NonCanonicalLane(i, payload[i]);
                    state[i - offset] = addmod(state[i - offset], payload[i], P);
                }
                state = _permutation(state);
            }
        }
        output = new uint256[](16);
        for (uint256 blockIndex; blockIndex < 4; ++blockIndex) {
            if (blockIndex != 0) state = _permutation(state);
            for (uint256 i; i < 4; ++i) output[4 * blockIndex + i] = state[i];
        }
    }

    function hash(uint256 role, uint256 level, uint256[] calldata payload) external view returns (uint256[] memory) {
        return _hash(role, level, payload);
    }

    function note(uint256[] calldata payload) external view returns (uint256[] memory) {
        if (payload.length != 32) revert WrongLength(32, payload.length);
        return _hash(0x11, 0, payload);
    }

    function nullifier(uint256[] calldata payload) external view returns (uint256[] memory) {
        if (payload.length != 24) revert WrongLength(24, payload.length);
        return _hash(0x12, 0, payload);
    }

    function node(uint256 level, uint256[] calldata left, uint256[] calldata right) external view returns (uint256[] memory) {
        if (left.length != 16) revert WrongLength(16, left.length);
        if (right.length != 16) revert WrongLength(16, right.length);
        uint256[] memory payload = new uint256[](32);
        for (uint256 i; i < 16; ++i) {
            payload[i] = left[i];
            payload[16 + i] = right[i];
        }
        return _hash(0x20, level, payload);
    }
}
