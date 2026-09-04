import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { checkpointDigest, decodeFieldArray, encodeFieldArray, field, fromHex, FullDigestStore, hex, MODULUS, proofId, statementKey, Transcript, u16, type Candidate, type Snapshot } from "./transcript.ts";
import { keccak_256 } from "../../../../packages/sdk/node_modules/@noble/hashes/sha3.js";
const canonicalPartA = Uint8Array.from(readFileSync("research/candidates/v03-baseline/proofs/v03-fixed-01/part-a.pqtc"));
const canonicalPartB = Uint8Array.from(readFileSync("research/candidates/v03-baseline/proofs/v03-fixed-01/part-b.pqtc"));
const canonicalContinuation = {
  fixture: "research/runs/v03-fixed-01.json",
  partA: hex(canonicalPartA),
  partB: hex(canonicalPartB),
  partAKeccak256: hex(keccak_256(canonicalPartA)),
  partBKeccak256: hex(keccak_256(canonicalPartB)),
  proofId: hex(canonicalPartB.slice(338, 370)),
  globalDigest: hex(canonicalPartA.slice(338, 370)),
  checkpointDigest: hex(canonicalPartA.slice(9_578, 9_610)),
  halfPositions: { partAStart: 0, partACount: 16, partBStart: 16, partBCount: 16 },
};


const candidates: Candidate[] = ["T0", "T1", "T2", "T3"];
const parameter = Uint8Array.from({ length: 64 }, (_, i) => i);
const publicValues = Array.from({ length: 64 }, (_, i) => i + 1);
const commitment = (seed: number): Uint8Array => Uint8Array.from({ length: 64 }, (_, i) => (seed * 29 + i * 17) & 255);
const fields = (seed: number, count: number): number[] => Array.from({ length: count }, (_, i) => (seed * 65_537 + i * 257 + 3) % MODULUS);
const deterministicBytes = (seed: number, count: number): Uint8Array => Uint8Array.from({ length: count }, (_, i) => (seed * 43 + i * 131) & 255);

interface ClaimEvent { op: "field" | "commitment" | "fields" | "extension" | "bits"; label: string; count?: number }
interface RunResult { candidate: Candidate; productionCompatible: boolean; challenges: Record<string, number | number[]>; claims: ClaimEvent[]; events: Snapshot[]; finalState: string; metrics: Record<string, number>; binding: Record<string, unknown> }

