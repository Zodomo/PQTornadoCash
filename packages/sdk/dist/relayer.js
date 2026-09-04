#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { keccak_256 } from "@noble/hashes/sha3.js";
import { coordinationDomains } from "./domains.js";
import { BABY_BEAR_MODULUS, PROTOCOL_VERSION, bytesFromHex, digestBytes, digestEqual, digestFromBytes, hex, payoutDigest, publicValues, statementHash, } from "./index.js";
export const RELAYER_REQUEST_VERSION = PROTOCOL_VERSION;
const UINT64_LIMIT = 1n << 64n;
const UINT256_LIMIT = 1n << 256n;
const TEXT_ENCODER = new TextEncoder();
const STATEMENT_KEY_LABEL = TEXT_ENCODER.encode(coordinationDomains.STATEMENT);
const PROOF_ID_LABEL = TEXT_ENCODER.encode(coordinationDomains.PROOF);
const CHECKPOINT_LABEL = TEXT_ENCODER.encode(coordinationDomains.CHECKPOINT);
const VERIFICATION_ID_LABEL = TEXT_ENCODER.encode(coordinationDomains.VERIFICATION);
const PROOF_PART_A_MAGIC = TEXT_ENCODER.encode("PQTCPA03");
const PROOF_PART_B_MAGIC = TEXT_ENCODER.encode("PQTCPB03");
const PROOF_COMMON_HEADER_BYTES = 338;
const GLOBAL_DATA_BYTES = 9_208;
const QUERY_COUNT = 32;
const HALF_QUERY_COUNT = 16;
const FRI_ROUNDS = 9;
const CHECKPOINT_FIXED_BYTES = 452;
const PART_A_END = "0x50414533";
const PART_B_END = "0x50424533";
const VERIFICATION_STARTED_TOPIC = hex(keccak_256(TEXT_ENCODER.encode("VerificationStarted(bytes32,address,bytes32)")));
function concat(...parts) {
    const length = parts.reduce((sum, part) => sum + part.length, 0);
    const output = new Uint8Array(length);
    let cursor = 0;
    for (const part of parts) {
        output.set(part, cursor);
        cursor += part.length;
    }
    return output;
}
function uintWord(value) {
    if (value < 0n || value >= UINT256_LIMIT)
        throw new RangeError("integer does not fit an ABI word");
    const output = new Uint8Array(32);
    for (let index = output.length - 1; index >= 0; index--) {
        output[index] = Number(value & 0xffn);
        value >>= 8n;
    }
    return output;
}
function abiAddress(address) {
    const output = new Uint8Array(32);
    output.set(address, 12);
    return output;
}
function abiBytes(bytes) {
    const padded = new Uint8Array(Math.ceil(bytes.length / 32) * 32);
    padded.set(bytes);
    return concat(uintWord(BigInt(bytes.length)), padded);
}
function functionSelector(signature) {
    return keccak_256(TEXT_ENCODER.encode(signature)).slice(0, 4);
}
function asRecord(value, name) {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
        throw new TypeError(`${name} must be an object`);
    }
    return value;
}
function requireExactKeys(record, expected, name) {
    for (const key of Object.keys(record)) {
        if (!expected.includes(key))
            throw new Error(`${name} contains unsupported field ${key}`);
    }
    for (const key of expected) {
        if (!(key in record))
            throw new Error(`${name} is missing ${key}`);
    }
}
function requireString(value, name) {
    if (typeof value !== "string")
        throw new TypeError(`${name} must be a string`);
    return value;
}
function unsignedDecimal(value, name, limit) {
    const text = requireString(value, name);
    if (!/^(0|[1-9][0-9]*)$/.test(text))
        throw new TypeError(`${name} must be canonical unsigned decimal`);
    const parsed = BigInt(text);
    if (parsed >= limit)
        throw new RangeError(`${name} is out of range`);
    return parsed;
}
function address(value, name, allowZero = false) {
    const bytes = bytesFromHex(requireString(value, name), 20);
    if (!allowZero && bytes.every((byte) => byte === 0))
        throw new Error(`${name} cannot be zero`);
    return { bytes, hex: hex(bytes) };
}
function canonicalDigest(value, name, allowZero = true) {
    const bytes = bytesFromHex(requireString(value, name), 64);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    let nonzero = false;
    for (let index = 0; index < 16; index++) {
        const limb = view.getUint32(index * 4, false);
        if (limb >= BABY_BEAR_MODULUS)
            throw new RangeError(`${name} limb ${index} is not canonical`);
        nonzero ||= limb !== 0;
    }
    if (!allowZero && !nonzero)
        throw new Error(`${name} cannot be zero`);
    return digestFromBytes(bytes);
}
function proofDigest(value, name, allowZero = true) {
    const bytes = bytesFromHex(requireString(value, name), 64);
    if (!allowZero && bytes.every((byte) => byte === 0))
        throw new Error(`${name} cannot be zero`);
    return digestFromBytes(bytes);
}
function digestHex(digest) {
    return hex(digestBytes(digest));
}
function sameBytes(left, right) {
    if (left.length !== right.length)
        return false;
    let difference = 0;
    for (let index = 0; index < left.length; index++)
        difference |= left[index] ^ right[index];
    return difference === 0;
}
function parsePublicValues(value) {
    if (!Array.isArray(value) || value.length !== 64)
        throw new Error("publicValues must contain 64 elements");
    const output = new Uint32Array(64);
    for (let index = 0; index < value.length; index++) {
        const limb = value[index];
        if (!Number.isInteger(limb) || limb < 0 || limb >= BABY_BEAR_MODULUS) {
            throw new RangeError(`publicValues[${index}] is not canonical`);
        }
        output[index] = limb;
    }
    return output;
}
function abiPublicValues(values) {
    if (values.length !== 64)
        throw new Error("public values must contain 64 elements");
    const words = new Uint8Array(64 * 32);
    const view = new DataView(words.buffer);
    for (let index = 0; index < values.length; index++) {
        const value = values[index];
        if (value >= BABY_BEAR_MODULUS)
            throw new RangeError(`public value ${index} is not canonical`);
        view.setUint32(index * 32 + 28, value, false);
    }
    return words;
}
export function deriveStatementKey(parameterId, values) {
    const canonicalParameterId = proofDigest(digestHex(parameterId), "parameterId", false);
    const label = new Uint8Array(32);
    label.set(STATEMENT_KEY_LABEL);
    return hex(keccak_256(concat(label, digestBytes(canonicalParameterId), abiPublicValues(values))));
}
export function deriveCoreProofId(statementKey, proofPartA) {
    const label = new Uint8Array(32);
    label.set(PROOF_ID_LABEL);
    return hex(keccak_256(concat(label, bytesFromHex(statementKey, 32), keccak_256(proofPartA))));
}
export function deriveVerificationId(coreProofId, consumer) {
    const label = new Uint8Array(32);
    label.set(VERIFICATION_ID_LABEL);
    return hex(keccak_256(concat(label, bytesFromHex(coreProofId, 32), abiAddress(address(consumer, "consumer").bytes))));
}
function parseProofPart(value, expectedKind, expectedParameterId, expectedPublicValues, expectedStatementKey) {
    const name = `proof.part${expectedKind}`;
    const payload = bytesFromHex(requireString(value, name));
    const proofIdBytes = expectedKind === "B" ? 32 : 0;
    const globalDigestOffset = PROOF_COMMON_HEADER_BYTES + proofIdBytes;
    const globalDataOffset = globalDigestOffset + 32;
    const checkpointOffset = globalDataOffset + GLOBAL_DATA_BYTES;
    if (payload.length < checkpointOffset + CHECKPOINT_FIXED_BYTES + 4 + HALF_QUERY_COUNT * 4 + 4) {
        throw new Error(`${name} is truncated`);
    }
    const magic = expectedKind === "A" ? PROOF_PART_A_MAGIC : PROOF_PART_B_MAGIC;
    if (!sameBytes(payload.subarray(0, 8), magic)) {
        throw new Error(`${name} has wrong magic or the proof parts were swapped`);
    }
    const endMarker = expectedKind === "A" ? PART_A_END : PART_B_END;
    if (hex(payload.subarray(payload.length - 4)) !== endMarker)
        throw new Error(`${name} has invalid end marker`);
    const view = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
    if (view.getUint16(8, false) !== RELAYER_REQUEST_VERSION)
        throw new Error(`${name} must use proof version 3`);
    if (view.getUint8(10) !== 3)
        throw new Error(`${name} must use the v0.3 security profile`);
    if (view.getUint8(11) !== 9
        || view.getUint8(12) !== FRI_ROUNDS
        || view.getUint8(13) !== 4) {
        throw new Error(`${name} has unsupported proof shape`);
    }
    if (view.getUint16(14, false) !== QUERY_COUNT)
        throw new Error(`${name} must contain 32 queries`);
    const parameterId = proofDigest(hex(payload.slice(16, 80)), `${name}.parameterId`, false);
    if (!digestEqual(parameterId, expectedParameterId))
        throw new Error(`${name} parameter ID mismatch`);
    if (view.getUint16(80, false) !== 64)
        throw new Error(`${name} public value count must be 64`);
    for (let index = 0; index < 64; index++) {
        const limb = view.getUint32(82 + index * 4, false);
        if (limb >= BABY_BEAR_MODULUS)
            throw new Error(`${name} public value ${index} is not canonical`);
        if (limb !== expectedPublicValues[index])
            throw new Error(`${name} statement public values mismatch`);
    }
    const globalDigest = payload.slice(globalDigestOffset, globalDataOffset);
    const globalData = payload.slice(globalDataOffset, checkpointOffset);
    if (!sameBytes(keccak_256(globalData), globalDigest)) {
        throw new Error(`${name} global data digest mismatch`);
    }
    const checkpointDigest = payload.slice(checkpointOffset, checkpointOffset + 32);
    const checkpointGlobalDigest = payload.slice(checkpointOffset + 32, checkpointOffset + 64);
    if (!sameBytes(checkpointGlobalDigest, globalDigest)) {
        throw new Error(`${name} checkpoint does not bind global data`);
    }
    if (view.getUint16(checkpointOffset + 320, false) !== QUERY_COUNT) {
        throw new Error(`${name} checkpoint must contain 32 queries`);
    }
    const queryIndices = new Uint32Array(QUERY_COUNT);
    for (let index = 0; index < QUERY_COUNT; index++) {
        const queryIndex = view.getUint32(checkpointOffset + 322 + index * 4, false);
        if (queryIndex >= 1 << 13)
            throw new Error(`${name} checkpoint query index is out of range`);
        queryIndices[index] = queryIndex;
    }
    const uniqueCount = view.getUint16(checkpointOffset + 450, false);
    if (uniqueCount > QUERY_COUNT)
        throw new Error(`${name} checkpoint unique-query count is invalid`);
    const halfOffset = checkpointOffset + CHECKPOINT_FIXED_BYTES + uniqueCount * 4;
    if (payload.length < halfOffset + 4 + HALF_QUERY_COUNT * 4 + 4)
        throw new Error(`${name} is truncated`);
    const expectedUnique = [...new Set(queryIndices)].sort((left, right) => left - right);
    if (uniqueCount !== expectedUnique.length)
        throw new Error(`${name} checkpoint unique queries are invalid`);
    for (let index = 0; index < uniqueCount; index++) {
        if (view.getUint32(checkpointOffset + CHECKPOINT_FIXED_BYTES + index * 4, false) !== expectedUnique[index]) {
            throw new Error(`${name} checkpoint unique queries are invalid`);
        }
    }
    const expectedHalfStart = expectedKind === "A" ? 0 : HALF_QUERY_COUNT;
    if (view.getUint16(halfOffset, false) !== expectedHalfStart
        || view.getUint16(halfOffset + 2, false) !== HALF_QUERY_COUNT) {
        throw new Error(`${name} must contain the ${expectedKind === "A" ? "first" : "second"} 16 queries`);
    }
    for (let index = 0; index < HALF_QUERY_COUNT; index++) {
        if (view.getUint32(halfOffset + 4 + index * 4, false)
            !== queryIndices[expectedHalfStart + index]) {
            throw new Error(`${name} half-query indices do not match its checkpoint`);
        }
    }
    const checkpointPayload = payload.slice(checkpointOffset + 32, halfOffset);
    const paddedCheckpointLabel = new Uint8Array(32);
    paddedCheckpointLabel.set(CHECKPOINT_LABEL);
    const expectedCheckpointDigest = keccak_256(concat(paddedCheckpointLabel, bytesFromHex(expectedStatementKey, 32), keccak_256(checkpointPayload)));
    if (!sameBytes(checkpointDigest, expectedCheckpointDigest)) {
        throw new Error(`${name} checkpoint digest mismatch`);
    }
    if (expectedKind === "A")
        return { payload, globalDigest, checkpointDigest };
    const proofId = payload.slice(PROOF_COMMON_HEADER_BYTES, PROOF_COMMON_HEADER_BYTES + 32);
    if (proofId.every((byte) => byte === 0))
        throw new Error(`${name} proof ID cannot be zero`);
    return { payload, globalDigest, checkpointDigest, proofId };
}
function validateRequest(input, policy, nowSeconds) {
    const request = asRecord(input, "request");
    requireExactKeys(request, [
        "version", "chainId", "pool", "registry", "scope", "parameterId", "root", "nullifierHash",
        "recipient", "relayer", "fee", "deadline", "statementId", "publicValues", "proof",
    ], "request");
    if (request.version !== RELAYER_REQUEST_VERSION)
        throw new Error("protocol version 3 is required");
    const chainId = unsignedDecimal(request.chainId, "chainId", UINT64_LIMIT);
    if (chainId !== policy.chainId)
        throw new Error("request chain does not match connected chain");
    const requestPool = address(request.pool, "pool");
    const policyPool = address(policy.pool, "configured pool");
    if (!sameBytes(requestPool.bytes, policyPool.bytes))
        throw new Error("request pool does not match configured pool");
    const requestRegistry = address(request.registry, "registry");
    const policyRegistry = address(policy.registry, "configured registry");
    if (!sameBytes(requestRegistry.bytes, policyRegistry.bytes))
        throw new Error("request registry does not match pool registry");
    const requestScope = canonicalDigest(request.scope, "scope");
    const policyScope = canonicalDigest(policy.scope, "configured scope");
    if (!digestEqual(requestScope, policyScope))
        throw new Error("request scope does not match pool scope");
    const parameterId = proofDigest(request.parameterId, "parameterId", false);
    const policyParameterId = proofDigest(policy.parameterId, "configured parameterId", false);
    if (!digestEqual(parameterId, policyParameterId))
        throw new Error("request parameter ID does not match pool parameter ID");
    const root = canonicalDigest(request.root, "root");
    const nullifierHash = canonicalDigest(request.nullifierHash, "nullifierHash");
    const parsedRecipient = address(request.recipient, "recipient");
    const parsedRelayer = address(request.relayer, "relayer");
    const configuredRelayer = address(policy.relayer, "configured relayer");
    if (!sameBytes(parsedRelayer.bytes, configuredRelayer.bytes)) {
        throw new Error("request relayer does not match configured relayer");
    }
    if (sameBytes(parsedRecipient.bytes, parsedRelayer.bytes)) {
        throw new Error("recipient must be independent from relayer");
    }
    const fee = unsignedDecimal(request.fee, "fee", UINT256_LIMIT);
    if (policy.denomination <= 0n || policy.denomination >= UINT256_LIMIT)
        throw new Error("invalid pool denomination");
    if (fee > policy.denomination)
        throw new Error("fee exceeds pool denomination");
    const deadline = unsignedDecimal(request.deadline, "deadline", UINT64_LIMIT);
    if (deadline <= nowSeconds)
        throw new Error("request deadline has expired");
    const statement = {
        scope: requestScope,
        root,
        nullifierHash,
        payoutDigest: payoutDigest(parsedRecipient.bytes, parsedRelayer.bytes, fee),
    };
    const expectedStatementId = statementHash(statement);
    const suppliedStatementId = canonicalDigest(request.statementId, "statementId");
    if (!digestEqual(suppliedStatementId, expectedStatementId))
        throw new Error("statement ID mismatch");
    const suppliedPublicValues = parsePublicValues(request.publicValues);
    const expectedPublicValues = publicValues(statement);
    for (let index = 0; index < expectedPublicValues.length; index++) {
        if (suppliedPublicValues[index] !== expectedPublicValues[index]) {
            throw new Error("public values do not match withdrawal statement");
        }
    }
    const proof = asRecord(request.proof, "proof");
    requireExactKeys(proof, ["partA", "partB"], "proof");
    const statementKey = deriveStatementKey(parameterId, expectedPublicValues);
    const partA = parseProofPart(proof.partA, "A", parameterId, expectedPublicValues, statementKey);
    const coreProofId = bytesFromHex(deriveCoreProofId(statementKey, partA.payload), 32);
    const partB = parseProofPart(proof.partB, "B", parameterId, expectedPublicValues, statementKey);
    if (partB.proofId === undefined || !sameBytes(partB.proofId, coreProofId)) {
        throw new Error("proof.partB core proof ID does not bind proof.partA");
    }
    if (!sameBytes(partA.globalDigest, partB.globalDigest)) {
        throw new Error("proof parts have mismatched global data digest");
    }
    if (!sameBytes(partA.checkpointDigest, partB.checkpointDigest)) {
        throw new Error("proof parts have mismatched checkpoint digests");
    }
    return Object.freeze({
        pool: requestPool.hex,
        registry: requestRegistry.hex,
        parameterId,
        root,
        nullifierHash,
        recipient: parsedRecipient.bytes,
        relayer: parsedRelayer.bytes,
        relayerHex: parsedRelayer.hex,
        fee,
        deadline,
        publicValues: expectedPublicValues,
        statementKey,
        proofPartA: partA.payload,
        proofPartB: partB.payload,
        verificationId: bytesFromHex(deriveVerificationId(hex(coreProofId), requestPool.hex), 32),
    });
}
function encodeWithdrawalFields(request) {
    return concat(digestBytes(request.root), digestBytes(request.nullifierHash), abiAddress(request.recipient), abiAddress(request.relayer), uintWord(request.fee));
}
function encodeBeginWithdrawal(request) {
    return concat(functionSelector("beginWithdrawal(((bytes32,bytes32),(bytes32,bytes32),address,address,uint256),bytes)"), encodeWithdrawalFields(request), uintWord(8n * 32n), abiBytes(request.proofPartA));
}
function encodeWithdrawal(request, verificationId) {
    return concat(functionSelector("withdraw(((bytes32,bytes32),(bytes32,bytes32),address,address,uint256),bytes32,bytes)"), encodeWithdrawalFields(request), verificationId, uintWord(9n * 32n), abiBytes(request.proofPartB));
}
function verificationIdFromReceipt(receipt, request) {
    if (!(receipt.status === 1 || receipt.status === "0x1" || receipt.status === "0x01")) {
        throw new Error("part A transaction did not succeed");
    }
    if (receipt.to === null || address(receipt.to, "receipt.to").hex !== request.pool) {
        throw new Error("part A receipt is not from the configured pool transaction");
    }
    const matchingLogs = receipt.logs.filter((log) => {
        if (address(log.address, "receipt log address").hex !== request.registry)
            return false;
        return log.topics[0]?.toLowerCase() === VERIFICATION_STARTED_TOPIC.toLowerCase();
    });
    if (matchingLogs.length !== 1)
        throw new Error("part A receipt must contain exactly one VerificationStarted event");
    const topics = matchingLogs[0].topics;
    if (topics.length !== 4)
        throw new Error("malformed VerificationStarted event");
    const verificationId = bytesFromHex(topics[1], 32);
    if (!sameBytes(verificationId, request.verificationId)) {
        throw new Error("VerificationStarted verification ID does not match proof and consumer");
    }
    if (verificationId.every((byte) => byte === 0))
        throw new Error("verification ID cannot be zero");
    const consumerWord = bytesFromHex(topics[2], 32);
    if (!consumerWord.slice(0, 12).every((byte) => byte === 0))
        throw new Error("event consumer is not canonical");
    if (!sameBytes(consumerWord.slice(12), bytesFromHex(request.pool, 20))) {
        throw new Error("VerificationStarted consumer does not match pool");
    }
    if (hex(bytesFromHex(topics[3], 32)) !== request.statementKey) {
        throw new Error("VerificationStarted statement key mismatch");
    }
    return verificationId;
}
/**
 * Stateful two-transaction withdrawal builder. Part B cannot be produced until a successful,
 * statement-bound part A receipt has been supplied, and no third transaction can be produced.
 */
