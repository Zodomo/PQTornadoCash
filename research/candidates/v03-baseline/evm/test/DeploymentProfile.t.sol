// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity 0.8.30;

import {Test} from "forge-std/Test.sol";
import {Digest512} from "v03/libraries/Digest512.sol";
import {PQTCClassicPool} from "v03/PQTCClassicPool.sol";
import {PQTCVerificationRegistry} from "v03/PQTCVerificationRegistry.sol";
import {PQTCAirStageVerifier} from "v03/verifier/PQTCAirStageVerifier.sol";
import {PQTCQueryVerifier} from "v03/verifier/PQTCQueryVerifier.sol";

contract DeploymentProfileTest is Test {
    Digest512 private parameterId = Digest512(
        0x35adfcc070249bb0393c2fd45f0bbd48ef03cbfc08070d03335eaf952975e62a,
        0xb7bc82ead4f8c1f1c39b3372be85195853134dfc9d24f43b97a5e0454ea07779
    );

    function testDeploymentInitcodeRuntimeAndCodeDepositGas() external {
        uint256 before = gasleft();
        PQTCAirStageVerifier air = new PQTCAirStageVerifier();
        _emit("PQTCAirStageVerifier", before - gasleft(), address(air).code.length, type(PQTCAirStageVerifier).creationCode.length);
        before = gasleft();
        PQTCQueryVerifier query = new PQTCQueryVerifier();
        _emit("PQTCQueryVerifier", before - gasleft(), address(query).code.length, type(PQTCQueryVerifier).creationCode.length);
        bytes memory registryArgs = abi.encode(air, query, parameterId);
        before = gasleft();
        PQTCVerificationRegistry registry = new PQTCVerificationRegistry(air, query, parameterId);
        _emit("PQTCVerificationRegistry", before - gasleft(), address(registry).code.length, type(PQTCVerificationRegistry).creationCode.length + registryArgs.length);
        bytes memory poolArgs = abi.encode(uint256(1 ether), parameterId, registry);
        before = gasleft();
        PQTCClassicPool pool = new PQTCClassicPool(1 ether, parameterId, registry);
        _emit("PQTCClassicPool", before - gasleft(), address(pool).code.length, type(PQTCClassicPool).creationCode.length + poolArgs.length);
    }

    function _emit(string memory name, uint256 totalCreateGas, uint256 runtimeBytes, uint256 initcodeBytes) private {
        emit log_named_string("V03_DEPLOY_CONTRACT", name);
        emit log_named_uint("V03_DEPLOY_INITCODE_BYTES", initcodeBytes);
        emit log_named_uint("V03_DEPLOY_RUNTIME_BYTES", runtimeBytes);
        emit log_named_uint("V03_DEPLOY_CODE_DEPOSIT_GAS", runtimeBytes * 200);
        emit log_named_uint("V03_DEPLOY_OBSERVED_NEW_EXPRESSION_GAS", totalCreateGas);
        emit log_named_uint("V03_DEPLOY_CONSTRUCTOR_EXECUTION_GAS_NOT_SEPARATELY_OBSERVABLE", 0);
    }
}
