# v0.3 proof-length and pruned-frontier study

This package derives the proof-size frontier of the frozen v0.3 codec, parses all 60 retained baseline proofs plus the engineering-report fixture, and separates measured execution from exact byte arithmetic and future-floor projections. It changes no production code.

Run the deterministic audit from the repository root:

```sh
python3 research/proof-length/check.py
```

Regenerate `results.json` and `source-hashes.json` with `--write`. The checker uses only the Python standard library. It rejects malformed structure, recomputes every encoded frontier count from the checkpoint indices, reconciles every ledger with the exact file length, checks retained metadata/calldata/trace values, runs an exhaustive tree dynamic program, and performs five parser mutations.

## Exact geometry

The source-fixed production shape is:

- 32 transcript-derived 13-bit indices, split by query position 16/16;
- proof degree bits 9 and log blowup 4, hence height 13;
- three input batches: `(1 matrix × 8 fields)`, `(1 × 194)`, and `(16 × 8)`;
- nine binary FRI rounds with committed tree heights 12, 11, ..., 4;
- four random codewords, eight BabyBear salt elements per opened matrix row;
- 64-byte commitment/frontier digests and 16-byte extension elements.

Duplicate query positions are preserved in the fixed opened data but deduplicated by index when `prune_paths` builds a frontier. A and B prune independently, so equal indices in opposite halves do not share frontier bytes.

## Frontier formula and exhaustive bound

For a nonempty distinct-index set $S \subset [0,2^h)$, define

$$U_l(S)=\left|\{i \mathbin{\mathtt{>>}} l:i\in S\}\right|.$$

At level $l$, `prune_paths` emits one digest for every occupied parent with exactly one occupied child. The exact count is $2U_{l+1}-U_l$, so

$$F_h(S)=\sum_{l=0}^{h-1}(2U_{l+1}-U_l)=2+\sum_{l=1}^{h-1}U_l-U_0.$$

For one 16-position half, with duplicates removed by the set operation,

$$T(S)=3F_{13}(S)+\sum_{r=0}^{8}F_{12-r}(\{i\mathbin{\mathtt{>>}}(r+1):i\in S\}).$$

Equivalently,

$$T=24-3U_0+2U_1+3U_2+4U_3+5U_4+6U_5+7U_6+8U_7+9U_8+10U_9+12U_{10}+12U_{11}+12U_{12}.$$

`check.py` does not assume that the obvious witnesses are optimal. Its dynamic program recursively tries every feasible distribution of $n=1,\ldots,16$ occupied leaves between the two children at every one of 13 tree levels, for both minimum and maximum. Direct codec-equivalent evaluation of witnesses independently reaches the DP extrema:

| Half extreme | Initial index pattern | Input frontier, each of 3 | FRI frontiers by round | Total $T$ |
|---|---|---:|---|---:|
| Minimum | aligned complete subtree `0..15` | 9 | `9,9,9,9,8,7,6,5,4` | 93 |
| Maximum | one index in each 512-leaf block, `0,512,...,7680` | 144 | `128,112,96,80,64,48,32,16,0` | 1,008 |

For the pair maximum, B can use a second distinct leaf in each 512-leaf block. Both halves then attain 1,008 while the checkpoint contains 32 unique indices. Therefore the upper bound does not understate any proof encodable by this geometry. The codec's defensive 4,096-hash reader limit is not reachable by a valid pruned frontier and is not used as a loose substitute.

## Exact byte ledger

Let $u$ be the number of unique indices among all 32 checkpoint queries and let $T_A,T_B$ be the half frontier totals. Every raw byte is assigned below; `other_unknown` is zero.

| Component | A bytes | B bytes |
|---|---:|---:|
| Format magic, version, profile, shape | 16 | 16 |
| Parameter binding | 64 | 64 |
| Public statement count and 64 fields | 258 | 258 |
| Part-A proof-ID binding | 0 | 32 |
| Global digest | 32 | 32 |
| Three commitment roots | 192 | 192 |
| OOD openings | 7,168 | 7,168 |
| Masking/hiding openings | 1,216 | 1,216 |
| Nine FRI commitments | 576 | 576 |
| Commit/query grinding witnesses | 40 | 40 |
| Final polynomial | 16 | 16 |
| Checkpoint digest/state/challenges | 320 | 320 |
| Checkpoint query and unique-index lists | $132+4u$ | $132+4u$ |
| Half header and 16 indices | 68 | 68 |
| Three batches of input rows | 21,120 | 21,120 |
| Input and FRI MMCS salts | 13,824 | 13,824 |
| Twelve frontier length prefixes | 48 | 48 |
| Nine rounds of FRI sibling values | 2,304 | 2,304 |
| Frontier digests | $64T_A$ | $64T_B$ |
| End marker | 4 | 4 |

Thus

