//! Bounded API repair: the REAL H0 trace is packed into the hiding PCS's Poly.
//! Deliberately opens the eight WORK columns at row zero to make the composition
//! barrier executable: these are the complete nullifier secret, not dummy data.
//! This is a PCS proof of exact-trace openings, NOT a withdrawal relation proof.
use std::{fs, time::Instant};
use p3_challenger::CanObserve;
use p3_commit::MultilinearPcs;
use p3_field::PrimeCharacteristicRing;
use p3_multilinear_util::{point::Point, poly::Poly};
use p3_whir::{DomainSeparator, FoldingFactor, ProtocolParameters, SecurityAssumption};
use p3_whir::pcs::zk::{ZkParameters, ZkWhirConfig};
use pqtc_r2_backend::*;
use rand::rngs::StdRng;
use serde_json::json;

type Proof = <HidingPcs as MultilinearPcs<EF, Challenger>>::Proof;
fn main() {
    let input = input();
    // Existing C20 profile, only replacing synthetic width12 by actual trace arity16.
    // A 128-bit request changes the upstream derivation target, not a claim of security.
    let config = match ZkWhirConfig::new(16, ProtocolParameters {
        security_level: input.security, pow_bits: 0, round_log_inv_rates: vec![],
        folding_factor: FoldingFactor::Constant(4), soundness_type: SecurityAssumption::CapacityBound,
        starting_log_inv_rate: 2,
    }, ZkParameters { ell_zk: 4, mask_log_inv_rate: 1 }) {
        Ok(c) => c,
        Err(e) => {
            json_file(&input.output.join("result.json"), &json!({"status": "PARAMETER_DERIVATION_FAILURE", "error": format!("{e:?}"), "requested_security_bits": input.security, "security_status": "SECURITY_NOT_QUALIFIED", "privacy_evidence": "COMPOSITION_NOT_ESTABLISHED"}));
            std::process::exit(2);
        }
    };
    json_file(&input.output.join("security-terms.json"), &json!({
        "scope": "UPSTREAM_HIDING_BASE_CASE_IDEAL_IOP_RBR_DIAGNOSTIC_ONLY",
        "end_to_end_security": "NOT_ESTABLISHED", "requested_security_bits": input.security,
        "report": config.hiding_base_case_security_report()
    }));
    fs::write(input.output.join("derived-parameters.txt"), format!("{config:#?}")).unwrap();
    let pcs = HidingPcs::new(config, Dft::default(), mmcs(), rand::make_rng::<StdRng>());
    let mut values = input.trace.transpose().values;
    values.resize(1 << 16, F::ZERO);
    let polynomial = Poly::new(values);
    // Frozen air.rs defines WORK = NUM_WITHDRAWAL_COLS - 16; row0 WORK[0..8]
    // is copied verbatim from nullifier_secret before the first hash permutation.
    let points: Vec<_> = (0..8).map(|i| Point::<EF>::hypercube((190 - 16 + i) * 256, 16)).collect();
    let expected: Vec<_> = input.witness.nullifier_secret.limbs().iter().map(|&x| EF::from_u32(x)).collect();
    assert_eq!(points.iter().map(|p| polynomial.eval_base(p)).collect::<Vec<_>>(), expected);
    let challenger = || {
        let mut ch = Challenger::new(permutation());
        let mut ds = DomainSeparator::new(vec![]);
        pcs.add_domain_separator::<8>(&mut ds);
        ds.observe_domain_separator(&mut ch);
        bind_mode(&mut ch, 4001, input.security);
        for &v in &input.public { ch.observe(v); }
        ch
    };
    let mut runs = Vec::new();
    let mut saved = Vec::new();
    for repeat in 0..2 {
        let mut ch = challenger();
        let started = Instant::now();
        let (commitment, data) = pcs.commit(polynomial.clone(), &mut ch);
        let proof = pcs.open(data, points.clone(), &mut ch);
        let prover_ns = started.elapsed().as_nanos();
        let bytes = postcard::to_allocvec(&proof).unwrap();
        let decoded: Proof = postcard::from_bytes(&bytes).unwrap();
        let started = Instant::now();
        pcs.verify(&commitment, &decoded, &mut challenger(), points.clone()).unwrap();
        let verifier_ns = started.elapsed().as_nanos();
        assert_eq!(decoded.evals, expected, "the complete synthetic secret is publicly revealed");
        fs::write(input.output.join(format!("opening-{repeat}.postcard")), &bytes).unwrap();
        fs::write(input.output.join(format!("commitment-{repeat}.postcard")), postcard::to_allocvec(&commitment).unwrap()).unwrap();
        let mut tampered: Proof = postcard::from_bytes(&bytes).unwrap();
        tampered.evals[0] += EF::ONE;
        let rejected = pcs.verify(&commitment, &tampered, &mut challenger(), points.clone()).is_err();
        assert!(rejected);
        let truncated = postcard::from_bytes::<Proof>(&bytes[..bytes.len()/2]).is_err();
        assert!(truncated);
        runs.push(json!({"repeat": repeat, "verified": true, "proof_bytes": bytes.len(), "prover_time_ns": prover_ns, "verifier_time_ns": verifier_ns, "altered_claim_rejected": rejected, "truncated_proof_rejected": truncated}));
        saved.push(bytes);
    }
    assert_ne!(saved[0], saved[1], "fresh OS randomness must change hiding proof bytes");
    json_file(&input.output.join("result.json"), &json!({
        "pipeline_id": "R2-C4", "configuration": "H0-HIDING-WHIR-EXACT-TRACE-OPENING-REPAIR",
        "specification_status": "EXACT_FROZEN_H0_TRACE_PCS_ONLY", "correctness_evidence": "EXACT_REFERENCE_AND_AIR_CHECKED_LOCALLY_PCS_OPENINGS_VERIFIED",
        "privacy_evidence": "CONSTRUCTED_LEAKAGE_OF_EIGHT_NULLIFIER_SECRET_LIMBS",
        "security_status": "SECURITY_NOT_QUALIFIED", "performance_evidence": "MEASURED_COMPONENT_NOT_COMPLETE_RELATION",
        "implementation_stage": "BOUNDED_POLY_ADAPTER_EXECUTED_NO_HIDING_OUTER_PIOP",
        "promotion_status": "NOT_READY_FOR_BUILD_SELECTION", "source_pin": PIN,
        "complete_relation_proof": false, "fresh_mask_proofs_differ": true,
        "opened_private_value": "row0 WORK[0..8] = nullifier_secret.limbs()",
        "claim": "PCS correctly reveals requested evaluations; this is NOT an attack on its stated hiding guarantee",
        "remaining_barrier": "PrescribedPointPcs/table and successor layout adapter plus a hiding outer zerocheck with masked opening claims; merely wrapping the PCS cannot hide exposed AIR evaluations",
        "runs": runs, "requested_security_bits": input.security
    }));
}
