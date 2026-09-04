import { keccak_256 } from "../../../../packages/sdk/node_modules/@noble/hashes/sha3.js";

export const MODULUS = 2_013_265_921;
export type Candidate = "T0" | "T1" | "T2" | "T3";
export type ItemType = 1 | 2 | 3;
export interface Metrics { keccakCalls: number; hashedBytes: number; copiedBytes: number; peakFrameBytes: number }
export interface Snapshot { label: string; operation: "absorb" | "squeeze"; state: string; pendingItems: number; pendingBytes: number; outputBytes: number; squeezeCounter: string; rejectedWords: number }

const encoder = new TextEncoder();
const VERSION: Record<Candidate, Uint8Array> = {
  T0: encoder.encode("PQTCT0-01"),
  T1: encoder.encode("PQTCT1-01"),
  T2: encoder.encode("PQTCT2-01"),
  T3: encoder.encode("PQTCT3-01"),
};

function concat(...parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const part of parts) { out.set(part, at); at += part.length; }
  return out;
}
export function u16(n: number): Uint8Array {
  if (!Number.isSafeInteger(n) || n < 0 || n > 0xffff) throw new Error("u16 out of range");
  return Uint8Array.of(n >>> 8, n);
}
export function u32(n: number): Uint8Array {
  if (!Number.isSafeInteger(n) || n < 0 || n > 0xffff_ffff) throw new Error("u32 out of range");
  return Uint8Array.of(n >>> 24, n >>> 16, n >>> 8, n);
}
export function u64(n: bigint): Uint8Array {
  if (n < 0n || n > 0xffff_ffff_ffff_ffffn) throw new Error("u64 out of range");
  const out = new Uint8Array(8);
  for (let i = 7; i >= 0; i--) { out[i] = Number(n & 255n); n >>= 8n; }
  return out;
}
export function field(n: number): Uint8Array {
  if (!Number.isSafeInteger(n) || n < 0 || n >= MODULUS) throw new Error(`noncanonical field ${n}`);
  return u32(n);
}
export function hex(bytes: Uint8Array): string { return Buffer.from(bytes).toString("hex"); }
export function fromHex(value: string, bytes?: number): Uint8Array {
  if (!/^(?:[0-9a-f]{2})*$/i.test(value)) throw new Error("noncanonical hex");
  const out = Uint8Array.from(Buffer.from(value, "hex"));
  if (bytes !== undefined && out.length !== bytes) throw new Error(`expected ${bytes} bytes`);
  return out;
}
function be32(bytes: Uint8Array): number {
  return ((bytes[0]! * 0x1000000) + (bytes[1]! << 16) + (bytes[2]! << 8) + bytes[3]!) >>> 0;
}

export class Transcript {
  variant: Candidate;
  metrics: Metrics = { keccakCalls: 0, hashedBytes: 0, copiedBytes: 0, peakFrameBytes: 0 };
  events: Snapshot[] = [];
  private stateBytes: Uint8Array;
  private output = new Uint8Array();
  private outputAt = 0;
  private counter = 0n;
  private pending: Uint8Array[] = [];
  private pendingLength = 0;
  private rejected = 0;

  constructor(variant: Candidate, parameterDigest: Uint8Array, publicValues: number[], productionCompatibleT0 = false) {
    this.variant = variant;
    if (parameterDigest.length !== 64) throw new Error("parameter digest must be 64 bytes");
    publicValues.forEach(field);
    const fields = concat(...publicValues.map(field));
    const payload = productionCompatibleT0 && variant === "T0"
      ? concat(parameterDigest, fields)
      : concat(VERSION[variant], parameterDigest, u32(publicValues.length), fields);
    this.stateBytes = this.k512(0x42, payload);
    this.events.push(this.snapshot("init", "absorb"));
  }

