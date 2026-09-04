//! Normative one-byte protocol domains. Changing any value changes the protocol.

pub const SCOPE: u8 = 0x10;
pub const NOTE: u8 = 0x11;
pub const NULLIFIER: u8 = 0x12;
pub const EMPTY_LEAF: u8 = 0x13;
pub const PAYOUT: u8 = 0x14;
pub const STATEMENT: u8 = 0x15;
pub const APP_MERKLE_NODE: u8 = 0x20;

pub const PROOF_LEAF: u8 = 0x40;
pub const PROOF_NODE: u8 = 0x41;
pub const TRANSCRIPT_INIT: u8 = 0x42;
pub const TRANSCRIPT_ABSORB: u8 = 0x43;
pub const TRANSCRIPT_SQUEEZE: u8 = 0x44;
pub const PARAMETER_MANIFEST: u8 = 0x45;
