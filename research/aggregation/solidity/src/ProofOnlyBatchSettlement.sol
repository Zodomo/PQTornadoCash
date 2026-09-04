// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

struct Digest512 {
    bytes32 left;
    bytes32 right;
}

struct Withdrawal {
    Digest512 root;
    Digest512 nullifier;
    address payable recipient;
    address payable relayer;
    uint256 fee;
}

struct Payout {
    address payable recipient;
    address payable relayer;
    uint256 fee;
}

interface IRootRegistry {
    function isKnownRoot(bytes32 left, bytes32 right) external view returns (bool);
}

interface IAggregateProofVerifier {
    function verify(bytes32 batchId, bytes calldata outerProof) external view returns (bool);
}

library SP70Grid {
    function supported(uint256 count) internal pure returns (bool) {
        return count == 1 || count == 2 || count == 4 || count == 8 || count == 16 || count == 32 || count == 64;
    }
}

/// @notice Research-only proof-facing settlement shell. No accepted verifier is supplied.
/// @dev A verifier must validate N hiding individual proofs and bind every public
/// statement to batchId. Supplying a permissive verifier is unsafe and is used
/// only by the isolated gas-component test harness.
contract ProofOnlyBatchSettlement {
    bytes32 public constant STATEMENT_DOMAIN = keccak256("PQTC.SP70.PUBLIC.STATEMENT.V1");
    bytes32 public constant BATCH_DOMAIN = keccak256("PQTC.SP70.CANONICAL.BATCH.V1");

    uint256 public immutable denomination;
    IRootRegistry public immutable roots;
    IAggregateProofVerifier public immutable verifier;
    mapping(bytes32 => mapping(bytes32 => bool)) public nullifiers;
    mapping(address => uint256) public credits;
    uint256 public totalLiability;
    uint256 private reentrancyState = 1;

    error InvalidConfiguration();
    error InvalidBatchSize();
    error UnknownRoot();
    error ZeroNullifier();
    error NullifierSpent();
    error DuplicateNullifier();
    error NoncanonicalOrder();
    error ZeroRecipient();
    error FeeExceedsDenomination();
    error ZeroRelayer();
    error InvalidAggregateProof();
    error InsufficientCustody();
    error NoCredit();
    error TransferFailed();
    error ReentrantCall();

    event BatchSettled(bytes32 indexed batchId, uint256 count, address indexed aggregator);
    event CreditClaimed(address indexed payee, uint256 amount);

    constructor(uint256 denomination_, IRootRegistry roots_, IAggregateProofVerifier verifier_) {
        if (denomination_ == 0 || address(roots_) == address(0) || address(verifier_) == address(0)) {
            revert InvalidConfiguration();
        }
        denomination = denomination_;
        roots = roots_;
        verifier = verifier_;
    }

    receive() external payable {}

    function settle(Withdrawal[] calldata withdrawals, bytes calldata outerProof) external returns (bytes32 identifier) {
        identifier = _checkedBatchId(withdrawals);
        if (!verifier.verify(identifier, outerProof)) revert InvalidAggregateProof();

        uint256 addedLiability = withdrawals.length * denomination;
        if (address(this).balance < totalLiability + addedLiability) revert InsufficientCustody();
        totalLiability += addedLiability;
        for (uint256 i; i < withdrawals.length; ++i) {
            Withdrawal calldata row = withdrawals[i];
            nullifiers[row.nullifier.left][row.nullifier.right] = true;
            credits[row.recipient] += denomination - row.fee;
            if (row.fee != 0) credits[row.relayer] += row.fee;
        }
        emit BatchSettled(identifier, withdrawals.length, msg.sender);
    }

    function batchIdentifier(Withdrawal[] calldata withdrawals) external view returns (bytes32) {
        return _checkedBatchId(withdrawals);
    }

    function claim() external {
        if (reentrancyState != 1) revert ReentrantCall();
        uint256 amount = credits[msg.sender];
        if (amount == 0) revert NoCredit();
        reentrancyState = 2;
        credits[msg.sender] = 0;
        totalLiability -= amount;
        (bool paid,) = payable(msg.sender).call{value: amount}("");
        if (!paid) revert TransferFailed();
        reentrancyState = 1;
        emit CreditClaimed(msg.sender, amount);
    }

    function _checkedBatchId(Withdrawal[] calldata withdrawals) private view returns (bytes32 identifier) {
        uint256 count = withdrawals.length;
        if (!SP70Grid.supported(count)) revert InvalidBatchSize();
        identifier = keccak256(abi.encode(BATCH_DOMAIN, block.chainid, address(this), denomination, count));
        bytes32 previous;
        for (uint256 i; i < count; ++i) {
            Withdrawal calldata row = withdrawals[i];
            if (!roots.isKnownRoot(row.root.left, row.root.right)) revert UnknownRoot();
            if (row.nullifier.left == bytes32(0) && row.nullifier.right == bytes32(0)) revert ZeroNullifier();
            if (nullifiers[row.nullifier.left][row.nullifier.right]) revert NullifierSpent();
            if (row.recipient == address(0)) revert ZeroRecipient();
            if (row.fee > denomination) revert FeeExceedsDenomination();
            if (row.fee != 0 && row.relayer == address(0)) revert ZeroRelayer();
            for (uint256 j; j < i; ++j) {
                if (
                    withdrawals[j].nullifier.left == row.nullifier.left
                        && withdrawals[j].nullifier.right == row.nullifier.right
                ) revert DuplicateNullifier();
            }
            bytes32 statement = keccak256(
                abi.encode(
                    STATEMENT_DOMAIN,
                    block.chainid,
                    address(this),
                    denomination,
                    row.root.left,
                    row.root.right,
                    row.nullifier.left,
                    row.nullifier.right,
                    row.recipient,
                    row.relayer,
                    row.fee
                )
            );
            if (i != 0 && statement <= previous) revert NoncanonicalOrder();
            previous = statement;
            identifier = keccak256(abi.encode(identifier, statement));
        }
    }
}

