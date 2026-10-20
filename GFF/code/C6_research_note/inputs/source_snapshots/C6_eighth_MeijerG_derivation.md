# C6(1): compress the finite eighth-power block to ordinary Meijer G

## Scope and outcome

The input is the supplied `C6_sixth_MeijerG_expression.json`, copied unchanged
under `inputs/previous_partial_expression.json`. The normalization is
`r6 = 2187 C6(1)`.

This step replaces the COMPLETE finite eighth-power block `24 PZ6 + PK6/3`,
which used U8, Y1 and Y7, by one ordinary univariate Meijer G value at argument 1.
The new parameters include two explicitly elementary complex conjugates.
This is a compression of a linear combination of three already standard values,
not an evaluation of an unresolved elliptic period or a theorem of arithmetic
independence. Its higher function order and nonrational parameters are costs.
No faster numerical evaluation is asserted.

The direct wheel attempt did not establish a finite evaluation. The wheel,
seventh-power logarithmic sector, and primitive Pa remain unresolved in the
requested finite Mathematica-built-in basis. No full integral-free/sum-free C6
formula is claimed. The input known polynomial, prior Pb reduction, finite
polylogarithmic block, source repair, and upstream graph/RG qualification stay
unchanged.

## 1. One standard univariate value

Define the real positive elementary constants
\[
 \rho_8=\sqrt{2177203-1028322\sqrt2},
\]
\[
 d_8=\frac{1}{2\pi}\arctan\frac{556}{1233-417\sqrt2},\qquad
 \eta_8=\frac{1}{2\pi}\operatorname{arcosh}
            \frac{1233-139\sqrt2}{\rho_8},
 \qquad \alpha_\pm=d_8\pm i\eta_8.
\]
All inverse functions here have their principal real values. Their numerical
values satisfy d8>0, eta8>0; no branch selection is left implicit.

With repeated parameters indicated by [r], put
\[
 {\cal G}_8=G_{11,11}^{3,8}\!\left(
 1\;\middle|\begin{matrix}
 -1/4,(1/2)^{[8]},\alpha_+,\alpha_-\\
 0^{[8]},3/4,\alpha_+,\alpha_-
 \end{matrix}\right).
\]
The standard convention places the FIRST eight upper parameters and FIRST three
lower parameters in numerator groups. Therefore the full split is:

* upper numerator: -1/4, followed by seven copies of 1/2;
* upper denominator: 1/2, alpha+, alpha-;
* lower numerator: three zeros;
* lower denominator: five zeros, 3/4, alpha+, alpha-.

Both occurrences of either alpha are in DENOMINATOR gamma groups. They cannot
be canceled as a matching numerator/denominator pair.

The result is
\[
 \boxed{24P_{Z,6}+\frac13P_K=16\pi^3\rho_8\,{\cal G}_8.}       \tag{1}
\]
This is an ordinary Meijer G in Mathematica's documented interface [1,2]. No
bivariate function, parameter derivative, limit, sum or integral appears in (1).

## 2. Complete block being replaced

Retain the ordinary definitions
\[
 U_8={}_9F_8\!\left(
 \begin{matrix}5/4,(1/2)^{[8]}\\1/4,1^{[7]}\end{matrix};1\right),
\]
\[
 Y_r=\frac r8\left[\frac{\Gamma((r+2)/8)}{\Gamma((r+6)/8)}\right]^8
 {}_{10}F_9\!\left(
 \begin{matrix}1,1+r/8,((r+2)/8)^{[8]}\\r/8,((r+6)/8)^{[8]}\end{matrix};1\right),
 \quad r=1,7.
\]
The preceding formula contains exactly
\[
 \boxed{\begin{aligned}
 B_8={}&\pi^6(4932-5004\sqrt2)U_8\\
 &+556\pi^2\big[(17+12\sqrt2)Y_1-(17-12\sqrt2)Y_7\big].
 \end{aligned}}                                                  \tag{2}
\]
The inherited periodization in `inputs/even_sector_derivation.md`, equations
(8)-(10), identifies (2) with `24 PZ6 + PK6/3`. This graph-period identification
is an inherited analytic input, not inferred from numerical agreement here.

