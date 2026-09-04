# PQTornadoCash independent review and targeted follow-up

## Start here

1. Read `REPOSITORY_REVIEW.md` for the evaluation of public commit `e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997`.
2. Give engineers `FOLLOW_UP_RESEARCH_PLAN.md` as the next bounded research directive.
3. Use `RESEARCH_RETURN_TEMPLATE.md` for their next handoff.
4. Use `FINDINGS.json` to track corrections and unresolved review questions.
5. Consult `SOURCES.md` for pinned evidence.

## Central recommendation

Keep `OUTCOME_D / RECOMMEND_ADDITIONAL_TARGETED_RESEARCH`, but separate permission to measure from permission to promote. The next round should produce complete, non-custodial local proofs and EVM calls for a small number of causally comparable candidates. It must not wait for every component to be production-approved before collecting the performance evidence needed to prioritize that review.

## Independent arithmetic

The package includes one executable sensitivity study:

```sh
python3 evidence/ldr_objective_sensitivity.py --output /tmp/ldr-sensitivity.json
```

Requires Python 3.10 or later and the standard library only. It reproduces the visible q32 m=185/56.201-bit calculation and compares a full-expression objective, which yields m=23/about 71.007 conditional modeled bits. This is not a new security proof, not a 100-bit qualification, and not execution of the repository's own tests.

The companion probability-sum and full-epsilon rows are explicitly labeled sensitivity calculations. They do not replace an applicable composition theorem.

## Execution boundary

The review inspected repository sources through GitHub and executed the independent sensitivity script. It did not clone/build the repository or execute the five handoff commands, Rust/Foundry tests, proof generation, or deployments. The executable environment lacked GitHub DNS access and Rust/Foundry. Retained repository measurements are identified as project evidence, not independently rerun results.

## No authorization

This package does not authorize a production build, public testnet deployment, real-value custody, a verifier upgrade, or migration. The follow-up permits isolated local research experiments only.

`PACKAGE_MANIFEST.json` lists file sizes and SHA-256 digests, excluding itself to avoid self-reference.
