// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {Digest512} from "../src/libraries/Digest512.sol";
import {P2BB512} from "../src/libraries/P2BB512.sol";
import {PQTCApplicationHash} from "../src/libraries/PQTCApplicationHash.sol";

contract HashVectorsTest is Test {
    uint8 private constant DEPTH = 20;
    Digest512[20] private filledSubtrees;
    Digest512[21] private zeros;

    function testAllThousandV3ApplicationVectorsAndRoots() external {
        string memory json = vm.readFile("test-vectors/hash/v3.json");
        assertEq(vm.parseJsonUint(json, ".version"), 3);
        assertEq(vm.parseJsonUint(json, ".count"), 1_000);
        string memory first = ".vectors[0]";
        Digest512 memory parameterId = parseDigest(json, string.concat(first, ".parameter_id"));
        Digest512 memory poolScope = PQTCApplicationHash.scope(
            11_155_111, 0x1111111111111111111111111111111111111111, 0.001 ether, DEPTH, 3, parameterId
        );
        assertDigest(poolScope, parseDigest(json, string.concat(first, ".scope")));
        zeros[0] = PQTCApplicationHash.emptyLeaf(poolScope);
        for (uint8 level = 0; level < DEPTH; ++level) {
            filledSubtrees[level] = zeros[level];
            zeros[level + 1] = PQTCApplicationHash.merkleNode(level, zeros[level], zeros[level]);
        }

        for (uint256 i = 0; i < 1_000; ++i) {
            string memory base = string.concat(".vectors[", vm.toString(i), "]");
            bytes32 secret = vm.parseJsonBytes32(json, string.concat(base, ".nullifier_secret"));
            bytes32 trapdoor = vm.parseJsonBytes32(json, string.concat(base, ".trapdoor"));
            Digest512 memory noteCommitment = PQTCApplicationHash.commitment(poolScope, secret, trapdoor);
            assertDigest(noteCommitment, parseDigest(json, string.concat(base, ".commitment")));
            assertDigest(
                PQTCApplicationHash.nullifierHash(poolScope, secret),
                parseDigest(json, string.concat(base, ".nullifier_hash"))
            );
            assertDigest(
                PQTCApplicationHash.payoutDigest(
                    parseAddress(json, string.concat(base, ".recipient")),
                    parseAddress(json, string.concat(base, ".relayer")),
                    parseUint256(json, string.concat(base, ".fee"))
                ),
                parseDigest(json, string.concat(base, ".payout_digest"))
            );
            assertDigest(zeros[0], parseDigest(json, string.concat(base, ".zero_leaf")));
            assertDigest(
                PQTCApplicationHash.merkleNode(0, noteCommitment, zeros[0]),
                parseDigest(json, string.concat(base, ".level_zero_node"))
            );
            assertDigest(
                insert(noteCommitment, uint32(i)), parseDigest(json, string.concat(base, ".root_after_insert"))
            );
        }
    }

    function testNotePreimagesRequireCanonicalBigEndianU32Limbs() external {
        Digest512 memory poolScope = Digest512(bytes32(0), bytes32(0));
        bytes32 noncanonicalFirst = bytes32(uint256(2_013_265_921) << 224);
        bytes memory firstError = abi.encodeWithSelector(
            PQTCApplicationHash.NonCanonicalNotePreimageLimb.selector, uint256(0), uint256(2_013_265_921)
        );

        vm.expectRevert(firstError);
        this.hashCommitment(poolScope, noncanonicalFirst, bytes32(0));
        vm.expectRevert(firstError);
        this.hashNullifier(poolScope, noncanonicalFirst);

        bytes32 noncanonicalLast = bytes32(uint256(2_013_265_921));
        vm.expectRevert(
            abi.encodeWithSelector(
                PQTCApplicationHash.NonCanonicalNotePreimageLimb.selector, uint256(7), uint256(2_013_265_921)
            )
        );
        this.hashNullifier(poolScope, noncanonicalLast);
        Digest512 memory canonicalBoundary =
            PQTCApplicationHash.nullifierHash(poolScope, bytes32(uint256(2_013_265_920)));
        P2BB512.toFields(canonicalBoundary);

        bytes32 noncanonicalTrapdoor = bytes32(uint256(2_013_265_921) << 128);
        vm.expectRevert(
            abi.encodeWithSelector(
                PQTCApplicationHash.NonCanonicalNotePreimageLimb.selector, uint256(11), uint256(2_013_265_921)
            )
        );
        this.hashCommitment(poolScope, bytes32(0), noncanonicalTrapdoor);
    }

    function hashCommitment(Digest512 calldata poolScope, bytes32 nullifierSecret, bytes32 trapdoor)
        external
        pure
        returns (Digest512 memory)
    {
        return PQTCApplicationHash.commitment(poolScope, nullifierSecret, trapdoor);
    }

    function hashNullifier(Digest512 calldata poolScope, bytes32 nullifierSecret)
        external
        pure
        returns (Digest512 memory)
    {
        return PQTCApplicationHash.nullifierHash(poolScope, nullifierSecret);
    }

    function insert(Digest512 memory leaf, uint32 index) private returns (Digest512 memory current) {
        current = leaf;
        for (uint8 level = 0; level < DEPTH; ++level) {
            if (index & 1 == 0) {
                filledSubtrees[level] = current;
                current = PQTCApplicationHash.merkleNode(level, current, zeros[level]);
            } else {
                current = PQTCApplicationHash.merkleNode(level, filledSubtrees[level], current);
            }
            index >>= 1;
        }
    }

    function parseDigest(string memory json, string memory key) private pure returns (Digest512 memory value) {
        bytes memory encoded = vm.parseJsonBytes(json, key);
        assertEq(encoded.length, 64);
        assembly ("memory-safe") {
            mstore(value, mload(add(encoded, 0x20)))
            mstore(add(value, 0x20), mload(add(encoded, 0x40)))
        }
    }

    function parseAddress(string memory json, string memory key) private pure returns (address value) {
        bytes memory encoded = vm.parseJsonBytes(json, key);
        assertEq(encoded.length, 20);
        assembly ("memory-safe") { value := shr(96, mload(add(encoded, 0x20))) }
    }

    function parseUint256(string memory json, string memory key) private pure returns (uint256 value) {
        bytes memory encoded = vm.parseJsonBytes(json, key);
        assertEq(encoded.length, 32);
        assembly ("memory-safe") { value := mload(add(encoded, 0x20)) }
    }

    function assertDigest(Digest512 memory actual, Digest512 memory expected) private pure {
        uint32[16] memory actualFields = P2BB512.toFields(actual);
        uint32[16] memory expectedFields = P2BB512.toFields(expected);
        for (uint256 i = 0; i < 16; ++i) {
            assertEq(actualFields[i], expectedFields[i], "canonical digest limb");
        }
    }
}
