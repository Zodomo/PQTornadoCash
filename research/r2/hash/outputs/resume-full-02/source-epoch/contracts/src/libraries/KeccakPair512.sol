// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Digest512} from "./Digest512.sol";

library KeccakPair512 {
    function hash(uint8 tag, bytes memory payload) internal pure returns (Digest512 memory digest) {
        assembly ("memory-safe") {
            let savedLength := mload(payload)
            let start := add(payload, 0x1e)
            mstore8(start, 0)
            mstore8(add(start, 1), tag)
            mstore(digest, keccak256(start, add(savedLength, 2)))
            mstore8(start, 1)
            mstore(add(digest, 0x20), keccak256(start, add(savedLength, 2)))
            mstore(payload, savedLength)
        }
    }

    function hashCalldata(uint8 tag, bytes calldata payload) internal pure returns (Digest512 memory digest) {
        bytes memory message = new bytes(payload.length + 2);
        message[1] = bytes1(tag);
        assembly ("memory-safe") {
            calldatacopy(add(message, 0x22), payload.offset, payload.length)
            mstore(digest, keccak256(add(message, 0x20), mload(message)))
            mstore8(add(message, 0x20), 1)
            mstore(add(digest, 0x20), keccak256(add(message, 0x20), mload(message)))
        }
    }
}
