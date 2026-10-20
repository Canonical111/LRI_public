# C6(1): twelve fixed values, seventh parameters from two cubics and one quartic

## Scope and change

This is a complete finite representation of the inherited analytic coefficient.
All blocks except the seventh-sector parameter specification are copied from the
accepted C6_seventh_Abel_formula.md. The five degree-ten polynomials have been
replaced by two cubics and one quartic in a squared coordinate. Their ten roots,
with square-root sign pairs and fixed shifts, generate 32 listed root parameters
instead of 50. No polynomial root problem above degree four remains.

The formula still contains twelve fixed function values, no explicit infinite sum,
no residual integral, and no parameter derivative or limit. The local parameter
lists remain of orders 4/3; shared orders are 14/14 for four values and 16/16 for
the central value. There are 184 seventh-sector list entries rather than 220.
All lower parameters have positive real parts. Two upper lists have a negative
nonintegral entry, so their local defining coefficients are signed.

This is a parameter simplification, not an arithmetic-independence result or a
new physical graph/RG verification. The known polynomial and source correction
remain unchanged. The previously proved wheel and primitive special-function
identifications remain inherited inputs.

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
&+9408\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}
p_r\Omega_r^{\mathrm{sym}}\mathcal K_r^{\mathrm{sym}}\\
&+7680\pi^3\mathcal H_*.
\end{aligned}}
\tag{1}
\]
The sum in (1) has exactly five terms. Every symbol is specified below.

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

## 4. Seventh-sector parameter reduction

Put
\[
A=\pi+4\log2,\quad
\xi_+=-\frac{55A}{98}+\frac{(401+735\sqrt2)\pi}{1598},\quad
\xi_-=-\frac{55A}{98}+\frac{(401-735\sqrt2)\pi}{1598}.
\]
The inherited five weights are
\[
\begin{array}{c|c|c}
r&p_r&\xi_r\\\hline
1&\cos^7(\pi/8)(13+22\sqrt2)&\xi_+\\
2&-35&37A/196-67\pi/140\\
3&\cos^7(\pi/8)(22\sqrt2-13)&\xi_-+4\\
5&-\sin^7(\pi/8)(22\sqrt2-13)&\xi_-+4/3\\
7&\sin^7(\pi/8)(13+22\sqrt2)&\xi_++24/5
\end{array}
\]
with \(\xi_r=b_r/(98p_r)\). Define only three new elementary constants:
\[
\mu_+=\xi_++4,\qquad\mu_-=\xi_-,\qquad
\mu_0=1+\frac{37A}{196}-\frac{67\pi}{140}.
\]
Their approximate values are 3.51266739683952846, -4.57434006191691609,
and 0.61297612244373291, respectively. They are computed from known constants,
not fitted to a numerical period.

Define the cubic and quartic
\[
\boxed{\mathcal C_\mu(z)=4096\mu z^3+(3072-768\mu)z^2
 +(640-720\mu)z+12-17\mu,}
\tag{1}
\]
\[
\boxed{\mathcal D_\mu(z)=65536\mu z^4+(65536-49152\mu)z^3
 +(28672-53760\mu)z^2+(1792-4032\mu)z+16-39\mu.}
\tag{2}
\]
For each r, write
\[
t=r/8,\qquad a=t+1/4,\quad b=t+3/4,\quad c=t+1/2.
\]
For r=1,7 take all three roots of \(\mathcal C_{\mu_+}\); for r=3,5 take
all three roots of \(\mathcal C_{\mu_-}\). In each case form the SIX-member list
\[
\boldsymbol\theta_r=(c+\sqrt{z_1},c-\sqrt{z_1},\ldots,
 c+\sqrt{z_3},c-\sqrt{z_3}).\tag{3}
\]
For r=2, use all four roots of \(\mathcal D_{\mu_0}\) and form the analogous
EIGHT-member list. Both signs are included, so square-root branch choice and
root ordering do not affect the function. These theta parameters are not the
wheel's harmonic remainder delta_n.

No root problem above degree four remains. The resulting parameters need not
have algebraic degree at most four, because a square root is subsequently taken.
They are algebraic over the field generated by pi, log(2), and sqrt(2), not
asserted algebraic over the rationals.

### Five fixed Kampé de Fériet values

Use the classical complex-variable convention [1]: the shared lists act on
m+n, the next lists on m and the last on n, with the usual factorial factors.
A repeated-list exponent [k] denotes k entries, and 1+theta means componentwise
addition. An empty list is denoted by a dash.

