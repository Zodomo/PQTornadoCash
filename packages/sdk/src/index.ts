import { randomBytes } from "node:crypto";
import { keccak_256 } from "@noble/hashes/sha3.js";
import { coordinationDomains, domains } from "./domains.js";

export { coordinationDomains, domains };
export const TREE_DEPTH = 20;
export const PROTOCOL_VERSION = 3;
export const BABY_BEAR_MODULUS = 2_013_265_921;
export type Digest512 = Readonly<{ left: Uint8Array; right: Uint8Array }>;
export type Address = Uint8Array;

const NOTE_PREFIX = "pqtc-note-v3:";
const NOTE_LENGTH = 194;
const textEncoder = new TextEncoder();
const P = 2_013_265_921n;

const EXTERNAL_INITIAL = [
  [
    0x69cbb6afn, 0x46ad93f9n, 0x60a00f4en, 0x6b1297cdn, 0x23189afen, 0x732e7befn, 0x72c246den, 0x2c941900n,
    0x0557eeden, 0x1580496fn, 0x3a3ea77bn, 0x54f3f271n, 0x0f49b029n, 0x47872fe1n, 0x221e2e36n, 0x1ab7202en,
  ],
  [
    0x487779a6n, 0x3851c9d8n, 0x38dc17c0n, 0x209f8849n, 0x268dcee8n, 0x350c48dan, 0x5b9ad32en, 0x0523272bn,
    0x3f89055bn, 0x01e894b2n, 0x13ddedden, 0x1b2ef334n, 0x7507d8b4n, 0x6ceeb94en, 0x52eb6ba2n, 0x50642905n,
  ],
  [
    0x05453f3fn, 0x06349efcn, 0x6922787cn, 0x04bfff9cn, 0x768c714an, 0x3e9ff21an, 0x15737c9cn, 0x2229c807n,
    0x0d47f88cn, 0x097e0eccn, 0x27eadba0n, 0x2d7d29e4n, 0x3502aaa0n, 0x0f475fd7n, 0x29fbda49n, 0x018afffdn,
  ],
  [
    0x0315b618n, 0x6d4497d1n, 0x1b171d9en, 0x52861abdn, 0x2e5d0501n, 0x3ec8646cn, 0x6e5f250an, 0x148ae8e6n,
    0x17f5fa4an, 0x3e66d284n, 0x0051aa3bn, 0x483f7913n, 0x2cfe5f15n, 0x023427can, 0x2cc78315n, 0x1e36ea47n,
  ],
] as const;

const EXTERNAL_FINAL = [
  [
    0x7290a80dn, 0x6f7e5329n, 0x598ec8a8n, 0x76a859a0n, 0x6559e868n, 0x657b83afn, 0x13271d3fn, 0x1f876063n,
    0x0aeeae37n, 0x706e9ca6n, 0x46400ceen, 0x72a05c26n, 0x2c589c9en, 0x20bd37a7n, 0x6a2d3d10n, 0x20523767n,
  ],
  [
    0x5b8fe9c4n, 0x2aa501d6n, 0x1e01ac3en, 0x1448bc54n, 0x5ce5ad1cn, 0x4918a14dn, 0x2c46a83fn, 0x4fcf6876n,
    0x61d8d5c8n, 0x6ddf4ff9n, 0x11fda4d3n, 0x02933a8fn, 0x170eaf81n, 0x5a9c314fn, 0x49a12590n, 0x35ec52a1n,
  ],
  [
    0x58eb1611n, 0x5e481e65n, 0x367125c9n, 0x0eba33ban, 0x1fc28dedn, 0x066399adn, 0x0cbec0ean, 0x75fd1af0n,
    0x50f5bf4en, 0x643d5f41n, 0x6f4fe718n, 0x5b3cbbden, 0x1e3afb3en, 0x296fb027n, 0x45e1547bn, 0x4a8db2abn,
  ],
  [
    0x59986d19n, 0x30bcdfa3n, 0x1db63932n, 0x1d7c2824n, 0x53b33681n, 0x0673b747n, 0x038a98a3n, 0x2c5bce60n,
    0x351979cdn, 0x5008fb73n, 0x547bca78n, 0x711af481n, 0x3f93bf64n, 0x644d987bn, 0x3c8bcd87n, 0x608758b8n,
  ],
] as const;

