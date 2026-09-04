// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity 0.8.30;

import {Test} from "forge-std/Test.sol";
import {Digest512} from "v03/libraries/Digest512.sol";
import {IPQTCVerificationRegistry} from "v03/PQTCClassicPool.sol";
import {PQTCVerificationRegistry} from "v03/PQTCVerificationRegistry.sol";
import {PQTCAirStageVerifier} from "v03/verifier/PQTCAirStageVerifier.sol";
import {PQTCQueryVerifier} from "v03/verifier/PQTCQueryVerifier.sol";
import {ResearchFixturePool} from "../src/ResearchFixturePool.sol";

contract BaselineFixtureTest is Test {
    address payable private constant FIXED_POOL = payable(0xc00000000000000000000000000000000000C000);
    Digest512 private parameterId = Digest512(
        0x35adfcc070249bb0393c2fd45f0bbd48ef03cbfc08070d03335eaf952975e62a,
        0xb7bc82ead4f8c1f1c39b3372be85195853134dfc9d24f43b97a5e0454ea07779
    );
    address private constant SYNTHETIC_SENDER = 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266;


    function testArbitraryGeneratedFixtureThroughCompletePoolCalls() external {
        string memory fixture = vm.envString("V03_FIXTURE_DIR");
        string memory data = vm.readFile(string.concat(fixture, "/evm.json"));
        assertEq(vm.parseJsonAddress(data, ".pool_address"), FIXED_POOL, "fixture targets research pool");
        uint256 denomination = vm.parseUint(vm.parseJsonString(data, ".denomination_wei"));
        Digest512 memory fixtureScope = _digest(data, ".scope");
        Digest512 memory root = _digest(data, ".root");

        PQTCAirStageVerifier air = new PQTCAirStageVerifier();
        PQTCQueryVerifier query = new PQTCQueryVerifier();
        PQTCVerificationRegistry registry = new PQTCVerificationRegistry(air, query, parameterId);
        ResearchFixturePool template =
            new ResearchFixturePool(denomination, parameterId, IPQTCVerificationRegistry(address(registry)));
        vm.etch(FIXED_POOL, address(template).code);
        ResearchFixturePool(FIXED_POOL).researchInitializeEtchedStorage(fixtureScope, root, parameterId);
        (bytes32 scopeLeft, bytes32 scopeRight) = ResearchFixturePool(FIXED_POOL).scope();
        assertEq(scopeLeft, fixtureScope.left, "fixture scope left");
        assertEq(scopeRight, fixtureScope.right, "fixture scope right");
        vm.deal(FIXED_POOL, denomination);

        bytes memory expectedA = vm.readFileBinary(string.concat(fixture, "/part-a.calldata"));
        bytes memory expectedB = vm.readFileBinary(string.concat(fixture, "/part-b.calldata"));
        uint256 beforeA = gasleft();
        (bool okA, bytes memory resultA) = FIXED_POOL.call(expectedA);
        uint256 gasA = beforeA - gasleft();
        if (!okA) _revertWith(resultA);
        bytes32 verificationId = abi.decode(resultA, (bytes32));
        assertEq(verificationId, vm.parseJsonBytes32(vm.readFile(string.concat(fixture, "/proof-metadata.json")), ".verification_id"), "exact consumer-bound ID");

        uint256 beforeB = gasleft();
        (bool okB, bytes memory resultB) = FIXED_POOL.call(expectedB);
        uint256 gasB = beforeB - gasleft();
        if (!okB) _revertWith(resultB);
        assertTrue(ResearchFixturePool(FIXED_POOL).nullifiers(_digest(data, ".nullifier_hash").left, _digest(data, ".nullifier_hash").right), "nullifier spent");
        emit log_named_uint("V03_POOL_A_EXECUTION_GAS", gasA);
        emit log_named_uint("V03_POOL_B_EXECUTION_GAS", gasB);
        emit log_named_uint("V03_POOL_A_STANDARD_INTRINSIC_GAS", _intrinsic(expectedA));
        emit log_named_uint("V03_POOL_B_STANDARD_INTRINSIC_GAS", _intrinsic(expectedB));
        emit log_named_uint("V03_POOL_A_CALLDATA_BYTES", expectedA.length);
        emit log_named_uint("V03_POOL_B_CALLDATA_BYTES", expectedB.length);
    }
    function testExportFixturePrestate() external {
        string memory fixture = vm.envString("V03_FIXTURE_DIR");
        string memory data = vm.readFile(string.concat(fixture, "/evm.json"));
        assertEq(vm.parseJsonAddress(data, ".pool_address"), FIXED_POOL, "fixture targets research pool");
        uint256 denomination = vm.parseUint(vm.parseJsonString(data, ".denomination_wei"));
        Digest512 memory fixtureScope = _digest(data, ".scope");
        Digest512 memory root = _digest(data, ".root");

        PQTCAirStageVerifier air = new PQTCAirStageVerifier();
        PQTCQueryVerifier query = new PQTCQueryVerifier();
        PQTCVerificationRegistry registry = new PQTCVerificationRegistry(air, query, parameterId);
        ResearchFixturePool template =
            new ResearchFixturePool(denomination, parameterId, IPQTCVerificationRegistry(address(registry)));
        vm.etch(FIXED_POOL, address(template).code);
        ResearchFixturePool(FIXED_POOL).researchInitializeEtchedStorage(fixtureScope, root, parameterId);
        vm.deal(FIXED_POOL, denomination);
        vm.deal(SYNTHETIC_SENDER, 100 ether);
        vm.dumpState(vm.envString("V03_PRESTATE_OUT"));
    }


    function _digest(string memory data, string memory key) private pure returns (Digest512 memory value) {
        bytes memory encoded = vm.parseJsonBytes(data, key);
        require(encoded.length == 64, "digest length");
        assembly ("memory-safe") {
            mstore(value, mload(add(encoded, 0x20)))
            mstore(add(value, 0x20), mload(add(encoded, 0x40)))
        }
    }

    function _intrinsic(bytes memory payload) private pure returns (uint256 gasValue) {
        gasValue = 21_000;
        for (uint256 i; i < payload.length; ++i) gasValue += payload[i] == 0 ? 4 : 16;
    }

    function _revertWith(bytes memory reason) private pure {
        assembly ("memory-safe") { revert(add(reason, 0x20), mload(reason)) }
    }
}
