// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity 0.8.30;

import {Test} from "forge-std/Test.sol";
import {FieldBakeoff} from "../src/FieldBakeoff.sol";

contract FieldBakeoffTest is Test {
    FieldBakeoff private bench;

    function setUp() external {
        bench = new FieldBakeoff();
    }

    function testSharedBaseAndExtensionIdentities() external view {
        for (uint8 candidate; candidate < 6; ++candidate) {
            (uint256 p, uint256 d,,) = bench.specification(candidate);
            uint256 a = bench.deterministicBase(candidate, 1);
            assertEq(bench.baseSub(candidate, bench.baseAdd(candidate, a, 1), 1), a);
            assertEq(bench.baseMul(candidate, a, bench.baseInverse(candidate, a)), 1);

            uint256[] memory e = bench.deterministicExtension(candidate, 10);
            uint256[] memory product = bench.extensionMul(candidate, e, bench.extensionInverse(candidate, e));
            assertEq(product.length, d);
            assertEq(product[0], 1);
            for (uint256 i = 1; i < d; ++i) assertEq(product[i], 0);
            assertEq(bench.baseAdd(candidate, p - 1, 1), 0);
        }
    }

    function testPinnedReductionPolynomials() external view {
        uint256[] memory x4 = new uint256[](5);
        uint256[] memory x = new uint256[](5);
        x4[4] = 1;
        x[1] = 1;
        uint256[] memory quintic = bench.extensionMul(2, x4, x);
        assertEq(quintic[0], 1);
        assertEq(quintic[1], 0);
        assertEq(quintic[2], 2_130_706_432);
        assertEq(quintic[3], 0);
        assertEq(quintic[4], 0);

        uint256[] memory u = new uint256[](4);
        u[2] = 1;
        uint256[] memory qm31 = bench.extensionMul(4, u, u);
        assertEq(qm31[0], 2);
        assertEq(qm31[1], 1);
        assertEq(qm31[2], 0);
        assertEq(qm31[3], 0);
    }

    function testCanonicalityAndEncodingWidths() external {
        for (uint8 candidate; candidate < 6; ++candidate) {
            (uint256 p,,,) = bench.specification(candidate);
            vm.expectRevert(abi.encodeWithSelector(FieldBakeoff.NonCanonical.selector, p, p));
            bench.canonical(candidate, p);
            uint256[] memory one = new uint256[](1);
            one[0] = p - 1;
            uint256 expected = candidate == 3 ? 8 : candidate == 5 ? 32 : 4;
            assertEq(bench.rawEncode(candidate, one).length, expected);
            assertEq(bench.abiEncode(candidate, one).length, 96); // dynamic-array offset, length, one word
        }
    }

    function testDeterministicKernelCoverage() external view {
        uint256[4] memory dots = [uint256(32), 64, 128, 256];
        uint256[3] memory batches = [uint256(16), 32, 64];
        for (uint8 candidate; candidate < 6; ++candidate) {
            for (uint8 operation; operation <= 12; ++operation) bench.kernel(candidate, operation, 1);
            for (uint256 i; i < dots.length; ++i) bench.kernel(candidate, 13, dots[i]);
            for (uint256 i; i < batches.length; ++i) {
                bench.kernel(candidate, 14, batches[i]);
                bench.kernel(candidate, 15, batches[i]);
            }
            bench.kernel(candidate, 16, 64);
            bench.kernel(candidate, 17, 2);
        }
    }

    /// forge test -vv prints reproducible gas deltas for every candidate and kernel.
    function testGasSnapshots() external {
        uint256[4] memory dots = [uint256(32), 64, 128, 256];
        uint256[3] memory batches = [uint256(16), 32, 64];
        for (uint8 candidate; candidate < 6; ++candidate) {
            for (uint8 operation; operation <= 12; ++operation) _measure(candidate, operation, 1);
            for (uint256 i; i < dots.length; ++i) _measure(candidate, 13, dots[i]);
            for (uint256 i; i < batches.length; ++i) {
                _measure(candidate, 14, batches[i]);
                _measure(candidate, 15, batches[i]);
            }
            _measure(candidate, 16, 64);
            _measure(candidate, 17, 2);

            uint256 before = gasleft();
            bench.canonical(candidate, bench.deterministicBase(candidate, 1));
            emit log_named_uint(_label(candidate, 18, 1), before - gasleft());

            (uint256 p,,,) = bench.specification(candidate);
            before = gasleft();
            (bool ok,) = address(bench).call(abi.encodeCall(FieldBakeoff.canonical, (candidate, p)));
            assertFalse(ok);
            emit log_named_uint(_label(candidate, 19, 1), before - gasleft());
        }
    }

    function _measure(uint8 candidate, uint8 operation, uint256 n) private {
        uint256 before = gasleft();
        bench.kernel(candidate, operation, n);
        emit log_named_uint(_label(candidate, operation, n), before - gasleft());
    }

    function _label(uint8 candidate, uint8 operation, uint256 n) private view returns (string memory) {
        return string.concat("F", vm.toString(candidate), "/op", vm.toString(operation), "/n", vm.toString(n));
    }
}
