//! R2 T3-02: H0 hashing, runtime-checked q32 challenge epochs.
use std::collections::VecDeque;
use p3_baby_bear::BabyBear;
use p3_challenger::{CanFinalizeDigest, CanObserve, CanSample, CanSampleBits, CanSampleUniformBits, FieldChallenger, GrindingChallenger, ResamplingError};
use p3_field::{BasedVectorSpace, PrimeCharacteristicRing, PrimeField32};
use p3_symmetric::MerkleCap;
use pqtc_hash::k512;
use pqtc_spec::{BABY_BEAR_MODULUS, Digest512};
#[path = "../../../../../crates/pqtc-stark/src/crypto.rs"]
mod h0;
pub use h0::{DIGEST_WORDS, ProofLeafHasher, ProofNodeCompressor, proof_leaf_digest, proof_node_digest, digest_words, words_digest};
pub const VERSION: &[u8] = b"PQTCT3-02";

#[derive(Clone, Debug, serde::Serialize)]
pub struct Event {
    pub epoch: u16, pub operation: &'static str, pub canonical: String,
    pub before: String, pub after: String, pub value: Option<u32>, pub rejected: Vec<u32>,
}
#[derive(Clone, Debug)]
pub struct Transcript512 {
    state: Digest512, output: VecDeque<u8>, counter: u64,
    epoch: u16, slot: u16, pending: Vec<u8>, remaining: u16, pow: bool,
    recording: bool, pub events: Vec<Event>,
}
impl Transcript512 {
    pub fn new(parameter: Digest512, pv: &[BabyBear]) -> Self {
        assert_eq!(pv.len(), 64, "R2 q32 H0 public values");
        let mut payload = VERSION.to_vec();
        payload.extend_from_slice(&parameter.to_bytes());
        payload.extend_from_slice(&(pv.len() as u32).to_be_bytes());
        for v in pv { payload.extend_from_slice(&v.as_canonical_u32().to_be_bytes()); }
        Self { state: k512(0x42,&payload), output: VecDeque::new(), counter:0,
            epoch:0, slot:0, pending:Vec::new(), remaining:0, pow:false, recording:false, events:Vec::new() }
    }
    pub fn record(&mut self) { self.recording = true; }
    pub fn position(&self) -> (u16,u16) { (self.epoch,self.slot) }
    pub fn state(&self) -> Digest512 { assert!(self.pending.is_empty()); self.state }
    fn count(&self) -> u16 { match self.epoch { 0=>68,1=>2,2=>2096,3..=11=>2,12=>14,_=>0 } }
    fn kind(&self) -> u8 { match self.epoch { 0 if self.slot==3=>2,1=>2,3..=11 if self.slot==0=>2,_=>1 } }
    /// Authoritative wire API. Explicit epoch/slot are checked, not diagnostic labels.
    pub fn observe_frame(&mut self, epoch:u16, slot:u16, kind:u8, bytes:&[u8]) -> Result<(), &'static str> {
        if epoch!=self.epoch || slot!=self.slot || self.remaining!=0 || slot>=self.count() { return Err("phase/order/count"); }
        if kind!=self.kind() || bytes.len()!=if kind==1 {4}else{64} { return Err("type/length"); }
        if kind==1 && u32::from_be_bytes(bytes.try_into().unwrap())>=BABY_BEAR_MODULUS { return Err("noncanonical field"); }
        self.pending.push(kind); self.pending.extend_from_slice(&slot.to_be_bytes());
        self.pending.extend_from_slice(&(bytes.len() as u32).to_be_bytes()); self.pending.extend_from_slice(bytes);
        self.slot+=1; Ok(())
    }
    fn observe_raw(&mut self, kind:u8, bytes:&[u8]) { self.observe_frame(self.epoch,self.slot,kind,bytes).expect("invalid transcript observation"); }
    fn flush(&mut self) -> Result<(), &'static str> {
        if self.remaining!=0 { return Ok(()); }
        if self.epoch>12 || self.slot!=self.count() { return Err("early/missing challenge observation"); }
        let before=self.state;
        let mut frame=VERSION.to_vec(); frame.extend_from_slice(&self.epoch.to_be_bytes());
        frame.extend_from_slice(&(self.slot as u32).to_be_bytes()); frame.extend_from_slice(&(self.pending.len() as u32).to_be_bytes()); frame.append(&mut self.pending);
        let mut payload=self.state.to_bytes().to_vec(); payload.extend_from_slice(&frame);
        self.state=k512(0x46,&payload); self.output.clear(); self.counter=0;
        self.pow=self.epoch>=3; self.remaining=if self.epoch==12 {crate::QUERY_COUNT as u16 + 1}else if self.pow {5}else{4};
        if self.recording { self.events.push(Event{epoch:self.epoch,operation:"frame",canonical:hex::encode(frame),before:hex::encode(before.to_bytes()),after:hex::encode(self.state.to_bytes()),value:None,rejected:vec![]}); }
        Ok(())
    }
    fn word(&mut self)->u32 {
        if self.output.is_empty() { let mut payload=self.state.to_bytes().to_vec(); payload.extend_from_slice(&self.counter.to_be_bytes()); self.counter=self.counter.checked_add(1).unwrap(); self.output.extend(k512(0x44,&payload).to_bytes()); }
        u32::from_be_bytes(core::array::from_fn(|_| self.output.pop_front().unwrap()))
    }
    fn consume(&mut self, value:u32, rejected:Vec<u32>, operation:&'static str) {
        if self.recording { let s=hex::encode(self.state.to_bytes()); self.events.push(Event{epoch:self.epoch,operation,canonical:String::new(),before:s.clone(),after:s,value:Some(value),rejected}); }
        self.remaining-=1; if self.remaining==0 {self.epoch+=1;self.slot=0;}
    }
    pub fn try_field(&mut self)->Result<u32,&'static str> {
        self.flush()?; if self.pow || self.epoch==12 {return Err("wrong challenge kind");}
        let mut rejected=Vec::new(); loop {let v=self.word()&0x7fff_ffff; if v<BABY_BEAR_MODULUS {self.consume(v,rejected,"field");return Ok(v);} if self.recording {rejected.push(v);} }
    }
    pub fn try_bits(&mut self,bits:usize)->Result<u32,&'static str> {
        self.flush()?; if bits!=if self.pow {16}else if self.epoch==12 {13}else{return Err("wrong challenge kind")} {return Err("bit count");}
        let v=self.word()&((1u32<<bits)-1); self.pow=false; self.consume(v,vec![],"bits"); Ok(v)
    }
    pub fn finished(&self)->bool {self.epoch==13 && self.remaining==0 && self.pending.is_empty()}
}
impl CanObserve<BabyBear> for Transcript512 {fn observe(&mut self,v:BabyBear){self.observe_raw(1,&v.as_canonical_u32().to_be_bytes());}}
impl CanObserve<MerkleCap<BabyBear,[u64;8]>> for Transcript512 {fn observe(&mut self,c:MerkleCap<BabyBear,[u64;8]>){self.observe(&c);}}
impl CanObserve<&MerkleCap<BabyBear,[u64;8]>> for Transcript512 {fn observe(&mut self,c:&MerkleCap<BabyBear,[u64;8]>){assert_eq!(c.num_roots(),1);self.observe_raw(2,&words_digest(c.roots()[0]).to_bytes());}}
impl<EF:BasedVectorSpace<BabyBear>> CanSample<EF> for Transcript512 {fn sample(&mut self)->EF {EF::from_basis_coefficients_fn(|_| BabyBear::new(self.try_field().expect("invalid transcript sample")))}}
impl CanSampleBits<usize> for Transcript512 {fn sample_bits(&mut self,bits:usize)->usize {self.try_bits(bits).expect("invalid transcript bits") as usize}}
impl CanSampleUniformBits<BabyBear> for Transcript512 {fn sample_uniform_bits<const R:bool>(&mut self,bits:usize)->Result<usize,ResamplingError>{Ok(self.sample_bits(bits))}}
impl GrindingChallenger for Transcript512 {
    type Witness=BabyBear;
    fn grind(&mut self,bits:usize)->BabyBear {assert_eq!(bits,16);let initial=self.clone();for v in 0..BABY_BEAR_MODULUS {let mut trial=initial.clone();let w=BabyBear::new(v);if trial.check_witness(bits,w){*self=trial;return w;}}panic!("no witness")}
}
impl FieldChallenger<BabyBear> for Transcript512 {}
impl CanFinalizeDigest for Transcript512 {type Digest=[u8;64];fn finalize(self)->Self::Digest {assert!(self.finished());self.state.to_bytes()}}
