// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {PQTCDomains} from "../PQTCDomains.sol";
import {Digest512} from "./Digest512.sol";
import {P2BB512} from "./P2BB512.sol";

/// @notice Canonical P2BB512-v1 application hashes.
/// Digests and note preimages are decoded as canonical big-endian u32
/// BabyBear elements; ordinary byte strings are absorbed as big-endian u16s.
library PQTCApplicationHash {
    uint32 private constant BABY_BEAR_MODULUS = 2_013_265_921;
    uint32 private constant P2BB512_VERSION = 1;

    error NonCanonicalNotePreimageLimb(uint256 index, uint256 value);

    function scope(
        uint64 chainId,
        address pool,
        uint256 denomination,
        uint8 treeDepth,
        uint32 protocolVersion,
        Digest512 memory parameterId
    ) internal pure returns (Digest512 memory) {
        // parameterId is a proof-system identifier, not an application field
        // digest, so scope binds its 64 raw bytes as u16 chunks.
        bytes memory payload = abi.encodePacked(
            chainId, pool, denomination, treeDepth, protocolVersion, parameterId.left, parameterId.right
        );
        uint16[65] memory elements;
        for (uint256 i = 0; i < 65; ++i) {
            uint256 byteIndex = i * 2;
            elements[i] = uint16(uint8(payload[byteIndex])) << 8;
            if (byteIndex + 1 < payload.length) elements[i] |= uint16(uint8(payload[byteIndex + 1]));
        }
        return P2BB512.hashU16s65Odd(PQTCDomains.SCOPE, elements);
    }

    function commitment(Digest512 memory poolScope, bytes32 nullifierSecret, bytes32 trapdoor)
        internal
        pure
        returns (Digest512 memory)
    {
        uint32[32] memory elements;
        uint32[16] memory scopeFields = P2BB512.toFields(poolScope);
        for (uint256 i = 0; i < 16; ++i) {
            elements[i] = scopeFields[i];
        }
        for (uint256 i = 0; i < 8; ++i) {
            elements[i + 16] = _notePreimageLimb(nullifierSecret, i, i);
            elements[i + 24] = _notePreimageLimb(trapdoor, i, i + 8);
        }
        return _hashFields32(PQTCDomains.NOTE, 128, elements);
    }

    function nullifierHash(Digest512 memory poolScope, bytes32 nullifierSecret)
        internal
        pure
        returns (Digest512 memory)
    {
        uint32[24] memory elements;
        uint32[16] memory scopeFields = P2BB512.toFields(poolScope);
        for (uint256 i = 0; i < 16; ++i) {
            elements[i] = scopeFields[i];
        }
        for (uint256 i = 0; i < 8; ++i) {
            elements[i + 16] = _notePreimageLimb(nullifierSecret, i, i);
        }
        return _hashFields24(PQTCDomains.NULLIFIER, 96, elements);
    }

    function emptyLeaf(Digest512 memory poolScope) internal pure returns (Digest512 memory) {
        return P2BB512.hashFields16(PQTCDomains.EMPTY_LEAF, P2BB512.toFields(poolScope));
    }

    function merkleNode(uint8 level, Digest512 memory left, Digest512 memory right)
        internal
        pure
        returns (Digest512 memory)
    {
        return P2BB512.merkleNode(level, left, right);
    }

    function payoutDigest(address recipient, address relayer, uint256 fee) internal pure returns (Digest512 memory) {
        uint16[36] memory elements;
        uint160 recipientBits = uint160(recipient);
        uint160 relayerBits = uint160(relayer);
        for (uint256 i = 0; i < 10; ++i) {
            elements[i] = uint16(recipientBits >> (144 - 16 * i));
            elements[i + 10] = uint16(relayerBits >> (144 - 16 * i));
        }
        for (uint256 i = 0; i < 16; ++i) {
            elements[i + 20] = uint16(fee >> (240 - 16 * i));
        }
        return P2BB512.hashU16s36(PQTCDomains.PAYOUT, elements);
    }

    function statementHash(
        Digest512 memory poolScope,
        Digest512 memory root,
        Digest512 memory nullifier,
        Digest512 memory payout
    ) internal pure returns (Digest512 memory) {
        uint32[64] memory elements;
        Digest512[4] memory digests;
        digests[0] = poolScope;
        digests[1] = root;
        digests[2] = nullifier;
        digests[3] = payout;
        for (uint256 digestIndex = 0; digestIndex < 4; ++digestIndex) {
            uint32[16] memory fields = P2BB512.toFields(digests[digestIndex]);
            for (uint256 limb = 0; limb < 16; ++limb) {
                elements[digestIndex * 16 + limb] = fields[limb];
            }
        }
        return P2BB512.hashFields64(PQTCDomains.STATEMENT, elements);
    }

    // NOTE and NULLIFIER absorb canonical u32 fields throughout. Their byte
    // lengths bind the original 64-byte scope and 32-byte preimage values.
    function _hashFields24(uint8 domainTag, uint32 payloadByteLength, uint32[24] memory elements)
        private
        pure
        returns (Digest512 memory)
    {
        uint32[16] memory state = _initialState(domainTag, payloadByteLength, 24);
        for (uint256 offset = 0; offset < 24; offset += 4) {
            state = _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function _hashFields32(uint8 domainTag, uint32 payloadByteLength, uint32[32] memory elements)
        private
        pure
        returns (Digest512 memory)
    {
        uint32[16] memory state = _initialState(domainTag, payloadByteLength, 32);
        for (uint256 offset = 0; offset < 32; offset += 4) {
            state = _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function _notePreimageLimb(bytes32 encoded, uint256 wordIndex, uint256 preimageIndex)
        private
        pure
        returns (uint32 value)
    {
        value = uint32(uint256(encoded) >> (224 - 32 * wordIndex));
        if (value >= BABY_BEAR_MODULUS) revert NonCanonicalNotePreimageLimb(preimageIndex, value);
    }

    function _initialState(uint8 domainTag, uint32 payloadByteLength, uint32 payloadElementCount)
        private
        pure
        returns (uint32[16] memory state)
    {
        state[4] = P2BB512_VERSION;
        state[5] = domainTag;
        state[6] = payloadByteLength;
        state[7] = payloadElementCount;
    }

    function _absorb(uint32[16] memory state, uint32 a, uint32 b, uint32 c, uint32 d)
        private
        pure
        returns (uint32[16] memory)
    {
        state[0] = uint32(addmod(state[0], a, BABY_BEAR_MODULUS));
        state[1] = uint32(addmod(state[1], b, BABY_BEAR_MODULUS));
        state[2] = uint32(addmod(state[2], c, BABY_BEAR_MODULUS));
        state[3] = uint32(addmod(state[3], d, BABY_BEAR_MODULUS));
        return P2BB512.permute(state);
    }

    function _squeeze(uint32[16] memory state) private pure returns (Digest512 memory) {
        uint32[16] memory output;
        for (uint256 blockIndex = 0; blockIndex < 4; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            output[offset] = state[0];
            output[offset + 1] = state[1];
            output[offset + 2] = state[2];
            output[offset + 3] = state[3];
            if (blockIndex != 3) state = P2BB512.permute(state);
        }
        return P2BB512.fromFields(output);
    }
}
