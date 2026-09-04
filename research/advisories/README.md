# SP-02 — Plonky3 Advisory Applicability

## Result

**Gate: FAIL.** All five public Plonky3 advisories published by the 2026-09-04 cutoff have upstream fixes in pinned commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`, with qualifications recorded in `advisory-matrix.json`. The pinned Plonky3 README still states that native verification may panic for malformed proofs. PQTC v0.3 calls upstream verification without `catch_unwind`. Strict serialized decoding is defense in depth, not a proof that all in-memory malformed shapes are unreachable or panic-free.

This result blocks integration and security qualification. It does not block isolated `BENCHMARK_ONLY` experiments that cannot become custody code.

## Evidence table

| Advisory | Upstream affected path | Pinned status | Custom analogous path | Regression | Result | Residual risk |
|---|---|---|---|---|---|---|
| GHSA-vrmm-4mm5-38vm | Two-adic/circle PCS opening transcript order | patch `b5ec4d96` present | Rust codec checkpoint; Solidity `_observeOod` | codec roundtrip; Solidity rejection suite | patch/source order present; focused run required | every opening and cross-language challenge requires coverage |
| GHSA-m23j-cj9m-ppg9 | FRI verifier parallel-size checks | patch `367f7613` present | codec shape gate; query verifier | serialized mutations; Solidity rejection suite | explicit shape gates present; focused run required | in-memory malformed objects remain outside codec proof |
| GHSA-f69f-5fx9-w9r9 | FRI final degree and mixed-height roll-in | patch `e784f449` present | final polynomial fixed at one | codec shape; serialized mutations | v0.3 exact-length path present | future variable-arity/mixed-height designs must retest |
| GHSA-3g92-f9ch-qjcm | variable-length `PaddingFreeSponge` | patch/documentation `5c1dc1d6` present | P2BB512 and Transcript512 custom framing | typed transcript and structured mutations | not the vulnerable upstream class | explicit rate-boundary cross-language vectors remain desirable |
| GHSA-vj64-rjf3-w3v7 / CVE-2026-46654 | MultiField32 challenger packing/squeeze | mainline patch `5ac9b5ff` present | custom Transcript512, not MultiField32 | typed transcript; both digest halves; Solidity rejection suite | vulnerable class not used | partial-tail, high-bit, rejection and reachability invariants must remain explicit |
| Plonky3 malformed-proof panic known issue | native verifier | unresolved at pin | `verify_withdrawal` lacks unwind boundary | serialized mutation batch | **applicable/uncertain** | process availability and verifier API robustness |

## Reproduction

```sh
python3 research/advisories/run_regressions.py
```

The command writes `regression-results.json`, captures exact command output and hashes, and exits nonzero only when an executed defensive regression fails. The SP-02 gate remains `FAIL` while the explicit panic-containment source check is false; that expected gate result does not make successfully executed regressions fail their command.

## Scope limits

- The assessment covers public upstream advisories and the upstream malformed-proof known issue. Private/unpublished reports are not discoverable.
- RustSec advisory-db snapshot `5a0ebedfe8bdd2e295b171f4162f8c977bcad9a5` had no Plonky3 package matches.
- Advisory metadata for GHSA-f69f and GHSA-vj64 has documented commit/version ambiguity. The matrix retains it rather than inventing a clean range.
- No external reviewer has accepted the custom transcript, codec, or Solidity equivalence.
