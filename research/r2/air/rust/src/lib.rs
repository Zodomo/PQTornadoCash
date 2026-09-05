//! Isolated R2 AIR experiments. The original relation and proof crates are read-only.
use std::borrow::Cow;
use p3_air::{Air, AirBuilder, BaseAir, WindowAccess};
use p3_baby_bear::*;
use p3_field::{PrimeCharacteristicRing, PrimeField32};
use p3_matrix::{Matrix, dense::RowMajorMatrix};
use p3_poseidon2::GenericPoseidon2LinearLayers;
use serde::{Serialize, Deserialize};
use p3_poseidon2_air::{Poseidon2Air, RoundConstants, generate_trace_rows, num_cols};
use p3_uni_stark::SubAirBuilder;
type HorizontalAir = Poseidon2Air<BabyBear, GenericPoseidon2LinearLayersBabyBear, 32, 7, 0, 4, 30>;
const HORIZONTAL_COLS:usize = num_cols::<32,7,0,4,30>();
fn horizontal_constants()->RoundConstants<BabyBear,32,4,30> {
    RoundConstants::new(BABYBEAR_POSEIDON2_RC_32_EXTERNAL_INITIAL,BABYBEAR_POSEIDON2_RC_32_INTERNAL,BABYBEAR_POSEIDON2_RC_32_EXTERNAL_FINAL)
}

pub mod h0;
pub mod h5;
pub mod runner;
pub mod solidity;

