use std::{fs, path::PathBuf, time::Instant};

use anyhow::{Context, Result, bail};
use clap::{Parser, Subcommand};
use p3_air::{Air, RowWindow};
use p3_baby_bear::BabyBear;
use p3_challenger::{CanObserve, CanSample, CanSampleBits};
use p3_commit::PolynomialSpace;
use p3_field::{
    BasedVectorSpace, PrimeCharacteristicRing, PrimeField32, coset::TwoAdicMultiplicativeCoset,
};
use p3_matrix::{dense::RowMajorMatrixView, stack::VerticalPair};
use p3_symmetric::MerkleCap;
use p3_uni_stark::{VerifierConstraintFolder, recompose_quotient_from_chunks};
use pqtc_hash::{
    Note, commitment, digest_to_elements, empty_leaf, keccak256, merkle_node, nullifier_hash,
    payout_digest, scope,
};
use pqtc_indexer::{IndexedBlock, Indexer, IndexerSnapshot};
use pqtc_merkle::MerkleTree;
use pqtc_poseidon_air::{NUM_WITHDRAWAL_COLS, TRACE_HEIGHT, WithdrawalAir, WithdrawalWitness};
use pqtc_security::{ParameterManifest, analyze_profile};
use pqtc_spec::{
    CanonicalSecret, Digest512, PROTOCOL_VERSION, PUBLIC_VALUES_COUNT, ScopeInput, TREE_DEPTH,
    WithdrawalStatement,
};
use pqtc_stark::{
    Challenge, Config, SecurityProfile,
    codec::{COMMON_HEADER_BYTES, decode_proof_parts, encode_proof_parts},
    crypto::{Transcript512, digest_words, proof_leaf_digest, proof_node_digest},
    prove_withdrawal, verify_withdrawal, withdrawal_config_from_os_entropy,
};
use serde::Serialize;

#[derive(Parser)]
#[command(name = "pqtc", version, about = "PQ Tornado Classic research CLI")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Generate a note from operating-system entropy.
    NoteNew {
        #[arg(long)]
        chain_id: u64,
        #[arg(long)]
        pool: String,
        #[arg(long)]
        parameter_id: String,
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Generate canonical parameter manifests.
    ParametersGenerate {
        #[arg(long, default_value = "parameters")]
        out_dir: PathBuf,
    },
    /// Generate the canonical 1,000-case cross-language vector corpus.
    VectorsGenerate {
        #[arg(long, default_value = "test-vectors/hash/v3.json")]
        out: PathBuf,
    },
    /// Generate Rust fixtures for Solidity verifier modules.
    VerifierVectorsGenerate {
        #[arg(long, default_value = "test-vectors/verifier/v3.json")]
        out: PathBuf,
    },
    /// Prove and verify the complete reference withdrawal AIR.
    BenchmarkWithdrawal {
        #[arg(long, default_value = "dev")]
        profile: String,
        #[arg(long)]
        out_dir: Option<PathBuf>,
        /// Emit one natively verified proof without benchmark mutation checks.
        #[arg(long, default_value_t = false)]
        fixture_only: bool,
    },

    /// Prepare a deposit commitment and nullifier from an encoded note.
    DepositPrepare {
        #[arg(long)]
        note: String,
        #[arg(long)]
        scope: String,
        #[arg(long)]
        out: Option<PathBuf>,
    },
    /// Replay cross-checked deposit blocks and persist an index snapshot.
    TreeSync {
        #[arg(long)]
        scope: String,
        #[arg(long, default_value_t = 12)]
        confirmations: u64,
        #[arg(long)]
        primary: PathBuf,
        #[arg(long)]
        secondary: PathBuf,
        #[arg(long)]
        out: PathBuf,
    },
    /// Produce a confirmed Merkle path from a persisted snapshot.
    TreeProvePath {
        #[arg(long)]
        snapshot: PathBuf,
        #[arg(long)]
        commitment: String,
        #[arg(long)]
        out: PathBuf,
    },
    /// Generate canonical two-part withdrawal proof payloads from JSON inputs.
    ProveWithdraw {
        #[arg(long)]
        statement: PathBuf,
        #[arg(long)]
        witness: PathBuf,
        #[arg(long, default_value = "sepolia-v0.3")]
        profile: String,
        #[arg(long)]
        out_dir: PathBuf,
    },
    /// Verify canonical two-part withdrawal proof payloads without EVM execution.
    VerifyNative {
        #[arg(long)]
        statement: PathBuf,
        #[arg(long)]
        part_a: PathBuf,
        #[arg(long)]
        part_b: PathBuf,
        #[arg(long, default_value = "sepolia-v0.3")]
        profile: String,
    },
}

