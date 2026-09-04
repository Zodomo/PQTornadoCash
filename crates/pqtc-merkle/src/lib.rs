//! Append-only depth-20 P2BB512 application Merkle tree.

use pqtc_hash::{digest_to_elements, empty_leaf, merkle_node};
use pqtc_spec::{Digest512, TREE_DEPTH};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use thiserror::Error;

pub const CAPACITY: u32 = 1 << TREE_DEPTH;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct MerklePath {
    pub leaf_index: u32,
    pub siblings: [Digest512; TREE_DEPTH as usize],
}

impl MerklePath {
    #[must_use]
    pub fn root(&self, leaf: Digest512) -> Digest512 {
        let mut current = leaf;
        for (level, sibling) in self.siblings.iter().enumerate() {
            current = if self.leaf_index & (1 << level) == 0 {
                merkle_node(level_u8(level), current, *sibling)
            } else {
                merkle_node(level_u8(level), *sibling, current)
            };
        }
        current
    }

    #[must_use]
    pub fn path_bits(&self) -> [u8; TREE_DEPTH as usize] {
        core::array::from_fn(|level| ((self.leaf_index >> level) & 1) as u8)
    }
}

#[derive(Clone, Debug)]
pub struct MerkleTree {
    zeros: [Digest512; TREE_DEPTH as usize + 1],
    filled_subtrees: [Digest512; TREE_DEPTH as usize],
    leaves: Vec<Digest512>,
    commitments: HashSet<Digest512>,
    root: Digest512,
}

impl MerkleTree {
    /// Constructs a tree for a canonical P2BB512 scope.
    ///
    /// # Panics
    ///
    /// Panics when `scope` contains a noncanonical `BabyBear` limb. Untrusted
    /// inputs must use [`Self::try_new`].
    #[must_use]
    pub fn new(scope: Digest512) -> Self {
        Self::try_new(scope).expect("Merkle scope contains a noncanonical BabyBear limb")
    }

    /// Constructs a tree after validating every scope limb.
    ///
    /// # Errors
    ///
    /// Returns [`MerkleError::NonCanonicalDigest`] for a noncanonical scope.
    pub fn try_new(scope: Digest512) -> Result<Self, MerkleError> {
        ensure_canonical(scope)?;
        let mut zeros = [Digest512::ZERO; TREE_DEPTH as usize + 1];
        zeros[0] = empty_leaf(scope);
        for level in 0..TREE_DEPTH as usize {
            zeros[level + 1] = merkle_node(level_u8(level), zeros[level], zeros[level]);
        }
        Ok(Self {
            filled_subtrees: core::array::from_fn(|level| zeros[level]),
            leaves: Vec::new(),
            commitments: HashSet::new(),
            root: zeros[TREE_DEPTH as usize],
            zeros,
        })
    }

    #[must_use]
    pub const fn root(&self) -> Digest512 {
        self.root
    }

    #[must_use]
    pub fn len(&self) -> u32 {
        u32::try_from(self.leaves.len()).unwrap_or(u32::MAX)
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.leaves.is_empty()
    }

    #[must_use]
    pub fn zeros(&self) -> &[Digest512; TREE_DEPTH as usize + 1] {
        &self.zeros
    }

    /// Inserts one unique nonzero commitment and returns its index and new root.
    ///
    /// # Errors
    ///
    /// Returns [`MerkleError`] when the commitment is zero or duplicated, or
    /// when the tree is full.
    pub fn insert(&mut self, leaf: Digest512) -> Result<(u32, Digest512), MerkleError> {
        ensure_canonical(leaf)?;
        if leaf.is_zero() {
            return Err(MerkleError::ZeroCommitment);
        }
        if self.leaves.len() >= CAPACITY as usize {
            return Err(MerkleError::Full);
        }
        if !self.commitments.insert(leaf) {
            return Err(MerkleError::DuplicateCommitment);
        }

        let leaf_index = u32::try_from(self.leaves.len()).map_err(|_| MerkleError::Full)?;
        let mut current = leaf;
        let mut index = leaf_index;
        for level in 0..TREE_DEPTH as usize {
            if index & 1 == 0 {
                self.filled_subtrees[level] = current;
                current = merkle_node(level_u8(level), current, self.zeros[level]);
            } else {
                current = merkle_node(level_u8(level), self.filled_subtrees[level], current);
            }
            index >>= 1;
        }
        self.leaves.push(leaf);
        self.root = current;
        Ok((leaf_index, current))
    }

