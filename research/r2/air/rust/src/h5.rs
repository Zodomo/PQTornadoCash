use p3_baby_bear::BabyBear;
use p3_field::{PrimeCharacteristicRing,PrimeField32};
use pqtc_r2_hash as hash;
use serde::{Serialize,Deserialize};
use p3_symmetric::Permutation;
use crate::{ScheduledAir,Geometry,Expr,c};

#[derive(Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Case {
    pub scope_bytes:Vec<u8>, pub payout_bytes:Vec<u8>,
    pub nullifier_secret:[u32;8], pub trapdoor:[u32;8],
    pub leaf_index:u32, pub path_bits:[u8;20], pub siblings:[[u32;12];20],
}
fn digest(a:[u32;12])->anyhow::Result<hash::Digest>{anyhow::ensure!(a.iter().all(|x|*x<hash::MODULUS),"noncanonical H5 digest");Ok(a.map(BabyBear::new))}
fn bytes_fields(a:&[u8])->Vec<BabyBear>{a.chunks(2).map(|x|BabyBear::new(u16::from_be_bytes([x[0],*x.get(1).unwrap_or(&0)]) as u32)).collect()}
pub fn validate_public(p:&[BabyBear])->anyhow::Result<()> {
    anyhow::ensure!(p.len()==173,"H5 public shape");
    anyhow::ensure!(p[72..].iter().all(|x|x.as_canonical_u32()<=65535),"H5 public byte encoding");
    anyhow::ensure!(p[136].as_canonical_u32()&255==0,"H5 odd byte padding");Ok(())
}
pub fn prepare(case:&Case,geometry:Geometry)->anyhow::Result<(ScheduledAir,Vec<BabyBear>)>{
    let sb:&[u8;129]=case.scope_bytes.as_slice().try_into()?;let pb:&[u8;72]=case.payout_bytes.as_slice().try_into()?;
    anyhow::ensure!(case.nullifier_secret.iter().chain(case.trapdoor.iter()).all(|x|*x<hash::MODULUS),"noncanonical secret; reduction prohibited");
    anyhow::ensure!(case.leaf_index<1<<20,"index range");for l in 0..20 {anyhow::ensure!(case.path_bits[l]==((case.leaf_index>>l)&1) as u8,"path/index mismatch");}
    let secret=case.nullifier_secret.map(BabyBear::new);let trapdoor=case.trapdoor.map(BabyBear::new);
    let scope=hash::scope(sb);let payout=hash::payout(pb);let nullifier=hash::nullifier(scope,secret);let empty=hash::empty(scope);
    let mut root=hash::note(scope,secret,trapdoor);
    for l in 0..20 {let sibling=digest(case.siblings[l])?;root=if case.path_bits[l]==0{hash::node(l as u8,root,sibling)}else{hash::node(l as u8,sibling,root)};}
    let statement=hash::statement(scope,root,nullifier,payout);
    let mut pv=Vec::new();for d in [scope,root,nullifier,payout,statement,empty]{pv.extend_from_slice(&d);}pv.extend(bytes_fields(sb));pv.extend(bytes_fields(pb));validate_public(&pv)?;
    let mut inputs=hash::public_inputs(1,129,&pv[72..137]);inputs.extend(hash::public_inputs(6,72,&pv[137..173]));inputs.push(hash::empty_input(scope));inputs.push(hash::nullifier_input(scope,secret));inputs.push(hash::note_input(scope,secret,trapdoor));
    let mut work=hash::note(scope,secret,trapdoor);let mut workspaces=vec![[BabyBear::ZERO;12];9];let mut secret_work=[BabyBear::ZERO;12];secret_work[..8].copy_from_slice(&secret);workspaces.push(secret_work);workspaces.push(secret_work);
    for l in 0..20 {let sibling=digest(case.siblings[l])?;let input=if case.path_bits[l]==0{hash::node_input(l as u8,work,sibling)}else{hash::node_input(l as u8,sibling,work)};inputs.push(input);workspaces.push(work);work=hash::compress(input);}
    inputs.extend(hash::public_inputs(7,48,&pv[..48]));inputs.resize(64,[BabyBear::ZERO;32]);workspaces.resize(64,[BabyBear::ZERO;12]);
    let mut air=ScheduledAir::new(32,12,64,173,geometry);
    for p in 0..64 {let mut row=inputs[p].to_vec();row.extend_from_slice(&workspaces[p]);let node=(11..31).contains(&p);row.push(BabyBear::from_u8(if node{case.path_bits[p-11]}else{0}));row.push(BabyBear::from_u32(if node{case.leaf_index>>(p-11)}else{0}));air.permutation_rows.push(row);}
    air.reference_outputs=inputs.iter().map(|x|hash::PERMUTATION.permute(*x).to_vec()).collect();
    for (start,blocks,role,length,payload_start,payload_len,output_start) in [(0,5,1,129,72,65,0),(5,3,6,72,137,36,36),(31,4,7,48,0,48,48)] {
        for block in 0..blocks {let p=start+block;let mut e=Vec::new();for i in 0..16 {let j=block*16+i;let value=if j<payload_len{Expr::Public(payload_start+j)}else{c(usize::from(j==payload_len))};e.push(air.input(12+i)-value);}
            for (i,v) in [role,hash::VERSION as usize,length,block].into_iter().enumerate(){e.push(air.input(28+i)-c(v));}
            if block==0 {for i in 0..12{e.push(air.input(i));}}
            air.rule(format!("public-role-{role}-frame-{block}"),move|q|q==p,e);
            if block+1<blocks {air.rule(format!("public-role-{role}-chain-{block}"),move|q|q==p,(0..12).map(|i|air.next_input(i)-air.out(i)).collect());}
            else {air.rule(format!("public-role-{role}-output"),move|q|q==p,(0..12).map(|i|air.out(i)-Expr::Public(output_start+i)).collect());}
        }
    }
    for (p,role,at,count) in [(8,4,28,12),(9,3,20,20),(10,2,28,28)] {
        let mut e=(0..12).map(|i|air.input(i)-Expr::Public(i)).collect::<Vec<_>>();
        for (i,v) in [role,hash::VERSION as usize,count,0].into_iter().enumerate(){e.push(air.input(at+i)-c(v));}
        if p==8 {for i in 12..28{e.push(air.input(i));}for i in 0..12{e.push(air.out(i)-Expr::Public(60+i));}}
        else {for i in 0..8{e.push(air.input(12+i)-air.work(i));}for i in 8..12{e.push(air.work(i));}}
        if p==9 {for i in 24..32{e.push(air.input(i));}for i in 0..12{e.push(air.out(i)-Expr::Public(24+i));e.push(air.next_work(i)-air.work(i));}}
        if p==10 {for i in 0..12{e.push(air.next_work(i)-air.out(i));}}
        air.rule(format!("private-role-{role}"),move|q|q==p,e);
    }
    for level in 0..20 {let p=11+level;let mut e=vec![air.bit()*(air.bit()-c(1))];
        for i in 0..12 {e.push((c(1)-air.bit())*(air.input(i)-air.work(i)));e.push(air.bit()*(air.input(12+i)-air.work(i)));if level<19 {e.push(air.next_work(i)-air.out(i));}else{e.push(air.out(i)-Expr::Public(12+i));}}
        for (i,v) in [5,hash::VERSION as usize,24,level].into_iter().enumerate(){e.push(air.input(24+i)-c(v));}for i in 28..32{e.push(air.input(i));}
        e.push(if level<19{air.index()-air.bit()-c(2)*Expr::Next(air.layout.index)}else{air.index()-air.bit()});
        air.rule(format!("ordered-merkle-level-{level}"),move|q|q==p,e);
    }
    let mut outside=vec![air.bit(),air.index()];air.rule("non-merkle-private-index",|p|!(11..31).contains(&p),std::mem::take(&mut outside));
    air.rule("unused-workspace",|p|!(9..31).contains(&p),(0..12).map(|i|air.work(i)).collect());
    air.rule("padding-input",|p|p>=35,(0..32).map(|i|air.input(i)).collect());
    Ok((air,pv))
}
