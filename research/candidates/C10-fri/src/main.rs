use std::{collections::BTreeSet, fs, path::PathBuf, time::Instant};

use anyhow::{Context, Result, ensure};
use clap::Parser;
use p3_challenger::{CanObserve, CanSampleBits, FieldChallenger, GrindingChallenger};
use p3_field::{BasedVectorSpace, PrimeCharacteristicRing, PrimeField32};
use p3_fri::FriParameters;
use p3_uni_stark::{prove, verify};
use pqtc_hash::keccak256;
use pqtc_poseidon_air::{NUM_WITHDRAWAL_COLS, TRACE_HEIGHT, WithdrawalAir, WithdrawalWitness, check_witness, generate_withdrawal_trace, public_values};
use pqtc_spec::{Digest512, WithdrawalStatement};
use pqtc_stark::{Challenge, ChallengeMmcs, Config, Dft, Pcs, StarkProof, Val, ValMmcs};
use pqtc_stark::crypto::{ProofLeafHasher, ProofNodeCompressor, Transcript512};
use rand::{SeedableRng, rngs::StdRng};
use serde::{Deserialize, Serialize};
use serde_json::json;

const PINNED_PLONKY3: &str = "3152b14a89067c83775a8076cc262ffc48a1fd7c";
const V03_PARAMETER_ID: &str = "35adfcc070249bb0393c2fd45f0bbd48ef03cbfc08070d03335eaf952975e62ab7bc82ead4f8c1f1c39b3372be85195853134dfc9d24f43b97a5e0454ea07779";
const QUOTIENT_CHUNKS: usize = 16;

#[derive(Parser)]
#[command(about = "Research-only complete-hiding FRI parameter prover; never a production profile")]
struct Cli {
    #[arg(long)]
    manifest: PathBuf,
    #[arg(long)]
    input: PathBuf,
    #[arg(long)]
    out: PathBuf,
    #[arg(long, default_value_t = 2)]
    repetitions: usize,
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Manifest {
    model_version: u32,
    profile_id: String,
    plonky3_commit: String,
    logical_trace_height: usize,
    proof_degree_bits: usize,
    hiding_degree_padding_bits: usize,
    is_zk: bool,
    extension_field_bits: usize,
    challenge_field_bits: usize,
    mmcs_construction: String,
    mmcs_binding_bits_classical: usize,
    mmcs_binding_bits_quantum: usize,
    relation_width: usize,
    num_constraints: usize,
    max_constraint_degree: usize,
    max_combo: usize,
    quotient_chunks: usize,
    hiding_random_functions: usize,
    batch_count_derivation: String,
    num_batched_functions: usize,
    fri_log_blowup: usize,
    fri_num_queries: usize,
    fri_log_final_poly_len: usize,
    fri_max_log_arity: usize,
    commit_grinding_bits: usize,
    query_grinding_bits: usize,
    omissions: Vec<String>,
}

#[derive(Serialize)]
struct Repetition {
    repetition: usize,
    proof_identity_keccak256: String,
    research_canonical_raw_bytes: usize,
    prove_ms: f64,
    native_verify_ms: f64,
    process_peak_rss_bytes: u64,
    native_verified: bool,
    degree_bits: usize,
    fri_rounds: usize,
    configured_queries: usize,
    sampled_queries: usize,
    unique_query_indices: usize,
    query_indices: Vec<u32>,
    input_frontier_digests: Vec<usize>,
    fri_frontier_digests: Vec<usize>,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    ensure!(cli.repetitions >= 2, "at least two repetitions are required to demonstrate hiding variability");
    let manifest_bytes = fs::read(&cli.manifest).with_context(|| format!("read {}", cli.manifest.display()))?;
    let manifest: Manifest = serde_json::from_slice(&manifest_bytes).context("parse strict parameter manifest")?;
    validate_manifest(&manifest)?;
    let statement: WithdrawalStatement = read_json(cli.input.join("statement.json"))?;
    let witness: WithdrawalWitness = read_json(cli.input.join("witness.json"))?;
    check_witness(statement, &witness).context("withdrawal witness does not satisfy the frozen relation")?;
    fs::create_dir_all(&cli.out)?;

