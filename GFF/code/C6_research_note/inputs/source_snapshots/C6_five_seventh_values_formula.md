# C6(1): optional finite representation with 12 fixed special-function values

## Scope

The full 17-value input is retained as a simpler-parameter alternative. This
version replaces its five ordinary seventh-sector values plus five Kampé de
Fériet values by five higher-order Kampé de Fériet values. The total is 12 fixed
function values. The cost is sixteen polynomial-root parameters per shift and
local y orders 26/25 rather than 4/3. This is a function-call compression, NOT
an elementary evaluation or arithmetic-independence reduction. No additional
function variable is introduced. The physical graph/RG identification and
all prior block identities remain inherited. No new all-sector certificate is claimed.

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
&-9408\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}
p_r\Omega_r\mathcal K_r\\
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

## 4. The seventh sector: five higher-order Kampé de Fériet values

This section replaces the previous five ordinary Z values AND five logarithmic
Kampé de Fériet values. It must not be added to either old seventh-sector block.

For r in {1,2,3,5,7}, put
\[
t=r/8,\quad a=t+1/4,\quad b=t+3/4,\quad c=t+1/2.
\]
Let
\[
c_7=\cos^7(\pi/8),\quad s_7=\sin^7(\pi/8),\quad
R_+=13+22\sqrt2,\quad R_-=22\sqrt2-13,
\]
\[
L_+=\frac{\pi(2303+1127\sqrt2)}{R_+},\qquad
L_-=\frac{\pi(2303-1127\sqrt2)}{R_-}.
\]
The five elementary coefficients are

| r | p_r | xi_r |
|---|---|---|
| 1 | c7 R+ | (L+ - 55 A)/98 |
| 2 | -35 | (1295 A - 3283 pi)/6860 |
| 3 | c7 R- | (392 - 55 A - L-)/98 |
| 5 | -s7 R- | (392/3 - 55 A - L-)/98 |
| 7 | s7 R+ | (2352/5 - 55 A + L+)/98 |

Here xi_r is exactly the old ordinary weight b_r divided by 98 p_r.
It depends only on pi, log(2) and sqrt(2), not on an unknown period.

Define the following finite rational expressions in the temporary variable x:
\[
\kappa_r=t\left(\frac ba\right)^7,\qquad
f_r(x)=\frac{\kappa_r}{x+t}
\left[x+(x+1)\left(\frac{x+a}{x+b}\right)^7\right],
\]
\[
\boxed{d_r(x)=\frac{x+c}{(x+a)(x+b)}
-\xi_r\,[f_r(x+1)-f_r(x)].}
\]
These definitions involve no sum, integral, or derivative. In particular,
\[
f_r(0)=1,\qquad
 d_r(0)=\frac c{ab}-\xi_r\left\{
 \frac{\kappa_r}{t+1}\left[1+2\left(\frac{a+1}{b+1}\right)^7\right]-1
 \right\}.
\]
The following expression is a MONIC POLYNOMIAL of degree sixteen:
\[
\boxed{P_r(x)=(x+a)(x+t)(x+t+1)(x+b)^7(x+b+1)^7d_r(x).}
\]
Let beta_(r,1),...,beta_(r,16) be the negatives of ALL its roots, counting
multiplicity. Equivalently,
\[
P_r(x)=\prod_{j=1}^{16}(x+\beta_{r,j}).
\]
The list is unordered: the function is symmetric in each parameter group, so
no ordering or branch selection among the roots is required. The complete
polynomial coefficients are exported in the JSON. They are algebraic over the
field generated by the known elementary constants, not asserted algebraic over Q.

Put boldsymbol(beta)_r=(beta_(r,1),...,beta_(r,16)). In the standard classical
complex-variable Kampé de Fériet convention of Appendix A define
\[
\boxed{\mathcal K_r=
F_{8:0;25}^{8:1;26}\!\left[
\begin{matrix}
t+2,(a+1)^{[7]}:1;1,a,t,b^{[7]},1+\boldsymbol\beta_r\\
t+1,(b+1)^{[7]}:-;a+1,t+2,(b+2)^{[7]},\boldsymbol\beta_r
\end{matrix};-1,-1\right].}
\]
Adding one to a list means adding one to every member. The dash is an empty list.
At r=2, P_2 has the factors (x+1)(x+2); canceling the corresponding identical
upper/lower entries reduces local orders 26/25 to 23/22. The uniform form above
is valid without doing that cancellation.

