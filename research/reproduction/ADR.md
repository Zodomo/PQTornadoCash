# ADR: Fail-closed declarative reproduction controller

## Status

Accepted for the research evidence package. It is not a protocol, finalist, deployment, or production decision.

## Context

Plan section 25 requires one-command build, corpus, fresh hiding proof, native verification, EVM verification, security, and report workflows. The current integrated-finalist ledger reports zero eligible finalists. The repository nevertheless contains many useful component experiments whose commands and negative outcomes must remain reproducible without being mistaken for an integrated candidate.

The package must also verify a large, changing evidence tree. Build products, caches, VCS state, prior user-moved plans/reports, local secrets, temporary proof outputs, and the evidence manifest itself must not enter the manifest.

## Decision

Use one standard-library Python controller and a declarative JSON registry.

1. Candidate action availability is explicit for every minimum candidate and every section-25 action. An unavailable action always returns `NOT_AVAILABLE_NO_ELIGIBLE_FINALIST` and nonzero exit status.
2. C00 maps to the frozen v0.3 native binary, canonical semantic corpus, retained 60-proof ledger, local Foundry pool harness, q32 security manifest, and benchmark-run report generator. C01 maps only to the exact q48 width-190 security comparator. No component command is silently substituted for an integrated action.
3. Experimental packages are separately catalogued with exact argv and prerequisites. Their registry classification is evidence-only.
4. Child processes use argv arrays, `shell=False`, and a reduced environment. EVM execution accepts only the local Anvil/Foundry route. There is no RPC, key, broadcast, deployment, or arbitrary-command option.
5. Dry-run emits the same ordered commands that execution would run. Unsupported actions remain unsupported in dry-run.
6. Fresh proofs are isolated below an excluded work tree. Success additionally requires metadata proving OS entropy, immediate native verification, codec round-trip, distinct proof IDs, and difference from each corresponding retained proof.
7. The evidence manifest is deterministic: sorted paths, SHA-256, byte counts, no timestamps. It pins listed files but allows new evidence files until explicit regeneration, so concurrent additions do not invalidate already pinned bytes. Changed, removed, unsafe, or excluded listed files fail verification.
8. `all-safe` performs only in-process read-only manifest, registry, pin, and JSON checks. It invokes no subprocess and cannot contact a chain.

## Consequences

The controller refuses apparently convenient workflows for C10–C40 while no finalist exists. This is intentional negative evidence, not missing glue. Component commands remain discoverable and reproducible but cannot report candidate success. Authoritative v0.3 run records are read-only; reproduction outputs are disposable and excluded. A future eligible finalist requires an explicit registry change, exact entrypoints, prerequisites, pinned artifacts, and review rather than inheriting C00 behavior.
