# Parameter manifest to runtime-bytecode binding

## Conclusion

**v0.3 is not deployment-ready.** The frozen `parameters/sepolia-v0.3/manifest.json` has `expected_runtime_code_hashes: []`. The four hashes below are reproducible evidence for the current canonical Foundry artifacts and a clearly labeled synthetic constructor/address projection; they do not repair or replace the frozen manifest, identify deployed accounts, or authorize deployment. Research candidate Solidity kernels have source hashes but no canonical deployment artifacts, so they are also not runtime-bound.

Run from the repository root:

```sh
python3 research/runtime-binding/binding.py extract
python3 research/runtime-binding/binding.py check
python3 research/runtime-binding/binding.py regressions
```

`extract` reads canonical Foundry contract JSON (`bytecode.object`, `deployedBytecode.object`, link/immutable references, and parsed metadata). `check` compares every source, artifact, profile, size, constructor word, immutable value, and expected hash. `regressions` makes in-memory corruptions and requires all eight negative cases to fail. `results.json` and `negative-results.json` are the checked machine-readable outputs.

## Exact artifact measurements and explicit projection

The build is solc `0.8.30+commit.73712a01`, optimizer enabled with 200 runs, via-IR enabled, Prague EVM, `bytecodeHash=none`, and remapping `forge-std/=lib/forge-std/src/`. Artifact and source SHA-256 values are in `manifest.json`, `results.json`, and `sources.json`.

| Ordered role | creation code bytes / Keccak-256 | constructor bytes | full initcode Keccak-256 | runtime bytes | runtime Keccak-256 |
|---|---:|---:|---|---:|---|
| `PQTCAirStageVerifier` | 17,831 / `0x37915c35be7e18b69fdf9ce79054282b7a8e083a1d54539c0f43d22a3245db6b` | 0 | same as creation code | 17,805 | `0xa7102ce1827cd3aa56517a5e0e68d5e7e19501580bf3c21a3085b2a55833a4a6` |
| `PQTCQueryVerifier` | 12,982 / `0x2e8eb0896ddd0579783af4b81ecff5956bc3fffb81c84357b5047701b07d63bd` | 0 | same as creation code | 12,956 | `0x87d61698f9756e4bea73afdb15b1bf877b550a421ea9a9a4306a3c7776a874ae` |
| `PQTCVerificationRegistry` | 13,517 / `0x793cbe675ad2a27f74172de8a268407d3f63b3d54db5b5ee5cba22058ab7de2e` | 128 | `0x6dbb50bf5409e2abd975821607a45e09036871e602e831e59387be53715439cc` | 13,123 | `0xbdfc33817e83d249367a1e0351ecebec47763afe9708383d9f07a0cc137beb60` |
| `PQTCClassicPool` | 12,872 / `0x9e46b300a782bc55f966b284d267f4a85853a33bbbf88196518ae64daf9d919a` | 128 | `0xa1e60c4d18c788eecdfeb98d1752114277f5bbe10182e4185add554e457dbe89` | 7,548 | `0xa6cd9d3a47850a451ecf79e6ad2d6f46dd8d3b56f4ea7f252e2759da89d5e4a2` |

The AIR/query figures are measured directly because neither artifact has constructor arguments, link references, or immutable references. Registry/pool creation-code and template facts are measured; their full-initcode and final-runtime hashes are projections using the exact ABI words in `manifest.json`: frozen parameter ID, `1 ether`, and synthetic AIR/query/registry addresses. Those addresses are not claimed deployments. Their zero-filled runtime-template hashes are separately retained so a template can never be mistaken for deployed code.

## Why the byte strings differ

- **Creation code** is `bytecode.object`: constructor machinery plus the code that returns runtime. Its hash does not include ABI constructor arguments.
- **Full initcode** is creation code concatenated with ABI constructor arguments. `CREATE2` hashes this full byte string. Registry and pool therefore differ from their bare creation-code hashes.
- **Runtime template** is `deployedBytecode.object` before constructor immutable substitution. Foundry/solc provides exact byte offsets in `immutableReferences`; hashing the zero-filled template is not a deployed-code hash.
- **Final runtime** is the template with every immutable reference patched to the constructor value. Registry embeds the two parameter-ID halves and AIR/query addresses. Pool embeds denomination and registry address. The parameter ID and scope are also written to pool storage; storage is not covered by `EXTCODEHASH`.
- **Constructor execution** can initialize storage using `chainid`, `address(this)`, or other context without changing runtime bytes. Consequently equal runtime hashes do not establish equal pool scope or equal initialized state.

## Compiler, metadata, and linking boundary

Bytecode identity is a full-build identity. Solc version/build, source contents and paths, optimizer mode and run count, optimizer details, via-IR, EVM revision, remappings, library mode, and metadata settings can all alter output. Compiler metadata is embedded at the end of bytecode unless disabled or changed; IPFS metadata and `bytecodeHash=none` are not interchangeable. The checker compares parsed artifact settings and the profile file SHA-256 rather than trusting a profile label.

