//! Canonical protocol types and encodings for PQ Tornado Classic v0.3.

pub mod domains;

use core::{fmt, str::FromStr};
use rand::{CryptoRng, Rng, RngExt, TryRng};
use serde::{
    Deserialize, Deserializer, Serialize, Serializer,
    de::{Error as _, SeqAccess, Visitor},
    ser::SerializeTuple,
};
use thiserror::Error;

pub const PROTOCOL_VERSION: u32 = 3;
pub const TREE_DEPTH: u8 = 20;
pub const BABY_BEAR_MODULUS: u32 = 2_013_265_921;
pub const PUBLIC_VALUES_COUNT: usize = 64;
pub const PLONKY3_COMMIT: &str = "3152b14a89067c83775a8076cc262ffc48a1fd7c";

/// A 32-byte secret encoded as eight canonical big-endian `BabyBear` limbs.
///
/// Construction always validates that every limb is strictly less than
/// [`BABY_BEAR_MODULUS`]. Random construction samples full-width `u32` values
/// and rejects out-of-field candidates, so it introduces no modulo bias.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct CanonicalSecret([u32; 8]);

impl CanonicalSecret {
    pub const BYTE_LEN: usize = 32;
    pub const LIMB_COUNT: usize = 8;

    /// Validates eight field limbs.
    ///
    /// # Errors
    ///
    /// Returns [`CanonicalError::NonCanonicalField`] for the first limb that
    /// is not a canonical `BabyBear` value.
    pub fn from_limbs(limbs: [u32; Self::LIMB_COUNT]) -> Result<Self, CanonicalError> {
        for &value in &limbs {
            if value >= BABY_BEAR_MODULUS {
                return Err(CanonicalError::NonCanonicalField { value });
            }
        }
        Ok(Self(limbs))
    }

    /// Decodes and validates eight big-endian field limbs.
    ///
    /// # Errors
    ///
    /// Returns [`CanonicalError::NonCanonicalField`] for the first limb that
    /// is not a canonical `BabyBear` value.
    pub fn from_bytes(bytes: [u8; Self::BYTE_LEN]) -> Result<Self, CanonicalError> {
        let mut limbs = [0u32; Self::LIMB_COUNT];
        for (limb, chunk) in limbs.iter_mut().zip(bytes.chunks_exact(4)) {
            let [a, b, c, d] = chunk else {
                unreachable!("chunks_exact(4) only yields four-byte chunks");
            };
            *limb = decode_field([*a, *b, *c, *d])?;
        }
        Ok(Self(limbs))
    }

    /// Samples eight independent, uniform `BabyBear` limbs from `rng`.
    pub fn random_with<R: CryptoRng + Rng + ?Sized>(rng: &mut R) -> Self {
        let limbs = core::array::from_fn(|_| {
            loop {
                let candidate: u32 = rng.random();
                if candidate < BABY_BEAR_MODULUS {
                    break candidate;
                }
            }
        });
        Self(limbs)
    }

    /// Samples eight independent, uniform `BabyBear` limbs directly from the
    /// operating system.
    ///
    /// # Panics
    ///
    /// Panics when operating-system randomness is unavailable.
    #[must_use]
    pub fn generate() -> Self {
        let limbs = core::array::from_fn(|_| {
            loop {
                let candidate = rand::rngs::SysRng
                    .try_next_u32()
                    .expect("operating-system randomness is unavailable");
                if candidate < BABY_BEAR_MODULUS {
                    break candidate;
                }
            }
        });
        Self(limbs)
    }

    #[must_use]
    pub const fn limbs(&self) -> &[u32; Self::LIMB_COUNT] {
        &self.0
    }

    #[must_use]
    pub const fn into_limbs(self) -> [u32; Self::LIMB_COUNT] {
        self.0
    }

    #[must_use]
    pub fn to_bytes(self) -> [u8; Self::BYTE_LEN] {
        let mut bytes = [0u8; Self::BYTE_LEN];
        for (&limb, output) in self.0.iter().zip(bytes.chunks_exact_mut(4)) {
            output.copy_from_slice(&limb.to_be_bytes());
        }
        bytes
    }
}

impl TryFrom<&[u8]> for CanonicalSecret {
    type Error = CanonicalError;

    fn try_from(bytes: &[u8]) -> Result<Self, Self::Error> {
        let bytes: [u8; Self::BYTE_LEN] = bytes.try_into().map_err(|_| CanonicalError::Length {
            expected: Self::BYTE_LEN,
            actual: bytes.len(),
        })?;
        Self::from_bytes(bytes)
    }
}

impl TryFrom<[u8; CanonicalSecret::BYTE_LEN]> for CanonicalSecret {
    type Error = CanonicalError;