  private k512(tag: number, payload: Uint8Array): Uint8Array {
    const leftInput = concat(Uint8Array.of(0, tag), payload);
    const rightInput = concat(Uint8Array.of(1, tag), payload);
    this.metrics.keccakCalls += 2;
    this.metrics.hashedBytes += leftInput.length + rightInput.length;
    this.metrics.copiedBytes += leftInput.length + rightInput.length + 64;
    return concat(keccak_256(leftInput), keccak_256(rightInput));
  }
  private resetOutput(): void { this.output = new Uint8Array(); this.outputAt = 0; this.counter = 0n; }
  private typed(type: ItemType, payload: Uint8Array, label: string): void {
    if (type === 1 && payload.length !== 4) throw new Error("scalar width");
    if (type === 2 && payload.length !== 64) throw new Error("commitment width");
    if (type === 3) decodeFieldArray(payload);
    if (this.variant === "T2") {
      const digest = this.k512(0x45, concat(VERSION.T2, Uint8Array.of(type), u32(payload.length), payload));
      this.stateBytes = this.k512(0x43, concat(this.stateBytes, digest));
      this.resetOutput();
    } else if (this.variant === "T3") {
      const item = concat(Uint8Array.of(type), u32(payload.length), payload);
      this.pending.push(item); this.pendingLength += item.length;
      this.metrics.copiedBytes += item.length;
      this.metrics.peakFrameBytes = Math.max(this.metrics.peakFrameBytes, this.pendingLength);
    } else {
      this.stateBytes = this.k512(0x43, concat(this.stateBytes, Uint8Array.of(type), u32(payload.length), payload));
      this.resetOutput();
    }
    this.events.push(this.snapshot(label, "absorb"));
  }
  absorbField(value: number, label: string): void { this.typed(1, field(value), label); }
  absorbCommitment(value: Uint8Array, label: string): void {
    if (value.length !== 64) throw new Error("commitment must be 64 bytes");
    this.typed(2, value, label);
  }
  absorbFields(values: number[], label: string): void {
    values.forEach(field);
    if (this.variant === "T0") {
      values.forEach((v, i) => this.absorbField(v, `${label}[${i}]`));
      return;
    }
    this.typed(3, concat(u32(values.length), ...values.map(field)), label);
  }
  private flush(): void {
    if (this.variant !== "T3" || this.pending.length === 0) return;
    const items = concat(...this.pending);
    const payload = concat(VERSION.T3, u32(this.pending.length), u32(items.length), items);
    this.stateBytes = this.k512(0x46, concat(this.stateBytes, payload));
    this.pending = []; this.pendingLength = 0; this.resetOutput();
  }
  private bytes(count: number): Uint8Array {
    this.flush();
    const out = new Uint8Array(count);
    for (let i = 0; i < count; i++) {
      if (this.outputAt === this.output.length) {
        this.output = this.k512(0x44, concat(this.stateBytes, u64(this.counter++)));
        this.outputAt = 0;
      }
      out[i] = this.output[this.outputAt++]!;
    }
    return out;
  }
  sampleField(label: string): number {
    for (;;) {
      const word = be32(this.bytes(4)) & 0x7fffffff;
      if (word < MODULUS) { this.events.push(this.snapshot(label, "squeeze")); return word; }
      this.rejected++;
    }
  }
  sampleExtension(label: string): number[] {
    const value = [0, 1, 2, 3].map((i) => this.sampleField(`${label}.c${i}`));
    return value;
  }
  sampleBits(bits: number, label: string): number {
    if (!Number.isInteger(bits) || bits < 0 || bits > 31) throw new Error("bits out of range");
    const word = be32(this.bytes(4));
    const value = bits === 0 ? 0 : word & (2 ** bits - 1);
    this.events.push(this.snapshot(label, "squeeze"));
    return value;
  }
  clone(): Transcript {
    const out = Object.create(Transcript.prototype) as Transcript;
    Object.assign(out, this);
    out.metrics = { ...this.metrics };
    out.events = [...this.events];
    out.stateBytes = this.stateBytes.slice(); out.output = this.output.slice();
    out.pending = this.pending.map((p) => p.slice());
    return out;
  }
  adopt(other: Transcript): void {
    this.stateBytes = other.stateBytes; this.output = other.output; this.outputAt = other.outputAt;
    this.counter = other.counter; this.pending = other.pending; this.pendingLength = other.pendingLength;
    this.rejected = other.rejected; Object.assign(this.metrics, other.metrics);
    this.events.splice(0, this.events.length, ...other.events);
  }
  checkWitness(bits: number, witness: number, label: string): boolean {
    if (bits === 0) return true;
    this.absorbField(witness, `${label}.witness`);
    return this.sampleBits(bits, `${label}.check`) === 0;
  }
  grind(bits: number, label: string): number {
    if (bits === 0) return 0;
    for (let witness = 0; witness < MODULUS; witness++) {
      const trial = this.clone();
      trial.absorbField(witness, `${label}.witness`);
      if (trial.sampleBits(bits, `${label}.check`) === 0) { this.adopt(trial); return witness; }
    }
    throw new Error("no PoW witness");
  }
  state(): Uint8Array { this.flush(); return this.stateBytes.slice(); }
  snapshot(label: string, operation: "absorb" | "squeeze"): Snapshot {
    return { label, operation, state: hex(this.stateBytes), pendingItems: this.pending.length, pendingBytes: this.pendingLength,
      outputBytes: this.output.length - this.outputAt, squeezeCounter: this.counter.toString(), rejectedWords: this.rejected };
  }
}