/// @notice Isolated exact-cost harness; not a deployable withdrawal path.
contract NullifierSettlementComponent {
    mapping(bytes32 => mapping(bytes32 => bool)) public spent;

    error InvalidBatchSize();
    error ZeroNullifier();
    error NullifierSpent();
    error DuplicateNullifier();

    function consume(Digest512[] calldata values) external {
        if (!SP70Grid.supported(values.length)) revert InvalidBatchSize();
        for (uint256 i; i < values.length; ++i) {
            Digest512 calldata value = values[i];
            if (value.left == bytes32(0) && value.right == bytes32(0)) revert ZeroNullifier();
            if (spent[value.left][value.right]) revert NullifierSpent();
            for (uint256 j; j < i; ++j) {
                if (values[j].left == value.left && values[j].right == value.right) revert DuplicateNullifier();
            }
        }
        for (uint256 i; i < values.length; ++i) {
            spent[values[i].left][values[i].right] = true;
        }
    }
}

/// @notice Isolated pull-credit and claim-cost harness; not a verifier or pool.
contract PullPayoutSettlementComponent {
    uint256 public immutable denomination;
    mapping(address => uint256) public credits;

    error InvalidBatchSize();
    error InvalidPayout();
    error NoCredit();
    error TransferFailed();

    constructor(uint256 denomination_) {
        if (denomination_ == 0) revert InvalidPayout();
        denomination = denomination_;
    }

    receive() external payable {}

    function credit(Payout[] calldata payouts) external {
        if (!SP70Grid.supported(payouts.length)) revert InvalidBatchSize();
        for (uint256 i; i < payouts.length; ++i) {
            Payout calldata row = payouts[i];
            if (row.recipient == address(0) || row.fee > denomination || (row.fee != 0 && row.relayer == address(0))) {
                revert InvalidPayout();
            }
            credits[row.recipient] += denomination - row.fee;
            if (row.fee != 0) credits[row.relayer] += row.fee;
        }
    }

    function claim() external {
        uint256 amount = credits[msg.sender];
        if (amount == 0) revert NoCredit();
        credits[msg.sender] = 0;
        (bool paid,) = payable(msg.sender).call{value: amount}("");
        if (!paid) revert TransferFailed();
    }
}
