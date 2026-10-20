# C6(1): a projection-free real-valued representation

This is the recommended nine-value alternative, not an independence/minimality result. It uses two established real-valued functions at pi/2 rather than the real projection of a quintic-parameter complex KdF value. It keeps the original eighteen-monomial polynomial size. The optional all-log-sine form below has ten fixed values. Seven other values, zero-index conventions and source correction are unchanged.

Put
\[
\ell=\log2,\quad A=\pi+4\ell,\quad Q=\Gamma(1/4)^4/\pi,\quad G=\operatorname{Catalan},
\quad L=\operatorname{Ls}_3(\pi/2),\quad C=\operatorname{Cl}_{2,1,2}(\pi/2).
\]
Use the Borwein–Straub real log-sine and descending-index multiple Clausen conventions, as specified in DERIVATION.md. The multiple Clausen notation removes an explicit real-part operation but does not evaluate the weight-five period in simpler constants.

## 1. Complete formula

\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_{\rm real}-2176[(32G+9\pi^2)L+128C]
+B_{\rm low}+B_6+B_8\\
&-393\pi\sqrt{89}\,\mathcal H_W
+24\pi^{3/2}[\rho_7\mathcal G_7+196\pi\sqrt{185}\,\mathcal H_7^{(u)}]
+7680\pi^3\mathcal H_*.
\end{aligned}}
\]
All seven non-polylogarithmic values are specified after this section.

The complete known polynomial is
\[
E_{\rm real}=\frac Q8[63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)]
+Q^2(29\pi-249A)+\mathcal P_{\rm real},
\]
\[
\begin{aligned}
\mathcal P_{\rm real}={}&\frac{21}{640}A^5+\frac7{64}A^3\pi^2
+\frac{1149}{64}A^2\pi^3+\frac{7863}{16}A^2\zeta(3)\\
&+192AG(16G+3\pi^2)+\frac{14853}{640}A\pi^4
-\frac{15776}{3}G\pi^3-\frac{145153}{128}\pi^5\\
&+\frac{722279}{48}\pi^2\zeta(3)-\frac{805959}{8}\zeta(5).
\end{aligned}
\]
There is no new physical term: E_real=E-476 pi^3(32G+9pi^2)/3 is the exact compensation for replacing D3=-Ls3(pi/2)/2-7pi^3/192. All previously included source corrections remain included once.

### Optional single-real-family formula

Let U=Ls_(2,3)^(0,0)(pi/2) and V=Ls_(4,1)^(0,0)(pi/2) in Umezawa's convention (first index belongs to the innermost variable). Then
\[
C=-GL+\frac32U+\frac12V-\frac{13}{192}G\pi^3+
\frac{451}{3072}\pi^2\zeta(3)+\frac{7635}{2048}\zeta(5).
\]
Thus one can replace the first two terms of the boxed formula by
\[
E_{\rm LS}-6528(3\pi^2-32G)L-139264(3U+V).
\]
Here E_LS has exactly the same Q-block and the same first six displayed polynomial terms as E_real. In its last four monomials, the coefficients of G pi^3, pi^5, pi^2 zeta(3), zeta(5) are respectively
\[
13600,\qquad -145153/128,\qquad -413491/16,\qquad -9112839/8.
\]
This formula uses three standard real log-sine values instead of two real log-sine/Clausen values. It has ten fixed values overall. Neither choice introduces quintic parameters or explicit Re/Im in the coefficient.

The definitions of Ls and Cl below are standard function conventions, not additional residual integrations to apply to the master expression. See DERIVATION.md for their real defining kernels, the exact weight-five identity, and the scope of the numerical checks.

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

### New unit-slope seventh-sector H value

Keep the old parameter

\[
 \beta=\frac1\pi\arctan\frac{13+i\sqrt{139}}{14},
\]

with the principal complex inverse tangent, and let a bar denote conjugation.
Define the ordered parameter/slope lists

