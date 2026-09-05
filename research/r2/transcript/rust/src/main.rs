use std::{fs, path::{Path,PathBuf}, time::Instant};
use p3_field::PrimeCharacteristicRing;
use pqtc_r2_transcript::{QUERY_COUNT, QUERY_SPLITS};
use pqtc_r2_transcript::{codec::{encode_proof_parts,decode_proof_parts,replay_checkpoint,COMMON_HEADER_BYTES,GLOBAL_DATA_BYTES}, crypto::Transcript512, prove_withdrawal,verify_withdrawal,withdrawal_config_from_os_entropy,withdrawal_public_values,SecurityProfile,Val,WithdrawalWitness};
use pqtc_spec::{Digest512,WithdrawalStatement};
use pqtc_hash::{k512,keccak256};
use serde_json::{json,Value};
type Result<T, E = Box<dyn std::error::Error>> = std::result::Result<T,E>;
const FROZEN_PARAMETER:&str="35adfcc070249bb0393c2fd45f0bbd48ef03cbfc08070d03335eaf952975e62ab7bc82ead4f8c1f1c39b3372be85195853134dfc9d24f43b97a5e0454ea07779";
fn arg(name:&str)->Option<String>{let args:Vec<_>=std::env::args().collect();args.windows(2).find(|x|x[0]==name).map(|x|x[1].clone())}
fn save(path:impl AsRef<Path>,v:&impl serde::Serialize)->Result<()> {fs::write(path,serde_json::to_vec_pretty(v)?)?;Ok(())}
fn parse_hex<const N:usize>(s:&str)->Result<[u8;N]>{hex::decode(s.trim_start_matches("0x"))?.try_into().map_err(|_|"hex length".into())}
fn abi_word(n:usize)->[u8;32]{let mut b=[0;32];b[24..].copy_from_slice(&(n as u64).to_be_bytes());b}
fn abi_call(signature:&str,static_args:&[u8],dynamic:&[&[u8]])->Vec<u8>{
    let mut out=keccak256(signature.as_bytes())[..4].to_vec();out.extend_from_slice(static_args);
    let mut offset=static_args.len()+32*dynamic.len();for d in dynamic {out.extend_from_slice(&abi_word(offset));offset+=32+d.len().div_ceil(32)*32;}
    for d in dynamic {out.extend_from_slice(&abi_word(d.len()));out.extend_from_slice(d);out.resize(out.len()+((32-d.len()%32)%32),0);}out
}
fn static_args(parameter:Digest512,statement:WithdrawalStatement)->Vec<u8>{let mut b=parameter.to_bytes().to_vec();for v in statement.public_values(){b.extend_from_slice(&abi_word(v as usize));}b}
fn verification_id(core:[u8;64],consumer:[u8;20])->[u8;32]{let mut b=b"PQTC.R2.V4.VERIFICATION".to_vec();b.resize(32,0);b.extend_from_slice(&core);b.extend_from_slice(&[0;12]);b.extend_from_slice(&consumer);keccak256(&b)}
fn ledger(bytes:&[u8],part_b:bool)->Value {
    let mut sections=Vec::new();let mut at=0;
    let mut add=|name:String,len:usize|{sections.push(json!({"name":name,"offset":at,"bytes":len}));at+=len;};
    add("header".into(),COMMON_HEADER_BYTES);if part_b{add("core_proof_binding_512".into(),64);}add("global_binding_512".into(),64);add("global".into(),GLOBAL_DATA_BYTES);
    let cp=COMMON_HEADER_BYTES+if part_b{64}else{0}+64+GLOBAL_DATA_BYTES;
    let unique_at = 386 + QUERY_COUNT * 4;
    let unique=u16::from_be_bytes(bytes[cp+unique_at..cp+unique_at+2].try_into().unwrap()) as usize;
    add("checkpoint_512".into(),388+QUERY_COUNT*4+unique*4);
    let half=cp+388+QUERY_COUNT*4+unique*4;let q=u16::from_be_bytes(bytes[half+2..half+4].try_into().unwrap()) as usize;
    add("query_header_and_indices".into(),4+q*4);
    drop(add);
    for (batch,(matrices,width)) in [(1,8),(1,194),(16,8)].into_iter().enumerate(){
        let rows=q*matrices*width*4;sections.push(json!({"name":format!("input_{batch}_rows"),"offset":at,"bytes":rows}));at+=rows;
        let salts=q*matrices*8*4;sections.push(json!({"name":format!("input_{batch}_salts"),"offset":at,"bytes":salts}));at+=salts;
        let n=u32::from_be_bytes(bytes[at..at+4].try_into().unwrap()) as usize;let len=4+n*64;sections.push(json!({"name":format!("input_{batch}_frontier"),"offset":at,"bytes":len,"digest_count":n}));at+=len;
    }
    for round in 0..9 {let len=q*48;sections.push(json!({"name":format!("fri_{round}_siblings_salts"),"offset":at,"bytes":len}));at+=len;let n=u32::from_be_bytes(bytes[at..at+4].try_into().unwrap()) as usize;let len=4+n*64;sections.push(json!({"name":format!("fri_{round}_frontier"),"offset":at,"bytes":len,"digest_count":n}));at+=len;}
    sections.push(json!({"name":"end","offset":at,"bytes":4}));at+=4;assert_eq!(at,bytes.len());
    json!({"sections":sections,"raw_bytes":at,"zero_bytes":bytes.iter().filter(|&&v|v==0).count(),"nonzero_bytes":bytes.iter().filter(|&&v|v!=0).count()})
}
fn misuse()->Value {
    let new=||Transcript512::new(Digest512::default(),&[Val::ZERO;64]);let mut cases=Vec::new();
    let mut t=new();cases.push(("early",t.try_field().is_err()));
    for (name,epoch,slot,kind,payload) in [("cross_phase",1,0,1,vec![0;4]),("reordered",0,1,1,vec![0;4]),("wrong_type",0,0,2,vec![0;64]),("empty",0,0,1,vec![]),("noncanonical",0,0,1,2013265921u32.to_be_bytes().to_vec())]{let mut t=new();cases.push((name,t.observe_frame(epoch,slot,kind,&payload).is_err()));}
    let mut t=new();t.observe_frame(0,0,1,&[0;4]).unwrap();cases.push(("duplicate",t.observe_frame(0,0,1,&[0;4]).is_err()));cases.push(("missing",t.try_field().is_err()));
    assert!(cases.iter().all(|x|x.1));json!(cases)
}
fn frozen_control(out:&Path,parameter:Digest512,statement:WithdrawalStatement,witness:&WithdrawalWitness,consumer:[u8;20])->Result<()> {
    let out=out.join("frozen-control");fs::create_dir_all(&out)?;
    let profile=pqtc_stark::SecurityProfile::SepoliaV03;
    let config=pqtc_stark::withdrawal_config_from_os_entropy(profile,parameter,statement);
    let start=Instant::now();let proof=pqtc_stark::prove_withdrawal(&config,statement,witness)?;let prove_ms=start.elapsed().as_secs_f64()*1000.;
    let start=Instant::now();assert!(pqtc_stark::verify_withdrawal(&config,statement,&proof));let verify_ms=start.elapsed().as_secs_f64()*1000.;
    let parts=pqtc_stark::codec::encode_proof_parts(&proof,profile,parameter,statement)?;
    fs::write(out.join("proof.postcard"),postcard::to_allocvec(&proof)?)?;
    fs::write(out.join("part-a.pqtc"),&parts.part_a.bytes)?;fs::write(out.join("part-b.pqtc"),&parts.part_b.bytes)?;
    let mut b=b"PQTC.V3.VERIFICATION".to_vec();b.resize(32,0);b.extend_from_slice(&parts.part_a.proof_id);b.extend_from_slice(&[0;12]);b.extend_from_slice(&consumer);let id=keccak256(&b);
    let args=static_args(parameter,statement);let mut complete=id.to_vec();complete.extend_from_slice(&args);
    let a=abi_call("beginVerification((bytes32,bytes32),uint32[64],bytes)",&args,&[&parts.part_a.bytes]);
    let b=abi_call("completeVerification(bytes32,(bytes32,bytes32),uint32[64],bytes)",&complete,&[&parts.part_b.bytes]);
    fs::write(out.join("part-a.calldata"),&a)?;fs::write(out.join("part-b.calldata"),&b)?;
    save(out.join("results.json"),&json!({"configuration":"frozen-H0-q32-transcript-v3","relation":"same supplied H0 statement and witness; parameter same as experiment for causal comparison","parameter_id":parameter.to_string(),"public_values":statement.public_values().to_vec(),"consumer":hex::encode(consumer),"verification_id":"0x".to_owned()+&hex::encode(id),"native_verified":true,"prove_ms":prove_ms,"verify_ms":verify_ms,"raw_a_bytes":parts.part_a.bytes.len(),"raw_b_bytes":parts.part_b.bytes.len(),"abi_a_bytes":a.len(),"abi_b_bytes":b.len(),"measurement_class":"fresh_native_full_path_single_sample","promotion":false}))
}

