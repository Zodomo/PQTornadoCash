#![allow(
    clippy::many_single_char_names,
    clippy::needless_pass_by_value,
    clippy::needless_range_loop,
    clippy::too_many_arguments,
    clippy::too_many_lines
)]

use core::borrow::Borrow;

use p3_air::{Air, AirBuilder, BaseAir, ConstraintReport, WindowAccess, check_all_constraints};
use p3_baby_bear::{
    BABYBEAR_POSEIDON2_HALF_FULL_ROUNDS, BABYBEAR_POSEIDON2_PARTIAL_ROUNDS_16,
    BABYBEAR_POSEIDON2_RC_16_EXTERNAL_FINAL, BABYBEAR_POSEIDON2_RC_16_EXTERNAL_INITIAL,
    BABYBEAR_POSEIDON2_RC_16_INTERNAL, BABYBEAR_S_BOX_DEGREE, BabyBear,
    GenericPoseidon2LinearLayersBabyBear, default_babybear_poseidon2_16,
};
use p3_field::PrimeCharacteristicRing;
use p3_matrix::{Matrix, dense::RowMajorMatrix};
use p3_poseidon2_air::{
    Poseidon2Air, Poseidon2Cols, RoundConstants, generate_trace_rows, num_cols,
};
use p3_symmetric::Permutation;
use p3_uni_stark::SubAirBuilder;
use pqtc_hash::digest_to_elements;
use pqtc_spec::{PUBLIC_VALUES_COUNT, WithdrawalStatement, domains};

use crate::{RelationError, WithdrawalWitness, check_witness, public_values};

const WIDTH: usize = 16;
const RATE: usize = 4;
const REGS: usize = 0;
const HALF: usize = BABYBEAR_POSEIDON2_HALF_FULL_ROUNDS;
const PARTIAL: usize = BABYBEAR_POSEIDON2_PARTIAL_ROUNDS_16;
type InnerAir = Poseidon2Air<
    BabyBear,
    GenericPoseidon2LinearLayersBabyBear,
    WIDTH,
    BABYBEAR_S_BOX_DEGREE,
    REGS,
    HALF,
    PARTIAL,
>;
type InnerCols<T> = Poseidon2Cols<T, WIDTH, BABYBEAR_S_BOX_DEGREE, REGS, HALF, PARTIAL>;

pub const NUM_POSEIDON_COLS: usize =
    num_cols::<WIDTH, BABYBEAR_S_BOX_DEGREE, REGS, HALF, PARTIAL>();
pub(crate) const IS_NOTE: usize = NUM_POSEIDON_COLS;
pub(crate) const IS_NULLIFIER: usize = IS_NOTE + 1;
pub(crate) const IS_MERKLE: usize = IS_NULLIFIER + 1;
pub(crate) const IS_PAYOUT: usize = IS_MERKLE + 1;
pub(crate) const IS_PADDING: usize = IS_PAYOUT + 1;
pub(crate) const STEP_BITS: usize = IS_PADDING + 1;
pub(crate) const LEVEL_BITS: usize = STEP_BITS + 4;
pub(crate) const IS_LAST_LEVEL: usize = LEVEL_BITS + 5;
pub(crate) const PATH_BIT: usize = IS_LAST_LEVEL + 1;
pub(crate) const INDEX: usize = PATH_BIT + 1;
pub(crate) const WORK: usize = INDEX + 1;
pub const NUM_WITHDRAWAL_COLS: usize = WORK + 16;
pub const NUM_CONSTRAINTS: usize = 1_186;
pub const ACTIVE_PERMUTATIONS: usize = 240;
pub const TRACE_HEIGHT: usize = 256;
pub const MAX_CONSTRAINT_DEGREE: usize = 7;
const _: () = assert!(NUM_POSEIDON_COLS == 157);
const _: () = assert!(NUM_WITHDRAWAL_COLS == 190);
const _: () = assert!(PUBLIC_VALUES_COUNT == 64);

