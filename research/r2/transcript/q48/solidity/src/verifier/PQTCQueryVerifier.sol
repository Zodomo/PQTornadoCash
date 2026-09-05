// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBear} from "../libraries/BabyBear.sol";
import {BabyBearExt4Packed as Ext} from "../libraries/BabyBearExt4Packed.sol";
import {CanonicalCodec} from "../libraries/CanonicalCodec.sol";
import {Digest512} from "../libraries/Digest512.sol";
import {PQTCProofCodec} from "../libraries/PQTCProofCodec.sol";
import {FriVerifier} from "./FriVerifier.sol";
import {MmcsVerifier} from "./MmcsVerifier.sol";

/// Verifies one 16-query half using packed rows and deduplicated pruned MMCS frontiers.
contract PQTCQueryVerifier {
    uint256 public immutable HALF;
    constructor(uint16 count) { require(count >= 22 && count <= 26, "query count"); HALF = count; }
    uint256 private constant GLOBAL_LOG_HEIGHT = 13;
    uint256 private constant TRACE_WIDTH = 190;
    uint256 private constant RANDOM_CODEWORDS = 4;
    uint256 private constant SALT_FIELDS = 8;
    uint256 private constant MULTIPLICATIVE_GENERATOR = 31;
    uint256 private constant REDUCTION_TERMS = 524;

    struct Context {
        Digest512[3] inputRoots; // random, trace, quotient
        Digest512[9] friRoots;
        uint256 zeta;
        uint256 friAlpha;
        uint256 finalPolynomial;
        uint256[9] friBetas;
        uint256[8] randomAtZeta;
        uint256[194] traceLocalAtZeta;
        uint256[194] traceNextAtZeta;
        uint256[128] quotientAtZeta;
        uint32[48] queryIndices;
    }

    struct ReductionState {
        uint32[32] indices;
        uint256[32] atXAtZeta;
        uint256[32] atXAtNext;
        uint256[32] inverseZeta;
        uint256[32] inverseNext;
        uint256[32] reduced;
        uint256[524] alphaPowers;
        uint256 zetaAggregate;
        uint256 nextAggregate;
    }

    error InvalidQuery();
    error InvalidFinalPolynomial();

    function verifyFirstHalf(bytes calldata proof, uint256 cursor, Context calldata context)
        external
        view
        virtual
        returns (uint256 next, uint256 zetaAggregate, uint256 nextAggregate)
    {
        return _verifyHalf(proof, cursor, 0, context, 0, 0, true);
    }

    function verifySecondHalf(
        bytes calldata proof,
        uint256 cursor,
        Context calldata context,
        uint256 zetaAggregate,
        uint256 nextAggregate
    ) external view returns (uint256 next) {
        (next,,) = _verifyHalf(proof, cursor, uint16(48 - HALF), context, zetaAggregate, nextAggregate, false);
    }

    function _verifyHalf(
        bytes calldata proof,
        uint256 cursor,
        uint16 expectedStart,
        Context calldata context,
        uint256 zetaAggregate,
        uint256 nextAggregate,
        bool computeAggregates
    ) private view returns (uint256 next, uint256 computedZeta, uint256 computedNext) {
        cursor = PQTCProofCodec.requireHalfHeader(proof, cursor, expectedStart, uint16(HALF));
        ReductionState memory state;
        for (uint256 q; q < HALF; ++q) {
            (state.indices[q], cursor) = CanonicalCodec.readU32(proof, cursor);
            if (state.indices[q] != context.queryIndices[uint256(expectedStart) + q]) revert InvalidQuery();
        }
        state.alphaPowers[0] = 1;
        for (uint256 i = 1; i < REDUCTION_TERMS; ++i) {
            state.alphaPowers[i] = Ext.mul(state.alphaPowers[i - 1], context.friAlpha);
        }
        if (computeAggregates) {
            (state.zetaAggregate, state.nextAggregate) = _openingAggregates(context, state.alphaPowers);
        } else {
            state.zetaAggregate = Ext.check(zetaAggregate);
            state.nextAggregate = Ext.check(nextAggregate);
        }
        _batchInverses(state.indices, context.zeta, state.inverseZeta, state.inverseNext);
        cursor = _inputBatch(proof, cursor, state, 0, context);
        cursor = _inputBatch(proof, cursor, state, 1, context);
        cursor = _inputBatch(proof, cursor, state, 2, context);
        for (uint256 q; q < HALF; ++q) {
            state.reduced[q] = Ext.add(
                Ext.mul(Ext.sub(state.zetaAggregate, state.atXAtZeta[q]), state.inverseZeta[q]),
                Ext.mul(Ext.sub(state.nextAggregate, state.atXAtNext[q]), state.inverseNext[q])
            );
        }
        next = _fri(proof, cursor, state.indices, state.reduced, context);
        computedZeta = state.zetaAggregate;
        computedNext = state.nextAggregate;
    }

    function _inputBatch(
        bytes calldata proof,
        uint256 cursor,
        ReductionState memory state,
        uint256 batch,
        Context calldata context
    ) internal view virtual returns (uint256 next) {
        uint256 matrices = batch == 2 ? 16 : 1;
        uint256 rowWidth = batch == 0 ? 8 : batch == 1 ? TRACE_WIDTH + RANDOM_CODEWORDS : 8;
        uint256 rowsOffset = cursor;
        uint256 rowBytes = HALF * matrices * rowWidth * 4;
        uint256 saltBytes = HALF * matrices * SALT_FIELDS * 4;
        if (cursor > proof.length || rowBytes + saltBytes > proof.length - cursor) {
            revert CanonicalCodec.Truncated();
        }
        _requireCanonicalRange(proof, rowsOffset, rowBytes);
        cursor += rowBytes;
        uint256 saltsOffset = cursor;
        _requireCanonicalRange(proof, saltsOffset, saltBytes);
        cursor += saltBytes;
        MmcsVerifier.LeafWords memory leaves;
        for (uint256 q; q < HALF; ++q) {
            (leaves.lefts[q], leaves.rights[q]) =
                MmcsVerifier.hashBatchLeaf(proof, rowsOffset, saltsOffset, q, matrices, rowWidth);
            _reduceBatch(proof, rowsOffset, q, batch, state);
        }
        return MmcsVerifier.verifyPruned(
            context.inputRoots[batch], state.indices, leaves, GLOBAL_LOG_HEIGHT, HALF, proof, cursor
        );
    }

    function _reduceBatch(
        bytes calldata proof,
        uint256 rowsOffset,
        uint256 query,
        uint256 batch,
        ReductionState memory state
    ) internal view virtual {
        uint256 rowWidth = batch == 0 ? 8 : batch == 1 ? TRACE_WIDTH + RANDOM_CODEWORDS : 128;
        uint256 start = rowsOffset + query * rowWidth * 4;
        if (batch == 0) {
            state.atXAtZeta[query] = _dotProductBase(proof, start, state.alphaPowers, 0, 8);
            return;
        }
        if (batch == 1) {
            state.atXAtZeta[query] = Ext.add(
                state.atXAtZeta[query],
                _dotProductBase(proof, start, state.alphaPowers, 8, TRACE_WIDTH + RANDOM_CODEWORDS)
            );
            state.atXAtNext[query] = _dotProductBase(
                proof, start, state.alphaPowers, 8 + TRACE_WIDTH + RANDOM_CODEWORDS, TRACE_WIDTH + RANDOM_CODEWORDS
            );
            return;
        }
        state.atXAtZeta[query] = Ext.add(
            state.atXAtZeta[query],
            _dotProductBase(proof, start, state.alphaPowers, 8 + 2 * (TRACE_WIDTH + RANDOM_CODEWORDS), 128)
        );
    }

    function _requireCanonicalRange(bytes calldata proof, uint256 offset, uint256 length) private view {
        assembly ("memory-safe") {
            let position := add(proof.offset, offset)
            let end := add(position, length)
            for {} lt(position, end) { position := add(position, 4) } {
                let value := shr(224, calldataload(position))
                if iszero(lt(value, 2013265921)) {
                    mstore(0, shl(224, 0x65a81779))
                    mstore(4, value)
                    revert(0, 36)
                }
            }
        }
    }

    function _dotProductBase(
        bytes calldata proof,
        uint256 rowOffset,
        uint256[524] memory powers,
        uint256 powerOffset,
        uint256 count
    ) private view returns (uint256 result) {
        assembly ("memory-safe") {
            let p := 2013265921
            let mask := 0xffffffff
            let input := add(proof.offset, rowOffset)
            let power := add(powers, mul(powerOffset, 0x20))
            let end := add(power, mul(count, 0x20))
            let a0 := 0
            let a1 := 0
            let a2 := 0
            let a3 := 0
            for {} lt(power, end) {
                power := add(power, 0x20)
                input := add(input, 4)
            } {
                let scalar := shr(224, calldataload(input))
                let coefficient := mload(power)
                a0 := addmod(a0, mulmod(and(coefficient, mask), scalar, p), p)
                a1 := addmod(a1, mulmod(and(shr(32, coefficient), mask), scalar, p), p)
                a2 := addmod(a2, mulmod(and(shr(64, coefficient), mask), scalar, p), p)
                a3 := addmod(a3, mulmod(and(shr(96, coefficient), mask), scalar, p), p)
            }
            result := or(or(a0, shl(32, a1)), or(shl(64, a2), shl(96, a3)))
        }
    }

    function _openingAggregates(Context calldata context, uint256[524] memory alphaPowers)
        private
        view
        returns (uint256 zetaAggregate, uint256 nextAggregate)
    {
        for (uint256 column; column < 8; ++column) {
            zetaAggregate = Ext.add(zetaAggregate, Ext.mul(alphaPowers[column], context.randomAtZeta[column]));
        }
        for (uint256 column; column < TRACE_WIDTH + RANDOM_CODEWORDS; ++column) {
            zetaAggregate = Ext.add(zetaAggregate, Ext.mul(alphaPowers[8 + column], context.traceLocalAtZeta[column]));
            nextAggregate = Ext.add(
                nextAggregate,
                Ext.mul(alphaPowers[8 + TRACE_WIDTH + RANDOM_CODEWORDS + column], context.traceNextAtZeta[column])
            );
        }
        for (uint256 matrix; matrix < 16; ++matrix) {
            for (uint256 column; column < 8; ++column) {
                uint256 position = 8 + 2 * (TRACE_WIDTH + RANDOM_CODEWORDS) + matrix * 8 + column;
                zetaAggregate =
                    Ext.add(zetaAggregate, Ext.mul(alphaPowers[position], context.quotientAtZeta[matrix * 8 + column]));
            }
        }
    }

    function _batchInverses(
        uint32[32] memory indices,
        uint256 zeta,
        uint256[32] memory inverseZeta,
        uint256[32] memory inverseNext
    ) private view {
        uint256[64] memory denominators;
        uint256[64] memory prefixes;
        uint256 zetaNext = Ext.mulBase(zeta, FriVerifier.twoAdicGenerator(8));
        uint256 product = 1;
        for (uint256 q; q < HALF; ++q) {
            uint256 point = _queryPoint(indices[q]);
            denominators[q] = Ext.sub(zeta, point);
            denominators[HALF + q] = Ext.sub(zetaNext, point);
        }
        for (uint256 i; i < HALF * 2; ++i) {
            prefixes[i] = product;
            product = Ext.mul(product, denominators[i]);
        }
        uint256 inverseProduct = Ext.inv(product);
        for (uint256 reverse = HALF * 2; reverse > 0; --reverse) {
            uint256 i = reverse - 1;
            uint256 inverse = Ext.mul(inverseProduct, prefixes[i]);
            inverseProduct = Ext.mul(inverseProduct, denominators[i]);
            if (i < HALF) inverseZeta[i] = inverse;
            else inverseNext[i - HALF] = inverse;
        }
    }

    function _fri(
        bytes calldata proof,
        uint256 cursor,
        uint32[32] memory indices,
        uint256[32] memory folded,
        Context calldata context
    ) internal view virtual returns (uint256 next) {
        for (uint256 round; round < 9; ++round) {
            cursor = _friRound(proof, cursor, indices, folded, context, round);
        }
        for (uint256 q; q < HALF; ++q) {
            if (folded[q] != context.finalPolynomial) revert InvalidFinalPolynomial();
        }
        return cursor;
    }

    function _friRound(
        bytes calldata proof,
        uint256 cursor,
        uint32[32] memory indices,
        uint256[32] memory folded,
        Context calldata context,
        uint256 round
    ) private view returns (uint256) {
        uint256[32] memory siblings;
        for (uint256 q; q < HALF; ++q) {
            (siblings[q], cursor) = _readExtension(proof, cursor);
        }
        uint256 saltsOffset = cursor;
        uint256 saltBytes = HALF * SALT_FIELDS * 4;
        if (cursor > proof.length || saltBytes > proof.length - cursor) revert CanonicalCodec.Truncated();
        _requireCanonicalRange(proof, saltsOffset, saltBytes);
        cursor += saltBytes;
        uint32[32] memory parentIndices;
        MmcsVerifier.LeafWords memory leaves;
        uint256 logFoldedHeight = GLOBAL_LOG_HEIGHT - round - 1;
        for (uint256 q; q < HALF; ++q) {
            uint256 index = indices[q];
            (leaves.lefts[q], leaves.rights[q]) =
                MmcsVerifier.hashFriLeafWords(folded[q], siblings[q], index, proof, saltsOffset + q * SALT_FIELDS * 4);
            parentIndices[q] = uint32(index >> 1);
        }
        uint32[32] memory inverseTwoXs = _inverseFoldPoints(parentIndices, HALF, logFoldedHeight);
        cursor = MmcsVerifier.verifyPruned(
            context.friRoots[round], parentIndices, leaves, logFoldedHeight, HALF, proof, cursor
        );
        for (uint256 q; q < HALF; ++q) {
            uint256 index = indices[q];
            uint256 low = index & 1 == 0 ? folded[q] : siblings[q];
            uint256 high = index & 1 == 0 ? siblings[q] : folded[q];
            indices[q] = parentIndices[q];
            folded[q] = _fold(context.friBetas[round], low, high, inverseTwoXs[q]);
        }
        return cursor;
    }

    function _queryPoint(uint256 index) private view returns (uint256) {
        uint256 generator = FriVerifier.twoAdicGenerator(GLOBAL_LOG_HEIGHT);
        return BabyBear.mul(
            MULTIPLICATIVE_GENERATOR, BabyBear.pow(generator, FriVerifier.reverseBits(index, GLOBAL_LOG_HEIGHT))
        );
    }

    function _fold(uint256 beta, uint256 low, uint256 high, uint256 inverseTwoX) private view returns (uint256) {
        uint256 evenPart = Ext.mulBase(Ext.add(low, high), 1_006_632_961);
        uint256 oddPart = Ext.mul(Ext.mulBase(Ext.sub(low, high), inverseTwoX), beta);
        return Ext.add(evenPart, oddPart);
    }

    function _inverseFoldPoints(uint32[32] memory parentIndices, uint256 count, uint256 logHeight)
        private
        view
        returns (uint32[32] memory inverses)
    {
        uint32[32] memory points;
        uint32[32] memory prefixes;
        uint256 generator = FriVerifier.twoAdicGenerator(logHeight + 1);
        uint256 order = uint256(1) << (logHeight + 1);
        uint256 exponentSum;
        uint256 product = 1;
        for (uint256 q; q < count; ++q) {
            uint256 exponent = FriVerifier.reverseBits(parentIndices[q], logHeight);
            uint32 point = uint32(BabyBear.pow(generator, exponent));
            points[q] = point;
            prefixes[q] = uint32(product);
            product = BabyBear.mul(product, point);
            exponentSum = (exponentSum + exponent) & (order - 1);
        }
        uint256 inverseProduct = BabyBear.pow(generator, (order - exponentSum) & (order - 1));
        for (uint256 reverse = count; reverse > 0; --reverse) {
            uint256 q = reverse - 1;
            inverses[q] = uint32(BabyBear.mul(1_006_632_961, BabyBear.mul(inverseProduct, prefixes[q])));
            inverseProduct = BabyBear.mul(inverseProduct, points[q]);
        }
    }

    function _readExtension(bytes calldata proof, uint256 cursor) private view returns (uint256 value, uint256 next) {
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
}
