# C6(1): finite representation with 17 fixed special-function values

## Scope

This is the full current finite representation in the admitted multivariate class. The two wheel Kampé de Fériet values have been replaced by one unit-slope bivariate Fox H value. The previous single-H primitive and all other blocks are retained. The full function count is 17 rather than 18. No explicit residual infinite sum, integral, parameter derivative or limit is present. This is representation compression, not an elementary evaluation or arithmetic-independence theorem. Physical graph/RG identification remains inherited.

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

`build_verify.py` passes 36 finite checks of the new parameter lists, gamma kernel, coefficient weights, full-formula substitution, counts, and preservation of the polynomial, primitive, seventh sector and source correction. The global fourth/sixth wheel identity is explicitly inherited, as explained in DERIVATION.md.

Independent new-kernel calculations at 35 and 65 working digits agree with the old wheel component interval midpoints. At 65 digits the discrepancy in W0 is below 1.520e-64. The analytically evaluated inner Barnes transform was separately checked by direct contour quadrature at three complex s-points. These are floating-point implementation checks, not new rigorous Barnes quadrature certificates.

`propagate_interval.py` transfers the accepted rational wheel enclosure to H_W with exact rational arithmetic and a bracket for sqrt(89). Its width is less than 2.221e-146. The certificate is labelled propagated; no new independent verification of the physical coefficient or all-sector numerical reassembly is claimed.

The previously recorded value of the inherited analytic representation remains
\[
C_6^{\rm rep}(1)=14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]

| Standard function class | Fixed values |
|---|---:|
| Multiple polylogarithms | 2 |
| Ordinary generalized hypergeometric | 5 |
| Ordinary univariate Meijer G | 3 |
| Kampé de Fériet | 5 |
| Bivariate Fox H | 2 |
| **Total** | **17** |
| Explicit residual infinite sums or integrals | 0 |

This is a representation count, not minimality or transcendence degree. The five seventh-sector Kampé de Fériet values are unchanged. The wheel and primitive each use one bivariate H value with a different parameter list.

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
List Pochhammer symbols mean products over their lists. This specifies all five J_r in section 4. Those values converge absolutely at (-1,-1); their absolute total-index diagonal is O(log(k+2)/(k+1)^(5/2)).

For the bivariate H function, shared upper numerator triples (e;E,F) produce Gamma(1-e-E*s-F*t); shared lower denominator triples (f;A,B) produce Gamma(1-f-A*s-B*t) in the denominator. A local upper numerator pair (a,A) gives Gamma(1-a-A*s), while an upper denominator pair gives Gamma(a+A*s) in the denominator. A local lower numerator pair (b,B) gives Gamma(b+B*s), while a lower denominator pair gives Gamma(1-b-B*s) in the denominator. The second local variable obeys the same convention. Both H kernels are explicitly specified above.

## Sources and reproduction

The input `C6_compact_H_expression.json` supplies the accepted complete coefficient. The input curvature derivation makes the inherited wheel contour identity explicit. The input `C6_central_binomial_wheel_intervals.json` supplies the previously proved rational numerical enclosure; it is not used to choose any formula coefficient.

The newly derived wheel identity and all assumptions are detailed in DERIVATION.md. Standard definitions and identities are from NIST DLMF 5.5, 5.11, 5.12, 5.15 and 16.17; Andrade–Rathie–Farias, *Exact Bayesian computation using H-functions* (2018), Definition B; and the classical complex-variable definition in the introduction of Ito–Kumabe–Nakagawa–Nemoto, arXiv:2212.14321v2. No general special-function reference is cited as an independent Ising graph calculation.

Run:
```
python build_verify.py
python numerical.py 35 --inner
python numerical.py 65 --inner
python propagate_interval.py
```
