# Independent phi6-sector calculation and a joint thermal extrapolation through C7

## Result and scope

This calculation extends the oscillator Hamiltonian and two tuning conditions in
`Hamitonian.md` and the Hamiltonian-truncation subsection of
`lri_d1_epsilon_expansion_detailed.tex`. It uses a new spectral channel, phi6, to
supply exponent inputs to the cutoff-tail fit. It does **not** substitute the
known diagrammatic C4,...,C7 as fit targets.

The fixed-exponent reference fits give the following infinite-cutoff intercepts
for the **unmodified two-coupling Hamiltonian**:

| Subleading basis | C4 | C5 | C6 | C7 |
|---|---:|---:|---:|---:|
| A | 45.340475 | -734.447427 | 14359.6252 | -323483.6760 |
| B | 45.330026 | -733.516090 | 14345.9173 | -323123.1715 |
| C | 45.349132 | -734.046457 | 14350.3053 | -323011.2470 |

The displayed digits identify fitted intercepts, not their accuracy. A numerical
summary is C6_HT about 1.435e4 and C7_HT about -3.23e5. A broader set of
subleading-basis/window/cutoff-coordinate tests gives C6 estimates from about
13858 to 14548 and C7 estimates from about -329447 to -315392, across 4032
combined gap-input/basis/window/cutoff-coordinate variations. These are observed
model spreads, **not confidence intervals, rigorous enclosures, or bounds on
Hamiltonian-matching error**.

The finite-cutoff phi6 gap has been calculated through epsilon^5, the thermal gap
through epsilon^7. An isolated vacuum correction has been included and tested,
and its continuum shift through epsilon^3 is determined analytically below.
**Complete Hamiltonian matching through epsilon^5 has not been derived.** In
particular, a raw spectral gap cannot simply be relabelled a fully matched CFT
scaling dimension.

## 1. Hamiltonian and tuning

We retain the source prescription

\[
H=H_0+r(\epsilon)M(\epsilon)+g(\epsilon)V(\epsilon),
\quad H_0=N+P/4-\epsilon P/4,
\]

\[
u_n^2=\frac{((1-\epsilon)/2)_n}{n!},\qquad
M=(B^\dagger)^2+2B^\dagger B+B^2,\quad
V=\frac1{12}\sum_{j=0}^4 {4\choose j}(B^\dagger)^jB^{4-j}.
\]

Here B is the sum of u_n a_n. Sphere parity is projected only after a complete
vertex, not between its ladder factors. The cutoff N+P/4<=Lambda is frozen at
epsilon=0; Lambda is even. The couplings are tuned to

\[
E_1-E_0=(1-\epsilon)/4,\qquad E_3-E_0=(3+\epsilon)/4.
\]

All oscillator-weight epsilon jets needed at the requested order are retained.
The gap starts with

\[
D_6(\epsilon,\Lambda)=E_{\phi^6}-E_0
=\frac32+\frac72\epsilon+\sum_{k=2}^5 d_k(\Lambda)\epsilon^k+O(\epsilon^6).
\]

The d_k are **not** the thermal C_k. If the gap is identified with the leading
irrelevant operator, its cutoff exponent is D6-1. That identification remains an
assumption for the unmatched regulator.

## 2. Completed numerical calculations

A second-order trial wavefunction determines an energy through epsilon^5 by
Rayleigh stationarity. Starting from six zero-mode particles, P<=14 and at most
eight nonzero-mode particles suffice exactly at this perturbative order. A
first-order trial state, P<=10 and at most four nonzero-mode particles, suffices
through epsilon^3. The bases also include the auxiliary parity sectors needed by
individual ladder operations.

The fifth-order phi6 calculation has 26 completed even cutoffs: 4 through 50,
then 54 and 58. The third-order dataset extends this to 64, 80, 96, 112 and 128.
A run at 62 in the fifth-order basis exhausted the available resources; no result
from that attempt is used.

Representative raw phi6 coefficients are:

