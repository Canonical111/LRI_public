# Direct nonperturbative circle-mode HT in two dimensions

## Result and scope

Completed **84 main curve points** at four bath cutoffs, plus **7 zero-mode/auxiliary refinements**. The measured interval is 0.1251 <= Delta_sigma <= 0.4999. Every main point was tuned by its spin and shadow gaps, not its thermal gap.

**These are finite-regulator spectra, not a controlled continuum Delta_epsilon curve.** The strong-coupling descendant checks and the short-range endpoint test are not satisfied. The curve is obtained by direct fixed-epsilon diagonalization, not a resummation or a polynomial fit.

## Physical interval and endpoints

In d=2, x=Delta_sigma=(2-s)/2 and epsilon=2s-2=2-4x. The interacting LR range is 1/8<x<1/2, ending at s*=7/4. The known endpoint pairs are (1/2,1) and (1/8,1). The thermal relation is nu^{-1}=2-Delta_epsilon, not 1-Delta_epsilon. These endpoint values do not enter the thermal calculation. See arXiv:1703.03430 and arXiv:1703.05325 for the shadow relation and exact 2d crossover data.

## What was diagonalized

The bath has two-index modes (a,b), energy x+a+b, angular momentum a-b, and squared weight (x)_a(x)_b/(a!b!). The zero mode (0,0) is diagonalized nonperturbatively. All positive-mode occupations satisfying N<=L are retained, with no additional particle cap. The first three cutoffs use L=6,8 with nz=20/osc=160 and L=10 with nz=24/osc=192; L=12 also uses nz=24/osc=192. Main scalar levels are in J=0, even spatial-reflection parity; the field parity is separate. Complete vertices, not individual ladder factors, are angular-projected.

Both r and g are tuned at every x to E_sigma-E0=x and E_chi-E0=2-x. Delta_epsilon is the untuned first excited even scalar gap. This branch is followed from weak coupling, without a complete nonperturbative OPE identification. The frozen total-energy regulator and its isolated vacuum counterterm are not used. The exact operator formulas are in docs/METHOD.md.

## Primary data

| x=Delta_sigma | L=6 | L=8 | L=10 | L=12 |
|---:|---:|---:|---:|---:|
| 0.4999 | 0.999933379246 | 0.999933379943 | 0.999933380398 | not evaluated |
| 0.495 | 0.996777148816 | 0.996778616266 | 0.996779554010 | 0.996780202575 |
| 0.475 | 0.985761821910 | 0.985780298093 | 0.985791057846 | 0.985797973901 |
| 0.45 | 0.975190572485 | 0.975222344082 | 0.975239207474 | 0.975249709323 |
| 0.4 | 0.960948073739 | 0.961089829066 | 0.961194172439 | 0.961283757727 |
| 0.35 | 0.953963229491 | 0.954634037481 | 0.955126932336 | 0.955521946464 |
| 0.3 | 0.954809624542 | 0.956226781331 | 0.957229975252 | 0.957978870531 |
| 0.25 | 0.963638418788 | 0.965559136280 | 0.966906935877 | 0.967845592298 |
| 0.2 | 0.979966254785 | 0.981809797593 | 0.983172703800 | 0.984027462156 |
| 0.15 | 1.004469514025 | 1.005648337058 | 1.006730630162 | 1.007216808971 |
| 0.13 | 1.017714300963 | 1.018545774918 | 1.019462848265 | 1.019713895759 |
| 0.126 | 1.020719955954 | 1.021481308464 | 1.022361570449 | 1.022557674182 |
| 0.1251 | 1.021415669469 | 1.022161278295 | 1.023033040695 | 1.023216362511 |

No continuum fitting or endpoint interpolation is performed. Lines in the plot only join computed finite-cutoff points.

## Validation

| Check | Largest observed discrepancy |
|---|---:|
| independent_original_normal_ordering_actions | 7.212e-13 |
| angle_average_vs_J0_projection | 2.6645e-15 |
| hermiticity_bilinear | 1.4211e-14 |
| moving_subspace_jacobian | 1.2689e-08 |
| tensor_ladder_actions | 7.1054e-15 |
| free_endpoint_gap_residual | 1.1102e-16 |
| reused_vs_fresh_ladders | 0 |

Across all primary/refinement records, maximum tuning residual is 8.9378e-11; maximum eigenvector residual is 2.039e-11; maximum orthogonality residual is 1.6098e-14. These are implementation and finite-matrix tests, not physical error estimates.

A sparse-index sorting bug was detected during development by comparing reused and fresh bath constructions. It was corrected by copying immutable edge metadata before CSR sorting. All affected outputs were invalidated and all delivered scans were rerun. The final validation explicitly tests both metadata immutability and multi-parameter spectra against freshly constructed bases.

