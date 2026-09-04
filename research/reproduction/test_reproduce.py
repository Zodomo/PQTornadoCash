from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
SPEC = importlib.util.spec_from_file_location("pqtc_reproduce", PACKAGE / "reproduce.py")
assert SPEC and SPEC.loader
reproduce = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reproduce
SPEC.loader.exec_module(reproduce)


class ReproductionTests(unittest.TestCase):
    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PACKAGE / "reproduce.py"), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_minimum_candidates_and_every_action_are_explicit(self) -> None:
        registry = json.loads((PACKAGE / "command-registry.json").read_text())
        self.assertEqual(reproduce.MINIMUM_CANDIDATES - set(registry["candidates"]), set())
        for candidate in registry["candidates"].values():
            self.assertFalse(candidate["eligibleFinalist"])
            self.assertEqual(set(candidate["actions"]), set(reproduce.ACTIONS))
            self.assertTrue(all(value in {"AVAILABLE", reproduce.UNAVAILABLE} for value in candidate["actions"].values()))

    def test_dry_run_emits_exact_argv_without_execution(self) -> None:
        result = self.cli("prove", "--candidate", "C00", "--cases", "all", "--runs", "2", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        commands = document["result"]["commands"]
        self.assertEqual(document["result"]["executedCommands"], 0)
        self.assertEqual([row["executed"] for row in commands], [False, False])
        self.assertEqual(commands[0]["argv"][1], "prove")
        self.assertEqual(commands[0]["argv"][3], "research/reproduction/.work/C00/corpus/fixed")
        self.assertEqual(commands[1]["argv"][3], "research/reproduction/.work/C00/corpus/corpus/swc-v1-000")
        self.assertEqual(commands[0]["argv"][-1], "research/reproduction/.work/C00/proofs/v03-fixed-01")
        self.assertEqual(commands[1]["argv"][-1], "research/reproduction/.work/C00/proofs/v03-corpus-01")

    def test_unsupported_action_fails_closed_even_in_dry_run(self) -> None:
        result = self.cli("verify-evm", "--candidate", "C11", "--client", "anvil", "--dry-run")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["error"]["code"], reproduce.UNAVAILABLE)
        self.assertEqual(result.stdout, "")

    def test_manifest_exclusions_and_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "research/reproduction").mkdir(parents=True)
            (root / "research/ok.json").write_text("{}\n")
            (root / "research/reproduction/evidence-manifest.json").write_text("self")
            (root / "research/cache").mkdir()
            (root / "research/cache/ignored.bin").write_bytes(b"cache")
            (root / "research/target").mkdir()
            (root / "research/target/ignored.bin").write_bytes(b"build")
            (root / "old_reports").mkdir()
            (root / "old_reports/ignored.md").write_text("old")
            (root / ".env").write_text("SECRET=x")
            output = root / "research/reproduction/evidence-manifest.json"
            document = reproduce.generate_manifest(root, [Path("research"), Path("old_reports"), Path(".env")], output)
            self.assertEqual([row["path"] for row in document["files"]], ["research/ok.json"])
            output.write_text(reproduce.canonical_json(document))
            self.assertTrue(reproduce.verify_manifest(root, output)["valid"])
            (root / "research/ok.json").write_text("changed\n")
            result = reproduce.verify_manifest(root, output)
            self.assertFalse(result["valid"])
            self.assertIn("sha256 mismatch: research/ok.json", result["errors"])

    def test_all_safe_is_read_only_and_offline(self) -> None:
        result = self.cli("all-safe")
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)["result"]
        self.assertEqual(document["mode"], "ALL_SAFE_READ_ONLY")
        self.assertEqual(document["subprocesses"], 0)
        self.assertEqual(document["liveChainActions"], 0)
        self.assertEqual(document["secretInputs"], 0)
        self.assertTrue(document["valid"])


if __name__ == "__main__":
    unittest.main()
