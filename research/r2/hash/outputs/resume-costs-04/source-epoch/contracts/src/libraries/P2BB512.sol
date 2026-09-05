// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Digest512} from "./Digest512.sol";

/// @notice P2BB512-v1: the pinned Plonky3 BabyBear Poseidon2 permutation and
/// a width-16, rate-4 application sponge.
library P2BB512 {
    uint256 internal constant P = 2_013_265_921;
    uint256 internal constant VERSION = 1;
    uint8 internal constant MERKLE_NODE_DOMAIN = 0x20;

    error NonCanonicalFieldElement(uint256 index, uint256 value);
    error NonCanonicalDigestLimb(uint256 index, uint256 value);

    // Plonky3 0.6.0, commit 3152b14a89067c83775a8076cc262ffc48a1fd7c.
    // Each word contains eight consecutive, big-endian u32 round constants.
    uint256 private constant EXTERNAL_0A = 0x69cbb6af46ad93f960a00f4e6b1297cd23189afe732e7bef72c246de2c941900;
    uint256 private constant EXTERNAL_0B = 0x0557eede1580496f3a3ea77b54f3f2710f49b02947872fe1221e2e361ab7202e;
    uint256 private constant EXTERNAL_1A = 0x487779a63851c9d838dc17c0209f8849268dcee8350c48da5b9ad32e0523272b;
    uint256 private constant EXTERNAL_1B = 0x3f89055b01e894b213ddedde1b2ef3347507d8b46ceeb94e52eb6ba250642905;
    uint256 private constant EXTERNAL_2A = 0x05453f3f06349efc6922787c04bfff9c768c714a3e9ff21a15737c9c2229c807;
    uint256 private constant EXTERNAL_2B = 0x0d47f88c097e0ecc27eadba02d7d29e43502aaa00f475fd729fbda49018afffd;
    uint256 private constant EXTERNAL_3A = 0x0315b6186d4497d11b171d9e52861abd2e5d05013ec8646c6e5f250a148ae8e6;
    uint256 private constant EXTERNAL_3B = 0x17f5fa4a3e66d2840051aa3b483f79132cfe5f15023427ca2cc783151e36ea47;
    uint256 private constant EXTERNAL_4A = 0x7290a80d6f7e5329598ec8a876a859a06559e868657b83af13271d3f1f876063;
    uint256 private constant EXTERNAL_4B = 0x0aeeae37706e9ca646400cee72a05c262c589c9e20bd37a76a2d3d1020523767;
    uint256 private constant EXTERNAL_5A = 0x5b8fe9c42aa501d61e01ac3e1448bc545ce5ad1c4918a14d2c46a83f4fcf6876;
    uint256 private constant EXTERNAL_5B = 0x61d8d5c86ddf4ff911fda4d302933a8f170eaf815a9c314f49a1259035ec52a1;
    uint256 private constant EXTERNAL_6A = 0x58eb16115e481e65367125c90eba33ba1fc28ded066399ad0cbec0ea75fd1af0;
    uint256 private constant EXTERNAL_6B = 0x50f5bf4e643d5f416f4fe7185b3cbbde1e3afb3e296fb02745e1547b4a8db2ab;
    uint256 private constant EXTERNAL_7A = 0x59986d1930bcdfa31db639321d7c282453b336810673b747038a98a32c5bce60;
    uint256 private constant EXTERNAL_7B = 0x351979cd5008fb73547bca78711af4813f93bf64644d987b3c8bcd87608758b8;

    uint256 private constant INTERNAL_A = 0x5a8053c0693be6393858867d19334f6b128f0fd84e2b1ccb61210ce03c318939;
    uint256 private constant INTERNAL_B = 0x0b5b2f222edb11d5213effdf0cac4606241af16d000000000000000000000000;

    /// @notice Applies default_babybear_poseidon2_16() to one canonical state.
    function permute(uint32[16] memory state) internal pure returns (uint32[16] memory result) {
        uint256[16] memory wide;
        for (uint256 i = 0; i < 16; ++i) {
            if (state[i] >= P) revert NonCanonicalFieldElement(i, state[i]);
            wide[i] = state[i];
        }
        _permute(wide);
        for (uint256 i = 0; i < 16; ++i) {
            result[i] = uint32(wide[i]);
        }
    }

    /// @notice Decodes sixteen big-endian u32 limbs and rejects noncanonical limbs.
    function toFields(Digest512 memory digest) internal pure returns (uint32[16] memory fields) {
        uint256 left = uint256(digest.left);
        uint256 right = uint256(digest.right);
        for (uint256 i = 0; i < 8; ++i) {
            uint32 value = uint32(left >> (224 - 32 * i));
            if (value >= P) revert NonCanonicalDigestLimb(i, value);
            fields[i] = value;
        }
        for (uint256 i = 0; i < 8; ++i) {
            uint32 value = uint32(right >> (224 - 32 * i));
            if (value >= P) revert NonCanonicalDigestLimb(i + 8, value);
            fields[i + 8] = value;
        }
    }

    /// @notice Encodes sixteen canonical BabyBear elements as big-endian u32 limbs.
    function fromFields(uint32[16] memory fields) internal pure returns (Digest512 memory digest) {
        uint256 left;
        uint256 right;
        for (uint256 i = 0; i < 8; ++i) {
            if (fields[i] >= P) revert NonCanonicalFieldElement(i, fields[i]);
            left |= uint256(fields[i]) << (224 - 32 * i);
        }
        for (uint256 i = 0; i < 8; ++i) {
            if (fields[i + 8] >= P) revert NonCanonicalFieldElement(i + 8, fields[i + 8]);
            right |= uint256(fields[i + 8]) << (224 - 32 * i);
        }
        digest = Digest512(bytes32(left), bytes32(right));
    }

    function hashEmpty(uint8 domainTag) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 0, 0, 0);
        _absorb(state, 0, 0, 0, 0);
        return _squeeze(state);
    }

    function hashFields16(uint8 domainTag, uint32[16] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 64, 16, 0);
        for (uint256 blockIndex = 0; blockIndex < 4; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _check4(elements, offset);
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashFields32(uint8 domainTag, uint32[32] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 128, 32, 0);
        for (uint256 blockIndex = 0; blockIndex < 8; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _check4(elements, offset);
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashFields48(uint8 domainTag, uint32[48] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 192, 48, 0);
        for (uint256 blockIndex = 0; blockIndex < 12; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _check4(elements, offset);
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashFields64(uint8 domainTag, uint32[64] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 256, 64, 0);
        for (uint256 blockIndex = 0; blockIndex < 16; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _check4(elements, offset);
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashU16s16(uint8 domainTag, uint16[16] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 32, 16, 0);
        for (uint256 blockIndex = 0; blockIndex < 4; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashU16s32(uint8 domainTag, uint16[32] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 64, 32, 0);
        for (uint256 blockIndex = 0; blockIndex < 8; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    function hashU16s36(uint8 domainTag, uint16[36] memory elements) internal pure returns (Digest512 memory) {
        uint256[16] memory state = _initialState(domainTag, 72, 36, 0);
        for (uint256 blockIndex = 0; blockIndex < 9; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        return _squeeze(state);
    }

    /// @dev The 65th u16 stores an odd final byte in its high byte; its low byte must be zero.
    function hashU16s65Odd(uint8 domainTag, uint16[65] memory elements) internal pure returns (Digest512 memory) {
        if (elements[64] & 0xff != 0) revert NonCanonicalFieldElement(64, elements[64]);
        uint256[16] memory state = _initialState(domainTag, 129, 65, 0);
        for (uint256 blockIndex = 0; blockIndex < 16; ++blockIndex) {
            uint256 offset = blockIndex * 4;
            _absorb(state, elements[offset], elements[offset + 1], elements[offset + 2], elements[offset + 3]);
        }
        _absorb(state, elements[64], 0, 0, 0);
        return _squeeze(state);
    }

    /// @notice Hashes left || right with the tree level bound in capacity aux.
    function merkleNode(uint8 level, Digest512 memory left, Digest512 memory right)
        internal
        pure
        returns (Digest512 memory)
    {
        uint256[16] memory state = _initialState(MERKLE_NODE_DOMAIN, 128, 32, level);
        _absorbDigest(state, left);
        _absorbDigest(state, right);
        return _squeeze(state);
    }

    function _initialState(uint8 domainTag, uint256 payloadByteLength, uint256 payloadElementCount, uint256 aux)
        private
        pure
        returns (uint256[16] memory state)
    {
        state[4] = VERSION;
        state[5] = domainTag;
        state[6] = payloadByteLength;
        state[7] = payloadElementCount;
        state[8] = aux;
    }

    function _absorb(uint256[16] memory state, uint256 a, uint256 b, uint256 c, uint256 d) private pure {
        state[0] = addmod(state[0], a, P);
        state[1] = addmod(state[1], b, P);
        state[2] = addmod(state[2], c, P);
        state[3] = addmod(state[3], d, P);
        _permute(state);
    }

    function _absorbDigest(uint256[16] memory state, Digest512 memory digest) private pure {
        _absorbPacked128(state, uint256(digest.left) >> 128, 0);
        _absorbPacked128(state, uint128(uint256(digest.left)), 4);
        _absorbPacked128(state, uint256(digest.right) >> 128, 8);
        _absorbPacked128(state, uint128(uint256(digest.right)), 12);
    }

    function _absorbPacked128(uint256[16] memory state, uint256 packed, uint256 index) private pure {
        uint256 a = uint32(packed >> 96);
        uint256 b = uint32(packed >> 64);
        uint256 c = uint32(packed >> 32);
        uint256 d = uint32(packed);
        if (a >= P) revert NonCanonicalDigestLimb(index, a);
        if (b >= P) revert NonCanonicalDigestLimb(index + 1, b);
        if (c >= P) revert NonCanonicalDigestLimb(index + 2, c);
        if (d >= P) revert NonCanonicalDigestLimb(index + 3, d);
        _absorb(state, a, b, c, d);
    }

    function _squeeze(uint256[16] memory state) private pure returns (Digest512 memory digest) {
        uint256 left = _rateWord(state) << 128;
        _permute(state);
        left |= _rateWord(state);
        _permute(state);
        uint256 right = _rateWord(state) << 128;
        _permute(state);
        right |= _rateWord(state);
        digest = Digest512(bytes32(left), bytes32(right));
    }

    function _rateWord(uint256[16] memory state) private pure returns (uint256 word) {
        assembly ("memory-safe") {
            word := or(
                or(shl(96, mload(state)), shl(64, mload(add(state, 32)))),
                or(shl(32, mload(add(state, 64))), mload(add(state, 96)))
            )
        }
    }

    function _permute(uint256[16] memory state) private pure {
        assembly ("memory-safe") {
            function sbox(x) -> y {
                let square := mulmod(x, x, 2013265921)
                let fourth := mulmod(square, square, 2013265921)
                y := mulmod(mulmod(fourth, square, 2013265921), x, 2013265921)
            }

            function externalLinear(s) {
                for { let offset := 0 } lt(offset, 512) { offset := add(offset, 128) } {
                    let x0 := mload(add(s, offset))
                    let x1 := mload(add(add(s, offset), 32))
                    let x2 := mload(add(add(s, offset), 64))
                    let x3 := mload(add(add(s, offset), 96))
                    // Every input is below P, so these unreduced sums are below 7P
                    // and cannot overflow a word. Reducing only the four outputs is
                    // equivalent to the M4 transform but avoids intermediate ADDMODs.
                    let total := add(add(x0, x1), add(x2, x3))
                    mstore(add(s, offset), mod(add(add(total, x0), add(x1, x1)), 2013265921))
                    mstore(add(add(s, offset), 32), mod(add(add(total, x1), add(x2, x2)), 2013265921))
                    mstore(add(add(s, offset), 64), mod(add(add(total, x2), add(x3, x3)), 2013265921))
                    mstore(add(add(s, offset), 96), mod(add(add(total, x3), add(x0, x0)), 2013265921))
                }

                // Four canonical terms sum to less than 4P.
                let sum0 :=
                    mod(add(add(mload(s), mload(add(s, 128))), add(mload(add(s, 256)), mload(add(s, 384)))), 2013265921)
                let sum1 :=
                    mod(
                        add(add(mload(add(s, 32)), mload(add(s, 160))), add(mload(add(s, 288)), mload(add(s, 416)))),
                        2013265921
                    )
                let sum2 :=
                    mod(
                        add(add(mload(add(s, 64)), mload(add(s, 192))), add(mload(add(s, 320)), mload(add(s, 448)))),
                        2013265921
                    )
                let sum3 :=
                    mod(
                        add(add(mload(add(s, 96)), mload(add(s, 224))), add(mload(add(s, 352)), mload(add(s, 480)))),
                        2013265921
                    )
                for { let offset := 0 } lt(offset, 512) { offset := add(offset, 128) } {
                    mstore(add(s, offset), addmod(mload(add(s, offset)), sum0, 2013265921))
                    mstore(add(add(s, offset), 32), addmod(mload(add(add(s, offset), 32)), sum1, 2013265921))
                    mstore(add(add(s, offset), 64), addmod(mload(add(add(s, offset), 64)), sum2, 2013265921))
                    mstore(add(add(s, offset), 96), addmod(mload(add(add(s, offset), 96)), sum3, 2013265921))
                }
            }

            function externalRound(s, first, second) {
                for { let i := 0 } lt(i, 8) { i := add(i, 1) } {
                    let shift := sub(224, mul(i, 32))
                    let offset := mul(i, 32)
                    mstore(
                        add(s, offset),
                        sbox(addmod(mload(add(s, offset)), and(shr(shift, first), 0xffffffff), 2013265921))
                    )
                    offset := add(offset, 256)
                    mstore(
                        add(s, offset),
                        sbox(addmod(mload(add(s, offset)), and(shr(shift, second), 0xffffffff), 2013265921))
                    )
                }
                externalLinear(s)
            }

            function internalLinear(s) {
                let partSum := 0
                for { let offset := 32 } lt(offset, 512) { offset := add(offset, 32) } {
                    partSum := add(partSum, mload(add(s, offset)))
                }
                // Fifteen canonical terms sum to less than 15P.
                partSum := mod(partSum, 2013265921)
                let x0 := mload(s)
                let sum := mod(add(partSum, x0), 2013265921)
                mstore(s, mod(add(partSum, sub(2013265921, x0)), 2013265921))
                mstore(add(s, 32), mod(add(sum, mload(add(s, 32))), 2013265921))
                mstore(add(s, 64), mod(add(add(sum, mload(add(s, 64))), mload(add(s, 64))), 2013265921))
                // Each product below is less than P^2, and adding sum remains
                // below 2^62, so ordinary multiplication cannot overflow.
                mstore(add(s, 96), mod(add(sum, mul(mload(add(s, 96)), 1006632961)), 2013265921))
                mstore(add(s, 128), mod(add(sum, mul(mload(add(s, 128)), 3)), 2013265921))
                mstore(add(s, 160), mod(add(sum, mul(mload(add(s, 160)), 4)), 2013265921))
                mstore(add(s, 192), mod(add(sum, mul(mload(add(s, 192)), 1006632960)), 2013265921))
                mstore(add(s, 224), mod(add(sum, mul(mload(add(s, 224)), 2013265918)), 2013265921))
                mstore(add(s, 256), mod(add(sum, mul(mload(add(s, 256)), 2013265917)), 2013265921))
                mstore(add(s, 288), mod(add(sum, mul(mload(add(s, 288)), 2005401601)), 2013265921))
                mstore(add(s, 320), mod(add(sum, mul(mload(add(s, 320)), 1509949441)), 2013265921))
                mstore(add(s, 352), mod(add(sum, mul(mload(add(s, 352)), 1761607681)), 2013265921))
                mstore(add(s, 384), mod(add(sum, mul(mload(add(s, 384)), 2013265906)), 2013265921))
                mstore(add(s, 416), mod(add(sum, mul(mload(add(s, 416)), 7864320)), 2013265921))
                mstore(add(s, 448), mod(add(sum, mul(mload(add(s, 448)), 125829120)), 2013265921))
                mstore(add(s, 480), mod(add(sum, mul(mload(add(s, 480)), 15)), 2013265921))
            }

            externalLinear(state)
            externalRound(
                state,
                0x69cbb6af46ad93f960a00f4e6b1297cd23189afe732e7bef72c246de2c941900,
                0x0557eede1580496f3a3ea77b54f3f2710f49b02947872fe1221e2e361ab7202e
            )
            externalRound(
                state,
                0x487779a63851c9d838dc17c0209f8849268dcee8350c48da5b9ad32e0523272b,
                0x3f89055b01e894b213ddedde1b2ef3347507d8b46ceeb94e52eb6ba250642905
            )
            externalRound(
                state,
                0x05453f3f06349efc6922787c04bfff9c768c714a3e9ff21a15737c9c2229c807,
                0x0d47f88c097e0ecc27eadba02d7d29e43502aaa00f475fd729fbda49018afffd
            )
            externalRound(
                state,
                0x0315b6186d4497d11b171d9e52861abd2e5d05013ec8646c6e5f250a148ae8e6,
                0x17f5fa4a3e66d2840051aa3b483f79132cfe5f15023427ca2cc783151e36ea47
            )

            for { let round := 0 } lt(round, 13) { round := add(round, 1) } {
                let constantValue
                switch lt(round, 8)
                case 1 {
                    constantValue := and(
                        shr(
                            sub(224, mul(round, 32)),
                            0x5a8053c0693be6393858867d19334f6b128f0fd84e2b1ccb61210ce03c318939
                        ),
                        0xffffffff
                    )
                }
                default {
                    constantValue := and(
                        shr(
                            sub(224, mul(sub(round, 8), 32)),
                            0x0b5b2f222edb11d5213effdf0cac4606241af16d000000000000000000000000
                        ),
                        0xffffffff
                    )
                }
                mstore(state, sbox(addmod(mload(state), constantValue, 2013265921)))
                internalLinear(state)
            }

            externalRound(
                state,
                0x7290a80d6f7e5329598ec8a876a859a06559e868657b83af13271d3f1f876063,
                0x0aeeae37706e9ca646400cee72a05c262c589c9e20bd37a76a2d3d1020523767
            )
            externalRound(
                state,
                0x5b8fe9c42aa501d61e01ac3e1448bc545ce5ad1c4918a14d2c46a83f4fcf6876,
                0x61d8d5c86ddf4ff911fda4d302933a8f170eaf815a9c314f49a1259035ec52a1
            )
            externalRound(
                state,
                0x58eb16115e481e65367125c90eba33ba1fc28ded066399ad0cbec0ea75fd1af0,
                0x50f5bf4e643d5f416f4fe7185b3cbbde1e3afb3e296fb02745e1547b4a8db2ab
            )
            externalRound(
                state,
                0x59986d1930bcdfa31db639321d7c282453b336810673b747038a98a32c5bce60,
                0x351979cd5008fb73547bca78711af4813f93bf64644d987b3c8bcd87608758b8
            )
        }
    }

    function _check4(uint32[16] memory elements, uint256 offset) private pure {
        for (uint256 i = 0; i < 4; ++i) {
            uint256 value = elements[offset + i];
            if (value >= P) revert NonCanonicalFieldElement(offset + i, value);
        }
    }

    function _check4(uint32[32] memory elements, uint256 offset) private pure {
        for (uint256 i = 0; i < 4; ++i) {
            uint256 value = elements[offset + i];
            if (value >= P) revert NonCanonicalFieldElement(offset + i, value);
        }
    }

    function _check4(uint32[48] memory elements, uint256 offset) private pure {
        for (uint256 i = 0; i < 4; ++i) {
            uint256 value = elements[offset + i];
            if (value >= P) revert NonCanonicalFieldElement(offset + i, value);
        }
    }

    function _check4(uint32[64] memory elements, uint256 offset) private pure {
        for (uint256 i = 0; i < 4; ++i) {
            uint256 value = elements[offset + i];
            if (value >= P) revert NonCanonicalFieldElement(offset + i, value);
        }
    }
}
