// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Script} from "forge-std/Script.sol";
import {Digest512} from "../contracts/src/libraries/Digest512.sol";
import {PQTCClassicPool} from "../contracts/src/PQTCClassicPool.sol";

/// Submits one v3 two-part proof to an existing pool in exactly two transactions.
contract SubmitTwoPartProof is Script {
    function run() external returns (bytes32 verificationId) {
        PQTCClassicPool pool = PQTCClassicPool(vm.envAddress("POOL"));
        string memory proofDir = vm.envString("PROOF_DIR");
        bytes memory partA = vm.readFileBinary(string.concat(proofDir, "/part-a.pqtc"));
        bytes memory partB = vm.readFileBinary(string.concat(proofDir, "/part-b.pqtc"));
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
