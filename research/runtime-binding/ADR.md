# ADR: Two-layer proof-system and deployment identity

## Status

Research decision; v0.3 remains not deployment-ready.

## Context

The frozen v0.3 manifest can encode expected runtime hashes but contains an empty list. Directly adding a runtime hash to the same parameter ID embedded as a registry immutable creates the equation `parameterId = H(... runtime(parameterId) ...)`, with no ordinary deterministic construction and an unnecessary hash cycle. Creation code, full initcode, runtime templates, and deployed runtime are also different objects: constructor arguments are appended only to full initcode, while constructor-assigned immutables are copied into returned runtime.

## Decision

Use two identities in a future clean cutover:

1. `proofSystemId` commits to the application relation, base/extension fields, PCS/LDT and parameters, transcript, proof codec, verifier interface, and reviewed stateless verifier source or parameter-independent code identity.
2. `deploymentManifestId` is computed after compilation and address selection. It commits to `proofSystemId`; an ordered contract-role list; source/artifact identities; compiler version; optimizer enabled/runs/details; via-IR flag; EVM revision; metadata mode; remappings; external library addresses and code hashes; creation-code, full-initcode, runtime-template, and constructor-resolved runtime hashes; exact ABI constructor arguments; chain ID; addresses; denomination; pool-as-registry-consumer relationship; factory/deployer and CREATE2 salts if used; and an explicit no-proxy/no-admin or upgrade policy.

`deploymentManifestId` must not be a constructor argument or immutable of any runtime whose hash it commits to. The deployment tool computes it last and compares `eth_getCode`/`EXTCODEHASH` after construction.

```text
relation/fields/PCS/transcript/codec/interface
                    |
                    v
              proofSystemId
                    |
source + solc/profile + libraries ---> creation/runtime templates
                    |                         |
constructor args ---+--> full initcode ------+
                    |                         |
chain + deployer + salt --> addresses --------+
                    |                         |
                    +--> resolved runtimes ---+
                                              |
                                              v
                                    deploymentManifestId
```

There is no edge from `deploymentManifestId` back into compilation, constructor arguments, or runtime. A CREATE2 address may depend on full initcode containing `proofSystemId`; this remains acyclic because the final deployment identity depends on that address, not conversely.

## Alternatives evaluated

### Direct CREATE plus post-deployment code hash

Simple and sufficient to compare runtime, but the address depends on deployer nonce, the runtime hash omits constructor-only effects and storage initialization, and the creation transaction must be separately bound. Acceptable only when the manifest records creator, nonce-derived address, full initcode, constructor args, receipt, initialized state invariants, and runtime.

### CREATE2

Binds deployer, salt, and full-initcode hash into the address and makes precomputation possible. It does not replace runtime checking, chain binding, initialized-state checking, or factory-code review. Constructor arguments change the address; immutable arguments change both address and runtime. A salt naming convention is not an identity unless the exact factory and initcode are also pinned.

### Profile-enforcing factory

Can enforce order, salts, arguments, and expected post-construction code hashes, and emit a useful receipt trail. The factory becomes part of the trusted deployment surface and must itself be hash-bound. Prefer a reviewed, immutable, single-purpose or permissionlessly deterministic factory. An admin-controlled factory can deploy a different set later and is not a substitute for a signed immutable manifest.

### On-chain registry

A registry mapping `(chainId, proofSystemId, consumer)` to a manifest ID, ordered addresses, and code hashes gives consumers a discoverable allowlist. It still needs an off-chain reproducible artifact packet. An immutable registry gives clean semantics; an admin-updatable registry changes which proof system/deployment is trusted and therefore constitutes a protocol upgrade. Timelocks and multisigs improve governance visibility but do not preserve identity.

### Proxies and upgradeable modules

Rejected as the default. `EXTCODEHASH(proxy)` binds only proxy runtime, not implementation, beacon, admin, storage layout, or initialized state. Any upgrade authority invalidates a permanent verifier identity. If upgrades are required, each implementation and configuration needs a new deployment manifest and proof-system compatibility decision; consumers must explicitly opt into the new ID. Silent in-place substitution is prohibited.

## Consequences

- Contract order is consensus-like manifest data, not a presentation detail.
- Compiler metadata is hash-significant. `bytecode_hash = "none"` and IPFS metadata produce different bytecode even from identical Solidity.
- Optimizer runs/details, via-IR, solc build, EVM revision, remappings, and library linking are hash-significant and must be exact.
- External-library placeholders must be resolved before hashing; linked addresses and each library's runtime hash must be recorded. The measured v0.3 artifacts use only inlined/internal libraries and report empty link-reference maps.
- Constructor-resolved runtime hashes do not bind arbitrary initialized storage. Pool chain/scope and the registry consumer relation need explicit chain/address/constructor/state checks.
- An upgrade, admin change, implementation change, compiler rebuild, library relink, constructor change, or address/chain change yields a new deployment manifest ID. Proof compatibility alone does not authorize it.
