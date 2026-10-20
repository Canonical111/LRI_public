# Diagnosis of the C4/C5 offset of the joint thermal extrapolation (PLAN G3)

Data: the saved thermal rows (Λ = 2…50, even) and the saved φ6 gap rows (fifth order to Λ = 58, third order to
Λ = 128).

Produced by: `analysis/diagnose_systematic.py`, which writes `analysis/diagnosis.json`. This file quotes that output.

Status of the data: §§1–7 use the saved data (Λ ≤ 50) only. §8 summarizes the update with the new cutoffs
completed so far; the numbers are in `analysis/UPDATED_RESULTS.md` and `analysis/diagnosis_extended.json`
(regenerate with `analysis/extended/fetch_results.sh`, `run_extended.py`, `diagnose_systematic.py --thermal-extra …`
and `write_updated_results.py`).

How the reference values are used:
- The exact C4 = 45.42488010356 and C5 = −731.13947662454 appear only in comparisons and in the clearly labelled
  calibration check (§5).
- The diagrammatic C6 = 14331.8 ± 0.5 and C7 = −322550 ± 41 are compared after the fact.
- No headline number is fitted to any of them.
- The ranges below are spreads over tested models, not confidence intervals.

## 1. The offset (reference fits: 16 ≤ Λ ≤ 50, shift 0, reference gap input)

| basis | C4 − exact (rel.) | C5 − exact (rel.) | (C6 − diag)/σ | (C7 − diag)/σ |
|---|---|---|---|---|
| A | −1.86e-3 | +4.52e-3 | +55.7 | −22.8 |
| B | −2.09e-3 | +3.25e-3 | +28.2 | −14.0 |
| C | −1.67e-3 | +3.98e-3 | +37.0 | −11.2 |

Sign convention: C5 > exact in relative terms means that C5 is more negative. So |C5|, |C6| and |C7| come out too
large in magnitude, and C4 too small.

## 2. D1: the 4032-variant ensemble

The ensemble is that of `combined_stress.py`, recomputed with C4 and C5 included. It reproduces the saved C6 and
C7 of all 4032 variants to ≤ 1e-6.

Relative C4 error:
- median −1.96e-3; 5–95 % range −3.56e-3 … −1.8e-5; extremes −1.15e-2 … +1.5e-3;
- 96 % of the variants lie below the exact value.

Relative C5 error:
- median +3.24e-3; 5–95 % range −1.03e-3 … +1.12e-2;
- 92 % of the variants lie below the exact value (more negative).

**No variant has both C4 and C5 within 1e-3 of the exact values.**

A labelled heuristic, not a result: a linear regression of C6 and C7 on the two relative errors across the
ensemble (R² = 0.96 and 0.81) gives C6 ≈ 14249 and C7 ≈ −316970 at zero C4 and C5 error. That is *further* from
the diagrammatic values than the reference fits. Within this model family, making C4 and C5 right does not make
C6 and C7 right. So the near-agreement of C6 and C7 with the diagrammatic values cannot be read as "the same small
systematic at every order".

## 3. D2: window dependence (reference gap input, shift 0)

Upper edge `hi` = 36 → 50, with `lo` = 16:
- C4 is essentially flat:
  - A: −1.77e-3 → −1.86e-3;
  - B: −2.14e-3 → −2.09e-3;
  - C: −1.43e-3 → −1.67e-3.
  It moves slightly *away* from the exact value in A and C.
- C5 drifts slowly *toward* the exact value in all three:
  - A: 4.95e-3 → 4.52e-3;
  - B: 3.38e-3 → 3.25e-3;
  - C: 4.67e-3 → 3.98e-3.

Lower edge `lo` = 12 → 24, with `hi` = 50: C4 moves by 0.1–0.5e-3 and C5 by 0.25–1.4e-3.

Across the bases at `lo` 16 and `hi` 50:

| | minimal | A | B | C | D | E | F |
|---|---|---|---|---|---|---|---|
| C4 | −1.8e-5 | −1.86e-3 | −2.09e-3 | −1.67e-3 | −2.31e-3 | −1.82e-3 | −2.16e-3 |
| C5 | +1.22e-2 | +4.52e-3 | +3.25e-3 | +3.98e-3 | +1.95e-3 | +2.49e-3 | +2.82e-3 |

