/** Poseidon2/BabyBear domains for protocol-v3 application statements. */
export declare const applicationDomains: Readonly<{
    readonly SCOPE: 16;
    readonly NOTE: 17;
    readonly NULLIFIER: 18;
    readonly EMPTY_LEAF: 19;
    readonly PAYOUT: 20;
    readonly STATEMENT: 21;
    readonly APP_MERKLE_NODE: 32;
}>;
/** KeccakPair512 domains retained only by the proof system and parameter manifest. */
export declare const proofDomains: Readonly<{
    readonly PROOF_LEAF: 64;
    readonly PROOF_NODE: 65;
    readonly TRANSCRIPT_INIT: 66;
    readonly TRANSCRIPT_ABSORB: 67;
    readonly TRANSCRIPT_SQUEEZE: 68;
    readonly PARAMETER_MANIFEST: 69;
}>;
/** Keccak coordination labels for the v3 two-part proof protocol. */
export declare const coordinationDomains: Readonly<{
    readonly STATEMENT: "PQTC.V3.STATEMENT";
    readonly PROOF: "PQTC.V3.PROOF";
    readonly CHECKPOINT: "PQTC.V3.CHECKPOINT";
    readonly VERIFICATION: "PQTC.V3.VERIFICATION";
}>;
export declare const domains: Readonly<{
    PROOF_LEAF: 64;
    PROOF_NODE: 65;
    TRANSCRIPT_INIT: 66;
    TRANSCRIPT_ABSORB: 67;
    TRANSCRIPT_SQUEEZE: 68;
    PARAMETER_MANIFEST: 69;
    SCOPE: 16;
    NOTE: 17;
    NULLIFIER: 18;
    EMPTY_LEAF: 19;
    PAYOUT: 20;
    STATEMENT: 21;
    APP_MERKLE_NODE: 32;
}>;
export type ApplicationDomain = typeof applicationDomains[keyof typeof applicationDomains];
export type ProofDomain = typeof proofDomains[keyof typeof proofDomains];
export declare function isApplicationDomain(value: number): value is ApplicationDomain;
export declare function isProofDomain(value: number): value is ProofDomain;
