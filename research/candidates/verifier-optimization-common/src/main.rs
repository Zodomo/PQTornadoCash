use std::env;
use std::fs;
use std::hint::black_box;
use std::time::Instant;

const P: u64 = 2_013_265_921;
const N: usize = 256;

fn add(a: u64, b: u64) -> u64 { (a + b) % P }
fn mul(a: u64, b: u64) -> u64 { (a * b) % P }
fn pow(mut x: u64, mut n: u64) -> u64 {
    let mut y = 1;
    while n != 0 {
        if n & 1 == 1 { y = mul(y, x); }
        x = mul(x, x);
        n >>= 1;
    }
    y
}
fn inverse(x: u64) -> Option<u64> { if x == 0 { None } else { Some(pow(x, P - 2)) } }
fn checked_inverse(x: u64, witness: u64, zero_legal: bool) -> Result<u64, &'static str> {
    if zero_legal { return Err("inverse witness forbidden where zero is legal"); }
    if x == 0 { return Err("nonzero denominator guard"); }
    if witness >= P || mul(x, witness) != 1 { return Err("invalid inverse witness"); }
    Ok(witness)
}

fn materialized(coeffs: &[u64], alpha: u64) -> u64 {
    let mut powers = vec![1u64; coeffs.len()];
    for i in 1..coeffs.len() { powers[i] = mul(powers[i - 1], alpha); }
    coeffs.iter().zip(powers).fold(0, |acc, (&c, a)| add(acc, mul(c, a)))
}
fn streamed(coeffs: &[u64], alpha: u64) -> u64 {
    let (mut acc, mut power) = (0, 1);
    for &c in coeffs { acc = add(acc, mul(c, power)); power = mul(power, alpha); }
    acc
}
fn horner(coeffs: &[u64], alpha: u64) -> u64 {
    coeffs.iter().rev().fold(0, |acc, &c| add(mul(acc, alpha), c))
}
fn parse_u32_be(bytes: &[u8], at: usize) -> Result<u64, &'static str> {
    if at + 4 > bytes.len() { return Err("truncated field"); }
    let x = u32::from_be_bytes(bytes[at..at + 4].try_into().unwrap()) as u64;
    if x >= P { return Err("noncanonical field"); }
    Ok(x)
}
fn parse_then_dot(bytes: &[u8], weights: &[u64]) -> Result<u64, &'static str> {
    if bytes.len() != weights.len() * 4 { return Err("wrong section length"); }
    let mut parsed = Vec::with_capacity(weights.len());
    for i in 0..weights.len() { parsed.push(parse_u32_be(bytes, i * 4)?); }
    Ok(parsed.iter().zip(weights).fold(0, |a, (&x, &w)| add(a, mul(x, w))))
}
fn fused_dot(bytes: &[u8], weights: &[u64]) -> Result<u64, &'static str> {
    if bytes.len() != weights.len() * 4 { return Err("wrong section length"); }
    let mut acc = 0;
    for (i, &w) in weights.iter().enumerate() { acc = add(acc, mul(parse_u32_be(bytes, i * 4)?, w)); }
    Ok(acc)
}
fn pack31(values: &[u32]) -> Result<Vec<u8>, &'static str> {
    let mut out = Vec::with_capacity((values.len() * 31 + 7) / 8);
    let (mut bits, mut used) = (0u64, 0usize);
    for &v in values {
        if v as u64 >= P { return Err("noncanonical field"); }
        bits |= (v as u64) << used;
        used += 31;
        while used >= 8 { out.push(bits as u8); bits >>= 8; used -= 8; }
    }
    if used != 0 { out.push(bits as u8); }
    Ok(out)
}
fn unpack31(bytes: &[u8], count: usize) -> Result<Vec<u32>, &'static str> {
    let expected = (count.checked_mul(31).ok_or("length overflow")? + 7) / 8;
    if bytes.len() != expected { return Err("noncanonical packed length"); }
    let (mut out, mut bits, mut used, mut at) = (Vec::with_capacity(count), 0u64, 0usize, 0usize);
    for _ in 0..count {
        while used < 31 {
            bits |= (bytes[at] as u64) << used;
            used += 8;
            at += 1;
        }
        let v = bits & 0x7fff_ffff;
        if v >= P { return Err("noncanonical field"); }
        out.push(v as u32);
        bits >>= 31;
        used -= 31;
    }
    if used != 0 && bits != 0 { return Err("nonzero padding bits"); }
    Ok(out)
}
fn frontier_count(indices: &[u32], depth: u32) -> Result<usize, &'static str> {
    if depth > 31 { return Err("unsupported depth"); }
    let mut nodes = indices.to_vec();
    nodes.sort_unstable();
    if nodes.windows(2).any(|x| x[0] == x[1]) { return Err("duplicate query index"); }
    if nodes.iter().any(|&x| x >= (1u32 << depth)) { return Err("query index out of range"); }
    let mut frontier = 0;
    for _ in 0..depth {
        let mut parents = Vec::with_capacity(nodes.len());
        let mut i = 0;
        while i < nodes.len() {
            if i + 1 < nodes.len() && nodes[i + 1] == (nodes[i] ^ 1) { i += 2; } else { frontier += 1; i += 1; }
            let parent = nodes[i - 1] >> 1;
            if parents.last().copied() != Some(parent) { parents.push(parent); }
        }
        nodes = parents;
    }
    Ok(frontier)
}
fn exact_max_frontier(depth: usize, queries: usize) -> usize {
    let impossible = usize::MAX / 4;
    let mut dp = vec![vec![impossible; queries + 1]; depth + 1];
    dp[0][0] = 0;
    if queries >= 1 { dp[0][1] = 0; }
    for h in 1..=depth {
        let cap = (1usize << h).min(queries);
        for q in 0..=cap {
            let child_cap = 1usize << (h - 1);
            let lo = q.saturating_sub(child_cap);
            let hi = q.min(child_cap);
            let mut best = 0;
            for l in lo..=hi {
                let r = q - l;
                if dp[h - 1][l] == impossible || dp[h - 1][r] == impossible { continue; }
                let added = usize::from(l == 0 && r > 0) + usize::from(r == 0 && l > 0);
                best = best.max(dp[h - 1][l] + dp[h - 1][r] + added);
            }
            dp[h][q] = best;
        }
    }
    dp[depth][queries]
}
fn bench<F: FnMut() -> u64>(reps: u64, mut f: F) -> (u128, u64) {
    let start = Instant::now();
    let mut checksum = 0;
    for _ in 0..reps { checksum ^= black_box(f()); }
    (start.elapsed().as_nanos(), checksum)
}
fn main() {
    let mut output = None;
    let mut reps = 2_000u64;
    let args: Vec<String> = env::args().collect();
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--output" => { i += 1; output = args.get(i).cloned(); }
            "--repetitions" => { i += 1; reps = args.get(i).and_then(|x| x.parse().ok()).expect("valid repetitions"); }
            _ => panic!("unknown argument: {}", args[i]),
        }
        i += 1;
    }
    let coeffs: Vec<u64> = (0..N).map(|i| ((i * 1_000_003 + 17) as u64) % P).collect();
    let weights: Vec<u64> = (0..N).map(|i| ((i * 65_537 + 29) as u64) % P).collect();
    let bytes: Vec<u8> = coeffs.iter().flat_map(|x| (*x as u32).to_be_bytes()).collect();
    let mut table32 = Vec::with_capacity(32);
    let mut table_value = 1;
    for _ in 0..32 { table32.push(table_value); table_value = mul(table_value, 7); }
    let query_step = pow(7, 127);
    let mut query_points = Vec::with_capacity(32);
    let mut query_value = 1;
    for _ in 0..32 { query_points.push(query_value); query_value = mul(query_value, query_step); }
    assert_eq!(materialized(&coeffs, 7), streamed(&coeffs, 7));
    assert_eq!(streamed(&coeffs, 7), horner(&coeffs, 7));
    assert_eq!(parse_then_dot(&bytes, &weights), fused_dot(&bytes, &weights));
    let fields: Vec<u32> = coeffs.iter().map(|&x| x as u32).collect();
    let packed = pack31(&fields).unwrap();
    assert_eq!(unpack31(&packed, fields.len()).unwrap(), fields);
    assert!(pack31(&[P as u32]).is_err());
    assert!(unpack31(&packed[..packed.len() - 1], fields.len()).is_err());
    let mut padded = pack31(&[1]).unwrap(); padded[3] |= 0x80;
    assert!(unpack31(&padded, 1).is_err());
    assert!(checked_inverse(0, 0, false).is_err());
    assert!(checked_inverse(1, 1, true).is_err());
    assert!(checked_inverse(7, inverse(7).unwrap(), false).is_ok());
    assert!(frontier_count(&[1, 1], 9).is_err());
    assert!(frontier_count(&[512], 9).is_err());

    let (v1_materialized, c1) = bench(reps, || materialized(&coeffs, 7));
    let (v1_streamed, c2) = bench(reps, || streamed(&coeffs, 7));
    let (v1_horner, c3) = bench(reps, || horner(&coeffs, 7));
    let denominators: Vec<u64> = (2..34).collect();
    let inverses: Vec<u64> = denominators.iter().map(|&x| inverse(x).unwrap()).collect();
    let (v2_exp, c4) = bench(reps / 10 + 1, || denominators.iter().fold(0, |a, &x| a ^ inverse(x).unwrap()));
    let (v2_checked, c5) = bench(reps / 10 + 1, || denominators.iter().zip(&inverses).fold(0, |a, (&x, &w)| a ^ checked_inverse(x, w, false).unwrap()));
    let (v3_two_pass, c6) = bench(reps, || parse_then_dot(&bytes, &weights).unwrap());
    let (v3_fused, c7) = bench(reps, || fused_dot(&bytes, &weights).unwrap());
    let (v4_copy, c8) = bench(reps, || { let copied = coeffs.clone(); streamed(&copied, 7) });
    let (v4_slice, c9) = bench(reps, || streamed(&coeffs, 7));
    let (v5_fixed, c10) = bench(reps, || table32.iter().fold(0, |a, &x| a ^ x));
    let (v5_derived, c11) = bench(reps, || { let mut x = 1; (0..32).fold(0, |a, _| { let y=x; x=mul(x,7); a^y }) });
    let (v5_checked, c12) = bench(reps, || table32.windows(2).fold(table32[0], |a, x| { assert_eq!(x[1], mul(x[0], 7)); a ^ x[1] }));
    let exponents: Vec<u64> = (0..32).map(|x| x * 127).collect();
    let (v6_exp, c13) = bench(reps / 10 + 1, || exponents.iter().fold(0, |a, &e| a ^ pow(7,e)));
    let (v6_incremental, c14) = bench(reps / 10 + 1, || (0..32).fold((0,1), |(a,x),_| (a^x,mul(x,query_step))).0);
    let (v6_checked, c15) = bench(reps / 10 + 1, || query_points.windows(2).fold(query_points[0], |a, x| { assert_eq!(x[1], mul(x[0], query_step)); a ^ x[1] }));
    let (v6_fixed, c16) = bench(reps, || query_points[..8].iter().fold(0, |a, &x| a ^ x));
    let (v8_u32, c17) = bench(reps, || (0..fields.len()).fold(0, |a,i| a ^ parse_u32_be(&bytes, i*4).unwrap()));
    let (v8_pack, c18) = bench(reps, || pack31(&fields).unwrap().len() as u64);
    let checksums = [c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12,c13,c14,c15,c16,c17,c18].iter().fold(0u64, |a,&x| a^x);
    let max_frontier_13_32 = exact_max_frontier(13, 32);
    let spread: Vec<u32> = (0..32).map(|i| i * 256).collect();
    assert_eq!(frontier_count(&spread, 13).unwrap(), max_frontier_13_32);
    let json = format!(r#"{{
  "schema":"pqtc-sp31-native-measurements-v1",
  "engine":"rust-std-instant",
  "repetitions":{reps},
  "babyBearModulus":{P},
  "terms":{N},
  "checksums":{checksums},
  "measurements":{{
    "V1":{{"materializedNs":{v1_materialized},"streamedNs":{v1_streamed},"hornerNs":{v1_horner},"materializedBytes":2048,"streamedBytes":0,"materializedMultiplications":511,"streamedMultiplications":512,"hornerMultiplications":256}},
    "V2":{{"exponentiationNs":{v2_exp},"checkedWitnessNs":{v2_checked},"witnessBytes":128,"exponentiationMultiplicationsPerInverse":61,"checkedMultiplicationsPerInverse":1}},
    "V3":{{"separateParseDotNs":{v3_two_pass},"fusedParseDotNs":{v3_fused},"separateScratchBytes":2048,"fusedScratchBytes":0}},
    "V4":{{"copyEvaluateNs":{v4_copy},"sliceEvaluateNs":{v4_slice},"copyBytes":2048,"boundedScratchBytes":0}},
    "V5":{{"fixedReadNs":{v5_fixed},"derivedNs":{v5_derived},"calldataCheckedNs":{v5_checked},"fixedTableBytes":128,"calldataTableBytes":128}},
    "V6":{{"exponentiationNs":{v6_exp},"incrementalNs":{v6_incremental},"checkedSuppliedNs":{v6_checked},"fixedTable8Ns":{v6_fixed},"suppliedPointBytes":128,"fixedTableBytes":32}},
    "V7":{{"treeDepth":13,"queries":32,"exactWorstCaseFrontierDigests":{max_frontier_13_32},"digest512WorstCaseBytes":{},"digest384WorstCaseBytes":{},"digest320WorstCaseBytes":{},"digest256LowerBoundBytes":{}}},
    "V8":{{"u32ReadNs":{v8_u32},"pack31Ns":{v8_pack},"elements":256,"u32Bytes":1024,"packed31Bytes":{}}},
    "V9":{{"splits":[[8,24],[10,22],[12,20],[13,19],[14,18],[15,17],[16,16]],"model":"evaluated by package driver with AIR segment placement"}}
  }},
  "negativeTests":{{"zeroInverseRejected":true,"zeroLegalWitnessRejected":true,"noncanonicalFieldRejected":true,"truncatedPackingRejected":true,"nonzeroPaddingRejected":true,"duplicateFrontierIndexRejected":true,"outOfRangeFrontierIndexRejected":true}}
}}"#, max_frontier_13_32*64, max_frontier_13_32*48, max_frontier_13_32*40, max_frontier_13_32*32, packed.len());
    if let Some(path) = output { fs::write(path, &json).expect("write output"); } else { println!("{json}"); }
}
