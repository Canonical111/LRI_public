# C6(1): the complete wheel becomes one unit-slope bivariate H value

## Result and scope

The accepted input is `inputs/C6_compact_H_expression.json`. It contains 18 fixed special-function values, including two wheel Kampé de Fériet values F4,F6 and one already compressed primitive value Hstar. All quantities are in the inherited normalization r6 = 2187 C6(1).

This continuation replaces the weighted pair

\[
-9432\pi^3\mathfrak F_4-5895\pi^4\mathfrak F_6
\]

by **one fixed bivariate Fox H value, with every slope equal to one**:

\[
\boxed{-393\pi\sqrt{89}\,\mathcal H_W.}
\]

The overall fixed-value count is 17 instead of 18. No explicit residual sum, integral, parameter derivative, or limiting operation is added to the active coefficient. The known polynomial and every other block are unchanged.

This is a new representation reduction using an INHERITED global wheel identity. It is not an elementary summation, proof of arithmetic dependence, or a new derivation of the physical graph/RG coefficient. The numerical checks below are not an independent interval certificate for Barnes quadrature. An optional interval is propagated from the previously proved wheel certificate, and is explicitly identified as such.

## 1. A single standard value with complete parameters

Put

\[
\alpha_W=\frac1\pi\arctan\frac58\in(0,1/2).
\]

In the Andrade–Rathie–Farias Definition B convention [1], define

\[
\boxed{
\mathcal H_W=
H_{2,2;\,5,5;\,2,2}^{0,2;\,2,3;\,2,2}
\left[
\begin{matrix}
(\frac12;1,1)^{[2]}:
 (\frac12,1)^{[4]},(\alpha_W,1);
 (\frac12,1),(0,1)\\
(-\frac12;1,1)^{[2]}:
 (0,1)^{[4]},(\alpha_W,1);
 (0,1),(\frac12,1)
\end{matrix}\;\middle|\;1,1\right].}
\tag{1}
\]

A superscript [r] means repetition. A shared triple is (parameter; slope in s, slope in t). A local pair is (parameter, slope). The numerator indices are:

- shared n=2, with no shared lower numerator factors;
- s-local m=2, n=3;
- t-local m=2, n=2.

Thus every parameter is 0, 1/2, -1/2, or the single explicit real number alphaW. In the s-local lists, the alphaW entries belong to both denominator groups; they do not cancel.

Here is the exact inverse-Mellin kernel, so the definition is unambiguous. Put

\[
N_\alpha(s)=
\frac{\Gamma(s)^2\Gamma(\frac12-s)^3}
{\Gamma(1-s)^2\Gamma(\frac12+s)
 \Gamma(s+\alpha)\Gamma(1-s-\alpha)},
\]

\[
P(t)=\Gamma(t)\Gamma(t+\tfrac12)
      \Gamma(\tfrac12-t)\Gamma(1-t).
\]

The kernel of (1) is

\[
\boxed{
N_{\alpha_W}(s)P(t)
\frac{\Gamma(\frac12-s-t)^2}{\Gamma(\frac32-s-t)^2}
=\frac{N_{\alpha_W}(s)P(t)}{(\frac12-s-t)^2}.}
\tag{2}
\]

The standard upward contours are Re(s)=1/4 and Re(t)=1/8, with measure ds dt/(2 pi i)^2. This specifies the named function, not another operation in the final coefficient.

The new wheel identity is

\[
\boxed{
W_0=24\mathfrak F_4+15\pi\mathfrak F_6
=\frac{\sqrt{89}}{\pi^2}\mathcal H_W.}
\tag{3}
\]

W0 includes n=0. For the legacy n>=1 notation,

\[
\mathscr W_c=\frac{\sqrt{89}}{\pi^2}\mathcal H_W
-\frac{(8+5\pi)\pi^2}{3}.
\]

No zero term is extracted from the currently accepted coefficient, and Delta E=0.

## 2. The inherited identity that makes the two wheel components compatible

For proof only, retain

\[
a_n=(1/2)_n/n!,\quad
h_n=\log2+H_n-H_{2n},\quad
\delta_n=\pi^2/3-4H_{2n}^{(2)}+2H_n^{(2)},
\]

\[
\tau_n=12\zeta(3)-16H_{2n}^{(3)}+4H_n^{(3)},
\quad D_4=\sum_{n\ge0}a_n^4\delta_n,
\quad D_6=\sum_{n\ge0}(4n+1)a_n^6\delta_n.
\]

The SOURCE-DERIVED global identity is

\[
\boxed{\sum_{n\ge0}a_n^4(8h_n\delta_n+\tau_n)=\pi^2D_6.}
\tag{4}
\]

It is equation (5) in Section 2 of `C6_central_binomial_wheel_reduction.md`, and is explicitly retained in `inputs/C6_wheel_Meijer_curvature_derivation.md`. We do not claim to prove (4) anew here. In particular, (4) is a summation identity, not a termwise equality of fourth- and sixth-power coefficients.

