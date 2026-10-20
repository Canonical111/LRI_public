# C6(1): a finite nine-value representation

## Scope

This is an exact finite reformulation of the retained analytic C6 coefficient.
The complete seventh sector now uses two fixed values, not five. Its former
Kampé de Fériet calls and cubic/quartic root sets are absent. Four explicit
nonrational shifts, determined using square roots and inverse tangents, suffice.
All other sectors and the complete known polynomial are copied from the accepted
input. The physical graph/RG identification remains inherited.

The new bivariate H has a shared slope pair (2,1), and argument (1,-1), with
Log(-1)=i*pi. Unlike the old wheel and primitive values it is not restricted to
unit slopes. It is absolutely convergent on the contours specified in Section 4.
No integral, infinite sum, parameter derivative, or limiting operation remains
to be applied in the coefficient itself. The standard-function kernel
specifications below fix conventions; they are not extra remainder blocks.
This is not an elementary evaluation or an arithmetic-independence theorem.

## 1. Complete coefficient

Put
\[
\ell=\log2,\qquad A=\pi+4\ell,\qquad
Q=\frac{\Gamma(1/4)^4}{\pi},\qquad G=\operatorname{Catalan}.
\]
Then
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E+B_{\rm pol}+B_{\rm low}+B_6+B_8
-393\pi\sqrt{89}\,\mathcal H_W\\
&+24\pi^{3/2}\bigl[\rho_7\mathcal G_7
+392\sqrt{185}\,\mathcal H_7\bigr]
+7680\pi^3\mathcal H_*.
\end{aligned}}
\]
All symbols are specified below. There is no polynomial compensation:
Delta E=0. The source correction and all included zero-index terms remain
included exactly once.

### Complete known polynomial

\[
\begin{aligned}
E={}&\frac Q8[63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)]
+Q^2(29\pi-249A)+\mathcal P,\\
\mathcal P={}&\frac{21}{640}A^5+\frac7{64}A^3\pi^2
+\frac{1149}{64}A^2\pi^3+\frac{7863}{16}A^2\zeta(3)\\
&+192AG(16G+3\pi^2)+\frac{14853}{640}A\pi^4
-\frac{544}{3}G\pi^3+\frac{37631}{128}\pi^5\\
&+\frac{722279}{48}\pi^2\zeta(3)-\frac{805959}{8}\zeta(5).
\end{aligned}
\tag{2}
\]
No extra source repair, wheel zero term, or former -144 Q^3/pi term is to be added.

### Finite polylogarithmic block

\[
B_{\rm pol}=4352\left[(32G+9\pi^2)\Im\operatorname{Li}_{2,1}(i,1)
-64\Re\operatorname{Li}_{2,1,2}(i,1,1)\right].
\tag{3}
\]
The convention is the ordinary strict multiple-polylogarithm convention. Equivalently the two functions are HPL words 011 and 01101, using the letters dz/z and dz/(1-z).

## 2. Ordinary Meijer G blocks retained from the current formula

Write a^[j] for j repetitions. In the ordinary G_(p,q)^(m,n), the first n upper and first m lower parameters are in numerator gamma groups. Ordered parameter lists therefore matter.

Set
\[
\begin{aligned}
X_4&=42A^2+18A\pi+1227\pi^2-96Q,\\
Y_4&=\frac{105}{4}A^2+9A\pi+\frac{2469}{4}\pi^2-60Q,\\
\rho_4&=\sqrt{X_4^2+Y_4^2},\qquad
\alpha_4=\pi^{-1}\arctan(Y_4/X_4).
\end{aligned}
\]
Here X4,Y4 are positive and the real principal inverse tangent is used. Define
\[
\mathcal G_4=G_{5,5}^{2,3}\!\left(1\;\middle|\;
\begin{matrix}(1/2)^{[4]},\alpha_4\\0^{[4]},\alpha_4\end{matrix}\right),
\qquad B_{\rm low}=-4\pi^2\rho_4\mathcal G_4.
\tag{4}
\]
For the sixth-power block put
\[
\alpha_6=\frac{1}{\pi}\arctan\frac{11}{13},\qquad
\mathcal G_6=G_{7,7}^{4,5}\!\left(1\;\middle|\;
\begin{matrix}(1/2)^{[6]},\alpha_6\\0^{[6]},\alpha_6\end{matrix}\right).
\]
Then
\[
\boxed{B_6=192\pi\sqrt{290}\,\mathcal G_6=24P_b.}
\tag{5}
\]
This reuses the earlier identity sqrt(290) G6 = 13 X35 + 11 X44. Its exact Wolfram splits are

