use std::collections::VecDeque;

use p3_baby_bear::BabyBear;
use p3_challenger::{
    CanFinalizeDigest, CanObserve, CanSample, CanSampleBits, CanSampleUniformBits, FieldChallenger,
    GrindingChallenger, ResamplingError,
};
use p3_field::{BasedVectorSpace, PrimeCharacteristicRing, PrimeField32};
use p3_symmetric::{CryptographicHasher, MerkleCap, PseudoCompressionFunction};
use pqtc_hash::k512;
use pqtc_spec::{BABY_BEAR_MODULUS, Digest512, domains};

pub const DIGEST_WORDS: usize = 8;
const FIELD_ITEM: u8 = 1;
const COMMITMENT_ITEM: u8 = 2;

#[derive(Clone, Copy, Debug, Default)]
pub struct ProofLeafHasher;

impl CryptographicHasher<BabyBear, [u64; DIGEST_WORDS]> for ProofLeafHasher {
    fn hash_iter<I>(&self, input: I) -> [u64; DIGEST_WORDS]
    where
        I: IntoIterator<Item = BabyBear>,
    {
        let values: Vec<_> = input.into_iter().collect();
        digest_words(hash_leaf(values.iter().map(PrimeField32::as_canonical_u32)))
    }
}

impl<const N: usize> CryptographicHasher<[BabyBear; N], [[u64; N]; DIGEST_WORDS]>
    for ProofLeafHasher
{
    fn hash_iter<I>(&self, input: I) -> [[u64; N]; DIGEST_WORDS]
    where
        I: IntoIterator<Item = [BabyBear; N]>,
    {
        let values: Vec<_> = input.into_iter().collect();
        let lane_digests: [[u64; DIGEST_WORDS]; N] = core::array::from_fn(|lane| {
            digest_words(hash_leaf(
                values.iter().map(|packed| packed[lane].as_canonical_u32()),
            ))
        });
        core::array::from_fn(|word| core::array::from_fn(|lane| lane_digests[lane][word]))
    }
}

fn hash_leaf(values: impl IntoIterator<Item = u32>) -> Digest512 {
    let fields: Vec<u32> = values.into_iter().collect();
    let byte_len = u32::try_from(
        fields
            .len()
            .checked_mul(4)
            .expect("leaf byte length overflow"),
    )
    .expect("leaf byte length exceeds u32");
    let mut payload = Vec::with_capacity(4 + byte_len as usize);
    payload.extend_from_slice(&byte_len.to_be_bytes());
    for value in fields {
        payload.extend_from_slice(&value.to_be_bytes());
    }
    k512(domains::PROOF_LEAF, &payload)
}
#[must_use]
pub fn proof_leaf_digest(values: &[u32]) -> Digest512 {
    hash_leaf(values.iter().copied())
}

#[derive(Clone, Copy, Debug, Default)]
pub struct ProofNodeCompressor;

impl PseudoCompressionFunction<[u64; DIGEST_WORDS], 2> for ProofNodeCompressor {
    fn compress(&self, input: [[u64; DIGEST_WORDS]; 2]) -> [u64; DIGEST_WORDS] {
        digest_words(hash_node(input.map(words_digest)))
    }
}

impl<const N: usize> PseudoCompressionFunction<[[u64; N]; DIGEST_WORDS], 2>
    for ProofNodeCompressor
{
    fn compress(&self, input: [[[u64; N]; DIGEST_WORDS]; 2]) -> [[u64; N]; DIGEST_WORDS] {
        let lane_digests: [[u64; DIGEST_WORDS]; N] = core::array::from_fn(|lane| {
            let children = core::array::from_fn(|child| {
                words_digest(core::array::from_fn(|word| input[child][word][lane]))
            });
            digest_words(hash_node(children))
        });
        core::array::from_fn(|word| core::array::from_fn(|lane| lane_digests[lane][word]))
    }
}

fn hash_node(children: [Digest512; 2]) -> Digest512 {
    let mut payload = [0u8; 128];
    payload[..64].copy_from_slice(&children[0].to_bytes());
    payload[64..].copy_from_slice(&children[1].to_bytes());
    k512(domains::PROOF_NODE, &payload)
}
#[must_use]
pub fn proof_node_digest(left: Digest512, right: Digest512) -> Digest512 {
    hash_node([left, right])
}

#[must_use]
pub fn digest_words(digest: Digest512) -> [u64; DIGEST_WORDS] {
    let bytes = digest.to_bytes();
    core::array::from_fn(|i| {
        u64::from_be_bytes(bytes[i * 8..i * 8 + 8].try_into().expect("word range"))
    })
}

#[must_use]
pub fn words_digest(words: [u64; DIGEST_WORDS]) -> Digest512 {
    let mut bytes = [0u8; 64];
    for (chunk, word) in bytes.chunks_exact_mut(8).zip(words) {
        chunk.copy_from_slice(&word.to_be_bytes());
    }
    Digest512::from_bytes(bytes)
}

/// Explicit 512-bit, typed, length-delimited Fiat-Shamir transcript.
#[derive(Clone, Debug)]
pub struct Transcript512 {
    state: Digest512,
    output: VecDeque<u8>,
    squeeze_counter: u64,
}

impl Transcript512 {
    #[must_use]
    pub fn new(parameter_id: Digest512, public_values: &[BabyBear]) -> Self {
        let mut payload = Vec::with_capacity(64 + public_values.len() * 4);
        payload.extend_from_slice(&parameter_id.to_bytes());
        for value in public_values {
            payload.extend_from_slice(&value.as_canonical_u32().to_be_bytes());
        }
        Self {
            state: k512(domains::TRANSCRIPT_INIT, &payload),
            output: VecDeque::new(),
            squeeze_counter: 0,
        }
    }

