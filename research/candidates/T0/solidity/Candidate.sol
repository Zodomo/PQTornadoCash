// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;
import "../../../cryptanalysis/transcript/solidity/TranscriptResearch.sol";

/// @notice BENCHMARK_ONLY T0 production-compatible field-by-field control.
contract T0TranscriptCandidate {
    function initialize(bytes32 left, bytes32 right, uint32[] calldata publicValues) external pure returns (bytes32, bytes32) {
        TranscriptResearch.State memory state = TranscriptResearch.initialize(TranscriptResearch.Variant.T0, left, right, publicValues, true);
        return (state.left, state.right);
    }
}
