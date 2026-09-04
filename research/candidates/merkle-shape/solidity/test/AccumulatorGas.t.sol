// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {Digest512} from "pqtc/libraries/Digest512.sol";
import {H0BinaryAccumulator} from "../src/ResearchAccumulators.sol";

contract AccumulatorGasTest is Test {
    function testCanonicalH0SweepAndBoundaries() external {
        Digest512 memory scope = Digest512(bytes32(uint256(1)), bytes32(uint256(2)));
        uint256 beforeCreate = gasleft();
        H0BinaryAccumulator unbounded = new H0BinaryAccumulator(scope, false);
        uint256 unboundedDeployment = beforeCreate - gasleft();
        beforeCreate = gasleft();
        H0BinaryAccumulator bounded = new H0BinaryAccumulator(scope, true);
        uint256 boundedDeployment = beforeCreate - gasleft();

        uint256[] memory unboundedSweep = new uint256[](256);
        uint256[] memory boundedSweep = new uint256[](256);
        for (uint256 i; i < 256; ++i) {
            Digest512 memory leaf = _leaf(i);
            unboundedSweep[i] = _callGas(address(unbounded), abi.encodeCall(unbounded.insert, (leaf))).gasUsed;
            boundedSweep[i] = _callGas(address(bounded), abi.encodeCall(bounded.insert, (leaf))).gasUsed;
        }

        uint256[] memory indices = new uint256[](42);
        uint256[] memory unboundedBoundaryGas = new uint256[](42);
        bool[] memory accepted = new bool[](42);
        uint256 cursor;
        for (uint256 k; k <= 20; ++k) {
            uint256 power = uint256(1) << k;
            indices[cursor] = power - 1;
            unbounded.researchLoadSyntheticIndex(uint32(power - 1));
            CallResult memory below = _callGas(address(unbounded), abi.encodeCall(unbounded.insert, (_leaf(1000 + cursor))));
            unboundedBoundaryGas[cursor] = below.gasUsed;
            accepted[cursor++] = below.success;

            indices[cursor] = power;
            unbounded.researchLoadSyntheticIndex(uint32(power));
            CallResult memory at = _callGas(address(unbounded), abi.encodeCall(unbounded.insert, (_leaf(1000 + cursor))));
            unboundedBoundaryGas[cursor] = at.gasUsed;
            accepted[cursor++] = at.success;
        }
        assertFalse(accepted[41], "full-capacity insertion must reject");
        for (uint256 i; i < 41; ++i) assertTrue(accepted[i], "in-capacity insertion rejected");

        string memory object = "sp11";
        vm.serializeString(object, "schema", "sp11-foundry-gas-v1");
        vm.serializeString(object, "measurement_class", "EXACT_FOUNDRY_GASLEFT_DELTA");
        vm.serializeUint(object, "unbounded_deployment_gas", unboundedDeployment);
        vm.serializeUint(object, "bounded_deployment_gas", boundedDeployment);
        vm.serializeUint(object, "unbounded_runtime_bytes", address(unbounded).code.length);
        vm.serializeUint(object, "bounded_runtime_bytes", address(bounded).code.length);
        vm.serializeUint(object, "indices_0_255", _range256());
        vm.serializeUint(object, "unbounded_insert_gas_0_255", unboundedSweep);
        vm.serializeUint(object, "bounded_insert_gas_0_255", boundedSweep);
        vm.serializeUint(object, "boundary_indices", indices);
        vm.serializeUint(object, "unbounded_boundary_gas", unboundedBoundaryGas);
        string memory json = vm.serializeBool(object, "boundary_insert_accepted", accepted);
        vm.writeJson(json, "../outputs/foundry-gas.json");
    }

    struct CallResult { uint256 gasUsed; bool success; }

    function _callGas(address target, bytes memory data) private returns (CallResult memory result) {
        uint256 beforeCall = gasleft();
        (result.success,) = target.call(data);
        result.gasUsed = beforeCall - gasleft();
    }

    function _leaf(uint256 value) private pure returns (Digest512 memory) {
        return Digest512(bytes32(value + 3), bytes32(value + 4));
    }

    function _range256() private pure returns (uint256[] memory values) {
        values = new uint256[](256);
        for (uint256 i; i < 256; ++i) values[i] = i;
    }
}