    fn absorb(&mut self, item_type: u8, bytes: &[u8]) {
        let len = u32::try_from(bytes.len()).expect("transcript item exceeds u32");
        let mut payload = Vec::with_capacity(64 + 1 + 4 + bytes.len());
        payload.extend_from_slice(&self.state.to_bytes());
        payload.push(item_type);
        payload.extend_from_slice(&len.to_be_bytes());
        payload.extend_from_slice(bytes);
        self.state = k512(domains::TRANSCRIPT_ABSORB, &payload);
        self.output.clear();
        self.squeeze_counter = 0;
    }

    fn sample_byte(&mut self) -> u8 {
        if self.output.is_empty() {
            let mut payload = [0u8; 72];
            payload[..64].copy_from_slice(&self.state.to_bytes());
            payload[64..].copy_from_slice(&self.squeeze_counter.to_be_bytes());
            self.squeeze_counter = self
                .squeeze_counter
                .checked_add(1)
                .expect("squeeze counter overflow");
            self.output
                .extend(k512(domains::TRANSCRIPT_SQUEEZE, &payload).to_bytes());
        }
        self.output.pop_front().expect("squeeze fills output")
    }

    #[must_use]
    pub const fn state(&self) -> Digest512 {
        self.state
    }
}

impl CanObserve<BabyBear> for Transcript512 {
    fn observe(&mut self, value: BabyBear) {
        self.absorb(FIELD_ITEM, &value.as_canonical_u32().to_be_bytes());
    }
}

impl CanObserve<MerkleCap<BabyBear, [u64; DIGEST_WORDS]>> for Transcript512 {
    fn observe(&mut self, cap: MerkleCap<BabyBear, [u64; DIGEST_WORDS]>) {
        self.observe(&cap);
    }
}

impl CanObserve<&MerkleCap<BabyBear, [u64; DIGEST_WORDS]>> for Transcript512 {
    fn observe(&mut self, cap: &MerkleCap<BabyBear, [u64; DIGEST_WORDS]>) {
        let mut bytes = Vec::with_capacity(cap.roots().len() * 64);
        for root in cap.roots() {
            for word in root {
                bytes.extend_from_slice(&word.to_be_bytes());
            }
        }
        self.absorb(COMMITMENT_ITEM, &bytes);
    }
}

impl<EF: BasedVectorSpace<BabyBear>> CanSample<EF> for Transcript512 {
    fn sample(&mut self) -> EF {
        EF::from_basis_coefficients_fn(|_| {
            loop {
                let value =
                    u32::from_be_bytes(core::array::from_fn(|_| self.sample_byte())) & 0x7fff_ffff;
                if value < BABY_BEAR_MODULUS {
                    return BabyBear::new(value);
                }
            }
        })
    }
}

impl CanSampleBits<usize> for Transcript512 {
    fn sample_bits(&mut self, bits: usize) -> usize {
        assert!(bits < usize::BITS as usize);
        assert!(bits <= 31);
        let value = u32::from_be_bytes(core::array::from_fn(|_| self.sample_byte())) as usize;
        value & ((1usize << bits) - 1)
    }
}

impl CanSampleUniformBits<BabyBear> for Transcript512 {
    fn sample_uniform_bits<const RESAMPLE: bool>(
        &mut self,
        bits: usize,
    ) -> Result<usize, ResamplingError> {
        Ok(self.sample_bits(bits))
    }
}

impl GrindingChallenger for Transcript512 {
    type Witness = BabyBear;

    fn grind(&mut self, bits: usize) -> Self::Witness {
        if bits == 0 {
            return BabyBear::ZERO;
        }
        let initial = self.clone();
        for value in 0..BABY_BEAR_MODULUS {
            let witness = BabyBear::new(value);
            let mut trial = initial.clone();
            if trial.check_witness(bits, witness) {
                *self = trial;
                return witness;
            }
        }
        panic!("no grinding witness found")
    }
}

impl FieldChallenger<BabyBear> for Transcript512 {}

impl CanFinalizeDigest for Transcript512 {
    type Digest = [u8; 64];
    fn finalize(self) -> Self::Digest {
        self.state.to_bytes()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use p3_challenger::{CanObserve, CanSample};

    #[test]
    fn transcript_is_typed_and_deterministic() {
        let mut a = Transcript512::new(Digest512::ZERO, &[]);
        let mut b = a.clone();
        a.observe(BabyBear::new(1));
        b.observe(BabyBear::new(1));
        assert_eq!(a.state(), b.state());
        let ca: BabyBear = a.sample();
        let cb: BabyBear = b.sample();
        assert_eq!(ca, cb);
    }
    #[test]
    fn grinding_matches_single_witness_verification() {
        let mut prover = Transcript512::new(Digest512::ZERO, &[]);
        prover.observe(BabyBear::new(7));
        let mut verifier = prover.clone();
        let witness = prover.grind(8);
        assert!(verifier.check_witness(8, witness));
        let prover_sample: BabyBear = prover.sample();
        let verifier_sample: BabyBear = verifier.sample();
        assert_eq!(prover_sample, verifier_sample);
    }

    #[test]
    fn digest_halves_both_affect_nodes() {
        let a = digest_words(Digest512 {
            left: [1; 32],
            right: [2; 32],
        });
        let b = digest_words(Digest512 {
            left: [3; 32],
            right: [4; 32],
        });
        let baseline = ProofNodeCompressor.compress([a, b]);
        let mut changed = a;
        changed[7] ^= 1;
        assert_ne!(baseline, ProofNodeCompressor.compress([changed, b]));
    }
}
