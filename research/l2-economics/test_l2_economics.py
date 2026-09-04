from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

import generate
from l2_model import (
    NETWORKS,
    SECP256K1_G,
    SECP256K1_N,
    _point_add,
    _point_mul,
    byte_gas,
    fastlz_compressed_size,
    keccak256,
    payload,
    research_address,
    sign_hash,
    signed_eip1559,
)

HERE = Path(__file__).resolve().parent


class L2EconomicsTests(unittest.TestCase):
    def test_public_research_key_and_signature(self) -> None:
        self.assertEqual(research_address(), "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266")
        digest = keccak256(b"SP-71 deterministic signature test")
        _, r, s = sign_hash(digest)
        inverse = pow(s, -1, SECP256K1_N)
        check = _point_add(
            _point_mul((int.from_bytes(digest, "big") * inverse) % SECP256K1_N, SECP256K1_G),
            _point_mul((r * inverse) % SECP256K1_N, _point_mul(0xAC0974BEC39A17E36BA4A6B4D238FF944BACB478CBED5EFCAE784D7BF4F2FF80)),
        )
        self.assertIsNotNone(check)
        self.assertEqual(check[0] % SECP256K1_N, r)
        self.assertLessEqual(s, SECP256K1_N // 2)

    def test_type_2_transaction_is_deterministic(self) -> None:
        data = payload("repeated", 80 * 1024)
        first = signed_eip1559(10, 1 << 24, data)
        second = signed_eip1559(10, 1 << 24, data)
        self.assertEqual(first, second)
        self.assertEqual(first[0], 2)
        self.assertGreater(len(first), len(data))

    def test_fastlz_sizes_match_pinned_upstream_vectors(self) -> None:
        self.assertEqual(fastlz_compressed_size(b"a" * 1000), 21)
        self.assertEqual(fastlz_compressed_size(bytes(range(256)) * 10), 297)
        self.assertEqual(fastlz_compressed_size(__import__("hashlib").shake_256(b"x").digest(10000)), 10312)
        self.assertEqual(fastlz_compressed_size(b"abc"), 4)
        self.assertEqual(fastlz_compressed_size(b"a" * 70_000), 286)
        self.assertEqual(fastlz_compressed_size(bytes(range(256)) * 300), 573)
        self.assertEqual(fastlz_compressed_size(__import__("hashlib").shake_256(b"x").digest(100_000)), 103_100)

    def test_eip7623_endpoint_floors(self) -> None:
        for kib, all_zero, all_nonzero in ((80, 840_200, 3_297_800), (210, 2_171_400, 8_622_600)):
            size = kib * 1024
            self.assertEqual(byte_gas(b"\x00" * size)["eip7623_floor_gas"], all_zero)
            self.assertEqual(byte_gas(b"\xff" * size)["eip7623_floor_gas"], all_nonzero)

    def test_exact_inclusive_byte_boundaries(self) -> None:
        self.assertEqual(NETWORKS["op-mainnet"]["signed_size_limit"], 131_072)
        self.assertEqual(NETWORKS["arbitrum-one"]["signed_size_limit"], 95_000)
        self.assertEqual(NETWORKS["scroll-mainnet"]["signed_size_limit"], 116_736)
        for config in NETWORKS.values():
            limit = config["signed_size_limit"]
            self.assertTrue(limit <= limit)
            self.assertFalse(limit + 1 <= limit)

    def test_80_and_210_kib_ordinary_outcomes(self) -> None:
        for network, config in NETWORKS.items():
            for family in ("seeded-incompressible", "repeated"):
                tx80 = signed_eip1559(config["chain_id"], config["tx_gas_limit"], payload(family, 80 * 1024))
                tx210 = signed_eip1559(config["chain_id"], config["tx_gas_limit"], payload(family, 210 * 1024))
                self.assertLessEqual(len(tx80), config["signed_size_limit"], (network, family, len(tx80)))
                self.assertGreater(len(tx210), config["signed_size_limit"], (network, family, len(tx210)))

    def test_results_use_projection_and_negative_evidence_labels(self) -> None:
        with (HERE / "results" / "fee-projections.csv").open(newline="") as handle:
            fees = list(csv.DictReader(handle))
        self.assertTrue(fees)
        self.assertTrue(all(row["classification"] == "PROJECTION" for row in fees))
        self.assertTrue(all(row["price_provenance"] == "SYNTHETIC_OFFLINE_INPUT_NOT_LIVE" for row in fees))
        for row in fees:
            if row["network"] != "op-mainnet":
                self.assertEqual(row["total_fee_wei"], "")
                self.assertTrue(row["estimator_status"].startswith("NOT_EVALUATED_MISSING_PINNED_"))
        summary = json.loads((HERE / "results" / "summary.json").read_text())
        self.assertEqual(summary["pqtc_receipt_evidence"], "NOT_EVALUATED_NO_SELECTED_L2_VERIFIER_RECEIPT")
        self.assertTrue(all(value == "PROJECTED_SIZE_REJECTED" for value in summary["ordinary_210_kib_verdict"].values()))
        self.assertIn("NOT_EVALUATED", summary["hardware_profiles"]["H2"])
        self.assertIn("NOT_EVALUATED", summary["hardware_profiles"]["H3"])

    def test_baseline_never_claims_l2_receipt(self) -> None:
        with (HERE / "results" / "baseline-feasibility.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 360)
        self.assertTrue(all(row["size_feasibility"] == "REJECTED_SOURCE_PROVEN_CALLDATA_ALONE_EXCEEDS_SIGNED_TX_LIMIT" for row in rows))
        self.assertTrue(all(row["pqtc_l2_receipt_evidence"] == "NOT_EVALUATED_NO_SELECTED_L2_VERIFIER_RECEIPT" for row in rows))

    def test_retained_artifacts_are_byte_reproducible(self) -> None:
        generate.write_or_check(True)


if __name__ == "__main__":
    unittest.main()