The two-term minimal basis gets C4 right but C5 wrong by 1.2 %.

## 4. D3 and D4: alternative tails and cutoff shifts

| variant (lo 16, hi 50) | C4 | C5 | C6 | C7 | max cond |
|---|---|---|---|---|---|
| A / B / C | −1.86 / −2.09 / −1.67e-3 | +4.52 / +3.25 / +3.98e-3 | 14360 / 14346 / 14350 | −323484 / −323123 / −323011 | 1.5e6–8e7 |
| A / B / C + free thermal exponents | same C4 | +1.20 / +0.65 / +1.15e-3 | 14324 / 14296 / 14350 | −322497 / −321267 / −324008 | 7e7–2e9 |
| A + z^j/Λ, j ≤ k−2 | −1.34e-3 | +3.06e-3 | 14415 | −323045 | 2e15 |
| A + z^j/Λ^1.5, 2 ≤ j ≤ k−2 | −2.16e-3 | +2.02e-3 | 14343 | −322847 | 4e13 |
| A + both towers | −2.67e-3 | −1.61e-3 | 14200 | −317789 | 2e17 |
| gap input: vacuum-subtracted / free leading log / ω3 free (A, B, C) | changes ≤ 1e-5 | ≤ 3e-5 | ≤ 1.5 | ≤ 50 | unchanged |

- Free exponents start at k ≥ 5, so they leave C4 unchanged. They bring C5 to within 0.6–1.2e-3.
- The log-tower bases are numerically ill-conditioned (cond 1e13–1e17) at 18 data points, so their numbers are
  indicative only.
- **The gap inputs are not the source** of the offset.
- D4, cutoff shifts of ±2 and ±4 in Λ: C4 moves by up to 2e-3 and C5 by up to 7e-3, in both directions.

## 5. Calibration check (labelled; uses the exact C4 and C5)

The reference bases are refitted with C4 and C5 fixed at their exact values, and the maximum fit residuals are
compared with the free fits. The data are accurate to about 1e-9.

| basis | max residual, C4 order: free → exact imposed | C5 order: free → exact imposed | C6, C7 with exact C4 and C5 imposed |
|---|---|---|---|
| A | 8.5e-8 → 7.9e-6 | 4.7e-6 → 5.4e-4 | 14253.7, −320988 |
| B | 4.1e-9 → 6.7e-7 | 3.0e-7 → 3.7e-5 | 14257.8, −320964 |
| C | 1.3e-7 → 3.5e-6 | 2.2e-6 → 2.5e-4 | 14249.6, −320523 |

Imposing the exact limits raises the residuals by factors of 28–170, far above the data accuracy. So **within
these tail bases on Λ ≤ 50, the exact C4 and C5 are inconsistent with the data.** Imposing them also moves C6 and C7
away from the diagrammatic values, to about 14250 and −320500 to −321000.

## 6. Residual-ratio curves

R_n(Λ) = [C_n(Λ) + Σ_j e_j (C_{n−j}(Λ) − C_{n−j}(∞)) − C_n(exact)] / T2(Λ), for n = 4 and 5, with the exact lower
limits. The model predicts R_n(Λ) → a_n, plus corrections suppressed relative to T2. The measured values:

| Λ | 10 | 18 | 26 | 34 | 42 | 50 |
|---|---|---|---|---|---|---|
| R4 | 164.53 | 158.78 | 155.66 | 153.61 | 152.13 | 151.00 |
| R5 | −1975.3 | −1736.2 | −1596.1 | −1498.2 | −1423.5 | −1363.4 |

Both are still drifting at Λ = 50. The step in R4 over the last 8 units of Λ is 1.1, in R5 about 60. How the drift
extrapolates is exactly the tail question; Λ ≤ 50 cannot settle it.

## 7. Conclusion at Λ ≤ 50: unresolved

