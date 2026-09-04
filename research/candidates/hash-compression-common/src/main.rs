use std::env;
use std::fs;
use std::io::Read;
use std::path::Path;

use serde::{Deserialize, Serialize};
use sha2::{Digest as _, Sha256};
use sha3::Keccak256;
use sp10_hash_research::{
    Candidate, MappingRecord, Role, TREE_DEPTH, TreeParity, Vector, application_hash, benchmark,
    benchmark_application, controls, make_vector, map_bytes, map_supplied_draws, primitive, root_direct, root_iterative,
};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Corpus { cases: Vec<Case> }

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Case {
    case_id: String,
    leaf_index: u32,
    nullifier_secret_bytes: String,
    trapdoor_bytes: String,
    pool_address: String,
    sibling_seeds: Vec<String>,
    generation_metadata: GenerationMetadata,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase")]
struct GenerationMetadata { rejection_sampling_trigger: Option<RejectionTrigger> }

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RejectionTrigger { target_field: String, draws: Vec<String> }

#[derive(Debug, Serialize)]
struct MappingEvidence {
    candidate: Candidate,
    case_id: String,
    source: String,
    record: MappingRecord,
}

#[derive(Debug, Serialize)]
struct VectorBundle {
    schema: &'static str,
    generator: &'static str,
    source_corpus_sha256: String,
    vector_count: usize,
    mapping_record_count: usize,
    vectors: Vec<Vector>,
    mappings: Vec<MappingEvidence>,
    tree_parity: Vec<TreeParity>,
}

fn decode_hex(value: &str) -> Result<Vec<u8>, String> {
    hex::decode(value.strip_prefix("0x").unwrap_or(value)).map_err(|e| e.to_string())
}

fn deterministic_input(candidate: Candidate, index: usize) -> Vec<u32> {
    let len = match candidate { Candidate::H0 => 32, Candidate::H7 => 36, _ => candidate.width() };
    let label = format!("{}-primitive-{index}", candidate.id());
    map_bytes(&label, label.as_bytes(), len, candidate.modulus()).0
}

fn candidate_controls(candidate: Candidate, role: Role, shape: u32, level: u32) -> [u32; 4] {
    let mut result = controls(role, shape, level);
    if candidate == Candidate::H0 {
        result[0] = match role { Role::Primitive => 1, Role::Note => 0x11, Role::Nullifier => 0x12, Role::Node => 0x20 };
    }
    result
}

fn mutate(candidate: Candidate, index: usize, mut input: Vec<u32>) -> (Vec<u32>, &'static str, Role, u32) {
    let modulus = candidate.modulus();
    let output_len = candidate.output_len();
    match index % 8 {
        0 => { input[0] = 0; (input, "canonical-boundary-zero", Role::Primitive, 0) }
        1 => { input[0] = 1; (input, "canonical-boundary-one", Role::Primitive, 0) }
        2 => { input[0] = modulus - 1; (input, "canonical-boundary-p-minus-one", Role::Primitive, 0) }
        3 => {
            let lane = input.len() - 4; input[lane] = Role::Note as u32;
            (input, "domain-role-mutation", Role::Note, 0)
        }
        4 => {
            let lane = input.len() - 1; input[lane] = 19;
            (input, "level-mutation", Role::Primitive, 19)
        }
        5 => {
            if input.len() >= output_len * 2 { for i in 0..output_len { input.swap(i, output_len + i); } }
            (input, "left-right-mutation", Role::Primitive, 0)
        }
        6 => {
            let lane = input.len().saturating_sub(3); input[lane] = 2;
            (input, "version-mutation", Role::Primitive, 0)
        }
        _ => {
            let lane = input.len().saturating_sub(2); input[lane] = input[lane].wrapping_add(1) % modulus;
            (input, "shape-mutation", Role::Primitive, 0)
        }
    }
}

fn primitive_vectors() -> Vec<Vector> {
    let mut vectors = Vec::with_capacity(Candidate::EXECUTABLE.len() * 2048);
    for candidate in Candidate::EXECUTABLE {
        for index in 0..2048 {
            let base = deterministic_input(candidate, index);
            let (input, mutation, role, level) = mutate(candidate, index, base);
            let vector_controls = candidate_controls(candidate, role, input.len() as u32, level);
            let output = match candidate {
                Candidate::H0 => sp10_hash_research::p2bb512(role, level, &input),
                Candidate::H7 => {
                    let mut message = controls(role, input.len() as u32, level).to_vec();
                    message.extend_from_slice(&input);
                    sp10_hash_research::rpo_m31_sponge(&message)
                }
                _ => primitive(candidate, &input),
            };
            vectors.push(make_vector(
                format!("{}-primitive-{index:04}", candidate.id()), candidate, "primitive", role,
                input, output, vector_controls, mutation,
            ));
        }
    }
    vectors
}

fn candidate_case_material(candidate: Candidate, case: &Case, mappings: &mut Vec<MappingEvidence>) -> Result<Option<(Vec<u32>, Vec<u32>, Vec<u32>, Vec<Vec<u32>>)>, String> {
    let digest_count = candidate.output_len();
    let secret_count = if candidate == Candidate::H0 { 8 } else { digest_count };
    let ns_bytes = decode_hex(&case.nullifier_secret_bytes)?;
    let tp_bytes = decode_hex(&case.trapdoor_bytes)?;
    let pool_bytes = decode_hex(&case.pool_address)?;
    let (mut ns, ns_record) = map_bytes("nullifier-secret", &ns_bytes, secret_count, candidate.modulus());
    let (mut tp, tp_record) = map_bytes("trapdoor", &tp_bytes, secret_count, candidate.modulus());
    let (scope, scope_record) = map_bytes("pool-scope", &pool_bytes, digest_count, candidate.modulus());
    mappings.push(MappingEvidence { candidate, case_id: case.case_id.clone(), source: "nullifierSecretBytes".into(), record: ns_record });
    mappings.push(MappingEvidence { candidate, case_id: case.case_id.clone(), source: "trapdoorBytes".into(), record: tp_record });
    mappings.push(MappingEvidence { candidate, case_id: case.case_id.clone(), source: "poolAddress".into(), record: scope_record });
    if let Some(trigger) = &case.generation_metadata.rejection_sampling_trigger {
        let draws = trigger.draws.iter().map(|x| decode_hex(x)).collect::<Result<Vec<_>, _>>()?;
        let (accepted, record) = map_supplied_draws(&draws, candidate.modulus());
        mappings.push(MappingEvidence { candidate, case_id: case.case_id.clone(), source: format!("trigger:{}", trigger.target_field), record });
        let Some(value) = accepted else { return Ok(None); };
        match trigger.target_field.as_str() {
            "nullifierSecretBytes" => ns[0] = value,
            "trapdoorBytes" => tp[0] = value,
            other => return Err(format!("unsupported rejection-sampling target {other}")),
        }
    }
    let mut siblings = Vec::with_capacity(TREE_DEPTH);
    for (level, seed) in case.sibling_seeds.iter().enumerate() {
        let bytes = decode_hex(seed)?;
        let (mapped, record) = map_bytes(&format!("sibling-{level}"), &bytes, digest_count, candidate.modulus());
        mappings.push(MappingEvidence { candidate, case_id: case.case_id.clone(), source: format!("siblingSeeds[{level}]"), record });
        siblings.push(mapped);
    }
    Ok(Some((ns, tp, scope, siblings)))
}

fn application_vectors(corpus: &Corpus, vectors: &mut Vec<Vector>, mappings: &mut Vec<MappingEvidence>, trees: &mut Vec<TreeParity>) -> Result<(), String> {
    for candidate in [Candidate::H0, Candidate::H3, Candidate::H5, Candidate::H6, Candidate::H7] {
        for case in &corpus.cases {
            let Some((ns, tp, scope, siblings)) = candidate_case_material(candidate, case, mappings)? else { continue; };
            let note_payload = if candidate == Candidate::H0 {
                [scope.clone(), ns.clone(), tp].concat()
            } else {
                [ns.clone(), tp].concat()
            };
            let note = application_hash(candidate, Role::Note, 0, &note_payload);
            vectors.push(make_vector(format!("{}-{}-note", candidate.id(), case.case_id), candidate, "application", Role::Note, note_payload.clone(), note.clone(), candidate_controls(candidate, Role::Note, note_payload.len() as u32, 0), "none"));
            let nullifier_payload = [scope, ns].concat();
            let nullifier = application_hash(candidate, Role::Nullifier, 0, &nullifier_payload);
            vectors.push(make_vector(format!("{}-{}-nullifier", candidate.id(), case.case_id), candidate, "application", Role::Nullifier, nullifier_payload.clone(), nullifier, candidate_controls(candidate, Role::Nullifier, nullifier_payload.len() as u32, 0), "none"));
            let root_a = root_iterative(candidate, case.leaf_index, &note, &siblings);
            let root_b = root_direct(candidate, case.leaf_index, &note, &siblings);
            trees.push(TreeParity { candidate, case_id: case.case_id.clone(), leaf_index: case.leaf_index, root_iterative: root_a.clone(), root_direct: root_b.clone(), equal: root_a == root_b, node_permutations: TREE_DEPTH });
            let mut first_node = if case.leaf_index & 1 == 0 { note.clone() } else { siblings[0].clone() };
            if case.leaf_index & 1 == 0 { first_node.extend_from_slice(&siblings[0]); } else { first_node.extend_from_slice(&note); }
            vectors.push(make_vector(format!("{}-{}-node-l0", candidate.id(), case.case_id), candidate, "application", Role::Node, first_node, application_hash(candidate, Role::Node, 0, &if case.leaf_index & 1 == 0 { [note, siblings[0].clone()].concat() } else { [siblings[0].clone(), note].concat() }), candidate_controls(candidate, Role::Node, (2 * candidate.output_len()) as u32, 0), "left-right-canonical"));
        }
    }
    Ok(())
}

fn vectors(corpus_path: &Path, output_path: &Path) -> Result<(), String> {
    let bytes = fs::read(corpus_path).map_err(|e| e.to_string())?;
    let corpus: Corpus = serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
    let mut all_vectors = primitive_vectors();
    let mut mappings = Vec::new();
    let mut tree_parity = Vec::new();
    application_vectors(&corpus, &mut all_vectors, &mut mappings, &mut tree_parity)?;
    if all_vectors.len() < 10_000 { return Err(format!("only {} vectors generated", all_vectors.len())); }
    if tree_parity.iter().any(|x| !x.equal) { return Err("tree parity failure".into()); }
    let bundle = VectorBundle {
        schema: "pqtc-sp10-cross-language-v1",
        generator: "sp10-hash-research@0.1.0",
        source_corpus_sha256: hex::encode(Sha256::digest(&bytes)),
        vector_count: all_vectors.len(), mapping_record_count: mappings.len(),
        vectors: all_vectors, mappings, tree_parity,
    };
    if let Some(parent) = output_path.parent() { fs::create_dir_all(parent).map_err(|e| e.to_string())?; }
    fs::write(output_path, serde_json::to_vec_pretty(&bundle).map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
    println!("generated {} vectors and {} depth-20 parity cases", bundle.vector_count, bundle.tree_parity.len());
    Ok(())
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct NativeDiagnosticBundle<T> {
    schema: &'static str,
    classification: &'static str,
    comparable_common_protocol_benchmark: bool,
    protocol_gaps: [&'static str; 5],
    distributions: Vec<T>,
}

fn benches(output_path: &Path, samples: usize) -> Result<(), String> {
    let mut results = Vec::new();
    for candidate in Candidate::EXECUTABLE {
        results.push(benchmark(candidate, samples));
        if candidate.application_enabled() {
            for role in [Role::Note, Role::Nullifier, Role::Node] {
                results.push(benchmark_application(candidate, role, samples));
            }
        }
    }
    if let Some(parent) = output_path.parent() { fs::create_dir_all(parent).map_err(|e| e.to_string())?; }
    let bundle = NativeDiagnosticBundle {
        schema: "sp10-native-diagnostic-v2",
        classification: "DIAGNOSTIC_NOT_COMMON_PROTOCOL",
        comparable_common_protocol_benchmark: false,
        protocol_gaps: [
            "no warmup phase",
            "p90 not recorded",
            "p99 not recorded",
            "standard deviation not recorded",
            "less than 10 seconds of measured work",
        ],
        distributions: results,
    };
    fs::write(output_path, serde_json::to_vec_pretty(&bundle).map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
    println!("measured {} diagnostic operation distributions with {} samples each", bundle.distributions.len(), samples);
    Ok(())
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct ArtifactHash {
    path: String,
    bytes: u64,
    sha256: String,
    ethereum_keccak256: String,
}

fn hash_outputs(output_path: &Path, inputs: &[String]) -> Result<(), String> {
    let mut records = Vec::with_capacity(inputs.len());
    for input in inputs {
        let mut file = fs::File::open(input).map_err(|e| e.to_string())?;
        let mut sha = Sha256::new();
        let mut keccak = Keccak256::new();
        let mut bytes = 0u64;
        let mut buffer = vec![0u8; 1024 * 1024];
        loop {
            let count = file.read(&mut buffer).map_err(|e| e.to_string())?;
            if count == 0 { break; }
            sha.update(&buffer[..count]);
            keccak.update(&buffer[..count]);
            bytes += count as u64;
        }
        records.push(ArtifactHash {
            path: input.clone(),
            bytes,
            sha256: hex::encode(sha.finalize()),
            ethereum_keccak256: hex::encode(keccak.finalize()),
        });
    }
    fs::write(output_path, serde_json::to_vec_pretty(&records).map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
    println!("hashed {} artifacts", records.len());
    Ok(())
}

fn usage() -> String {
    "usage: sp10-hash-research vectors <semantic-cases.json> <output.json> | bench <output.json> [samples] | hash <output.json> <inputs...>".into()
}

fn run() -> Result<(), String> {
    let args = env::args().collect::<Vec<_>>();
    match args.get(1).map(String::as_str) {
        Some("vectors") if args.len() == 4 => vectors(Path::new(&args[2]), Path::new(&args[3])),
        Some("bench") if (3..=4).contains(&args.len()) => benches(Path::new(&args[2]), args.get(3).map_or(Ok(1000), |x| x.parse::<usize>().map_err(|e| e.to_string()))?),
        Some("hash") if args.len() >= 4 => hash_outputs(Path::new(&args[2]), &args[3..]),
        _ => Err(usage()),
    }
}

fn main() { if let Err(error) = run() { eprintln!("{error}"); std::process::exit(2); } }
