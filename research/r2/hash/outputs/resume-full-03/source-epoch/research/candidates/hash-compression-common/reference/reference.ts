#!/usr/bin/env -S node --experimental-strip-types
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const CONSTANTS = JSON.parse(readFileSync(resolve(HERE, "../constants/pinned.json"), "utf8"));
const BB = 2013265921n;
const M31 = 2147483647n;
type Candidate = "H0" | "H1" | "H3" | "H4" | "H5" | "H6" | "H7";
type Role = "Primitive" | "Note" | "Nullifier" | "Node";

function mod(value: bigint, p: bigint): bigint {
  const reduced = value % p;
  return reduced < 0n ? reduced + p : reduced;
}

function pow(value: bigint, exponent: bigint, p: bigint): bigint {
  let x = mod(value, p), y = 1n, e = exponent;
  while (e > 0n) { if (e & 1n) y = y * x % p; x = x * x % p; e >>= 1n; }
  return y;
}

function external(state: bigint[]): void {
  const width = state.length;
  for (let i = 0; i < width; i += 4) {
    const [a, b, c, d] = state.slice(i, i + 4);
    state[i] = mod(2n*a + 3n*b + c + d, BB);
    state[i+1] = mod(a + 2n*b + 3n*c + d, BB);
    state[i+2] = mod(a + b + 2n*c + 3n*d, BB);
    state[i+3] = mod(3n*a + b + c + 2n*d, BB);
  }
  const sums = [0n, 0n, 0n, 0n];
  for (let i = 0; i < width; i++) sums[i % 4] += state[i];
  for (let i = 0; i < width; i++) state[i] = mod(state[i] + sums[i % 4], BB);
}

export function poseidon2(input: number[]): number[] {
  const params = CONSTANTS.poseidon2[String(input.length)];
  if (!params) throw new Error(`unsupported Poseidon2 width ${input.length}`);
  const state = input.map(BigInt);
  external(state);
  for (let r = 0; r < 4; r++) {
    for (let i = 0; i < state.length; i++) state[i] = pow(state[i] + BigInt(params.initial[r * state.length + i]), 7n, BB);
    external(state);
  }
  for (let r = 0; r < params.internal.length; r++) {
    state[0] = pow(state[0] + BigInt(params.internal[r]), 7n, BB);
    const sum = state.reduce((a: bigint, b: bigint) => a + b, 0n);
    for (let i = 0; i < state.length; i++) state[i] = mod(sum + BigInt(params.diagonal[i]) * state[i], BB);
  }
  for (let r = 0; r < 4; r++) {
    for (let i = 0; i < state.length; i++) state[i] = pow(state[i] + BigInt(params.final[r * state.length + i]), 7n, BB);
    external(state);
  }
  return state.map(Number);
}

export function compress(input: number[], d: number): number[] {
  const output = poseidon2(input);
  return output.slice(0, d).map((value, i) => Number((BigInt(value) + BigInt(input[i])) % BB));
}

function roleValue(role: Role): number { return { Primitive: 1, Note: 0x11, Nullifier: 0x12, Node: 0x20 }[role]; }

export function p2bb512(role: Role, level: number, payload: number[]): number[] {
  const state = new Array<number>(16).fill(0);
  state[4] = 1; state[5] = roleValue(role); state[6] = payload.length * 4;
  state[7] = payload.length; state[8] = level;
  if (payload.length === 0) state.splice(0, 16, ...poseidon2(state));
  else for (let offset = 0; offset < payload.length; offset += 4) {
    for (let i = 0; i < Math.min(4, payload.length - offset); i++) state[i] = Number((BigInt(state[i]) + BigInt(payload[offset + i])) % BB);
    state.splice(0, 16, ...poseidon2(state));
  }
  const output: number[] = [];
  for (let block = 0; block < 4; block++) {
    if (block !== 0) state.splice(0, 16, ...poseidon2(state));
    output.push(...state.slice(0, 4));
  }
  return output;
}

function rpoMds(state: bigint[]): bigint[] {
  const row = CONSTANTS.rpoM31.mdsFirstRow32.map(BigInt);
  return state.map((_, r) => mod(state.reduce((acc, x, c) => acc + row[(c + 32 - r) % 32] * x, 0n), M31));
}

export function rpoPermutation(input: number[]): number[] {
  if (input.length !== 24) throw new Error("RPO-M31 state width must be 24");
  const rc = CONSTANTS.rpoM31.roundConstants.map(BigInt);
  let state = input.map(BigInt);
  for (let round = 0; round < 7; round++) {
    state = rpoMds(state).map((x, i) => pow(x + rc[2 * round * 24 + i], 5n, M31));
    state = rpoMds(state).map((x, i) => pow(x + rc[(2 * round + 1) * 24 + i], 1717986917n, M31));
  }
  state = rpoMds(state).map((x, i) => mod(x + rc[14 * 24 + i], M31));
  return state.map(Number);
}

