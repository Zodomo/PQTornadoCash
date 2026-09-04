// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {Test} from "forge-std/Test.sol";
import {CanonicalCodec} from "../src/libraries/CanonicalCodec.sol";
import {Digest512} from "../src/libraries/Digest512.sol";
import {P2BB512} from "../src/libraries/P2BB512.sol";
import {PQTCAirStageVerifier} from "../src/verifier/PQTCAirStageVerifier.sol";
import {PQTCQueryVerifier} from "../src/verifier/PQTCQueryVerifier.sol";
import {PQTCVerificationRegistry} from "../src/PQTCVerificationRegistry.sol";
import {IPQTCVerificationRegistry, PQTCClassicPool} from "../src/PQTCClassicPool.sol";

contract FixturePool is PQTCClassicPool {
    constructor(Digest512 memory parameterId_, IPQTCVerificationRegistry registry_)
        PQTCClassicPool(1, parameterId_, registry_)
    {}

    function installFixture(Digest512 calldata scope_, Digest512 calldata root_) external {
        scope = scope_;
        knownRoots[root_.left][root_.right] = true;
    }
}

contract NoopAirStageVerifier is PQTCAirStageVerifier {
    function evaluateRange(
        uint256[] calldata,
        uint256[] calldata,
        uint32[64] calldata,
        uint256,
        uint256,
        uint256 accumulator,
        uint8,
        uint8
    ) external pure override returns (uint256) {
        return accumulator;
    }
}

contract NoopQueryVerifier is PQTCQueryVerifier {
    function verifyFirstHalf(bytes calldata proof, uint256, Context calldata)
        external
        pure
        override
        returns (uint256, uint256, uint256)
    {
        return (proof.length - 4, 0, 0);
    }
}

contract FriSkippingQueryVerifier is PQTCQueryVerifier {
    function _fri(bytes calldata proof, uint256, uint32[16] memory, uint256[16] memory, Context calldata)
        internal
        pure
        virtual
        override
        returns (uint256)
    {
        return proof.length - 4;
    }
}

contract SkipInputQueryVerifier is FriSkippingQueryVerifier {
    function _inputBatch(bytes calldata proof, uint256 cursor, ReductionState memory, uint256 batch, Context calldata)
        internal
        pure
        override
        returns (uint256)
    {
        uint256 matrices = batch == 2 ? 16 : 1;
        uint256 rowWidth = batch == 0 ? 8 : batch == 1 ? 194 : 8;
        cursor += 16 * matrices * rowWidth * 4;
        cursor += 16 * matrices * 8 * 4;
        uint32 frontierCount;
        (frontierCount, cursor) = CanonicalCodec.readU32(proof, cursor);
        return cursor + uint256(frontierCount) * 64;
    }
}

contract NoReductionQueryVerifier is FriSkippingQueryVerifier {
    function _reduceBatch(bytes calldata, uint256, uint256, uint256, ReductionState memory) internal pure override {}
}

