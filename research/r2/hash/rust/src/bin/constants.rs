use p3_baby_bear::*;
use p3_field::{PrimeCharacteristicRing,PrimeField32};
use p3_poseidon2::GenericPoseidon2LinearLayers;
fn matrix<const W:usize>(internal:bool)->Vec<Vec<u32>> where GenericPoseidon2LinearLayersBabyBear:GenericPoseidon2LinearLayers<W>{
    let mut matrix=vec![vec![0;W];W];for column in 0..W{let mut state=[BabyBear::ZERO;W];state[column]=BabyBear::ONE;if internal{GenericPoseidon2LinearLayersBabyBear::internal_linear_layer(&mut state);}else{GenericPoseidon2LinearLayersBabyBear::external_linear_layer(&mut state);}for row in 0..W{matrix[row][column]=state[row].as_canonical_u32();}}matrix
}
fn main(){println!("{}",serde_json::json!({
"16":{"initial":BABYBEAR_POSEIDON2_RC_16_EXTERNAL_INITIAL.iter().flatten().map(|x|x.as_canonical_u32()).collect::<Vec<_>>(),"internal":BABYBEAR_POSEIDON2_RC_16_INTERNAL.map(|x|x.as_canonical_u32()),"final":BABYBEAR_POSEIDON2_RC_16_EXTERNAL_FINAL.iter().flatten().map(|x|x.as_canonical_u32()).collect::<Vec<_>>(),"external_matrix":matrix::<16>(false),"internal_matrix":matrix::<16>(true)},
"32":{"initial":BABYBEAR_POSEIDON2_RC_32_EXTERNAL_INITIAL.iter().flatten().map(|x|x.as_canonical_u32()).collect::<Vec<_>>(),"internal":BABYBEAR_POSEIDON2_RC_32_INTERNAL.map(|x|x.as_canonical_u32()),"final":BABYBEAR_POSEIDON2_RC_32_EXTERNAL_FINAL.iter().flatten().map(|x|x.as_canonical_u32()).collect::<Vec<_>>(),"external_matrix":matrix::<32>(false),"internal_matrix":matrix::<32>(true)}
}));}
