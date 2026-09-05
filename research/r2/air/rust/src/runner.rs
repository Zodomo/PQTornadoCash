use std::{path::{Path,PathBuf},time::Instant,collections::BTreeSet};
use anyhow::{Result,ensure,Context};
use clap::Parser;
use serde::{Serialize,Deserialize};
use serde_json::{Value,json};
use sha3::{Digest,Keccak256};
use rand::{SeedableRng,rngs::StdRng};
use p3_air::{Air,BaseAir,DebugConstraintBuilder,check_all_constraints,symbolic::{AirLayout,get_symbolic_constraints,get_max_constraint_degree}};
use p3_baby_bear::BabyBear;
use p3_field::{PrimeCharacteristicRing,PrimeField32};
use p3_matrix::{Matrix,dense::{RowMajorMatrix,RowMajorMatrixView},stack::ViewPair};
use p3_fri::FriParameters;
use p3_uni_stark::{prove,verify};
use pqtc_stark::{Config,StarkProof,ValMmcs,ChallengeMmcs,Dft,Pcs,crypto::{ProofLeafHasher,ProofNodeCompressor,Transcript512}};
use pqtc_spec::{WithdrawalStatement,Digest512};
use pqtc_poseidon_air::WithdrawalWitness;
use crate::{ScheduledAir,Geometry,h0,h5};

