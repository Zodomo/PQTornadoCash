//! Canonical two-transaction calldata codec for Poseidon withdrawal proofs.
//! Fixed dimensions are implicit; query authentication paths stay pruned and
//! are independently deduplicated for each transaction's query half.

use std::collections::BTreeSet;

use p3_challenger::{CanObserve, CanSampleBits, FieldChallenger, GrindingChallenger};
use p3_commit::OpenedValues as PcsOpenedValues;
use p3_field::{BasedVectorSpace, PrimeCharacteristicRing, PrimeField32};
use p3_fri::FriProof;
use p3_symmetric::MerkleCap;
use p3_uni_stark::{Commitments, OpenedValues, Proof};
use pqtc_hash::k512;
fn binding(bytes: &[u8]) -> [u8; 64] { k512(0x47, bytes).to_bytes() }
use pqtc_poseidon_air::{NUM_WITHDRAWAL_COLS, TRACE_HEIGHT};
use pqtc_spec::{BABY_BEAR_MODULUS, Digest512, PUBLIC_VALUES_COUNT, WithdrawalStatement};
use thiserror::Error;

use crate::crypto::Transcript512;
use crate::query::{HalfFriRound, HalfInput, QueryHalf, merge_queries, split_queries};
use crate::{Challenge, Config, SecurityProfile, StarkProof, Val};

pub const PROOF_PART_VERSION: u16 = 4;
pub const PROOF_PART_A_MAGIC: [u8; 8] = *b"PQTCPA04";
pub const PROOF_PART_B_MAGIC: [u8; 8] = *b"PQTCPB04";
const PART_A_END: u32 = 0x5041_4534;
const PART_B_END: u32 = 0x5042_4534;
const STATEMENT_DOMAIN: &[u8] = b"PQTC.R2.V4.STATEMENT";
const CHECKPOINT_DOMAIN: &[u8] = b"PQTC.R2.V4.CHECKPOINT";
const PROOF_ID_DOMAIN: &[u8] = b"PQTC.R2.V4.PROOF";
const QUOTIENT_CHUNKS: usize = 16;
const EXTENSION_DEGREE: usize = 4;
const MMCS_SALT_ELEMENTS: usize = 8;
const FRI_ROUNDS: usize = 9;
const FIELD_BYTES: usize = 4;
const CHALLENGE_BYTES: usize = EXTENSION_DEGREE * FIELD_BYTES;
const COMMITMENT_BYTES: usize = 8 * 8;
const DIGEST_BYTES: usize = 64;
const MAX_PATH_HASHES: usize = 4_096;

pub const COMMON_HEADER_BYTES: usize =
    8 + 2 + 4 + 2 + 2 + DIGEST_BYTES + 2 + PUBLIC_VALUES_COUNT * FIELD_BYTES;
const fn global_data_bytes(random_codewords: usize) -> usize {
    3 * COMMITMENT_BYTES
        + (2 * NUM_WITHDRAWAL_COLS + QUOTIENT_CHUNKS * EXTENSION_DEGREE + EXTENSION_DEGREE)
            * CHALLENGE_BYTES
        + (1 + 2 + QUOTIENT_CHUNKS) * random_codewords * CHALLENGE_BYTES
        + FRI_ROUNDS * COMMITMENT_BYTES
        + FRI_ROUNDS * FIELD_BYTES
        + CHALLENGE_BYTES
        + FIELD_BYTES
}
pub const GLOBAL_DATA_BYTES: usize = global_data_bytes(4);
const _: () = assert!(COMMON_HEADER_BYTES == 340);
pub const PRODUCTION_QUERY_COUNT: usize = crate::QUERY_COUNT;
pub const PRODUCTION_HALF_QUERY_COUNT: usize = PRODUCTION_QUERY_COUNT / 2;
const _: () = assert!(SecurityProfile::SepoliaV03.fri().2 == PRODUCTION_QUERY_COUNT);
const _: () = assert!(TRACE_HEIGHT == 256);
const _: () = assert!(GLOBAL_DATA_BYTES == 9_208);