```wolfram
MeijerG[{{1/2,1/2,1/2,1/2,1/2},{1/2,alpha6}},
        {{0,0,0,0},{0,0,alpha6}},1]
```

For the eighth-power block set
\[
\begin{aligned}
\rho_8&=\sqrt{2177203-1028322\sqrt2},\\
d_8&=\frac1{2\pi}\arctan\!\frac{556}{1233-417\sqrt2},\\
\eta_8&=\frac1{2\pi}\operatorname{arcosh}\!\frac{1233-139\sqrt2}{\rho_8},\\
\alpha_\pm&=d_8\pm i\eta_8.
\end{aligned}
\]
All inverse functions here take their principal real values. Then
\[
\begin{aligned}
\mathcal G_8&=G_{11,11}^{3,8}\!\left(1\;\middle|\;
\begin{matrix}-1/4,(1/2)^{[8]},\alpha_+,\alpha_-\\
0^{[8]},3/4,\alpha_+,\alpha_-\end{matrix}\right),\\
B_8&=16\pi^3\rho_8\mathcal G_8=24P_{Z,6}+P_K/3.
\end{aligned}
\tag{6}
\]
Repeated alpha parameters in these lists do not cancel, since they are in different denominator gamma groups.

## 3. The wheel: one fixed bivariate H value

