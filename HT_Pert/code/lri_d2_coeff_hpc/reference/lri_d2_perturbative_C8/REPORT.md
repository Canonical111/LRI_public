# Direct 2D Hamiltonian-truncation coefficients through C8

## Main result and limitations

The uploaded 2D nonperturbative Hamiltonian has now been expanded directly
through epsilon^8. Raw and consistent-window coefficients were calculated at
every even bath cutoff L=0,2,...,20. The two primary gaps remain the ONLY tuning
conditions. No thermal coefficient or finite-epsilon polynomial fit determines
these numbers. The old 1D mode formulas and 1D asymptotic tails are not reused.

**These are complete finite-cutoff coefficients of the uploaded product-regulator
model, not a completed physical continuum C8 calculation.** No continuum fit or
precision interval for C3..C8 is produced. The nonperturbative HPC ZIP is preserved
unchanged and is used as an independent finite-epsilon oracle.

## 1. Largest-cutoff coefficients

At L=20, x=(2-epsilon)/4 and Delta_E=sum_(k=0)^8 C_k epsilon^k+O(epsilon^9):

| k | Raw C_k | Consistent-window C_k |
|---:|---:|---:|
| 0 | 1.000000000000 | 1.000000000000 |
| 1 | -0.166666666667 | -0.166666666667 |
| 2 | 0.300757793850 | 0.300757793850 |
| 3 | -0.735677875239 | -0.735677875239 |
| 4 | 3.274739159298 | 3.279013086211 |
| 5 | -21.220896745679 | -21.217890789738 |
| 6 | 168.006886192838 | 168.046624225296 |
| 7 | -1543.890838156440 | -1544.376650114721 |
| 8 | 15945.540706015912 | 15950.059007240465 |

The digits describe numerical evaluation of a finite model, not physical
accuracy after regulator removal. C0=1 and C1=-1/6 follow exactly from the
Hamiltonian normalization and primary constraints.

## 2. High-order cutoff dependence

| L | Consistent C6 | Consistent C7 | Consistent C8 |
|---:|---:|---:|---:|
| 4 | 84.932727034342 | -687.690167139807 | 6270.278877673581 |
| 8 | 115.628698361457 | -993.558731518867 | 9600.803818686341 |
| 12 | 137.667356199360 | -1221.643713172784 | 12184.666674528286 |
| 16 | 154.545134294052 | -1399.877348845496 | 14250.138382324280 |
| 18 | 161.642319272278 | -1475.632311601670 | 15138.683823427276 |
| 20 | 168.046624225296 | -1544.376650114721 | 15950.059007240465 |

All intermediate even cutoffs are in results/coefficients_C0_C8.csv. The L18->20
change in C8 is about 811.4, much larger than the numerical comparison errors.
A precise physical C8 cannot be obtained by calling the last row converged.

The exact second-order continuum limit is C2=4 log(2)/9=0.3080654135821979...,
whereas C2(20)=0.3007577938498298. Even this lowest nonlinear coefficient still
has an appreciable cutoff tail. No analogous complete C6,C7,C8 tail is supplied
by the present new calculation.

## 3. The useful symmetries

Circle modes carry exact angular momentum J=a-b. The scalar primaries use J=0,
spatial reflection even under a<->b, and definite field parity. Reflection-orbit
normalization is retained exactly. The identity N-J even means scalar vacuum
subproblems only occur at even bath levels.

In addition, an exact reachable-state proof reduces the auxiliary ladder space
to N+|J|<=L. It does NOT change the physical scalar cutoff N<=L or remove angular
sectors that can contribute. Annihilation cannot increase N+|J|; creation cannot
return from outside the envelope to a legal scalar endpoint in a normal-ordered
vertex. Unreduced calculations check this optimization.

At L16, the reflection-reduced auxiliary space drops from 1,122,136 to 329,428
states without a physical change. The largest L20 run uses 2,397,430 auxiliary
states, with 298,728 field-even and 322,954 field-odd scalar states. The input's
basis graph builder is reused; the new normal-order and Taylor engines are
separate from its dressed finite-coupling solver.

## 4. How the coefficients are obtained

Mode weights are differentiated by the exact recurrence
v_n=(n-1/2-epsilon/4)v_(n-1)/n, then u_ab=sqrt(v_a v_b). Angular projection occurs
only after complete Gaussian-normal-ordered vertices.

