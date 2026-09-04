use anyhow::{Result, ensure};
use clap::Parser;
use pqtc_spec::{Digest512, WithdrawalStatement};
use pqtc_stark::{SecurityProfile, StarkProof, codec::decode_proof_parts, verify_withdrawal, withdrawal_config_from_os_entropy};
use serde_json::json;
use std::{fs, io::Read, panic::{AssertUnwindSafe, catch_unwind}, path::{Path, PathBuf}, time::Instant};

#[derive(Parser)]
struct Args {
    #[arg(long)] statement: PathBuf,
    #[arg(long)] parameter: String,
    #[arg(long)] part_a: PathBuf,
    #[arg(long)] part_b: PathBuf,
    #[arg(long, default_value = "none")] mutation: String,
    #[arg(long)] uncontained: bool,
}
fn bounded_read(path: &Path, limit: u64) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    fs::File::open(path)?.take(limit + 1).read_to_end(&mut bytes)?;
    ensure!(bytes.len() as u64 <= limit, "input byte ceiling exceeded");
    Ok(bytes)
}
fn mutate(proof: &mut StarkProof, mutation: &str) -> Result<()> {
    match mutation {
        "none" => (),
        "trace-local-empty" => proof.opened_values.trace_local.clear(),
        "trace-next-absent" => proof.opened_values.trace_next = None,
        "quotient-empty" => proof.opened_values.quotient_chunks.clear(),
        "random-absent" => proof.opened_values.random = None,
        "hiding-empty" => proof.opening_proof.0.clear(),
        "fri-input-empty" => proof.opening_proof.1.input_openings.clear(),
        "fri-openings-empty" => proof.opening_proof.1.commit_phase_openings.clear(),
        "fri-final-empty" => proof.opening_proof.1.final_poly.clear(),
        "fri-commits-empty" => proof.opening_proof.1.commit_phase_commits.clear(),
        "fri-witnesses-empty" => proof.opening_proof.1.commit_pow_witnesses.clear(),
        _ => anyhow::bail!("unknown in-memory mutation"),
    }
    Ok(())
}
fn main() -> Result<()> {
    let args = Args::parse();
    let parameter = Digest512::from_bytes(hex::decode(args.parameter.trim_start_matches("0x"))?.try_into().map_err(|_| anyhow::anyhow!("parameter requires 64 bytes"))?);
    let statement: WithdrawalStatement = serde_json::from_slice(&bounded_read(&args.statement, 16384)?)?;
    let part_a = bounded_read(&args.part_a, 524288)?;
    let part_b = bounded_read(&args.part_b, 524288)?;
    let config = withdrawal_config_from_os_entropy(SecurityProfile::SepoliaV03, parameter, statement);
    let operation = || -> Result<bool> {
        let mut proof = decode_proof_parts(&part_a, &part_b, SecurityProfile::SepoliaV03, parameter, statement)?;
        mutate(&mut proof, &args.mutation)?;
        Ok(verify_withdrawal(&config, statement, &proof))
    };
    let started = Instant::now();
    let result = if args.uncontained { Ok(operation()) } else { catch_unwind(AssertUnwindSafe(operation)) };
    let (status, error) = match result {
        Ok(Ok(true)) => ("ACCEPTED", None),
        Ok(Ok(false)) => ("REJECTED", None),
        Ok(Err(error)) => ("DECODE_OR_INPUT_REJECTED", Some(error.to_string())),
        Err(_) => ("PANIC_CONTAINED_AND_REJECTED", None),
    };
    // Exercise a fresh valid request after the hostile in-memory request in this process.
    let recovery = if args.mutation != "none" && !args.uncontained {
        let valid = decode_proof_parts(&part_a, &part_b, SecurityProfile::SepoliaV03, parameter, statement)?;
        Some(catch_unwind(AssertUnwindSafe(|| verify_withdrawal(&config, statement, &valid))).unwrap_or(false))
    } else { None };
    println!("{}", json!({"schema": "pqtc.r2.native-worker.v1", "status": status, "error": error, "contained": !args.uncontained, "mutation": args.mutation, "mutation_boundary": if args.mutation == "none" { "serialized-untrusted-input" } else { "constructed-in-memory-after-valid-decode-not-a-codec-reachability-claim" }, "valid_request_after_mutation": recovery, "elapsed_ms": started.elapsed().as_secs_f64()*1000.0, "input_bytes": part_a.len()+part_b.len(), "panic_policy": "Unwind only; allocator abort and process termination require supervisor isolation", "scope": "Native availability diagnostic, never a Solidity soundness bypass"}));
    ensure!(recovery != Some(false), "worker did not recover for valid proof");
    if status == "ACCEPTED" && args.mutation != "none" { anyhow::bail!("malformed in-memory proof accepted"); }
    Ok(())
}
