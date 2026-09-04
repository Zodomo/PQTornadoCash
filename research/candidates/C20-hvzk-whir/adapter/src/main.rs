use std::time::Instant;

use p3_baby_bear::{BabyBear, Poseidon2BabyBear};
use p3_challenger::DuplexChallenger;
use p3_commit::MultilinearPcs;
use p3_dft::Radix2DFTSmallBatch;
use p3_field::extension::BinomialExtensionField;
use p3_field::{Field, PrimeCharacteristicRing};
use p3_merkle_tree::MerkleTreeMmcs;
use p3_multilinear_util::point::Point;
use p3_multilinear_util::poly::Poly;
use p3_symmetric::{PaddingFreeSponge, TruncatedPermutation};
use p3_whir::fiat_shamir::domain_separator::DomainSeparator;
use p3_whir::parameters::{FoldingFactor, ProtocolParameters, SecurityAssumption};
use p3_whir::pcs::zk::{HidingWhirPcs, ZkParameters, ZkWhirConfig};
use postcard::to_allocvec;
use rand::rngs::{SmallRng, StdRng};
use rand::{SeedableRng};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

const PIN: &str = "3152b14a89067c83775a8076cc262ffc48a1fd7c";
const NUM_VARIABLES: usize = 12;
const PUBLIC_PROXY_ELEMENTS: usize = 1 << NUM_VARIABLES;

type F = BabyBear;
type EF = BinomialExtensionField<F, 4>;
type Perm = Poseidon2BabyBear<16>;
type MyHash = PaddingFreeSponge<Perm, 16, 8, 8>;
type MyCompress = TruncatedPermutation<Perm, 2, 8, 16>;
type MyChallenger = DuplexChallenger<F, Perm, 16, 8>;
type PackedF = <F as Field>::Packing;
type MyMmcs = MerkleTreeMmcs<PackedF, PackedF, MyHash, MyCompress, 2, 8>;
type MyDft = Radix2DFTSmallBatch<F>;
type Pcs = HidingWhirPcs<EF, F, MyDft, MyMmcs, MyChallenger, StdRng>;

fn permutation() -> Perm {
    // This seed fixes public Poseidon2 parameters only. It never drives hiding masks.
    Perm::new_from_rng_128(&mut SmallRng::seed_from_u64(1))
}

fn make_config() -> ZkWhirConfig<EF, F, MyChallenger> {
    ZkWhirConfig::new(
        NUM_VARIABLES,
        ProtocolParameters {
            security_level: 32,
            pow_bits: 0,
            round_log_inv_rates: vec![],
            folding_factor: FoldingFactor::Constant(4),
            soundness_type: SecurityAssumption::CapacityBound,
            starting_log_inv_rate: 2,
        },
        ZkParameters {
            ell_zk: 4,
            mask_log_inv_rate: 1,
        },
    )
    .expect("the pinned upstream smoke configuration must be valid")
}

fn make_pcs(config: ZkWhirConfig<EF, F, MyChallenger>) -> Pcs {
    let perm = permutation();
    let mmcs = MyMmcs::new(MyHash::new(perm.clone()), MyCompress::new(perm), 0);
    // A new OS-seeded CSPRNG is constructed for each proof. HidingWhirPcs then forks
    // fresh StdRng streams for commit and open through its CryptoRng-only API.
    Pcs::new(config, MyDft::default(), mmcs, rand::make_rng::<StdRng>())
}

fn public_polynomial() -> Poly<F> {
    // Stable, public proxy data tied to frozen H0 dimensions. This is deliberately
    // not a PQTC witness and does not implement any withdrawal constraint.
    Poly::new(
        (0..PUBLIC_PROXY_ELEMENTS)
            .map(|i| F::from_u64(((i * i + 190 * i + 1_186) % 2_013_265_921) as u64))
            .collect(),
    )
}

fn public_point() -> Point<EF> {
    Point::new(
        (0..NUM_VARIABLES)
            .map(|i| EF::from_u64((17 + 13 * i) as u64))
            .collect(),
    )
}

fn challenger(pcs: &Pcs) -> MyChallenger {
    let mut challenger = MyChallenger::new(permutation());
    let mut separator = DomainSeparator::new(vec![]);
    pcs.add_domain_separator::<8>(&mut separator);
    separator.observe_domain_separator(&mut challenger);
    challenger
}

fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes).iter().map(|byte| format!("{byte:02x}")).collect()
}

