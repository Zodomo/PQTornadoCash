// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;
import "../../../cryptanalysis/transcript/solidity/TranscriptResearch.sol";

/// @notice BENCHMARK_ONLY T1 typed-array research construction.
contract T1TranscriptCandidate {
    function initialize(bytes32 left, bytes32 right, uint32[] calldata publicValues) external pure returns (bytes32, bytes32) {
        TranscriptResearch.State memory state = TranscriptResearch.initialize(TranscriptResearch.Variant.T1, left, right, publicValues, false);
        return (state.left, state.right);
    }
}
