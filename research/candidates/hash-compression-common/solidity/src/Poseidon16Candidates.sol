// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;
import "./Poseidon2Kernel.sol";

library P2C16 {
    function rc(uint256 key) internal pure returns (uint256 value) {
        assembly {
            switch key
            case 0 { value := 1774958255 }
            case 1 { value := 1185780729 }
            case 2 { value := 1621102414 }
            case 3 { value := 1796380621 }
            case 4 { value := 588815102 }
            case 5 { value := 1932426223 }
            case 6 { value := 1925334750 }
            case 7 { value := 747903232 }
            case 8 { value := 89648862 }
            case 9 { value := 360728943 }
            case 10 { value := 977184635 }
            case 11 { value := 1425273457 }
            case 12 { value := 256487465 }
            case 13 { value := 1200041953 }
            case 14 { value := 572403254 }
            case 15 { value := 448208942 }
            case 16 { value := 1215789478 }
            case 17 { value := 944884184 }
            case 18 { value := 953948096 }
            case 19 { value := 547326025 }
            case 20 { value := 646827752 }
            case 21 { value := 889997530 }
            case 22 { value := 1536873262 }
            case 23 { value := 86189867 }
            case 24 { value := 1065944411 }
            case 25 { value := 32019634 }
            case 26 { value := 333311454 }
            case 27 { value := 456061748 }
            case 28 { value := 1963448500 }
            case 29 { value := 1827584334 }
            case 30 { value := 1391160226 }
            case 31 { value := 1348741381 }
            case 32 { value := 88424255 }
            case 33 { value := 104111868 }
            case 34 { value := 1763866748 }
            case 35 { value := 79691676 }
            case 36 { value := 1988915530 }
            case 37 { value := 1050669594 }
            case 38 { value := 359890076 }
            case 39 { value := 573163527 }
            case 40 { value := 222820492 }
            case 41 { value := 159256268 }
            case 42 { value := 669703072 }
            case 43 { value := 763177444 }
            case 44 { value := 889367200 }
            case 45 { value := 256335831 }
            case 46 { value := 704371273 }
            case 47 { value := 25886717 }
            case 48 { value := 51754520 }
            case 49 { value := 1833211857 }
            case 50 { value := 454499742 }
            case 51 { value := 1384520381 }
            case 52 { value := 777848065 }
            case 53 { value := 1053320300 }
            case 54 { value := 1851729162 }
            case 55 { value := 344647910 }
            case 56 { value := 401996362 }
            case 57 { value := 1046925956 }
            case 58 { value := 5351995 }
            case 59 { value := 1212119315 }
            case 60 { value := 754867989 }
            case 61 { value := 36972490 }
            case 62 { value := 751272725 }
            case 63 { value := 506915399 }
            case 65536 { value := 1518359488 }
            case 65537 { value := 1765533241 }
            case 65538 { value := 945325693 }
            case 65539 { value := 422793067 }
            case 65540 { value := 311365592 }
            case 65541 { value := 1311448267 }
            case 65542 { value := 1629555936 }
            case 65543 { value := 1009879353 }
            case 65544 { value := 190525218 }
            case 65545 { value := 786108885 }
            case 65546 { value := 557776863 }
            case 65547 { value := 212616710 }
            case 65548 { value := 605745517 }
            case 131072 { value := 1922082829 }
            case 131073 { value := 1870549801 }
            case 131074 { value := 1502529704 }
            case 131075 { value := 1990744480 }
            case 131076 { value := 1700391016 }
            case 131077 { value := 1702593455 }
            case 131078 { value := 321330495 }
            case 131079 { value := 528965731 }
            case 131080 { value := 183414327 }
            case 131081 { value := 1886297254 }
            case 131082 { value := 1178602734 }
            case 131083 { value := 1923111974 }
            case 131084 { value := 744004766 }
            case 131085 { value := 549271463 }
            case 131086 { value := 1781349648 }
            case 131087 { value := 542259047 }
            case 131088 { value := 1536158148 }
            case 131089 { value := 715456982 }
            case 131090 { value := 503426110 }
            case 131091 { value := 340311124 }
            case 131092 { value := 1558555932 }
            case 131093 { value := 1226350925 }
            case 131094 { value := 742828095 }
            case 131095 { value := 1338992758 }
            case 131096 { value := 1641600456 }
            case 131097 { value := 1843351545 }
            case 131098 { value := 301835475 }
            case 131099 { value := 43203215 }
            case 131100 { value := 386838401 }
            case 131101 { value := 1520185679 }
            case 131102 { value := 1235297680 }
            case 131103 { value := 904680097 }
            case 131104 { value := 1491801617 }
            case 131105 { value := 1581784677 }
            case 131106 { value := 913384905 }
            case 131107 { value := 247083962 }
            case 131108 { value := 532844013 }
            case 131109 { value := 107190701 }
            case 131110 { value := 213827818 }
            case 131111 { value := 1979521776 }
            case 131112 { value := 1358282574 }
            case 131113 { value := 1681743681 }
            case 131114 { value := 1867507480 }
            case 131115 { value := 1530706910 }
            case 131116 { value := 507181886 }
            case 131117 { value := 695185447 }
            case 131118 { value := 1172395131 }
            case 131119 { value := 1250800299 }
            case 131120 { value := 1503161625 }
            case 131121 { value := 817684387 }
            case 131122 { value := 498481458 }
            case 131123 { value := 494676004 }
            case 131124 { value := 1404253825 }
            case 131125 { value := 108246855 }
            case 131126 { value := 59414691 }
            case 131127 { value := 744214112 }
            case 131128 { value := 890862029 }
            case 131129 { value := 1342765939 }
            case 131130 { value := 1417398904 }
            case 131131 { value := 1897591937 }
            case 131132 { value := 1066647396 }
            case 131133 { value := 1682806907 }
            case 131134 { value := 1015795079 }
            case 131135 { value := 1619482808 }
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
            case 12 { value := 2013265906 }
            case 13 { value := 7864320 }
            case 14 { value := 125829120 }
            case 15 { value := 15 }
            default { revert(0, 0) }
        }
    }
}

contract H1Poseidon2 is Poseidon2Kernel {
    constructor() Poseidon2Kernel(16, 7, 13) {}
    function _rc(uint256 section, uint256 index) internal pure override returns (uint256) { return P2C16.rc((section << 16) | index); }
    function _diag(uint256 index) internal pure override returns (uint256) { return P2C16.diag(index); }
}