fn main() -> Result<()> {
    match Cli::parse().command {
        Command::NoteNew {
            chain_id,
            pool,
            parameter_id,
            out,
        } => {
            let note = Note::generate(
                chain_id,
                parse_hex::<20>(&pool)?,
                Digest512::from_bytes(parse_hex::<64>(&parameter_id)?),
            );
            let encoded = note.encode();
            if let Some(path) = out {
                fs::write(&path, encoded.as_bytes())
                    .with_context(|| format!("write {}", path.display()))?;
            } else {
                println!("{encoded}");
            }
        }
        Command::ParametersGenerate { out_dir } => {
            for profile in ["dev", "ci", "sepolia-v0.3"] {
                let manifest = ParameterManifest::profile(profile);
                let directory = out_dir.join(profile);
                fs::create_dir_all(&directory)?;
                fs::write(
                    directory.join("security-analysis.json"),
                    serde_json::to_vec_pretty(&analyze_profile(profile))?,
                )?;
                fs::write(directory.join("manifest.bin"), manifest.encode_binary()?)?;
                fs::write(
                    directory.join("manifest.json"),
                    serde_json::to_vec_pretty(&manifest)?,
                )?;
                fs::write(
                    directory.join("parameter-id.txt"),
                    format!("{}\n", manifest.id()?),
                )?;
            }
        }
        Command::VectorsGenerate { out } => generate_vectors(&out)?,
        Command::VerifierVectorsGenerate { out } => generate_verifier_vectors(&out)?,
        Command::BenchmarkWithdrawal {
            profile,
            out_dir,
            fixture_only,
        } => {
            let security_profile = parse_security_profile(&profile)?;
            let parameter = ParameterManifest::profile(&profile).id()?;
            let scope = Digest512 {
                left: [1; 32],
                right: [2; 32],
            };
            let nullifier_secret = CanonicalSecret::from_limbs([3; 8])?;
            let trapdoor = CanonicalSecret::from_limbs([4; 8])?;
            let leaf = commitment(scope, nullifier_secret, trapdoor);
            let mut tree = MerkleTree::new(scope);
            let (leaf_index, root) = tree.insert(leaf)?;
            let path = tree.path(leaf_index)?;
            let statement = WithdrawalStatement {
                scope,
                root,
                nullifier_hash: nullifier_hash(scope, nullifier_secret),
                payout_digest: payout_digest([5; 20], [6; 20], [0; 32]),
            };
            let witness = WithdrawalWitness {
                nullifier_secret,
                trapdoor,
                leaf_index,
                path_bits: path.path_bits(),
                siblings: path.siblings,
            };
            let config = withdrawal_config_from_os_entropy(security_profile, parameter, statement);
            let start = Instant::now();
            let first = prove_withdrawal(&config, statement, &witness)?;
            let prove_time = start.elapsed();
            let first_parts = encode_proof_parts(&first, security_profile, parameter, statement)?;
            if let Some(directory) = out_dir {
                fs::create_dir_all(&directory)?;
                fs::write(directory.join("part-a.pqtc"), &first_parts.part_a.bytes)?;
                fs::write(directory.join("part-b.pqtc"), &first_parts.part_b.bytes)?;
            }
            let decoded = decode_proof_parts(
                &first_parts.part_a.bytes,
                &first_parts.part_b.bytes,
                security_profile,
                parameter,
                statement,
            )?;
            let first_encoded_len = first_parts.part_a.bytes.len() + first_parts.part_b.bytes.len();
            if fixture_only {
                if !verify_withdrawal(&config, statement, &decoded) {
                    bail!("native verifier rejected generated withdrawal proof");
                }
                println!("proof_part_a_bytes={}", first_parts.part_a.bytes.len());
                println!("proof_part_b_bytes={}", first_parts.part_b.bytes.len());
                println!("proof_bytes={first_encoded_len}");
                println!("prove_ms={}", prove_time.as_millis());
                println!("canonical_roundtrip_verified=true");
                return Ok(());
            }
            let second = prove_withdrawal(&config, statement, &witness)?;
            let second_parts = encode_proof_parts(&second, security_profile, parameter, statement)?;
            if first_parts.part_a.bytes == second_parts.part_a.bytes
                && first_parts.part_b.bytes == second_parts.part_b.bytes
            {
                bail!("hiding prover emitted identical proofs for the same witness");
            }
            let first_valid = verify_withdrawal(&config, statement, &first);
            let second_valid = verify_withdrawal(&config, statement, &second);
            let decoded_valid = verify_withdrawal(&config, statement, &decoded);
            if !(first_valid && second_valid && decoded_valid) {
                bail!(
                    "native verifier rejected generated withdrawal proof: first={first_valid} second={second_valid} decoded={decoded_valid}"
                );
            }
            let wrong_parameter = Digest512 {
                left: [0xa5; 32],
                right: [0x5a; 32],
            };
            if decode_proof_parts(
                &first_parts.part_a.bytes,
                &first_parts.part_b.bytes,
                security_profile,
                wrong_parameter,
                statement,
            )
            .is_ok()
            {
                bail!("proof decoder accepted a mismatched parameter ID");
            }
            let mut reordered_public = first_parts.part_a.bytes.clone();
            let public_offset =
                COMMON_HEADER_BYTES - PUBLIC_VALUES_COUNT * core::mem::size_of::<u32>();
            for byte in 0..core::mem::size_of::<u32>() {
                reordered_public.swap(
                    public_offset + byte,
                    public_offset + (PUBLIC_VALUES_COUNT / 4) * core::mem::size_of::<u32>() + byte,
                );
            }
            if decode_proof_parts(
                &reordered_public,
                &first_parts.part_b.bytes,
                security_profile,
                parameter,
                statement,
            )
            .is_ok()
            {
                bail!("proof decoder accepted reordered public values");
            }
            for mutation in 0..100 {
                let mut part_a = first_parts.part_a.bytes.clone();
                let mut part_b = first_parts.part_b.bytes.clone();
                let corrupted = if mutation & 1 == 0 {
                    &mut part_a
                } else {
                    &mut part_b
                };
                let index = mutation * (corrupted.len() - 1) / 99;
                corrupted[index] ^= 1 << (mutation % 8);
                if let Ok(candidate) =
                    decode_proof_parts(&part_a, &part_b, security_profile, parameter, statement)
                {
                    if verify_withdrawal(&config, statement, &candidate) {
                        bail!("mutated proof {mutation} verified");
                    }
                }
            }
            let verify_time = start.elapsed();
            println!("trace_rows={TRACE_HEIGHT}");
            println!("trace_width={NUM_WITHDRAWAL_COLS}");
            println!("proof_part_a_bytes={}", first_parts.part_a.bytes.len());
            println!("proof_part_b_bytes={}", first_parts.part_b.bytes.len());
            println!("proof_bytes={first_encoded_len}");
            println!(
                "opened_trace_local={} opened_trace_next={} quotient_chunks={} quotient_chunk_width={} random_openings={}",
                first.opened_values.trace_local.len(),
                first.opened_values.trace_next.as_ref().map_or(0, Vec::len),
                first.opened_values.quotient_chunks.len(),
                first
                    .opened_values
                    .quotient_chunks
                    .first()
                    .map_or(0, Vec::len),
                first.opened_values.random.as_ref().map_or(0, Vec::len),
            );
            println!(
                "fri_rounds={} fri_inputs={} fri_final_poly={}",
                first.opening_proof.1.commit_phase_commits.len(),
                first.opening_proof.1.input_openings.len(),
                first.opening_proof.1.final_poly.len(),
            );
            for (input, opening) in first.opening_proof.1.input_openings.iter().enumerate() {
                let row_widths: Vec<usize> = opening
                    .opened_values
                    .first()
                    .map(|matrices| matrices.iter().map(Vec::len).collect())
                    .unwrap_or_default();
                println!(
                    "fri_input_{input}_queries={} matrix_widths={row_widths:?} salts_per_query={} path_hashes={}",
                    opening.opened_values.len(),
                    opening.opening_proof.0.first().map_or(0, Vec::len),
                    opening.opening_proof.1.sibling_hashes.len(),
                );
            }
            let hiding = &first.opening_proof.0;
            println!(
                "hiding_shapes={:?}",
                hiding
                    .iter()
                    .map(|round| round
                        .iter()
                        .map(|matrix| matrix.iter().map(Vec::len).collect::<Vec<_>>())
                        .collect::<Vec<_>>())
                    .collect::<Vec<_>>(),
            );
            println!("prove_ms={}", prove_time.as_millis());
            println!("verify_and_mutations_ms={}", verify_time.as_millis());
            println!("same_witness_proofs_differ=true");
            println!("canonical_roundtrip_verified=true");
            println!("structured_mutations_rejected=100");
        }
        Command::DepositPrepare { note, scope, out } => {
            let note = Note::parse(&note)?;
            let pool_scope = parse_application_digest(&scope)?;
            let prepared = serde_json::json!({
                "commitment": commitment(pool_scope, note.nullifier_secret, note.trapdoor).to_string(),
                "nullifier_hash": nullifier_hash(pool_scope, note.nullifier_secret).to_string(),
            });
            let encoded = serde_json::to_vec_pretty(&prepared)?;
            if let Some(path) = out {
                fs::write(path, encoded)?;
            } else {
                println!("{}", String::from_utf8(encoded).expect("JSON is UTF-8"));
            }
        }
        Command::TreeSync {
            scope,
            confirmations,
            primary,
            secondary,
            out,
        } => {
            let primary: Vec<IndexedBlock> = serde_json::from_slice(&fs::read(primary)?)?;
            let secondary: Vec<IndexedBlock> = serde_json::from_slice(&fs::read(secondary)?)?;
            if primary.len() != secondary.len() {
                bail!("RPC endpoint block counts differ");
            }
            let mut indexer = Indexer::new(parse_application_digest(&scope)?, confirmations)?;
            for (block, corroboration) in primary.into_iter().zip(&secondary) {
                indexer.apply_cross_checked(block, corroboration)?;
            }
            fs::write(out, serde_json::to_vec_pretty(&indexer.snapshot())?)?;
        }
        Command::TreeProvePath {
            snapshot,
            commitment,
            out,
        } => {
            let snapshot: IndexerSnapshot = serde_json::from_slice(&fs::read(snapshot)?)?;
            let indexer = Indexer::from_snapshot(snapshot)?;
            let (root, path) = indexer.confirmed_path(parse_application_digest(&commitment)?)?;
            fs::write(
                out,
                serde_json::to_vec_pretty(&serde_json::json!({
                    "root": root,
                    "path": path,
                }))?,
            )?;
        }
        Command::ProveWithdraw {
            statement,
            witness,
            profile,
            out_dir,
        } => {
            let statement: WithdrawalStatement = serde_json::from_slice(&fs::read(statement)?)?;
            validate_statement(statement)?;
            let witness: WithdrawalWitness = serde_json::from_slice(&fs::read(witness)?)?;
            let security_profile = parse_security_profile(&profile)?;
            let parameter = ParameterManifest::profile(&profile).id()?;
            let config = withdrawal_config_from_os_entropy(security_profile, parameter, statement);
            let proof = prove_withdrawal(&config, statement, &witness)?;
            if !verify_withdrawal(&config, statement, &proof) {
                bail!("native verification failed after proving");
            }
            let encoded = encode_proof_parts(&proof, security_profile, parameter, statement)?;
            fs::create_dir_all(&out_dir)?;
            fs::write(out_dir.join("part-a.pqtc"), &encoded.part_a.bytes)?;
            fs::write(out_dir.join("part-b.pqtc"), &encoded.part_b.bytes)?;
            fs::write(
                out_dir.join("metadata.json"),
                serde_json::to_vec_pretty(&serde_json::json!({
                    "version": PROTOCOL_VERSION,
                    "profile": profile,
                    "parameter_id": parameter.to_string(),
                    "statement_key": hex_value(&encoded.part_a.statement_key),
                    "proof_id": hex_value(&encoded.part_a.proof_id),
                    "part_a_bytes": encoded.part_a.bytes.len(),
                    "part_b_bytes": encoded.part_b.bytes.len(),
                }))?,
            )?;
        }
        Command::VerifyNative {
            statement,
            part_a,
            part_b,
            profile,
        } => {
            let statement: WithdrawalStatement = serde_json::from_slice(&fs::read(statement)?)?;
            validate_statement(statement)?;
            let security_profile = parse_security_profile(&profile)?;
            let parameter = ParameterManifest::profile(&profile).id()?;
            let part_a = fs::read(part_a)?;
            let part_b = fs::read(part_b)?;
            let proof =
                decode_proof_parts(&part_a, &part_b, security_profile, parameter, statement)?;
            let config = withdrawal_config_from_os_entropy(security_profile, parameter, statement);
            if !verify_withdrawal(&config, statement, &proof) {
                bail!("proof is invalid");
            }
            println!("valid=true");
        }
    }
    Ok(())
}