- `checkpoint = 452 + 4u`;
- `half including end = 37,368 + 64T`;
- `part A = 47,398 + 4u + 64T_A`;
- `part B = 47,430 + 4u + 64T_B`;
- A ABI calldata is `292 + 32*ceil(A/32)`;
- B ABI calldata is `324 + 32*ceil(B/32)`.

The exact codec extrema, including a jointly feasible checkpoint uniqueness count, are:

| Bound | A raw | B raw | Pair raw | A ABI | B ABI | Pair ABI |
|---|---:|---:|---:|---:|---:|---:|
| Minimum | 53,414 | 53,446 | 106,860 | 53,732 | 53,796 | 107,528 |
| Maximum | 112,038 | 112,070 | 224,108 | 112,356 | 112,420 | 224,776 |

The minimum pair uses the same aligned 16-index subtree in both halves ($u=16$). The maximum pair uses two distinct leaves per 512-leaf block ($u=32$).

## Parsed evidence

All 60 retained proof pairs passed structural parsing, checkpoint/half consistency, exact frontier recomputation, and byte-ledger reconciliation. Their baseline metadata records 60 native-verification passes and 60 codec-roundtrip passes. The checker also matches every retained ABI calldata length and standard intrinsic value to its Foundry trace.

| Quantity | Observed minimum | Observed maximum |
|---|---:|---:|
| A frontier digests | 741 (`v03-fixed-19`) | 959 (`v03-fixed-03`) |
| B frontier digests | 722 (`v03-fixed-06`) | 978 (`v03-fixed-10`) |
| A raw bytes | 94,950 | 108,902 |
| B raw bytes | 93,762 | 110,150 |
| Pair raw bytes | 198,052 (`v03-fixed-06`) | 213,804 (`v03-corpus-08`) |
| A ABI bytes | 95,268 | 109,220 |
| B ABI bytes | 94,116 | 110,500 |

The report fixture parses as A = 101,990 bytes with 851 frontier digests and B = 108,294 bytes with 949, totaling 210,284. It is neither the observed nor theoretical maximum. Among the retained full 32-query schedules, `v03-corpus-22`, `v03-fixed-06`, and `v03-fixed-25` each contain one exact query-index collision (31 unique indices); the other 57 have 32 unique indices. `results.json` records every half's distinct-node/collision profile after shifts 0 through 12 and aggregate collision counts across all 120 halves.

## Intrinsic and calldata floors

For exact retained calldata, standard intrinsic and active EIP-7623 floors count actual zero/nonzero bytes. Uniform 64/96 scenarios are byte-only projections.

| Quantity | Observed minimum | Observed maximum |
|---|---:|---:|
| A standard intrinsic | 1,536,204 | 1,758,836 |
| B standard intrinsic | 1,517,352 | 1,778,140 |
| A active EIP-7623 floor | 3,809,010 | 4,365,590 |
| B active EIP-7623 floor | 3,761,880 | 4,413,850 |
| A uniform 64 floor | 6,118,152 | 7,011,080 |
| B uniform 64 floor | 6,044,424 | 7,093,000 |
| A uniform 96 floor | 9,166,728 | 10,506,120 |
| B uniform 96 floor | 9,056,136 | 10,629,000 |

At the exact theoretical maximum, the byte-only 64/96 floors are 7,211,784/10,807,176 for A and 7,215,880/10,813,320 for B. Actual-byte standard intrinsic lies between 470,424 and 1,818,696 for A and between 470,680 and 1,819,720 for B; the active floor lies between 1,144,560 and 4,515,240 for A and between 1,145,200 and 4,517,800 for B. These intervals are exact all-zero/all-nonzero bounds, not claims that either byte distribution can form a valid proof.

## Transaction/proof-size gate

The exact proof-size gate passes: no v0.3 proof under the frozen geometry can exceed 112,070 raw bytes in one part, 112,420 bytes in one ABI call, or 224,108 raw bytes across both parts.

The active full-transaction gate fails on measured evidence. Combining each retained call only with its own measured execution and exact calldata shows 9/60 A calls above the 16,777,216 EIP-7825 cap and 0/60 B calls above it. The A breach records are:

`v03-corpus-13`, `v03-corpus-26`, `v03-corpus-29`, `v03-fixed-02`, `v03-fixed-03`, `v03-fixed-07`, `v03-fixed-16`, `v03-fixed-18`, and `v03-fixed-28`.

No theoretical-maximum-frontier transaction was executed. Consequently the theoretical active and 64/96 entries remain byte/floor results only; they do not establish a full-transaction pass or failure after execution. For each retained proof only, `results.json` also reports projected uniform-64/96 gas used as the maximum of that exact call's measured regular total and its scenario floor; these same-artifact combinations are projections, not measurements under a future fork. The canonical report's full ABI calldata is not retained beside its raw proof files, so its report gas values are preserved as measurements rather than reconstructed.

See `results.json` for all per-proof ledgers, indices, collision profiles, frontier counts, byte distributions, floors, measured transactions, DP states, mutations, and gate labels.
