// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

/// @notice Research-only digest width and fixed-storage microbenchmark harness.
contract DigestWidthHarness {
    bytes32 internal firstWord;
    bytes32 internal secondWord;

    function hash512(uint8 tag, bytes calldata payload) external pure returns (bytes32 left, bytes32 right) {
        return _pair(tag, payload);
    }

    function hash384(uint8 tag, bytes calldata payload) external pure returns (bytes24 left, bytes24 right) {
        (bytes32 fullLeft, bytes32 fullRight) = _pair(tag, payload);
        return (bytes24(fullLeft), bytes24(fullRight));
    }

    function hash320(uint8 tag, bytes calldata payload) external pure returns (bytes20 left, bytes20 right) {
        (bytes32 fullLeft, bytes32 fullRight) = _pair(tag, payload);
        return (bytes20(fullLeft), bytes20(fullRight));
    }

    function hash256(uint8 tag, bytes calldata payload) external pure returns (bytes32 digest) {
        return _single(tag, payload);
    }

    function store512(bytes32 left, bytes32 right) external {
        firstWord = left;
        secondWord = right;
    }

    function store384(bytes24 left, bytes24 right) external {
        firstWord = bytes32(left);
        secondWord = bytes32(right);
    }

    function store320(bytes20 left, bytes20 right) external {
        firstWord = bytes32(left);
        secondWord = bytes32(right);
    }

    function store256(bytes32 digest) external {
        firstWord = digest;
    }

    function hashAndStore512(uint8 tag, bytes calldata payload) external {
        (firstWord, secondWord) = _pair(tag, payload);
    }

    function hashAndStore384(uint8 tag, bytes calldata payload) external {
        (bytes32 left, bytes32 right) = _pair(tag, payload);
        firstWord = bytes32(bytes24(left));
        secondWord = bytes32(bytes24(right));
    }

    function hashAndStore320(uint8 tag, bytes calldata payload) external {
        (bytes32 left, bytes32 right) = _pair(tag, payload);
        firstWord = bytes32(bytes20(left));
        secondWord = bytes32(bytes20(right));
    }

    function hashAndStore256(uint8 tag, bytes calldata payload) external {
        firstWord = _single(tag, payload);
    }

    function storedWords() external view returns (bytes32, bytes32) {
        return (firstWord, secondWord);
    }

    function _pair(uint8 tag, bytes calldata payload) private pure returns (bytes32 left, bytes32 right) {
        bytes memory framed = new bytes(payload.length + 2);
        framed[1] = bytes1(tag);
        assembly ("memory-safe") {
            calldatacopy(add(framed, 0x22), payload.offset, payload.length)
            left := keccak256(add(framed, 0x20), mload(framed))
            mstore8(add(framed, 0x20), 1)
            right := keccak256(add(framed, 0x20), mload(framed))
        }
    }

    function _single(uint8 tag, bytes calldata payload) private pure returns (bytes32 digest) {
        bytes memory framed = new bytes(payload.length + 2);
        framed[1] = bytes1(tag);
        assembly ("memory-safe") {
            calldatacopy(add(framed, 0x22), payload.offset, payload.length)
            digest := keccak256(add(framed, 0x20), mload(framed))
        }
    }
}
