import assert from "node:assert/strict";
import test from "node:test";
import { keccak_256 } from "@noble/hashes/sha3.js";

import {
  BABY_BEAR_MODULUS,
  MerkleTree,
  NoteSecretTracker,
  commitment,
  decodeCompactProof,
  digestBytes,
  digestElements,
  digestEqual,
  digestFromBytes,
  domains,
  emptyLeaf,
  encodeCompactProof,
  encodeDepositCalldata,
  encodeNote,
  hex,
  k512,
  merkleNode,
  newNote,
  nullifierHash,
  p2bb512,
  parseNote,
  payoutDigest,
  poseidon2BabyBear16,
  publicValues,
  rootFromPath,
  secretBytes,
  secretFromBytes,
  scope,
  statementHash,
} from "../dist/index.js";

test("matches the pinned Plonky3 BabyBear width-16 permutation", () => {
  const input = Array.from({ length: 16 }, (_, index) => index);
  const expected = [
    1906786279, 1737026427, 1959749225, 700325316, 1638050605, 1021608788, 1726691001,
    1761127344, 1552405120, 417318995, 36799261, 1215172152, 614923223, 1300746575,
    957311597, 304856115,
  ];
  assert.deepEqual([...poseidon2BabyBear16(input)], expected);
  assert.equal(
    hex(digestBytes(p2bb512(domains.SCOPE, 32, 0, input))),
    "0x192285c83ad82d235f4020c4185fb99a5d7a4574217a7fa5097c082c4c905cfd69df098f455618e612d7819f26e68e4d5ff4842c4d5177ae479caee05752c4bd",
  );
});

test("P2BB512 digests are canonical and bind domain, byte length, and auxiliary level", () => {
  const payload = [0x0102, 0x0300];
  const digest = p2bb512(domains.NOTE, 3, 0, payload);
  assert.equal(digestBytes(digest).length, 64);
  assert.deepEqual([...digestElements(digest)], [...digestElements(digestFromBytes(digestBytes(digest)))]);
  for (const element of digestElements(digest)) assert.ok(element < BABY_BEAR_MODULUS);

  assert.equal(digestEqual(digest, p2bb512(domains.NULLIFIER, 3, 0, payload)), false);
  assert.equal(digestEqual(digest, p2bb512(domains.NOTE, 4, 0, payload)), false);
  assert.equal(digestEqual(digest, p2bb512(domains.NOTE, 3, 1, payload)), false);

  const noncanonicalBytes = new Uint8Array(64);
  new DataView(noncanonicalBytes.buffer).setUint32(0, BABY_BEAR_MODULUS, false);
  assert.throws(() => emptyLeaf(digestFromBytes(noncanonicalBytes)), /not canonical/);
});

test("application helpers use canonical digest elements and bind Merkle levels", () => {
  const parameterId = {
    left: new Uint8Array(32).fill(0xa5),
    right: new Uint8Array(32).fill(0x5a),
  };
  const poolScope = scope({
    chainId: 11_155_111n,
    pool: new Uint8Array(20).fill(1),
    denomination: 1_000_000_000_000_000_000n,
    parameterId,
  });
  const noteSecret = new Uint32Array(8).fill(2);
  const noteTrapdoor = new Uint32Array(8).fill(3);
  const noteCommitment = commitment(poolScope, noteSecret, noteTrapdoor);
  const nullifier = nullifierHash(poolScope, noteSecret);
  const zero = emptyLeaf(poolScope);
  assert.equal(digestEqual(merkleNode(0, noteCommitment, zero), merkleNode(1, noteCommitment, zero)), false);

  const tree = new MerkleTree(poolScope);
  const inserted = tree.insert(noteCommitment);
  assert.ok(digestEqual(rootFromPath(noteCommitment, tree.path(inserted.leafIndex)), inserted.root));

  const payout = payoutDigest(new Uint8Array(20).fill(4), new Uint8Array(20).fill(5), 7n);
  const statement = { scope: poolScope, root: inserted.root, nullifierHash: nullifier, payoutDigest: payout };
  assert.equal(publicValues(statement).length, 64);
  assert.equal(digestBytes(statementHash(statement)).length, 64);
  for (const value of publicValues(statement)) assert.ok(value < BABY_BEAR_MODULUS);

  const previousVersion = scope({
    chainId: 11_155_111n,
    pool: new Uint8Array(20).fill(1),
    denomination: 1_000_000_000_000_000_000n,
    protocolVersion: 2,
    parameterId,
  });
  assert.equal(digestEqual(poolScope, previousVersion), false);
});