export class WithdrawalSubmission {
    #request;
    #stage = 0;
    constructor(request) {
        this.#request = request;
    }
    static create(input, policy, nowSeconds = BigInt(Math.floor(Date.now() / 1000))) {
        return new WithdrawalSubmission(validateRequest(input, policy, nowSeconds));
    }
    partA() {
        if (this.#stage !== 0)
            throw new Error("part A must be the first and only first-phase transaction");
        this.#stage = 1;
        return Object.freeze({
            phase: "A",
            order: 1,
            from: this.#request.relayerHex,
            to: this.#request.pool,
            data: hex(encodeBeginWithdrawal(this.#request)),
        });
    }
    partB(receipt, nowSeconds = BigInt(Math.floor(Date.now() / 1000))) {
        if (this.#stage !== 1)
            throw new Error("part B requires part A to be submitted first");
        if (this.#request.deadline <= nowSeconds)
            throw new Error("request deadline expired before part B");
        const verificationId = verificationIdFromReceipt(receipt, this.#request);
        this.#stage = 2;
        return Object.freeze({
            phase: "B",
            order: 2,
            from: this.#request.relayerHex,
            to: this.#request.pool,
            data: hex(encodeWithdrawal(this.#request, verificationId)),
        });
    }
}
let rpcId = 0;
async function rpc(rpcUrl, method, params) {
    const response = await fetch(rpcUrl, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: ++rpcId, method, params }),
    });
    if (!response.ok)
        throw new Error(`RPC HTTP ${response.status}`);
    const envelope = await response.json();
    if (envelope.error)
        throw new Error(envelope.error.message);
    if (envelope.result === undefined)
        throw new Error(`RPC ${method} returned no result`);
    return envelope.result;
}
async function ethCall(rpcUrl, to, signature) {
    const result = await rpc(rpcUrl, "eth_call", [{ to, data: hex(functionSelector(signature)) }, "latest"]);
    return bytesFromHex(result);
}
async function waitForReceipt(rpcUrl, transactionHash) {
    for (;;) {
        const receipt = await rpc(rpcUrl, "eth_getTransactionReceipt", [transactionHash]);
        if (receipt !== null)
            return receipt;
        const { promise, resolve } = Promise.withResolvers();
        setTimeout(resolve, 1_000);
        await promise;
    }
}
function requestAddress(input, field) {
    const request = asRecord(input, "request");
    return address(request[field], field).hex;
}
export async function runRelayerCli(argv = process.argv.slice(2), environment = process.env) {
    const [requestPath] = argv;
    const rpcUrl = environment.RPC_URL;
    const relayer = environment.RELAYER_FROM;
    if (!requestPath || !rpcUrl || !relayer) {
        throw new Error("usage: RPC_URL=... RELAYER_FROM=0x... pqtc-relayer request.json");
    }
    const input = JSON.parse(await readFile(requestPath, "utf8"));
    const pool = requestAddress(input, "pool");
    const [chainHex, scopeResult, parameterResult, denominationResult, registryResult] = await Promise.all([
        rpc(rpcUrl, "eth_chainId", []),
        ethCall(rpcUrl, pool, "scope()"),
        ethCall(rpcUrl, pool, "parameterId()"),
        ethCall(rpcUrl, pool, "denomination()"),
        ethCall(rpcUrl, pool, "verificationRegistry()"),
    ]);
    if (scopeResult.length !== 64 || parameterResult.length !== 64 || denominationResult.length !== 32 || registryResult.length !== 32) {
        throw new Error("pool returned malformed protocol metadata");
    }
    if (!registryResult.slice(0, 12).every((byte) => byte === 0))
        throw new Error("pool returned noncanonical registry address");
    const submission = WithdrawalSubmission.create(input, {
        chainId: BigInt(chainHex),
        pool,
        registry: hex(registryResult.slice(12)),
        scope: hex(scopeResult),
        parameterId: hex(parameterResult),
        denomination: BigInt(hex(denominationResult)),
        relayer,
    });
    const partA = submission.partA();
    const partAHash = await rpc(rpcUrl, "eth_sendTransaction", [{ from: partA.from, to: partA.to, data: partA.data }]);
    const receipt = await waitForReceipt(rpcUrl, partAHash);
    const partB = submission.partB(receipt);
    const partBHash = await rpc(rpcUrl, "eth_sendTransaction", [{ from: partB.from, to: partB.to, data: partB.data }]);
    process.stdout.write(`${JSON.stringify({ partA: partAHash, partB: partBHash })}\n`);
}
const isMain = process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain)
    await runRelayerCli();
