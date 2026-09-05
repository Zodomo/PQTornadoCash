// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;
import "./Poseidon2Kernel.sol";

library P2C24 {
    function rc(uint256 key) internal pure returns (uint256 value) {
        assembly {
            switch key
            case 0 { value := 262278199 }
            case 1 { value := 127253399 }
            case 2 { value := 314968988 }
            case 3 { value := 246143118 }
            case 4 { value := 157582794 }
            case 5 { value := 118043943 }
            case 6 { value := 454905424 }
            case 7 { value := 815798990 }
            case 8 { value := 1004040026 }
            case 9 { value := 1773108264 }
            case 10 { value := 1066694495 }
            case 11 { value := 1930780904 }
            case 12 { value := 1180307149 }
            case 13 { value := 1464793095 }
            case 14 { value := 1660766320 }
            case 15 { value := 1389166148 }
            case 16 { value := 343354132 }
            case 17 { value := 1307439985 }
            case 18 { value := 638242172 }
            case 19 { value := 525458520 }
            case 20 { value := 1964135730 }
            case 21 { value := 1751797115 }
            case 22 { value := 1421525369 }
            case 23 { value := 831813382 }
            case 24 { value := 695835963 }
            case 25 { value := 1845603984 }
            case 26 { value := 540703332 }
            case 27 { value := 1333667262 }
            case 28 { value := 1917861751 }
            case 29 { value := 1170029417 }
            case 30 { value := 1989924532 }
            case 31 { value := 1518763784 }
            case 32 { value := 1339793538 }
            case 33 { value := 622609176 }
            case 34 { value := 686842369 }
            case 35 { value := 1737016378 }
            case 36 { value := 1282239129 }
            case 37 { value := 897025192 }
            case 38 { value := 716894289 }
            case 39 { value := 1997503974 }
            case 40 { value := 395622276 }
            case 41 { value := 1201063290 }
            case 42 { value := 1917549072 }
            case 43 { value := 1150912935 }
            case 44 { value := 1687379185 }
            case 45 { value := 1507936940 }
            case 46 { value := 241306552 }
            case 47 { value := 989176635 }
            case 48 { value := 1147522062 }
            case 49 { value := 27129487 }
            case 50 { value := 1257820264 }
            case 51 { value := 142102402 }
            case 52 { value := 217046702 }
            case 53 { value := 1664590951 }
            case 54 { value := 855276054 }
            case 55 { value := 1215259350 }
            case 56 { value := 946500736 }
            case 57 { value := 552696906 }
            case 58 { value := 1424297384 }
            case 59 { value := 538103555 }
            case 60 { value := 1608853840 }
            case 61 { value := 162510541 }
            case 62 { value := 623051854 }
            case 63 { value := 1549062383 }
            case 64 { value := 1908416316 }
            case 65 { value := 1622328571 }
            case 66 { value := 1079030649 }
            case 67 { value := 1584033957 }
            case 68 { value := 1099252725 }
            case 69 { value := 1910423126 }
            case 70 { value := 447555988 }
            case 71 { value := 862495875 }
            case 72 { value := 128479034 }
            case 73 { value := 1587822577 }
            case 74 { value := 608401422 }
            case 75 { value := 1290028279 }
            case 76 { value := 342857858 }
            case 77 { value := 825405577 }
            case 78 { value := 427731030 }
            case 79 { value := 1718628547 }
            case 80 { value := 588764636 }
            case 81 { value := 204228775 }
            case 82 { value := 1454563174 }
            case 83 { value := 1740472809 }
            case 84 { value := 1338899225 }
            case 85 { value := 1269493554 }
            case 86 { value := 53007114 }
            case 87 { value := 1647670797 }
            case 88 { value := 306391314 }
            case 89 { value := 172614232 }
            case 90 { value := 51256176 }
            case 91 { value := 1221257987 }
            case 92 { value := 1239734761 }
            case 93 { value := 273790406 }
            case 94 { value := 1781980094 }
            case 95 { value := 1291790245 }
            case 65536 { value := 497520322 }
            case 65537 { value := 1930103076 }
            case 65538 { value := 1052077299 }
            case 65539 { value := 1540960371 }
            case 65540 { value := 924863639 }
            case 65541 { value := 1365519753 }
            case 65542 { value := 1726563304 }
            case 65543 { value := 440300254 }
            case 65544 { value := 1891545577 }
            case 65545 { value := 822033215 }
            case 65546 { value := 1111544260 }
            case 65547 { value := 308575117 }
            case 65548 { value := 1708681573 }
            case 65549 { value := 1240419708 }
            case 65550 { value := 1199068823 }
            case 65551 { value := 1186174623 }
            case 65552 { value := 1551596046 }
            case 65553 { value := 1886977120 }
            case 65554 { value := 1327682690 }
            case 65555 { value := 1210751726 }
            case 65556 { value := 1810596765 }
            case 131072 { value := 53041581 }
            case 131073 { value := 723038058 }
            case 131074 { value := 1439947916 }
            case 131075 { value := 1136469704 }
            case 131076 { value := 205609311 }
            case 131077 { value := 1883820770 }
            case 131078 { value := 14387587 }
            case 131079 { value := 720724951 }
            case 131080 { value := 1854174607 }
            case 131081 { value := 1629316321 }
            case 131082 { value := 530151394 }
            case 131083 { value := 1679178250 }
            case 131084 { value := 1549779579 }
            case 131085 { value := 48375137 }
            case 131086 { value := 976057819 }
            case 131087 { value := 463976218 }
            case 131088 { value := 875839332 }
            case 131089 { value := 1946596189 }
            case 131090 { value := 434078361 }
            case 131091 { value := 1878280202 }
            case 131092 { value := 1363837384 }
            case 131093 { value := 1470845646 }
            case 131094 { value := 1792450386 }
            case 131095 { value := 1040977421 }
            case 131096 { value := 1209164052 }
            case 131097 { value := 714957516 }
            case 131098 { value := 390340387 }
            case 131099 { value := 1213686459 }
            case 131100 { value := 790726260 }
            case 131101 { value := 117294666 }
            case 131102 { value := 140621810 }
            case 131103 { value := 993455846 }
            case 131104 { value := 1889603648 }
            case 131105 { value := 78845751 }
            case 131106 { value := 925018226 }
            case 131107 { value := 708123747 }
            case 131108 { value := 1647665372 }
            case 131109 { value := 1649953458 }
            case 131110 { value := 942439428 }
            case 131111 { value := 1006235079 }
            case 131112 { value := 238616145 }
            case 131113 { value := 930036496 }
            case 131114 { value := 1401020792 }
            case 131115 { value := 989618631 }
            case 131116 { value := 1545325389 }
            case 131117 { value := 1715719711 }
            case 131118 { value := 755691969 }
            case 131119 { value := 150307788 }
            case 131120 { value := 1567618575 }
            case 131121 { value := 1663353317 }
            case 131122 { value := 1950429111 }
            case 131123 { value := 1891637550 }
            case 131124 { value := 192082241 }
            case 131125 { value := 1080533265 }
            case 131126 { value := 1463323727 }
            case 131127 { value := 890243564 }
            case 131128 { value := 158646617 }
            case 131129 { value := 1402624179 }
            case 131130 { value := 59510015 }
            case 131131 { value := 1198261138 }
            case 131132 { value := 1065075039 }
            case 131133 { value := 1150410028 }
            case 131134 { value := 1293938517 }
            case 131135 { value := 76770019 }
            case 131136 { value := 1478577620 }
            case 131137 { value := 1748789933 }
            case 131138 { value := 457372011 }
            case 131139 { value := 1841795381 }
            case 131140 { value := 760115692 }
            case 131141 { value := 1042892522 }
            case 131142 { value := 1507649755 }
            case 131143 { value := 1827572010 }
            case 131144 { value := 1206940496 }
            case 131145 { value := 1896271507 }
            case 131146 { value := 1003792297 }
            case 131147 { value := 738091882 }
            case 131148 { value := 1124078057 }
            case 131149 { value := 1889898 }
            case 131150 { value := 813674331 }
            case 131151 { value := 228520958 }
            case 131152 { value := 1832911930 }
            case 131153 { value := 781141772 }
            case 131154 { value := 459826664 }
            case 131155 { value := 202271745 }
            case 131156 { value := 1296144415 }
            case 131157 { value := 1111203133 }
            case 131158 { value := 1090783436 }
            case 131159 { value := 641665156 }
            case 131160 { value := 1393671120 }
            case 131161 { value := 1303271640 }
            case 131162 { value := 809508074 }
            case 131163 { value := 162506101 }
            case 131164 { value := 1262312258 }
            case 131165 { value := 1672219447 }
            case 131166 { value := 1608891156 }
            case 131167 { value := 1380248020 }
            default { revert(0, 0) }
        }
    }
    function diag(uint256 key) internal pure returns (uint256 value) {
        assembly {
            switch key
            case 0 { value := 2013265919 }
            case 1 { value := 1 }
            case 2 { value := 2 }
            case 3 { value := 1006632961 }
            case 4 { value := 3 }
            case 5 { value := 4 }
            case 6 { value := 1006632960 }
            case 7 { value := 2013265918 }
            case 8 { value := 2013265917 }
            case 9 { value := 2005401601 }
            case 10 { value := 1509949441 }
            case 11 { value := 1761607681 }
            case 12 { value := 1887436801 }
            case 13 { value := 1997537281 }
            case 14 { value := 2009333761 }
            case 15 { value := 2013265906 }
            case 16 { value := 7864320 }
            case 17 { value := 503316480 }
            case 18 { value := 251658240 }
            case 19 { value := 125829120 }
            case 20 { value := 62914560 }
            case 21 { value := 31457280 }
            case 22 { value := 15728640 }
            case 23 { value := 15 }
            default { revert(0, 0) }
        }
    }
}

contract H3Poseidon2 is Poseidon2ApplicationKernel {
    constructor() Poseidon2ApplicationKernel(24, 10, 21) {}
    function _rc(uint256 section, uint256 index) internal pure override returns (uint256) { return P2C24.rc((section << 16) | index); }
    function _diag(uint256 index) internal pure override returns (uint256) { return P2C24.diag(index); }
}

contract H4Poseidon2 is Poseidon2Kernel {
    constructor() Poseidon2Kernel(24, 11, 21) {}
    function _rc(uint256 section, uint256 index) internal pure override returns (uint256) { return P2C24.rc((section << 16) | index); }
    function _diag(uint256 index) internal pure override returns (uint256) { return P2C24.diag(index); }
}

