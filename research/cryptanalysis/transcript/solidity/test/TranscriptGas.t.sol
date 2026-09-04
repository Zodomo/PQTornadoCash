// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;
import "../TranscriptResearch.sol";

contract TranscriptGasScenario {
    function testT0Gas() external { runCandidate(0); }
    function testT1Gas() external { runCandidate(1); }
    function testT2Gas() external { runCandidate(2); }
    function testT3Gas() external { runCandidate(3); }

    function runCandidate(uint8 candidate) private {
        TranscriptGasHarness harness = new TranscriptGasHarness();
        uint32[] memory publicValues = new uint32[](64);
        for (uint32 i; i < 64; ++i) publicValues[i] = i + 1;
        bytes memory typedArray = abi.encodePacked(uint32(2), uint32(1), uint32(2));
        harness.bench(candidate, bytes32(uint256(1)), bytes32(uint256(2)), publicValues, typedArray, bytes("canonical-proof"), bytes("canonical-proof"), bytes("canonical-calldata"), bytes("canonical-calldata"));
    }
}
