import { coordinationDomains, domains } from "./domains.js";
export { coordinationDomains, domains };
export declare const TREE_DEPTH = 20;
export declare const PROTOCOL_VERSION = 3;
export declare const BABY_BEAR_MODULUS = 2013265921;
export type Digest512 = Readonly<{
    left: Uint8Array;
    right: Uint8Array;
}>;
export type Address = Uint8Array;
export declare function digestBytes(digest: Digest512): Uint8Array;
export declare function digestFromBytes(bytes: Uint8Array): Digest512;
export declare function digestEqual(a: Digest512, b: Digest512): boolean;
export declare function poseidon2BabyBear16(input: ArrayLike<number>): Uint32Array;
export declare function digestElements(digest: Digest512, name?: string): Uint32Array;
export declare function digestFromElements(elements: ArrayLike<number>): Digest512;
export type CanonicalSecret = ArrayLike<number | bigint>;
export declare function secretBytes(secret: CanonicalSecret, name?: string): Uint8Array;
export declare function secretFromBytes(bytes: Uint8Array, name?: string): Uint32Array;
export declare function randomSecret(): Uint32Array;
export declare function p2bb512(tag: number, payloadByteLength: number, aux: number, payload: ArrayLike<number>): Digest512;
export declare function k512(tag: number, payload: Uint8Array): Digest512;
export interface ScopeInput {
    chainId: bigint;
    pool: Address;
    denomination: bigint;
    treeDepth?: number;
    protocolVersion?: number;
    parameterId: Digest512;
}
export declare function scope(input: ScopeInput): Digest512;
export declare function commitment(poolScope: Digest512, nullifierSecret: CanonicalSecret, trapdoor: CanonicalSecret): Digest512;
export declare function nullifierHash(poolScope: Digest512, nullifierSecret: CanonicalSecret): Digest512;
export declare function emptyLeaf(poolScope: Digest512): Digest512;
export declare function merkleNode(level: number, left: Digest512, right: Digest512): Digest512;
export declare function payoutDigest(recipient: Address, relayer: Address, fee: bigint): Digest512;
export interface WithdrawalStatement {
    scope: Digest512;
    root: Digest512;
    nullifierHash: Digest512;
    payoutDigest: Digest512;
}
export declare function statementHash(statement: WithdrawalStatement): Digest512;
export declare function publicValues(statement: WithdrawalStatement): Uint32Array;
export interface CompactProofV3 {
    parameterId: Digest512;
    publicValues: Uint32Array;
    starkPayload: Uint8Array;
}
export declare function encodeCompactProof(proof: CompactProofV3): Uint8Array;
export declare function decodeCompactProof(bytes: Uint8Array): CompactProofV3;
export interface Note {
    chainId: bigint;
    pool: Address;
    parameterId: Digest512;
    nullifierSecret: CanonicalSecret;
    trapdoor: CanonicalSecret;
}
export declare function newNote(chainId: bigint, pool: Address, parameterId: Digest512): Note;
export declare function encodeNote(note: Note): string;
export declare function parseNote(encoded: string): Note;
export declare class NoteSecretTracker {
    private readonly nullifierSecrets;
    register(note: Note): void;
}
export interface MerklePath {
    leafIndex: number;
    siblings: Digest512[];
}
export declare class MerkleTree {
    readonly zeros: Digest512[];
    readonly leaves: Digest512[];
    readonly filledSubtrees: Digest512[];
    private readonly commitmentKeys;
    root: Digest512;
    constructor(poolScope: Digest512);
    insert(leaf: Digest512): Readonly<{
        leafIndex: number;
        root: Digest512;
    }>;
    path(leafIndex: number): MerklePath;
}
export declare function rootFromPath(leaf: Digest512, path: MerklePath): Digest512;
export declare function encodeDepositCalldata(noteCommitment: Digest512): Uint8Array;
export declare function hex(bytes: Uint8Array): `0x${string}`;
export declare function bytesFromHex(value: string, expectedLength?: number): Uint8Array;
