// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Digest512} from "./Digest512.sol";

library CanonicalCodec {
    uint32 internal constant BABY_BEAR_MODULUS = 2_013_265_921;

    error Truncated();
    error NonCanonicalField(uint32 value);
    error CountMismatch(uint256 expected, uint256 actual);
    error TrailingBytes();

    function readU8(bytes calldata data, uint256 cursor) internal pure returns (uint8 value, uint256 next) {
        _requireAvailable(data, cursor, 1);
        return (uint8(data[cursor]), cursor + 1);
    }

    function readU16(bytes calldata data, uint256 cursor) internal pure returns (uint16 value, uint256 next) {
        _requireAvailable(data, cursor, 2);
        assembly ("memory-safe") { value := shr(240, calldataload(add(data.offset, cursor))) }
        return (value, cursor + 2);
    }

    function readU32(bytes calldata data, uint256 cursor) internal pure returns (uint32 value, uint256 next) {
        _requireAvailable(data, cursor, 4);
        assembly ("memory-safe") { value := shr(224, calldataload(add(data.offset, cursor))) }
        return (value, cursor + 4);
    }

    function readU64(bytes calldata data, uint256 cursor) internal pure returns (uint64 value, uint256 next) {
        _requireAvailable(data, cursor, 8);
        assembly ("memory-safe") { value := shr(192, calldataload(add(data.offset, cursor))) }
        return (value, cursor + 8);
    }

    function readBytes32(bytes calldata data, uint256 cursor) internal pure returns (bytes32 value, uint256 next) {
        _requireAvailable(data, cursor, 32);
        assembly ("memory-safe") { value := calldataload(add(data.offset, cursor)) }
        return (value, cursor + 32);
    }

    function readDigest(bytes calldata data, uint256 cursor)
        internal
        pure
        returns (Digest512 memory value, uint256 next)
    {
        (value.left, cursor) = readBytes32(data, cursor);
        (value.right, next) = readBytes32(data, cursor);
    }

    function readField(bytes calldata data, uint256 cursor) internal pure returns (uint32 value, uint256 next) {
        (value, next) = readU32(data, cursor);
        if (value >= BABY_BEAR_MODULUS) revert NonCanonicalField(value);
    }

    function readCount(bytes calldata data, uint256 cursor, uint256 expected) internal pure returns (uint256 next) {
        uint32 actual;
        (actual, next) = readU32(data, cursor);
        if (actual != expected) revert CountMismatch(expected, actual);
    }

    function requireEnd(bytes calldata data, uint256 cursor) internal pure {
        if (cursor != data.length) revert TrailingBytes();
    }

    function _requireAvailable(bytes calldata data, uint256 cursor, uint256 length) private pure {
        if (cursor > data.length || length > data.length - cursor) revert Truncated();
    }
}
