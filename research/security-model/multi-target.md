# Multi-target and composition model

## Declared scenarios

Every report includes target-count logarithms 0, 20, 32, and 40. If a one-proof forgery event has bound `epsilon <= 2^-b`, the union bound over at most `T=2^t` target proofs gives

`Pr[at least one forgery] <= T*epsilon <= 2^-(b-t)`.

The calculator therefore reports `max(0,b-t)` per applicable term and for each regime. This is conservative: it does not assume independence or try to recover a birthday/occupancy improvement. A caller must choose `t` from an explicit bound on adversarially useful proof targets over the system lifetime. The `t=0` row is the ordinary single-target profile.

For the v0.3 q32 profile, quantum-adjusted regime totals are:

| log2 targets | Random words | UDR | LDR / best proven |
|---:|---:|---:|---:|
| 0 | 107.997888224 | 37.190582247 | 56.201226486 |
| 20 | 87.997888224 | 17.190582247 | 36.201226486 |
| 32 | 75.997888224 | 5.190582247 | 24.201226486 |
| 40 | 67.997888224 | 0 | 16.201226486 |

These are scenario bounds, not predictions of network volume. Negative mathematical values are clamped to zero security bits. The JSON retains `target_count_log2` on each adjusted regime and emits adjusted term tables so the affected accounting is inspectable.

## Grinding under multiple targets

Commit and query proof-of-work are credited only to their respective FRI rounds. The classical column credits all configured work bits; the quantum column credits half under the explicit Grover-style square-root model. The target union bound is then applied to the resulting per-proof term.

This model does not claim that a grind proves Fiat–Shamir security in the QROM. It also does not allow one grind to boost unrelated AIR, DEEP, batching, challenge-field, or MMCS terms. Whether work can be amortized across a concrete protocol's targets depends on transcript domain separation and is outside this calculator; using the union bound avoids silently assuming it cannot be amortized.

## Exact inner/outer and aggregate composition

A manifest may include:

```json
{
  "composition": {
    "components": [
      {"name": "inner", "count": 8, "classical_bits": 110, "quantum_bits": 100},
      {"name": "outer", "count": 1, "use_profile_result": true}
    ],
    "omissions": ["State the theorem/application gap for each supplied component here."]
  }
}
```

For component failure bounds `epsilon_i <= 2^-b_i` used `a_i` times, the calculator computes

`b_composed = -log2(sum_i a_i*2^-b_i)`.

This is exact arithmetic for the stated union bound (implemented as a scaled log-sum to avoid underflow), not the commonly used but inexact `min_i b_i`. `use_profile_result` selects this calculator's best proven UDR/LDR result, never random words. Fixed component bit values are labeled manifest assumptions. Composition remains unreviewed and inherits every component omission.

Recursive soundness often needs more than adding inner and outer acceptance errors: extraction assumptions, statement encoding, cycle/field compatibility, commitment binding across layers, and Fiat–Shamir composition may introduce additional terms. Those must be supplied as components or omissions; absent values are not treated as infinite security.
