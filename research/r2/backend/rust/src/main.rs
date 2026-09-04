//! Exact H0 relation through upstream multilinear AIR zerocheck + plain WHIR.
//! NON-HIDING CONTROL: never eligible as a private withdrawal candidate.
use std::{fs, time::Instant};
use p3_challenger::DuplexChallenger;
use p3_field::PrimeCharacteristicRing;
use p3_multi_stark::{config::MultiStarkConfig, MultiStarkProof, ProverInstance, ProverInstances, VerifierInstance, VerifierInstances, prove, setup, verify};
use p3_sumcheck::{OpeningBatch, layout::{Layout, PrefixProver, Table, Witness}};
use p3_whir::{DomainSeparator, FoldingFactor, ProtocolParameters, SecurityAssumption, WhirConfig, WhirProver, WhirProverData};
use pqtc_poseidon_air::WithdrawalAir;
use pqtc_r2_backend::*;
use serde_json::json;

type L = PrefixProver<F, EF>;
type Pcs = WhirProver<EF, F, Dft, Mmcs, Challenger, L>;
const FOLDING: usize = 2;
struct Config { pcs: Pcs, security: usize }
impl MultiStarkConfig for Config {
    type Val = F;
    type Challenge = EF;
    type Challenger = Challenger;
    type Pcs = Pcs;
    fn pcs(&self) -> &Pcs { &self.pcs }
    fn min_num_variables(&self) -> usize { FOLDING }
    fn build_witness(&self, tables: Vec<Table<F>>) -> Witness<F> { L::new_witness(tables, FOLDING) }
    fn committed_table<'a>(&self, data: &'a WhirProverData<F, EF, Mmcs, L>, index: usize) -> &'a Table<F> { data.table(index) }
}
fn challenger(config: &Config) -> Challenger {
    let mut ch = DuplexChallenger::new(permutation());
    let mut ds = DomainSeparator::new(vec![]);
    config.pcs.add_domain_separator::<8>(&mut ds);
    ds.observe_domain_separator(&mut ch);
    bind_mode(&mut ch, 4, config.security);
    ch
}
fn main() {
    let input = input();
    let fold = FoldingFactor::Constant(FOLDING);
    // Exactly the rate recurrence in pinned multi-stark/tests/whir_fibonacci.rs.
    // Geometry is the REAL 190 x 256 trace, padded to a 2^16 stacked MLE.
    let schedule = fold.compute_folding_schedule(16).unwrap();
    let mut rate = 1;
    let rates = schedule.iter().take(schedule.len() - 1).map(|f| { rate += f - 1; rate }).collect();
    let params = ProtocolParameters { security_level: input.security, pow_bits: 0,
        round_log_inv_rates: rates, folding_factor: fold,
        soundness_type: SecurityAssumption::CapacityBound, starting_log_inv_rate: 1 };
    let derived = match WhirConfig::new(16, params) {
        Ok(c) => c,
        Err(e) => {
            json_file(&input.output.join("result.json"), &json!({"status": "PARAMETER_DERIVATION_FAILURE", "error": format!("{e:?}"), "requested_security_bits": input.security, "security_status": "SECURITY_NOT_QUALIFIED", "privacy_evidence": "NON_HIDING_CONTROL"}));
            std::process::exit(2);
        }
    };
    fs::write(input.output.join("derived-parameters.txt"), format!("{derived:#?}")).unwrap();
    let config = Config { pcs: Pcs::new(derived, Dft::default(), mmcs()), security: input.security };
    let air = WithdrawalAir::default();
    let (pk, vk) = setup(&config, &[&air], &mut challenger(&config));
    let started = Instant::now();
    let proof = prove(&config, ProverInstances::new(vec![ProverInstance::new(
        &air, Table::new(input.trace.transpose()), &pk, &input.public
    )]), 0, &mut challenger(&config));
    let prover_ns = started.elapsed().as_nanos();
    let proof_bytes = postcard::to_allocvec(&proof).unwrap();
    fs::write(input.output.join("proof.postcard"), &proof_bytes).unwrap();
    let commitment_bytes = postcard::to_allocvec(&proof.commitment).unwrap().len();
    let sumcheck_bytes = postcard::to_allocvec(&proof.sumcheck).unwrap().len();
    let opening_bytes = postcard::to_allocvec(&proof.opening).unwrap().len();
    let preprocessed_bytes = postcard::to_allocvec(&proof.preprocessed_opening).unwrap().len();
    assert_eq!(proof_bytes.len(), commitment_bytes + sumcheck_bytes + opening_bytes + preprocessed_bytes);
    let verify_proof = |proof: &MultiStarkProof<Config>, public: &[F]| {
        verify(&config, VerifierInstances::new(vec![VerifierInstance::new(&air, &vk, 8, public)]), proof, 0, &mut challenger(&config))
    };
    // Read the serialized artifact, not the in-memory prover object.
    let mut decoded: MultiStarkProof<Config> = postcard::from_bytes(&proof_bytes).unwrap();
    let started = Instant::now();
    verify_proof(&decoded, &input.public).expect("exact H0 native WHIR verification");
    let verifier_ns = started.elapsed().as_nanos();
    let mut mutations = Vec::new();
    for (name, offset) in [("scope", 0), ("root", 16), ("nullifier", 32), ("payout_binding", 48)] {
        let mut public = input.public;
        public[offset] += F::ONE;
        let rejected = verify_proof(&decoded, &public).is_err();
        assert!(rejected, "mutated public statement accepted: {name}");
        mutations.push(json!({"mutation": name, "rejected": rejected}));
    }
    let batch = &decoded.opening.evals[0];
    let mut current = batch.current().to_vec();
    current[0] += EF::ONE;
    decoded.opening.evals[0] = OpeningBatch::new(current, batch.next().to_vec());
    let tampered_rejected = verify_proof(&decoded, &input.public).is_err();
    assert!(tampered_rejected);
    fs::write(input.output.join("tampered-proof.postcard"), postcard::to_allocvec(&decoded).unwrap()).unwrap();
    let truncated_rejected = postcard::from_bytes::<MultiStarkProof<Config>>(&proof_bytes[..proof_bytes.len()/2]).is_err();
    assert!(truncated_rejected);
    json_file(&input.output.join("result.json"), &json!({
        "pipeline_id": "R2-C4", "configuration": "H0-MULTILINEAR-PLAIN-WHIR-CONTROL",
        "specification_status": "EXACT_FROZEN_H0", "correctness_evidence": "SERIALIZED_NATIVE_PROOF_VERIFIED",
        "privacy_evidence": "NON_HIDING_CONTROL_NOT_PRIVATE_WITHDRAWAL", "security_status": "SECURITY_NOT_QUALIFIED",
        "performance_evidence": "MEASURED_SINGLE_EXECUTION_NOT_DISTRIBUTION", "implementation_stage": "SAME_RELATION_NATIVE_NON_HIDING_CONTROL",
        "promotion_status": "NOT_READY_FOR_BUILD_SELECTION", "source_pin": PIN,
        "requested_security_bits": input.security, "soundness_assumption": "CONDITIONAL_CAPACITY_BOUND",
        "security_report_scope": "UPSTREAM_PARAMETER_DERIVATION_NOT_END_TO_END_SECURITY_CERTIFICATION",
        "trace_rows": 256, "trace_columns": 190, "stacked_num_variables": 16,
        "proof_bytes": proof_bytes.len(), "prover_time_ns": prover_ns, "verifier_time_ns": verifier_ns,
        "public_mutations": mutations, "tampered_opening_rejected": tampered_rejected, "truncated_proof_rejected": truncated_rejected,
        "proof_ledger": {"full_native_postcard": proof_bytes.len(), "commitment": commitment_bytes, "zerocheck": sumcheck_bytes, "main_opening": opening_bytes, "preprocessed_option": preprocessed_bytes, "evm_abi_bytes": null},
        "evm_status": "NOT_EVALUATED_NATIVE_HIDING_GATE_NOT_PASSED"
    }));
}
