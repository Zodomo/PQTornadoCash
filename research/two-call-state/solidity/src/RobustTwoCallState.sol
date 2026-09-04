// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity 0.8.30;

struct Digest512 {
    bytes32 left;
    bytes32 right;
}

struct FixedBindings {
    Digest512 statement;
    Digest512 globalData;
    Digest512 checkpoint;
    Digest512 proof;
    Digest512 continuation;
    Digest512 root;
}

interface ITwoCallSplitVerifier {
    function verifyPartA(uint8 split, bytes32 nullifierKey, FixedBindings calldata bindings, bytes calldata proof)
        external
        returns (bool);

    function verifyPartB(uint8 split, bytes32 nullifierKey, FixedBindings calldata bindings, bytes calldata proof)
        external
        returns (bool);
}

/// @notice Research-only fixed-state continuation registry. It does not implement a proof system.
/// @dev The sole immutable consumer reconstructs statements and performs value movement in the same
///      transaction as complete(). No proof bytes or reusable verification fact are retained.
contract RobustTwoCallState {
    uint8 public constant MIN_SPLIT = 8;
    uint8 public constant MAX_SPLIT = 16;
    bytes32 public constant NULLIFIER_KEY_DOMAIN = keccak256("PQTC.SP72.NULLIFIER.KEY.V1");

    struct Checkpoint {
        uint64 createdAt;
        uint64 expiresAt;
        uint8 split;
        Digest512 statement;
        Digest512 globalData;
        Digest512 checkpoint;
        Digest512 proof;
        Digest512 continuation;
        Digest512 root;
    }

    address public immutable consumer;
    ITwoCallSplitVerifier public immutable verifier;
    uint64 public immutable ttlBlocks;
    uint8 public immutable split;

    mapping(bytes32 nullifierKey => Checkpoint value) private checkpoints;
    mapping(bytes32 rootKey => uint64 count) private rootPinCounts;
    uint256 public activeCheckpointCount;

    error InvalidConfiguration();
    error UnauthorizedConsumer();
    error InvalidBinding();
    error ActiveCheckpoint();
    error UnknownCheckpoint();
    error CheckpointExpired();
    error CheckpointNotExpired();
    error BindingMismatch();
    error InvalidProof();

    event CheckpointStarted(bytes32 indexed nullifierKey, bytes32 indexed rootKey, uint64 expiresAt);
    event CheckpointCompleted(bytes32 indexed nullifierKey, bytes32 indexed rootKey);
    event CheckpointCleaned(bytes32 indexed nullifierKey, bytes32 indexed rootKey, address indexed cleaner);
    event CheckpointReplaced(bytes32 indexed nullifierKey, bytes32 indexed oldRootKey, bytes32 indexed newRootKey);

    modifier onlyConsumer() {
        if (msg.sender != consumer) revert UnauthorizedConsumer();
        _;
    }

    constructor(address consumer_, ITwoCallSplitVerifier verifier_, uint64 ttlBlocks_, uint8 split_) {
        if (
            consumer_ == address(0) || address(verifier_) == address(0) || ttlBlocks_ == 0 || split_ < MIN_SPLIT
                || split_ > MAX_SPLIT
        ) revert InvalidConfiguration();
        consumer = consumer_;
        verifier = verifier_;
        ttlBlocks = ttlBlocks_;
        split = split_;
    }

    function begin(bytes32 nullifierKey, FixedBindings calldata bindings, bytes calldata proofPartA)
        external
        onlyConsumer
        returns (uint64 expiresAt)
    {
        _requireBinding(bindings);
        Checkpoint storage current = checkpoints[nullifierKey];
        if (current.expiresAt != 0) {
            if (block.number < current.expiresAt) {
                if (!_same(current, bindings)) revert ActiveCheckpoint();
                return current.expiresAt;
            }
            bytes32 oldRootKey = digestKey(current.root);
            _erase(nullifierKey, current);
            emit CheckpointReplaced(nullifierKey, oldRootKey, digestKey(bindings.root));
        }

        if (!verifier.verifyPartA(split, nullifierKey, bindings, proofPartA)) revert InvalidProof();
        uint256 expiry = block.number + ttlBlocks;
        if (expiry > type(uint64).max) revert InvalidConfiguration();
        expiresAt = uint64(expiry);
        _store(current, bindings, expiresAt);
        bytes32 rootKey = digestKey(bindings.root);
        ++rootPinCounts[rootKey];
        ++activeCheckpointCount;
        emit CheckpointStarted(nullifierKey, rootKey, expiresAt);
    }

    function complete(bytes32 nullifierKey, FixedBindings calldata bindings, bytes calldata proofPartB)
        external
        onlyConsumer
        returns (bool)
    {
        Checkpoint storage current = checkpoints[nullifierKey];
        if (current.expiresAt == 0) revert UnknownCheckpoint();
        if (block.number >= current.expiresAt) revert CheckpointExpired();
        if (!_same(current, bindings)) revert BindingMismatch();
        if (!verifier.verifyPartB(split, nullifierKey, bindings, proofPartB)) revert InvalidProof();

        bytes32 rootKey = digestKey(current.root);
        _erase(nullifierKey, current);
        emit CheckpointCompleted(nullifierKey, rootKey);
        return true;
    }

    function cleanup(bytes32 nullifierKey) external {
        Checkpoint storage current = checkpoints[nullifierKey];
        if (current.expiresAt == 0) revert UnknownCheckpoint();
        if (block.number < current.expiresAt) revert CheckpointNotExpired();
        bytes32 rootKey = digestKey(current.root);
        _erase(nullifierKey, current);
        emit CheckpointCleaned(nullifierKey, rootKey, msg.sender);
    }

    function checkpoint(bytes32 nullifierKey) external view returns (Checkpoint memory) {
        return checkpoints[nullifierKey];
    }

    function isActive(bytes32 nullifierKey) public view returns (bool) {
        uint64 expiresAt = checkpoints[nullifierKey].expiresAt;
        return expiresAt != 0 && block.number < expiresAt;
    }

    function rootPinCount(Digest512 calldata root) external view returns (uint64) {
        return rootPinCounts[digestKey(root)];
    }

    function isRootPinned(Digest512 calldata root) external view returns (bool) {
        return rootPinCounts[digestKey(root)] != 0;
    }

    function digestKey(Digest512 memory digest) public pure returns (bytes32) {
        return keccak256(abi.encode(digest.left, digest.right));
    }

    function nullifierKey(Digest512 memory nullifier) public pure returns (bytes32) {
        return keccak256(abi.encode(NULLIFIER_KEY_DOMAIN, nullifier.left, nullifier.right));
    }

    function _store(Checkpoint storage target, FixedBindings calldata bindings, uint64 expiresAt) private {
        target.createdAt = uint64(block.number);
        target.expiresAt = expiresAt;
        target.split = split;
        target.statement = bindings.statement;
        target.globalData = bindings.globalData;
        target.checkpoint = bindings.checkpoint;
        target.proof = bindings.proof;
        target.continuation = bindings.continuation;
        target.root = bindings.root;
    }

    function _erase(bytes32 nullifierKey, Checkpoint storage current) private {
        bytes32 rootKey = digestKey(current.root);
        delete checkpoints[nullifierKey];
        --rootPinCounts[rootKey];
        --activeCheckpointCount;
    }

    function _same(Checkpoint storage current, FixedBindings calldata bindings) private view returns (bool) {
        return current.split == split && _eq(current.statement, bindings.statement)
            && _eq(current.globalData, bindings.globalData) && _eq(current.checkpoint, bindings.checkpoint)
            && _eq(current.proof, bindings.proof) && _eq(current.continuation, bindings.continuation)
            && _eq(current.root, bindings.root);
    }

    function _eq(Digest512 storage a, Digest512 calldata b) private view returns (bool) {
        return a.left == b.left && a.right == b.right;
    }

    function _requireBinding(FixedBindings calldata bindings) private pure {
        if (
            _zero(bindings.statement) || _zero(bindings.globalData) || _zero(bindings.checkpoint)
                || _zero(bindings.proof) || _zero(bindings.continuation) || _zero(bindings.root)
        ) revert InvalidBinding();
    }

    function _zero(Digest512 calldata value) private pure returns (bool) {
        return value.left == bytes32(0) && value.right == bytes32(0);
    }
}