function run(candidate: Candidate): RunResult {
  const t = new Transcript(candidate, parameter, publicValues, candidate === "T0");
  const claims: ClaimEvent[] = [];
  const challenges: Record<string, number | number[]> = {};
  const absorbField = (value: number, label: string): void => { claims.push({ op: "field", label }); t.absorbField(value, label); };
  const absorbCommitment = (value: Uint8Array, label: string): void => { claims.push({ op: "commitment", label }); t.absorbCommitment(value, label); };
  const absorbFields = (value: number[], label: string): void => { claims.push({ op: "fields", label, count: value.length }); t.absorbFields(value, label); };
  const sampleExtension = (label: string): number[] => { claims.push({ op: "extension", label }); const value = t.sampleExtension(label); challenges[label] = value; return value; };

  absorbField(9, "B0.degree_bits"); absorbField(8, "B0.base_degree_bits"); absorbField(0, "B0.preprocessed_width");
  absorbCommitment(commitment(1), "B0.trace_commit"); absorbFields(publicValues, "B0.public_values"); sampleExtension("B0.air_alpha");
  absorbCommitment(commitment(2), "B1.quotient_commit"); absorbCommitment(commitment(3), "B1.random_commit"); sampleExtension("B1.zeta");
  absorbFields(fields(10, 32), "B2.random_plus_hiding");
  absorbFields(fields(11, 776), "B2.trace_local_plus_hiding"); absorbFields(fields(12, 776), "B2.trace_next_plus_hiding");
  for (let i = 0; i < 16; i++) absorbFields(fields(20 + i, 32), `B2.quotient_${i}_plus_hiding`);
  sampleExtension("B2.fri_alpha");
  for (let round = 0; round < 9; round++) {
    absorbCommitment(commitment(40 + round), `B3.${round}.fri_commit`);
    const witness = t.grind(16, `B3.${round}.commit_pow`);
    claims.push({ op: "field", label: `B3.${round}.commit_pow.witness` }, { op: "bits", label: `B3.${round}.commit_pow.check`, count: 16 });
    challenges[`B3.${round}.commit_pow_witness`] = witness;
    sampleExtension(`B3.${round}.fri_beta`);
  }
  absorbFields(fields(80, 4), "B4.final_poly");
  if (candidate === "T0") for (let i = 0; i < 9; i++) absorbField(1, `B4.log_arities[${i}]`);
  else absorbFields(Array(9).fill(1), "B4.log_arities");
  const queryWitness = t.grind(8, "B4.query_pow");
  claims.push({ op: "field", label: "B4.query_pow.witness" }, { op: "bits", label: "B4.query_pow.check", count: 8 });
  challenges["B4.query_pow_witness"] = queryWitness;
  const queryIndices: number[] = [];
  for (let i = 0; i < 32; i++) queryIndices.push(t.sampleBits(13, `B4.query_index[${i}]`));
  challenges["B4.query_indices"] = queryIndices;

  const globalBytes = deterministicBytes(91, 9_208);
  const coreProofBytes = deterministicBytes(92, 24_576);
  const globalDigest = keccak_256(globalBytes);
  const coreProofDigest = keccak_256(coreProofBytes);
  const key = statementKey(parameter, publicValues);
  const extensionBytes = (name: string): Uint8Array => Uint8Array.from((challenges[name] as number[]).flatMap((v) => [...field(v)]));
  const uniqueIndices = [...new Set(queryIndices)].sort((a, b) => a - b);
  const checkpointPayload = Uint8Array.from([
    ...globalDigest, ...t.state(), ...extensionBytes("B0.air_alpha"), ...extensionBytes("B1.zeta"), ...extensionBytes("B2.fri_alpha"),
    ...Array.from({ length: 9 }, (_, i) => extensionBytes(`B3.${i}.fri_beta`)).flatMap((v) => [...v]),
    queryIndices.length >>> 8, queryIndices.length & 255, ...queryIndices.flatMap((v) => [v >>> 24, v >>> 16, v >>> 8, v]),
    uniqueIndices.length >>> 8, uniqueIndices.length & 255, ...uniqueIndices.flatMap((v) => [v >>> 24, v >>> 16, v >>> 8, v]),
  ]);
  const cpDigest = checkpointDigest(key, checkpointPayload);
  const makeHeader = (magic: string): Uint8Array => Uint8Array.from([
    ...new TextEncoder().encode(magic), ...u16(3), 3, 9, 9, 4, ...u16(32), ...parameter, ...u16(64), ...publicValues.flatMap((value) => [...field(value)]),
  ]);
  const headerA = makeHeader("PQTCPA03");
  const headerB = makeHeader("PQTCPB03");
  const halfA = deterministicBytes(93, 4_096); const halfB = deterministicBytes(94, 4_096);
  const partA = Uint8Array.from([...headerA, ...globalDigest, ...globalBytes, ...cpDigest, ...checkpointPayload, ...halfA, 0x50, 0x41, 0x45, 0x33]);
  const id = proofId(key, partA);
  const partB = Uint8Array.from([...headerB, ...id, ...globalDigest, ...globalBytes, ...cpDigest, ...checkpointPayload, ...halfB, 0x50, 0x42, 0x45, 0x33]);
  const statementDigests = Array.from({ length: 4 }, (_, digest) => Uint8Array.from(publicValues.slice(digest * 16, digest * 16 + 16).flatMap((value) => [...field(value)])));
  const record = { parameter, statementDigests, globalDigest, coreProofDigest };
  const store = new FullDigestStore(); const storedKey = store.put(publicValues, record); store.getChecked(storedKey, publicValues, record);

  return {
    candidate, productionCompatible: candidate === "T0", challenges, claims, events: t.events, finalState: hex(t.state()),
    metrics: { ...t.metrics },
    binding: { parameterDigest: hex(parameter), statementPublicValues: publicValues, statementDigests: statementDigests.map(hex), statementKey: hex(key),
      globalBytes: hex(globalBytes), globalDigest: hex(globalDigest), coreProofBytes: hex(coreProofBytes), coreProofDigest: hex(coreProofDigest),
      checkpointPayload: hex(checkpointPayload), checkpointDigest: hex(cpDigest), syntheticPartAFrame: hex(partA), proofId: hex(id), syntheticPartBFrame: hex(partB), syntheticFramesAreCanonicalProofs: false,
      canonicalV03Continuation: canonicalContinuation,
      continuation: { halfAStart: 0, halfACount: 16, halfBStart: 16, halfBCount: 16, queryIndices } },
  };
}

