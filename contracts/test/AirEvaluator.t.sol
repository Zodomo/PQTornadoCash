// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {BabyBear} from "../src/libraries/BabyBear.sol";
import {AirEvaluatorPoseidon} from "../src/verifier/AirEvaluatorPoseidon.sol";
import {PQTCAirStageVerifier} from "../src/verifier/PQTCAirStageVerifier.sol";
import {StarkOodVerifier} from "../src/verifier/StarkOodVerifier.sol";

contract PoseidonAirHarness {
    function evaluate(
        uint256[] calldata localRaw,
        uint256[] calldata nextRaw,
        uint256[] calldata publicRaw,
        uint256 isFirst,
        uint256 isLast,
        uint256 isTransition,
        uint256 alpha
    ) external pure returns (uint256) {
        uint256[] memory local = localRaw;
        uint256[] memory next = nextRaw;
        uint256[] memory publicValues = publicRaw;
        return AirEvaluatorPoseidon.evaluate(local, next, publicValues, isFirst, isLast, isTransition, alpha);
    }

    function evaluateRange(
        uint256[] calldata localRaw,
        uint256[] calldata nextRaw,
        uint256[] calldata publicRaw,
        uint256 isFirst,
        uint256 isLast,
        uint256 isTransition,
        uint256 alpha,
        uint256 accumulator,
        uint8 start,
        uint8 end
    ) external pure returns (uint256) {
        uint256[] memory local = localRaw;
        uint256[] memory next = nextRaw;
        uint256[] memory publicValues = publicRaw;
        return AirEvaluatorPoseidon.evaluateRange(
            local, next, publicValues, isFirst, isLast, isTransition, alpha, accumulator, start, end
        );
    }
}

contract OodHarness {
    function selectors(uint256 zeta) external pure returns (uint256, uint256, uint256, uint256) {
        StarkOodVerifier.Selectors memory selected = StarkOodVerifier.selectors(zeta);
        return (selected.isFirst, selected.isLast, selected.isTransition, selected.invVanishing);
    }
}

contract AirEvaluatorTest is Test {
    PoseidonAirHarness private harness;

    function setUp() external {
        harness = new PoseidonAirHarness();
    }

    function testWithdrawalAirHasExactly190ColumnsAnd64PublicValues() external view {
        uint256[] memory local = new uint256[](190);
        uint256[] memory next = new uint256[](190);
        uint256[] memory publicValues = new uint256[](64);
        local[158] = 1; // nullifier selector; the other four row-kind selectors are zero.
        uint256 folded = harness.evaluate(local, next, publicValues, 0, 0, 0, 7);
        publicValues[0] = 1;
        uint256 mutated = harness.evaluate(local, next, publicValues, 0, 0, 0, 7);
        assertNotEq(folded, mutated, "64-field statement must be constrained by the AIR");
    }

    function testSegmentedEvaluationPreservesHornerOrder() external view {
        uint256[] memory local = new uint256[](190);
        uint256[] memory next = new uint256[](190);
        uint256[] memory publicValues = new uint256[](64);
        local[158] = 1;
        local[174] = 9;
        next[189] = 11;
        publicValues[7] = 13;
        uint256 whole = harness.evaluate(local, next, publicValues, 17, 19, 23, 29);
        uint256 first = harness.evaluateRange(local, next, publicValues, 17, 19, 23, 29, 0, 0, 3);
        uint256 second = harness.evaluateRange(local, next, publicValues, 17, 19, 23, 29, first, 3, 7);
        assertEq(second, whole);
    }

    function testRejectsLegacy230ColumnWithdrawalRows() external {
        uint256[] memory local = new uint256[](230);
        uint256[] memory next = new uint256[](230);
        uint256[] memory publicValues = new uint256[](64);
        vm.expectRevert(AirEvaluatorPoseidon.InvalidInputWidth.selector);
        harness.evaluate(local, next, publicValues, 0, 0, 0, 7);
    }

    function testRejectsLegacy128PublicValueStatement() external {
        uint256[] memory local = new uint256[](190);
        uint256[] memory next = new uint256[](190);
        uint256[] memory publicValues = new uint256[](128);
        vm.expectRevert(AirEvaluatorPoseidon.InvalidInputWidth.selector);
        harness.evaluate(local, next, publicValues, 0, 0, 0, 7);
    }

    function testAirEntryRejectsNoncanonicalOpenedField() external {
        PQTCAirStageVerifier verifier = new PQTCAirStageVerifier();
        uint256[] memory local = new uint256[](190);
        uint256[] memory next = new uint256[](190);
        uint256[] memory quotient = new uint256[](64);
        uint32[64] memory publicValues;
        local[0] = 2_013_265_921;
        vm.expectRevert(abi.encodeWithSelector(BabyBear.NonCanonicalField.selector, uint256(2_013_265_921)));
        verifier.verify(local, next, quotient, publicValues, 2, 3);
    }

    function testRustDifferentialAirVector() external view {
        string memory json = vm.readFile("test-vectors/verifier/v3.json");
        assertEq(vm.parseJsonUint(json, ".version"), 3);
        uint256[] memory local = _packedArray(json, ".air.local", 190);
        uint256[] memory next = _packedArray(json, ".air.next", 190);
        uint256[] memory publicValues = _packedArray(json, ".air.public_values", 64);
        uint256 actual = harness.evaluate(
            local,
            next,
            publicValues,
            _packed(json, ".air.is_first"),
            _packed(json, ".air.is_last"),
            _packed(json, ".air.is_transition"),
            _packed(json, ".air.alpha")
        );
        assertEq(actual, _packed(json, ".air.expected"), "Solidity AIR order differs from Rust");
    }

    function testTraceSelectorsUse256RowDomain() external {
        OodHarness ood = new OodHarness();
        (uint256 first, uint256 last, uint256 transition, uint256 inverseVanishing) = ood.selectors(2);
        assertTrue(first != 0);
        assertTrue(last != 0);
        assertTrue(transition != 0);
        assertTrue(inverseVanishing != 0);
    }

    function _packedArray(string memory json, string memory path, uint256 expectedLength)
        private
        pure
        returns (uint256[] memory packed)
    {
        uint256[][] memory coefficients = abi.decode(vm.parseJson(json, path), (uint256[][]));
        assertEq(coefficients.length, expectedLength);
        packed = new uint256[](expectedLength);
        for (uint256 i; i < expectedLength; ++i) {
            assertEq(coefficients[i].length, 4);
            packed[i] = coefficients[i][0] | (coefficients[i][1] << 32) | (coefficients[i][2] << 64)
                | (coefficients[i][3] << 96);
        }
    }

    function _packed(string memory json, string memory path) private pure returns (uint256 value) {
        uint256[] memory coefficients = vm.parseJsonUintArray(json, path);
        assertEq(coefficients.length, 4);
        value = coefficients[0] | (coefficients[1] << 32) | (coefficients[2] << 64) | (coefficients[3] << 96);
    }
}