    let parameter = v03_parameter_id()?;
    let pvs = public_values(statement);
    let mut repetitions = Vec::with_capacity(cli.repetitions);
    for repetition in 0..cli.repetitions {
        let config = config_from_os_entropy(&manifest, parameter, &pvs);
        let trace = generate_withdrawal_trace(statement, &witness)?;
        let started = Instant::now();
        let proof = prove(&config, &WithdrawalAir::default(), trace, &pvs);
        let prove_ms = started.elapsed().as_secs_f64() * 1_000.0;
        let verify_started = Instant::now();
        ensure!(verify(&config, &WithdrawalAir::default(), &proof, &pvs).is_ok(), "native verifier rejected fresh proof {repetition}");
        let native_verify_ms = verify_started.elapsed().as_secs_f64() * 1_000.0;
        let canonical = canonical_research_encoding(&proof);
        let query_indices = derive_query_indices(&proof, &manifest, parameter, &pvs)?;
        let unique_query_indices = query_indices.iter().copied().collect::<BTreeSet<_>>().len();
        let input_frontier_digests = proof.opening_proof.1.input_openings.iter().map(|opening| opening.opening_proof.1.sibling_hashes.len()).collect();
        let fri_frontier_digests = proof.opening_proof.1.commit_phase_openings.iter().map(|opening| opening.opening_proof.1.sibling_hashes.len()).collect();
        repetitions.push(Repetition {
            repetition,
            proof_identity_keccak256: format!("0x{}", hex::encode(keccak256(&canonical))),
            research_canonical_raw_bytes: canonical.len(),
            prove_ms,
            native_verify_ms,
            process_peak_rss_bytes: peak_rss_bytes(),
            native_verified: true,
            degree_bits: proof.degree_bits,
            fri_rounds: proof.opening_proof.1.commit_phase_commits.len(),
            configured_queries: manifest.fri_num_queries,
            sampled_queries: query_indices.len(),
            unique_query_indices,
            query_indices,
            input_frontier_digests,
            fri_frontier_digests,
        });
    }
    let identities = repetitions.iter().map(|r| &r.proof_identity_keccak256).collect::<BTreeSet<_>>();
    ensure!(identities.len() == repetitions.len(), "fresh proofs did not differ; complete-hiding variability check failed closed");
    let output = json!({
        "schemaVersion": 1,
        "candidateId": "C10-fri",
        "classification": "RESEARCH_ONLY_NOT_SECURITY_QUALIFIED",
        "profileId": manifest.profile_id,
        "manifestSha256": sha256_external(&manifest_bytes),
        "parameterId": parameter.to_string(),
        "parameterBindingWarning": "The frozen v0.3 parameter id is intentionally reused only to preserve the H0 transcript relation; these research parameters are not production-compatible.",
        "plonky3Commit": PINNED_PLONKY3,
        "entropySource": "operating-system entropy via rand::rng, independently reseeding MMCS and PCS StdRng for every repetition",
        "relation": {"air":"pqtc_poseidon_air::WithdrawalAir","traceHeight":TRACE_HEIGHT,"traceWidth":NUM_WITHDRAWAL_COLS,"unchanged":true},
        "proofsDiffer": true,
        "repetitions": repetitions,
    });
    let mut encoded = serde_json::to_vec_pretty(&output)?;
    encoded.push(b'\n');
    fs::write(cli.out.join("measurements.json"), encoded)?;
    println!("profile={} repetitions={} fresh_different=true native_verified=true", manifest.profile_id, cli.repetitions);
    Ok(())
}

fn validate_manifest(m: &Manifest) -> Result<()> {
    ensure!(m.model_version == 1, "unsupported security model version");
    ensure!(m.plonky3_commit == PINNED_PLONKY3, "Plonky3 commit is not the exact pin");
    ensure!(m.logical_trace_height == TRACE_HEIGHT, "logical trace height differs from WithdrawalAir");
    ensure!(m.proof_degree_bits == 9 && m.hiding_degree_padding_bits == 1 && m.is_zk, "profile is not the complete-hiding v0.3 degree relation");
    ensure!(m.relation_width == NUM_WITHDRAWAL_COLS && m.num_constraints == 1186 && m.max_constraint_degree == 7 && m.max_combo == 2, "manifest changes the frozen v0.3/H0 relation");
    ensure!(m.quotient_chunks == QUOTIENT_CHUNKS, "quotient chunk count differs from the frozen relation");
    ensure!(m.hiding_random_functions >= 1, "complete hiding requires at least one random codeword");
    ensure!(m.num_batched_functions == m.relation_width + m.quotient_chunks + m.hiding_random_functions, "batch count does not match relation + quotient + hiding");
    ensure!(m.batch_count_derivation == "relation_plus_quotient_plus_hiding", "unsupported batch-count derivation");
    ensure!(m.fri_log_blowup >= 3 && m.max_constraint_degree <= (1usize << m.fri_log_blowup), "profile is not buildable by the hiding FRI degree rule");
    ensure!(m.fri_max_log_arity == 1, "only the frozen binary fold schedule is supported");
    ensure!(m.fri_num_queries > 0 && m.fri_num_queries <= u16::MAX as usize, "query count is out of range");
    ensure!(m.fri_log_final_poly_len < m.proof_degree_bits, "final polynomial log length is not buildable");
    ensure!(m.commit_grinding_bits <= 31 && m.query_grinding_bits <= 31, "grinding bits exceed fail-closed research limit 31");
    ensure!(m.extension_field_bits == 124 && m.challenge_field_bits == 120, "field security declarations differ from the frozen model");
    ensure!(m.mmcs_binding_bits_classical == 128 && m.mmcs_binding_bits_quantum == 128, "MMCS assumed binding cap differs from the frozen model");
    ensure!(!m.omissions.is_empty(), "security omissions must remain explicit");
    Ok(())
}

fn config_from_os_entropy(m: &Manifest, parameter_id: Digest512, pvs: &[Val]) -> Config {
    let mut os_rng = rand::rng();
    let mmcs_rng = StdRng::from_rng(&mut os_rng);
    let pcs_rng = StdRng::from_rng(&mut os_rng);
    let val_mmcs = ValMmcs::new(ProofLeafHasher, ProofNodeCompressor, 0, mmcs_rng);
    let challenge_mmcs = ChallengeMmcs::new(val_mmcs.clone());
    let fri = FriParameters {
        log_blowup: m.fri_log_blowup,
        log_final_poly_len: m.fri_log_final_poly_len,
        max_log_arity: m.fri_max_log_arity,
        num_queries: m.fri_num_queries,
        commit_proof_of_work_bits: m.commit_grinding_bits,
        query_proof_of_work_bits: m.query_grinding_bits,
        mmcs: challenge_mmcs,
    };
    let pcs = Pcs::new(Dft::default(), val_mmcs, fri, m.hiding_random_functions, pcs_rng);
    Config::new(pcs, Transcript512::new(parameter_id, pvs))
}

fn derive_query_indices(proof: &StarkProof, m: &Manifest, parameter: Digest512, pvs: &[Val]) -> Result<Vec<u32>> {
    let mut t = Transcript512::new(parameter, pvs);
    t.observe(Val::from_usize(proof.degree_bits));
    t.observe(Val::from_usize(proof.degree_bits - 1));
    t.observe(Val::ZERO);
    t.observe(proof.commitments.trace.clone());
    t.observe_slice(pvs);
    let _: Challenge = t.sample_algebra_element();
    t.observe(proof.commitments.quotient_chunks.clone());
    t.observe(proof.commitments.random.clone().context("missing hiding commitment")?);
    let _: Challenge = t.sample_algebra_element();
    let hiding = &proof.opening_proof.0;
    t.observe_algebra_slice(&joined(proof.opened_values.random.as_ref().context("missing random opening")?, &hiding[0][0][0]));
    t.observe_algebra_slice(&joined(&proof.opened_values.trace_local, &hiding[1][0][0]));
    t.observe_algebra_slice(&joined(proof.opened_values.trace_next.as_ref().context("missing next opening")?, &hiding[1][0][1]));
    for (i, chunk) in proof.opened_values.quotient_chunks.iter().enumerate() {
        t.observe_algebra_slice(&joined(chunk, &hiding[2][i][0]));
    }
    let _: Challenge = t.sample_algebra_element();
    for (cap, &witness) in proof.opening_proof.1.commit_phase_commits.iter().zip(&proof.opening_proof.1.commit_pow_witnesses) {
        t.observe(cap.clone());
        ensure!(t.check_witness(m.commit_grinding_bits, witness), "invalid commit grinding witness");
        let _: Challenge = t.sample_algebra_element();
    }
    t.observe_algebra_slice(&proof.opening_proof.1.final_poly);
    for opening in &proof.opening_proof.1.commit_phase_openings {
        t.observe(Val::from_u8(opening.log_arity));
    }
    ensure!(t.check_witness(m.query_grinding_bits, proof.opening_proof.1.query_pow_witness), "invalid query grinding witness");
    let bits = proof.degree_bits + m.fri_log_blowup;
    Ok((0..m.fri_num_queries).map(|_| t.sample_bits(bits) as u32).collect())
}

fn joined(a: &[Challenge], b: &[Challenge]) -> Vec<Challenge> {
    a.iter().chain(b).copied().collect()
}

fn canonical_research_encoding(proof: &StarkProof) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(b"PQTCC10R1");
    put_usize(&mut out, proof.degree_bits);
    put_cap(&mut out, &proof.commitments.trace);
    put_cap(&mut out, &proof.commitments.quotient_chunks);
    if let Some(cap) = &proof.commitments.random { put_cap(&mut out, cap); }
    put_exts(&mut out, &proof.opened_values.trace_local);
    if let Some(v) = &proof.opened_values.trace_next { put_exts(&mut out, v); }
    put_usize(&mut out, proof.opened_values.quotient_chunks.len());
    for v in &proof.opened_values.quotient_chunks { put_exts(&mut out, v); }
    if let Some(v) = &proof.opened_values.random { put_exts(&mut out, v); }
    put_usize(&mut out, proof.opening_proof.0.len());
    for batch in &proof.opening_proof.0 {
        put_usize(&mut out, batch.len());
        for matrix in batch {
            put_usize(&mut out, matrix.len());
            for point in matrix { put_exts(&mut out, point); }
        }
    }
    let fri = &proof.opening_proof.1;
    put_usize(&mut out, fri.commit_phase_commits.len());
    for cap in &fri.commit_phase_commits { put_cap(&mut out, cap); }
    put_usize(&mut out, fri.commit_pow_witnesses.len());
    for &v in &fri.commit_pow_witnesses { put_val(&mut out, v); }
    put_usize(&mut out, fri.input_openings.len());
    for opening in &fri.input_openings {
        put_usize(&mut out, opening.opened_values.len());
        for query in &opening.opened_values {
            put_usize(&mut out, query.len());
            for row in query { put_vals(&mut out, row); }
        }
        put_usize(&mut out, opening.opening_proof.0.len());
        for query in &opening.opening_proof.0 {
            put_usize(&mut out, query.len());
            for salt in query { put_vals(&mut out, salt); }
        }
        put_hashes(&mut out, &opening.opening_proof.1.sibling_hashes);
    }
    put_usize(&mut out, fri.commit_phase_openings.len());
    for opening in &fri.commit_phase_openings {
        put_usize(&mut out, usize::from(opening.log_arity));
        put_usize(&mut out, opening.sibling_values.len());
        for values in &opening.sibling_values { put_exts(&mut out, values); }
        put_usize(&mut out, opening.opening_proof.0.len());
        for query in &opening.opening_proof.0 {
            put_usize(&mut out, query.len());
            for salt in query { put_vals(&mut out, salt); }
        }
        put_hashes(&mut out, &opening.opening_proof.1.sibling_hashes);
    }
    put_exts(&mut out, &fri.final_poly);
    put_val(&mut out, fri.query_pow_witness);
    out
}

