//! Simple u64 arithmetic reference, independent of Plonky3 field/permutation code.
include!("constants.rs");
const P:u64=2013265921;
fn pow7(x:u64)->u64 {let x=x%P;let x2=x*x%P;let x4=x2*x2%P;x4*x2%P*x%P}
fn external(s:&mut [u64]) {
    for a in s.chunks_exact_mut(4){let [w,x,y,z]=<[u64;4]>::try_from(&*a).unwrap();a.copy_from_slice(&[(2*w+3*x+y+z)%P,(w+2*x+3*y+z)%P,(w+x+2*y+3*z)%P,(3*w+x+y+2*z)%P]);}
    let mut sums=[0u64;4];for(i,x)in s.iter().enumerate(){sums[i%4]+=x;}for(i,x)in s.iter_mut().enumerate(){*x=(*x+sums[i%4])%P;}
}
pub fn permute(input:&[u32])->Vec<u32> {
    let (initial,internal,finals,diag):(&[u64],&[u64],&[u64],&[u64])=match input.len(){16=>(&INITIAL16,&INTERNAL16,&FINAL16,&DIAGONAL16),32=>(&INITIAL32,&INTERNAL32,&FINAL32,&DIAGONAL32),_=>panic!("width")};
    let mut s:Vec<u64>=input.iter().map(|&x|{assert!(u64::from(x)<P);u64::from(x)}).collect();let w=s.len();external(&mut s);
    for row in initial.chunks_exact(w){for(x,c)in s.iter_mut().zip(row){*x=pow7(*x+c);}external(&mut s);}
    for c in internal {s[0]=pow7(s[0]+c);let sum=s.iter().sum::<u64>()%P;for(x,d)in s.iter_mut().zip(diag){*x=(sum+*x*d)%P;}}
    for row in finals.chunks_exact(w){for(x,c)in s.iter_mut().zip(row){*x=pow7(*x+c);}external(&mut s);}s.into_iter().map(|x|x as u32).collect()
}
pub fn sponge(tag:u8,bytes:u32,level:u32,payload:&[u32])->Vec<u32>{
    let mut s=vec![0;16];s[4..9].copy_from_slice(&[1,u32::from(tag),bytes,payload.len()as u32,level]);
    if payload.is_empty(){s=permute(&s);}else{for chunk in payload.chunks(4){for(i,&v)in chunk.iter().enumerate(){s[i]=((u64::from(s[i])+u64::from(v))%P)as u32;}s=permute(&s);}}
    let mut out=Vec::with_capacity(16);for b in 0..4{if b!=0{s=permute(&s);}out.extend_from_slice(&s[..4]);}out
}
