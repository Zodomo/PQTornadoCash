use sha3::{Digest, Keccak256};
use std::collections::{HashMap, VecDeque};

pub const BABY_BEAR_MODULUS: u32 = 2_013_265_921;
const INIT: u8 = 0x42;
const ABSORB: u8 = 0x43;
const SQUEEZE: u8 = 0x44;
const ITEM_DIGEST: u8 = 0x45;
const BOUNDARY_FRAME: u8 = 0x46;
const FIELD: u8 = 1;
const COMMITMENT: u8 = 2;
const FIELD_ARRAY: u8 = 3;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Variant { T0, T1, T2, T3 }
impl Variant {
    pub const fn version(self) -> &'static [u8; 9] {
        match self { Self::T0 => b"PQTCT0-01", Self::T1 => b"PQTCT1-01", Self::T2 => b"PQTCT2-01", Self::T3 => b"PQTCT3-01" }
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct Metrics { pub keccak_calls: u64, pub hashed_bytes: u64, pub copied_bytes: u64, pub peak_frame_bytes: usize }

#[derive(Clone, Debug)]
pub struct Transcript {
    variant: Variant,
    state: [u8; 64],
    output: VecDeque<u8>,
    squeeze_counter: u64,
    pending: Vec<Vec<u8>>,
    pending_bytes: usize,
    pub rejected_words: u64,
    pub metrics: Metrics,
}

impl Transcript {
    pub fn new(variant: Variant, parameter: &[u8; 64], public_values: &[u32], production_compatible_t0: bool) -> Result<Self, &'static str> {
        for &value in public_values { canonical(value)?; }
        let mut payload = Vec::with_capacity(9 + 64 + 4 + public_values.len() * 4);
        if !(production_compatible_t0 && variant == Variant::T0) {
            payload.extend_from_slice(variant.version());
        }
        payload.extend_from_slice(parameter);
        if !(production_compatible_t0 && variant == Variant::T0) {
            payload.extend_from_slice(&u32::try_from(public_values.len()).map_err(|_| "public count overflow")?.to_be_bytes());
        }
        for &value in public_values { payload.extend_from_slice(&value.to_be_bytes()); }
        let mut transcript = Self { variant, state: [0; 64], output: VecDeque::new(), squeeze_counter: 0, pending: Vec::new(), pending_bytes: 0, rejected_words: 0, metrics: Metrics::default() };
        transcript.state = transcript.k512(INIT, &payload);
        Ok(transcript)
    }

    fn k512(&mut self, tag: u8, payload: &[u8]) -> [u8; 64] {
        let mut left = Keccak256::new(); left.update([0, tag]); left.update(payload);
        let mut right = Keccak256::new(); right.update([1, tag]); right.update(payload);
        let mut out = [0u8; 64]; out[..32].copy_from_slice(&left.finalize()); out[32..].copy_from_slice(&right.finalize());
        self.metrics.keccak_calls += 2;
        self.metrics.hashed_bytes += 2 * (2 + payload.len()) as u64;
        self.metrics.copied_bytes += (2 * (2 + payload.len()) + 64) as u64;
        out
    }

    fn reset_output(&mut self) { self.output.clear(); self.squeeze_counter = 0; }

