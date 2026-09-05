// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;

/// Published RPO-M31 permutation and 16-rate/8-capacity sponge from ePrint 2024/1635.
contract H7RpoM31 {
    uint256 internal constant P = 2147483647;
    error NonCanonicalLane(uint256 lane, uint256 value);
    error EmptyMessage();
    error WrongLength(uint256 expected, uint256 actual);

    function _rc(uint256 key) internal pure returns (uint256 value) {
        assembly {
            switch key
            case 0 { value := 1044571043 }
            case 1 { value := 1317517494 }
            case 2 { value := 249487400 }
            case 3 { value := 1712152640 }
            case 4 { value := 936790368 }
            case 5 { value := 1798470765 }
            case 6 { value := 75987472 }
            case 7 { value := 923861688 }
            case 8 { value := 1748282650 }
            case 9 { value := 1458636302 }
            case 10 { value := 2125307428 }
            case 11 { value := 627234082 }
            case 12 { value := 2094513831 }
            case 13 { value := 392286449 }
            case 14 { value := 1205004590 }
            case 15 { value := 1646616632 }
            case 16 { value := 146852791 }
            case 17 { value := 1084936660 }
            case 18 { value := 1213837505 }
            case 19 { value := 1508526896 }
            case 20 { value := 2088113386 }
            case 21 { value := 438801021 }
            case 22 { value := 620341898 }
            case 23 { value := 1747829738 }
            case 24 { value := 1684110208 }
            case 25 { value := 194902933 }
            case 26 { value := 2034327328 }
            case 27 { value := 1605185266 }
            case 28 { value := 776772368 }
            case 29 { value := 877927050 }
            case 30 { value := 1561964863 }
            case 31 { value := 962611746 }
            case 32 { value := 188953594 }
            case 33 { value := 1836996574 }
            case 34 { value := 856531682 }
            case 35 { value := 749945640 }
            case 36 { value := 751634965 }
            case 37 { value := 187573186 }
            case 38 { value := 1378231507 }
            case 39 { value := 1231694826 }
            case 40 { value := 1943461010 }
            case 41 { value := 2139818866 }
            case 42 { value := 1719290980 }
            case 43 { value := 1471403545 }
            case 44 { value := 304901028 }
            case 45 { value := 1593911519 }
            case 46 { value := 2121163118 }
            case 47 { value := 1042419745 }
            case 48 { value := 430714545 }
            case 49 { value := 1802534386 }
            case 50 { value := 1411432650 }
            case 51 { value := 1975589510 }
            case 52 { value := 251312259 }
            case 53 { value := 546614365 }
            case 54 { value := 861319596 }
            case 55 { value := 433939148 }
            case 56 { value := 1152132416 }
            case 57 { value := 899019929 }
            case 58 { value := 561968644 }
            case 59 { value := 1115375421 }
            case 60 { value := 1681855333 }
            case 61 { value := 136300369 }
            case 62 { value := 384504971 }
            case 63 { value := 467924243 }
            case 64 { value := 1603505046 }
            case 65 { value := 653434233 }
            case 66 { value := 1505420243 }
            case 67 { value := 1284859439 }
            case 68 { value := 236632659 }
            case 69 { value := 976134411 }
            case 70 { value := 494176167 }
            case 71 { value := 679268153 }
            case 72 { value := 874463401 }
            case 73 { value := 564716317 }
            case 74 { value := 1001251281 }
            case 75 { value := 1386232188 }
            case 76 { value := 1228044904 }
            case 77 { value := 1465124466 }
            case 78 { value := 877364151 }
            case 79 { value := 898604478 }
            case 80 { value := 1544100063 }
            case 81 { value := 915337253 }
            case 82 { value := 1950629822 }
            case 83 { value := 1906906106 }
            case 84 { value := 757979146 }
            case 85 { value := 2002835449 }
            case 86 { value := 1214662108 }
            case 87 { value := 1434697933 }
            case 88 { value := 1662108020 }
            case 89 { value := 1936844077 }
            case 90 { value := 542769444 }
            case 91 { value := 204190061 }
            case 92 { value := 1012010535 }
            case 93 { value := 1430350110 }
            case 94 { value := 1398293548 }
            case 95 { value := 886809152 }
            case 96 { value := 790804361 }
            case 97 { value := 367584450 }
            case 98 { value := 1165352909 }
            case 99 { value := 2233920 }
            case 100 { value := 955253877 }
            case 101 { value := 621800289 }
            case 102 { value := 1485836247 }
            case 103 { value := 1656386665 }
            case 104 { value := 1985508482 }
            case 105 { value := 1032665723 }
            case 106 { value := 722925139 }
            case 107 { value := 2020384718 }
            case 108 { value := 1115877501 }
            case 109 { value := 20610385 }
            case 110 { value := 180841501 }
            case 111 { value := 395256351 }
            case 112 { value := 1552537471 }
            case 113 { value := 2110092113 }
            case 114 { value := 1058543121 }
            case 115 { value := 81808142 }
            case 116 { value := 949977919 }
            case 117 { value := 715499236 }
            case 118 { value := 943686204 }
            case 119 { value := 1422121034 }
            case 120 { value := 745980516 }
            case 121 { value := 1913889045 }
            case 122 { value := 1782769571 }
            case 123 { value := 1165159750 }
            case 124 { value := 1914385059 }
            case 125 { value := 1809338068 }
            case 126 { value := 1177671488 }
            case 127 { value := 598847504 }
            case 128 { value := 1285095643 }
            case 129 { value := 1935029517 }
            case 130 { value := 390198635 }
            case 131 { value := 116743474 }
            case 132 { value := 1719389913 }
            case 133 { value := 154253453 }
            case 134 { value := 1239199897 }
            case 135 { value := 592659166 }
            case 136 { value := 139837822 }
            case 137 { value := 953279054 }
            case 138 { value := 918427924 }
            case 139 { value := 1262684657 }
            case 140 { value := 849026136 }
            case 141 { value := 1491875427 }
            case 142 { value := 687067407 }
            case 143 { value := 286614573 }
            case 144 { value := 1938265077 }
            case 145 { value := 764410813 }
            case 146 { value := 966180870 }
            case 147 { value := 841434815 }
            case 148 { value := 535875336 }
            case 149 { value := 292916763 }
            case 150 { value := 1320939155 }
            case 151 { value := 1414337386 }
            case 152 { value := 1928600283 }
            case 153 { value := 293987357 }
            case 154 { value := 1001539892 }
            case 155 { value := 1425158027 }
            case 156 { value := 1127542804 }
            case 157 { value := 1390392454 }
            case 158 { value := 1535562128 }
            case 159 { value := 469264898 }
            case 160 { value := 184249372 }
            case 161 { value := 716590694 }
            case 162 { value := 1228813361 }
            case 163 { value := 1780157382 }
            case 164 { value := 1949536017 }
            case 165 { value := 73510583 }
            case 166 { value := 1934750976 }
            case 167 { value := 2140723487 }
            case 168 { value := 245425607 }
            case 169 { value := 1414863040 }
            case 170 { value := 1951927839 }
            case 171 { value := 196132533 }
            case 172 { value := 416495472 }
            case 173 { value := 1407191283 }
            case 174 { value := 42873232 }
            case 175 { value := 639964293 }
            case 176 { value := 1013217774 }
            case 177 { value := 519899172 }
            case 178 { value := 1334120767 }
            case 179 { value := 1853855471 }
            case 180 { value := 663063513 }
            case 181 { value := 1693625049 }
            case 182 { value := 1567218755 }
            case 183 { value := 2123277830 }
            case 184 { value := 1243733868 }
            case 185 { value := 1783823199 }
            case 186 { value := 769587054 }
            case 187 { value := 48044813 }
            case 188 { value := 324092972 }
            case 189 { value := 1795938818 }
            case 190 { value := 1134458730 }
            case 191 { value := 1328939602 }
            case 192 { value := 1230851342 }
            case 193 { value := 267767087 }
            case 194 { value := 522693111 }
            case 195 { value := 57086192 }
            case 196 { value := 107676261 }
            case 197 { value := 442564081 }
            case 198 { value := 716638036 }
            case 199 { value := 1755526725 }
            case 200 { value := 2125501390 }
            case 201 { value := 271091103 }
            case 202 { value := 671689141 }
            case 203 { value := 956120501 }
            case 204 { value := 660403697 }
            case 205 { value := 1300430489 }
            case 206 { value := 53310533 }
            case 207 { value := 535970544 }
            case 208 { value := 2068115302 }
            case 209 { value := 2133603187 }
            case 210 { value := 62017252 }
            case 211 { value := 1539180651 }
            case 212 { value := 1160889845 }
            case 213 { value := 141875767 }
            case 214 { value := 1652116664 }
            case 215 { value := 679606033 }
            case 216 { value := 359733143 }
            case 217 { value := 212711718 }
            case 218 { value := 588071278 }
            case 219 { value := 1766076774 }
            case 220 { value := 1262041434 }
            case 221 { value := 1727953856 }
            case 222 { value := 567579954 }
            case 223 { value := 1441364608 }
            case 224 { value := 439540796 }
            case 225 { value := 1326545544 }
            case 226 { value := 67193305 }
            case 227 { value := 534841932 }
            case 228 { value := 737345739 }
            case 229 { value := 694226368 }
            case 230 { value := 973220856 }
            case 231 { value := 2017274086 }
            case 232 { value := 750471678 }
            case 233 { value := 138369658 }
            case 234 { value := 1904221552 }
            case 235 { value := 720786848 }
            case 236 { value := 951516589 }
            case 237 { value := 921310073 }
            case 238 { value := 389800747 }
            case 239 { value := 952921749 }
            case 240 { value := 282292561 }
            case 241 { value := 1208095394 }
            case 242 { value := 1247331148 }
            case 243 { value := 1245102222 }
            case 244 { value := 859543152 }
            case 245 { value := 1462120451 }
            case 246 { value := 799775307 }
            case 247 { value := 968355629 }
            case 248 { value := 1612145162 }
            case 249 { value := 1749315342 }
            case 250 { value := 293380594 }
            case 251 { value := 145527966 }
            case 252 { value := 1419068342 }
            case 253 { value := 2031957997 }
            case 254 { value := 888083721 }
            case 255 { value := 1382614377 }
            case 256 { value := 916920974 }
            case 257 { value := 1296916153 }
            case 258 { value := 2011230971 }
            case 259 { value := 697722432 }
            case 260 { value := 386062754 }
            case 261 { value := 1900046699 }
            case 262 { value := 1585545260 }
            case 263 { value := 708361486 }
            case 264 { value := 178122392 }
            case 265 { value := 1311864996 }
            case 266 { value := 1352288535 }
            case 267 { value := 1283109748 }
            case 268 { value := 1379051687 }
            case 269 { value := 2090838053 }
            case 270 { value := 628779636 }
            case 271 { value := 971729603 }
            case 272 { value := 1004705254 }
            case 273 { value := 2047415761 }
            case 274 { value := 714775169 }
            case 275 { value := 1188845145 }
            case 276 { value := 1401204922 }
            case 277 { value := 674825691 }
            case 278 { value := 416212167 }
            case 279 { value := 1843107919 }
            case 280 { value := 596301862 }
            case 281 { value := 1915939922 }
            case 282 { value := 1618162956 }
            case 283 { value := 1450092627 }
            case 284 { value := 107386172 }
            case 285 { value := 506445401 }
            case 286 { value := 1921830619 }
            case 287 { value := 2086845529 }
            case 288 { value := 724994202 }
            case 289 { value := 198168589 }
            case 290 { value := 169256380 }
            case 291 { value := 920601077 }
            case 292 { value := 342498620 }
            case 293 { value := 1886429554 }
            case 294 { value := 1189428740 }
            case 295 { value := 392408933 }
            case 296 { value := 1592337489 }
            case 297 { value := 1746180144 }
            case 298 { value := 1460751591 }
            case 299 { value := 444800367 }
            case 300 { value := 1210701826 }
            case 301 { value := 638380860 }
            case 302 { value := 295249870 }
            case 303 { value := 1546224051 }
            case 304 { value := 2066701216 }
            case 305 { value := 61687557 }
            case 306 { value := 2032029179 }
            case 307 { value := 464348718 }
            case 308 { value := 445515901 }
            case 309 { value := 1448021165 }
            case 310 { value := 312825948 }
            case 311 { value := 2073211063 }
            case 312 { value := 972419809 }
            case 313 { value := 167003533 }
            case 314 { value := 73895973 }
            case 315 { value := 1814963636 }
            case 316 { value := 848867698 }
            case 317 { value := 360586058 }
            case 318 { value := 1902061290 }
            case 319 { value := 1181548648 }
            case 320 { value := 1091022720 }
            case 321 { value := 1505503585 }
            case 322 { value := 2073616608 }
            case 323 { value := 1076682089 }
            case 324 { value := 1964736989 }
            case 325 { value := 768226089 }
            case 326 { value := 269778254 }
            case 327 { value := 2045559121 }
            case 328 { value := 2025368936 }
            case 329 { value := 1061136486 }
            case 330 { value := 597010591 }
            case 331 { value := 1642802834 }
            case 332 { value := 1214396177 }
            case 333 { value := 989902115 }
            case 334 { value := 155452933 }
            case 335 { value := 12002769 }
            case 336 { value := 95012232 }
            case 337 { value := 1536513128 }
            case 338 { value := 159034207 }
            case 339 { value := 856068314 }
            case 340 { value := 1739694228 }
            case 341 { value := 1349483389 }
            case 342 { value := 1055805398 }
            case 343 { value := 1000132196 }
            case 344 { value := 1164649946 }
            case 345 { value := 1162020698 }
            case 346 { value := 2054206931 }
            case 347 { value := 1025425448 }
            case 348 { value := 1748283578 }
            case 349 { value := 1657857317 }
            case 350 { value := 303425122 }
            case 351 { value := 688113491 }
            case 352 { value := 1562492500 }
            case 353 { value := 1148182238 }
            case 354 { value := 1650552995 }
            case 355 { value := 1591611216 }
            case 356 { value := 1676998327 }
            case 357 { value := 1600694694 }
            case 358 { value := 549083144 }
            case 359 { value := 376686657 }
            default { revert(0, 0) }
        }
    }
    function _mdsFirstRow(uint256 key) internal pure returns (uint256 value) {
        assembly {
            switch key
            case 0 { value := 185870542 }
            case 1 { value := 2144994796 }
            case 2 { value := 1696461115 }
            case 3 { value := 215190769 }
            case 4 { value := 930115258 }
            case 5 { value := 766567118 }
            case 6 { value := 2003379079 }
            case 7 { value := 1770558586 }
            case 8 { value := 1779722644 }
            case 9 { value := 434368282 }
            case 10 { value := 289154277 }
            case 11 { value := 1979813463 }
            case 12 { value := 1436360233 }
            case 13 { value := 1342944808 }
            case 14 { value := 63026005 }
            case 15 { value := 903393155 }
            case 16 { value := 1512525948 }
            case 17 { value := 105409451 }
            case 18 { value := 1072974295 }
            case 19 { value := 979558870 }
            case 20 { value := 436105640 }
            case 21 { value := 2126764826 }
            case 22 { value := 1981550821 }
            case 23 { value := 636196459 }
            case 24 { value := 645360517 }
            case 25 { value := 412540024 }
            case 26 { value := 1649351985 }
            case 27 { value := 1485803845 }
            case 28 { value := 53244687 }
            case 29 { value := 719457988 }
            case 30 { value := 270924307 }
            case 31 { value := 82564914 }
            default { revert(0, 0) }
        }
    }

    function _pow(uint256 x, uint256 exponent) private pure returns (uint256 result) {
        result = 1;
        while (exponent != 0) {
            if ((exponent & 1) != 0) result = mulmod(result, x, P);
            x = mulmod(x, x, P);
            exponent >>= 1;
        }
    }

    function _mds(uint256[] memory state) private pure returns (uint256[] memory output) {
        output = new uint256[](24);
        for (uint256 row; row < 24; ++row) {
            uint256 accumulator;
            for (uint256 column; column < 24; ++column) accumulator = addmod(accumulator, mulmod(_mdsFirstRow((column + 32 - row) % 32), state[column], P), P);
            output[row] = accumulator;
        }
    }

    function _permutation(uint256[] memory state) internal pure returns (uint256[] memory) {
        if (state.length != 24) revert WrongLength(24, state.length);
        for (uint256 i; i < 24; ++i) if (state[i] >= P) revert NonCanonicalLane(i, state[i]);
        for (uint256 round; round < 7; ++round) {
            state = _mds(state);
            for (uint256 i; i < 24; ++i) state[i] = _pow(addmod(state[i], _rc(2 * round * 24 + i), P), 5);
            state = _mds(state);
            for (uint256 i; i < 24; ++i) state[i] = _pow(addmod(state[i], _rc((2 * round + 1) * 24 + i), P), 1717986917);
        }
        state = _mds(state);
        for (uint256 i; i < 24; ++i) state[i] = addmod(state[i], _rc(14 * 24 + i), P);
        return state;
    }

    function permutation(uint256[] calldata input) external pure returns (uint256[] memory) { return _permutation(input); }

    function sponge(uint256[] memory message) public pure returns (uint256[] memory output) {
        if (message.length == 0) revert EmptyMessage();
        uint256 finalLength = ((message.length - 1) % 16) + 1;
        uint256[] memory state = new uint256[](24);
        state[16] = 16 - finalLength;
        for (uint256 offset; offset < message.length; offset += 16) {
            uint256 end = offset + 16 < message.length ? offset + 16 : message.length;
            for (uint256 i = offset; i < end; ++i) {
                if (message[i] >= P) revert NonCanonicalLane(i, message[i]);
                state[i - offset] = addmod(state[i - offset], message[i], P);
            }
            state = _permutation(state);
        }
        output = new uint256[](16);
        for (uint256 i; i < 16; ++i) output[i] = state[i];
    }

    function _application(uint256 role, uint256 level, uint256[] memory payload) private pure returns (uint256[] memory) {
        uint256[] memory message = new uint256[](payload.length + 4);
        message[0] = role; message[1] = 1; message[2] = payload.length; message[3] = level;
        for (uint256 i; i < payload.length; ++i) message[i + 4] = payload[i];
        return sponge(message);
    }
    function note(uint256[] calldata payload) external pure returns (uint256[] memory) { return _application(2, 0, payload); }
    function nullifier(uint256[] calldata payload) external pure returns (uint256[] memory) { return _application(3, 0, payload); }
    function node(uint256 level, uint256[] calldata left, uint256[] calldata right) external pure returns (uint256[] memory) {
        if (left.length != 16) revert WrongLength(16, left.length);
        if (right.length != 16) revert WrongLength(16, right.length);
        uint256[] memory payload = new uint256[](32);
        for (uint256 i; i < 16; ++i) { payload[i] = left[i]; payload[16 + i] = right[i]; }
        return _application(4, level, payload);
    }
}