For r in {1,3,5,7}, set mu_r=mu_+ for r=1,7 and mu_r=mu_- for r=3,5. Then
\[
\boxed{\mathcal K_r^{\rm sym}=
F_{14:0;3}^{14:1;4}\!\left[
\begin{matrix}
a^{[6]},a+1,c+1,1+\boldsymbol\theta_r:1;1,t+1,a,b-1\\
b,(b+1)^{[6]},c,\boldsymbol\theta_r:-;t,a+1,b
\end{matrix};-1,-1\right].}\tag{4}
\]
Its multiplier is
\[
\boxed{\Omega_r^{\rm sym}=
\left[\frac{\Gamma(a)}{\Gamma(b)}\right]^7
\frac{tc\,\mathcal C_{\mu_r}(c^2)}{2048(b-1)b^6}.}\tag{5}
\]
For r=2, use t=1/4,a=1/2,b=1,c=3/4 and the eight-member theta list:
\[
\boxed{\mathcal K_2^{\rm sym}=
F_{16:0;3}^{16:1;4}\!\left[
\begin{matrix}
a^{[7]},c+1,1+\boldsymbol\theta_2:1;1,t+1,a-1,b\\
(b+1)^{[7]},c,\boldsymbol\theta_2:-;t,a,b+1
\end{matrix};-1,-1\right].}\tag{6}
\]
Its multiplier simplifies to
\[
\boxed{\Omega_2^{\rm sym}=\frac{3\pi^{7/2}}{1024}(84\mu_0-85).}\tag{7}
\]
Equivalently it is
\[
[\Gamma(a)/\Gamma(b)]^7\frac{tc\,\mathcal D_{\mu_0}(c^2)}
 {32768(a-1)b^8}.
\]
The separate r=2 formula avoids the singular b-1=0 that would result from
naively using (4) at this shift. No parameter limit or regularization is used.

The exact full-sector replacement is
\[
\boxed{B_7=9408\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}
 p_r\Omega_r^{\rm sym}\mathcal K_r^{\rm sym}.}\tag{8}
\]
Only five terms occur. For each shift,
\[
\Omega_r^{\rm sym}\mathcal K_r^{\rm sym}
=\widehat\Omega_r\widehat{\mathcal K}_r,
\]
where the right-hand side is the preceding degree-ten Abel representation.

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

## 6. Verification and counts

The new coefficient identities and finite summation-by-parts proof are given in
DERIVATION.md. The exact verifier passes 173 finite checks, including both odd
polynomial factorizations, rational root-isolation signs, all five finite Abel
boundaries, coefficient normalizations, and preservation of unchanged blocks.

At 160 working digits with 400 Euler-weighted diagonals, the new seventh block
agrees with the independently constructed original coefficients to an absolute
discrepancy approximately 3.619e-113 in r6 units. Root-based Pochhammer lists were
checked at six separate indices per shift, with maximum relative discrepancy
below 2.668e-160. These are floating-point checks, NOT special-value interval
certificates. No new all-sector evaluation or Wolfram kernel execution occurred.

Both the preceding and new series used for checking have absolute diagonal decay
O(log(n+2)/(n+1)^(3/2)). The new representation is not claimed numerically faster.

| Class | Fixed values |
|---|---:|
| Multiple polylogarithms | 2 |
| Univariate Meijer G | 3 |
| Kampé de Fériet | 5 |
| Bivariate Fox H | 2 |
| **Total** | **12** |
| Explicit residual infinite sums or integrals | **0** |

The known polynomial retains eighteen expanded monomials.

## Appendix A. Standard conventions

For Kampé de Fériet
\[
F_{q:s;u}^{p:r;t}\!\left[
\begin{matrix}\boldsymbol a:\boldsymbol b;\boldsymbol c\\
\boldsymbol d:\boldsymbol e;\boldsymbol f\end{matrix};x,y\right],
\]
the coefficient of x^m y^n in its standard defining expansion is
\[
\frac{(\boldsymbol a)_{m+n}(\boldsymbol b)_m(\boldsymbol c)_n}
{(\boldsymbol d)_{m+n}(\boldsymbol e)_m(\boldsymbol f)_n\,m!n!}.
\]
List Pochhammer symbols mean products over their lists. This specifies all five new K_r in section 4. Those values converge absolutely at (-1,-1); their absolute total-index diagonal is O(log(k+2)/(k+1)^(3/2)).

For the bivariate H function, shared upper numerator triples (e;E,F) produce Gamma(1-e-E*s-F*t); shared lower denominator triples (f;A,B) produce Gamma(1-f-A*s-B*t) in the denominator. A local upper numerator pair (a,A) gives Gamma(1-a-A*s), while an upper denominator pair gives Gamma(a+A*s) in the denominator. A local lower numerator pair (b,B) gives Gamma(b+B*s), while a lower denominator pair gives Gamma(1-b-B*s) in the denominator. The second local variable obeys the same convention. Both H kernels are explicitly specified above.

## Sources and reproduction

Accepted input: C6_seventh_Abel_expression.json and C6_seventh_Abel_formula.md.
All previous wheel, primitive, Meijer G and polylogarithmic identities remain
inherited. The new contiguous-harmonic and Abel transformation is proved in
DERIVATION.md; it is not attributed to the standard references.

Kampé de Fériet convention: Ito, Kumabe, Nakagawa, Nemoto, arXiv:2212.14321v2,
Introduction (classical complex-variable definition):
https://arxiv.org/html/2212.14321v2

Gamma recurrence and gamma-ratio asymptotic: NIST DLMF sections 5.5 and 5.11:
https://dlmf.nist.gov/5.5
https://dlmf.nist.gov/5.11

To reproduce the new checks using Python 3, SymPy and mpmath:

```
python build_and_verify.py
python numerical.py --N 240 --digits 105
python numerical.py --N 400 --digits 160
```
