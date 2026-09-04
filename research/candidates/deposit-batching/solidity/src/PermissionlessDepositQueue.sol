// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

interface ITransitionVerifier {
    function verify(bytes32 statementHash, bytes calldata proof) external view returns (bool);
}

/// @notice Research-only queue interface. No transition verifier is supplied by SP-12.
/// @dev This contract must not hold production funds until a trustless verifier is qualified.
contract PermissionlessDepositQueue {
    uint16 public constant MAX_BATCH = 256;
    bytes32 public constant PREFIX_DOMAIN = keccak256("PQTC.SP12.CANONICAL.PREFIX.V1");
    bytes32 public constant STATEMENT_DOMAIN = keccak256("PQTC.SP12.PUBLIC.TRANSITION.V1");

    struct Deposit {
        bytes32 commitmentLeft;
        bytes32 commitmentRight;
        address depositor;
        address refundAddress;
        uint64 enqueuedAt;
    }

    uint256 public immutable denomination;
    uint64 public immutable timeoutSeconds;
    ITransitionVerifier public immutable verifier;
    address payable public immutable destination;
    Deposit[] internal queue;
    mapping(bytes32 => mapping(bytes32 => bool)) public seenCommitments;
    uint64 public head;
    uint64 public accumulatorIndex;
    uint64 public queueEpoch;
    bytes32 public rootLeft;
    bytes32 public rootRight;
    uint256 private reentrancyState = 1;

    error InvalidConfiguration();
    error IncorrectValue();
    error InvalidCommitment();
    error DuplicateCommitment();
    error InvalidBatchSize();
    error InsufficientQueue();
    error InvalidProof();
    error TimeoutNotReached();
    error TransferFailed();
    error ReentrantCall();

    event Enqueued(uint64 indexed sequence, bytes32 indexed commitmentLeft, bytes32 indexed commitmentRight, address depositor, address refundAddress);
    event PrefixFinalized(uint64 indexed startIndex, uint16 count, bytes32 prefixCommitment, address indexed finalizer);
    event HeadRefunded(uint64 indexed sequence, address indexed refundAddress);

    modifier nonReentrant() {
        if (reentrancyState != 1) revert ReentrantCall();
        reentrancyState = 2;
        _;
        reentrancyState = 1;
    }

    constructor(
        uint256 denomination_,
        uint64 timeoutSeconds_,
        ITransitionVerifier verifier_,
        address payable destination_,
        bytes32 initialRootLeft,
        bytes32 initialRootRight
    ) {
        if (denomination_ == 0 || timeoutSeconds_ == 0 || address(verifier_) == address(0) || destination_ == address(0)) {
            revert InvalidConfiguration();
        }
        denomination = denomination_;
        timeoutSeconds = timeoutSeconds_;
        verifier = verifier_;
        destination = destination_;
        rootLeft = initialRootLeft;
        rootRight = initialRootRight;
    }

    function enqueue(bytes32 commitmentLeft, bytes32 commitmentRight, address refundAddress) external payable nonReentrant {
        if (msg.value != denomination) revert IncorrectValue();
        if ((commitmentLeft == bytes32(0) && commitmentRight == bytes32(0)) || refundAddress == address(0)) revert InvalidCommitment();
        if (seenCommitments[commitmentLeft][commitmentRight]) revert DuplicateCommitment();
        seenCommitments[commitmentLeft][commitmentRight] = true;
        uint64 sequence = uint64(queue.length);
        queue.push(Deposit(commitmentLeft, commitmentRight, msg.sender, refundAddress, uint64(block.timestamp)));
        emit Enqueued(sequence, commitmentLeft, commitmentRight, msg.sender, refundAddress);
    }

    function finalizePrefix(uint16 count, bytes32 newRootLeft, bytes32 newRootRight, bytes calldata proof) external nonReentrant {
        if (!_supportedBatch(count)) revert InvalidBatchSize();
        if (uint256(head) + count > queue.length) revert InsufficientQueue();
        bytes32 prefix = canonicalPrefix(count);
        bytes32 statement = keccak256(abi.encode(
            STATEMENT_DOMAIN, block.chainid, address(this), denomination, destination,
            rootLeft, rootRight, newRootLeft, newRootRight, prefix,
            accumulatorIndex, count, queueEpoch
        ));
        if (!verifier.verify(statement, proof)) revert InvalidProof();
        uint64 start = accumulatorIndex;
        head += count;
        accumulatorIndex += count;
        queueEpoch += 1;
        rootLeft = newRootLeft;
        rootRight = newRootRight;
        (bool paid,) = destination.call{value: uint256(count) * denomination}("");
        if (!paid) revert TransferFailed();
        emit PrefixFinalized(start, count, prefix, msg.sender);
    }

    function refundExpiredHead() external nonReentrant {
        if (head >= queue.length) revert InsufficientQueue();
        Deposit storage deposit = queue[head];
        if (block.timestamp < uint256(deposit.enqueuedAt) + timeoutSeconds) revert TimeoutNotReached();
        uint64 sequence = head;
        address payable recipient = payable(deposit.refundAddress);
        head = sequence + 1;
        queueEpoch += 1;
        (bool paid,) = recipient.call{value: denomination}("");
        if (!paid) revert TransferFailed();
        emit HeadRefunded(sequence, recipient);
    }

    function canonicalPrefix(uint16 count) public view returns (bytes32 prefix) {
        if (!_supportedBatch(count)) revert InvalidBatchSize();
        if (uint256(head) + count > queue.length) revert InsufficientQueue();
        prefix = keccak256(abi.encodePacked(PREFIX_DOMAIN, count));
        for (uint256 i; i < count; ++i) {
            Deposit storage deposit = queue[uint256(head) + i];
            prefix = keccak256(abi.encodePacked(
                prefix, uint64(uint256(head) + i), deposit.commitmentLeft, deposit.commitmentRight,
                deposit.depositor, deposit.refundAddress, deposit.enqueuedAt
            ));
        }
    }

    function pendingCount() external view returns (uint256) {
        return queue.length - head;
    }

    function _supportedBatch(uint16 count) private pure returns (bool) {
        return count == 8 || count == 16 || count == 32 || count == 64 || count == MAX_BATCH;
    }
}
