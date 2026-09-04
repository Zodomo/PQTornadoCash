//! Plain-reference P2BB512-v1 withdrawal relation.

pub mod air;

pub use air::{
    ACTIVE_PERMUTATIONS, MAX_CONSTRAINT_DEGREE, NUM_CONSTRAINTS, NUM_POSEIDON_COLS,
    NUM_WITHDRAWAL_COLS, TRACE_HEIGHT, WithdrawalAir, evaluate_constraints,
    generate_withdrawal_trace,
};

use p3_baby_bear::BabyBear;
use p3_field::PrimeCharacteristicRing;
use pqtc_hash::{commitment, digest_to_elements, nullifier_hash};
use pqtc_spec::{CanonicalSecret, Digest512, TREE_DEPTH, WithdrawalStatement};
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Private data for the fixed-depth withdrawal relation.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct WithdrawalWitness {
    pub nullifier_secret: CanonicalSecret,
    pub trapdoor: CanonicalSecret,
    pub leaf_index: u32,
    pub path_bits: [u8; TREE_DEPTH as usize],
    pub siblings: [Digest512; TREE_DEPTH as usize],
}

impl WithdrawalWitness {
    #[must_use]
    pub fn commitment(&self, scope: Digest512) -> Digest512 {
        commitment(scope, self.nullifier_secret, self.trapdoor)
    }
}

/// Checks the non-polynomial input preconditions and the plain withdrawal relation.
///
/// # Errors
///
/// Returns [`RelationError`] when the statement or witness is noncanonical or
/// does not satisfy the withdrawal relation.
pub fn check_witness(
    statement: WithdrawalStatement,
    witness: &WithdrawalWitness,
) -> Result<(), RelationError> {
    for (name, digest) in [
        ("scope", statement.scope),
        ("root", statement.root),
        ("nullifier", statement.nullifier_hash),
        ("payout", statement.payout_digest),
    ] {
        if digest_to_elements(digest).is_none() {
            return Err(RelationError::NonCanonicalDigest(name));
        }
    }
    if witness.leaf_index >= 1 << TREE_DEPTH {
        return Err(RelationError::LeafIndexOutOfRange);
    }
    for (level, (&bit, sibling)) in witness.path_bits.iter().zip(&witness.siblings).enumerate() {
        if bit > 1 {
            return Err(RelationError::NonBooleanPathBit { level, value: bit });
        }
        if bit != ((witness.leaf_index >> level) & 1) as u8 {
            return Err(RelationError::PathIndexMismatch { level });
        }
        if digest_to_elements(*sibling).is_none() {
            return Err(RelationError::NonCanonicalSibling { level });
        }
    }
    if nullifier_hash(statement.scope, witness.nullifier_secret) != statement.nullifier_hash {
        return Err(RelationError::NullifierMismatch);
    }
    let mut current = witness.commitment(statement.scope);
    for (level, (&bit, sibling)) in witness.path_bits.iter().zip(&witness.siblings).enumerate() {
        let level = u8::try_from(level).map_err(|_| RelationError::LeafIndexOutOfRange)?;
        current = if bit == 0 {
            pqtc_hash::merkle_node(level, current, *sibling)
        } else {
            pqtc_hash::merkle_node(level, *sibling, current)
        };
    }
    if current != statement.root {
        return Err(RelationError::RootMismatch);
    }
    Ok(())
}

