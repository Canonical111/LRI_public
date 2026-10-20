# C6(1): twelve fixed values with lower-degree seventh-sector parameters

## Scope

This is a complete finite special-function representation of the inherited
analytic coefficient, with the same twelve fixed function values as the input.
The five seventh-sector Kampé de Fériet functions now use degree-ten parameter
polynomials instead of degree sixteen. The fifty roots are specified explicitly
by finite polynomials; they are not inferred from a numerical period.

The normalized local lists have orders 4/3, with eighteen upper and eighteen
lower shared parameters. Uniform listed parameter entries fall from 340 to 220
across the five values. No further function call is removed in this step.
Literal diagonal summation is slower: its absolute terms have order
log(k)/k^(3/2), rather than log(k)/k^(5/2). Both forms converge absolutely.

The known polynomial, other finite sectors, source correction, and graph/RG
qualification are unchanged. This is a parameter simplification, not an
arithmetic-independence theorem or a new all-sector numerical certificate.

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
p_r\widehat\Omega_r\widehat{\mathcal K}_r\\
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

## 4. Seventh sector with degree-ten shared-root parameters

This section replaces the WHOLE prior seventh-sector block. Do not add either
the old Z/J values or the preceding degree-sixteen K values to this version.

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


Define the finite polynomial
\[
\boxed{\begin{aligned}
\widetilde P_r(x)={}&
\xi_r(x+t)(x+b)^8(x+c+1)\\
&+(x+t+1)(x+a)^6(x+c)
\left[\xi_r(x+a+1)(x+b+1)-(x+c+1)\right].
\end{aligned}}
\]
It has degree ten and leading coefficient 2 xi_r. Specify ALL ten root parameters
with multiplicity by
\[
\boxed{\widetilde P_r(x)=2\xi_r\prod_{j=1}^{10}(x+\gamma_{r,j}).}
\]
Their order is immaterial. These are algebraic over the field generated by the
known t_r and xi_r, not asserted algebraic over the rationals. They are different
parameters from the previous degree-sixteen roots.

With boldsymbol(gamma)_r the ten-element list, put
\[
\boxed{\widehat{\mathcal K}_r=
F_{18:0;3}^{18:1;4}\!\left[
\begin{matrix}
a^{[6]},a+1,c,1+\boldsymbol\gamma_r:
1;1,c+1,a,b\\
(b+1)^{[7]},c+2,\boldsymbol\gamma_r:
-;c,a+1,b+1
\end{matrix};-1,-1\right].}
\]
The convention is fixed in Appendix A. List addition is componentwise, and a
dash is an empty list. Define the explicit prefactor
\[
\boxed{\widehat\Omega_r=
\left[\frac{\Gamma(a)}{\Gamma(b)}\right]^7
\frac{\widetilde P_r(0)}{(c+1)b^8}.}
\]
Then the COMPLETE seventh-sector contribution is
\[
\boxed{B_7=24\pi^3\mathscr M_7=
9408\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}
p_r\widehat\Omega_r\widehat{\mathcal K}_r.}
\]
The displayed sum has FIVE terms only. The prefactors are signed. The positive
9408 coefficient is consistent with the old negative coefficient because
\[
\widehat\Omega_r\widehat{\mathcal K}_r=-\Omega_r\mathcal K_r.
\]
There is no additional lower-boundary constant and no polynomial compensation.

The exact interval sign checks give xi_1,xi_2,xi_3,xi_5<0 and xi_7>1. For
real x>=0 these make the new polynomial respectively strictly negative or
strictly positive. It therefore has no nonnegative real root. In particular,
no gamma_(r,j) is a forbidden nonpositive integer lower parameter, and the
prefactor is nonzero. The normalized shared and local coefficients are positive
at integer indices. Every total-index diagonal has the alternating sign (-1)^n.

All five defining bivariate series converge absolutely at (-1,-1), with absolute
diagonal bound O(log(n+2)/(n+1)^(3/2)). This is slower than in the degree-sixteen
representation. The finite identity and its endpoint justification are proved
in DERIVATION.md.

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

## 6. Executed checks and numerical scope

The complete finite substitution, gamma normalization, new coefficient ratios,
finite Abel boundary, degree and parameter counts, and preservation of the
unchanged input are checked by 127 exact finite tests. They are implementation
checks, not a count of independent analytic theorems. Lower-parameter admissibility
has a separate exact rational sign proof.

Three coefficient constructions were evaluated separately: the retained shifted
harmonic summand, the previous degree-sixteen KdF diagonals, and the new shared-
ratio KdF diagonals. Runs with (N,working digits)=(280,120) and (420,170) yield
complete old/new seventh-block absolute discrepancies of about 6.90e-78 and
5.21e-120. The block value is
\[
B_7=-11409730.02189293040856018259030951811363354779663422666\ldots.
\]
These are floating-point comparisons, NOT interval certificates. Root-based
Pochhammer ratios were separately checked at six indices per shift, with
maximum relative discrepancy below 4.16e-110 at 110 working digits.

No new all-sector C6 numerical evaluation, physical graph/RG proof, or Wolfram
kernel execution was performed. The number of fixed values remains twelve:

| Class | Fixed values |
|---|---:|
| Multiple polylogarithms | 2 |
| Ordinary univariate Meijer G | 3 |
| Kampé de Fériet | 5 |
| Bivariate Fox H | 2 |
| **Total** | **12** |
| Explicit residual infinite sums / integrals | 0 |

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

Input: C6_five_seventh_values_expression.json (retained under inputs/).
Prior wheel, primitive, polylogarithmic and lower-period transformations are
inherited. The new proof is the finite Abel summation in DERIVATION.md.

Kampé de Fériet convention: Ito, Kumabe, Nakagawa, Nemoto,
arXiv:2212.14321v2, Introduction (classical complex-variable definition).
Gamma recurrence and asymptotics: NIST DLMF 5.5 and 5.11.
The unchanged bivariate H convention is Andrade–Rathie–Farias, Definition B.

From the package directory:
```
python build_and_verify.py
python numerical.py 280 120
python numerical.py 420 170
python check_roots.py
```
Results are recorded in JSON, with no saved numerical target used to generate
the new coefficients.