fn main()->Result<()> {
    let out=PathBuf::from(arg("--out").unwrap_or_else(||"research/r2/transcript/outputs".into()));fs::create_dir_all(&out)?;
    let input=PathBuf::from(arg("--input").unwrap_or_else(||"research/candidates/v03-baseline/proofs/v03-fixed-01".into()));
    let statement_path=arg("--statement").map(PathBuf::from).unwrap_or_else(||input.join("statement.json"));
    let witness_path=arg("--witness").map(PathBuf::from).unwrap_or_else(||input.join("witness.json"));
    let statement:WithdrawalStatement=serde_json::from_slice(&fs::read(&statement_path)?)?;let witness:WithdrawalWitness=serde_json::from_slice(&fs::read(&witness_path)?)?;
    let parameter=if let Some(p)=arg("--parameter-id"){Digest512::from_bytes(parse_hex(&p)?)}else{let mut payload=format!("PQTC.R2.T3-02.H0.Q{}",QUERY_COUNT).into_bytes();payload.extend_from_slice(&parse_hex::<64>(FROZEN_PARAMETER)?);k512(0x47,&payload)};
    let consumer=parse_hex::<20>(&arg("--consumer").unwrap_or_else(||"f39fd6e51aad88f6f4ce6ab8827279cfffb92266".into()))?;
    let profile=SecurityProfile::SepoliaV03;let config=withdrawal_config_from_os_entropy(profile,parameter,statement);
    let start=Instant::now();let proof=if let Some(path)=arg("--proof"){postcard::from_bytes(&fs::read(path)?)?}else{prove_withdrawal(&config,statement,&witness)?};let prove_ms=start.elapsed().as_secs_f64()*1000.;
    let start=Instant::now();assert!(verify_withdrawal(&config,statement,&proof));let verify_ms=start.elapsed().as_secs_f64()*1000.;
    fs::write(out.join("proof.postcard"),postcard::to_allocvec(&proof)?)?;save(out.join("statement.json"),&statement)?;save(out.join("witness.json"),&witness)?;
    let mut split_results=Vec::new();
    for &split in QUERY_SPLITS {
        let dir=out.join(format!("split-{split}"));fs::create_dir_all(&dir)?;let start=Instant::now();
        let parts=encode_proof_parts(&proof,profile,parameter,statement,split)?;let encode_ms=start.elapsed().as_secs_f64()*1000.;
        let roundtrip=decode_proof_parts(&parts.part_a.bytes,&parts.part_b.bytes,profile,parameter,statement,split)?;assert!(verify_withdrawal(&config,statement,&roundtrip));
        fs::write(dir.join("part-a.pqtc"),&parts.part_a.bytes)?;fs::write(dir.join("part-b.pqtc"),&parts.part_b.bytes)?;
        let id=verification_id(parts.part_a.proof_id,consumer);let args=static_args(parameter,statement);let mut complete=id.to_vec();complete.extend_from_slice(&args);
        let ca=abi_call("beginVerification((bytes32,bytes32),uint32[64],bytes)",&args,&[&parts.part_a.bytes]);let cb=abi_call("completeVerification(bytes32,(bytes32,bytes32),uint32[64],bytes)",&complete,&[&parts.part_b.bytes]);let direct=abi_call("verifyOneCall((bytes32,bytes32),uint32[64],bytes,bytes)",&args,&[&parts.part_a.bytes,&parts.part_b.bytes]);
        for(name,bytes)in[("part-a.calldata",&ca),("part-b.calldata",&cb),("one-call.calldata",&direct)]{fs::write(dir.join(name),bytes)?;}
        let mut mutations=Vec::new();
        for part in 0..2 {let original=if part==0{&parts.part_a.bytes}else{&parts.part_b.bytes};let mut offsets=vec![0,9,16,20,52,COMMON_HEADER_BYTES,COMMON_HEADER_BYTES+32,original.len()-5];
            let cp=COMMON_HEADER_BYTES+if part==1{64}else{0}+64+GLOBAL_DATA_BYTES;offsets.extend([cp,cp+32,cp+64,cp+96,cp+128,cp+160]);
            for at in offsets {let mut mutated=original.clone();mutated[at]^=1;let(a,b)=if part==0{(mutated.as_slice(),parts.part_b.bytes.as_slice())}else{(parts.part_a.bytes.as_slice(),mutated.as_slice())};let accepted=std::panic::catch_unwind(std::panic::AssertUnwindSafe(||decode_proof_parts(a,b,profile,parameter,statement,split).is_ok_and(|p|verify_withdrawal(&config,statement,&p)))).unwrap_or(false);assert!(!accepted,"mutation accepted");mutations.push(json!({"part":part,"offset":at,"rejected":!accepted}));}
            for mode in ["trailing","truncated"]{let mut m=original.clone();if mode=="trailing"{m.push(0)}else{m.pop();}let(a,b)=if part==0{(m.as_slice(),parts.part_b.bytes.as_slice())}else{(parts.part_a.bytes.as_slice(),m.as_slice())};assert!(decode_proof_parts(a,b,profile,parameter,statement,split).is_err());mutations.push(json!({"part":part,"mode":mode,"rejected":true}));}
        }
        let row=json!({"first_queries":split,"second_queries":QUERY_COUNT-split,"encode_ms":encode_ms,"native_verified":true,"codec_roundtrip_verified":true,"proof_id":"0x".to_owned()+&hex::encode(parts.part_a.proof_id),"verification_id":"0x".to_owned()+&hex::encode(id),"statement_binding":"0x".to_owned()+&hex::encode(parts.part_a.statement_key),"checkpoint_binding":"0x".to_owned()+&hex::encode(parts.part_a.checkpoint.digest),"global_binding":"0x".to_owned()+&hex::encode(parts.part_a.checkpoint.global_digest),"part_a":ledger(&parts.part_a.bytes,false),"part_b":ledger(&parts.part_b.bytes,true),"abi_a_bytes":ca.len(),"abi_b_bytes":cb.len(),"abi_direct_bytes":direct.len(),"signed_envelope_bytes":null,"mutations":mutations});save(dir.join("results.json"),&row)?;split_results.push(row);
        if split==*QUERY_SPLITS.last().unwrap() {let (_,events)=replay_checkpoint(&proof,profile,parameter,statement,parts.part_a.checkpoint.global_digest)?;save(out.join("transcript-vectors.json"),&json!({"parameter_id":parameter.to_string(),"public_values":statement.public_values().to_vec(),"events":events,"query_count":QUERY_COUNT}))?;}
    }
    if QUERY_COUNT==32 && std::env::args().any(|a|a=="--compare-frozen") { frozen_control(&out,parameter,statement,&witness,consumer)?; }
    save(out.join("results.json"),&json!({"package":"R2-05","candidate_id":"R2-C0","configuration":format!("T3-02-H0-q{}-v4-full512",QUERY_COUNT),"query_count":QUERY_COUNT,"parameter_id":parameter.to_string(),"public_values":statement.public_values().to_vec(),"consumer":"0x".to_owned()+&hex::encode(consumer),"specification":"compiled query schedule enforced; H0 withdrawal predicate unchanged","correctness":{"native_verified":true,"misuse":misuse()},"privacy":"upstream HidingFriPcs+MerkleTreeHidingMmcs; experimental unqualified","security":"compiled query profile and new transcript unqualified; no security promotion","performance":{"measurement_class":"fresh_native_full_path_single_sample","prove_ms":prove_ms,"verify_ms":verify_ms,"proof_reused":arg("--proof").is_some()},"stage":"native-proof-codec-mutations-executed","promotion":false,"splits":split_results,"command":std::env::args().collect::<Vec<_>>() }))?;
    println!("{}",out.join("results.json").display());Ok(())
}
