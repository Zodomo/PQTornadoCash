import copy
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "calculator"))

import security_calculator as calculator


class SecurityCalculatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "manifests" / "v03-q32.json").open(encoding="utf-8") as handle:
            cls.base = json.load(handle)

    def calculate(self, **changes):
        manifest = copy.deepcopy(self.base)
        manifest.update(changes)
        return calculator.calculate(manifest)

    def test_reproduces_pinned_v03_floors_and_exposes_omission(self):
        report = self.calculate()
        single = report["single_target"]
        self.assertEqual(single["random_words"]["floor_quantum_bits"], 107)
        self.assertEqual(single["udr"]["floor_quantum_bits"], 37)
        self.assertEqual(single["ldr"]["floor_quantum_bits"], 56)
        self.assertEqual(single["best_proven"]["floor_quantum_bits"], 56)
        batch = next(t for t in single["random_words"]["terms"] if t["term"] == "batched-opening-proximity")
        self.assertEqual(batch["proof_status"], "omitted-unmodeled")
        self.assertFalse(batch["applies"])
        self.assertFalse(report["security_qualified_candidate"])
        self.assertFalse(report["independent_human_acceptance"])

    def test_removing_batched_functions_visibly_changes_applicable_soundness(self):
        baseline = self.calculate()
        unbatched = self.calculate(
            num_batched_functions=1,
            batch_count_derivation="explicit",
            batch_count_rationale="Adversarial test intentionally removes batching.",
        )
        self.assertGreater(
            unbatched["single_target"]["ldr"]["quantum_bits"],
            baseline["single_target"]["ldr"]["quantum_bits"],
        )
        self.assertEqual(
            unbatched["single_target"]["random_words"]["quantum_bits"],
            baseline["single_target"]["random_words"]["quantum_bits"],
            "pinned random-words omission must remain explicit rather than guessed",
        )
        baseline_term = next(t for t in baseline["single_target"]["udr"]["terms"] if t["term"] == "batched-opening-proximity")
        unbatched_term = next(t for t in unbatched["single_target"]["udr"]["terms"] if t["term"] == "batched-opening-proximity")
        self.assertTrue(baseline_term["applies"])
        self.assertFalse(unbatched_term["applies"])

    def test_doubling_target_count_costs_one_bit(self):
        report = self.calculate()
        zero = report["multi_target_scenarios"][0]
        custom = calculator._subtract_targets(report["single_target"]["udr"], 1)
        self.assertAlmostEqual(custom["quantum_bits"], zero["udr"]["quantum_bits"] - 1.0)
        q32 = next(x for x in report["multi_target_scenarios"] if x["target_count_log2"] == 32)
        self.assertAlmostEqual(q32["ldr"]["quantum_bits"], report["single_target"]["ldr"]["quantum_bits"] - 32.0)

    def test_reducing_challenge_budget_lowers_ceiling(self):
        low = self.calculate(challenge_field_bits=96)
        cap = next(t for t in low["single_target"]["random_words"]["terms"] if t["term"] == "challenge-field-ceiling")
        self.assertEqual(cap["quantum_bits"], 96.0)
        self.assertLess(low["single_target"]["random_words"]["quantum_bits"], self.calculate()["single_target"]["random_words"]["quantum_bits"])

    def test_query_increases_are_monotonic_for_all_reported_regimes(self):
        previous = None
        for queries in (1, 2, 4, 8, 16, 32, 48, 64, 96, 128):
            report = self.calculate(fri_num_queries=queries)
            current = tuple(report["single_target"][name]["quantum_bits"] for name in ("random_words", "udr", "ldr"))
            if previous is not None:
                for before, after in zip(previous, current):
                    self.assertGreaterEqual(after + 1e-9, before)
            previous = current

    def test_rejects_unbuildable_zk_degree_blowup(self):
        with self.assertRaisesRegex(calculator.ManifestError, "buildable zk limit"):
            self.calculate(fri_log_blowup=2, max_constraint_degree=7)

    def test_rejects_impossible_domain_and_accepts_valid_lde_arity(self):
        with self.assertRaisesRegex(calculator.ManifestError, "available LDE fold depth"):
            self.calculate(fri_log_final_poly_len=2, fri_max_log_arity=12)
        with self.assertRaisesRegex(calculator.ManifestError, "LDE fold domain"):
            self.calculate(fri_log_final_poly_len=20)
        valid = self.calculate(
            logical_trace_height=4,
            proof_degree_bits=2,
            hiding_degree_padding_bits=0,
            fri_log_blowup=1,
            fri_max_log_arity=3,
            max_constraint_degree=2,
        )
        self.assertTrue(valid["single_target"]["udr"]["available"])
        self.assertEqual(self.calculate(fri_log_final_poly_len=0)["manifest"]["fri_log_final_poly_len"], 0)
        highest_valid = self.calculate(fri_log_final_poly_len=8)
        self.assertEqual(highest_valid["manifest"]["fri_log_final_poly_len"], 8)
        for invalid_final_log in (9, 10):
            with self.subTest(invalid_final_log=invalid_final_log):
                with self.assertRaisesRegex(
                    calculator.ManifestError,
                    "strictly below proof_degree_bits",
                ):
                    self.calculate(fri_log_final_poly_len=invalid_final_log)

    def test_hiding_padding_is_separate_and_consistent(self):
        report = self.calculate()
        term = next(t for t in report["single_target"]["udr"]["terms"] if t["term"] == "hiding-degree-padding")
        self.assertEqual(term["inputs"]["logical_degree_bits"], 8)
        self.assertEqual(term["inputs"]["hiding_degree_padding_bits"], 1)
        self.assertEqual(term["inputs"]["proof_degree_bits"], 9)
        with self.assertRaisesRegex(calculator.ManifestError, "proof_degree_bits must equal"):
            self.calculate(hiding_degree_padding_bits=0)

    def test_batch_derivation_rejects_silent_count_mismatch(self):
        with self.assertRaisesRegex(calculator.ManifestError, "num_batched_functions must equal"):
            self.calculate(num_batched_functions=209)

    def test_batch_derivation_is_closed_enum_and_explicit_requires_rationale(self):
        with self.assertRaisesRegex(calculator.ManifestError, "batch_count_derivation must be"):
            self.calculate(batch_count_derivation="relation_plus_quotient_plus_hidin", num_batched_functions=1)
        with self.assertRaisesRegex(calculator.ManifestError, "requires batch_count_rationale"):
            self.calculate(batch_count_derivation="explicit", num_batched_functions=1)
        explicit = self.calculate(
            batch_count_derivation="explicit",
            batch_count_rationale="One deliberately unbatched function for a standalone LDT.",
            num_batched_functions=1,
        )
        self.assertFalse(
            next(
                t
                for t in explicit["single_target"]["udr"]["terms"]
                if t["term"] == "batched-opening-proximity"
            )["applies"]
        )

    def test_udr_survives_when_pinned_ldr_search_has_no_m(self):
        report = self.calculate(
            logical_trace_height=2,
            proof_degree_bits=1,
            hiding_degree_padding_bits=0,
            fri_log_blowup=2,
            max_constraint_degree=2,
        )
        self.assertTrue(report["single_target"]["udr"]["available"])
        self.assertGreater(report["single_target"]["udr"]["quantum_bits"], 0)
        self.assertFalse(report["single_target"]["ldr"]["available"])
        self.assertEqual(report["single_target"]["ldr"]["quantum_bits"], 0)
        self.assertEqual(report["single_target"]["best_proven"]["selected_quantum_regime"], "udr")

    def test_ldr_machine_labels_include_johnson_condition(self):
        report = self.calculate()
        ldr = report["single_target"]["ldr"]
        self.assertEqual(ldr["proof_status"], calculator.LDR_STATUS)
        self.assertIn("mutual correlated agreement", " ".join(ldr["assumptions"]))
        for term in ldr["terms"]:
            if term["term"] in {
                "air-random-linear-combination",
                "deep-ali",
                "fri-query-phase",
                "fri-commit-phase",
                "batched-opening-proximity",
            }:
                self.assertEqual(term["proof_status"], calculator.LDR_STATUS)
                self.assertIn("mutual correlated agreement", " ".join(term["omissions"]))
        self.assertEqual(
            report["single_target"]["best_proven"]["quantum_proof_status"],
            calculator.LDR_STATUS,
        )

    def test_exact_inner_outer_composition_uses_sum_not_min(self):
        report = self.calculate(
            composition={
                "components": [
                    {"name": "inner", "count": 2, "classical_bits": 60, "quantum_bits": 50},
                    {"name": "outer", "count": 1, "use_profile_result": True},
                ],
                "omissions": ["Component independence is not assumed; this is a union bound."],
            }
        )
        composition = report["composition"]
        best = report["single_target"]["best_proven"]
        expected_q = -math.log2(2 * 2**-50 + 2**-best["quantum_bits"])
        self.assertAlmostEqual(composition["quantum_bits"], expected_q, places=8)
        self.assertLess(composition["quantum_bits"], min(50, best["quantum_bits"]))

    def test_target_search_finds_proven_100_and_refuses_to_qualify_it(self):
        targets = calculator.target_profiles(
            self.base,
            targets=(100,),
            max_queries=120,
            max_log_blowup=3,
        )
        profile = targets["targets"][0]["regimes"]["best_proven"]["profile"]
        self.assertEqual(profile["fri_log_blowup"], 3)
        self.assertEqual(profile["fri_num_queries"], 111)
        self.assertGreaterEqual(profile["quantum_bits"], 100)
        self.assertFalse(targets["targets"][0]["security_qualified_candidate"])

    def test_random_words_target_is_excluded_and_retains_batch_omission(self):
        targets = calculator.target_profiles(
            self.base,
            targets=(80,),
            max_queries=10,
            max_log_blowup=12,
        )
        random_words = targets["targets"][0]["regimes"]["random_words"]
        self.assertTrue(random_words["attainable"])
        self.assertEqual(random_words["proof_status"], calculator.RANDOM_STATUS)
        self.assertEqual(
            random_words["target_recommendation"],
            "excluded-conjectural-and-batched-opening-unmodeled",
        )
        self.assertFalse(random_words["batching_omission"]["modeled"])
        self.assertEqual(random_words["batching_omission"]["num_batched_functions"], 210)
        self.assertIn("num_batched_functions", random_words["batching_omission"]["omission"])
        self.assertFalse(targets["random_words_eligible_for_target_recommendation"])

    def test_output_is_deterministic(self):
        first = json.dumps(self.calculate(), sort_keys=True, separators=(",", ":"))
        second = json.dumps(self.calculate(), sort_keys=True, separators=(",", ":"))
        self.assertEqual(first, second)

    def test_csv_and_table_contain_required_columns(self):
        report = self.calculate()
        csv_text = calculator.render_csv(report)
        table = calculator.render_table(report)
        for heading in ("formula_source", "inputs", "classical_bits", "quantum_bits", "proof_status", "binding_quantum", "omissions"):
            self.assertIn(heading, csv_text.splitlines()[0])
        self.assertIn("Bottlenecks (low to high)", table)
        self.assertIn("status: UNREVIEWED", table)
        self.assertIn("formula:", table)
        self.assertIn("source:", table)
        self.assertIn("inputs:", table)
        self.assertIn("omissions:", table)


if __name__ == "__main__":
    unittest.main()