interface WireEvent { type: number; payload: Uint8Array; label: string }
function validateWire(actual: WireEvent[], expected: WireEvent[]): string {
  if (actual.length !== expected.length) throw new Error(actual.length < expected.length ? "truncated claim sequence" : "trailing claim");
  for (let i = 0; i < expected.length; i++) {
    const a = actual[i]!; const e = expected[i]!;
    if (a.label !== e.label) throw new Error("claim reorder or challenge-before-claim");
    if (a.type !== e.type) throw new Error("type substitution");
    if (a.payload.length !== e.payload.length) throw new Error("item truncation or trailing zero");
    if (a.type === 1) { if (a.payload.length !== 4) throw new Error("scalar width"); field(Number(BigInt(`0x${hex(a.payload)}`))); }
    else if (a.type === 2) { if (a.payload.length !== 64) throw new Error("commitment width"); }
    else if (a.type === 3) decodeFieldArray(a.payload);
    else throw new Error("unknown item type");
    if (hex(a.payload) !== hex(e.payload)) throw new Error("claim value mismatch");
  }
  return "accepted";
}
function misuseResults(binding: Record<string, unknown>): Record<string, { outcome: string; reason: string }> {
  const expected: WireEvent[] = [
    { type: 1, payload: field(9), label: "degree" }, { type: 2, payload: commitment(1), label: "trace" },
    { type: 3, payload: encodeFieldArray([1, 2]), label: "public" },
  ];
  const mutations: Record<string, WireEvent[]> = {
    reorder: [expected[1]!, expected[0]!, expected[2]!], truncation: [{ ...expected[0]!, payload: expected[0]!.payload.slice(0, 3) }, expected[1]!, expected[2]!],
    count: [expected[0]!, expected[1]!, { ...expected[2]!, payload: Uint8Array.from([0, 0, 0, 3, ...expected[2]!.payload.slice(4)]) }],
    trailing_zero: [expected[0]!, expected[1]!, { ...expected[2]!, payload: Uint8Array.from([...expected[2]!.payload, 0]) }],
    type_substitution: [{ ...expected[0]!, type: 2 }, expected[1]!, expected[2]!],
    challenge_before_claim: [expected[0]!, { ...expected[1]!, label: "challenge" }, expected[2]!],
  };
  const out: Record<string, { outcome: string; reason: string }> = {};
  for (const [name, value] of Object.entries(mutations)) {
    try { validateWire(value, expected); out[name] = { outcome: "ERROR_ACCEPTED", reason: "validator accepted mutation" }; }
    catch (error) { out[name] = { outcome: "REJECTED", reason: error instanceof Error ? error.message : "unknown rejection" }; }
  }
  const partA = fromHex(binding.syntheticPartAFrame as string); const partB = fromHex(binding.syntheticPartBFrame as string); const id = fromHex(binding.proofId as string);
  const requirePartPair = (a: Uint8Array, b: Uint8Array, expectedId: Uint8Array): void => {
    if (new TextDecoder().decode(a.slice(0, 8)) !== "PQTCPA03" || new TextDecoder().decode(b.slice(0, 8)) !== "PQTCPB03") throw new Error("half role/magic mismatch");
    if (hex(b.slice(338, 370)) !== hex(expectedId)) throw new Error("cross-proof proof-id mismatch");
  };
  try { requirePartPair(partB, partA, id); out.half_swap = { outcome: "ERROR_ACCEPTED", reason: "accepted" }; }
  catch (error) { out.half_swap = { outcome: "REJECTED", reason: error instanceof Error ? error.message : "unknown rejection" }; }
  const mixed = partB.slice(); mixed.set(keccak_256(new TextEncoder().encode("other proof")), 338);
  try { requirePartPair(partA, mixed, id); out.cross_proof_mixing = { outcome: "ERROR_ACCEPTED", reason: "accepted" }; }
  catch (error) { out.cross_proof_mixing = { outcome: "REJECTED", reason: error instanceof Error ? error.message : "unknown rejection" }; }
  const fullParameter = fromHex(binding.parameterDigest as string, 64);
  const statementValues = binding.statementPublicValues as number[];
  const fullRecord = {
    parameter: fullParameter,
    statementDigests: (binding.statementDigests as string[]).map((digest) => fromHex(digest, 64)),
    globalDigest: fromHex(binding.globalDigest as string, 32),
    coreProofDigest: fromHex(binding.coreProofDigest as string, 32),
  };
  const store = new FullDigestStore(); const key = store.put(statementValues, fullRecord);
  const swappedRecord = { ...fullRecord, parameter: Uint8Array.from([...fullParameter.slice(32), ...fullParameter.slice(0, 32)]) };
  try { store.getChecked(key, statementValues, swappedRecord); out.digest_half_swap = { outcome: "ERROR_ACCEPTED", reason: "accepted" }; }
  catch (error) { out.digest_half_swap = { outcome: "REJECTED", reason: error instanceof Error ? error.message : "unknown rejection" }; }
  return out;
}