The criterion fixed in advance (PLAN G3, review LRI-007) allows a matching offset to be claimed only if all three
of these hold:
- the intercepts are stable in the window;
- the extended data are predicted by the frozen Λ ≤ 50 fits;
- the intercepts are insensitive to tail-basis extensions.

At Λ ≤ 50:
- **Stable window:** partly. C4 is flat in `hi`, but C5 still drifts toward the exact value.
- **Tail insensitivity:** fails. The basis, free exponents, log towers and cutoff shifts each move C4 and C5 by an
  amount comparable to the offset itself.
- **Held-out test:** not yet possible.

The exact limits cannot be accommodated by the tested tails (§5), and R4 and R5 are not converged (§6). Two
explanations remain open:
- a misspecified asymptotic tail, with power or log structure beyond the tested bases;
- a genuine matching offset of the truncated Hamiltonian.

The decisive tests use the new cutoffs. They are:
- whether the frozen Λ ≤ 50 fits predict Λ = 52…116;
- whether R4 and R5 continue toward values compatible with the exact limits;
- whether the calibration-check residual ratio falls when `hi` is raised to 116.

## 8. Update with the new cutoffs (campaign snapshot; see UPDATED_RESULTS.md)

§8 was written with thermal Λ = 70…84, φ6 d5 to Λ = 106 and d3 to Λ = 176. UPDATED_RESULTS.md is regenerated
from the latest snapshot (thermal complete for every even Λ from 52 to 118 on 2026-09-29). The criteria verdicts
below are unchanged at Λ = 118. The generated snapshot numbers are in UPDATED_RESULTS.md. Qualitatively,
so far:
- **Held-out test passes by a wide margin.** The frozen Λ ≤ 50 reference fits predict the new thermal
  coefficients to 7.5e-7 … 5.4e-6 of the remaining distance to their own limits. The tail model describes the
  finite-cutoff data well far beyond its window.
- **The offset persists.** With `hi` = 84, C4 stays at −1.86e-3 to −2.04e-3 relative to the exact value in A, B
  and C, and C5 at +3.0 to +4.0e-3.
- **The calibration check strengthens.** Imposing the exact C4 and C5 raises the residuals by factors of 36–280 at
  `hi` = 84. The free-fit residuals themselves grow 6–7× (A and C: from about 1e-7 to 6e-7).
- **R4 and R5 are still drifting:** R4 is 151.0 at Λ = 50 and 148.1 at Λ = 84.
- **The window criterion is not met.** C5 drifts by 5–7e-4 in A and C between `hi` = 50 and 84.
- **The tail criterion is not met for C5.** At `hi` = 84 the D3 spread is 4.0e-3 against a smallest offset of
  3.0e-3; freeing the exponents alone moves C5 by about 3e-3. C4 passes, with spread 6.2e-4 against an offset of
  1.9e-3.

Under the pre-set rule, therefore, **no matching offset is claimed**.

*Campaign inventory (final, 2026-10-01).* 111 new cutoffs: thermal at every even Λ from 52 to 118, φ6 d5 at every
planned cutoff up to 160, and φ6 d3 to 832. φ6 d3 Λ = 608 was never run. A top-up on 2026-10-01 marked it out of
time because `campaign.EXPIRY` still held the old allocation's end (2026-09-30). That record was revoked on
2026-10-02 (`campaign/EXHAUSTED.revoked.jsonl`); it was not a resource limit. Λ = 608 would only fill one hole in
the d3 grid, where ω3 is already stable to 2.4e-5. The remaining ambiguity is between a slowly
converging tail (R_n still drifting) and a genuine offset (predictions accurate, intercepts stable in C4). The
largest cutoffs, Λ ≥ 100, are the decisive data. This section will be refreshed when the campaign completes.

## 9. Exploratory, post hoc: raising the lower window edge (data to Λ = 118)