    /// Returns the authentication path for an inserted leaf.
    ///
    /// # Errors
    ///
    /// Returns [`MerkleError::UnknownLeaf`] when `leaf_index` is not present.
    pub fn path(&self, leaf_index: u32) -> Result<MerklePath, MerkleError> {
        if leaf_index as usize >= self.leaves.len() {
            return Err(MerkleError::UnknownLeaf { index: leaf_index });
        }
        let mut siblings = [Digest512::ZERO; TREE_DEPTH as usize];
        let mut nodes = self.leaves.clone();
        let mut index = leaf_index as usize;
        for (level, sibling) in siblings.iter_mut().enumerate() {
            *sibling = nodes.get(index ^ 1).copied().unwrap_or(self.zeros[level]);
            if nodes.len() & 1 == 1 {
                nodes.push(self.zeros[level]);
            }
            nodes = nodes
                .chunks_exact(2)
                .map(|pair| merkle_node(level_u8(level), pair[0], pair[1]))
                .collect();
            index >>= 1;
        }
        let path = MerklePath {
            leaf_index,
            siblings,
        };
        debug_assert_eq!(path.root(self.leaves[leaf_index as usize]), self.root);
        Ok(path)
    }

    #[must_use]
    pub fn leaf(&self, index: u32) -> Option<Digest512> {
        self.leaves.get(index as usize).copied()
    }
}

fn level_u8(level: usize) -> u8 {
    u8::try_from(level).unwrap_or_default()
}

fn ensure_canonical(digest: Digest512) -> Result<(), MerkleError> {
    digest_to_elements(digest)
        .map(|_| ())
        .ok_or(MerkleError::NonCanonicalDigest)
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum MerkleError {
    #[error("digest contains a noncanonical BabyBear limb")]
    NonCanonicalDigest,
    #[error("commitment cannot be zero")]
    ZeroCommitment,
    #[error("commitment already exists")]
    DuplicateCommitment,
    #[error("tree is full")]
    Full,
    #[error("leaf index {index} is not present")]
    UnknownLeaf { index: u32 },
}

#[cfg(test)]
mod tests {
    use super::*;

    fn digest(n: u8) -> Digest512 {
        Digest512 {
            left: [n; 32],
            right: [n.wrapping_add(1); 32],
        }
    }

    #[test]
    fn roots_and_paths_match_after_every_insert() {
        let mut tree = MerkleTree::new(digest(9));
        for i in 1..=64 {
            let leaf = digest(i);
            let (index, root) = tree.insert(leaf).unwrap();
            assert_eq!(tree.path(index).unwrap().root(leaf), root);
            for prior in 0..=index {
                assert_eq!(
                    tree.path(prior).unwrap().root(tree.leaf(prior).unwrap()),
                    root
                );
            }
        }
    }

    #[test]
    fn rejects_zero_duplicate_and_unknown_leaf() {
        let mut tree = MerkleTree::new(digest(9));
        assert_eq!(
            tree.insert(Digest512::ZERO),
            Err(MerkleError::ZeroCommitment)
        );
        tree.insert(digest(1)).unwrap();
        assert_eq!(
            tree.insert(digest(1)),
            Err(MerkleError::DuplicateCommitment)
        );
        assert_eq!(tree.path(1), Err(MerkleError::UnknownLeaf { index: 1 }));
    }

    #[test]
    fn merkle_node_is_bound_to_its_level() {
        let left = digest(1);
        let right = digest(2);
        assert_ne!(merkle_node(0, left, right), merkle_node(1, left, right));
    }

    #[test]
    fn rejects_noncanonical_scope_and_commitment() {
        let mut bytes = [0u8; 64];
        bytes[..4].copy_from_slice(&pqtc_spec::BABY_BEAR_MODULUS.to_be_bytes());
        let invalid = Digest512::from_bytes(bytes);
        assert!(matches!(
            MerkleTree::try_new(invalid),
            Err(MerkleError::NonCanonicalDigest)
        ));
        let mut tree = MerkleTree::new(digest(1));
        assert_eq!(tree.insert(invalid), Err(MerkleError::NonCanonicalDigest));
    }
}
