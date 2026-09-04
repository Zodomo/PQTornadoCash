// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {CanonicalCodec} from "../src/libraries/CanonicalCodec.sol";
import {Digest512} from "../src/libraries/Digest512.sol";
import {PQTCProofCodec} from "../src/libraries/PQTCProofCodec.sol";
import {FriVerifier} from "../src/verifier/FriVerifier.sol";
import {MmcsVerifier} from "../src/verifier/MmcsVerifier.sol";

contract VerifierFoundationHarness {
    function parseCommon(bytes calldata proof, Digest512 calldata parameterId, uint32[64] calldata values)
        external
        pure
        returns (uint256)
    {
        return PQTCProofCodec.parseCommon(proof, PQTCProofCodec.PART_A_MAGIC, parameterId, values).cursor;
    }

    function statementKey(Digest512 calldata parameterId, uint32[64] calldata values) external pure returns (bytes32) {
        return PQTCProofCodec.statementKey(parameterId, values);
    }

    function requirePartAEnd(bytes calldata proof) external pure {
        PQTCProofCodec.requireEnd(proof, 0, PQTCProofCodec.PART_A_END);
    }

    function verifyRepeatedLeaf(
        Digest512 calldata root,
        uint32 index,
        Digest512 calldata leaf,
        bytes calldata frontier,
        uint256 height,
        uint256 leafCount
    ) external pure returns (uint256) {
        uint32[16] memory indices;
        MmcsVerifier.LeafWords memory leaves;
        for (uint256 i; i < 16; ++i) {
            indices[i] = index;
            leaves.lefts[i] = leaf.left;
            leaves.rights[i] = leaf.right;
        }
        return MmcsVerifier.verifyPruned(root, indices, leaves, height, leafCount, frontier, 0);
    }

    function node(Digest512 calldata left, Digest512 calldata right) external pure returns (Digest512 memory) {
        return MmcsVerifier.hashNode(left, right);
    }

    function reverseBits(uint256 value, uint256 bits) external pure returns (uint256) {
        return FriVerifier.reverseBits(value, bits);
    }
}

contract VerifierFoundationTest is Test {
    VerifierFoundationHarness private harness;
    Digest512 private parameter;
    uint32[64] private values;

    function setUp() external {
        harness = new VerifierFoundationHarness();
        parameter = Digest512(bytes32(uint256(1)), bytes32(uint256(2)));
        for (uint256 i; i < 64; ++i) {
            values[i] = uint32(i + 1);
        }
    }

    function testV3CommonHeaderIsStrictAndCanonical() external view {
        bytes memory encoded = _header(values);
        assertEq(harness.parseCommon(encoded, parameter, values), 338);
    }

    function testRejectsV2Magic() external {
        bytes memory encoded = _header(values);
        bytes8 oldMagic = bytes8("PQTCPA02");
        assembly ("memory-safe") { mstore(add(encoded, 0x20), oldMagic) }
        vm.expectRevert(PQTCProofCodec.InvalidMagic.selector);
        harness.parseCommon(encoded, parameter, values);
    }

    function testRejectsV2Version() external {
        bytes memory encoded = _header(values);
        encoded[8] = bytes1(uint8(0));
        encoded[9] = bytes1(uint8(2));
        vm.expectRevert(PQTCProofCodec.UnsupportedVersion.selector);
        harness.parseCommon(encoded, parameter, values);
    }

    function testRejectsV2ProfileTag() external {
        bytes memory encoded = _header(values);
        encoded[10] = bytes1(uint8(2));
        vm.expectRevert(PQTCProofCodec.UnsupportedProfile.selector);
        harness.parseCommon(encoded, parameter, values);
    }

    function testRejectsV2QueryCount() external {
        bytes memory encoded = _header(values);
        encoded[14] = bytes1(uint8(0));
        encoded[15] = bytes1(uint8(48));
        vm.expectRevert(PQTCProofCodec.InvalidShape.selector);
        harness.parseCommon(encoded, parameter, values);
    }

    function testV3EndMarkerIsStrict() external view {
        harness.requirePartAEnd(hex"50414533");
    }

    function testRejectsV2EndMarker() external {
        vm.expectRevert(PQTCProofCodec.InvalidEndMarker.selector);
        harness.requirePartAEnd(hex"50414532");
    }

    function testRejectsNonCanonicalPublicField() external {
        uint32[64] memory malformed = values;
        malformed[7] = 2_013_265_921;
        bytes memory encoded = _header(malformed);
        vm.expectRevert(abi.encodeWithSelector(CanonicalCodec.NonCanonicalField.selector, uint32(2_013_265_921)));
        harness.parseCommon(encoded, parameter, malformed);
    }

    function testStatementKeyUsesStandardAbiEncoding() external view {
        bytes32 expected = keccak256(abi.encode(bytes32("PQTC.V3.STATEMENT"), parameter.left, parameter.right, values));
        assertEq(harness.statementKey(parameter, values), expected);
    }

    function testDeduplicatedPrunedProofAcceptsRepeatedIndex() external view {
        Digest512 memory leaf = Digest512(bytes32(uint256(11)), bytes32(uint256(12)));
        Digest512 memory sibling0 = Digest512(bytes32(uint256(21)), bytes32(uint256(22)));
        Digest512 memory sibling1 = Digest512(bytes32(uint256(31)), bytes32(uint256(32)));
        Digest512 memory parent = harness.node(leaf, sibling0);
        Digest512 memory root = harness.node(parent, sibling1);
        bytes memory frontier =
            abi.encodePacked(uint32(2), sibling0.left, sibling0.right, sibling1.left, sibling1.right);
        assertEq(harness.verifyRepeatedLeaf(root, 0, leaf, frontier, 2, 16), frontier.length);
    }

    function testPrunedProofRejectsMalformedFrontier() external {
        Digest512 memory leaf = Digest512(bytes32(uint256(11)), bytes32(uint256(12)));
        Digest512 memory root = leaf;
        bytes memory frontier = abi.encodePacked(uint32(0));
        vm.expectRevert(MmcsVerifier.InvalidMultiproof.selector);
        harness.verifyRepeatedLeaf(root, 0, leaf, frontier, 2, 16);
    }

    function testPrunedProofRejectsLeafCountAboveHalf() external {
        Digest512 memory leaf = Digest512(bytes32(uint256(11)), bytes32(uint256(12)));
        vm.expectRevert(MmcsVerifier.InvalidMultiproof.selector);
        harness.verifyRepeatedLeaf(leaf, 0, leaf, hex"", 1, 17);
    }

    function testReverseBitsUsesOnlyRequestedWidth() external view {
        assertEq(harness.reverseBits(0x0d, 4), 0x0b);
        assertEq(harness.reverseBits(0x10d, 4), 0x0b);
    }

    function _header(uint32[64] memory publicValues) private view returns (bytes memory out) {
        out = abi.encodePacked(
            bytes8("PQTCPA03"),
            uint16(3),
            uint8(3),
            uint8(9),
            uint8(9),
            uint8(4),
            uint16(32),
            parameter.left,
            parameter.right,
            uint16(64)
        );
        for (uint256 i; i < 64; ++i) {
            out = bytes.concat(out, bytes4(publicValues[i]));
        }
    }
}
