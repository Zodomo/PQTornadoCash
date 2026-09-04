use p3_security::{fri::{self, FriRegime}, grinding::GrindingSites, proximity,
    shape::{InstanceShape, StarkAirParams}, stark};
use p3_uni_stark::{ConjecturedSecurity, ProvenSecurity, StarkSecurityParams};
use serde_json::{Value, json};
use std::{env, error::Error, fs};

fn number(v: &Value, key: &str) -> Result<usize, Box<dyn Error>> {
    Ok(usize::try_from(v[key].as_u64().ok_or_else(|| format!("missing integer {key}"))?)?)
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = env::args().collect();
    if args.len() != 3 { return Err("usage: pqtc-r2-security-pinned INPUT_PROFILES.json OUTPUT.json".into()); }
    let inputs: Vec<Value> = serde_json::from_slice(&fs::read(&args[1])?)?;
    let mut rows = Vec::new();
    for v in inputs {
        for adversary in ["classical", "quantum_grinding_only"] {
            let divisor = if adversary == "classical" { 1 } else { 2 };
            let regime = FriRegime {
                log_blowup: number(&v, "fri_log_blowup")?,
                num_queries: number(&v, "fri_num_queries")?,
                log_final_poly_len: number(&v, "fri_log_final_poly_len")?,
                max_log_arity: number(&v, "fri_max_log_arity")?,
                commit_pow_bits: number(&v, "commit_grinding_bits")? / divisor,
                query_pow_bits: number(&v, "query_grinding_bits")? / divisor,
            };
            let air = StarkAirParams {
                num_constraints: number(&v, "num_constraints")?,
                max_constraint_degree: number(&v, "max_constraint_degree")?,
                max_combo: number(&v, "max_combo")?,
            };
            let cap = if divisor == 1 { "mmcs_binding_bits_classical" } else { "mmcs_binding_bits_quantum" };
            let shape = InstanceShape {
                log_trace_length: number(&v, "proof_degree_bits")?,
                modulus_bits: number(&v, "challenge_field_bits")?,
                collision_resistance: number(&v, cap)?,
                num_batched_functions: number(&v, "num_batched_functions")?,
            };
            let report = stark::proven_security_report(&regime, &air, &shape, &[], &GrindingSites::NONE);
            let mut params = StarkSecurityParams::new(regime, shape.modulus_bits,
                shape.collision_resistance, air.num_constraints, air.max_constraint_degree, air.max_combo);
            params.num_batched_functions = shape.num_batched_functions;
            let integer = ProvenSecurity::compute_from_proof(shape.log_trace_length, &params);
            let random = ConjecturedSecurity::compute_from_params(&params, shape.log_trace_length);
            let upper = proximity::compute_upper_m(1 << shape.log_trace_length).min(proximity::LDR_M_CAP);
            let per_m: Vec<_> = (3..=upper).map(|m| json!({"m":m,
                "ldt_bits":fri::proven_error_ldr_m(&regime,&air,&shape,m).bits(),
                "commit_bits":fri::commit_phase_error_ldr_m(&regime,&shape,m).map(|b| b.bits()),
                "query_bits":fri::query_phase_error(proximity::alpha_ldr_m(regime.log_blowup,m),regime.num_queries,regime.query_pow_bits).bits()
            })).collect();
            rows.push(json!({"profile_id":v["profile_id"], "adversary":adversary,
                "formula_version":"plonky3-3152b14-unmodified", "inputs":v,
                "selected_m":fri::best_ldr_m(&regime,&air,&shape).map(|x|x.0),
                "report":report, "udr_bits":report.udr.security_bits(),
                "ldr_bits":report.ldr.as_ref().map(|r|r.security_bits()),
                "floor_udr":integer.unique_decoding_bits,"floor_ldr":integer.list_decoding_bits,
                "random_words_floor":random.security_bits,"per_m":per_m,
                "status":"SECURITY_NOT_QUALIFIED", "quantum_scope":"Only grinding credit is divided by two; no QROM theorem"}));
        }
    }
    fs::write(&args[2], serde_json::to_vec_pretty(&rows)?)?;
    println!("wrote {} pinned rows to {}", rows.len(), args[2]);
    Ok(())
}