This analysis is *not* part of the pre-registered protocol. It was chosen after the extended data had been seen,
because at lo = 16 the free-fit residuals grow far above the data accuracy once hi reaches about 110. Script:
`analysis/extended/explore_lower_edge.py`, output `explore_lower_edge.json`. The fit is the same model (§6 of the
REPORT, extended gap input), with lo ∈ {16, 24, 32, 40, 50, 60, 70} and hi = 118 (numbers quoted at hi = 116; at hi = 118 they change by ≤ 1e-5 relative in C4). The tail variants are:
- every basis;
- A, B and D with free exponents or with the original gap input;
- A and D plus a z^j/Λ tower, a z^j/Λ^1.5 tower, or an extra Λ^−0.75 term.

**Fit quality.** At lo ≥ 40 every non-minimal variant fits the C4 order at the data accuracy, with max residual
1e-9 … 2e-12. At lo = 16 only one variant does.

**C4, all 18 non-minimal variants at lo = 40…70:** relative offset between −1.82e-3 and −1.99e-3.
- The standard bases, free exponents and both gap inputs: −1.96e-3 … −1.99e-3.
- Basis E and the tail extensions: −1.82e-3 … −1.92e-3. Some are ill-conditioned (cond 1e11–1e16), so they are
  indicative only.
- In absolute terms, C4(Λ → ∞) is between 45.335 and 45.342, against the exact 45.42488: an offset of −0.083 to
  −0.090. The spread over tail structures is about 1/10 of the offset.

**C5:** relative offset between +0.07e-2 and +0.31e-2 (more negative than exact) in every variant, strongly basis
dependent. Free exponents give the smallest offset.

**C6, C7:** 14312–14345 and −321963 … −323044. The model spread brackets the diagrammatic 14331.8 ± 0.5 and
−322550 ± 41, so they are consistent but not decisive.

**Reading (exploratory).**
- With every tested power and log tail fitting the data to its accuracy, the extrapolated C4 of the truncated
  Hamiltonian stays 0.18–0.20 % below the exact value. That is evidence for a genuine O(ε⁴) matching offset of the
  truncated Hamiltonian.
- It is not a proof. A tail structure outside the tested families (for example 1/log Λ) cannot be excluded, and
  the choice of the lower edge was made after seeing the data.
- C5 is offset in the same direction in every variant, but its size is not pinned down.

## 10. Adversarial stress test of §9 (2026-10-02)

The test used five independent analyst lenses. Each was checked by an independent verifier, who re-derived the key
numbers with their own code (50–65-digit least squares). Every decision-relevant number reproduced. Scripts, outputs
and the full journal are in `analysis/stress_test/`. This is post hoc, like §9.

The lenses were:
- slow tails;
- extrapolation independent of the joint model, validated on C2 and C3;
- data integrity and resampling;
- cutoff coordinate;
- higher orders.

### 10.1 Corrections to how §9 argues
1. **The data are about 1000 times more accurate than §9 assumed.** A model-free finite-difference test puts the noise
   of the C4-order target at about 1.2e-12 rms (raw C4 about 3.5e-13, C3 about 6e-14, C2 about 5e-15). The quoted
   1e-9 is the regression maximum over C0…C7 and is set by C7. At 1e-9 the test does not discriminate: the exact C4
   also "fits" in bases E, D, F and B at lo ≥ 50–70.
2. **The 18 variants are only 10–12 distinct fits at the C4 order.** Free exponents act only for k ≥ 5, and the
   gap-input swap changes only ω3 and above, so A, B and D each appear three times. Two tower variants duplicate
   others.
3. **The tight cluster at −1.96e-3 … −1.99e-3 comes from bases that underfit** by 400–700 times the noise, with a
   smooth systematic residual pattern. Fits that actually reach the noise floor give **−1.80e-3 … −1.92e-3**, i.e.
   C4_HT ≈ 45.338–45.343.
4. **The "spread about 1/10 of the offset" is fragile.** Within physically motivated tail classes, the adequate fits
   span about 30–40 % of the offset. Treating a cutoff shift as a nuisance parameter widens the spread by 15–40 %,
   always away from the exact value.
5. **The evidence comes mainly from low windows.** In the physically natural S4 tail basis (half-odd powers with
   log^0..2, integer powers with log^0..1), the intercept is resolved at lo = 16–24, where the exact C4 is excluded.
   At lo ≥ 40 it is undetermined.
