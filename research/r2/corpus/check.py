#!/usr/bin/env python3
"""Pin generated corpus artifacts and check independent full-tree/incremental agreement."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def main():
    jobs = json.loads((HERE / "h0/jobs.json").read_text())
    history = json.loads((HERE / "deposit-h0/manifest.json").read_text())
    assert jobs["distinct_corpus_witnesses"] == 256
    assert len(history["deposits"]) == 4096 and len(history["cases"]) >= 256
    assert history["deposits"][0]["leafIndex"] == 0 and history["deposits"][-1]["leafIndex"] == 4095
    reference = ROOT / "research/r2/operations/outputs/reference-history-01"
    for index in range(8):
        for name in ("statement.json", "witness.json", "evm.json"):
            assert (reference / f"note-{index:03}" / name).read_bytes() == (HERE / "deposit-h0" / f"note-{index:03}" / name).read_bytes()
    files = [HERE / "semantic-cases.json", HERE / "manifest.json", ROOT / "research/r2/baseline/instrument.py", ROOT / "research/r2/baseline/outputs/r2-main/instrumentation.patch", ROOT / "research/r2/operations/rust/src/main.rs", Path(__file__)]
    for subtree in ("h0", "deposit-h0"):
        files.extend(sorted((HERE / subtree).rglob("*.json")))
    artifacts = [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in files]
    result = {"schema": "pqtc.r2.corpus-freeze.v1", "raw_semantic_cases": 256, "canonical_h0_mapped_cases": 256, "native_deposit_history_length": 4096, "deposit_backed_withdrawal_cases": len(history["cases"]), "independent_full_tree_vs_incremental_first_eight": "PASS", "fixture_secret_entropy_bits": 0, "proof_randomness": "Actual provers acquire fresh OS entropy separately; deterministic public fixtures are not secret notes", "scope": "H0 C0/C1 share exact mapped input files; compression candidates derive distinct hash outputs. Abstract arbitrary-sibling paths are not populated-tree evidence. Deposit-backed cases use the complete native-generated history, not a claim of4096 mined transactions.", "legacy_job_ids": "h0/jobs.json contains a planned legacy-named prove schedule; it is not evidence that286 proofs were executed", "artifacts": artifacts}
    output = HERE / "freeze.json"
    if output.exists():
        assert json.loads(output.read_text()) == result, "frozen corpus changed"
    else:
        output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "artifacts"}))

if __name__ == "__main__":
    main()
