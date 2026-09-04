# Assumptions and limits

| Assumption or boundary | Status | Consequence |
|---|---|---|
| Frozen tag peels to commit `00f829001999ee66da6fd5161c4c205c07d0b937`. | Machine-checked by inventory command | A mismatch aborts before proving. |
| Plonky3 is the exact commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`. | Source-bound and inventory-checked | No branch/tag substitution is accepted. |
| q32 random-words security is 107 bits. | Conjectural | It is not reported as proven security. |
| v0.3 q32 has a 56-bit list-decoding result and a 37-bit quantum unique-decoding result. | 56-bit LDR is a conditional theorem requiring mutual correlated agreement up to the Johnson bound; 37-bit UDR is unconditional | Neither regime meets a strict proven 100-bit target; external cryptographic review remains OPEN. |
| P2BB512 behaves like the intended ideal permutation up to its generic capacity ceiling. | Unreviewed structural assumption | Independent classical/quantum cryptanalysis remains required. |
| KeccakPair512 Fiat–Shamir composition is secure in the QROM. | Unproven | No complete QROM claim is made. |
| Four random codewords and salted MMCS leaves give the intended witness hiding. | Implementation mechanism present; full proof absent | Timing, malformed-input, and composition leakage remain review items. |
| OS entropy is available to every proving process. | Runtime prerequisite | Proving aborts rather than using deterministic fallback entropy. |
| Corpus mapping's domain-separated Keccak draws are suitable for rejection sampling. | Research derivation assumption | Every noncanonical draw is retained; no modulo reduction occurs. |
| Foundry Prague execution is representative of the selected client configuration. | Benchmark assumption | Second-client execution is separately required. |
| Synthetic fixture roots may be installed without a deposit history. | Explicit harness-only relaxation | Pool-facing verification/payout is exercised, but append-only history provenance is not claimed. |
| Report fixture gas generalizes to fresh proofs. | Rejected | Fresh gas fields remain unmeasured until execution; maximum frontier/gas remains open. |
| Ethereum account/consensus security is post-quantum. | Out of scope and not assumed | The result is only a PQ-oriented application-proof experiment. |

No live note secret, signing key, public RPC, or production `.env` is an input to this package.
