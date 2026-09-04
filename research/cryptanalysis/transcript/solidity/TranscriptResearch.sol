// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

/// @notice SP-30 research only. Not custody code and not audited.
library TranscriptResearch {
    uint32 internal constant BABY_BEAR_MODULUS = 2_013_265_921;
    uint8 internal constant INIT = 0x42;
    uint8 internal constant ABSORB = 0x43;
    uint8 internal constant SQUEEZE = 0x44;
    uint8 internal constant ITEM_DIGEST = 0x45;
    uint8 internal constant BOUNDARY_FRAME = 0x46;
    uint8 internal constant FIELD = 1;
    uint8 internal constant COMMITMENT = 2;
    uint8 internal constant FIELD_ARRAY = 3;

    enum Variant { T0, T1, T2, T3 }
    error NonCanonicalField(uint32 value);
    error InvalidWidth();
    error InvalidType();
    error InvalidCount();
    error BitsOutOfRange();
    error SqueezeCounterOverflow();

    struct State {
        Variant variant;
        bytes32 left;
        bytes32 right;
        bytes output;
        uint32 outputAt;
        uint64 counter;
        bytes pending;
        uint32 pendingItems;
        uint64 keccakCalls;
        uint64 hashedBytes;
        uint64 copiedBytes;
        uint64 peakFrameBytes;
    }

    function version(Variant variant) internal pure returns (bytes9) {
        if (variant == Variant.T0) return bytes9("PQTCT0-01");
        if (variant == Variant.T1) return bytes9("PQTCT1-01");
        if (variant == Variant.T2) return bytes9("PQTCT2-01");
        return bytes9("PQTCT3-01");
    }

    function initialize(Variant variant, bytes32 parameterLeft, bytes32 parameterRight, uint32[] memory publicValues, bool productionCompatibleT0) internal pure returns (State memory state) {
        bytes memory fields = encodeFields(publicValues, false);
        bytes memory payload = productionCompatibleT0 && variant == Variant.T0
            ? abi.encodePacked(parameterLeft, parameterRight, fields)
            : abi.encodePacked(version(variant), parameterLeft, parameterRight, uint32(publicValues.length), fields);
        state.variant = variant;
        (state.left, state.right) = k512(INIT, payload);
        state.keccakCalls = 2;
        state.hashedBytes = uint64(2 * (2 + payload.length));
        state.copiedBytes = uint64(2 * (2 + payload.length) + 64);
    }

    function k512(uint8 tag, bytes memory payload) internal pure returns (bytes32 left, bytes32 right) {
        left = keccak256(abi.encodePacked(uint8(0), tag, payload));
        right = keccak256(abi.encodePacked(uint8(1), tag, payload));
    }

    function accountK512(State memory state, uint256 payloadLength) private pure {
        state.keccakCalls += 2;
        state.hashedBytes += uint64(2 * (2 + payloadLength));
        state.copiedBytes += uint64(2 * (2 + payloadLength) + 64);
    }

    function absorbField(State memory state, uint32 value) internal pure {
        canonical(value);
        absorbTyped(state, FIELD, abi.encodePacked(value));
    }

    function absorbCommitment(State memory state, bytes32 left, bytes32 right) internal pure {
        absorbTyped(state, COMMITMENT, abi.encodePacked(left, right));
    }

    function absorbFields(State memory state, uint32[] memory values) internal pure {
        if (state.variant == Variant.T0) {
            for (uint256 i; i < values.length; ++i) absorbField(state, values[i]);
        } else {
            absorbTyped(state, FIELD_ARRAY, encodeFields(values, true));
        }
    }

    function encodeFields(uint32[] memory values, bool withCount) internal pure returns (bytes memory out) {
        out = withCount ? abi.encodePacked(uint32(values.length)) : bytes("");
        for (uint256 i; i < values.length; ++i) {
            canonical(values[i]);
            out = bytes.concat(out, abi.encodePacked(values[i]));
        }
    }

    function decodeFieldArray(bytes memory payload) internal pure returns (uint32[] memory values) {
        if (payload.length < 4) revert InvalidCount();
        uint32 count;
        assembly { count := shr(224, mload(add(payload, 32))) }
        if (payload.length != 4 + uint256(count) * 4) revert InvalidCount();
        values = new uint32[](count);
        for (uint256 i; i < count; ++i) {
            uint32 value;
            assembly { value := shr(224, mload(add(add(payload, 36), mul(i, 4)))) }
            canonical(value); values[i] = value;
        }
    }

    function absorbTyped(State memory state, uint8 itemType, bytes memory payload) internal pure {
        validateItem(itemType, payload);
        if (state.variant == Variant.T2) {
            bytes memory item = abi.encodePacked(version(Variant.T2), itemType, uint32(payload.length), payload);
            (bytes32 itemLeft, bytes32 itemRight) = k512(ITEM_DIGEST, item); accountK512(state, item.length);
            bytes memory stateItem = abi.encodePacked(state.left, state.right, itemLeft, itemRight);
            (state.left, state.right) = k512(ABSORB, stateItem); accountK512(state, stateItem.length); resetOutput(state);
        } else if (state.variant == Variant.T3) {
            bytes memory item = abi.encodePacked(itemType, uint32(payload.length), payload);
            state.pending = bytes.concat(state.pending, item); state.pendingItems += 1; state.copiedBytes += uint64(item.length);
            if (state.pending.length > state.peakFrameBytes) state.peakFrameBytes = uint64(state.pending.length);
        } else {
            bytes memory input = abi.encodePacked(state.left, state.right, itemType, uint32(payload.length), payload);
            (state.left, state.right) = k512(ABSORB, input); accountK512(state, input.length); resetOutput(state);
        }
    }

    function flush(State memory state) internal pure {
        if (state.variant != Variant.T3 || state.pendingItems == 0) return;
        bytes memory frame = abi.encodePacked(version(Variant.T3), state.pendingItems, uint32(state.pending.length), state.pending);
        bytes memory input = abi.encodePacked(state.left, state.right, frame);
        (state.left, state.right) = k512(BOUNDARY_FRAME, input); accountK512(state, input.length);
        delete state.pending; state.pendingItems = 0; resetOutput(state);
    }

    function sampleField(State memory state) internal pure returns (uint32 value) {
        while (true) {
            value = nextWord(state) & 0x7fff_ffff;
            if (value < BABY_BEAR_MODULUS) return value;
        }
        revert NonCanonicalField(value);
    }

    function sampleExtension(State memory state) internal pure returns (uint32[4] memory value) {
        for (uint256 i; i < 4; ++i) value[i] = sampleField(state);
    }

    function sampleBits(State memory state, uint8 bits) internal pure returns (uint32) {
        if (bits > 31) revert BitsOutOfRange();
        uint32 word = nextWord(state);
        return bits == 0 ? 0 : word & uint32((uint256(1) << bits) - 1);
    }
    function checkWitness(State memory state, uint8 bits, uint32 witness) internal pure returns (bool) {
        if (bits == 0) return true;
        absorbField(state, witness);
        return sampleBits(state, bits) == 0;
    }


    function nextWord(State memory state) private pure returns (uint32 word) {
        flush(state);
        if (state.outputAt + 4 > state.output.length) {
            if (state.counter == type(uint64).max) revert SqueezeCounterOverflow();
            bytes memory payload = abi.encodePacked(state.left, state.right, state.counter);
            (bytes32 left, bytes32 right) = k512(SQUEEZE, payload); accountK512(state, payload.length);
            state.output = abi.encodePacked(left, right); state.outputAt = 0; state.counter += 1;
        }
        bytes memory output = state.output;
        uint256 at = state.outputAt;
        assembly { word := shr(224, mload(add(add(output, 32), at))) }
        state.outputAt += 4;
    }

    function resetOutput(State memory state) private pure { delete state.output; state.outputAt = 0; state.counter = 0; }

    function validateItem(uint8 itemType, bytes memory payload) private pure {
        if (itemType == FIELD) {
            if (payload.length != 4) revert InvalidWidth();
            uint32 value; assembly { value := shr(224, mload(add(payload, 32))) } canonical(value);
        } else if (itemType == COMMITMENT) {
            if (payload.length != 64) revert InvalidWidth();
        } else if (itemType == FIELD_ARRAY) {
            decodeFieldArray(payload);
        } else revert InvalidType();
    }

    function canonical(uint32 value) private pure { if (value >= BABY_BEAR_MODULUS) revert NonCanonicalField(value); }

    function statementKey(bytes32 parameterLeft, bytes32 parameterRight, uint32[64] memory publicValues) internal pure returns (bytes32) {
        bytes memory encoded = abi.encode(bytes32("PQTC.V3.STATEMENT"), parameterLeft, parameterRight);
        for (uint256 i; i < 64; ++i) { canonical(publicValues[i]); encoded = bytes.concat(encoded, abi.encode(uint256(publicValues[i]))); }
        return keccak256(encoded);
    }

    function checkpointDigest(bytes32 key, bytes memory payload) internal pure returns (bytes32) {
        return keccak256(abi.encode(bytes32("PQTC.V3.CHECKPOINT"), key, keccak256(payload)));
    }

    function proofId(bytes32 key, bytes memory partA) internal pure returns (bytes32) {
        return keccak256(abi.encode(bytes32("PQTC.V3.PROOF"), key, keccak256(partA)));
    }
}

