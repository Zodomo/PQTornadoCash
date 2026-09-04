#!/usr/bin/env node
import { type Digest512 } from "./index.js";
export declare const RELAYER_REQUEST_VERSION = 3;
export interface WithdrawalRequestV3 {
    version: 3;
    chainId: string;
    pool: string;
    registry: string;
    scope: string;
    parameterId: string;
    root: string;
    nullifierHash: string;
    recipient: string;
    relayer: string;
    fee: string;
    deadline: string;
    statementId: string;
    publicValues: number[];
    proof: {
        partA: string;
        partB: string;
    };
}
export interface RelayerPolicy {
    chainId: bigint;
    pool: string;
    registry: string;
    scope: string;
    parameterId: string;
    denomination: bigint;
    relayer: string;
}
export interface RelayerTransaction {
    readonly phase: "A" | "B";
    readonly order: 1 | 2;
    readonly from: `0x${string}`;
    readonly to: `0x${string}`;
    readonly data: `0x${string}`;
}
export interface TransactionReceipt {
    status: string | number;
    to: string | null;
    logs: ReadonlyArray<{
        address: string;
        topics: readonly string[];
    }>;
}
export declare function deriveStatementKey(parameterId: Digest512, values: Uint32Array): `0x${string}`;
export declare function deriveCoreProofId(statementKey: string, proofPartA: Uint8Array): `0x${string}`;
export declare function deriveVerificationId(coreProofId: string, consumer: string): `0x${string}`;
/**
 * Stateful two-transaction withdrawal builder. Part B cannot be produced until a successful,
 * statement-bound part A receipt has been supplied, and no third transaction can be produced.
 */
export declare class WithdrawalSubmission {
    #private;
    private constructor();
    static create(input: unknown, policy: RelayerPolicy, nowSeconds?: bigint): WithdrawalSubmission;
    partA(): RelayerTransaction;
    partB(receipt: TransactionReceipt, nowSeconds?: bigint): RelayerTransaction;
}
export declare function runRelayerCli(argv?: string[], environment?: NodeJS.ProcessEnv): Promise<void>;