const INTERNAL = [
  0x5a8053c0n, 0x693be639n, 0x3858867dn, 0x19334f6bn, 0x128f0fd8n, 0x4e2b1ccbn, 0x61210ce0n,
  0x3c318939n, 0x0b5b2f22n, 0x2edb11d5n, 0x213effdfn, 0x0cac4606n, 0x241af16dn,
] as const;

const INTERNAL_DIAGONAL = [
  2_013_265_919n, 1n, 2n, 1_006_632_961n, 3n, 4n, 1_006_632_960n, 2_013_265_918n,
  2_013_265_917n, 2_005_401_601n, 1_509_949_441n, 1_761_607_681n, 2_013_265_906n,
  7_864_320n, 125_829_120n, 15n,
] as const;

function concat(...parts: Uint8Array[]): Uint8Array {
  const length = parts.reduce((sum, part) => sum + part.length, 0);
  const out = new Uint8Array(length);
  let cursor = 0;
  for (const part of parts) { out.set(part, cursor); cursor += part.length; }
  return out;
}

function sized(bytes: Uint8Array, length: number, name: string): Uint8Array {
  if (bytes.length !== length) throw new RangeError(`${name} must be ${length} bytes`);
  return bytes;
}

function integer(value: bigint, length: number): Uint8Array {
  if (value < 0n || value >= 1n << BigInt(length * 8)) throw new RangeError(`integer does not fit ${length} bytes`);
  const out = new Uint8Array(length);
  for (let i = length - 1; i >= 0; i--) { out[i] = Number(value & 0xffn); value >>= 8n; }
  return out;
}

export function digestBytes(digest: Digest512): Uint8Array {
  return concat(sized(digest.left, 32, "digest.left"), sized(digest.right, 32, "digest.right"));
}

export function digestFromBytes(bytes: Uint8Array): Digest512 {
  sized(bytes, 64, "digest");
  return { left: bytes.slice(0, 32), right: bytes.slice(32) };
}

export function digestEqual(a: Digest512, b: Digest512): boolean {
  const aa = digestBytes(a); const bb = digestBytes(b);
  let difference = 0;
  for (let i = 0; i < aa.length; i++) difference |= aa[i]! ^ bb[i]!;
  return difference === 0;
}

function add(a: bigint, b: bigint): bigint {
  return (a + b) % P;
}


function mul(a: bigint, b: bigint): bigint {
  return (a * b) % P;
}

function sbox(value: bigint): bigint {
  const square = mul(value, value);
  const fourth = mul(square, square);
  return mul(mul(fourth, square), value);
}

function externalLinearLayer(state: bigint[]): void {
  for (let offset = 0; offset < 16; offset += 4) {
    const x0 = state[offset]!;
    const x1 = state[offset + 1]!;
    const x2 = state[offset + 2]!;
    const x3 = state[offset + 3]!;
    const t01 = add(x0, x1);
    const t23 = add(x2, x3);
    const t0123 = add(t01, t23);
    const t01123 = add(t0123, x1);
    const t01233 = add(t0123, x3);
    state[offset] = add(t01123, t01);
    state[offset + 1] = add(t01123, add(x2, x2));
    state[offset + 2] = add(t01233, t23);
    state[offset + 3] = add(t01233, add(x0, x0));
  }
  const sums = [0n, 0n, 0n, 0n];
  for (let i = 0; i < 16; i++) sums[i & 3] = add(sums[i & 3]!, state[i]!);
  for (let i = 0; i < 16; i++) state[i] = add(state[i]!, sums[i & 3]!);
}

function externalRounds(state: bigint[], constants: readonly (readonly bigint[])[]): void {
  for (const round of constants) {
    for (let i = 0; i < 16; i++) state[i] = sbox(add(state[i]!, round[i]!));
    externalLinearLayer(state);
  }
}

