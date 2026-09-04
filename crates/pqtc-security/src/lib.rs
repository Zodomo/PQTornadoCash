//! Canonical parameter manifests and conservative security accounting.

use p3_air::symbolic::AirLayout;
use p3_baby_bear::BabyBear;
use p3_field::extension::BinomialExtensionField;
use p3_security::fri::FriRegime;
use p3_uni_stark::{ConjecturedSecurity, ProvenSecurity, StarkSecurityParams};
use pqtc_hash::{keccak256, parameter_id};
use pqtc_poseidon_air::{NUM_WITHDRAWAL_COLS, TRACE_HEIGHT, WithdrawalAir};
use pqtc_spec::{Digest512, PLONKY3_COMMIT, PROTOCOL_VERSION, TREE_DEPTH};
use serde::{Deserialize, Serialize};
use thiserror::Error;

pub const MANIFEST_MAGIC: [u8; 8] = *b"PQTCPRM3";
pub const MANIFEST_VERSION: u16 = 3;

pub const CHALLENGE_FIELD_BITS: usize = 120;
pub const QUANTUM_ADJUSTED_MMCS_BITS: usize = 128;
pub const BATCHED_FUNCTIONS: usize = NUM_WITHDRAWAL_COLS + 16 + 4;
pub const PROOF_DEGREE_BITS: usize = 9;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct SecurityAnalysis {
    pub conjectured_bits: usize,
    pub proven_unique_decoding_bits: usize,
    pub proven_list_decoding_bits: usize,
    pub proven_bits: usize,
    pub challenge_field_bits: usize,
    pub quantum_adjusted_mmcs_bits: usize,
    pub batched_functions: usize,
    pub air_constraints: usize,
    pub air_max_constraint_degree: usize,
}

#[must_use]
pub fn analyze_profile(name: &str) -> SecurityAnalysis {
    analyze_manifest(&ParameterManifest::profile(name))
}

