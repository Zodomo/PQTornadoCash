// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

/// Local diagnostic recipient/relayer, never a verification substitute.
contract PayoutReceiver {
    bool public rejectPayment;
    bool public attemptReentry;
    address public pool;
    bytes4 public reentryError;
    uint256 public payments;

    function configure(bool reject_, bool reentry_, address pool_) external {
        rejectPayment = reject_;
        attemptReentry = reentry_;
        pool = pool_;
    }

    receive() external payable {
        require(!rejectPayment, "local recipient rejection");
        if (attemptReentry) {
            // Any guarded entry must reject before denomination/hash checks.
            (bool accepted, bytes memory result) = pool.call(
                abi.encodeWithSignature("deposit((bytes32,bytes32))", bytes32(0), bytes32(0))
            );
            require(!accepted && result.length >= 4 && bytes4(result) == bytes4(keccak256("ReentrantCall()")), "reentry guard did not reject");
            reentryError = bytes4(result);
        }
        payments++;
    }
}
