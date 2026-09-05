// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {CanonicalCodec} from "./CanonicalCodec.sol";
import {Binding512} from "./Binding512.sol";
import {Digest512} from "./Digest512.sol";

/// Strict reader for the PQTC v0.3 two-part proof framing.
library PQTCProofCodec {
    uint64 internal constant PART_A_MAGIC = 0x5051544350413034; // PQTCPA04
    uint64 internal constant PART_B_MAGIC = 0x5051544350423034; // PQTCPB04
    uint16 internal constant VERSION = 4;
    uint8 internal constant PROFILE_SEPOLIA_V03 = 3;
    uint8 internal constant PROOF_DEGREE_BITS = 9;
    uint8 internal constant BASE_DEGREE_BITS = 8;
    uint8 internal constant FRI_ROUNDS = 9;
    uint8 internal constant RANDOM_CODEWORDS = 4;
    uint16 internal constant QUERY_COUNT = 48;
    uint16 internal constant HALF_QUERY_COUNT = 24;
    uint16 internal constant PUBLIC_VALUES_COUNT = 64;
    uint32 internal constant PART_A_END = 0x50414534;
    uint32 internal constant PART_B_END = 0x50424534;
    uint32 internal constant BABY_BEAR_MODULUS = 2_013_265_921;

    struct Common {
        Digest512 parameterId;
        uint32[64] publicValues;
        uint256 cursor;
        uint16 firstQueries;
    }

    error InvalidMagic();
    error UnsupportedVersion();
    error UnsupportedProfile();
    error InvalidShape();
    error ParameterMismatch();
    error PublicValueMismatch(uint256 index);
    error InvalidEndMarker();

    function parseCommon(
        bytes calldata proof,
        uint64 expectedMagic,
        Digest512 calldata expectedParameterId,
        uint32[64] calldata expectedPublicValues
    ) internal pure returns (Common memory common) {
        uint256 cursor;
        uint64 magic;
        (magic, cursor) = CanonicalCodec.readU64(proof, cursor);
        if (magic != expectedMagic) revert InvalidMagic();
        uint16 version;
        (version, cursor) = CanonicalCodec.readU16(proof, cursor);
        if (version != VERSION) revert UnsupportedVersion();
        uint8 profile;
        (profile, cursor) = CanonicalCodec.readU8(proof, cursor);
        if (profile != PROFILE_SEPOLIA_V03) revert UnsupportedProfile();
        uint8 degreeBits;
        uint8 friRounds;
        uint8 randomCodewords;
        uint16 queries;
        (degreeBits, cursor) = CanonicalCodec.readU8(proof, cursor);
        (friRounds, cursor) = CanonicalCodec.readU8(proof, cursor);
        (randomCodewords, cursor) = CanonicalCodec.readU8(proof, cursor);
        (queries, cursor) = CanonicalCodec.readU16(proof, cursor);
        (common.firstQueries, cursor) = CanonicalCodec.readU16(proof, cursor);
        if (common.firstQueries != 22 && common.firstQueries != 24 && common.firstQueries != 26) revert InvalidShape();
        if (
            degreeBits != PROOF_DEGREE_BITS || degreeBits - 1 != BASE_DEGREE_BITS || friRounds != FRI_ROUNDS
                || randomCodewords != RANDOM_CODEWORDS || queries != QUERY_COUNT
        ) revert InvalidShape();
        (common.parameterId, cursor) = CanonicalCodec.readDigest(proof, cursor);
        if (
            common.parameterId.left != expectedParameterId.left || common.parameterId.right != expectedParameterId.right
        ) revert ParameterMismatch();
        uint16 publicCount;
        (publicCount, cursor) = CanonicalCodec.readU16(proof, cursor);
        if (publicCount != PUBLIC_VALUES_COUNT) revert InvalidShape();
        for (uint256 i; i < PUBLIC_VALUES_COUNT; ++i) {
            (common.publicValues[i], cursor) = CanonicalCodec.readField(proof, cursor);
            if (expectedPublicValues[i] >= BABY_BEAR_MODULUS) {
                revert CanonicalCodec.NonCanonicalField(expectedPublicValues[i]);
            }
            if (common.publicValues[i] != expectedPublicValues[i]) revert PublicValueMismatch(i);
        }
        common.cursor = cursor;
    }

    function statementKey(Digest512 calldata parameterId, uint32[64] calldata publicValues)
        internal
        pure
        returns (Digest512 memory)
    {
        for (uint256 i; i < PUBLIC_VALUES_COUNT; ++i) {
            if (publicValues[i] >= BABY_BEAR_MODULUS) revert CanonicalCodec.NonCanonicalField(publicValues[i]);
        }
        return Binding512.hash(abi.encode(bytes32("PQTC.R2.V4.STATEMENT"), parameterId.left, parameterId.right, publicValues));
    }

    function requireHalfHeader(bytes calldata proof, uint256 cursor, uint16 expectedStart, uint16 expectedCount)
        internal
        pure
        returns (uint256 next)
    {
        uint16 start;
        uint16 count;
        (start, cursor) = CanonicalCodec.readU16(proof, cursor);
        (count, next) = CanonicalCodec.readU16(proof, cursor);
        if (start != expectedStart || count != expectedCount) revert InvalidShape();
    }

    function requireEnd(bytes calldata proof, uint256 cursor, uint32 expectedMarker) internal pure {
        uint32 marker;
        (marker, cursor) = CanonicalCodec.readU32(proof, cursor);
        if (marker != expectedMarker) revert InvalidEndMarker();
        CanonicalCodec.requireEnd(proof, cursor);
    }
}