#[must_use]
pub fn analyze_manifest(manifest: &ParameterManifest) -> SecurityAnalysis {
    let fri = FriRegime {
        log_blowup: usize::from(manifest.fri_log_blowup),
        num_queries: usize::from(manifest.fri_query_count),
        log_final_poly_len: 0,
        max_log_arity: usize::from(manifest.fri_max_log_arity),
        commit_pow_bits: usize::from(manifest.commit_grinding_bits) / 2,
        query_pow_bits: usize::from(manifest.query_grinding_bits) / 2,
    };
    let air = WithdrawalAir::default();
    let mut parameters =
        StarkSecurityParams::from_air::<BabyBear, BinomialExtensionField<BabyBear, 4>, _>(
            fri,
            &air,
            AirLayout::from_air::<BabyBear>(&air),
            CHALLENGE_FIELD_BITS,
            QUANTUM_ADJUSTED_MMCS_BITS,
            2,
        );
    parameters.num_batched_functions = BATCHED_FUNCTIONS;
    let air_constraints = parameters.num_constraints;
    let air_max_constraint_degree = parameters.air_max_constraint_degree;
    let conjectured = ConjecturedSecurity::compute_from_params(&parameters, PROOF_DEGREE_BITS);
    let proven = ProvenSecurity::compute_from_proof(PROOF_DEGREE_BITS, &parameters);
    SecurityAnalysis {
        conjectured_bits: conjectured.security_bits,
        proven_unique_decoding_bits: proven.unique_decoding_bits,
        proven_list_decoding_bits: proven.list_decoding_bits,
        proven_bits: proven.security_bits(),
        challenge_field_bits: CHALLENGE_FIELD_BITS,
        quantum_adjusted_mmcs_bits: QUANTUM_ADJUSTED_MMCS_BITS,
        batched_functions: BATCHED_FUNCTIONS,
        air_constraints,
        air_max_constraint_degree,
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ParameterManifest {
    pub profile: String,
    pub plonky3_commit: String,
    pub rust_toolchain: String,
    pub field: String,
    pub extension_degree: u8,
    pub air_version: u16,
    pub air_source_hash: [u8; 32],
    pub tree_depth: u8,
    pub protocol_version: u32,
    pub trace_height: u32,
    pub fri_log_blowup: u8,
    pub fri_max_log_arity: u8,
    pub fri_query_count: u16,
    pub fri_final_polynomial_bound: u32,
    pub commit_grinding_bits: u8,
    pub query_grinding_bits: u8,
    pub random_codeword_count: u8,
    pub mmcs_salt_elements: u8,
    pub proof_codec_version: u16,
    pub verifier_interface_version: u16,
    pub expected_runtime_code_hashes: Vec<[u8; 32]>,
}

fn air_source_hash() -> [u8; 32] {
    let mut component_hashes = [0u8; 64];
    component_hashes[..32].copy_from_slice(&keccak256(include_bytes!(
        "../../pqtc-poseidon-air/src/lib.rs"
    )));
    component_hashes[32..].copy_from_slice(&keccak256(include_bytes!(
        "../../pqtc-poseidon-air/src/air.rs"
    )));
    keccak256(&component_hashes)
}

impl ParameterManifest {
    #[must_use]
    pub fn profile(name: &str) -> Self {
        let (blowup, queries, commit_pow, query_pow, random) = match name {
            "dev" => (3, 2, 0, 0, 2),
            "ci" => (3, 16, 4, 4, 4),
            "sepolia-v0.3" => (4, 32, 16, 16, 4),
            _ => panic!("unknown parameter profile"),
        };
        Self {
            profile: name.to_owned(),
            plonky3_commit: PLONKY3_COMMIT.to_owned(),
            rust_toolchain: "1.97.0".to_owned(),
            field: "BabyBear(2013265921)".to_owned(),
            extension_degree: 4,
            air_source_hash: air_source_hash(),
            air_version: 3,
            tree_depth: TREE_DEPTH,
            protocol_version: PROTOCOL_VERSION,
            trace_height: TRACE_HEIGHT as u32,
            fri_log_blowup: blowup,
            fri_max_log_arity: 1,
            fri_query_count: queries,
            fri_final_polynomial_bound: 1,
            commit_grinding_bits: commit_pow,
            query_grinding_bits: query_pow,
            random_codeword_count: random,
            mmcs_salt_elements: 8,
            proof_codec_version: 3,
            verifier_interface_version: 3,
            expected_runtime_code_hashes: Vec::new(),
        }
    }

    pub fn validate(&self) -> Result<(), ManifestError> {
        let expected_profile = match self.profile.as_str() {
            "dev" => (3, 2, 0, 0, 2),
            "ci" => (3, 16, 4, 4, 4),
            "sepolia-v0.3" => (4, 32, 16, 16, 4),
            _ => return Err(ManifestError::Profile),
        };
        if self.plonky3_commit != PLONKY3_COMMIT {
            return Err(ManifestError::Plonky3Commit);
        }
        if self.air_source_hash != air_source_hash() {
            return Err(ManifestError::AirSourceHash);
        }
        if self.air_version != 3
            || self.tree_depth != TREE_DEPTH
            || self.protocol_version != PROTOCOL_VERSION
            || self.proof_codec_version != 3
            || self.verifier_interface_version != 3
        {
            return Err(ManifestError::Protocol);
        }
        if self.trace_height != TRACE_HEIGHT as u32 {
            return Err(ManifestError::TraceHeight);
        }
        if self.field != "BabyBear(2013265921)" || self.extension_degree != 4 {
            return Err(ManifestError::Parameters);
        }
        if self.mmcs_salt_elements != 8 || self.random_codeword_count != expected_profile.4 {
            return Err(ManifestError::Hiding);
        }
        if self.fri_max_log_arity != 1
            || self.fri_final_polynomial_bound != 1
            || self.fri_query_count == 0
        {
            return Err(ManifestError::Parameters);
        }
        if self.profile == "sepolia-v0.3" && analyze_manifest(self).conjectured_bits < 100 {
            return Err(ManifestError::Security);
        }
        if (
            self.fri_log_blowup,
            self.fri_query_count,
            self.commit_grinding_bits,
            self.query_grinding_bits,
            self.random_codeword_count,
        ) != expected_profile
        {
            return Err(ManifestError::Parameters);
        }
        Ok(())
    }

    /// Conservative proven-security floor from Plonky3's round-by-round bound.
    #[must_use]
    pub fn conservative_quantum_bits(&self) -> u16 {
        analyze_manifest(self)
            .proven_bits
            .try_into()
            .unwrap_or(u16::MAX)
    }

    /// Deployment target under Plonky3's documented random-words conjecture.
    #[must_use]
    pub fn target_quantum_bits(&self) -> u16 {
        analyze_manifest(self)
            .conjectured_bits
            .try_into()
            .unwrap_or(u16::MAX)
    }

    pub fn encode_binary(&self) -> Result<Vec<u8>, ManifestError> {
        self.validate()?;
        let mut out = Vec::new();
        out.extend_from_slice(&MANIFEST_MAGIC);
        put_u16(&mut out, MANIFEST_VERSION);
        put_string(&mut out, &self.profile)?;
        put_string(&mut out, &self.plonky3_commit)?;
        put_string(&mut out, &self.rust_toolchain)?;
        put_string(&mut out, &self.field)?;
        out.push(self.extension_degree);
        put_u16(&mut out, self.air_version);
        out.extend_from_slice(&self.air_source_hash);
        out.push(self.tree_depth);
        out.extend_from_slice(&self.protocol_version.to_be_bytes());
        out.extend_from_slice(&self.trace_height.to_be_bytes());
        out.push(self.fri_log_blowup);
        out.push(self.fri_max_log_arity);
        put_u16(&mut out, self.fri_query_count);
        out.extend_from_slice(&self.fri_final_polynomial_bound.to_be_bytes());
        out.push(self.commit_grinding_bits);
        out.push(self.query_grinding_bits);
        out.push(self.random_codeword_count);
        out.push(self.mmcs_salt_elements);
        put_u16(&mut out, self.proof_codec_version);
        put_u16(&mut out, self.verifier_interface_version);
        put_u16(
            &mut out,
            self.expected_runtime_code_hashes
                .len()
                .try_into()
                .map_err(|_| ManifestError::Length)?,
        );
        for hash in &self.expected_runtime_code_hashes {
            out.extend_from_slice(hash);
        }
        Ok(out)
    }

    pub fn id(&self) -> Result<Digest512, ManifestError> {
        Ok(parameter_id(&self.encode_binary()?))
    }
}

fn put_u16(out: &mut Vec<u8>, value: u16) {
    out.extend_from_slice(&value.to_be_bytes());
}
fn put_string(out: &mut Vec<u8>, value: &str) -> Result<(), ManifestError> {
    put_u16(
        out,
        value.len().try_into().map_err(|_| ManifestError::Length)?,
    );
    out.extend_from_slice(value.as_bytes());
    Ok(())
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum ManifestError {
    #[error("unknown profile")]
    Profile,
    #[error("Plonky3 commit differs from the protocol pin")]
    Plonky3Commit,
    #[error("AIR source hash differs from the v0.3 withdrawal AIR")]
    AirSourceHash,
    #[error("protocol constants differ from v0.3")]
    Protocol,
    #[error("trace height is invalid")]
    TraceHeight,
    #[error("hiding parameters are not canonical")]
    Hiding,
    #[error("profile parameters are not canonical")]
    Parameters,
    #[error("sepolia profile does not meet the conjectured 100-bit target")]
    Security,
    #[error("manifest field is too long")]
    Length,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn profiles_encode_deterministically() {
        for name in ["dev", "ci", "sepolia-v0.3"] {
            let manifest = ParameterManifest::profile(name);
            assert_eq!(
                manifest.encode_binary().unwrap(),
                manifest.encode_binary().unwrap()
            );
            assert!(!manifest.id().unwrap().is_zero());
        }
    }

    #[test]
    fn sepolia_accounting_reaches_documented_conjectured_target() {
        let manifest = ParameterManifest::profile("sepolia-v0.3");
        let analysis = analyze_profile("sepolia-v0.3");
        assert_eq!(analysis.conjectured_bits, 107);
        assert_eq!(analysis.proven_unique_decoding_bits, 37);
        assert_eq!(analysis.proven_list_decoding_bits, 56);
        assert_eq!(analysis.proven_bits, 56);
        assert_eq!(NUM_WITHDRAWAL_COLS, 190);
        assert_eq!(analysis.batched_functions, 210);
        assert_eq!(analysis.air_constraints, 1_186);
        assert_eq!(analysis.air_max_constraint_degree, 7);
        assert_eq!(manifest.target_quantum_bits(), 107);
        assert_eq!(manifest.conservative_quantum_bits(), 56);
    }

    #[test]
    fn sepolia_manifest_pins_v3_q32_hiding_profile() {
        let manifest = ParameterManifest::profile("sepolia-v0.3");
        assert_eq!(MANIFEST_MAGIC, *b"PQTCPRM3");
        assert_eq!(MANIFEST_VERSION, 3);
        assert_eq!(manifest.air_version, 3);
        assert_eq!(manifest.protocol_version, 3);
        assert_eq!(manifest.proof_codec_version, 3);
        assert_eq!(manifest.verifier_interface_version, 3);
        assert_eq!(manifest.fri_log_blowup, 4);
        assert_eq!(manifest.fri_query_count, 32);
        assert_eq!(manifest.commit_grinding_bits, 16);
        assert_eq!(manifest.query_grinding_bits, 16);
        assert_eq!(manifest.random_codeword_count, 4);
        assert_eq!(manifest.mmcs_salt_elements, 8);
        assert_eq!(manifest.validate(), Ok(()));
    }

    #[test]
    fn sepolia_manifest_rejects_sub_hundred_bit_actual_parameters() {
        let mut manifest = ParameterManifest::profile("sepolia-v0.3");
        manifest.fri_query_count = 1;
        assert!(analyze_manifest(&manifest).conjectured_bits < 100);
        assert_eq!(manifest.validate(), Err(ManifestError::Security));
    }

    #[test]
    fn manifest_rejects_non_v3_protocol_and_codec_versions() {
        let mut manifest = ParameterManifest::profile("dev");
        manifest.protocol_version = 2;
        assert_eq!(manifest.validate(), Err(ManifestError::Protocol));

        let mut manifest = ParameterManifest::profile("dev");
        manifest.air_version = 2;
        assert_eq!(manifest.validate(), Err(ManifestError::Protocol));

        let mut manifest = ParameterManifest::profile("dev");
        manifest.proof_codec_version = 2;
        assert_eq!(manifest.validate(), Err(ManifestError::Protocol));

        let mut manifest = ParameterManifest::profile("dev");
        manifest.verifier_interface_version = 2;
        assert_eq!(manifest.validate(), Err(ManifestError::Protocol));
    }
}
