from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
REPOSITORY = HARNESS.parents[1]
for directory in ("gas-schedules", "proof-ledger", "hardware-detect", "report-generator", "benchctl"):
    sys.path.insert(0, str(HARNESS / directory))

from gas_schedules import calculate_scenarios
from hardware_detect import detect_environment
from keccak import Keccak256, self_test
from proof_ledger import LedgerError, build_ledger
from report_generator import generate_manifest, generate_summaries, verify_manifest
from schema_validator import load_json, validate_document


def valid_run() -> dict[str, object]:
    return {
        "schema_version": "1",
        "run_id": "test-run-1",
        "candidate_id": "candidate-a",
        "spike_id": "SP-01",
        "timestamp_utc": "2026-09-04T12:00:00Z",
        "git": {"repository": "local", "commit": "1234567", "dirty": False, "submodules": {}},
        "toolchain": {"rustc": "rustc 1", "solc": "solc 1", "foundry": "forge 1", "evm_revision": "cancun"},
        "hardware": {
            "hardware_id": "test-hardware",
            "cpu_model": "test-cpu",
            "physical_cores": 1,
            "logical_cores": 1,
            "ram_bytes": 1,
            "os": "test-os",
        },
        "protocol": {
            "semantic_version": "1",
            "asset": "ETH",
            "denomination_wei": "1",
            "tree_depth": 20,
            "case_id": "case-000",
        },
        "relation": {
            "kind": "AIR",
            "logical_rows": 1,
            "padded_rows": 1,
            "trace_width": 1,
            "constraint_count": 1,
            "max_degree": 1,
            "batched_functions": 1,
        },
        "proof_system": {
            "name": "test",
            "base_field": "test",
            "challenge_field": "test",
            "hiding": True,
            "trusted_setup": False,
            "classical_wrapper": False,
        },
        "security": {
            "classification": "BENCHMARK_ONLY",
            "terms": [],
            "lowest_accepted_bits": None,
            "qrom_status": "unknown",
            "zk_status": "test-only",
        },
        "prover": {
            "success": False,
            "cold_or_warm": "COLD",
            "wall_ms": None,
            "peak_rss_bytes": None,
            "native_verify_ms": None,
            "distribution": {"count": 0, "p50": None, "p95": None, "p99": None},
        },
        "proof_bytes": {
            "raw_proof_bytes": 3,
            "abi_calldata_bytes": 4,
            "zero_bytes": 1,
            "nonzero_bytes": 3,
            "sections": {"proof": 3},
        },
        "evm": {
            "measured": False,
            "client": "none",
            "execution_gas": 0,
            "standard_intrinsic_gas": 21000,
            "receipt_gas_used": 0,
            "gas_scenarios": [
                {"name": "ACTIVE_EIP7623", "floor_gas": 21000, "total_gas": 21000, "tx_cap_margin": 16756216},
                {"name": "SCENARIO_EIP7976_64_PER_BYTE", "floor_gas": 21000, "total_gas": 21000, "tx_cap_margin": 16756216},
                {"name": "SCENARIO_EIP8311_96_PER_BYTE", "floor_gas": 21000, "total_gas": 21000, "tx_cap_margin": 16756216},
            ],
            "runtime_bytes": 0,
        },
        "artifacts": [],
        "result": {
            "success": False,
            "gate_status": "FAIL",
            "failure_reason": "intentional negative result",
            "confounders": ["none"],
            "notes": ["retained"],
        },
    }


