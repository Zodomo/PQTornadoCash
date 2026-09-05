// SPDX-License-Identifier: MIT OR Apache-2.0
pragma solidity >=0.8.30 <0.9.0;

library PQTCDomains {
    uint8 internal constant SCOPE = 0x10;
    uint8 internal constant NOTE = 0x11;
    uint8 internal constant NULLIFIER = 0x12;
    uint8 internal constant EMPTY_LEAF = 0x13;
    uint8 internal constant PAYOUT = 0x14;
    uint8 internal constant STATEMENT = 0x15;
    uint8 internal constant APP_MERKLE_NODE = 0x20;
    uint8 internal constant PROOF_LEAF = 0x40;
    uint8 internal constant PROOF_NODE = 0x41;
    uint8 internal constant TRANSCRIPT_INIT = 0x42;
    uint8 internal constant TRANSCRIPT_ABSORB = 0x43;
    uint8 internal constant TRANSCRIPT_SQUEEZE = 0x44;
    uint8 internal constant PARAMETER_MANIFEST = 0x45;
}
