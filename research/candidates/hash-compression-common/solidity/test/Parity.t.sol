// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity ^0.8.24;
import {H0Sponge} from "../src/H0Sponge.sol";
import {H1Poseidon2} from "../src/Poseidon16Candidates.sol";
import {H3Poseidon2, H4Poseidon2} from "../src/Poseidon24Candidates.sol";
import {H5Poseidon2, H6Poseidon2} from "../src/Poseidon32Candidates.sol";
import {H7RpoM31} from "../src/H7RpoM31.sol";
contract Parity {
    function _eq(uint256[] memory actual, uint256[] memory expected) private pure { require(actual.length == expected.length, "length"); for (uint256 i; i < actual.length; ++i) require(actual[i] == expected[i], "lane"); }
    function _seq(uint256 n) private pure returns (uint256[] memory a) { a = new uint256[](n); for (uint256 i; i < n; ++i) a[i] = i + 1; }
    function testPoseidon16PinnedVector() external {
        H1Poseidon2 kernel = new H1Poseidon2();
        uint256[] memory input = new uint256[](16); uint32[16] memory source = [894848333, 1437655012, 1200606629, 1690012884, 71131202, 1749206695, 1717947831, 120589055, 19776022, 42382981, 1831865506, 724844064, 171220207, 1299207443, 227047920, 1783754913]; for (uint256 i; i < 16; ++i) input[i] = uint256(source[i]) % 2013265921;
        uint256[] memory expected = new uint256[](16); uint32[16] memory answer = [516096821, 90309867, 1101817252, 1660784290, 360715097, 1789519026, 1788910906, 563338433, 319524748, 1741414159, 1650859320, 894311162, 1121347488, 1692793758, 1052633829, 1344246938]; for (uint256 i; i < 16; ++i) expected[i] = answer[i];
        _eq(kernel.permutation(input), expected);
    }
    function testPoseidon24PinnedVector() external {
        H4Poseidon2 kernel = new H4Poseidon2();
        uint256[] memory input = new uint256[](24); uint32[24] memory source = [886409618, 1327899896, 1902407911, 591953491, 648428576, 1844789031, 1198336108, 355597330, 1799586834, 59617783, 790334801, 1968791836, 559272107, 31054313, 1042221543, 474748436, 135686258, 263665994, 1962340735, 1741539604, 2026927696, 449439011, 1131357108, 50869465]; for (uint256 i; i < 24; ++i) input[i] = uint256(source[i]) % 2013265921;
        uint256[] memory expected = new uint256[](24); uint32[24] memory answer = [882297297, 1264077610, 512812497, 782602970, 867738552, 1251075457, 309180082, 340784773, 524041877, 351272188, 404451680, 15001466, 322926653, 1773004150, 1718440818, 674682955, 1154713225, 1719133502, 324232301, 1005243141, 443371079, 268735940, 770060019, 718377682]; for (uint256 i; i < 24; ++i) expected[i] = answer[i];
        _eq(kernel.permutation(input), expected);
    }
    function testPoseidon32PinnedVector() external {
        H5Poseidon2 kernel = new H5Poseidon2();
        uint256[] memory input = new uint256[](32); uint32[32] memory source = [377682961, 1957793603, 980981814, 6565119, 1583211709, 176593168, 1672635515, 226854190, 1096634172, 1317773742, 1472230830, 1621534427, 559807320, 1484241910, 1847825942, 3491998, 950152427, 1935451636, 275759400, 227625951, 1271142011, 1492341973, 1502961189, 147694103, 1939834518, 1449972249, 1822424048, 1518111482, 714203295, 383863563, 411489861, 1253612091]; for (uint256 i; i < 32; ++i) input[i] = uint256(source[i]) % 2013265921;
        uint256[] memory expected = new uint256[](32); uint32[32] memory answer = [303440672, 985419733, 780962554, 1395263823, 188752116, 1348917749, 677984158, 667170017, 97281439, 178741618, 1770541242, 1894441262, 847173187, 1374453653, 1242356754, 1485142795, 1019698843, 334329175, 540395852, 918117757, 1288401072, 508687761, 996827321, 1660764537, 546969284, 1848510002, 334793951, 736596659, 1928951999, 1444080616, 55017699, 1832626373]; for (uint256 i; i < 32; ++i) expected[i] = answer[i];
        _eq(kernel.permutation(input), expected);
    }
    function testH0ApplicationVector() external {
        H0Sponge kernel = new H0Sponge(); uint256[] memory expected = new uint256[](16); uint32[16] memory answer = [1371018046, 608990609, 1048304045, 1590109088, 713745007, 1140652620, 1500515823, 928289631, 1238315048, 485489018, 1526041673, 1161763304, 414315635, 1067455242, 93934195, 223725480]; for (uint256 i; i < 16; ++i) expected[i] = answer[i]; _eq(kernel.note(_seq(32)), expected);
    }
    function testH3ApplicationVector() external {
        H3Poseidon2 kernel = new H3Poseidon2(); uint256[] memory expected = new uint256[](10); uint32[10] memory answer = [375004468, 646173907, 1807982651, 89538298, 916457007, 97238205, 1398012006, 450658320, 1995019648, 903148414]; for (uint256 i; i < 10; ++i) expected[i] = answer[i]; _eq(kernel.note(_seq(20)), expected);
    }
    function testH5ApplicationVector() external {
        H5Poseidon2 kernel = new H5Poseidon2(); uint256[] memory expected = new uint256[](12); uint32[12] memory answer = [142719137, 1000080115, 909630913, 381072420, 1505459982, 1668718263, 1317022018, 85558165, 1337347973, 1885139377, 841903424, 604745240]; for (uint256 i; i < 12; ++i) expected[i] = answer[i]; _eq(kernel.note(_seq(24)), expected);
    }
    function testH6ApplicationVector() external {
        H6Poseidon2 kernel = new H6Poseidon2(); uint256[] memory expected = new uint256[](14); uint32[14] memory answer = [492871309, 1612428121, 1430400058, 463152251, 1624972296, 1845742215, 1825555862, 1645873054, 1797231729, 1972285041, 649699386, 2010011719, 1645966372, 1894411437]; for (uint256 i; i < 14; ++i) expected[i] = answer[i]; _eq(kernel.note(_seq(28)), expected);
    }
    function testH7PinnedPermutationAndApplication() external {
        H7RpoM31 kernel = new H7RpoM31(); uint256[] memory input = new uint256[](24); for (uint256 i; i < 24; ++i) input[i] = i;
        uint256[] memory expectedPermutation = new uint256[](24); uint32[24] memory permutationAnswer = [1990425063, 95513650, 1492148912, 1455268556, 347571427, 1892690094, 34080484, 1175631837, 1348619901, 1096114017, 310913313, 1912324205, 609442899, 2112777835, 1331189849, 507241525, 1800223977, 568712449, 2123164950, 86025361, 1585828474, 1334334486, 188486534, 1147991035]; for (uint256 i; i < 24; ++i) expectedPermutation[i] = permutationAnswer[i]; _eq(kernel.permutation(input), expectedPermutation);
        uint256[] memory expectedNote = new uint256[](16); uint32[16] memory noteAnswer = [186086376, 1476067265, 1739135530, 1493401907, 715004007, 58639479, 483121991, 2115868369, 1963252253, 1713441571, 428964071, 757681105, 1805296726, 696418616, 695306431, 107269358]; for (uint256 i; i < 16; ++i) expectedNote[i] = noteAnswer[i]; _eq(kernel.note(_seq(32)), expectedNote);
    }
}
