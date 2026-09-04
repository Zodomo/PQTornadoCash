# SP-10 hash-compression measurement package

This standalone research crate and its Solidity/TypeScript mirrors measure H0–H7 without changing v0.3 custody code. No artifact or speed result grants a security-qualified label.

## Reproduce

- Generate raw vectors temporarily, run TypeScript/depth-20/Solidity parity, package deterministically with zstd, and delete raw JSON: `python3 research/candidates/hash-compression-common/run.py vectors-parity`
- Decompress and re-hash the retained package against its uncompressed-content and compressed-artifact digests: `python3 research/candidates/hash-compression-common/run.py vectors-package-check`
- Native diagnostic timings plus Solidity gas/size suite: `python3 research/candidates/hash-compression-common/run.py benchmark --samples 1000`. The 1,000-sample native output is `DIAGNOSTIC_NOT_COMMON_PROTOCOL`, not comparable benchmark evidence.
- Independently regenerate and compare constants: `python3 research/candidates/hash-compression-common/scripts/compare-constants.py --plonky3 /path/to/Plonky3`

The constants checkout must be exactly `3152b14a89067c83775a8076cc262ffc48a1fd7c`. Solidity measurements use the canonical profile: solc 0.8.30, Prague EVM, optimizer enabled with 200 runs, and via-IR enabled. Raw vector JSON exists only while parity runs; the retained deterministic artifact is `vectors/cross-language.json.zst`, described by `vectors/package.json`. Native diagnostic samples are below `native/`; they have no warmup, p90, p99, or standard deviation and contain less than 10 seconds of measured work, so they are not common-protocol comparisons. Candidate-named machine-readable gas and size values are in `gas/results.json`, and raw Forge gas-report output is in `gas/forge-gas-report.txt`. `measurement-hashes.json` binds the uncompressed vector content, compressed vector artifact, and other retained outputs with SHA-256 and Ethereum Keccak-256. Source corpus files are read-only inputs.

## Coverage limits

Rust and TypeScript matched all 18,146 retained vector records. Solidity parity covers only 8 suite-wide anchor vectors, not the required 10,000; full 18,146-vector three-language parity and the required misuse suite are `NOT_EVALUATED`. The earlier constant-comparison run is `NOT_RETAINED`.

Non-H0 note/nullifier names denote primitive/layout microbenchmarks only. Those payloads omit protocol scope and use candidate-output-width placeholders rather than the frozen semantic secret/trapdoor widths. Scope, empty-leaf, and statement roles are `NOT_EVALUATED`, so no complete application-role parity is claimed. `ResearchTree.syntheticDepth20RootUpdate` is likewise not a direct deposit: it performs 20 hashes and updates a dynamic `uint256[]` root while omitting real deposit/state work and the protocol's two-slot digest representation. Complete non-H0 direct-deposit gas is `NOT_EVALUATED`; the separately reproduced frozen H0 direct deposit is 13,991,021 gas.

## Canonical encoding

Field lanes are unsigned canonical integers. Digest bytes concatenate each lane as four-byte big-endian. Artifact hashes are SHA-256 and Ethereum Keccak-256 (not NIST SHA3-256). Candidate byte inputs use `SHA256("PQT-SP10-H2F-RS-v1" || len(label) || label || len(source) || source || element-index || counter)`; the first four digest bytes are interpreted big-endian and rejected when they are at least the field modulus. Every accepted and rejected draw is retained. Supplied retry triggers apply the same first-u32 rule in order, replace the first mapped lane of their named target on acceptance, and retain an explicit mapping failure while omitting that application case when all supplied draws reject.

Poseidon compression is exactly `Trunc_d(P(x)+x)`, first lanes only. Application-capable compressors place `left-or-first payload || right-or-second payload || role/domain || protocol-version || shape || level`; each control is a separate field. The role value is the application-domain identifier, not a second packed field. The layout is injective because role/domains are distinct, version is explicit, shape is the exact payload lane count, node level is explicit, and no variable-width concatenation is accepted. H3 uses all 24 lanes, H5 leaves four fixed zero lanes, and H6 uses all 32 lanes. H1 and H4 application roles stop rather than pack controls.

H7 preserves the published RPO-M31 sponge: width 24, rate 16, capacity 8, seven rounds plus concluding linear/constants step. Zero padding and the published 16-way final-block-length domain in state lane 16 are used. Application framing is an absorbed message, not a feed-forward compressor.