    fn typed(&mut self, item_type: u8, payload: &[u8]) -> Result<(), &'static str> {
        validate_item(item_type, payload)?;
        match self.variant {
            Variant::T2 => {
                let mut item = Vec::with_capacity(9 + 1 + 4 + payload.len());
                item.extend_from_slice(self.variant.version()); item.push(item_type);
                item.extend_from_slice(&u32::try_from(payload.len()).map_err(|_| "item too long")?.to_be_bytes()); item.extend_from_slice(payload);
                let digest = self.k512(ITEM_DIGEST, &item);
                let mut state_item = Vec::with_capacity(128); state_item.extend_from_slice(&self.state); state_item.extend_from_slice(&digest);
                self.state = self.k512(ABSORB, &state_item); self.reset_output();
            }
            Variant::T3 => {
                let mut item = Vec::with_capacity(5 + payload.len()); item.push(item_type);
                item.extend_from_slice(&u32::try_from(payload.len()).map_err(|_| "item too long")?.to_be_bytes()); item.extend_from_slice(payload);
                self.pending_bytes += item.len(); self.metrics.copied_bytes += item.len() as u64;
                self.metrics.peak_frame_bytes = self.metrics.peak_frame_bytes.max(self.pending_bytes); self.pending.push(item);
            }
            Variant::T0 | Variant::T1 => {
                let mut input = Vec::with_capacity(69 + payload.len()); input.extend_from_slice(&self.state); input.push(item_type);
                input.extend_from_slice(&u32::try_from(payload.len()).map_err(|_| "item too long")?.to_be_bytes()); input.extend_from_slice(payload);
                self.state = self.k512(ABSORB, &input); self.reset_output();
            }
        }
        Ok(())
    }

    pub fn absorb_field(&mut self, value: u32) -> Result<(), &'static str> { canonical(value)?; self.typed(FIELD, &value.to_be_bytes()) }
    pub fn absorb_commitment(&mut self, digest: &[u8; 64]) -> Result<(), &'static str> { self.typed(COMMITMENT, digest) }
    pub fn absorb_fields(&mut self, values: &[u32]) -> Result<(), &'static str> {
        for &value in values { canonical(value)?; }
        if self.variant == Variant::T0 { for &value in values { self.absorb_field(value)?; } return Ok(()); }
        let mut payload = Vec::with_capacity(4 + values.len() * 4);
        payload.extend_from_slice(&u32::try_from(values.len()).map_err(|_| "array count overflow")?.to_be_bytes());
        for &value in values { payload.extend_from_slice(&value.to_be_bytes()); }
        self.typed(FIELD_ARRAY, &payload)
    }

    fn flush(&mut self) -> Result<(), &'static str> {
        if self.variant != Variant::T3 || self.pending.is_empty() { return Ok(()); }
        let mut items = Vec::with_capacity(self.pending_bytes); for item in &self.pending { items.extend_from_slice(item); }
        let mut frame = Vec::with_capacity(17 + items.len()); frame.extend_from_slice(self.variant.version());
        frame.extend_from_slice(&u32::try_from(self.pending.len()).map_err(|_| "frame count overflow")?.to_be_bytes());
        frame.extend_from_slice(&u32::try_from(items.len()).map_err(|_| "frame length overflow")?.to_be_bytes()); frame.extend_from_slice(&items);
        let mut input = Vec::with_capacity(64 + frame.len()); input.extend_from_slice(&self.state); input.extend_from_slice(&frame);
        self.state = self.k512(BOUNDARY_FRAME, &input); self.pending.clear(); self.pending_bytes = 0; self.reset_output(); Ok(())
    }

    fn take_bytes<const N: usize>(&mut self) -> Result<[u8; N], &'static str> {
        self.flush()?; let mut out = [0u8; N];
        for byte in &mut out {
            if self.output.is_empty() {
                let mut payload = [0u8; 72]; payload[..64].copy_from_slice(&self.state); payload[64..].copy_from_slice(&self.squeeze_counter.to_be_bytes());
                self.squeeze_counter = self.squeeze_counter.checked_add(1).ok_or("squeeze counter overflow")?;
                let block = self.k512(SQUEEZE, &payload);
                self.output.extend(block);
            }
            *byte = self.output.pop_front().ok_or("empty squeeze")?;
        }
        Ok(out)
    }

    pub fn sample_field(&mut self) -> Result<u32, &'static str> {
        loop { let value = u32::from_be_bytes(self.take_bytes()?) & 0x7fff_ffff; if value < BABY_BEAR_MODULUS { return Ok(value); } self.rejected_words += 1; }
    }
    pub fn sample_extension(&mut self) -> Result<[u32; 4], &'static str> {
        Ok([self.sample_field()?, self.sample_field()?, self.sample_field()?, self.sample_field()?])
    }
    pub fn sample_bits(&mut self, bits: usize) -> Result<u32, &'static str> {
        if bits > 31 { return Err("bits out of range"); }
        let value = u32::from_be_bytes(self.take_bytes()?); Ok(if bits == 0 { 0 } else { value & ((1u32 << bits) - 1) })
    }
    pub fn check_witness(&mut self, bits: usize, witness: u32) -> Result<bool, &'static str> {
        if bits == 0 { return Ok(true); }
        self.absorb_field(witness)?;
        Ok(self.sample_bits(bits)? == 0)
    }
    pub fn grind(&mut self, bits: usize) -> Result<u32, &'static str> {
        if bits == 0 { return Ok(0); }
        for witness in 0..BABY_BEAR_MODULUS {
            let mut trial = self.clone(); trial.absorb_field(witness)?;
            if trial.sample_bits(bits)? == 0 { *self = trial; return Ok(witness); }
        }
        Err("no PoW witness")
    }
    pub fn state(&mut self) -> Result<[u8; 64], &'static str> { self.flush()?; Ok(self.state) }
    pub fn pending_items(&self) -> usize { self.pending.len() }
}

