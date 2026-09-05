// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBearExt4Packed as Ext} from "./libraries/BabyBearExt4Packed.sol";
import {CanonicalCodec} from "./libraries/CanonicalCodec.sol";
import {Digest512} from "./libraries/Digest512.sol";
import {PQTCProofCodec} from "./libraries/PQTCProofCodec.sol";
import {Binding512} from "./libraries/Binding512.sol";
import {Transcript512} from "./libraries/Transcript512.sol";
import {PQTCAirStageVerifier} from "./verifier/PQTCAirStageVerifier.sol";
import {PQTCQueryVerifier} from "./verifier/PQTCQueryVerifier.sol";

/// Two-transaction verifier. Only a compact, consumer-bound checkpoint crosses transactions.
contract PQTCVerificationRegistry {
    uint256 private constant GLOBAL_DATA_BYTES = 9_208;
    uint256 private constant TRACE_WIDTH = 190;
    uint256 private constant RANDOM_CODEWORDS = 4;
    uint256 private constant QUOTIENT_EXTENSIONS = 64;
    uint256 private constant QUERY_COUNT = 48;
    uint256 private constant FRI_ROUNDS = 9;
    uint8 private constant AIR_SPLIT = 3;

    struct StoredCheckpoint {
        address consumer;
        Digest512 coreProofId;
        Digest512 statementKey;
        Digest512 checkpointDigest;
        Digest512 globalDigest;
        uint256 airAccumulator;
        uint8 airCursor;
        uint256 zetaAggregate;
        uint256 nextAggregate;
        uint256 expiresAt;
    }

    struct TranscriptCheckpoint {
        Digest512 digest;
        Digest512 globalDigest;
        Digest512 state;
        uint256 airAlpha;
        uint256 zeta;
        uint256 friAlpha;
        uint256[9] friBetas;
        uint32[48] queryIndices;
        uint256 cursor;
    }

    struct GlobalData {
        PQTCQueryVerifier.Context query;
        uint256[190] traceLocal;
        uint256[190] traceNext;
        uint256[64] quotient;
        uint32[9] friWitnesses;
        uint32 queryWitness;
        uint256 cursor;
    }

    bytes32 public immutable parameterLeft;
    bytes32 public immutable parameterRight;
    PQTCAirStageVerifier public immutable airVerifier;
    PQTCQueryVerifier public immutable queryVerifier;
    PQTCQueryVerifier public immutable queryVerifierB;
    uint16 public immutable firstQueries;

    mapping(bytes32 => StoredCheckpoint) private checkpoints;

    event VerificationStarted(bytes32 indexed proofId, address indexed consumer, bytes32 indexed statementKey);
    event VerificationCompleted(bytes32 indexed proofId, address indexed consumer, bytes32 indexed statementKey);

    error ZeroAddress();
    error ParameterDisabled();
    error ProofAlreadyStarted();
    error UnknownProof();
    error UnauthorizedConsumer();
    error StatementMismatch();
    error GlobalDataMismatch();
    error InvalidCheckpoint();
    error InvalidTranscript();
    error InvalidGrindingWitness();

    constructor(PQTCAirStageVerifier airVerifier_, PQTCQueryVerifier queryVerifier_, PQTCQueryVerifier queryVerifierB_, Digest512 memory parameterId_) {
        if (address(airVerifier_) == address(0) || address(queryVerifier_) == address(0)) revert ZeroAddress();
        if (parameterId_.left == bytes32(0) && parameterId_.right == bytes32(0)) revert ParameterDisabled();
        airVerifier = airVerifier_;
        queryVerifier = queryVerifier_;
        queryVerifierB = queryVerifierB_;
        uint256 split = queryVerifier_.HALF();
        if ((split != 22 && split != 24 && split != 26) || queryVerifierB_.HALF() != 48 - split) revert InvalidCheckpoint();
        firstQueries = uint16(split);
        parameterLeft = parameterId_.left;
        parameterRight = parameterId_.right;
    }

    function beginVerification(Digest512 calldata parameterId, uint32[64] calldata publicValues, bytes calldata partA)
        public
        returns (bytes32 proofId)
    {
        _requireParameter(parameterId);
        PQTCProofCodec.Common memory common =
            PQTCProofCodec.parseCommon(partA, PQTCProofCodec.PART_A_MAGIC, parameterId, publicValues);
        Digest512 memory statementKey = PQTCProofCodec.statementKey(parameterId, publicValues);
        if (common.firstQueries != firstQueries) revert InvalidCheckpoint();
        uint256 cursor = common.cursor;
        Digest512 memory suppliedGlobalDigest;
        (suppliedGlobalDigest, cursor) = CanonicalCodec.readDigest(partA, cursor);
        uint256 globalStart = cursor;
        GlobalData memory globals = _parseGlobalData(partA, cursor);
        cursor = globals.cursor;
        if (cursor - globalStart != GLOBAL_DATA_BYTES || !Binding512.equal(Binding512.hash(partA[globalStart:cursor]), suppliedGlobalDigest)) {
            revert GlobalDataMismatch();
        }
        TranscriptCheckpoint memory parsedCheckpoint = _parseCheckpoint(partA, cursor, statementKey);
        cursor = parsedCheckpoint.cursor;
        if (!Binding512.equal(parsedCheckpoint.globalDigest, suppliedGlobalDigest)) revert GlobalDataMismatch();
        _verifyTranscript(parameterId, publicValues, globals, parsedCheckpoint);
        _applyCheckpoint(globals.query, parsedCheckpoint);

        uint256[] memory local = new uint256[](TRACE_WIDTH);
        uint256[] memory next = new uint256[](TRACE_WIDTH);
        for (uint256 i; i < TRACE_WIDTH; ++i) {
            local[i] = globals.traceLocal[i];
            next[i] = globals.traceNext[i];
        }
        uint256 airAccumulator = airVerifier.evaluateRange(
            local, next, publicValues, parsedCheckpoint.zeta, parsedCheckpoint.airAlpha, 0, 0, AIR_SPLIT
        );
        uint256 zetaAggregate;
        uint256 nextAggregate;
        (cursor, zetaAggregate, nextAggregate) = queryVerifier.verifyFirstHalf(partA, cursor, globals.query);
        PQTCProofCodec.requireEnd(partA, cursor, PQTCProofCodec.PART_A_END);

        Digest512 memory coreProofId = Binding512.hash(abi.encode(bytes32("PQTC.R2.V4.PROOF"), statementKey, Binding512.hash(partA)));
        proofId = keccak256(abi.encode(bytes32("PQTC.R2.V4.VERIFICATION"), coreProofId, msg.sender));
        StoredCheckpoint storage existing = checkpoints[proofId];
        if (existing.consumer != address(0) && block.number >= existing.expiresAt) delete checkpoints[proofId];
        if (existing.consumer != address(0)) {
            if (
                existing.consumer != msg.sender || !Binding512.equal(existing.coreProofId, coreProofId)
                    || !Binding512.equal(existing.statementKey, statementKey) || !Binding512.equal(existing.checkpointDigest, parsedCheckpoint.digest)
                    || !Binding512.equal(existing.globalDigest, suppliedGlobalDigest) || existing.airAccumulator != airAccumulator
                    || existing.airCursor != AIR_SPLIT || existing.zetaAggregate != zetaAggregate
                    || existing.nextAggregate != nextAggregate
            ) revert ProofAlreadyStarted();
            emit VerificationStarted(proofId, msg.sender, statementKey.left);
            return proofId;
        }
        checkpoints[proofId] = StoredCheckpoint(
            msg.sender,
            coreProofId,
            statementKey,
            parsedCheckpoint.digest,
            suppliedGlobalDigest,
            airAccumulator,
            AIR_SPLIT,
            zetaAggregate,
            nextAggregate,
            block.number + 64
        );
        emit VerificationStarted(proofId, msg.sender, statementKey.left);
    }

    function completeVerification(
        bytes32 proofId,
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        bytes calldata partB
    ) public returns (bool) {
        StoredCheckpoint memory stored = checkpoints[proofId];
        if (stored.consumer == address(0)) revert UnknownProof();
        if (block.number >= stored.expiresAt) revert InvalidCheckpoint();
        if (msg.sender != stored.consumer) revert UnauthorizedConsumer();
        _requireParameter(parameterId);
        Digest512 memory statementKey = PQTCProofCodec.statementKey(parameterId, publicValues);
        if (!Binding512.equal(statementKey, stored.statementKey)) revert StatementMismatch();
        PQTCProofCodec.Common memory common =
            PQTCProofCodec.parseCommon(partB, PQTCProofCodec.PART_B_MAGIC, parameterId, publicValues);
        if (common.firstQueries != firstQueries) revert InvalidCheckpoint();
        uint256 cursor = common.cursor;
        Digest512 memory encodedCoreProofId;
        (encodedCoreProofId, cursor) = CanonicalCodec.readDigest(partB, cursor);
        if (!Binding512.equal(encodedCoreProofId, stored.coreProofId)) revert InvalidCheckpoint();
        Digest512 memory suppliedGlobalDigest;
        (suppliedGlobalDigest, cursor) = CanonicalCodec.readDigest(partB, cursor);
        if (!Binding512.equal(suppliedGlobalDigest, stored.globalDigest)) revert GlobalDataMismatch();
        uint256 globalStart = cursor;
        GlobalData memory globals = _parseGlobalDataPartB(partB, cursor);
        cursor = globals.cursor;
        if (cursor - globalStart != GLOBAL_DATA_BYTES || !Binding512.equal(Binding512.hash(partB[globalStart:cursor]), suppliedGlobalDigest)) {
            revert GlobalDataMismatch();
        }
        TranscriptCheckpoint memory parsedCheckpoint = _parseCheckpoint(partB, cursor, statementKey);
        cursor = parsedCheckpoint.cursor;
        if (
            !Binding512.equal(parsedCheckpoint.digest, stored.checkpointDigest) || !Binding512.equal(parsedCheckpoint.globalDigest, suppliedGlobalDigest)
                || !Binding512.equal(parsedCheckpoint.globalDigest, stored.globalDigest)
        ) revert InvalidCheckpoint();
        _applyCheckpoint(globals.query, parsedCheckpoint);

        uint256[] memory local = new uint256[](TRACE_WIDTH);
        uint256[] memory next = new uint256[](TRACE_WIDTH);
        uint256[] memory quotient = new uint256[](QUOTIENT_EXTENSIONS);
        for (uint256 i; i < TRACE_WIDTH; ++i) {
            local[i] = globals.traceLocal[i];
            next[i] = globals.traceNext[i];
        }
        for (uint256 i; i < QUOTIENT_EXTENSIONS; ++i) {
            quotient[i] = globals.quotient[i];
        }
        if (stored.airCursor != AIR_SPLIT) revert InvalidCheckpoint();
        uint256 airAccumulator = airVerifier.evaluateRange(
            local,
            next,
            publicValues,
            parsedCheckpoint.zeta,
            parsedCheckpoint.airAlpha,
            stored.airAccumulator,
            stored.airCursor,
            7
        );
        airVerifier.requireValid(airAccumulator, quotient, parsedCheckpoint.zeta);

        // Deleting before the expensive verifier call makes re-entry impossible. Any later pool revert
        // reverts this deletion as part of the same transaction.
        delete checkpoints[proofId];
        cursor =
            queryVerifierB.verifySecondHalf(partB, cursor, globals.query, stored.zetaAggregate, stored.nextAggregate);
        PQTCProofCodec.requireEnd(partB, cursor, PQTCProofCodec.PART_B_END);
        emit VerificationCompleted(proofId, msg.sender, statementKey.left);
        return true;
    }

    function verifyOneCall(Digest512 calldata parameterId, uint32[64] calldata publicValues, bytes calldata partA, bytes calldata partB) external returns (bool) {
        bytes32 id = beginVerification(parameterId, publicValues, partA);
        return completeVerification(id, parameterId, publicValues, partB);
    }

    // Consumer-owned cancellation prevents abandoned research sessions becoming immortal.
    function cancelVerification(bytes32 proofId) external {
        if (checkpoints[proofId].consumer != msg.sender) revert UnauthorizedConsumer();
        delete checkpoints[proofId];
    }

    function cleanupExpired(bytes32 proofId) external {
        StoredCheckpoint storage stored = checkpoints[proofId];
        if (stored.consumer == address(0)) revert UnknownProof();
        if (block.number < stored.expiresAt) revert InvalidCheckpoint();
        delete checkpoints[proofId];
    }

    function expiresAt(bytes32 proofId) external view returns (uint256) {
        return checkpoints[proofId].expiresAt;
    }

    function checkpoint(bytes32 proofId)
        external
        view
        returns (address consumer, Digest512 memory statementKey, Digest512 memory checkpointDigest, Digest512 memory globalDigest)
    {
        StoredCheckpoint storage value = checkpoints[proofId];
        return (value.consumer, value.statementKey, value.checkpointDigest, value.globalDigest);
    }

    function _parseGlobalData(bytes calldata proof, uint256 cursor) private pure returns (GlobalData memory data) {
        Digest512 memory traceRoot;
        Digest512 memory quotientRoot;
        Digest512 memory randomRoot;
        (traceRoot, cursor) = CanonicalCodec.readDigest(proof, cursor);
        (quotientRoot, cursor) = CanonicalCodec.readDigest(proof, cursor);
        (randomRoot, cursor) = CanonicalCodec.readDigest(proof, cursor);
        data.query.inputRoots[0] = randomRoot;
        data.query.inputRoots[1] = traceRoot;
        data.query.inputRoots[2] = quotientRoot;

        for (uint256 i; i < TRACE_WIDTH; ++i) {
            (data.traceLocal[i], cursor) = _readExtension(proof, cursor);
            data.query.traceLocalAtZeta[i] = data.traceLocal[i];
        }
        for (uint256 i; i < TRACE_WIDTH; ++i) {
            (data.traceNext[i], cursor) = _readExtension(proof, cursor);
            data.query.traceNextAtZeta[i] = data.traceNext[i];
        }
        for (uint256 matrix; matrix < 16; ++matrix) {
            for (uint256 column; column < 4; ++column) {
                uint256 value;
                (value, cursor) = _readExtension(proof, cursor);
                data.quotient[matrix * 4 + column] = value;
                data.query.quotientAtZeta[matrix * 8 + column] = value;
            }
        }
        for (uint256 i; i < 4; ++i) {
            (data.query.randomAtZeta[i], cursor) = _readExtension(proof, cursor);
        }
        for (uint256 i; i < RANDOM_CODEWORDS; ++i) {
            (data.query.randomAtZeta[4 + i], cursor) = _readExtension(proof, cursor);
        }
        for (uint256 point; point < 2; ++point) {
            for (uint256 i; i < RANDOM_CODEWORDS; ++i) {
                uint256 value;
                (value, cursor) = _readExtension(proof, cursor);
                if (point == 0) data.query.traceLocalAtZeta[TRACE_WIDTH + i] = value;
                else data.query.traceNextAtZeta[TRACE_WIDTH + i] = value;
            }
        }
        for (uint256 matrix; matrix < 16; ++matrix) {
            for (uint256 i; i < RANDOM_CODEWORDS; ++i) {
                (data.query.quotientAtZeta[matrix * 8 + 4 + i], cursor) = _readExtension(proof, cursor);
            }
        }
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            (data.query.friRoots[round], cursor) = CanonicalCodec.readDigest(proof, cursor);
        }
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            (data.friWitnesses[round], cursor) = CanonicalCodec.readField(proof, cursor);
        }
        (data.query.finalPolynomial, cursor) = _readExtension(proof, cursor);
        (data.queryWitness, cursor) = CanonicalCodec.readField(proof, cursor);
        data.cursor = cursor;
    }

    function _parseGlobalDataPartB(bytes calldata proof, uint256 cursor) private pure returns (GlobalData memory data) {
        (data.query.inputRoots[1], cursor) = CanonicalCodec.readDigest(proof, cursor);
        (data.query.inputRoots[2], cursor) = CanonicalCodec.readDigest(proof, cursor);
        (data.query.inputRoots[0], cursor) = CanonicalCodec.readDigest(proof, cursor);
        for (uint256 i; i < TRACE_WIDTH; ++i) {
            (data.traceLocal[i], cursor) = _readExtension(proof, cursor);
        }
        for (uint256 i; i < TRACE_WIDTH; ++i) {
            (data.traceNext[i], cursor) = _readExtension(proof, cursor);
        }
        for (uint256 matrix; matrix < 16; ++matrix) {
            for (uint256 column; column < 4; ++column) {
                (data.quotient[matrix * 4 + column], cursor) = _readExtension(proof, cursor);
            }
        }
        uint256 skippedOodBytes = 80 * 16;
        if (cursor > proof.length || skippedOodBytes > proof.length - cursor) revert CanonicalCodec.Truncated();
        cursor += skippedOodBytes;
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            (data.query.friRoots[round], cursor) = CanonicalCodec.readDigest(proof, cursor);
        }
        uint256 skippedWitnessBytes = FRI_ROUNDS * 4;
        if (cursor > proof.length || skippedWitnessBytes > proof.length - cursor) revert CanonicalCodec.Truncated();
        cursor += skippedWitnessBytes;
        (data.query.finalPolynomial, cursor) = _readExtension(proof, cursor);
        (, cursor) = CanonicalCodec.readU32(proof, cursor);
        data.cursor = cursor;
    }

    function _parseCheckpoint(bytes calldata proof, uint256 cursor, Digest512 memory statementKey)
        private
        pure
        returns (TranscriptCheckpoint memory checkpointValue)
    {
        (checkpointValue.digest, cursor) = CanonicalCodec.readDigest(proof, cursor);
        uint256 payloadStart = cursor;
        (checkpointValue.globalDigest, cursor) = CanonicalCodec.readDigest(proof, cursor);
        (checkpointValue.state, cursor) = CanonicalCodec.readDigest(proof, cursor);
        (checkpointValue.airAlpha, cursor) = _readExtension(proof, cursor);
        (checkpointValue.zeta, cursor) = _readExtension(proof, cursor);
        (checkpointValue.friAlpha, cursor) = _readExtension(proof, cursor);
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            (checkpointValue.friBetas[round], cursor) = _readExtension(proof, cursor);
        }
        uint16 totalQueries;
        (totalQueries, cursor) = CanonicalCodec.readU16(proof, cursor);
        if (totalQueries != QUERY_COUNT) revert InvalidCheckpoint();
        for (uint256 i; i < QUERY_COUNT; ++i) {
            (checkpointValue.queryIndices[i], cursor) = CanonicalCodec.readU32(proof, cursor);
            if (checkpointValue.queryIndices[i] >= (uint32(1) << 13)) revert InvalidCheckpoint();
        }
        uint16 uniqueCount;
        (uniqueCount, cursor) = CanonicalCodec.readU16(proof, cursor);
        uint32[48] memory expectedUnique;
        uint256 expectedCount = _unique(checkpointValue.queryIndices, expectedUnique);
        if (uniqueCount != expectedCount) revert InvalidCheckpoint();
        for (uint256 i; i < expectedCount; ++i) {
            uint32 supplied;
            (supplied, cursor) = CanonicalCodec.readU32(proof, cursor);
            if (supplied != expectedUnique[i]) revert InvalidCheckpoint();
        }
        Digest512 memory expected =
            Binding512.hash(abi.encode(bytes32("PQTC.R2.V4.CHECKPOINT"), statementKey, Binding512.hash(proof[payloadStart:cursor])));
        if (!Binding512.equal(checkpointValue.digest, expected)) revert InvalidCheckpoint();
        checkpointValue.cursor = cursor;
    }

    function _verifyTranscript(
        Digest512 calldata parameterId,
        uint32[64] calldata publicValues,
        GlobalData memory globals,
        TranscriptCheckpoint memory checkpointValue
    ) private pure {
        uint32[] memory values = new uint32[](64);
        for (uint256 i; i < 64; ++i) {
            values[i] = publicValues[i];
        }
        Transcript512.State memory transcript = Transcript512.initialize(parameterId, values);
        Transcript512.observeField(transcript, 9);
        Transcript512.observeField(transcript, 8);
        Transcript512.observeField(transcript, 0);
        Transcript512.observeCommitment(transcript, globals.query.inputRoots[1]);
        for (uint256 i; i < 64; ++i) {
            Transcript512.observeField(transcript, publicValues[i]);
        }
        uint256 airAlpha = _sampleExtension(transcript);
        Transcript512.observeCommitment(transcript, globals.query.inputRoots[2]);
        Transcript512.observeCommitment(transcript, globals.query.inputRoots[0]);
        uint256 zeta = _sampleExtension(transcript);
        _observeOod(transcript, globals.query);
        uint256 friAlpha = _sampleExtension(transcript);
        uint256[9] memory betas;
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            Transcript512.observeCommitment(transcript, globals.query.friRoots[round]);
            if (!Transcript512.checkWitness(transcript, 16, globals.friWitnesses[round])) {
                revert InvalidGrindingWitness();
            }
            betas[round] = _sampleExtension(transcript);
        }
        _observeExtension(transcript, globals.query.finalPolynomial);
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            Transcript512.observeField(transcript, 1);
        }
        if (!Transcript512.checkWitness(transcript, 16, globals.queryWitness)) revert InvalidGrindingWitness();
        uint32[48] memory indices;
        for (uint256 i; i < QUERY_COUNT; ++i) {
            indices[i] = uint32(Transcript512.sampleBits(transcript, 13));
        }
        if (
            checkpointValue.state.left != transcript.digest.left
                || checkpointValue.state.right != transcript.digest.right || checkpointValue.airAlpha != airAlpha
                || checkpointValue.zeta != zeta || checkpointValue.friAlpha != friAlpha
        ) revert InvalidTranscript();
        for (uint256 round; round < FRI_ROUNDS; ++round) {
            if (checkpointValue.friBetas[round] != betas[round]) revert InvalidTranscript();
        }
        for (uint256 i; i < QUERY_COUNT; ++i) {
            if (checkpointValue.queryIndices[i] != indices[i]) revert InvalidTranscript();
        }
    }

    function _observeOod(Transcript512.State memory transcript, PQTCQueryVerifier.Context memory context) private pure {
        for (uint256 i; i < 8; ++i) {
            _observeExtension(transcript, context.randomAtZeta[i]);
        }
        for (uint256 i; i < TRACE_WIDTH + RANDOM_CODEWORDS; ++i) {
            _observeExtension(transcript, context.traceLocalAtZeta[i]);
        }
        for (uint256 i; i < TRACE_WIDTH + RANDOM_CODEWORDS; ++i) {
            _observeExtension(transcript, context.traceNextAtZeta[i]);
        }
        for (uint256 matrix; matrix < 16; ++matrix) {
            for (uint256 i; i < 8; ++i) {
                _observeExtension(transcript, context.quotientAtZeta[matrix * 8 + i]);
            }
        }
    }

    function _applyCheckpoint(PQTCQueryVerifier.Context memory context, TranscriptCheckpoint memory checkpointValue)
        private
        pure
    {
        context.zeta = checkpointValue.zeta;
        context.friAlpha = checkpointValue.friAlpha;
        context.friBetas = checkpointValue.friBetas;
        context.queryIndices = checkpointValue.queryIndices;
    }

    function _unique(uint32[48] memory indices, uint32[48] memory unique) private pure returns (uint256 count) {
        for (uint256 i; i < QUERY_COUNT; ++i) {
            uint32 value = indices[i];
            uint256 position;
            while (position < count && unique[position] < value) ++position;
            if (position < count && unique[position] == value) continue;
            for (uint256 move = count; move > position; --move) {
                unique[move] = unique[move - 1];
            }
            unique[position] = value;
            ++count;
        }
    }

    function _sampleExtension(Transcript512.State memory transcript) private pure returns (uint256) {
        uint32[4] memory value = Transcript512.sampleExt4(transcript);
        return Ext.fromCoefficients(value[0], value[1], value[2], value[3]);
    }

    function _observeExtension(Transcript512.State memory transcript, uint256 value) private pure {
        Ext.check(value);
        Transcript512.observeField(transcript, uint32(value));
        Transcript512.observeField(transcript, uint32(value >> 32));
        Transcript512.observeField(transcript, uint32(value >> 64));
        Transcript512.observeField(transcript, uint32(value >> 96));
    }

    function _readExtension(bytes calldata proof, uint256 cursor) private pure returns (uint256 value, uint256 next) {
        if (cursor > proof.length || 16 > proof.length - cursor) revert CanonicalCodec.Truncated();
        assembly ("memory-safe") {
            let word := calldataload(add(proof.offset, cursor))
            let mask := 0xffffffff
            let c0 := shr(224, word)
            let c1 := and(shr(192, word), mask)
            let c2 := and(shr(160, word), mask)
            let c3 := and(shr(128, word), mask)
            if iszero(and(and(lt(c0, 2013265921), lt(c1, 2013265921)), and(lt(c2, 2013265921), lt(c3, 2013265921)))) {
                mstore(0, shl(224, 0x65a81779))
                let badValue := c0
                if and(lt(c0, 2013265921), iszero(lt(c1, 2013265921))) { badValue := c1 }
                if and(and(lt(c0, 2013265921), lt(c1, 2013265921)), iszero(lt(c2, 2013265921))) {
                    badValue := c2
                }
                if and(
                    and(and(lt(c0, 2013265921), lt(c1, 2013265921)), lt(c2, 2013265921)),
                    iszero(lt(c3, 2013265921))
                ) {
                    badValue := c3
                }
                mstore(4, badValue)
                revert(0, 36)
            }
            value := or(or(c0, shl(32, c1)), or(shl(64, c2), shl(96, c3)))
        }
        next = cursor + 16;
    }

    function _requireParameter(Digest512 calldata parameterId) private view {
        if (parameterId.left != parameterLeft || parameterId.right != parameterRight) revert ParameterDisabled();
    }
}
