# C6(1): compressed finite representation with 18 fixed special values

## Scope

This is the complete current formula in the admitted multivariate special-function class. The primitive has one fixed bivariate Fox H value instead of four. The earlier optional sixth-sector combination is also packed into one ordinary Meijer G value instead of two. Total fixed-value count: 18 instead of 22.

This is an exact representation compression, not an elementary summation or an arithmetic-independence result. Primitive parameter complexity increases: four half-integer-parameter H values become one higher-order H with four explicit complex-conjugate parameters obtained from a fixed cubic algebraic number. There is still no explicit residual infinite sum, integral, parameter derivative, or limit in the active formula.

The known polynomial, wheel normalization, seventh-sector coefficients, and repaired source contribution are unchanged. The previously proved primitive contour identity is an inherited input. See DERIVATION.md for the new algebraic factorization and exact verification. No new full-C6 evaluation or interval certificate is claimed.

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
-9432\pi^3\mathfrak F_4-5895\pi^4\mathfrak F_6\\
&+96\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}
\left[b_r\mathcal Z_r-98p_r\nu_r\mathfrak J_r\right]\\
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

## 3. The wheel: two Kampé de Fériet values

Use the classical complex-variable Kampé de Fériet convention
\[
F_{q:s;u}^{p:r;t}\!\left[
\begin{matrix}\boldsymbol a:\boldsymbol b;\boldsymbol c\\
\boldsymbol d:\boldsymbol e;\boldsymbol f\end{matrix};x,y\right].
\]
The first group is shared between the two variables; the second and third are local to x and y. The six indices give the lengths of the six lists. Its standard coefficient convention is recorded in Appendix A and in expression.json.

Set
\[
\boldsymbol c=(7/4,1/2,1/2,1,1),\qquad
\boldsymbol d=(3/4,3/2,3/2,2,2).
\]
Then
\[
\boxed{\mathfrak F_4=F_{5:3;0}^{5:4;1}\!\left[
\begin{matrix}\boldsymbol c:(1/2)^{[4]};1\\
\boldsymbol d:1^{[3]};-\end{matrix};1,1\right],}
\tag{7}
\]
\[
\boxed{\mathfrak F_6=F_{5:6;0}^{5:7;1}\!\left[
\begin{matrix}\boldsymbol c:5/4,(1/2)^{[6]};1\\
\boldsymbol d:1/4,1^{[5]};-\end{matrix};1,1\right].}
\tag{8}
\]
The minus sign in an array denotes an empty parameter list.

The exact replacement is
\[
\boxed{W_0=24\mathfrak F_4+15\pi\mathfrak F_6.}
\tag{9}
\]
W0 includes n=0. For the earlier n>=1 convention,
\[
\mathscr W_c=24\mathfrak F_4+15\pi\mathfrak F_6
-\frac{(8+5\pi)\pi^2}{3}.
\]
Thus the current wheel contribution is exactly -9432 pi^3 F4 -5895 pi^4 F6; no separate polynomial compensation occurs.

## 4. The seventh sector: five Kampé de Fériet values

For each of the five indices r in {1,2,3,5,7}, put
\[
t=r/8,\qquad a=t+1/4,\qquad b=t+3/4,\qquad c=t+1/2.
\]
Define
\[
\boxed{\mathfrak J_r=F_{8:0;3}^{8:1;4}\!\left[
\begin{matrix}t+2,(a+1)^{[7]}:1;1,c+1,a,b\\
t+1,(b+1)^{[7]}:-;c,a+1,b+1\end{matrix};-1,-1\right],}
\tag{10}
\]
\[
\mathcal Z_r=t\left[\frac{\Gamma(a)}{\Gamma(b)}\right]^7
{}_9F_8\!\left(\begin{matrix}1,1+t,a^{[7]}\\t,b^{[7]}\end{matrix};-1\right),
\qquad
\nu_r=\frac{(t+1)c}{ab}\left[\frac{\Gamma(a+1)}{\Gamma(b+1)}\right]^7.
\tag{11}
\]
For r=2 the ordinary hypergeometric function has a canceling upper/lower 1; either the displayed 9F8 or its canceled 8F7 has the same value.

Put
\[
c_7=\cos^7(\pi/8),\quad s_7=\sin^7(\pi/8),\quad
R_+=13+22\sqrt2,\quad R_-=22\sqrt2-13,\quad
D_+=2303+1127\sqrt2,\quad D_-=2303-1127\sqrt2.
\]
The finite coefficients are

| r | p_r | b_r |
|---|---|---|
| 1 | c7 R+ | c7 [pi D+ -55 A R+] |
| 2 | -35 | (3283 pi -1295 A)/2 |
| 3 | c7 R- | c7 [(392-55 A)R- -pi D-] |
| 5 | -s7 R- | s7 [(55 A-392/3)R- +pi D-] |
| 7 | s7 R+ | s7 [(2352/5-55 A)R+ +pi D+] |

