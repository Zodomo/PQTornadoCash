import { Transcript } from "../../../cryptanalysis/transcript/typescript/transcript.ts";

export const CANDIDATE = "T3" as const;
export function createTranscript(parameterDigest: Uint8Array, publicValues: number[]): Transcript {
  return new Transcript(CANDIDATE, parameterDigest, publicValues);
}
