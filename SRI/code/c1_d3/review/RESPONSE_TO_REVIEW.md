# Response to the review and record of revisions

## Overall assessment

I agree with the review's main distinction: the retained-spectrum calculation is reproducible, but the narrow interval requires substantially more prominent discussion of input feasibility and assumption sensitivity. The revised note retains the calculation and corrects its interpretation. It reports **C1_retained = 0.273152423826** separately from the **scenario-specific range [0.2690, 0.2760]**. It no longer presents 0.2725 ± 0.0035 as the headline result.

The previous note already said that the interval was conditional, uncertified, and not a confidence interval, and described sampled allowances. The review's general statement that none of the limitations were disclosed is therefore too broad. However, the absence of the central-input infeasibility and the box/gap sensitivity tables was a substantive omission. Generic caveats were not an adequate substitute for these concrete diagnostics.

The attached review is copied unchanged as `review/ising3d_C1_review.md`. Its remote cluster outputs and independent reimplementations were not supplied. The new numerical evidence described below was generated with the scripts included in this revision; it is not a claim to have rerun the reviewer's unavailable implementations.

## Independently checked numerical points

The complete 20-stage workflow was rerun from scratch with the revised main-path code. The central coefficients and the original nominal, doubled-padding and weak-gap outputs agree with the delivered reference targets. The expanded full-run verifier passes 23 checks, including checks previously omitted from verification.

For the saved nominal LP, I independently find 68 violated rows at the central vector, all in sigma^4. Minimizing the maximum displacement with the nominal rows fixed gives **0.5735097801920123** box units, or **1.1470195603840245** quoted-error units. The witness satisfies the scaled rows up to about 3.8e-10. The report contains the witness, row indices and source hashes: `outputs/review_validation/fixed_lp_diagnostics.json`.

This fixed-LP minimum is not a claim that all inputs must move by the same amount, not a Gaussian significance, and not the threshold of a rebuilt smaller-box problem. The note now makes these distinctions explicit. Exclusion of the central **vector** does not exclude the number C1_retained from the final ratio interval.

Eleven gap/padding scenarios and eight additional box scenarios were independently recomputed. All use ten updates. Gap scans explicitly reuse the level-40 reference basis; box scans regenerate the affected sensitivities, sampled denominator, secants and padding. Their receipts and raw arrays are delivered. In particular:

| Change from the nominal scenario | Newly computed interval |
|---|---|
| Gaps (8, 6.5) | [0.2689017408, 0.2754113757] |
| Gaps (7, 7) | [0.2689067581, 0.2762911052] |
| Gaps (6, 6), ten updates | [0.2641991492, 0.2783385361] |
| Crossing padding ×2, ten updates | [0.2692746356, 0.2754096821] |
| Crossing padding ×3, ten updates | [0.2688700725, 0.2755722686] |
| Input box ±3 quoted errors, regenerated | [0.2684810806, 0.2760007917] |
| Input box ±4 quoted errors, regenerated | [0.2670763160, 0.2768354273] |
| Input box ±6 quoted errors, regenerated | [0.2638030203, 0.2786993520] |

The smaller rebuilt boxes ±1 and ±1.2 quoted errors are infeasible. The regenerated box scan does not exactly reproduce every last digit of the review's stress table; the reviewer's driver is unavailable, and this revision specifies and supplies its own regeneration protocol, including data-derived denominator constants. The qualitative conclusion is the same: the advertised range is not robust to these modest assumption changes.

The widened-box scans retain the chosen 5e-5 integrated-objective allowance. That allowance has not been uniformly validated over those enlarged boxes. These are sensitivity diagnostics, not new certified physical bounds. No attempt is made to average their endpoints into a universal error bar.

## Major items