fn parse_hex<const N: usize>(value: &str) -> Result<[u8; N]> {
    let value = value.strip_prefix("0x").unwrap_or(value);
    let bytes = hex::decode(value).context("invalid hex")?;
    if bytes.len() != N {
        bail!("expected {N} bytes, got {}", bytes.len());
    }
    Ok(bytes.try_into().expect("length checked"))
}

fn parse_application_digest(value: &str) -> Result<Digest512> {
    let digest = Digest512::from_bytes(parse_hex::<64>(value)?);
    validate_application_digest(digest)?;
    Ok(digest)
}

fn validate_statement(statement: WithdrawalStatement) -> Result<()> {
    for (name, digest) in [
        ("scope", statement.scope),
        ("root", statement.root),
        ("nullifier_hash", statement.nullifier_hash),
        ("payout_digest", statement.payout_digest),
    ] {
        validate_application_digest(digest)
            .with_context(|| format!("{name} is not a canonical P2BB512 digest"))?;
    }
    Ok(())
}

fn validate_application_digest(digest: Digest512) -> Result<()> {
    if digest_to_elements(digest).is_none() {
        bail!("digest contains a noncanonical BabyBear limb");
    }
    Ok(())
}

fn parse_security_profile(value: &str) -> Result<SecurityProfile> {
    match value {
        "dev" => Ok(SecurityProfile::Dev),
        "ci" => Ok(SecurityProfile::Ci),
        "sepolia-v0.3" => Ok(SecurityProfile::SepoliaV03),
        _ => bail!("unknown security profile: {value}"),
    }
}

