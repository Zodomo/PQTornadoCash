// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBear} from "../libraries/BabyBear.sol";
import {BabyBearExt4, BabyBearExt4Value} from "../libraries/BabyBearExt4.sol";

library FriVerifier {
    uint256 private constant TWO_ADIC_BASE = 0x1a427a41;
    uint256 private constant TWO_ADICITY = 27;
    uint256 private constant INVERSE_TWO = 1_006_632_961;

    error InvalidLogHeight();

    /// Plonky3 binary two-adic fold. `logHeight` is the height after this fold.
    function foldBinary(
        uint256 index,
        uint256 logHeight,
        BabyBearExt4Value memory beta,
        BabyBearExt4Value memory low,
        BabyBearExt4Value memory high
    ) internal pure returns (BabyBearExt4Value memory) {
        if (logHeight + 1 > TWO_ADICITY) revert InvalidLogHeight();
        uint256 generator = twoAdicGenerator(logHeight + 1);
        uint256 x = BabyBear.pow(generator, reverseBits(index, logHeight));
        uint256 inverseTwoX = BabyBear.mul(INVERSE_TWO, BabyBear.inv(x));
        BabyBearExt4Value memory evenPart = BabyBearExt4.mulBase(BabyBearExt4.add(low, high), INVERSE_TWO);
        BabyBearExt4Value memory oddPart =
            BabyBearExt4.mul(BabyBearExt4.mulBase(BabyBearExt4.sub(low, high), inverseTwoX), beta);
        return BabyBearExt4.add(evenPart, oddPart);
    }

    function twoAdicGenerator(uint256 logOrder) internal pure returns (uint256 value) {
        if (logOrder > TWO_ADICITY) revert InvalidLogHeight();
        value = TWO_ADIC_BASE;
        for (uint256 i = logOrder; i < TWO_ADICITY; i++) {
            value = BabyBear.mul(value, value);
        }
    }

    function reverseBits(uint256 value, uint256 bits) internal pure returns (uint256 reversed) {
        for (uint256 i = 0; i < bits; i++) {
            reversed = (reversed << 1) | ((value >> i) & 1);
        }
    }

    function equal(BabyBearExt4Value memory a, BabyBearExt4Value memory b) internal pure returns (bool) {
        return a.c0 == b.c0 && a.c1 == b.c1 && a.c2 == b.c2 && a.c3 == b.c3;
    }
}
