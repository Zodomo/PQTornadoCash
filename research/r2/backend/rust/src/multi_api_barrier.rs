//! Expected compile error at the next real adapter boundary, not a synthetic AIR.
//! Pinned multi-stark prove/verify require this trait even though MultilinearPcs
//! alone is enough to declare MultiStarkConfig.
use pqtc_r2_backend::{Challenger, EF, F, HidingPcs};
fn required_by_multilinear_air<P: p3_sumcheck::PrescribedPointPcs<EF, Challenger, Val = F, Commitment = <HidingPcs as p3_commit::MultilinearPcs<EF, Challenger>>::Commitment>>() {}
fn main() { required_by_multilinear_air::<HidingPcs>(); }