Substitute (1) for the WHOLE expression (2). There is no index-zero extraction
and no elementary compensation. The known polynomial remains exactly the
18-monomial polynomial from the latest input. The seven other ordinary pFq
records, the two previous Pb Meijer values (or their one-value alternative),
and the finite polylogarithmic block are unchanged.

## 3. Residue proof before compressing the parameters

For the proof only, set
\[
 M_j(s)=\frac{\Gamma(s)^j\Gamma(1/2-s)^{8-j}}
 {\Gamma(1-s)^{8-j}\Gamma(1/2+s)^j}
 =\left[\frac{\Gamma(s)}{\Gamma(s+1/2)}\right]^8
       \tan^{8-j}(\pi s).
                                                               \tag{3}
\]
Gamma reflection [3] proves the equality. Use the upward vertical line
Re(s)=1/4, and define proof-only contour values K_j by integrating
`(1/4-s) M_j(s)/(2 pi i)` on that line. These contours do NOT occur in the
proposed Wolfram expression. They can equally be regarded as fixed Meijer G
values with one contiguous parameter pair.

The gamma ratio has size O(|Im(s)|^-1/2) on this line. Since
|tan(pi(1/4+iu))|=1, the weighted kernels are O((1+|u|)^-3).
Their integrals are absolutely convergent, including at function argument 1.
This uses the standard gamma-ratio asymptotic [4], not a regularization.

Let a_n=(1/2)_n/n!, y_n=n+1/4,
\[
 h_n=\log2+H_n-H_{2n},\qquad
 \delta_n=\pi^2/3-4H_{2n}^{(2)}+2H_n^{(2)}.
\]
Near a left pole s=-n+epsilon, the gamma recurrence and polygamma values [3,5]
give
\[
 \frac{\Gamma(-n+\epsilon)}{\Gamma(1/2-n+\epsilon)}
 =\frac{a_n}{\sqrt\pi\,\epsilon}
 \exp\left[2h_n\epsilon+
       \frac{\delta_n-2\pi^2/3}{2}\epsilon^2+O(\epsilon^3)\right].
                                                               \tag{4}
\]
Multiplication by 1/4-s=y_n-epsilon and extraction of the first three residues
therefore give
\[
\begin{aligned}
 K_1&=\pi^3\sum_{n\ge0}a_n^8y_n,\\
 K_2&=\pi^2\sum_{n\ge0}a_n^8(16y_nh_n-1),\\
 K_3&=\pi\sum_{n\ge0}a_n^8
  \big[y_n(128h_n^2+4\delta_n-\pi^2)-16h_n\big].
\end{aligned}                                                     \tag{5}
\]
For justification, initially use 0<x<1 in the inverse Mellin representation
and its standard left residue expansion. The absolute weighted-kernel bound
above permits x approaching 1. The displayed residue sums converge absolutely
(a_n^8=O(n^-4), y_n=O(n), and the harmonic remainders are bounded), so the
endpoint formulas follow without a residual limiting prescription.

The central-binomial representation in the inherited source is
\[
 B_8=8\pi^4\sum_{n\ge0}a_n^8\left[
 (2466-834\sqrt2)\pi^2y_n-1112\pi(1-16y_nh_n)
 +139\sqrt2(256y_nh_n^2-32h_n+8y_n\delta_n)\right].
                                                               \tag{6}
\]
Define the exact algebraic coefficients
\[
 a=1233-278\sqrt2,\qquad b=556,\qquad c=139\sqrt2.
\]
A coefficient-by-coefficient polynomial identity between (5) and (6) gives
\[
 \boxed{B_8=16\pi^3(aK_1+bK_2+cK_3).}                         \tag{7}
\]
No coefficient in (7) was selected from numerical values.

## 4. Encode the weighted kernel as one standard Meijer G