type Digest = [u64; 8];
type Commitment = MerkleCap<Val, Digest>;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ProofShape {
    pub query_count: usize,
    pub first_queries: usize,
    pub log_blowup: usize,
    pub random_codewords: usize,
}
impl ProofShape {
    #[must_use]
    pub fn for_profile(profile: SecurityProfile) -> Self {
        let (log_blowup, _, query_count, _, _) = profile.fri();
        Self {
            query_count,
            first_queries: query_count / 2,
            log_blowup,
            random_codewords: profile.random_codewords(),
        }
    }
    #[must_use]
    pub const fn degree_bits(self) -> usize {
        TRACE_HEIGHT.ilog2() as usize + 1
    }
    pub const fn fri_rounds(self) -> usize {
        FRI_ROUNDS
    }
    pub(crate) const fn input_matrix_width(self, batch: usize) -> usize {
        match batch {
            0 => EXTENSION_DEGREE + self.random_codewords,
            1 => NUM_WITHDRAWAL_COLS + self.random_codewords,
            2 => EXTENSION_DEGREE + self.random_codewords,
            _ => 0,
        }
    }
    pub(crate) const fn input_matrix_count(self, batch: usize) -> usize {
        match batch {
            0 | 1 => 1,
            2 => QUOTIENT_CHUNKS,
            _ => 0,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TranscriptCheckpoint {
    pub digest: [u8; 64],
    pub global_digest: [u8; 64],
    pub state: Digest512,
    pub air_alpha: Challenge,
    pub zeta: Challenge,
    pub fri_alpha: Challenge,
    pub fri_betas: Vec<Challenge>,
    pub query_indices: Vec<u32>,
    pub unique_query_indices: Vec<u32>,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProofPartA {
    pub bytes: Vec<u8>,
    pub proof_id: [u8; 64],
    pub statement_key: [u8; 64],
    pub checkpoint: TranscriptCheckpoint,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProofPartB {
    pub bytes: Vec<u8>,
    pub proof_id: [u8; 64],
    pub checkpoint_digest: [u8; 64],
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EncodedProofParts {
    pub part_a: ProofPartA,
    pub part_b: ProofPartB,
}

#[must_use]
pub fn statement_key(parameter_id: Digest512, statement: WithdrawalStatement) -> [u8; 64] {
    let mut abi = Vec::with_capacity((3 + PUBLIC_VALUES_COUNT) * 32);
    put_abi_word(&mut abi, STATEMENT_DOMAIN);
    abi.extend_from_slice(&parameter_id.left);
    abi.extend_from_slice(&parameter_id.right);
    for value in statement.public_values() {
        abi.extend_from_slice(&[0; 28]);
        put_u32(&mut abi, value);
    }
    binding(&abi)
}

pub fn encode_proof_parts(
    proof: &StarkProof,
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
    first_queries: usize,
) -> Result<EncodedProofParts, StarkCodecError> {
    let part_a = encode_proof_part_a(proof, profile, parameter_id, statement, first_queries)?;
    let part_b = encode_proof_part_b(proof, profile, parameter_id, statement, &part_a, first_queries)?;
    Ok(EncodedProofParts { part_a, part_b })
}
pub fn encode_proof_part_a(
    proof: &StarkProof,
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
    first_queries: usize,
) -> Result<ProofPartA, StarkCodecError> {
    ensure_canonical_statement(statement)?;
    let mut shape = ProofShape::for_profile(profile);
    if !crate::QUERY_SPLITS.contains(&first_queries) || shape.query_count != crate::QUERY_COUNT { return Err(StarkCodecError::Shape("split")); }
    shape.first_queries = first_queries;
    validate_shape(proof, shape)?;
    let global = encode_global(proof, shape)?;
    let global_digest = binding(&global);
    let checkpoint = derive_checkpoint(proof, profile, parameter_id, statement, global_digest)?;
    let halves = split_queries(proof, shape, &checkpoint)?;
    let mut out = Vec::new();
    put_header(
        &mut out,
        PROOF_PART_A_MAGIC,
        profile,
        shape,
        parameter_id,
        statement,
    )?;
    out.extend_from_slice(&global_digest);
    out.extend_from_slice(&global);
    put_checkpoint(&mut out, &checkpoint)?;
    put_half(&mut out, &halves[0])?;
    put_u32(&mut out, PART_A_END);
    let key = statement_key(parameter_id, statement);
    let proof_id = derive_proof_id(key, &out);
    Ok(ProofPartA {
        bytes: out,
        proof_id,
        statement_key: key,
        checkpoint,
    })
}
pub fn encode_proof_part_b(
    proof: &StarkProof,
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
    part_a: &ProofPartA,
    first_queries: usize,
) -> Result<ProofPartB, StarkCodecError> {
    ensure_canonical_statement(statement)?;
    let mut shape = ProofShape::for_profile(profile);
    if !crate::QUERY_SPLITS.contains(&first_queries) || shape.query_count != crate::QUERY_COUNT { return Err(StarkCodecError::Shape("split")); }
    shape.first_queries = first_queries;
    validate_shape(proof, shape)?;
    let key = statement_key(parameter_id, statement);
    if part_a.statement_key != key || part_a.proof_id != derive_proof_id(key, &part_a.bytes) {
        return Err(StarkCodecError::CrossPartBinding);
    }
    let global = encode_global(proof, shape)?;
    let global_digest = binding(&global);
    let checkpoint = derive_checkpoint(proof, profile, parameter_id, statement, global_digest)?;
    if checkpoint != part_a.checkpoint {
        return Err(StarkCodecError::CrossPartBinding);
    }
    let halves = split_queries(proof, shape, &checkpoint)?;
    let mut out = Vec::new();
    put_header(
        &mut out,
        PROOF_PART_B_MAGIC,
        profile,
        shape,
        parameter_id,
        statement,
    )?;
    out.extend_from_slice(&part_a.proof_id);
    out.extend_from_slice(&global_digest);
    out.extend_from_slice(&global);
    put_checkpoint(&mut out, &checkpoint)?;
    put_half(&mut out, &halves[1])?;
    put_u32(&mut out, PART_B_END);
    Ok(ProofPartB {
        bytes: out,
        proof_id: part_a.proof_id,
        checkpoint_digest: checkpoint.digest,
    })
}

pub fn decode_proof_parts(
    part_a: &[u8],
    part_b: &[u8],
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
    first_queries: usize,
) -> Result<StarkProof, StarkCodecError> {
    let mut shape = ProofShape::for_profile(profile);
    if !crate::QUERY_SPLITS.contains(&first_queries) || shape.query_count != crate::QUERY_COUNT { return Err(StarkCodecError::Shape("split")); }
    shape.first_queries = first_queries;
    let mut a = Reader::new(part_a);
    a.header(PROOF_PART_A_MAGIC, profile, shape, parameter_id, statement)?;
    let a_digest = a.take::<64>()?;
    let (global_a, raw_a) = a.global(shape, profile)?;
    if binding(raw_a) != a_digest {
        return Err(StarkCodecError::GlobalDigest);
    }
    let cp_a = a.checkpoint(shape)?;
    validate_checkpoint_digest(&cp_a, parameter_id, statement)?;
    if cp_a.global_digest != a_digest {
        return Err(StarkCodecError::GlobalDigest);
    }
    let half_a = a.half(shape, 0)?;
    if a.u32()? != PART_A_END {
        return Err(StarkCodecError::EndMarker);
    }
    a.finish()?;
    let proof_id = derive_proof_id(statement_key(parameter_id, statement), part_a);

    let mut b = Reader::new(part_b);
    b.header(PROOF_PART_B_MAGIC, profile, shape, parameter_id, statement)?;
    if b.take::<64>()? != proof_id {
        return Err(StarkCodecError::CrossPartBinding);
    }
    let b_digest = b.take::<64>()?;
    let (_global_b, raw_b) = b.global(shape, profile)?;
    if b_digest != a_digest || raw_b != raw_a || binding(raw_b) != b_digest {
        return Err(StarkCodecError::GlobalDigest);
    }
    let cp_b = b.checkpoint(shape)?;
    if cp_b != cp_a {
        return Err(StarkCodecError::CrossPartBinding);
    }
    let half_b = b.half(shape, shape.first_queries)?;
    if b.u32()? != PART_B_END {
        return Err(StarkCodecError::EndMarker);
    }
    b.finish()?;
    let mut proof = global_a.into_proof(shape);
    merge_queries(&mut proof, shape, &cp_a, [half_a, half_b])?;
    validate_shape(&proof, shape)?;
    if derive_checkpoint(&proof, profile, parameter_id, statement, a_digest)? != cp_a {
        return Err(StarkCodecError::TranscriptCheckpoint);
    }
    Ok(proof)
}

struct GlobalData {
    commitments: Commitments<Commitment>,
    opened: OpenedValues<Challenge>,
    hiding: PcsOpenedValues<Challenge>,
    commits: Vec<Commitment>,
    pow: Vec<Val>,
    final_poly: Vec<Challenge>,
    query_pow: Val,
}
impl GlobalData {
    fn into_proof(self, shape: ProofShape) -> StarkProof {
        Proof::<Config> {
            commitments: self.commitments,
            opened_values: self.opened,
            opening_proof: (
                self.hiding,
                FriProof {
                    commit_phase_commits: self.commits,
                    commit_pow_witnesses: self.pow,
                    input_openings: Vec::new(),
                    commit_phase_openings: Vec::new(),
                    final_poly: self.final_poly,
                    query_pow_witness: self.query_pow,
                },
            ),
            degree_bits: shape.degree_bits(),
        }
    }
}
fn encode_global(proof: &StarkProof, shape: ProofShape) -> Result<Vec<u8>, StarkCodecError> {
    let expected_len = global_data_bytes(shape.random_codewords);
    let mut out = Vec::with_capacity(expected_len);
    put_cap(&mut out, &proof.commitments.trace)?;
    put_cap(&mut out, &proof.commitments.quotient_chunks)?;
    put_cap(
        &mut out,
        proof
            .commitments
            .random
            .as_ref()
            .ok_or(StarkCodecError::Shape("random commitment"))?,
    )?;
    put_exts(&mut out, &proof.opened_values.trace_local);
    put_exts(
        &mut out,
        proof
            .opened_values
            .trace_next
            .as_ref()
            .ok_or(StarkCodecError::Shape("trace next"))?,
    );
    for chunk in &proof.opened_values.quotient_chunks {
        put_exts(&mut out, chunk);
    }
    put_exts(
        &mut out,
        proof
            .opened_values
            .random
            .as_ref()
            .ok_or(StarkCodecError::Shape("random opening"))?,
    );
    for round in &proof.opening_proof.0 {
        for matrix in round {
            for point in matrix {
                put_exts(&mut out, point);
            }
        }
    }
    for cap in &proof.opening_proof.1.commit_phase_commits {
        put_cap(&mut out, cap)?;
    }
    for &w in &proof.opening_proof.1.commit_pow_witnesses {
        put_val(&mut out, w);
    }
    put_exts(&mut out, &proof.opening_proof.1.final_poly);
    put_val(&mut out, proof.opening_proof.1.query_pow_witness);
    if out.len() != expected_len {
        return Err(StarkCodecError::Shape("global data bytes"));
    }
    Ok(out)
}

pub fn derive_checkpoint(
    proof: &StarkProof,
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
    global_digest: [u8; 64],
) -> Result<TranscriptCheckpoint, StarkCodecError> {
    Ok(replay_checkpoint(proof, profile, parameter_id, statement, global_digest)?.0)
}

pub fn replay_checkpoint(
    proof: &StarkProof,
    profile: SecurityProfile,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
    global_digest: [u8; 64],
) -> Result<(TranscriptCheckpoint, Vec<crate::crypto::Event>), StarkCodecError> {
    let shape = ProofShape::for_profile(profile);
    let pv = crate::withdrawal_public_values(statement);
    let mut t = Transcript512::new(parameter_id, &pv);
    t.record();
    t.observe(Val::from_usize(proof.degree_bits));
    t.observe(Val::from_usize(proof.degree_bits - 1));
    t.observe(Val::ZERO);
    t.observe(proof.commitments.trace.clone());
    t.observe_slice(&pv);
    let air_alpha = t.sample_algebra_element();
    t.observe(proof.commitments.quotient_chunks.clone());
    t.observe(
        proof
            .commitments
            .random
            .clone()
            .ok_or(StarkCodecError::Shape("random commitment"))?,
    );
    let zeta = t.sample_algebra_element();
    let h = &proof.opening_proof.0;
    t.observe_algebra_slice(&joined(
        proof
            .opened_values
            .random
            .as_ref()
            .ok_or(StarkCodecError::Shape("random opening"))?,
        &h[0][0][0],
    ));
    t.observe_algebra_slice(&joined(&proof.opened_values.trace_local, &h[1][0][0]));
    t.observe_algebra_slice(&joined(
        proof
            .opened_values
            .trace_next
            .as_ref()
            .ok_or(StarkCodecError::Shape("trace next"))?,
        &h[1][0][1],
    ));
    for (i, chunk) in proof.opened_values.quotient_chunks.iter().enumerate() {
        t.observe_algebra_slice(&joined(chunk, &h[2][i][0]));
    }
    let fri_alpha = t.sample_algebra_element();
    let (_, _, q, commit_pow, query_pow) = profile.fri();
    let mut fri_betas = Vec::with_capacity(shape.fri_rounds());
    for (cap, &w) in proof
        .opening_proof
        .1
        .commit_phase_commits
        .iter()
        .zip(&proof.opening_proof.1.commit_pow_witnesses)
    {
        t.observe(cap.clone());
        if !t.check_witness(commit_pow, w) {
            return Err(StarkCodecError::InvalidCommitPow);
        }
        fri_betas.push(t.sample_algebra_element());
    }
    t.observe_algebra_slice(&proof.opening_proof.1.final_poly);
    for _ in 0..shape.fri_rounds() {
        t.observe(Val::ONE);
    }
    if !t.check_witness(query_pow, proof.opening_proof.1.query_pow_witness) {
        return Err(StarkCodecError::InvalidQueryPow);
    }
    let state = t.state();
    let bits = proof.degree_bits + shape.log_blowup;
    let query_indices = (0..q)
        .map(|_| t.sample_bits(bits) as u32)
        .collect::<Vec<_>>();
    let unique_query_indices = sorted_unique(&query_indices);
    let mut cp = TranscriptCheckpoint {
        digest: [0; 64],
        global_digest,
        state,
        air_alpha,
        zeta,
        fri_alpha,
        fri_betas,
        query_indices,
        unique_query_indices,
    };
    cp.digest = checkpoint_digest(statement_key(parameter_id, statement), &cp)?;
    assert!(t.finished());
    Ok((cp, t.events))
}
fn joined(a: &[Challenge], b: &[Challenge]) -> Vec<Challenge> {
    a.iter().chain(b).copied().collect()
}
fn sorted_unique(v: &[u32]) -> Vec<u32> {
    v.iter()
        .copied()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}
fn checkpoint_digest(
    key: [u8; 64],
    cp: &TranscriptCheckpoint,
) -> Result<[u8; 64], StarkCodecError> {
    let mut payload = Vec::new();
    put_checkpoint_payload(&mut payload, cp)?;
    let mut abi = Vec::with_capacity(96);
    put_abi_word(&mut abi, CHECKPOINT_DOMAIN);
    abi.extend_from_slice(&key);
    abi.extend_from_slice(&binding(&payload));
    Ok(binding(&abi))
}
fn validate_checkpoint_digest(
    cp: &TranscriptCheckpoint,
    parameter_id: Digest512,
    statement: WithdrawalStatement,
) -> Result<(), StarkCodecError> {
    if checkpoint_digest(statement_key(parameter_id, statement), cp)? == cp.digest {
        Ok(())
    } else {
        Err(StarkCodecError::TranscriptCheckpoint)
    }
}
fn derive_proof_id(key: [u8; 64], part_a: &[u8]) -> [u8; 64] {
    let mut abi = Vec::with_capacity(96);
    put_abi_word(&mut abi, PROOF_ID_DOMAIN);
    abi.extend_from_slice(&key);
    abi.extend_from_slice(&binding(part_a));
    binding(&abi)
}
fn ensure_canonical_statement(statement: WithdrawalStatement) -> Result<(), StarkCodecError> {
    if let Some(value) = statement
        .public_values()
        .into_iter()
        .find(|&value| value >= BABY_BEAR_MODULUS)
    {
        Err(StarkCodecError::NonCanonicalField { value })
    } else {
        Ok(())
    }
}

fn validate_shape(proof: &StarkProof, s: ProofShape) -> Result<(), StarkCodecError> {
    if proof.degree_bits != s.degree_bits() {
        return Err(StarkCodecError::Shape("degree bits"));
    }
    for cap in [
        &proof.commitments.trace,
        &proof.commitments.quotient_chunks,
        proof
            .commitments
            .random
            .as_ref()
            .ok_or(StarkCodecError::Shape("random commitment"))?,
    ] {
        if cap.num_roots() != 1 {
            return Err(StarkCodecError::Shape("cap"));
        }
    }
    if proof.opened_values.trace_local.len() != NUM_WITHDRAWAL_COLS
        || proof.opened_values.trace_next.as_ref().map(Vec::len) != Some(NUM_WITHDRAWAL_COLS)
        || proof.opened_values.quotient_chunks.len() != QUOTIENT_CHUNKS
        || proof
            .opened_values
            .quotient_chunks
            .iter()
            .any(|x| x.len() != 4)
        || proof.opened_values.random.as_ref().map(Vec::len) != Some(4)
        || proof.opened_values.preprocessed_local.is_some()
        || proof.opened_values.preprocessed_next.is_some()
    {
        return Err(StarkCodecError::Shape("OOD"));
    }
    let h = &proof.opening_proof.0;
    let points = [vec![1], vec![2], vec![1; 16]];
    if h.len() != 3 {
        return Err(StarkCodecError::Shape("hiding"));
    }
    for (r, expected) in h.iter().zip(points) {
        if r.len() != expected.len() {
            return Err(StarkCodecError::Shape("hiding"));
        }
        for (m, n) in r.iter().zip(expected) {
            if m.len() != n || m.iter().any(|p| p.len() != s.random_codewords) {
                return Err(StarkCodecError::Shape("hiding"));
            }
        }
    }
    let fri = &proof.opening_proof.1;
    if fri.commit_phase_commits.len() != s.fri_rounds()
        || fri.commit_pow_witnesses.len() != s.fri_rounds()
        || fri.commit_phase_openings.len() != s.fri_rounds()
        || fri.input_openings.len() != 3
        || fri.final_poly.len() != 1
    {
        return Err(StarkCodecError::Shape("FRI"));
    }
    for (batch, input) in fri.input_openings.iter().enumerate() {
        let m = s.input_matrix_count(batch);
        let w = s.input_matrix_width(batch);
        if input.opened_values.len() != s.query_count
            || input.opening_proof.0.len() != s.query_count
            || input
                .opened_values
                .iter()
                .any(|q| q.len() != m || q.iter().any(|r| r.len() != w))
            || input
                .opening_proof
                .0
                .iter()
                .any(|q| q.len() != m || q.iter().any(|x| x.len() != 8))
            || input.opening_proof.1.sibling_hashes.len() > MAX_PATH_HASHES
        {
            return Err(StarkCodecError::Shape("input multiproof"));
        }
    }
    for round in &fri.commit_phase_openings {
        if round.log_arity != 1
            || round.sibling_values.len() != s.query_count
            || round.sibling_values.iter().any(|x| x.len() != 1)
            || round.opening_proof.0.len() != s.query_count
            || round
                .opening_proof
                .0
                .iter()
                .any(|q| q.len() != 1 || q[0].len() != 8)
            || round.opening_proof.1.sibling_hashes.len() > MAX_PATH_HASHES
        {
            return Err(StarkCodecError::Shape("FRI multiproof"));
        }
    }
    Ok(())
}

fn put_header(
    out: &mut Vec<u8>,
    magic: [u8; 8],
    profile: SecurityProfile,
    s: ProofShape,
    parameter: Digest512,
    statement: WithdrawalStatement,
) -> Result<(), StarkCodecError> {
    out.extend_from_slice(&magic);
    put_u16(out, PROOF_PART_VERSION);
    out.push(profile_tag(profile));
    out.push(s.degree_bits() as u8);
    out.push(s.fri_rounds() as u8);
    out.push(s.random_codewords as u8);
    put_u16(out, s.query_count as u16);
    put_u16(out, s.first_queries as u16);
    out.extend_from_slice(&parameter.to_bytes());
    put_u16(out, PUBLIC_VALUES_COUNT as u16);
    for v in statement.public_values() {
        if v >= BABY_BEAR_MODULUS {
            return Err(StarkCodecError::NonCanonicalField { value: v });
        }
        put_u32(out, v);
    }
    Ok(())
}
const fn profile_tag(p: SecurityProfile) -> u8 {
    match p {
        SecurityProfile::Dev => 0,
        SecurityProfile::Ci => 1,
        SecurityProfile::SepoliaV03 => 3,
    }
}
fn put_abi_word(out: &mut Vec<u8>, v: &[u8]) {
    out.extend_from_slice(v);
    out.resize(out.len() + 32 - v.len(), 0);
}
fn put_u16(out: &mut Vec<u8>, v: u16) {
    out.extend_from_slice(&v.to_be_bytes());
}
fn put_u32(out: &mut Vec<u8>, v: u32) {
    out.extend_from_slice(&v.to_be_bytes());
}
fn put_val(out: &mut Vec<u8>, v: Val) {
    put_u32(out, v.as_canonical_u32());
}
fn put_ext(out: &mut Vec<u8>, v: Challenge) {
    for &x in v.as_basis_coefficients_slice() {
        put_val(out, x);
    }
}
fn put_exts(out: &mut Vec<u8>, v: &[Challenge]) {
    for &x in v {
        put_ext(out, x);
    }
}
fn put_digest(out: &mut Vec<u8>, d: Digest) {
    for w in d {
        out.extend_from_slice(&w.to_be_bytes());
    }
}
fn put_cap(out: &mut Vec<u8>, c: &Commitment) -> Result<(), StarkCodecError> {
    if c.num_roots() != 1 {
        return Err(StarkCodecError::Shape("cap"));
    }
    put_digest(out, c.roots()[0]);
    Ok(())
}
fn put_checkpoint(out: &mut Vec<u8>, cp: &TranscriptCheckpoint) -> Result<(), StarkCodecError> {
    out.extend_from_slice(&cp.digest);
    put_checkpoint_payload(out, cp)
}
fn put_checkpoint_payload(
    out: &mut Vec<u8>,
    cp: &TranscriptCheckpoint,
) -> Result<(), StarkCodecError> {
    out.extend_from_slice(&cp.global_digest);
    out.extend_from_slice(&cp.state.to_bytes());
    put_ext(out, cp.air_alpha);
    put_ext(out, cp.zeta);
    put_ext(out, cp.fri_alpha);
    for &x in &cp.fri_betas {
        put_ext(out, x);
    }
    put_u16(out, cp.query_indices.len() as u16);
    for &x in &cp.query_indices {
        put_u32(out, x);
    }
    put_u16(out, cp.unique_query_indices.len() as u16);
    for &x in &cp.unique_query_indices {
        put_u32(out, x);
    }
    Ok(())
}
fn put_half(out: &mut Vec<u8>, h: &QueryHalf) -> Result<(), StarkCodecError> {
    put_u16(out, h.start as u16);
    put_u16(out, h.indices.len() as u16);
    for &i in &h.indices {
        put_u32(out, i);
    }
    for input in &h.inputs {
        put_rows(out, &input.opened_values);
        put_rows(out, &input.salts);
        put_hashes(out, &input.sibling_hashes)?;
    }
    for round in &h.fri_rounds {
        for q in &round.sibling_values {
            put_exts(out, q);
        }
        put_rows(out, &round.salts);
        put_hashes(out, &round.sibling_hashes)?;
    }
    Ok(())
}
fn put_rows(out: &mut Vec<u8>, qs: &[Vec<Vec<Val>>]) {
    for q in qs {
        for row in q {
            for &x in row {
                put_val(out, x);
            }
        }
    }
}
fn put_hashes(out: &mut Vec<u8>, hs: &[[u64; 8]]) -> Result<(), StarkCodecError> {
    put_u32(
        out,
        u32::try_from(hs.len()).map_err(|_| StarkCodecError::Length)?,
    );
    for &h in hs {
        put_digest(out, h);
    }
    Ok(())
}

struct Reader<'a> {
    bytes: &'a [u8],
    cursor: usize,
}
impl<'a> Reader<'a> {
    const fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, cursor: 0 }
    }
    fn take<const N: usize>(&mut self) -> Result<[u8; N], StarkCodecError> {
        let end = self
            .cursor
            .checked_add(N)
            .ok_or(StarkCodecError::Truncated)?;
        let v = self
            .bytes
            .get(self.cursor..end)
            .ok_or(StarkCodecError::Truncated)?;
        self.cursor = end;
        Ok(v.try_into().expect("length"))
    }
    fn u8(&mut self) -> Result<u8, StarkCodecError> {
        Ok(self.take::<1>()?[0])
    }
    fn u16(&mut self) -> Result<u16, StarkCodecError> {
        Ok(u16::from_be_bytes(self.take()?))
    }
    fn u32(&mut self) -> Result<u32, StarkCodecError> {
        Ok(u32::from_be_bytes(self.take()?))
    }
    fn val(&mut self) -> Result<Val, StarkCodecError> {
        let v = self.u32()?;
        if v >= BABY_BEAR_MODULUS {
            Err(StarkCodecError::NonCanonicalField { value: v })
        } else {
            Ok(Val::from_u32(v))
        }
    }
    fn ext(&mut self) -> Result<Challenge, StarkCodecError> {
        let c = [self.val()?, self.val()?, self.val()?, self.val()?];
        Ok(Challenge::from_basis_coefficients_fn(|i| c[i]))
    }
    fn exts(&mut self, n: usize) -> Result<Vec<Challenge>, StarkCodecError> {
        (0..n).map(|_| self.ext()).collect()
    }
    fn digest(&mut self) -> Result<Digest, StarkCodecError> {
        let mut d = [0; 8];
        for w in &mut d {
            *w = u64::from_be_bytes(self.take()?);
        }
        Ok(d)
    }
    fn cap(&mut self) -> Result<Commitment, StarkCodecError> {
        Ok(MerkleCap::new(vec![self.digest()?]))
    }
    fn header(
        &mut self,
        magic: [u8; 8],
        profile: SecurityProfile,
        s: ProofShape,
        parameter: Digest512,
        statement: WithdrawalStatement,
    ) -> Result<(), StarkCodecError> {
        if self.take::<8>()? != magic {
            return Err(StarkCodecError::Magic);
        }
        if self.u16()? != PROOF_PART_VERSION {
            return Err(StarkCodecError::Version);
        }
        if self.u8()? != profile_tag(profile) {
            return Err(StarkCodecError::Profile);
        }
        if self.u8()? as usize != s.degree_bits()
            || self.u8()? as usize != s.fri_rounds()
            || self.u8()? as usize != s.random_codewords
            || self.u16()? as usize != s.query_count
            || self.u16()? as usize != s.first_queries
        {
            return Err(StarkCodecError::Shape("header"));
        }
        if Digest512::from_bytes(self.take()?) != parameter {
            return Err(StarkCodecError::ParameterId);
        }
        if self.u16()? as usize != PUBLIC_VALUES_COUNT {
            return Err(StarkCodecError::PublicValues);
        }
        let mut pv = [0; PUBLIC_VALUES_COUNT];
        for x in &mut pv {
            *x = self.u32()?;
            if *x >= BABY_BEAR_MODULUS {
                return Err(StarkCodecError::NonCanonicalField { value: *x });
            }
        }
        if pv != statement.public_values() {
            return Err(StarkCodecError::PublicValues);
        }
        Ok(())
    }
    fn global(
        &mut self,
        s: ProofShape,
        profile: SecurityProfile,
    ) -> Result<(GlobalData, &'a [u8]), StarkCodecError> {
        let start = self.cursor;
        let commitments = Commitments {
            trace: self.cap()?,
            quotient_chunks: self.cap()?,
            random: Some(self.cap()?),
        };
        let opened = OpenedValues {
            trace_local: self.exts(NUM_WITHDRAWAL_COLS)?,
            trace_next: Some(self.exts(NUM_WITHDRAWAL_COLS)?),
            preprocessed_local: None,
            preprocessed_next: None,
            quotient_chunks: (0..16).map(|_| self.exts(4)).collect::<Result<_, _>>()?,
            random: Some(self.exts(4)?),
        };
        let points = [vec![1], vec![2], vec![1; 16]];
        let mut hiding = Vec::new();
        for ps in points {
            let mut r = Vec::new();
            for n in ps {
                let mut m = Vec::new();
                for _ in 0..n {
                    m.push(self.exts(s.random_codewords)?);
                }
                r.push(m);
            }
            hiding.push(r);
        }
        let commits = (0..s.fri_rounds())
            .map(|_| self.cap())
            .collect::<Result<_, _>>()?;
        let pow = (0..s.fri_rounds())
            .map(|_| self.val())
            .collect::<Result<_, _>>()?;
        let final_poly = self.exts(1 << profile.fri().1)?;
        let query_pow = self.val()?;
        if self.cursor - start != global_data_bytes(s.random_codewords) {
            return Err(StarkCodecError::Shape("global data bytes"));
        }
        Ok((
            GlobalData {
                commitments,
                opened,
                hiding,
                commits,
                pow,
                final_poly,
                query_pow,
            },
            &self.bytes[start..self.cursor],
        ))
    }
    fn checkpoint(&mut self, s: ProofShape) -> Result<TranscriptCheckpoint, StarkCodecError> {
        let digest = self.take()?;
        let global_digest = self.take()?;
        let state = Digest512::from_bytes(self.take()?);
        let air_alpha = self.ext()?;
        let zeta = self.ext()?;
        let fri_alpha = self.ext()?;
        let fri_betas = self.exts(s.fri_rounds())?;
        if self.u16()? as usize != s.query_count {
            return Err(StarkCodecError::QueryOrder);
        }
        let query_indices = (0..s.query_count)
            .map(|_| self.u32())
            .collect::<Result<Vec<_>, _>>()?;
        let n = self.u16()? as usize;
        if n > s.query_count {
            return Err(StarkCodecError::QueryOrder);
        }
        let unique_query_indices = (0..n).map(|_| self.u32()).collect::<Result<Vec<_>, _>>()?;
        if unique_query_indices != sorted_unique(&query_indices) {
            return Err(StarkCodecError::QueryOrder);
        }
        Ok(TranscriptCheckpoint {
            digest,
            global_digest,
            state,
            air_alpha,
            zeta,
            fri_alpha,
            fri_betas,
            query_indices,
            unique_query_indices,
        })
    }
    fn rows(
        &mut self,
        q: usize,
        m: usize,
        w: usize,
    ) -> Result<Vec<Vec<Vec<Val>>>, StarkCodecError> {
        (0..q)
            .map(|_| {
                (0..m)
                    .map(|_| (0..w).map(|_| self.val()).collect())
                    .collect()
            })
            .collect()
    }
    fn hashes(&mut self) -> Result<Vec<[u64; 8]>, StarkCodecError> {
        let n = self.u32()? as usize;
        if n > MAX_PATH_HASHES {
            return Err(StarkCodecError::Length);
        }
        (0..n).map(|_| self.digest()).collect()
    }
    fn half(&mut self, s: ProofShape, expected_start: usize) -> Result<QueryHalf, StarkCodecError> {
        let start = self.u16()? as usize;
        let q = self.u16()? as usize;
        if start != expected_start || q != if expected_start == 0 { s.first_queries } else { s.query_count - s.first_queries } {
            return Err(StarkCodecError::QueryOrder);
        }
        let indices = (0..q).map(|_| self.u32()).collect::<Result<Vec<_>, _>>()?;
        let mut inputs = Vec::new();
        for batch in 0..3 {
            inputs.push(HalfInput {
                opened_values: self.rows(
                    q,
                    s.input_matrix_count(batch),
                    s.input_matrix_width(batch),
                )?,
                salts: self.rows(q, s.input_matrix_count(batch), MMCS_SALT_ELEMENTS)?,
                sibling_hashes: self.hashes()?,
            });
        }
        let mut fri_rounds = Vec::new();
        for _ in 0..s.fri_rounds() {
            let sibling_values = (0..q).map(|_| self.exts(1)).collect::<Result<_, _>>()?;
            fri_rounds.push(HalfFriRound {
                sibling_values,
                salts: self.rows(q, 1, 8)?,
                sibling_hashes: self.hashes()?,
            });
        }
        Ok(QueryHalf {
            start,
            indices,
            inputs,
            fri_rounds,
        })
    }
    fn finish(self) -> Result<(), StarkCodecError> {
        if self.cursor == self.bytes.len() {
            Ok(())
        } else {
            Err(StarkCodecError::TrailingBytes)
        }
    }
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum StarkCodecError {
    #[error("proof part is truncated")]
    Truncated,
    #[error("invalid proof part magic")]
    Magic,
    #[error("unsupported proof part version")]
    Version,
    #[error("security profile mismatch")]
    Profile,
    #[error("parameter ID mismatch")]
    ParameterId,
    #[error("public values mismatch")]
    PublicValues,
    #[error("parts are not bound to one proof")]
    CrossPartBinding,
    #[error("global proof data digest mismatch")]
    GlobalDigest,
    #[error("invalid transcript checkpoint")]
    TranscriptCheckpoint,
    #[error("noncanonical query order")]
    QueryOrder,
    #[error("invalid commitment grinding witness")]
    InvalidCommitPow,
    #[error("invalid query grinding witness")]
    InvalidQueryPow,
    #[error("invalid proof shape: {0}")]
    Shape(&'static str),
    #[error("field element {value} is noncanonical")]
    NonCanonicalField { value: u32 },
    #[error("proof component length is out of bounds")]
    Length,
    #[error("invalid part end marker")]
    EndMarker,
    #[error("trailing bytes")]
    TrailingBytes,
}