/// Returns the identity column index for a Poseidon input.
///
/// # Panics
///
/// Panics when `index` is outside the 16-column permutation width.
#[must_use]
pub const fn poseidon_input(index: usize) -> usize {
    assert!(index < WIDTH);
    index
}
fn constants() -> RoundConstants<BabyBear, WIDTH, HALF, PARTIAL> {
    RoundConstants::new(
        BABYBEAR_POSEIDON2_RC_16_EXTERNAL_INITIAL,
        BABYBEAR_POSEIDON2_RC_16_INTERNAL,
        BABYBEAR_POSEIDON2_RC_16_EXTERNAL_FINAL,
    )
}

#[derive(Clone)]
pub struct WithdrawalAir {
    poseidon: InnerAir,
}
impl Default for WithdrawalAir {
    fn default() -> Self {
        Self {
            poseidon: Poseidon2Air::new(constants()),
        }
    }
}
impl BaseAir<BabyBear> for WithdrawalAir {
    fn width(&self) -> usize {
        NUM_WITHDRAWAL_COLS
    }
    fn num_public_values(&self) -> usize {
        PUBLIC_VALUES_COUNT
    }
    fn max_constraint_degree(&self) -> Option<usize> {
        Some(MAX_CONSTRAINT_DEGREE)
    }
}

impl<AB: AirBuilder<F = BabyBear>> Air<AB> for WithdrawalAir {
    fn eval(&self, builder: &mut AB) {
        {
            let mut sub =
                SubAirBuilder::<_, InnerAir, BabyBear>::new(builder, 0..NUM_POSEIDON_COLS);
            self.poseidon.eval(&mut sub);
        }
        let main = builder.main();
        let local = main.current_slice();
        let next = main.next_slice();
        let lp: &InnerCols<AB::Var> = local[..NUM_POSEIDON_COLS].borrow();
        let np: &InnerCols<AB::Var> = next[..NUM_POSEIDON_COLS].borrow();
        let output = &lp.ending_full_rounds[HALF - 1].post;
        let public = builder.public_values().to_vec();

        for &c in &[
            IS_NOTE,
            IS_NULLIFIER,
            IS_MERKLE,
            IS_PAYOUT,
            IS_PADDING,
            IS_LAST_LEVEL,
            PATH_BIT,
        ] {
            builder.assert_bool(local[c]);
        }
        for c in STEP_BITS..STEP_BITS + 4 {
            builder.assert_bool(local[c]);
        }
        for c in LEVEL_BITS..LEVEL_BITS + 5 {
            builder.assert_bool(local[c]);
        }
        builder.assert_eq(
            local[IS_NOTE]
                + local[IS_NULLIFIER]
                + local[IS_MERKLE]
                + local[IS_PAYOUT]
                + local[IS_PADDING],
            AB::Expr::ONE,
        );
        builder.assert_eq(
            local[IS_LAST_LEVEL],
            AB::Expr::from(local[IS_MERKLE]) * level_eq::<AB>(local, 19),
        );
        builder
            .when(AB::Expr::ONE - local[IS_MERKLE])
            .assert_zero(local[PATH_BIT]);
        builder
            .when(AB::Expr::ONE - local[IS_MERKLE])
            .assert_zero(local[INDEX]);

        let mut first = builder.when_first_row();
        first.assert_one(local[IS_NULLIFIER]);
        first.assert_zero(step_value::<AB>(local));
        first.assert_zero(level_value::<AB>(local));
        for i in 8..16 {
            first.assert_zero(local[WORK + i]);
        }
        builder
            .when(AB::Expr::ONE - local[IS_MERKLE])
            .assert_zero(level_value::<AB>(local));
        builder
            .when(local[IS_PADDING])
            .assert_zero(step_value::<AB>(local));
        let mut last = builder.when_last_row();
        last.assert_one(local[IS_PADDING]);

        initial_row(
            builder,
            local,
            lp,
            IS_NULLIFIER,
            domains::NULLIFIER,
            96,
            24,
            false,
        );
        initial_row(builder, local, lp, IS_NOTE, domains::NOTE, 128, 32, false);
        initial_row(
            builder,
            local,
            lp,
            IS_MERKLE,
            domains::APP_MERKLE_NODE,
            128,
            32,
            true,
        );

        for j in 0..RATE {
            builder
                .when(AB::Expr::from(local[IS_NULLIFIER]) * step_eq::<AB>(local, 0))
                .assert_eq(lp.inputs[j], public[j]);
            builder
                .when(AB::Expr::from(local[IS_NOTE]) * step_eq::<AB>(local, 0))
                .assert_eq(lp.inputs[j], public[j]);
            builder
                .when(
                    AB::Expr::from(local[IS_MERKLE])
                        * step_eq::<AB>(local, 0)
                        * (AB::Expr::ONE - local[PATH_BIT]),
                )
                .assert_eq(lp.inputs[j], local[WORK + j]);
        }
        for step in 0..4 {
            let c = AB::Expr::from(local[IS_PAYOUT]) * step_eq::<AB>(local, step);
            for j in 0..RATE {
                builder
                    .when(c.clone())
                    .assert_eq(lp.inputs[j], public[48 + step * RATE + j]);
            }
            for j in RATE..WIDTH {
                builder.when(c.clone()).assert_zero(lp.inputs[j]);
            }
        }
        for j in 0..WIDTH {
            builder.when(local[IS_PADDING]).assert_zero(lp.inputs[j]);
            builder
                .when(local[IS_PAYOUT] + local[IS_PADDING])
                .assert_zero(local[WORK + j]);
        }

        let tr = builder.is_transition();
        metadata(builder, local, next, tr.clone());
        chaining(builder, next, lp, np, &public, tr.clone());

        for i in 0..16 {
            builder
                .when(tr.clone() * local[IS_NULLIFIER])
                .assert_eq(next[WORK + i], local[WORK + i]);
        }
        for step in 0..11 {
            work_transition(
                builder,
                local,
                next,
                output,
                tr.clone() * local[IS_NOTE] * step_eq::<AB>(local, step),
                7,
                step,
            );
        }
        for step in 0..10 {
            work_transition(
                builder,
                local,
                next,
                output,
                tr.clone() * local[IS_MERKLE] * step_eq::<AB>(local, step),
                7,
                step,
            );
        }
        work_transition(
            builder,
            local,
            next,
            output,
            tr.clone()
                * local[IS_MERKLE]
                * step_eq::<AB>(local, 10)
                * (AB::Expr::ONE - local[IS_LAST_LEVEL]),
            7,
            10,
        );

        for chunk in 0..4 {
            let nc = AB::Expr::from(local[IS_NULLIFIER]) * step_eq::<AB>(local, 5 + chunk);
            let rc = AB::Expr::from(local[IS_MERKLE])
                * local[IS_LAST_LEVEL]
                * step_eq::<AB>(local, 7 + chunk);
            for j in 0..RATE {
                builder
                    .when(nc.clone())
                    .assert_eq(output[j], public[32 + chunk * RATE + j]);
                builder
                    .when(rc.clone())
                    .assert_eq(output[j], public[16 + chunk * RATE + j]);
            }
        }
    }
}

