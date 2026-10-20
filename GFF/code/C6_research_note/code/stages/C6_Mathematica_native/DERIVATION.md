# C6(1) in Mathematica built-ins, with explicit one-dimensional quadrature

## Result and limitation

The input is `inputs/C6_standard_primitive_expression.json`, with normalization
`r6 = 2187 C6(1)`. The graph/RG identification, source correction, and earlier
period identities are inherited. This note does not rederive the six-loop
physical coefficient.

The previous expression uses seven Kampé de Fériet values, four bivariate Fox
H-values, and a single-valued HPL. A published name is not the same thing as a
Mathematica built-in. In particular, the documented `FoxH` and `MeijerG` have
one function argument and do not implement the bivariate values in that input.

This continuation replaces those uncommon function heads by an explicit real
one-dimensional integral whose integrand uses only `HypergeometricPFQ`,
`PolyLog`, `EllipticK`, and elementary functions. The fixed-value part uses
`Gamma`, `Zeta`, `Catalan`, ordinary `HypergeometricPFQ`, and classical `PolyLog`.
`CarlsonRF` is used in the numerical code only as a stable built-in form of a
complementary `EllipticK`.

**This is an exact quadrature representation, NOT a finite special-value-only
closed form.** Combining the four integrands does not prove that the four
periods are dependent. No parameter derivatives or infinite sums occur in the
active formula, but one explicit definite integral does remain.

A genuine finite simplification obtained on the way is the reduction of all
three univariate Meijer G solutions of the primitive to products of complete
elliptic integrals. The known polynomial has 19 expanded monomials instead of
21. None of these claims is a period-independence or minimality statement.

## 1. Complete formula

Put
\[
 A=\pi+4\log2,\qquad Q=\Gamma(1/4)^4/\pi,\qquad G=\operatorname{Catalan}.
\]
Let \(\mathcal O\) be the finite combination of thirteen ordinary hypergeometric
values specified in Section 2. Then
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_{\rm native}+\mathcal O
 -39168\pi^2\Im\operatorname{Li}_3((1+i)/2)\\
 &+\int_0^1\left[R_{\rm pol}(x)+R_W(x)+R_7(x)+R_P(x)\right]dx .
\end{aligned}} \tag{1}
\]
The four integrands are explicit below. For numerical work they are integrated
separately, so cancellation in one part does not hide integration error in another.

The complete known part is
\[
\begin{aligned}
E_{\rm native}={}&-\frac{144Q^3}{\pi}
 +\frac Q8[63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)]\\
&+Q^2(29\pi-249A)+\mathcal P_{\rm native},
\end{aligned}\tag{2}
\]
where
\[
\boxed{\begin{aligned}
\mathcal P_{\rm native}={}&\frac{21}{640}A^5+\frac7{64}A^3\pi^2
 +\frac{6045}{64}A^2\pi^3+\frac{7863}{16}A^2\zeta(3)\\
&+96AG(32G-45\pi^2)-\frac{83067}{640}A\pi^4+22848G\pi^3\\
&+\frac{164927}{128}\pi^5-\frac{424371}{16}\pi^2\zeta(3)
 -\frac{805959}{8}\zeta(5).
\end{aligned}}\tag{3}
\]
The existing \(-144Q^3/\pi\) term remains included once. There is no new primitive
or wheel zero-index compensation. The saved source correction remains included once.

## 2. The finite ordinary-function block

Repeated parameters are denoted by \(a^{[j]}\). Define ordinary functions
\[
U_4(w)={}_4F_3((1/2)^{[4]};1^{[3]};w),
\]
\[
U_6(w)={}_7F_6(5/4,(1/2)^{[6]};1/4,1^{[5]};w),
\]
\[
U_8(w)={}_9F_8(5/4,(1/2)^{[8]};1/4,1^{[7]};w).
\]
Also
\[
H_-={}_7F_6(1,(1/4)^{[6]};(3/4)^{[6]};1),\quad
H_0={}_6F_5((1/2)^{[6]};1^{[5]};1),
\]
\[
H_+={}_7F_6(1,(3/4)^{[6]};(5/4)^{[6]};1).
\]
For \(t=r/8\), \(a=(r+2)/8\), \(b=(r+6)/8\), put
\[
Z_r^{(q)}(w)=t\left[\frac{\Gamma(a)}{\Gamma(b)}\right]^q
 {}_{q+2}F_{q+1}(1,1+t,a^{[q]};t,b^{[q]};w).
\]
Use \(Z_r(w)=Z_r^{(7)}(w)\), and \(Y_1=Z_1^{(8)}(1)\),
\(Y_7=Z_7^{(8)}(1)\). Matching parameters can be cancelled; the Wolfram
file preserves the already cancelled input parameter lists.

