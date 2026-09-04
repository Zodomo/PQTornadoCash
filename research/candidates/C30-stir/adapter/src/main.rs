use std::time::Instant;

use p3_baby_bear::{BabyBear, Poseidon2BabyBear};
use p3_challenger::{CanObserve, DuplexChallenger, FieldChallenger};
use p3_commit::{ExtensionMmcs, Pcs};
use p3_dft::Radix2DitParallel;
use p3_field::extension::BinomialExtensionField;
use p3_field::{Field, PrimeCharacteristicRing};
use p3_matrix::dense::RowMajorMatrix;
use p3_merkle_tree::MerkleTreeMmcs;
use p3_stir::{SecurityAssumption, StirParameters, TwoAdicStirPcs};
use p3_symmetric::{PaddingFreeSponge, TruncatedPermutation};
use rand::rngs::SmallRng;
use rand::SeedableRng;
use serde_json::json;
use sha2::{Digest, Sha256};

const PIN: &str = "3152b14a89067c83775a8076cc262ffc48a1fd7c";
const LOG_DEGREE: usize = 12;
const POLYNOMIAL_ELEMENTS: usize = 1 << LOG_DEGREE;
const WIDTH: usize = 1;

type Val = BabyBear;
type Challenge = BinomialExtensionField<Val, 4>;
type Perm = Poseidon2BabyBear<16>;
type MyHash = PaddingFreeSponge<Perm, 16, 8, 8>;
type MyCompress = TruncatedPermutation<Perm, 2, 8, 16>;
type ValMmcs = MerkleTreeMmcs<
    <Val as Field>::Packing,
    <Val as Field>::Packing,
    MyHash,
    MyCompress,
    2,
    8,
>;
type ChallengeMmcs = ExtensionMmcs<Val, Challenge, ValMmcs>;
type Dft = Radix2DitParallel<Val>;
type Challenger = DuplexChallenger<Val, Perm, 16, 8>;
type StirPcs = TwoAdicStirPcs<Val, Dft, ValMmcs, ChallengeMmcs, Challenge, Challenger>;

fn public_polynomial() -> RowMajorMatrix<Val> {
    RowMajorMatrix::new(
        (0..POLYNOMIAL_ELEMENTS)
            .map(|i| Val::from_u64(((i * i + 190 * i + 1_186) % 2_013_265_921) as u64))
            .collect(),
        WIDTH,
    )
}

fn make_pcs() -> (StirPcs, Challenger) {
    let mut rng = SmallRng::seed_from_u64(1);
    let perm = Perm::new_from_rng_128(&mut rng);
    let hash = MyHash::new(perm.clone());
    let compress = MyCompress::new(perm.clone());
    let val_mmcs = ValMmcs::new(hash, compress, 0);
    let challenge_mmcs = ChallengeMmcs::new(val_mmcs.clone());
    let params = StirParameters {
        log_blowup: 2,
        log_folding_factor: 2,
        log_starting_folding_factor: 2,
        soundness_type: SecurityAssumption::CapacityBound,
        security_level: 32,
        max_pow_bits: 0,
        mmcs: challenge_mmcs,
    };
    (
        StirPcs::new(Dft::default(), val_mmcs, params),
        Challenger::new(perm),
    )
}

fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes).iter().map(|byte| format!("{byte:02x}")).collect()
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
        "run through run-focused.sh so the exact source pin and hash are checked"
    );
    const COMPILED_ZK: bool = <StirPcs as Pcs<Challenge, Challenger>>::ZK;
    assert!(!COMPILED_ZK, "pinned TwoAdicStirPcs must remain non-hiding");

    let (pcs, challenger_template) = make_pcs();
    let domain = <StirPcs as Pcs<Challenge, Challenger>>::natural_domain_for_degree(
        &pcs,
        POLYNOMIAL_ELEMENTS,
    );

    let commit_started = Instant::now();
    let (commitment, prover_data) =
        <StirPcs as Pcs<Challenge, Challenger>>::commit(&pcs, [(domain, public_polynomial())]);
    let commit_time_ns = commit_started.elapsed().as_nanos();

    let mut prover_challenger = challenger_template.clone();
    prover_challenger.observe(commitment.clone());
    let point: Challenge = prover_challenger.sample_algebra_element();
    let open_started = Instant::now();
    let (opened, proof) = <StirPcs as Pcs<Challenge, Challenger>>::open(
        &pcs,
        vec![(&prover_data, vec![vec![point]])],
        &mut prover_challenger,
    );
    let open_time_ns = open_started.elapsed().as_nanos();
    let proof_bytes = postcard::to_allocvec(&proof).expect("serialize complete STIR PCS proof");

    let opening = opened[0][0][0].clone();
    let claims = vec![(domain, vec![(point, opening)])];
    let mut verifier_challenger = challenger_template;
    verifier_challenger.observe(commitment.clone());
    let verifier_point: Challenge = verifier_challenger.sample_algebra_element();
    assert_eq!(verifier_point, point);
    let verify_started = Instant::now();
    <StirPcs as Pcs<Challenge, Challenger>>::verify(
        &pcs,
        vec![(commitment, claims)],
        &proof,
        &mut verifier_challenger,
    )
    .expect("complete upstream TwoAdicStirPcs proof must verify");
    let native_verify_time_ns = verify_started.elapsed().as_nanos();

    let result = json!({
        "schema_version": 1,
        "candidate_id": "C30",
        "spike_id": "SP-52",
        "status": "BENCHMARK_ONLY",
        "evidence_class": "UPSTREAM_BASELINE_NOT_PQTC",
        "measurement_label": "UPSTREAM_BASELINE_NOT_PQTC",
        "upstream": {
            "repository": "https://github.com/Plonky3/Plonky3",
            "commit": PIN,
            "package": "p3-stir",
            "api": "TwoAdicStirPcs",
            "source_hashes_verified_by_runner": true
        },
        "compiled_api_checks": {
            "two_adic_stir_pcs": true,
            "zk": COMPILED_ZK,
            "hiding": false
        },
        "proxy_geometry": {
            "public_data": true,
            "log_degree": LOG_DEGREE,
            "polynomial_elements": POLYNOMIAL_ELEMENTS,
            "matrix_width": WIDTH,
            "opened_points": 1,
            "log_blowup": 2,
            "log_folding_factor": 2,
            "security_level_parameter": 32,
            "matched_with_candidate": "C20",
            "implements_frozen_pqtc_relation": false
        },
        "verified": true,
        "proof_bytes": proof_bytes.len(),
        "proof_sha256": sha256_hex(&proof_bytes),
        "commit_time_ns": commit_time_ns,
        "open_time_ns": open_time_ns,
        "native_verify_time_ns": native_verify_time_ns,
        "peak_rss_bytes": peak_rss_bytes(),
        "relation_gate": {
            "accepted_sp10_relation_available": false,
            "control_relation": "frozen-v0.3/H0",
            "upstream_smoke_implements_relation": false
        },
        "privacy_finalist": false,
        "pqtc_measurement": false
    });
    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
