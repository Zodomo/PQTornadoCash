#!/usr/bin/env python3
"""Generate a local-only H0 pool with source-pinned precomputed empty-tree constants."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
POOL_SOURCE = ROOT / "contracts/src/PQTCClassicPool.sol"
SOURCE_SHA256 = "5ce4f94692e87922efd0584e543afc43937ad8647161dd4e3e16bb8a442c0fd0"

def solidity_digest(value):
    halves = [value[side] for side in ("left", "right")]
    for half in halves:
        if len(bytes.fromhex(half.removeprefix("0x"))) != 32:
            raise ValueError("digest half must be exactly 32 bytes")
    return f"Digest512(bytes32({halves[0]}), bytes32({halves[1]}))"

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    output = a.output.resolve()
    if not output.is_relative_to(ROOT / "research/r2/operations") or output.exists():
        p.error("output must be new and stay in research/r2/operations")
    raw = POOL_SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("frozen H0 pool source changed")
    manifest_raw = a.inputs.read_bytes()
    manifest = json.loads(manifest_raw)
    if manifest["schema"] != "pqtc.r2.actual-deposit-inputs.v1" or not manifest["synthetic"] or manifest["funded"]:
        raise ValueError("only generated unfunded local research inputs are permitted")
    zeros = manifest["zeros"]
    if len(zeros) != 21 or manifest["chainId"] != 31337:
        raise ValueError("expected depth20 disposable chain31337")
    pool = manifest["pool"].removeprefix("0x")
    if len(bytes.fromhex(pool)) != 20:
        raise ValueError("invalid predicted pool address")
    text = raw.decode().replace("PQTCClassicPool", "R2ScopedPool").replace("IPQTCVerificationRegistry", "IR2VerificationRegistry")
    for library in ("Digest512", "P2BB512", "PQTCApplicationHash"):
        relative = os.path.relpath(ROOT / f"contracts/src/libraries/{library}.sol", output.parent).replace(os.sep, "/")
        text = text.replace(f'"./libraries/{library}.sol"', f'"{relative}"')
    start = text.index("        zeros[0] = PQTCApplicationHash.emptyLeaf(scope);")
    end = text.index("        Digest512 memory initialRoot = zeros[TREE_DEPTH];", start)
    scope = manifest["scope"]
    initialization = [
        "        // Local research build: all constants are scoped to this exact predicted CREATE context.",
        f'        if (address(this) != address(bytes20(hex"{pool}")) || block.chainid != 31337 || denomination_ != {int(manifest["denominationWei"])}) revert InvalidDependency();',
        f'        if (scope.left != bytes32({scope["left"]}) || scope.right != bytes32({scope["right"]})) revert InvalidDependency();',
    ]
    for level, zero in enumerate(zeros):
        initialization.append(f"        zeros[{level}] = {solidity_digest(zero)};")
        if level < 20:
            initialization.append(f"        filledSubtrees[{level}] = zeros[{level}];")
    text = text[:start] + "\n".join(initialization) + "\n" + text[end:]
    insertion = "    function currentRoot() external view returns (Digest512 memory) {"
    assert text.count(insertion) == 1
    text = text.replace(insertion, """    function withdrawOneCall(Withdrawal calldata withdrawal, bytes calldata partA, bytes calldata partB)
        external nonReentrant
    {
        uint32[64] memory values = _validatedPublicValues(withdrawal);
        bytes32 verificationId = verificationRegistry.beginVerification(parameterId, values, partA);
        if (!verificationRegistry.completeVerification(verificationId, parameterId, values, partB)) revert InvalidProof();
        _completeWithdrawal(withdrawal);
    }

""" + insertion)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text)
    record = {"schema": "pqtc.r2.scoped-pool-generation.v1", "source": str(POOL_SOURCE.relative_to(ROOT)), "source_sha256": SOURCE_SHA256, "input": str(a.inputs), "input_sha256": hashlib.sha256(manifest_raw).hexdigest(), "output": str(output.relative_to(ROOT)), "output_sha256": hashlib.sha256(text.encode()).hexdigest(), "scope": scope, "pool": manifest["pool"], "chain_id": 31337, "denomination_wei": manifest["denominationWei"], "optimization": "Compile native-generated scoped zero digests into initcode; retain all original deposit, root, nullifier, payout and reentrancy checks; scope recomputed and both halves checked on-chain", "constraint": "Not a generic deployment factory; changing pool, chain, denomination or experimental parameter requires fresh inputs and a fresh compiled artifact", "qualification": "SECURITY_NOT_QUALIFIED; native/Solidity vector and actual deposit/withdraw execution required"}
    output.with_suffix(".generation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))

if __name__ == "__main__":
    main()
