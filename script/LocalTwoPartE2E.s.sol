// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Script} from "forge-std/Script.sol";
import {Digest512} from "../contracts/src/libraries/Digest512.sol";
import {PQTCClassicPool} from "../contracts/src/PQTCClassicPool.sol";

/// Submits the canonical v3 proof parts to an existing local pool in exactly two transactions.
contract LocalTwoPartE2E is Script {
    function run() external returns (PQTCClassicPool pool, bytes32 verificationId) {
        pool = PQTCClassicPool(vm.envAddress("POOL"));
        bytes memory partA = vm.readFileBinary("test-vectors/verifier/v3/part-a.pqtc");
        bytes memory partB = vm.readFileBinary("test-vectors/verifier/v3/part-b.pqtc");
        PQTCClassicPool.Withdrawal memory withdrawal = _withdrawal();

        vm.startBroadcast();
        verificationId = pool.beginWithdrawal(withdrawal, partA);
        pool.withdraw(withdrawal, verificationId, partB);
        vm.stopBroadcast();
    }

    function _withdrawal() private view returns (PQTCClassicPool.Withdrawal memory withdrawal) {
        withdrawal.root = Digest512(vm.envBytes32("ROOT_LEFT"), vm.envBytes32("ROOT_RIGHT"));
        withdrawal.nullifierHash =
            Digest512(vm.envBytes32("NULLIFIER_HASH_LEFT"), vm.envBytes32("NULLIFIER_HASH_RIGHT"));
        withdrawal.recipient = payable(vm.envAddress("RECIPIENT"));
        withdrawal.relayer = payable(vm.envOr("RELAYER", address(0)));
        withdrawal.fee = vm.envOr("FEE_WEI", uint256(0));
    }
}
