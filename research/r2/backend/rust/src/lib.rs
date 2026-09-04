use std::{fs, path::{Path, PathBuf}};
use p3_baby_bear::{BabyBear, Poseidon2BabyBear};
use p3_challenger::{CanObserve, DuplexChallenger};
use p3_dft::Radix2DFTSmallBatch;
use p3_field::{extension::BinomialExtensionField, Field, PrimeCharacteristicRing};
use p3_matrix::dense::RowMajorMatrix;
use p3_merkle_tree::MerkleTreeMmcs;
use p3_symmetric::{PaddingFreeSponge, TruncatedPermutation};
use p3_whir::pcs::zk::HidingWhirPcs;
use pqtc_poseidon_air::{WithdrawalWitness, check_witness, generate_withdrawal_trace, public_values, evaluate_constraints};
use pqtc_spec::WithdrawalStatement;
use rand::{SeedableRng, rngs::{SmallRng, StdRng}};
use serde_json::{Value, json};

pub type F = BabyBear;
pub type EF = BinomialExtensionField<F, 4>;
pub type Perm = Poseidon2BabyBear<16>;
pub type Hash = PaddingFreeSponge<Perm, 16, 8, 8>;
pub type Compress = TruncatedPermutation<Perm, 2, 8, 16>;
pub type Challenger = DuplexChallenger<F, Perm, 16, 8>;
pub type Packed = <F as Field>::Packing;
pub type Mmcs = MerkleTreeMmcs<Packed, Packed, Hash, Compress, 2, 8>;
pub type Dft = Radix2DFTSmallBatch<F>;
pub type HidingPcs = HidingWhirPcs<EF, F, Dft, Mmcs, Challenger, StdRng>;
pub const PIN: &str = "3152b14a89067c83775a8076cc262ffc48a1fd7c";

pub fn permutation() -> Perm {
    // Public permutation constants only; never use this RNG for masks.
    Perm::new_from_rng_128(&mut SmallRng::seed_from_u64(1))
}
pub fn mmcs() -> Mmcs {
    Mmcs::new(Hash::new(permutation()), Compress::new(permutation()), 0)
}
pub fn bind_mode(ch: &mut Challenger, mode: u32, security: usize) {
    // Separate exact application control from the deliberately leaking repair probe.
    ch.observe(F::from_u32(0x5232));
    ch.observe(F::from_u32(mode));
    ch.observe(F::from_usize(security));
}
pub fn json_file(path: &Path, value: &Value) {
    fs::write(path, serde_json::to_vec_pretty(value).unwrap()).unwrap();
}
pub struct Input {
    pub statement: WithdrawalStatement,
    pub witness: WithdrawalWitness,
    pub trace: RowMajorMatrix<F>,
    pub public: [F; 64],
    pub output: PathBuf,
    pub security: usize,
}
pub fn input() -> Input {
    let args: Vec<_> = std::env::args().skip(1).collect();
    assert_eq!(args.len(), 4, "usage: <statement.json> <witness.json> <output-directory> <requested-security-bits>");
    let statement = serde_json::from_slice(&fs::read(&args[0]).unwrap()).unwrap();
    let witness = serde_json::from_slice(&fs::read(&args[1]).unwrap()).unwrap();
    check_witness(statement, &witness).expect("exact reference relation and canonical inputs");
    let trace = generate_withdrawal_trace(statement, &witness).unwrap();
    let public = public_values(statement);
    assert!(evaluate_constraints(&trace, &public, Some(1)).is_ok());
    let output = PathBuf::from(&args[2]);
    fs::create_dir_all(&output).unwrap();
    let security = args[3].parse().unwrap();
    assert!(security == 32 || security == 128, "only historical 32-bit control or explicit 128-bit derivation request");
    json_file(&output.join("inputs.json"), &json!({
        "statement": statement, "witness": witness,
        "synthetic_unfunded_only": true, "trace_rows": 256, "trace_columns": 190,
        "constraint_count_per_row": 1186, "constraint_degree": 7,
        "reference_relation": "EXACT_FROZEN_H0", "requested_security_bits": security,
        "security_status": "SECURITY_NOT_QUALIFIED"
    }));
    Input { statement, witness, trace, public, output, security }
}
