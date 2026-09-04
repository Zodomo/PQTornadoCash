# Pinned PCS bakeoff controls

Run the three candidate packages first, one focused command at a time:

```sh
./research/candidates/C20-hvzk-whir/run-focused.sh
./research/candidates/C30-stir/run-focused.sh
./research/candidates/C40-circle/run-focused.sh
```

Then validate and aggregate their retained results:

```sh
./research/backends/pcs-bakeoff/run-focused.sh
```

An optional first argument selects the aggregate output; the default is `outputs/latest.json`. The aggregator uses clean temporary source/build staging directories, reruns each candidate result validator, cross-checks the matched C20/C30 public polynomial geometry and ZK booleans, and retains one summary JSON.

The summary intentionally contains no proof-size or timing ranking. C20/C30 share only a 4,096-element, one-point public proxy, not a complete relation or matched security model. C40 is source-watch only. All upstream measurements remain **`UPSTREAM_BASELINE_NOT_PQTC`**; none implements the frozen relation or qualifies as a PQTC measurement.

Frozen v0.3/H0 is the only faithful relation control: fixed-denomination withdrawal, binary depth-20 P2BB512-v1 tree, 16-field digest, 256×190 AIR with 1,186 constraints and degree seven, common-corpus semantics, and statement binding of scope, root, nullifier, recipient, relayer, and fee.

The aggregate has no privacy finalists and no candidates eligible for PQTC ranking. See `manifest.json`, `ADR.md`, `assumptions.md`, `status.json`, `source-hashes.json`, `negative-results.json`, and `result.schema.json`.