#[derive(Serialize)]
struct VectorFile {
    version: u16,
    count: usize,
    vectors: Vec<HashVector>,
}

#[derive(Serialize)]
struct HashVector {
    index: u32,
    chain_id: String,
    pool: String,
    denomination: String,
    parameter_id: String,
    scope: String,
    nullifier_secret: String,
    trapdoor: String,
    commitment: String,
    nullifier_hash: String,
    recipient: String,
    relayer: String,
    fee: String,
    payout_digest: String,
    zero_leaf: String,
    level_zero_node: String,
    root_after_insert: String,
}

fn generate_vectors(path: &PathBuf) -> Result<()> {
    let chain_id = 11_155_111u64;
    let pool = [0x11; 20];
    let denomination = u256(1_000_000_000_000_000);
    let parameter = ParameterManifest::profile("dev").id()?;
    let scope_input = ScopeInput {
        chain_id,
        pool,
        denomination,
        tree_depth: TREE_DEPTH,
        protocol_version: PROTOCOL_VERSION,
        parameter_id: parameter,
    };
    let pool_scope = scope(scope_input);
    let zero_leaf = empty_leaf(pool_scope);
    let mut tree = MerkleTree::new(pool_scope);
    let mut vectors = Vec::with_capacity(1_000);
    for index in 0..1_000u32 {
        let nullifier_secret = deterministic_secret(b"pqtc-nullifier-vector", index)?;
        let trapdoor = deterministic_secret(b"pqtc-trapdoor-vector", index)?;
        let note_commitment = commitment(pool_scope, nullifier_secret, trapdoor);
        let nullifier = nullifier_hash(pool_scope, nullifier_secret);
        let recipient_seed = deterministic_bytes(b"pqtc-recipient-vector", index);
        let relayer_seed = deterministic_bytes(b"pqtc-relayer-vector", index);
        let recipient: [u8; 20] = recipient_seed[12..].try_into().expect("fixed slice");
        let relayer: [u8; 20] = relayer_seed[12..].try_into().expect("fixed slice");
        let fee = u256(u128::from(index) * 1_000_000_000);
        let payout = payout_digest(recipient, relayer, fee);
        let level_zero_node = merkle_node(0, note_commitment, zero_leaf);
        let (_, root) = tree.insert(note_commitment)?;
        vectors.push(HashVector {
            index,
            chain_id: chain_id.to_string(),
            pool: hex_value(&pool),
            denomination: hex_value(&denomination),
            parameter_id: parameter.to_string(),
            scope: pool_scope.to_string(),
            nullifier_secret: nullifier_secret.to_string(),
            trapdoor: trapdoor.to_string(),
            commitment: note_commitment.to_string(),
            nullifier_hash: nullifier.to_string(),
            recipient: hex_value(&recipient),
            relayer: hex_value(&relayer),
            fee: hex_value(&fee),
            payout_digest: payout.to_string(),
            zero_leaf: zero_leaf.to_string(),
            level_zero_node: level_zero_node.to_string(),
            root_after_insert: root.to_string(),
        });
    }
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(
        path,
        serde_json::to_vec_pretty(&VectorFile {
            version: PROTOCOL_VERSION as u16,
            count: vectors.len(),
            vectors,
        })?,
    )?;
    Ok(())
}