/// Converts the four statement digests to the AIR's 64 public `BabyBear` values.
///
/// # Panics
///
/// Panics when a statement digest contains a noncanonical field element.
pub fn public_values(statement: WithdrawalStatement) -> [BabyBear; 64] {
    let mut values = [BabyBear::ZERO; 64];
    for (chunk, digest) in values.chunks_exact_mut(16).zip([
        statement.scope,
        statement.root,
        statement.nullifier_hash,
        statement.payout_digest,
    ]) {
        chunk.copy_from_slice(
            &digest_to_elements(digest)
                .expect("withdrawal statement contains a non-canonical digest"),
        );
    }
    values
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum RelationError {
    #[error("{0} digest contains a non-canonical BabyBear element")]
    NonCanonicalDigest(&'static str),
    #[error("Merkle sibling at level {level} contains a non-canonical BabyBear element")]
    NonCanonicalSibling { level: usize },
    #[error("leaf index is not a 20-bit value")]
    LeafIndexOutOfRange,
    #[error("path bit {level} has non-boolean value {value}")]
    NonBooleanPathBit { level: usize, value: u8 },
    #[error("path bit {level} does not equal the leaf-index bit")]
    PathIndexMismatch { level: usize },
    #[error("computed nullifier does not equal the public nullifier")]
    NullifierMismatch,
    #[error("computed Merkle root does not equal the public root")]
    RootMismatch,
}

#[cfg(test)]
mod tests {
    use p3_air::{
        BaseAir,
        symbolic::{AirLayout, get_max_constraint_degree, get_symbolic_constraints},
    };
    use p3_field::PrimeCharacteristicRing;
    use p3_matrix::Matrix;
    use pqtc_hash::{commitment, nullifier_hash, payout_digest};
    use pqtc_merkle::MerkleTree;

    use super::*;
    use crate::air::{
        INDEX, IS_MERKLE, IS_NOTE, IS_NULLIFIER, IS_PADDING, IS_PAYOUT, LEVEL_BITS, PATH_BIT,
        STEP_BITS, WORK, poseidon_input,
    };

    fn fixture() -> (WithdrawalStatement, WithdrawalWitness) {
        let scope = pqtc_hash::p2bb512(pqtc_spec::domains::SCOPE, 0, 0, &[]);
        let secret = CanonicalSecret::from_bytes([3; 32]).unwrap();
        let trapdoor = CanonicalSecret::from_bytes([4; 32]).unwrap();
        let leaf = commitment(scope, secret, trapdoor);
        let mut tree = MerkleTree::new(scope);
        let (leaf_index, root) = tree.insert(leaf).unwrap();
        let path = tree.path(leaf_index).unwrap();
        (
            WithdrawalStatement {
                scope,
                root,
                nullifier_hash: nullifier_hash(scope, secret),
                payout_digest: payout_digest([5; 20], [6; 20], [0; 32]),
            },
            WithdrawalWitness {
                nullifier_secret: secret,
                trapdoor,
                leaf_index,
                path_bits: path.path_bits(),
                siblings: path.siblings,
            },
        )
    }

    fn statement_for_witness(
        scope: Digest512,
        payout_digest: Digest512,
        witness: &WithdrawalWitness,
    ) -> WithdrawalStatement {
        let mut root = witness.commitment(scope);
        for (level, (&bit, sibling)) in witness.path_bits.iter().zip(&witness.siblings).enumerate()
        {
            root = if bit == 0 {
                pqtc_hash::merkle_node(level as u8, root, *sibling)
            } else {
                pqtc_hash::merkle_node(level as u8, *sibling, root)
            };
        }
        WithdrawalStatement {
            scope,
            root,
            nullifier_hash: nullifier_hash(scope, witness.nullifier_secret),
            payout_digest,
        }
    }

    fn rejected(trace: &p3_matrix::dense::RowMajorMatrix<BabyBear>, public: &[BabyBear]) -> bool {
        !evaluate_constraints(trace, public, Some(1)).is_ok()
    }

    #[test]
    fn valid_witness_has_fixed_secure_shape() {
        let (statement, witness) = fixture();
        let trace = generate_withdrawal_trace(statement, &witness).unwrap();
        assert_eq!(trace.height(), TRACE_HEIGHT);
        assert_eq!(trace.width(), NUM_WITHDRAWAL_COLS);
        assert_eq!(WithdrawalAir::default().width(), NUM_WITHDRAWAL_COLS);
        assert_eq!(NUM_WITHDRAWAL_COLS, 190);
        assert_eq!(ACTIVE_PERMUTATIONS, 240);
        assert_eq!(NUM_CONSTRAINTS, 1_186);
        assert_eq!(MAX_CONSTRAINT_DEGREE, 7);
        assert!(evaluate_constraints(&trace, &public_values(statement), None).is_ok());
    }
    #[test]
    fn row_schedule_and_commitment_overwrite_are_exact() {
        let (statement, witness) = fixture();
        let trace = generate_withdrawal_trace(statement, &witness).unwrap();
        let row = |index: usize| trace.row_slice(index).unwrap();
        for (index, selector) in [
            (0, IS_NULLIFIER),
            (8, IS_NULLIFIER),
            (9, IS_NOTE),
            (19, IS_NOTE),
            (20, IS_MERKLE),
            (239, IS_MERKLE),
            (240, IS_PAYOUT),
            (243, IS_PAYOUT),
            (244, IS_PADDING),
            (255, IS_PADDING),
        ] {
            assert_eq!(
                row(index)[selector],
                BabyBear::ONE,
                "wrong selector on row {index}"
            );
        }
        let secret = (*witness.nullifier_secret.limbs()).map(BabyBear::from_u32);
        for index in 0..=16 {
            assert_eq!(&row(index)[WORK..WORK + 8], &secret);
            assert_eq!(&row(index)[WORK + 8..WORK + 16], &[BabyBear::ZERO; 8]);
        }
        for chunk in 0..4 {
            let destination_row = 17 + chunk;
            assert_eq!(
                &row(destination_row)[WORK + chunk * 4..WORK + (chunk + 1) * 4],
                &row(destination_row - 1)[141..145],
                "commitment chunk {chunk} was not assembled"
            );
        }
        for index in 240..TRACE_HEIGHT {
            assert_eq!(&row(index)[WORK..WORK + 16], &[BabyBear::ZERO; 16]);
        }
    }

    #[test]
    fn symbolic_report_matches_declared_shape() {
        let air = WithdrawalAir::default();
        let layout = AirLayout::from_air::<BabyBear>(&air);
        assert_eq!(
            get_symbolic_constraints::<BabyBear, _>(&air, layout).len(),
            NUM_CONSTRAINTS
        );
        assert_eq!(
            get_max_constraint_degree::<BabyBear, _>(&air, layout, TRACE_HEIGHT),
            MAX_CONSTRAINT_DEGREE
        );
    }

    #[test]
    fn every_private_limb_and_work_column_is_constrained() {
        let (statement, witness) = fixture();
        let baseline = generate_withdrawal_trace(statement, &witness).unwrap();
        let public = public_values(statement);

        for limb in 0..8 {
            for (row, name) in [
                (4 + limb / 4, "nullifier secret"),
                (13 + limb / 4, "note secret"),
            ] {
                let mut trace = baseline.clone();
                trace.values[row * NUM_WITHDRAWAL_COLS + poseidon_input(limb % 4)] += BabyBear::ONE;
                assert!(rejected(&trace, &public), "{name} limb {limb} was free");
            }
            let mut trace = baseline.clone();
            trace.values[(15 + limb / 4) * NUM_WITHDRAWAL_COLS + poseidon_input(limb % 4)] +=
                BabyBear::ONE;
            assert!(rejected(&trace, &public), "trapdoor limb {limb} was free");
        }

        for column in 0..16 {
            for row in [0, 8, 9, 19, 20] {
                let mut trace = baseline.clone();
                trace.values[row * NUM_WITHDRAWAL_COLS + WORK + column] += BabyBear::ONE;
                assert!(
                    rejected(&trace, &public),
                    "WORK[{column}] was free on row {row}"
                );
            }
        }
    }

    #[test]
    fn every_secret_limb_is_used_by_both_private_hashes() {
        let (original, witness) = fixture();
        for limb in 0..CanonicalSecret::LIMB_COUNT {
            let mut changed = witness.clone();
            let mut limbs = changed.nullifier_secret.into_limbs();
            limbs[limb] += 1;
            changed.nullifier_secret = CanonicalSecret::from_limbs(limbs).unwrap();
            let changed_statement =
                statement_for_witness(original.scope, original.payout_digest, &changed);
            let trace = generate_withdrawal_trace(changed_statement, &changed).unwrap();

            let mut old_nullifier = changed_statement;
            old_nullifier.nullifier_hash = original.nullifier_hash;
            assert!(
                rejected(&trace, &public_values(old_nullifier)),
                "secret limb {limb} was absent from the nullifier hash"
            );
            let mut old_commitment = changed_statement;
            old_commitment.root = original.root;
            assert!(
                rejected(&trace, &public_values(old_commitment)),
                "secret limb {limb} was absent from the note commitment"
            );
        }
    }

    #[test]
    fn every_trapdoor_delta_changes_the_note_commitment() {
        let (original, witness) = fixture();
        for limb in 0..CanonicalSecret::LIMB_COUNT {
            let mut changed = witness.clone();
            let mut limbs = changed.trapdoor.into_limbs();
            limbs[limb] += 1;
            changed.trapdoor = CanonicalSecret::from_limbs(limbs).unwrap();
            let changed_statement =
                statement_for_witness(original.scope, original.payout_digest, &changed);
            let trace = generate_withdrawal_trace(changed_statement, &changed).unwrap();
            assert!(
                rejected(&trace, &public_values(original)),
                "trapdoor limb {limb} did not affect the note commitment"
            );
        }
    }

    #[test]
    fn operation_and_merkle_boundaries_are_constrained() {
        let (statement, witness) = fixture();
        let baseline = generate_withdrawal_trace(statement, &witness).unwrap();
        let public = public_values(statement);
        let mut boundaries = vec![
            (8, "nullifier/note"),
            (19, "note/merkle"),
            (239, "merkle/payout"),
            (243, "payout/padding"),
        ];
        boundaries.extend((0..19).map(|level| (20 + level * 11 + 10, "Merkle level")));
        for (row, name) in boundaries {
            let mut trace = baseline.clone();
            trace.values[(row + 1) * NUM_WITHDRAWAL_COLS + STEP_BITS] += BabyBear::ONE;
            assert!(
                rejected(&trace, &public),
                "{name} boundary after row {row} was free"
            );
        }
        for (row, column, name) in [
            (9, LEVEL_BITS, "note level"),
            (20, PATH_BIT, "path bit"),
            (20, LEVEL_BITS, "level"),
            (20, INDEX, "leaf index"),
            (21, poseidon_input(0), "sibling"),
            (244, poseidon_input(0), "padding"),
            (244, LEVEL_BITS, "padding level"),
            (244, WORK, "padding work"),
        ] {
            let mut trace = baseline.clone();
            trace.values[row * NUM_WITHDRAWAL_COLS + column] += BabyBear::ONE;
            assert!(rejected(&trace, &public), "mutation was accepted: {name}");
        }
    }

    #[test]
    fn every_public_field_is_bound() {
        let (statement, witness) = fixture();
        let trace = generate_withdrawal_trace(statement, &witness).unwrap();
        let public = public_values(statement);
        for index in 0..64 {
            let mut mutated = public;
            mutated[index] += BabyBear::ONE;
            assert!(
                rejected(&trace, &mutated),
                "public field {index} was not bound"
            );
        }
    }
}
