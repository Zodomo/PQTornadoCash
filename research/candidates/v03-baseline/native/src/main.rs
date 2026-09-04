use std::{fs, path::{Path, PathBuf}, time::Instant};

use anyhow::{Context, Result, ensure};
use clap::{Parser, Subcommand};
use pqtc_hash::{commitment, empty_leaf, keccak256, merkle_node, nullifier_hash, payout_digest, scope};
use pqtc_poseidon_air::{WithdrawalWitness, check_witness};
use pqtc_security::ParameterManifest;
use pqtc_spec::{BABY_BEAR_MODULUS, CanonicalSecret, Digest512, PROTOCOL_VERSION, ScopeInput, TREE_DEPTH, WithdrawalStatement};
use pqtc_stark::{SecurityProfile, codec::{decode_proof_parts, encode_proof_parts}, prove_withdrawal, verify_withdrawal, withdrawal_config_from_os_entropy};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

const CANDIDATE_ID: &str = "C00/v03-baseline";
const PARAMETER_ID: &str = "35adfcc070249bb0393c2fd45f0bbd48ef03cbfc08070d03335eaf952975e62ab7bc82ead4f8c1f1c39b3372be85195853134dfc9d24f43b97a5e0454ea07779";
const FIXED_POOL: [u8; 20] = [0xc0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0xc0,0];

