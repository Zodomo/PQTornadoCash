// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

struct Digest512 {
    bytes32 left;
    bytes32 right;
}

library Digest512Lib {
    function isZero(Digest512 memory value) internal pure returns (bool) {
        return value.left == bytes32(0) && value.right == bytes32(0);
    }

    function equal(Digest512 memory a, Digest512 memory b) internal pure returns (bool) {
        return a.left == b.left && a.right == b.right;
    }

    function key(Digest512 memory value) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(value.left, value.right));
    }
}