6. **White-noise z-scores and residual-inflation factors are not calibrated.** At C3, where the limit is known,
   adequate fits exclude the true C3 at up to 172σ. Imposing the exact C3, or the diagrammatic C7, inflates residuals
   10–60 times. So Claim 2's factors (28–280) and large |z| values are not, by themselves, evidence.

### 10.2 What survives
- **Clean data.**
  - No step at the 50/52 boundary between old and new code: below 2e-12.
  - No step at the int64 path for L ≥ 112, and no parity structure.
  - Every resampling (drop L ≥ 112, new rows only, L mod 4, jackknife) moves C4 by ≤ 0.8 % of the offset.
- **Every calibrated method gives C4 below the exact value.** No method that recovers C2 and C3 from the same data
  returns 45.42488:
  - Neville and BST on the e-subtracted sequence give 45.3353–45.3372 (relative −1.93e-3 … −1.97e-3);
  - fits with only ω1 imposed have a median of −1.90e-3;
  - fully ω-free raw fits give −0.8e-3 … −1.9e-3 (median −1.6e-3).
  The exact value would need a leading log² coefficient about 40–80 % away from the prediction of ω1 = 3.5, and ω1 is
  itself confirmed to about 1e-5 by C3.
- **The cutoff coordinate cannot create a genuine offset.** The limit is invariant under L → f(L). Reaching the exact
  C4 needs shifts of +6 to +12 in L, with cancelling tail coefficients about 100 times larger. Those fits are 40–60
  times above the noise floor and fail held-out prediction by about three orders of magnitude.
- **Scale argument.** Calibrated tail-fit biases at C3 are about 3e-5 of the remaining C3 tail at L = 118. The C4
  offset is 2.3 % of the remaining C4 tail. A tail artefact would have to be about 700 times worse at C4 than at C3.
- **Calibrated Bayesian fits.** Gaussian priors on tail coefficients, with widths chosen by maximum evidence, recover
  the exact C3 within 0.6–2.3σ. At C4 they give −1.86e-3 … −1.97e-3, with the exact C4 excluded at |z| ≥ 27. The prior
  settings that admit the exact value are ≥ 30 log-evidence units worse.
- **Independent physics expectation.** The draft quoted in `EFFECTIVE_HAMILTONIAN_PROPOSAL.md` §2.1 lists
  infinite-cutoff defects of the two-coupling HT: descendant spacing 1 + 0.0185 ε², and a two-particle shift of
  −0.13 ε². They are invisible to the two tuning conditions and enter Δ_{φ²} at ε⁴. The draft already attributes "the
  0.19 % miss of C4" to them, and the offset found here is that size.

### 10.3 What the data cannot exclude
- **A near-constant tail term.** L^−p with p ≤ 0.05, or b/log L with b ≈ −1, is degenerate with the intercept and fits
  at the noise floor with the exact C4. Only physics excludes it: fixed-order perturbation theory gives half-integer
  powers times logs, and no operator has Δ − 1 near 0.02–0.05.
- **Rich power towers up to L^−3.** These make the exact C4 compatible (|z| ≤ 3), but they need cancelling
  coefficients up to 1e6, against ≤ 280 in the free fits.

### 10.4 Higher orders
- **C5:** offset toward more negative values in all fixed-shift variants (+0.07 … +0.31 %), with a basis-dependent
  size. The sign is not robust to cutoff shifts: basis E at s = +9 reaches nearly the exact C5, though 4 times above
  the C5 noise floor.
  - The C5 offset is not induced by the C4 offset through the e_j coupling; that coupling pushes the other way.
  - With the exact C4 imposed, C5 moves further from exact (+0.56 … +0.70 %).
- **C6, C7:** they cannot discriminate.
  - The variant spread is bimodal: about 14326–14345 with fixed ω and about 14312–14316 with free ω.
  - The best-behaved fixed-ω fits (E, D + L^−0.75 at lo = 60) give C6 = 14329.7–14331.1 and C7 = −322514 … −322565.
    That matches the diagrammatic values, with no offset at n = 6, 7.
  - Free-ω fits give relative offsets of about −1.2e-3 (C6) and −1.5e-3 (C7).
  - With the exact C4 and C5 imposed, C6 ≈ 14247–14256 and C7 ≈ −318843 … −320783, far from the diagrammatic values.