### Independent small-epsilon comparison

Saved sixth-order finite-cutoff coefficients from the previous d=2 calculation are evaluated only AFTER each direct root solve. All weights, couplings and eigenvalues in the direct solve are evaluated at fixed x.

| L | epsilon | Direct thermal gap | Sixth-order finite-cutoff polynomial | Difference |
|---:|---:|---:|---:|---:|
| 4 | 0.005 | 0.99917359321813 | 0.99917359321818 | -4.841e-14 |
| 4 | 0.01 | 0.99836078632070 | 0.99836078632703 | -6.327e-12 |
| 4 | 0.02 | 0.99677455314153 | 0.99677455388776 | -7.462e-10 |
| 8 | 0.005 | 0.99917387851889 | 0.99917387851897 | -8.604e-14 |
| 8 | 0.01 | 0.99836188374328 | 0.99836188375235 | -9.067e-12 |
| 8 | 0.02 | 0.99677861626613 | 0.99677861733510 | -1.069e-09 |

The remaining differences include higher perturbative orders; they are not required to vanish identically. No fit in epsilon is used.

### Local and auxiliary refinement

| L | x | (nz,osc) old -> new | Change in thermal gap |
|---:|---:|---|---:|
| 8 | 0.126 | (20,160) -> (28,224) | -8.0158e-14 |
| 8 | 0.2 | (20,160) -> (28,224) | 4.976e-12 |
| 8 | 0.3 | (20,160) -> (28,224) | -2.4603e-13 |
| 8 | 0.45 | (20,160) -> (28,224) | -7.0588e-13 |
| 12 | 0.126 | (24,192) -> (32,256) | 1.1986e-12 |
| 12 | 0.2 | (24,192) -> (32,256) | -2.7427e-12 |
| 12 | 0.4 | (24,192) -> (32,256) | -5.9986e-12 |

These selected refinements resolve the local-mode truncation much better than the differences across bath cutoffs. They are not uniform bounds for every point.

## Independent angular-sector diagnostics

The first J=1 candidates should sit one unit above the corresponding scalar primaries. They are measured at the already tuned scalar couplings. Their identification is by continuity and low-level ordering, not a nonperturbative OPE determination.

| L | x | Spin-descendant spacing error | Thermal-descendant spacing error |
|---:|---:|---:|---:|
| 6 | 0.495 | 0.000035940 | 0.000112745 |
| 6 | 0.45 | 0.005617388 | 0.013144992 |
| 6 | 0.4 | 0.029941124 | 0.054131518 |
| 6 | 0.3 | 0.127766865 | 0.162326190 |
| 6 | 0.2 | 0.263244932 | 0.252545106 |
| 6 | 0.126 | 0.397025746 | 0.292914640 |
| 10 | 0.495 | 0.000044005 | 0.000106534 |
| 10 | 0.45 | 0.007230138 | 0.013304474 |
| 10 | 0.4 | 0.038872863 | 0.057005822 |
| 10 | 0.3 | 0.154222442 | 0.169632234 |
| 10 | 0.2 | 0.296628698 | 0.263044364 |
| 10 | 0.126 | 0.415385749 | 0.297441709 |

Near the short-range boundary, L=12 gives Delta_epsilon(0.1251)=1.023216362511, not approximately the expected endpoint 1. The finite difference over .1251 to .126 is -0.731876.

The independent near-crossover field theory predicts Delta_epsilon=1+O((x-1/8)^2), with a vanishing first derivative (arXiv:1703.03430, equation 13). Neither this property nor the descendant conditions are satisfied by the stronger-coupling finite-regulator data. Increasing L from 6 to 12 has not fixed that. These observations do not prove a nonzero continuum mismatch: unresolved nonuniform cutoff convergence and branch identification remain possibilities.

## What should happen next

Derive high-state matching for the actual circle-mode product projector and test it on held-out descendant and stress-tensor information. Do not transplant d=1 coefficients or the different d=2 total-energy vacuum window. Use multiple bath cutoffs and alternative regulators after consistent matching. Near x=1/8, the complementary short-range Ising plus generalized-free chi formulation can provide an independent route. Do not interpret the four-curve spread as a physical error band.

## Reproduction

README.md maps every script to its inputs/outputs. code/analyze.py, code/plot.py and code/write_report.py regenerate the CSVs, figures and this report from saved accepted JSONs. tests/validate.py and tests/weak_limit.py rerun the numerical checks. No claim is made of cluster-scale validation or production-grade multi-writer locking.
