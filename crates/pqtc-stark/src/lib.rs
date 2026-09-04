//! Hiding two-adic FRI proving for the Poseidon2 withdrawal AIR.

pub mod codec;
pub mod crypto;
mod query;

use p3_baby_bear::BabyBear;
use p3_commit::ExtensionMmcs;
use p3_dft::Radix2DitParallel;
use p3_field::extension::BinomialExtensionField;
use p3_fri::{FriParameters, HidingFriPcs};
use p3_merkle_tree::MerkleTreeHidingMmcs;
use p3_uni_stark::{Proof, StarkConfig, prove, verify};
pub use pqtc_poseidon_air::{RelationError, WithdrawalWitness};
use pqtc_poseidon_air::{WithdrawalAir, generate_withdrawal_trace, public_values};
use pqtc_spec::{Digest512, WithdrawalStatement};
use rand::{SeedableRng, rngs::StdRng};

use crate::crypto::{DIGEST_WORDS, ProofLeafHasher, ProofNodeCompressor, Transcript512};

pub type Val = BabyBear;
pub type Challenge = BinomialExtensionField<Val, 4>;
type Packing = [Val; p3_keccak::VECTOR_LEN];
type DigestPacking = [u64; p3_keccak::VECTOR_LEN];
pub type ValMmcs = MerkleTreeHidingMmcs<
    Packing,
    DigestPacking,
    ProofLeafHasher,
    ProofNodeCompressor,
    StdRng,
    2,
    DIGEST_WORDS,
    8,
>;
pub type ChallengeMmcs = ExtensionMmcs<Val, Challenge, ValMmcs>;
pub type Dft = Radix2DitParallel<Val>;
pub type Pcs = HidingFriPcs<Val, Dft, ValMmcs, ChallengeMmcs, StdRng>;
pub type Config = StarkConfig<Pcs, Challenge, Transcript512>;
pub type StarkProof = Proof<Config>;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SecurityProfile {
    Dev,
    Ci,
    SepoliaV03,
}

impl SecurityProfile {
    #[must_use]
    pub const fn fri(self) -> (usize, usize, usize, usize, usize) {
        match self {
            Self::Dev => (3, 0, 2, 0, 0),
            Self::Ci => (3, 0, 16, 4, 4),
            Self::SepoliaV03 => (4, 0, 32, 16, 16),
        }
    }

    #[must_use]
    pub const fn random_codewords(self) -> usize {
        match self {
            Self::Dev => 2,
            Self::Ci | Self::SepoliaV03 => 4,
        }
    }
}

/// Constructs a proving or verification configuration from operating-system entropy.
/// No deterministic seed is exposed by the production API.
#[must_use]
pub fn config_from_os_entropy(
    profile: SecurityProfile,
    parameter_id: Digest512,
    public_values: &[Val],
) -> Config {
    let mut os_rng = rand::rng();
    let mmcs_rng = StdRng::from_rng(&mut os_rng);
    let pcs_rng = StdRng::from_rng(&mut os_rng);
    build_config(profile, parameter_id, public_values, mmcs_rng, pcs_rng)
}

fn build_config(
    profile: SecurityProfile,
    parameter_id: Digest512,
    public_values: &[Val],
    mmcs_rng: StdRng,
    pcs_rng: StdRng,
) -> Config {
    let leaf_hash = ProofLeafHasher;
    let compress = ProofNodeCompressor;
    let val_mmcs = ValMmcs::new(leaf_hash, compress, 0, mmcs_rng);
    let challenge_mmcs = ChallengeMmcs::new(val_mmcs.clone());
    let dft = Dft::default();
    let (log_blowup, log_final_poly_len, num_queries, commit_pow, query_pow) = profile.fri();
    let fri_params = FriParameters {
        log_blowup,
        log_final_poly_len,
        max_log_arity: 1,
        num_queries,
        commit_proof_of_work_bits: commit_pow,
        query_proof_of_work_bits: query_pow,
        mmcs: challenge_mmcs,
    };
    let pcs = Pcs::new(
        dft,
        val_mmcs,
        fri_params,
        profile.random_codewords(),
        pcs_rng,
    );
    let challenger = Transcript512::new(parameter_id, public_values);
    Config::new(pcs, challenger)
}
#[must_use]
pub fn withdrawal_public_values(
    statement: WithdrawalStatement,
) -> [Val; pqtc_spec::PUBLIC_VALUES_COUNT] {
    public_values(statement)
}

#[must_use]
pub fn withdrawal_config_from_os_entropy(
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
) -> Config {
    config_from_os_entropy(profile, parameter_id, &withdrawal_public_values(statement))
}

pub fn prove_withdrawal(
    config: &Config,
    statement: WithdrawalStatement,
    witness: &WithdrawalWitness,
) -> Result<StarkProof, RelationError> {
    let trace = generate_withdrawal_trace(statement, witness)?;
    let public_values = withdrawal_public_values(statement);
    Ok(prove(
        config,
        &WithdrawalAir::default(),
        trace,
        &public_values,
    ))
}

#[must_use]
pub fn verify_withdrawal(
    config: &Config,
    statement: WithdrawalStatement,
    proof: &StarkProof,
) -> bool {
    let public_values = withdrawal_public_values(statement);
    verify(config, &WithdrawalAir::default(), proof, &public_values).is_ok()
}
