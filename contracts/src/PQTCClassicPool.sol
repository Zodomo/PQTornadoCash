// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Digest512, Digest512Lib} from "./libraries/Digest512.sol";
import {P2BB512} from "./libraries/P2BB512.sol";
import {PQTCApplicationHash} from "./libraries/PQTCApplicationHash.sol";

interface IPQTCVerificationRegistry {
    function beginVerification(
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata proofPartA
    ) external returns (bytes32 verificationId);

    function completeVerification(
        bytes32 verificationId,
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata proofPartB
    ) external returns (bool);
}

/// Fixed-denomination, append-only, depth-20 native-ETH mixer pool.
/// The verification registry, parameter ID, denomination, and scope never change.
contract PQTCClassicPool {
    using Digest512Lib for Digest512;

    uint8 public constant TREE_DEPTH = 20;
    uint32 public constant PROTOCOL_VERSION = 3;
    uint32 public constant CAPACITY = uint32(1) << TREE_DEPTH;

    uint256 public immutable denomination;
    IPQTCVerificationRegistry public immutable verificationRegistry;
    Digest512 public scope;
    Digest512 public parameterId;
    uint32 public nextIndex;
    Digest512[20] internal filledSubtrees;
    Digest512[21] internal zeros;

    mapping(bytes32 => mapping(bytes32 => bool)) public commitments;
    mapping(bytes32 => mapping(bytes32 => bool)) public nullifiers;
    mapping(bytes32 => mapping(bytes32 => bool)) public knownRoots;

    uint256 private reentrancyState = 1;

    struct Withdrawal {
        Digest512 root;
        Digest512 nullifierHash;
        address payable recipient;
        address payable relayer;
        uint256 fee;
    }

    event Deposit(
        bytes32 indexed commitmentLeft,
        bytes32 indexed commitmentRight,
        uint32 leafIndex,
        bytes32 rootLeft,
        bytes32 rootRight,
        uint256 timestamp
    );
    event WithdrawalComplete(
        bytes32 indexed nullifierLeft,
        bytes32 indexed nullifierRight,
        address indexed recipient,
        address relayer,
        uint256 fee
    );

    error ReentrantCall();
    error InvalidDenomination();
    error InvalidDependency();
    error IncorrectDepositValue();
    error ZeroCommitment();
    error DuplicateCommitment();
    error TreeFull();
    error UnknownRoot();
    error NullifierSpent();
    error ZeroRecipient();
    error FeeExceedsDenomination();
    error ZeroRelayer();
    error InvalidProof();
    error TransferFailed();

    modifier nonReentrant() {
        if (reentrancyState != 1) revert ReentrantCall();
        reentrancyState = 2;
        _;
        reentrancyState = 1;
    }

    constructor(uint256 denomination_, Digest512 memory parameterId_, IPQTCVerificationRegistry verificationRegistry_) {
        if (denomination_ == 0) revert InvalidDenomination();
        if (parameterId_.isZero()) revert InvalidDependency();
        if (address(verificationRegistry_) == address(0)) revert InvalidDependency();
        denomination = denomination_;
        parameterId = parameterId_;
        verificationRegistry = verificationRegistry_;
        scope = PQTCApplicationHash.scope(
            uint64(block.chainid), address(this), denomination_, TREE_DEPTH, PROTOCOL_VERSION, parameterId_
        );

        zeros[0] = PQTCApplicationHash.emptyLeaf(scope);
        for (uint8 level = 0; level < TREE_DEPTH; level++) {
            filledSubtrees[level] = zeros[level];
            zeros[level + 1] = PQTCApplicationHash.merkleNode(level, zeros[level], zeros[level]);
        }
        Digest512 memory initialRoot = zeros[TREE_DEPTH];
        latestRoot = initialRoot;
        knownRoots[initialRoot.left][initialRoot.right] = true;
    }

    function deposit(Digest512 calldata commitment) external payable nonReentrant {
        if (msg.value != denomination) revert IncorrectDepositValue();
        P2BB512.toFields(commitment);
        if (commitment.left == bytes32(0) && commitment.right == bytes32(0)) revert ZeroCommitment();
        if (commitments[commitment.left][commitment.right]) revert DuplicateCommitment();
        uint32 leafIndex = nextIndex;
        if (leafIndex >= CAPACITY) revert TreeFull();

        Digest512 memory current = commitment;
        uint32 index = leafIndex;
        for (uint8 level = 0; level < TREE_DEPTH; level++) {
            if (index & 1 == 0) {
                filledSubtrees[level] = current;
                current = PQTCApplicationHash.merkleNode(level, current, zeros[level]);
            } else {
                current = PQTCApplicationHash.merkleNode(level, filledSubtrees[level], current);
            }
            index >>= 1;
        }

        commitments[commitment.left][commitment.right] = true;
        knownRoots[current.left][current.right] = true;
        nextIndex = leafIndex + 1;
        latestRoot = current;
        emit Deposit(commitment.left, commitment.right, leafIndex, current.left, current.right, block.timestamp);
    }

    function beginWithdrawal(Withdrawal calldata withdrawal, bytes calldata proofPartA)
        external
        nonReentrant
        returns (bytes32 verificationId)
    {
        uint32[64] memory values = _validatedPublicValues(withdrawal);
        return verificationRegistry.beginVerification(parameterId, values, proofPartA);
    }

    function withdraw(Withdrawal calldata withdrawal, bytes32 verificationId, bytes calldata proofPartB)
        external
        nonReentrant
    {
        uint32[64] memory values = _validatedPublicValues(withdrawal);
        if (!verificationRegistry.completeVerification(verificationId, parameterId, values, proofPartB)) {
            revert InvalidProof();
        }
        _completeWithdrawal(withdrawal);
    }

    function currentRoot() external view returns (Digest512 memory) {
        return latestRoot;
    }

    function zero(uint8 level) external view returns (Digest512 memory) {
        if (level > TREE_DEPTH) revert UnknownRoot();
        return zeros[level];
    }

    function _completeWithdrawal(Withdrawal calldata withdrawal) private {
        nullifiers[withdrawal.nullifierHash.left][withdrawal.nullifierHash.right] = true;
        uint256 recipientAmount = denomination - withdrawal.fee;
        (bool recipientPaid,) = withdrawal.recipient.call{value: recipientAmount}("");
        if (!recipientPaid) revert TransferFailed();
        if (withdrawal.fee != 0) {
            (bool relayerPaid,) = withdrawal.relayer.call{value: withdrawal.fee}("");
            if (!relayerPaid) revert TransferFailed();
        }
        emit WithdrawalComplete(
            withdrawal.nullifierHash.left,
            withdrawal.nullifierHash.right,
            withdrawal.recipient,
            withdrawal.relayer,
            withdrawal.fee
        );
    }

    function _validatedPublicValues(Withdrawal calldata withdrawal) private view returns (uint32[64] memory values) {
        uint32[16] memory rootFields = P2BB512.toFields(withdrawal.root);
        uint32[16] memory nullifierFields = P2BB512.toFields(withdrawal.nullifierHash);
        if (!knownRoots[withdrawal.root.left][withdrawal.root.right]) revert UnknownRoot();
        if (nullifiers[withdrawal.nullifierHash.left][withdrawal.nullifierHash.right]) revert NullifierSpent();
        if (withdrawal.recipient == address(0)) revert ZeroRecipient();
        if (withdrawal.fee > denomination) revert FeeExceedsDenomination();
        if (withdrawal.fee != 0 && withdrawal.relayer == address(0)) revert ZeroRelayer();
        Digest512 memory payout =
            PQTCApplicationHash.payoutDigest(withdrawal.recipient, withdrawal.relayer, withdrawal.fee);
        return _publicValues(rootFields, nullifierFields, payout);
    }

    function _publicValues(uint32[16] memory rootFields, uint32[16] memory nullifierFields, Digest512 memory payout)
        private
        view
        returns (uint32[64] memory values)
    {
        uint32[16] memory scopeFields = P2BB512.toFields(scope);
        uint32[16] memory payoutFields = P2BB512.toFields(payout);
        for (uint256 limb = 0; limb < 16; ++limb) {
            values[limb] = scopeFields[limb];
            values[16 + limb] = rootFields[limb];
            values[32 + limb] = nullifierFields[limb];
            values[48 + limb] = payoutFields[limb];
        }
    }

    // `knownRoots` intentionally retains all history. Track the latest root separately
    // without adding another public storage mapping lookup in deposits.
    Digest512 private latestRoot;
}
