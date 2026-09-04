import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { hex, MODULUS, Transcript } from "./transcript.ts";

const fixturePath = "research/candidates/v03-baseline/proofs/v03-fixed-01/part-a.pqtc";
const proof = Uint8Array.from(readFileSync(fixturePath));
let at = 0;
function take(count: number): Uint8Array {
  if (at + count > proof.length) throw new Error("truncated canonical fixture");
  const value = proof.slice(at, at + count); at += count; return value;
}
function word(bytes: Uint8Array): number {
  if (bytes.length !== 4) throw new Error("word width");
  return ((bytes[0]! * 0x1000000) + (bytes[1]! << 16) + (bytes[2]! << 8) + bytes[3]!) >>> 0;
}
function takeField(): number {
  const value = word(take(4));
  if (value >= MODULUS) throw new Error(`noncanonical fixture field ${value}`);
  return value;
}
function takeFields(count: number): number[] { return Array.from({ length: count }, takeField); }
function equalFields(label: string, actual: number[], expected: number[]): void {
  if (actual.length !== expected.length || actual.some((value, i) => value !== expected[i])) throw new Error(`${label} mismatch`);
}

if (new TextDecoder().decode(take(8)) !== "PQTCPA03") throw new Error("part A magic");
if (word(Uint8Array.from([0, 0, ...take(2)])) !== 3) throw new Error("part version");
const profile = take(1)[0]; const degreeBits = take(1)[0]; const friRounds = take(1)[0]; const randomCodewords = take(1)[0];
const queryCount = word(Uint8Array.from([0, 0, ...take(2)]));
if (profile !== 3 || degreeBits !== 9 || friRounds !== 9 || randomCodewords !== 4 || queryCount !== 32) throw new Error("production shape");
const parameter = take(64);
const publicCount = word(Uint8Array.from([0, 0, ...take(2)]));
if (publicCount !== 64) throw new Error("public count");
const publicValues = takeFields(publicCount);
const encodedGlobalDigest = take(32);
const globalStart = at;
const traceCommit = take(64); const quotientCommit = take(64); const randomCommit = take(64);
const traceLocal = takeFields(190 * 4); const traceNext = takeFields(190 * 4);
const quotient = Array.from({ length: 16 }, () => takeFields(4 * 4));
const randomOpening = takeFields(4 * 4);
const hidingRandom = takeFields(4 * 4);
const hidingTraceLocal = takeFields(4 * 4); const hidingTraceNext = takeFields(4 * 4);
const hidingQuotient = Array.from({ length: 16 }, () => takeFields(4 * 4));
const friCommits = Array.from({ length: 9 }, () => take(64));
const commitWitnesses = takeFields(9);
const finalPoly = takeFields(4);
const queryWitness = takeField();
if (at - globalStart !== 9_208) throw new Error("global width");
const checkpointDigest = take(32);
const checkpointGlobalDigest = take(32);
const checkpointState = take(64);
const checkpointAlpha = takeFields(4); const checkpointZeta = takeFields(4); const checkpointFriAlpha = takeFields(4);
const checkpointBetas = Array.from({ length: 9 }, () => takeFields(4));
const checkpointQueryCount = word(Uint8Array.from([0, 0, ...take(2)]));
const checkpointQueries = takeFields(checkpointQueryCount);
const uniqueCount = word(Uint8Array.from([0, 0, ...take(2)]));
const uniqueQueries = takeFields(uniqueCount);

if (hex(encodedGlobalDigest) !== hex(checkpointGlobalDigest)) throw new Error("checkpoint/global digest mismatch");
const t = new Transcript("T0", parameter, publicValues, true);
t.absorbField(9, "degree_bits"); t.absorbField(8, "base_degree_bits"); t.absorbField(0, "preprocessed_width");
t.absorbCommitment(traceCommit, "trace_commit"); t.absorbFields(publicValues, "public_values");
const alpha = t.sampleExtension("air_alpha"); equalFields("air alpha", alpha, checkpointAlpha);
t.absorbCommitment(quotientCommit, "quotient_commit"); t.absorbCommitment(randomCommit, "random_commit");
const zeta = t.sampleExtension("zeta"); equalFields("zeta", zeta, checkpointZeta);
t.absorbFields([...randomOpening, ...hidingRandom], "random_plus_hiding");
t.absorbFields([...traceLocal, ...hidingTraceLocal], "trace_local_plus_hiding");
t.absorbFields([...traceNext, ...hidingTraceNext], "trace_next_plus_hiding");
for (let i = 0; i < 16; i++) t.absorbFields([...quotient[i]!, ...hidingQuotient[i]!], `quotient_${i}_plus_hiding`);
const friAlpha = t.sampleExtension("fri_alpha"); equalFields("fri alpha", friAlpha, checkpointFriAlpha);
for (let round = 0; round < 9; round++) {
  t.absorbCommitment(friCommits[round]!, `fri_commit_${round}`);
  if (!t.checkWitness(16, commitWitnesses[round]!, `commit_pow_${round}`)) throw new Error(`invalid canonical commit PoW ${round}`);
  equalFields(`fri beta ${round}`, t.sampleExtension(`fri_beta_${round}`), checkpointBetas[round]!);
}
t.absorbFields(finalPoly, "final_poly");
for (let round = 0; round < 9; round++) t.absorbField(1, `log_arity_${round}`);
if (!t.checkWitness(8, queryWitness, "query_pow")) throw new Error("invalid canonical query PoW");
const queries = Array.from({ length: 32 }, (_, i) => t.sampleBits(13, `query_${i}`));
equalFields("query indices", queries, checkpointQueries);
const sortedUnique = [...new Set(queries)].sort((a, b) => a - b);
equalFields("unique query indices", sortedUnique, uniqueQueries);
if (hex(t.state()) !== hex(checkpointState)) throw new Error("checkpoint transcript state mismatch");

const evidence = {
  schema: "pqtc.sp30.v03-conformance.v1", fixture: fixturePath, fixtureSha256: createHash("sha256").update(proof).digest("hex"),
  fixtureBytes: proof.length, globalBytes: at >= globalStart ? 9_208 : 0, checkpointDigest: hex(checkpointDigest),
  matches: { airAlpha: true, zeta: true, friAlpha: true, friBetas: 9, commitPowChecks: 9, queryPowCheck: true, queryIndices: 32, uniqueQueryIndices: uniqueCount, transcriptState: true, globalDigestRepeated: true },
  transcriptMetrics: t.metrics, result: "PASS_T0_EXACT_V03_CHECKPOINT_REPLAY",
};
writeFileSync("research/cryptanalysis/transcript/v03-conformance.json", `${JSON.stringify(evidence, null, 2)}\n`);
console.log(evidence.result);