fn deterministic_bytes(label: &[u8], index: u32) -> [u8; 32] {
    let mut input = Vec::with_capacity(label.len() + 4);
    input.extend_from_slice(label);
    input.extend_from_slice(&index.to_be_bytes());
    keccak256(&input)
}

fn deterministic_secret(label: &[u8], index: u32) -> Result<CanonicalSecret> {
    let mut input = Vec::with_capacity(label.len() + 9);
    input.extend_from_slice(label);
    input.extend_from_slice(&index.to_be_bytes());
    let limb_offset = input.len();
    input.extend_from_slice(&[0; 5]);
    let limbs = core::array::from_fn(|limb| {
        input[limb_offset] = limb as u8;
        let mut attempt = 0u32;
        loop {
            input[limb_offset + 1..].copy_from_slice(&attempt.to_be_bytes());
            let candidate =
                u32::from_be_bytes(keccak256(&input)[..4].try_into().expect("fixed slice"));
            if candidate < pqtc_spec::BABY_BEAR_MODULUS {
                break candidate;
            }
            attempt = attempt.wrapping_add(1);
        }
    });
    CanonicalSecret::from_limbs(limbs).map_err(Into::into)
}

fn u256(value: u128) -> [u8; 32] {
    let mut out = [0u8; 32];
    out[16..].copy_from_slice(&value.to_be_bytes());
    out
}

fn hex_value(bytes: &[u8]) -> String {
    format!("0x{}", hex::encode(bytes))
}

#[derive(Serialize)]
struct VerifierVectorFile {
    version: u16,
    fields: Vec<FieldVector>,
    extensions: Vec<ExtensionVector>,
    transcripts: Vec<TranscriptVector>,
    mmcs: Vec<MmcsVector>,
    fri_folds: Vec<FriFoldVector>,
    air: AirVector,
}

#[derive(Serialize)]
struct FieldVector {
    a: u32,
    b: u32,
    add: u32,
    sub: u32,
    mul: u32,
    inv_a: u32,
}

#[derive(Serialize)]
struct ExtensionVector {
    a: [u32; 4],
    b: [u32; 4],
    add: [u32; 4],
    sub: [u32; 4],
    mul: [u32; 4],
}

#[derive(Serialize)]
struct TranscriptVector {
    parameter_id: String,
    public_values: Vec<u32>,
    observed_field: u32,
    observed_commitment: String,
    challenges: Vec<u32>,
    bits14: usize,
}

#[derive(Serialize)]
struct MmcsVector {
    root: String,
    leaf_values: Vec<u32>,
    leaf_index: usize,
    siblings: Vec<String>,
}

#[derive(Serialize)]
struct FriFoldVector {
    index: usize,
    log_height: usize,
    beta: [u32; 4],
    low: [u32; 4],
    high: [u32; 4],
    expected: [u32; 4],
}

#[derive(Serialize)]
struct AirVector {
    local: Vec<[u32; 4]>,
    next: Vec<[u32; 4]>,
    public_values: Vec<[u32; 4]>,
    is_first: [u32; 4],
    is_last: [u32; 4],
    is_transition: [u32; 4],
    alpha: [u32; 4],
    expected: [u32; 4],
    zeta: [u32; 4],
    selectors: [[u32; 4]; 4],
    quotient_openings: Vec<[u32; 4]>,
    quotient: [u32; 4],
}