Let theta=pi s. Its trigonometric factor is
\[
 a\tan^7\theta+b\tan^6\theta+c\tan^5\theta
 =\tan^5\theta\sec^2\theta
   [a\sin^2\theta+b\sin\theta\cos\theta+c\cos^2\theta].
\]
Because
\[
 \rho_8^2=(a-c)^2+b^2,\quad
 \cos(2\pi d_8)=\frac{a-c}{\rho_8},\quad
 \sin(2\pi d_8)=\frac b{\rho_8},\quad
 \cosh(2\pi\eta_8)=\frac{a+c}{\rho_8},
\]
the sine-product identity gives exactly
\[
 a\sin^2\theta+b\sin\theta\cos\theta+c\cos^2\theta
 =\rho_8\sin\pi(s+\alpha_+)\sin\pi(s+\alpha_-).             \tag{8}
\]
The parameters are well defined because
\[
 a>c>0,\qquad 4ac-b^2=685548\sqrt2-618272>0,
\]
so (a+c)/rho8>1.

Reflection and recurrence now convert each factor into gamma factors:
\[
 \pi^2 M_3(s)\sec^2(\pi s)
 =\frac{\Gamma(s)^3\Gamma(1/2-s)^7}
       {\Gamma(1-s)^5\Gamma(1/2+s)},
\]
\[
 \frac{\sin\pi(s+\alpha)}\pi
 =\frac1{\Gamma(s+\alpha)\Gamma(1-s-\alpha)},\qquad
 \frac14-s=\frac{\Gamma(5/4-s)}{\Gamma(1/4-s)}.
\]
Thus the weighted kernel for `a K1 + b K2 + c K3` is rho8 times
\[
 \boxed{
 \frac{\Gamma(s)^3\Gamma(1/2-s)^7\Gamma(5/4-s)}
 {\Gamma(1-s)^5\Gamma(1/2+s)\Gamma(1/4-s)
  \Gamma(s+\alpha_+)\Gamma(1-s-\alpha_+)
  \Gamma(s+\alpha_-)\Gamma(1-s-\alpha_-)}.}
                                                               \tag{9}
\]
This is exactly the standard Meijer G kernel for the parameter split in
Section 1 [1,2]. Its left numerator poles are the nonpositive integers;
its right numerator poles are positive half-integers and 5/4 plus nonnegative
integers. The line Re(s)=1/4 separates them. All alpha factors are denominators
and introduce only zeros. Absolute convergence of (9) follows also from its
exact equality to the O(|u|^-3) linear combination in (3).

The conjugate pair of parameters implies that (9) at conjugate s is the
complex conjugate kernel, so the value at 1 is real. No explicit real-part
operation or branch average is required in (1).

This proves the one-value formula. The sine-product factorization packages the
three kernel components; it is NOT an additional arithmetic-independence result.

## 5. All-rational parameter alternative

For a version without inverse trigonometric/hyperbolic parameters, define
\[
 J_{37}=G_{9,9}^{3,8}\!\left(1\middle|
 \begin{matrix}-1/4,(1/2)^{[8]}\\0^{[8]},3/4\end{matrix}\right),
\]
\[
 J_{46}=G_{9,9}^{4,7}\!\left(1\middle|
 \begin{matrix}-1/4,(1/2)^{[8]}\\0^{[8]},3/4\end{matrix}\right).
\]
The different numerator splits matter despite identical complete parameter
lists. Kernel reflection gives `K_j=-K_(8-j)` and, in particular, K4=0.
Consequently
\[
 J_{37}=\pi^2(K_1+K_3),\qquad J_{46}=\pi^2K_2,
 \qquad K_1=\pi^3 U_8/4.
\]
It follows that
\[
 \boxed{B_8=4\pi^6(1233-417\sqrt2)U_8
       +16\pi(139\sqrt2 J_{37}+556J_{46}).}                    \tag{10}
\]
This has THREE built-in calls with rational parameters; (1) has ONE
higher-order call with a nonrational conjugate pair. Neither representation is
claimed universally preferable for numerical speed or stability.