/// @notice Research consumer proving root pinning and atomic verification/nullifier/payment behavior.
contract AtomicTwoCallPool {
    bytes32 public constant STATEMENT_LEFT_DOMAIN = keccak256("PQTC.SP72.STATEMENT.LEFT.V1");
    bytes32 public constant STATEMENT_RIGHT_DOMAIN = keccak256("PQTC.SP72.STATEMENT.RIGHT.V1");

    address public immutable rootAuthority;
    RobustTwoCallState public immutable stateMachine;
    mapping(bytes32 rootKey => bool known) public knownRoots;
    mapping(bytes32 nullifierKey => bool spent) public nullifierSpent;
    uint256 private reentrancyState = 1;

    error UnauthorizedRootAuthority();
    error UnknownRoot();
    error RootPinned();
    error NullifierAlreadySpent();
    error InvalidWithdrawal();
    error PaymentFailed();
    error ReentrantCall();

    event RootInstalled(bytes32 indexed rootKey);
    event RootAged(bytes32 indexed rootKey);
    event WithdrawalCompleted(bytes32 indexed nullifierKey, address indexed recipient, uint256 amount);

    modifier onlyRootAuthority() {
        if (msg.sender != rootAuthority) revert UnauthorizedRootAuthority();
        _;
    }

    modifier nonReentrant() {
        if (reentrancyState != 1) revert ReentrantCall();
        reentrancyState = 2;
        _;
        reentrancyState = 1;
    }

    constructor(address rootAuthority_, ITwoCallSplitVerifier verifier_, uint64 ttlBlocks_, uint8 split_) {
        if (rootAuthority_ == address(0)) revert InvalidWithdrawal();
        rootAuthority = rootAuthority_;
        stateMachine = new RobustTwoCallState(address(this), verifier_, ttlBlocks_, split_);
    }

    receive() external payable {}

    function installRoot(Digest512 calldata root) external onlyRootAuthority {
        bytes32 key = stateMachine.digestKey(root);
        knownRoots[key] = true;
        emit RootInstalled(key);
    }

    function ageRoot(Digest512 calldata root) external onlyRootAuthority {
        bytes32 key = stateMachine.digestKey(root);
        if (!knownRoots[key]) revert UnknownRoot();
        if (stateMachine.isRootPinned(root)) revert RootPinned();
        delete knownRoots[key];
        emit RootAged(key);
    }

    function beginWithdrawal(
        Digest512 calldata nullifier,
        Digest512 calldata root,
        address payable recipient,
        uint256 amount,
        Digest512 calldata globalData,
        Digest512 calldata checkpointDigest,
        Digest512 calldata proofDigest,
        Digest512 calldata continuationDigest,
        bytes calldata proofPartA
    ) external nonReentrant returns (bytes32 key, uint64 expiresAt) {
        if (recipient == address(0) || amount == 0) revert InvalidWithdrawal();
        if (!knownRoots[stateMachine.digestKey(root)]) revert UnknownRoot();
        key = stateMachine.nullifierKey(nullifier);
        if (nullifierSpent[key]) revert NullifierAlreadySpent();
        FixedBindings memory bindings = _bindings(
            nullifier, root, recipient, amount, globalData, checkpointDigest, proofDigest, continuationDigest
        );
        expiresAt = stateMachine.begin(key, bindings, proofPartA);
    }

    function completeWithdrawal(
        Digest512 calldata nullifier,
        Digest512 calldata root,
        address payable recipient,
        uint256 amount,
        Digest512 calldata globalData,
        Digest512 calldata checkpointDigest,
        Digest512 calldata proofDigest,
        Digest512 calldata continuationDigest,
        bytes calldata proofPartB
    ) external nonReentrant {
        bytes32 key = stateMachine.nullifierKey(nullifier);
        if (nullifierSpent[key]) revert NullifierAlreadySpent();
        FixedBindings memory bindings = _bindings(
            nullifier, root, recipient, amount, globalData, checkpointDigest, proofDigest, continuationDigest
        );
        stateMachine.complete(key, bindings, proofPartB);
        nullifierSpent[key] = true;
        (bool paid,) = recipient.call{value: amount}("");
        if (!paid) revert PaymentFailed();
        emit WithdrawalCompleted(key, recipient, amount);
    }

    function expectedBindings(
        Digest512 calldata nullifier,
        Digest512 calldata root,
        address recipient,
        uint256 amount,
        Digest512 calldata globalData,
        Digest512 calldata checkpointDigest,
        Digest512 calldata proofDigest,
        Digest512 calldata continuationDigest
    ) external view returns (FixedBindings memory) {
        return _bindings(nullifier, root, recipient, amount, globalData, checkpointDigest, proofDigest, continuationDigest);
    }

    function _bindings(
        Digest512 calldata nullifier,
        Digest512 calldata root,
        address recipient,
        uint256 amount,
        Digest512 calldata globalData,
        Digest512 calldata checkpointDigest,
        Digest512 calldata proofDigest,
        Digest512 calldata continuationDigest
    ) private view returns (FixedBindings memory bindings) {
        bindings.statement = Digest512({
            left: keccak256(
                abi.encode(
                    STATEMENT_LEFT_DOMAIN,
                    block.chainid,
                    address(this),
                    nullifier.left,
                    nullifier.right,
                    root.left,
                    root.right,
                    recipient,
                    amount
                )
            ),
            right: keccak256(
                abi.encode(
                    STATEMENT_RIGHT_DOMAIN,
                    block.chainid,
                    address(this),
                    nullifier.left,
                    nullifier.right,
                    root.left,
                    root.right,
                    recipient,
                    amount
                )
            )
        });
        bindings.globalData = globalData;
        bindings.checkpoint = checkpointDigest;
        bindings.proof = proofDigest;
        bindings.continuation = continuationDigest;
        bindings.root = root;
    }
}
