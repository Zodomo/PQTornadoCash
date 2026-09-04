// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity 0.8.30;

import {PQTCClassicPool, IPQTCVerificationRegistry} from "v03/PQTCClassicPool.sol";
import {Digest512} from "v03/libraries/Digest512.sol";

/// @dev Research-only fixture loader. It deliberately bypasses deposit history so
/// synthetic common-corpus paths can exercise the unmodified pool-facing A/B calls.
contract ResearchFixturePool is PQTCClassicPool {
    constructor(uint256 denomination_, Digest512 memory parameterId_, IPQTCVerificationRegistry registry_)
        PQTCClassicPool(denomination_, parameterId_, registry_)
    {}

    function researchInitializeEtchedStorage(Digest512 calldata scope_, Digest512 calldata root_, Digest512 calldata parameterId_)
        external
    {
        scope = scope_;
        parameterId = parameterId_;
        knownRoots[root_.left][root_.right] = true;
        // PQTCClassicPool's private reentrancyState is slot 90 in the frozen
        // v0.3 storage layout. The test asserts that a complete guarded call works.
        assembly ("memory-safe") { sstore(90, 1) }
    }
}