pub fn canonical(value: u32) -> Result<(), &'static str> { if value < BABY_BEAR_MODULUS { Ok(()) } else { Err("noncanonical field") } }
pub fn decode_field_array(payload: &[u8]) -> Result<Vec<u32>, &'static str> {
    if payload.len() < 4 { return Err("truncated count"); }
    let count = u32::from_be_bytes(payload[..4].try_into().map_err(|_| "count width")?) as usize;
    if payload.len() != 4usize.checked_add(count.checked_mul(4).ok_or("array size overflow")?).ok_or("array size overflow")? { return Err("array count/length mismatch or trailing bytes"); }
    payload[4..].chunks_exact(4).map(|word| { let value = u32::from_be_bytes(word.try_into().map_err(|_| "field width")?); canonical(value)?; Ok(value) }).collect()
}
fn validate_item(item_type: u8, payload: &[u8]) -> Result<(), &'static str> {
    match item_type { FIELD if payload.len() == 4 => canonical(u32::from_be_bytes(payload.try_into().map_err(|_| "scalar width")?)), FIELD => Err("scalar width"), COMMITMENT if payload.len() == 64 => Ok(()), COMMITMENT => Err("commitment width"), FIELD_ARRAY => decode_field_array(payload).map(|_| ()), _ => Err("unknown item type") }
}

fn abi_word(label: &[u8]) -> Result<[u8; 32], &'static str> { if label.len() > 32 { return Err("ABI word overflow"); } let mut out = [0u8; 32]; out[..label.len()].copy_from_slice(label); Ok(out) }
fn keccak(input: &[u8]) -> [u8; 32] { Keccak256::digest(input).into() }
pub fn statement_key(parameter: &[u8; 64], public_values: &[u32]) -> Result<[u8; 32], &'static str> {
    if public_values.len() != 64 { return Err("full-width statement required"); }
    let mut encoded = Vec::with_capacity(67 * 32); encoded.extend_from_slice(&abi_word(b"PQTC.V3.STATEMENT")?); encoded.extend_from_slice(parameter);
    for &value in public_values { canonical(value)?; encoded.extend_from_slice(&[0; 28]); encoded.extend_from_slice(&value.to_be_bytes()); }
    Ok(keccak(&encoded))
}
pub fn checkpoint_digest(key: &[u8; 32], payload: &[u8]) -> Result<[u8; 32], &'static str> {
    let mut encoded = Vec::with_capacity(96); encoded.extend_from_slice(&abi_word(b"PQTC.V3.CHECKPOINT")?); encoded.extend_from_slice(key); encoded.extend_from_slice(&keccak(payload)); Ok(keccak(&encoded))
}
pub fn proof_id(key: &[u8; 32], part_a: &[u8]) -> Result<[u8; 32], &'static str> {
    let mut encoded = Vec::with_capacity(96); encoded.extend_from_slice(&abi_word(b"PQTC.V3.PROOF")?); encoded.extend_from_slice(key); encoded.extend_from_slice(&keccak(part_a)); Ok(keccak(&encoded))
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FullDigestRecord { pub parameter: [u8; 64], pub statement_digests: [[u8; 64]; 4], pub global_digest: [u8; 32], pub core_proof_digest: [u8; 32] }
#[derive(Default)]
pub struct FullDigestStore { records: HashMap<[u8; 32], FullDigestRecord> }
fn validate_statement_digests(public_values: &[u32], digests: &[[u8; 64]; 4]) -> Result<(), &'static str> {
    if public_values.len() != 64 { return Err("full-width statement required"); }
    for (index, word) in digests.iter().flat_map(|digest| digest.chunks_exact(4)).enumerate() {
        let value = u32::from_be_bytes(word.try_into().map_err(|_| "statement field width")?);
        canonical(value)?;
        if value != public_values[index] { return Err("statement digest/public field mismatch"); }
    }
    Ok(())
}
impl FullDigestStore {
    pub fn put(&mut self, public_values: &[u32], record: FullDigestRecord) -> Result<[u8; 32], &'static str> {
        validate_statement_digests(public_values, &record.statement_digests)?;
        let key = statement_key(&record.parameter, public_values)?; self.records.insert(key, record); Ok(key)
    }
    pub fn get_checked(&self, key: &[u8; 32], public_values: &[u32], supplied: &FullDigestRecord) -> Result<&FullDigestRecord, &'static str> {
        let stored = self.records.get(key).ok_or("unknown lookup key")?;
        if &statement_key(&stored.parameter, public_values)? != key { return Err("stored full statement/key mismatch"); }
        validate_statement_digests(public_values, &stored.statement_digests)?;
        if stored != supplied { return Err("full-width digest mismatch"); }
        Ok(stored)
    }
}