export function poseidon2BabyBear16(input: ArrayLike<number>): Uint32Array {
  if (input.length !== 16) throw new RangeError("Poseidon2 state must contain 16 elements");
  const state = new Array<bigint>(16);
  for (let index = 0; index < state.length; index++) {
    const value = input[index]!;
    if (!Number.isInteger(value) || value < 0 || value >= BABY_BEAR_MODULUS) {
      throw new RangeError(`state element ${index} is not canonical`);
    }
    state[index] = BigInt(value);
  }
  externalLinearLayer(state);
  externalRounds(state, EXTERNAL_INITIAL);
  for (const constant of INTERNAL) {
    state[0] = sbox(add(state[0]!, constant));
    let sum = 0n;
    for (const value of state) sum = add(sum, value);
    for (let i = 0; i < 16; i++) state[i] = add(sum, mul(state[i]!, INTERNAL_DIAGONAL[i]!));
  }
  externalRounds(state, EXTERNAL_FINAL);
  return Uint32Array.from(state, (value) => Number(value));
}

export function digestElements(digest: Digest512, name = "digest"): Uint32Array {
  const bytes = digestBytes(digest);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const elements = new Uint32Array(16);
  for (let i = 0; i < elements.length; i++) {
    const value = view.getUint32(i * 4, false);
    if (value >= BABY_BEAR_MODULUS) throw new RangeError(`${name} element ${i} is not canonical`);
    elements[i] = value;
  }
  return elements;
}

export function digestFromElements(elements: ArrayLike<number>): Digest512 {
  if (elements.length !== 16) throw new RangeError("digest must contain 16 elements");
  const bytes = new Uint8Array(64);
  const view = new DataView(bytes.buffer);
  for (let i = 0; i < elements.length; i++) {
    const value = elements[i]!;
    if (!Number.isInteger(value) || value < 0 || value >= BABY_BEAR_MODULUS) {
      throw new RangeError(`digest element ${i} is not canonical`);
    }
    view.setUint32(i * 4, value, false);
  }
  return digestFromBytes(bytes);
}

function byteElements(bytes: Uint8Array): number[] {
  const elements = new Array<number>(Math.ceil(bytes.length / 2));
  for (let i = 0; i < elements.length; i++) elements[i] = (bytes[i * 2]! << 8) | (bytes[i * 2 + 1] ?? 0);
  return elements;
}

export type CanonicalSecret = ArrayLike<number | bigint>;

function secretElements(secret: CanonicalSecret, name: string): number[] {
  if (secret.length !== 8) throw new RangeError(`${name} must contain 8 limbs`);
  const elements = new Array<number>(8);
  for (let index = 0; index < elements.length; index++) {
    const input = secret[index]!;
    if (
      (typeof input === "number" && (!Number.isInteger(input) || input < 0 || input >= BABY_BEAR_MODULUS))
      || (typeof input === "bigint" && (input < 0n || input >= P))
      || (typeof input !== "number" && typeof input !== "bigint")
    ) {
      throw new RangeError(`${name} limb ${index} is not canonical`);
    }
    elements[index] = Number(input);
  }
  return elements;
}

export function secretBytes(secret: CanonicalSecret, name = "secret"): Uint8Array {
  const elements = secretElements(secret, name);
  const bytes = new Uint8Array(32);
  const view = new DataView(bytes.buffer);
  for (let index = 0; index < elements.length; index++) view.setUint32(index * 4, elements[index]!, false);
  return bytes;
}

export function secretFromBytes(bytes: Uint8Array, name = "secret"): Uint32Array {
  sized(bytes, 32, name);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const secret = new Uint32Array(8);
  for (let index = 0; index < secret.length; index++) {
    const limb = view.getUint32(index * 4, false);
    if (limb >= BABY_BEAR_MODULUS) throw new RangeError(`${name} limb ${index} is not canonical`);
    secret[index] = limb;
  }
  return secret;
}

export function randomSecret(): Uint32Array {
  const secret = new Uint32Array(8);
  let accepted = 0;
  while (accepted < secret.length) {
    const entropy = randomBytes(64);
    const view = new DataView(entropy.buffer, entropy.byteOffset, entropy.byteLength);
    for (let offset = 0; offset < entropy.length && accepted < secret.length; offset += 4) {
      const candidate = view.getUint32(offset, false);
      if (candidate < BABY_BEAR_MODULUS) secret[accepted++] = candidate;
    }
  }
  return secret;
}

