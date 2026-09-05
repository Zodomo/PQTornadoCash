// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBearExt4Packed as Ext} from "../libraries/BabyBearExt4Packed.sol";
import {AirEvaluatorPoseidon} from "./AirEvaluatorPoseidon.sol";
import {StarkOodVerifier} from "./StarkOodVerifier.sol";

/// Stateless v0.3 OOD verifier for the 190-column Poseidon withdrawal AIR.
contract PQTCAirStageVerifier {
    uint256 private constant WIDTH = 190;

    error InvalidOodShape();

    function evaluateRange(
        uint256[] calldata traceLocal,
        uint256[] calldata traceNext,
        uint32[64] calldata publicValues,
        uint256 zeta,
        uint256 alpha,
        uint256 accumulator,
        uint8 start,
        uint8 end
    ) external pure virtual returns (uint256) {
        if (traceLocal.length != WIDTH || traceNext.length != WIDTH) revert InvalidOodShape();
        uint256[] memory local = new uint256[](WIDTH);
        uint256[] memory next = new uint256[](WIDTH);
        uint256[] memory publicExt = new uint256[](64);
        for (uint256 i; i < WIDTH; ++i) {
            local[i] = Ext.check(traceLocal[i]);
            next[i] = Ext.check(traceNext[i]);
        }
        for (uint256 i; i < 64; ++i) {
            publicExt[i] = Ext.fromBase(publicValues[i]);
        }
        StarkOodVerifier.Selectors memory selectors = StarkOodVerifier.selectors(zeta);
        return AirEvaluatorPoseidon.evaluateRange(
            local,
            next,
            publicExt,
            selectors.isFirst,
            selectors.isLast,
            selectors.isTransition,
            Ext.check(alpha),
            Ext.check(accumulator),
            start,
            end
        );
    }

    function requireValid(uint256 folded, uint256[] calldata quotientOpenings, uint256 zeta)
        external
        pure
        returns (bool)
    {
        if (quotientOpenings.length != 64) revert InvalidOodShape();
        uint256[] memory quotient = new uint256[](64);
        for (uint256 i; i < 64; ++i) {
            quotient[i] = Ext.check(quotientOpenings[i]);
        }
        StarkOodVerifier.requireValid(Ext.check(folded), quotient, zeta);
        return true;
    }

    function verify(
        uint256[] calldata traceLocal,
        uint256[] calldata traceNext,
        uint256[] calldata quotientOpenings,
        uint32[64] calldata publicValues,
        uint256 zeta,
        uint256 alpha
    ) external pure returns (bool) {
        if (traceLocal.length != WIDTH || traceNext.length != WIDTH || quotientOpenings.length != 64) {
            revert InvalidOodShape();
        }
        uint256[] memory local = new uint256[](WIDTH);
        uint256[] memory next = new uint256[](WIDTH);
        uint256[] memory publicExt = new uint256[](64);
        for (uint256 i; i < WIDTH; ++i) {
            local[i] = Ext.check(traceLocal[i]);
            next[i] = Ext.check(traceNext[i]);
        }
        for (uint256 i; i < 64; ++i) {
            publicExt[i] = Ext.fromBase(publicValues[i]);
        }
        StarkOodVerifier.Selectors memory selectors = StarkOodVerifier.selectors(zeta);
        uint256 folded = AirEvaluatorPoseidon.evaluate(
            local, next, publicExt, selectors.isFirst, selectors.isLast, selectors.isTransition, Ext.check(alpha)
        );
        uint256[] memory quotient = new uint256[](64);
        for (uint256 i; i < 64; ++i) {
            quotient[i] = Ext.check(quotientOpenings[i]);
        }
        StarkOodVerifier.requireValid(folded, quotient, zeta);
        return true;
    }
}
