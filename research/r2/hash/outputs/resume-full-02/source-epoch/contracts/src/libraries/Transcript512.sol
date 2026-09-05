// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {PQTCDomains} from "../PQTCDomains.sol";
import {Digest512} from "./Digest512.sol";
import {KeccakPair512} from "./KeccakPair512.sol";

library Transcript512 {
    uint32 internal constant BABY_BEAR_MODULUS = 2_013_265_921;
    uint8 private constant FIELD_ITEM = 1;
    uint8 private constant COMMITMENT_ITEM = 2;

    struct State {
        Digest512 digest;
        bytes output;
        uint256 outputCursor;
        uint64 squeezeCounter;
        bytes scratch;
    }

    error InvalidField();
    error InvalidBitCount();
    error SqueezeCounterOverflow();

    function initialize(Digest512 memory parameterId, uint32[] memory publicValues)
        internal
        pure
        returns (State memory state)
    {
        bytes memory payload = new bytes(64 + publicValues.length * 4);
        assembly ("memory-safe") {
            mstore(add(payload, 0x20), mload(parameterId))
            mstore(add(payload, 0x40), mload(add(parameterId, 0x20)))
        }
        for (uint256 i; i < publicValues.length; ++i) {
            if (publicValues[i] >= BABY_BEAR_MODULUS) revert InvalidField();
            assembly ("memory-safe") {
                mstore(add(add(payload, 0x60), mul(i, 4)), shl(224, mload(add(add(publicValues, 0x20), mul(i, 0x20)))))
            }
        }
        state.digest = KeccakPair512.hash(PQTCDomains.TRANSCRIPT_INIT, payload);
        state.scratch = new bytes(160);
    }

    function observeField(State memory state, uint32 value) internal pure {
        if (value >= BABY_BEAR_MODULUS) revert InvalidField();
        _absorbField(state, value);
    }

    function observeCommitment(State memory state, Digest512 memory commitment) internal pure {
        _absorbCommitment(state, commitment);
    }

    function sampleField(State memory state) internal pure returns (uint32) {
        while (true) {
            uint32 value = _sampleU32(state) & 0x7fff_ffff;
            if (value < BABY_BEAR_MODULUS) return value;
        }
        revert InvalidField();
    }

    function sampleExt4(State memory state) internal pure returns (uint32[4] memory value) {
        for (uint256 i = 0; i < 4; i++) {
            value[i] = sampleField(state);
        }
    }

    function sampleBits(State memory state, uint256 bits) internal pure returns (uint256) {
        if (bits > 31) revert InvalidBitCount();
        if (bits == 0) return 0;
        return uint256(_sampleU32(state)) & ((uint256(1) << bits) - 1);
    }

    function checkWitness(State memory state, uint256 bits, uint32 witness) internal pure returns (bool) {
        if (bits == 0) return true;
        observeField(state, witness);
        return sampleBits(state, bits) == 0;
    }

    function _absorbField(State memory state, uint32 value) private pure {
        Digest512 memory digest = state.digest;
        bytes memory scratch = state.scratch;
        assembly ("memory-safe") {
            let start := add(scratch, 0x20)
            mstore8(start, 0)
            mstore8(add(start, 1), 0x43)
            mstore(add(start, 2), mload(digest))
            mstore(add(start, 34), mload(add(digest, 0x20)))
            mstore8(add(start, 66), 1)
            mstore(add(start, 67), shl(224, 4))
            mstore(add(start, 71), shl(224, value))
            mstore(digest, keccak256(start, 75))
            mstore8(start, 1)
            mstore(add(digest, 0x20), keccak256(start, 75))
        }
        state.digest = digest;
        _resetOutput(state);
    }

    function _absorbCommitment(State memory state, Digest512 memory commitment) private pure {
        Digest512 memory digest = state.digest;
        bytes memory scratch = state.scratch;
        assembly ("memory-safe") {
            let start := add(scratch, 0x20)
            mstore8(start, 0)
            mstore8(add(start, 1), 0x43)
            mstore(add(start, 2), mload(digest))
            mstore(add(start, 34), mload(add(digest, 0x20)))
            mstore8(add(start, 66), 2)
            mstore(add(start, 67), shl(224, 64))
            mstore(add(start, 71), mload(commitment))
            mstore(add(start, 103), mload(add(commitment, 0x20)))
            mstore(digest, keccak256(start, 135))
            mstore8(start, 1)
            mstore(add(digest, 0x20), keccak256(start, 135))
        }
        state.digest = digest;
        _resetOutput(state);
    }

    function _resetOutput(State memory state) private pure {
        state.output = "";
        state.outputCursor = 0;
        state.squeezeCounter = 0;
    }

    function _sampleU32(State memory state) private pure returns (uint32 value) {
        bytes memory four = new bytes(4);
        for (uint256 i = 0; i < 4; i++) {
            four[i] = _sampleByte(state);
        }
        assembly ("memory-safe") { value := shr(224, mload(add(four, 0x20))) }
    }

    function _sampleByte(State memory state) private pure returns (bytes1 value) {
        if (state.outputCursor == state.output.length) {
            if (state.squeezeCounter == type(uint64).max) revert SqueezeCounterOverflow();
            Digest512 memory blockDigest = KeccakPair512.hash(
                PQTCDomains.TRANSCRIPT_SQUEEZE,
                abi.encodePacked(state.digest.left, state.digest.right, state.squeezeCounter)
            );
            state.squeezeCounter++;
            state.output = abi.encodePacked(blockDigest.left, blockDigest.right);
            state.outputCursor = 0;
        }
        value = state.output[state.outputCursor++];
    }
}