Put
\[
\alpha_W=\frac1\pi\arctan\frac58.
\]
All slopes in the following standard bivariate Fox H value are one:
\[
\boxed{\mathcal H_W=
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
\tag{7}
\]
The standard convention is Andrade–Rathie–Farias Definition B. The numerator indices are shared n=2; s-local m=2,n=3; t-local m=2,n=2. Ordered repeated alphaW parameters belong to denominator groups and do not cancel.

For exact normalization, set
\[
N_{\alpha}(s)=\frac{\Gamma(s)^2\Gamma(\frac12-s)^3}
{\Gamma(1-s)^2\Gamma(\frac12+s)\Gamma(s+\alpha)\Gamma(1-s-\alpha)},
\]
\[
P(t)=\Gamma(t)\Gamma(t+\tfrac12)\Gamma(\tfrac12-t)\Gamma(1-t).
\]
The inverse-Mellin kernel is
\[
\boxed{\frac{N_{\alpha_W}(s)P(t)}{(\frac12-s-t)^2},}
\tag{8}
\]
with upward contours Re(s)=1/4, Re(t)=1/8 and standard measure ds dt/(2 pi i)^2. This fixes the named-function parameters; it is not an extra integral in the master expression.

The entire zero-included wheel is
\[
\boxed{W_0=\frac{\sqrt{89}}{\pi^2}\mathcal H_W,\qquad
-393\pi^3 W_0=-393\pi\sqrt{89}\mathcal H_W.}
\tag{9}
\]
For the original n>=1 notation, Wcentral=W0-(8+5*pi)*pi**2/3. The master formula uses W0; no additional zero-index compensation or source correction is to be added.

Numerically, H_W = 82.198372839948704474444779671977025125648737334356408964906750... . The optional interval file propagates the previously proved rational wheel enclosure. See DERIVATION.md for the inherited global identity and new kernel conversion.

## 4. The seventh sector: one Meijer G and one bivariate H

Put A=pi+4 log(2), and define
\[
a_7=259A-49\pi,\qquad b_7=481A-539\pi,\qquad c_7=407A-1127\pi,
\]
where c_7 here is a quadratic coefficient, NOT the old shorthand cos(pi/8)^7.
Set
\[
\Delta_7=\sqrt{b_7^2-4a_7c_7},\qquad
\rho_7=\sqrt{(a_7-c_7)^2+b_7^2},
\]
\[
\eta_\pm=\frac1\pi\arctan\frac{b_7\pm\Delta_7}{2a_7},\qquad
\beta=\frac1\pi\arctan\frac{13+i\sqrt{139}}{14}.
\]
All square roots displayed above are positive real roots. The inverse tangents
for eta are real principal values; the complex inverse tangent for beta is
principal. The conjugate of beta supplies the other local parameter. The
constants obey a_7>0, b_7>0, c_7<0. Thus Delta_7 is positive, and eta_+ and eta_-
are real with opposite signs. These signs follow, for example, from
2/3<log(2)<7/10 and 3<pi<22/7. No parameter is fitted to a period value.

Define
\[
\boxed{\mathcal G_7=G_{10,10}^{3,8}\!\left(
1\;\middle|\;\begin{matrix}-\tfrac14,(\tfrac12)^{[7]},\eta_+,\eta_-\\
0^{[7]},\tfrac34,\eta_+,\eta_-\end{matrix}\right).}
\tag{1}
\]
The ordered upper list has eight numerator entries; the ordered lower list has
three numerator entries. In the standard inverse-Mellin convention its kernel is
\[
N_7(s)=\frac{\Gamma(s)^3\Gamma(\tfrac12-s)^7\Gamma(\tfrac54-s)}
{\Gamma(1-s)^4\Gamma(\tfrac14-s)
\Gamma(s+\eta_+)\Gamma(1-s-\eta_+)
\Gamma(s+\eta_-)\Gamma(1-s-\eta_-)}.
\tag{2}
\]

For the second value use the same standard bivariate H convention as the input.
Let
\[
\mathbf a=((-\tfrac14,1),(\tfrac12,1)^{[7]},(\beta,1),(\bar\beta,1)),
\]
\[
\mathbf b=((0,1)^{[6]},(1,1),(\tfrac34,1),(\beta,1),(\bar\beta,1)).
\]
Then
\[
\boxed{\mathcal H_7=
H_{1,1;\,10,10;\,2,2}^{0,1;\,3,8;\,1,2}
\!\left[\begin{matrix}
(0;2,1):\mathbf a;(0,1),(0,1)\\
(-1;2,1):\mathbf b;(0,1),(-1,1)
\end{matrix}\;\middle|\;1,-1\right].}
\tag{3}
\]
The first local numerator counts are n=8 upper and m=3 lower. The second local
counts are n=2 upper and m=1 lower. The shared counts are n=1 upper and m=0 lower.

For an unambiguous independent specification of the convention, its kernel is
\[
A_7(s)\frac{\Gamma(t)\Gamma(1-t)^2}{\Gamma(2-t)}
\frac{\Gamma(1-2s-t)}{\Gamma(2-2s-t)}e^{-i\pi t},
\tag{4}
\]
where
\[
A_7(s)=\frac{\Gamma(s)^3\Gamma(\tfrac12-s)^7\Gamma(\tfrac54-s)}
{\Gamma(1-s)^3\Gamma(-s)\Gamma(\tfrac14-s)
 \Gamma(s+\beta)\Gamma(1-s-\beta)
 \Gamma(s+\bar\beta)\Gamma(1-s-\bar\beta)}.
\tag{5}
\]
The upward lines Re(s)=1/4 and Re(t)=1/8 use the usual measure
 ds dt/(2 pi i)^2. The phase in (4) is exactly the named function's
(-1)^(-t) factor, not an additional operation applied afterward.

With B_7 denoting the COMPLETE seventh contribution in r6=2187 C6 units,
\[
\boxed{B_7=24\pi^{3/2}
 [\rho_7\mathcal G_7+392\sqrt{185}\,\mathcal H_7].}
\tag{6}
\]
Equivalently the old central value satisfies
\[
\boxed{\mathscr M_7=
\frac{\rho_7\mathcal G_7+392\sqrt{185}\,\mathcal H_7}{\pi^{3/2}}.}
\tag{7}
\]
No term is removed from the zero mode and no polynomial compensation is added.

## 5. The primitive: one bivariate Fox H value

Let lambda be the unique real root in (15,16) of
\[
4\lambda^3-112\lambda^2+909\lambda-2250=0.
\]
Equivalently,
\[
\lambda=\frac{28+\sqrt{409}\cos\!\left(\frac13\arccos\frac{7298}{409\sqrt{409}}\right)}3.
\]
Put
\[
e=\frac{\sqrt{40\lambda-279}}{20},\qquad
\chi=\frac{2(21\lambda-150)}{40\lambda-279},
\]
\[
B_\sigma=\frac{21}{20}+\sigma e,\qquad
C_\sigma=\frac\lambda{10}+\sigma e\chi,
\qquad \sigma\in\{+1,-1\},
\]
\[
\beta_\sigma=\frac1\pi\arctan\left(\frac{B_\sigma}{2}
+i\sqrt{C_\sigma-B_\sigma^2/4}\right).
\]
The real square roots are positive and the complex inverse tangent is principal. Both square-root radicands are positive. Conjugation supplies the second member of each pair. These parameters contain no unknown period.

Define the ordered parameter/slope lists
\[
\mathbf a_\sigma=((1/2,1)^{[4]},(\beta_\sigma,1),(\bar\beta_\sigma,1)),
\]
\[
\mathbf b_\sigma=((0,1)^{[3]},(\beta_\sigma,1),(\bar\beta_\sigma,1)).
\]
In the Andrade-Rathie-Farias bivariate H convention, set
\[
\boxed{\mathcal H_*=H_{0,1;6,5;6,5}^{0,0;3,3;3,3}
\!\left[\begin{matrix}-:\mathbf a_+;\mathbf a_-\\
(0;1,1):\mathbf b_+;\mathbf b_-\end{matrix}\;\middle|\;1,1\right].}
\tag{13}
\]
The first three upper and first three lower entries in each local group are numerator gamma groups. All slopes are one. This is a bivariate function, not Mathematica's univariate FoxH or MeijerG interface.

To fix the normalization without any ambiguity, define the gamma factor
\[
\Psi_\sigma(s)=\frac{\Gamma(s)^3\Gamma(1/2-s)^3}
{\Gamma(1/2+s)\Gamma(s+\beta_\sigma)\Gamma(1-s-\beta_\sigma)
\Gamma(s+\bar\beta_\sigma)\Gamma(1-s-\bar\beta_\sigma)}.
\]
The standard inverse-Mellin kernel is Psi_+(s) Psi_-(t)/Gamma(1-s-t), with upward lines Re(s)=Re(t)=1/4 and the standard measure ds dt/(2 pi i)^2. This is the named function's parameter specification; it is not an extra integration operation in the master coefficient.

The complete primitive is
\[
\boxed{P_a=80\pi^3\mathcal H_*,\qquad S_P=10\mathcal H_*,
\qquad \mathscr P_c^{(3)}=40\pi\mathcal H_*.}
\tag{14}
\]
Consequently
\[
\boxed{96P_a=7680\pi^3\mathcal H_*.}
\tag{15}
\]
There is no added polynomial or zero-index compensation. Numerically, from the proved beta-product representation,
\[
\mathcal H_*=135.0234860111609249908488197821688196879586538126766890134710495752391\ldots.
\]
This numerical check is not an interval certificate.


## 6. Numerical checks and representation size

At 80 working decimal digits,
\[
\mathcal G_7=8.38817429186383748625482510888136818661142660132305\ldots,
\]
\[
\mathcal H_7=-20.35920964993894539299593231407576888649928855816310\ldots,
\]
\[
B_7=-11409730.02189293040856018259030951811363354779663423\ldots.
\]
The new expression was checked against a fresh central-series Euler evaluation
and a fresh original five-shift evaluation. Discrepancies were below 1.239e-73
and 3.007e-73, respectively. These are floating-point cross-checks, not new
interval certificates. The H value was evaluated via its own outer gamma kernel
with an analytically evaluated inner Barnes transform; that inner identity was
also checked separately by direct contour quadrature. No new all-sector C6 or
physical graph/RG verification is claimed. The previously recorded complete
analytic coefficient remains approximately
14331.6870327580543204454632552462171183173230619887904582031423.

| Fixed value class | Count |
|---|---:|
| Multiple polylogarithms | 2 |
| Univariate Meijer G | 4 |
| Bivariate Fox H | 3 |
| Kampé de Fériet | 0 |
| Total | 9 |
| Explicit residual infinite sums or integrals | 0 |

The known polynomial has eighteen expanded monomials. The ninth-value count
excludes elementary constants and gamma/zeta prefactors; it does not measure
arithmetic independence.

## Standard conventions and reproduction

In G_(p,q)^(m,n), the first n upper and first m lower entries are numerator
gamma groups. In the bivariate H convention used here, a shared upper numerator
triple (e;E,F) gives Gamma(1-e-E*s-F*t). A shared lower denominator triple
(f;A,B) gives Gamma(1-f-A*s-B*t) in the denominator. Local upper numerator and
upper denominator pairs (a,A) give Gamma(1-a-A*s) and reciprocal Gamma(a+A*s),
respectively. Local lower numerator and lower denominator pairs (b,B) give
Gamma(b+B*s) and reciprocal Gamma(1-b-B*s), respectively. The second variable
obeys the same rules. The variables supply x^(-s)y^(-t). Every specialized
kernel and required branch is specified above.

References: NIST DLMF 5.5, 5.11, 5.15, 16.17; the inherited bivariate convention
is Andrade--Rathie--Farias, Definition B, DOI 10.1007/s40314-017-0451-z.
The project-specific source and proof are listed in DERIVATION.md.

To reproduce the finite checks and numerical comparisons:

```text
python build_and_verify.py
python numerical.py 45
python numerical.py 80
python check_inner.py
python check_shifted.py
```

The numerical scripts require mpmath; exact checks require SymPy.
No Wolfram kernel or external multivariate-special-function package was used.