For an upward s-contour at Re(s)=1/4, let B[f]=(2 pi i)^-1 int f(s) ds. The two ordinary fourth-order Meijer kernels are

\[
M_1(s)=\frac{\Gamma(s)\Gamma(\frac12-s)^3}
 {\Gamma(1-s)^3\Gamma(\frac12+s)},\qquad
M_2(s)=\frac{\Gamma(s)^2\Gamma(\frac12-s)^2}
 {\Gamma(1-s)^2\Gamma(\frac12+s)^2}.
\]

Set d(s)=psi_1(1/2-s)-psi_1(1-s). At s=-n+epsilon, the source gamma expansions give

\[
M_1(s)=\frac{\pi a_n^4}{\epsilon}+O(1),\qquad
M_2(s)=\frac{a_n^4}{\epsilon^2}(1+8h_n\epsilon+O(\epsilon^2)),
\]

\[
d(-n+\epsilon)=\delta_n+\tau_n\epsilon+O(\epsilon^2).
\]

Summing the residues, and applying (4) in the second case, gives

\[
\boxed{B[M_1d]=\pi D_4,\qquad B[M_2d]=\pi^2D_6.}
\tag{5}
\]

These contour identifications, including their endpoint convergence, are also proved in the inherited curvature note. The new calculation therefore starts from the actual wheel, not the neighboring Dougall companion:

\[
W_0=8D_4+5\pi D_6
=\frac1\pi B[(8M_1+5M_2)d].
\tag{6}
\]

## 3. Sine addition combines the two local kernels

Gamma reflection [2] yields, with R(s)=[Gamma(s)/Gamma(s+1/2)]^4,

\[
M_1=R(s)\tan^3(\pi s),\qquad M_2=R(s)\tan^2(\pi s).
\]

It also gives

\[
N_\alpha(s)=M_2(s)\frac{\sin\pi(s+\alpha)}{\cos\pi s}
=\cos(\pi\alpha)M_1(s)+\sin(\pi\alpha)M_2(s).
\]

For alpha=alphaW,

\[
\cos(\pi\alpha_W)=8/\sqrt{89},\qquad
\sin(\pi\alpha_W)=5/\sqrt{89}.
\]

Consequently

\[
\boxed{8M_1+5M_2=\sqrt{89}\,N_{\alpha_W},\qquad
W_0=\frac{\sqrt{89}}\pi B[N_{\alpha_W}d].}
\tag{7}
\]

No wheel value is used to select alphaW: it encodes only the rational weights 8 and 5 already present in (6).

## 4. Evaluate the shared trigamma insertion as a second standard Barnes kernel

For Re(s)<1/2, the trigamma integral [3] gives

\[
d(s)=-4\int_0^1\frac{x^{-2s}\log x}{1+x}\,dx.
\tag{8}
\]

Use the elementary Mellin inversion

\[
\frac1{1+x}=\frac1{2\pi i}\int_{\Re z=1/4}
\Gamma(z)\Gamma(1-z)x^{-z}\,dz.
\]

On Re(s)=1/4, the x-integral is absolutely convergent. Integrating it gives

\[
d(s)=\frac4{2\pi i}\int_{\Re z=1/4}
\frac{\Gamma(z)\Gamma(1-z)}{(1-2s-z)^2}\,dz.
\tag{9}
\]

Now put z=2t, and apply gamma duplication [2]:

\[
\Gamma(2t)\Gamma(1-2t)=\frac{P(t)}{2\pi}.
\]

The measure contributes 2, while the denominator contributes 1/4. Therefore

\[
\boxed{
\frac1{2\pi i}\int_{\Re t=1/8}
\frac{P(t)}{(\frac12-s-t)^2}\,dt=\pi d(s).}
\tag{10}
\]

The factor pi in (10) is essential. It permits all slopes to remain ONE. Directly using (9) would instead leave a shared slope two and a different prefactor.

Inserting (10) into (7) identifies precisely the standard bivariate H kernel (2). This proves W0=sqrt(89) H_W/pi^2, and hence

\[
\boxed{-9432\pi^3\mathfrak F_4-5895\pi^4\mathfrak F_6
=-393\pi\sqrt{89}\,\mathcal H_W.}
\tag{11}
\]

## 5. Convergence and contour conditions

On s=1/4+iu, |tan(pi s)|=1. Gamma-ratio asymptotics [4] imply M1,M2 and therefore NalphaW are O((1+|u|)^-2), so their absolute vertical integrals converge.

The second local factor has the exact simplification

\[
P(t)=\frac{2\pi^2}{\sin(2\pi t)}.
\]

On t=1/8+iv it decays exponentially as |v| increases. Also

\[
\left|\frac12-s-t\right|\ge\frac18.
\]

Thus the absolute value of the double kernel is bounded by

\[
64\,|N_{\alpha_W}(1/4+iu)|\,|P(1/8+iv)|,
\]