export function p2bb512(tag: number, payloadByteLength: number, aux: number, payload: ArrayLike<number>): Digest512 {
  if (!Number.isInteger(tag) || tag < 0 || tag > 255) throw new RangeError("tag must be one byte");
  if (!Number.isInteger(payloadByteLength) || payloadByteLength < 0 || payloadByteLength >= BABY_BEAR_MODULUS) {
    throw new RangeError("payload byte length is not canonical");
  }
  if (!Number.isInteger(aux) || aux < 0 || aux >= BABY_BEAR_MODULUS) throw new RangeError("aux is not canonical");
  if (!Number.isSafeInteger(payload.length) || payload.length < 0 || payload.length >= BABY_BEAR_MODULUS) {
    throw new RangeError("payload element count is not canonical");
  }
  const state = new Uint32Array(16);
  state[4] = 1;
  state[5] = tag;
  state[6] = payloadByteLength;
  state[7] = payload.length;
  state[8] = aux;
  const blocks = Math.max(1, Math.ceil(payload.length / 4));
  for (let block = 0; block < blocks; block++) {
    for (let i = 0; i < 4; i++) {
      const index = block * 4 + i;
      const value = index < payload.length ? payload[index]! : 0;
      if (!Number.isInteger(value) || value < 0 || value >= BABY_BEAR_MODULUS) {
        throw new RangeError(`payload element ${index} is not canonical`);
      }
      state[i] = Number((BigInt(state[i]!) + BigInt(value)) % P);
    }
    state.set(poseidon2BabyBear16(state));
  }
  const output = new Uint32Array(16);
  for (let block = 0; block < 4; block++) {
    output.set(state.subarray(0, 4), block * 4);
    if (block !== 3) state.set(poseidon2BabyBear16(state));
  }
  return digestFromElements(output);
}

export function k512(tag: number, payload: Uint8Array): Digest512 {
  if (!Number.isInteger(tag) || tag < 0 || tag > 255) throw new RangeError("tag must be one byte");
  return {
    left: keccak_256(concat(Uint8Array.of(0, tag), payload)),
    right: keccak_256(concat(Uint8Array.of(1, tag), payload)),
  };
}

export interface ScopeInput {
  chainId: bigint;
  pool: Address;
  denomination: bigint;
  treeDepth?: number;
  protocolVersion?: number;
  parameterId: Digest512;
}

export function scope(input: ScopeInput): Digest512 {
  const depth = input.treeDepth ?? TREE_DEPTH;
  const version = input.protocolVersion ?? PROTOCOL_VERSION;
  const payload = concat(
    integer(input.chainId, 8), sized(input.pool, 20, "pool"), integer(input.denomination, 32),
    integer(BigInt(depth), 1), integer(BigInt(version), 4), digestBytes(input.parameterId),
  );
  return p2bb512(domains.SCOPE, payload.length, 0, byteElements(payload));
}

export function commitment(
  poolScope: Digest512,
  nullifierSecret: CanonicalSecret,
  trapdoor: CanonicalSecret,
): Digest512 {
  return p2bb512(domains.NOTE, 128, 0, [
    ...digestElements(poolScope, "scope"),
    ...secretElements(nullifierSecret, "nullifierSecret"),
    ...secretElements(trapdoor, "trapdoor"),
  ]);
}

export function nullifierHash(poolScope: Digest512, nullifierSecret: CanonicalSecret): Digest512 {
  return p2bb512(domains.NULLIFIER, 96, 0, [
    ...digestElements(poolScope, "scope"),
    ...secretElements(nullifierSecret, "nullifierSecret"),
  ]);
}

export function emptyLeaf(poolScope: Digest512): Digest512 {
  return p2bb512(domains.EMPTY_LEAF, 64, 0, digestElements(poolScope, "scope"));
}

