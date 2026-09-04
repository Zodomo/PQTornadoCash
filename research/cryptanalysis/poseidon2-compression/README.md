# Poseidon2 compression cryptanalysis packet

`packet.json` is the complete SP-10 handoff for independent review. It does not self-award review, security, or deployment eligibility. The exact object is first-lane `Trunc_d(P(x)+x)` with pinned Plonky3 constants; Plonky3 `TruncatedPermutation` is outside scope because it omits feed-forward.

The packet distinguishes reported attacks from breaks, assumptions from theorems, exact H1/H3/H4 applicability from uncertain width-32 extrapolation, and generic BHT/Grover ceilings from qualification. H2 remains a no-code stop. Any matrix, lane ordering, round count, constant, feed-forward, or packing change requires a new packet.