fn initial_row<AB: AirBuilder<F = BabyBear>>(
    b: &mut AB,
    r: &[AB::Var],
    p: &InnerCols<AB::Var>,
    selector: usize,
    tag: u8,
    bytes: u32,
    elements: u32,
    level: bool,
) {
    let c = AB::Expr::from(r[selector]) * step_eq::<AB>(r, 0);
    b.when(c.clone()).assert_eq(p.inputs[4], BabyBear::ONE);
    b.when(c.clone())
        .assert_eq(p.inputs[5], BabyBear::from_u8(tag));
    b.when(c.clone())
        .assert_eq(p.inputs[6], BabyBear::from_u32(bytes));
    b.when(c.clone())
        .assert_eq(p.inputs[7], BabyBear::from_u32(elements));
    if level {
        b.when(c.clone())
            .assert_eq(p.inputs[8], level_value::<AB>(r));
    } else {
        b.when(c.clone()).assert_zero(p.inputs[8]);
    }
    for i in 9..WIDTH {
        b.when(c.clone()).assert_zero(p.inputs[i]);
    }
}

fn metadata<AB: AirBuilder<F = BabyBear>>(b: &mut AB, l: &[AB::Var], n: &[AB::Var], tr: AB::Expr) {
    let s = step_value::<AB>(l);
    let ns = step_value::<AB>(n);
    let lev = level_value::<AB>(l);
    let nl = level_value::<AB>(n);

    let c = tr.clone() * l[IS_NULLIFIER] * (AB::Expr::ONE - step_eq::<AB>(l, 8));
    b.when(c.clone()).assert_one(n[IS_NULLIFIER]);
    b.when(c).assert_eq(ns.clone(), s.clone() + AB::Expr::ONE);
    let c = tr.clone() * l[IS_NULLIFIER] * step_eq::<AB>(l, 8);
    b.when(c.clone()).assert_one(n[IS_NOTE]);
    b.when(c).assert_zero(ns.clone());

    let c = tr.clone() * l[IS_NOTE] * (AB::Expr::ONE - step_eq::<AB>(l, 10));
    b.when(c.clone()).assert_one(n[IS_NOTE]);
    b.when(c).assert_eq(ns.clone(), s.clone() + AB::Expr::ONE);
    let c = tr.clone() * l[IS_NOTE] * step_eq::<AB>(l, 10);
    b.when(c.clone()).assert_one(n[IS_MERKLE]);
    b.when(c.clone()).assert_zero(ns.clone());
    b.when(c).assert_zero(nl.clone());

    let c = tr.clone() * l[IS_MERKLE] * (AB::Expr::ONE - step_eq::<AB>(l, 10));
    b.when(c.clone()).assert_one(n[IS_MERKLE]);
    b.when(c.clone()).assert_eq(ns.clone(), s + AB::Expr::ONE);
    b.when(c.clone()).assert_eq(nl.clone(), lev.clone());
    b.when(c.clone()).assert_eq(n[PATH_BIT], l[PATH_BIT]);
    b.when(c).assert_eq(n[INDEX], l[INDEX]);
    let c = tr.clone() * l[IS_MERKLE] * step_eq::<AB>(l, 10) * (AB::Expr::ONE - l[IS_LAST_LEVEL]);
    b.when(c.clone()).assert_one(n[IS_MERKLE]);
    b.when(c.clone()).assert_zero(ns.clone());
    b.when(c.clone()).assert_eq(nl, lev + AB::Expr::ONE);
    b.when(c)
        .assert_eq(l[INDEX], l[PATH_BIT] + AB::Expr::TWO * n[INDEX]);
    let c = tr.clone() * l[IS_MERKLE] * step_eq::<AB>(l, 10) * l[IS_LAST_LEVEL];
    b.when(c.clone()).assert_one(n[IS_PAYOUT]);
    b.when(c.clone()).assert_zero(ns.clone());
    b.when(c).assert_eq(l[INDEX], l[PATH_BIT]);

    let c = tr.clone() * l[IS_PAYOUT] * (AB::Expr::ONE - step_eq::<AB>(l, 3));
    b.when(c.clone()).assert_one(n[IS_PAYOUT]);
    b.when(c)
        .assert_eq(ns.clone(), step_value::<AB>(l) + AB::Expr::ONE);
    let c = tr.clone() * l[IS_PAYOUT] * step_eq::<AB>(l, 3);
    b.when(c.clone()).assert_one(n[IS_PADDING]);
    b.when(c).assert_zero(ns.clone());
    let c = tr * l[IS_PADDING];
    b.when(c.clone()).assert_one(n[IS_PADDING]);
    b.when(c).assert_zero(ns);
}

