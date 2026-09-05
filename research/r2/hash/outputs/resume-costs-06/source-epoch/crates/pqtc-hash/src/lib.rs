//! Poseidon2/BabyBear application hashes, proof-only Keccak hashes, and the versioned note codec.

use std::sync::LazyLock;

use base64::{Engine as _, engine::general_purpose::URL_SAFE_NO_PAD};
use p3_baby_bear::{BabyBear, Poseidon2BabyBear, default_babybear_poseidon2_16};
use p3_field::{PrimeCharacteristicRing, PrimeField32, integers::QuotientMap};
use p3_symmetric::Permutation;
use pqtc_spec::{
    CanonicalError, CanonicalSecret, Digest512, ScopeInput, WithdrawalStatement, domains,
};
use rand::{CryptoRng, Rng};
use sha3::{Digest as _, Keccak256};
use thiserror::Error;

pub const NOTE_PREFIX: &str = "pqtc-note-v3:";
const NOTE_MAGIC: [u8; 4] = *b"PQTN";
const NOTE_VERSION: u16 = 3;
const NOTE_BODY_LEN: usize = 162;
const NOTE_BINARY_LEN: usize = NOTE_BODY_LEN + 32;
const P2BB512_WIDTH: usize = 16;
const P2BB512_RATE: usize = 4;
const P2BB512_VERSION: u32 = 1;

static P2BB512_PERMUTATION: LazyLock<Poseidon2BabyBear<P2BB512_WIDTH>> =
    LazyLock::new(default_babybear_poseidon2_16);

#[must_use]
pub fn keccak256(bytes: &[u8]) -> [u8; 32] {
    Keccak256::digest(bytes).into()
}

#[must_use]
pub fn k512(tag: u8, payload: &[u8]) -> Digest512 {
    let mut left = Keccak256::new();
    left.update([0, tag]);
    left.update(payload);
    let mut right = Keccak256::new();
    right.update([1, tag]);
    right.update(payload);
    Digest512 {
        left: left.finalize().into(),
        right: right.finalize().into(),
    }
}

/// Hashes canonical field elements with the protocol P2BB512 sponge.
///
/// # Panics
///
/// Panics when a framing value is not canonical in the `BabyBear` field or
/// when the payload length exceeds `u32::MAX`.
#[must_use]
pub fn p2bb512(tag: u8, payload_byte_length: u32, aux: u32, payload: &[BabyBear]) -> Digest512 {
    let payload_element_count =
        u32::try_from(payload.len()).expect("P2BB512 payload element count exceeds u32");
    let mut state = [BabyBear::ZERO; P2BB512_WIDTH];
    state[P2BB512_RATE] = BabyBear::new(P2BB512_VERSION);
    state[P2BB512_RATE + 1] = BabyBear::new(u32::from(tag));
    state[P2BB512_RATE + 2] = BabyBear::from_canonical_checked(payload_byte_length)
        .expect("P2BB512 payload byte length is not canonical BabyBear");
    state[P2BB512_RATE + 3] = BabyBear::from_canonical_checked(payload_element_count)
        .expect("P2BB512 payload element count is not canonical BabyBear");
    state[P2BB512_RATE + 4] =
        BabyBear::from_canonical_checked(aux).expect("P2BB512 aux is not canonical BabyBear");

    if payload.is_empty() {
        P2BB512_PERMUTATION.permute_mut(&mut state);
    } else {
        for block in payload.chunks(P2BB512_RATE) {
            for (rate, &element) in state[..P2BB512_RATE].iter_mut().zip(block) {
                *rate += element;
            }
            P2BB512_PERMUTATION.permute_mut(&mut state);
        }
    }

    let mut output = [BabyBear::ZERO; P2BB512_WIDTH];
    for block_index in 0..(P2BB512_WIDTH / P2BB512_RATE) {
        if block_index != 0 {
            P2BB512_PERMUTATION.permute_mut(&mut state);
        }
        let start = block_index * P2BB512_RATE;
        output[start..start + P2BB512_RATE].copy_from_slice(&state[..P2BB512_RATE]);
    }
    elements_to_digest(output)
}

#[must_use]
pub fn digest_to_elements(digest: Digest512) -> Option<[BabyBear; P2BB512_WIDTH]> {
    let bytes = digest.to_bytes();
    let mut elements = [BabyBear::ZERO; P2BB512_WIDTH];
    for (element, bytes) in elements.iter_mut().zip(bytes.chunks_exact(4)) {
        let [a, b, c, d] = bytes else {
            unreachable!("chunks_exact(4) only yields four-byte chunks");
        };
        let value = u32::from_be_bytes([*a, *b, *c, *d]);
        *element = BabyBear::from_canonical_checked(value)?;
    }
    Some(elements)
}

