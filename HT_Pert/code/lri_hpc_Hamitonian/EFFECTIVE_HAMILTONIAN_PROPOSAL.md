# Proposal: effective-Hamiltonian matching for the d = 1 long-range Ising Hamiltonian truncation

Status: proposal (2026-09-29). Nothing described here has been computed yet except where a source is cited.
Context: `PHI6_JOINT_C7_REPORT.md` (this folder), `Hamitonian.md`, and the Hamiltonian-truncation subsection and the
"Limits of the Hamiltonian-truncation method" paragraph of `Draft/lri_d1_epsilon_expansion_detailed.tex`.

## 0. Summary

- **Problem.** The two-coupling cylinder Hamiltonian H = H_GFF + r(ε)M + g(ε)V, tuned only by the two exact gap
  conditions, is not the fixed-point dilatation operator.
  - At infinite cutoff it misses mode-dependent one- and two-body terms that start at O(ε²).
  - At finite cutoff it carries spectator-dependent cutoff artifacts. Only one of these, the isolated vacuum shell,
    has been matched so far.
  - The first defect alone plausibly explains why the HT intercepts miss the exactly known C4 and C5 by 0.2–0.45%.
    If so, the HT C6 and C7 are limited by the same systematic, not by the extrapolation.
- **Proposal.** Build the missing counterterms explicitly and fix them with additional exact conditions of the fixed
  point, such as integer descendant spacings and Ward identities, instead of absorbing them into tail fits. Then
  match the cutoff dependence analytically.
- **Scope, answering "perturbative or non-perturbative?".**
  - Stage 1 is **perturbative**: the output is the ε-expansion coefficients C_k. Its purpose is an independent,
    end-to-end check of the diagrammatic C6 and C7 by a method with no Feynman graphs, validated first on the exact
    C4 and C5.
  - The matched Hamiltonian is also the prerequisite for Stage 2, which is **non-perturbative**: diagonalize at
    finite ε and compute scaling dimensions, such as ν(σ) and correction-to-scaling exponents, where the ε-series is
    not useful.
  - The order Stage 1 → Stage 2 is deliberate. Without matching, finite-ε results would carry a scheme error of
    unknown size. Stage 1 measures and removes it where exact answers exist.

## 1. Setup (unchanged from the source)

- The Hamiltonian is H = H_0 + r(ε)M(ε) + g(ε)V(ε), with H_0 = N + P/4 − εP/4.
- The mode weights are u_n² = ((1−ε)/2)_n/n!, and B = Σ u_n a_n; M = B†² + 2B†B + B²; V = (1/12) Σ_j C(4,j) B†^j B^{4−j}.
- The cutoff is N + P/4 ≤ Λ, frozen at ε = 0. Sphere parity is projected after complete vertices.
- The tuning conditions are E_1 − E_0 = (1−ε)/4 (Δ_φ exact, no field renormalization) and E_3 − E_0 = (3+ε)/4 (the
  shadow relation Δ_{φ³} = 1 − Δ_φ). Both are exact properties of the long-range fixed point, not only
  perturbative statements.
- The target is Δ_{φ²} = E_2 − E_0 = 1/2 − ε/6 + Σ_k C_k ε^k.

## 2. Evidence that matching is needed

### 2.1 Error at infinite cutoff (scheme)
From the draft (`sec:htrunc` and its "Limits of the Hamiltonian-truncation method" paragraph), in the tuned
two-coupling Hamiltonian at infinite cutoff:

| Observable | Exact fixed point | Two-coupling HT |
|---|---|---|
| E(∂φ)−E(φ), E(∂φ²)−E(φ²), E(∂φ³)−E(φ³) | 1 | 1 + 0.0185 ε² |
| E(∂²φ)−E(φ) | 2 | 2 + 0.0185 ε² |
| two-particle state a₀†a₂†\|0⟩ | no extra shift | additional −0.13 ε² |

- These terms vanish on the two tuning states, so the two conditions cannot see them.
- They leave C2 and C3 unchanged but enter Δ_{φ²} at ε⁴, through the O(ε) wavefunction components.
- A one-body counterterm κ Σ_n n a_n†a_n, fixed by the ∂φ Ward identity (κ₂ = −0.0185), moves C4 by only +0.004,
  so the **two-body** part dominates.
- The draft attributes the 0.19% miss of C4 to this.

The report's post-fit intercepts show the same pattern at every order:

| | HT reference fits A/B/C | Diagrammatic | HT − diagrammatic |
|---|---|---|---|
| C4 | 45.340475 / 45.330026 / 45.349132 | 45.42488010356 (exact) | −0.084 / −0.095 / −0.076 (≈ −0.2%) |
| C5 | −734.447 / −733.516 / −734.046 | −731.13947662454 (exact) | −3.31 / −2.38 / −2.91 (0.33–0.45% too large in magnitude) |
| C6 | 14359.63 / 14345.92 / 14350.31 | 14331.8 ± 0.5 (numerical) | +27.9 / +14.1 / +18.5 (0.10–0.19%) |
| C7 | −323483.7 / −323123.2 / −323011.2 | −322550 ± 41 (numerical) | −934 / −573 / −461 (0.14–0.29%) |

- The offset is systematic, of similar relative size at every order, and present even where the answer is exact.
- The report's 4032-variant model spreads (C6: 13858–14548; C7: −329447 to −315392) contain the diagrammatic
  values, but all three reference fits miss them.

### 2.2 Error at finite cutoff (artifacts)
- **Vacuum shells.** Because the cutoff constrains the total energy of a state, disconnected vacuum shells are removed
  differently for a state of energy E_i than for the vacuum.
  - Restoring them (the report's D_i(ε)) gives the exact shifts δω₂ = −1/54 and δω₃ = −(2A+3)/81, with
    A = π + 4 log 2.
  - This is the only matched piece so far.
- **Connected boundary term.** d₂ contains an extra (8/(9√π)) Λ^{−1/2} amplitude beyond a local φ⁶ insertion. It is
  spectator-dependent, at the same power as the φ⁶ channel, and not matched.
- **Slow convergence.** The raw coefficients at Λ = 50 reach only 57% (C4), 48% (C5), 40% (C6) and 34% (C7) of their
  limits. For example, C7(50) = −109205.5 against −322550. The fitted tail therefore carries most of the answer.

## 3. Plan

### Stage 0: diagnosis (cheap; existing code and cutoffs)
Measure, order by order in ε and as functions of Λ, the violations of **exact** fixed-point conditions that the two
couplings do not enforce:
- descendant spacings E(∂ⁿO) − E(O) − n for O = φ, φ², φ³, φ⁴ and n = 1, 2, 3;
- two- and three-particle mode states: shifts not accounted for by the primaries and descendants they belong to;
- the ∂φ Ward identity and any other exact relations available in d = 1.

Extrapolate each violation to Λ = ∞. The output is a table v_{O,n,k} (violation at order ε^k), which tells which
operator structures (one-body or two-body, and which mode dependence) are missing, and at which order.

**Decision point.** If the infinite-cutoff violations are consistent with zero at the orders that matter, the
systematic of §2.1 is an extrapolation effect instead, and Stage 1b (cutoff matching) becomes the priority.

### Stage 1a: scheme matching at Λ = ∞ (perturbative)
1. **Counterterm basis.** Consistent with the symmetries, it contains:
   - one-body terms Σ_n κ(n; ε) a_n†a_n;
   - two-body normal-ordered terms with mode-dependent kernels, K(m,n;p,q; ε) a_m†a_n†a_p a_q, plus the
     creation/annihilation-changing structures allowed by parity;
   - higher-body terms only if Stage 0 shows they are needed.

   Each coefficient is expanded in ε, starting at the order where Stage 0 finds a violation.
2. **Fixing conditions.** Impose, order by order, the Stage 0 conditions (integer descendant spacings, Ward
   identities) in addition to the two existing gap conditions.
   - The number of independent conditions must cover the counterterm parameters.
   - Any leftover freedom must be shown not to affect Δ_{φ²}. This is the analogue of scheme independence.
3. **Recompute** C4…C7 with the same Rayleigh–Schrödinger machinery and the same tail analysis as the report.
4. **Acceptance, pre-registered before comparing C6 and C7.**
   - C4 and C5 must reproduce their exact values within the extrapolation uncertainty of the new fit.
   - Only then are the HT C6 and C7 compared, blind, with 14331.8 ± 0.5 and −322550 ± 41.

### Stage 1b: cutoff matching (perturbative)
- Replace fitted tails by analytic large-Λ asymptotics of the omitted perturbative sums, extending the report's
  exact results for d₂ and g₂ and for the vacuum part of d₃.
- Equivalently, add the effective operators of the Hamiltonian-truncation effective theory, ΔH(Λ) ≈ V (E − H_high)⁻¹
  V + …, computed order by order in ε, including the connected spectator-dependent terms (e.g. the 8/(9√π) channel).
- **Goal:** residual tails that start at Λ⁻¹ or Λ^{−3/2}, so that the extrapolations are short and a withheld-cutoff
  test is meaningful at the level of the diagrammatic uncertainties.

### Stage 2: non-perturbative use at finite ε
Diagonalize the matched Hamiltonian at fixed ε (fixed σ = (1+ε)/2) in the full truncated Fock space, not in
perturbation theory:
- **Tuning.** At each ε, tune (r, g) by a two-dimensional root find so that the truncated spectrum satisfies the two
  exact conditions; both hold non-perturbatively. Take the extra counterterms either from the Stage 1 ε-series,
  resummed or truncated, or fix them non-perturbatively with the same exact spacing conditions. Comparing the two
  choices estimates the matching uncertainty.
- **Observables:**
  - Δ_{φ²}(σ), giving ν(σ);
  - the dimension of the leading irrelevant operator, giving the correction-to-scaling exponent;
  - the low spectrum in general, and OPE data from matrix elements.
- **Checks:**
  - reproduce the ε-series at small ε;
  - compare with the 1D cluster Monte Carlo campaign (`LRI_1d_MC_report/`) and with resummations of the series.
- **Size.** The number of Fock states with N + P/4 ≤ Λ in one field-parity sector (P even) is 12,089 (Λ = 20),
  149,230 (30), 1,254,504 (40), 8,230,733 (50) and 45,237,589 (60). Reflection parity roughly halves these.
  Sparse Lanczos up to Λ ≈ 50–60 is therefore feasible on a cluster node; beyond that the space grows too fast.
- **Convergence.** Finite-cutoff effects scale as Λ^{−(Δ_irr − 1)}. The exponent is governed by the true
  non-perturbative Δ_irr(σ), which can be read off the same spectrum. Its series, 1/2 + 7ε/2 − 29.55ε² + …, is
  useful only at small ε. Near σ → 1 (ε → 1) the crossover to short-range behaviour limits the method.

## 4. Perturbative versus non-perturbative

| | Stage 1 (perturbative) | Stage 2 (non-perturbative) |
|---|---|---|
| Computes | ε-expansion coefficients C_k (and ε-expansions of other dimensions) | Δ(σ) at finite ε; spectrum; correction-to-scaling exponent |
| Method | Rayleigh–Schrödinger in ε on the truncated space | Full diagonalization at fixed ε with non-perturbative tuning |
| Validation | Exact C4, C5; diagrammatic C6, C7 | Small-ε agreement with the series; Monte Carlo at finite σ |
| Needs matching because | the scheme error biases C_k by 0.1–0.45% | the same missing terms are then O(ε²) effects at finite ε, with no series to compare against |
| New physics output | an independent graph-free check of C6, C7 (and possibly C8 later) | numbers the ε-expansion cannot give reliably at moderate σ |

## 5. Risks and open questions

- **Completeness of the counterterm basis.** Two-body kernels with general mode dependence carry many parameters.
  Stage 0 must show that a small structured family suffices.
- **Uniqueness and scheme ambiguity.** A finite set of exact conditions may leave directions unfixed. It must be shown
  that they do not affect Δ_{φ²} at the orders computed.
- **Scheme error versus extrapolation error.** If Stage 0 finds small infinite-cutoff violations, the §2.1 pattern
  comes mainly from the tail model, and Stage 1b matters more than 1a.
- **Cost.** At high orders the perturbative particle and mode caps (P ≤ 15, Q ≤ 12 for C7) and the counterterm ε-jets
  grow quickly. The existing `lri_hpc` package supplies the kernels.
- **Non-perturbative counterterms.** In Stage 2, counterterm coefficients known only as ε-series may not be adequate
  at larger ε. Fixing them by exact conditions at finite ε is preferable, but requires enough such conditions in
  the truncated spectrum.

## 6. First steps

1. **Stage 0 driver.** Compute descendant-spacing and multi-particle violations through ε⁴ at the existing cutoffs
   with the current kernels, and extrapolate them to Λ = ∞. This needs no new theory.
2. **Stage 0 report.** Decide from it the counterterm structures for Stage 1a, or whether to prioritise Stage 1b.
3. **Pre-register the Stage 1 acceptance tests** (§3, Stage 1a, item 4) before any matched C6 or C7 is looked at.

## References

- `PHI6_JOINT_C7_REPORT.md` (this folder): the φ⁶ gap, the vacuum-shell matching and the joint thermal extrapolation.
- `Draft/lri_d1_epsilon_expansion_detailed.tex`, Hamiltonian-truncation subsection and "Limits of the
  Hamiltonian-truncation method".
- C6(1) = 14331.8 ± 0.5: `lri_C6_numerical_update/`. C7(1) = −322550 ± 41: `LRI_C7_HPC/results/2026-09_expanse_v2/REPORT.md`.
- T. Cohen et al., *Hamiltonian Truncation Effective Theory*, arXiv:2110.08273.
- J. Elias Miró and J. Ingoldby, *Effective Hamiltonians and Counterterms for Hamiltonian Truncation*, arXiv:2212.07266.