test("v3 application hashes match the Rust canonical-secret vector", () => {
  const parameterId = k512(domains.PARAMETER_MANIFEST, new TextEncoder().encode("manifest"));
  const poolScope = scope({
    chainId: 11_155_111n,
    pool: new Uint8Array(20).fill(1),
    denomination: BigInt(`0x${"02".repeat(32)}`),
    parameterId,
  });
  const nullifierSecret = Uint32Array.of(3, 5, 7, 11, 13, 17, 19, 23);
  const trapdoor = Uint32Array.of(29, 31, 37, 41, 43, 47, 53, 59);
  assert.equal(
    hex(digestBytes(poolScope)),
    "0x29d774fa067d5844644966e1326483b24085e8fe771fdf570d64b61815b83cdf31d6b62414ead4750956548b6643d0831fdba8e822e0ada718ffd4d3470a56c7",
  );
  assert.equal(
    hex(digestBytes(commitment(poolScope, nullifierSecret, trapdoor))),
    "0x174026330a3b3def58a2547403d04234035843a84b7814a330ff65e4049592cc69da09314cc70f0d6ead8d1d38a5dd2f45f5e9741b7e063f24acd369233a1979",
  );
  assert.equal(
    hex(digestBytes(nullifierHash(poolScope, nullifierSecret))),
    "0x703e079c63caf3b65227079e3201df600319e2fb294395ae278a63183b0b8fe2078b9d397692e1e14e7952cd3f80d97301a420444d733f0b2fb440fc18deaba6",
  );
});

test("note codec v3 uses eight canonical BabyBear limbs and detects corruption", () => {
  const note = {
    chainId: 11_155_111n,
    pool: new Uint8Array(20).fill(1),
    parameterId: { left: new Uint8Array(32).fill(2), right: new Uint8Array(32).fill(3) },
    nullifierSecret: Uint32Array.of(0, 1, 0x01020304, BABY_BEAR_MODULUS - 1, 5, 6, 7, 8),
    trapdoor: Uint32Array.of(9, 10, 11, 12, 13, 14, 15, 16),
  };
  const encoded = encodeNote(note);
  assert.ok(encoded.startsWith("pqtc-note-v3:"));
  assert.deepEqual(parseNote(encoded), note);
  assert.deepEqual(secretFromBytes(secretBytes(note.nullifierSecret)), note.nullifierSecret);
  assert.equal(
    hex(secretBytes(Uint32Array.of(0x01020304, 0, 1, 2, 3, 4, 5, BABY_BEAR_MODULUS - 1))),
    "0x0102030400000000000000010000000200000003000000040000000578000000",
  );
  assert.deepEqual(
    secretFromBytes(secretBytes([0n, 1n, 2n, 3n, 4n, 5n, 6n, 7n])),
    Uint32Array.of(0, 1, 2, 3, 4, 5, 6, 7),
  );
  const raw = Buffer.from(encoded.slice("pqtc-note-v3:".length), "base64url");
  raw[100]! ^= 1;
  assert.throws(() => parseNote(`pqtc-note-v3:${raw.toString("base64url")}`), /checksum/);
  assert.throws(() => parseNote(encoded.replace("pqtc-note-v3:", "pqtc-note-v2:")), /prefix/);
  const noncanonicalRaw = Buffer.from(encoded.slice("pqtc-note-v3:".length), "base64url");
  new DataView(
    noncanonicalRaw.buffer,
    noncanonicalRaw.byteOffset,
    noncanonicalRaw.byteLength,
  ).setUint32(98, BABY_BEAR_MODULUS, false);
  noncanonicalRaw.set(
    keccak_256(Buffer.concat([Uint8Array.of(0, domains.NOTE), noncanonicalRaw.subarray(0, 162)])),
    162,
  );
  assert.throws(
    () => parseNote(`pqtc-note-v3:${noncanonicalRaw.toString("base64url")}`),
    /nullifierSecret limb 0 is not canonical/,
  );
  assert.throws(() => encodeNote({ ...note, nullifierSecret: new Uint32Array(32).fill(4) }), /8 limbs/);
  assert.throws(
    () => encodeNote({ ...note, trapdoor: [0, 1, 2, 3, 4, 5, 6, BABY_BEAR_MODULUS] }),
    /limb 7 is not canonical/,
  );
  const tracker = new NoteSecretTracker();
  tracker.register(note);
  assert.throws(() => tracker.register({ ...note, trapdoor: new Uint32Array(8).fill(9) }), /already used/);
});