fn chaining<AB: AirBuilder<F = BabyBear>>(
    b: &mut AB,
    n: &[AB::Var],
    lp: &InnerCols<AB::Var>,
    np: &InnerCols<AB::Var>,
    public: &[AB::PublicVar],
    tr: AB::Expr,
) {
    let out = &lp.ending_full_rounds[HALF - 1].post;

    for step in 1..6 {
        let c = tr.clone() * n[IS_NULLIFIER] * step_eq::<AB>(n, step);
        for j in 0..RATE {
            let payload: AB::Expr = if step < 4 {
                public[step * RATE + j].into()
            } else {
                AB::Expr::from(n[WORK + (step - 4) * RATE + j])
            };
            b.when(c.clone())
                .assert_eq(np.inputs[j], AB::Expr::from(out[j]) + payload);
        }
        for j in RATE..WIDTH {
            b.when(c.clone()).assert_eq(np.inputs[j], out[j]);
        }
    }
    for step in 6..9 {
        squeeze(
            b,
            np,
            out,
            tr.clone() * n[IS_NULLIFIER] * step_eq::<AB>(n, step),
        );
    }

    for step in 1..8 {
        let c = tr.clone() * n[IS_NOTE] * step_eq::<AB>(n, step);
        // On steps 6 and 7 the four unconstrained rate deltas are exactly the
        // eight trapdoor limbs; all twelve capacity lanes are still chained below.
        for j in 0..RATE {
            if step < 4 {
                let payload: AB::Expr = public[step * RATE + j].into();
                b.when(c.clone())
                    .assert_eq(np.inputs[j], AB::Expr::from(out[j]) + payload);
            } else if step < 6 {
                b.when(c.clone())
                    .assert_eq(np.inputs[j], out[j] + n[WORK + (step - 4) * RATE + j]);
            }
        }
        for j in RATE..WIDTH {
            b.when(c.clone()).assert_eq(np.inputs[j], out[j]);
        }
    }
    for step in 8..11 {
        squeeze(b, np, out, tr.clone() * n[IS_NOTE] * step_eq::<AB>(n, step));
    }

    for step in 1..8 {
        let c = tr.clone() * n[IS_MERKLE] * step_eq::<AB>(n, step);
        for j in 0..RATE {
            let k = step * RATE + j;
            let cc = if k < 16 {
                c.clone() * (AB::Expr::ONE - n[PATH_BIT])
            } else {
                c.clone() * n[PATH_BIT]
            };
            b.when(cc)
                .assert_eq(np.inputs[j], AB::Expr::from(out[j]) + n[WORK + k % 16]);
        }
        for j in RATE..WIDTH {
            b.when(c.clone()).assert_eq(np.inputs[j], out[j]);
        }
    }
    for step in 8..11 {
        squeeze(
            b,
            np,
            out,
            tr.clone() * n[IS_MERKLE] * step_eq::<AB>(n, step),
        );
    }
}
fn squeeze<AB: AirBuilder<F = BabyBear>>(
    b: &mut AB,
    np: &InnerCols<AB::Var>,
    out: &[AB::Var; WIDTH],
    c: AB::Expr,
) {
    for j in 0..WIDTH {
        b.when(c.clone()).assert_eq(np.inputs[j], out[j]);
    }
}
fn work_transition<AB: AirBuilder<F = BabyBear>>(
    b: &mut AB,
    l: &[AB::Var],
    n: &[AB::Var],
    out: &[AB::Var; WIDTH],
    c: AB::Expr,
    first: usize,
    step: usize,
) {
    let chunk = step.checked_sub(first).filter(|&x| x < 4);
    for i in 0..16 {
        if chunk == Some(i / RATE) {
            b.when(c.clone()).assert_eq(n[WORK + i], out[i % RATE]);
        } else {
            b.when(c.clone()).assert_eq(n[WORK + i], l[WORK + i]);
        }
    }
}
fn step_eq<AB: AirBuilder>(r: &[AB::Var], v: usize) -> AB::Expr {
    bits_eq::<AB>(&r[STEP_BITS..STEP_BITS + 4], v)
}
fn level_eq<AB: AirBuilder>(r: &[AB::Var], v: usize) -> AB::Expr {
    bits_eq::<AB>(&r[LEVEL_BITS..LEVEL_BITS + 5], v)
}
fn bits_eq<AB: AirBuilder>(bits: &[AB::Var], v: usize) -> AB::Expr {
    bits.iter().enumerate().fold(AB::Expr::ONE, |p, (i, x)| {
        p * if (v >> i) & 1 == 1 {
            AB::Expr::from(*x)
        } else {
            AB::Expr::ONE - *x
        }
    })
}
fn step_value<AB: AirBuilder>(r: &[AB::Var]) -> AB::Expr {
    bit_value::<AB>(&r[STEP_BITS..STEP_BITS + 4])
}
fn level_value<AB: AirBuilder>(r: &[AB::Var]) -> AB::Expr {
    bit_value::<AB>(&r[LEVEL_BITS..LEVEL_BITS + 5])
}
fn bit_value<AB: AirBuilder>(bits: &[AB::Var]) -> AB::Expr {
    bits.iter().enumerate().fold(AB::Expr::ZERO, |s, (i, x)| {
        s + AB::Expr::from_usize(1 << i) * *x
    })
}

