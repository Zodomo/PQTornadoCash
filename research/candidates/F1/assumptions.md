# F1 assumptions

- Modulus: `2130706433`; challenge construction: `x^4 - 3`.
- Canonical base width is 4 bytes; extension width is 16 bytes. Raw vectors are fixed-width big-endian; ABI uses one 32-byte word per coefficient.
- The deterministic input mixer is specified in `vectors.json`; it is not a randomness or entropy source.
- Challenge cardinality is approximately 123.954738750 bits (floor 123). The reported conservative entropy budget is only that cardinality floor, not a FRI, Fiat-Shamir, hiding, QROM, or complete-proof bound.
- Base/challenge two-adicity is 24/26. Domain feasibility still depends on the selected backend and blowup.
- Opened-row floors use 190 columns and EIP-2028 byte prices (4 gas zero, 16 gas nonzero), with no envelope, authentication, FRI, memory, or intrinsic transaction cost.
- The 256-row frozen geometry and any explicitly supplied SP-20 geometry are relation inputs, not evidence that the relation was ported.
- No public network, RPC, `.env`, live key, classical wrapper, or alternate encoding is used.