Finally define the finite gamma prefactor
\[
\Omega_r=(t+1)\left[\frac{\Gamma(a+1)}{\Gamma(b+1)}\right]^7d_r(0).
\]
The complete seventh-sector replacement is
\[
\boxed{24\pi^3\mathscr M_7=
-9408\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}p_r\Omega_r\mathcal K_r.}
\]
The displayed sum has five terms. There is no new polynomial or constant term.
The ordinary n=0 contributions are absorbed by the exact zero-boundary identity
in DERIVATION.md; they have not been omitted.

All lower parameters avoid nonpositive integers. For r=1,2,3,5, the polynomial
P_r has all coefficients positive and therefore no nonnegative real root. For
r=7, its descending coefficients have signs +,-,...,-, so it has one positive
root; exact rational interval signs locate that root in (205,206). Thus it
cannot be a nonnegative integer. This also proves d_r(0) is nonzero. The file
results/parameter_certificate.json contains the rational elementary-constant
bounds and sign checks.

The defining double series is absolutely convergent at (-1,-1): its absolute
k-th total-index diagonal is O(log(k+2)/(k+1)^(5/2)). This follows from d_r(j)=
1/j+O(1/j^2) and the shared gamma ratio. No regularization or parameter limit is
used in this specification.

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

## 6. Verification and limits

The exact script checks the finite telescoping identity, all five coefficient
maps, nonsingular root parameter lists and the full seventh-sector replacement.
It also checks exact preservation of the input known polynomial, both bivariate
H blocks, all univariate Meijer-G values, the finite polylogarithmic block and
the source correction. The known shift is zero.

Numerical Euler-diagonal runs at (N,digits)=(256,110),(400,155) compare the new
KdF definitions with the old ordinary hypergeometric values and old KdF
harmonic diagonals. The larger run gives absolute discrepancy below 4.73e-116
for the complete seventh contribution in r6 units. This is a floating-point
comparison, NOT a rigorous numerical interval certificate. The root-defined
coefficient lists were independently checked at eight indices for every r,
including both sides of the positive root for r=7. Their largest discrepancy
was below 3.18e-87 with 85-digit root solves.

No fresh all-sector evaluation, physical graph/RG proof or Mathematica kernel
execution was performed. The previously recorded C6 value is therefore not
newly certified by this substitution.

| Function class | Input | This alternative |
|---|---:|---:|
| Multiple polylogarithms | 2 | 2 |
| Ordinary generalized hypergeometric | 5 | 0 |
| Univariate Meijer G | 3 | 3 |
| Kampé de Fériet | 5 | 5 |
| Bivariate Fox H | 2 | 2 |
| **Total** | **17** | **12** |
| Explicit residual infinite sums or integrals | 0 | 0 |

The 17-value representation has much simpler seventh-sector parameters. The
12-value representation should not be described as unconditionally simpler,
faster, or arithmetically smaller. Its merit is the reduced number of distinct
fixed function evaluations in the master formula.

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
List Pochhammer symbols mean products over their lists. This specifies all five K_r in section 4. Those values converge absolutely at (-1,-1); their absolute total-index diagonal is O(log(k+2)/(k+1)^(5/2)).

For the bivariate H function, shared upper numerator triples (e;E,F) produce Gamma(1-e-E*s-F*t); shared lower denominator triples (f;A,B) produce Gamma(1-f-A*s-B*t) in the denominator. A local upper numerator pair (a,A) gives Gamma(1-a-A*s), while an upper denominator pair gives Gamma(a+A*s) in the denominator. A local lower numerator pair (b,B) gives Gamma(b+B*s), while a lower denominator pair gives Gamma(1-b-B*s) in the denominator. The second local variable obeys the same convention. Both H kernels are explicitly specified above.

## Sources and reproduction

Input: C6_single_wheel_H_expression.json, preserved under inputs/previous_expression.json.
The prior wheel, primitive, polylogarithmic and lower-period transformations are
inherited analytic identities. This package proves the new seventh-sector
zero-boundary telescope and parameter identification only.

Standard function definition: Ito, Kumabe, Nakagawa and Nemoto,
*Kampé de Fériet hypergeometric functions over finite fields*, arXiv:2212.14321v2,
Introduction, classical complex-variable definition (not the later finite-field
analogue). Gamma recurrence and growth: NIST DLMF 5.5 and 5.11.
Bivariate H convention for the unchanged blocks: Andrade, Rathie, Farias,
*Exact Bayesian computation using H-functions* (2018), Definition B.

Run:
```
python build_and_verify.py
python numerical.py 256 110
python numerical.py 400 155
python check_roots.py
```
The file DERIVATION.md supplies the full proof, including the endpoint and
parameter-exclusion arguments.
