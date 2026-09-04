// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity 0.8.30;

import {Test} from "forge-std/Test.sol";
import {
    AtomicTwoCallPool,
    Digest512,
    FixedBindings,
    ITwoCallSplitVerifier,
    RobustTwoCallState
} from "../src/RobustTwoCallState.sol";

contract BindingVerifier is ITwoCallSplitVerifier {
    bytes32 private constant PART_A_DOMAIN = keccak256("PQTC.SP72.MOCK.PART.A.V1");
    bytes32 private constant PART_B_DOMAIN = keccak256("PQTC.SP72.MOCK.PART.B.V1");

    function verifyPartA(uint8 split, bytes32 key, FixedBindings calldata bindings, bytes calldata proof)
        external
        pure
        override
        returns (bool)
    {
        return proof.length == 32 && abi.decode(proof, (bytes32)) == _hash(PART_A_DOMAIN, split, key, bindings);
    }

    function verifyPartB(uint8 split, bytes32 key, FixedBindings calldata bindings, bytes calldata proof)
        external
        pure
        override
        returns (bool)
    {
        return proof.length == 32 && abi.decode(proof, (bytes32)) == _hash(PART_B_DOMAIN, split, key, bindings);
    }

    function proofA(uint8 split, bytes32 key, FixedBindings memory bindings) external pure returns (bytes memory) {
        return abi.encode(_hashMemory(PART_A_DOMAIN, split, key, bindings));
    }

    function proofB(uint8 split, bytes32 key, FixedBindings memory bindings) external pure returns (bytes memory) {
        return abi.encode(_hashMemory(PART_B_DOMAIN, split, key, bindings));
    }

    function _hash(bytes32 domain, uint8 split, bytes32 key, FixedBindings calldata b)
        private
        pure
        returns (bytes32)
    {
        return keccak256(
            abi.encode(
                domain,
                split,
                key,
                b.statement.left,
                b.statement.right,
                b.globalData.left,
                b.globalData.right,
                b.checkpoint.left,
                b.checkpoint.right,
                b.proof.left,
                b.proof.right,
                b.continuation.left,
                b.continuation.right,
                b.root.left,
                b.root.right
            )
        );
    }

    function _hashMemory(bytes32 domain, uint8 split, bytes32 key, FixedBindings memory b)
        private
        pure
        returns (bytes32)
    {
        return keccak256(
            abi.encode(
                domain,
                split,
                key,
                b.statement.left,
                b.statement.right,
                b.globalData.left,
                b.globalData.right,
                b.checkpoint.left,
                b.checkpoint.right,
                b.proof.left,
                b.proof.right,
                b.continuation.left,
                b.continuation.right,
                b.root.left,
                b.root.right
            )
        );
    }
}

contract RevertingRecipient {
    receive() external payable {
        revert("payment rejected");
    }
}

contract ReentrantRecipient {
    address public target;
    bytes public payload;
    bool public attempted;
    bool public reentrySucceeded;

    function arm(address target_, bytes calldata payload_) external {
        target = target_;
        payload = payload_;
    }

    receive() external payable {
        attempted = true;
        (reentrySucceeded,) = target.call(payload);
    }
}