#[derive(Clone, Copy)]
enum Kind {
    Note,
    Nullifier,
    Merkle,
}
#[derive(Clone)]
struct ControllerRow {
    kind: Kind,
    step: usize,
    level: usize,
    path_bit: u8,
    index: u32,
    work: [BabyBear; 16],
}

#[allow(clippy::too_many_arguments)]
fn append_hash(
    inputs: &mut Vec<[BabyBear; WIDTH]>,
    rows: &mut Vec<ControllerRow>,
    perm: &impl Permutation<[BabyBear; WIDTH]>,
    kind: Kind,
    tag: u8,
    bytes: u32,
    aux: u32,
    payload: &[BabyBear],
    level: usize,
    path_bit: u8,
    index: u32,
    work: &mut [BabyBear; 16],
    update_work: bool,
) {
    debug_assert_eq!(payload.len() % RATE, 0);
    let absorb = payload.len() / RATE;
    let mut state = [BabyBear::ZERO; WIDTH];
    state[4] = BabyBear::ONE;
    state[5] = BabyBear::from_u8(tag);
    state[6] = BabyBear::from_u32(bytes);
    state[7] = BabyBear::from_usize(payload.len());
    state[8] = BabyBear::from_u32(aux);
    for step in 0..absorb {
        for j in 0..RATE {
            state[j] += payload[step * RATE + j];
        }
        inputs.push(state);
        rows.push(ControllerRow {
            kind,
            step,
            level,
            path_bit,
            index,
            work: *work,
        });
        perm.permute_mut(&mut state);
        if update_work && step + 1 == absorb {
            work[..RATE].copy_from_slice(&state[..RATE]);
        }
    }
    for squeeze in 1..4 {
        let step = absorb + squeeze - 1;
        inputs.push(state);
        rows.push(ControllerRow {
            kind,
            step,
            level,
            path_bit,
            index,
            work: *work,
        });
        perm.permute_mut(&mut state);
        if update_work {
            work[squeeze * RATE..(squeeze + 1) * RATE].copy_from_slice(&state[..RATE]);
        }
    }
}

