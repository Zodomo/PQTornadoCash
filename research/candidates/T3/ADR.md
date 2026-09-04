# T3: challenge-boundary frame

## Decision

T3_EXTERNAL_REVIEW_ONLY. Independent review permits external study only and blocks integration: candidate APIs lack a claim/boundary state machine, mutation/parity evidence is incomplete, and the full-width continuation redesign is not implemented.

## Context

Typed claims are framed and flushed once immediately before each challenge boundary. The exact intended claim order and challenge boundaries are recorded in `../../cryptanalysis/transcript/SPEC.md`. The comparison is frozen v0.3 at Plonky3 `3152b14a89067c83775a8076cc262ffc48a1fd7c`.

## Measured consequences

The focused runner records candidate-named Solidity prefix transcript gas, strict-parser gas, bytecode sizes, calldata, Keccak, hash-input, copy, and continuation-size observations under the canonical research profile. Full verifier-path gas remains explicitly `NOT_EVALUATED`.

## Independent internal review

Verdict: `T3_EXTERNAL_REVIEW_ONLY` with high confidence. Integration is blocked for every candidate. The Rust, Solidity, and TypeScript primitive APIs expose absorb/sample directly without enforcing the normative claim/boundary state machine, so callers can request a premature challenge. The TypeScript misuse oracle validates out-of-band labels rather than malformed serialized grammar. Rust/Solidity mutation execution and cross-language parity execution are absent. The proposed full-width continuation redesign is not implemented: identifiers remain bytes32, the Solidity key maps to one overwriteable slot, and its record comparison adds another Keccak digest rather than comparing an authoritative collision-safe representation. The recorded full-width values and exact T0 replay are research evidence, not proof that these blockers are resolved.

## Security disposition

`BENCHMARK_ONLY`. No custody package imports this code. No soundness, QROM, zero-knowledge, collision-composition, deployment-safety, or full-width continuation claim is approved. External review is the maximum permitted next step; integration remains closed.