| Lambda | d2 | d3 | d4 | d5 |
|---|---:|---:|---:|---:|
| 24 | -26.7685581618 | 432.4844822557 | -9073.6699372266 | 223012.3073705847 |
| 40 | -27.4250673235 | 458.3553255960 | -9912.7121159922 | 250090.2412238788 |
| 50 | -27.6580098596 | 467.7583032025 | -10222.4289079871 | 260308.6887383714 |
| 58 | -27.7979580209 | 473.4779225740 | -10412.3505556428 | 266636.4969142783 |

The CSV is authoritative for numerical records. A metadata string in the raw
third-order production JSON says fifth-order; the `degree` field, coefficient
array length and this report correctly identify those additional runs as third
order. The generator has been corrected for subsequent runs.

The thermal calculation now contains **all 25 even cutoffs from 2 to 50**. The
new endpoint is

\[
C_7(50)=-109205.49183788928,
\]

with C6(50)=5791.508474879353. The raw sixth/seventh-order tails are therefore
still large compared with the desired intercepts.

At cutoffs 4,6,8, the phi6 Rayleigh-quotient calculation was checked against a
full fifth-order Rayleigh-Schrodinger recursion, separately for both prescriptions.
The largest observed absolute discrepancy is below 8e-10. The previous seventh-
order full-recursion validation is retained as `prior_c7/C7_validation.json`.
These test the implementation; they are not physical uncertainty estimates.

## 3. Exact second-order checks and an additional boundary channel

Let A=pi+4 log(2), v_m=(1/2)_m/m!, and m=Lambda-2. Independent oscillator sums
satisfy the exact rational identity

\[
d_2(\Lambda)+45 C_2(\Lambda)
=\frac{(48m+104)v_m+m+91}{54(m+1)}.
\]

It follows that

\[
\omega_2^{\rm raw}=-5A+\frac1{54}=-29.552388360629354\ldots.
\]

There is a useful stronger diagnostic. With
T2(Lambda)=C2(Lambda)-A/9,

\[
d_2(\Lambda)-\omega_2^{\rm raw}
=-45T_2(\Lambda)
+\frac{(48m+104)v_m+90}{54(m+1)}.
\]

Therefore

\[
d_2(\Lambda)-\omega_2^{\rm raw}
=\frac{208}{9\sqrt\pi}\Lambda^{-1/2}
+\frac5{3}\Lambda^{-1}+O(\Lambda^{-3/2}).
\]

A local phi6 insertion alone would give the ratio -45 between the phi6-gap and
thermal tails. Indeed, for h times the normal-ordered sixth-order vertex, its
zero-mode diagonal element is h p(p-1)(p-2)/18. Tuning the phi3 gap gives
 delta g=-h/9; hence delta E2=-h/9 and delta E6=5h. The actual raw cutoff gap
contains the additional leading amplitude 8/(9 sqrt(pi)).

This is an exact demonstration of a spectator-dependent boundary contribution
at the **same inverse-cutoff power** as the putative local phi6 channel. It does
not by itself disprove the proposed thermal leading exponent, but it prevents
us from treating the gap's own tail as an established single-channel identity.
Free-leading-log variants are included among the gap-fit sensitivity tests.

One way to derive the boundary term is to decompose the all-creation matrix
norm on the p=6 reference into powers of F(q)=(1-q)^(-1/2):

\[
\|V_{+4}|6\rangle\|^2(q)
=\frac16F^4+4F^3+15F^2+\frac{40}{3}F+\frac52.
\]

The absolute-energy cutoff removes one extra even mode shell from this channel.
The coefficient of F^4 produces 1/54, and the other powers give the remaining
terms in the exact boundary identity.

## 4. Vacuum matching: an exact improvement through third order

The isolated diagonal correction used for comparison is g(epsilon)^2 D(epsilon),
where on a free basis state with E_i^0=N_i+P_i/4,

\[
D_i(\epsilon)=-\frac16
\sum_{\substack{m\ {\rm even}\\m+1\leq\Lambda<m+1+E_i^0}}
\frac{(2-2\epsilon)_m}{m!\,(m+1-\epsilon)}.
\]

All thresholds are fixed at epsilon=0. This restores the missing disconnected
vacuum shells, not the complete effective Hamiltonian. Its effect on the source
calibration states vanishes at low orders; the second-order trial states are
unchanged and determine both prescriptions through epsilon^5. A separate full
recursion explicitly checks this statement.

For the phi6 reference precisely the m=Lambda-2 vacuum shell is restored. Hence