export function rpoSponge(message: number[]): number[] {
  if (message.length === 0) throw new Error("published RPO-M31 padding domain requires a non-empty final block");
  const state = new Array<number>(24).fill(0);
  const finalLength = ((message.length - 1) % 16) + 1;
  state[16] = 16 - finalLength;
  for (let offset = 0; offset < message.length; offset += 16) {
    for (let i = 0; i < Math.min(16, message.length - offset); i++) state[i] = Number((BigInt(state[i]) + BigInt(message[offset + i])) % M31);
    state.splice(0, 24, ...rpoPermutation(state));
  }
  return state.slice(0, 16);
}

interface CrossLanguageVector {
  candidate: Candidate;
  kind: string;
  role: Role;
  controls: [number, number, number, number];
  input: number[];
  output: number[];
  sha256: string;
  ethereum_keccak256: string;
  vector_id: string;
}
interface TreeRecord { equal: boolean; root_iterative: number[]; root_direct: number[] }
interface Bundle { vector_count: number; vectors: CrossLanguageVector[]; tree_parity: TreeRecord[] }

function parseBundle(value: unknown): Bundle {
  if (value === null || typeof value !== "object") throw new Error("vector bundle must be an object");
  const object = value as Record<string, unknown>;
  if (typeof object.vector_count !== "number" || !Array.isArray(object.vectors) || !Array.isArray(object.tree_parity)) throw new Error("invalid vector bundle shape");
  for (const entry of object.vectors) {
    if (entry === null || typeof entry !== "object") throw new Error("invalid vector");
    const vector = entry as Record<string, unknown>;
    if (typeof vector.candidate !== "string" || typeof vector.kind !== "string" || typeof vector.role !== "string" || typeof vector.vector_id !== "string" || typeof vector.sha256 !== "string" || typeof vector.ethereum_keccak256 !== "string" || !Array.isArray(vector.controls) || vector.controls.length !== 4 || !Array.isArray(vector.input) || !Array.isArray(vector.output)) throw new Error("invalid vector fields");
    if (![...vector.controls, ...vector.input, ...vector.output].every((x) => typeof x === "number")) throw new Error("non-numeric vector lane");
  }
  for (const entry of object.tree_parity) {
    if (entry === null || typeof entry !== "object") throw new Error("invalid tree record");
    const tree = entry as Record<string, unknown>;
    if (typeof tree.equal !== "boolean" || !Array.isArray(tree.root_iterative) || !Array.isArray(tree.root_direct)) throw new Error("invalid tree record fields");
  }
  return object as unknown as Bundle;
}

function outputFor(vector: CrossLanguageVector): number[] {
  const candidate = vector.candidate;
  if (candidate === "H0") return p2bb512(vector.role, vector.controls[3], vector.input);
  if (candidate === "H7") return rpoSponge([...vector.controls, ...vector.input]);
  const d: Record<string, number> = { H1: 7, H3: 10, H4: 11, H5: 12, H6: 14 };
  if (vector.kind === "primitive") return compress(vector.input, d[candidate]);
  const width: Record<string, number> = { H3: 24, H5: 32, H6: 32 };
  const state = new Array<number>(width[candidate]).fill(0);
  state.splice(0, vector.input.length, ...vector.input);
  state.splice(vector.input.length, 4, ...vector.controls);
  return compress(state, d[candidate]);
}

function verify(path: string): void {
  const bundle = parseBundle(JSON.parse(readFileSync(path, "utf8")) as unknown);
  if (bundle.vector_count < 10000 || bundle.vector_count !== bundle.vectors.length) throw new Error("vector-count invariant failed");
  let checked = 0;
  for (const vector of bundle.vectors) {
    const actual = outputFor(vector);
    if (actual.length !== vector.output.length || actual.some((x, i) => x !== vector.output[i])) throw new Error(`cross-language mismatch: ${vector.vector_id}`);
    const bytes = Buffer.concat(actual.map((x) => { const b = Buffer.alloc(4); b.writeUInt32BE(x); return b; }));
    if (createHash("sha256").update(bytes).digest("hex") !== vector.sha256) throw new Error(`SHA-256 mismatch: ${vector.vector_id}`);
    if (createHash("sha3-256").update(bytes).digest("hex") === vector.ethereum_keccak256) throw new Error(`NIST SHA3 mislabeled as Ethereum Keccak: ${vector.vector_id}`);
    checked++;
  }
  if (bundle.tree_parity.some((x) => !x.equal || JSON.stringify(x.root_iterative) !== JSON.stringify(x.root_direct))) throw new Error("tree parity record failed");
  console.log(JSON.stringify({ ok: true, checked, treeParity: bundle.tree_parity.length }));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 4 || process.argv[2] !== "verify") throw new Error("usage: reference.ts verify <vectors.json>");
  verify(resolve(process.argv[3]));
}
