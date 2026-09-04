// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity 0.8.30;

/// @notice Research-only SP-40 arithmetic kernels. This contract is not a verifier.
/// @dev Coefficients are canonical, least-degree-first. Candidate IDs are F0..F5 => 0..5.
contract FieldBakeoff {
    error InvalidCandidate(uint8 candidate);
    error NonCanonical(uint256 value, uint256 modulus);
    error DivisionByZero();
    error InvalidLength(uint256 expected, uint256 actual);

    uint256 internal constant BABY_BEAR = 2_013_265_921;
    uint256 internal constant KOALA_BEAR = 2_130_706_433;
    uint256 internal constant GOLDILOCKS = 18_446_744_069_414_584_321;
    uint256 internal constant MERSENNE31 = 2_147_483_647;
    uint256 internal constant BN254_SCALAR =
        21_888_242_871_839_275_222_246_405_745_257_275_088_548_364_400_416_034_343_698_204_186_575_808_495_617;
    uint64 internal constant SEED = 0x535034304649454c;
    uint64 internal constant MIX = 0x9e3779b97f4a7c15;

    // Shapes: binomial x^d-w, quintic x^5+x^2-1, QM31 tower, degree-one base.
    function specification(uint8 candidate)
        public
        pure
        returns (uint256 modulus, uint256 degree, uint256 shape, uint256 nonresidue)
    {
        if (candidate == 0) return (BABY_BEAR, 4, 0, 11);
        if (candidate == 1) return (KOALA_BEAR, 4, 0, 3);
        if (candidate == 2) return (KOALA_BEAR, 5, 1, 0);
        if (candidate == 3) return (GOLDILOCKS, 2, 0, 7);
        if (candidate == 4) return (MERSENNE31, 4, 2, 0);
        if (candidate == 5) return (BN254_SCALAR, 1, 3, 0);
        revert InvalidCandidate(candidate);
    }

    function canonical(uint8 candidate, uint256 value) external pure returns (uint256) {
        (uint256 p,,,) = specification(candidate);
        return _check(value, p);
    }

    function baseAdd(uint8 candidate, uint256 a, uint256 b) public pure returns (uint256) {
        (uint256 p,,,) = specification(candidate);
        return addmod(_check(a, p), _check(b, p), p);
    }

    function baseSub(uint8 candidate, uint256 a, uint256 b) public pure returns (uint256) {
        (uint256 p,,,) = specification(candidate);
        return _sub(_check(a, p), _check(b, p), p);
    }

    function baseMul(uint8 candidate, uint256 a, uint256 b) public pure returns (uint256) {
        (uint256 p,,,) = specification(candidate);
        return mulmod(_check(a, p), _check(b, p), p);
    }

    function baseSquare(uint8 candidate, uint256 a) public pure returns (uint256) {
        (uint256 p,,,) = specification(candidate);
        a = _check(a, p);
        return mulmod(a, a, p);
    }

    function basePower(uint8 candidate, uint256 a, uint256 exponent) public pure returns (uint256) {
        (uint256 p,,,) = specification(candidate);
        return _powBase(_check(a, p), exponent, p);
    }

    function baseInverse(uint8 candidate, uint256 a) public pure returns (uint256) {
        (uint256 p,,,) = specification(candidate);
        a = _check(a, p);
        if (a == 0) revert DivisionByZero();
        return _powBase(a, p - 2, p);
    }

    function extensionAdd(uint8 candidate, uint256[] memory a, uint256[] memory b)
        public
        pure
        returns (uint256[] memory out)
    {
        (uint256 p, uint256 d,,) = specification(candidate);
        _checkExt(a, d, p);
        _checkExt(b, d, p);
        out = new uint256[](d);
        for (uint256 i; i < d; ++i) out[i] = addmod(a[i], b[i], p);
    }

    function extensionSub(uint8 candidate, uint256[] memory a, uint256[] memory b)
        public
        pure
        returns (uint256[] memory out)
    {
        (uint256 p, uint256 d,,) = specification(candidate);
        _checkExt(a, d, p);
        _checkExt(b, d, p);
        out = new uint256[](d);
        for (uint256 i; i < d; ++i) out[i] = _sub(a[i], b[i], p);
    }

    function extensionMul(uint8 candidate, uint256[] memory a, uint256[] memory b)
        public
        pure
        returns (uint256[] memory)
    {
        (uint256 p, uint256 d, uint256 shape, uint256 w) = specification(candidate);
        _checkExt(a, d, p);
        _checkExt(b, d, p);
        if (shape == 2) return _mulQm31(a, b, p);
        if (shape == 3) {
            uint256[] memory singleton = new uint256[](1);
            singleton[0] = mulmod(a[0], b[0], p);
            return singleton;
        }
        uint256[] memory convolution = new uint256[](2 * d - 1);
        for (uint256 i; i < d; ++i) {
            for (uint256 j; j < d; ++j) {
                convolution[i + j] = addmod(convolution[i + j], mulmod(a[i], b[j], p), p);
            }
        }
        if (shape == 0) {
            for (uint256 k = 2 * d - 2; k >= d; --k) {
                convolution[k - d] = addmod(convolution[k - d], mulmod(convolution[k], w, p), p);
            }
        } else {
            // x^5 = 1 - x^2 for the pinned KoalaBear quintic trinomial.
            for (uint256 k = 8; k >= 5; --k) {
                convolution[k - 5] = addmod(convolution[k - 5], convolution[k], p);
                convolution[k - 3] = _sub(convolution[k - 3], convolution[k], p);
            }
        }
        uint256[] memory out = new uint256[](d);
        for (uint256 i; i < d; ++i) out[i] = convolution[i];
        return out;
    }

    function extensionSquare(uint8 candidate, uint256[] memory a) public pure returns (uint256[] memory) {
        return extensionMul(candidate, a, a);
    }

    function extensionMulBase(uint8 candidate, uint256[] memory a, uint256 b)
        public
        pure
        returns (uint256[] memory out)
    {
        (uint256 p, uint256 d,,) = specification(candidate);
        _checkExt(a, d, p);
        b = _check(b, p);
        out = new uint256[](d);
        for (uint256 i; i < d; ++i) out[i] = mulmod(a[i], b, p);
    }

    function extensionPower(uint8 candidate, uint256[] memory a, uint256 exponent)
        public
        pure
        returns (uint256[] memory result)
    {
        (uint256 p, uint256 d,,) = specification(candidate);
        _checkExt(a, d, p);
        result = new uint256[](d);
        result[0] = 1;
        while (exponent != 0) {
            if ((exponent & 1) != 0) result = extensionMul(candidate, result, a);
            exponent >>= 1;
            if (exponent != 0) a = extensionMul(candidate, a, a);
        }
    }

    function extensionInverse(uint8 candidate, uint256[] memory a)
        public
        pure
        returns (uint256[] memory)
    {
        (uint256 p, uint256 d,,) = specification(candidate);
        _checkExt(a, d, p);
        bool nonzero;
        for (uint256 i; i < d; ++i) nonzero = nonzero || a[i] != 0;
        if (!nonzero) revert DivisionByZero();
        uint256 order = 1;
        for (uint256 i; i < d; ++i) order *= p;
        return extensionPower(candidate, a, order - 2);
    }

    function dotProduct(uint8 candidate, uint256[][] memory extensions, uint256[] memory bases)
        public
        pure
        returns (uint256[] memory accumulator)
    {
        if (extensions.length != bases.length) revert InvalidLength(extensions.length, bases.length);
        (, uint256 d,,) = specification(candidate);
        accumulator = new uint256[](d);
        for (uint256 i; i < extensions.length; ++i) {
            accumulator = extensionAdd(candidate, accumulator, extensionMulBase(candidate, extensions[i], bases[i]));
        }
    }

    function batchInverseBase(uint8 candidate, uint256[] memory values)
        public
        pure
        returns (uint256[] memory out)
    {
        (uint256 p,,,) = specification(candidate);
        uint256 n = values.length;
        uint256[] memory prefixes = new uint256[](n + 1);
        prefixes[0] = 1;
        for (uint256 i; i < n; ++i) {
            values[i] = _check(values[i], p);
            if (values[i] == 0) revert DivisionByZero();
            prefixes[i + 1] = mulmod(prefixes[i], values[i], p);
        }
        uint256 suffix = _powBase(prefixes[n], p - 2, p);
        out = new uint256[](n);
        for (uint256 i = n; i != 0; --i) {
            out[i - 1] = mulmod(suffix, prefixes[i - 1], p);
            suffix = mulmod(suffix, values[i - 1], p);
        }
    }

    function batchInverseExtension(uint8 candidate, uint256[][] memory values)
        public
        pure
        returns (uint256[][] memory out)
    {
        (, uint256 d,,) = specification(candidate);
        uint256 n = values.length;
        uint256[][] memory prefixes = new uint256[][](n + 1);
        prefixes[0] = new uint256[](d);
        prefixes[0][0] = 1;
        for (uint256 i; i < n; ++i) prefixes[i + 1] = extensionMul(candidate, prefixes[i], values[i]);
        uint256[] memory suffix = extensionInverse(candidate, prefixes[n]);
        out = new uint256[][](n);
        for (uint256 i = n; i != 0; --i) {
            out[i - 1] = extensionMul(candidate, suffix, prefixes[i - 1]);
            suffix = extensionMul(candidate, suffix, values[i - 1]);
        }
    }

    function polynomialEvaluation(uint8 candidate, uint256[][] memory coefficients, uint256[] memory point)
        public
        pure
        returns (uint256[] memory accumulator)
    {
        (, uint256 d,,) = specification(candidate);
        accumulator = new uint256[](d);
        for (uint256 i = coefficients.length; i != 0; --i) {
            accumulator = extensionAdd(candidate, extensionMul(candidate, accumulator, point), coefficients[i - 1]);
        }
    }

    function fold(uint8 candidate, uint256[] memory low, uint256[] memory high, uint256[] memory beta, uint256 x)
        public
        pure
        returns (uint256[] memory)
    {
        uint256 invTwo = baseInverse(candidate, 2);
        uint256 invTwoX = baseInverse(candidate, baseMul(candidate, 2, x));
        uint256[] memory evenPart = extensionMulBase(candidate, extensionAdd(candidate, low, high), invTwo);
        uint256[] memory oddPart = extensionMul(
            candidate, beta, extensionMulBase(candidate, extensionSub(candidate, low, high), invTwoX)
        );
        return extensionAdd(candidate, evenPart, oddPart);
    }

    /// @notice One deterministic entry point for gas snapshots; n is used by variable-size kernels.
    function kernel(uint8 candidate, uint8 operation, uint256 n) external pure returns (bytes32) {
        uint256 a = deterministicBase(candidate, 1);
        uint256 b = deterministicBase(candidate, 2);
        uint256[] memory ea = deterministicExtension(candidate, 10);
        uint256[] memory eb = deterministicExtension(candidate, 30);
        if (operation == 0) return bytes32(baseAdd(candidate, a, b));
        if (operation == 1) return bytes32(baseSub(candidate, a, b));
        if (operation == 2) return bytes32(baseMul(candidate, a, b));
        if (operation == 3) return bytes32(baseSquare(candidate, a));
        if (operation == 4) return bytes32(baseInverse(candidate, a));
        if (operation == 5) return bytes32(basePower(candidate, a, 65_537));
        if (operation == 6) return keccak256(abi.encode(extensionAdd(candidate, ea, eb)));
        if (operation == 7) return keccak256(abi.encode(extensionSub(candidate, ea, eb)));
        if (operation == 8) return keccak256(abi.encode(extensionMul(candidate, ea, eb)));
        if (operation == 9) return keccak256(abi.encode(extensionSquare(candidate, ea)));
        if (operation == 10) return keccak256(abi.encode(extensionInverse(candidate, ea)));
        if (operation == 11) return keccak256(abi.encode(extensionPower(candidate, ea, 65_537)));
        if (operation == 12) return keccak256(abi.encode(extensionMulBase(candidate, ea, a)));
        if (operation == 13) {
            uint256[][] memory es = new uint256[][](n);
            uint256[] memory bs = new uint256[](n);
            for (uint256 i; i < n; ++i) {
                es[i] = deterministicExtension(candidate, 100 + i * ea.length);
                bs[i] = deterministicBase(candidate, 500 + i);
            }
            return keccak256(abi.encode(dotProduct(candidate, es, bs)));
        }
        if (operation == 14) {
            uint256[] memory values = new uint256[](n);
            for (uint256 i; i < n; ++i) values[i] = deterministicBase(candidate, 700 + i);
            return keccak256(abi.encode(batchInverseBase(candidate, values)));
        }
        if (operation == 15) {
            uint256[][] memory values = new uint256[][](n);
            for (uint256 i; i < n; ++i) values[i] = deterministicExtension(candidate, 900 + i * ea.length);
            return keccak256(abi.encode(batchInverseExtension(candidate, values)));
        }
        if (operation == 16) {
            uint256[][] memory coefficients = new uint256[][](64);
            for (uint256 i; i < 64; ++i) coefficients[i] = deterministicExtension(candidate, 1_200 + i * ea.length);
            return keccak256(abi.encode(polynomialEvaluation(candidate, coefficients, deterministicExtension(candidate, 1_800))));
        }
        if (operation == 17) {
            return keccak256(abi.encode(fold(
                candidate,
                deterministicExtension(candidate, 2_000),
                deterministicExtension(candidate, 2_100),
                deterministicExtension(candidate, 2_200),
                deterministicBase(candidate, 2_300)
            )));
        }
        revert("invalid operation");
    }

    function deterministicBase(uint8 candidate, uint256 index) public pure returns (uint256) {
        (uint256 p,,,) = specification(candidate);
        unchecked {
            uint64 x = SEED + uint64(index + 1) * MIX;
            uint64 mixed = (x ^ (x >> 29) ^ (x << 17)) | 1;
            return uint256(mixed) % p;
        }
    }

    function deterministicExtension(uint8 candidate, uint256 offset) public pure returns (uint256[] memory out) {
        (, uint256 d,,) = specification(candidate);
        out = new uint256[](d);
        for (uint256 i; i < d; ++i) out[i] = deterministicBase(candidate, offset + i);
    }

    function rawEncode(uint8 candidate, uint256[] memory values) external pure returns (bytes memory out) {
        (uint256 p,,,) = specification(candidate);
        uint256 width = candidate == 3 ? 8 : candidate == 5 ? 32 : 4;
        out = new bytes(values.length * width);
        for (uint256 i; i < values.length; ++i) {
            uint256 value = _check(values[i], p);
            for (uint256 j; j < width; ++j) out[i * width + width - 1 - j] = bytes1(uint8(value >> (j * 8)));
        }
    }

    function abiEncode(uint8 candidate, uint256[] memory values) external pure returns (bytes memory) {
        (uint256 p,,,) = specification(candidate);
        for (uint256 i; i < values.length; ++i) _check(values[i], p);
        return abi.encode(values);
    }

    function _mulQm31(uint256[] memory a, uint256[] memory b, uint256 p)
        private
        pure
        returns (uint256[] memory out)
    {
        // (a0+a1*i)+(a2+a3*i)u, i^2=-1, u^2=2+i.
        (uint256 r0, uint256 i0) = _complexMul(a[0], a[1], b[0], b[1], p);
        (uint256 r1, uint256 i1) = _complexMul(a[2], a[3], b[2], b[3], p);
        (uint256 lr, uint256 li) = _complexMul(a[0], a[1], b[2], b[3], p);
        (uint256 rr, uint256 ri) = _complexMul(a[2], a[3], b[0], b[1], p);
        out = new uint256[](4);
        out[0] = addmod(r0, _sub(addmod(r1, r1, p), i1, p), p);
        out[1] = addmod(i0, addmod(r1, addmod(i1, i1, p), p), p);
        out[2] = addmod(lr, rr, p);
        out[3] = addmod(li, ri, p);
    }

    function _complexMul(uint256 ar, uint256 ai, uint256 br, uint256 bi, uint256 p)
        private
        pure
        returns (uint256 real, uint256 imag)
    {
        real = _sub(mulmod(ar, br, p), mulmod(ai, bi, p), p);
        imag = addmod(mulmod(ar, bi, p), mulmod(ai, br, p), p);
    }

    function _powBase(uint256 base, uint256 exponent, uint256 p) private pure returns (uint256 result) {
        result = 1;
        while (exponent != 0) {
            if ((exponent & 1) != 0) result = mulmod(result, base, p);
            exponent >>= 1;
            if (exponent != 0) base = mulmod(base, base, p);
        }
    }

    function _checkExt(uint256[] memory a, uint256 degree, uint256 p) private pure {
        if (a.length != degree) revert InvalidLength(degree, a.length);
        for (uint256 i; i < degree; ++i) _check(a[i], p);
    }

    function _check(uint256 value, uint256 p) private pure returns (uint256) {
        if (value >= p) revert NonCanonical(value, p);
        return value;
    }

    function _sub(uint256 a, uint256 b, uint256 p) private pure returns (uint256) {
        return addmod(a, p - b, p);
    }
}