The complete sector identity is
\[
\boxed{24\pi^3\mathscr M_7=
96\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}
[b_r\mathcal Z_r-98p_r\nu_r\mathfrak J_r].}
\tag{12}
\]
This includes the ordinary Z terms as well as the logarithmic content. Do not keep the old complete M7 series or add its separate Z terms again.

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

`build_verify.py` checks the primitive coefficient-matrix determinant, its exact factorization modulo the cubic polynomial, the normalization identity, the standard-function parameter groups, the entire C6 substitution, and preservation of the full known polynomial and source correction. It passes 39 finite checks. DERIVATION.md specifies precisely which global identity is inherited.

`numerical.py --dps 40 --meijer` and the same run at 70 digits check the new local gamma kernels, direct univariate Meijer G values, and the primitive's factored beta pairing against a separate original quartic-kernel quadrature. There are six successful direct univariate G checks in each run. No independent two-dimensional Mellin-Barnes quadrature or new rigorous interval was computed. No full-C6 numerical reassembly was run.

The previously recorded value of the inherited analytic expression remains
\[
C_6^{\rm rep}(1)=14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]

| Standard function class | Fixed values |
|---|---:|
| Multiple polylogarithms | 2 |
| Ordinary generalized hypergeometric | 5 |
| Ordinary univariate Meijer G | 3 |
| Kampe de Feriet | 7 |
| Bivariate Fox H | 1 |
| Total | 18 |
| Explicit residual infinite sums or integrals | 0 |

This is an occurrence count, not a minimality or transcendence-degree claim. The tradeoff is fewer values with more complicated primitive parameters. The source's lower-order, rational-parameter alternatives remain in the input file.

## Appendix A. Standard coefficient and kernel conventions

For Kampé de Fériet, the coefficient of x^m y^n in the standard defining expansion is
\[
\frac{(\boldsymbol a)_{m+n}(\boldsymbol b)_m(\boldsymbol c)_n}
{(\boldsymbol d)_{m+n}(\boldsymbol e)_m(\boldsymbol f)_n\,m!n!}.
\]
Here a list Pochhammer symbol means a product over the list. This fixes all seven standard values without a custom residual definition.

The wheel identification follows from the rational identity
\[
\frac1{(k+1/2)^2}-\frac1{(k+1)^2}
=3\frac{(7/4)_k(1/2)_k^2(1)_k^2}{(3/4)_k(3/2)_k^2(2)_k^2}.
\]
The seventh-sector identification uses the exact rational coefficient
\[
\frac12\left(\frac1{j+a}+\frac1{j+b}\right)
=\frac c{ab}\frac{(c+1)_j(a)_j(b)_j}{(c)_j(a+1)_j(b+1)_j}.
\]
The primitive compression combines the inherited beta pairing and its contour relation with an exact rank-two factorization. The gamma reflection factors convert its two local quadratics into single G_(5,5) kernels; beta integration then gives the displayed H_* parameters.

All seven Kampé de Fériet values are absolutely convergent at their displayed arguments. For the wheel this follows from nonnegativity and the convergent trigamma remainder; for J_r the total-index absolute diagonal is O(log(k+2)/(k+1)^(5/2)). The single new bivariate H kernel converges absolutely on the stated contours, as shown by the factored local-kernel bound in DERIVATION.md. These analytic convergence arguments are retained in the bundled source derivations, not replaced by the finite spot checks.

## Sources and provenance

The following project sources are included in this package:
- `inputs/latest_expression.json`: latest accepted ordinary-function finite part, unchanged.
- `inputs/broad_expression.json`: earlier standard bivariate parameters and weights.
- `inputs/wheel_expression.json`: earlier shifted seventh weights and wheel source repair.
- `source_derivations/`: the three analytic multivariate conversions, plus the current self-contained formula and lower reduction.

External definitions verified for this assembly:
1. R. Ito, S. Kumabe, A. Nakagawa, Y. Nemoto, *Kampé de Fériet hypergeometric functions over finite fields*, arXiv:2212.14321v2. The introductory **classical complex-variable** definition is used; the finite-field analogue is not used. https://arxiv.org/html/2212.14321v2
2. J. A. A. Andrade, P. N. Rathie, R. B. A. Farias, *Exact Bayesian computation using H-functions*, Computational and Applied Mathematics 37 (2018), 2277–2293, DOI 10.1007/s40314-017-0451-z. Definition B, equations (4)–(8). Author-posted text: https://www.researchgate.net/publication/316770540_Exact_Bayesian_computation_using_H-functions
3. NIST DLMF 16.17 (ordinary Meijer G), 5.15 (polygamma), 5.12 (beta). https://dlmf.nist.gov/16.17 ; https://dlmf.nist.gov/5.15 ; https://dlmf.nist.gov/5.12

No source above is being cited as an independent derivation of the physical C6 coefficient.

New derivation and reproduction: `DERIVATION.md`, `build_verify.py`, and `numerical.py`. The input expression and prior primitive/sixth-sector derivations are preserved under `inputs/`.
