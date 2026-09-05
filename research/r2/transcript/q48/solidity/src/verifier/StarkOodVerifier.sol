// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBear} from "../libraries/BabyBear.sol";
import {BabyBearExt4Packed as Ext} from "../libraries/BabyBearExt4Packed.sol";
import {FriVerifier} from "./FriVerifier.sol";

/// Fixed-domain OOD arithmetic for the v0.2 256-row hiding withdrawal AIR.
library StarkOodVerifier {
    uint256 private constant TRACE_LOG_SIZE = 8;
    uint256 private constant QUOTIENT_LOG_SIZE = 12;
    uint256 private constant QUOTIENT_CHUNK_LOG_SIZE = 8;
    uint256 private constant QUOTIENT_CHUNKS = 16;
    uint256 private constant MULTIPLICATIVE_GENERATOR = 31;

    struct Selectors {
        uint256 isFirst;
        uint256 isLast;
        uint256 isTransition;
        uint256 invVanishing;
    }

    error InvalidQuotientShape();
    error OodEvaluationMismatch();

    function selectors(uint256 zeta) internal pure returns (Selectors memory result) {
        uint256 subgroupGenerator = FriVerifier.twoAdicGenerator(TRACE_LOG_SIZE);
        uint256 inverseGenerator = BabyBear.inv(subgroupGenerator);
        uint256 vanishing = Ext.sub(Ext.pow(zeta, uint256(1) << TRACE_LOG_SIZE), 1);
        uint256 firstDenominator = Ext.sub(zeta, 1);
        uint256 lastDenominator = Ext.sub(zeta, inverseGenerator);
        uint256 inverseProduct = Ext.inv(Ext.mul(Ext.mul(firstDenominator, lastDenominator), vanishing));
        result.isFirst = Ext.mul(vanishing, Ext.mul(Ext.mul(lastDenominator, vanishing), inverseProduct));
        result.isLast = Ext.mul(vanishing, Ext.mul(Ext.mul(firstDenominator, vanishing), inverseProduct));
        result.isTransition = lastDenominator;
        result.invVanishing = Ext.mul(Ext.mul(firstDenominator, lastDenominator), inverseProduct);
    }

    /// Each of 16 quotient chunks is represented by four extension-valued
    /// openings of its base-field coefficient polynomials.
    function recomposeQuotient(uint256[] memory quotientOpenings, uint256 zeta)
        internal
        pure
        returns (uint256 quotient)
    {
        if (quotientOpenings.length != QUOTIENT_CHUNKS * 4) revert InvalidQuotientShape();
        uint256 quotientGenerator = FriVerifier.twoAdicGenerator(QUOTIENT_LOG_SIZE);
        uint256[16] memory shifts;
        uint256[16] memory inverseShifts;
        uint256 shift = MULTIPLICATIVE_GENERATOR;
        for (uint256 i = 0; i < QUOTIENT_CHUNKS; i++) {
            shifts[i] = shift;
            inverseShifts[i] = BabyBear.inv(shift);
            shift = BabyBear.mul(shift, quotientGenerator);
        }
        uint256[16] memory vanishingAtZeta;
        uint256[17] memory prefixes;
        prefixes[0] = 1;
        for (uint256 i = 0; i < QUOTIENT_CHUNKS; i++) {
            vanishingAtZeta[i] = _vanishingWithInverse(zeta, inverseShifts[i], QUOTIENT_CHUNK_LOG_SIZE);
            prefixes[i + 1] = Ext.mul(prefixes[i], vanishingAtZeta[i]);
        }
        uint256 suffix = 1;
        for (uint256 reverse = QUOTIENT_CHUNKS; reverse > 0; reverse--) {
            uint256 i = reverse - 1;
            uint256 numerator = Ext.mul(prefixes[i], suffix);
            suffix = Ext.mul(vanishingAtZeta[i], suffix);
            uint256 denominator = 1;
            for (uint256 j = 0; j < QUOTIENT_CHUNKS; j++) {
                if (j == i) continue;
                uint256 ratio = BabyBear.mul(shifts[i], inverseShifts[j]);
                denominator = BabyBear.mul(
                    denominator, BabyBear.sub(BabyBear.pow(ratio, uint256(1) << QUOTIENT_CHUNK_LOG_SIZE), 1)
                );
            }
            uint256 weight = Ext.mulBase(numerator, BabyBear.inv(denominator));
            uint256 chunk = quotientOpenings[i * 4];
            uint256 basis = uint256(1) << 32;
            for (uint256 coefficient = 1; coefficient < 4; coefficient++) {
                chunk = Ext.add(chunk, Ext.mul(basis, quotientOpenings[i * 4 + coefficient]));
                basis = Ext.mul(basis, uint256(1) << 32);
            }
            quotient = Ext.add(quotient, Ext.mul(weight, chunk));
        }
    }

    function requireValid(uint256 foldedConstraints, uint256[] memory quotientOpenings, uint256 zeta) internal pure {
        Selectors memory domainSelectors = selectors(zeta);
        uint256 expected = recomposeQuotient(quotientOpenings, zeta);
        if (Ext.mul(foldedConstraints, domainSelectors.invVanishing) != expected) {
            revert OodEvaluationMismatch();
        }
    }

    function _vanishingWithInverse(uint256 point, uint256 inverseShift, uint256 logSize)
        private
        pure
        returns (uint256)
    {
        return Ext.sub(Ext.pow(Ext.mulBase(point, inverseShift), uint256(1) << logSize), 1);
    }
}
