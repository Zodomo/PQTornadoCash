import assert from "node:assert/strict";
import test from "node:test";
import { keccak_256 } from "@noble/hashes/sha3.js";

import {
  BABY_BEAR_MODULUS,
  bytesFromHex,
  digestBytes,
  digestFromBytes,
  hex,
  payoutDigest,
  publicValues,
  statementHash,
} from "../dist/index.js";
import {
  WithdrawalSubmission,
  deriveCoreProofId,
  deriveStatementKey,
  deriveVerificationId,
  type RelayerPolicy,
  type TransactionReceipt,
  type WithdrawalRequestV3,
} from "../dist/relayer.js";

const encoder = new TextEncoder();
const POOL = "0x1111111111111111111111111111111111111111";
const REGISTRY = "0x2222222222222222222222222222222222222222";
const RECIPIENT = "0x3333333333333333333333333333333333333333";
const RELAYER = "0x4444444444444444444444444444444444444444";
const VERIFICATION_STARTED_TOPIC = hex(keccak_256(encoder.encode(
  "VerificationStarted(bytes32,address,bytes32)",
)));

function digest(seed: number): `0x${string}` {
  const bytes = new Uint8Array(64);
  const view = new DataView(bytes.buffer);
  for (let index = 0; index < 16; index++) view.setUint32(index * 4, seed + index, false);
  return hex(bytes);
}
function selector(signature: string): `0x${string}` {
  return hex(keccak_256(encoder.encode(signature)).slice(0, 4));
}
function proofPart(
  kind: "A" | "B",
  parameterId: string,
  values: Uint32Array,
  statementKey: string,
  coreProofId?: string,
): `0x${string}` {
  const commonLength = 338;
  const globalLength = 9_208;
  const queryCount = 32;
  const halfCount = 16;
  const checkpointLength = 452 + queryCount * 4;
  const proofIdLength = kind === "B" ? 32 : 0;
  const bytes = new Uint8Array(
    commonLength + proofIdLength + 32 + globalLength + checkpointLength + 4 + halfCount * 4 + 1 + 4,
  );
  const view = new DataView(bytes.buffer);
  bytes.set(encoder.encode(kind === "A" ? "PQTCPA03" : "PQTCPB03"));
  view.setUint16(8, 3, false);
  view.setUint8(10, 3);
  view.setUint8(11, 9);
  view.setUint8(12, 9);
  view.setUint8(13, 4);
  view.setUint16(14, queryCount, false);
  bytes.set(bytesFromHex(parameterId, 64), 16);
  view.setUint16(80, 64, false);
  for (let index = 0; index < values.length; index++) view.setUint32(82 + index * 4, values[index]!, false);

  if (kind === "B") bytes.set(bytesFromHex(coreProofId!, 32), commonLength);
  const globalDigestOffset = commonLength + proofIdLength;
  const globalDataOffset = globalDigestOffset + 32;
  const globalData = new Uint8Array(globalLength);
  for (let index = 0; index < globalData.length; index++) globalData[index] = index & 0xff;
  const globalDigest = keccak_256(globalData);
  bytes.set(globalDigest, globalDigestOffset);
  bytes.set(globalData, globalDataOffset);

  const checkpointOffset = globalDataOffset + globalLength;
  bytes.set(globalDigest, checkpointOffset + 32);
  view.setUint16(checkpointOffset + 320, queryCount, false);
  for (let index = 0; index < queryCount; index++) {
    view.setUint32(checkpointOffset + 322 + index * 4, index, false);
  }
  view.setUint16(checkpointOffset + 450, queryCount, false);
  for (let index = 0; index < queryCount; index++) {
    view.setUint32(checkpointOffset + 452 + index * 4, index, false);
  }
  const checkpointEnd = checkpointOffset + checkpointLength;
  const checkpointLabel = new Uint8Array(32);
  checkpointLabel.set(encoder.encode("PQTC.V3.CHECKPOINT"));
  bytes.set(
    keccak_256(Buffer.concat([
      checkpointLabel,
      bytesFromHex(statementKey, 32),
      keccak_256(bytes.slice(checkpointOffset + 32, checkpointEnd)),
    ])),
    checkpointOffset,
  );

  view.setUint16(checkpointEnd, kind === "A" ? 0 : halfCount, false);
  view.setUint16(checkpointEnd + 2, halfCount, false);
  for (let index = 0; index < halfCount; index++) {
    view.setUint32(checkpointEnd + 4 + index * 4, (kind === "A" ? 0 : halfCount) + index, false);
  }
  bytes.set(
    bytesFromHex(kind === "A" ? "0x50414533" : "0x50424533"),
    bytes.length - 4,
  );
  return hex(bytes);
}

