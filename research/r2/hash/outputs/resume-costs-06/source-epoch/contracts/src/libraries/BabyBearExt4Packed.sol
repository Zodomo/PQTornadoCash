// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBear} from "./BabyBear.sol";

/// Degree-four BabyBear extension packed as four 32-bit little-endian lanes.
/// The unused high 128 bits must be zero. Arithmetic output is always canonical.
library BabyBearExt4Packed {
    uint256 private constant MASK = type(uint32).max;
    uint256 private constant NONRESIDUE = 11;

    error NonCanonicalExtension();

    function fromCoefficients(uint256 coefficient0, uint256 coefficient1, uint256 coefficient2, uint256 coefficient3)
        internal
        pure
        returns (uint256)
    {
        BabyBear.check(coefficient0);
        BabyBear.check(coefficient1);
        BabyBear.check(coefficient2);
        BabyBear.check(coefficient3);
        return _pack(coefficient0, coefficient1, coefficient2, coefficient3);
    }

    function check(uint256 a) internal pure returns (uint256) {
        if (a >> 128 != 0) revert NonCanonicalExtension();
        BabyBear.check(c0(a));
        BabyBear.check(c1(a));
        BabyBear.check(c2(a));
        BabyBear.check(c3(a));
        return a;
    }

    function c0(uint256 a) internal pure returns (uint256) {
        return a & MASK;
    }

    function c1(uint256 a) internal pure returns (uint256) {
        return (a >> 32) & MASK;
    }

    function c2(uint256 a) internal pure returns (uint256) {
        return (a >> 64) & MASK;
    }

    function c3(uint256 a) internal pure returns (uint256) {
        return (a >> 96) & MASK;
    }

    function fromBase(uint256 value) internal pure returns (uint256) {
        return BabyBear.check(value);
    }

    function add(uint256 a, uint256 b) internal pure returns (uint256 result) {
        assembly ("memory-safe") {
            let p := 2013265921
            let mask := 0xffffffff
            let r0 := addmod(and(a, mask), and(b, mask), p)
            let r1 := addmod(and(shr(32, a), mask), and(shr(32, b), mask), p)
            let r2 := addmod(and(shr(64, a), mask), and(shr(64, b), mask), p)
            let r3 := addmod(and(shr(96, a), mask), and(shr(96, b), mask), p)
            result := or(or(r0, shl(32, r1)), or(shl(64, r2), shl(96, r3)))
        }
    }

    function sub(uint256 a, uint256 b) internal pure returns (uint256 result) {
        assembly ("memory-safe") {
            let p := 2013265921
            let mask := 0xffffffff
            let r0 := addmod(and(a, mask), sub(p, and(b, mask)), p)
            let r1 := addmod(and(shr(32, a), mask), sub(p, and(shr(32, b), mask)), p)
            let r2 := addmod(and(shr(64, a), mask), sub(p, and(shr(64, b), mask)), p)
            let r3 := addmod(and(shr(96, a), mask), sub(p, and(shr(96, b), mask)), p)
            result := or(or(r0, shl(32, r1)), or(shl(64, r2), shl(96, r3)))
        }
    }

    function mulBase(uint256 a, uint256 b) internal pure returns (uint256 result) {
        assembly ("memory-safe") {
            let p := 2013265921
            let mask := 0xffffffff
            let r0 := mulmod(and(a, mask), b, p)
            let r1 := mulmod(and(shr(32, a), mask), b, p)
            let r2 := mulmod(and(shr(64, a), mask), b, p)
            let r3 := mulmod(and(shr(96, a), mask), b, p)
            result := or(or(r0, shl(32, r1)), or(shl(64, r2), shl(96, r3)))
        }
    }

    function mul(uint256 a, uint256 b) internal pure returns (uint256 result) {
        assembly ("memory-safe") {
            let p := 2013265921
            let mask := 0xffffffff
            let a0 := and(a, mask)
            let a1 := and(shr(32, a), mask)
            let a2 := and(shr(64, a), mask)
            let a3 := and(shr(96, a), mask)
            let b0 := and(b, mask)
            let b1 := and(shr(32, b), mask)
            let b2 := and(shr(64, b), mask)
            let b3 := and(shr(96, b), mask)

            let t4 := addmod(addmod(mulmod(a1, b3, p), mulmod(a2, b2, p), p), mulmod(a3, b1, p), p)
            let t5 := addmod(mulmod(a2, b3, p), mulmod(a3, b2, p), p)
            let r0 := addmod(mulmod(a0, b0, p), mulmod(11, t4, p), p)
            let r1 := addmod(addmod(mulmod(a0, b1, p), mulmod(a1, b0, p), p), mulmod(11, t5, p), p)
            let r2 :=
                addmod(
                    addmod(addmod(mulmod(a0, b2, p), mulmod(a1, b1, p), p), mulmod(a2, b0, p), p),
                    mulmod(11, mulmod(a3, b3, p), p),
                    p
                )
            let r3 :=
                addmod(
                    addmod(addmod(mulmod(a0, b3, p), mulmod(a1, b2, p), p), mulmod(a2, b1, p), p),
                    mulmod(a3, b0, p),
                    p
                )
            result := or(or(r0, shl(32, r1)), or(shl(64, r2), shl(96, r3)))
        }
    }

    function pow(uint256 base, uint256 exponent) internal pure returns (uint256 result) {
        result = 1;
        while (exponent != 0) {
            if (exponent & 1 != 0) result = mul(result, base);
            base = mul(base, base);
            exponent >>= 1;
        }
    }

    function _pack(uint256 a0, uint256 a1, uint256 a2, uint256 a3) private pure returns (uint256) {
        return a0 | (a1 << 32) | (a2 << 64) | (a3 << 96);
    }

    function inv(uint256 value) internal pure returns (uint256) {
        check(value);
        if (value == 0) revert BabyBear.DivisionByZero();
        return pow(value, 16_428_751_811_598_850_197_311_699_254_593_454_079);
    }
}