fn prove_once() -> Value {
    let polynomial = public_polynomial();
    let point = public_point();
    let config = make_config();
    let pcs = make_pcs(config);
    let expected_eval = polynomial.eval_base(&point);

    let mut prover_challenger = challenger(&pcs);
    let prover_started = Instant::now();
    let (commitment, prover_data) = pcs.commit(polynomial, &mut prover_challenger);
    let proof = pcs.open(prover_data, vec![point.clone()], &mut prover_challenger);
    let prover_ns = prover_started.elapsed().as_nanos();

    assert_eq!(proof.evals.as_slice(), &[expected_eval]);
    let proof_bytes = to_allocvec(&proof).expect("serialize complete upstream proof");

    let mut verifier_challenger = challenger(&pcs);
    let verifier_started = Instant::now();
    pcs.verify(&commitment, &proof, &mut verifier_challenger, vec![point])
        .expect("complete upstream HidingWhirPcs proof must verify");
    let verifier_ns = verifier_started.elapsed().as_nanos();

    json!({
        "verified": true,
        "proof_bytes": proof_bytes.len(),
        "proof_sha256": sha256_hex(&proof_bytes),
        "prover_time_ns": prover_ns,
        "native_verify_time_ns": verifier_ns
    })
}

#[cfg(target_os = "macos")]
fn peak_rss_bytes() -> u64 {
    let mut usage = std::mem::MaybeUninit::<libc::rusage>::uninit();
    let rc = unsafe { libc::getrusage(libc::RUSAGE_SELF, usage.as_mut_ptr()) };
    assert_eq!(rc, 0, "getrusage failed");
    unsafe { usage.assume_init().ru_maxrss as u64 }
}

#[cfg(not(target_os = "macos"))]
fn peak_rss_bytes() -> u64 {
    let mut usage = std::mem::MaybeUninit::<libc::rusage>::uninit();
    let rc = unsafe { libc::getrusage(libc::RUSAGE_SELF, usage.as_mut_ptr()) };
    assert_eq!(rc, 0, "getrusage failed");
    unsafe { (usage.assume_init().ru_maxrss as u64) * 1024 }
}

fn main() {
    assert_eq!(
        std::env::var("PQTC_SOURCE_HASHES_VERIFIED").as_deref(),
        Ok("1"),
        "run through run-focused.sh so the exact source pin and hashes are checked"
    );
    let security_report = make_config().hiding_base_case_security_report();
    let first = prove_once();
    let second = prove_once();
    let proofs_differ = first["proof_sha256"] != second["proof_sha256"];
    assert!(proofs_differ, "fresh CryptoRng masks must change repeated proofs");

    let result = json!({
        "schema_version": 1,
        "candidate_id": "C20",
        "spike_id": "SP-51",
        "status": "DEFERRED",
        "evidence_class": "UPSTREAM_BASELINE_NOT_PQTC",
        "measurement_label": "UPSTREAM_BASELINE_NOT_PQTC",
        "upstream": {
            "repository": "https://github.com/Plonky3/Plonky3",
            "commit": PIN,
            "package": "p3-whir",
            "api": "HidingWhirPcs",
            "source_hashes_verified_by_runner": true
        },
        "compiled_api_checks": {
            "hiding_whir_pcs": true,
            "rng_type": "rand::rngs::StdRng",
            "rng_trait_gate": "CryptoRng + Send + Sync",
            "fresh_os_seed_per_proof": true,
            "zk": true
        },
        "proxy_geometry": {
            "public_data": true,
            "num_variables": NUM_VARIABLES,
            "polynomial_elements": PUBLIC_PROXY_ELEMENTS,
            "opened_points": 1,
            "matched_with_candidate": "C30",
            "implements_frozen_pqtc_relation": false
        },
        "runs": [first, second],
        "repeat_proofs_differ": proofs_differ,
        "peak_rss_bytes": peak_rss_bytes(),
        "security_report_scope": "UPSTREAM_DIAGNOSTIC_HIDING_BASE_CASE_ONLY_NOT_END_TO_END",
        "security_report": security_report,
        "relation_gate": {
            "accepted_sp10_relation_available": false,
            "control_relation": "frozen-v0.3/H0",
            "upstream_smoke_implements_relation": false
        },
        "integration_gates": {
            "sp02_native_malformed_proof_panic": "FAIL",
            "sp10_accepted_relation": "MISSING",
            "matching_evm_verifier": "MISSING",
            "exact_transcript_qrom_reduction": "MISSING",
            "external_cryptographic_review": "NOT_PERFORMED"
        },
        "pqtc_measurement": false
    });
    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