contract CompactVerifierTest is Test {
    uint256 private constant EIP_7825_GAS_LIMIT = 16_777_216;
    uint256 private constant A_CHECKPOINT_OFFSET = 338 + 32 + 9_208;
    uint256 private constant B_CHECKPOINT_OFFSET = 338 + 32 + 32 + 9_208;

    bytes private partA;
    bytes private partB;
    Digest512 private parameterId;
    uint32[64] private publicValues;
    PQTCVerificationRegistry private registry;

    function setUp() external {
        partA = vm.readFileBinary("test-vectors/verifier/v3/part-a.pqtc");
        partB = vm.readFileBinary("test-vectors/verifier/v3/part-b.pqtc");
        (parameterId, publicValues) = _common(partA);
        registry = new PQTCVerificationRegistry(new PQTCAirStageVerifier(), new PQTCQueryVerifier(), parameterId);
    }

    function measureA(
        PQTCVerificationRegistry target,
        Digest512 calldata parameter,
        uint32[64] calldata values,
        bytes calldata proof
    ) external returns (uint256 used, bytes32 proofId) {
        uint256 beforeGas = gasleft();
        proofId = target.beginVerification(parameter, values, proof);
        used = beforeGas - gasleft();
    }

    function measureB(
        PQTCVerificationRegistry target,
        bytes32 proofId,
        Digest512 calldata parameter,
        uint32[64] calldata values,
        bytes calldata proof
    ) external returns (uint256 used) {
        uint256 beforeGas = gasleft();
        target.completeVerification(proofId, parameter, values, proof);
        used = beforeGas - gasleft();
    }

    function measurePoolA(FixturePool target, PQTCClassicPool.Withdrawal calldata withdrawal, bytes calldata proof)
        external
        returns (uint256 used, bytes32 proofId)
    {
        uint256 beforeGas = gasleft();
        proofId = target.beginWithdrawal(withdrawal, proof);
        used = beforeGas - gasleft();
    }

    function measurePoolB(
        FixturePool target,
        PQTCClassicPool.Withdrawal calldata withdrawal,
        bytes32 proofId,
        bytes calldata proof
    ) external returns (uint256 used) {
        uint256 beforeGas = gasleft();
        target.withdraw(withdrawal, proofId, proof);
        used = beforeGas - gasleft();
    }

    function testCanonicalV3ProofCompletesInExactlyTwoPoolFacingGasBoundedCalls() external {
        FixturePool pool = new FixturePool(parameterId, IPQTCVerificationRegistry(address(registry)));
        PQTCClassicPool.Withdrawal memory withdrawal = _fixtureWithdrawal();
        pool.installFixture(_digestAt(0), withdrawal.root);
        vm.deal(address(pool), 1);

        (uint256 partAExecutionGas, bytes32 proofId) = this.measurePoolA(pool, withdrawal, partA);
        bytes32 statementKey =
            keccak256(abi.encode(bytes32("PQTC.V3.STATEMENT"), parameterId.left, parameterId.right, publicValues));
        bytes32 coreProofId = keccak256(abi.encode(bytes32("PQTC.V3.PROOF"), statementKey, keccak256(partA)));
        assertEq(proofId, keccak256(abi.encode(bytes32("PQTC.V3.VERIFICATION"), coreProofId, address(pool))));
        uint256 partBExecutionGas = this.measurePoolB(pool, withdrawal, proofId, partB);
        uint256 partATransactionGas =
            _transactionGas(partAExecutionGas, abi.encodeCall(PQTCClassicPool.beginWithdrawal, (withdrawal, partA)));
        uint256 partBTransactionGas =
            _transactionGas(partBExecutionGas, abi.encodeCall(PQTCClassicPool.withdraw, (withdrawal, proofId, partB)));
        assertLe(partATransactionGas, EIP_7825_GAS_LIMIT, "part A complete ABI transaction exceeds EIP-7825");
        assertLe(partBTransactionGas, EIP_7825_GAS_LIMIT, "part B complete ABI transaction exceeds EIP-7825");
        emit log_named_uint("compact verifier part A execution gas", partAExecutionGas);
        emit log_named_uint("compact verifier part A transaction gas", partATransactionGas);
        emit log_named_uint("compact verifier part B execution gas", partBExecutionGas);
        emit log_named_uint("compact verifier part B transaction gas", partBTransactionGas);
    }

    function testGasProfileV3VerifierComponents() external {
        NoopAirStageVerifier noopAir = new NoopAirStageVerifier();
        PQTCAirStageVerifier realAir = new PQTCAirStageVerifier();
        PQTCVerificationRegistry baseline = new PQTCVerificationRegistry(noopAir, new NoopQueryVerifier(), parameterId);
        PQTCVerificationRegistry withAir = new PQTCVerificationRegistry(realAir, new NoopQueryVerifier(), parameterId);
        PQTCVerificationRegistry prepared =
            new PQTCVerificationRegistry(noopAir, new SkipInputQueryVerifier(), parameterId);
        PQTCVerificationRegistry committed =
            new PQTCVerificationRegistry(noopAir, new NoReductionQueryVerifier(), parameterId);
        PQTCVerificationRegistry reduced =
            new PQTCVerificationRegistry(noopAir, new FriSkippingQueryVerifier(), parameterId);
        PQTCVerificationRegistry queried = new PQTCVerificationRegistry(noopAir, new PQTCQueryVerifier(), parameterId);

        (uint256 parsingGas,) = this.measureA(baseline, parameterId, publicValues, partA);
        (uint256 airCumulative,) = this.measureA(withAir, parameterId, publicValues, partA);
        (uint256 preparedCumulative,) = this.measureA(prepared, parameterId, publicValues, partA);
        (uint256 committedCumulative,) = this.measureA(committed, parameterId, publicValues, partA);
        (uint256 reducedCumulative,) = this.measureA(reduced, parameterId, publicValues, partA);
        (uint256 queriedCumulative,) = this.measureA(queried, parameterId, publicValues, partA);

        emit log_named_uint("profile parsing transcript storage", parsingGas);
        emit log_named_uint("profile AIR first segment", airCumulative - parsingGas);
        emit log_named_uint("profile alpha inverse shared OOD", preparedCumulative - parsingGas);
        emit log_named_uint("profile input MMCS", committedCumulative - preparedCumulative);
        emit log_named_uint("profile DEEP X reductions", reducedCumulative - committedCumulative);
        emit log_named_uint("profile nine FRI rounds", queriedCumulative - reducedCumulative);

        PQTCVerificationRegistry complete = new PQTCVerificationRegistry(realAir, new PQTCQueryVerifier(), parameterId);
        (uint256 actualA, bytes32 proofId) = this.measureA(complete, parameterId, publicValues, partA);
        uint256 actualB = this.measureB(complete, proofId, parameterId, publicValues, partB);
        emit log_named_uint("profile actual A execution", actualA);
        emit log_named_uint("profile actual B execution", actualB);
    }

    function testCompletionIsOneUse() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        registry.completeVerification(proofId, parameterId, publicValues, partB);
        vm.expectRevert(PQTCVerificationRegistry.UnknownProof.selector);
        registry.completeVerification(proofId, parameterId, publicValues, partB);
    }

    function testIdenticalPartAIsIdempotentWhileCheckpointExists() external {
        bytes32 first = registry.beginVerification(parameterId, publicValues, partA);
        bytes32 second = registry.beginVerification(parameterId, publicValues, partA);
        assertEq(first, second);
    }

    function testPartBIsBoundToConsumer() external {
        address consumer = address(0xBEEF);
        vm.prank(consumer);
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        vm.expectRevert(PQTCVerificationRegistry.UnauthorizedConsumer.selector);
        registry.completeVerification(proofId, parameterId, publicValues, partB);
    }

    function testRejectsMixedPartProofId() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        bytes memory mixed = partB;
        mixed[338] = bytes1(uint8(mixed[338]) ^ 1);
        vm.expectRevert(PQTCVerificationRegistry.InvalidCheckpoint.selector);
        registry.completeVerification(proofId, parameterId, publicValues, mixed);
    }

    function testRejectsDifferentStatementAtCompletion() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        uint32[64] memory other = publicValues;
        other[0] = other[0] == 0 ? 1 : 0;
        vm.expectRevert(PQTCVerificationRegistry.StatementMismatch.selector);
        registry.completeVerification(proofId, parameterId, other, partB);
    }

    function testRejectsTranscriptBoundGlobalMutation() external {
        bytes memory mutated = partA;
        mutated[370] = bytes1(uint8(mutated[370]) ^ 1); // first byte of trace root

        vm.expectRevert(PQTCVerificationRegistry.GlobalDataMismatch.selector);
        registry.beginVerification(parameterId, publicValues, mutated);
    }

    function testRejectsSecondPartGlobalMutation() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        bytes memory mutated = partB;
        mutated[402] = bytes1(uint8(mutated[402]) ^ 1); // first byte of part B trace root
        vm.expectRevert(PQTCVerificationRegistry.GlobalDataMismatch.selector);
        registry.completeVerification(proofId, parameterId, publicValues, mutated);
    }

    function testRejectsNoncanonicalHeaderField() external {
        bytes memory malformed = partA;
        _putU32(malformed, 82, 2_013_265_921);
        vm.expectRevert(abi.encodeWithSelector(CanonicalCodec.NonCanonicalField.selector, uint32(2_013_265_921)));
        registry.beginVerification(parameterId, publicValues, malformed);
    }

    function testFixtureSplitsAllQueriesIntoOrderedHalves() external view {
        uint256 halfA = _halfOffset(partA, A_CHECKPOINT_OFFSET);
        uint256 halfB = _halfOffset(partB, B_CHECKPOINT_OFFSET);
        assertEq(_u16(partA, halfA), 0);
        assertEq(_u16(partA, halfA + 2), 16);
        assertEq(_u16(partB, halfB), 16);
        assertEq(_u16(partB, halfB + 2), 16);
    }

    function testRejectsReorderedFirstHalfQueries() external {
        bytes memory reordered = partA;
        _swapDistinctIndices(reordered, _halfOffset(reordered, A_CHECKPOINT_OFFSET) + 4);
        vm.expectRevert(PQTCQueryVerifier.InvalidQuery.selector);
        registry.beginVerification(parameterId, publicValues, reordered);
    }

    function testRejectsReorderedSecondHalfQueries() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        bytes memory reordered = partB;
        uint256 half = _halfOffset(reordered, B_CHECKPOINT_OFFSET);
        _swapDistinctIndices(reordered, half + 4);
        vm.expectRevert(PQTCQueryVerifier.InvalidQuery.selector);
        registry.completeVerification(proofId, parameterId, publicValues, reordered);
    }

    function testRejectsMalformedPrunedFrontier() external {
        bytes32 proofId = registry.beginVerification(parameterId, publicValues, partA);
        bytes memory malformed = partB;
        uint256 half = _halfOffset(malformed, B_CHECKPOINT_OFFSET);
        uint256 firstFrontierCount = half + 4 + 16 * 4 + 16 * 8 * 4 + 16 * 8 * 4;
        _putU32(malformed, firstFrontierCount, type(uint32).max);
        vm.expectRevert();
        registry.completeVerification(proofId, parameterId, publicValues, malformed);
    }

    function _halfOffset(bytes memory proof, uint256 checkpointOffset) private pure returns (uint256) {
        uint16 uniqueCount = _u16(proof, checkpointOffset + 450);
        return checkpointOffset + 452 + uint256(uniqueCount) * 4;
    }

    function _swapDistinctIndices(bytes memory proof, uint256 indicesOffset) private pure {
        uint32 first = _u32(proof, indicesOffset);
        for (uint256 i = 1; i < 16; ++i) {
            uint256 offset = indicesOffset + i * 4;
            uint32 candidate = _u32(proof, offset);
            if (candidate != first) {
                _putU32(proof, indicesOffset, candidate);
                _putU32(proof, offset, first);
                return;
            }
        }
        revert("fixture has no distinct second-half query indices");
    }

    function _common(bytes memory proof) private pure returns (Digest512 memory parameter, uint32[64] memory values) {
        assembly ("memory-safe") {
            mstore(parameter, mload(add(proof, 0x30)))
            mstore(add(parameter, 0x20), mload(add(proof, 0x50)))
        }
        for (uint256 i; i < 64; ++i) {
            values[i] = _u32(proof, 82 + i * 4);
        }
    }

    function _fixtureWithdrawal() private view returns (PQTCClassicPool.Withdrawal memory withdrawal) {
        withdrawal = PQTCClassicPool.Withdrawal({
            root: _digestAt(16),
            nullifierHash: _digestAt(32),
            recipient: payable(address(0x0505050505050505050505050505050505050505)),
            relayer: payable(address(0x0606060606060606060606060606060606060606)),
            fee: 0
        });
    }

    function testRejectsFriSaltMutationAtRegeneratedOffset() external {
        bytes memory mutated = partA;
        uint256 saltOffset = _firstFriSaltOffset(mutated, A_CHECKPOINT_OFFSET);
        uint32 salt = _u32(mutated, saltOffset);
        _putU32(mutated, saltOffset, salt == 0 ? 1 : salt - 1);
        vm.expectRevert();
        registry.beginVerification(parameterId, publicValues, mutated);
    }

    function _firstFriSaltOffset(bytes memory proof, uint256 checkpointOffset) private pure returns (uint256) {
        uint256 cursor = _halfOffset(proof, checkpointOffset) + 4 + 16 * 4;
        cursor = _skipInputBatch(proof, cursor, 1, 8);
        cursor = _skipInputBatch(proof, cursor, 1, 194);
        cursor = _skipInputBatch(proof, cursor, 16, 8);
        return cursor + 16 * 16;
    }

    function _skipInputBatch(bytes memory proof, uint256 cursor, uint256 matrices, uint256 rowWidth)
        private
        pure
        returns (uint256)
    {
        cursor += 16 * matrices * rowWidth * 4 + 16 * matrices * 8 * 4;
        uint32 frontierCount = _u32(proof, cursor);
        return cursor + 4 + uint256(frontierCount) * 64;
    }

    function _digestAt(uint256 offset) private view returns (Digest512 memory) {
        uint32[16] memory fields;
        for (uint256 i; i < 16; ++i) {
            fields[i] = publicValues[offset + i];
        }
        return P2BB512.fromFields(fields);
    }

    function _u16(bytes memory data, uint256 offset) private pure returns (uint16 value) {
        assembly ("memory-safe") { value := shr(240, mload(add(add(data, 0x20), offset))) }
    }

    function _u32(bytes memory data, uint256 offset) private pure returns (uint32 value) {
        assembly ("memory-safe") { value := shr(224, mload(add(add(data, 0x20), offset))) }
    }

    // The measured wrapper includes an extra CALL, so this is a conservative upper bound
    // on execution plus the exact intrinsic cost of the pool-facing ABI calldata.
    function _transactionGas(uint256 executionGas, bytes memory callData) private pure returns (uint256 total) {
        total = 21_000 + executionGas;
        for (uint256 i; i < callData.length; ++i) {
            total += callData[i] == bytes1(0) ? 4 : 16;
        }
    }

    function _putU32(bytes memory data, uint256 offset, uint32 value) private pure {
        data[offset] = bytes1(uint8(value >> 24));
        data[offset + 1] = bytes1(uint8(value >> 16));
        data[offset + 2] = bytes1(uint8(value >> 8));
        data[offset + 3] = bytes1(uint8(value));
    }
}