    fn try_from(bytes: [u8; CanonicalSecret::BYTE_LEN]) -> Result<Self, Self::Error> {
        Self::from_bytes(bytes)
    }
}

impl fmt::Debug for CanonicalSecret {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("CanonicalSecret(REDACTED)")
    }
}

impl fmt::Display for CanonicalSecret {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "0x{}", hex::encode(self.to_bytes()))
    }
}

impl FromStr for CanonicalSecret {
    type Err = CanonicalError;

    fn from_str(encoded: &str) -> Result<Self, Self::Err> {
        let hex = encoded
            .strip_prefix("0x")
            .ok_or(CanonicalError::InvalidSecretEncoding)?;
        if hex.len() != Self::BYTE_LEN * 2 {
            return Err(CanonicalError::Length {
                expected: Self::BYTE_LEN * 2,
                actual: hex.len(),
            });
        }
        let mut bytes = [0u8; Self::BYTE_LEN];
        hex::decode_to_slice(hex, &mut bytes).map_err(|_| CanonicalError::InvalidSecretEncoding)?;
        Self::from_bytes(bytes)
    }
}

impl Serialize for CanonicalSecret {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        if serializer.is_human_readable() {
            serializer.serialize_str(&self.to_string())
        } else {
            let mut tuple = serializer.serialize_tuple(Self::BYTE_LEN)?;
            for byte in self.to_bytes() {
                tuple.serialize_element(&byte)?;
            }
            tuple.end()
        }
    }
}

struct CanonicalSecretVisitor;

impl<'de> Visitor<'de> for CanonicalSecretVisitor {
    type Value = CanonicalSecret;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a canonical 0x-prefixed 32-byte BabyBear secret")
    }

    fn visit_str<E: serde::de::Error>(self, value: &str) -> Result<Self::Value, E> {
        value.parse().map_err(E::custom)
    }

    fn visit_seq<A: SeqAccess<'de>>(self, mut sequence: A) -> Result<Self::Value, A::Error> {
        let mut bytes = [0u8; CanonicalSecret::BYTE_LEN];
        for (index, byte) in bytes.iter_mut().enumerate() {
            *byte = sequence
                .next_element()?
                .ok_or_else(|| A::Error::invalid_length(index, &self))?;
        }
        CanonicalSecret::from_bytes(bytes).map_err(A::Error::custom)
    }
}

impl<'de> Deserialize<'de> for CanonicalSecret {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        if deserializer.is_human_readable() {
            deserializer.deserialize_str(CanonicalSecretVisitor)
        } else {
            deserializer.deserialize_tuple(Self::BYTE_LEN, CanonicalSecretVisitor)
        }
    }
}

#[derive(Clone, Copy, Default, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Digest512 {
    pub left: [u8; 32],
    pub right: [u8; 32],
}

impl Digest512 {
    pub const ZERO: Self = Self {
        left: [0; 32],
        right: [0; 32],
    };

    #[must_use]
    pub fn to_bytes(self) -> [u8; 64] {
        let mut out = [0; 64];
        out[..32].copy_from_slice(&self.left);
        out[32..].copy_from_slice(&self.right);
        out
    }

    #[must_use]
    pub fn from_bytes(bytes: [u8; 64]) -> Self {
        let mut left = [0; 32];
        let mut right = [0; 32];
        left.copy_from_slice(&bytes[..32]);
        right.copy_from_slice(&bytes[32..]);
        Self { left, right }
    }

    #[must_use]
    pub fn is_zero(&self) -> bool {
        *self == Self::ZERO
    }
}

impl fmt::Debug for Digest512 {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "0x{}", hex::encode(self.to_bytes()))
    }
}

impl fmt::Display for Digest512 {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "0x{}", hex::encode(self.to_bytes()))
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ScopeInput {
    pub chain_id: u64,
    pub pool: [u8; 20],
    pub denomination: [u8; 32],
    pub tree_depth: u8,
    pub protocol_version: u32,
    pub parameter_id: Digest512,
}

