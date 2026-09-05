// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

library BabyBear {
    uint256 internal constant P = 2_013_265_921;

    error NonCanonicalField(uint256 value);
    error DivisionByZero();

    function check(uint256 value) internal pure returns (uint256) {
        if (value >= P) revert NonCanonicalField(value);
        return value;
    }

    function add(uint256 a, uint256 b) internal pure returns (uint256 c) {
        unchecked {
            c = a + b;
            if (c >= P) c -= P;
        }
    }

    function sub(uint256 a, uint256 b) internal pure returns (uint256) {
        unchecked {
            return a >= b ? a - b : a + P - b;
        }
    }

    function neg(uint256 a) internal pure returns (uint256) {
        return a == 0 ? 0 : P - a;
    }

    function mul(uint256 a, uint256 b) internal pure returns (uint256) {
        return mulmod(a, b, P);
    }

    function pow(uint256 base, uint256 exponent) internal pure returns (uint256 result) {
        result = 1;
        while (exponent != 0) {
            if (exponent & 1 != 0) result = mulmod(result, base, P);
            base = mulmod(base, base, P);
            exponent >>= 1;
        }
    }

    function inv(uint256 value) internal pure returns (uint256) {
        if (value == 0) revert DivisionByZero();
        return pow(value, P - 2);
    }
}
