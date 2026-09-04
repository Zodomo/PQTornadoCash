# C40 assumptions

- The source-watch scope is the authoritative pinned Plonky3 commit and `circle/src/pcs.rs`; absence claims are bounded to that source and the frozen landscape cutoff.
- `CirclePcs` upstream native prover/verifier availability does not imply a comparable PQTC lower bound.
- Frozen v0.3/H0 uses BabyBear and a two-adic AIR. Translating it to a `ComplexExtendable` Circle field is a relation change and is not authorized after SP-10 accepted no candidate.
- A non-hiding Circle run could never qualify as a privacy finalist. Randomized trace encoding described by a paper is not treated as an implemented noninteractive hiding PCS.
- No local ZK wrapper, transcript theorem, field bridge, or EVM verifier may be invented by this watch package.
- The focused command is a source/pin check and produces no proof, timing, proof-size, RSS, or PQTC measurement.