/// Generates the canonical withdrawal execution trace.
///
/// # Errors
///
/// Returns [`RelationError`] when the witness does not satisfy the withdrawal
/// relation or contains a noncanonical digest.
///
/// # Panics
///
/// Panics only if fixed protocol dimensions are internally inconsistent.
pub fn generate_withdrawal_trace(
    statement: WithdrawalStatement,
    witness: &WithdrawalWitness,
) -> Result<RowMajorMatrix<BabyBear>, RelationError> {
    check_witness(statement, witness)?;
    let perm = default_babybear_poseidon2_16();
    let scope = digest_to_elements(statement.scope).expect("checked scope");
    let secret = (*witness.nullifier_secret.limbs()).map(BabyBear::from_u32);
    let trapdoor = (*witness.trapdoor.limbs()).map(BabyBear::from_u32);
    let mut inputs = Vec::with_capacity(TRACE_HEIGHT);
    let mut rows = Vec::with_capacity(ACTIVE_PERMUTATIONS);
    let mut work = [BabyBear::ZERO; 16];
    work[..8].copy_from_slice(&secret);
    let mut payload = Vec::with_capacity(32);

    payload.extend_from_slice(&scope);
    payload.extend_from_slice(&secret);
    append_hash(
        &mut inputs,
        &mut rows,
        &perm,
        Kind::Nullifier,
        domains::NULLIFIER,
        96,
        0,
        &payload,
        0,
        0,
        0,
        &mut work,
        false,
    );

    payload.clear();
    payload.extend_from_slice(&scope);
    payload.extend_from_slice(&secret);
    payload.extend_from_slice(&trapdoor);
    append_hash(
        &mut inputs,
        &mut rows,
        &perm,
        Kind::Note,
        domains::NOTE,
        128,
        0,
        &payload,
        0,
        0,
        0,
        &mut work,
        true,
    );

    let mut remaining = witness.leaf_index;
    for level in 0..20 {
        let sibling = digest_to_elements(witness.siblings[level]).expect("checked sibling");
        let bit = witness.path_bits[level];
        payload.clear();
        if bit == 0 {
            payload.extend_from_slice(&work);
            payload.extend_from_slice(&sibling);
        } else {
            payload.extend_from_slice(&sibling);
            payload.extend_from_slice(&work);
        }
        append_hash(
            &mut inputs,
            &mut rows,
            &perm,
            Kind::Merkle,
            domains::APP_MERKLE_NODE,
            128,
            u32::try_from(level).map_err(|_| RelationError::LeafIndexOutOfRange)?,
            &payload,
            level,
            bit,
            remaining,
            &mut work,
            true,
        );
        remaining >>= 1;
    }
    assert_eq!(inputs.len(), ACTIVE_PERMUTATIONS);
    assert_eq!(rows.len(), ACTIVE_PERMUTATIONS);
    let pv = public_values(statement);
    for step in 0..4 {
        let mut input = [BabyBear::ZERO; WIDTH];
        input[..RATE].copy_from_slice(&pv[48 + step * RATE..48 + (step + 1) * RATE]);
        inputs.push(input);
    }
    inputs.resize(TRACE_HEIGHT, [BabyBear::ZERO; WIDTH]);
    let pt = generate_trace_rows::<
        BabyBear,
        GenericPoseidon2LinearLayersBabyBear,
        WIDTH,
        BABYBEAR_S_BOX_DEGREE,
        REGS,
        HALF,
        PARTIAL,
    >(inputs, &constants(), 0);
    let mut trace = RowMajorMatrix::new(
        BabyBear::zero_vec(TRACE_HEIGHT * NUM_WITHDRAWAL_COLS),
        NUM_WITHDRAWAL_COLS,
    );
    for ri in 0..TRACE_HEIGHT {
        let source = pt.row_slice(ri).expect("row");
        let row = &mut trace.values[ri * NUM_WITHDRAWAL_COLS..(ri + 1) * NUM_WITHDRAWAL_COLS];
        row[..NUM_POSEIDON_COLS].copy_from_slice(&source);
        if ri < ACTIVE_PERMUTATIONS {
            write_controller(row, &rows[ri]);
        } else if ri < ACTIVE_PERMUTATIONS + 4 {
            row[IS_PAYOUT] = BabyBear::ONE;
            write_bits(row, STEP_BITS, ri - ACTIVE_PERMUTATIONS, 4);
        } else {
            row[IS_PADDING] = BabyBear::ONE;
        }
    }
    Ok(trace)
}

