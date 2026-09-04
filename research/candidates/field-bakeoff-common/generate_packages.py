#!/usr/bin/env python3
"""Generate the six SP-40 evidence packages from reviewed metadata."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "3152b14a89067c83775a8076cc262ffc48a1fd7c"
COMMON_HASHES = {
    "dft/src/traits.rs": "6eec343eef88e701f6cf11dc205a1cbaa0d6efcb3a6e947622a636f656eee142",
    "fri/src/lib.rs": "de8d645f19bbd37cb3f5b8c3b142001440a5fa9a36c4642d20f2b6aa184d9f2e",
    "circle/src/pcs.rs": "51e2140ab4f0840362a30f5a37fbac9ba598e7c31ddc2de01a7932b170dd7aff",
    "field/src/extension/mod.rs": "aac05a6fdcc6f309792680d356c00ee491b4ad79790f746a04119523fe68ec38",
    "field/src/extension/quintic_extension.rs": "47dda94a12d861afd41e85658e30cb0c132b83dc77455f32dddf721ac220e889",
    "monty-31/src/extension.rs": "248f0e353eca0620a9c7d8ae6612d74cc4cd4147a6487013cf184b8383d317f2",
}
DATA = {
    "F0": {
        "base": "BabyBear", "p": 2013265921, "degree": 4, "poly": "x^4 - 11", "baseAdicity": 27, "extAdicity": 29,
        "source": {"baby-bear/src/baby_bear.rs": "c807d94f76a9624d744d552ab8b188faba2446bfebb6ec626b49e7fd44047e5f"},
        "compat": "Pinned p3-baby-bear implements the degree-four binomial extension and multiplicative two-adic DFT/FRI path used by the frozen UniSTARK baseline.",
        "parameters": "Pinned default BabyBear Poseidon2 width 16/24/32 constructors and known-answer tests are present.",
        "attacks": "Small-characteristic and extension-field algebraic/subfield structure must be included in protocol soundness analysis; a challenge can lie in the base subfield. No candidate-specific break is asserted.",
        "maturity": "HIGH_RELATIVE: this is the frozen baseline field stack, but the SP-40 Solidity harness remains research code.",
        "negative": ["The challenge space is below 2^124 and cannot by itself supply a strict 128-bit uniform challenge.", "Four 32-bit coefficients make each extension opening 16 raw bytes and four ABI words."],
    },
    "F1": {
        "base": "KoalaBear", "p": 2130706433, "degree": 4, "poly": "x^4 - 3", "baseAdicity": 24, "extAdicity": 26,
        "source": {"koala-bear/src/koala_bear.rs": "8abc03dd0f576d9839867d2a2f8025f5dd70f325df3c65535d498f9e3e304180"},
        "compat": "Pinned p3-koala-bear implements the degree-four binomial extension and the generic p3-dft/p3-fri multiplicative-domain interfaces.",
        "parameters": "Pinned default KoalaBear Poseidon2 width 16/24/32 constructors and known-answer tests are present.",
        "attacks": "The same small-characteristic, subfield-challenge, and algebraic-permutation analyses required for BabyBear remain required; no candidate-specific break is asserted.",
        "maturity": "HIGH_LIBRARY_MEDIUM_INTEGRATION: optimized pinned field and permutation code exist; the frozen PQTornado relation has not been ported.",
        "negative": ["The challenge space is below 2^124 and cannot by itself supply a strict 128-bit uniform challenge.", "Base two-adicity 24 is lower than BabyBear's 27, although it covers the frozen 256-row relation."],
    },
    "F2": {
        "base": "KoalaBear", "p": 2130706433, "degree": 5, "poly": "x^5 + x^2 - 1", "baseAdicity": 24, "extAdicity": 24,
        "source": {"koala-bear/src/koala_bear.rs": "8abc03dd0f576d9839867d2a2f8025f5dd70f325df3c65535d498f9e3e304180"},
        "compat": "Pinned p3-field exports QuinticTrinomialExtensionField and pinned p3-koala-bear implements x^5+x^2-1 arithmetic, Frobenius data, and a two-adic extension generator; generic FRI traits can use it after a complete configuration is selected.",
        "parameters": "The application permutation remains the pinned KoalaBear base-field Poseidon2; no separate extension permutation is required by this microbench.",
        "attacks": "A larger challenge space does not replace FRI, DEEP, hiding, and QROM analyses. Quintic subfield events and algebraic structure remain explicit proof obligations; no candidate-specific break is asserted.",
        "maturity": "MEDIUM: the specialized quintic is implemented and tested upstream, but it is not the frozen PQTornado challenge field and has no EVM integration history here.",
        "negative": ["Five coefficient extension operations and openings are structurally more expensive for the EVM than degree-four candidates.", "No complete frozen-relation proof or PCS configuration has been produced for this stack."],
    },
    "F3": {
        "base": "Goldilocks", "p": 18446744069414584321, "degree": 2, "poly": "x^2 - 7", "baseAdicity": 32, "extAdicity": 33,
        "source": {"goldilocks/src/extension.rs": "a22b3caad017169569b5689ed71f2a4608a23a839d4e5ce13c6ca5e145262689"},
        "compat": "Pinned p3-goldilocks supplies the quadratic extension, optimized DFT, and generic multiplicative p3-fri compatibility.",
        "parameters": "Pinned default Goldilocks Poseidon2 width 8/12/16 constructors and known-answer tests are present.",
        "attacks": "The pseudo-Mersenne reduction and redundant internal representations make canonical serialization checks security-critical. Goldilocks-specific algebraic analyses remain required; no candidate-specific break is asserted.",
        "maturity": "HIGH_LIBRARY_MEDIUM_INTEGRATION: optimized upstream arithmetic exists; PQTornado's Solidity verifier and codec have not been ported.",
        "negative": ["Eight-byte base elements double raw trace-opening bytes relative to 31-bit candidates.", "The field has slightly fewer than 2^64 elements, so the quadratic challenge space is slightly below 2^128 and has a 127-bit floor."],
    },
    "F4": {
        "base": "Mersenne31", "p": 2147483647, "degree": 4, "poly": "i^2 + 1; u^2 - (2+i) (QM31 tower)", "baseAdicity": 1, "extAdicity": 33,
        "source": {"mersenne-31/src/extension.rs": "018a5b65de0448245c3f321dd15f5b20381c14cf90f51e63f4eac45be932a181", "mersenne-31/src/qm31.rs": "aac16195540b51c6d1a362229c117ef63b767ff54167539cc08966a0d651d5c7"},
        "compat": "Mersenne31 base multiplicative domains have only two-adicity one. The pinned compatible route is the complex/circle backend; QM31 supplies a four-dimensional challenge field over Mersenne31.",
        "parameters": "Pinned default Mersenne31 Poseidon2 width 16/24/32 constructors exist; the circle PCS must be configured separately.",
        "attacks": "Circle-domain soundness, complex conjugation/tower subfields, and Mersenne reduction canonicality require backend-specific analysis. A multiplicative-FRI argument cannot be reused unchanged.",
        "maturity": "MEDIUM_BACKEND_SPECIFIC: pinned circle, complex DFT, QM31, and Poseidon2 code exist, but the frozen relation and EVM verifier are not circle ports.",
        "negative": ["The base field cannot run the frozen multiplicative two-adic FFT/FRI path beyond size two; a circle-backend port is mandatory.", "The approximately 124-bit challenge space is below a strict 128-bit uniform challenge target."],
    },
    "F5": {
        "base": "BN254 scalar field", "p": 21888242871839275222246405745257275088548364400416034343698204186575808495617, "degree": 1, "poly": "none (base-field challenge)", "baseAdicity": 28, "extAdicity": 28,
        "source": {"bn254/src/bn254.rs": "d9f6d16f262a260eaec12c7e685b5d47f63ec5484ff962952c1fba37bcf21768", "bn254/src/poseidon2.rs": "6f50741ea1763cc1749e116a3b124c7e939abf29f2e09668e1fa990d9f071b7a"},
        "compat": "Pinned p3-bn254 implements Field and TwoAdicField, so generic p3-dft/p3-fri arithmetic interfaces are available. A complete hash/MMCS/transcript/PCS instantiation is not frozen.",
        "parameters": "Pinned p3-bn254 exports a Poseidon2 type and round-count constants but no reviewed default-constant constructor, so permutation benchmarking stops rather than inventing constants.",
        "attacks": "Large-prime arithmetic avoids extension subfields but does not remove Fiat-Shamir, FRI, grinding, hiding, or QROM obligations. Canonical 254-bit decoding is mandatory.",
        "maturity": "MEDIUM_FIELD_LOW_STACK: pinned scalar arithmetic exists; no frozen PQTornado application permutation, PCS, Solidity codec, or complete proof uses this field.",
        "negative": ["Every raw base/challenge element is 32 bytes: eight times a 31-bit raw element.", "No pinned default application-permutation parameters or complete PQTornado PCS configuration are available."],
    },
}


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen(component: str) -> dict:
    return {
        "component": component,
        "researchDisposition": "EXPLICITLY_UNCHANGED_FROZEN_V03_OUT_OF_SCOPE",
        "integratedByCandidate": False,
        "silentInheritance": False,
    }


def protocol_matrix(candidate: str, d: dict) -> dict:
    matrix = {
        name: frozen(name)
        for name in [
            "noteEntropyAndEncoding",
            "applicationDigest",
            "hashMode",
            "treeArityDepth",
            "publicStatement",
            "relation",
            "hidingConstruction",
            "proofMmcs",
            "transcript",
            "proofCodec",
            "evmVerifier",
            "checkpointModel",
            "deploymentManifest",
            "custodyContracts",
            "economicModel",
            "securityTargetAndCalculators",
            "commonProtocolCorpus",
        ]
    }
    matrix["baseChallengeField"] = {
        "component": "baseChallengeField",
        "researchDisposition": "ALTERNATIVE_MEASURED_IN_ISOLATED_SP40_HARNESS",
        "frozenV03RuntimeValue": "BabyBear / degree-four extension",
        "candidateResearchValue": f"{d['base']} / degree {d['degree']} / {d['poly']}",
        "integratedByCandidate": False,
        "silentInheritance": False,
    }
    matrix["pcsLdt"] = {
        "component": "pcsLdt",
        "researchDisposition": "COMPATIBILITY_ONLY_NO_CONFIGURATION_INSTANTIATED",
        "frozenV03RuntimeValue": "hiding two-adic FRI",
        "candidateResearchValue": d["compat"],
        "integratedByCandidate": False,
        "silentInheritance": False,
    }
    return {
        "complete": True,
        "defaultRule": "NO_UNLISTED_COMPONENT_IS_INHERITED_OR_CHANGED",
        "candidateId": candidate,
        "layers": matrix,
    }


def main() -> None:
    for candidate, d in DATA.items():
        path = ROOT / candidate
        path.mkdir(parents=True, exist_ok=True)
        challenge_bits = d["degree"] * math.log2(d["p"])
        floor_bits = math.floor(challenge_bits)
        base_bytes = 8 if candidate == "F3" else 32 if candidate == "F5" else 4
        ext_bytes = base_bytes * d["degree"]
        source_hashes = {**d["source"], **COMMON_HASHES}
        local_paths = [
            ROOT / "field-bakeoff-common/native/Cargo.lock",
            ROOT / "field-bakeoff-common/native/src/main.rs",
            ROOT / "field-bakeoff-common/solidity/src/FieldBakeoff.sol",
            ROOT / "field-bakeoff-common/solidity/test/FieldBakeoff.t.sol",
            ROOT / "field-bakeoff-common/outputs/native-latest.json",
            ROOT / "field-bakeoff-common/outputs/solidity-latest.json",
            ROOT / "field-bakeoff-common/outputs/projection-latest.json",
            path / "vectors.json",
        ]
        manifest = {
            "candidateId": candidate,
            "spikeId": "SP-40",
            "status": "BENCHMARK_ONLY",
            "noCode": False,
            "completeProofClaimed": False,
            "nativeTimingEvidence": {
                "classification": "DIAGNOSTIC_NOT_COMMON_PROTOCOL",
                "commonProtocolComparable": False,
                "warmupIterations": 0,
                "distribution": "fixed wrapping-u64 mixer, not common protocol corpus",
                "rankingUse": "PROHIBITED",
            },
            "protocolLayerMatrix": protocol_matrix(candidate, d),
            "pinnedPlonky3Commit": PIN,
            "field": {
                "base": d["base"], "modulus": str(d["p"]), "modulusBitsCeil": d["p"].bit_length(),
                "challengeDegree": d["degree"], "irreduciblePolynomial": d["poly"],
                "challengeSpaceBitsApprox": round(challenge_bits, 9), "challengeSpaceBitsFloor": floor_bits,
                "conservativeEntropyBudgetBits": floor_bits,
                "entropyQualification": "field-cardinality ceiling only; not a complete protocol soundness or QROM bound",
                "baseTwoAdicity": d["baseAdicity"], "challengeTwoAdicity": d["extAdicity"],
            },
            "encoding": {
                "canonicalBaseBytes": base_bytes, "canonicalExtensionBytes": ext_bytes,
                "raw": "canonical fixed-width big-endian coefficients, least-degree coefficient first",
                "abi": "uint256 per canonical coefficient",
                "abiBaseBytes": 32, "abiExtensionBytes": 32 * d["degree"],
                "distributionEvidence": "vectors.json distribution over 4096 deterministic values",
                "openedRowFloorEvidence": "../field-bakeoff-common/outputs/projection-latest.json (64 and 96 rows at 190 columns)",
            },
            "parameterAvailability": d["parameters"],
            "compatibility": d["compat"],
            "fieldSpecificAttackReview": d["attacks"],
            "implementationMaturity": d["maturity"],
            "paretoStatus": "UNRANKED_DIAGNOSTIC_TIMINGS_NOT_GATE_EVIDENCE",
            "gate": {"passed": False, "reason": "Native timings are diagnostic rather than common-protocol comparable, and complete proof bytes, total EVM gas, prover time, soundness, and maturity are not all evidenced."},
            "artifacts": ["ADR.md", "assumptions.md", "negative-results.md", "status.json", "vectors.json", "source-evidence.json", "../field-bakeoff-common/native/Cargo.lock", "../field-bakeoff-common/native/src/main.rs", "../field-bakeoff-common/solidity/src/FieldBakeoff.sol", "../field-bakeoff-common/solidity/test/FieldBakeoff.t.sol", "../field-bakeoff-common/outputs/native-latest.json", "../field-bakeoff-common/outputs/solidity-latest.json", "../field-bakeoff-common/outputs/projection-latest.json"],
            "commands": {
                "native": "cargo run --release --locked --manifest-path research/candidates/field-bakeoff-common/native/Cargo.toml -- --iterations 64 --rows 256 --columns 190 --out research/candidates/field-bakeoff-common/outputs/native-latest.json",
                "solidity": "python3 research/candidates/field-bakeoff-common/solidity/run_bench.py --out research/candidates/field-bakeoff-common/outputs/solidity-latest.json",
            },
            "publicNetworkExecution": "PROHIBITED",
            "productionSecrets": "PROHIBITED",
        }
        dump(path / "manifest.json", manifest)
        dump(path / "status.json", {
            "candidateId": candidate, "status": "BENCHMARK_ONLY", "gate": "NOT_PASSED", "paretoStatus": manifest["paretoStatus"],
            "completeProof": "NOT_ATTEMPTED_IN_SP40_MICROBENCH", "evmCompleteVerification": "NOT_ATTEMPTED",
            "nativeOutput": "../field-bakeoff-common/outputs/native-latest.json", "solidityOutput": "../field-bakeoff-common/outputs/solidity-latest.json",
            "measuredEvidence": ["native smoke diagnostics classified DIAGNOSTIC_NOT_COMMON_PROTOCOL", "Solidity isolated-kernel gas diagnostics", "deterministic vectors", "encoding and opened-row byte/gas floors"],
            "unmeasuredGates": ["complete proof bytes", "complete EVM execution gas", "prover time on a ported relation", "complete protocol soundness", "audited implementation maturity"],
        })
        dump(path / "source-evidence.json", {
            "pinnedCommit": PIN, "hashAlgorithm": "SHA-256", "repository": "https://github.com/Plonky3/Plonky3",
            "files": [{"path": name, "sha256": digest} for name, digest in source_hashes.items()],
            "localEvidence": [
                {"path": str(local.relative_to(ROOT)), "sha256": sha256(local)}
                for local in local_paths
            ],
            "generator": "research/candidates/field-bakeoff-common/generate_packages.py",
            "claims": {"compatibility": d["compat"], "parameterAvailability": d["parameters"]},
        })
        (path / "ADR.md").write_text(f"""# ADR: {candidate} remains research-only\n\n## Context\n\nSP-40 reopens the field stack without changing the frozen v0.3 custody protocol. {d['compat']} {d['parameters']}\n\n## Decision\n\nRetain {candidate} as `BENCHMARK_ONLY`. The native output is classified `DIAGNOSTIC_NOT_COMMON_PROTOCOL`: it has no common-protocol corpus distribution or warmup phase, and scalar samples can be timer-overhead-scale. It may prove executability only; cross-candidate ranking and nondominance use are prohibited. The isolated Solidity gas output is likewise not a complete verifier result. Do not integrate this field into the prover, proof codec, verifier, or contracts.\n\n## Protocol-layer disposition\n\n`manifest.json.protocolLayerMatrix` explicitly lists every frozen or investigated layer. No unlisted layer is silently inherited or changed. Only the candidate field arithmetic is measured in isolation; even that alternative is not integrated.\n\n## Gate\n\nThe candidate advances only if it is nondominated across common-protocol complete proof bytes, total EVM execution gas, prover time, soundness ceiling, and implementation maturity. Those dimensions are not available here, so the gate is not passed and Pareto rank is unassigned. No complete-proof result is claimed.\n\n## Consequences\n\n- Deterministic arithmetic vectors and 64/96-row encoding floors remain valid non-timing evidence.\n- A later common-protocol run must define distributions, warmup, repetition policy, and a ported relation/backend before timing comparison.\n- Unsupported PCS or parameter paths stop with source-backed reasons in `source-evidence.json`; no local constants are invented.\n""")
        (path / "assumptions.md").write_text(f"""# {candidate} assumptions\n\n- Modulus: `{d['p']}`; challenge construction: `{d['poly']}`.\n- Canonical base width is {base_bytes} bytes; extension width is {ext_bytes} bytes. Raw vectors are fixed-width big-endian; ABI uses one 32-byte word per coefficient.\n- The deterministic input mixer is specified in `vectors.json`; it is not a randomness or entropy source.\n- Challenge cardinality is approximately {challenge_bits:.9f} bits (floor {floor_bits}). The reported conservative entropy budget is only that cardinality floor, not a FRI, Fiat-Shamir, hiding, QROM, or complete-proof bound.\n- Base/challenge two-adicity is {d['baseAdicity']}/{d['extAdicity']}. Domain feasibility still depends on the selected backend and blowup.\n- Opened-row floors use 190 columns and EIP-2028 byte prices (4 gas zero, 16 gas nonzero), with no envelope, authentication, FRI, memory, or intrinsic transaction cost.\n- The 256-row frozen geometry and any explicitly supplied SP-20 geometry are relation inputs, not evidence that the relation was ported.\n- No public network, RPC, `.env`, live key, classical wrapper, or alternate encoding is used.\n""")
        negatives = "\n".join(f"- {x}" for x in d["negative"])
        (path / "negative-results.md").write_text(f"""# {candidate} negative results and stops\n\n{negatives}\n- Native timings are `DIAGNOSTIC_NOT_COMMON_PROTOCOL`: no common-protocol input distribution or warmup was used, and scalar samples can be timer-overhead-scale. They cannot support ranking, nondominance, or a gate pass.\n- PCS commit/open/verify is not benchmarked because SP-40 does not freeze the required hash/MMCS/transcript/PCS tuple; selecting one would add a protocol decision.\n- Peak RSS is process-wide rather than per-operation, and thread-scaling includes worker creation; neither is a complete prover resource result.\n- No complete hiding proof, complete verifier gas, proof byte count, or Pareto win is claimed.\n\nThese stops are gates, not zero-cost entries. Unsupported or unmeasured work must not be converted into a favorable score.\n""")
        (path / "README.md").write_text(f"""# {candidate}: {d['base']} / degree {d['degree']}\n\nStatus: **BENCHMARK_ONLY**. Challenge field: `{d['poly']}`.\n\nThis package contains the candidate manifest, explicit no-silent-inheritance protocol matrix, decision record, assumptions, negative results, refreshed source/evidence hashes, and deterministic vectors. Shared executable Rust and Solidity kernels live in `../field-bakeoff-common/`. Native timing is `DIAGNOSTIC_NOT_COMMON_PROTOCOL` and cannot rank candidates. Encoding and 64/96 opened-row floors are generated in `../field-bakeoff-common/outputs/projection-latest.json`.\n\n{d['maturity']}\n\nNo complete proof, production compatibility, deployment readiness, nondominance, or Pareto victory is asserted.\n""")


    native_output = ROOT / "field-bakeoff-common/outputs/native-latest.json"
    solidity_output = ROOT / "field-bakeoff-common/outputs/solidity-latest.json"
    projection_output = ROOT / "field-bakeoff-common/outputs/projection-latest.json"
    native_data = json.loads(native_output.read_text())
    solidity_data = json.loads(solidity_output.read_text())
    dump(ROOT / "field-bakeoff-common/status.json", {
        "spikeId": "SP-40",
        "status": "BENCHMARK_ONLY",
        "gate": "NOT_PASSED",
        "paretoSelection": "NONE",
        "completeProofClaimed": False,
        "nativeTimingClassification": native_data["measurementClassification"],
        "nativeCommonProtocolComparable": native_data["commonProtocolComparable"],
        "solidityMeasurementCount": len(solidity_data["measurements"]),
        "retainedOutputs": [
            {"path": str(output.relative_to(ROOT)), "sha256": sha256(output)}
            for output in [native_output, solidity_output, projection_output]
        ],
        "candidates": [
            {
                "candidateId": candidate,
                "status": "BENCHMARK_ONLY",
                "gate": "NOT_PASSED",
                "paretoStatus": "UNRANKED_DIAGNOSTIC_TIMINGS_NOT_GATE_EVIDENCE",
                "manifestSha256": sha256(ROOT / candidate / "manifest.json"),
                "statusSha256": sha256(ROOT / candidate / "status.json"),
                "sourceEvidenceSha256": sha256(ROOT / candidate / "source-evidence.json"),
            }
            for candidate in DATA
        ],
        "generatedBy": "research/candidates/field-bakeoff-common/generate_packages.py",
    })

if __name__ == "__main__":
    main()
