// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBear} from "./BabyBear.sol";

struct BabyBearExt4Value {
    uint256 c0;
    uint256 c1;
    uint256 c2;
    uint256 c3;
}

library BabyBearExt4 {
    uint256 internal constant NONRESIDUE = 11;

    function check(BabyBearExt4Value memory a) internal pure returns (BabyBearExt4Value memory) {
        BabyBear.check(a.c0);
        BabyBear.check(a.c1);
        BabyBear.check(a.c2);
        BabyBear.check(a.c3);
        return a;
    }

    function add(BabyBearExt4Value memory a, BabyBearExt4Value memory b)
        internal
        pure
        returns (BabyBearExt4Value memory)
    {
        return BabyBearExt4Value({
            c0: BabyBear.add(a.c0, b.c0),
            c1: BabyBear.add(a.c1, b.c1),
            c2: BabyBear.add(a.c2, b.c2),
            c3: BabyBear.add(a.c3, b.c3)
        });
    }

    function sub(BabyBearExt4Value memory a, BabyBearExt4Value memory b)
        internal
        pure
        returns (BabyBearExt4Value memory)
    {
        return BabyBearExt4Value({
            c0: BabyBear.sub(a.c0, b.c0),
            c1: BabyBear.sub(a.c1, b.c1),
            c2: BabyBear.sub(a.c2, b.c2),
            c3: BabyBear.sub(a.c3, b.c3)
        });
    }

    function mul(BabyBearExt4Value memory a, BabyBearExt4Value memory b)
        internal
        pure
        returns (BabyBearExt4Value memory r)
    {
        uint256 t0 = BabyBear.mul(a.c0, b.c0);
        uint256 t1 = BabyBear.add(BabyBear.mul(a.c0, b.c1), BabyBear.mul(a.c1, b.c0));
        uint256 t2 =
            BabyBear.add(BabyBear.add(BabyBear.mul(a.c0, b.c2), BabyBear.mul(a.c1, b.c1)), BabyBear.mul(a.c2, b.c0));
        uint256 t3 = BabyBear.add(
            BabyBear.add(BabyBear.add(BabyBear.mul(a.c0, b.c3), BabyBear.mul(a.c1, b.c2)), BabyBear.mul(a.c2, b.c1)),
            BabyBear.mul(a.c3, b.c0)
        );
        uint256 t4 =
            BabyBear.add(BabyBear.add(BabyBear.mul(a.c1, b.c3), BabyBear.mul(a.c2, b.c2)), BabyBear.mul(a.c3, b.c1));
        uint256 t5 = BabyBear.add(BabyBear.mul(a.c2, b.c3), BabyBear.mul(a.c3, b.c2));
        uint256 t6 = BabyBear.mul(a.c3, b.c3);
        r.c0 = BabyBear.add(t0, BabyBear.mul(NONRESIDUE, t4));
        r.c1 = BabyBear.add(t1, BabyBear.mul(NONRESIDUE, t5));
        r.c2 = BabyBear.add(t2, BabyBear.mul(NONRESIDUE, t6));
        r.c3 = t3;
    }

    function mulBase(BabyBearExt4Value memory a, uint256 b) internal pure returns (BabyBearExt4Value memory) {
        return BabyBearExt4Value({
            c0: BabyBear.mul(a.c0, b), c1: BabyBear.mul(a.c1, b), c2: BabyBear.mul(a.c2, b), c3: BabyBear.mul(a.c3, b)
        });
    }

    function fromBase(uint256 value) internal pure returns (BabyBearExt4Value memory) {
        return BabyBearExt4Value(BabyBear.check(value), 0, 0, 0);
    }

    function neg(BabyBearExt4Value memory a) internal pure returns (BabyBearExt4Value memory) {
        return BabyBearExt4Value(BabyBear.neg(a.c0), BabyBear.neg(a.c1), BabyBear.neg(a.c2), BabyBear.neg(a.c3));
    }

    function pow(BabyBearExt4Value memory base, uint256 exponentLow, uint256 exponentHigh)
        internal
        pure
        returns (BabyBearExt4Value memory result)
    {
        result = fromBase(1);
        while (exponentLow != 0 || exponentHigh != 0) {
            if (exponentLow & 1 != 0) result = mul(result, base);
            base = mul(base, base);
            exponentLow = (exponentLow >> 1) | (exponentHigh << 255);
            exponentHigh >>= 1;
        }
    }

    /// Inverse by exponentiation to p^4 - 2. The exponent is encoded as a
    /// little-endian 256-bit low limb and high limb.
    function inv(BabyBearExt4Value memory value) internal pure returns (BabyBearExt4Value memory) {
        check(value);
        if (value.c0 == 0 && value.c1 == 0 && value.c2 == 0 && value.c3 == 0) {
            revert BabyBear.DivisionByZero();
        }
        // (2_013_265_921^4 - 2), split into 256-bit limbs. The high limb is zero.
        return pow(value, 16_428_751_811_598_850_197_311_699_254_593_454_079, 0);
    }

    function equal(BabyBearExt4Value memory a, BabyBearExt4Value memory b) internal pure returns (bool) {
        return a.c0 == b.c0 && a.c1 == b.c1 && a.c2 == b.c2 && a.c3 == b.c3;
    }
}
