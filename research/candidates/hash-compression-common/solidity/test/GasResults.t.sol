// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

import {Vm} from "forge-std/Vm.sol";
import {H0Sponge} from "../src/H0Sponge.sol";
import {H1Poseidon2} from "../src/Poseidon16Candidates.sol";
import {H3Poseidon2, H4Poseidon2} from "../src/Poseidon24Candidates.sol";
import {H5Poseidon2, H6Poseidon2} from "../src/Poseidon32Candidates.sol";
import {H7RpoM31} from "../src/H7RpoM31.sol";
import {INodeKernel, ResearchTree} from "./GasBench.t.sol";

contract GasResults {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    string private constant RESULTS = "../gas/results.json";

    function _lanes(uint256 n) private pure returns (uint256[] memory result) {
        result = new uint256[](n);
        for (uint256 i; i < n; ++i) result[i] = i + 1;
    }

    function _write(string memory candidate, string memory metric, uint256 value) private {
        vm.writeJson(vm.toString(value), RESULTS, string.concat(".", candidate, ".", metric));
    }

    function _staticGas(address target, bytes memory callData) private view returns (uint256 used) {
        uint256 beforeGas = gasleft();
        (bool ok, bytes memory result) = target.staticcall(callData);
        used = beforeGas - gasleft();
        require(ok && result.length != 0, "measurement call failed");
    }

    function _callGas(address target, bytes memory callData) private returns (uint256 used) {
        uint256 beforeGas = gasleft();
        (bool ok,) = target.call(callData);
        used = beforeGas - gasleft();
        require(ok, "measurement call failed");
    }

    function _treeMetrics(string memory candidate, INodeKernel kernel, uint256 digestLength) private {
        uint256 beforeGas = gasleft();
        new ResearchTree(kernel, digestLength, true);
        _write(candidate, "zeroTreeConstructorGas", beforeGas - gasleft());

        ResearchTree computeTree = new ResearchTree(kernel, digestLength, false);
        _write(
            candidate,
            "depth20ComputeOnlyInsertionGas",
            _staticGas(address(computeTree), abi.encodeCall(computeTree.computeOnlyInsertion, (_lanes(digestLength))))
        );

        ResearchTree storageTree = new ResearchTree(kernel, digestLength, false);
        _write(
            candidate,
            "syntheticDepth20RootUpdateGas",
            _callGas(address(storageTree), abi.encodeCall(storageTree.syntheticDepth20RootUpdate, (_lanes(digestLength))))
        );
    }

    function testH0() external {
        H0Sponge kernel = new H0Sponge();
        _write("H0", "permutationGas", _staticGas(address(kernel), abi.encodeCall(kernel.permutation, (_lanes(16)))));
        kernel = new H0Sponge();
        _write("H0", "noteGas", _staticGas(address(kernel), abi.encodeCall(kernel.note, (_lanes(32)))));
        kernel = new H0Sponge();
        _write("H0", "nullifierGas", _staticGas(address(kernel), abi.encodeCall(kernel.nullifier, (_lanes(24)))));
        kernel = new H0Sponge();
        _write("H0", "nodeGas", _staticGas(address(kernel), abi.encodeCall(kernel.node, (7, _lanes(16), _lanes(16)))));
        _write("H0", "runtimeBytes", address(kernel).code.length);
        _write("H0", "initcodeBytes", type(H0Sponge).creationCode.length);
        _treeMetrics("H0", INodeKernel(address(kernel)), 16);
    }

    function testH1() external {
        H1Poseidon2 kernel = new H1Poseidon2();
        _write("H1", "permutationGas", _staticGas(address(kernel), abi.encodeCall(kernel.permutation, (_lanes(16)))));
        kernel = new H1Poseidon2();
        _write("H1", "compressionGas", _staticGas(address(kernel), abi.encodeCall(kernel.compression, (_lanes(16)))));
        _write("H1", "runtimeBytes", address(kernel).code.length);
        _write("H1", "initcodeBytes", type(H1Poseidon2).creationCode.length);
    }

    function testH3() external {
        H3Poseidon2 kernel = new H3Poseidon2();
        _write("H3", "permutationGas", _staticGas(address(kernel), abi.encodeCall(kernel.permutation, (_lanes(24)))));
        kernel = new H3Poseidon2();
        _write("H3", "compressionGas", _staticGas(address(kernel), abi.encodeCall(kernel.compression, (_lanes(24)))));
        kernel = new H3Poseidon2();
        _write("H3", "noteGas", _staticGas(address(kernel), abi.encodeCall(kernel.note, (_lanes(20)))));
        kernel = new H3Poseidon2();
        _write("H3", "nullifierGas", _staticGas(address(kernel), abi.encodeCall(kernel.nullifier, (_lanes(20)))));
        kernel = new H3Poseidon2();
        _write("H3", "nodeGas", _staticGas(address(kernel), abi.encodeCall(kernel.node, (7, _lanes(10), _lanes(10)))));
        _write("H3", "runtimeBytes", address(kernel).code.length);
        _write("H3", "initcodeBytes", type(H3Poseidon2).creationCode.length);
        _treeMetrics("H3", INodeKernel(address(kernel)), 10);
    }

    function testH4() external {
        H4Poseidon2 kernel = new H4Poseidon2();
        _write("H4", "permutationGas", _staticGas(address(kernel), abi.encodeCall(kernel.permutation, (_lanes(24)))));
        kernel = new H4Poseidon2();
        _write("H4", "compressionGas", _staticGas(address(kernel), abi.encodeCall(kernel.compression, (_lanes(24)))));
        _write("H4", "runtimeBytes", address(kernel).code.length);
        _write("H4", "initcodeBytes", type(H4Poseidon2).creationCode.length);
    }

    function testH5() external {
        H5Poseidon2 kernel = new H5Poseidon2();
        _write("H5", "permutationGas", _staticGas(address(kernel), abi.encodeCall(kernel.permutation, (_lanes(32)))));
        kernel = new H5Poseidon2();
        _write("H5", "compressionGas", _staticGas(address(kernel), abi.encodeCall(kernel.compression, (_lanes(32)))));
        kernel = new H5Poseidon2();
        _write("H5", "noteGas", _staticGas(address(kernel), abi.encodeCall(kernel.note, (_lanes(24)))));
        kernel = new H5Poseidon2();
        _write("H5", "nullifierGas", _staticGas(address(kernel), abi.encodeCall(kernel.nullifier, (_lanes(24)))));
        kernel = new H5Poseidon2();
        _write("H5", "nodeGas", _staticGas(address(kernel), abi.encodeCall(kernel.node, (7, _lanes(12), _lanes(12)))));
        _write("H5", "runtimeBytes", address(kernel).code.length);
        _write("H5", "initcodeBytes", type(H5Poseidon2).creationCode.length);
        _treeMetrics("H5", INodeKernel(address(kernel)), 12);
    }

    function testH6() external {
        H6Poseidon2 kernel = new H6Poseidon2();
        _write("H6", "permutationGas", _staticGas(address(kernel), abi.encodeCall(kernel.permutation, (_lanes(32)))));
        kernel = new H6Poseidon2();
        _write("H6", "compressionGas", _staticGas(address(kernel), abi.encodeCall(kernel.compression, (_lanes(32)))));
        kernel = new H6Poseidon2();
        _write("H6", "noteGas", _staticGas(address(kernel), abi.encodeCall(kernel.note, (_lanes(28)))));
        kernel = new H6Poseidon2();
        _write("H6", "nullifierGas", _staticGas(address(kernel), abi.encodeCall(kernel.nullifier, (_lanes(28)))));
        kernel = new H6Poseidon2();
        _write("H6", "nodeGas", _staticGas(address(kernel), abi.encodeCall(kernel.node, (7, _lanes(14), _lanes(14)))));
        _write("H6", "runtimeBytes", address(kernel).code.length);
        _write("H6", "initcodeBytes", type(H6Poseidon2).creationCode.length);
        _treeMetrics("H6", INodeKernel(address(kernel)), 14);
    }

    function testH7PrimitiveAndApplication() external {
        H7RpoM31 kernel = new H7RpoM31();
        _write("H7", "permutationGas", _staticGas(address(kernel), abi.encodeCall(kernel.permutation, (_lanes(24)))));
        kernel = new H7RpoM31();
        _write("H7", "spongeGas", _staticGas(address(kernel), abi.encodeCall(kernel.sponge, (_lanes(36)))));
        kernel = new H7RpoM31();
        _write("H7", "noteGas", _staticGas(address(kernel), abi.encodeCall(kernel.note, (_lanes(32)))));
        kernel = new H7RpoM31();
        _write("H7", "nullifierGas", _staticGas(address(kernel), abi.encodeCall(kernel.nullifier, (_lanes(32)))));
        kernel = new H7RpoM31();
        _write("H7", "nodeGas", _staticGas(address(kernel), abi.encodeCall(kernel.node, (7, _lanes(16), _lanes(16)))));
        _write("H7", "runtimeBytes", address(kernel).code.length);
        _write("H7", "initcodeBytes", type(H7RpoM31).creationCode.length);
    }

    function testH7ZeroTreeConstructor() external {
        H7RpoM31 kernel = new H7RpoM31();
        uint256 beforeGas = gasleft();
        new ResearchTree(INodeKernel(address(kernel)), 16, true);
        _write("H7", "zeroTreeConstructorGas", beforeGas - gasleft());
    }

    function testH7ComputeOnlyInsertion() external {
        H7RpoM31 kernel = new H7RpoM31();
        ResearchTree tree = new ResearchTree(INodeKernel(address(kernel)), 16, false);
        _write("H7", "depth20ComputeOnlyInsertionGas", _staticGas(address(tree), abi.encodeCall(tree.computeOnlyInsertion, (_lanes(16)))));
    }

    function testH7SyntheticDepth20RootUpdate() external {
        H7RpoM31 kernel = new H7RpoM31();
        ResearchTree tree = new ResearchTree(INodeKernel(address(kernel)), 16, false);
        _write("H7", "syntheticDepth20RootUpdateGas", _callGas(address(tree), abi.encodeCall(tree.syntheticDepth20RootUpdate, (_lanes(16)))));
    }
}
