// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

/// Research-only exact arithmetic for pinned Plonky3 BabyBear Poseidon2.
/// Compression is first-lane Trunc_d(P(x) + x), never TruncatedPermutation.
abstract contract Poseidon2Kernel {
    uint256 internal constant P = 2013265921;
    uint256 public immutable WIDTH;
    uint256 public immutable OUTPUT;
    uint256 public immutable PARTIAL_ROUNDS;

    error NonCanonicalLane(uint256 lane, uint256 value);
    error WrongLength(uint256 expected, uint256 actual);

    constructor(uint256 width, uint256 output, uint256 partialRounds) {
        WIDTH = width;
        OUTPUT = output;
        PARTIAL_ROUNDS = partialRounds;
    }

    function _rc(uint256 section, uint256 index) internal pure virtual returns (uint256);
    function _diag(uint256 index) internal pure virtual returns (uint256);

    function _pow7(uint256 x) private pure returns (uint256) {
        uint256 x2 = mulmod(x, x, P);
        uint256 x4 = mulmod(x2, x2, P);
        return mulmod(mulmod(x4, x2, P), x, P);
    }

    function _external(uint256[] memory state) private pure {
        uint256 width = state.length;
        for (uint256 i; i < width; i += 4) {
            uint256 a = state[i]; uint256 b = state[i + 1];
            uint256 c = state[i + 2]; uint256 d = state[i + 3];
            state[i] = addmod(addmod(addmod(mulmod(2, a, P), mulmod(3, b, P), P), c, P), d, P);
            state[i + 1] = addmod(addmod(addmod(a, mulmod(2, b, P), P), mulmod(3, c, P), P), d, P);
            state[i + 2] = addmod(addmod(addmod(a, b, P), mulmod(2, c, P), P), mulmod(3, d, P), P);
            state[i + 3] = addmod(addmod(addmod(mulmod(3, a, P), b, P), c, P), mulmod(2, d, P), P);
        }
        uint256[4] memory sums;
        for (uint256 i; i < width; ++i) sums[i & 3] = addmod(sums[i & 3], state[i], P);
        for (uint256 i; i < width; ++i) state[i] = addmod(state[i], sums[i & 3], P);
    }

    function _permutation(uint256[] memory state) internal view returns (uint256[] memory) {
        if (state.length != WIDTH) revert WrongLength(WIDTH, state.length);
        for (uint256 i; i < state.length; ++i) if (state[i] >= P) revert NonCanonicalLane(i, state[i]);
        _external(state);
        for (uint256 round; round < 4; ++round) {
            for (uint256 i; i < WIDTH; ++i) state[i] = _pow7(addmod(state[i], _rc(0, round * WIDTH + i), P));
            _external(state);
        }
        for (uint256 round; round < PARTIAL_ROUNDS; ++round) {
            state[0] = _pow7(addmod(state[0], _rc(1, round), P));
            uint256 sum;
            for (uint256 i; i < WIDTH; ++i) sum = addmod(sum, state[i], P);
            for (uint256 i; i < WIDTH; ++i) state[i] = addmod(sum, mulmod(_diag(i), state[i], P), P);
        }
        for (uint256 round; round < 4; ++round) {
            for (uint256 i; i < WIDTH; ++i) state[i] = _pow7(addmod(state[i], _rc(2, round * WIDTH + i), P));
            _external(state);
        }
        return state;
    }

    function permutation(uint256[] calldata input) external view returns (uint256[] memory) {
        return _permutation(input);
    }

    function compression(uint256[] calldata input) external view returns (uint256[] memory output) {
        uint256[] memory original = input;
        uint256[] memory state = _permutation(input);
        output = new uint256[](OUTPUT);
        for (uint256 i; i < OUTPUT; ++i) output[i] = addmod(state[i], original[i], P);
    }

    function _application(uint256 role, uint256 level, uint256[] memory payload) internal view returns (uint256[] memory output) {
        if (payload.length != 2 * OUTPUT) revert WrongLength(2 * OUTPUT, payload.length);
        uint256[] memory state = new uint256[](WIDTH);
        for (uint256 i; i < payload.length; ++i) state[i] = payload[i];
        state[payload.length] = role;
        state[payload.length + 1] = 1; // protocol version
        state[payload.length + 2] = payload.length; // shape, in field lanes
        state[payload.length + 3] = level;
        uint256[] memory original = new uint256[](OUTPUT);
        for (uint256 i; i < OUTPUT; ++i) original[i] = state[i];
        state = _permutation(state);
        output = new uint256[](OUTPUT);
        for (uint256 i; i < OUTPUT; ++i) output[i] = addmod(state[i], original[i], P);
    }
}

abstract contract Poseidon2ApplicationKernel is Poseidon2Kernel {
    constructor(uint256 width, uint256 output, uint256 partialRounds) Poseidon2Kernel(width, output, partialRounds) {}
    function note(uint256[] calldata payload) external view returns (uint256[] memory) { return _application(2, 0, payload); }
    function nullifier(uint256[] calldata payload) external view returns (uint256[] memory) { return _application(3, 0, payload); }
    function node(uint256 level, uint256[] calldata left, uint256[] calldata right) external view returns (uint256[] memory) {
        if (left.length != OUTPUT) revert WrongLength(OUTPUT, left.length);
        if (right.length != OUTPUT) revert WrongLength(OUTPUT, right.length);
        uint256[] memory payload = new uint256[](2 * OUTPUT);
        for (uint256 i; i < OUTPUT; ++i) { payload[i] = left[i]; payload[OUTPUT + i] = right[i]; }
        return _application(4, level, payload);
    }
}