#[must_use]
pub fn elements_to_digest(elements: [BabyBear; P2BB512_WIDTH]) -> Digest512 {
    let mut bytes = [0u8; 64];
    for (&element, output) in elements.iter().zip(bytes.chunks_exact_mut(4)) {
        output.copy_from_slice(&element.as_canonical_u32().to_be_bytes());
    }
    Digest512::from_bytes(bytes)
}

fn encode_bytes(bytes: &[u8], output: &mut [BabyBear]) {
    assert_eq!(output.len(), bytes.len().div_ceil(2));
    for (chunk, element) in bytes.chunks(2).zip(output) {
        let value = u16::from_be_bytes([chunk[0], chunk.get(1).copied().unwrap_or(0)]);
        *element = BabyBear::new(u32::from(value));
    }
}

fn canonical_digest(digest: Digest512) -> [BabyBear; P2BB512_WIDTH] {
    digest_to_elements(digest).expect("P2BB512 digest contains a noncanonical BabyBear element")
}

fn secret_elements(secret: CanonicalSecret) -> [BabyBear; CanonicalSecret::LIMB_COUNT] {
    secret.into_limbs().map(BabyBear::new)
}

#[must_use]
pub fn scope(input: ScopeInput) -> Digest512 {
    let encoded = input.encode();
    let mut payload = [BabyBear::ZERO; 65];
    encode_bytes(&encoded, &mut payload);
    p2bb512(domains::SCOPE, 129, 0, &payload)
}

#[must_use]
pub fn commitment(
    scope: Digest512,
    nullifier_secret: CanonicalSecret,
    trapdoor: CanonicalSecret,
) -> Digest512 {
    let mut payload = [BabyBear::ZERO; 32];
    payload[..16].copy_from_slice(&canonical_digest(scope));
    payload[16..24].copy_from_slice(&secret_elements(nullifier_secret));
    payload[24..].copy_from_slice(&secret_elements(trapdoor));
    p2bb512(domains::NOTE, 128, 0, &payload)
}

#[must_use]
pub fn nullifier_hash(scope: Digest512, nullifier_secret: CanonicalSecret) -> Digest512 {
    let mut payload = [BabyBear::ZERO; 24];
    payload[..16].copy_from_slice(&canonical_digest(scope));
    payload[16..].copy_from_slice(&secret_elements(nullifier_secret));
    p2bb512(domains::NULLIFIER, 96, 0, &payload)
}

#[must_use]
pub fn empty_leaf(scope: Digest512) -> Digest512 {
    let payload = canonical_digest(scope);
    p2bb512(domains::EMPTY_LEAF, 64, 0, &payload)
}

#[must_use]
pub fn merkle_node(level: u8, left: Digest512, right: Digest512) -> Digest512 {
    let mut payload = [BabyBear::ZERO; 32];
    payload[..16].copy_from_slice(&canonical_digest(left));
    payload[16..].copy_from_slice(&canonical_digest(right));
    p2bb512(domains::APP_MERKLE_NODE, 128, u32::from(level), &payload)
}

#[must_use]
pub fn payout_digest(recipient: [u8; 20], relayer: [u8; 20], fee: [u8; 32]) -> Digest512 {
    let mut encoded = [0u8; 72];
    encoded[..20].copy_from_slice(&recipient);
    encoded[20..40].copy_from_slice(&relayer);
    encoded[40..].copy_from_slice(&fee);
    let mut payload = [BabyBear::ZERO; 36];
    encode_bytes(&encoded, &mut payload);
    p2bb512(domains::PAYOUT, 72, 0, &payload)
}

#[must_use]
pub fn statement_hash(statement: WithdrawalStatement) -> Digest512 {
    let mut payload = [BabyBear::ZERO; 64];
    for (output, digest) in payload.chunks_exact_mut(16).zip([
        statement.scope,
        statement.root,
        statement.nullifier_hash,
        statement.payout_digest,
    ]) {
        output.copy_from_slice(&canonical_digest(digest));
    }
    p2bb512(domains::STATEMENT, 256, 0, &payload)
}

