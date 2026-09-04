// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

/// @notice Research-only SP-31 kernels. This contract is not a verifier and must not be integrated.
contract VerifierOptimizationBench {
    uint256 internal constant P = 2_013_265_921;
    uint256 internal constant MAX_FIELDS = 512;
    bytes internal constant POWERS_OF_SEVEN = hex"0000000100000007000000310000015700000961000041a70001cb91000c90f70057f6c10267bf4710d63af175db9c976901481b0f08f8b7693ecd0110b79b0175053d076324ab2b5e00ae283a04c3132e21558252e9568c64615dd066a990ab76a2f4a86e74b0923530d3f80c55cbc556589263046c00b01ef404d060ac21af";
    bytes internal constant QUERY_POINTS_STEP_127 = hex"000000011495082e32472c745111f9a372ff454f434a8f0c224f6a1676813c88";

    error Bound();
    error Noncanonical();
    error ZeroDenominator();
    error ZeroLegal();
    error InvalidWitness();
    error InvalidFrontier();

    function materializedAlpha(uint256[] calldata coefficients, uint256 alpha) external pure returns (uint256 acc) {
        if (coefficients.length > MAX_FIELDS || alpha >= P) revert Bound();
        uint256[] memory powers = new uint256[](coefficients.length);
        if (powers.length != 0) powers[0] = 1;
        for (uint256 i = 1; i < powers.length; ++i) powers[i] = mulmod(powers[i - 1], alpha, P);
        for (uint256 i; i < powers.length; ++i) {
            if (coefficients[i] >= P) revert Noncanonical();
            acc = addmod(acc, mulmod(coefficients[i], powers[i], P), P);
        }
    }

    function streamedAlpha(uint256[] calldata coefficients, uint256 alpha) external pure returns (uint256 acc) {
        if (coefficients.length > MAX_FIELDS || alpha >= P) revert Bound();
        uint256 power = 1;
        for (uint256 i; i < coefficients.length; ++i) {
            if (coefficients[i] >= P) revert Noncanonical();
            acc = addmod(acc, mulmod(coefficients[i], power, P), P);
            power = mulmod(power, alpha, P);
        }
    }

    function hornerAlpha(uint256[] calldata coefficients, uint256 alpha) external pure returns (uint256 acc) {
        if (coefficients.length > MAX_FIELDS || alpha >= P) revert Bound();
        for (uint256 i = coefficients.length; i != 0; --i) {
            if (coefficients[i - 1] >= P) revert Noncanonical();
            acc = addmod(mulmod(acc, alpha, P), coefficients[i - 1], P);
        }
    }

    function exponentiateInverse(uint256 denominator) external pure returns (uint256) {
        if (denominator == 0 || denominator >= P) revert ZeroDenominator();
        uint256 exponent = P - 2;
        uint256 base = denominator;
        uint256 result = 1;
        while (exponent != 0) {
            if ((exponent & 1) != 0) result = mulmod(result, base, P);
            base = mulmod(base, base, P);
            exponent >>= 1;
        }
        return result;
    }

    function checkedRequiredInverse(uint256 denominator, uint256 witness) external pure returns (uint256) {
        if (denominator == 0 || denominator >= P) revert ZeroDenominator();
        if (witness >= P || mulmod(denominator, witness, P) != 1) revert InvalidWitness();
        return witness;
    }

    function zeroLegalInverseForbidden(uint256, uint256) external pure {
        revert ZeroLegal();
    }

    function parseThenDot(bytes calldata encoded, uint256[] calldata weights) external pure returns (uint256 acc) {
        uint256 count = weights.length;
        if (count > MAX_FIELDS || encoded.length != count * 4) revert Bound();
        uint256[] memory fields = new uint256[](count);
        for (uint256 i; i < count; ++i) fields[i] = _u32be(encoded, i * 4);
        for (uint256 i; i < count; ++i) {
            if (weights[i] >= P) revert Noncanonical();
            acc = addmod(acc, mulmod(fields[i], weights[i], P), P);
        }
    }

    function fusedParseDot(bytes calldata encoded, uint256[] calldata weights) external pure returns (uint256 acc) {
        uint256 count = weights.length;
        if (count > MAX_FIELDS || encoded.length != count * 4) revert Bound();
        for (uint256 i; i < count; ++i) {
            if (weights[i] >= P) revert Noncanonical();
            acc = addmod(acc, mulmod(_u32be(encoded, i * 4), weights[i], P), P);
        }
    }

    function copiedEvaluation(uint256[] calldata values, uint256 alpha) external pure returns (uint256 acc) {
        if (values.length > MAX_FIELDS || alpha >= P) revert Bound();
        uint256[] memory copied = values;
        uint256 power = 1;
        for (uint256 i; i < copied.length; ++i) {
            if (copied[i] >= P) revert Noncanonical();
            acc = addmod(acc, mulmod(copied[i], power, P), P);
            power = mulmod(power, alpha, P);
        }
    }

    function calldataEvaluation(uint256[] calldata values, uint256 alpha) external pure returns (uint256 acc) {
        if (values.length > MAX_FIELDS || alpha >= P) revert Bound();
        uint256 power = 1;
        for (uint256 i; i < values.length; ++i) {
            if (values[i] >= P) revert Noncanonical();
            acc = addmod(acc, mulmod(values[i], power, P), P);
            power = mulmod(power, alpha, P);
        }
    }

    function fixedPowerTableDigest() external pure returns (uint256 acc) {
        bytes memory table = POWERS_OF_SEVEN;
        for (uint256 i; i < 32; ++i) {
            uint256 value;
            assembly ("memory-safe") {
                value := shr(224, mload(add(add(table, 0x20), mul(i, 4))))
            }
            acc ^= value;
        }
    }

    function derivedPowerTableDigest() external pure returns (uint256 acc) {
        uint256 x = 1;
        for (uint256 i; i < 32; ++i) { acc ^= x; x = mulmod(x, 7, P); }
    }

    function checkedCalldataTableDigest(uint256[] calldata table) external pure returns (uint256 acc) {
        if (table.length != 32 || table[0] != 1) revert Bound();
        for (uint256 i; i < table.length; ++i) {
            if (table[i] >= P || (i != 0 && table[i] != mulmod(table[i - 1], 7, P))) revert InvalidWitness();
            acc ^= table[i];
        }
    }

    function exponentQueryPoints(uint256 base, uint256 step, uint256 count) external pure returns (uint256 acc) {
        if (base == 0 || base >= P || count > 64) revert Bound();
        for (uint256 i; i < count; ++i) acc ^= _pow(base, i * step);
    }

    function incrementalQueryPoints(uint256 base, uint256 step, uint256 count) external pure returns (uint256 acc) {
        if (base == 0 || base >= P || count > 64) revert Bound();
        uint256 x = 1;
        uint256 multiplier = _pow(base, step);
        for (uint256 i; i < count; ++i) { acc ^= x; x = mulmod(x, multiplier, P); }
    }

    function checkedQueryPoints(uint256 base, uint256 step, uint256[] calldata points) external pure returns (uint256 acc) {
        if (base == 0 || base >= P || points.length > 64 || points.length == 0 || points[0] != 1) revert Bound();
        uint256 multiplier = _pow(base, step);
        for (uint256 i; i < points.length; ++i) {
            if (points[i] >= P || (i != 0 && points[i] != mulmod(points[i - 1], multiplier, P))) revert InvalidWitness();
            acc ^= points[i];
        }
    }

    function fixedQueryPoints8() external pure returns (uint256 acc) {
        bytes memory table = QUERY_POINTS_STEP_127;
        for (uint256 i; i < 8; ++i) {
            uint256 value;
            assembly ("memory-safe") {
                value := shr(224, mload(add(add(table, 0x20), mul(i, 4))))
            }
            acc ^= value;
        }
    }

    function frontierCount(uint32[] calldata sortedUniqueIndices, uint256 depth) external pure returns (uint256 frontier) {
        if (depth == 0 || depth > 31 || sortedUniqueIndices.length == 0 || sortedUniqueIndices.length > 64) revert Bound();
        uint32[] memory nodes = sortedUniqueIndices;
        for (uint256 i; i < nodes.length; ++i) {
            if (nodes[i] >= uint32(1 << depth) || (i != 0 && nodes[i] <= nodes[i - 1])) revert InvalidFrontier();
        }
        uint256 length = nodes.length;
        for (uint256 level; level < depth; ++level) {
            uint256 writeAt;
            uint256 readAt;
            while (readAt < length) {
                uint32 node = nodes[readAt];
                if (readAt + 1 < length && nodes[readAt + 1] == (node ^ 1)) readAt += 2;
                else { ++frontier; ++readAt; }
                uint32 parent = node >> 1;
                if (writeAt == 0 || nodes[writeAt - 1] != parent) nodes[writeAt++] = parent;
            }
            length = writeAt;
        }
    }

    function unpack32(bytes calldata encoded, uint256 count) external pure returns (uint256 checksum) {
        if (count > MAX_FIELDS || encoded.length != count * 4) revert Bound();
        for (uint256 i; i < count; ++i) checksum ^= _u32be(encoded, i * 4);
    }

    function unpack31(bytes calldata packed, uint256 count) external pure returns (uint256 checksum) {
        return _unpack31(packed, count);
    }

    function section31(bytes calldata proof, uint256 offset, uint256 count) external pure returns (uint256 checksum) {
        if (offset > proof.length || count > MAX_FIELDS || count > (type(uint256).max - 7) / 31) revert Bound();
        uint256 length = (count * 31 + 7) / 8;
        if (length > proof.length - offset) revert Bound();
        return _unpack31(proof[offset:offset + length], count);
    }

    function splitCost(uint256 partAQueries, bool airInA) external pure returns (uint256 partA, uint256 partB) {
        if (partAQueries < 8 || partAQueries > 16) revert Bound();
        uint256 partBQueries = 32 - partAQueries;
        uint256 sharedA = 8_648_031;
        uint256 sharedB = 8_976_981;
        uint256 perQuery = 211_212;
        uint256 airSegment = 2_863_647;
        partA = sharedA + partAQueries * perQuery + (airInA ? airSegment : 0);
        partB = sharedB + partBQueries * perQuery + (airInA ? 0 : airSegment);
    }

    function _u32be(bytes calldata encoded, uint256 at) private pure returns (uint256 value) {
        value = uint256(uint32(bytes4(encoded[at:at + 4])));
        if (value >= P) revert Noncanonical();
    }

    function _unpack31(bytes calldata packed, uint256 count) private pure returns (uint256 checksum) {
        if (count > MAX_FIELDS || count > (type(uint256).max - 7) / 31 || packed.length != (count * 31 + 7) / 8) revert Bound();
        uint256 bits;
        uint256 used;
        uint256 at;
        for (uint256 i; i < count; ++i) {
            while (used < 31) { bits |= uint256(uint8(packed[at++])) << used; used += 8; }
            uint256 value = bits & 0x7fff_ffff;
            if (value >= P) revert Noncanonical();
            checksum ^= value;
            bits >>= 31;
            used -= 31;
        }
        if (used != 0 && bits != 0) revert Noncanonical();
    }

    function _pow(uint256 base, uint256 exponent) private pure returns (uint256 result) {
        result = 1;
        while (exponent != 0) {
            if ((exponent & 1) != 0) result = mulmod(result, base, P);
            base = mulmod(base, base, P);
            exponent >>= 1;
        }
    }
}