With
\[
C_s=60Q-\frac{105}{4}A^2-9A\pi-\frac{2469}{4}\pi^2,\qquad
C_d=96Q-42A^2-18A\pi-1227\pi^2,
\]
all fixed ordinary terms are
\[
\begin{aligned}
\mathcal O={}&4\pi^3C_dU_4(1)+2\pi^4C_sU_6(1)
 +\frac{288Q^3}{\pi}H_- -2496\pi^5H_0
 +\frac{6291456\pi^5}{Q^3}H_+\\
&+\pi^6(4932-5004\sqrt2)U_8(1)\\
&+556\pi^2[(17+12\sqrt2)Y_1-(17-12\sqrt2)Y_7]
 +96\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}b_rZ_r(-1).
\end{aligned}\tag{4}
\]
The last sum is finite. To specify its weights, set
\[
c_7=\cos^7(\pi/8),\quad s_7=\sin^7(\pi/8),\quad
R_+=13+22\sqrt2,\quad R_-=22\sqrt2-13,
\]
\[
\alpha_+=2303+1127\sqrt2,\qquad \alpha_-=2303-1127\sqrt2.
\]
The unchanged input table is

| r | p_r | b_r |
|---|---|---|
| 1 | \(c_7R_+\) | \(c_7[\pi\alpha_+-55AR_+]\) |
| 2 | \(-35\) | \((3283\pi-1295A)/2\) |
| 3 | \(c_7R_-\) | \(c_7[(392-55A)R_- -\pi\alpha_-]\) |
| 5 | \(-s_7R_-\) | \(s_7[(55A-392/3)R_-+\pi\alpha_-]\) |
| 7 | \(s_7R_+\) | \(s_7[(2352/5-55A)R_++\pi\alpha_+]\) |

Every parameter and coefficient in (4) is also given literally in `C6Native.wl`
and `results/expression.json`. None is supplied by a numerical fit.

## 3. Four explicit one-variable integrands

### 3.1 Polylogarithms: only the classical trilogarithm remains as a function head

The integrand is
\[
\boxed{R_{\rm pol}(x)=-417792\log x\,
\Re\left[\frac{\frac\pi4\log^2(1-ix)-i\operatorname{Li}_3(1-ix)}{1-ix}\right].}
\tag{5}
\]
Principal branches are used. The argument \(1-ix\), \(0<x\le1\), lies below
the classical cut and never crosses it. The integrand tends to zero at zero.

Here is the proof and the polynomial compensation. Use ordinary HPL letters
\(\omega_0=dz/z\), \(\omega_1=dz/(1-z)\). The previous flat-harmonic
combination was
\[
S=H_{01101}+H_{01011}+2H_{00111},\qquad S_5=\Re S(i).
\]
Shuffle and reflection give
\[
S=\log z\,H_{0111}-H_{01110},
\]
\[
H_{1110}(z)=\operatorname{Li}_4(1-z)-\zeta(4)
-\zeta(3)\log(1-z)-\frac{\zeta(2)}2\log^2(1-z).
\]
Thus, with
\[
I_4(z)=\int_0^z\frac{\operatorname{Li}_4(1-t)-\zeta(4)}t\,dt,
\]
\[
H_{01110}=I_4+\zeta(3)\operatorname{Li}_2-\zeta(2)\operatorname{Li}_{2,1}.
\]
The Nielsen function \(H_{0111}(z)=\mathrm{PolyLog}[1,3,z]\) has its standard
integral \(-\frac16\int_0^1\log^3(1-zt)dt/t\). Using the inherited exact value
\(\Re\operatorname{Li}_{2,1}(i)=29\zeta(3)/64-\pi G/4\), one obtains
\[
S_5=-\Re I_4(i)-\frac\pi2\Im\mathrm{PolyLog}[1,3,i]
 +\frac{37}{384}\pi^2\zeta(3)-\frac{\pi^3G}{24}.
\]
Combining the two integrals and integrating by parts yields (5), with
\[
-417792S_5=\int_0^1R_{\rm pol}(x)dx
 +17408G\pi^3-40256\pi^2\zeta(3).\tag{6}
\]
Both integration-by-parts boundary terms vanish. The numerator before integration
by parts vanishes at zero, and \(\log 1=0\) handles the other boundary.

The latest SVHPL block is first changed to the already established
\(-39168\pi^2\Im\operatorname{Li}_3((1+i)/2)-417792S_5\) form.
Equation (6) then gives (2)-(3). `build.py` verifies the compensation directly
against the CURRENT polynomial, so the use of an earlier intermediate basis
does not revert any later correction.

