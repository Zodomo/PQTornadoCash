// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {PQTCClassicPool, IPQTCVerificationRegistry} from "../src/PQTCClassicPool.sol";
import {Digest512} from "../src/libraries/Digest512.sol";
import {P2BB512} from "../src/libraries/P2BB512.sol";
import {PQTCApplicationHash} from "../src/libraries/PQTCApplicationHash.sol";

contract PoolMockRegistry is IPQTCVerificationRegistry {
    struct Checkpoint {
        address consumer;
        Digest512 parameterId;
        bytes32 statementKey;
        bool pending;
    }

    mapping(bytes32 => Checkpoint) internal checkpoints;

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
        checkpoints[verificationId] = Checkpoint(msg.sender, parameterId, statementKey, true);
    }

    function pending(bytes32 proofId) external view returns (bool) {
        return checkpoints[proofId].pending;
    }

    function consumer(bytes32 verificationId) external view returns (address) {
        return checkpoints[verificationId].consumer;
    }

    function completeVerification(
        bytes32 proofId,
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata proofPartB
    ) external returns (bool) {
        Checkpoint storage checkpoint = checkpoints[proofId];
        if (
            !checkpoint.pending || checkpoint.consumer != msg.sender || checkpoint.parameterId.left != parameterId.left
                || checkpoint.parameterId.right != parameterId.right
                || keccak256(proofPartB) != keccak256("valid-part-b")
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

contract PaymentReceiver {
    receive() external payable {}
}

contract RejectPayment {
    receive() external payable {
        revert();
    }
}


contract ReentrantRecipient {
    PQTCClassicPool private pool;
    bytes32 private nestedProofId;
    PQTCClassicPool.Withdrawal private nestedWithdrawal;
    bool public attempted;
    bool public nestedSucceeded;
    bytes4 public nestedError;

    function arm(PQTCClassicPool pool_, bytes32 proofId_, PQTCClassicPool.Withdrawal memory withdrawal_) external {
        pool = pool_;
        nestedProofId = proofId_;
        nestedWithdrawal = withdrawal_;
    }

    receive() external payable {
        attempted = true;
        bytes memory callData =
            abi.encodeCall(PQTCClassicPool.withdraw, (nestedWithdrawal, nestedProofId, bytes("valid-part-b")));
        bytes memory reason;
        (nestedSucceeded, reason) = address(pool).call(callData);
        if (reason.length >= 4) {
            bytes4 selector;
            assembly ("memory-safe") { selector := mload(add(reason, 0x20)) }
            nestedError = selector;
        }
    }
}

contract PQTCClassicPoolTest is Test {
    uint256 private constant DENOMINATION = 1 ether;
    bytes32 private constant PROOF_ID = keccak256("proof");
    Digest512 private parameter = Digest512(bytes32(uint256(1)), bytes32(uint256(2)));
    PoolMockRegistry private registry;
    PQTCClassicPool private pool;

    function setUp() external {
        registry = new PoolMockRegistry();
        pool = new PQTCClassicPool(DENOMINATION, parameter, registry);
        vm.deal(address(this), 10 ether);
    }

    function testDeploymentUsesCanonicalProtocolV3Scope() external view {
        assertEq(pool.PROTOCOL_VERSION(), 3);
        Digest512 memory expected = PQTCApplicationHash.scope(
            uint64(block.chainid), address(pool), DENOMINATION, pool.TREE_DEPTH(), 3, parameter
        );
        Digest512 memory actual = _scope();
        assertEq(actual.left, expected.left);
        assertEq(actual.right, expected.right);
        P2BB512.toFields(actual);
    }

    function testMerkleNodeBindsLevel() external pure {
        Digest512 memory left = Digest512(bytes32(uint256(3)), bytes32(uint256(4)));
        Digest512 memory right = Digest512(bytes32(uint256(5)), bytes32(uint256(6)));
        Digest512 memory levelZero = PQTCApplicationHash.merkleNode(0, left, right);
        Digest512 memory levelOne = PQTCApplicationHash.merkleNode(1, left, right);
        assertTrue(levelZero.left != levelOne.left || levelZero.right != levelOne.right);
    }

    function testDepositFitsOneTransactionGasGate() external {
        Digest512 memory commitment = PQTCApplicationHash.commitment(_scope(), bytes32(uint256(3)), bytes32(uint256(4)));
        uint256 gasBefore = gasleft();
        pool.deposit{value: DENOMINATION}(commitment);
        uint256 executionGas = gasBefore - gasleft();
        assertLt(executionGas, 16_500_000, "deposit exceeds one-transaction execution gas gate");
        emit log_named_uint("deposit execution gas", executionGas);
    }

    function testDepositsMatchDepthTwentyPathsAndRetainRoots() external {
        Digest512 memory first = Digest512(bytes32(uint256(3)), bytes32(uint256(4)));
        Digest512 memory second = Digest512(bytes32(uint256(5)), bytes32(uint256(6)));
        Digest512 memory initial = pool.currentRoot();

        pool.deposit{value: DENOMINATION}(first);
        Digest512 memory expectedFirst = first;
        for (uint8 level = 0; level < 20; ++level) {
            expectedFirst = PQTCApplicationHash.merkleNode(level, expectedFirst, pool.zero(level));
        }
        Digest512 memory firstRoot = pool.currentRoot();
        assertEq(firstRoot.left, expectedFirst.left);
        assertEq(firstRoot.right, expectedFirst.right);

        pool.deposit{value: DENOMINATION}(second);
        Digest512 memory expectedSecond = PQTCApplicationHash.merkleNode(0, first, second);
        for (uint8 level = 1; level < 20; ++level) {
            expectedSecond = PQTCApplicationHash.merkleNode(level, expectedSecond, pool.zero(level));
        }
        Digest512 memory secondRoot = pool.currentRoot();
        assertEq(secondRoot.left, expectedSecond.left);
        assertEq(secondRoot.right, expectedSecond.right);
        assertTrue(pool.knownRoots(initial.left, initial.right));
        assertTrue(pool.knownRoots(firstRoot.left, firstRoot.right));
        assertTrue(pool.knownRoots(secondRoot.left, secondRoot.right));
        assertTrue(pool.commitments(first.left, first.right));
        assertTrue(pool.commitments(second.left, second.right));
        assertEq(pool.nextIndex(), 2);
    }

    function testDepositRejectsWrongValueZeroDuplicateAndNoncanonicalCommitment() external {
        Digest512 memory commitment = Digest512(bytes32(uint256(3)), bytes32(uint256(4)));
        vm.expectRevert(PQTCClassicPool.IncorrectDepositValue.selector);
        pool.deposit{value: DENOMINATION - 1}(commitment);
        vm.expectRevert(PQTCClassicPool.ZeroCommitment.selector);
        pool.deposit{value: DENOMINATION}(Digest512(bytes32(0), bytes32(0)));

        Digest512 memory noncanonical = Digest512(bytes32(uint256(2_013_265_921) << 224), bytes32(uint256(1)));
        vm.expectRevert(
            abi.encodeWithSelector(P2BB512.NonCanonicalDigestLimb.selector, uint256(0), uint256(2_013_265_921))
        );
        pool.deposit{value: DENOMINATION}(noncanonical);
        pool.deposit{value: DENOMINATION}(commitment);
        vm.expectRevert(PQTCClassicPool.DuplicateCommitment.selector);
        pool.deposit{value: DENOMINATION}(commitment);
    }

    function testAtomicWithdrawalPaysRecipientAndRelayerAndPreventsDoubleSpend() external {
        Digest512 memory root = _deposit();
        PaymentReceiver recipient = new PaymentReceiver();
        PaymentReceiver relayer = new PaymentReceiver();
        Digest512 memory nullifier = Digest512(bytes32(uint256(11)), bytes32(uint256(12)));
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(relayer)),
            fee: 0.1 ether
        });
        bytes32 verificationId = _begin(withdrawal);
        assertEq(registry.consumer(verificationId), address(pool));
        assertEq(_begin(withdrawal), verificationId);
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "wrong-part-b");
        assertTrue(registry.pending(verificationId));
        assertFalse(pool.nullifiers(nullifier.left, nullifier.right));

        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        assertEq(address(recipient).balance, 0.9 ether);
        assertEq(address(relayer).balance, 0.1 ether);
        assertTrue(pool.nullifiers(nullifier.left, nullifier.right));
        assertFalse(registry.pending(verificationId));
        vm.expectRevert(PQTCClassicPool.NullifierSpent.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
    }

    function testPaymentFailureRollsBackNullifierAndVerifierCompletion() external {
        Digest512 memory root = _deposit();
        RejectPayment recipient = new RejectPayment();
        Digest512 memory nullifier = Digest512(bytes32(uint256(21)), bytes32(uint256(22)));
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: 0
        });
        bytes32 verificationId = _begin(withdrawal);

        vm.expectRevert(PQTCClassicPool.TransferFailed.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        assertFalse(pool.nullifiers(nullifier.left, nullifier.right));
        assertTrue(registry.pending(verificationId));
        assertEq(address(pool).balance, DENOMINATION);
    }

    function testWithdrawalValidationPrecedesVerification() external {
        Digest512 memory root = _deposit();
        PaymentReceiver recipient = new PaymentReceiver();
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: Digest512(bytes32(uint256(31)), bytes32(uint256(32))),
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: DENOMINATION + 1
        });
        vm.expectRevert(PQTCClassicPool.FeeExceedsDenomination.selector);
        pool.beginWithdrawal(withdrawal, "valid-part-a");
        withdrawal.fee = 1;
        vm.expectRevert(PQTCClassicPool.ZeroRelayer.selector);
        pool.beginWithdrawal(withdrawal, "valid-part-a");
        withdrawal.fee = 0;
        withdrawal.root = Digest512(bytes32(uint256(71)), bytes32(uint256(72)));
        vm.expectRevert(PQTCClassicPool.UnknownRoot.selector);
        pool.beginWithdrawal(withdrawal, "valid-part-a");
        withdrawal.root = root;
        withdrawal.recipient = payable(address(0));
        vm.expectRevert(PQTCClassicPool.ZeroRecipient.selector);
        pool.beginWithdrawal(withdrawal, "valid-part-a");
        withdrawal.recipient = payable(address(recipient));
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, PROOF_ID, "valid-part-b");
    }

    function testWithdrawalRejectsNoncanonicalRootAndNullifierAtBoundary() external {
        Digest512 memory root = _deposit();
        PaymentReceiver recipient = new PaymentReceiver();
        Digest512 memory noncanonical = Digest512(bytes32(uint256(2_013_265_921) << 224), bytes32(uint256(1)));
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: noncanonical,
            nullifierHash: Digest512(bytes32(uint256(1)), bytes32(uint256(2))),
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: 0
        });
        bytes memory expectedError =
            abi.encodeWithSelector(P2BB512.NonCanonicalDigestLimb.selector, uint256(0), uint256(2_013_265_921));
        vm.expectRevert(expectedError);
        pool.beginWithdrawal(withdrawal, "valid-part-a");

        withdrawal.root = root;
        withdrawal.nullifierHash = noncanonical;
        vm.expectRevert(expectedError);
        pool.withdraw(withdrawal, PROOF_ID, "valid-part-b");
    }

    function testReentrancyGuardBlocksNestedIndependentWithdrawal() external {
        _deposit();
        Digest512 memory root = _depositDistinct();
        ReentrantRecipient recipient = new ReentrantRecipient();
        Digest512 memory outerNullifier = Digest512(bytes32(uint256(41)), bytes32(uint256(42)));
        Digest512 memory nestedNullifier = Digest512(bytes32(uint256(43)), bytes32(uint256(44)));
        PQTCClassicPool.Withdrawal memory outer = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: outerNullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: 0
        });
        PQTCClassicPool.Withdrawal memory nested = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nestedNullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: 0
        });
        bytes32 outerProofId = _begin(outer);
        bytes32 nestedProofId = _begin(nested);
        recipient.arm(pool, nestedProofId, nested);

        pool.withdraw(outer, outerProofId, "valid-part-b");
        assertTrue(recipient.attempted());
        assertFalse(recipient.nestedSucceeded());
        assertEq(recipient.nestedError(), PQTCClassicPool.ReentrantCall.selector);
        assertFalse(pool.nullifiers(nestedNullifier.left, nestedNullifier.right));
        assertTrue(registry.pending(nestedProofId));
        assertEq(address(pool).balance, DENOMINATION);
    }

    function testCheckpointBindsExactRootNullifierRecipientRelayerAndFee() external {
        Digest512 memory initialRoot = pool.currentRoot();
        Digest512 memory root = _deposit();
        PaymentReceiver recipient = new PaymentReceiver();
        PaymentReceiver changedRecipient = new PaymentReceiver();
        PaymentReceiver relayer = new PaymentReceiver();
        PaymentReceiver changedRelayer = new PaymentReceiver();
        Digest512 memory nullifier = Digest512(bytes32(uint256(61)), bytes32(uint256(62)));
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(relayer)),
            fee: 0.1 ether
        });
        bytes32 verificationId = _begin(withdrawal);

        withdrawal.recipient = payable(address(changedRecipient));
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        withdrawal.recipient = payable(address(recipient));

        withdrawal.relayer = payable(address(changedRelayer));
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        withdrawal.relayer = payable(address(relayer));

        withdrawal.fee = 0.2 ether;
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        withdrawal.fee = 0.1 ether;

        withdrawal.root = initialRoot;
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        withdrawal.root = root;

        withdrawal.nullifierHash = Digest512(bytes32(uint256(63)), bytes32(uint256(64)));
        vm.expectRevert(PQTCClassicPool.InvalidProof.selector);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        withdrawal.nullifierHash = nullifier;

        assertTrue(registry.pending(verificationId));
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        assertEq(address(recipient).balance, 0.9 ether);
        assertEq(address(relayer).balance, 0.1 ether);
        assertTrue(pool.nullifiers(nullifier.left, nullifier.right));
    }

    function testForcedEtherCannotIncreaseWithdrawalAmount() external {
        Digest512 memory root = _deposit();
        vm.deal(address(pool), address(pool).balance + 2 ether);
        PaymentReceiver recipient = new PaymentReceiver();
        Digest512 memory nullifier = Digest512(bytes32(uint256(51)), bytes32(uint256(52)));
        PQTCClassicPool.Withdrawal memory withdrawal = PQTCClassicPool.Withdrawal({
            root: root,
            nullifierHash: nullifier,
            recipient: payable(address(recipient)),
            relayer: payable(address(0)),
            fee: 0
        });
        bytes32 verificationId = _begin(withdrawal);
        pool.withdraw(withdrawal, verificationId, "valid-part-b");
        assertEq(address(recipient).balance, DENOMINATION);
        assertEq(address(pool).balance, 2 ether);
    }

    function _begin(PQTCClassicPool.Withdrawal memory withdrawal) private returns (bytes32 verificationId) {
        return pool.beginWithdrawal(withdrawal, "valid-part-a");
    }

    function _deposit() private returns (Digest512 memory) {
        pool.deposit{value: DENOMINATION}(Digest512(bytes32(uint256(7)), bytes32(uint256(8))));
        return pool.currentRoot();
    }

    function _depositDistinct() private returns (Digest512 memory) {
        pool.deposit{value: DENOMINATION}(Digest512(bytes32(uint256(9)), bytes32(uint256(10))));
        return pool.currentRoot();
    }

    function _scope() private view returns (Digest512 memory value) {
        (value.left, value.right) = pool.scope();
    }
}