/// @notice A bytes32 mapping key is only an index; all protocol digests remain in storage.
contract FullDigestStoreResearch {
    struct Record {
        bytes32 parameterLeft;
        bytes32 parameterRight;
        bytes32[8] statementHalves;
        bytes32 globalDigest;
        bytes32 coreProofDigest;
        bool present;
    }
    mapping(bytes32 => Record) private records;
    error UnknownKey();
    error FullDigestMismatch();
    function validateStatementDigests(uint32[64] memory publicValues, bytes32[8] memory halves) private pure {
        for (uint256 i; i < 64; ++i) {
            uint256 shift = (7 - (i % 8)) * 32;
            if (uint32(uint256(halves[i / 8]) >> shift) != publicValues[i]) revert FullDigestMismatch();
        }
    }


    function put(uint32[64] memory publicValues, Record memory record) external returns (bytes32 key) {
        validateStatementDigests(publicValues, record.statementHalves);
        key = TranscriptResearch.statementKey(record.parameterLeft, record.parameterRight, publicValues);
        record.present = true; records[key] = record;
    }

    function getChecked(bytes32 key, uint32[64] memory publicValues, Record memory supplied) external view returns (Record memory stored) {
        stored = records[key]; if (!stored.present) revert UnknownKey();
        validateStatementDigests(publicValues, stored.statementHalves);
        if (TranscriptResearch.statementKey(stored.parameterLeft, stored.parameterRight, publicValues) != key
            || keccak256(abi.encode(stored)) != keccak256(abi.encode(supplied.parameterLeft, supplied.parameterRight, supplied.statementHalves, supplied.globalDigest, supplied.coreProofDigest, true))) revert FullDigestMismatch();
    }
}