class GasScheduleTests(unittest.TestCase):
    def test_three_data_floor_scenarios(self) -> None:
        result = calculate_scenarios(1000, 0, 0)
        scenarios = {item["name"]: item for item in result["gas_scenarios"]}
        self.assertEqual(scenarios["ACTIVE_EIP7623"]["total_gas"], 31_000)
        self.assertEqual(scenarios["SCENARIO_EIP7976_64_PER_BYTE"]["total_gas"], 85_000)
        self.assertEqual(scenarios["SCENARIO_EIP8311_96_PER_BYTE"]["total_gas"], 117_000)

    def test_creation_charges_are_in_standard_branch(self) -> None:
        result = calculate_scenarios(1, 1, 0, is_contract_creation=True)
        self.assertEqual(result["initcode_words"], 1)
        self.assertEqual(result["creation_intrinsic_gas"], 32_002)
        self.assertEqual(result["standard_total_gas"], 53_022)
        self.assertTrue(all(item["total_gas"] == 53_022 for item in result["gas_scenarios"]))


class LedgerTests(unittest.TestCase):
    def test_counts_and_sections_reconcile(self) -> None:
        result = build_ledger(b"abc", b"\x00abc", {"header": 1, "body": 2})
        self.assertEqual(result["zero_bytes"], 1)
        self.assertEqual(result["nonzero_bytes"], 3)
        self.assertEqual(result["abi_overhead_bytes"], 1)
        self.assertTrue(result["reconciliation"]["sections_equal_raw_proof"])

    def test_section_mismatch_is_rejected(self) -> None:
        with self.assertRaises(LedgerError):
            build_ledger(b"abc", b"abc", {"proof": 2})


class KeccakAndManifestTests(unittest.TestCase):
    def test_ethereum_vectors(self) -> None:
        self_test()
        self.assertEqual(
            Keccak256(b"abc").hexdigest(),
            "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45",
        )

    def test_manifest_is_sorted_repeatable_and_self_excluding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "z.bin").write_bytes(b"z")
            (root / "a.bin").write_bytes(b"")
            output = root / "manifest.json"
            manifest = generate_manifest([root], output, root)
            first = output.read_bytes()
            manifest_again = generate_manifest([root], output, root)
            self.assertEqual(first, output.read_bytes())
            self.assertEqual(manifest, manifest_again)
            self.assertEqual([item["path"] for item in manifest["artifacts"]], ["a.bin", "z.bin"])
            self.assertEqual(manifest["excluded"], [{"path": "manifest.json", "reason": "self_reference"}])
            self.assertTrue(verify_manifest(output, root)["valid"])


class SchemaAndSummaryTests(unittest.TestCase):
    def test_root_schema_accepts_valid_and_rejects_invalid_required_fields(self) -> None:
        schema = load_json(REPOSITORY / "benchmark-run.schema.json")
        run = valid_run()
        self.assertEqual(validate_document(run, schema), [])
        del run["proof_bytes"]
        run["spike_id"] = "bad"
        errors = validate_document(run, schema)
        self.assertTrue(any(item["keyword"] == "required" and "proof_bytes" in item["message"] for item in errors))
        self.assertTrue(any(item["path"] == "$.spike_id" and item["keyword"] == "pattern" for item in errors))

    def test_csv_retains_negative_outcome_and_source_digests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            schema = root / "benchmark-run.schema.json"
            schema.write_bytes((REPOSITORY / "benchmark-run.schema.json").read_bytes())
            runs = root / "runs"
            runs.mkdir()
            (runs / "run.json").write_text(json.dumps(valid_run()), encoding="utf-8")
            counts = generate_summaries(
                [Path("runs")], Path("all.csv"), Path("candidates.csv"), schema, root
            )
            text = (root / "all.csv").read_text(encoding="utf-8")
            self.assertEqual(counts, {"runs": 1, "candidates": 1})
            self.assertIn("intentional negative result", text)
            self.assertIn("source_run_sha256", text)
            self.assertIn("source_run_keccak256", text)


class DetectionTests(unittest.TestCase):
    def test_detection_has_schema_required_fields(self) -> None:
        result = detect_environment("cancun")
        self.assertGreater(result["hardware"]["physical_cores"], 0)
        self.assertGreater(result["hardware"]["ram_bytes"], 0)
        self.assertEqual(result["toolchain"]["evm_revision"], "cancun")
        self.assertIn("complete", result["detection"])


if __name__ == "__main__":
    unittest.main()
