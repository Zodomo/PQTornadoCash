# SP-30 transcript construction bake-off

## Decision

Independent internal-review verdict: `T3_EXTERNAL_REVIEW_ONLY`. T3 may be studied externally but no T0–T3 candidate may be integrated. T0 remains the exact production-compatible measurement control, T1 is not selected, and T2 is rejected on instrumented efficiency. All four remain `BENCHMARK_ONLY`.

## Basis

The pinned v0.3 prover and verifier absorb the instance and trace/public claims before `air_alpha`, quotient/random commitments before `zeta`, claimed openings before FRI batching `alpha`, each FRI commitment and PoW witness before its folding `beta`, and final polynomial/log arities/query witness before query indices. `SPEC.md` fixes this order and makes every challenge boundary non-crossable. Deterministic runs record state after every logical absorb and challenge squeeze and rejection outcomes for all required misuse classes.

The deterministic TypeScript graph gives T0/T1/T2/T3 K512-call counts of 4,428/126/220/58. The focused Solidity run under solc 0.8.30, Prague, optimizer 200, and via-IR measured B0-prefix transcript gas of 287,425/167,799/178,264/166,554 and strict-parser gas of 1,468/1,462/1,463/1,463. It also records 5,486-byte initcode and 5,460-byte runtime code. These standalone-prefix observations support advancing T3 to review but do not establish deployment savings: EVM memory expansion and the integrated full-verifier gas delta remain explicitly unevaluated.

## Binding decision

The research target requires full-width parameter, statement, global, checkpoint, core-proof, and A/B values while permitting only a 32-byte lookup index. The vectors retain those full values, but the implementation does not complete that redesign: proof/checkpoint identifiers remain `bytes32`, and the Solidity store does not provide collision-safe multi-record handling or direct authoritative comparison. No full-width continuation security claim is accepted.

## Independent internal-review blockers

The high-confidence review found that the Rust, Solidity, and TypeScript APIs are transcript primitives, not claim/boundary state machines: direct sample calls can occur before required claims. The TypeScript misuse oracle rejects generator-side labels rather than malformed serialized grammar, and there is no Rust/Solidity mutation execution or cross-language parity run. The full-width continuation redesign is not implemented: IDs remain `bytes32`; the Solidity mapping has a single overwriteable slot per key; and record comparison is mediated by another Keccak digest. Full-width vector presence and exact T0 replay do not resolve these issues. They are explicit integration blockers, not follow-up polish.

## Security limits

No candidate carries a QROM proof or an independent Fiat–Shamir composition analysis. Hash-call reduction is not a security argument. Unknown types/versions, noncanonical fields, malformed counts/lengths, trailing bytes, claim reordering, premature challenge requests, digest-half swaps, proof-half swaps, and cross-proof mixing must all reject before verification. External review must assess the frame grammar, the state/output reset rule, domain separation, and the exact graph before any further gate.
