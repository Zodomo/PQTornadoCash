use std::collections::{BTreeMap, BTreeSet};

use p3_field::{BasedVectorSpace, Field, PrimeCharacteristicRing, PrimeField32, TwoAdicField};
use p3_fri::{BatchMultiOpening, CommitPhaseMultiStep};
use p3_merkle_tree::PrunedMerklePaths;
use p3_symmetric::MerkleCap;
use pqtc_spec::Digest512;

use crate::codec::{ProofShape, StarkCodecError, TranscriptCheckpoint};
use crate::crypto::{digest_words, proof_leaf_digest, proof_node_digest, words_digest};
use crate::{Challenge, StarkProof, Val};

#[derive(Clone)]
pub(crate) struct QueryHalf {
    pub start: usize,
    pub indices: Vec<u32>,
    pub inputs: Vec<HalfInput>,
    pub fri_rounds: Vec<HalfFriRound>,
}
#[derive(Clone)]
pub(crate) struct HalfInput {
    pub opened_values: Vec<Vec<Vec<Val>>>,
    pub salts: Vec<Vec<Vec<Val>>>,
    pub sibling_hashes: Vec<[u64; 8]>,
}
#[derive(Clone)]
pub(crate) struct HalfFriRound {
    pub sibling_values: Vec<Vec<Challenge>>,
    pub salts: Vec<Vec<Vec<Val>>>,
    pub sibling_hashes: Vec<[u64; 8]>,
}

pub(crate) fn split_queries(
    proof: &StarkProof,
    shape: ProofShape,
    cp: &TranscriptCheckpoint,
) -> Result<[QueryHalf; 2], StarkCodecError> {
    let count = cp.query_indices.len();
    let split = shape.first_queries;
    if split == 0 || split >= count {
        return Err(StarkCodecError::Shape("query halves"));
    }
    let log_height = proof.degree_bits + shape.log_blowup;
    let roots = input_roots(proof)?;
    let mut input_paths = Vec::with_capacity(3);
    for (opening, root) in proof.opening_proof.1.input_openings.iter().zip(roots) {
        input_paths.push(expand_paths(
            &cp.query_indices,
            &input_leaves(&opening.opened_values, &opening.opening_proof.0)?,
            &opening.opening_proof.1,
            log_height,
            commitment_root(root)?,
        )?);
    }
    let (round_indices, round_leaves) = fri_round_leaves(proof, shape, cp)?;
    let mut fri_paths = Vec::with_capacity(shape.fri_rounds());
    for round in 0..shape.fri_rounds() {
        fri_paths.push(expand_paths(
            &round_indices[round],
            &round_leaves[round],
            &proof.opening_proof.1.commit_phase_openings[round]
                .opening_proof
                .1,
            log_height - round - 1,
            commitment_root(&proof.opening_proof.1.commit_phase_commits[round])?,
        )?);
    }
    let build = |start: usize, end: usize| -> Result<QueryHalf, StarkCodecError> {
        let qs: Vec<usize> = (start..end).collect();
        let mut inputs = Vec::with_capacity(3);
        for (batch, opening) in proof.opening_proof.1.input_openings.iter().enumerate() {
            inputs.push(HalfInput {
                opened_values: qs
                    .iter()
                    .map(|&q| opening.opened_values[q].clone())
                    .collect(),
                salts: qs
                    .iter()
                    .map(|&q| opening.opening_proof.0[q].clone())
                    .collect(),
                sibling_hashes: prune_paths(
                    &qs.iter().map(|&q| cp.query_indices[q]).collect::<Vec<_>>(),
                    &qs.iter()
                        .map(|&q| input_paths[batch][q].clone())
                        .collect::<Vec<_>>(),
                )?,
            });
        }
        let mut fri_rounds = Vec::with_capacity(shape.fri_rounds());
        for round in 0..shape.fri_rounds() {
            let opening = &proof.opening_proof.1.commit_phase_openings[round];
            fri_rounds.push(HalfFriRound {
                sibling_values: qs
                    .iter()
                    .map(|&q| opening.sibling_values[q].clone())
                    .collect(),
                salts: qs
                    .iter()
                    .map(|&q| opening.opening_proof.0[q].clone())
                    .collect(),
                sibling_hashes: prune_paths(
                    &qs.iter()
                        .map(|&q| round_indices[round][q])
                        .collect::<Vec<_>>(),
                    &qs.iter()
                        .map(|&q| fri_paths[round][q].clone())
                        .collect::<Vec<_>>(),
                )?,
            });
        }
        Ok(QueryHalf {
            start,
            indices: cp.query_indices[start..end].to_vec(),
            inputs,
            fri_rounds,
        })
    };
    Ok([build(0, split)?, build(split, count)?])
}