fn generate_air_vector() -> AirVector {
    let local: Vec<Challenge> = (0..NUM_WITHDRAWAL_COLS)
        .map(|index| ext_from_array(deterministic_ext(b"pqtc-air-local", index as u32)))
        .collect();
    let next: Vec<Challenge> = (0..NUM_WITHDRAWAL_COLS)
        .map(|index| ext_from_array(deterministic_ext(b"pqtc-air-next", index as u32)))
        .collect();
    let public_base: Vec<BabyBear> = (0..PUBLIC_VALUES_COUNT as u32)
        .map(|index| BabyBear::from_u32(deterministic_ext(b"pqtc-air-public", index)[0]))
        .collect();
    let is_first = ext_from_array(deterministic_ext(b"pqtc-air-first", 0));
    let is_last = ext_from_array(deterministic_ext(b"pqtc-air-last", 0));
    let is_transition = ext_from_array(deterministic_ext(b"pqtc-air-transition", 0));
    let alpha = ext_from_array(deterministic_ext(b"pqtc-air-alpha", 0));

    let main = VerticalPair::new(
        RowMajorMatrixView::new_row(&local),
        RowMajorMatrixView::new_row(&next),
    );
    let preprocessed = VerticalPair::new(
        RowMajorMatrixView::new(&[], 0),
        RowMajorMatrixView::new(&[], 0),
    );
    let mut folder: VerifierConstraintFolder<'_, Config> = VerifierConstraintFolder {
        main,
        preprocessed,
        preprocessed_window: RowWindow::from_two_rows(&[], &[]),
        periodic_values: &[],
        public_values: &public_base,
        is_first_row: is_first,
        is_last_row: is_last,
        is_transition,
        alpha,
        accumulator: Challenge::ZERO,
    };
    WithdrawalAir::default().eval(&mut folder);
    let zeta = ext_from_array(deterministic_ext(b"pqtc-air-zeta", 0));
    let trace_domain =
        TwoAdicMultiplicativeCoset::new(BabyBear::ONE, 8).expect("valid trace domain");
    let domain_selectors = trace_domain.selectors_at_point(zeta);
    let proof_trace_domain =
        TwoAdicMultiplicativeCoset::new(BabyBear::ONE, 9).expect("valid hiding trace domain");
    let quotient_domains = proof_trace_domain
        .try_create_disjoint_domain(1 << 13)
        .expect("valid quotient domain")
        .split_domains(16);
    let quotient_chunks: Vec<Vec<Challenge>> = (0..16)
        .map(|chunk| {
            (0..4)
                .map(|coefficient| {
                    ext_from_array(deterministic_ext(
                        b"pqtc-air-quotient",
                        (chunk * 4 + coefficient) as u32,
                    ))
                })
                .collect()
        })
        .collect();
    let quotient =
        recompose_quotient_from_chunks::<Config>(&quotient_domains, &quotient_chunks, zeta);
    AirVector {
        local: local.iter().copied().map(ext_to_array).collect(),
        next: next.iter().copied().map(ext_to_array).collect(),
        public_values: public_base
            .iter()
            .map(|value| [value.as_canonical_u32(), 0, 0, 0])
            .collect(),
        is_first: ext_to_array(is_first),
        is_last: ext_to_array(is_last),
        is_transition: ext_to_array(is_transition),
        alpha: ext_to_array(alpha),
        expected: ext_to_array(folder.accumulator),
        zeta: ext_to_array(zeta),
        selectors: [
            ext_to_array(domain_selectors.is_first_row),
            ext_to_array(domain_selectors.is_last_row),
            ext_to_array(domain_selectors.is_transition),
            ext_to_array(domain_selectors.inv_vanishing),
        ],
        quotient_openings: quotient_chunks
            .into_iter()
            .flatten()
            .map(ext_to_array)
            .collect(),
        quotient: ext_to_array(quotient),
    }
}

fn ext_from_array(coefficients: [u32; 4]) -> Challenge {
    Challenge::from_basis_coefficients_fn(|index| BabyBear::from_u32(coefficients[index]))
}

fn ext_to_array(value: Challenge) -> [u32; 4] {
    let coefficients: &[BabyBear] = value.as_basis_coefficients_slice();
    core::array::from_fn(|index| coefficients[index].as_canonical_u32())
}

