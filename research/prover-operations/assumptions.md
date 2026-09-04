# SP-73 assumptions and evidence boundaries

| ID | Statement | Treatment |
|---|---|---|
| A-01 | The only analyzed source runs are `research/runs/v03-{corpus,fixed}-01..30.json`. | Enforced as an exact 60-ID set. |
| A-02 | `benchmark-run.schema.json` is the authoritative schema for those records. | Every record is validated with the committed focused validator. |
| A-03 | The records describe the frozen v0.3 baseline at commit `00f829001999ee66da6fd5161c4c205c07d0b937`; they are not SP-73 reruns. | Candidate, source spike, commit, and success fields are checked. |
| A-04 | Hardware H1/H2/H3 labels are measurement classes, not hash-candidate identifiers. | No inference is made from `research/candidates/H1`, `H2`, or `H3`. |
| A-05 | All 60 source records are warm measurements. | Enforced from `prover.cold_or_warm`; no record is relabeled cold. |
| A-06 | The H1 hardware profile and source records refer to the same hardware class despite their different identifier strings. | Only architecture, CPU model, physical/logical core counts, and RAM are required to match. |
| A-07 | NEON is present on the H1 hardware. | Supported by the hardware profile. A NEON-specific executed code path is not assumed because run-level `cpu_features` is empty and `target_features` was not retained per run. |
| A-08 | Peak RSS is the source runner's `/usr/bin/time` observation. | Reported as measured; allocation totals, pressure behavior, and swap are not inferred. |
| A-09 | The eight artifact sizes in each record are retained disk bytes. | Sizes and SHA-256 are checked against files. This is not peak workspace or cache usage. |
| A-10 | Raw proof bytes are the sum of retained A/B proof files; ABI calldata bytes are the sum of retained A/B calldata files. | Enforced. These are payload sizes, not measured network transfers. |
| A-11 | `trusted_setup=false` means the proof system has no trusted setup. | It does not establish setup/precomputation time or cache size. |
| A-12 | H2 and H3 were unavailable in the committed environment. | Both remain `NOT_EVALUATED`; no projection from H1 is allowed. |
| A-13 | Scalar, AVX2, AVX-512, WASM, cancellation, progress, memory pressure, and crash recovery have no retained evidence. | Each remains `NOT_EVALUATED`. |
| A-14 | The baseline generator is a destructive, batch research command. | It is reproducible evidence plumbing, not a practical product CLI. |
| A-15 | The baseline README states the retained local t8n route does not contact RPC. | This does not establish privacy for a deployed note/path/RPC workflow. |
| A-16 | Cross-user aggregation never needs or receives private witnesses. | Only proofs and public statements may cross that boundary. |
| A-17 | No proving service proposal is accepted. | Witness isolation, attestation, telemetry, and production local fallback remain open until implemented and reviewed. |
| A-18 | The analyzer's p90/p95/p99 are nearest-rank statistics; mean and population standard deviation are Decimal-derived and rounded half-even to 12 places. | The policy is deterministic and recorded in the manifest. |
| A-19 | No Solidity is built in this package. | Any future Solidity-side measurement must use solc 0.8.30, Prague, optimizer 200, and via-IR. |
| A-20 | This study is operational evidence only. | It does not provide cryptographic acceptance, finalist selection, live-chain evidence, or external review. |