fn write_controller(row: &mut [BabyBear], s: &ControllerRow) {
    row[match s.kind {
        Kind::Note => IS_NOTE,
        Kind::Nullifier => IS_NULLIFIER,
        Kind::Merkle => IS_MERKLE,
    }] = BabyBear::ONE;
    write_bits(row, STEP_BITS, s.step, 4);
    write_bits(row, LEVEL_BITS, s.level, 5);
    row[IS_LAST_LEVEL] = BabyBear::from_bool(matches!(s.kind, Kind::Merkle) && s.level == 19);
    row[PATH_BIT] = BabyBear::from_u8(s.path_bit);
    row[INDEX] = BabyBear::from_u32(s.index);
    row[WORK..WORK + 16].copy_from_slice(&s.work);
}
fn write_bits(row: &mut [BabyBear], start: usize, value: usize, bits: usize) {
    for bit in 0..bits {
        row[start + bit] = BabyBear::from_bool((value >> bit) & 1 == 1);
    }
}
#[must_use]
pub fn evaluate_constraints(
    trace: &RowMajorMatrix<BabyBear>,
    public: &[BabyBear],
    max_failures: Option<usize>,
) -> ConstraintReport {
    check_all_constraints(&WithdrawalAir::default(), trace, public, max_failures)
}
