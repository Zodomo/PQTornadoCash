// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Script} from "forge-std/Script.sol";
import {Digest512} from "../contracts/src/libraries/Digest512.sol";
import {PQTCAirStageVerifier} from "../contracts/src/verifier/PQTCAirStageVerifier.sol";
import {PQTCQueryVerifier} from "../contracts/src/verifier/PQTCQueryVerifier.sol";
import {PQTCVerificationRegistry} from "../contracts/src/PQTCVerificationRegistry.sol";
import {PQTCClassicPool} from "../contracts/src/PQTCClassicPool.sol";

contract DeploySepolia is Script {
    uint256 private constant SEPOLIA_CHAIN_ID = 11_155_111;
    error WrongChain(uint256 actual);

    event Deployment(
        address indexed pool,
        address indexed registry,
        address indexed airVerifier,
        address queryVerifier,
        bytes32 parameterLeft,
        bytes32 parameterRight,
        uint256 denomination
    );

    function run()
        external
        returns (
            PQTCClassicPool pool,
            PQTCVerificationRegistry registry,
            PQTCAirStageVerifier airVerifier,
            PQTCQueryVerifier queryVerifier
        )
    {
        if (block.chainid != SEPOLIA_CHAIN_ID) revert WrongChain(block.chainid);
        Digest512 memory parameterId =
            Digest512(vm.envBytes32("PARAMETER_ID_LEFT"), vm.envBytes32("PARAMETER_ID_RIGHT"));
        uint256 denomination = vm.envOr("DENOMINATION_WEI", uint256(0.001 ether));

        vm.startBroadcast();
        airVerifier = new PQTCAirStageVerifier();
        queryVerifier = new PQTCQueryVerifier();
        registry = new PQTCVerificationRegistry(airVerifier, queryVerifier, parameterId);
        pool = new PQTCClassicPool(denomination, parameterId, registry);
        emit Deployment(
            address(pool),
            address(registry),
            address(airVerifier),
            address(queryVerifier),
            parameterId.left,
            parameterId.right,
            denomination
        );
        vm.stopBroadcast();
    }

}