The same order-by-order primary tuning and subcutoff-vacuum recursion as in the
1D coefficient work is applied to the actual TWO-dimensional matrices. Four
wavefunction orders determine eighth-order energies through the stationary
normalized Rayleigh quotient, with all Hamiltonian, mass/quartic, vacuum and
normalization terms present. Full-order recursion independently checks it.

The exact degree-eight support bounds are P<=19 and Q_positive<=16. Degree seven
uses smaller independent support P<=15,Q<=12 and agrees through C7 at L16 and L20.
No reduced numerical precision, fastmath, or coefficient pruning is used.

## 5. The window is not an epsilon^5 model

The consistent product window is D_L(N)=Ev(L)-Ev(L-N), with all Ev calculated
in the corrected model at the SAME outer r,g. It is expanded directly to order
eight. The previous 1D frozen-energy window uses a different state-dependent
argument and is not transplanted here.

Because D annihilates every zero-bath reference, its first primary-energy effect
is at order four. Raw and consistent C0..C3 agree. The literal raw-vacuum-table
prescription agrees with consistent through order FIVE and first differs at
order SIX. Four literal controls document this rather than assume equivalence.

An exact new check derives the first corrected-minus-raw shift from the
first-order wavefunctions and the exact vacuum coefficient. With K=L/2,

    Ev,2(L)=-(K+1)(K+2)/216,
    delta C4(L)=sum_(n=1)^K n(2K+3-n)c_n^2 b(n)/972,
    c_n=(1/2)_n/n!,
    b(n)=1/[9(2n-1)^2]+1/(4n^2)+1/(2n+1)^2+1/[36(n+1)^2].

This is independent of the new fourth-order energy recursion. Its own asymptotic
behavior contains A*L-5 log(L)/(8748*pi)+O(1), with
A=0.0002207292996452666338602081.... That is a statement about the WINDOW DIFFERENCE,
not about raw or complete corrected C4 separately. Raw artifacts may cancel
those terms; the complete asymptotic cancellation is not proved here. It is a
reason to treat matching and numerical accuracy as separate issues.

## 6. Independent validation

| Check | Largest observed difference |
|---|---:|
| Exact finite C2 sum | 2.498e-15 |
| Exact second-order vacuum | 1.665e-16 |
| Independent fourth-order window sum | 9.35e-15 |
| All coefficient/oracle/symmetry tests, scaled | 9.745e-15 |

The rational oracle independently enumerates circle occupations and uses exact
polynomial coordinates, with no reflection/envelope reduction and no stationary
quotient. It computes raw/consistent C0..C8 at L=0,2,4,6. It shares no numerical
matrix elements or benchmark targets with the main engine.

The actual uploaded dressed solver supplies a third check. At L2,L4 and
epsilon=.08,.04,.02, its unexpanded eigenvalues and nonlinear vacuum windows
are compared with the new eighth-order polynomial at the SAME Taylor coupling
series. There is no coefficient extraction by fitting or extra retuning.

- L=2, raw: remainder-halving factors 485.106, 500.814.
- L=2, consistent: remainder-halving factors 485.104, 500.953.
- L=4, raw: remainder-halving factors 479.901, 497.504.
- L=4, consistent: remainder-halving factors 479.910, 497.861.

The factors approach 512, as expected for a ninth-order remainder. This verifies
the finite-regulator expansion, not the physical continuum.

Exact rational stationary-quotient tests, reference diagonals, Hermiticity,
enlarged support, and deliberately wrong intermediate-angular projections are
also included. The last give a negative control rather than a fitted success.

The four new regeneration/validation drivers passed. A further 46 selected
original numerical and optimization tests passed in a disposable copy with a
four-thread Numba ceiling. An initial environment capped Numba at one thread
and failed its four-thread test; the unchanged rerun passed. The original
cluster/launcher suite was not repeated.

## 7. Reproduction and next step

README.md maps the commands to every output. The largest consistent run took
66.2 seconds locally with a peak process RSS of 2.69 GiB.
These are local observations, not MPI or cluster performance claims. The new
wrappers are not integrated into the uploaded cross-node dispatcher.

The next physical task is a 2D-specific high-state matching and tail study of
this same regulator (or a separately labelled factorizing-parent branch).
The present complete finite arrays, exact Fraction oracle, and held-out source
solver checks provide a reproducible reference for that task. No OPE calculation
or known thermal C6/C7/C8 value is needed to obtain the coefficients supplied here.