for (const candidate of candidates) {
  const result = run(candidate);
  const dir = `research/candidates/${candidate}`; mkdirSync(`${dir}/vectors`, { recursive: true }); mkdirSync(`${dir}/measurements`, { recursive: true });
  writeFileSync(`${dir}/vectors/transcript.json`, `${JSON.stringify({ schema: "pqtc.sp30.transcript-vector.v1", ...result }, null, 2)}\n`);
  writeFileSync(`${dir}/vectors/misuse.json`, `${JSON.stringify({ schema: "pqtc.sp30.misuse-results.v1", candidate, results: misuseResults(result.binding) }, null, 2)}\n`);
  const m = result.metrics;
  writeFileSync(`${dir}/measurements/transcript.json`, `${JSON.stringify({ schema: "pqtc.sp30.measurement.v1", candidate, classification: "BENCHMARK_ONLY",
    measured: { keccakCalls: m.keccakCalls, hashedBytes: m.hashedBytes, copiedBytes: m.copiedBytes, peakFrameBytes: m.peakFrameBytes },
    baselineFixture: { run: "research/runs/v03-fixed-01.json", partABytes: 108326, partBBytes: 103878, partACalldataBytes: 108644, partBCalldataBytes: 104228 },
    explicitlyUnmeasured: { parserGas: "NOT_EVALUATED: Solidity harness not executed in this research run", transcriptGas: "NOT_EVALUATED: Solidity harness not executed in this research run", runtimeCodeBytes: "NOT_EVALUATED: Solidity compiler not executed in this research run", deploymentCodeBytes: "NOT_EVALUATED: Solidity compiler not executed in this research run", proofBytesDelta: "NOT_EVALUATED: BENCHMARK_ONLY candidate is not encoded as a canonical proof", abiCalldataBytesDelta: "NOT_EVALUATED: no candidate canonical proof calldata exists without prohibited integration", fullPathGasDelta: "NOT_EVALUATED: canonical fixture research/runs/v03-fixed-01.json is retained, but BENCHMARK_ONLY transcript candidates are intentionally not integrated into the frozen full verifier path", memoryExpansionGas: "NOT_EVALUATED: requires EVM execution trace" },
    accounting: "Instrumentation counts both Keccak-256 invocations in K512 and all bytes presented to them. copiedBytes counts construction of the two K512 preimages and 64-byte output plus T3 encoded-item staging; it excludes caller-owned input construction, allocator internals, and EVM memory expansion. Counts cover the accepted transcript path and exclude discarded prover grinding trials." }, null, 2)}\n`);
}
