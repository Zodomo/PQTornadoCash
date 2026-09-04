/** Poseidon2/BabyBear domains for protocol-v3 application statements. */
export const applicationDomains = Object.freeze({
  SCOPE: 0x10,
  NOTE: 0x11,
  NULLIFIER: 0x12,
  EMPTY_LEAF: 0x13,
  PAYOUT: 0x14,
  STATEMENT: 0x15,
  APP_MERKLE_NODE: 0x20,
} as const);

/** KeccakPair512 domains retained only by the proof system and parameter manifest. */
export const proofDomains = Object.freeze({
  PROOF_LEAF: 0x40,
  PROOF_NODE: 0x41,
  TRANSCRIPT_INIT: 0x42,
  TRANSCRIPT_ABSORB: 0x43,
  TRANSCRIPT_SQUEEZE: 0x44,
  PARAMETER_MANIFEST: 0x45,
} as const);

/** Keccak coordination labels for the v3 two-part proof protocol. */
export const coordinationDomains = Object.freeze({
  STATEMENT: "PQTC.V3.STATEMENT",
  PROOF: "PQTC.V3.PROOF",
  CHECKPOINT: "PQTC.V3.CHECKPOINT",
  VERIFICATION: "PQTC.V3.VERIFICATION",
} as const);

export const domains = Object.freeze({ ...applicationDomains, ...proofDomains });

export type ApplicationDomain = typeof applicationDomains[keyof typeof applicationDomains];
export type ProofDomain = typeof proofDomains[keyof typeof proofDomains];

export function isApplicationDomain(value: number): value is ApplicationDomain {
  return (value >= applicationDomains.SCOPE && value <= applicationDomains.STATEMENT)
    || value === applicationDomains.APP_MERKLE_NODE;
}

export function isProofDomain(value: number): value is ProofDomain {
  return value >= proofDomains.PROOF_LEAF && value <= proofDomains.PARAMETER_MANIFEST;
}