pub(crate) fn merge_queries(
    proof: &mut StarkProof,
    shape: ProofShape,
    cp: &TranscriptCheckpoint,
    halves: [QueryHalf; 2],
) -> Result<(), StarkCodecError> {
    let split = shape.first_queries;
    if halves[0].start != 0
        || halves[1].start != split
        || halves[0].indices != cp.query_indices[..split]
        || halves[1].indices != cp.query_indices[split..]
    {
        return Err(StarkCodecError::QueryOrder);
    }
    let log_height = proof.degree_bits + shape.log_blowup;
    let roots = input_roots(proof)?;
    let mut inputs = Vec::with_capacity(3);
    for batch in 0..3 {
        let mut values = halves[0].inputs[batch].opened_values.clone();
        values.extend_from_slice(&halves[1].inputs[batch].opened_values);
        let mut salts = halves[0].inputs[batch].salts.clone();
        salts.extend_from_slice(&halves[1].inputs[batch].salts);
        let mut paths = Vec::with_capacity(shape.query_count);
        for half in &halves {
            paths.extend(expand_paths(
                &half.indices,
                &input_leaves(&half.inputs[batch].opened_values, &half.inputs[batch].salts)?,
                &PrunedMerklePaths {
                    sibling_hashes: half.inputs[batch].sibling_hashes.clone(),
                },
                log_height,
                commitment_root(roots[batch])?,
            )?);
        }
        inputs.push(BatchMultiOpening {
            opened_values: values,
            opening_proof: (
                salts,
                PrunedMerklePaths {
                    sibling_hashes: prune_paths(&cp.query_indices, &paths)?,
                },
            ),
        });
    }
    proof.opening_proof.1.input_openings = inputs;
    let skeleton = (0..shape.fri_rounds())
        .map(|round| {
            let mut values = halves[0].fri_rounds[round].sibling_values.clone();
            values.extend_from_slice(&halves[1].fri_rounds[round].sibling_values);
            let mut salts = halves[0].fri_rounds[round].salts.clone();
            salts.extend_from_slice(&halves[1].fri_rounds[round].salts);
            CommitPhaseMultiStep {
                log_arity: 1,
                sibling_values: values,
                opening_proof: (
                    salts,
                    PrunedMerklePaths {
                        sibling_hashes: Vec::new(),
                    },
                ),
            }
        })
        .collect();
    proof.opening_proof.1.commit_phase_openings = skeleton;
    let (round_indices, round_leaves) = fri_round_leaves(proof, shape, cp)?;
    let mut rounds = Vec::with_capacity(shape.fri_rounds());
    for round in 0..shape.fri_rounds() {
        let mut values = halves[0].fri_rounds[round].sibling_values.clone();
        values.extend_from_slice(&halves[1].fri_rounds[round].sibling_values);
        let mut salts = halves[0].fri_rounds[round].salts.clone();
        salts.extend_from_slice(&halves[1].fri_rounds[round].salts);
        let mut paths = Vec::with_capacity(shape.query_count);
        for (half_no, half) in halves.iter().enumerate() {
            let range = if half_no == 0 {
                0..split
            } else {
                split..shape.query_count
            };
            paths.extend(expand_paths(
                &round_indices[round][range.clone()],
                &round_leaves[round][range],
                &PrunedMerklePaths {
                    sibling_hashes: half.fri_rounds[round].sibling_hashes.clone(),
                },
                log_height - round - 1,
                commitment_root(&proof.opening_proof.1.commit_phase_commits[round])?,
            )?);
        }
        rounds.push(CommitPhaseMultiStep {
            log_arity: 1,
            sibling_values: values,
            opening_proof: (
                salts,
                PrunedMerklePaths {
                    sibling_hashes: prune_paths(&round_indices[round], &paths)?,
                },
            ),
        });
    }
    proof.opening_proof.1.commit_phase_openings = rounds;
    Ok(())
}

