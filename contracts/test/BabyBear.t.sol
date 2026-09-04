// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {BabyBear} from "../src/libraries/BabyBear.sol";
import {BabyBearExt4, BabyBearExt4Value} from "../src/libraries/BabyBearExt4.sol";

contract BabyBearHarness {
    function add(uint256 a, uint256 b) external pure returns (uint256) {
        return BabyBear.add(a, b);
    }

    function sub(uint256 a, uint256 b) external pure returns (uint256) {
        return BabyBear.sub(a, b);
    }

    function mul(uint256 a, uint256 b) external pure returns (uint256) {
        return BabyBear.mul(a, b);
    }

    function extMul(BabyBearExt4Value calldata a, BabyBearExt4Value calldata b)
        external
        pure
        returns (BabyBearExt4Value memory)
    {
        return BabyBearExt4.mul(a, b);
    }
}

contract BabyBearTest is Test {
    uint256 private constant P = 2_013_265_921;
    BabyBearHarness private harness;

    function setUp() external {
        harness = new BabyBearHarness();
    }

    function testBoundaryArithmetic() external view {
        assertEq(harness.add(P - 1, P - 1), P - 2);
        assertEq(harness.sub(0, 1), P - 1);
        assertEq(harness.mul(P - 1, P - 1), 1);
    }

    function testExtMultiplicationReducesX4ToEleven() external view {
        BabyBearExt4Value memory x3 = BabyBearExt4Value(0, 0, 0, 1);
        BabyBearExt4Value memory x = BabyBearExt4Value(0, 1, 0, 0);
        BabyBearExt4Value memory result = harness.extMul(x3, x);
        assertEq(result.c0, 11);
        assertEq(result.c1, 0);
        assertEq(result.c2, 0);
        assertEq(result.c3, 0);
    }

    function testGasBaseFieldOperations() external {
        uint256 beforeGas = gasleft();
        harness.add(1_234_567, 7_654_321);
        harness.mul(1_234_567, 7_654_321);
        emit log_named_uint("base field add+mul gas", beforeGas - gasleft());
    }
}
