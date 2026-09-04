# ADR: bound v0.3 proof length from query sets, not sampled proof sizes

## Status

Accepted for this research package.

## Context

The v0.3 codec stores fixed-shape opened values and salts but variable-length pruned MMCS frontiers. The engineering report measured one proof, and the baseline reproducer retained 60 more. Sampling alone cannot establish the maximum accepted proof length because transcript-derived query indices can collide or share ancestors differently in each ordered 16-query half.

## Decision

Model the Rust `prune_paths` algorithm exactly. For a distinct query set `S` and `U_l = |{i >> l : i in S}|`, count missing siblings at level `l` as `2U_{l+1} - U_l`. Apply that count three times to the height-13 input trees and once to every applicable FRI tree after its query-index shift.

Use an exhaustive binary-tree dynamic program over every feasible left/right occupancy split for 1 through 16 distinct leaves. This proves the frontier extrema without enumerating `choose(8192,16)` sets. Independently evaluate concrete witnesses with the direct `prune_paths`-equivalent calculator. Parse every retained proof and the report fixture, require encoded frontier counts to equal the index-derived counts, and require the complete byte ledger to equal the file length.

Keep gas evidence in three classes:

1. exact measured retained calldata and matching execution trace;
2. exact derived byte length and standard/active floor bounds;
3. explicitly projected uniform 64/96 byte floors.

Do not attach sampled execution to a theoretical-extreme frontier.

## Consequences

The exact per-half frontier range is 93 to 1,008 64-byte digests. With the checkpoint unique-index term included, the exact pair maximum is 224,108 raw proof bytes; maximum ABI call sizes are 112,356 bytes for A and 112,420 bytes for B. This upper bound covers every query sequence encodable under the frozen 32-query, 16/16, 13-bit geometry.

The size bound does not rescue the active transaction gate: exact baseline traces show 9 of 60 A transactions above the `2^24` specified-gas-limit cap and no B breaches. Conversely, a byte-only 64/96 floor below the cap does not establish a full-transaction pass because execution was not measured at the theoretical frontier maximum.

## Rejected alternatives

- Treat the report's 210,284-byte proof as representative or maximal: rejected; its half frontiers are 851 and 949, neither is the theoretical maximum.
- Bound each of 16 authentication paths independently by its height: safe but not exact and ignores canonical pruning.
- Use the codec's defensive `MAX_PATH_HASHES = 4096` per frontier as the proof maximum: rejected; `split_queries`/`expand_paths` constrain a valid frontier to the queried tree, so that decoder allocation guard is not an encodable-proof frontier.
- Infer execution gas from proof length alone: rejected; byte values and query collision structure affect calldata and verifier work.
