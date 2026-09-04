// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {Test} from "forge-std/Test.sol";
import {VerifierOptimizationBench} from "../src/VerifierOptimizationBench.sol";

contract VerifierOptimizationGasTest is Test {
    VerifierOptimizationBench internal bench;
    uint256[] internal values;
    uint256[] internal powers;
    bytes internal encoded;

    function setUp() public {
        bench = new VerifierOptimizationBench();
        encoded = new bytes(256 * 4);
        uint256 x = 1;
        for (uint256 i; i < 256; ++i) {
            uint256 value = (i * 1_000_003 + 17) % 2_013_265_921;
            values.push(value);
            encoded[i * 4] = bytes1(uint8(value >> 24));
            encoded[i * 4 + 1] = bytes1(uint8(value >> 16));
            encoded[i * 4 + 2] = bytes1(uint8(value >> 8));
            encoded[i * 4 + 3] = bytes1(uint8(value));
            if (i < 32) { powers.push(x); x = mulmod(x, 7, 2_013_265_921); }
        }
    }

    function testV1Gas() public {
        uint256 start = gasleft(); bench.materializedAlpha(values, 7); emit log_named_uint("V1.materializedGas", start - gasleft());
        start = gasleft(); bench.streamedAlpha(values, 7); emit log_named_uint("V1.streamedGas", start - gasleft());
        start = gasleft(); bench.hornerAlpha(values, 7); emit log_named_uint("V1.hornerGas", start - gasleft());
    }

    function testV2Gas() public {
        uint256 start = gasleft(); bench.exponentiateInverse(7); emit log_named_uint("V2.exponentiationGas", start - gasleft());
        start = gasleft(); bench.checkedRequiredInverse(7, 862_828_252); emit log_named_uint("V2.checkedWitnessGas", start - gasleft());
    }

    function testV3Gas() public {
        uint256 start = gasleft(); bench.parseThenDot(encoded, values); emit log_named_uint("V3.separateParseDotGas", start - gasleft());
        start = gasleft(); bench.fusedParseDot(encoded, values); emit log_named_uint("V3.fusedParseDotGas", start - gasleft());
    }

    function testV4Gas() public {
        uint256 start = gasleft(); bench.copiedEvaluation(values, 7); emit log_named_uint("V4.copiedEvaluationGas", start - gasleft());
        start = gasleft(); bench.calldataEvaluation(values, 7); emit log_named_uint("V4.calldataEvaluationGas", start - gasleft());
    }

    function testV5Gas() public {
        uint256 start = gasleft(); bench.fixedPowerTableDigest(); emit log_named_uint("V5.fixedTableGas", start - gasleft());
        start = gasleft(); bench.derivedPowerTableDigest(); emit log_named_uint("V5.derivedTableGas", start - gasleft());
        start = gasleft(); bench.checkedCalldataTableDigest(powers); emit log_named_uint("V5.checkedCalldataTableGas", start - gasleft());
    }

    function testV6Gas() public {
        uint256 start = gasleft(); bench.exponentQueryPoints(7, 127, 32); emit log_named_uint("V6.exponentiationGas", start - gasleft());
        start = gasleft(); bench.incrementalQueryPoints(7, 127, 32); emit log_named_uint("V6.incrementalGas", start - gasleft());
        uint256[] memory points = new uint256[](32); uint256 x = 1;
        for (uint256 i; i < 32; ++i) { points[i] = x; x = mulmod(x, 345_311_278, 2_013_265_921); }
        start = gasleft(); bench.checkedQueryPoints(7, 127, points); emit log_named_uint("V6.checkedPointsGas", start - gasleft());
        start = gasleft(); bench.fixedQueryPoints8(); emit log_named_uint("V6.fixedTable8Gas", start - gasleft());
    }

    function testV7Gas() public {
        uint32[] memory indices = new uint32[](32);
        for (uint32 i; i < 32; ++i) indices[i] = i * 256;
        uint256 start = gasleft(); uint256 count = bench.frontierCount(indices, 13); emit log_named_uint("V7.exactFrontierGas", start - gasleft());
        assertEq(count, 256);
    }

    function testV8Gas() public {
        bytes memory packed = _pack31(values);
        uint256 start = gasleft(); bench.unpack32(encoded, values.length); emit log_named_uint("V8.unpack32Gas", start - gasleft());
        start = gasleft(); bench.unpack31(packed, values.length); emit log_named_uint("V8.unpack31Gas", start - gasleft());
        start = gasleft(); bench.section31(packed, 0, values.length); emit log_named_uint("V8.section31Gas", start - gasleft());
        emit log_named_uint("V8.u32Bytes", encoded.length);
        emit log_named_uint("V8.packed31Bytes", packed.length);
    }

    function testV9Gas() public {
        uint256[7] memory splits = [uint256(8),10,12,13,14,15,16];
        for (uint256 i; i < splits.length; ++i) {
            (uint256 a0, uint256 b0) = bench.splitCost(splits[i], true);
            (uint256 a1, uint256 b1) = bench.splitCost(splits[i], false);
            emit log_named_uint(string.concat("V9.airA.", vm.toString(splits[i]), ".maxGas"), a0 > b0 ? a0 : b0);
            emit log_named_uint(string.concat("V9.airB.", vm.toString(splits[i]), ".maxGas"), a1 > b1 ? a1 : b1);
        }
    }

    function testRuntimeAndDeploymentGas() public {
        uint256 start = gasleft(); VerifierOptimizationBench deployed = new VerifierOptimizationBench();
        emit log_named_uint("COMMON.deploymentExecutionGas", start - gasleft());
        emit log_named_uint("COMMON.runtimeBytes", address(deployed).code.length);
    }

    function testUnsafeInverseCasesReject() public {
        vm.expectRevert(VerifierOptimizationBench.ZeroDenominator.selector); bench.checkedRequiredInverse(0, 0);
        vm.expectRevert(VerifierOptimizationBench.ZeroLegal.selector); bench.zeroLegalInverseForbidden(1, 1);
        vm.expectRevert(VerifierOptimizationBench.InvalidWitness.selector); bench.checkedRequiredInverse(7, 1);
    }

    function testUnsafeCodecCasesReject() public {
        bytes memory packed = _pack31(values);
        bytes memory truncated = new bytes(packed.length - 1);
        for (uint256 i; i < truncated.length; ++i) truncated[i] = packed[i];
        vm.expectRevert(VerifierOptimizationBench.Bound.selector); bench.unpack31(truncated, values.length);
        bytes memory noncanonical = hex"ffffff7f";
        vm.expectRevert(VerifierOptimizationBench.Noncanonical.selector); bench.unpack31(noncanonical, 1);
        bytes memory padding = hex"01000080";
        vm.expectRevert(VerifierOptimizationBench.Noncanonical.selector); bench.unpack31(padding, 1);
        vm.expectRevert(VerifierOptimizationBench.Bound.selector); bench.section31(packed, packed.length, 1);
    }

    function testUnsafeFrontierCasesReject() public {
        uint32[] memory duplicate = new uint32[](2); duplicate[0] = 1; duplicate[1] = 1;
        vm.expectRevert(VerifierOptimizationBench.InvalidFrontier.selector); bench.frontierCount(duplicate, 13);
        uint32[] memory outOfRange = new uint32[](1); outOfRange[0] = 8192;
        vm.expectRevert(VerifierOptimizationBench.InvalidFrontier.selector); bench.frontierCount(outOfRange, 13);
    }

    function _pack31(uint256[] memory input) private pure returns (bytes memory out) {
        out = new bytes((input.length * 31 + 7) / 8);
        uint256 bits; uint256 used; uint256 at;
        for (uint256 i; i < input.length; ++i) {
            bits |= input[i] << used; used += 31;
            while (used >= 8) { out[at++] = bytes1(uint8(bits)); bits >>= 8; used -= 8; }
        }
        if (used != 0) out[at] = bytes1(uint8(bits));
    }
}