function makeFixture(): {
  request: WithdrawalRequestV3;
  policy: RelayerPolicy;
  statementKey: `0x${string}`;
  verificationId: `0x${string}`;
} {
  const scope = digest(10);
  const parameterId = `0x${"ff".repeat(64)}`;
  const root = digest(50);
  const nullifierHash = digest(70);
  const statement = {
    scope: digestFromBytes(bytesFromHex(scope, 64)),
    root: digestFromBytes(bytesFromHex(root, 64)),
    nullifierHash: digestFromBytes(bytesFromHex(nullifierHash, 64)),
    payoutDigest: payoutDigest(bytesFromHex(RECIPIENT, 20), bytesFromHex(RELAYER, 20), 7n),
  };
  const statementId = hex(digestBytes(statementHash(statement)));
  const values = publicValues(statement);
  const statementKey = deriveStatementKey(digestFromBytes(bytesFromHex(parameterId, 64)), values);
  const partA = proofPart("A", parameterId, values, statementKey);
  const coreProofId = deriveCoreProofId(statementKey, bytesFromHex(partA));
  const verificationId = deriveVerificationId(coreProofId, POOL);
  return {
    request: {
      version: 3,
      chainId: "11155111",
      pool: POOL,
      registry: REGISTRY,
      scope,
      parameterId,
      root,
      nullifierHash,
      recipient: RECIPIENT,
      relayer: RELAYER,
      fee: "7",
      deadline: "2000",
      statementId,
      publicValues: [...values],
      proof: { partA, partB: proofPart("B", parameterId, values, statementKey, coreProofId) },
    },
    policy: {
      chainId: 11_155_111n,
      pool: POOL,
      registry: REGISTRY,
      scope,
      parameterId,
      denomination: 100n,
      relayer: RELAYER,
    },
    statementKey,
    verificationId,
  };
}

function receipt(statementKey: string, verificationId: string, overrides: Partial<TransactionReceipt> = {}): TransactionReceipt {
  return {
    status: "0x1",
    to: POOL,
    logs: [{
      address: REGISTRY,
      topics: [
        VERIFICATION_STARTED_TOPIC,
        verificationId,
        `0x${"00".repeat(12)}${POOL.slice(2)}`,
        statementKey,
      ],
    }],
    ...overrides,
  };
}

test("withdrawal submission exposes exactly two ordered transactions", () => {
  const { request, policy, statementKey, verificationId } = makeFixture();
  const submission = WithdrawalSubmission.create(request, policy, 1_000n);

  assert.throws(() => submission.partB(receipt(statementKey, verificationId), 1_000n), /requires part A/);
  const partA = submission.partA();
  assert.deepEqual({ phase: partA.phase, order: partA.order, to: partA.to }, {
    phase: "A", order: 1, to: POOL,
  });
  assert.equal(
    partA.data.slice(0, 10),
    selector("beginWithdrawal(((bytes32,bytes32),(bytes32,bytes32),address,address,uint256),bytes)"),
  );
  assert.throws(() => submission.partA(), /first-phase/);

  const partB = submission.partB(receipt(statementKey, verificationId), 1_000n);
  assert.deepEqual({ phase: partB.phase, order: partB.order, to: partB.to }, {
    phase: "B", order: 2, to: POOL,
  });
  assert.equal(
    partB.data.slice(0, 10),
    selector("withdraw(((bytes32,bytes32),(bytes32,bytes32),address,address,uint256),bytes32,bytes)"),
  );
  assert.ok(partB.data.includes(verificationId.slice(2)));
  assert.throws(() => submission.partB(receipt(statementKey, verificationId), 1_000n), /requires part A/);
});