| Review item | Assessment and revision |
|---|---|
| **M1: central inputs infeasible; box controls width** | Agree. Added a dedicated subsection with the 68-row result, minimax problem, witness interpretation, and a rebuilt-box sensitivity table. The note explains the nonrigorous status of the printed errors and distinguishes possible physical/input tension from a proved identification of its cause. |
| **M2: gap sensitivity omitted** | Agree. Added the full nine-row, matched ten-update gap table for the final method. It includes the mild (8,6.5) and (7,7) changes as well as weaker gaps. This is necessary interpretation of the final method, not an abandoned approach. |
| **M3: bare gap assumptions** | Agree that motivation and citations were missing. Added spatial-parity versus internal-parity definitions, an illustrative table of nearby unlisted states, and references to SD, HKR, Zhu and FFK. The margins are estimates, not certified gaps. HKR's spin-six extraction near 8.78 is explicitly marked unstable. The note does not declare all unstable entries artifacts or claim the cited studies prove completeness. |
| **M4: refinement command overwrites full receipt** | Agree. The note now gives `--output outputs/refinement_clean`. The driver also defaults non-full profiles to separate profile-specific directories, while full defaults to `outputs/reproduced`. Full-run verification is documented separately from a refinement-only run. |

The interpretation “either underestimated input errors or a missing operator” is a useful possible explanation of M1, but not an exhaustive theorem. Numerical/nonlinear-envelope hypotheses remain uncertified too. The revised note does not infer the existence or dimension of a new operator from these tests. The review's additional claimed central-gap threshold near 5.3 and its isolated-extra-operator scans were not rerun and are not presented as new package results.

## Minor items

| Review item | Assessment and revision |
|---|---|
| **m1: asymmetric interval hidden by midpoint** | Agree. Interval-first presentation throughout the note and README; retained value separate. The offsets from rounded 0.2732 are about −0.0042 and +0.0028. Compatibility fields retain the midpoint but label it explicitly as a midpoint, not a best fit. |
| **m2: stale hard-coded main constants** | Agree. Added `runtime_config.py`. The main ratio and denominator reference are read from current `analysis_results.json`; the denominator allowance is rounded outward from `input_box_results.json`; the scaled epsilon-prime window uses the actual parameter scale. The objective allowance is shared and its consistency is verified. Allowances remain chosen settings, not derived uncertainty bounds. Historical-only diagnostic modules are not recharacterized as configurable production calculations. |
| **m3: ratio sign condition unasserted** | Agree. The note derives the smaller-denominator conversion only for a numerator interval straddling zero. Explicit exceptions check this and positivity of the denominator. The nominal numerator range is approximately [−0.00335609, +0.00206082]. |
| **m4: real-axis sign condition unstated** | Agree. Added the factor q_D(x;G) and the condition q_D ≤ 1. Its maxima at the nominal nonsymmetric real points are about 0.6629 for sigma and 0.7121 for epsilon. The implementation checks the condition. |
| **m5: chosen, sampled nonlinear allowances** | Agree with the criticism of emphasis. The old note did disclose sampling, but the revision explicitly calls 1.5, 5e-5 and 1.001 choices; gives the measured 0.666645 padding ratio and 2.3952e-5 objective remainder; and identifies the absence of a uniform bound on mixed low-input/family cross terms. |
| **m6: verification gaps and side effects** | Agree. Verification now checks d0, J and padding at levels 40/48, normalized radial positivity, generalized-free remainder/prefactor tests, integrated-tail quadrature and angular/exponent envelopes. Missing outputs become failed checks rather than uncaught exceptions. Reports live beside the requested results, not in a fixed principal location. Integrity verification detects unlisted delivery files as well as hash mismatches, with an explicit option for intentional later additions. |
| **m7: Python `assert` guards disappear under -O** | Agree. Scientific guards in the affected numerical scripts now use explicit exceptions. The ratio guards are exercised under `python -O` by the supplied guard-regression script. No claim is made that every possible failing branch was exhaustively tested. |
| **m8: quadratic denominator can have an interior extremum** | Agree. Coupling candidate sets now include f=0 whenever the allowed interval contains zero. This does not change the present data. The dimension/grid envelope is still sampled, not interval arithmetic. |
| **m9: displayed working range unchecked** | Agree. Asset generation and the verifier check that the chosen range contains the computed nominal and doubled-padding runs. They do not claim it covers the box/gap stress runs; the note explicitly shows that it does not. |
| **m10: no published comparison** | Agree. Added a short normalization table and references to both BRRZ papers and Behan 2018. One arithmetic correction to the review: the present b0 gives **I_sigma = −1.950430157053901**, not −1.950413. This tiny slip has no effect on the favorable comparison with −1.950(5). |
| **m11: domain folding asserted** | Agree. Added the origin inversion with its marginal-dimension cancellation, the crossed OPE representation on the remaining ball, and inversion about e with its Jacobian and even-spin invariance. The mixed channel step is explicitly not a sigma/epsilon permutation symmetry. Consistent analytic continuation is stated as a prerequisite. |
| **m12: odd-spin sign unexplained** | Agree. Explained the cancellation between the lightcone-block sign and the reflected ordered OPE product. The implemented positive square remains unchanged. The normalized radial-state and generalized-free checks are identified; raw mixed-block coefficients are not incorrectly declared all positive. |
| **m13: printed input errors not all rigorous** | Agree. The note distinguishes rigorous S,E entries in Chang et al. from coupling/central-charge extraction errors, and fixed-Lambda spectrum spreads from cutoff convergence. The unverified error of the sensitive odd spin-three coupling is not treated as statistically calibrated. |
| **m14: missing references** | Agree. Added the requested journal information for the five original references, the PRL, HKR, FFK, Zhu and Behan 2018 citations, and updated source metadata. |