an integrable product. The shared poles lie strictly to the right of the prescribed contours, since Re(s+t)=3/8<1/2. Local left/right gamma poles are separated. Repeated shared gamma factors require no regularization.

This supplies absolute convergence and Fubini justification. The x/Barnes interchange in (9) is likewise dominated by the integrable x weight x^-3/4 |log x| and the exponentially decaying z-kernel.

## 6. Full C6 update and exact checks

Only the two F4,F6 terms change. The new master coefficient is

\[
\begin{aligned}
2187C_6(1)={}&E+B_{\rm pol}+B_{\rm low}
+192\pi\sqrt{290}\,\mathcal G_6+B_8
-393\pi\sqrt{89}\,\mathcal H_W\\
&+96\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}
[b_r\mathcal Z_r-98p_r\nu_r\mathfrak J_r]
+7680\pi^3\mathcal H_*.
\end{aligned}
\]

The five-term finite sum, every seventh-sector coefficient, every primitive parameter, the entire 18-monomial known polynomial, and the source correction are preserved. The independent variable alphaW is unrelated to the alpha4 angle already used in the lower-period block.

`build_verify.py` passes 36 finite checks: parameter-to-kernel identifications, shared gamma cancellation, sine packing, residue coefficients, contour-scale factors, coefficient weights, exact full-C6 replacement, all preserved source blocks, and the value count. These are implementation/algebra checks, not 36 independent analytic theorems. The global identity (4) and upstream physical normalization remain inherited.

The count is 2 multiple-polylogarithms + 5 ordinary hypergeometric values + 3 univariate Meijer G values + 5 Kampé de Fériet values + 2 bivariate H values = **17**. This is a written-value count, not a transcendence-degree claim.

## 7. Numerical checks and interval scope

`numerical.py` evaluates the NEW gamma-product kernel NalphaW directly. Its outer Barnes integral uses the proved inner evaluation (10). That inner evaluation is separately checked by numerical integration of the actual t-gamma kernel at three s-points. The old F4,F6 rational interval midpoints are read only afterward for comparison.

At 65 decimal working digits:

\[
\begin{aligned}
\alpha_W&=0.17780768448935275311550358750224810754418503323744367797060811819\ldots,\\
\mathcal H_W&=82.198372839948704474444779671977025125648737334356408964906749531\ldots,\\
W_0&=78.570312136547117160682748886719852438531916411450796117300294653\ldots.
\end{aligned}
\]

The wheel discrepancy relative to the old component midpoints is 1.520e-64 or less; the discrepancy in r6 wheel units is 2.490e-60 or less. The three direct inner-Barnes tests have largest discrepancy less than 4.748e-66. A separate 35-digit run is included.

These are floating-point checks, NOT a new rigorous numerical Barnes error bound. No independent two-dimensional quadrature of the complete H value and no fresh all-sector C6 evaluation were performed.

`propagate_interval.py` separately propagates the inherited exact wheel/pi intervals through H_W=pi^2 W0/sqrt(89), with an integer-square-root enclosure and exact rational outward rounding. The resulting interval width is below 2.221e-146. This is a rigorous *propagation* of the accepted source certificate, not a new proof of the wheel identity or of the physical six-loop calculation.

## Reproduction

Python 3, SymPy, and mpmath suffice. No web access is used by the scripts.

```
python build_verify.py
python numerical.py 35 --inner
python numerical.py 65 --inner
python propagate_interval.py
```

`results/expression.json` is the full updated formula. `FORMULA.md` is self-contained, including every unchanged fixed-value parameter list. `results/exact_checks.json`, the two numerical reports, and `results/propagated_interval.json` distinguish algebra, empirical numerical checks, and inherited interval propagation.

## Sources

[1] J. A. A. Andrade, P. N. Rathie, R. B. A. Farias, *Exact Bayesian computation using H-functions*, Computational and Applied Mathematics 37 (2018), 2277–2293. Definition B, equations (4)–(8). https://doi.org/10.1007/s40314-017-0451-z . Author-posted full text: https://www.researchgate.net/publication/316770540_Exact_Bayesian_computation_using_H-functions . This supplies the standard bivariate-function convention, not a C6 identity.

[2] NIST DLMF 5.5, gamma reflection and duplication: https://dlmf.nist.gov/5.5 .

[3] NIST DLMF 5.15, trigamma series and recurrence: https://dlmf.nist.gov/5.15 .

[4] NIST DLMF 5.11, gamma-ratio asymptotics: https://dlmf.nist.gov/5.11 .

[5] NIST DLMF 16.17 and 5.12, standard Mellin/Beta conventions: https://dlmf.nist.gov/16.17 ; https://dlmf.nist.gov/5.12 .

The supplied `C6_central_binomial_wheel_reduction.md`, section 2, supplies the global identity (4). Its exact scope states that graph/RG identification and earlier project identities are inherited. The corresponding curvature derivation is preserved in `inputs/` for independent inspection of all contour normalizations used here.