### 3.2 Wheel: two Kampé de Fériet values become a pFq kernel

The integrand is
\[
\boxed{R_W(x)=\frac{4\log x}{1+x}
 [3144\pi^3U_4(x^2)+1965\pi^4U_6(x^2)].}\tag{7}
\]
Indeed, the trigamma series/integral gives
\[
\delta_n=\psi_1(n+1/2)-\psi_1(n+1)
=-4\int_0^1\frac{x^{2n}\log x}{1+x}dx.
\]
The original two ordinary generating functions have coefficients \(a_n^4\)
and \((4n+1)a_n^6\), where \(a_n=(1/2)_n/n!\). Thus the previously defined
standard bivariate values obey
\[
3\mathfrak F_4=-4\int_0^1\frac{\log x}{1+x}U_4(x^2)dx,\qquad
3\mathfrak F_6=-4\int_0^1\frac{\log x}{1+x}U_6(x^2)dx.
\]
Their weights \(-9432\pi^3\) and \(-5895\pi^4\) give (7).
These are sums beginning at zero, as in the current input. No zero term is
removed or added. Tonelli applies to the positive unweighted kernels.

### 3.3 Seventh sector: five bivariate values become divided differences of pFq

With the finite weights from Section 2,
\[
\boxed{R_7(x)=9408\pi^{3/2}
 \sum_{r\in\{1,2,3,5,7\}}p_rx^{(r+2)/4-1}
 \frac{Z_r(-1)-Z_r(-x^2)}{1-x}.}\tag{8}
\]
For \(a=(r+2)/8\),
\[
H_{2n}(2a)=\int_0^1x^{2a-1}\frac{1-x^{2n}}{1-x}dx.
\]
Inserting this identity into the inherited logarithmic stream gives precisely
\(L(r/8)=\int_0^1x^{2a-1}[Z_r(-1)-Z_r(-x^2)]/(1-x)dx\).
The last reduction had \(L=-\nu_r\mathfrak J_r\), hence the sign in (8) is positive.
Absolute convergence of the original logarithmic streams justifies the interchange.
At \(x=1\) the divided difference has the removable limit
\(-2Z'_r(-1)\). The derivative for that numerical endpoint is evaluated by the
standard shifted-parameter pFq formula; no parameter derivative is required.

### 3.4 Primitive: only complete elliptic integrals

Define the stable quadratic variable
\[
\lambda(x)=\frac{x}{2(1+\sqrt{1-x})}
 =\frac{1-\sqrt{1-x}}2,
\]
and write
\[
K_x=K(\lambda(x)),\qquad K_x^c=K(1-\lambda(x)).
\]
Here \(K(m)=\mathrm{EllipticK}[m]\) uses the **parameter** convention, not the
modulus convention. Let
\[
A_x=(K_x+K_x^c)(K_{1-x}+K_{1-x}^c),\qquad B_x=K_xK_{1-x}.
\]
The primitive contribution to r6 is
\[
\boxed{R_P(x)=\frac{1536}{\sqrt{x(1-x)}}
 [15A_x^2+24A_xB_x-4B_x^2].}\tag{9}
\]
To prove it, the quadratic Gauss transformation and logarithmic normalization give
\[
{}_2F_1(1/4,1/4;1;x)=\frac2\pi K_x,
\]
\[
\sqrt Q\,{}_2F_1(1/4,1/4;1/2;1-x)=2(K_x+K_x^c).\tag{10}
\]
A direct independent proof substitutes \(x=4m(1-m)\) into the elliptic equation
\(m(1-m)Y''+(1-2m)Y'-Y/4=0\). It gives
\(x(1-x)y''+(1-3x/2)y'-y/16=0\). At zero, the complete logarithmic
normalization is fixed by
\[
2(K_x+K_x^c)=-\log x+\pi+6\log2+O(x|\log x|).
\]
This matches the inherited zero-balanced Gauss connection coefficient. The
regular and logarithmic Frobenius data determine the identity without a fitted constant.

The inherited univariate Meijer G solutions therefore have the finite reductions
\[
g_1=\frac4{\pi^{3/2}}K_x^2,\quad
 g_2=\frac4{\pi^{3/2}}K_xK_x^c,\quad
 g_3=\frac2{\pi^{3/2}}[(K_x^c)^2-K_x^2].\tag{11}
\]
These identities remove even the univariate Meijer G functions from the kernel.
For the inherited symmetric primitive, \(R=Qh(x)h(1-x)=4A_x\) and
\(S=2\pi^2v(x)v(1-x)=8B_x\). Substituting in
\(96P_a=96\int(15R^2+12RS-S^2)/\sqrt{x(1-x)}\,dx\) proves (9).
This also shows explicitly why Q disappears from the primitive integrand.

## 4. Numerical implementation

`C6Native.wl` is a standalone Wolfram Language package. Load it with

```wolfram
Get["C6Native.wl"];
expr = C6NativeExpression[];
report = C6NativeEvaluate[25];
report["C6"]
```

The exact function returns an `Inactive[Integrate]` expression. It is intentionally
not labelled a closed form. The numerical function evaluates four real integral
blocks separately with `NIntegrate`, and returns the individual r6 contributions.
It never uses the saved decimal value of C6 as an input.

For the wheel and seventh blocks the evaluator uses \(x=u^4\). The seventh
power factor becomes the integer power \(u^{r+1}\), and the endpoint at one
is supplied by the exact shifted-pFq derivative. For the symmetric primitive,
it folds to \(x\le1/2\) and sets \(x=u^4/2\). The complementary elliptic
integral is evaluated as `CarlsonRF[0,lambda,1]`, avoiding subtraction of an
extremely small number from one. All of these are standard built-ins.

No Wolfram kernel was executed in this environment. The package received a
static delimiter check, and its mathematics was checked independently in Python.
The requested NIntegrate goals and working precision are NOT certified error bounds.
The routine does not suppress integration warnings; they should be inspected.

## 5. Executed checks

`verify_symbolic.py` passes 60 finite checks, including the elliptic ODE pullback,
three Meijer-to-elliptic products, primitive normalization, finite harmonic
integrals for all five shifts, all relevant signs, complete polynomial
compensation, unchanged thirteen ordinary values, and preservation of the source
correction. Some checks are implementation tests rather than independent theorems.

`verify_numeric.py` was run at 35 and 60 decimal working digits. At 60 digits:

- the 25 Gauss/Meijer-to-elliptic point checks have maximum residual below
  1.245e-60;
- the primitive computed using ONLY the elliptic kernel differs from the old
  rational interval midpoint by less than 4.079e-56;
- the new polylog integral identity differs from the independently enclosed old
  Euler sum by less than 5.608e-56;
- the five seventh-sector quadratures differ from the inherited standard-function
  interval midpoints by less than 4.746e-60.

The primitive result is

```text
334926.045248051837883222001240077786613085905253136679683127
```

The proper-subinterval wheel checks use an elementary bound on the omitted
endpoint interval. They are not a new interval certificate, because the proper
integrals were evaluated by floating-point quadrature.

A SEPARATE full native-form run freshly evaluated all thirteen ordinary values
and both full wheel integrals, combining them with the new quadrature results.
At 35-digit working precision and the stated finite Gauss-Legendre quadrature
settings it gave

```text
14331.687032758054293869696798096616
```

The absolute discrepancy from the inherited fine C6 interval midpoint is about
2.658e-14. **This run does not establish 35-digit accuracy.** The wheel endpoint
quadrature is the limiting part. The unchanged exact analytic identity is distinct
from the numerical accuracy of this particular quadrature setting.

No new full-C6 rigorous interval or physical graph/RG certification is claimed.
No additional arithmetic relation between the remaining periods is claimed.

## 6. References and input provenance

All external function/API statements were checked against primary documentation.

- Wolfram `HypergeometricPFQ`:
  `https://reference.wolfram.com/language/ref/HypergeometricPFQ.html`
- Wolfram classical and Nielsen `PolyLog`:
  `https://reference.wolfram.com/language/ref/PolyLog.html`
- Wolfram `EllipticK` (parameter convention):
  `https://reference.wolfram.com/language/ref/EllipticK.html`
- Wolfram `CarlsonRF`:
  `https://reference.wolfram.com/language/ref/CarlsonRF.html`
- Wolfram `NIntegrate`:
  `https://reference.wolfram.com/language/ref/NIntegrate.html`
- Wolfram `FoxH` and `MeijerG` documented signatures:
  `https://reference.wolfram.com/language/ref/FoxH.html`
  and `https://reference.wolfram.com/language/ref/MeijerG.html`
- NIST DLMF Sections 5.12, 5.15, 15.8, 19.2 (beta, polygamma, Gauss, elliptic).
- Remiddi and Vermaseren, *Harmonic Polylogarithms*, arXiv:hep-ph/9905237,
  for the finite shuffle and reflection conventions.

The supplied current expression and the older classical-trilog polynomial are
copied unchanged under `inputs/`. Their source-specific identities remain
inherited. The current-input hash is in `results/expression.json`. The native
polynomial is verified directly against that current input, not inferred merely
by comparing numerical C6 values.