### 10.5 Net assessment
- The truncated Hamiltonian's C4 extrapolates to **45.338–45.343** with noise-floor fits, or 45.335–45.337 with
  independent Neville/BST. That is **0.18–0.20 % (about −0.08 to −0.09) below the exact value**.
- This holds in every calibrated method, conditional on standard power-times-log asymptotics. It matches an
  independently expected O(ε⁴) scheme defect of the two-coupling Hamiltonian.
- It is **strong evidence, not proof**, of a genuine matching offset. The open loophole is a near-constant or
  1/log L tail, which only theory can close.
- C5's offset is likely but not pinned down. C6 and C7 cannot settle the question.
- The pre-registered (lo = 16) verdict remains "unresolved".

## 11. Exact-identity checks of the corrected HT through ε⁴ (2026-10-02)

Descendant spacings are exactly integer at every order in ε, so any HT violation is a scheme defect, measured without
a continuum fit of C4. The checks used:
- two independent implementations: one on the package kernels, one from scratch with exact rationals; they agree to
  ≤ 8e-13 on 1688 finite-cutoff numbers;
- a reconciler and two skeptics.
Scripts, outputs and journal are in `analysis/identity_checks/`.

**Identities (extrapolated, per window count W):**
- **ε³:**
  - raw: +0.146 W (predicted (2A+3)/81 − 1/27 = 0.14603);
  - package g²D: −W/27 (the third-order bubble is missing);
  - complete disconnected vacuum-window correction (Dconn): 0 within 0.003 W, in all sectors.
- **ε⁴:**
  - the package g²D violates every descendant identity, by about −0.46 W; the violation does not decay and is linear
    in W (worse than raw);
  - Dconn removes 96–100 % of that.
- **Exactness.** With the frozen cutoff at Λ ≡ 1/4 or 1/2 (mod 2), raw HT satisfies E(∂φ) − E(φ) = 1 exactly through
  ε³ at every finite Λ (≤ 6e-15). The even-Λ violations are therefore cutoff-placement (window) artifacts.

**New C4 shift.**
- The ε⁴ vacuum density that g²D omits also falls in the fractional windows of the zero-mode reference states: the P=8
  level at E = Λ (p = 1, 2, 3) and the P=6 level at E = Λ − 1/2 (p = 3).
- After retuning, **ΔC4 = +0.0186910** on top of g²D. This was computed three independent ways, including exact sums
  to Λ = 288 (0.0186909946), with no log term.
- Built consistently, Dconn has no log Λ. The literal E_vac(Λ) − E_vac(Λ − E0) double-counts the bubble-bubble class,
  which reintroduces log Λ/17496.
- This supersedes the review statement that "at C4 the correction is effectively complete": g²D misses about 23 % of
  the total disconnected-window correction (K + 0.0187 = 0.0803).

**Independent confirmation from identities.** With the cutoff at Λ = L + 1/4, v4(∂φ) measures exactly the C4-relevant
level combination:
- with g²D alone it is +0.047…+0.053, against a predicted +0.0561, so the shift is confirmed without any C4
  extrapolation;
- with Dconn it is −0.0035…−0.0084 (range −0.021…+0.011), which bounds any further window defect visible to C4 at
  −0.001…−0.003 (range −0.007…+0.004). The central value has the wrong sign to close the remaining miss.

**C4 now.**

| | C4 | vs exact 45.42488 |
|---|---|---|
| raw HT | 45.335–45.338 | −0.19 % |
| + g²D (K) | 45.397–45.403 | −0.055 % … −0.062 % |
| + full disconnected window (Dconn) | **45.415–45.419** (pre-registered bases A–F, lo = 40–70); up to 45.423 with post-hoc tails | **−0.006 … −0.010** (−0.013 % … −0.021 %); post-hoc −0.002 |

