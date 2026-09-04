// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;
import "../../../cryptanalysis/transcript/solidity/TranscriptResearch.sol";

/// @notice BENCHMARK_ONLY T2 item-digest-plus-state research construction.
contract T2TranscriptCandidate {
    function initialize(bytes32 left, bytes32 right, uint32[] calldata publicValues) external pure returns (bytes32, bytes32) {
        TranscriptResearch.State memory state = TranscriptResearch.initialize(TranscriptResearch.Variant.T2, left, right, publicValues, false);
        return (state.left, state.right);
    }
}
