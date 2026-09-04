// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {ITransitionVerifier, PermissionlessDepositQueue} from "../src/PermissionlessDepositQueue.sol";

contract QueueGasTest is Test {
    function testMeasureQueueUserDepositPath() external {
        PermissionlessDepositQueue queue = new PermissionlessDepositQueue(
            1 ether,
            1 days,
            ITransitionVerifier(address(1)),
            payable(address(2)),
            bytes32(uint256(3)),
            bytes32(uint256(4))
        );
        vm.deal(address(this), 256 ether);
        uint256[] memory samples = new uint256[](256);
        for (uint256 i; i < samples.length; ++i) {
            bytes memory data = abi.encodeCall(
                queue.enqueue,
                (bytes32(i + 5), bytes32(i + 261), address(this))
            );
            uint256 beforeCall = gasleft();
            (bool ok,) = address(queue).call{value: 1 ether}(data);
            samples[i] = beforeCall - gasleft();
            assertTrue(ok, "valid enqueue rejected");
        }
        assertEq(queue.pendingCount(), 256);
        string memory object = "sp12";
        vm.serializeString(object, "schema", "sp12-foundry-queue-gas-v1");
        vm.serializeString(object, "measurement_class", "ISOLATED_ENQUEUE_GASLEFT_DIAGNOSTIC");
        vm.serializeUint(object, "indices", _range256());
        string memory json = vm.serializeUint(object, "enqueue_gas", samples);
        vm.writeJson(json, "../outputs/foundry-gas.json");
    }

    function _range256() private pure returns (uint256[] memory values) {
        values = new uint256[](256);
        for (uint256 i; i < values.length; ++i) values[i] = i;
    }
}
