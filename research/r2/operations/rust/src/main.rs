use anyhow::{Context, Result, ensure};
use clap::Parser;
use pqtc_hash::{commitment, empty_leaf, merkle_node, nullifier_hash, payout_digest, scope};
use pqtc_poseidon_air::{WithdrawalWitness, check_witness};
use pqtc_spec::{CanonicalSecret, Digest512, ScopeInput, WithdrawalStatement};
use serde_json::{Value, json};
use std::{fs, path::PathBuf};

#[derive(Parser)]
struct Args {
    #[arg(long)] pool: String,
    #[arg(long)] parameter: String,
    #[arg(long)] recipient: String,
    #[arg(long)] relayer: String,
    #[arg(long, default_value_t = 31337)] chain_id: u64,
    #[arg(long, default_value_t = 1_000_000_000_000_000_000u128)] denomination: u128,
    #[arg(long, default_value_t = 1_000_000_000_000_000u128)] fee: u128,
    #[arg(long, default_value_t = 8)] notes: usize,
    #[arg(long, default_value_t = 1)] retain_every: usize,
    #[arg(long)] output: PathBuf,
}
fn bytes<const N: usize>(text: &str) -> Result<[u8; N]> {
    hex::decode(text.strip_prefix("0x").unwrap_or(text))?.try_into()
        .map_err(|_| anyhow::anyhow!("expected {N} bytes"))
}
fn word(value: u128) -> [u8; 32] {
    let mut out = [0; 32];
    out[16..].copy_from_slice(&value.to_be_bytes());
    out
}
fn digest_hex(value: Digest512) -> Value {
    json!({"left": format!("0x{}", hex::encode(value.left)), "right": format!("0x{}", hex::encode(value.right))})
}
fn main() -> Result<()> {
    let args = Args::parse();
    ensure!(!args.output.exists(), "refusing to overwrite retained input directory");
    ensure!((1..=4096).contains(&args.notes) && args.retain_every > 0, "local diagnostic supports 1..4096 deposits and a positive retention stride");
    ensure!(args.denomination > 0 && args.fee <= args.denomination, "invalid local denomination/fee");
    let pool = bytes::<20>(&args.pool)?;
    let recipient = bytes::<20>(&args.recipient)?;
    let relayer = bytes::<20>(&args.relayer)?;
    ensure!(recipient != [0; 20] && (args.fee == 0 || relayer != [0; 20]), "invalid payout address");
    let parameter = Digest512::from_bytes(bytes::<64>(&args.parameter)?);
    let input = ScopeInput { chain_id: args.chain_id, pool, denomination: word(args.denomination), tree_depth: 20, protocol_version: 3, parameter_id: parameter };
    let scope_value = scope(input);
    let mut zeros = [Digest512::ZERO; 21];
    zeros[0] = empty_leaf(scope_value);
    for level in 0..20 { zeros[level + 1] = merkle_node(level as u8, zeros[level], zeros[level]); }
    fs::create_dir_all(&args.output)?;
    let mut filled = [Digest512::ZERO; 20];
    filled.copy_from_slice(&zeros[..20]);
    let mut deposits = Vec::new();
    let mut cases = Vec::new();
    for index in 0..args.notes {
        // Public deterministic test notes, never suitable for funded deployments.
        let secret = CanonicalSecret::from_limbs(std::array::from_fn(|j| 1000 + index as u32 * 16 + j as u32))?;
        let trapdoor = CanonicalSecret::from_limbs(std::array::from_fn(|j| 1008 + index as u32 * 16 + j as u32))?;
        let leaf = commitment(scope_value, secret, trapdoor);
        let mut current = leaf;
        let mut position = index;
        let mut siblings = [Digest512::ZERO; 20];
        for level in 0..20 {
            siblings[level] = if position & 1 == 0 { zeros[level] } else { filled[level] };
            current = if position & 1 == 0 {
                filled[level] = current;
                merkle_node(level as u8, current, siblings[level])
            } else {
                merkle_node(level as u8, siblings[level], current)
            };
            position >>= 1;
        }
        deposits.push(json!({"leafIndex": index, "commitment": digest_hex(leaf), "root": digest_hex(current)}));
        if index >= 16 && index % args.retain_every != 0 && !(index + 1).is_power_of_two() && index + 1 != args.notes { continue; }
        let witness = WithdrawalWitness { nullifier_secret: secret, trapdoor, leaf_index: index as u32, path_bits: std::array::from_fn(|j| ((index >> j) & 1) as u8), siblings };
        let statement = WithdrawalStatement { scope: scope_value, root: current, nullifier_hash: nullifier_hash(scope_value, secret), payout_digest: payout_digest(recipient, relayer, word(args.fee)) };
        check_witness(statement, &witness).context("real sequential deposit witness failed relation")?;
        let directory = args.output.join(format!("note-{index:03}"));
        fs::create_dir(&directory)?;
        fs::write(directory.join("statement.json"), serde_json::to_vec_pretty(&statement)?)?;
        fs::write(directory.join("witness.json"), serde_json::to_vec_pretty(&witness)?)?;
        let evm = json!({"synthetic": true, "funded": false, "leafIndex": index, "scope": digest_hex(scope_value), "parameterId": digest_hex(parameter), "commitment": digest_hex(leaf), "root": digest_hex(statement.root), "nullifierHash": digest_hex(statement.nullifier_hash), "payoutDigest": digest_hex(statement.payout_digest), "recipient": args.recipient, "relayer": args.relayer, "feeWei": args.fee.to_string()});
        fs::write(directory.join("evm.json"), serde_json::to_vec_pretty(&evm)?)?;
        cases.push(evm);
    }
    let manifest = json!({"schema": "pqtc.r2.actual-deposit-inputs.v1", "synthetic": true, "funded": false, "scopeInput": input, "pool": args.pool, "chainId": args.chain_id, "denominationWei": args.denomination.to_string(), "scope": digest_hex(scope_value), "parameterId": digest_hex(parameter), "zeros": zeros.into_iter().map(digest_hex).collect::<Vec<_>>(), "cases": cases, "deposits": deposits, "retention_stride": args.retain_every, "interpretation": "Native-generated complete sequential append-only deposit history, not a mined-chain claim; retained witnesses target their insertion roots. No arbitrary sibling seeds."});
    fs::write(args.output.join("manifest.json"), serde_json::to_vec_pretty(&manifest)?)?;
    println!("{}", json!({"status": "REFERENCE_RELATION_CHECKED", "notes": args.notes, "output": args.output}));
    Ok(())
}