test("swapped proof parts are rejected before calldata is returned", () => {
  const { request, policy } = makeFixture();
  const swapped = structuredClone(request);
  [swapped.proof.partA, swapped.proof.partB] = [swapped.proof.partB, swapped.proof.partA];
  assert.throws(() => WithdrawalSubmission.create(swapped, policy, 1_000n), /swapped/);
});

test("each proof part authenticates its exact 9208-byte globals and 16-query half", () => {
  const { request, policy } = makeFixture();
  const badGlobal = structuredClone(request);
  const partA = bytesFromHex(badGlobal.proof.partA);
  partA[338 + 32 + 9_207] ^= 1;
  badGlobal.proof.partA = hex(partA);
  assert.throws(() => WithdrawalSubmission.create(badGlobal, policy, 1_000n), /global data digest mismatch/);

  const badQueryCount = structuredClone(request);
  const badHeader = bytesFromHex(badQueryCount.proof.partA);
  new DataView(badHeader.buffer).setUint16(14, 48, false);
  badQueryCount.proof.partA = hex(badHeader);
  assert.throws(() => WithdrawalSubmission.create(badQueryCount, policy, 1_000n), /32 queries/);

  const badHalf = structuredClone(request);
  const badHalfBytes = bytesFromHex(badHalf.proof.partB);
  const partBHalfOffset = 338 + 32 + 32 + 9_208 + 452 + 32 * 4;
  new DataView(badHalfBytes.buffer).setUint16(partBHalfOffset, 0, false);
  badHalf.proof.partB = hex(badHalfBytes);
  assert.throws(() => WithdrawalSubmission.create(badHalf, policy, 1_000n), /second 16 queries/);
});

test("statement and receipt bindings are checked before part B calldata", () => {
  const { request, policy, statementKey, verificationId } = makeFixture();
  const mismatched = structuredClone(request);
  const mismatchedPartB = bytesFromHex(mismatched.proof.partB);
  const view = new DataView(mismatchedPartB.buffer);
  view.setUint32(82, view.getUint32(82, false) + 1, false);
  mismatched.proof.partB = hex(mismatchedPartB);
  assert.throws(() => WithdrawalSubmission.create(mismatched, policy, 1_000n), /statement public values mismatch/);

  const wrongParameter = structuredClone(request);
  const parameterPartB = bytesFromHex(wrongParameter.proof.partB);
  parameterPartB[16] ^= 1;
  wrongParameter.proof.partB = hex(parameterPartB);
  assert.throws(() => WithdrawalSubmission.create(wrongParameter, policy, 1_000n), /parameter ID mismatch/);

  const submission = WithdrawalSubmission.create(request, policy, 1_000n);
  submission.partA();
  assert.throws(
    () => submission.partB(receipt(statementKey, `0x${"99".repeat(32)}`), 1_000n),
    /verification ID does not match/,
  );
  assert.throws(
    () => submission.partB(receipt(`0x${"99".repeat(32)}`, verificationId), 1_000n),
    /statement key mismatch/,
  );
  assert.doesNotThrow(() => submission.partB(receipt(statementKey, verificationId), 1_000n));
});

