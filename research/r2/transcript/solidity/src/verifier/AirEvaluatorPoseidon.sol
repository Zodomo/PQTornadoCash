// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

import {BabyBearExt4Packed as Ext} from "../libraries/BabyBearExt4Packed.sol";

/// The constraint order is exactly pqtc_poseidon_air::WithdrawalAir::eval.
library AirEvaluatorPoseidon {
    uint256 internal constant WIDTH = 190;
    uint256 internal constant CONSTRAINTS = 1_186;
    uint256 private constant POSEIDON_WIDTH = 16;
    uint256 private constant POSEIDON_COLUMNS = 157;
    uint256 private constant OUTPUT = 141;
    uint256 private constant IS_NOTE = 157;
    uint256 private constant IS_NULLIFIER = 158;
    uint256 private constant IS_MERKLE = 159;
    uint256 private constant IS_PAYOUT = 160;
    uint256 private constant IS_PADDING = 161;
    uint256 private constant STEP_BITS = 162;
    uint256 private constant LEVEL_BITS = 166;
    uint256 private constant IS_LAST_LEVEL = 171;
    uint256 private constant PATH_BIT = 172;
    uint256 private constant INDEX = 173;
    uint256 private constant WORK = 174;

    uint256 private constant EXTERNAL_0A = 0x69cbb6af46ad93f960a00f4e6b1297cd23189afe732e7bef72c246de2c941900;
    uint256 private constant EXTERNAL_0B = 0x0557eede1580496f3a3ea77b54f3f2710f49b02947872fe1221e2e361ab7202e;
    uint256 private constant EXTERNAL_1A = 0x487779a63851c9d838dc17c0209f8849268dcee8350c48da5b9ad32e0523272b;
    uint256 private constant EXTERNAL_1B = 0x3f89055b01e894b213ddedde1b2ef3347507d8b46ceeb94e52eb6ba250642905;
    uint256 private constant EXTERNAL_2A = 0x05453f3f06349efc6922787c04bfff9c768c714a3e9ff21a15737c9c2229c807;
    uint256 private constant EXTERNAL_2B = 0x0d47f88c097e0ecc27eadba02d7d29e43502aaa00f475fd729fbda49018afffd;
    uint256 private constant EXTERNAL_3A = 0x0315b6186d4497d11b171d9e52861abd2e5d05013ec8646c6e5f250a148ae8e6;
    uint256 private constant EXTERNAL_3B = 0x17f5fa4a3e66d2840051aa3b483f79132cfe5f15023427ca2cc783151e36ea47;
    uint256 private constant EXTERNAL_4A = 0x7290a80d6f7e5329598ec8a876a859a06559e868657b83af13271d3f1f876063;
    uint256 private constant EXTERNAL_4B = 0x0aeeae37706e9ca646400cee72a05c262c589c9e20bd37a76a2d3d1020523767;
    uint256 private constant EXTERNAL_5A = 0x5b8fe9c42aa501d61e01ac3e1448bc545ce5ad1c4918a14d2c46a83f4fcf6876;
    uint256 private constant EXTERNAL_5B = 0x61d8d5c86ddf4ff911fda4d302933a8f170eaf815a9c314f49a1259035ec52a1;
    uint256 private constant EXTERNAL_6A = 0x58eb16115e481e65367125c90eba33ba1fc28ded066399ad0cbec0ea75fd1af0;
    uint256 private constant EXTERNAL_6B = 0x50f5bf4e643d5f416f4fe7185b3cbbde1e3afb3e296fb02745e1547b4a8db2ab;
    uint256 private constant EXTERNAL_7A = 0x59986d1930bcdfa31db639321d7c282453b336810673b747038a98a32c5bce60;
    uint256 private constant EXTERNAL_7B = 0x351979cd5008fb73547bca78711af4813f93bf64644d987b3c8bcd87608758b8;
    uint256 private constant INTERNAL_A = 0x5a8053c0693be6393858867d19334f6b128f0fd84e2b1ccb61210ce03c318939;
    uint256 private constant INTERNAL_B = 0x0b5b2f222edb11d5213effdf0cac4606241af16d000000000000000000000000;

    struct Fold {
        uint256 value;
        uint256 alpha;
    }

    uint8 internal constant SEGMENTS = 7;

    error InvalidInputWidth();
    error InvalidSegmentRange();

    function evaluate(
        uint256[] memory local,
        uint256[] memory next,
        uint256[] memory publicValues,
        uint256 isFirst,
        uint256 isLast,
        uint256 isTransition,
        uint256 alpha
    ) internal pure returns (uint256) {
        return evaluateRange(local, next, publicValues, isFirst, isLast, isTransition, alpha, 0, 0, SEGMENTS);
    }

    function evaluateRange(
        uint256[] memory local,
        uint256[] memory next,
        uint256[] memory publicValues,
        uint256 isFirst,
        uint256 isLast,
        uint256 isTransition,
        uint256 alpha,
        uint256 accumulator,
        uint8 start,
        uint8 end
    ) internal pure returns (uint256) {
        if (local.length != WIDTH || next.length != WIDTH || publicValues.length != 64) {
            revert InvalidInputWidth();
        }
        if (start > end || end > SEGMENTS) revert InvalidSegmentRange();
        Fold memory fold = Fold(accumulator, alpha);
        for (uint8 segment = start; segment < end; ++segment) {
            if (segment == 0) {
                _poseidon(fold, local);
            } else if (segment == 1) {
                _shape(fold, local, isFirst, isLast);
                _initial(fold, local);
            } else if (segment == 2) {
                _bindInputs(fold, local, publicValues);
                _metadata(fold, local, next, isTransition);
                _chainingPrivate(fold, local, next, publicValues, isTransition);
            } else if (segment == 3) {
                _chainingMerkle(fold, local, next, isTransition);
            } else if (segment == 4) {
                _workPrivate(fold, local, next, isTransition);
            } else if (segment == 5) {
                _workMerkle(fold, local, next, isTransition);
            } else {
                _outputs(fold, local, publicValues);
            }
        }
        return fold.value;
    }

    function _poseidon(Fold memory fold, uint256[] memory row) private pure {
        uint256[16] memory state;
        for (uint256 i; i < 16; ++i) {
            state[i] = row[i];
        }
        _externalLinear(state);
        for (uint256 round; round < 4; ++round) {
            (uint256 first, uint256 second) = _externalConstants(round);
            for (uint256 i; i < 16; ++i) {
                uint256 rc = i < 8 ? uint32(first >> (224 - 32 * i)) : uint32(second >> (224 - 32 * (i - 8)));
                state[i] = _pow7(Ext.add(state[i], Ext.fromBase(rc)));
            }
            _externalLinear(state);
            uint256 post = 16 + round * 16;
            for (uint256 i; i < 16; ++i) {
                _push(fold, Ext.sub(state[i], row[post + i]));
                state[i] = row[post + i];
            }
        }
        for (uint256 round; round < 13; ++round) {
            uint256 x = Ext.add(state[0], Ext.fromBase(_internalConstant(round)));
            x = _pow7(x);
            _push(fold, Ext.sub(x, row[80 + round]));
            state[0] = row[80 + round];
            _internalLinear(state);
        }
        for (uint256 round; round < 4; ++round) {
            (uint256 first, uint256 second) = _externalConstants(round + 4);
            for (uint256 i; i < 16; ++i) {
                uint256 rc = i < 8 ? uint32(first >> (224 - 32 * i)) : uint32(second >> (224 - 32 * (i - 8)));
                state[i] = _pow7(Ext.add(state[i], Ext.fromBase(rc)));
            }
            _externalLinear(state);
            uint256 post = 93 + round * 16;
            for (uint256 i; i < 16; ++i) {
                _push(fold, Ext.sub(state[i], row[post + i]));
                state[i] = row[post + i];
            }
        }
    }

    function _shape(Fold memory fold, uint256[] memory local, uint256 isFirst, uint256 isLast) private pure {
        uint256[7] memory selectors = [IS_NOTE, IS_NULLIFIER, IS_MERKLE, IS_PAYOUT, IS_PADDING, IS_LAST_LEVEL, PATH_BIT];
        for (uint256 i; i < selectors.length; ++i) {
            _push(fold, _bool(local[selectors[i]]));
        }
        for (uint256 i; i < 4; ++i) {
            _push(fold, _bool(local[STEP_BITS + i]));
        }
        for (uint256 i; i < 5; ++i) {
            _push(fold, _bool(local[LEVEL_BITS + i]));
        }
        uint256 sum = Ext.add(Ext.add(local[IS_NOTE], local[IS_NULLIFIER]), Ext.add(local[IS_MERKLE], local[IS_PAYOUT]));
        _push(fold, Ext.sub(Ext.add(sum, local[IS_PADDING]), Ext.fromBase(1)));
        _push(fold, Ext.sub(local[IS_LAST_LEVEL], Ext.mul(local[IS_MERKLE], _levelEq(local, 19))));
        uint256 notMerkle = Ext.sub(Ext.fromBase(1), local[IS_MERKLE]);
        _zero(fold, notMerkle, local[PATH_BIT]);
        _zero(fold, notMerkle, local[INDEX]);
        _eq(fold, isFirst, local[IS_NULLIFIER], Ext.fromBase(1));
        _zero(fold, isFirst, _stepValue(local));
        _zero(fold, isFirst, _levelValue(local));
        for (uint256 i = 8; i < 16; ++i) {
            _zero(fold, isFirst, local[WORK + i]);
        }
        _zero(fold, notMerkle, _levelValue(local));
        _zero(fold, local[IS_PADDING], _stepValue(local));
        _eq(fold, isLast, local[IS_PADDING], Ext.fromBase(1));
    }

    function _initial(Fold memory fold, uint256[] memory local) private pure {
        _initialRow(fold, local, IS_NULLIFIER, 0x12, 96, 24, false);
        _initialRow(fold, local, IS_NOTE, 0x11, 128, 32, false);
        _initialRow(fold, local, IS_MERKLE, 0x20, 128, 32, true);
    }

    function _bindInputs(Fold memory fold, uint256[] memory local, uint256[] memory publicValues) private pure {
        for (uint256 j; j < 4; ++j) {
            _eq(fold, Ext.mul(local[IS_NULLIFIER], _stepEq(local, 0)), local[j], publicValues[j]);
            _eq(fold, Ext.mul(local[IS_NOTE], _stepEq(local, 0)), local[j], publicValues[j]);
            uint256 c = Ext.mul(Ext.mul(local[IS_MERKLE], _stepEq(local, 0)), Ext.sub(Ext.fromBase(1), local[PATH_BIT]));
            _eq(fold, c, local[j], local[WORK + j]);
        }
        for (uint256 step; step < 4; ++step) {
            uint256 c = Ext.mul(local[IS_PAYOUT], _stepEq(local, step));
            for (uint256 j; j < 4; ++j) {
                _eq(fold, c, local[j], publicValues[48 + step * 4 + j]);
            }
            for (uint256 j = 4; j < 16; ++j) {
                _zero(fold, c, local[j]);
            }
        }
        uint256 empty = Ext.add(local[IS_PAYOUT], local[IS_PADDING]);
        for (uint256 j; j < 16; ++j) {
            _zero(fold, local[IS_PADDING], local[j]);
            _zero(fold, empty, local[WORK + j]);
        }
    }

    function _metadata(Fold memory fold, uint256[] memory l, uint256[] memory n, uint256 tr) private pure {
        uint256 one = Ext.fromBase(1);
        uint256 s = _stepValue(l);
        uint256 ns = _stepValue(n);
        uint256 lev = _levelValue(l);
        uint256 nl = _levelValue(n);

        uint256 c = Ext.mul(Ext.mul(tr, l[IS_NULLIFIER]), Ext.sub(one, _stepEq(l, 8)));
        _eq(fold, c, n[IS_NULLIFIER], one);
        _eq(fold, c, ns, Ext.add(s, one));
        c = Ext.mul(Ext.mul(tr, l[IS_NULLIFIER]), _stepEq(l, 8));
        _eq(fold, c, n[IS_NOTE], one);
        _zero(fold, c, ns);

        c = Ext.mul(Ext.mul(tr, l[IS_NOTE]), Ext.sub(one, _stepEq(l, 10)));
        _eq(fold, c, n[IS_NOTE], one);
        _eq(fold, c, ns, Ext.add(s, one));
        c = Ext.mul(Ext.mul(tr, l[IS_NOTE]), _stepEq(l, 10));
        _eq(fold, c, n[IS_MERKLE], one);
        _zero(fold, c, ns);
        _zero(fold, c, nl);

        c = Ext.mul(Ext.mul(tr, l[IS_MERKLE]), Ext.sub(one, _stepEq(l, 10)));
        _eq(fold, c, n[IS_MERKLE], one);
        _eq(fold, c, ns, Ext.add(s, one));
        _eq(fold, c, nl, lev);
        _eq(fold, c, n[PATH_BIT], l[PATH_BIT]);
        _eq(fold, c, n[INDEX], l[INDEX]);
        c = Ext.mul(Ext.mul(Ext.mul(tr, l[IS_MERKLE]), _stepEq(l, 10)), Ext.sub(one, l[IS_LAST_LEVEL]));
        _eq(fold, c, n[IS_MERKLE], one);
        _zero(fold, c, ns);
        _eq(fold, c, nl, Ext.add(lev, one));
        _eq(fold, c, l[INDEX], Ext.add(l[PATH_BIT], Ext.mulBase(n[INDEX], 2)));
        c = Ext.mul(Ext.mul(Ext.mul(tr, l[IS_MERKLE]), _stepEq(l, 10)), l[IS_LAST_LEVEL]);
        _eq(fold, c, n[IS_PAYOUT], one);
        _zero(fold, c, ns);
        _eq(fold, c, l[INDEX], l[PATH_BIT]);

        c = Ext.mul(Ext.mul(tr, l[IS_PAYOUT]), Ext.sub(one, _stepEq(l, 3)));
        _eq(fold, c, n[IS_PAYOUT], one);
        _eq(fold, c, ns, Ext.add(_stepValue(l), one));
        c = Ext.mul(Ext.mul(tr, l[IS_PAYOUT]), _stepEq(l, 3));
        _eq(fold, c, n[IS_PADDING], one);
        _zero(fold, c, ns);
        c = Ext.mul(tr, l[IS_PADDING]);
        _eq(fold, c, n[IS_PADDING], one);
        _zero(fold, c, ns);
    }

    function _chainingPrivate(
        Fold memory fold,
        uint256[] memory l,
        uint256[] memory n,
        uint256[] memory publicValues,
        uint256 tr
    ) private pure {
        for (uint256 step = 1; step < 6; ++step) {
            uint256 c = Ext.mul(Ext.mul(tr, n[IS_NULLIFIER]), _stepEq(n, step));
            for (uint256 j; j < 4; ++j) {
                uint256 payload = step < 4 ? publicValues[step * 4 + j] : n[WORK + (step - 4) * 4 + j];
                _eq(fold, c, n[j], Ext.add(l[OUTPUT + j], payload));
            }
            for (uint256 j = 4; j < 16; ++j) {
                _eq(fold, c, n[j], l[OUTPUT + j]);
            }
        }
        for (uint256 step = 6; step < 9; ++step) {
            _squeeze(fold, l, n, Ext.mul(Ext.mul(tr, n[IS_NULLIFIER]), _stepEq(n, step)));
        }
        for (uint256 step = 1; step < 8; ++step) {
            // Steps 6 and 7 leave exactly four rate deltas free for the eight
            // ephemeral trapdoor limbs; the twelve capacity lanes remain chained.
            uint256 c = Ext.mul(Ext.mul(tr, n[IS_NOTE]), _stepEq(n, step));
            if (step < 6) {
                for (uint256 j; j < 4; ++j) {
                    uint256 payload = step < 4 ? publicValues[step * 4 + j] : n[WORK + (step - 4) * 4 + j];
                    _eq(fold, c, n[j], Ext.add(l[OUTPUT + j], payload));
                }
            }
            for (uint256 j = 4; j < 16; ++j) {
                _eq(fold, c, n[j], l[OUTPUT + j]);
            }
        }
        for (uint256 step = 8; step < 11; ++step) {
            _squeeze(fold, l, n, Ext.mul(Ext.mul(tr, n[IS_NOTE]), _stepEq(n, step)));
        }
    }

    function _chainingMerkle(Fold memory fold, uint256[] memory l, uint256[] memory n, uint256 tr) private pure {
        for (uint256 step = 1; step < 8; ++step) {
            uint256 c = Ext.mul(Ext.mul(tr, n[IS_MERKLE]), _stepEq(n, step));
            for (uint256 j; j < 4; ++j) {
                uint256 k = step * 4 + j;
                uint256 side = k < 16 ? Ext.sub(Ext.fromBase(1), n[PATH_BIT]) : n[PATH_BIT];
                _eq(fold, Ext.mul(c, side), n[j], Ext.add(l[OUTPUT + j], n[WORK + (k % 16)]));
            }
            for (uint256 j = 4; j < 16; ++j) {
                _eq(fold, c, n[j], l[OUTPUT + j]);
            }
        }
        for (uint256 step = 8; step < 11; ++step) {
            _squeeze(fold, l, n, Ext.mul(Ext.mul(tr, n[IS_MERKLE]), _stepEq(n, step)));
        }
    }

    function _workPrivate(Fold memory fold, uint256[] memory l, uint256[] memory n, uint256 tr) private pure {
        for (uint256 i; i < 16; ++i) {
            _eq(fold, Ext.mul(tr, l[IS_NULLIFIER]), n[WORK + i], l[WORK + i]);
        }
        for (uint256 step; step < 11; ++step) {
            _workTransition(fold, l, n, Ext.mul(Ext.mul(tr, l[IS_NOTE]), _stepEq(l, step)), 7, step);
        }
    }

    function _workMerkle(Fold memory fold, uint256[] memory l, uint256[] memory n, uint256 tr) private pure {
        for (uint256 step; step < 10; ++step) {
            _workTransition(fold, l, n, Ext.mul(Ext.mul(tr, l[IS_MERKLE]), _stepEq(l, step)), 7, step);
        }
        uint256 c =
            Ext.mul(Ext.mul(Ext.mul(tr, l[IS_MERKLE]), _stepEq(l, 10)), Ext.sub(Ext.fromBase(1), l[IS_LAST_LEVEL]));
        _workTransition(fold, l, n, c, 7, 10);
    }

    function _outputs(Fold memory fold, uint256[] memory l, uint256[] memory publicValues) private pure {
        for (uint256 chunk; chunk < 4; ++chunk) {
            uint256 nc = Ext.mul(l[IS_NULLIFIER], _stepEq(l, 5 + chunk));
            uint256 rc = Ext.mul(Ext.mul(l[IS_MERKLE], l[IS_LAST_LEVEL]), _stepEq(l, 7 + chunk));
            for (uint256 j; j < 4; ++j) {
                _eq(fold, nc, l[OUTPUT + j], publicValues[32 + chunk * 4 + j]);
                _eq(fold, rc, l[OUTPUT + j], publicValues[16 + chunk * 4 + j]);
            }
        }
    }

    function _initialRow(
        Fold memory fold,
        uint256[] memory row,
        uint256 selector,
        uint256 tag,
        uint256 byteLength,
        uint256 elementCount,
        bool level
    ) private pure {
        uint256 c = Ext.mul(row[selector], _stepEq(row, 0));
        _eq(fold, c, row[4], Ext.fromBase(1));
        _eq(fold, c, row[5], Ext.fromBase(tag));
        _eq(fold, c, row[6], Ext.fromBase(byteLength));
        _eq(fold, c, row[7], Ext.fromBase(elementCount));
        if (level) _eq(fold, c, row[8], _levelValue(row));
        else _zero(fold, c, row[8]);
        for (uint256 i = 9; i < 16; ++i) {
            _zero(fold, c, row[i]);
        }
    }

    function _squeeze(Fold memory fold, uint256[] memory l, uint256[] memory n, uint256 c) private pure {
        for (uint256 j; j < 16; ++j) {
            _eq(fold, c, n[j], l[OUTPUT + j]);
        }
    }

    function _workTransition(
        Fold memory fold,
        uint256[] memory l,
        uint256[] memory n,
        uint256 c,
        uint256 first,
        uint256 step
    ) private pure {
        bool writes = step >= first && step < first + 4;
        uint256 chunk = writes ? step - first : type(uint256).max;
        for (uint256 i; i < 16; ++i) {
            uint256 expected = writes && chunk == i / 4 ? l[OUTPUT + (i % 4)] : l[WORK + i];
            _eq(fold, c, n[WORK + i], expected);
        }
    }

    function _stepEq(uint256[] memory row, uint256 value) private pure returns (uint256) {
        return _bitsEq(row, STEP_BITS, 4, value);
    }

    function _levelEq(uint256[] memory row, uint256 value) private pure returns (uint256) {
        return _bitsEq(row, LEVEL_BITS, 5, value);
    }

    function _bitsEq(uint256[] memory row, uint256 start, uint256 count, uint256 value)
        private
        pure
        returns (uint256 p)
    {
        p = Ext.fromBase(1);
        for (uint256 i; i < count; ++i) {
            uint256 factor = ((value >> i) & 1) == 1 ? row[start + i] : Ext.sub(Ext.fromBase(1), row[start + i]);
            p = Ext.mul(p, factor);
        }
    }

    function _stepValue(uint256[] memory row) private pure returns (uint256 value) {
        for (uint256 i; i < 4; ++i) {
            value = Ext.add(value, Ext.mulBase(row[STEP_BITS + i], uint256(1) << i));
        }
    }

    function _levelValue(uint256[] memory row) private pure returns (uint256 value) {
        for (uint256 i; i < 5; ++i) {
            value = Ext.add(value, Ext.mulBase(row[LEVEL_BITS + i], uint256(1) << i));
        }
    }

    function _externalLinear(uint256[16] memory state) private pure {
        for (uint256 group; group < 4; ++group) {
            uint256 i = group * 4;
            uint256 x0 = state[i];
            uint256 x1 = state[i + 1];
            uint256 x2 = state[i + 2];
            uint256 x3 = state[i + 3];
            uint256 t01 = Ext.add(x0, x1);
            uint256 t23 = Ext.add(x2, x3);
            uint256 total = Ext.add(t01, t23);
            uint256 with1 = Ext.add(total, x1);
            uint256 with3 = Ext.add(total, x3);
            state[i + 3] = Ext.add(with3, Ext.mulBase(x0, 2));
            state[i + 1] = Ext.add(with1, Ext.mulBase(x2, 2));
            state[i] = Ext.add(with1, t01);
            state[i + 2] = Ext.add(with3, t23);
        }
        uint256[4] memory sums;
        for (uint256 lane; lane < 4; ++lane) {
            sums[lane] = Ext.add(Ext.add(state[lane], state[lane + 4]), Ext.add(state[lane + 8], state[lane + 12]));
        }
        for (uint256 i; i < 16; ++i) {
            state[i] = Ext.add(state[i], sums[i % 4]);
        }
    }

    function _internalLinear(uint256[16] memory state) private pure {
        uint256 partSum;
        for (uint256 i = 1; i < 16; ++i) {
            partSum = Ext.add(partSum, state[i]);
        }
        uint256 sum = Ext.add(partSum, state[0]);
        state[0] = Ext.sub(partSum, state[0]);
        uint256[15] memory diagonal = [
            uint256(1),
            2,
            1_006_632_961,
            3,
            4,
            1_006_632_960,
            2_013_265_918,
            2_013_265_917,
            2_005_401_601,
            1_509_949_441,
            1_761_607_681,
            2_013_265_906,
            7_864_320,
            125_829_120,
            15
        ];
        for (uint256 i = 1; i < 16; ++i) {
            state[i] = Ext.add(sum, Ext.mulBase(state[i], diagonal[i - 1]));
        }
    }

    function _pow7(uint256 x) private pure returns (uint256) {
        uint256 square = Ext.mul(x, x);
        return Ext.mul(Ext.mul(Ext.mul(square, square), square), x);
    }

    function _internalConstant(uint256 round) private pure returns (uint256) {
        return round < 8 ? uint32(INTERNAL_A >> (224 - 32 * round)) : uint32(INTERNAL_B >> (224 - 32 * (round - 8)));
    }

    function _externalConstants(uint256 round) private pure returns (uint256 first, uint256 second) {
        if (round == 0) return (EXTERNAL_0A, EXTERNAL_0B);
        if (round == 1) return (EXTERNAL_1A, EXTERNAL_1B);
        if (round == 2) return (EXTERNAL_2A, EXTERNAL_2B);
        if (round == 3) return (EXTERNAL_3A, EXTERNAL_3B);
        if (round == 4) return (EXTERNAL_4A, EXTERNAL_4B);
        if (round == 5) return (EXTERNAL_5A, EXTERNAL_5B);
        if (round == 6) return (EXTERNAL_6A, EXTERNAL_6B);
        return (EXTERNAL_7A, EXTERNAL_7B);
    }

    function _push(Fold memory fold, uint256 constraint) private pure {
        fold.value = Ext.add(Ext.mul(fold.value, fold.alpha), constraint);
    }

    function _eq(Fold memory fold, uint256 condition, uint256 a, uint256 b) private pure {
        _push(fold, Ext.mul(condition, Ext.sub(a, b)));
    }

    function _zero(Fold memory fold, uint256 condition, uint256 value) private pure {
        _push(fold, Ext.mul(condition, value));
    }

    function _bool(uint256 value) private pure returns (uint256) {
        return Ext.mul(value, Ext.sub(value, Ext.fromBase(1)));
    }
}
