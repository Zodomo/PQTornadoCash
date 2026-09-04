# Runtime-binding assumptions

## Exact baseline

- The frozen subject is commit `00f829001999ee66da6fd5161c4c205c07d0b937`, tag `pqtc-v0.3-research-baseline`, profile `sepolia-v0.3`, and the 64-byte ID in `parameters/sepolia-v0.3/parameter-id.txt`.
- `parameters/sepolia-v0.3/manifest.json` is read, not changed. Its `expected_runtime_code_hashes` value is exactly `[]`.
- The canonical build inputs for measured bytecode are the root `foundry.toml` and root `out/<source>/<contract>.json` artifacts. The artifact metadata, rather than a prose profile name, is authoritative.
- Ethereum Keccak-256 means Keccak padding (`0x01`), not FIPS SHA3-256 padding (`0x06`). SHA-256 is used only for file identity.

## Measurement versus projection

- Artifact SHA-256, source SHA-256, creation-code size/hash, zero-filled runtime-template size/hash, immutable-reference locations, compiler metadata, and unlinked-library status are measured from existing files.
- Full initcode and constructor-resolved runtime hashes for the registry and pool are deterministic projections. They use Sepolia chain ID `11155111`, denomination `1 ether`, and the synthetic addresses in `manifest.json`; they are not observations of deployed accounts.
- AIR and query verifier runtime hashes are exact for the artifact because those contracts have no constructor arguments, link references, or immutable references.
- Registry and pool final runtime hashes are exact only for the declared projected constructor values. The extractor patches every compiler-declared immutable reference and refuses partial or extra bindings.
- Artifact AST immutable IDs are compiler-output identifiers, not stable semantic names. `immutableRoles` maps those IDs to semantic constructor fields and is checked independently.

## Candidate boundary

- Candidate Solidity files are source-only research harnesses or kernels. None has a canonical deployable Foundry artifact in scope, so no candidate runtime hash is claimed. Their source hashes are preserved as a negative result, not promoted into deployment evidence.
- No audit, cryptographic approval, network receipt, deployment authorization, proxy qualification, or security claim follows from a bytecode hash match.

## Identity model

- The frozen v0.3 parameter ID is treated as the study's legacy `proofSystemId`; this is terminology for the analysis, not a mutation of the frozen format.
- A future `deploymentManifestId` is a post-build identity. It may include `proofSystemId`, ordered runtime and full-initcode hashes, constructor arguments, chain, addresses, consumer, and compiler profile. It must not be embedded into bytecode whose hash it includes.
- Pool scope is constructor-derived storage binding `chainid`, pool address, denomination, tree depth, protocol version, and parameter ID. Registry checkpoints bind `msg.sender` as consumer. Runtime hashes alone do not prove those storage or chain facts.