export function merkleNode(level: number, left: Digest512, right: Digest512): Digest512 {
  if (!Number.isInteger(level) || level < 0 || level >= TREE_DEPTH) throw new RangeError("invalid Merkle level");
  return p2bb512(domains.APP_MERKLE_NODE, 128, level, [...digestElements(left, "left"), ...digestElements(right, "right")]);
}

export function payoutDigest(recipient: Address, relayer: Address, fee: bigint): Digest512 {
  const payload = concat(sized(recipient, 20, "recipient"), sized(relayer, 20, "relayer"), integer(fee, 32));
  return p2bb512(domains.PAYOUT, payload.length, 0, byteElements(payload));
}

export interface WithdrawalStatement {
  scope: Digest512;
  root: Digest512;
  nullifierHash: Digest512;
  payoutDigest: Digest512;
}

export function statementHash(statement: WithdrawalStatement): Digest512 {
  const elements = [
    ...digestElements(statement.scope, "scope"),
    ...digestElements(statement.root, "root"),
    ...digestElements(statement.nullifierHash, "nullifierHash"),
    ...digestElements(statement.payoutDigest, "payoutDigest"),
  ];
  return p2bb512(domains.STATEMENT, 256, 0, elements);
}

export function publicValues(statement: WithdrawalStatement): Uint32Array {
  const out = new Uint32Array(64);
  out.set(digestElements(statement.scope, "scope"), 0);
  out.set(digestElements(statement.root, "root"), 16);
  out.set(digestElements(statement.nullifierHash, "nullifierHash"), 32);
  out.set(digestElements(statement.payoutDigest, "payoutDigest"), 48);
  return out;
}
const PROOF_MAGIC = new TextEncoder().encode("PQTCSTK3");
const PROOF_END = Uint8Array.of(0x50, 0x51, 0x45, 0x4e);
const MAX_STARK_PAYLOAD_BYTES = 2 * 1024 * 1024;
const PUBLIC_VALUES_COUNT = 64;

export interface CompactProofV3 {
  parameterId: Digest512;
  publicValues: Uint32Array;
  starkPayload: Uint8Array;
}

export function encodeCompactProof(proof: CompactProofV3): Uint8Array {
  if (proof.publicValues.length !== PUBLIC_VALUES_COUNT) throw new RangeError("public value count must be 64");
  if (proof.starkPayload.length > MAX_STARK_PAYLOAD_BYTES) throw new RangeError("STARK payload is too large");
  const parameter = digestBytes(proof.parameterId);
  if (parameter.every((byte) => byte === 0)) throw new Error("parameter ID cannot be zero");
  const fields = new Uint8Array(PUBLIC_VALUES_COUNT * 4);
  const fieldView = new DataView(fields.buffer);
  for (let i = 0; i < PUBLIC_VALUES_COUNT; i++) {
    const value = proof.publicValues[i]!;
    if (value >= BABY_BEAR_MODULUS) throw new RangeError(`field element ${value} is not canonical`);
    fieldView.setUint32(i * 4, value, false);
  }
  return concat(
    PROOF_MAGIC,
    integer(3n, 2),
    parameter,
    integer(BigInt(PUBLIC_VALUES_COUNT), 2),
    fields,
    integer(BigInt(proof.starkPayload.length), 4),
    proof.starkPayload,
    PROOF_END,
  );
}