#[must_use]
pub fn parameter_id(manifest: &[u8]) -> Digest512 {
    k512(domains::PARAMETER_MANIFEST, manifest)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Note {
    pub chain_id: u64,
    pub pool: [u8; 20],
    pub parameter_id: Digest512,
    pub nullifier_secret: CanonicalSecret,
    pub trapdoor: CanonicalSecret,
}

impl Note {
    /// Generates a note with two independently sampled canonical secrets using
    /// operating-system randomness.
    #[must_use]
    pub fn generate(chain_id: u64, pool: [u8; 20], parameter_id: Digest512) -> Self {
        Self {
            chain_id,
            pool,
            parameter_id,
            nullifier_secret: CanonicalSecret::generate(),
            trapdoor: CanonicalSecret::generate(),
        }
    }

    /// Generates a note with two independently sampled canonical secrets using
    /// the supplied cryptographic RNG.
    pub fn random<R: CryptoRng + Rng>(
        chain_id: u64,
        pool: [u8; 20],
        parameter_id: Digest512,
        rng: &mut R,
    ) -> Self {
        Self {
            chain_id,
            pool,
            parameter_id,
            nullifier_secret: CanonicalSecret::random_with(rng),
            trapdoor: CanonicalSecret::random_with(rng),
        }
    }

    #[must_use]
    pub fn encode_binary(self) -> [u8; NOTE_BINARY_LEN] {
        let mut out = [0u8; NOTE_BINARY_LEN];
        out[..4].copy_from_slice(&NOTE_MAGIC);
        out[4..6].copy_from_slice(&NOTE_VERSION.to_be_bytes());
        out[6..14].copy_from_slice(&self.chain_id.to_be_bytes());
        out[14..34].copy_from_slice(&self.pool);
        out[34..98].copy_from_slice(&self.parameter_id.to_bytes());
        out[98..130].copy_from_slice(&self.nullifier_secret.to_bytes());
        out[130..162].copy_from_slice(&self.trapdoor.to_bytes());
        let checksum = note_checksum(&out[..NOTE_BODY_LEN]);
        out[NOTE_BODY_LEN..].copy_from_slice(&checksum);
        out
    }

    #[must_use]
    pub fn encode(self) -> String {
        format!(
            "{NOTE_PREFIX}{}",
            URL_SAFE_NO_PAD.encode(self.encode_binary())
        )
    }

    /// Parses and validates a canonical encoded note.
    ///
    /// # Errors
    ///
    /// Returns [`NoteError`] when the prefix, base64, length, magic, version,
    /// checksum, or either secret encoding is invalid.
    pub fn parse(encoded: &str) -> Result<Self, NoteError> {
        let value = encoded.strip_prefix(NOTE_PREFIX).ok_or(NoteError::Prefix)?;
        let bytes = URL_SAFE_NO_PAD
            .decode(value)
            .map_err(|_| NoteError::Base64)?;
        if bytes.len() != NOTE_BINARY_LEN {
            return Err(NoteError::Length {
                actual: bytes.len(),
            });
        }
        if bytes[..4] != NOTE_MAGIC {
            return Err(NoteError::Magic);
        }
        if u16::from_be_bytes([bytes[4], bytes[5]]) != NOTE_VERSION {
            return Err(NoteError::Version);
        }
        if bytes[NOTE_BODY_LEN..] != note_checksum(&bytes[..NOTE_BODY_LEN]) {
            return Err(NoteError::Checksum);
        }
        let mut pool = [0u8; 20];
        pool.copy_from_slice(&bytes[14..34]);
        let mut parameter = [0u8; 64];
        parameter.copy_from_slice(&bytes[34..98]);
        let mut nullifier_secret_bytes = [0u8; CanonicalSecret::BYTE_LEN];
        nullifier_secret_bytes.copy_from_slice(&bytes[98..130]);
        let nullifier_secret =
            CanonicalSecret::from_bytes(nullifier_secret_bytes).map_err(NoteError::Secret)?;
        let mut trapdoor_bytes = [0u8; CanonicalSecret::BYTE_LEN];
        trapdoor_bytes.copy_from_slice(&bytes[130..162]);
        let trapdoor = CanonicalSecret::from_bytes(trapdoor_bytes).map_err(NoteError::Secret)?;
        Ok(Self {
            chain_id: u64::from_be_bytes([
                bytes[6], bytes[7], bytes[8], bytes[9], bytes[10], bytes[11], bytes[12], bytes[13],
            ]),
            pool,
            parameter_id: Digest512::from_bytes(parameter),
            nullifier_secret,
            trapdoor,
        })
    }
}

fn note_checksum(body: &[u8]) -> [u8; 32] {
    let mut hash = Keccak256::new();
    hash.update([0, domains::NOTE]);
    hash.update(body);
    hash.finalize().into()
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum NoteError {
    #[error("note prefix is not pqtc-note-v3")]
    Prefix,
    #[error("note payload is not canonical base64url")]
    Base64,
    #[error("note length must be {NOTE_BINARY_LEN} bytes, got {actual}")]
    Length { actual: usize },
    #[error("note magic is invalid")]
    Magic,
    #[error("note version is unsupported")]
    Version,
    #[error("note checksum is invalid")]
    Checksum,
    #[error("note secret is not canonical: {0}")]
    Secret(CanonicalError),
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::{SeedableRng, rngs::StdRng};

    fn digest_with_offset(offset: u32) -> Digest512 {
        elements_to_digest(core::array::from_fn(|index| {
            BabyBear::new(offset + u32::try_from(index).expect("index fits u32"))
        }))
    }

    fn repeated_secret(byte: u8) -> CanonicalSecret {
        CanonicalSecret::from_bytes([byte; CanonicalSecret::BYTE_LEN])
            .expect("repeated-byte fixture is canonical")
    }

    #[test]
    fn k512_is_ethereum_keccak_and_remains_proof_only() {
        assert_eq!(
            hex::encode(keccak256(b"")),
            "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
        );
        assert_ne!(
            hex::encode(keccak256(b"")),
            "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a"
        );
        assert_eq!(
            parameter_id(b"manifest"),
            k512(domains::PARAMETER_MANIFEST, b"manifest")
        );

        let payload = [BabyBear::new(7), BabyBear::new(9)];
        assert_ne!(
            k512(domains::SCOPE, &[0, 7, 0, 9]),
            p2bb512(domains::SCOPE, 4, 0, &payload)
        );
    }

    #[test]
    fn p2bb512_is_deterministic_and_binds_domain_and_lengths() {
        let payload = core::array::from_fn::<_, 5, _>(|index| {
            BabyBear::new(u32::try_from(index).expect("index fits u32"))
        });
        let baseline = p2bb512(domains::SCOPE, 9, 0, &payload);
        assert_eq!(baseline, p2bb512(domains::SCOPE, 9, 0, &payload));
        assert_ne!(baseline, p2bb512(domains::NOTE, 9, 0, &payload));
        assert_ne!(baseline, p2bb512(domains::SCOPE, 10, 0, &payload));

        let mut extra_element = payload.to_vec();
        extra_element.push(BabyBear::ZERO);
        assert_ne!(baseline, p2bb512(domains::SCOPE, 9, 0, &extra_element));
        assert!(digest_to_elements(baseline).is_some());
        assert_eq!(
            hex::encode(baseline.to_bytes()),
            "683e24183b7b8e38192b953f0cb670ac637d03f6311b44f17458f2eb5ca9dc901d7bcacd1146c2774c97f80b0fd111e7270e6fe038bcbfec2103b6f644a96520"
        );
        let mut permutation_input =
            core::array::from_fn(|index| BabyBear::new(u32::try_from(index).expect("index fits")));
        P2BB512_PERMUTATION.permute_mut(&mut permutation_input);
        assert_eq!(
            permutation_input.map(|element| element.as_canonical_u32()),
            [
                1_906_786_279,
                1_737_026_427,
                1_959_749_225,
                700_325_316,
                1_638_050_605,
                1_021_608_788,
                1_726_691_001,
                1_761_127_344,
                1_552_405_120,
                417_318_995,
                36_799_261,
                1_215_172_152,
                614_923_223,
                1_300_746_575,
                957_311_597,
                304_856_115,
            ]
        );
        let payload_0_to_15: [BabyBear; 16] =
            core::array::from_fn(|index| BabyBear::new(u32::try_from(index).expect("index fits")));
        assert_eq!(
            hex::encode(p2bb512(domains::SCOPE, 32, 0, &payload_0_to_15).to_bytes()),
            "192285c83ad82d235f4020c4185fb99a5d7a4574217a7fa5097c082c4c905cfd69df098f455618e612d7819f26e68e4d5ff4842c4d5177ae479caee05752c4bd"
        );
    }

    #[test]
    fn digest_elements_round_trip_canonically_in_halves() {
        let elements = core::array::from_fn(|index| {
            BabyBear::from_canonical_checked(
                BabyBear::ORDER_U32 - 1 - u32::try_from(index).expect("index fits u32"),
            )
            .expect("value is canonical")
        });
        let digest = elements_to_digest(elements);
        assert_eq!(&digest.left[..4], &(BabyBear::ORDER_U32 - 1).to_be_bytes());
        assert_eq!(&digest.right[..4], &(BabyBear::ORDER_U32 - 9).to_be_bytes());
        assert_eq!(digest_to_elements(digest), Some(elements));

        let mut noncanonical = digest.to_bytes();
        noncanonical[..4].copy_from_slice(&BabyBear::ORDER_U32.to_be_bytes());
        let noncanonical = Digest512::from_bytes(noncanonical);
        assert_eq!(digest_to_elements(noncanonical), None);
        assert!(std::panic::catch_unwind(|| empty_leaf(noncanonical)).is_err());
    }

    #[test]
    fn note_round_trip_and_corruption_detection() {
        let mut rng = StdRng::seed_from_u64(7);
        let note = Note::random(
            11_155_111,
            [3; 20],
            Digest512 {
                left: [4; 32],
                right: [5; 32],
            },
            &mut rng,
        );
        let encoded = note.encode();
        assert!(encoded.starts_with("pqtc-note-v3:"));
        assert_eq!(Note::parse(&encoded), Ok(note));

        let canonical_binary = note.encode_binary();
        assert_eq!(&canonical_binary[4..6], &3u16.to_be_bytes());

        let v2_prefix = encoded.replacen("pqtc-note-v3:", "pqtc-note-v2:", 1);
        assert_eq!(Note::parse(&v2_prefix), Err(NoteError::Prefix));

        let mut v2_binary = canonical_binary;
        v2_binary[4..6].copy_from_slice(&2u16.to_be_bytes());
        let checksum = note_checksum(&v2_binary[..NOTE_BODY_LEN]);
        v2_binary[NOTE_BODY_LEN..].copy_from_slice(&checksum);
        let v2_version = format!("{NOTE_PREFIX}{}", URL_SAFE_NO_PAD.encode(v2_binary));
        assert_eq!(Note::parse(&v2_version), Err(NoteError::Version));

        let mut corrupted_binary = canonical_binary;
        corrupted_binary[100] ^= 1;
        let bad = format!("{NOTE_PREFIX}{}", URL_SAFE_NO_PAD.encode(corrupted_binary));
        assert_eq!(Note::parse(&bad), Err(NoteError::Checksum));

        let mut noncanonical_binary = canonical_binary;
        noncanonical_binary[98..102].copy_from_slice(&BabyBear::ORDER_U32.to_be_bytes());
        let checksum = note_checksum(&noncanonical_binary[..NOTE_BODY_LEN]);
        noncanonical_binary[NOTE_BODY_LEN..].copy_from_slice(&checksum);
        let noncanonical = format!(
            "{NOTE_PREFIX}{}",
            URL_SAFE_NO_PAD.encode(noncanonical_binary)
        );
        assert!(matches!(
            Note::parse(&noncanonical),
            Err(NoteError::Secret(CanonicalError::NonCanonicalField {
                value: BabyBear::ORDER_U32
            }))
        ));
    }

    #[test]
    fn canonical_scope_schema_is_big_endian_u16_and_length_bound() {
        let input = ScopeInput {
            chain_id: u64::MAX,
            pool: [0xff; 20],
            denomination: [0xff; 32],
            tree_depth: u8::MAX,
            protocol_version: u32::MAX,
            parameter_id: Digest512 {
                left: [0xff; 32],
                right: [0xfe; 32],
            },
        };
        let encoded = input.encode();
        assert_eq!(&encoded[..8], &u64::MAX.to_be_bytes());
        assert_eq!(&encoded[28..60], &[0xff; 32]);
        assert_eq!(&encoded[61..65], &u32::MAX.to_be_bytes());

        let mut payload = [BabyBear::ZERO; 65];
        encode_bytes(&encoded, &mut payload);
        assert_eq!(payload[64].as_canonical_u32(), 0xfe00);
        assert_eq!(scope(input), p2bb512(domains::SCOPE, 129, 0, &payload));
    }

    #[test]
    fn application_hashes_are_canonical_and_deterministic() {
        let scope_input = ScopeInput {
            chain_id: 11_155_111,
            pool: [1; 20],
            denomination: [2; 32],
            tree_depth: 20,
            protocol_version: 3,
            parameter_id: parameter_id(b"manifest"),
        };
        let scope_digest = scope(scope_input);
        let nullifier_secret = repeated_secret(3);
        let trapdoor = repeated_secret(4);
        let commitment_digest = commitment(scope_digest, nullifier_secret, trapdoor);
        let nullifier_digest = nullifier_hash(scope_digest, nullifier_secret);
        let empty_digest = empty_leaf(scope_digest);
        let root = merkle_node(0, commitment_digest, empty_digest);
        let payout = payout_digest([5; 20], [6; 20], [7; 32]);
        let statement = WithdrawalStatement {
            scope: scope_digest,
            root,
            nullifier_hash: nullifier_digest,
            payout_digest: payout,
        };
        let statement_digest = statement_hash(statement);

        for digest in [
            scope_digest,
            commitment_digest,
            nullifier_digest,
            empty_digest,
            root,
            payout,
            statement_digest,
        ] {
            assert!(digest_to_elements(digest).is_some());
        }
        assert_eq!(scope_digest, scope(scope_input));
        assert_eq!(
            commitment_digest,
            commitment(scope_digest, nullifier_secret, trapdoor)
        );
        assert_eq!(statement_digest, statement_hash(statement));
    }

    #[test]
    fn every_secret_limb_is_binding() {
        let scope_digest = p2bb512(domains::SCOPE, 0, 0, &[]);
        let zero = CanonicalSecret::from_limbs([0; CanonicalSecret::LIMB_COUNT]).unwrap();
        let baseline_commitment = commitment(scope_digest, zero, zero);
        let baseline_nullifier = nullifier_hash(scope_digest, zero);

        for index in 0..CanonicalSecret::LIMB_COUNT {
            let mut limbs = [0; CanonicalSecret::LIMB_COUNT];
            limbs[index] = 1;
            let changed = CanonicalSecret::from_limbs(limbs).unwrap();
            assert_ne!(
                commitment(scope_digest, changed, zero),
                baseline_commitment,
                "nullifier-secret limb {index} did not affect commitment"
            );
            assert_ne!(
                commitment(scope_digest, zero, changed),
                baseline_commitment,
                "trapdoor limb {index} did not affect commitment"
            );
            assert_ne!(
                nullifier_hash(scope_digest, changed),
                baseline_nullifier,
                "nullifier-secret limb {index} did not affect nullifier"
            );
        }
    }

    #[test]
    fn canonical_v3_application_vector() {
        let scope_digest = scope(ScopeInput {
            chain_id: 11_155_111,
            pool: [1; 20],
            denomination: [2; 32],
            tree_depth: 20,
            protocol_version: 3,
            parameter_id: parameter_id(b"manifest"),
        });
        let nullifier_secret = CanonicalSecret::from_limbs([3, 5, 7, 11, 13, 17, 19, 23]).unwrap();
        let trapdoor = CanonicalSecret::from_limbs([29, 31, 37, 41, 43, 47, 53, 59]).unwrap();

        assert_eq!(
            hex::encode(scope_digest.to_bytes()),
            "29d774fa067d5844644966e1326483b24085e8fe771fdf570d64b61815b83cdf31d6b62414ead4750956548b6643d0831fdba8e822e0ada718ffd4d3470a56c7"
        );
        assert_eq!(
            hex::encode(commitment(scope_digest, nullifier_secret, trapdoor).to_bytes()),
            "174026330a3b3def58a2547403d04234035843a84b7814a330ff65e4049592cc69da09314cc70f0d6ead8d1d38a5dd2f45f5e9741b7e063f24acd369233a1979"
        );
        assert_eq!(
            hex::encode(nullifier_hash(scope_digest, nullifier_secret).to_bytes()),
            "703e079c63caf3b65227079e3201df600319e2fb294395ae278a63183b0b8fe2078b9d397692e1e14e7952cd3f80d97301a420444d733f0b2fb440fc18deaba6"
        );
    }
    #[test]
    fn merkle_level_order_and_digest_halves_are_binding() {
        let a = digest_with_offset(1);
        let b = digest_with_offset(101);
        assert_ne!(merkle_node(0, a, b), merkle_node(1, a, b));
        assert_ne!(merkle_node(0, a, b), merkle_node(0, b, a));

        let mut changed = digest_to_elements(a).expect("digest is canonical");
        changed[8] += BabyBear::ONE;
        let changed_right_half = elements_to_digest(changed);
        assert_ne!(merkle_node(0, a, b), merkle_node(0, changed_right_half, b));
    }
}
