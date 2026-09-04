# Focused external request: R2-01 / F04 / F09 / F11

**Review status: OPEN. No reviewer has accepted this packet. No signature, expert approval, security bits or deployment recommendation is inferred from internal execution.** Measurement continues independently of this request.

Return one versioned answer per item below, tied to the exact source/constant/input hashes in generated `outputs/results.json`, `sources/index.json`, the frozen Plonky3 commit3152b14a89067c83775a8076cc262ffc48a1fd7c, and the exact R2 experimental IDs. Allowed answers are ACCEPT_SCOPED_MODEL, COUNTEREXAMPLE, APPLICABLE_COST_UNKNOWN, INAPPLICABLE_WITH_REASON, or NOT_EVALUATED. Give attack/game model, assumptions, work/memory/oracle budgets and scope of every statement. A label without the requested derivation is not a deliverable.

## 1. One analytical m throughout the actual soundness argument

**Bounded input:** q32/q48/q64, b4, extension budget120, baseline shape512/190/1186/degree7/max_combo2. `all-terms` retains every allowed m. `summary` compares FRI-only and full objectives, minima and probability sums, dominant/full epsilon.

**Decisive task:** Check the same m=23 can be used in AIR, DEEP, FRI query/commit and batching arguments for the q32 instance; give the exact theorem conditions or one failing premise. Explain whether optimizing the whole expression is legitimate without altering the transcript/proof distribution. Check q48/m3 and q64/m3 only after q32 mapping is resolved. Determine whether m_cap1000 is merely computational and whether the upper endpoint satisfies the cited strict eta condition.

**Required output:** A one-page map of component theorem/radius/list-size assumptions and a reproduced numerical row; state separately whether min or a sum belongs at each composition boundary. An internal arithmetic equality is not acceptance of the premise. Do not change the preserved upstream or independent paths.

## 2. Initial PCS random-linear-combination object

**Bounded input:**18 matrices across3 commitments,330 base polynomial columns,524 point-specific reductions, nominal210. Exact baseline inventory is in `pcs-inventory.json`; native/contract powers are recorded individually. C1/C3 provide separate actual shape inputs.

**Decisive task:** Starting from the batching theorem's random linear combination, map its function index and random coefficients onto the native loops. Determine whether extension coefficient grouping, repeated local/next quotients, randomizing codewords and correlated quotient masks permit an alternative basis. Derive the polynomial degree in the shared challenge alpha and the proximity event, not just a count.

**Required output:** Explicit formula whose indices explain either210,330,524 or another derived number; mark why excluded objects are excluded. Address whether a common alpha across points or grouping into extension polynomials satisfies the theorem distribution. Give a counterexample if the nominal interpretation is invalid. Do not mechanically substitute the largest count.

## 3. Bibliographic/theorem identity and ROM/QROM boundary

**Bounded input:** pinned source comments cite2024/1553 as STARK/FRI soundness; checked source index identifies it as *STARK-based Signatures from the RPO Permutation*. BCHKS25 is2025/2055. Transcript uses KeccakPair512/custom challenger, rejection-sampled BabyBear extension challenges and per-site grinding.

**Decisive task:** Resolve exact paper version/title/theorem statements used for n/q and round-by-round soundness. Then name the exact ROM/QROM theorem and losses that would compose this IOP, MMCS and challenger, or explicitly state no applicable accepted reduction is presently provided. g/2 is only a work-credit sensitivity, not that reduction.

**Required output:** Reference correction plus assumptions/losses table. No end-to-end quantum number until missing terms have an explicit accepted model. Show which oracle/attempt budgets are already included before any lifetime subtraction.

## 4. Exact H5/H6 constrained compression, not family-level reassurance

**Bounded input:** p2013265921, alpha7, width32, RF8/RP30, first12/14 feed-forward lanes, exact constants/diagonal and Horizon M4, all R2-H5-complete-v1 role lanes. H6 has only frozen node semantics. Sources2025/954,2026/306,2026/1692 are extracted-text hash-pinned with pin limitations disclosed.

**Decisive task:** First analyze H5 node and H5 note separately. Extend or falsify the supplied one-full-round affine gadget under fixed controls, same scope, and useful-output constraints. Show how width32 and the implementation's different M4 affect2026/306 hypotheses. Distinguish first-round tensor applicability from full attack applicability. For2026/1692, account for three additional initial full rounds absent from its operational demonstrations. Only then compare H6 node d14. Do not extrapolate H6 complete semantics.

**Required output:** Exact polynomial systems for target preimage and two-copy useful collision, satisfying canonical lanes and fixed domains; an explicit skip with residual variable/equation/degree count or a failed condition. If solving cost is evaluated, give success probability, finite-field root extraction, regularity assumptions, memory, omega and quantum versus classical work. If only applicable, return APPLICABLE_COST_UNKNOWN. A ratio/speedup is not a security exponent.

**Bounded experiment escalation:** Start from the supplied real-field one-round witness generator. Attempt at most one additional full round with an explicitly stated fixed field/width/layout/solver and resource cap approved by Main. Retain equations, attempted constraints, solver logs and null result; failure to find a solution is not a proof no solution exists. No public-chain data or funded notes.

## 5. H0 multi-squeeze and H5 chaining/role composition

**Bounded input:** H0 rate4/capacity12/output16 over4 squeezes with exact byte/count/tag/aux framing. H5 public scope/payout/statement chain states, mandatory delimiter, chunk length/index and role controls. Node scope is inherited through leaves.

**Decisive task:** Map the operation-mode-specific attacks to all squeezed/chained outputs, not only first-block CICO. Check cross-role input-family overlap under different control offsets and whether transitive scope binding suffices for first-divergence Merkle reduction. A typed injective encoding does not prove a collision-resistant chain.

**Required output:** Exact game reductions or counterexamples for same-scope binding, cross-role reuse and statement/payout linking. Provide per-role conditional findings; unknown primitive cost does not stop proof-performance measurement.

## 6. Lifetime and privacy, one sheet per game

**Bounded input:** eight game sheets in `threat-games.json`; canonical eight-limb secret entropy≈247.255 bits; random/trace/quotient hiding inventory; synthetic research seeds have no custody use.

**Decisive task:** For each game select an actual target population and query budget or state a symbolic variable. Specifically distinguish unspent commitments without a trapdoor checker from a hypothetical secret-check oracle; useful commitment collisions with distinct nullifiers from arbitrary collisions; live continuation records from historical proof counts; distinguishing advantage from search work. Show that replay/state-machine invariants and lifetime multipliers are not confused with hash bounds.

**Required output:** At most eight game-specific advantage expressions, each with a source theorem or explicit assumption. For privacy, one simulator/rank/entropy argument covering openings and correlated quotient masks, plus whether many-proof adaptive composition and shared transcript preserve it. Configured hiding, random-looking bytes and mutation rejection are not zero-knowledge proofs.

## Exit criteria

- **Research continuation:** executable arithmetic and explicit object mapping with questions exposed; no external acceptance prerequisite for isolated performance measurement.
- **Scoped security acceptance:** reviewer explicitly signs/version-pins the specific games/theorems/instances and lists unresolved exclusions.
- **Exact candidate stop:** useful below-target attack or irreparable relation flaw with witness/reproducer and actual cost assumptions. An uncomputed attack, weak lower bound or missing review is not an exhibited break.
