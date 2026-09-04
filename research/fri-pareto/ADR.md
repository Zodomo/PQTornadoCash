# SP-50 C10 hiding-FRI parameter sweep

## Status

Research-only. Rejected for production selection. No row is `SECURITY_QUALIFIED`.

## Context

SP-10 accepted no compression relation. SP-50 therefore keeps the frozen v0.3/H0 `WithdrawalAir`, witness, public values, trace height 256, width 190, 1,186 constraints, degree 7, 16 quotient chunks, KeccakPair512 transcript, hiding MMCS, and exact Plonky3 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`. Only FRI blowup, query count, commit/query grinding, final-polynomial log length, and hiding random-codeword count vary.

The independent calculator's generated best-proven quantum floor is the ranking security value. Conjectural random-words values are never used as acceptance values. The 60-run C00 distribution is the only baseline for broad-grid byte/time/RSS/gas projection.

## Decision

Keep C10 as an executable research sweep, not a protocol candidate. `run.py` strictly derives calculator manifests, invokes the independent calculator for every buildable row, retains the expected buildability rejection, projects the broader grid with an explicit versioned model, and runs two OS-randomized native-proved/native-verified proofs for each anchor unless `--metadata-only` is selected.

A profile below 100 generated best-proven bits receives `SECURITY_BELOW_100`. A 100-bit profile that cannot fit the active EIP-7825 cap as one transaction receives `ONE_TX_FAIL`; if either projected A/B transaction exceeds the cap it receives `TWO_TX_FAIL`. The runner leaves `winner` null rather than relaxing the security method or transaction cap.

## Evidence policy

Anchor `measurements.json` records the exact research canonical serialization length, proof identity, proof/verification time, process peak RSS, sampled and unique query indices, and input/FRI pruned-frontier digest counts. The production A/B codec cannot accept research parameter tags, so all production-codec byte and EVM values remain explicitly `PROJECTED_BASELINE_REGRESSION_NOT_MEASURED`; they are not represented as exact calldata or execution measurements.

Active Osaka uses EIP-7623 10/40 calldata floors and the EIP-7825 `2^24` transaction gas-limit cap. The 64/64 scenario is scheduled but unactivated; 96/96 is draft and unscheduled. Both are reported only as scenarios.

## Consequences

The q32 and q48 anchors remain security failures. The calculator-minimum buildable 100-bit point is blowup 3, q111 under the generated proven method, but transaction feasibility can still reject it. External cryptographic review, QROM/Fiat-Shamir review, MMCS analysis, transcript review, correlated-agreement review where applicable, and advisory closure remain mandatory and unresolved.
