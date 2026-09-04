use std::fmt::Debug;
use std::fs;
use std::hint::black_box;
use std::path::PathBuf;
use std::time::Instant;

use p3_baby_bear::{BabyBear, default_babybear_poseidon2_16};
use p3_bn254::Bn254;
use p3_dft::{Radix2Dit, TwoAdicSubgroupDft};
use p3_field::extension::{BinomialExtensionField, Complex, QuinticTrinomialExtensionField};
use p3_field::{Algebra, BasedVectorSpace, Field, PrimeCharacteristicRing, TwoAdicField, batch_multiplicative_inverse};
use p3_goldilocks::{Goldilocks, default_goldilocks_poseidon2_16};
use p3_koala_bear::{KoalaBear, default_koalabear_poseidon2_16};
use p3_mersenne_31::{Mersenne31, Mersenne31ComplexRadix2Dit, QM31, default_mersenne31_poseidon2_16};
use p3_symmetric::Permutation;
use serde::Serialize;

const PINNED_PLONKY3: &str = "3152b14a89067c83775a8076cc262ffc48a1fd7c";
const SEED: u64 = 0x5350_3430_4649_454c;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Measurement {
    operation: String,
    workload: usize,
    iterations: usize,
    total_ns: u128,
    ns_per_iteration: f64,
    result_witness: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Capability {
    primitive: String,
    status: String,
    detail: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct CandidateReport {
    candidate_id: String,
    base_field: String,
    challenge_field: String,
    base_bytes: usize,
    extension_bytes: usize,
    deterministic_seed: String,
    measurements: Vec<Measurement>,
    capabilities: Vec<Capability>,
    deterministic_distribution: Distribution,
    relation_projection: Projection,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Distribution {
    sample_count: usize,
    zero_count: usize,
    nonzero_count: usize,
    generation: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Projection {
    rows: usize,
    columns: usize,
    raw_base_bytes: usize,
    abi_base_bytes: usize,
    raw_calldata_gas_floor_all_zero: usize,
    raw_calldata_gas_ceiling_all_nonzero: usize,
    scope: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct RunReport {
    schema_version: &'static str,
    benchmark_only: bool,
    complete_proof_claimed: bool,
    pinned_plonky3_commit: &'static str,
    iterations: usize,
    measurement_classification: &'static str,
    common_protocol_comparable: bool,
    warmup_iterations: usize,
    input_distribution: &'static str,
    timing_caveat: &'static str,
    process_peak_rss_bytes: u64,
    candidates: Vec<CandidateReport>,
}

struct Args {
    out: PathBuf,
    iterations: usize,
    rows: usize,
    columns: usize,
}

fn parse_args() -> Args {
    let mut out = PathBuf::from("research/candidates/field-bakeoff-common/outputs/native-latest.json");
    let mut iterations = 64usize;
    let mut rows = 256usize;
    let mut columns = 190usize;
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        let mut value = || args.next().unwrap_or_else(|| panic!("missing value for {arg}"));
        match arg.as_str() {
            "--out" => out = PathBuf::from(value()),
            "--iterations" => iterations = value().parse().expect("invalid --iterations"),
            "--rows" => rows = value().parse().expect("invalid --rows"),
            "--columns" => columns = value().parse().expect("invalid --columns"),
            _ => panic!("unknown argument: {arg}"),
        }
    }
    assert!(iterations > 0, "iterations must be nonzero");
    assert!(rows > 0 && columns > 0, "geometry must be nonzero");
    Args { out, iterations, rows, columns }
}

fn measure<T: Debug>(operation: impl Into<String>, workload: usize, iterations: usize, mut kernel: impl FnMut() -> T) -> Measurement {
    let start = Instant::now();
    let mut result = black_box(kernel());
    for _ in 1..iterations {
        result = black_box(kernel());
    }
    let total_ns = start.elapsed().as_nanos();
    let witness = format!("{result:?}");
    Measurement {
        operation: operation.into(),
        workload,
        iterations,
        total_ns,
        ns_per_iteration: total_ns as f64 / iterations as f64,
        result_witness: witness,
    }
}

fn scalar<F: PrimeCharacteristicRing>(index: usize) -> F {
    let x = SEED.wrapping_add((index as u64 + 1).wrapping_mul(0x9e37_79b9_7f4a_7c15));
    F::from_u64((x ^ (x >> 29) ^ (x << 17)) | 1)
}

fn ext<F, EF>(offset: usize) -> EF
where
    F: Field,
    EF: Field + BasedVectorSpace<F>,
{
    EF::from_basis_coefficients_fn(|i| scalar::<F>(offset + i))
}

fn projection(rows: usize, columns: usize, base_bytes: usize) -> Projection {
    let raw = rows.checked_mul(columns).and_then(|x| x.checked_mul(base_bytes)).expect("geometry overflow");
    Projection {
        rows,
        columns,
        raw_base_bytes: raw,
        abi_base_bytes: rows.checked_mul(columns).and_then(|x| x.checked_mul(32)).expect("geometry overflow"),
        raw_calldata_gas_floor_all_zero: raw * 4,
        raw_calldata_gas_ceiling_all_nonzero: raw * 16,
        scope: "opened trace rows only; excludes authentication, FRI, transcript, memory expansion, and proof envelope".into(),
    }
}

fn arithmetic_report<F, EF>(
    candidate_id: &str,
    base_name: &str,
    challenge_name: &str,
    base_bytes: usize,
    extension_bytes: usize,
    iterations: usize,
    rows: usize,
    columns: usize,
) -> CandidateReport
where
    F: Field + Debug + Send + Sync + 'static,
    EF: Field + Algebra<F> + BasedVectorSpace<F> + Debug + Send + Sync,
{
    let a = scalar::<F>(1);
    let b = scalar::<F>(2);
    let ea = ext::<F, EF>(10);
    let eb = ext::<F, EF>(30);
    let mut measurements = vec![
        measure("base_add", 1, iterations, || black_box(a) + black_box(b)),
        measure("base_sub", 1, iterations, || black_box(a) - black_box(b)),
        measure("base_mul", 1, iterations, || black_box(a) * black_box(b)),
        measure("base_square", 1, iterations, || black_box(a).square()),
        measure("base_inverse", 1, iterations, || black_box(a).try_inverse().expect("nonzero deterministic scalar")),
        measure("base_power_65537", 1, iterations, || black_box(a).exp_u64(65_537)),
        measure("extension_add", 1, iterations, || black_box(ea) + black_box(eb)),
        measure("extension_sub", 1, iterations, || black_box(ea) - black_box(eb)),
        measure("extension_mul", 1, iterations, || black_box(ea) * black_box(eb)),
        measure("extension_square", 1, iterations, || black_box(ea).square()),
        measure("extension_inverse", 1, iterations, || black_box(ea).try_inverse().expect("nonzero deterministic extension")),
        measure("extension_power_65537", 1, iterations, || black_box(ea).exp_u64(65_537)),
        measure("extension_mul_base", 1, iterations, || black_box(ea) * black_box(a)),
    ];

    for n in [32usize, 64, 128, 256] {
        let left: Vec<EF> = (0..n).map(|i| ext::<F, EF>(100 + i * EF::DIMENSION)).collect();
        let right: Vec<F> = (0..n).map(|i| scalar::<F>(500 + i)).collect();
        measurements.push(measure(format!("dot_product_{n}"), n, iterations, || {
            left.iter().zip(&right).fold(EF::ZERO, |acc, (&x, &y)| acc + x * y)
        }));
    }

    for n in [16usize, 32, 64] {
        let base_values: Vec<F> = (0..n).map(|i| scalar::<F>(700 + i)).collect();
        let ext_values: Vec<EF> = (0..n).map(|i| ext::<F, EF>(900 + i * EF::DIMENSION)).collect();
        measurements.push(measure(format!("base_batch_inverse_{n}"), n, iterations, || batch_multiplicative_inverse(&base_values)));
        measurements.push(measure(format!("extension_batch_inverse_{n}"), n, iterations, || batch_multiplicative_inverse(&ext_values)));
    }

    let coefficients: Vec<EF> = (0..64).map(|i| ext::<F, EF>(1_200 + i * EF::DIMENSION)).collect();
    let point = ext::<F, EF>(1_800);
    measurements.push(measure("polynomial_evaluation_64", 64, iterations, || {
        coefficients.iter().rev().fold(EF::ZERO, |acc, &coefficient| acc * point + coefficient)
    }));

    let low = ext::<F, EF>(2_000);
    let high = ext::<F, EF>(2_100);
    let beta = ext::<F, EF>(2_200);
    let x = scalar::<F>(2_300);
    let inv_two = F::TWO.try_inverse().expect("two is nonzero");
    let inv_two_x = (F::TWO * x).try_inverse().expect("nonzero deterministic fold point");
    measurements.push(measure("fri_fold_binary", 2, iterations, || {
        (black_box(low) + black_box(high)) * inv_two
            + black_box(beta) * ((black_box(low) - black_box(high)) * inv_two_x)
    }));

    let parallel_left: Vec<EF> = (0..256).map(|i| ext::<F, EF>(2_400 + i * EF::DIMENSION)).collect();
    let parallel_right: Vec<F> = (0..256).map(|i| scalar::<F>(3_500 + i)).collect();
    for threads in [1usize, 2, 4] {
        measurements.push(measure(format!("parallel_dot_256_threads_{threads}"), 256 * threads, iterations, || {
            std::thread::scope(|scope| {
                let handles: Vec<_> = (0..threads)
                    .map(|_| scope.spawn(|| parallel_left.iter().zip(&parallel_right).fold(EF::ZERO, |acc, (&x, &y)| acc + x * y)))
                    .collect();
                handles.into_iter().map(|handle| handle.join().expect("parallel field worker")).collect::<Vec<_>>()
            })
        }));
    }

    let sample_count = 256usize;
    let zero_count = (0..sample_count).filter(|&i| scalar::<F>(3_000 + i).is_zero()).count();
    CandidateReport {
        candidate_id: candidate_id.into(),
        base_field: base_name.into(),
        challenge_field: challenge_name.into(),
        base_bytes,
        extension_bytes,
        deterministic_seed: format!("0x{SEED:016x}"),
        measurements,
        capabilities: Vec::new(),
        deterministic_distribution: Distribution {
            sample_count,
            zero_count,
            nonzero_count: sample_count - zero_count,
            generation: "fixed wrapping-u64 mixer mapped through PrimeCharacteristicRing::from_u64; no OS randomness".into(),
        },
        relation_projection: projection(rows, columns, base_bytes),
    }
}

fn peak_rss_bytes() -> u64 {
    let mut usage = std::mem::MaybeUninit::<libc::rusage>::zeroed();
    // SAFETY: getrusage initializes the supplied rusage object for RUSAGE_SELF.
    let result = unsafe { libc::getrusage(libc::RUSAGE_SELF, usage.as_mut_ptr()) };
    assert_eq!(result, 0, "getrusage failed");
    // SAFETY: the successful getrusage call initialized the object.
    let max_rss = unsafe { usage.assume_init() }.ru_maxrss as u64;
    #[cfg(target_os = "macos")]
    return max_rss;
    #[cfg(not(target_os = "macos"))]
    return max_rss * 1024;
}

fn add_dft<F: TwoAdicField + Debug>(report: &mut CandidateReport, iterations: usize) {
    let input: Vec<F> = (0..256).map(scalar::<F>).collect();
    let dft = Radix2Dit::<F>::default();
    report.measurements.push(measure("native_fft_256", 256, iterations, || dft.dft(input.clone())));
    report.measurements.push(measure("native_lde_256_blowup16", 4096, iterations, || dft.lde(input.clone(), 4)));
    report.capabilities.push(Capability { primitive: "FFT/LDE".into(), status: "MEASURED".into(), detail: "p3_dft::Radix2Dit over the pinned base field; workload includes the consumed input clone".into() });
}

fn add_mersenne_complex_dft(report: &mut CandidateReport, iterations: usize) {
    type C = Complex<Mersenne31>;
    let input: Vec<C> = (0..256).map(|i| C::new_complex(scalar::<Mersenne31>(i), scalar::<Mersenne31>(i + 256))).collect();
    let dft = Mersenne31ComplexRadix2Dit;
    report.measurements.push(measure("native_complex_fft_256", 256, iterations, || dft.dft(input.clone())));
    report.measurements.push(measure("native_complex_lde_256_blowup16", 4096, iterations, || dft.lde(input.clone(), 4)));
    report.capabilities.push(Capability { primitive: "FFT/LDE".into(), status: "MEASURED_COMPLEX_BACKEND".into(), detail: "p3_mersenne_31::Mersenne31ComplexRadix2Dit; this is the complex backend path, not a multiplicative FFT over Mersenne31".into() });
}

fn add_permutation<F, P>(report: &mut CandidateReport, iterations: usize, permutation: P)
where
    F: Field + Debug,
    P: Permutation<[F; 16]>,
{
    let input: [F; 16] = std::array::from_fn(scalar::<F>);
    report.measurements.push(measure("native_poseidon2_width16", 1, iterations, || permutation.permute(black_box(input))));
    report.capabilities.push(Capability { primitive: "application permutation".into(), status: "MEASURED".into(), detail: "pinned Plonky3 default width-16 Poseidon2 parameters".into() });
}

fn close_capabilities(report: &mut CandidateReport, has_default_poseidon: bool) {
    if !has_default_poseidon {
        report.capabilities.push(Capability { primitive: "application permutation".into(), status: "UNSUPPORTED".into(), detail: "pinned field crate exports a Poseidon2 type but no reviewed default constants constructor".into() });
    }
    report.capabilities.push(Capability { primitive: "PCS commit/open/verify".into(), status: "NOT_MEASURED_NO_FROZEN_CONFIGURATION".into(), detail: "p3-fri/p3-circle are generic; SP-40 has no frozen hash/MMCS/transcript/PCS parameter tuple. Instantiating one would silently add a protocol decision, so only arithmetic and available field-native primitives are measured".into() });
    report.capabilities.push(Capability { primitive: "peak memory".into(), status: "MEASURED_PROCESS_WIDE".into(), detail: "RunReport.processPeakRssBytes records getrusage(RUSAGE_SELF) high-water RSS after every candidate; it is a whole-run upper bound, not per-operation allocation".into() });
    report.capabilities.push(Capability { primitive: "parallel scaling".into(), status: "MEASURED_THREAD_COUNTS_1_2_4".into(), detail: "parallel_dot_256 measurements execute equal 256-term dot products per worker; workload and thread creation are included explicitly".into() });
}

fn main() {
    type F0E = BinomialExtensionField<BabyBear, 4>;
    type F1E = BinomialExtensionField<KoalaBear, 4>;
    type F2E = QuinticTrinomialExtensionField<KoalaBear>;
    type F3E = BinomialExtensionField<Goldilocks, 2>;

    let args = parse_args();
    let mut f0 = arithmetic_report::<BabyBear, F0E>("F0", "BabyBear", "BabyBear[x]/(x^4-11)", 4, 16, args.iterations, args.rows, args.columns);
    add_dft::<BabyBear>(&mut f0, args.iterations);
    add_permutation::<BabyBear, _>(&mut f0, args.iterations, default_babybear_poseidon2_16());
    close_capabilities(&mut f0, true);

    let mut f1 = arithmetic_report::<KoalaBear, F1E>("F1", "KoalaBear", "KoalaBear[x]/(x^4-3)", 4, 16, args.iterations, args.rows, args.columns);
    add_dft::<KoalaBear>(&mut f1, args.iterations);
    add_permutation::<KoalaBear, _>(&mut f1, args.iterations, default_koalabear_poseidon2_16());
    close_capabilities(&mut f1, true);

    let mut f2 = arithmetic_report::<KoalaBear, F2E>("F2", "KoalaBear", "KoalaBear[x]/(x^5+x^2-1)", 4, 20, args.iterations, args.rows, args.columns);
    add_dft::<KoalaBear>(&mut f2, args.iterations);
    add_permutation::<KoalaBear, _>(&mut f2, args.iterations, default_koalabear_poseidon2_16());
    close_capabilities(&mut f2, true);

    let mut f3 = arithmetic_report::<Goldilocks, F3E>("F3", "Goldilocks", "Goldilocks[x]/(x^2-7)", 8, 16, args.iterations, args.rows, args.columns);
    add_dft::<Goldilocks>(&mut f3, args.iterations);
    add_permutation::<Goldilocks, _>(&mut f3, args.iterations, default_goldilocks_poseidon2_16());
    close_capabilities(&mut f3, true);

    let mut f4 = arithmetic_report::<Mersenne31, QM31>("F4", "Mersenne31", "QM31=(F_p[i]/(i^2+1))[u]/(u^2-(2+i))", 4, 16, args.iterations, args.rows, args.columns);
    add_mersenne_complex_dft(&mut f4, args.iterations);
    add_permutation::<Mersenne31, _>(&mut f4, args.iterations, default_mersenne31_poseidon2_16());
    close_capabilities(&mut f4, true);

    let mut f5 = arithmetic_report::<Bn254, Bn254>("F5", "BN254 scalar field", "base field (degree one)", 32, 32, args.iterations, args.rows, args.columns);
    add_dft::<Bn254>(&mut f5, args.iterations);
    close_capabilities(&mut f5, false);

    let report = RunReport {
        schema_version: "sp40-field-bakeoff-v1",
        benchmark_only: true,
        complete_proof_claimed: false,
        pinned_plonky3_commit: PINNED_PLONKY3,
        iterations: args.iterations,
        measurement_classification: "DIAGNOSTIC_NOT_COMMON_PROTOCOL",
        common_protocol_comparable: false,
        warmup_iterations: 0,
        input_distribution: "fixed wrapping-u64 mixer; not the frozen common-protocol corpus distribution",
        timing_caveat: "64-iteration scalar samples can be timer-overhead-scale; values are smoke diagnostics only and cannot support cross-candidate ranking or nondominance",
        process_peak_rss_bytes: peak_rss_bytes(),
        candidates: vec![f0, f1, f2, f3, f4, f5],
    };
    if let Some(parent) = args.out.parent() {
        fs::create_dir_all(parent).expect("create output directory");
    }
    fs::write(&args.out, serde_json::to_vec_pretty(&report).expect("serialize report")).expect("write report");
    println!("{}", args.out.display());
}

#[cfg(test)]
mod tests {
    use super::*;

    fn field_identities<F, EF>()
    where
        F: Field + Debug,
        EF: Field + Algebra<F> + BasedVectorSpace<F> + Debug,
    {
        let a = scalar::<F>(1);
        let e = ext::<F, EF>(2);
        assert_eq!((a + F::ONE) - F::ONE, a);
        assert_eq!(a * a.try_inverse().unwrap(), F::ONE);
        assert_eq!(e * e.try_inverse().unwrap(), EF::ONE);
        assert_eq!(e.square(), e * e);
        assert_eq!(e * F::ONE, e);
    }

    #[test]
    fn every_supported_stack_satisfies_shared_kernel_identities() {
        field_identities::<BabyBear, BinomialExtensionField<BabyBear, 4>>();
        field_identities::<KoalaBear, BinomialExtensionField<KoalaBear, 4>>();
        field_identities::<KoalaBear, QuinticTrinomialExtensionField<KoalaBear>>();
        field_identities::<Goldilocks, BinomialExtensionField<Goldilocks, 2>>();
        field_identities::<Mersenne31, QM31>();
        field_identities::<Bn254, Bn254>();
    }
}