#[derive(Parser)]
struct Cli { #[command(subcommand)] command: Command }

#[derive(Subcommand)]
enum Command {
    Prepare { #[arg(long)] corpus: PathBuf, #[arg(long)] out: PathBuf },
    Prove { #[arg(long)] input: PathBuf, #[arg(long)] out: PathBuf },
    Verify { #[arg(long)] input: PathBuf, #[arg(long)] proof: PathBuf },
}

#[derive(Deserialize)]
struct Corpus { cases: Vec<SemanticCase> }

#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct SemanticCase {
    case_id: String,
    chain_id: String,
    denomination: String,
    fee: String,
    leaf_index: u32,
    nullifier_secret_bytes: String,
    path_bits: Vec<u8>,
    pool_address: String,
    recipient: String,
    relayer: String,
    sibling_seeds: Vec<String>,
    trapdoor_bytes: String,
    tree_depth: u8,
    #[serde(flatten)] extra: serde_json::Map<String, Value>,
}

#[derive(Serialize)]
struct MappingLog {
    algorithm: &'static str,
    byte_order: &'static str,
    modulus: u32,
    draws_total: usize,
    rejected_draws: Vec<RejectedDraw>,
}

#[derive(Serialize)]
struct RejectedDraw { target: String, draw_index: u64, candidate: u32 }

struct Mapper { draws: usize, rejected: Vec<RejectedDraw> }

impl Mapper {
    fn fields<const N: usize>(&mut self, target: &str, seed: &[u8]) -> [u32; N] {
        let mut values = Vec::with_capacity(N);
        let mut draw_index = 0u64;
        while values.len() < N {
            let mut message = Vec::with_capacity(23 + target.len() + seed.len());
            message.extend_from_slice(b"PQTC.C00.MAP.V1\0");
            message.extend_from_slice(target.as_bytes());
            message.push(0);
            message.extend_from_slice(seed);
            message.extend_from_slice(&draw_index.to_be_bytes());
            let digest = keccak256(&message);
            let candidate = u32::from_be_bytes(digest[..4].try_into().expect("four bytes"));
            self.draws += 1;
            if candidate < BABY_BEAR_MODULUS {
                values.push(candidate);
            } else {
                self.rejected.push(RejectedDraw { target: target.to_owned(), draw_index, candidate });
            }
            draw_index += 1;
        }
        values.try_into().ok().expect("exact field count")
    }
}

fn main() -> Result<()> {
    match Cli::parse().command {
        Command::Prepare { corpus, out } => prepare(&corpus, &out),
        Command::Prove { input, out } => prove_one(&input, &out),
        Command::Verify { input, proof } => verify_one(&input, &proof),
    }
}

fn prepare(corpus_path: &Path, out: &Path) -> Result<()> {
    if out.exists() { fs::remove_dir_all(out).context("remove previous prepared inputs")?; }
    fs::create_dir_all(out)?;
    let parameter_id = parameter_id()?;

    let fixed_dir = out.join("fixed");
    fs::create_dir_all(&fixed_dir)?;
    let fixed_statement = WithdrawalStatement {
        scope: Digest512 { left: [1; 32], right: [2; 32] },
        root: Digest512::ZERO,
        nullifier_hash: Digest512::ZERO,
        payout_digest: payout_digest([5; 20], [6; 20], [0; 32]),
    };
    let fixed_secret = CanonicalSecret::from_limbs([3; 8])?;
    let fixed_trapdoor = CanonicalSecret::from_limbs([4; 8])?;
    let leaf = commitment(fixed_statement.scope, fixed_secret, fixed_trapdoor);
    let mut current = leaf;
    let mut zero = empty_leaf(fixed_statement.scope);
    let mut siblings = [Digest512::ZERO; TREE_DEPTH as usize];
    for level in 0..TREE_DEPTH as usize {
        siblings[level] = zero;
        current = merkle_node(level as u8, current, zero);
        zero = merkle_node(level as u8, zero, zero);
    }
    let fixed_statement = WithdrawalStatement { root: current, nullifier_hash: nullifier_hash(fixed_statement.scope, fixed_secret), ..fixed_statement };
    let fixed_witness = WithdrawalWitness { nullifier_secret: fixed_secret, trapdoor: fixed_trapdoor, leaf_index: 0, path_bits: [0; TREE_DEPTH as usize], siblings };
    write_input(&fixed_dir, &fixed_statement, &fixed_witness, &json!({
        "kind": "fixed-baseline", "candidate_id": CANDIDATE_ID,
        "source": "old_reports/ENGINEERING_REPORT.md benchmark witness: scope halves 0x01/0x02, secrets 3/4, recipient 5, relayer 6, fee 0"
    }), &json!({"algorithm":"not-applicable; values are the report's canonical limbs","rejected_draws":[]} ), 1_000_000_000_000_000_000u128, [5;20], [6;20], 0, FIXED_POOL)?;

    let corpus: Corpus = serde_json::from_slice(&fs::read(corpus_path)?)?;
    ensure!(corpus.cases.len() >= 30, "semantic corpus has fewer than 30 cases");
    let mut selected = Vec::new();
    for case in corpus.cases.into_iter().filter(|case| case.tree_depth == TREE_DEPTH).take(30) {
        ensure!(case.path_bits.len() == TREE_DEPTH as usize && case.sibling_seeds.len() == TREE_DEPTH as usize, "{} is not a depth-20 case", case.case_id);
        ensure!(case.path_bits.iter().enumerate().all(|(level, bit)| *bit == ((case.leaf_index >> level) & 1) as u8), "{} path bits do not encode leaf index", case.case_id);
        let mut mapper = Mapper { draws: 0, rejected: Vec::new() };
        let secret_seed = parse_hex::<32>(&case.nullifier_secret_bytes)?;
        let trapdoor_seed = parse_hex::<32>(&case.trapdoor_bytes)?;
        let nullifier_secret = CanonicalSecret::from_limbs(mapper.fields("nullifier-secret", &secret_seed))?;
        let trapdoor = CanonicalSecret::from_limbs(mapper.fields("trapdoor", &trapdoor_seed))?;
        let mut mapped_siblings = Vec::with_capacity(TREE_DEPTH as usize);
        for (level, encoded) in case.sibling_seeds.iter().enumerate() {
            let seed = parse_hex::<32>(encoded)?;
            let fields: [u32; 16] = mapper.fields(&format!("sibling-{level}"), &seed);
            mapped_siblings.push(digest_from_fields(fields));
        }
        let siblings: [Digest512; TREE_DEPTH as usize] = mapped_siblings.try_into().ok().expect("depth checked");
        let pool = parse_hex::<20>(&case.pool_address)?;
        let recipient = parse_hex::<20>(&case.recipient)?;
        let relayer = parse_hex::<20>(&case.relayer)?;
        let denomination: u128 = case.denomination.parse().context("denomination exceeds u128")?;
        let fee: u128 = case.fee.parse().context("fee exceeds u128")?;
        ensure!(fee <= denomination, "{} fee exceeds denomination", case.case_id);
        let scope_digest = scope(ScopeInput {
            chain_id: case.chain_id.parse()?, pool, denomination: u256_bytes(denomination), tree_depth: TREE_DEPTH,
            protocol_version: PROTOCOL_VERSION, parameter_id,
        });
        let leaf = commitment(scope_digest, nullifier_secret, trapdoor);
        let mut intermediate = Vec::with_capacity(TREE_DEPTH as usize);
        let mut root = leaf;
        for (level, (&bit, sibling)) in case.path_bits.iter().zip(&siblings).enumerate() {
            root = if bit == 0 { merkle_node(level as u8, root, *sibling) } else { merkle_node(level as u8, *sibling, root) };
            intermediate.push(root);
        }
        let statement = WithdrawalStatement { scope: scope_digest, root, nullifier_hash: nullifier_hash(scope_digest, nullifier_secret), payout_digest: payout_digest(recipient, relayer, u256_bytes(fee)) };
        let witness = WithdrawalWitness { nullifier_secret, trapdoor, leaf_index: case.leaf_index, path_bits: case.path_bits.clone().try_into().ok().expect("depth checked"), siblings };
        check_witness(statement, &witness).with_context(|| format!("derived witness {}", case.case_id))?;
        let case_dir = out.join("corpus").join(&case.case_id);
        fs::create_dir_all(&case_dir)?;
        let mapping = MappingLog { algorithm: "Keccak-256(PQTC.C00.MAP.V1 || target || 0x00 || sourceBytes || uint64be(drawIndex)); take first big-endian u32 and reject values >= modulus", byte_order: "big-endian u32", modulus: BABY_BEAR_MODULUS, draws_total: mapper.draws, rejected_draws: mapper.rejected };
        let derived = json!({"candidateId":CANDIDATE_ID,"caseId":case.case_id,"scope":statement.scope,"commitment":leaf,"nullifier":statement.nullifier_hash,"siblings":siblings,"intermediateParents":intermediate,"root":statement.root,"payoutBinding":statement.payout_digest,"publicStatement":statement,"privateWitnessEncoding":witness,"semanticSourceCase":case});
        write_input(&case_dir, &statement, &witness, &derived, &serde_json::to_value(mapping)?, denomination, recipient, relayer, fee, FIXED_POOL)?;
        selected.push(case_dir.file_name().unwrap().to_string_lossy().into_owned());
    }
    ensure!(selected.len() == 30, "fewer than 30 supported depth-20 corpus cases");
    let jobs: Vec<Value> = (0..30).map(|i| json!({"run_id":format!("v03-fixed-{:02}", i+1),"input":"fixed","kind":"fixed-baseline"}))
        .chain(selected.iter().enumerate().map(|(i,id)| json!({"run_id":format!("v03-corpus-{:02}", i+1),"input":format!("corpus/{id}"),"kind":"semantic-corpus","case_id":id}))).collect();
    write_json(&out.join("jobs.json"), &json!({"candidate_id":CANDIDATE_ID,"count":60,"fixed_proofs":30,"distinct_corpus_witnesses":30,"entropy_policy":"fresh operating-system entropy is acquired inside each independent prove process","jobs":jobs}))?;
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn write_input(dir: &Path, statement: &WithdrawalStatement, witness: &WithdrawalWitness, derived: &Value, mapping: &Value, denomination: u128, recipient: [u8;20], relayer: [u8;20], fee: u128, pool: [u8;20]) -> Result<()> {
    check_witness(*statement, witness)?;
    write_json(&dir.join("statement.json"), statement)?;
    write_json(&dir.join("witness.json"), witness)?;
    write_json(&dir.join("derived-case.json"), derived)?;
    write_json(&dir.join("mapping.json"), mapping)?;
    write_json(&dir.join("evm.json"), &json!({
        "pool_address": format!("0x{}",hex::encode(pool)), "denomination_wei":denomination.to_string(),
        "scope":statement.scope.to_string(),"root":statement.root.to_string(),
        "nullifier_hash":statement.nullifier_hash.to_string(),
        "recipient":format!("0x{}",hex::encode(recipient)), "relayer":format!("0x{}",hex::encode(relayer)), "fee":fee.to_string()
    }))
}

fn prove_one(input: &Path, out: &Path) -> Result<()> {
    fs::create_dir_all(out)?;
    let statement: WithdrawalStatement = read_json(&input.join("statement.json"))?;
    let witness: WithdrawalWitness = read_json(&input.join("witness.json"))?;
    check_witness(statement, &witness)?;
    let parameter = ParameterManifest::profile("sepolia-v0.3").id()?;
    ensure!(parameter == parameter_id()?, "generated parameter ID differs from report");
    let config = withdrawal_config_from_os_entropy(SecurityProfile::SepoliaV03, parameter, statement);
    let started = Instant::now();
    let proof = prove_withdrawal(&config, statement, &witness)?;
    let prove_ms = started.elapsed().as_secs_f64() * 1000.0;
    let verify_started = Instant::now();
    ensure!(verify_withdrawal(&config, statement, &proof), "native verifier rejected new proof");
    let native_verify_ms = verify_started.elapsed().as_secs_f64() * 1000.0;
    let parts = encode_proof_parts(&proof, SecurityProfile::SepoliaV03, parameter, statement)?;
    fs::write(out.join("part-a.pqtc"), &parts.part_a.bytes)?;
    fs::write(out.join("part-b.pqtc"), &parts.part_b.bytes)?;
    fs::copy(input.join("statement.json"), out.join("statement.json"))?;
    fs::copy(input.join("witness.json"), out.join("witness.json"))?;
    fs::copy(input.join("derived-case.json"), out.join("derived-case.json"))?;
    fs::copy(input.join("mapping.json"), out.join("mapping.json"))?;
    fs::copy(input.join("evm.json"), out.join("evm.json"))?;
    let evm: Value = read_json(&input.join("evm.json"))?;
    let pool = parse_hex::<20>(evm["pool_address"].as_str().context("pool_address")?)?;
    let recipient = parse_hex::<20>(evm["recipient"].as_str().context("recipient")?)?;
    let relayer = parse_hex::<20>(evm["relayer"].as_str().context("relayer")?)?;
    let fee: u128 = evm["fee"].as_str().context("fee")?.parse()?;
    let verification_id = verification_id(parts.part_a.proof_id, pool);
    let calldata_a = begin_calldata(statement, recipient, relayer, fee, &parts.part_a.bytes);
    let calldata_b = withdraw_calldata(statement, recipient, relayer, fee, verification_id, &parts.part_b.bytes);
    fs::write(out.join("part-a.calldata"), &calldata_a)?;
    fs::write(out.join("part-b.calldata"), &calldata_b)?;
    let decoded = decode_proof_parts(&parts.part_a.bytes, &parts.part_b.bytes, SecurityProfile::SepoliaV03, parameter, statement)?;
    ensure!(verify_withdrawal(&config, statement, &decoded), "native verifier rejected codec round trip");
    let (zero, nonzero) = zero_nonzero([parts.part_a.bytes.as_slice(),parts.part_b.bytes.as_slice()].concat().as_slice());
    let (calldata_zero, calldata_nonzero) = zero_nonzero([calldata_a.as_slice(),calldata_b.as_slice()].concat().as_slice());
    let statement_bytes = fs::read(out.join("statement.json"))?;
    let witness_bytes = fs::read(out.join("witness.json"))?;
    let derived_bytes = fs::read(out.join("derived-case.json"))?;
    let mapping_bytes = fs::read(out.join("mapping.json"))?;
    let evm_bytes = fs::read(out.join("evm.json"))?;
    write_json(&out.join("proof-metadata.json"), &json!({
        "candidate_id":CANDIDATE_ID,"profile":"sepolia-v0.3","parameter_id":parameter.to_string(),
        "entropy_source":"operating-system entropy through pqtc_stark::withdrawal_config_from_os_entropy; no caller seed",
        "native_verified":true,"codec_roundtrip_verified":true,"prove_ms":prove_ms,"native_verify_ms":native_verify_ms,
        "proof_id":format!("0x{}",hex::encode(parts.part_a.proof_id)),"verification_id":format!("0x{}",hex::encode(verification_id)),
        "statement_key":format!("0x{}",hex::encode(parts.part_a.statement_key)),
        "part_a":artifact_meta(&parts.part_a.bytes),"part_b":artifact_meta(&parts.part_b.bytes),
        "calldata_a":artifact_meta(&calldata_a),"calldata_b":artifact_meta(&calldata_b),
        "statement":artifact_meta(&statement_bytes),"witness":artifact_meta(&witness_bytes),
        "derived_case":artifact_meta(&derived_bytes),"mapping":artifact_meta(&mapping_bytes),"evm_fixture":artifact_meta(&evm_bytes),
        "raw_proof_bytes":parts.part_a.bytes.len()+parts.part_b.bytes.len(),"abi_calldata_bytes":calldata_a.len()+calldata_b.len(),
        "zero_bytes":zero,"nonzero_bytes":nonzero,"calldata_zero_bytes":calldata_zero,"calldata_nonzero_bytes":calldata_nonzero,
        "query_count":parts.part_a.checkpoint.query_indices.len(),"unique_query_indices":parts.part_a.checkpoint.unique_query_indices.len(),
        "query_indices":parts.part_a.checkpoint.query_indices,"unique_query_index_values":parts.part_a.checkpoint.unique_query_indices,
        "frontier_digests":null,"frontier_status":"NOT_EVALUATED: the v0.3 public codec API does not expose split-query pruned-frontier lengths",
        "sections":{"part_a":parts.part_a.bytes.len(),"part_b":parts.part_b.bytes.len()},
        "section_status":"Only whole-part boundaries are exposed by the frozen public codec API; internal section lengths are NOT_EVALUATED"
    }))
}

fn verify_one(input: &Path, proof_dir: &Path) -> Result<()> {
    let statement: WithdrawalStatement = read_json(&input.join("statement.json"))?;
    let parameter = ParameterManifest::profile("sepolia-v0.3").id()?;
    let a = fs::read(proof_dir.join("part-a.pqtc"))?;
    let b = fs::read(proof_dir.join("part-b.pqtc"))?;
    let proof = decode_proof_parts(&a, &b, SecurityProfile::SepoliaV03, parameter, statement)?;
    let config = withdrawal_config_from_os_entropy(SecurityProfile::SepoliaV03, parameter, statement);
    ensure!(verify_withdrawal(&config, statement, &proof), "native proof verification failed");
    println!("valid=true");
    Ok(())
}

fn begin_calldata(statement: WithdrawalStatement, recipient: [u8;20], relayer: [u8;20], fee: u128, proof: &[u8]) -> Vec<u8> {
    let selector = &keccak256(b"beginWithdrawal(((bytes32,bytes32),(bytes32,bytes32),address,address,uint256),bytes)")[..4];
    encode_call(selector, statement, recipient, relayer, fee, None, proof)
}
fn withdraw_calldata(statement: WithdrawalStatement, recipient: [u8;20], relayer: [u8;20], fee: u128, verification_id: [u8;32], proof: &[u8]) -> Vec<u8> {
    let selector = &keccak256(b"withdraw(((bytes32,bytes32),(bytes32,bytes32),address,address,uint256),bytes32,bytes)")[..4];
    encode_call(selector, statement, recipient, relayer, fee, Some(verification_id), proof)
}
fn encode_call(selector: &[u8], statement: WithdrawalStatement, recipient: [u8;20], relayer: [u8;20], fee: u128, id: Option<[u8;32]>, proof: &[u8]) -> Vec<u8> {
    let words = if id.is_some() { 9 } else { 8 };
    let mut out = Vec::with_capacity(4 + words*32 + 32 + proof.len().next_multiple_of(32));
    out.extend_from_slice(selector);
    for digest in [statement.root, statement.nullifier_hash] { out.extend_from_slice(&digest.left); out.extend_from_slice(&digest.right); }
    out.extend_from_slice(&address_word(recipient)); out.extend_from_slice(&address_word(relayer)); out.extend_from_slice(&u256_bytes(fee));
    if let Some(id) = id { out.extend_from_slice(&id); }
    out.extend_from_slice(&u256_bytes((words*32) as u128));
    out.extend_from_slice(&u256_bytes(proof.len() as u128)); out.extend_from_slice(proof);
    out.resize(4 + words*32 + 32 + proof.len().next_multiple_of(32), 0);
    out
}
fn verification_id(proof_id: [u8;32], pool: [u8;20]) -> [u8;32] {
    let mut abi = Vec::with_capacity(96); let mut domain=[0u8;32]; domain[..20].copy_from_slice(b"PQTC.V3.VERIFICATION");
    abi.extend_from_slice(&domain); abi.extend_from_slice(&proof_id); abi.extend_from_slice(&address_word(pool)); keccak256(&abi)
}
fn address_word(address: [u8;20]) -> [u8;32] { let mut out=[0u8;32]; out[12..].copy_from_slice(&address); out }
fn u256_bytes(value: u128) -> [u8;32] { let mut out=[0u8;32]; out[16..].copy_from_slice(&value.to_be_bytes()); out }
fn digest_from_fields(fields: [u32;16]) -> Digest512 { let mut bytes=[0u8;64]; for (v,b) in fields.iter().zip(bytes.chunks_exact_mut(4)) { b.copy_from_slice(&v.to_be_bytes()); } Digest512::from_bytes(bytes) }
fn parameter_id() -> Result<Digest512> { Ok(Digest512::from_bytes(hex::decode(PARAMETER_ID)?.try_into().map_err(|_| anyhow::anyhow!("parameter ID length"))?)) }
fn parse_hex<const N: usize>(value: &str) -> Result<[u8;N]> { let raw=value.strip_prefix("0x").context("hex value lacks 0x prefix")?; let bytes=hex::decode(raw)?; bytes.try_into().map_err(|v:Vec<u8>| anyhow::anyhow!("expected {N} bytes, got {}",v.len())) }
fn write_json(path: &Path, value: &impl Serialize) -> Result<()> { let mut bytes=serde_json::to_vec_pretty(value)?; bytes.push(b'\n'); fs::write(path,bytes)?; Ok(()) }
fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T> { serde_json::from_slice(&fs::read(path)?).with_context(|| format!("parse {}",path.display())) }
fn artifact_meta(bytes: &[u8]) -> Value { json!({"bytes":bytes.len(),"keccak256":hex::encode(keccak256(bytes))}) }
fn zero_nonzero(bytes: &[u8]) -> (usize,usize) { let zero=bytes.iter().filter(|&&b|b==0).count(); (zero,bytes.len()-zero) }
