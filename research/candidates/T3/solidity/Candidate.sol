// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;
import "../../../cryptanalysis/transcript/solidity/TranscriptResearch.sol";

/// @notice BENCHMARK_ONLY T3 challenge-boundary-frame research construction.
contract T3TranscriptCandidate {
    function initialize(bytes32 left, bytes32 right, uint32[] calldata publicValues) external pure returns (bytes32, bytes32) {
        TranscriptResearch.State memory state = TranscriptResearch.initialize(TranscriptResearch.Variant.T3, left, right, publicValues, false);
        state.flush();
        return (state.left, state.right);
    }
}