The current four artifacts have empty creation/runtime `linkReferences`: their libraries are internal/inlined. A future external library leaves placeholders until linking. The checker rejects any non-empty link-reference map rather than hashing a placeholder. A future manifest must record each fully qualified library name, linked address, linked creation/runtime output, and the library account's runtime hash. Relinking is a new deployment identity.

## Chain, scope, and consumer binding

The pool constructor derives `scope` from `block.chainid`, `address(this)`, denomination, depth, protocol version, and parameter ID. Thus a runtime match on another chain/address does not reproduce the public statement. The registry derives checkpoint IDs from `msg.sender` and later requires the same consumer for completion, but it does **not** restrict starts to the pool; arbitrary callers receive separately namespaced checkpoints. The pool address is not a registry immutable. A valid deployment record must therefore bind and exercise the intended pool-as-consumer relationship, not merely list two matching accounts. Checks after deployment must include:

1. exact chain ID and ordered role/address mapping;
2. transaction input/full initcode and constructor ABI words;
3. receipt creator/factory and CREATE/CREATE2 derivation;
4. post-construction code hash and code size at every address;
5. pool denomination, parameter ID, registry, scope, and initial root/state invariants;
6. registry parameter halves, AIR/query addresses, and an exercised consumer-bound checkpoint path.

## Two-layer identity and no cycle

The architecture selected in `ADR.md` separates a protocol-facing `proofSystemId` from a post-build `deploymentManifestId`. The proof-system identity can bind parameter-independent stateless verifier sources/code, but it must not contain the hash of parameter-bound registry/pool runtime that embeds that same ID. Compilation and constructors consume `proofSystemId`; chain/deployer/salt determine addresses; the final deployment identity consumes all outputs. It is never fed back into them.

For the synthetic packet, canonical sorted compact JSON under domain `PQTC_DEPLOYMENT_MANIFEST_V1` hashes to projected `deploymentManifestId`:

`0x58be54c792f8d46e132326e7d9edf18a9bbd26f488b18d42a5930f55d86f252b`

This ID is reproducible, but not deployable evidence because its addresses are synthetic and the frozen v0.3 list remains empty.

## Factory, CREATE2, codehash, registry, and upgrades

- Plain `CREATE` plus a post-deployment codehash is workable only with creator/nonce/address, full initcode, receipt, constructor arguments, and initialized-state checks. Codehash alone loses all constructor-only effects.
- `CREATE2` usefully binds factory, salt, and full-initcode hash to the address. It still does not establish the returned runtime or initialized storage; both must be checked. Chain ID is absent from the CREATE2 formula, so the manifest must state the chain.
- A profile-enforcing factory can reject wrong order/args/codehash and emit evidence. It enlarges the reviewed surface. Its own runtime and authority must be bound; a mutable admin defeats permanence.
- An on-chain registry can map `(chainId, proofSystemId, consumer)` to one deployment manifest and ordered accounts. If an admin can rewrite it, that action is a protocol trust upgrade. Timelock/multisig governance is visible mutability, not immutable identity.
- A proxy codehash identifies only proxy code. It does not bind implementation/beacon/admin/storage. Default deployment should use immutable direct contracts. Any authorized implementation change requires a new deployment manifest ID and explicit consumer cutover; never silently retain the old identity.

## Candidate result

T0–T3 transcript candidates, common field/hash/Merkle/verifier harnesses, and transcript-cryptanalysis Solidity are hashed as sources. None has an accepted canonical deployment artifact, exact constructor plan, or reviewed integration. The checker preserves `SOURCE_ONLY_NO_CANONICAL_FOUNDRY_ARTIFACT` for every entry. A candidate may enter a future deployment manifest only after clean integration produces the same artifact evidence required of all four v0.3 roles.

## Required future clean cutover

A future manifest must be non-empty and bind, in canonical order:

- protocol/relation/field/PCS/transcript/codec/interface identity (`proofSystemId`);
- exact source tree or reproducible source hashes and dependency lock;
- solc build, Foundry version/profile, optimizer details/runs, via-IR, EVM revision, metadata mode, remappings, and linked libraries with addresses/codehashes;
- creation code, exact ABI constructor arguments, full initcode, immutable-reference resolution, final runtime bytes/hash, and size per role;
- chain ID, factory/deployer, CREATE or CREATE2 nonce/salt derivation, ordered role addresses, denomination, consumer relation, and initialized-state invariants;
- explicit direct/no-proxy/no-admin policy, or complete implementation/beacon/admin/upgrade semantics where deliberately allowed;
- post-deployment RPC code bytes/codehashes, receipts, and an independently reproduced checker result.

Any missing or empty expected hash is a hard failure. Contract reordering, one-byte changes, parameter substitution, profile drift, and unresolved link/immutable references are demonstrated failures in `negative-results.json`.