export function decodeCompactProof(bytes: Uint8Array): CompactProofV3 {
  const fixedPrefix = 8 + 2 + 64 + 2 + PUBLIC_VALUES_COUNT * 4 + 4;
  if (bytes.length < fixedPrefix + 4) throw new Error("proof is truncated");
  let cursor = 0;
  const take = (length: number): Uint8Array => {
    const end = cursor + length;
    if (!Number.isSafeInteger(end) || end > bytes.length) throw new Error("proof is truncated");
    const value = bytes.slice(cursor, end);
    cursor = end;
    return value;
  };
  const readU16 = (): number => new DataView(take(2).buffer).getUint16(0, false);
  const readU32 = (): number => new DataView(take(4).buffer).getUint32(0, false);
  if (!equalBytes(take(8), PROOF_MAGIC)) throw new Error("invalid proof magic");
  if (readU16() !== 3) throw new Error("unsupported proof codec version");
  const parameterId = digestFromBytes(take(64));
  if (digestBytes(parameterId).every((byte) => byte === 0)) throw new Error("parameter ID cannot be zero");
  if (readU16() !== PUBLIC_VALUES_COUNT) throw new Error("public value count must be 64");
  const values = take(PUBLIC_VALUES_COUNT * 4);
  const valueView = new DataView(values.buffer, values.byteOffset, values.byteLength);
  const publicValues = new Uint32Array(PUBLIC_VALUES_COUNT);
  for (let i = 0; i < PUBLIC_VALUES_COUNT; i++) {
    const value = valueView.getUint32(i * 4, false);
    if (value >= BABY_BEAR_MODULUS) throw new Error(`field element ${value} is not canonical`);
    publicValues[i] = value;
  }
  const payloadLength = readU32();
  if (payloadLength > MAX_STARK_PAYLOAD_BYTES) throw new Error("STARK payload is too large");
  const starkPayload = take(payloadLength);
  if (!equalBytes(take(4), PROOF_END)) throw new Error("invalid proof end marker");
  if (cursor !== bytes.length) throw new Error("proof has trailing bytes");
  return { parameterId, publicValues, starkPayload };
}


export interface Note {
  chainId: bigint;
  pool: Address;
  parameterId: Digest512;
  nullifierSecret: CanonicalSecret;
  trapdoor: CanonicalSecret;
}

export function newNote(chainId: bigint, pool: Address, parameterId: Digest512): Note {
  return { chainId, pool: sized(pool, 20, "pool").slice(), parameterId, nullifierSecret: randomSecret(), trapdoor: randomSecret() };
}

export function encodeNote(note: Note): string {
  const body = concat(
    textEncoder.encode("PQTN"), integer(3n, 2), integer(note.chainId, 8), sized(note.pool, 20, "pool"),
    digestBytes(note.parameterId), secretBytes(note.nullifierSecret, "nullifierSecret"), secretBytes(note.trapdoor, "trapdoor"),
  );
  const checksum = keccak_256(concat(Uint8Array.of(0, domains.NOTE), body));
  return NOTE_PREFIX + Buffer.from(concat(body, checksum)).toString("base64url");
}

export function parseNote(encoded: string): Note {
  if (!encoded.startsWith(NOTE_PREFIX)) throw new Error("invalid note prefix");
  const payload = encoded.slice(NOTE_PREFIX.length);
  if (!/^[A-Za-z0-9_-]+$/.test(payload)) throw new Error("invalid note encoding");
  const bytes = new Uint8Array(Buffer.from(payload, "base64url"));
  if (Buffer.from(bytes).toString("base64url") !== payload) throw new Error("noncanonical note encoding");
  if (bytes.length !== NOTE_LENGTH) throw new Error("invalid note length");
  if (new TextDecoder().decode(bytes.slice(0, 4)) !== "PQTN") throw new Error("invalid note magic");
  if (bytes[4] !== 0 || bytes[5] !== 3) throw new Error("unsupported note version");
  const expected = keccak_256(concat(Uint8Array.of(0, domains.NOTE), bytes.slice(0, 162)));
  if (!equalBytes(expected, bytes.slice(162))) throw new Error("invalid note checksum");
  let chainId = 0n;
  for (const byte of bytes.slice(6, 14)) chainId = (chainId << 8n) | BigInt(byte);
  return {
    chainId,
    pool: bytes.slice(14, 34),
    parameterId: digestFromBytes(bytes.slice(34, 98)),
    nullifierSecret: secretFromBytes(bytes.slice(98, 130), "nullifierSecret"),
    trapdoor: secretFromBytes(bytes.slice(130, 162), "trapdoor"),
  };
}

export class NoteSecretTracker {
  private readonly nullifierSecrets = new Set<string>();

  register(note: Note): void {
    const key = Buffer.from(secretBytes(note.nullifierSecret, "nullifierSecret")).toString("hex");
    if (this.nullifierSecrets.has(key)) throw new Error("nullifier secret was already used locally");
    this.nullifierSecrets.add(key);
  }
}