fn put_usize(out: &mut Vec<u8>, value: usize) { out.extend_from_slice(&(value as u64).to_be_bytes()); }
fn put_val(out: &mut Vec<u8>, value: Val) { out.extend_from_slice(&value.as_canonical_u32().to_be_bytes()); }
fn put_vals(out: &mut Vec<u8>, values: &[Val]) { put_usize(out, values.len()); for &v in values { put_val(out, v); } }
fn put_ext(out: &mut Vec<u8>, value: Challenge) { for &v in value.as_basis_coefficients_slice() { put_val(out, v); } }
fn put_exts(out: &mut Vec<u8>, values: &[Challenge]) { put_usize(out, values.len()); for &v in values { put_ext(out, v); } }
fn put_digest(out: &mut Vec<u8>, digest: [u64; 8]) { for word in digest { out.extend_from_slice(&word.to_be_bytes()); } }
fn put_cap(out: &mut Vec<u8>, cap: &p3_symmetric::MerkleCap<Val, [u64; 8]>) { put_usize(out, cap.roots().len()); for &digest in cap.roots() { put_digest(out, digest); } }
fn put_hashes(out: &mut Vec<u8>, hashes: &[[u64; 8]]) { put_usize(out, hashes.len()); for &digest in hashes { put_digest(out, digest); } }

fn v03_parameter_id() -> Result<Digest512> {
    let bytes: [u8; 64] = hex::decode(V03_PARAMETER_ID)?.try_into().map_err(|_| anyhow::anyhow!("invalid frozen parameter id"))?;
    Ok(Digest512::from_bytes(bytes))
}

fn read_json<T: for<'de> Deserialize<'de>>(path: PathBuf) -> Result<T> {
    serde_json::from_slice(&fs::read(&path)?).with_context(|| format!("parse {}", path.display()))
}

fn sha256_external(bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    hex::encode(Sha256::digest(bytes))
}

#[cfg(target_os = "macos")]
fn peak_rss_bytes() -> u64 {
    let mut usage = unsafe { std::mem::zeroed::<libc::rusage>() };
    if unsafe { libc::getrusage(libc::RUSAGE_SELF, &mut usage) } == 0 { usage.ru_maxrss as u64 } else { 0 }
}

#[cfg(not(target_os = "macos"))]
fn peak_rss_bytes() -> u64 {
    let mut usage = unsafe { std::mem::zeroed::<libc::rusage>() };
    if unsafe { libc::getrusage(libc::RUSAGE_SELF, &mut usage) } == 0 { (usage.ru_maxrss as u64) * 1024 } else { 0 }
}