\[
\delta\omega_2=-\frac1{54}.
\]

The quadratic coupling coefficient also has an exact shell formula:

\[
g_2(\Lambda)=C_2(\Lambda)+\frac19\left[
H_\Lambda-\frac1\Lambda+
2\psi(\Lambda/2+1/4)-2\psi(1/4)\right].
\]

It has the large-cutoff expansion

\[
g_2(\Lambda)=\frac13\log\Lambda+\frac{2A}{9}
+\frac{\gamma_E}{3}+O(\Lambda^{-1/2}).
\]

The finite-cutoff third-order vacuum correction is exactly

\[
\delta d_3(\Lambda)=-\frac{g_2(\Lambda)}9+
\frac{2H_{\Lambda-1}-2-1/(\Lambda-1)}{54}.
\]

The logarithms cancel at infinite cutoff, leaving the new analytic result

\[
\boxed{\delta\omega_3=-\frac{2A+3}{81}
=-0.18306620681060679\ldots.}
\]

The finite rational formulas agree with the saved numerical C2 and g2 to about
3.2e-14 and 1.9e-14, respectively. The predicted vacuum difference in d3 agrees
to about 7.0e-14 across the tested cutoffs. The numerical effect of this same
isolated correction on d4 and d5 is also recorded; it is not a full fourth/fifth-
order matching prescription.

The vacuum shift is far too small to explain the difference between the new
omega3 near 556 and the effective values 380--417 obtained by allowing omega3 to
float in the previous thermal fits.

## 5. Independent gap-only extrapolations

For the cubic gap coefficient, fits use data extending to Lambda=128. A
reference fit with basis B and 24<=Lambda<=128 gives

\[
\omega_3^{\rm raw}\simeq556.2143040.
\]

The same model trained only through 80 predicts the withheld 96,112,128 values
with maximum discrepancy about 5.2e-6. Across reasonable changes of basis and
allowing the leading log to float, the continuum intercept varies by tenths;
556.2 should not be interpreted as many certified digits. This computation uses
only the phi6 channel, not the high-order thermal coefficients.

Fixing that cubic input, the fifth-order gap data through 58 give a reference
exponent series

\[
\omega_{\rm raw}(\epsilon)\simeq
\frac12+\frac72\epsilon
-29.5523883606\epsilon^2
+556.2143040\epsilon^3
-13457.6893\epsilon^4
+376964.5614\epsilon^5.
\]

Only omega1 and omega2 in this display are exact continuum inputs here. The
higher numbers are fit parameters of a gap-only extrapolation. Complete gap-fit
basis/window variations are retained in the JSON files and propagated into the
thermal study. The same oscillator framework and tuning conditions are shared;
this is an independent spectral channel, not a separately implemented theory.

## 6. Joint thermal-tail model and withheld-data tests

We use the conditional leading-channel structure

\[
T(\epsilon,\Lambda)=\Lambda^{-1/2}
\left(\sum_{k\geq2} a_k\epsilon^k\right)
\exp[-\log\Lambda\sum_{j\geq1}\omega_j\epsilon^j]+
R(\epsilon,\Lambda).
\]

Define

\[
e_j(\ell)=[\epsilon^j]\exp[\ell\sum_{k\geq1}\omega_k\epsilon^k].
\]

Then we fit the transformed sequences

\[
C_n(\Lambda)+\sum_{j=1}^{n-2}e_j(\log\Lambda)
[C_{n-j}(\Lambda)-C_{n-j}(\infty)]
=C_n(\infty)+a_n\Lambda^{-1/2}+\widetilde R_n(\Lambda).
\]

Known C2 and C3 are intentional low-order control inputs. C4 through C7 are
successively fitted. The leading basis function is the actual T2(Lambda),
proportional to Lambda^(-1/2), rather than an independently estimated pure power.
No C4--C7 target is supplied. The externally determined omega3,omega4,omega5 are
not refitted to the thermal channel.

The subleading bases are:

- A: Lambda^-1, Lambda^-3/2, (log Lambda)Lambda^-3/2, Lambda^-2.
- B: A plus (log Lambda)Lambda^-2.
- C: Lambda^-1, (log Lambda)Lambda^-1, Lambda^-3/2, (log Lambda)Lambda^-3/2.

