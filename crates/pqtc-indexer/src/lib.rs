//! Reorg-aware deposit-log replay and Merkle-path construction.

use pqtc_merkle::{MerklePath, MerkleTree};
use pqtc_spec::{Digest512, PROTOCOL_VERSION};
use serde::{Deserialize, Serialize};
use thiserror::Error;

pub const SNAPSHOT_VERSION: u16 = PROTOCOL_VERSION as u16;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DepositLog {
    pub commitment: Digest512,
    pub leaf_index: u32,
    pub root: Digest512,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexedBlock {
    pub number: u64,
    pub hash: [u8; 32],
    pub parent_hash: [u8; 32],
    pub deposits: Vec<DepositLog>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexerSnapshot {
    pub version: u16,
    pub scope: Digest512,
    pub confirmations: u64,
    pub blocks: Vec<IndexedBlock>,
}

#[derive(Clone, Debug)]
pub struct Indexer {
    scope: Digest512,
    confirmations: u64,
    blocks: Vec<IndexedBlock>,
    tree: MerkleTree,
}

impl Indexer {
    /// Constructs an indexer after validating the canonical P2BB512 scope.
    ///
    /// # Errors
    ///
    /// Returns [`IndexError::NonCanonicalDigest`] for a noncanonical scope.
    pub fn new(scope: Digest512, confirmations: u64) -> Result<Self, IndexError> {
        Ok(Self {
            scope,
            confirmations,
            blocks: Vec::new(),
            tree: MerkleTree::try_new(scope).map_err(|_| IndexError::NonCanonicalDigest)?,
        })
    }

    pub fn apply_block(&mut self, block: IndexedBlock) -> Result<(), IndexError> {
        if let Some(tip) = self.blocks.last() {
            if block.parent_hash != tip.hash {
                let ancestor = self
                    .blocks
                    .iter()
                    .position(|candidate| candidate.hash == block.parent_hash)
                    .ok_or(IndexError::UnknownParent)?;
                self.blocks.truncate(ancestor + 1);
                self.rebuild()?;
            }
            let expected = self.blocks.last().expect("ancestor retained").number + 1;
            if block.number != expected {
                return Err(IndexError::NonSequentialBlock {
                    expected,
                    actual: block.number,
                });
            }
        }
        self.apply_deposits(&block.deposits)?;
        self.blocks.push(block);
        Ok(())
    }

    pub fn confirmed_path(
        &self,
        commitment: Digest512,
    ) -> Result<(Digest512, MerklePath), IndexError> {
        let tip = self.blocks.last().ok_or(IndexError::NoBlocks)?.number;
        let deposit = self
            .blocks
            .iter()
            .flat_map(|block| block.deposits.iter().map(move |log| (block.number, log)))
            .find(|(_, log)| log.commitment == commitment)
            .ok_or(IndexError::UnknownCommitment)?;
        if tip.saturating_sub(deposit.0) < self.confirmations {
            return Err(IndexError::Unconfirmed);
        }
        Ok((
            self.tree.root(),
            self.tree
                .path(deposit.1.leaf_index)
                .map_err(|_| IndexError::UnknownCommitment)?,
        ))
    }

    #[must_use]
    pub fn tip(&self) -> Option<(u64, [u8; 32])> {
        self.blocks.last().map(|block| (block.number, block.hash))
    }

    #[must_use]
    pub fn snapshot(&self) -> IndexerSnapshot {
        IndexerSnapshot {
            version: SNAPSHOT_VERSION,
            scope: self.scope,
            confirmations: self.confirmations,
            blocks: self.blocks.clone(),
        }
    }

    pub fn from_snapshot(snapshot: IndexerSnapshot) -> Result<Self, IndexError> {
        if snapshot.version != SNAPSHOT_VERSION {
            return Err(IndexError::UnsupportedSnapshot(snapshot.version));
        }
        let mut indexer = Self::new(snapshot.scope, snapshot.confirmations)?;
        for block in snapshot.blocks {
            indexer.apply_block(block)?;
        }
        Ok(indexer)
    }

    pub fn apply_cross_checked(
        &mut self,
        primary: IndexedBlock,
        secondary: &IndexedBlock,
    ) -> Result<(), IndexError> {
        if &primary != secondary {
            return Err(IndexError::RpcMismatch(primary.number));
        }
        self.apply_block(primary)
    }

    fn apply_deposits(&mut self, deposits: &[DepositLog]) -> Result<(), IndexError> {
        for log in deposits {
            let (index, root) = self
                .tree
                .insert(log.commitment)
                .map_err(|_| IndexError::InvalidDeposit)?;
            if index != log.leaf_index || root != log.root {
                return Err(IndexError::EventMismatch { index });
            }
        }
        Ok(())
    }

    fn rebuild(&mut self) -> Result<(), IndexError> {
        self.tree = MerkleTree::try_new(self.scope).map_err(|_| IndexError::NonCanonicalDigest)?;
        let deposits: Vec<_> = self
            .blocks
            .iter()
            .flat_map(|block| block.deposits.clone())
            .collect();
        self.apply_deposits(&deposits)
    }
}

#[derive(Clone, Debug, Error, PartialEq, Eq)]
pub enum IndexError {
    #[error("application digest contains a noncanonical BabyBear limb")]
    NonCanonicalDigest,
    #[error("block parent is not in the retained chain")]
    UnknownParent,
    #[error("expected block {expected}, got {actual}")]
    NonSequentialBlock { expected: u64, actual: u64 },
    #[error("deposit event at leaf {index} does not match replay")]
    EventMismatch { index: u32 },
    #[error("deposit is invalid")]
    InvalidDeposit,
    #[error("no blocks have been indexed")]
    NoBlocks,
    #[error("commitment is not indexed")]
    UnknownCommitment,
    #[error("deposit has not reached the configured confirmation depth")]
    Unconfirmed,
    #[error("unsupported index snapshot version {0}")]
    UnsupportedSnapshot(u16),
    #[error("RPC endpoints disagree at block {0}")]
    RpcMismatch(u64),
}

#[cfg(test)]
mod tests {
    use super::*;

    fn digest(n: u8) -> Digest512 {
        Digest512 {
            left: [n; 32],
            right: [n + 1; 32],
        }
    }

    #[test]
    fn rolls_back_to_known_parent_and_replays() {
        let scope = digest(1);
        let mut source = MerkleTree::new(scope);
        let leaf_a = digest(3);
        let (index_a, root_a) = source.insert(leaf_a).unwrap();
        let block_a = IndexedBlock {
            number: 10,
            hash: [10; 32],
            parent_hash: [9; 32],
            deposits: vec![DepositLog {
                commitment: leaf_a,
                leaf_index: index_a,
                root: root_a,
            }],
        };
        let mut indexer = Indexer::new(scope, 0).unwrap();
        indexer.apply_block(block_a).unwrap();
        let leaf_b = digest(4);
        let (index_b, root_b) = source.insert(leaf_b).unwrap();
        indexer
            .apply_block(IndexedBlock {
                number: 11,
                hash: [11; 32],
                parent_hash: [10; 32],
                deposits: vec![DepositLog {
                    commitment: leaf_b,
                    leaf_index: index_b,
                    root: root_b,
                }],
            })
            .unwrap();

        let mut fork = MerkleTree::new(scope);
        fork.insert(leaf_a).unwrap();
        let leaf_c = digest(5);
        let (index_c, root_c) = fork.insert(leaf_c).unwrap();
        indexer
            .apply_block(IndexedBlock {
                number: 11,
                hash: [12; 32],
                parent_hash: [10; 32],
                deposits: vec![DepositLog {
                    commitment: leaf_c,
                    leaf_index: index_c,
                    root: root_c,
                }],
            })
            .unwrap();
        assert!(indexer.confirmed_path(leaf_b).is_err());
        assert_eq!(indexer.confirmed_path(leaf_c).unwrap().0, root_c);
    }

    #[test]
    fn snapshot_replays_and_rpc_cross_check_rejects_disagreement() {
        let scope = digest(7);
        let mut source = MerkleTree::new(scope);
        let leaf = digest(9);
        let (leaf_index, root) = source.insert(leaf).unwrap();
        let block = IndexedBlock {
            number: 1,
            hash: [1; 32],
            parent_hash: [0; 32],
            deposits: vec![DepositLog {
                commitment: leaf,
                leaf_index,
                root,
            }],
        };
        let mut indexer = Indexer::new(scope, 0).unwrap();
        indexer.apply_cross_checked(block.clone(), &block).unwrap();
        let snapshot = indexer.snapshot();
        assert_eq!(snapshot.version, 3);
        let restored = Indexer::from_snapshot(snapshot).unwrap();
        assert_eq!(restored.confirmed_path(leaf).unwrap().0, root);
        let mut conflicting = block.clone();
        conflicting.hash = [2; 32];
        assert_eq!(
            indexer.apply_cross_checked(block, &conflicting),
            Err(IndexError::RpcMismatch(1))
        );
    }

    #[test]
    fn rejects_v2_snapshot_and_noncanonical_digests() {
        let scope = digest(1);
        let snapshot = IndexerSnapshot {
            version: 2,
            scope,
            confirmations: 0,
            blocks: Vec::new(),
        };
        assert!(matches!(
            Indexer::from_snapshot(snapshot),
            Err(IndexError::UnsupportedSnapshot(2))
        ));

        let mut bytes = [0u8; 64];
        bytes[..4].copy_from_slice(&pqtc_spec::BABY_BEAR_MODULUS.to_be_bytes());
        let invalid = Digest512::from_bytes(bytes);
        assert!(matches!(
            Indexer::new(invalid, 0),
            Err(IndexError::NonCanonicalDigest)
        ));

        let mut indexer = Indexer::new(scope, 0).unwrap();
        let block = IndexedBlock {
            number: 1,
            hash: [1; 32],
            parent_hash: [0; 32],
            deposits: vec![DepositLog {
                commitment: invalid,
                leaf_index: 0,
                root: Digest512::ZERO,
            }],
        };
        assert_eq!(indexer.apply_block(block), Err(IndexError::InvalidDeposit));
    }
}
