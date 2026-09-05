use p3_baby_bear::BabyBear;
use p3_matrix::Matrix;
use pqtc_poseidon_air::{WithdrawalWitness, generate_withdrawal_trace, public_values};
use pqtc_spec::{WithdrawalStatement, domains};
use crate::{ScheduledAir,Geometry,Expr,c};

fn phase(p:usize)->(usize,usize,usize) {
    if p<9 {(0,p,0)}else if p<20 {(1,p-9,0)}else if p<240 {(2,(p-20)%11,(p-20)/11)}else if p<244 {(3,p-240,0)}else{(4,0,0)}
}
/// C1 accepts precisely the frozen H0 public values and frozen witness representation.
/// The schedule replaces the frozen selector bits, not the application predicate.
pub fn prepare(statement:WithdrawalStatement,witness:&WithdrawalWitness,geometry:Geometry)->anyhow::Result<(ScheduledAir,Vec<BabyBear>)> {
    anyhow::ensure!(geometry!=Geometry::Horizontal,"C0 is the frozen horizontal runner, not this control");
    let frozen=generate_withdrawal_trace(statement,witness)?;
    let mut air=ScheduledAir::new(16,16,256,64,geometry);
    for p in 0..256 {
        let row=frozen.row_slice(p).unwrap();let work=frozen.width()-16;
        let mut source=row[..16].to_vec();source.extend_from_slice(&row[work..work+16]);source.push(row[work-2]);source.push(row[work-1]);air.permutation_rows.push(source);
        air.reference_outputs.push(row[pqtc_poseidon_air::NUM_POSEIDON_COLS-16..pqtc_poseidon_air::NUM_POSEIDON_COLS].to_vec());
    }
    for kind in 0..5 {
        let mut e=Vec::new();if kind!=2 {e.push(air.bit());e.push(air.index());}
        if kind>=3 {for j in 0..16 {e.push(air.work(j));}}
        air.rule(format!("phase-{kind}-workspace"),move|p|phase(p).0==kind,e);
    }
    air.rule("initial-secret-workspace",|p|p==0,(8..16).map(|j|air.work(j)).collect());
    air.rule("boolean-path-bits",|p|phase(p).0==2,vec![air.bit()*(air.bit()-c(1))]);
    for (kind,tag,bytes,elements) in [(0,domains::NULLIFIER,96,24),(1,domains::NOTE,128,32),(2,domains::APP_MERKLE_NODE,128,32)] {
        let mut e=vec![air.input(4)-c(1),air.input(5)-c(tag as usize),air.input(6)-c(bytes),air.input(7)-c(elements)];
        for j in 9..16 {e.push(air.input(j));}
        if kind!=2 {e.push(air.input(8));for j in 0..4 {e.push(air.input(j)-Expr::Public(j));}}
        else {for j in 0..4 {e.push((c(1)-air.bit())*(air.input(j)-air.work(j)));}}
        air.rule(format!("domain-and-initial-input-{kind}"),move|p|{let(k,s,_)=phase(p);k==kind&&s==0},e);
    }
    for level in 0..20 {air.rule(format!("level-domain-{level}"),move|p|phase(p)==(2,0,level),vec![air.input(8)-c(level)]);}
    for step in 0..4 {let mut e=Vec::new();for j in 0..4 {e.push(air.input(j)-Expr::Public(48+step*4+j));}for j in 4..16{e.push(air.input(j));}air.rule(format!("payout-public-{step}"),move|p|phase(p).0==3&&phase(p).1==step,e);}
    air.rule("padding-input",|p|p>=244,(0..16).map(|j|air.input(j)).collect());
    // Chaining into each next permutation. Every absorb capacity lane and every
    // squeeze lane is constrained; only trapdoor/sibling payload deltas are private.
    for kind in 0..3 {let end=if kind==0{9}else{11};let absorb=if kind==0{6}else{8};
        for step in 1..end {let mut e=Vec::new();for j in 0..16 {
            let delta=air.next_input(j)-air.out(j);
            if j>=4||step>=absorb {e.push(delta);}else if kind==0||kind==1 {
                if step<4 {e.push(delta-Expr::Public(step*4+j));}else if step<6 {e.push(delta-air.next_work((step-4)*4+j));}
            }else {let k=step*4+j;let bit=Expr::Next(air.layout.bit);let gate=if k<16 {c(1)-bit}else{bit};e.push(gate*(delta-air.next_work(k%16)));}
        }
        air.rule(format!("absorb-squeeze-{kind}-{step}"),move|p|p<255&&phase(p+1).0==kind&&phase(p+1).1==step,e);
    }}
    for kind in 0..3 {let steps=if kind==0{9}else{11};for step in 0..steps {
        let mut e=Vec::new();for j in 0..16 {let overwrite=kind!=0&&step>=7&&(step-7)==j/4;let value=if overwrite{air.out(j%4)}else{air.work(j)};e.push(air.next_work(j)-value);}
        air.rule(format!("workspace-carry-{kind}-{step}"),move|p|{let(k,s,l)=phase(p);k==kind&&s==step&&!(k==2&&l==19&&s==10)},e);
    }}
    // At the last root output, the next payout row independently constrains WORK=0.
    for step in 0..10 {air.rule(format!("path-carry-{step}"),move|p|{let(k,s,_)=phase(p);k==2&&s==step},vec![Expr::Next(air.layout.bit)-air.bit(),Expr::Next(air.layout.index)-air.index()]);}
    air.rule("private-index-shift",|p|{let(k,s,l)=phase(p);k==2&&s==10&&l<19},vec![air.index()-air.bit()-c(2)*Expr::Next(air.layout.index)]);
    air.rule("private-index-terminal",|p|phase(p)==(2,10,19),vec![air.index()-air.bit()]);
    for chunk in 0..4 {
        air.rule(format!("public-nullifier-{chunk}"),move|p|p==5+chunk,(0..4).map(|j|air.out(j)-Expr::Public(32+chunk*4+j)).collect());
        air.rule(format!("public-root-{chunk}"),move|p|phase(p)==(2,7+chunk,19),(0..4).map(|j|air.out(j)-Expr::Public(16+chunk*4+j)).collect());
    }
    Ok((air,public_values(statement).to_vec()))
}