function equalBytes(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let difference = 0;
  for (let i = 0; i < a.length; i++) difference |= a[i]! ^ b[i]!;
  return difference === 0;
}

export interface MerklePath { leafIndex: number; siblings: Digest512[] }

export class MerkleTree {
  readonly zeros: Digest512[];
  readonly leaves: Digest512[] = [];
  readonly filledSubtrees: Digest512[];
  private readonly commitmentKeys = new Set<string>();
  root: Digest512;

  constructor(poolScope: Digest512) {
    this.zeros = [emptyLeaf(poolScope)];
    for (let level = 0; level < TREE_DEPTH; level++) this.zeros.push(merkleNode(level, this.zeros[level]!, this.zeros[level]!));
    this.filledSubtrees = this.zeros.slice(0, TREE_DEPTH);
    this.root = this.zeros[TREE_DEPTH]!;
  }

  insert(leaf: Digest512): Readonly<{ leafIndex: number; root: Digest512 }> {
    const key = Buffer.from(digestBytes(leaf)).toString("hex");
    if (/^0+$/.test(key)) throw new Error("zero commitment");
    if (this.commitmentKeys.has(key)) throw new Error("duplicate commitment");
    if (this.leaves.length >= 1 << TREE_DEPTH) throw new Error("tree full");
    const leafIndex = this.leaves.length;
    let current = leaf; let index = leafIndex;
    for (let level = 0; level < TREE_DEPTH; level++) {
      if ((index & 1) === 0) { this.filledSubtrees[level] = current; current = merkleNode(level, current, this.zeros[level]!); }
      else current = merkleNode(level, this.filledSubtrees[level]!, current);
      index >>= 1;
    }
    this.commitmentKeys.add(key); this.leaves.push(leaf); this.root = current;
    return { leafIndex, root: current };
  }

  path(leafIndex: number): MerklePath {
    if (!Number.isInteger(leafIndex) || leafIndex < 0 || leafIndex >= this.leaves.length) throw new RangeError("unknown leaf");
    const siblings: Digest512[] = [];
    let nodes = this.leaves.slice(); let index = leafIndex;
    for (let level = 0; level < TREE_DEPTH; level++) {
      siblings.push(nodes[index ^ 1] ?? this.zeros[level]!);
      if ((nodes.length & 1) === 1) nodes.push(this.zeros[level]!);
      const parents: Digest512[] = [];
      for (let i = 0; i < nodes.length; i += 2) parents.push(merkleNode(level, nodes[i]!, nodes[i + 1]!));
      nodes = parents; index >>= 1;
    }
    return { leafIndex, siblings };
  }
}

export function rootFromPath(leaf: Digest512, path: MerklePath): Digest512 {
  if (path.siblings.length !== TREE_DEPTH) throw new RangeError("path must have 20 siblings");
  let current = leaf;
  for (let level = 0; level < TREE_DEPTH; level++) current = (path.leafIndex & (1 << level)) === 0
    ? merkleNode(level, current, path.siblings[level]!)
    : merkleNode(level, path.siblings[level]!, current);
  return current;
}



function selector(signature: string): Uint8Array {
  return keccak_256(textEncoder.encode(signature)).slice(0, 4);
}

export function encodeDepositCalldata(noteCommitment: Digest512): Uint8Array {
  return concat(
    selector("deposit((bytes32,bytes32))"),
    sized(noteCommitment.left, 32, "commitment.left"),
    sized(noteCommitment.right, 32, "commitment.right"),
  );
}


export function hex(bytes: Uint8Array): `0x${string}` {
  return `0x${Buffer.from(bytes).toString("hex")}`;
}

export function bytesFromHex(value: string, expectedLength?: number): Uint8Array {
  if (!/^0x[0-9a-fA-F]*$/.test(value) || value.length % 2 !== 0) throw new TypeError("invalid hex");
  const bytes = Uint8Array.from(Buffer.from(value.slice(2), "hex"));
  if (expectedLength !== undefined) sized(bytes, expectedLength, "hex value");
  return bytes;
}