test("part B requires the successful pool receipt and exact registry event", () => {
  const { request, policy, statementKey, verificationId } = makeFixture();
  const malformed: Array<[TransactionReceipt, RegExp]> = [
    [receipt(statementKey, verificationId, { status: "0x0" }), /did not succeed/],
    [receipt(statementKey, verificationId, { to: RECIPIENT }), /configured pool transaction/],
    [receipt(statementKey, verificationId, {
      logs: [{
        address: POOL,
        topics: [
          VERIFICATION_STARTED_TOPIC,
          verificationId,
          `0x${"00".repeat(12)}${POOL.slice(2)}`,
          statementKey,
        ],
      }],
    }), /exactly one VerificationStarted/],
    [receipt(statementKey, verificationId, {
      logs: [{
        address: REGISTRY,
        topics: [
          VERIFICATION_STARTED_TOPIC,
          verificationId,
          `0x${"00".repeat(12)}${RELAYER.slice(2)}`,
          statementKey,
        ],
      }],
    }), /consumer does not match pool/],
  ];
  for (const [candidate, expected] of malformed) {
    const submission = WithdrawalSubmission.create(request, policy, 1_000n);
    submission.partA();
    assert.throws(() => submission.partB(candidate, 1_000n), expected);
  }
});

test("noncanonical digest and public-value limbs are rejected", () => {
  const { request, policy } = makeFixture();
  const noncanonicalDigest = structuredClone(request);
  const bytes = bytesFromHex(noncanonicalDigest.root, 64);
  new DataView(bytes.buffer).setUint32(7 * 4, BABY_BEAR_MODULUS, false);
  noncanonicalDigest.root = hex(bytes);
  assert.throws(() => WithdrawalSubmission.create(noncanonicalDigest, policy, 1_000n), /limb 7 is not canonical/);

  const noncanonicalValues = structuredClone(request);
  noncanonicalValues.publicValues[12] = BABY_BEAR_MODULUS;
  assert.throws(() => WithdrawalSubmission.create(noncanonicalValues, policy, 1_000n), /publicValues\[12\] is not canonical/);

  const noncanonicalProof = structuredClone(request);
  const partA = bytesFromHex(noncanonicalProof.proof.partA);
  new DataView(partA.buffer).setUint32(82 + 12 * 4, BABY_BEAR_MODULUS, false);
  noncanonicalProof.proof.partA = hex(partA);
  assert.throws(() => WithdrawalSubmission.create(noncanonicalProof, policy, 1_000n), /public value 12 is not canonical/);
});

test("v2 requests, v2 proofs, and staged transaction fields are rejected", () => {
  const { request, policy } = makeFixture();
  const v2 = { ...request, version: 2 };
  assert.throws(() => WithdrawalSubmission.create(v2, policy, 1_000n), /protocol version 3/);
  const v2Proof = structuredClone(request);
  const partA = bytesFromHex(v2Proof.proof.partA);
  partA.set(encoder.encode("PQTCPA02"));
  new DataView(partA.buffer).setUint16(8, 2, false);
  v2Proof.proof.partA = hex(partA);
  assert.throws(() => WithdrawalSubmission.create(v2Proof, policy, 1_000n), /magic|proof version 3/);
  const staged = { ...request, transactions: [{ to: REGISTRY, data: "0x" }] };
  assert.throws(() => WithdrawalSubmission.create(staged, policy, 1_000n), /unsupported field transactions/);
});

test("chain, pool, scope, payout, fee, relayer, and deadline policy checks remain strict", () => {
  const { request, policy } = makeFixture();
  const cases: Array<[string, WithdrawalRequestV3, RegExp]> = [
    ["chain", { ...request, chainId: "1" }, /connected chain/],
    ["pool", { ...request, pool: RECIPIENT }, /configured pool/],
    ["scope", { ...request, scope: digest(101) }, /pool scope/],
    ["recipient", { ...request, recipient: RELAYER }, /independent/],
    ["relayer", { ...request, relayer: RECIPIENT }, /configured relayer/],
    ["fee", { ...request, fee: "101" }, /fee exceeds/],
    ["deadline", { ...request, deadline: "1000" }, /expired/],
  ];
  for (const [name, candidate, expected] of cases) {
    assert.throws(() => WithdrawalSubmission.create(candidate, policy, 1_000n), expected, name);
  }
});