#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub enum Geometry { Horizontal, WholeRound, Decomposed, Lanes4 }
#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum Expr { Const(u32), Local(usize), Next(usize), Public(usize), Periodic(usize), Add(Box<Expr>,Box<Expr>), Sub(Box<Expr>,Box<Expr>), Mul(Box<Expr>,Box<Expr>) }
impl std::ops::Add for Expr { type Output=Self; fn add(self,b:Self)->Self { Self::Add(Box::new(self),Box::new(b)) } }
impl std::ops::Sub for Expr { type Output=Self; fn sub(self,b:Self)->Self { Self::Sub(Box::new(self),Box::new(b)) } }
impl std::ops::Mul for Expr { type Output=Self; fn mul(self,b:Self)->Self { Self::Mul(Box::new(self),Box::new(b)) } }
pub fn c(n:usize)->Expr { Expr::Const(n as u32) }
impl Expr {
    fn eval<AB:AirBuilder<F=BabyBear>>(&self,l:&[AB::Var],n:&[AB::Var],p:&[AB::PublicVar],q:&[AB::PeriodicVar])->AB::Expr {
        match self { Self::Const(v)=>AB::Expr::from_u32(*v), Self::Local(i)=>l[*i].into(), Self::Next(i)=>n[*i].into(), Self::Public(i)=>p[*i].into(), Self::Periodic(i)=>q[*i].into(), Self::Add(a,b)=>a.eval::<AB>(l,n,p,q)+b.eval::<AB>(l,n,p,q), Self::Sub(a,b)=>a.eval::<AB>(l,n,p,q)-b.eval::<AB>(l,n,p,q), Self::Mul(a,b)=>a.eval::<AB>(l,n,p,q)*b.eval::<AB>(l,n,p,q) }
    }
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Rule { pub name:String, pub selector:usize, pub expressions:Vec<Expr> }
#[derive(Clone, Debug)]
struct Step { rc:Vec<BabyBear>, kind:usize }
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Layout { pub width:usize, pub state:usize, pub input:usize, pub work:usize, pub bit:usize, pub index:usize, pub a:usize, pub b:usize, pub output:usize }
#[derive(Clone)]
pub struct ScheduledAir {
    pub hash_width:usize, pub digest_width:usize, pub permutations:usize,
    pub public_count:usize, pub geometry:Geometry, pub layout:Layout,
    pub period:usize, pub periodic:Vec<Vec<BabyBear>>, pub rules:Vec<Rule>,
    steps:Vec<Step>, kinds:Vec<(usize,usize,bool,bool)>,
    pub permutation_rows:Vec<Vec<BabyBear>>,
    pub reference_outputs:Vec<Vec<BabyBear>>,
}

pub fn linear<R:PrimeCharacteristicRing+Clone>(state:&mut [R], external:bool) {
    match state.len() {
        16=>{ let mut a:[R;16]=std::array::from_fn(|i|state[i].clone()); if external { <GenericPoseidon2LinearLayersBabyBear as GenericPoseidon2LinearLayers<16>>::external_linear_layer(&mut a); } else { <GenericPoseidon2LinearLayersBabyBear as GenericPoseidon2LinearLayers<16>>::internal_linear_layer(&mut a); } state.clone_from_slice(&a); },
        32=>{ let mut a:[R;32]=std::array::from_fn(|i|state[i].clone()); if external { <GenericPoseidon2LinearLayersBabyBear as GenericPoseidon2LinearLayers<32>>::external_linear_layer(&mut a); } else { <GenericPoseidon2LinearLayersBabyBear as GenericPoseidon2LinearLayers<32>>::internal_linear_layer(&mut a); } state.clone_from_slice(&a); },
        _=>unreachable!()
    }
}
fn rounds(w:usize)->Vec<(Vec<BabyBear>,bool)> {
    let (first,last,partial) = if w==16 {(BABYBEAR_POSEIDON2_RC_16_EXTERNAL_INITIAL.iter().map(|r|r.to_vec()).collect::<Vec<_>>(),BABYBEAR_POSEIDON2_RC_16_EXTERNAL_FINAL.iter().map(|r|r.to_vec()).collect::<Vec<_>>(),BABYBEAR_POSEIDON2_RC_16_INTERNAL.to_vec())} else {(BABYBEAR_POSEIDON2_RC_32_EXTERNAL_INITIAL.iter().map(|r|r.to_vec()).collect::<Vec<_>>(),BABYBEAR_POSEIDON2_RC_32_EXTERNAL_FINAL.iter().map(|r|r.to_vec()).collect::<Vec<_>>(),BABYBEAR_POSEIDON2_RC_32_INTERNAL.to_vec())};
    first.into_iter().map(|r|(r,true)).chain(partial.into_iter().map(|r|{let mut v=vec![BabyBear::ZERO;w];v[0]=r;(v,false)})).chain(last.into_iter().map(|r|(r,true))).collect()
}
impl ScheduledAir {
    pub fn new(w:usize,d:usize,permutations:usize,public_count:usize,geometry:Geometry)->Self {
        assert!(permutations.is_power_of_two());
        let mut kinds=vec![(0,0,false,false)]; // idle, including constrained padding between rounds
        let mut steps=Vec::new();
        for (rc,full) in rounds(w) {
            let groups=if geometry==Geometry::Lanes4 && full {w/4}else{1};
            for group in 0..groups {
                let start=if full {group*w/groups}else{0}; let end=if full {(group+1)*w/groups}else{1};
                let kind=(start,end,full&&group+1==groups,!full);
                let id=if let Some(id)=kinds.iter().position(|x|*x==kind){id}else{kinds.push(kind);kinds.len()-1};
                let mut constants=vec![BabyBear::ZERO;w]; constants[start..end].copy_from_slice(&rc[start..end]);
                steps.push(Step{rc:constants,kind:id});
            }
        }
        let horizontal=geometry==Geometry::Horizontal;
        let period=if horizontal {1}else{(steps.len()+1).next_power_of_two()};
        let input=if horizontal {0}else{w};
        let work=if horizontal {HORIZONTAL_COLS}else{2*w};
        let bit=work+d; let index=bit+1;
        let a=index+1; let b=a+w;
        let width=if geometry==Geometry::Decomposed {b+w}else{a};
        let output=if horizontal {HORIZONTAL_COLS-w}else{0};
        let layout=Layout{width,state:0,input,work,bit,index,a,b,output};
        let mut air=Self{hash_width:w,digest_width:d,permutations,public_count,geometry,layout,period,periodic:Vec::new(),rules:Vec::new(),steps,kinds,permutation_rows:Vec::new(),reference_outputs:Vec::new()};
        if !horizontal {
            for lane in 0..w {air.periodic.push((0..period).map(|r|air.steps.get(r).map_or(BabyBear::ZERO,|s|s.rc[lane])).collect());}
            for kind in 0..air.kinds.len() {air.periodic.push((0..period).map(|r|BabyBear::from_bool(r+1<period && air.steps.get(r).map_or(0,|s|s.kind)==kind)).collect());}
            air.periodic.push((0..period).map(|r|BabyBear::from_bool(r+1==period)).collect());
        }
        air
    }
    pub fn input(&self,i:usize)->Expr {Expr::Local(self.layout.input+i)}
    pub fn next_input(&self,i:usize)->Expr {Expr::Next(self.layout.input+i)}
    pub fn work(&self,i:usize)->Expr {Expr::Local(self.layout.work+i)}
    pub fn next_work(&self,i:usize)->Expr {Expr::Next(self.layout.work+i)}
    pub fn out(&self,i:usize)->Expr {let out=Expr::Local(self.layout.output+i);if self.hash_width==32 {out+self.input(i)} else {out}}
    pub fn bit(&self)->Expr {Expr::Local(self.layout.bit)}
    pub fn index(&self)->Expr {Expr::Local(self.layout.index)}
    pub fn rule(&mut self,name:impl Into<String>, selected:impl Fn(usize)->bool, expressions:Vec<Expr>) {
        if expressions.is_empty() {return;}
        let values=(0..self.permutations*self.period).map(|r|BabyBear::from_bool(r%self.period+1==self.period&&selected(r/self.period))).collect::<Vec<_>>();
        let selector=if let Some(i)=self.periodic.iter().position(|x|*x==values){i}else{self.periodic.push(values);self.periodic.len()-1};
        self.rules.push(Rule{name:name.into(),selector,expressions});
    }
    pub fn trace(&self)->RowMajorMatrix<BabyBear> {
        assert_eq!(self.permutation_rows.len(),self.permutations);
        let w=self.hash_width; let l=&self.layout;
        let mut values=vec![BabyBear::ZERO;self.permutations*self.period*l.width];
        let horizontal_trace=if self.geometry==Geometry::Horizontal {
            Some(generate_trace_rows::<BabyBear,GenericPoseidon2LinearLayersBabyBear,32,7,0,4,30>(
                self.permutation_rows.iter().map(|r|r[..32].try_into().unwrap()).collect(),&horizontal_constants(),0))
        }else{None};
        for (p,source) in self.permutation_rows.iter().enumerate() {
            let input=&source[..w]; let mut state=input.to_vec();linear(&mut state,true);
            if self.geometry==Geometry::Horizontal {
                let row=&mut values[p*l.width..(p+1)*l.width];
                row[..HORIZONTAL_COLS].copy_from_slice(&horizontal_trace.as_ref().unwrap().row_slice(p).unwrap());
                row[l.work..l.index+1].copy_from_slice(&source[w..]);
            } else {
                for r in 0..self.period {
                    let row=&mut values[(p*self.period+r)*l.width..(p*self.period+r+1)*l.width];
                    row[..w].copy_from_slice(&state);row[l.input..l.input+w].copy_from_slice(input);row[l.work..l.index+1].copy_from_slice(&source[w..]);
                    for i in 0..w {if self.geometry==Geometry::Decomposed {let x=state[i]+self.steps.get(r).map_or(BabyBear::ZERO,|s|s.rc[i]);row[l.a+i]=x.square();row[l.b+i]=x.square().square();}}
                    if let Some(step)=self.steps.get(r) {let(start,end,external,internal)=self.kinds[step.kind];for i in start..end {state[i]=(state[i]+step.rc[i]).exp_const_u64::<7>();}if external||internal{linear(&mut state,external);}}
                }
            }
        }
        RowMajorMatrix::new(values,l.width)
    }
    pub fn rows(&self)->usize {self.permutations*self.period}
}
impl BaseAir<BabyBear> for ScheduledAir {
    fn width(&self)->usize {self.layout.width}
    fn num_public_values(&self)->usize {self.public_count}
    fn num_periodic_columns(&self)->usize {self.periodic.len()}
    fn periodic_columns(&self)->Cow<'_,[Vec<BabyBear>]> {Cow::Borrowed(&self.periodic)}
}
impl<AB:AirBuilder<F=BabyBear>> Air<AB> for ScheduledAir {
    fn eval(&self,b:&mut AB) {
        let window=b.main();let l=window.current_slice();let n=window.next_slice();let pv=b.public_values().to_vec();let periodic=b.periodic_values().to_vec();
        let w=self.hash_width;let layout=&self.layout;
        if self.geometry==Geometry::Horizontal {
            let mut sub=SubAirBuilder::<_,HorizontalAir,BabyBear>::new(b,0..HORIZONTAL_COLS);
            HorizontalAir::new(horizontal_constants()).eval(&mut sub);
        }else{
            if self.geometry==Geometry::Decomposed {for i in 0..w {let x=AB::Expr::from(l[i])+Into::<AB::Expr>::into(periodic[i]);b.assert_eq(l[layout.a+i],x.square());b.assert_eq(l[layout.b+i],AB::Expr::from(l[layout.a+i]).square());}}
            for (kind,&(start,end,external,internal)) in self.kinds.iter().enumerate() {
                let mut state=(0..w).map(|i|AB::Expr::from(l[i])).collect::<Vec<_>>();
                for i in start..end {let x=state[i].clone()+Into::<AB::Expr>::into(periodic[i]);state[i]=if self.geometry==Geometry::Decomposed {x*l[layout.a+i]*l[layout.b+i]}else{x.exp_const_u64::<7>()};}
                if external||internal {linear(&mut state,external);}
                let gate:AB::Expr=periodic[w+kind].into();for i in 0..w {b.when(gate.clone()).assert_eq(n[i],state[i].clone());}
            }
            let end:AB::Expr=periodic[w+self.kinds.len()].into();
            let mut next=(0..w).map(|i|AB::Expr::from(n[layout.input+i])).collect::<Vec<_>>();linear(&mut next,true);
            for i in 0..w {b.when(end.clone()*b.is_transition()).assert_eq(n[i],next[i].clone());}
            let mut first=(0..w).map(|i|AB::Expr::from(l[layout.input+i])).collect::<Vec<_>>();linear(&mut first,true);
            for i in 0..w {b.when_first_row().assert_eq(l[i],first[i].clone());}
            for i in layout.input..=layout.index {b.when(AB::Expr::ONE-end.clone()).assert_eq(l[i],n[i]);}
        }
        for rule in &self.rules {let gate:AB::Expr=periodic[rule.selector].into();for expr in &rule.expressions {b.when(gate.clone()).assert_zero(expr.eval::<AB>(l,n,&pv,&periodic));}}
    }
}
