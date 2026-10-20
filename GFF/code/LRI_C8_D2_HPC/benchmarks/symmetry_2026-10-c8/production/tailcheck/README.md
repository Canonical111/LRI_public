# C8(2) tail check: do the 4,832 "confirmed" L8 graphs have infinite variance? (2026-10-07, revised 2026-10-08)

Question (`LRI_C8_D2_HPC_loop/artifacts/tailq/QUESTION.md`, with the Codex review `codex_reply.md`): C63d's d=3-calibrated
heavy-tail rule confirmed 4,832 L8 graphs of the C8(2) production (`../result/README.md` section 4) as "possible
infinite variance". Is that real, and is C8(2) = 45,990.00 ± 8.22 trustworthy?

**Revision of 2026-10-08.** Codex verified the first version (`artifacts/tailq/QUESTION2.md`, reply `codex_reply2.md`):
"sound with caveats", findings 1-9. This revision addresses them.

| Finding | What changed | Section |
|---|---|---|
| 1 (criterion correct; strict margins) | kept; the strict-inequality note added | 2 |
| 2 (two fixed primes are randomized evidence, not an exact certificate) | rerun with 4 random primes x 2 random points per prime per graph, retries recorded, an aggregate error estimate with its degree/height assumptions; renamed "multi-prime randomized cancellation verification" | 2 |
| 3 (16 orderings are regression evidence) | stated; the nested-limit argument rests on the builder's construction | 2 |
| 4 (coverage complete) | no change needed | 2 |
| 5 (negative controls not auditable; exit status) | 9 archived controls with explicit assertions, including two infinite-variance controls; `tc_cert` and both wrappers exit nonzero on any missing record or failed check | 3 |
| 6 (class intervals, mixed windows) | common window 2^12..2^17 for every graph, 2^19 extensions separate, the graph as the unit, joint replicate resampling per scramble net | 5 |
| 7 (statements too strong; "N^-0.30..-0.32 for every class" false) | per-class Hill exponents given (−0.34 to −0.17); finite-sample wording | 4, 5 |
| 8 (double-lift: 4 tested graphs carry 0.011% of the class) | a targeted nested test of the 16 largest double-lift contributors (51.7% of the class's measured variance) | 6 |
| 9 (SE statements) | 8.22 is the estimated sampling SE; 8.26/8.32/8.97 are sensitivity scenarios; the 1.07/0.88/0.98 sentence corrected; "near Gaussian" descriptive | 7, 8 |

The production and pilot campaign data were only read. Symmetry only (sharedq and amdq). Jobs in section 9: the first
version 10 jobs, 54.84 core-h; this revision 6 jobs, **15.58 core-h** (budget 40).

## 1. Verdict

**Quoted result:**

> We report C8(2) = 45,990.0 ± 8.2, where the uncertainty is the estimated sampling standard error. Boundary analysis,
> supported by a multi-prime randomized cancellation verification of all 24,173 integrated kernels (four random primes in
> [2^61, 2^62) and two random evaluation points per prime per graph; estimated probability of any wrong valuation below
> 10^−53 under the stated assumptions), supports finite second moments at both production rates and bounded weights for
> all L7 and L8 kernels. The 4,832 L8 tail warnings are consistent with bounded, sharply peaked weights. Fresh nested
> sampling supports variance stability in the selected main groups. In the 380 double-lift power L8 graphs (0.058% of
> the measured variance), a targeted test of the 16 largest contributors (52% of that class's measured variance) shows
> rare-peak sampling effects, with per-point variance growing over 2^12..2^19 points in the largest two. The
> variance-inflation calculations are sensitivity scenarios, not error bounds.

In more detail:
- **Boundedness (section 2).** The boundary criterion with the parity lift gives m_G(S) ≥ α_G(S) > ρ α_G(S) at every face
  once the forest sum's cancellations are confirmed. The multi-prime randomized cancellation verification confirms them
  at all 3,959,753 expanded subsets of the 24,173 kernels, with 0 failures, 0 rate-table mismatches, 0 point redraws and
  0 disagreements between the 8 trials. Union-bound error estimate: ≤ 10^−53.3 (assumptions in section 2). Every L7 and
  L8 weight is bounded at both rates; all 24,173 have a finite second moment at both rates. This is randomized
  verification plus the builder-construction argument, not a deterministic characteristic-zero certificate.
- **Controls (section 3).** All 9 archived controls behave as asserted. Dropping a forest term or doubling a numerator
  makes the cancellation fail (ξ ≥ 1). A rate table ×3 gives infinite variance with a finite mean at both rates
  (ξ = 0.583 / 0.630). A table ×2.4 gives finite variance at rate a (ξ = 0.479) and infinite at rate b (ξ = 0.537).
- **Hill warnings (sections 4-5).** These describe finite-sample behaviour consistent with bounded, sharply peaked weights,
  supported principally by the boundary analysis. The k = 16 Hill estimate falls with N in every class. The exponents
  differ by class: −0.34, −0.32 and −0.30 for the controls, confirmed free and confirmed power; −0.27 for the untestable
  power L8 without double-lift subsets; −0.17 and −0.18 for the double-lift graphs. Falling fixed-k Hill estimates
  cannot prove boundedness.
- **Nested-N test (section 5).** The slope of ln N·Var(prefix mean) over the common window 2^12..2^17 (graph = unit,
  joint replicate bootstrap, conditional on the selected panel) is −0.018 [−0.051, +0.030] for confirmed free L8 and
  −0.062 [−0.110, +0.060] for confirmed power L8. A regularly varying tail with ξ = 0.61 would heuristically give +0.22.
  The untestable power L8 without double-lift subsets rise slightly: +0.086 [+0.039, +0.188].
- **Double-lift class (section 6).** Targeted class slope −0.004 [−0.019, +0.164], right-skewed. Per graph the slopes
  run from −0.49 to +0.39. The three largest contributors, extended to 2^19, have slopes +0.07 [−0.08, +0.31],
  +0.16 [+0.05, +0.33] and +0.30 [+0.20, +0.53] over 2^12..2^19. Their per-point variance is not yet resolved, but
  their weights are verified bounded.
- **SE (sections 7-8).** 8.22 is the estimated sampling SE. Inflating the double-lift class's measured variance by
  ×1.32 / ×18.9 / ×45 / ×335 gives 8.22 / 8.26 / 8.32 / 8.97. These are sensitivity scenarios, not bounds. Keep every
  graph in the estimand.

## 2. Analytic criterion and the multi-prime randomized cancellation verification

**The weight.** `src/kernel.hpp` defines the sampler.
- `rates()` builds the rate DP. The tables α_G(S) are multiplied by the campaign scale ρ_c (ρ_a = 0.8, ρ_b = 0.9).
- `sample()` picks an ordered (Hepp) sector, with the top edge at x = 1, and draws each successive gap
  z_i = e^{l_i} = u_i^{1/(ρ α(S_i))}. Here S_i is the set of edges below gap i.
- `evaluate()` returns t = v_0 · jac. In a sector this is

  t = Z_c · K_G(x) · Π_i z_i^{|S_i|/2 − ρ α_G(S_i)},   K_G = (Σ_e x_e)^−1 Σ_F N_F / U_F.

The forest kernel K_G is **rational** in x (`gen/build_free.cpp`, `gen/build_power.cpp`):
- U_F sums the cotree monomials that are tight on the forest's subgraphs;
- N_F is a signed sum of root edges;
- the measure is x_e^{1/2} per edge.

**Notation.**
- m_G(S) = |S|/2 + ν_S(K_G) is the exact leading exponent when x_e → λ x_e for e ∈ S, after all forest cancellations.
- Near that face t ~ z^{m − ρα}, with z = u^{1/(ρα)}, so P(t > x) ~ x^{−ρα/(ρα − m)}.

**Criterion** (Codex's; finding 1 confirms the implementation):
- bounded weight ⇔ m_G(S) ≥ ρ_c α_G(S) at every S;
- finite second moment ⇔ 2 m_G(S) > ρ_c α_G(S);
- the asymptotic tail index of the weight is ξ_c = max_S (1 − m_G(S)/(ρ_c α_G(S)))^+.

**Why it is decidable at d = 2.**
1. Each forest term has exponent |S|/2 + a_F(S) − h_F(S). Here a_F = 1 iff the numerator support lies in S, and h_F is
   the smallest |m ∩ S| over U_F's monomials. The builder stores α_G(S) = max(raw(S), 1 or 2)/2, with raw/2 the term
   minimum.
2. A sum cannot have a lower exponent than its terms. So m_G(S) ≥ raw(S)/2 = α_G(S) wherever raw > 0.
3. K_G is rational, so m_G(S) ∈ |S|/2 + ℤ (the parity lift).
4. Where raw ≤ 0 ("clamped": the forest subtraction must cancel), m_G(S) > 0 therefore already implies
   m_G(S) ≥ α_G(S) (1/2 for odd |S|, 1 for even |S|).
5. Hence for a convergent kernel with the builder's own rate table, m_G ≥ α_G > ρ α_G at every face. The weight is
   then bounded at **both** rates, with z-exponent at least (1 − ρ) α_G > 0.
6. Infinite variance with a finite mean is impossible for this sampler with the builder's tables. A deficient face would
   need m ≤ ρα/2 < α, hence m ≤ 0, which is a divergent integral (ξ ≥ 1). With other rate tables it is possible, and the
   rate-scaled controls of section 3 show the tool detects it.
7. With the builder's tables the campaigns cannot differ in finiteness.

**Nested limits (multi-scale).** Each U_F is the basis generating function of a matroid: a face of the cographic base
polytope, cut by tight rank constraints on a laminar family. So in any ordering a greedy monomial minimizes every suffix
count at once, and U_F/lead is a positive polynomial ≥ c > 0 on the closed sector box. Then:
- each term is z^{v_F} times a function analytic on the box;
- the sum's single-coordinate valuations w_i bound every monomial of its expansion;
- so |K_G| ≤ C Π z_i^{w_i} on each sector.

Codex (finding 3) agrees that this covers nested limits. The argument rests on the **builders' construction**
(`gen/build_free.cpp`, `gen/build_power.cpp`). The program's check of the greedy property on 16 random orderings per
term (19.3 million checks, 0 failures) is regression evidence, not an exhaustive structural certificate.

**The verification** (`scripts/tc_cert.cpp` v2, sharedq job 571402, 15:29, every member checked against
`inputs/inventory.json`'s sha256). For each graph it:
1. recomputes raw(S) for all 2^E − 2 subsets in exact integer arithmetic, as the builder does, and compares the stored
   rate table with it;
2. at every clamped subset expands Σ_F N_F/U_F in λ and finds the lowest order with a nonzero Laurent coefficient. The
   arithmetic is exact modulo **4 primes drawn uniformly among the primes in [2^61, 2^62)** (rejection sampling of odd
   candidates, deterministic Miller-Rabin; the primes are recorded per graph), at **2 random points per prime** (each
   edge variable uniform in [1, p−1]). The reported order is the minimum over the 8 trials;
3. checks that every coefficient below the first order with |S|/2 + ν > 0 vanishes (m_G(S) ≥ α_G(S)), and records
   whether m = α exactly ("tight") or more;
4. checks the greedy property on 16 random orderings.

Randomness: the master seed 8738015587015592808, registered in the seed logs (section 5), with a per-graph stream.

**Error direction** (Codex, finding 2):
- a nonzero coefficient modulo p, with nonzero denominators, proves nonvanishing;
- an error can only be a false zero, which overestimates the valuation;
- a point at which a leading denominator coefficient c_h vanishes mod p is redrawn, and the graph pass is redone
  (`degenerate_retries`, 0 in this run).

**Error estimate.** For subset S, order j ≤ jtop and the common denominator D = Π_G c_{h_G}^{E_G} (E_G = jtop + h_G + 1
over the included terms G), the coefficient times D is an integer polynomial Q in the E edge variables, with
- deg Q ≤ d_S = L Σ_G E_G (largest here 6,720);
- log2 ‖Q‖_∞ ≤ B_S = 1 + log2 Σ_G s_G + Σ_G E_G log2(2 b_G) (largest 8,536 bits), where s_G is the numerator's
  coefficient sum and b_G the number of denominator monomials; the inverse-series polynomials obey ‖P_n‖_1 ≤ (2b)^n.

If Q ≠ 0 over ℤ, then:
- at most ⌈B_S/61⌉ primes ≥ 2^61 divide all its coefficients, so a uniform prime is bad with probability
  β_S ≤ ⌈B_S/61⌉ / (3.8·10^16 − 4). There are at least 3.8·10^16 primes in [2^61, 2^62) (Dusart's bounds);
- at a good prime, a uniform point, conditioned on no redraw anywhere in the graph's pass (probability ≥ 1 − γ, with
  γ ≤ n_S T L / (2^61 − 2)), is a zero with probability δ_S ≤ d_S / ((2^61 − 2)(1 − γ)) (Schwartz-Zippel);
- the true lowest coefficient is therefore missed with probability P_S ≤ (β_S + δ_S²)^4.

Over every expanded subset of every graph, max_S P_S ≤ 10^−57.7, and the union bound gives
**Σ P_S ≤ 10^−53.3** (`results/cert_summary.json`, `evidence/tc2cert.571402.0/cert_check.json`).

The assumptions:
- the generator's draws (mt19937_64 seeded by splitmix64 from the registered master seed) behave as independent
  uniform draws, made after the payloads were fixed;
- the program computes the stated Laurent coefficients. The controls of section 3 and the agreement with v1 support
  this.

**It is a multi-prime randomized cancellation verification, not an exact (deterministic, characteristic-zero)
certificate.**

**Flags.**
- `bounded`: every check passed and min_S (m_low − ρα) > 0 at both rates.
- `certified` (finite second moment at both rates): every check passed and min_S (2 m_low − ρα) > 0 at both rates.
- m_low is a lower bound of m_G(S): exact where a coefficient was found nonzero, a bound where every computed
  coefficient vanished.
- The inequalities are **strict**. That is conservative, since boundedness also holds at equality. The flags are
  sufficient conditions, not an "iff" classifier (finding 1).

**Exit status.**
- `tc_cert` exits 0 only if every listed record exists and is certified, 3 if a record has an error or a failed
  check, and 4 on a missing record or a wrong `--expect` count.
- `scripts/tc_cert.slurm` then runs `scripts/tc_cert_check.py`. That fails unless tc_cert exited 0 and the records
  are exactly the 24,173 members, with none missing, extra or duplicated. It also requires that every record is
  certified with no failed check, that 4 distinct primes per graph pass a Python re-test, that every L7/L8 record is
  bounded with a builder table, that the legacy tables are exactly the free L ≤ 6 ones, and that the union bound is
  < 10^−30.
- The job writes `STATUS` PASSED or FAILED and exits nonzero on failure.

| Sector L | Graphs | Finite 2nd moment (both rates) | Bounded (both rates) | Clamped subsets (tight / higher) | Double-lift graphs | Rate-table mismatches, cancellation failures, greedy failures, redraws, trial disagreements |
|---|---:|---:|---:|---|---:|---|
| free L8 | 16,064 | **16,064** | **16,064** | 809,644 (269,406 / 540,238) | 0 | 0, 0, 0 of 13.9M, 0, 0 |
| power L8 | 4,336 | **4,336** | **4,336** | 1,243,629 (292,784 / 950,845) | 380 | 0, 0, 0 of 3.4M, 0, 0 |
| free L7 | 2,441 | 2,441 | 2,441 | 81,632 | 0 | 0, 0, 0, 0, 0 |
| power L7 | 709 | 709 | 709 | 116,351 | 71 | 0, 0, 0, 0, 0 |
| free L3–L6 (legacy rates, every subset expanded) | 492 | 492 | 475 | 8,925 | 0 | (legacy), 0, 0, 0, 0 |
| power L3–L6 | 131 | 131 | 131 | 9,321 | 10 | 0, 0, 0, 0, 0 |

- **Minimum margins over all L7 and L8 kernels.** m − ρα ≥ 0.1 (rate a) and 0.05 (rate b); 2m − ρα ≥ 0.6 and 0.55;
  the analytic ξ is 0 at both rates. These minima sit at odd subsets with α = 1/2, tight. Finding 1 checked them.
- **The 17 legacy free L5/L6 kernels** have unbounded but finite-variance weights: analytic ξ ≤ 0.25 at rate a and
  ≤ 0.33 at rate b.
- **Agreement with v1.** All 25 shared fields of all 24,173 records equal v1's (job 571351: two fixed primes, one point
  each; now `scripts/v1/`, `evidence/tccert.571351.0/`, `results/v1/cert_summary.json`): the tight/higher counts,
  margins, ξ bounds and flags. The 96,692 primes pass a Python re-test.
- **Coverage** (finding 4): the 24,173 records are the 24,173 inventory members. L8 holds 16,064 free and 4,336 power
  kernels, including every confirmed and untestable graph. The shift branch is algebraically neutral.
- **The structure behind the confirmations.** The production ξ̂ ranks the free L8 graphs by their number of clamped
  subsets (Spearman 0.96) and of forest terms (0.95). Confirmed free graphs have a median of 128 terms and 127 clamped
  subsets; cleared ones have 16 and 15. The peaks are cancellation peaks of large forest sums: bounded, but with a large
  bound C (the sector constant).

Files:
- `evidence/tc2cert.571402.0/`: `cert.jsonl.gz` (per graph, primes included), `members.txt.gz`, `cert_check.json`
  and `.txt`, `STATUS`, `seed.txt`, `inputs.sha256`, `time_cert.txt`;
- the uncompressed files stay on BeeGFS, with their sha256 in `evidence/large_files_followup.sha256`;
- `results/cert_summary.json`.

## 3. Negative and positive controls (finding 5)

`scripts/tc_negctl.py` writes 9 control payloads from free L8 G26268 (the production's largest variance contributor)
and power L8 G26451 (the largest double-lift contributor). Both sources are checked against `inventory.json`'s sha256,
and each mutation edits only the named tokens. `tc_cert` (the same build and seed) runs them, and `tc_negctl.py check`
asserts each expected outcome. Sharedq job 571403 ran it all, and `scripts/tc_negctl.slurm` fails unless tc_cert exits
3 and every assertion holds.

| Control | Mutation (rates mode) | Assertion | Outcome |
|---|---|---|---|
| pos_free (G26268) | none (builder) | certified, bounded, 0 failures, 0 mismatches | **pass**: 127 clamped (25 tight / 102 higher), margins 0.1 / 0.05 |
| pos_power (G26451) | none (builder) | certified, bounded, 0 failures, double-lift | **pass**: 703 clamped, max orders cancelled 2 |
| pos_given_free | none, table taken as given (all 65,534 subsets expanded) | certified, bounded, 0 failures | **pass** |
| drop_term_free | forest term 0 removed | failures > 0, not certified, not bounded, ξ ≥ 1 at both rates | **pass**: 13 failures, ξ = 1 / 1 |
| drop_term_power | forest term 0 removed | the same | **pass**: 232 failures, ξ = 2.25 / 2.11 |
| double_num_free | numerator of term 0 ×2 | failures > 0, 0 rate mismatches, not certified, ξ ≥ 1 | **pass**: 13 failures, ξ = 1 / 1 |
| rate_x3_free | every stored rate ×3, given | **infinite variance, finite mean, both rates**: 0 failures, 2m − ρα < 0 at a and b, 1/2 ≤ ξ < 1 | **pass**: min 2m − ρα = −1.4 / −2.45, ξ = 0.583 / 0.630 |
| rate_x2.4_free | every stored rate ×2.4, given | finite at a, **infinite at b**: 2m − ρα > 0 at a and < 0 at b, ξ_a < 1/2 ≤ ξ_b < 1 | **pass**: 0.04 / −0.56, ξ = 0.479 / 0.537 |
| rate_tamper_free | stored rate of {e0, e1} + 1/2 (builder) | exactly 1 rate mismatch, not certified | **pass** |

tc_cert exited 3 (6 records not certified, none with an error), as asserted.

Files are in `evidence/tc2neg.571403.0/`:
- `commands.txt` (the three commands);
- `negctl_inputs.json` (each mutation, the payload sha256 and the source sha256);
- `payloads/*.txt.gz`, compressed here with `gzip -n`; the sha256 of the uncompressed payloads is in `payloads.sha256`,
  and they equal `negctl_inputs.json`'s;
- `negctl_list.txt`, tc_cert's `cert.jsonl`, `cert.exit`, `negctl_check.json` and `.txt`, `STATUS`.

The v1 README's "127 / 23 failures" for G26268 used an unarchived mutation; this archived set replaces it.

## 4. Reconciling ξ̂ ≈ 0.61 with the ×1.035 variance growth (existing data)

**Corrected numbers.**
- The confirmed free graphs ran 32,768–131,072 points per replicate in production, not 524,288. The point ratio
  over the pilot is 8 (median), and 8–32 overall (`../result/prres.571287.0/analysis.json`, `threat`).
- ξ = 0.61 therefore predicts ×8^0.22 = **1.58** for the typical empirical growth, not ×2.9. This is a heuristic: under
  an infinite-variance model the population variance is infinite.
- Measured: pooled ×1.035. With the graphs cross-selected on the other campaign: ×1.030 / ×0.971 (heavy) against
  ×0.870 / ×0.880 (light).

| Evidence (L8; `results/ab_hill.json`, `evidence/tcmerged.571352.0/merged_tails.json`) | Measured | Regularly varying tail, ξ = 0.61 | Bounded, peaked weight |
|---|---|---|---|
| ξ̂(production)/ξ̂(pilot), confirmed free, classified on a and measured on b | **0.537** at 8×, **0.432** at 16× (power: 0.466, 0.335); no graph rose | 1 for an exact iid Pareto tail | falls with N |
| Models at 8× / 16× / 32× (k = 16) | | Pareto 1.00; log-type 0.73 / 0.67 / 0.62; lognormal 0.85 / 0.82 / 0.78 | (N1/N2)^{1/b}, b ≈ 3.3 |
| Hill plot at production (confirmed free, 8×) | ξ̂_16 0.63, ξ̂_8 0.49, ξ̂_4 0.39 | flat in k | decreasing with k (concave log-quantile) |
| Block-maximum dispersion ξ_sd = sd(ln max)·√6/π over 128 replicates | **0.27** | 0.61 (Fréchet) | small |
| Growth of the largest of N per 8× (confirmed free) | ×8^0.43 | ×8^0.61 | saturating |
| Matched a/b at equal N (free confirmed, 4,210 graphs) | ξ̂_b − ξ̂_a = **−0.0030 ± 0.0003** | rate-driven face: +0.039 (ξ_b = 1 − (8/9)(1 − ξ_a)) | ≈ 0, slightly lighter at b |
| L7 control (no threshold; C7(2) validated) | Hill 0.67 → 0.175 at 64× | | the same behaviour |

What the Hill estimate meets here, item by item:
- **Tiny k/N.** For an exact Pareto tail, k = 16 is unbiased. A bounded weight has no regularly varying tail, and
  fixed-k Hill then measures the local slope of the log-quantile function at level 16/N, which falls with N.
- **RQMC.** Both comparisons (pilot/production and the fresh nested prefixes) are RQMC samples. Their agreement
  therefore does not separate RQMC effects from the tail shape (finding 7). Replicate-based variance estimation is
  unaffected, because the scrambles are independent.
- **Selection.** Selecting on production ξ̂ inflates it, but the cross-selected medians are 0.626 against 0.629: the a/b
  correlation is 0.99, because both campaigns sample the same peaks.
- **The d = 3 calibration.**
  - `tail_calib.py` calibrates on Pareto, corner, lognormal and sparse families (iid, plus four Sobol toys) at R = 8.
  - It has **no bounded-peaked family**, so its false-confirmation rate for this situation was never measured.
  - At d = 2 the parity lift (section 2) rules out the face mechanism (a = r/(r − m)) that the rule was built to catch.

None of this proves boundedness. Falling fixed-k Hill estimates and the absent rate response are finite-sample behaviour
**consistent with bounded, sharply peaked weights**. The support comes principally from the boundary analysis
(finding 7).

**Codex's "cheapest test" (nested prefixes from the production checkpoints) cannot be done.** In the production, every
L8 graph-replicate is a single task: the chunk is the whole replicate, `graph_costs.csv` gives one row per replicate
for 40,784 of the 40,800 L8 graph-campaigns, and only 16 have 2 rows. So no prefix below the full N exists on disk.

## 5. Fresh nested-N test

**Design** (`scripts/tc_choose.py`, from the production per-graph data of `evidence/tcselect.571353.0/`). 48 graphs,
following Codex's staged design:

| Group | Graphs | How chosen |
|---|---:|---|
| confirmed free L8 | 16 | the 8 largest variance contributors (G26268, G24346, …) and 8 spanning ξ̂ |
| confirmed power L8 | 8 | 4 by variance, 4 by ξ̂ |
| untestable power L8 | 16 | 8 by variance; 6 stratified by ξ̂ tercile; G12233 and G12210 (extreme kurtosis) |
| controls | 8 | 2 never-screened free, 2 cleared free, 2 cleared power, 2 free primitives |

Run settings:
- each graph ran in both campaigns (rate .8 with the 52-bit net, rate .9 with the 60-bit net), with 32 independent
  scrambles each;
- each replicate was cut into 4,096-point rows up to N = 2^17, so every prefix 2^12 … 2^17 is an exact sub-estimate of
  the same scramble; 8 graphs went to 2^19 (`scripts/tc_nested_graphs.txt`, `tc_nested_classes.txt`);
- the worker was called exactly as production calls it (`scripts/tc_nested.py`): the gated dd+mp256 executable
  `a46f3060…` of export `ba68f401e46e` (sha256 checked), `production.derive_seeds` / `make_net` for the nets and digital
  shifts, layout 0, compensated sums, members checked against their sha256;
- **fresh base seed 7599440640766719655**, registered in symmetry's log by job 571358 (121 seeds then), in the mirror
  `designs/forbidden_seeds.json` and in `stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`;
- run directory `<SCRATCH>/c8-d2/tailcheck-nested-20261007-ba68f401e46e`. Its 96 native outputs stay on
  BeeGFS, with their sha256 in `evidence/tcnested.571385.0/native_outputs.sha256`; job 571406 re-verified them.

**Statistics** (revised for findings 6 and 7; `scripts/tc_nested_extract.py`, `scripts/tc_nested_joint.py`, sharedq job
571406, `evidence/tc2an.571406.0/`):
- σ²_gc(N) = N·Var_r(prefix mean). The C8 projection y = J8 · (m0, m1) is computed with the vendored assembly's
  Jacobian at the result's means, and reproduces the production's per-graph v to 4.4e-16. For L8 the two jets of a
  graph are proportional (m1/m0 = 1/6, or 0, for every replicate), so this projection and the earlier m0 + m1 give
  identical slopes and ratios.
- **Common window W0 = 2^12..2^17 for every graph.** The 2^19 extensions are reported separately (W1 = 2^12..2^19 and
  the segment 2^17..2^19). The slope is that of ln σ² on ln N.
- **The unit is the graph**: b_g is the mean of its two campaigns' slopes, and the class statistic is the mean of b_g
  over the class's graphs.
- Hill: the class curve is the median over graphs of the two-rate mean Hill estimate, and the exponent is its log-log
  slope over W0.
- **Uncertainty.** Each of 2,000 bootstrap draws resamples **one vector of 32 replicate indices per scramble net**
  (run, campaign, sector) and applies it to every graph and every prefix of that net, because all graphs of a net share
  its scrambles and the prefixes are nested. The 95% intervals are percentile intervals. They measure scramble-sampling
  uncertainty **conditional on the selected panel**. They are not population intervals: most graphs were deliberately
  selected.
- F = σ²(2^17)/σ²(N_prod) compares two prefix sizes of the **same fresh run**. Φ = σ²_fresh(N_prod)/σ²_production(N_prod)
  compares the fresh run with the production's 128-replicate estimate at the production's own N. Both are weighted by
  the graph-campaign's production share of Var(C8). The production replicates are resampled per production group.

**Common-window results** (`plots/nested_joint.png`):

| Class | Graphs (graph-campaigns) | Slope of σ², W0 | Per-graph slope min / median / max | Hill 2^12 → 2^17 (median) | Hill exponent, W0 | F (within run) | Φ (fresh / production at N_prod) | Production share of Var(C8) |
|---|---|---:|---|---|---:|---:|---:|---:|
| confirmed free L8 | 16 (32) | **−0.018** [−0.051, +0.030] | −0.11 / −0.02 / +0.11 | 1.21 → 0.41 | −0.315 [−0.325, −0.306] | 1.07 [0.96, 1.35] | 0.84 [0.71, 0.97] | 6.28e-3 |
| confirmed power L8 | 8 (16) | **−0.062** [−0.110, +0.060] | −0.24 / −0.04 / +0.06 | 1.99 → 0.71 | −0.303 [−0.314, −0.291] | 0.88 [0.76, 1.19] | 0.99 [0.77, 1.25] | 1.46e-3 |
| controls | 8 (16) | −0.019 [−0.077, +0.041] | −0.11 / −0.03 / +0.16 | 0.90 → 0.28 | −0.340 [−0.353, −0.324] | 0.91 [0.79, 1.09] | 0.96 [0.75, 1.19] | 1.66e-3 |
| untestable power L8, no double-lift | 12 (24) | +0.086 [+0.039, +0.188] | −0.15 / +0.04 / +0.39 | 1.88 → 0.74 | −0.267 [−0.278, −0.254] | 0.98 [0.88, 1.81] | 1.11 [0.81, 1.74] | 2.93e-3 |
| untestable power L8, double-lift (earlier sample) | 4 (8) | +0.779 [+0.477, +1.158] | +0.09 / +0.73 / +1.57 | 2.44 → 1.34 | −0.168 [−0.183, −0.149] | 18.9 [2.1, 322] | 3.75 [0.41, 21.4] | 6.4e-8 |
| **double-lift power L8, targeted** (section 6) | 16 (32) | **−0.004** [−0.019, +0.164] | −0.49 / +0.01 / +0.39 | 2.02 → 1.08 | −0.178 [−0.187, −0.168] | 1.32 [1.25, 2.80] | 0.92 [0.75, 1.74] | 2.97e-4 |

**2^19 extensions** (graph = two-campaign mean):

| Graph | Class | Slope W0 | Slope W1 (2^12..2^19) | Slope 2^17..2^19 | Hill 2^12 → 2^17 → 2^19 |
|---|---|---:|---:|---:|---|
| free G11388 (highest ξ̂ among the 16) | confirmed free | +0.060 [−0.125, +0.396] | +0.077 [−0.050, +0.289] | +0.222 [−0.130, +0.510] | 1.63 → 0.84 → 0.58 |
| free G24345 | confirmed free | −0.083 [−0.226, +0.103] | −0.043 [−0.159, +0.115] | −0.069 [−0.294, +0.139] | 1.19 → 0.44 → 0.30 |
| free G24346 | confirmed free | −0.029 [−0.181, +0.115] | −0.110 [−0.222, −0.007] | −0.306 [−0.673, +0.072] | 1.16 → 0.44 → 0.30 |
| free G26268 | confirmed free | −0.114 [−0.261, +0.053] | −0.048 [−0.170, +0.073] | +0.070 [−0.281, +0.431] | 1.21 → 0.38 → 0.25 |
| power G25008 | confirmed power | −0.016 [−0.183, +0.199] | −0.003 [−0.132, +0.151] | +0.014 [−0.287, +0.307] | 2.06 → 0.69 → 0.40 |
| power G26459 | confirmed power | +0.062 [−0.137, +0.353] | +0.009 [−0.097, +0.185] | −0.061 [−0.311, +0.211] | 1.97 → 0.74 → 0.46 |
| power G24472 | untestable, no double-lift | +0.109 [−0.058, +0.402] | −0.003 [−0.152, +0.224] | −0.237 [−0.538, +0.063] | 1.90 → 0.81 → 0.54 |
| power G12233 | untestable, double-lift | +1.573 [+0.786, +2.270] | +1.035 [+0.698, +1.497] | +0.289 [−0.017, +1.155] | 3.15 → 1.72 → 1.35 |
| power G26451 | double-lift, targeted | +0.144 [−0.045, +0.421] | **+0.164** [+0.052, +0.332] | +0.091 [−0.278, +0.477] | 2.34 → 1.41 → 0.86 |
| power G26453 | double-lift, targeted | +0.390 [+0.249, +0.741] | **+0.299** [+0.204, +0.528] | +0.217 [−0.093, +0.502] | 2.02 → 1.26 → 0.79 |
| power G24647 | double-lift, targeted | +0.263 [−0.026, +0.617] | +0.073 [−0.081, +0.309] | −0.437 [−0.740, −0.131] | 1.77 → 1.04 → 0.70 |

Reading:
- **Confirmed and control classes.** Common-window slopes are near zero, with intervals that contain 0. The four
  confirmed free and two confirmed power extensions stay flat to 2^19, and their Hill estimates fall to 0.25–0.58.
- **The heuristic.** A regularly varying tail with ξ = 0.61 would heuristically give +0.22. Finite variance does not
  imply a nonpositive slope over every finite range (scrambled-net results are asymptotic), and 2ξ − 1 is only a
  heuristic for typical growth under an infinite-variance model (finding 7).
- **Untestable power L8 without double-lift subsets.** These rise slightly over W0, +0.086 [+0.039, +0.188], a factor
  of about 1.35 over 32× in N. At the production's own N, the fresh variance agrees with the production's
  (Φ = 1.11 [0.81, 1.74]), and their 2^19 extension (G24472) is flat.
- **Hill exponents.** The class Hill exponents are **−0.34 (controls), −0.32 (confirmed free), −0.30 (confirmed power),
  −0.27 (untestable, no double-lift) and −0.17 / −0.18 (double-lift)**. The first version's "N^−0.30…−0.32 for every
  class" was wrong for the last three (finding 7).

**Superseded numbers.** The first version's class intervals (`results/nested_split.json`, `plots/nested.png`) were the
mean ± 1.96 × the between-graph-campaign SE, over fits that mixed 2^17 and 2^19 endpoints. They were confirmed free
−0.015 [−0.045, +0.015], confirmed power −0.067 [−0.164, +0.030], controls −0.019, untestable no-double-lift +0.076
[−0.017, +0.170] and double-lift +0.645 [+0.143, +1.147]. They are kept for the record only; the tables above replace
them.

## 6. Double-lift power L8 graphs: targeted nested test (finding 8)

**The class.** 380 power L8 graphs have a clamped subset that needs two orders of cancellation (raw ≤ −2). All are
untestable (< 32,768 points). Their measured variance is **5.753e-4 of Var(C8)**: the sum over their graph-campaigns of
the production's per-graph replicate variance contribution, divided by Var(C8). This is an estimate, not an upper bound
on the class's true variance. The first version's 4 graphs carry 6.4e-8 of Var(C8), **0.011% of the class's measured
variance**, so their ×18.9 / ×45 factors were never a validated class correction.

**Selection** (deterministic, `scripts/tc_dl_graphs.txt`, `tc_dl_classes.txt`; from `evidence/tcselect.571353.0/` and
the v2 records):
- the **16 double-lift graphs with the largest production variance share** (both campaigns summed): G26451, G26453,
  G24647, G25095, G10083, G25087, G26452, G23183, G14816, G25088, G8879, G20266, G10081, G10085, G20312 and G8762;
- they carry **2.973e-4 of Var(C8), 51.7% of the class's measured variance**. With the earlier 4, the tested graphs
  cover **51.7%** of it;
- none was in the earlier 48-graph sample;
- their production point counts are 8,192 (some 16,384), with production replicate kurtosis 1.9–77.

**Run.**
- Both campaigns, 32 scrambles each, nested prefixes 2^12..2^17; the three largest (G26451, G26453, G24647) went to
  2^19.
- The same `tc_nested.py` (sha256 identical to the first run's), the production's gated dd+mp256 executable
  `a46f3060…` of export `ba68f401e46e`, and the production's `derive_seeds` / `make_net`.
- **Fresh base seed 7724198544039388897.** Setup job 571401 checked it free and registered it in symmetry's log
  (123 seeds, sha256 `da4155ac…`), together with the verification's seed 8738015587015592808. Both are in the mirror
  `designs/forbidden_seeds.json` (123) and in `stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`.
- amdq jobs 571404 (campaign a, <NODE>) and 571405 (b, <NODE>), both surveyed EPYC 7543 production-pool nodes: 32 native
  calls, all exit 0, 14.34 busy core-h.
- Run directory `<SCRATCH>/c8-d2/tailcheck-dl-20261008-ba68f401e46e`. The native outputs stay on BeeGFS,
  with their sha256 in `evidence/tc2an.571406.0/native_outputs_dl.sha256`.

**Results** (`results/dl_targeted.json`; section 5 tables; `plots/nested_joint.png`, right panel):
- **Class slope (W0) −0.004 [−0.019, +0.164].** The interval is right-skewed: a draw that duplicates the few
  spike-carrying replicates raises σ² at large N. Per graph (two-rate mean) the slopes run from −0.49 to +0.39, and 8
  of 16 are positive.
- **The three largest extend to 2^19 with W1 slopes +0.164 [+0.052, +0.332] (G26451), +0.299 [+0.204, +0.528] (G26453)
  and +0.073 [−0.081, +0.309] (G24647).** The 2^17..2^19 segment of G24647 falls (−0.44 [−0.74, −0.13]). The other two
  are still undetermined there.
- **The spikes.** At 2^12 the largest single point holds 90–99.8% of the replicate's Σ|t| (largest over replicates).
  At 2^17 it holds 23–72%. The Hill estimate falls from 2.0 to 1.1 (2^17) and to 0.70–0.86 at 2^19, an exponent of
  −0.18.
- **F (within run, 2^17 over N_prod) = 1.32 [1.25, 2.80].** The per-point variance at 16× the production's N is higher
  than at the production's N. This is a pre-asymptotic, unresolved-peak effect, permitted for bounded weights.
- **Φ (fresh over production at N_prod) = 0.92 [0.75, 1.74]** (per graph-campaign 0.21–4.98). These graphs were
  selected **for large production variance**, so regression to the mean biases Φ low. It is consistent with the
  production estimates but is not an unbiased test of their underestimation. The earlier sample's 4 graphs, selected
  for extreme kurtosis and ξ̂ and not for variance, give Φ = 3.75 [0.41, 21.4] at 6.4e-8 of Var(C8).
- **Reading.** The double-lift weights are verified bounded (section 2), but their rare peaks are not resolved at the
  production's 8,192–16,384 points per replicate, nor fully at 2^19 for the two largest. Their replicate-based variance
  estimates are the least converged of the batch. With 0.058% of the measured variance, they cannot move the SE
  materially in any measured scenario (section 8).

## 7. The final sum at the replicate level

`evidence/tcrep.571375.0/replicate_c8.json` holds the C8-projected replicate values summed over every graph group,
index by index. This is the check the pooled per-graph kurtosis does not make.

| Quantity | Value | Gaussian reference (R = 128) |
|---|---|---|
| Final z = (a + b)/2: SE from its spread | 7.856 (assembly 8.217, which sums group variances; ratio 0.96, inside the ±6% sampling error) | |
| Excess kurtosis | **0.779** | median −0.103, **q95 0.712** |
| Skewness | −0.03 | |
| Shapiro p | 0.34 | |
| Median-of-means − mean | +1.0 SE | |
| Campaign a | kurtosis 0.92; one replicate at 3.87σ (p ≈ 0.014 for the largest of 128) | |
| Campaign a without that replicate | kurtosis −0.29, SE 11.6 instead of 12.3 | |
| Campaign b | kurtosis −0.45 | |
| Confirmed free L8 part | kurtosis −0.11 | |
| Untestable power L8 part | kurtosis −0.56 | |

"Near Gaussian" is descriptive only (finding 9). The final sum's excess kurtosis, 0.779, slightly exceeds the Gaussian
95th percentile, 0.712, mostly through the campaign-a replicate at 3.87σ. That replicate's deviation is spread over
independent strata: free L8 +2.3 sd units, mostly non-confirmed graphs; free L7 +0.7; power L8 +0.4; the confirmed free
part only +0.7. It is not a single spike.

## 8. Conclusion on the SE, wording and actions

- **C8(2) = 45,990.0 ± 8.2, the estimated sampling SE (8.217).**
  - The assembly uses the replicate covariance of the graph-summed replicate vectors. The final sum's own replicate
    spread gives 7.86.
  - The a/b agreement (0.44σ), the lower-order pulls and the pilot (1.73σ) support the scale.
  - The SE is an estimate, not validated coverage or a bound.
  - The boundary analysis with the randomized verification supports a finite population variance, so the replicate
    SE estimates a finite quantity. A robust replacement (median-of-means, truncation) is not needed; it agrees within
    1 SE anyway.
- **Stability ratios.** Within the fresh nested run, the per-point variance at 2^17 over that at each graph's
  production point count (share-weighted) is 1.07 / 0.88 / 0.98 for the confirmed free / confirmed power / untestable
  non-double-lift graphs. These compare two sizes **within the fresh run**. They support stability over those sizes,
  not a statement that the production variance is not underestimated (finding 9).
  - The direct comparison with the production at its own N is Φ = 0.84 [0.71, 0.97], 0.99 [0.77, 1.25] and
    1.11 [0.81, 1.74].
  - Selection on large production variance biases Φ low for the variance-selected graphs.
- **Sensitivity scenarios** (not bounds; `results/dl_targeted.json`): SE(f) = 8.217 · √(1 + Σ (f − 1) · share).

  | Scenario | SE |
  |---|---:|
  | double-lift class (5.753e-4 of Var(C8)) ×1.32, the targeted within-run F | 8.218 |
  | double-lift class ×2.80 (upper end of that F interval) | 8.221 |
  | double-lift class ×1.74 (upper end of the targeted Φ interval) | 8.219 |
  | double-lift class ×18.9 (the earlier 4-graph sample's share-weighted F) | 8.26 |
  | double-lift class ×45 (the earlier sample's mean F) | 8.32 |
  | double-lift class ×335 (the largest single graph-campaign F of the earlier sample, applied to all) | 8.97 |
  | double-lift class ×45 and the other 3,594 untestable power L8 graphs (8.95e-2 of Var(C8)) ×2 | 8.68 |

  None changes the a/b (0.44σ), lower-order or pilot checks.
- **Wording to quote:** section 1. Not "possible infinite variance"; not "exact certificate"; not "nested-N confirms
  finite variance"; not "worst-case SE". Keep every graph in the estimand.
- **Actions.**
  - (i) Record the rule's outcome as a d = 2 false confirmation (bounded peaks), with this verification as the
    disposition. No production rerun is needed.
  - (ii) Offer `scripts/tc_cert.cpp` to C63d. The same valuation check at d = 3 (exponents in p4/4 + ℤ) would address
    its double-lift power-L7 question.
  - (iii) Change the package rule: the fixed-k Hill rule should not label "possible infinite variance" without an N-trend
    check.
  - (iv) If more precision is ever bought, give the 380 double-lift power L8 graphs more points. Their replicate
    estimates are the least converged.
  - (v) For a deterministic statement, the cancellations could be certified in characteristic zero: exact rational
    reconstruction, or a height bound with enough primes. This was not done.

## 9. Jobs and core-hours (`evidence/sacct.txt`, `evidence/sacct_followup.txt`; Intel sharedq = AllocCPUS/2 physical cores, AMD = 64)

**First version (2026-10-07):**

| Job | Name | Partition | Elapsed | Core-h | Role |
|---|---|---|---|---:|---|
| 571351 | c8d2-tccert | sharedq (<NODE>) | 16:03 | 1.07 | v1 check, two fixed primes (superseded by 571402) |
| 571352 | c8d2-tcmerged | sharedq | 2:01 | 0.07 | pilot-to-production tail growth (merged tables) |
| 571353 | c8d2-tcselect | sharedq | 3:08 | 0.10 | per-graph data for the sample |
| 571358 | c8d2-tcnsetup | sharedq | 0:10 | 0.003 | seed registration, nets, members |
| 571362 | c8d2-tcnest-a | amdq (<NODE>) | 14:02 | 14.97 | nested runs a_free |
| 571363 | c8d2-tcnest-b | amdq (<NODE>) | 11:05 | 11.82 | nested runs b_free |
| 571366 | c8d2-tcnest-p | amdq (<NODE>) | 24:57 | 26.61 | nested runs a_power and b_power |
| 571365, 571375 | c8d2-tcrep | sharedq | 2:44, 2:43 | 0.18 | replicate-level shape |
| 571385 | c8d2-tcnan | sharedq | 0:39 | 0.01 | nested analysis (superseded statistics), output sha256 |
| **total** | 10 jobs | | | **54.84** | AMD 53.40, sharedq 1.44 |

**This revision (2026-10-08):**

| Job | Name | Partition | Elapsed | Core-h | Role |
|---|---|---|---|---:|---|
| 571401 | c8d2-tc2setup | sharedq (<NODE>) | 0:08 | 0.002 | two seeds registered; DL run setup (nets, members) |
| 571402 | c8d2-tc2cert | sharedq (<NODE>) | 15:29 | 1.03 | multi-prime randomized cancellation verification, all 24,173 kernels; PASSED |
| 571403 | c8d2-tc2neg | sharedq (<NODE>) | 2:48 | 0.09 | 9 controls with assertions; PASSED |
| 571404 | c8d2-tc2dl-a | amdq (<NODE>) | 7:27 | 7.95 | double-lift targeted run, campaign a |
| 571405 | c8d2-tc2dl-b | amdq (<NODE>) | 6:03 | 6.45 | double-lift targeted run, campaign b |
| 571406 | c8d2-tc2an | sharedq (<NODE>) | 1:31 | 0.05 | extraction, J8 check, joint-resampling statistics; PASSED |
| **total** | 6 jobs | | | **15.58** | AMD 14.40 (busy 14.34), sharedq 1.18 |

Site rules:
- symmetry only, every job named `c8d2-` with `--mem` and `--time`; the sharedq jobs ran with `--no-requeue`;
- the amdq jobs used the production exclusion list plus <NODE>–<NODE> (amddebugq-only nodes outside the surveyed pool)
  and ran on EPYC 7543 nodes of the production pool;
- at most 2 live AMD-pool jobs;
- no other job was touched, and none of these is left running.

## 10. Files

- `scripts/`: every script and job file used.
  - The revision's `.slurm` files ran from `<SCRATCH>/c8d2/work/tailcheck2-ba68f401e46e/`; the first
    version's from `…/tailcheck-ba68f401e46e/`. Each job's input sha256 is in its evidence folder.
  - `tc_cert.cpp` (v2), `tc_cert_list.py`, `tc_cert_check.py`, `tc_cert.slurm`: the verification and its pass/fail check.
  - `v1/tc_cert.cpp`, `v1/tc_cert.slurm`: the first version (job 571351), sha256 `335785c8…`, `8966e3b4…`.
  - `tc_negctl.py`, `tc_negctl.slurm`: the controls.
  - `tc_cert_seed.txt`, `tc_dl_seed.txt`, `tc_nested_seed.txt`: the seeds.
  - `tc_merged_tails.py`, `tc_select_data.py`, `tc_replicate_c8.py`: reads of the existing campaigns.
  - `tc_ab_hill.py`: Mac, from the committed `tails.csv.gz`.
  - `tc_choose.py`, `tc_nested.py`, `tc_nested_graphs.txt`, `tc_nested_classes.txt`: the first nested run.
  - `tc_dl_graphs.txt`, `tc_dl_classes.txt`, `tc_dl.slurm`, `tc2_setup.slurm`: the double-lift targeted run.
  - `tc_nested_extract.py`, `tc_nested_joint.py`, `tc2_analyze.slurm`, `native_outputs_old.sha256`: the revised
    statistics.
  - `tc_nested_analyze.py`, `tc_nested_split.py`: the first version's statistics (superseded).
  - `tc_cert_summary.py`, `tc_dl_summary.py`, `tc_plots.py`, `tc_plots_joint.py`: summaries and figures.
- `evidence/<job folder>/`: the jobs' outputs; `evidence/logs/`: the Slurm logs; `evidence/sacct.txt` and
  `evidence/sacct_followup.txt`; `evidence/large_files_followup.sha256`, the files kept on BeeGFS only.
- `results/`:
  - `cert_summary.json`: v2, with the error estimate; `v1/cert_summary.json` is the first version's;
  - `dl_targeted.json`: the double-lift coverage, per-graph table and SE scenarios;
  - `ab_hill.json`: the a/b test and pilot-to-production Hill ratios with the models;
  - `nested_split.json`: the first version's statistics (superseded by `evidence/tc2an.571406.0/nested_joint.json`).
- `plots/`: `nested_joint.png` (the revised statistics), `hill_vs_n.png`, and `nested.png` (the first version's,
  superseded).
- `seeds/`: `tailcheck_symmetry.json` (symmetry's log after job 571358) and `tailcheck2_symmetry.json` (after job
  571401), both merged into the mirror.
- Kept on BeeGFS only: the native outputs and nets of both nested runs, and the uncompressed `cert.jsonl` and
  `members.txt` of job 571402 (sha256 in the evidence folders).
