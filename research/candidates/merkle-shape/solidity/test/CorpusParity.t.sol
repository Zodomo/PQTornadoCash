// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {Digest512} from "pqtc/libraries/Digest512.sol";
import {PQTCApplicationHash} from "pqtc/libraries/PQTCApplicationHash.sol";

contract CorpusParityTest is Test {
    uint8 private constant DEPTH = 20;
    Digest512[20] private frontier;
    Digest512[21] private zeros;

    function testFrozenV03AllThousandRoots() external {
        string memory json = vm.readFile("../../../../test-vectors/hash/v3.json");
        assertEq(vm.parseJsonUint(json, ".version"), 3);
        assertEq(vm.parseJsonUint(json, ".count"), 1000);
        Digest512 memory scope = _digest(json, ".vectors[0].scope");
        zeros[0] = PQTCApplicationHash.emptyLeaf(scope);
        for (uint8 level; level < DEPTH; ++level) {
            frontier[level] = zeros[level];
            zeros[level + 1] = PQTCApplicationHash.merkleNode(level, zeros[level], zeros[level]);
        }
        for (uint256 i; i < 1000; ++i) {
            string memory base = string.concat(".vectors[", vm.toString(i), "]");
            Digest512 memory root = _insert(_digest(json, string.concat(base, ".commitment")), uint32(i));
            Digest512 memory expected = _digest(json, string.concat(base, ".root_after_insert"));
            assertEq(root.left, expected.left, "root left mismatch");
            assertEq(root.right, expected.right, "root right mismatch");
        }
    }

    function _insert(Digest512 memory current, uint32 index) private returns (Digest512 memory) {
        for (uint8 level; level < DEPTH; ++level) {
            if (index & 1 == 0) {
                frontier[level] = current;
                current = PQTCApplicationHash.merkleNode(level, current, zeros[level]);
            } else {
                current = PQTCApplicationHash.merkleNode(level, frontier[level], current);
            }
            index >>= 1;
        }
        return current;
    }

    function _digest(string memory json, string memory key) private pure returns (Digest512 memory value) {
        bytes memory encoded = vm.parseJsonBytes(json, key);
        if (encoded.length != 64) revert("digest length");
        assembly ("memory-safe") {
            mstore(value, mload(add(encoded, 0x20)))
            mstore(add(value, 0x20), mload(add(encoded, 0x40)))
        }
    }
}
