# C00/v03-baseline

Research-only reproduction of the frozen PQ Tornado Classic v0.3 candidate for SP-00. The code under `contracts/`, `crates/`, and `packages/` is consumed without modification. This package is not deployment authorization.

## Reproduction commands

From the repository root:

```sh
python3 research/candidates/v03-baseline/scripts/generate-all.py
python3 research/candidates/v03-baseline/scripts/verify-all.py
```

The first command parses and verifies the engineering report's 59 source records and 16 generated-artifact records, checks that `pqtc-v0.3-research-baseline` peels to `00f829001999ee66da6fd5161c4c205c07d0b937`, regenerates the parameter tree twice, byte-compares both trees and the frozen tree, derives candidate inputs, and creates exactly 60 fresh q32 proofs. Thirty proofs use one fixed report witness; thirty use distinct supported semantic-corpus witnesses. Every proving process obtains hiding entropy from the OS, immediately verifies its proof, round-trips the A/B codec, and retains exact statement, witness, proof, mapping, and pool calldata bytes. Re-running replaces only C00-generated evidence.

The second command verifies all 60 artifacts natively and then runs each exact A/B calldata pair through the nested Foundry harness's complete `beginWithdrawal` and `withdraw` calls. It is intentionally expensive. `--native-only` performs only native verification and leaves EVM status `NOT_EVALUATED`.

Additional deterministic commands:

```sh
research/candidates/v03-baseline/scripts/measure-deployment.sh
research/candidates/v03-baseline/scripts/run-geth-t8n.sh v03-fixed-19
```

The t8n route exports a focused Foundry prestate, signs two synthetic transactions offline with the public Anvil development key, and executes exact A then B calldata sequentially under Prague rules and the 2^24 gas cap. It uses a preinstalled `ethereum/client-go:alltools-v1.17.5` image pinned to commit `9621c6ad`; it never pulls an image, contacts RPC, or reads the repository `.env`. `v03-fixed-19` passes both simulated transactions and retains per-transaction opcode maps. The retained `v03-fixed-01` run is an intentional negative: Part A exhausts forwarded gas under the same cap. Neither result is a mined receipt.

## Candidate mapping

Corpus byte strings are not reduced modulo BabyBear. For each required field, the adapter computes `Keccak-256("PQTC.C00.MAP.V1\0" || target || 0x00 || sourceBytes || uint64be(drawIndex))`, interprets the first four digest bytes as a big-endian `u32`, accepts values below `2,013,265,921`, and rejects all others. Each run retains accepted values in the exact witness and every rejected candidate/index in `mapping.json`. Sixteen accepted fields form each canonical 64-byte sibling digest. The original semantic case is retained verbatim inside `derived-case.json`; it is never edited in place.

The 30 corpus proofs use the first 30 valid depth-20 cases in corpus order. The fixed-distribution series repeats the report's canonical benchmark witness (scope halves filled with `1`/`2`, secrets `3`/`4`, recipient `5`, relayer `6`, fee zero) while requiring 30 byte-distinct proof pairs.

## Evidence and honest gaps

Generated proof directories are `proofs/v03-*`; schema-valid raw records are `research/runs/v03-*.json`; the row-level distribution is `research/summaries/v03-distribution.csv`. SHA-256 and Ethereum Keccak-256 are lowercase and are computed over exact bytes. Internal frontier and subsection lengths are `NOT_EVALUATED`: the frozen public codec returns query indices and whole A/B parts but does not expose split-query frontier totals. They are not guessed. Sixty native and Foundry A/B checks pass, but 9/60 Part A total-gas observations exceed EIP-7825; the SP-00 gate is therefore `FAIL`. Top-level creation gas and mined receipts remain explicitly `NOT_EVALUATED` and cannot reverse that observed failure.

The Foundry harness is isolated under `evm/`. Its research-only subclass loads synthetic scope/root state so arbitrary corpus paths can traverse the unchanged pool-facing verification and payout code. This bypass is evidence plumbing, not a deployable pool and not a claim that synthetic sibling paths arose from deposits.

## Known baseline discrepancies

1. `.dockerignore` does not exclude `.env`, while `Dockerfile` executes `COPY . .`. The old report says private `.env` material is excluded, but the Docker context can include it. Never build the baseline image from a working tree containing `.env`; this package neither reads nor repairs the frozen Docker files.
2. The report says TypeScript consumes all 1,000 generated cross-language vectors. `packages/sdk/test/vectors.test.ts` does not load `test-vectors/hash/v3.json`; it checks a small hard-coded canonical vector and local properties. The Solidity test does iterate all 1,000. The TypeScript 1,000-vector claim is therefore unsupported by the frozen test source.

Synthetic benchmark secrets are public test data and must never be reused for a real note. No public RPC, live key, production secret, or deployment receipt is required or claimed.