export function encodeFieldArray(values: number[]): Uint8Array { values.forEach(field); return concat(u32(values.length), ...values.map(field)); }
export function decodeFieldArray(payload: Uint8Array): number[] {
  if (payload.length < 4) throw new Error("truncated count");
  const count = be32(payload.subarray(0, 4));
  if (payload.length !== 4 + count * 4) throw new Error("array count/length mismatch or trailing bytes");
  const out: number[] = [];
  for (let at = 4; at < payload.length; at += 4) {
    const value = be32(payload.subarray(at, at + 4)); field(value); out.push(value);
  }
  return out;
}

function abiWordAscii(value: string): Uint8Array {
  const bytes = new TextEncoder().encode(value);
  if (bytes.length > 32) throw new Error("ABI word overflow");
  return concat(bytes, new Uint8Array(32 - bytes.length));
}
function abiWordField(value: number): Uint8Array { return concat(new Uint8Array(28), field(value)); }
export function statementKey(parameter: Uint8Array, publicValues: number[]): Uint8Array {
  if (parameter.length !== 64 || publicValues.length !== 64) throw new Error("full-width statement required");
  publicValues.forEach(field);
  return keccak_256(concat(abiWordAscii("PQTC.V3.STATEMENT"), parameter, ...publicValues.map(abiWordField)));
}
export function checkpointDigest(key: Uint8Array, payload: Uint8Array): Uint8Array {
  if (key.length !== 32) throw new Error("key width");
  return keccak_256(concat(abiWordAscii("PQTC.V3.CHECKPOINT"), key, keccak_256(payload)));
}
export function proofId(key: Uint8Array, partA: Uint8Array): Uint8Array {
  if (key.length !== 32) throw new Error("key width");
  return keccak_256(concat(abiWordAscii("PQTC.V3.PROOF"), key, keccak_256(partA)));
}
export interface FullDigestRecord { parameter: Uint8Array; statementDigests: Uint8Array[]; globalDigest: Uint8Array; coreProofDigest: Uint8Array }
function requireStatementDigests(publicValues: number[], digests: Uint8Array[]): void {
  if (digests.length !== 4 || digests.some((digest) => digest.length !== 64)) throw new Error("four full statement digests required");
  const encodedFields = digests.flatMap((digest) => Array.from({ length: 16 }, (_, i) => be32(digest.subarray(i * 4, i * 4 + 4))));
  if (encodedFields.length !== publicValues.length || encodedFields.some((value, i) => value !== publicValues[i])) throw new Error("statement digest/public field mismatch");
}
export class FullDigestStore {
  private records = new Map<string, FullDigestRecord>();
  put(publicValues: number[], record: FullDigestRecord): Uint8Array {
    if (record.parameter.length !== 64 || record.statementDigests.length !== 4 || record.statementDigests.some((d) => d.length !== 64)
      || record.globalDigest.length !== 32 || record.coreProofDigest.length !== 32) throw new Error("full-width record required");
    requireStatementDigests(publicValues, record.statementDigests);
    const key = statementKey(record.parameter, publicValues);
    this.records.set(hex(key), { parameter: record.parameter.slice(), statementDigests: record.statementDigests.map((d) => d.slice()), globalDigest: record.globalDigest.slice(), coreProofDigest: record.coreProofDigest.slice() });
    return key;
  }
  getChecked(key: Uint8Array, publicValues: number[], supplied: FullDigestRecord): FullDigestRecord {
    const stored = this.records.get(hex(key)); if (!stored) throw new Error("unknown lookup key");
    if (hex(statementKey(stored.parameter, publicValues)) !== hex(key)) throw new Error("stored full statement/key mismatch");
    requireStatementDigests(publicValues, stored.statementDigests);
    const all = (r: FullDigestRecord) => [r.parameter, ...r.statementDigests, r.globalDigest, r.coreProofDigest].map(hex);
    if (JSON.stringify(all(stored)) !== JSON.stringify(all(supplied))) throw new Error("full-width digest mismatch");
    return stored;
  }
}