contract RobustTwoCallStateTest is Test {
    uint8 private constant SPLIT = 12;
    uint64 private constant TTL = 20;
    uint256 private constant AMOUNT = 1 ether;

    BindingVerifier private verifier;
    AtomicTwoCallPool private pool;
    RobustTwoCallState private machine;
    Digest512 private nullifier;
    Digest512 private root;
    Digest512 private root2;
    Digest512 private globalData;
    Digest512 private checkpointDigest;
    Digest512 private proofDigest;
    Digest512 private continuationDigest;
    address payable private recipient = payable(address(0xBEEF));

    function setUp() external {
        verifier = new BindingVerifier();
        pool = new AtomicTwoCallPool(address(this), verifier, TTL, SPLIT);
        machine = pool.stateMachine();
        nullifier = _digest(1);
        root = _digest(101);
        root2 = _digest(201);
        globalData = _digest(301);
        checkpointDigest = _digest(401);
        proofDigest = _digest(501);
        continuationDigest = _digest(601);
        pool.installRoot(root);
        pool.installRoot(root2);
        vm.deal(address(pool), 100 ether);
    }

    /// many valid Part A proofs for one note with different hiding randomness
    function testAttack_ManyValidPartAForOneNoteHasOneLiveCheckpoint() external {
        _begin(recipient, root, proofDigest, continuationDigest);
        Digest512 memory alternateProofDigest = _digest(502);
        (bytes32 key, FixedBindings memory alternate, bytes memory proofA) =
            _partA(recipient, root, alternateProofDigest, continuationDigest);
        vm.expectRevert(RobustTwoCallState.ActiveCheckpoint.selector);
        _callBegin(recipient, root, alternateProofDigest, continuationDigest, proofA);
        assertTrue(machine.isActive(key));
        assertEq(machine.activeCheckpointCount(), 1);
    }

    /// direct registry calls by arbitrary consumers
    function testAttack_DirectRegistryCallByArbitraryConsumerRejected() external {
        (bytes32 key, FixedBindings memory bindings, bytes memory proofA) =
            _partA(recipient, root, proofDigest, continuationDigest);
        vm.expectRevert(RobustTwoCallState.UnauthorizedConsumer.selector);
        machine.begin(key, bindings, proofA);
    }

    /// expired proof replay
    function testAttack_ExpiredProofReplayRejectedBeforeAndAfterCleanup() external {
        (bytes32 key,,) = _begin(recipient, root, proofDigest, continuationDigest);
        vm.roll(block.number + TTL);
        bytes memory proofB = _proofB(recipient, root, proofDigest, continuationDigest);
        vm.expectRevert(RobustTwoCallState.CheckpointExpired.selector);
        _callComplete(recipient, root, proofDigest, continuationDigest, proofB);
        machine.cleanup(key);
        vm.expectRevert(RobustTwoCallState.UnknownCheckpoint.selector);
        _callComplete(recipient, root, proofDigest, continuationDigest, proofB);
    }

    /// replacement races
    function testAttack_ReplacementRaceFirstValidReplacementWins() external {
        _begin(recipient, root, proofDigest, continuationDigest);
        vm.roll(block.number + TTL);
        Digest512 memory replacementProof = _digest(503);
        Digest512 memory replacementContinuation = _digest(603);
        _begin(recipient, root2, replacementProof, replacementContinuation);

        Digest512 memory racingProof = _digest(504);
        (,, bytes memory proofA) = _partA(recipient, root2, racingProof, replacementContinuation);
        vm.expectRevert(RobustTwoCallState.ActiveCheckpoint.selector);
        _callBegin(recipient, root2, racingProof, replacementContinuation, proofA);
        assertEq(machine.activeCheckpointCount(), 1);
        assertEq(machine.rootPinCount(root), 0);
        assertEq(machine.rootPinCount(root2), 1);
    }

    /// exact Part A front-run
    function testAttack_ExactPartAFrontRunIsIdempotentAndCannotRedirectPayment() external {
        (bytes32 key, FixedBindings memory bindings, bytes memory proofA) =
            _partA(recipient, root, proofDigest, continuationDigest);
        address attacker = address(0xA11CE);
        vm.prank(attacker);
        (, uint64 firstExpiry) = _callBegin(recipient, root, proofDigest, continuationDigest, proofA);
        (, uint64 secondExpiry) = _callBegin(recipient, root, proofDigest, continuationDigest, proofA);
        assertEq(firstExpiry, secondExpiry);
        assertEq(machine.activeCheckpointCount(), 1);

        bytes memory proofB = verifier.proofB(SPLIT, key, bindings);
        uint256 beforeBalance = recipient.balance;
        _callComplete(recipient, root, proofDigest, continuationDigest, proofB);
        assertEq(recipient.balance, beforeBalance + AMOUNT);
    }

    /// mixed A/B proofs
    function testAttack_MixedPartAAndPartBProofsRejectedWithoutDeletingState() external {
        (bytes32 key,,) = _begin(recipient, root, proofDigest, continuationDigest);
        Digest512 memory otherContinuation = _digest(604);
        bytes memory otherProofB = _proofB(recipient, root, proofDigest, otherContinuation);
        vm.expectRevert(RobustTwoCallState.BindingMismatch.selector);
        _callComplete(recipient, root, proofDigest, otherContinuation, otherProofB);
        assertTrue(machine.isActive(key));
        assertFalse(pool.nullifierSpent(key));
    }

    /// root aging
    function testAttack_RootAgingBlockedWhilePinnedThenAllowedAfterExpiryCleanup() external {
        (bytes32 key,,) = _begin(recipient, root, proofDigest, continuationDigest);
        vm.expectRevert(AtomicTwoCallPool.RootPinned.selector);
        pool.ageRoot(root);
        vm.roll(block.number + TTL);
        machine.cleanup(key);
        pool.ageRoot(root);
        assertFalse(pool.knownRoots(machine.digestKey(root)));
    }

    /// B payment revert
    function testAttack_PaymentRevertRollsBackVerificationAndNullifier() external {
        RevertingRecipient rejector = new RevertingRecipient();
        address payable rejectingRecipient = payable(address(rejector));
        (bytes32 key,,) = _begin(rejectingRecipient, root, proofDigest, continuationDigest);
        bytes memory proofB = _proofB(rejectingRecipient, root, proofDigest, continuationDigest);
        vm.expectRevert(AtomicTwoCallPool.PaymentFailed.selector);
        _callComplete(rejectingRecipient, root, proofDigest, continuationDigest, proofB);
        assertTrue(machine.isActive(key));
        assertFalse(pool.nullifierSpent(key));
        assertEq(machine.rootPinCount(root), 1);
    }

    /// reentrancy
    function testAttack_ReentrantPaymentCannotCompleteTwice() external {
        ReentrantRecipient receiver = new ReentrantRecipient();
        address payable reentrantRecipient = payable(address(receiver));
        (bytes32 key,,) = _begin(reentrantRecipient, root, proofDigest, continuationDigest);
        bytes memory proofB = _proofB(reentrantRecipient, root, proofDigest, continuationDigest);
        bytes memory reentry = abi.encodeCall(
            pool.completeWithdrawal,
            (
                nullifier,
                root,
                reentrantRecipient,
                AMOUNT,
                globalData,
                checkpointDigest,
                proofDigest,
                continuationDigest,
                proofB
            )
        );
        receiver.arm(address(pool), reentry);
        _callComplete(reentrantRecipient, root, proofDigest, continuationDigest, proofB);
        assertTrue(receiver.attempted());
        assertFalse(receiver.reentrySucceeded());
        assertTrue(pool.nullifierSpent(key));
        assertFalse(machine.isActive(key));
        assertEq(address(receiver).balance, AMOUNT);
    }

    /// cleanup front-running
    function testAttack_CleanupFrontRunFailsBeforeExpiryAndCannotBlockReplacement() external {
        (bytes32 key,,) = _begin(recipient, root, proofDigest, continuationDigest);
        address cleaner = address(0xC1EA);
        vm.prank(cleaner);
        vm.expectRevert(RobustTwoCallState.CheckpointNotExpired.selector);
        machine.cleanup(key);
        assertTrue(machine.isActive(key));

        vm.roll(block.number + TTL);
        vm.prank(cleaner);
        machine.cleanup(key);
        Digest512 memory replacementProof = _digest(505);
        _begin(recipient, root2, replacementProof, continuationDigest);
        assertEq(machine.activeCheckpointCount(), 1);
    }

    function testMeasureRetainedHarnessOverhead() external {
        (bytes32 key,, bytes memory proofA) = _partA(recipient, root, proofDigest, continuationDigest);
        uint256 beforePartA = gasleft();
        _callBegin(recipient, root, proofDigest, continuationDigest, proofA);
        uint256 partAGas = beforePartA - gasleft();

        bytes memory proofB = _proofB(recipient, root, proofDigest, continuationDigest);
        uint256 beforePartB = gasleft();
        _callComplete(recipient, root, proofDigest, continuationDigest, proofB);
        uint256 partBGas = beforePartB - gasleft();

        nullifier = _digest(2);
        (bytes32 cleanupKey,, bytes memory cleanupProofA) =
            _partA(recipient, root2, proofDigest, continuationDigest);
        _callBegin(recipient, root2, proofDigest, continuationDigest, cleanupProofA);
        vm.roll(block.number + TTL);
        uint256 beforeCleanup = gasleft();
        machine.cleanup(cleanupKey);
        uint256 cleanupGas = beforeCleanup - gasleft();

        string memory object = "sp72";
        vm.serializeString(object, "schema", "sp72-foundry-harness-gas-v1");
        vm.serializeString(object, "measurement_class", "EXACT_FOUNDRY_GASLEFT_DELTA");
        vm.serializeString(object, "scope", "state harness plus binding mock; excludes v0.3 verifier");
        vm.serializeUint(object, "part_a_gas", partAGas);
        vm.serializeUint(object, "part_b_gross_gas", partBGas);
        string memory json = vm.serializeUint(object, "cleanup_gross_gas", cleanupGas);
        vm.writeJson(json, "../outputs/harness-gas.json");
        assertFalse(machine.isActive(key));
    }

    function testInvariant_FixedCheckpointHasThirteenStructSlotsAndNoProofBytes() external {
        (bytes32 key, FixedBindings memory bindings,) = _begin(recipient, root, proofDigest, continuationDigest);
        RobustTwoCallState.Checkpoint memory saved = machine.checkpoint(key);
        assertEq(saved.split, SPLIT);
        assertEq(saved.statement.left, bindings.statement.left);
        assertEq(saved.statement.right, bindings.statement.right);
        assertEq(saved.proof.left, proofDigest.left);
        assertEq(saved.proof.right, proofDigest.right);
        assertEq(saved.continuation.left, continuationDigest.left);
        assertEq(saved.continuation.right, continuationDigest.right);
    }

    function _begin(
        address payable paymentRecipient,
        Digest512 memory selectedRoot,
        Digest512 memory selectedProofDigest,
        Digest512 memory selectedContinuation
    ) private returns (bytes32 key, FixedBindings memory bindings, bytes memory proofA) {
        (key, bindings, proofA) =
            _partA(paymentRecipient, selectedRoot, selectedProofDigest, selectedContinuation);
        _callBegin(paymentRecipient, selectedRoot, selectedProofDigest, selectedContinuation, proofA);
    }

    function _partA(
        address payable paymentRecipient,
        Digest512 memory selectedRoot,
        Digest512 memory selectedProofDigest,
        Digest512 memory selectedContinuation
    ) private view returns (bytes32 key, FixedBindings memory bindings, bytes memory proofA) {
        key = machine.nullifierKey(nullifier);
        bindings = pool.expectedBindings(
            nullifier,
            selectedRoot,
            paymentRecipient,
            AMOUNT,
            globalData,
            checkpointDigest,
            selectedProofDigest,
            selectedContinuation
        );
        proofA = verifier.proofA(SPLIT, key, bindings);
    }

    function _proofB(
        address payable paymentRecipient,
        Digest512 memory selectedRoot,
        Digest512 memory selectedProofDigest,
        Digest512 memory selectedContinuation
    ) private view returns (bytes memory) {
        bytes32 key = machine.nullifierKey(nullifier);
        FixedBindings memory bindings = pool.expectedBindings(
            nullifier,
            selectedRoot,
            paymentRecipient,
            AMOUNT,
            globalData,
            checkpointDigest,
            selectedProofDigest,
            selectedContinuation
        );
        return verifier.proofB(SPLIT, key, bindings);
    }

    function _callBegin(
        address payable paymentRecipient,
        Digest512 memory selectedRoot,
        Digest512 memory selectedProofDigest,
        Digest512 memory selectedContinuation,
        bytes memory proofA
    ) private returns (bytes32 key, uint64 expiresAt) {
        return pool.beginWithdrawal(
            nullifier,
            selectedRoot,
            paymentRecipient,
            AMOUNT,
            globalData,
            checkpointDigest,
            selectedProofDigest,
            selectedContinuation,
            proofA
        );
    }

    function _callComplete(
        address payable paymentRecipient,
        Digest512 memory selectedRoot,
        Digest512 memory selectedProofDigest,
        Digest512 memory selectedContinuation,
        bytes memory proofB
    ) private {
        pool.completeWithdrawal(
            nullifier,
            selectedRoot,
            paymentRecipient,
            AMOUNT,
            globalData,
            checkpointDigest,
            selectedProofDigest,
            selectedContinuation,
            proofB
        );
    }

    function _digest(uint256 seed) private pure returns (Digest512 memory) {
        return Digest512(bytes32(seed), bytes32(seed + 1));
    }
}