/// @notice Executable gas harness. It emits raw observations and makes no deployment claim.
contract TranscriptGasHarness {
    using TranscriptResearch for TranscriptResearch.State;
    event Measurement(uint8 indexed variant, uint256 transcriptGas, uint256 parserGas, uint256 calldataBytes, uint256 memoryHighWater, uint256 keccakCalls, uint256 hashedBytes, uint256 copiedBytes, uint256 runtimeCodeBytes, int256 proofBytesDelta, int256 calldataBytesDelta, int256 fullPathGasDelta);

    function bench(uint8 candidate, bytes32 parameterLeft, bytes32 parameterRight, uint32[] calldata publicValues, bytes calldata typedArray, bytes calldata candidateProof, bytes calldata canonicalProof, bytes calldata candidateProofCalldata, bytes calldata canonicalProofCalldata) external returns (bytes32 left, bytes32 right) {
        uint256 start = gasleft();
        TranscriptResearch.State memory state = TranscriptResearch.initialize(TranscriptResearch.Variant(candidate), parameterLeft, parameterRight, publicValues, candidate == 0);
        state.absorbField(9); state.absorbField(8); state.absorbField(0); state.absorbCommitment(parameterLeft, parameterRight); state.absorbFields(publicValues); state.sampleExtension();
        uint256 transcriptGas = start - gasleft();
        start = gasleft(); TranscriptResearch.decodeFieldArray(typedArray); uint256 parserGas = start - gasleft();
        state.flush(); left = state.left; right = state.right;
        uint256 size; assembly { size := extcodesize(address()) }
        int256 proofBytesDelta = int256(candidateProof.length) - int256(canonicalProof.length);
        int256 calldataBytesDelta = int256(candidateProofCalldata.length) - int256(canonicalProofCalldata.length);
        emit Measurement(candidate, transcriptGas, parserGas, msg.data.length, state.peakFrameBytes, state.keccakCalls, state.hashedBytes, state.copiedBytes, size, proofBytesDelta, calldataBytesDelta, type(int256).min);
    }
}
