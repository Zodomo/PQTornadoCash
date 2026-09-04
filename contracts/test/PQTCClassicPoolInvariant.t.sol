// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {StdInvariant} from "forge-std/StdInvariant.sol";
import {Test} from "forge-std/Test.sol";
import {PQTCClassicPool, IPQTCVerificationRegistry} from "../src/PQTCClassicPool.sol";
import {Digest512} from "../src/libraries/Digest512.sol";

contract InvariantRegistry is IPQTCVerificationRegistry {
    struct Checkpoint {
        address consumer;
        Digest512 parameterId;
        bytes32 statementKey;
    }

    mapping(bytes32 => Checkpoint) private checkpoints;

    function beginVerification(
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata proofPartA
    ) external returns (bytes32 verificationId) {
        for (uint256 i = 0; i < 64; ++i) {
            if (publicValues[i] >= 2_013_265_921) revert();
        }
        bytes32 statementKey =
            keccak256(abi.encode(bytes32("PQTC.V3.STATEMENT"), parameterId.left, parameterId.right, publicValues));
        bytes32 coreProofId = keccak256(abi.encode(bytes32("PQTC.V3.PROOF"), statementKey, keccak256(proofPartA)));
        verificationId = keccak256(abi.encode(bytes32("PQTC.V3.VERIFICATION"), coreProofId, msg.sender));
        checkpoints[verificationId] = Checkpoint(msg.sender, parameterId, statementKey);
    }

    function completeVerification(
        bytes32 proofId,
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata
    ) external returns (bool) {
        Checkpoint storage checkpoint = checkpoints[proofId];
        if (
            checkpoint.consumer != msg.sender || checkpoint.parameterId.left != parameterId.left
                || checkpoint.parameterId.right != parameterId.right
        ) return false;
        for (uint256 i = 0; i < 64; ++i) {
            if (publicValues[i] >= 2_013_265_921) return false;
        }
        bytes32 statementKey =
            keccak256(abi.encode(bytes32("PQTC.V3.STATEMENT"), parameterId.left, parameterId.right, publicValues));
        if (statementKey != checkpoint.statementKey) return false;
        delete checkpoints[proofId];
        return true;
    }
}

contract PoolInvariantHandler {
    uint256 private constant DENOMINATION = 1 ether;

    PQTCClassicPool public immutable pool;

    uint256 public totalDeposited;
    uint256 public totalWithdrawn;
    uint256 public actionNonce;
    Digest512 public lastNullifier;

    constructor(PQTCClassicPool pool_) {
        pool = pool_;
    }

    receive() external payable {}

    function deposit(uint256) external {
        uint256 nonce = ++actionNonce;
        Digest512 memory commitment = Digest512(bytes32(nonce), bytes32(nonce + 1));
        pool.deposit{value: DENOMINATION}(commitment);
        totalDeposited += DENOMINATION;
    }

    function withdraw(uint256) external {
        if (address(pool).balance < DENOMINATION) return;

        uint256 nonce = ++actionNonce;
        Digest512 memory nullifier = Digest512(bytes32(nonce), bytes32(nonce + 1));
        Digest512 memory root = pool.currentRoot();
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nullifier,
            recipient: payable(address(this)),
            relayer: payable(address(0)),
            fee: 0
        });
        bytes32 verificationId = pool.beginWithdrawal(withdrawal, abi.encode(nonce));
        pool.withdraw(withdrawal, verificationId, "");

        lastNullifier = nullifier;
        totalWithdrawn += DENOMINATION;
    }
}

contract PQTCClassicPoolInvariantTest is StdInvariant, Test {
    uint256 private constant DENOMINATION = 1 ether;

    PQTCClassicPool private pool;
    PoolInvariantHandler private handler;

    function setUp() external {
        Digest512 memory parameter = Digest512(bytes32(uint256(1)), bytes32(uint256(2)));
        InvariantRegistry registry = new InvariantRegistry();
        pool = new PQTCClassicPool(DENOMINATION, parameter, registry);
        handler = new PoolInvariantHandler(pool);
        vm.deal(address(handler), 1_000_000 ether);

        bytes4[] memory selectors = new bytes4[](2);
        selectors[0] = handler.deposit.selector;
        selectors[1] = handler.withdraw.selector;
        targetSelector(FuzzSelector({addr: address(handler), selectors: selectors}));
        targetContract(address(handler));
    }

    function invariantPoolBalanceMatchesNetDeposits() external view {
        assertEq(address(pool).balance, handler.totalDeposited() - handler.totalWithdrawn());
    }

    function invariantWithdrawalsNeverExceedDeposits() external view {
        assertLe(handler.totalWithdrawn(), handler.totalDeposited());
    }

    function invariantLastWithdrawalNullifierRemainsSpent() external view {
        if (handler.totalWithdrawn() == 0) return;
        (bytes32 left, bytes32 right) = handler.lastNullifier();
        assertTrue(pool.nullifiers(left, right));
    }
}