- All 12 distinct tail models give intercepts below exact, and the miss shrinks as the tail gets more flexible. Floor-
  level pre-registered bases (B, D, F) still disfavour the exact value about 100–160× in max residual.
- The remaining miss is most likely extrapolation bias. A further small defect of about −0.003 is not excluded, but the
  phase-1/4 identity test shows it is not a window defect.

**Not done.** C5 and higher under Dconn need the ε³ operator response on intermediate states and higher top levels
(P = 10, 12).

## 12. Complete window correction through ε⁵ and corrected C5 (2026-10-03)

The workflow used two independent implementations (A: eps-jet engine on the package kernels; B: from scratch with exact
rationals and closed-form top-level sums), a reconciler and two skeptics. A third from-scratch engine (the numerical
skeptic's) reproduces the ΔC5 table to ≤ 2.4e-12. Scripts, outputs and journal are in `analysis/eps5_window/`.

**Correction (settled to about 1e-12).**
- Dconn through ε⁵ is built consistently, without double counting. Only the P=8 level at E = Λ and the P=6 level at
  Λ − 1/2 fall in the reference windows at ε⁵; P = 10 and 12 cannot enter at fifth order.
- The complete ΔC5 = C5(Dconn) − C5(raw) is 0.69870 at L = 8 and 0.71358 at L = 118 (table in
  `analysis/eps5_window/reconcile/dC_reconciled.csv`). At L = 118 its components are:
  - g²D +0.5839;
  - ε³ bubble −0.1229;
  - ε⁴ rows +0.0311;
  - ε⁵ rows +0.2216.
- The limit is about 0.717–0.718 + 4.40e-4 log L. The log comes from the g²D/g³ operator response.

**ε⁵ identities (per window count W).**
- raw +2.3…+2.8 W;
- g²D (with or without the g³ bubble): −1.3…−1.6 W, non-decaying;
- Dconn: consistent with 0 within about ±0.1–0.2 W. ∂φ keeps a residual of about −0.1 that has not converged (drifts by
  0.03–0.3 as Lmax goes from 40 to 64).
- The window-visible C5 residual is about −0.02 (at worst −0.13), with the wrong sign. This includes the ε⁴ feed of
  +2.48 δ8 − 1.24 δ6, which the phase-1/4 test cannot see.
- No missing non-decaying ε⁵ term was found.

**Corrected C5 (exact −731.13947662454).**
- **Pre-registered joint model** (bases A–F, lo = 40–70): E −731.65…−731.72 (miss −0.51…−0.58), and A–F miss
  −0.51…−1.53. The correction moves every basis by the same +0.72, so the spread between bases (0.81–0.95) is
  unchanged. Five of the six bases fit C5 at 100–7000× the noise floor.
- **Leading tail freed** (post hoc): freeing the leading L^−1/2 and L^−1/2 log L terms at both C4 and C5 brings every
  basis to the noise floor.
  - Corrected C5 misses −0.22…+0.06 (lo = 50–70) and corrected C4 misses −0.007…+0.001 at the same time, closing
    79–109 % of the raw C5 miss (C4: 90–93 %).
  - Freeing the term at C5 only is equivalent to the free-exponent variants and needs an effective ω3 ≈ 380–430,
    against the gap value of 556.2.
- **Coupling between the orders.** Inside the pre-registered model, imposing the exact C4 pushes C5 to −0.74…−1.68
  (dC5/dlim4 = −32…−38). That tension disappears in the freed-tail family.

**Reading.**
- The complete window correction is done through ε⁵, and no window defect can explain any C5 miss.
- Corrected C5 is consistent with the exact value within about ±0.3–0.4.
- The remaining pre-registered miss comes mainly from the joint model fixing the leading L^−1/2 log L tail coefficient
  through the φ⁶-gap ω3. Whether that tie is right is the decisive open theory question. One hypothesis (untested): the
  frozen cutoff generates L^−1/2 tails from a state-dependent, power-divergent φ² counterterm (r2 grows like L^0.5),
  which would run with Δε rather than ω6.
- All tail freeing is post hoc.