fn input_roots(proof: &StarkProof) -> Result<[&MerkleCap<Val, [u64; 8]>; 3], StarkCodecError> {
    Ok([
        proof
            .commitments
            .random
            .as_ref()
            .ok_or(StarkCodecError::Shape("random commitment"))?,
        &proof.commitments.trace,
        &proof.commitments.quotient_chunks,
    ])
}
fn input_leaves(
    values: &[Vec<Vec<Val>>],
    salts: &[Vec<Vec<Val>>],
) -> Result<Vec<Digest512>, StarkCodecError> {
    if values.len() != salts.len() {
        return Err(StarkCodecError::Shape("input salts"));
    }
    values
        .iter()
        .zip(salts)
        .map(|(rows, ss)| {
            if rows.len() != ss.len() {
                return Err(StarkCodecError::Shape("input salts"));
            }
            let mut leaf = Vec::new();
            for (row, salt) in rows.iter().zip(ss) {
                leaf.extend(row.iter().map(PrimeField32::as_canonical_u32));
                leaf.extend(salt.iter().map(PrimeField32::as_canonical_u32));
            }
            Ok(proof_leaf_digest(&leaf))
        })
        .collect()
}
fn fri_round_leaves(
    proof: &StarkProof,
    shape: ProofShape,
    cp: &TranscriptCheckpoint,
) -> Result<(Vec<Vec<u32>>, Vec<Vec<Digest512>>), StarkCodecError> {
    let log_height = proof.degree_bits + shape.log_blowup;
    let reduced = reduced_openings(proof, cp, log_height)?;
    let mut indices = vec![vec![0; shape.query_count]; shape.fri_rounds()];
    let mut leaves = vec![Vec::with_capacity(shape.query_count); shape.fri_rounds()];
    for query in 0..shape.query_count {
        let mut folded = reduced[query];
        let mut index = cp.query_indices[query] as usize;
        for round in 0..shape.fri_rounds() {
            let sibling =
                proof.opening_proof.1.commit_phase_openings[round].sibling_values[query][0];
            let (low, high) = if index & 1 == 0 {
                (folded, sibling)
            } else {
                (sibling, folded)
            };
            let salt = &proof.opening_proof.1.commit_phase_openings[round]
                .opening_proof
                .0[query][0];
            let mut leaf = Vec::with_capacity(16);
            leaf.extend(ext_fields(low));
            leaf.extend(ext_fields(high));
            leaf.extend(salt.iter().map(PrimeField32::as_canonical_u32));
            index >>= 1;
            indices[round][query] = index as u32;
            leaves[round].push(proof_leaf_digest(&leaf));
            folded = fold_binary(
                index,
                log_height - round - 1,
                cp.fri_betas[round],
                low,
                high,
            );
        }
        if folded != proof.opening_proof.1.final_poly[0] {
            return Err(StarkCodecError::Shape("FRI final polynomial"));
        }
    }
    Ok((indices, leaves))
}
fn reduced_openings(
    proof: &StarkProof,
    cp: &TranscriptCheckpoint,
    log_height: usize,
) -> Result<Vec<Challenge>, StarkCodecError> {
    let hiding = &proof.opening_proof.0;
    let zeta_next = cp.zeta * Val::two_adic_generator(proof.degree_bits - 1);
    let mut result = Vec::with_capacity(cp.query_indices.len());
    for (query, &index) in cp.query_indices.iter().enumerate() {
        let x = Val::GENERATOR
            * Val::two_adic_generator(log_height)
                .exp_u64(reverse_bits(index as usize, log_height) as u64);
        let mut power = Challenge::ONE;
        let mut reduced = Challenge::ZERO;
        for batch in 0..3 {
            let matrices = if batch == 2 { 16 } else { 1 };
            for matrix in 0..matrices {
                let points = if batch == 0 {
                    vec![(
                        cp.zeta,
                        with_hidden(
                            proof
                                .opened_values
                                .random
                                .as_ref()
                                .ok_or(StarkCodecError::Shape("random opening"))?,
                            &hiding[0][0][0],
                        ),
                    )]
                } else if batch == 1 {
                    vec![
                        (
                            cp.zeta,
                            with_hidden(&proof.opened_values.trace_local, &hiding[1][0][0]),
                        ),
                        (
                            zeta_next,
                            with_hidden(
                                proof
                                    .opened_values
                                    .trace_next
                                    .as_ref()
                                    .ok_or(StarkCodecError::Shape("trace next"))?,
                                &hiding[1][0][1],
                            ),
                        ),
                    ]
                } else {
                    vec![(
                        cp.zeta,
                        with_hidden(
                            &proof.opened_values.quotient_chunks[matrix],
                            &hiding[2][matrix][0],
                        ),
                    )]
                };
                let row = &proof.opening_proof.1.input_openings[batch].opened_values[query][matrix];
                for (point, at_point) in points {
                    if row.len() != at_point.len() {
                        return Err(StarkCodecError::Shape("reduced opening"));
                    }
                    let inverse = (point - x).inverse();
                    for (&at_x, at_z) in row.iter().zip(at_point) {
                        reduced += power * (at_z - at_x) * inverse;
                        power *= cp.fri_alpha;
                    }
                }
            }
        }
        result.push(reduced);
    }
    Ok(result)
}
fn with_hidden(public: &[Challenge], hidden: &[Challenge]) -> Vec<Challenge> {
    public.iter().chain(hidden).copied().collect()
}
fn ext_fields(value: Challenge) -> impl Iterator<Item = u32> {
    let coefficients: &[Val] = value.as_basis_coefficients_slice();
    coefficients
        .iter()
        .map(PrimeField32::as_canonical_u32)
        .collect::<Vec<_>>()
        .into_iter()
}
fn fold_binary(
    index: usize,
    log_height: usize,
    beta: Challenge,
    low: Challenge,
    high: Challenge,
) -> Challenge {
    let x = Val::two_adic_generator(log_height + 1).exp_u64(reverse_bits(index, log_height) as u64);
    let inv = Val::TWO.inverse() * x.inverse();
    (low + high) * Val::TWO.inverse() + (low - high) * inv * beta
}
fn reverse_bits(value: usize, bits: usize) -> usize {
    (0..bits).fold(0, |out, bit| (out << 1) | ((value >> bit) & 1))
}
fn commitment_root(cap: &MerkleCap<Val, [u64; 8]>) -> Result<Digest512, StarkCodecError> {
    cap.roots()
        .first()
        .copied()
        .map(words_digest)
        .ok_or(StarkCodecError::Shape("Merkle root"))
}
fn expand_paths(
    indices: &[u32],
    leaves: &[Digest512],
    pruned: &PrunedMerklePaths<u64, 8>,
    height: usize,
    root: Digest512,
) -> Result<Vec<Vec<Digest512>>, StarkCodecError> {
    if indices.len() != leaves.len() {
        return Err(StarkCodecError::Shape("multiproof leaves"));
    }
    let mut nodes = BTreeMap::new();
    for (&index, &leaf) in indices.iter().zip(leaves) {
        if let Some(old) = nodes.insert(index as usize, leaf)
            && old != leaf
        {
            return Err(StarkCodecError::Shape("duplicate query opening"));
        }
    }
    let unique: Vec<usize> = nodes.keys().copied().collect();
    let mut paths: BTreeMap<usize, Vec<Digest512>> = unique
        .iter()
        .map(|&i| (i, Vec::with_capacity(height)))
        .collect();
    let mut cursor = 0;
    for level in 0..height {
        let groups: Vec<usize> = nodes
            .keys()
            .map(|i| i >> 1)
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        let mut complete = nodes.clone();
        for &group in &groups {
            for child in [group << 1, (group << 1) | 1] {
                if let std::collections::btree_map::Entry::Vacant(entry) = complete.entry(child) {
                    let sibling = pruned
                        .sibling_hashes
                        .get(cursor)
                        .copied()
                        .ok_or(StarkCodecError::Shape("pruned multiproof"))?;
                    cursor += 1;
                    entry.insert(words_digest(sibling));
                }
            }
        }
        for &leaf in &unique {
            paths
                .get_mut(&leaf)
                .expect("known leaf")
                .push(complete[&((leaf >> level) ^ 1)]);
        }
        nodes = groups
            .into_iter()
            .map(|group| {
                (
                    group,
                    proof_node_digest(complete[&(group << 1)], complete[&((group << 1) | 1)]),
                )
            })
            .collect();
    }
    if cursor != pruned.sibling_hashes.len()
        || nodes.len() != 1
        || nodes.values().next().copied() != Some(root)
    {
        return Err(StarkCodecError::Shape("pruned multiproof root"));
    }
    Ok(indices
        .iter()
        .map(|i| paths[&(*i as usize)].clone())
        .collect())
}
fn prune_paths(
    indices: &[u32],
    paths: &[Vec<Digest512>],
) -> Result<Vec<[u64; 8]>, StarkCodecError> {
    if indices.len() != paths.len() {
        return Err(StarkCodecError::Shape("multiproof paths"));
    }
    let mut nodes = BTreeMap::<usize, usize>::new();
    for (slot, &index) in indices.iter().enumerate() {
        if let Some(&old) = nodes.get(&(index as usize)) {
            if paths[old] != paths[slot] {
                return Err(StarkCodecError::Shape("duplicate query path"));
            }
        } else {
            nodes.insert(index as usize, slot);
        }
    }
    let height = paths.first().map_or(0, Vec::len);
    if paths.iter().any(|p| p.len() != height) {
        return Err(StarkCodecError::Shape("multiproof path height"));
    }
    let mut out = Vec::new();
    for level in 0..height {
        let groups: Vec<usize> = nodes
            .keys()
            .map(|i| i >> 1)
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        for &group in &groups {
            match (nodes.get(&(group << 1)), nodes.get(&((group << 1) | 1))) {
                (Some(&slot), None) | (None, Some(&slot)) => {
                    out.push(digest_words(paths[slot][level]))
                }
                (Some(_), Some(_)) => {}
                (None, None) => unreachable!(),
            }
        }
        nodes = groups
            .into_iter()
            .map(|group| {
                let slot = nodes
                    .get(&(group << 1))
                    .or_else(|| nodes.get(&((group << 1) | 1)))
                    .copied()
                    .expect("group member");
                (group, slot)
            })
            .collect();
    }
    Ok(out)
}
