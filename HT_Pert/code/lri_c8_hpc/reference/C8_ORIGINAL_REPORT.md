# Direct C8 from phi4 Hamiltonian truncation

## Main result

The coefficient is that of epsilon^8 with epsilon=2s-1 in the thermal dimension.
It is not the eighth coefficient of the expansion about the short-range endpoint.

**A new direct finite-cutoff calculation is complete. A matched physical C8 is not.**
There are 25 accepted raw cutoffs, all even Lambda=2,...,50, and 13 isolated-vacuum comparisons.

At the largest completed cutoff, C8_raw(50) = 2317638.0112179974094.
Conditional linked-tail fits suggest a raw-Hamiltonian intercept near 8.1 million.
That number is not a controlled continuum prediction or an uncertainty bound.

## 1. Raw direct coefficients

| Lambda | C4 | C6 | C7 | C8 |
|---:|---:|---:|---:|---:|
| 8 | 12.450246511 | 2257.375762 | -36303.024510 | 644581.163644 |
| 12 | 16.160216099 | 3104.930128 | -52483.173662 | 991985.624428 |
| 16 | 18.489692663 | 3683.760357 | -64104.629195 | 1251783.242269 |
| 24 | 21.445243408 | 4466.940382 | -80410.463044 | 1627810.176318 |
| 32 | 23.347608127 | 5000.110687 | -91834.828505 | 1897976.256289 |
| 40 | 24.725778214 | 5401.174430 | -100580.016727 | 2108010.158504 |
| 48 | 25.793662993 | 5720.896897 | -107637.160005 | 2279349.522080 |
| 50 | 26.025930588 | 5791.508475 | -109205.491838 | 2317638.011218 |

Each coefficient is extracted by formal-series algebra, not by sampling epsilon.
The production calculation uses fourth-order trial wavefunctions and their Rayleigh quotient.
All mode-weight jets through epsilon^7 and coupling tuning through epsilon^8 are retained.
The exact order-sufficient caps are P<=19 and Q<=16. The old seventh-order caps do not suffice.

The basis has 5,248,378 states at Lambda=50, including auxiliary parity sectors.
No C8 at Lambda=52 was accepted: the local memory limit was exhausted. This is recorded separately.

## 2. Validation

- Maximum lower-order discrepancy against the saved C0..C7 table: 1.46974e-09.
- Maximum exact C2 shell residual: 7.99361e-15.
- Maximum primary-gap tuning residual: 1.45519e-09.
- Independent full eighth-order recursion, both prescriptions, Lambda=2,4,6,8,12: maximum C/r/g discrepancy 2.77068e-08.
- Exact-rational nonorthogonal-basis recursion at Lambda=2,4,6,8,12: maximum C discrepancy 2.04891e-08.
- Enlarging the sufficient caps to P<=23,Q<=20 passes the tested comparisons.

These are numerical implementation checks, not estimates of physical matching or cutoff error.

## 3. Partial vacuum correction

Only H_raw+g(epsilon)^2 D(epsilon) is included here. D is the previously isolated missing-vacuum-shell term.
Both low-order wavefunctions and high-order couplings are recalculated. The calculation does NOT freeze the raw wavefunction.
No connected Dconn extension is assumed or fitted.

| Lambda | delta C4 | delta C7 | delta C8 |
|---:|---:|---:|---:|
| 12 | 0.060154343703 | 2.107848035 | 23.689575226 |
| 24 | 0.060758208206 | 2.318565304 | 32.900077242 |
| 40 | 0.061057751937 | 2.373171944 | 42.237019765 |
| 48 | 0.061144551666 | 2.377195039 | 45.809022702 |
| 50 | 0.061162793886 | 2.377121713 | 46.619378446 |

The C8 shifts do not bound missing connected-vacuum terms at orders three through eight or their subtraction iterations.
The previously discussed +0.0187 connected boundary effect on C4 is not transplanted to C8.
The cancellation of the isolated fourth-order logarithm against raw disconnected diagrams is not counted twice.

## 4. Conditional extrapolation

Assume a single leading channel Lambda^(-1/2) A(epsilon) exp[-log(Lambda) omega(epsilon)].
C2 and C3 are known control inputs. C4 through C8 are fitted, not supplied as targets.
Raw phi6 exponent inputs through omega5 are inherited from the prior study. omega6 is unknown and fitted at order eight.
The highest log term is fixed to -117649/(93312 sqrt(pi)) * log(Lambda)^6/sqrt(Lambda).

| Basis | fitted C8 intercept | fitted omega6 (nuisance) | eighth-order residual |
|---|---:|---:|---:|
| A | 8085634.855524 | -10493918.201 | 0.000482869 |
| B | 8077667.427311 | -10661714.067 | 9.26014e-06 |
| C | 8076893.793626 | -11065317.625 | 9.06019e-05 |

Reference fits use 16<=Lambda<=50. The three bases differ by subleading powers and logarithms.
Other linked-basis/window/cutoff-coordinate tests ending at 50 range roughly from 7.93 to 8.29 million.
That spread does not include every possible asymptotic channel or matching error, and is not an uncertainty interval.

For withheld-cutoff testing, fits trained only through 40 predict all higher coefficients recursively at 42..50.
Only C2 and C3 at the withheld cutoffs are supplied as controls.

| Basis | maximum withheld C8 error |
|---|---:|
| A | 0.297856705 |
| B | 0.054606723 |
| C | 0.036088231 |

Good nearby-cutoff prediction does not bound the extrapolated intercept.

### Adverse extrapolation test

Fitting C8 alone with the highest logarithm fixed, rather than linking lower-order tails, is unstable:

| Additional subleading terms, window 16..50 | fitted C8 | residual | scaled condition |
|---|---:|---:|---:|
| none | 10972505.763 | 0.00728411 | 2.08e+08 |
| L1 | 4636188.972 | 0.000268512 | 6.01e+10 |
| L1_L15 | 9521861.014 | 9.63453e-07 | 3.57e+12 |

These are not competing precise physical estimates. They demonstrate why the narrow linked-model spread cannot be promoted to a confidence interval.
Arithmetic perturbation and 70-digit linear-solve checks do not correct an incomplete tail model.

## 5. What is still required for a physical C8

A consistently connected vacuum-window correction through order eight, including mixed and iterated contributions, is not supplied or derived here.
Knowing C4 or its leading correction does not fix the new eighth-order vacuum and matching amplitudes.
Possible nonvanishing cutoff artifacts must be removed before declaring the fitted intercept a genuine limit.
The known lower-order coefficients and independent descendant identities provide acceptance tests for that matching.
More large-cutoff data would then test the matched tail model; they cannot be replaced by coefficient ratios or a Padé estimate.

The general effective-Hamiltonian framework is discussed in J. Elias Miro and J. Ingoldby, arXiv:2212.07266.
It does not provide this project-specific order-eight matching automatically.

## Reproduction

README.md lists all scripts and dependencies. docs/METHOD.md gives the mathematical construction.
results/ contains the accepted points and adverse diagnostics. No fitted source C8 is used as an input.
This research driver is not yet integrated with the private reviewed Expanse campaign layer.