\[
 \begin{split}
 \mathbf a&=((-\tfrac14,1),(\tfrac12,1)^{[7]},(\beta,1),(\bar\beta,1)),\\
 \mathbf b&=((0,1)^{[6]},(1,1),(\tfrac34,1),(\beta,1),(\bar\beta,1)),\\
 \mathbf c&=((0,1),(\tfrac12,1),(\tfrac12,1),(\tfrac14,1),(\tfrac34,1)),\\
 \mathbf d&=((0,1),(\tfrac12,1),(-\tfrac12,1),(\tfrac14,1),(\tfrac34,1)).
 \end{split}
\]

A superscript [j] means j repeated entries. Then

\[
 \boxed{
 \mathcal H_7^{(u)}=
 H_{1,1;\,10,10;\,5,5}^{0,1;\,3,8;\,2,3}
 \left[
 \begin{matrix}
 (\tfrac12;1,1):\mathbf a;\mathbf c\\
 (-\tfrac12;1,1):\mathbf b;\mathbf d
 \end{matrix}\;\middle|\;1,1\right].}
 \tag{1}
\]

The upper/lower numerator counts are, respectively: shared (1,0), first
local (8,3), second local (3,2). The logarithms of the two positive arguments
are both zero. There is no negative-argument logarithm to choose.

For unambiguous normalization, the standard inverse-Mellin kernel is

\[
 A_7(s)R(t)\frac{\Gamma(\frac12-s-t)}{\Gamma(\frac32-s-t)},
 \tag{2}
\]

where

\[
 A_7(s)=\frac{\Gamma(s)^3\Gamma(\frac12-s)^7\Gamma(\frac54-s)}
 {\Gamma(1-s)^3\Gamma(-s)\Gamma(\frac14-s)
 \Gamma(s+\beta)\Gamma(1-s-\beta)
 \Gamma(s+\bar\beta)\Gamma(1-s-\bar\beta)}
\]

and

\[
 R(t)=\frac{\Gamma(t)\Gamma(t+\frac12)\Gamma(1-t)\Gamma(\frac12-t)^2}
 {\Gamma(\frac32-t)\Gamma(t+\frac14)\Gamma(t+\frac34)
  \Gamma(\frac14-t)\Gamma(\frac34-t)}.
 \tag{3}
\]

Both lines run upward, with Re(s)=1/4, Re(t)=1/16, and the usual measure
 ds dt/(2*pi*i)^2. This is the kernel of the established function (1), not an
additional integral operation in the active coefficient.

Gamma reflection and recurrence [2] give the equivalent simple kernel

\[
 \boxed{\frac{A_7(s)\cot(2\pi t)}
 {(\frac12-t)(\frac12-s-t)}.}
 \tag{4}
\]

All numerator pole families are correctly separated on these lines. In
particular, the shared numerator argument has real part 3/16; no contour
pinch or parameter limit is introduced. The zeros from reciprocal gamma
factors are not poles.

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



## 6. Current size and numerical scope

The recommended expression uses one ordinary log-sine value, one multiple Clausen value, four ordinary Meijer-G values, and three unit-slope bivariate H values: nine fixed values in total. Its known polynomial has eighteen monomials. The optional all-log-sine expression uses three log-sine values and the same seven others: ten fixed values, also eighteen polynomial monomials. The multiple Clausen replacement is a real-valued convention, not a new arithmetic relation. Neither formula is asserted minimal.

Both new coefficient formulas have no explicit Re/Im operation, infinite sum, definite integral, parameter derivative, or limit to apply. Integral/series specifications of named standard functions in DERIVATION.md only fix conventions. The seven non-polylogarithmic parameters may still include complex conjugate pairs inherited from the original expression; this step does not claim to remove those parameters.

The new polylogarithmic identities were checked with 60 and 105 working decimal digits. At the higher precision, the weighted discrepancies were below 1.143e-100 (two-value real form) and 2.286e-100 (all-log-sine alternative). These are floating-point checks, not new interval certificates. The earlier numerical values quoted inside the unchanged elliptic definitions above are inherited and were not rerun in this step.

The recorded full analytic coefficient remains
\[
C_6^{\rm rep}(1)=14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]
No full-C6 numerical or physical graph/RG verification was performed here. The old wheel intervals retain their wheel-only scope. The existing source correction remains included exactly once.

See DERIVATION.md, check.py, build.py, and results/ for the new proofs, checks, and complete machine-readable expressions. Python, SymPy, and mpmath suffice to replay them.