fn generate_verifier_vectors(path: &PathBuf) -> Result<()> {
    const P: u64 = 2_013_265_921;
    let mut fields = Vec::with_capacity(10_000);
    for index in 0..10_000u32 {
        let a = u32::from_be_bytes(
            deterministic_bytes(b"pqtc-field-a", index)[..4]
                .try_into()
                .unwrap(),
        ) % (P as u32 - 1)
            + 1;
        let b = u32::from_be_bytes(
            deterministic_bytes(b"pqtc-field-b", index)[..4]
                .try_into()
                .unwrap(),
        ) % P as u32;
        fields.push(FieldVector {
            a,
            b,
            add: ((u64::from(a) + u64::from(b)) % P) as u32,
            sub: ((u64::from(a) + P - u64::from(b)) % P) as u32,
            mul: ((u64::from(a) * u64::from(b)) % P) as u32,
            inv_a: bb_pow(a, P - 2),
        });
    }

    let mut extensions = Vec::with_capacity(1_000);
    for index in 0..1_000u32 {
        let a = deterministic_ext(b"pqtc-ext-a", index);
        let b = deterministic_ext(b"pqtc-ext-b", index);
        extensions.push(ExtensionVector {
            a,
            b,
            add: core::array::from_fn(|i| bb_add(a[i], b[i])),
            sub: core::array::from_fn(|i| bb_sub(a[i], b[i])),
            mul: ext_mul(a, b),
        });
    }

    let mut transcripts = Vec::with_capacity(32);
    for index in 0..32u32 {
        let parameter_id = Digest512::from_bytes(
            [
                deterministic_bytes(b"pqtc-transcript-parameter-left", index),
                deterministic_bytes(b"pqtc-transcript-parameter-right", index),
            ]
            .concat()
            .try_into()
            .unwrap(),
        );
        let public_values: Vec<u32> = (0..8)
            .map(|item| {
                u32::from_be_bytes(
                    deterministic_bytes(b"pqtc-transcript-public", index * 8 + item)[..4]
                        .try_into()
                        .unwrap(),
                ) % P as u32
            })
            .collect();
        let public_fields: Vec<BabyBear> = public_values
            .iter()
            .copied()
            .map(BabyBear::from_u32)
            .collect();
        let observed_field = fields[index as usize].a;
        let observed_commitment = Digest512::from_bytes(
            [
                deterministic_bytes(b"pqtc-transcript-commitment-left", index),
                deterministic_bytes(b"pqtc-transcript-commitment-right", index),
            ]
            .concat()
            .try_into()
            .unwrap(),
        );
        let mut transcript = Transcript512::new(parameter_id, &public_fields);
        transcript.observe(BabyBear::from_u32(observed_field));
        transcript.observe(MerkleCap::<BabyBear, [u64; 8]>::new(vec![digest_words(
            observed_commitment,
        )]));
        let challenges = (0..8)
            .map(|_| {
                let value: BabyBear = transcript.sample();
                value.as_canonical_u32()
            })
            .collect();
        let bits14 = transcript.sample_bits(14);
        transcripts.push(TranscriptVector {
            parameter_id: parameter_id.to_string(),
            public_values,
            observed_field,
            observed_commitment: observed_commitment.to_string(),
            challenges,
            bits14,
        });
    }

    let mut mmcs = Vec::with_capacity(16);
    for fixture in 0..16u32 {
        let width = 1 + fixture as usize % 8;
        let leaves: Vec<Vec<u32>> = (0..64u32)
            .map(|leaf| {
                (0..width)
                    .map(|column| {
                        u32::from_be_bytes(
                            deterministic_bytes(
                                b"pqtc-mmcs",
                                fixture * 10_000 + leaf * 16 + column as u32,
                            )[..4]
                                .try_into()
                                .unwrap(),
                        ) % P as u32
                    })
                    .collect()
            })
            .collect();
        let mut layer: Vec<Digest512> = leaves
            .iter()
            .map(|values| proof_leaf_digest(values))
            .collect();
        let leaf_index = (fixture as usize * 13 + 7) % 64;
        let leaf_values = leaves[leaf_index].clone();
        let mut current_index = leaf_index;
        let mut siblings = Vec::with_capacity(6);
        while layer.len() > 1 {
            siblings.push(layer[current_index ^ 1].to_string());
            layer = layer
                .chunks_exact(2)
                .map(|pair| proof_node_digest(pair[0], pair[1]))
                .collect();
            current_index >>= 1;
        }
        mmcs.push(MmcsVector {
            root: layer[0].to_string(),
            leaf_values,
            leaf_index,
            siblings,
        });
    }

    let mut fri_folds = Vec::with_capacity(1_000);
    for index in 0..1_000u32 {
        let log_height = 1 + index as usize % 15;
        let domain_index = (index as usize * 7919) & ((1usize << log_height) - 1);
        let beta = deterministic_ext(b"pqtc-fri-beta", index);
        let low = deterministic_ext(b"pqtc-fri-low", index);
        let high = deterministic_ext(b"pqtc-fri-high", index);
        fri_folds.push(FriFoldVector {
            index: domain_index,
            log_height,
            beta,
            low,
            high,
            expected: fri_fold(domain_index, log_height, beta, low, high),
        });
    }
    let air = generate_air_vector();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(
        path,
        serde_json::to_vec_pretty(&VerifierVectorFile {
            version: PROTOCOL_VERSION as u16,
            fields,
            extensions,
            transcripts,
            mmcs,
            fri_folds,
            air,
        })?,
    )?;
    Ok(())
}

