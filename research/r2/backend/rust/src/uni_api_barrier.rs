//! Expected compile error: HidingWhirPcs has MultilinearPcs, not uni-stark's Pcs.
use pqtc_r2_backend::{Challenger, EF, F, HidingPcs};
fn required_by_frozen_uni_stark<P: p3_commit::Pcs<EF, Challenger, Domain = p3_field::coset::TwoAdicMultiplicativeCoset<F>>>() {}
fn main() { required_by_frozen_uni_stark::<HidingPcs>(); }
