//! Compile the very same symbolic AIR into a hash-bound extension-field instruction
//! tape. This is an AIR arithmetic cost prototype, never a proof verifier.
use std::{collections::BTreeMap,path::Path};
use p3_air::symbolic::{SymbolicExpr,SymbolicExpression,BaseLeaf,BaseEntry};
use p3_baby_bear::BabyBear;
use p3_field::{PrimeCharacteristicRing,PrimeField32,BasedVectorSpace};
use pqtc_stark::Challenge;
use serde_json::json;
use crate::{ScheduledAir,runner::{save,keccak}};
fn input_index(a:&ScheduledAir,l:&BaseLeaf<BabyBear>)->Option<usize>{match l {
    BaseLeaf::Variable(v)=>Some(match v.entry{BaseEntry::Main{offset}=>offset*a.layout.width+v.index,BaseEntry::Public=>2*a.layout.width+v.index,BaseEntry::Periodic=>2*a.layout.width+a.public_count+v.index,_=>panic!("unexpected preprocessed variable")}),
    BaseLeaf::IsFirstRow=>Some(2*a.layout.width+a.public_count+a.periodic.len()),BaseLeaf::IsLastRow=>Some(2*a.layout.width+a.public_count+a.periodic.len()+1),BaseLeaf::IsTransition=>Some(2*a.layout.width+a.public_count+a.periodic.len()+2),BaseLeaf::Constant(_)=>None}}
fn compile(a:&ScheduledAir,e:&SymbolicExpression<BabyBear>,nodes:&mut Vec<[u32;3]>,seen:&mut BTreeMap<[u32;3],u32>,memo:&mut BTreeMap<*const SymbolicExpression<BabyBear>,u32>)->u32 {
    // Pinned symbolic expressions share Arc children: visit each DAG node once.
    let pointer=e as *const _;
    if let Some(id)=memo.get(&pointer){return *id;}
    let node=match e {
        SymbolicExpr::Leaf(BaseLeaf::Constant(c))=>[0,c.as_canonical_u32(),0],
        SymbolicExpr::Leaf(l)=>[1,input_index(a,l).unwrap()as u32,0],
        SymbolicExpr::Add{x,y,..}=>[2,compile(a,x,nodes,seen,memo),compile(a,y,nodes,seen,memo)],
        SymbolicExpr::Sub{x,y,..}=>[3,compile(a,x,nodes,seen,memo),compile(a,y,nodes,seen,memo)],
        SymbolicExpr::Mul{x,y,..}=>[4,compile(a,x,nodes,seen,memo),compile(a,y,nodes,seen,memo)],
        SymbolicExpr::Neg{x,..}=>{
            let zero=[0,0,0];
            let z=if let Some(id)=seen.get(&zero){*id}else{let id=nodes.len()as u32;nodes.push(zero);seen.insert(zero,id);id};
            [3,z,compile(a,x,nodes,seen,memo)]
        }
    };
    let id=if let Some(id)=seen.get(&node){*id}else{let id=nodes.len()as u32;nodes.push(node);seen.insert(node,id);id};
    memo.insert(pointer,id);id
}
fn evaluate(a:&ScheduledAir,e:&SymbolicExpression<BabyBear>,values:&[Challenge],memo:&mut BTreeMap<*const SymbolicExpression<BabyBear>,Challenge>)->Challenge {
    let pointer=e as *const _;
    if let Some(value)=memo.get(&pointer){return *value;}
    let value=match e {
        SymbolicExpr::Leaf(BaseLeaf::Constant(c))=>Challenge::from(*c),
        SymbolicExpr::Leaf(l)=>values[input_index(a,l).unwrap()],
        SymbolicExpr::Add{x,y,..}=>evaluate(a,x,values,memo)+evaluate(a,y,values,memo),
        SymbolicExpr::Sub{x,y,..}=>evaluate(a,x,values,memo)-evaluate(a,y,values,memo),
        SymbolicExpr::Mul{x,y,..}=>evaluate(a,x,values,memo)*evaluate(a,y,values,memo),
        SymbolicExpr::Neg{x,..}=>-evaluate(a,x,values,memo)
    };
    memo.insert(pointer,value);value
}
pub fn export(air:&ScheduledAir,constraints:&[SymbolicExpression<BabyBear>],out:&Path)->anyhow::Result<()> {
    let mut nodes=Vec::new();let mut seen=BTreeMap::new();let mut memo=BTreeMap::new();for e in constraints{let id=compile(air,e,&mut nodes,&mut seen,&mut memo);nodes.push([5,id,0]);}
    let bytes=nodes.iter().flat_map(|n|n.iter().flat_map(|x|x.to_be_bytes())).collect::<Vec<_>>();std::fs::write(out.join("air-program.bin"),&bytes)?;
    let count=2*air.layout.width+air.public_count+air.periodic.len()+3;
    let values=(0..count).map(|i|Challenge::new(std::array::from_fn(|j|BabyBear::from_usize(1+(i*17+j*31)%1009)))).collect::<Vec<_>>();let alpha=Challenge::new([7,11,13,17].map(BabyBear::new));
    let mut values_memo=BTreeMap::new();
    let expected=constraints.iter().fold(Challenge::ZERO,|acc,e|acc*alpha+evaluate(air,e,&values,&mut values_memo));
    let limbs=|x:&Challenge|x.as_basis_coefficients_slice().iter().map(|v:&BabyBear|v.as_canonical_u32()).collect::<Vec<_>>();
    let operations=(0..6).map(|op|json!({"opcode":op,"count":nodes.iter().filter(|n|n[0]==op).count()})).collect::<Vec<_>>();
    save(out.join("air-cost-vector.json"),&json!({"program_keccak256":keccak(&bytes),"program_bytes":bytes.len(),"inputs":values.iter().map(limbs).collect::<Vec<_>>(),"alpha":limbs(&alpha),"expected":limbs(&expected),"operations":operations,"constraints":constraints.len(),"input_layout":{"local":0,"next":air.layout.width,"public":2*air.layout.width,"periodic":2*air.layout.width+air.public_count,"first_last_transition":count-3},"classification":"EXACT_ANALYTICAL_BOUND until Solidity execution; full BabyBear^4 AIR arithmetic with externally supplied periodic evaluations, not a proof verifier; program calldata and hash overhead separately attributable","security":"SECURITY_NOT_QUALIFIED"}))?;Ok(())
}
