use std::hint::black_box;
use std::time::Instant;

use p3_baby_bear::{
    BabyBear, default_babybear_poseidon2_16, default_babybear_poseidon2_24,
    default_babybear_poseidon2_32,
};
use p3_field::{PrimeCharacteristicRing, PrimeField32};
use p3_mersenne_31::Mersenne31;
use p3_rescue::RpoMersenne31;
use p3_symmetric::Permutation;
use serde::{Deserialize, Serialize};
use sha2::{Digest as _, Sha256};
use sha3::Keccak256;

pub const BABYBEAR_MODULUS: u32 = 2_013_265_921;
pub const M31_MODULUS: u32 = 2_147_483_647;
pub const PROTOCOL_VERSION: u32 = 1;
pub const TREE_DEPTH: usize = 20;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub enum Candidate {
    H0,
    H1,
    H2,
    H3,
    H4,
    H5,
    H6,
    H7,
}

impl Candidate {
    pub const EXECUTABLE: [Self; 7] = [Self::H0, Self::H1, Self::H3, Self::H4, Self::H5, Self::H6, Self::H7];

    pub const fn id(self) -> &'static str {
        match self {
            Self::H0 => "H0", Self::H1 => "H1", Self::H2 => "H2", Self::H3 => "H3",
            Self::H4 => "H4", Self::H5 => "H5", Self::H6 => "H6", Self::H7 => "H7",
        }
    }

    pub const fn width(self) -> usize {
        match self { Self::H0 | Self::H1 | Self::H2 => 16, Self::H3 | Self::H4 | Self::H7 => 24, Self::H5 | Self::H6 => 32 }
    }

    pub const fn output_len(self) -> usize {
        match self { Self::H0 | Self::H7 => 16, Self::H1 => 7, Self::H2 | Self::H3 => 10, Self::H4 => 11, Self::H5 => 12, Self::H6 => 14 }
    }

    pub const fn modulus(self) -> u32 {
        if matches!(self, Self::H7) { M31_MODULUS } else { BABYBEAR_MODULUS }
    }

    pub const fn application_enabled(self) -> bool {
        matches!(self, Self::H0 | Self::H3 | Self::H5 | Self::H6 | Self::H7)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[repr(u32)]
pub enum Role { Primitive = 1, Note = 2, Nullifier = 3, Node = 4 }

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MappingAttempt {
    pub element: usize,
    pub counter: u32,
    pub draw: String,
    pub value: u32,
    pub accepted: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MappingRecord {
    pub algorithm: &'static str,
    pub modulus: u32,
    pub attempts: Vec<MappingAttempt>,
    pub failure: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Vector {
    pub vector_id: String,
    pub candidate: Candidate,
    pub kind: String,
    pub role: Role,
    pub width: usize,
    pub output_len: usize,
    pub input: Vec<u32>,
    pub output: Vec<u32>,
    pub output_be_hex: String,
    pub sha256: String,
    pub ethereum_keccak256: String,
    pub controls: [u32; 4],
    pub mutation: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct TreeParity {
    pub candidate: Candidate,
    pub case_id: String,
    pub leaf_index: u32,
    pub root_iterative: Vec<u32>,
    pub root_direct: Vec<u32>,
    pub equal: bool,
    pub node_permutations: usize,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Distribution {
    pub candidate: Candidate,
    pub operation: String,
    pub samples: usize,
    pub min_ns: u128,
    pub median_ns: u128,
    pub p95_ns: u128,
    pub max_ns: u128,
    pub mean_ns: u128,
    pub raw_ns: Vec<u128>,
}

pub const fn controls(role: Role, shape: u32, level: u32) -> [u32; 4] {
    [role as u32, PROTOCOL_VERSION, shape, level]
}

pub fn digest_bytes(elements: &[u32]) -> Vec<u8> {
    elements.iter().flat_map(|x| x.to_be_bytes()).collect()
}

pub fn digest_metadata(elements: &[u32]) -> (String, String, String) {
    let bytes = digest_bytes(elements);
    let hex = hex::encode(&bytes);
    let sha = hex::encode(Sha256::digest(&bytes));
    let keccak = hex::encode(Keccak256::digest(&bytes));
    (hex, sha, keccak)
}

pub fn map_bytes(label: &str, source: &[u8], count: usize, modulus: u32) -> (Vec<u32>, MappingRecord) {
    let mut values = Vec::with_capacity(count);
    let mut attempts = Vec::new();
    for element in 0..count {
        let mut accepted = None;
        for counter in 0..=u16::MAX as u32 {
            let mut h = Sha256::new();
            h.update(b"PQT-SP10-H2F-RS-v1");
            h.update((label.len() as u32).to_be_bytes());
            h.update(label.as_bytes());
            h.update((source.len() as u32).to_be_bytes());
            h.update(source);
            h.update((element as u32).to_be_bytes());
            h.update(counter.to_be_bytes());
            let draw: [u8; 32] = h.finalize().into();
            let value = u32::from_be_bytes(draw[..4].try_into().expect("four bytes"));
            let ok = value < modulus;
            attempts.push(MappingAttempt { element, counter, draw: hex::encode(draw), value, accepted: ok });
            if ok { accepted = Some(value); break; }
        }
        match accepted {
            Some(value) => values.push(value),
            None => return (values, MappingRecord {
                algorithm: "sha256-counter-v1/first-u32-be/reject-if-value>=modulus",
                modulus, attempts,
                failure: Some(format!("no canonical draw for element {element} after 65536 attempts")),
            }),
        }
    }
    (values, MappingRecord {
        algorithm: "sha256-counter-v1/first-u32-be/reject-if-value>=modulus",
        modulus, attempts, failure: None,
    })
}

pub fn map_supplied_draws(draws: &[Vec<u8>], modulus: u32) -> (Option<u32>, MappingRecord) {
    let mut attempts = Vec::with_capacity(draws.len());
    for (counter, draw) in draws.iter().enumerate() {
        if draw.len() != 32 {
            return (None, MappingRecord { algorithm: "supplied-draw/first-u32-be/reject-if-value>=modulus", modulus, attempts, failure: Some(format!("draw {counter} has length {}, expected 32", draw.len())) });
        }
        let value = u32::from_be_bytes(draw[..4].try_into().expect("four bytes"));
        let accepted = value < modulus;
        attempts.push(MappingAttempt { element: 0, counter: counter as u32, draw: hex::encode(draw), value, accepted });
        if accepted {
            return (Some(value), MappingRecord { algorithm: "supplied-draw/first-u32-be/reject-if-value>=modulus", modulus, attempts, failure: None });
        }
    }
    (None, MappingRecord { algorithm: "supplied-draw/first-u32-be/reject-if-value>=modulus", modulus, attempts, failure: Some("all supplied draws were non-canonical".into()) })
}

fn babybear_array<const W: usize>(input: &[u32]) -> [BabyBear; W] {
    assert_eq!(input.len(), W);
    core::array::from_fn(|i| { assert!(input[i] < BABYBEAR_MODULUS); BabyBear::new(input[i]) })
}

fn babybear_values<const W: usize>(state: &[BabyBear; W]) -> Vec<u32> {
    state.iter().map(PrimeField32::as_canonical_u32).collect()
}

pub fn poseidon_permute(candidate: Candidate, input: &[u32]) -> Vec<u32> {
    match candidate.width() {
        16 => { let mut s = babybear_array::<16>(input); default_babybear_poseidon2_16().permute_mut(&mut s); babybear_values(&s) }
        24 => { let mut s = babybear_array::<24>(input); default_babybear_poseidon2_24().permute_mut(&mut s); babybear_values(&s) }
        32 => { let mut s = babybear_array::<32>(input); default_babybear_poseidon2_32().permute_mut(&mut s); babybear_values(&s) }
        _ => unreachable!(),
    }
}

pub fn poseidon_compress(candidate: Candidate, input: &[u32]) -> Vec<u32> {
    assert!(matches!(candidate, Candidate::H1 | Candidate::H3 | Candidate::H4 | Candidate::H5 | Candidate::H6));
    assert_eq!(input.len(), candidate.width());
    let permuted = poseidon_permute(candidate, input);
    (0..candidate.output_len()).map(|i| ((permuted[i] as u64 + input[i] as u64) % BABYBEAR_MODULUS as u64) as u32).collect()
}

pub fn p2bb512(role: Role, level: u32, payload: &[u32]) -> Vec<u32> {
    assert!(payload.iter().all(|x| *x < BABYBEAR_MODULUS));
    let mut state = [BabyBear::ZERO; 16];
    state[4] = BabyBear::new(PROTOCOL_VERSION);
    let tag = match role { Role::Primitive => 1, Role::Note => 0x11, Role::Nullifier => 0x12, Role::Node => 0x20 };
    state[5] = BabyBear::new(tag);
    state[6] = BabyBear::new((payload.len() as u32) * 4);
    state[7] = BabyBear::new(payload.len() as u32);
    state[8] = BabyBear::new(level);
    let permutation = default_babybear_poseidon2_16();
    if payload.is_empty() { permutation.permute_mut(&mut state); }
    else {
        for block in payload.chunks(4) {
            for (lane, value) in state[..4].iter_mut().zip(block) { *lane += BabyBear::new(*value); }
            permutation.permute_mut(&mut state);
        }
    }
    let mut output = Vec::with_capacity(16);
    for block in 0..4 {
        if block != 0 { permutation.permute_mut(&mut state); }
        output.extend(state[..4].iter().map(PrimeField32::as_canonical_u32));
    }
    output
}

pub fn rpo_m31_sponge(message: &[u32]) -> Vec<u32> {
    assert!(!message.is_empty(), "published 16-domain padding requires a non-empty final block");
    assert!(message.iter().all(|x| *x < M31_MODULUS));
    let final_len = ((message.len() - 1) % 16) + 1;
    let mut state = [Mersenne31::ZERO; 24];
    state[16] = Mersenne31::from_u32((16 - final_len) as u32);
    let permutation = RpoMersenne31::from_standard_constants();
    for block in message.chunks(16) {
        for (lane, value) in state[..16].iter_mut().zip(block) { *lane += Mersenne31::from_u32(*value); }
        permutation.permute_mut(&mut state);
    }
    state[..16].iter().map(PrimeField32::as_canonical_u32).collect()
}

pub fn primitive(candidate: Candidate, input: &[u32]) -> Vec<u32> {
    match candidate {
        Candidate::H0 => p2bb512(Role::Primitive, 0, input),
        Candidate::H1 | Candidate::H3 | Candidate::H4 | Candidate::H5 | Candidate::H6 => poseidon_compress(candidate, input),
        Candidate::H7 => rpo_m31_sponge(input),
        Candidate::H2 => panic!("H2 is a documented no-code stop"),
    }
}

pub fn application_hash(candidate: Candidate, role: Role, level: u32, payload: &[u32]) -> Vec<u32> {
    assert!(candidate.application_enabled());
    let shape = payload.len() as u32;
    match candidate {
        Candidate::H0 => p2bb512(role, level, payload),
        Candidate::H3 | Candidate::H5 | Candidate::H6 => {
            assert_eq!(payload.len(), 2 * candidate.output_len());
            let mut state = vec![0u32; candidate.width()];
            state[..payload.len()].copy_from_slice(payload);
            state[payload.len()..payload.len() + 4].copy_from_slice(&controls(role, shape, level));
            poseidon_compress(candidate, &state)
        }
        Candidate::H7 => {
            let mut message = controls(role, shape, level).to_vec();
            message.extend_from_slice(payload);
            rpo_m31_sponge(&message)
        }
        _ => panic!("application role is stopped for this candidate"),
    }
}

pub fn root_iterative(candidate: Candidate, leaf_index: u32, leaf: &[u32], siblings: &[Vec<u32>]) -> Vec<u32> {
    assert_eq!(siblings.len(), TREE_DEPTH);
    let mut node = leaf.to_vec();
    for (level, sibling) in siblings.iter().enumerate() {
        let mut payload = Vec::with_capacity(node.len() * 2);
        if ((leaf_index >> level) & 1) == 0 { payload.extend_from_slice(&node); payload.extend_from_slice(sibling); }
        else { payload.extend_from_slice(sibling); payload.extend_from_slice(&node); }
        node = application_hash(candidate, Role::Node, level as u32, &payload);
    }
    node
}

fn root_direct_inner(candidate: Candidate, leaf_index: u32, level: usize, node: &[u32], siblings: &[Vec<u32>]) -> Vec<u32> {
    if level == TREE_DEPTH { return node.to_vec(); }
    let mut payload = Vec::with_capacity(node.len() * 2);
    if ((leaf_index >> level) & 1) == 0 { payload.extend_from_slice(node); payload.extend_from_slice(&siblings[level]); }
    else { payload.extend_from_slice(&siblings[level]); payload.extend_from_slice(node); }
    let parent = application_hash(candidate, Role::Node, level as u32, &payload);
    root_direct_inner(candidate, leaf_index, level + 1, &parent, siblings)
}

pub fn root_direct(candidate: Candidate, leaf_index: u32, leaf: &[u32], siblings: &[Vec<u32>]) -> Vec<u32> {
    assert_eq!(siblings.len(), TREE_DEPTH);
    root_direct_inner(candidate, leaf_index, 0, leaf, siblings)
}

pub fn make_vector(id: String, candidate: Candidate, kind: &str, role: Role, input: Vec<u32>, output: Vec<u32>, controls: [u32; 4], mutation: &str) -> Vector {
    let (output_be_hex, sha256, ethereum_keccak256) = digest_metadata(&output);
    Vector { vector_id: id, candidate, kind: kind.into(), role, width: candidate.width(), output_len: candidate.output_len(), input, output, output_be_hex, sha256, ethereum_keccak256, controls, mutation: mutation.into() }
}

fn measure(candidate: Candidate, operation: &str, samples: usize, mut operation_call: impl FnMut() -> Vec<u32>) -> Distribution {
    assert!(samples > 0);
    let mut raw = Vec::with_capacity(samples);
    for _ in 0..samples {
        let started = Instant::now();
        black_box(operation_call());
        raw.push(started.elapsed().as_nanos());
    }
    raw.sort_unstable();
    let mean_ns = raw.iter().sum::<u128>() / samples as u128;
    Distribution { candidate, operation: operation.into(), samples, min_ns: raw[0], median_ns: raw[samples / 2], p95_ns: raw[(samples * 95 / 100).min(samples - 1)], max_ns: raw[samples - 1], mean_ns, raw_ns: raw }
}

pub fn benchmark(candidate: Candidate, samples: usize) -> Distribution {
    let modulus = candidate.modulus();
    let input_len = if matches!(candidate, Candidate::H0) { 32 } else if matches!(candidate, Candidate::H7) { 36 } else { candidate.width() };
    let input: Vec<u32> = (0..input_len).map(|i| ((i as u64 * 65_537 + 17) % modulus as u64) as u32).collect();
    measure(candidate, "primitive", samples, || primitive(candidate, black_box(&input)))
}

pub fn benchmark_application(candidate: Candidate, role: Role, samples: usize) -> Distribution {
    assert!(candidate.application_enabled());
    let payload_len = match (candidate, role) {
        (Candidate::H0, Role::Nullifier) => 24,
        (Candidate::H0, Role::Note | Role::Node) => 32,
        (_, Role::Note | Role::Nullifier | Role::Node) => 2 * candidate.output_len(),
        (_, Role::Primitive) => panic!("primitive uses benchmark()"),
    };
    let modulus = candidate.modulus();
    let payload: Vec<u32> = (0..payload_len).map(|i| ((i as u64 * 65_537 + 17) % modulus as u64) as u32).collect();
    let operation = match role { Role::Note => "note", Role::Nullifier => "nullifier", Role::Node => "node", Role::Primitive => unreachable!() };
    measure(candidate, operation, samples, || application_hash(candidate, role, if role == Role::Node { 7 } else { 0 }, black_box(&payload)))
}