fn bb_add(a: u32, b: u32) -> u32 {
    ((u64::from(a) + u64::from(b)) % 2_013_265_921) as u32
}
fn bb_sub(a: u32, b: u32) -> u32 {
    ((u64::from(a) + 2_013_265_921 - u64::from(b)) % 2_013_265_921) as u32
}
fn bb_mul(a: u32, b: u32) -> u32 {
    ((u64::from(a) * u64::from(b)) % 2_013_265_921) as u32
}
fn bb_pow(mut base: u32, mut exponent: u64) -> u32 {
    let mut result = 1;
    while exponent != 0 {
        if exponent & 1 != 0 {
            result = bb_mul(result, base);
        }
        base = bb_mul(base, base);
        exponent >>= 1;
    }
    result
}
fn deterministic_ext(label: &[u8], index: u32) -> [u32; 4] {
    let bytes = deterministic_bytes(label, index);
    core::array::from_fn(|coefficient| {
        u32::from_be_bytes(
            bytes[coefficient * 4..coefficient * 4 + 4]
                .try_into()
                .unwrap(),
        ) % 2_013_265_921
    })
}
fn ext_mul(a: [u32; 4], b: [u32; 4]) -> [u32; 4] {
    let t0 = bb_mul(a[0], b[0]);
    let t1 = bb_add(bb_mul(a[0], b[1]), bb_mul(a[1], b[0]));
    let t2 = bb_add(
        bb_add(bb_mul(a[0], b[2]), bb_mul(a[1], b[1])),
        bb_mul(a[2], b[0]),
    );
    let t3 = bb_add(
        bb_add(
            bb_add(bb_mul(a[0], b[3]), bb_mul(a[1], b[2])),
            bb_mul(a[2], b[1]),
        ),
        bb_mul(a[3], b[0]),
    );
    let t4 = bb_add(
        bb_add(bb_mul(a[1], b[3]), bb_mul(a[2], b[2])),
        bb_mul(a[3], b[1]),
    );
    let t5 = bb_add(bb_mul(a[2], b[3]), bb_mul(a[3], b[2]));
    let t6 = bb_mul(a[3], b[3]);
    [
        bb_add(t0, bb_mul(11, t4)),
        bb_add(t1, bb_mul(11, t5)),
        bb_add(t2, bb_mul(11, t6)),
        t3,
    ]
}
fn fri_fold(
    index: usize,
    log_height: usize,
    beta: [u32; 4],
    low: [u32; 4],
    high: [u32; 4],
) -> [u32; 4] {
    let mut generator = 0x1a42_7a41;
    for _ in log_height + 1..27 {
        generator = bb_mul(generator, generator);
    }
    let mut reversed = 0usize;
    for bit in 0..log_height {
        reversed = (reversed << 1) | ((index >> bit) & 1);
    }
    let x = bb_pow(generator, reversed as u64);
    let inverse_two_x = bb_mul(1_006_632_961, bb_pow(x, 2_013_265_919));
    let even: [u32; 4] = core::array::from_fn(|i| bb_mul(bb_add(low[i], high[i]), 1_006_632_961));
    let odd_base: [u32; 4] =
        core::array::from_fn(|i| bb_mul(bb_sub(low[i], high[i]), inverse_two_x));
    let odd = ext_mul(odd_base, beta);
    core::array::from_fn(|i| bb_add(even[i], odd[i]))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn application_digest_parser_rejects_noncanonical_limb() {
        let mut bytes = [0u8; 64];
        bytes[..4].copy_from_slice(&pqtc_spec::BABY_BEAR_MODULUS.to_be_bytes());
        assert!(parse_application_digest(&hex::encode(bytes)).is_err());
    }

    #[test]
    fn security_profile_parser_accepts_v3_and_rejects_v2() {
        assert_eq!(
            parse_security_profile("sepolia-v0.3").unwrap(),
            SecurityProfile::SepoliaV03
        );
        assert!(parse_security_profile("sepolia-v0.2").is_err());
    }

    #[test]
    fn deterministic_vector_secrets_are_canonical_big_endian_limbs() {
        let secret = deterministic_secret(b"pqtc-test-secret", 7).unwrap();
        assert!(
            secret
                .limbs()
                .iter()
                .all(|&limb| limb < pqtc_spec::BABY_BEAR_MODULUS)
        );
        assert_eq!(
            secret.to_string().parse::<CanonicalSecret>().unwrap(),
            secret
        );
    }

    #[test]
    fn witness_json_rejects_noncanonical_secret_limbs() {
        let secret = CanonicalSecret::from_limbs([1; 8]).unwrap();
        let witness = WithdrawalWitness {
            nullifier_secret: secret,
            trapdoor: secret,
            leaf_index: 0,
            path_bits: [0; TREE_DEPTH as usize],
            siblings: [Digest512::ZERO; TREE_DEPTH as usize],
        };
        let mut json = serde_json::to_value(witness).unwrap();
        json["nullifier_secret"] = serde_json::Value::String(format!(
            "0x{:08x}{}",
            pqtc_spec::BABY_BEAR_MODULUS,
            "00".repeat(28)
        ));
        assert!(serde_json::from_value::<WithdrawalWitness>(json).is_err());
    }

    #[test]
    fn statement_validation_checks_all_sixty_four_limbs() {
        let canonical = Digest512::ZERO;
        let mut bytes = [0u8; 64];
        bytes[60..].copy_from_slice(&pqtc_spec::BABY_BEAR_MODULUS.to_be_bytes());
        let noncanonical = Digest512::from_bytes(bytes);
        let statement = WithdrawalStatement {
            scope: canonical,
            root: canonical,
            nullifier_hash: canonical,
            payout_digest: noncanonical,
        };
        assert_eq!(statement.public_values().len(), 64);
        assert!(validate_statement(statement).is_err());
    }
}
