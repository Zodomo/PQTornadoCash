// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {Digest512} from "../src/libraries/Digest512.sol";
import {P2BB512} from "../src/libraries/P2BB512.sol";

contract P2BB512Harness {
    function permute(uint32[16] memory state) external pure returns (uint32[16] memory) {
        return P2BB512.permute(state);
    }

    function toFields(Digest512 memory digest) external pure returns (uint32[16] memory) {
        return P2BB512.toFields(digest);
    }

    function fromFields(uint32[16] memory fields) external pure returns (Digest512 memory) {
        return P2BB512.fromFields(fields);
    }

    function hashFields16(uint8 domainTag, uint32[16] memory elements) external pure returns (Digest512 memory) {
        return P2BB512.hashFields16(domainTag, elements);
    }

    function hashU16s16(uint8 domainTag, uint16[16] memory elements) external pure returns (Digest512 memory) {
        return P2BB512.hashU16s16(domainTag, elements);
    }

    function merkleNode(uint8 level, Digest512 memory left, Digest512 memory right)
        external
        pure
        returns (Digest512 memory)
    {
        return P2BB512.merkleNode(level, left, right);
    }

    function depth20(Digest512 memory leaf, Digest512[20] memory siblings)
        external
        pure
        returns (Digest512 memory current)
    {
        current = leaf;
        for (uint256 level = 0; level < 20; ++level) {
            current = P2BB512.merkleNode(uint8(level), current, siblings[level]);
        }
    }
}

contract P2BB512Test is Test {
    uint32 private constant P = 2_013_265_921;
    P2BB512Harness private harness;

    function setUp() external {
        harness = new P2BB512Harness();
    }

    /// Vector copied from the pinned Plonky3 BabyBear poseidon2.rs
    /// test_default_babybear_poseidon2_width_16 test.
    function testPinnedUpstreamPermutationVector() external view {
        uint32[16] memory input = [
            uint32(894848333),
            1437655012,
            1200606629,
            1690012884,
            71131202,
            1749206695,
            1717947831,
            120589055,
            19776022,
            42382981,
            1831865506,
            724844064,
            171220207,
            1299207443,
            227047920,
            1783754913
        ];
        uint32[16] memory expected = [
            uint32(516096821),
            90309867,
            1101817252,
            1660784290,
            360715097,
            1789519026,
            1788910906,
            563338433,
            319524748,
            1741414159,
            1650859320,
            894311162,
            1121347488,
            1692793758,
            1052633829,
            1344246938
        ];

        uint32[16] memory actual = harness.permute(input);
        for (uint256 i = 0; i < 16; ++i) {
            assertEq(actual[i], expected[i], "permutation limb");
        }
    }

    function testDigestBigEndianRoundTrip() external view {
        uint32[16] memory fields;
        for (uint32 i = 0; i < 16; ++i) {
            fields[i] = i;
        }

        Digest512 memory digest = harness.fromFields(fields);
        assertEq(digest.left, 0x0000000000000001000000020000000300000004000000050000000600000007);
        assertEq(digest.right, 0x00000008000000090000000a0000000b0000000c0000000d0000000e0000000f);

        uint32[16] memory decoded = harness.toFields(digest);
        for (uint256 i = 0; i < 16; ++i) {
            assertEq(decoded[i], fields[i], "digest limb");
        }
    }

    function testRejectsNonCanonicalDigestLimb() external {
        Digest512 memory malformed = Digest512(bytes32(uint256(P) << 224), bytes32(0));
        vm.expectRevert(abi.encodeWithSelector(P2BB512.NonCanonicalDigestLimb.selector, 0, P));
        harness.toFields(malformed);
    }

    function testMerkleRejectsNonCanonicalDigestLimb() external {
        Digest512 memory malformed = Digest512(bytes32(uint256(P) << 192), bytes32(0));
        Digest512 memory zero = Digest512(bytes32(0), bytes32(0));
        vm.expectRevert(abi.encodeWithSelector(P2BB512.NonCanonicalDigestLimb.selector, 1, P));
        harness.merkleNode(0, malformed, zero);
    }

    function testRejectsNonCanonicalPermutationInput() external {
        uint32[16] memory input;
        input[9] = P;
        vm.expectRevert(abi.encodeWithSelector(P2BB512.NonCanonicalFieldElement.selector, 9, P));
        harness.permute(input);
    }

    function testDomainAndLengthSeparation() external view {
        uint32[16] memory fields;
        uint16[16] memory u16s;
        for (uint16 i = 0; i < 16; ++i) {
            fields[i] = i + 1;
            u16s[i] = i + 1;
        }

        Digest512 memory fieldDomainA = harness.hashFields16(0x10, fields);
        Digest512 memory fieldDomainB = harness.hashFields16(0x11, fields);
        Digest512 memory shortEncoding = harness.hashU16s16(0x10, u16s);
        _assertDifferent(fieldDomainA, fieldDomainB, "domain tag must separate");
        _assertDifferent(fieldDomainA, shortEncoding, "payload byte length must separate");
    }

    function testMerkleAuxLevelSeparation() external view {
        uint32[16] memory leftFields;
        uint32[16] memory rightFields;
        for (uint32 i = 0; i < 16; ++i) {
            leftFields[i] = i + 1;
            rightFields[i] = i + 101;
        }
        Digest512 memory left = harness.fromFields(leftFields);
        Digest512 memory right = harness.fromFields(rightFields);

        Digest512 memory level0 = harness.merkleNode(0, left, right);
        Digest512 memory level1 = harness.merkleNode(1, left, right);
        _assertDifferent(level0, level1, "Merkle aux level must separate");
    }

    /// @dev Enforces the per-transaction budget for one complete depth-20 path.
    function testGasDepth20HashCeiling() external {
        uint32[16] memory fields;
        for (uint32 i = 0; i < 16; ++i) {
            fields[i] = i;
        }
        Digest512 memory leaf = harness.fromFields(fields);
        Digest512[20] memory siblings;
        for (uint256 i = 0; i < 20; ++i) {
            siblings[i] = leaf;
        }

        uint256 beforeGas = gasleft();
        harness.depth20(leaf, siblings);
        uint256 gasUsed = beforeGas - gasleft();
        emit log_named_uint("P2BB512 depth-20 hash gas", gasUsed);
        assertLe(gasUsed, 15_000_000, "depth-20 Merkle hashing exceeds 15M gas");
    }

    function _assertDifferent(Digest512 memory a, Digest512 memory b, string memory reason) private pure {
        assertTrue(a.left != b.left || a.right != b.right, reason);
    }
}