test("new notes rejection-sample canonical secrets", () => {
  const parameterId = { left: new Uint8Array(32).fill(1), right: new Uint8Array(32).fill(2) };
  for (let index = 0; index < 64; index++) {
    const note = newNote(1n, new Uint8Array(20).fill(3), parameterId);
    assert.equal(note.nullifierSecret.length, 8);
    assert.equal(note.trapdoor.length, 8);
    for (let limb = 0; limb < 8; limb++) {
      assert.ok(Number(note.nullifierSecret[limb]) < BABY_BEAR_MODULUS);
      assert.ok(Number(note.trapdoor[limb]) < BABY_BEAR_MODULUS);
    }
  }
});

test("integer boundaries and proof-only Keccak branches remain binding", () => {
  const parameterId = { left: new Uint8Array(32).fill(1), right: new Uint8Array(32).fill(2) };
  assert.doesNotThrow(() => scope({ chainId: (1n << 64n) - 1n, pool: new Uint8Array(20), denomination: (1n << 256n) - 1n, parameterId }));
  assert.throws(() => scope({ chainId: 1n << 64n, pool: new Uint8Array(20), denomination: 0n, parameterId }), /does not fit/);
  const value = k512(domains.PROOF_LEAF, new Uint8Array());
  assert.notDeepEqual(value.left, value.right);
});

test("compact proof v3 envelope round-trips 64 canonical public values", () => {
  const proof = {
    parameterId: {
      left: new Uint8Array(32).fill(0x11),
      right: new Uint8Array(32).fill(0x22),
    },
    publicValues: new Uint32Array(64).fill(1234),
    starkPayload: Uint8Array.of(1, 2, 3, 4, 5),
  };
  const encoded = encodeCompactProof(proof);
  assert.equal(new TextDecoder().decode(encoded.slice(0, 8)), "PQTCSTK3");
  assert.deepEqual(decodeCompactProof(encoded), proof);
  assert.deepEqual(encodeCompactProof(decodeCompactProof(encoded)), encoded);
  for (let length = 0; length < encoded.length; length++) {
    assert.throws(() => decodeCompactProof(encoded.slice(0, length)));
  }
  const v2 = encoded.slice();
  v2.set(new TextEncoder().encode("PQTCSTK2"));
  new DataView(v2.buffer).setUint16(8, 2, false);
  assert.throws(() => decodeCompactProof(v2), /magic|version/);
  assert.throws(() => decodeCompactProof(new Uint8Array([...encoded, 0])), /trailing/);
  const noncanonical = { ...proof, publicValues: proof.publicValues.slice() };
  noncanonical.publicValues[0] = BABY_BEAR_MODULUS;
  assert.throws(() => encodeCompactProof(noncanonical), /not canonical/);
});

test("deposit calldata uses canonical tuple ABI", () => {
  const digest = digestFromBytes(new Uint8Array(64));
  const deposit = encodeDepositCalldata(digest);
  assert.equal(hex(deposit.slice(0, 4)), "0xdc39710f");
  assert.equal(deposit.length, 4 + 64);
});
