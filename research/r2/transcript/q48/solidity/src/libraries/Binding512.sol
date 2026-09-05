// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;
import {Digest512} from "./Digest512.sol";
import {KeccakPair512} from "./KeccakPair512.sol";
library Binding512 {
    function hash(bytes memory payload) internal pure returns (Digest512 memory) { return KeccakPair512.hash(0x47, payload); }
    function equal(Digest512 memory a, Digest512 memory b) internal pure returns (bool) { return a.left == b.left && a.right == b.right; }
}
