//! R2-H5-complete-v1, experimental and security-not-qualified.
use p3_baby_bear::{BabyBear, Poseidon2BabyBear, default_babybear_poseidon2_32};
use p3_field::{PrimeCharacteristicRing, PrimeField32};
use p3_symmetric::Permutation;
use std::sync::LazyLock;
pub mod reference;
pub type Digest = [BabyBear; 12];
pub type Secret = [BabyBear; 8];
pub const VERSION: u32 = 2001;
pub const WIDTH: usize = 32;
pub const MODULUS: u32 = 2013265921;
pub static PERMUTATION: LazyLock<Poseidon2BabyBear<32>> = LazyLock::new(default_babybear_poseidon2_32);
pub fn compress(input: [BabyBear;32]) -> Digest {
    let output = PERMUTATION.permute(input);
    std::array::from_fn(|i| output[i] + input[i])
}
fn controls(state: &mut [BabyBear;32], at:usize, role:u32, count:u32, level:u32) {
    state[at..at+4].copy_from_slice(&[role,VERSION,count,level].map(BabyBear::new));
}
pub fn note_input(scope:Digest, secret:Secret, trapdoor:Secret) -> [BabyBear;32] {
    let mut x=[BabyBear::ZERO;32]; x[..12].copy_from_slice(&scope); x[12..20].copy_from_slice(&secret); x[20..28].copy_from_slice(&trapdoor); controls(&mut x,28,2,28,0); x
}
pub fn nullifier_input(scope:Digest, secret:Secret) -> [BabyBear;32] {
    let mut x=[BabyBear::ZERO;32]; x[..12].copy_from_slice(&scope); x[12..20].copy_from_slice(&secret); controls(&mut x,20,3,20,0); x
}
pub fn node_input(level:u8, left:Digest, right:Digest) -> [BabyBear;32] {
    assert!(level<20,"invalid tree level"); let mut x=[BabyBear::ZERO;32]; x[..12].copy_from_slice(&left); x[12..24].copy_from_slice(&right); controls(&mut x,24,5,24,u32::from(level)); x
}
pub fn empty_input(scope:Digest) -> [BabyBear;32] {
    let mut x=[BabyBear::ZERO;32]; x[..12].copy_from_slice(&scope); controls(&mut x,28,4,12,0); x
}
pub fn note(scope:Digest, secret:Secret, trapdoor:Secret)->Digest {compress(note_input(scope,secret,trapdoor))}
pub fn nullifier(scope:Digest, secret:Secret)->Digest {compress(nullifier_input(scope,secret))}
pub fn node(level:u8,left:Digest,right:Digest)->Digest {compress(node_input(level,left,right))}
pub fn empty(scope:Digest)->Digest {compress(empty_input(scope))}
pub fn public_inputs(role:u32,length:u32,payload:&[BabyBear])->Vec<[BabyBear;32]> {
    assert!(matches!((role,length,payload.len()),(1,129,65)|(6,72,36)|(7,48,48)));
    if role!=7 { assert!(payload.iter().all(|x| x.as_canonical_u32()<=65535)); }
    if role==1 { assert_eq!(payload[64].as_canonical_u32()&255,0); }
    let mut result=Vec::with_capacity((payload.len()+1).div_ceil(16)); let mut chain=[BabyBear::ZERO;12];
    for block in 0..(payload.len()+1).div_ceil(16) {
        let mut x=[BabyBear::ZERO;32]; x[..12].copy_from_slice(&chain);
        for i in 0..16 {let j=block*16+i; x[12+i]=if j<payload.len(){payload[j]}else if j==payload.len(){BabyBear::ONE}else{BabyBear::ZERO};}
        controls(&mut x,28,role,length,block as u32); if block+1<(payload.len()+1).div_ceil(16){chain=compress(x);} result.push(x);
    } result
}
fn public_hash(role:u32,length:u32,payload:&[BabyBear])->Digest {compress(*public_inputs(role,length,payload).last().unwrap())}
fn bytes_fields(bytes:&[u8])->Vec<BabyBear> {bytes.chunks(2).map(|x| BabyBear::new(u32::from(u16::from_be_bytes([x[0],*x.get(1).unwrap_or(&0)])))).collect()}
pub fn scope(bytes:&[u8;129])->Digest {public_hash(1,129,&bytes_fields(bytes))}
pub fn payout(bytes:&[u8;72])->Digest {public_hash(6,72,&bytes_fields(bytes))}
pub fn statement(scope:Digest,root:Digest,nullifier:Digest,payout:Digest)->Digest {
    let mut fields=[BabyBear::ZERO;48]; for (slot,value) in fields.chunks_exact_mut(12).zip([scope,root,nullifier,payout]){slot.copy_from_slice(&value);} public_hash(7,48,&fields)
}
#[derive(serde::Serialize,serde::Deserialize,Clone)]
#[serde(deny_unknown_fields)]
pub struct Request { pub config:String, pub role:u32, pub level:u32, pub payload:Vec<u32> }
/// Strict shared wire entrypoint. No expected output is accepted by any implementation.
pub fn evaluate(r:&Request,reference:bool)->Result<Vec<u32>,String> {
    if r.payload.iter().any(|&x|x>=MODULUS){return Err("noncanonical field".into());}
    let h0=r.config=="R2-H0-v03"; if !h0 && r.config!="R2-H5-complete-v1" {return Err("unknown configuration".into());}
    let d=if h0{16}else{12}; let expected=match r.role{1=>65,2=>d+16,3=>d+8,4=>d,5=>2*d,6=>36,7=>4*d,8|9=>if h0{16}else{32},10|11 if !h0=>32,_=>return Err("unknown role".into())};
    if r.payload.len()!=expected || (r.role==5 && r.level>=20) || (r.role!=5 && r.level!=0) {return Err("shape/level".into());}
    if matches!(r.role,1|6) && (r.payload.iter().any(|&x|x>65535)||(r.role==1 && r.payload[64]&255!=0)){return Err("noncanonical bytes".into());}
    if r.role>=8 {
        let p=if reference {reference::permute(&r.payload)} else if h0 {
            use p3_baby_bear::default_babybear_poseidon2_16;
            let x:[BabyBear;16]=std::array::from_fn(|i|BabyBear::new(r.payload[i]));
            default_babybear_poseidon2_16().permute(x).map(|v|v.as_canonical_u32()).to_vec()
        } else {
            let x:[BabyBear;32]=std::array::from_fn(|i|BabyBear::new(r.payload[i]));
            PERMUTATION.permute(x).map(|v|v.as_canonical_u32()).to_vec()
        };
        // 10/11 are isolated fault-injection kernels, never application domains.
        return Ok(if r.role==8{p}else{let count=if r.role==11{14}else{d};p[..count].iter().enumerate().map(|(i,&v)|((u64::from(v)+u64::from(r.payload[if r.role==10{i+1}else{i}]))%u64::from(MODULUS))as u32).collect()});
    }
    if h0 {let tag=[0,16,17,18,19,32,20,21][r.role as usize];let bytes=if r.role==1{129}else if r.role==6{72}else{r.payload.len()as u32*4};if reference{return Ok(reference::sponge(tag,bytes,r.level,&r.payload));}let fields:Vec<_>=r.payload.iter().copied().map(BabyBear::new).collect();return Ok(pqtc_hash::digest_to_elements(pqtc_hash::p2bb512(tag,bytes,r.level,&fields)).unwrap().map(|x|x.as_canonical_u32()).to_vec());}
    if !reference {
        let digest=|at:usize|->Digest{std::array::from_fn(|i|BabyBear::new(r.payload[at+i]))};
        let secret=|at:usize|->Secret{std::array::from_fn(|i|BabyBear::new(r.payload[at+i]))};
        let output=match r.role {
            1=>{let bytes:[u8;129]=std::array::from_fn(|i|(r.payload[i/2]>>if i%2==0{8}else{0})as u8);scope(&bytes)},
            2=>note(digest(0),secret(12),secret(20)),
            3=>nullifier(digest(0),secret(12)),
            4=>empty(digest(0)),
            5=>node(r.level as u8,digest(0),digest(12)),
            6=>{let bytes:[u8;72]=std::array::from_fn(|i|(r.payload[i/2]>>if i%2==0{8}else{0})as u8);payout(&bytes)},
            7=>statement(digest(0),digest(12),digest(24),digest(36)),
            _=>unreachable!(),
        };
        return Ok(output.map(|v|v.as_canonical_u32()).to_vec());
    }
    let compress_u32=|x:[u32;32]|->Vec<u32>{let y=reference::permute(&x);(0..12).map(|i|((u64::from(y[i])+u64::from(x[i]))%u64::from(MODULUS))as u32).collect()};
    if matches!(r.role,1|6|7){let mut chain=vec![0;12];for b in 0..(r.payload.len()+1).div_ceil(16){let mut x=[0;32];x[..12].copy_from_slice(&chain);for i in 0..16{let j=b*16+i;x[12+i]=if j<r.payload.len(){r.payload[j]}else if j==r.payload.len(){1}else{0};}let len=match r.role{1=>129,6=>72,_=>48};x[28..].copy_from_slice(&[r.role,VERSION,len,b as u32]);chain=compress_u32(x);}return Ok(chain);}
    let mut x=[0;32];x[..r.payload.len()].copy_from_slice(&r.payload);let at=match r.role{3=>20,5=>24,_=>28};x[at..at+4].copy_from_slice(&[r.role,VERSION,r.payload.len()as u32,r.level]);Ok(compress_u32(x))
}