impl ScopeInput {
    #[must_use]
    pub fn encode(self) -> [u8; 129] {
        let mut out = [0; 129];
        out[..8].copy_from_slice(&self.chain_id.to_be_bytes());
        out[8..28].copy_from_slice(&self.pool);
        out[28..60].copy_from_slice(&self.denomination);
        out[60] = self.tree_depth;
        out[61..65].copy_from_slice(&self.protocol_version.to_be_bytes());
        out[65..].copy_from_slice(&self.parameter_id.to_bytes());
        out
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct WithdrawalStatement {
    pub scope: Digest512,
    pub root: Digest512,
    pub nullifier_hash: Digest512,
    pub payout_digest: Digest512,
}

impl WithdrawalStatement {
    #[must_use]
    pub fn public_values(self) -> [u32; PUBLIC_VALUES_COUNT] {
        let mut values = [0u32; PUBLIC_VALUES_COUNT];
        let digests = [
            self.scope,
            self.root,
            self.nullifier_hash,
            self.payout_digest,
        ];
        let mut cursor = 0;
        for digest in digests {
            for half in [digest.left, digest.right] {
                for limb in half.chunks_exact(4) {
                    values[cursor] = u32::from_be_bytes([limb[0], limb[1], limb[2], limb[3]]);
                    cursor += 1;
                }
            }
        }
        values
    }
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum CanonicalError {
    #[error("field element {value} is not canonical")]
    NonCanonicalField { value: u32 },
    #[error("invalid byte length: expected {expected}, got {actual}")]
    Length { expected: usize, actual: usize },
    #[error("secret must be 0x-prefixed hexadecimal")]
    InvalidSecretEncoding,
}

/// Decodes one canonical big-endian `BabyBear` field element.
///
/// # Errors
///
/// Returns [`CanonicalError::NonCanonicalField`] when the integer is not less
/// than the `BabyBear` modulus.
pub fn decode_field(bytes: [u8; 4]) -> Result<u32, CanonicalError> {
    let value = u32::from_be_bytes(bytes);
    if value >= BABY_BEAR_MODULUS {
        return Err(CanonicalError::NonCanonicalField { value });
    }
    Ok(value)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn statement_uses_big_endian_thirty_two_bit_field_elements() {
        let mut digest = Digest512::ZERO;
        digest.left[0..4].copy_from_slice(&[0x12, 0x34, 0xab, 0xcd]);
        let values = WithdrawalStatement {
            scope: digest,
            root: Digest512::ZERO,
            nullifier_hash: Digest512::ZERO,
            payout_digest: Digest512::ZERO,
        }
        .public_values();
        assert_eq!(values[0], 0x1234_abcd);
        assert_eq!(values[1], 0);
    }

    #[test]
    fn field_codec_rejects_modulus() {
        assert_eq!(
            decode_field((BABY_BEAR_MODULUS - 1).to_be_bytes()),
            Ok(BABY_BEAR_MODULUS - 1)
        );
        assert!(matches!(
            decode_field(BABY_BEAR_MODULUS.to_be_bytes()),
            Err(CanonicalError::NonCanonicalField { .. })
        ));
    }

    #[test]
    fn canonical_secret_round_trips_binary_text_and_serde() {
        let limbs =
            core::array::from_fn(|index| u32::try_from(index).expect("small index") * 0x0102_0304);
        let secret = CanonicalSecret::from_limbs(limbs).unwrap();
        let bytes = secret.to_bytes();
        assert_eq!(CanonicalSecret::from_bytes(bytes), Ok(secret));
        assert_eq!(secret.to_string().parse(), Ok(secret));
        assert_eq!(core::mem::size_of::<CanonicalSecret>(), 32);

        let json = serde_json::to_string(&secret).unwrap();
        assert_eq!(
            serde_json::from_str::<CanonicalSecret>(&json).unwrap(),
            secret
        );
        let binary = postcard::to_allocvec(&secret).unwrap();
        assert_eq!(binary, bytes);
        assert_eq!(
            postcard::from_bytes::<CanonicalSecret>(&binary).unwrap(),
            secret
        );
        assert!(
            CanonicalSecret::generate()
                .limbs()
                .iter()
                .all(|&limb| limb < BABY_BEAR_MODULUS)
        );
    }

    #[test]
    fn canonical_secret_rejects_every_noncanonical_boundary() {
        for limb in 0..CanonicalSecret::LIMB_COUNT {
            let mut bytes = [0u8; CanonicalSecret::BYTE_LEN];
            bytes[limb * 4..limb * 4 + 4].copy_from_slice(&BABY_BEAR_MODULUS.to_be_bytes());
            assert!(matches!(
                CanonicalSecret::from_bytes(bytes),
                Err(CanonicalError::NonCanonicalField {
                    value: BABY_BEAR_MODULUS
                })
            ));
            assert!(CanonicalSecret::try_from(bytes.as_slice()).is_err());
            assert!(
                format!("0x{}", hex::encode(bytes))
                    .parse::<CanonicalSecret>()
                    .is_err()
            );
            let json = format!("\"0x{}\"", hex::encode(bytes));
            assert!(serde_json::from_str::<CanonicalSecret>(&json).is_err());
            assert!(postcard::from_bytes::<CanonicalSecret>(&bytes).is_err());
        }
    }
}