## Smaller items and observations

| Review item | Assessment and revision |
|---|---|
| **n1: lambda convention naming** | Agree. Named the KPS/Reehorst convention, gave the SD lightcone-block leading normalization and the free-scalar check w2 f_T² = 1/4. |
| **n2: undefined source amplitude and single-Z argument** | Agree. Defined D_O, A_{O,2}(delta) and I_O(delta;1), performed the scale integration, fixed the Z convention, and explained why this sourced external-state amplitude has one local insertion pole. |
| **n3: near resonance** | Agree as a robustness issue. The active scalar-series division now raises for |Delta+n−3|<1e-10. The note says the threshold is a guard, not a logarithmic subtraction prescription. It is inactive on the current spectrum. |
| **n4: “independent folding” label** | Agree. Reclassified this as same-domain algebraic/bookkeeping consistency. The old JSON key remains for compatibility, but the verifier and documentation do not overstate its independence. The reviewer's independent folding implementations are not claimed as newly delivered tests. |
| **n5: leading provenance labels** | Agree. Updated the active retained input snapshot, loader and generated table labels to the modern leading-data source/Ward identity. Historical reference outputs retain their original archived labels. Physical numbers are unchanged. |
| **n6: stale legacy stress coupling** | Agree. The legacy comparison now derives its stress couplings from the common dimensions and cT. The production result is unchanged. |
| **n7: “established”** | Softened to the crossover description proposed and supported in the cited work. No unrelated two-dimensional controversy is inserted into a three-dimensional reproduction note. |
| **n8: eight versus ten updates** | Agree. Preserved the original run with its actual update count and added matched ten-update padding tests. The difference is no longer silently attributed only to padding. |
| **n9: finite iteration not converged** | Agree. The note states the residual endpoint motion, distinguishes fixed-count stopping from convergence, and labels the ten-update weak-gap result separately. |
| **n10: code hygiene** | Removed duplicated leading constants and duplicate gap assignments where encountered. Broad reformatting and replacement of every historical numeric row selector were deliberately not undertaken; they are not prerequisites for the documented correction. The retained-snapshot test guards current row interpretation. |
| **n11: cached collection omits unchanged seeded outputs** | The existing behavior is documented rather than presented as a fresh final output. The primary delivered run is from scratch and includes all headline files. A full verifier is not promised for an incomplete cached profile. |

The note also explains why the folded region's smaller maximum radial coordinate is preferred, without restoring the abandoned domain sweep as a competing estimator. It explains that the less accurate auxiliary epsilon^4 correlator limits the even mixed-tail bound. The review's separate Monte Carlo discussion and higher-order coefficient inference are outside this C1 note and have not been incorporated or independently assessed.

## What changed, and what did not

The numerical central inputs are unchanged. Source labels and uncertainty-status metadata were corrected. Main code paths received the robustness fixes above; the original final numerical results are reproduced. The new tables quantify assumption sensitivity rather than claim a tighter error. The original conformal-block recurrence appendix and full retained-spectrum table bodies are preserved verbatim.

The revised TeX contains all added definitions and tables and still compiles from that one file alone. The package includes a detailed source diff, new sensitivity scripts and raw outputs, and the full supplied review. Compiler auxiliaries, temporary workspaces and rendered inspection images are not included.