The full program also tests simpler/more flexible bases, lower cutoffs
12,16,20,24, and the cutoff coordinates Lambda-2, Lambda, Lambda+2. The latter
are reparametrizations of the tail ansatz, not new Hamiltonian simulations.

With training restricted to 16<=Lambda<=40, the reference bases predict the
withheld C7 values at 42,44,46,48,50 with maximum absolute errors approximately
0.012, 0.0036, and 0.013. Predictions are recursive: the withheld C4,C5,C6 values
are not used. The low-order C2,C3 control variates at those cutoffs are used.
The phi6 spectral input is independent of the held-out thermal C7 values.

The good nearby-cutoff predictions should not be confused with a bound on the
infinite-cutoff extrapolation. At the reference gap input, tested subleading bases/windows/shifts give
C7 intercepts from approximately -327620 to -317407. A Cartesian-product test
of 4032 combined gap-input/basis/window/cutoff-coordinate variations expands
this to -329447 through -315392; see `combined_stress_summary.json`. Propagating alternative
raw gap fits through the three thermal reference bases also shifts C7, with the
full output retained in `gap_input_propagation.json`.

The reference linear solves were checked by 65-digit QR. Bounded numerical
perturbations of the input coefficients, with a largest amplitude of 5e-7 on C7,
were applied in 128 trials. The largest observed reference-model C7 intercept
change is below 0.4. Neither the perturbation sizes nor these trials constitute a
rigorous floating-point bound, but they indicate that tail-model uncertainty is
larger than the tested arithmetic sensitivity.

## 7. Physical interpretation and limitations

The results support a conditional HT intercept near -3.23e5 for C7 and 1.435e4
for C6. They do not turn the known diagrammatic C6 allowance into an independently
verified error bar.

The new C5 intercepts are about -733.5 to -734.4, rather than the diagrammatic
-731.1394766. Likewise C4 remains near 45.33--45.35 rather than 45.4248801. These
comparisons are made **after** fitting. The discrepancies reinforce the need to
separate matching errors and unresolved tail contributions from numerical solve
errors. The previous thermal-only fitted exponent coefficients should be viewed
as effective fit parameters, not independent predictions of the phi6 spectrum.

The attached source does not specify the complete cutoff-dependent effective
Hamiltonian through fifth order. The derivation above completes an isolated
vacuum contribution, not that full matching problem. Nonlocal matching terms are
part of systematic Hamiltonian-truncation treatments; relevant primary sources
checked for this analysis are Cohen et al., *Hamiltonian Truncation Effective
Theory*, arXiv:2110.08273, and Elias Miro and Ingoldby, *Effective Hamiltonians and
Counterterms for Hamiltonian Truncation*, arXiv:2212.07266. Those general papers
do not supply the missing model-specific coefficients here.

## 8. Reproduction

This archive contains the source code, completed finite-cutoff arrays, gap-only
fits, fixed-exponent thermal fits, sensitivity tests, exact boundary checks and
machine environment metadata. The convenient data tables are
`thermal_coefficients_through_C7.csv` and `phi6_gap_coefficients.csv`.

Reassemble all inexpensive saved-data fits and checks with:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python reproduce_saved_analysis.py
```

Regenerate small-cutoff phi6 validation:

```bash
OPENBLAS_NUM_THREADS=1 python compute_phi6.py --cutoffs 4 6 8 --validate --output validation_new.json
```

Regenerate selected fifth-order phi6 or third-order larger-cutoff records:

```bash
OPENBLAS_NUM_THREADS=1 python compute_phi6.py --cutoffs 16 24 32 40 --degree 5 --output gap_new.json
OPENBLAS_NUM_THREADS=1 python compute_phi6.py --cutoffs 64 80 96 --degree 3 --output gap3_new.json
```

Regenerate selected seventh-order thermal records:

```bash
OPENBLAS_NUM_THREADS=1 python check_lri_C7.py --cutoffs 12 24 36 40 --output thermal_new.json
```

Large Fock-space jobs require substantially more memory than the saved-data
analysis. The scripts retain the actual normalization, parity and cutoff
prescription and should not be combined with differently normalized graph data.