#[derive(Parser,Debug,Serialize,Deserialize)]
pub struct Args {
    #[arg(long,default_value="C1")]pub candidate:String,
    #[arg(long,default_value="prove")]pub action:String,
    #[arg(long,default_value="decomposed")]pub geometry:String,
    #[arg(long,default_value="fixed")]pub profile:String,
    #[arg(long)]pub security_model:Option<String>,
    #[arg(long,default_value_t=32)]pub queries:usize,
    #[arg(long,default_value_t=4)]pub log_blowup:usize,
    #[arg(long,default_value_t=0)]pub log_final_poly:usize,
    #[arg(long,default_value_t=1)]pub max_log_arity:usize,
    #[arg(long,default_value_t=0)]pub cap_height:usize,
    #[arg(long,default_value_t=16)]pub commit_pow:usize,
    #[arg(long,default_value_t=16)]pub query_pow:usize,
    #[arg(long)]pub output:PathBuf,
    #[arg(long)]pub statement:PathBuf,
    #[arg(long)]pub witness:PathBuf,
    #[arg(long)]pub h5_case:Option<PathBuf>,
    #[arg(long)]pub proof_input:Option<PathBuf>,
    #[arg(long,default_value="research/r2/corpus/semantic-cases.json")]pub corpus:PathBuf,
    #[arg(long,default_value_t=0)]pub case_index:usize,
    #[arg(long)]pub mutation_proofs:bool,
}
pub fn save(path:impl AsRef<Path>,v:&impl Serialize)->Result<()> {std::fs::write(path,serde_json::to_vec_pretty(v)?)?;Ok(())}
fn load<T:serde::de::DeserializeOwned>(p:&Path)->Result<T>{Ok(serde_json::from_slice(&std::fs::read(p).with_context(||format!("read {}",p.display()))?)?)}
pub fn keccak(bytes:&[u8])->String{hex::encode(Keccak256::digest(bytes))}
fn config(args:&Args,id:Digest512,pv:&[BabyBear])->Config {
    let mut entropy=rand::rng();
    let mmcs=ValMmcs::new(ProofLeafHasher,ProofNodeCompressor,args.cap_height,StdRng::from_rng(&mut entropy));
    let fri=FriParameters{log_blowup:args.log_blowup,log_final_poly_len:args.log_final_poly,max_log_arity:args.max_log_arity,num_queries:args.queries,commit_proof_of_work_bits:args.commit_pow,query_proof_of_work_bits:args.query_pow,mmcs:ChallengeMmcs::new(mmcs.clone())};
    let pcs=Pcs::new(Dft::default(),mmcs,fri,4,StdRng::from_rng(&mut entropy));
    Config::new(pcs,Transcript512::new(id,pv))
}
fn geometry(a:&Args)->Result<Geometry>{if a.candidate=="C2"{return Ok(Geometry::Horizontal)}Ok(match a.geometry.as_str(){"decomposed"=>Geometry::Decomposed,"whole-round"=>Geometry::WholeRound,"lanes4"=>Geometry::Lanes4,_=>anyhow::bail!("unknown bounded geometry")})}
fn h5_case(a:&Args,w:&WithdrawalWitness)->Result<h5::Case>{
    let corpus:Value=load(&a.corpus)?;let case=corpus["cases"].get(a.case_index).context("corpus case")?;
    let mut scope=Vec::new();scope.extend(case["chainId"].as_str().context("chainId")?.parse::<u64>()?.to_be_bytes());scope.extend(hex::decode(case["poolAddress"].as_str().context("pool")?.trim_start_matches("0x"))?);
    let denomination=case["denomination"].as_str().context("denomination")?.parse::<u128>()?;let mut amount=[0u8;32];amount[16..].copy_from_slice(&denomination.to_be_bytes());scope.extend(amount);scope.push(20);scope.extend(2001u32.to_be_bytes());scope.extend(pqtc_hash::parameter_id(b"R2-H5-complete-v1").to_bytes());
    let mut payout=hex::decode(case["recipient"].as_str().context("recipient")?.trim_start_matches("0x"))?;payout.extend(hex::decode(case["relayer"].as_str().context("relayer")?.trim_start_matches("0x"))?);let mut fee=[0u8;32];fee[16..].copy_from_slice(&case["fee"].as_str().context("fee")?.parse::<u128>()?.to_be_bytes());payout.extend(fee);
    // Canonical BabyBear witness limbs are retained exactly from the H0 mapping;
    // sibling12 is the first12 canonical independent limbs, never a byte reduction.
    let mut siblings=[[0;12];20];for l in 0..20{let elements=pqtc_hash::digest_to_elements(w.siblings[l]).context("canonical H0 sibling")?;for i in 0..12{siblings[l][i]=elements[i].as_canonical_u32();}}
    ensure!(case["leafIndex"].as_u64()==Some(w.leaf_index as u64),"corpus/witness scenario mismatch; pass matching --witness and --case-index");
    let mapped=h5::Case{scope_bytes:scope,payout_bytes:payout,nullifier_secret:*w.nullifier_secret.limbs(),trapdoor:*w.trapdoor.limbs(),leaf_index:w.leaf_index,path_bits:w.path_bits,siblings};
    if let Some(p)=&a.h5_case {let supplied:h5::Case=load(p)?;ensure!(serde_json::to_value(&supplied)?==serde_json::to_value(&mapped)?,"H5 case differs from explicit frozen witness/corpus mapping");}
    Ok(mapped)
}
#[derive(Serialize)]
struct Section {name:String,bytes:usize,children:Vec<Section>}
fn leaf(name:impl Into<String>,v:&impl Serialize)->Section{Section{name:name.into(),bytes:postcard::to_allocvec(v).expect("serializable proof field").len(),children:Vec::new()}}
fn node(name:impl Into<String>,v:&impl Serialize,mut children:Vec<Section>)->Section{let mut s=leaf(name,v);let sum:usize=children.iter().map(|x|x.bytes).sum();assert!(sum<=s.bytes);if sum<s.bytes{children.push(Section{name:"length/option-prefix".into(),bytes:s.bytes-sum,children:Vec::new()});}s.children=children;s}
fn ledger(p:&StarkProof)->Section {
    let f=&p.opening_proof.1;
    let input=f.input_openings.iter().enumerate().map(|(i,b)|node(format!("batch-{i}"),b,vec![leaf("row-openings",&b.opened_values),leaf("hiding-salts",&b.opening_proof.0),leaf("shared-pruned-frontier",&b.opening_proof.1)])).collect();
    let rounds=f.commit_phase_openings.iter().enumerate().map(|(i,r)|node(format!("round-{i}"),r,vec![leaf("log-arity",&r.log_arity),leaf("sibling-values",&r.sibling_values),leaf("hiding-salts",&r.opening_proof.0),leaf("shared-pruned-frontier",&r.opening_proof.1)])).collect();
    let fri=node("FRI",f,vec![leaf("commitments",&f.commit_phase_commits),leaf("commit-PoW",&f.commit_pow_witnesses),node("input-openings",&f.input_openings,input),node("FRI-round-openings",&f.commit_phase_openings,rounds),leaf("final-polynomial",&f.final_poly),leaf("query-PoW",&f.query_pow_witness)]);
    node("proof.postcard",p,vec![node("commitments",&p.commitments,vec![leaf("trace",&p.commitments.trace),leaf("quotient",&p.commitments.quotient_chunks),leaf("random",&p.commitments.random)]),node("out-of-domain-openings",&p.opened_values,vec![leaf("trace-local",&p.opened_values.trace_local),leaf("trace-next",&p.opened_values.trace_next),leaf("preprocessed-local",&p.opened_values.preprocessed_local),leaf("preprocessed-next",&p.opened_values.preprocessed_next),leaf("quotient-chunks",&p.opened_values.quotient_chunks),leaf("random",&p.opened_values.random)]),node("PCS",&p.opening_proof,vec![leaf("hiding-random-codewords",&p.opening_proof.0),fri]),leaf("degree-bits",&p.degree_bits)])
}
fn check_row(air:&ScheduledAir,t:&RowMajorMatrix<BabyBear>,pv:&[BabyBear],row:usize)->bool {
    let local=t.row_slice(row).unwrap();let next=t.row_slice((row+1)%t.height()).unwrap();let periodic=air.periodic_values(row);
    let mut b=DebugConstraintBuilder::new(row,ViewPair::new(RowMajorMatrixView::new_row(&local),RowMajorMatrixView::new_row(&next)),ViewPair::new(RowMajorMatrixView::new(&[],0),RowMajorMatrixView::new(&[],0)),pv,BabyBear::from_bool(row==0),BabyBear::from_bool(row+1==t.height()),BabyBear::from_bool(row+1!=t.height()),&periodic);air.eval(&mut b);!b.has_failures()
}
fn mutations(air:&ScheduledAir,trace:&RowMajorMatrix<BabyBear>,pv:&[BabyBear])->Result<Value>{
    let mut t=trace.clone();let mut checks=Vec::new();let mut rows=BTreeSet::new();for p in 0..air.permutations {let r=p*air.period;for row in [r.saturating_sub(1),r,(r+1).min(t.height()-1)]{rows.insert(row);}}rows.insert(t.height()-1);
    let mut columns=(0..air.hash_width).map(|i|air.layout.input+i).collect::<BTreeSet<_>>();columns.extend(0..air.hash_width);columns.extend(air.layout.work..=air.layout.index);if air.geometry==Geometry::Decomposed{columns.extend(air.layout.a..air.layout.b+air.hash_width);}
    for row in rows {for &column in &columns {let at=row*t.width()+column;t.values[at]+=BabyBear::ONE;let rejected=!check_row(air,&t,pv,row)||!check_row(air,&t,pv,(row+t.height()-1)%t.height());t.values[at]-=BabyBear::ONE;ensure!(rejected,"unconstrained mutation row={row} column={column}");checks.push(json!({"row":row,"column":column,"rejected":true}));}}
    Ok(json!({"measurement_class":"MEASURED","kind":"before-at-after-every-permutation-boundary","checks":checks,"scope":"Direct AIR constraints; negative proof rejection separately recorded when requested"}))
}
fn context_study(case:&h5::Case,out:&Path)->Result<()> {
    let bytes:&[u8;72]=case.payout_bytes.as_slice().try_into()?;
    let recipient:[u8;20]=bytes[..20].try_into()?;let relayer:[u8;20]=bytes[20..40].try_into()?;let fee:[u8;32]=bytes[40..].try_into()?;
    let iterations=2048;
    let mut rows=Vec::new();
    for mode in ["H0-application-payout","H5-application-payout","direct-fixed-width-u16","Keccak256-injective-u16"] {
        let started=Instant::now();let mut output=Vec::<u32>::new();
        for _ in 0..iterations {
            output=match mode {
                "H0-application-payout"=>pqtc_hash::digest_to_elements(pqtc_hash::payout_digest(std::hint::black_box(recipient),relayer,fee)).unwrap().iter().map(|v|v.as_canonical_u32()).collect(),
                "H5-application-payout"=>pqtc_r2_hash::payout(std::hint::black_box(bytes)).iter().map(|v|v.as_canonical_u32()).collect(),
                "direct-fixed-width-u16"=>std::hint::black_box(bytes).chunks_exact(2).map(|p|u16::from_be_bytes([p[0],p[1]])as u32).collect(),
                _=>Keccak256::digest(std::hint::black_box(bytes)).chunks_exact(2).map(|p|u16::from_be_bytes([p[0],p[1]])as u32).collect()
            };std::hint::black_box(&output);
        }
        rows.push(json!({"mode":mode,"native_ns_per_iteration":started.elapsed().as_nanos()as f64/iterations as f64,"public_field_elements":output.len(),"encoded_values":output,"measurement_class":"MEASURED","integrated_into_C2_C3":mode=="H5-application-payout"}));
    }
    save(out.join("public-context-study.json"),&json!({"rows":rows,"iterations":iterations,"scope":"Payout/context alternatives only, not whole-proof timings","binding_argument":"Recipient20||relayer20||fee32 is fixed width. Direct u16 lanes are injective. Keccak256 digest is encoded into sixteen u16 lanes without field reduction; collision resistance is a separate assumption. All lanes must enter the experimental transcript, which binds the entire public vector. Integrated H5 additionally proves exact payout framing and chaining.","security":"SECURITY_NOT_QUALIFIED","promotion":"NOT_AUTHORIZED"}))
}
pub fn run(a:Args)->Result<()> {
    ensure!(matches!(a.candidate.as_str(),"C1"|"C2"|"C3"),"candidate C1/C2/C3 required");ensure!(matches!(a.profile.as_str(),"fixed"|"normalized"),"profile");ensure!(a.profile!="normalized"||a.security_model.is_some(),"normalized requires --security-model naming assumptions and target");ensure!(a.queries>0&&a.log_blowup>0&&a.log_blowup<=8&&a.max_log_arity>0&&a.max_log_arity<=3&&a.commit_pow<=24&&a.query_pow<=24,"bounded parameter controls");
    std::fs::create_dir_all(&a.output)?;
    for entry in std::fs::read_dir(&a.output)? {let name=entry?.file_name();ensure!(name=="stdout.log"||name=="stderr.log","output already contains evidence; choose a fresh directory");}
    let statement:WithdrawalStatement=load(&a.statement)?;let witness:WithdrawalWitness=load(&a.witness)?;
    if a.action=="public-context" {return context_study(&h5_case(&a,&witness)?,&a.output)}
    let (air,pv)=if a.candidate=="C1"{h0::prepare(statement,&witness,geometry(&a)?)?}else{let case=h5_case(&a,&witness)?;save(a.output.join("h5-case.json"),&case)?;h5::prepare(&case,geometry(&a)?)?};
    save(a.output.join("public-values.json"),&pv.iter().map(|v|v.as_canonical_u32()).collect::<Vec<_>>())?;
    let source_hashes=json!({"lib":keccak(include_bytes!("lib.rs")),"h0":keccak(include_bytes!("h0.rs")),"h5":keccak(include_bytes!("h5.rs")),"runner":keccak(include_bytes!("runner.rs")),"hash":keccak(include_bytes!("../../../hash/rust/src/lib.rs"))});
    let binding=json!({"version":"R2-AIR-config-v1","candidate":a.candidate,"geometry":air.geometry,"queries":a.queries,"log_blowup":a.log_blowup,"log_final_poly":a.log_final_poly,"max_log_arity":a.max_log_arity,"cap_height":a.cap_height,"commit_pow":a.commit_pow,"query_pow":a.query_pow,"random_codewords":4,"periodic_keccak256":keccak(&postcard::to_allocvec(&air.periodic)?),"rules_keccak256":keccak(&serde_json::to_vec(&air.rules)?),"source":source_hashes,"p3_rev":"3152b14a89067c83775a8076cc262ffc48a1fd7c","codec":"postcard-1.1.3-full-native-proof"});
    let id=pqtc_hash::parameter_id(&serde_json::to_vec(&binding)?);save(a.output.join("configuration.json"),&json!({"experimental_id":hex::encode(id.to_bytes()),"binding":binding,"original_H0_statement_unchanged":a.candidate=="C1","security":"SECURITY_NOT_QUALIFIED"}))?;
    let cfg=config(&a,id,&pv);let layout=AirLayout::from_air::<BabyBear>(&air);let constraints=get_symbolic_constraints::<BabyBear,_>(&air,layout);let max_degree=get_max_constraint_degree::<BabyBear,_>(&air,layout,air.rows());
    let mut shape=json!({"candidate_id":format!("R2-{}",a.candidate),"logical_trace_height":air.rows(),"proof_degree_bits":air.rows().ilog2()+1,"masked_trace_height":air.rows()*2,"relation_width":air.width(),"main_width":air.width(),"preprocessed_width":0,"aux_width":0,"periodic_columns":air.periodic.len(),"periodic_periods":air.periodic.iter().map(Vec::len).collect::<Vec<_>>(),"num_constraints":constraints.len(),"max_constraint_degree":max_degree,"max_combo":2,"quotient_chunks":null,"hiding_random_functions":4,"num_batched_functions":null,"profile":a.profile,"security_model":a.security_model,"queries":a.queries,"log_blowup":a.log_blowup,"security":"SECURITY_NOT_QUALIFIED"});
    let quotient_chunks=1usize << (p3_uni_stark::get_log_num_quotient_chunks::<BabyBear,_>(&air,layout,air.rows(),1)+1);
    shape["quotient_chunks"]=json!(quotient_chunks);
    shape["num_batched_functions"]=json!(air.width()+quotient_chunks+4);
    shape["shape_measurement_class"]=json!("EXACT_ANALYTICAL_BOUND, derived by pinned symbolic AIR machinery");
    save(a.output.join("shape.json"),&shape)?;save(a.output.join("controller-rules.json"),&air.rules)?;
    crate::solidity::export(&air,&constraints,&a.output)?;
    let trace=air.trace();
    for (p,expected) in air.reference_outputs.iter().enumerate() {
        let row=trace.row_slice((p+1)*air.period-1).unwrap();
        ensure!(&row[air.layout.output..air.layout.output+air.hash_width]==expected.as_slice(),"host/horizontal/vertical permutation mismatch at {p}");
    }
    let report=check_all_constraints(&air,&trace,&pv,Some(16));ensure!(report.is_ok(),"AIR constraint failures: {:?}",report.failures);
    if a.action=="shape" {save(a.output.join("results.json"),&json!({"candidate_id":format!("R2-{}",a.candidate),"measurement_class":"EXACT_ANALYTICAL_BOUND","correctness":"reference-trace-checked","implementation_stage":"relation","shape":shape,"security":"SECURITY_NOT_QUALIFIED","promotion":"NOT_AUTHORIZED"}))?;return Ok(())}
    if a.action=="mutations" {save(a.output.join("mutations.json"),&mutations(&air,&trace,&pv)?)?;if !a.mutation_proofs{return Ok(())}}
    if a.action=="verify" {let input=a.proof_input.as_ref().context("verify requires --proof-input; --output is fresh evidence only")?;let bytes=std::fs::read(input.join("proof.postcard"))?;let proof:StarkProof=postcard::from_bytes(&bytes)?;ensure!(verify(&cfg,&air,&proof,&pv).is_ok(),"native verification failed");save(a.output.join("native-verification.json"),&json!({"native_verified":true,"proof_keccak256":keccak(&bytes),"proof_input":input,"security":"SECURITY_NOT_QUALIFIED"}))?;return Ok(())}
    ensure!(matches!(a.action.as_str(),"prove"|"mutations"),"unknown --action");
    let mutation_trace=a.mutation_proofs.then(||trace.clone());
    let start=Instant::now();let proof=prove(&cfg,&air,trace,&pv);let prove_ms=start.elapsed().as_secs_f64()*1000.;let start=Instant::now();let native_verified=verify(&cfg,&air,&proof,&pv).is_ok();let verify_ms=start.elapsed().as_secs_f64()*1000.;ensure!(native_verified,"generated proof rejected");
    let bytes=postcard::to_allocvec(&proof)?;std::fs::write(a.output.join("proof.postcard"),&bytes)?;save(a.output.join("proof.json"),&proof)?;let byte_ledger=ledger(&proof);ensure!(byte_ledger.bytes==bytes.len(),"ledger total");save(a.output.join("byte-ledger.json"),&byte_ledger)?;
    let q=proof.opened_values.quotient_chunks.len();let matrix_widths=proof.opening_proof.1.input_openings.iter().map(|b|b.opened_values.first().map(|q|q.iter().map(Vec::len).collect::<Vec<_>>()).unwrap_or_default()).collect::<Vec<_>>();
    ensure!(q==quotient_chunks,"symbolic versus committed quotient inventory");
    let observed=matrix_widths.iter().enumerate().flat_map(|(batch,widths)|widths.iter().enumerate().map(move|(matrix,width)|json!({"commitment":batch,"matrix":matrix,"base_width":width,"lde_height":1usize<<(proof.degree_bits+a.log_blowup),"opening_points":if batch==1{2}else{1}}))).collect::<Vec<_>>();
    shape["observed_input_matrices"]=json!(observed);
    shape["proof_degree_bits"]=json!(proof.degree_bits);shape["masked_trace_height"]=json!(1usize<<proof.degree_bits);shape["quotient_chunks"]=json!(q);shape["num_batched_functions"]=json!(air.width()+q+4);shape["distinct_base_committed_columns"]=json!(matrix_widths.iter().flatten().sum::<usize>());shape["input_batch_matrix_widths"]=json!(matrix_widths);shape["batch_count_interpretation"]=json!("num_batched_functions follows pinned challenge-polynomial convention only; distinct_base_committed_columns includes extension decomposition and masks; rotations are repeated openings, not extra polynomials");save(a.output.join("shape.json"),&shape)?;
    let inventory=json!({"measurement_class":"MEASURED","shape":shape,"trace_local_extensions":proof.opened_values.trace_local.len(),"trace_next_extensions":proof.opened_values.trace_next.as_ref().map(Vec::len),"quotient_extension_widths":proof.opened_values.quotient_chunks.iter().map(Vec::len).collect::<Vec<_>>(),"random_extension_width":proof.opened_values.random.as_ref().map(Vec::len),"hiding_opening_widths":proof.opening_proof.0.iter().map(|b|b.iter().map(|m|m.iter().map(Vec::len).collect::<Vec<_>>()).collect::<Vec<_>>()).collect::<Vec<_>>(),"fri_log_arities":proof.opening_proof.1.commit_phase_openings.iter().map(|r|r.log_arity).collect::<Vec<_>>(),"fri_sibling_values_per_query":proof.opening_proof.1.commit_phase_openings.iter().map(|r|r.sibling_values.iter().map(Vec::len).collect::<Vec<_>>()).collect::<Vec<_>>(),"salt_base_elements_per_leaf":8,"digest_u64_words":8,"extension":"BabyBear[X]/(X^4-11)","separate_ABI_codec":"NOT_EVALUATED; native postcard is not frozen EVM codec"});save(a.output.join("proof-inventory.json"),&inventory)?;
    let mut negatives=Vec::new();
    if let Some(trace)=mutation_trace {
        let boundary=if a.candidate=="C1"{9*air.period}else{10*air.period};
        for row in [boundary-1,boundary,boundary+1] {
            let mut bad=trace.clone();bad.values[row*air.width()]+=BabyBear::ONE;
            let result=std::panic::catch_unwind(std::panic::AssertUnwindSafe(||prove(&cfg,&air,bad,&pv)));
            match result {
                Ok(p)=>{ensure!(verify(&cfg,&air,&p,&pv).is_err(),"bad trace proof accepted");std::fs::write(a.output.join(format!("bad-proof-row-{row}.postcard")),postcard::to_allocvec(&p)?)?;negatives.push(json!({"row":row,"native_rejected":true,"prover_rejected":false}));},
                Err(_)=>negatives.push(json!({"row":row,"native_rejected":null,"prover_rejected":true}))
            }
        }
        for column in 0..pv.len() {
            let mut changed=pv.clone();changed[column]+=BabyBear::ONE;
            let changed_config=config(&a,id,&changed);
            ensure!(verify(&changed_config,&air,&proof,&changed).is_err(),"public field {column} not bound");
            negatives.push(json!({"public_column":column,"native_rejected":true}));
        }
        let wrong_id=pqtc_hash::parameter_id(b"R2-distinct-experimental-verifier");
        ensure!(verify(&config(&a,wrong_id,&pv),&air,&proof,&pv).is_err(),"experimental configuration substitution accepted");
        negatives.push(json!({"experimental_configuration_substitution_rejected":true}));
        save(a.output.join("negative-proofs.json"),&negatives)?;
        ensure!(negatives.iter().filter(|v|v.get("row").is_some()&&v["native_rejected"]==true).count()==3,"mutation proof coverage incomplete: prover rejection is not native rejection of an actual invalid-trace proof");
    }
    let results=json!({"candidate_id":format!("R2-{}",a.candidate),"specification":"exact","correctness":"integrated-tested","privacy":"configured hiding; composition not reviewed","security":"SECURITY_NOT_QUALIFIED","performance":"measured","implementation_stage":"native proof","promotion":"NOT_AUTHORIZED","measurement_class":"MEASURED","native_verified":native_verified,"prove_ms":prove_ms,"verify_ms":verify_ms,"raw_proof_bytes":bytes.len(),"raw_ABI_bytes":null,"proof_path":"proof.postcard","proof_keccak256":keccak(&bytes),"shape_path":"shape.json","byte_ledger_path":"byte-ledger.json","proof_inventory_path":"proof-inventory.json","profile":a.profile,"security_model":a.security_model,"randomness":"fresh OS entropy through rand::rng -> independent StdRng MMCS and PCS streams; no deterministic proof seed","synthetic_unfunded":true,"negative_proofs":negatives,"permutations":{"private_relation":if a.candidate=="C1"{240}else{22},"scope":if a.candidate=="C1"{0}else{5},"payout":if a.candidate=="C1"{4}else{3},"statement":if a.candidate=="C1"{0}else{4},"empty":if a.candidate=="C1"{0}else{1},"padded_total":air.permutations},"arguments":a,"peak_rss_bytes":null,"peak_rss_status":"NOT_EVALUATED; capture process RSS externally"});save(a.output.join("results.json"),&results)?;println!("{}",serde_json::to_string(&results)?);Ok(())
}