## 6. The restricted wheel attempt and its limit

The same first-three-residue construction for the fourth-power wheel weight
produces, up to nonzero powers of pi, the polynomial span
\[
 1,\quad h_n,\quad 32h_n^2+2\delta_n-\pi^2.
\]
There is no constant linear combination of these three polynomials equal to
`delta_n` as a formal polynomial in h_n and delta_n: its h_n^2 coefficient
would force the coefficient of the third polynomial to zero, while its
coefficient of delta_n would force that coefficient to one-half.

This explains why the direct local residue approach did not separate the
wheel's trigamma insertion. It is ONLY a restriction on this particular
three-kernel, termwise matching ansatz. It does not exclude other Meijer G
families, identities after full summation, parameter transformations, or a
finite evaluation of the definite period. No global non-reducibility theorem
is asserted.

## 7. Numerical and implementation checks

Independent numerical routes were used:

1. U8, Y1 and Y7 were reevaluated from their ordinary coefficient ratios with
   the retained exact-rational finite-tail evaluator. Gamma prefactors were
   evaluated in floating point.
2. The single Meijer G was evaluated from its own gamma-product kernel (9),
   not assigned the linear combination of old values.
3. The two rational-parameter kernels in (10) were evaluated separately.

At 80 decimal working digits, N=192 and rational-tail order 64, the values are

```
rho8 = 850.25647960681496545110445753381301551136617890658969227067027338919979515119383
alpha+ = 0.113438429090747755162684319529431173155662809026053077418002981222454994140268
       + 0.10348762186102480085365335955026477758356676273040103507317518075862440754444951 i
G8 = 23.052165208436562398847615239849165386555288417974065817810406111380624505674711
B8 = 9723693.7997039259148648309491905977597298508498220041290331962924581882722305481
```

The absolute discrepancy of the one-value form from the original block is
`1.7686873e-73` in r6 units; the rational alternative differs by `1.5918186e-73`.
A separate 40-digit run is also retained. These are floating-point cross-checks,
NOT new 73-digit or 80-digit interval certificates. No new evaluation of all
C6 sectors or upstream physical graph identification was performed.

The exact script checks the residue coefficients, inherited full eighth-sector
weight, trigonometric factorization, rational-parameter alternative, selected
Pochhammer coefficients, and preservation of the input polynomial, source
correction and other blocks. Static Wolfram delimiter/function checks are not
kernel execution. The .wl file was NOT executed in a Mathematica kernel.

`C6FinitePartR6[]` returns ONLY the finite part; three elliptic blocks are absent.
The file also exposes `C6ReductionStatus[]` so this distinction is machine-visible.

## Reproduction

Python 3, SymPy and mpmath are sufficient for the executed checks:

```
python build_and_verify.py
python numerical.py 40 128 40
python numerical.py 80 192 64
```

In Mathematica (not executed here):

```wolfram
Get["C6_eighth_MeijerG_patch.wl"];
C6EighthBlockSingle[]
C6EighthBlockRational[]
C6EighthNumericalCheck[40]
C6ReductionStatus[]
```

## References and retained inputs

[1] Wolfram Language, MeijerG, parameter-list splitting and numerical function.
https://reference.wolfram.com/language/ref/MeijerG.html

[2] NIST DLMF 16.17, standard Mellin-Barnes definition of Meijer G.
https://dlmf.nist.gov/16.17

[3] NIST DLMF 5.5, gamma recurrence and reflection.
https://dlmf.nist.gov/5.5

[4] NIST DLMF 5.11, gamma-ratio asymptotics.
https://dlmf.nist.gov/5.11

[5] NIST DLMF 5.15, polygamma recurrences and half-integer values.
https://dlmf.nist.gov/5.15

Inherited inputs: the supplied C6_sixth_MeijerG_expression.json (complete latest
partial expression), and C6_even_sector_derivation.md equations (8)-(10).
No source correction is removed or added a second time.
