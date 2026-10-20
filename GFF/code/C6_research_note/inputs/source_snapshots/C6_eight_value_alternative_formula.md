# C6(1): optional eight-value representation

This is an exact call-count compression, not a proved eight-dimensional
arithmetic period basis. One quintic-parameter Kampé de Fériet value replaces
the two MPL components. Seven other functions remain unchanged. The known
polynomial grows from 18 to 21 expanded monomials, so the prior nine-call formula
remains a simpler-parameter alternative. All upstream physical identifications
are inherited. No new full-C6 numerical certificate is claimed.

## 1. Full coefficient and new polylogarithmic value

Put
\[
\ell=\log2,\quad A=\pi+4\ell,\quad Q=\Gamma(1/4)^4/\pi,\quad G=\operatorname{Catalan}.
\]
Then
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_8+835584\Re(\Omega\mathcal F)+B_{\rm low}+B_6+B_8
-393\pi\sqrt{89}\,\mathcal H_W\\
&+24\pi^{3/2}[\rho_7\mathcal G_7+196\pi\sqrt{185}\,\mathcal H_7^{(u)}]
+7680\pi^3\mathcal H_*.
\end{aligned}}
\]
Every fixed function and parameter is given here or in the following sections.
There is no uncomputed sum or integral added to this expression. The multivariate
functions retain their standard defining conventions, not new C6-specific heads.

Define
\[
z=(1+i)/2,\quad\kappa=3\pi^2/64+\pi\ell/8-G/2,\quad c=3\ell/2+3i\pi/4,
\]
\[
P(x)=[i\kappa(x+1)^2+c(x+1)+3](x+2)^3
-z[i\kappa(x+2)^2+c(x+2)+2](x+1)^3.
\]
Take all five roots with multiplicity, in the sign convention
\[
P(x)=\kappa z\prod_{j=1}^5(x+\beta_j),\qquad\Omega=zP(0)/8.
\]
Put
\[
\boxed{\mathcal F=F_{8:0;2}^{8:1;3}\!\left[
\begin{matrix}1^{[3]},1+\boldsymbol\beta:1;1^{[3]}\\
3^{[3]},\boldsymbol\beta:-;2^{[2]}\end{matrix};z,z\right].}
\]
The KdF convention is: shared lists act on m+n; the first and second local lists
act on m and n. Its coefficient for lists A/D, B/E, C/F is
\((A)_{m+n}(B)_m(C)_n/[(D)_{m+n}(E)_m(F)_n m!n!]\).
All beta parameters avoid nonpositive integers, as proved in DERIVATION.md.

The complete known polynomial is
\[
E_8=\frac Q8[63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)]
+Q^2(29\pi-249A)+\mathcal P_8,
\]
\[
\begin{aligned}
\mathcal P_8={}&\frac1{1920}[5367A^5-26520A^4\pi-137150A^3\pi^2
+699510A^2\pi^3-2972057A\pi^4+4837177\pi^5]\\
&+48G[64AG-17A^2\pi-56A\pi^2-153\pi^3]\\
&+\frac{\zeta(3)}{16}[273879A^2-532032A\pi-1503123\pi^2]
+\frac{9025209}{8}\zeta(5).
\end{aligned}
\]
The source repair is included once. No wheel zero-index term, primitive zero
mode, or former -144 Q^3/pi term is appended.

## 2. Unchanged ordinary Meijer G blocks


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

\]
with upward contours Re(s)=1/4, Re(t)=1/8 and standard measure ds dt/(2 pi i)^2. This fixes the named-function parameters; it is not an extra integral in the master expression.

The entire zero-included wheel is
\[
\boxed{W_0=\frac{\sqrt{89}}{\pi^2}\mathcal H_W,\qquad
-393\pi^3 W_0=-393\pi\sqrt{89}\mathcal H_W.}

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

\]
The ordered upper list has eight numerator entries; the ordered lower list has
three numerator entries. In the standard inverse-Mellin convention its kernel is
\[
N_7(s)=\frac{\Gamma(s)^3\Gamma(\tfrac12-s)^7\Gamma(\tfrac54-s)}
{\Gamma(1-s)^4\Gamma(\tfrac14-s)
\Gamma(s+\eta_+)\Gamma(1-s-\eta_+)
\Gamma(s+\eta_-)\Gamma(1-s-\eta_-)}.

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
 
\]

The upper/lower numerator counts are, respectively: shared (1,0), first
local (8,3), second local (3,2). The logarithms of the two positive arguments
are both zero. There is no negative-argument logarithm to choose.

For unambiguous normalization, the standard inverse-Mellin kernel is

\[
 A_7(s)R(t)\frac{\Gamma(\frac12-s-t)}{\Gamma(\frac32-s-t)},
 
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
 
\]

Both lines run upward, with Re(s)=1/4, Re(t)=1/16, and the usual measure
 ds dt/(2*pi*i)^2. This is the kernel of the established function (1), not an
additional integral operation in the active coefficient.

Gamma reflection and recurrence [2] give the equivalent simple kernel

\[
 \boxed{\frac{A_7(s)\cot(2\pi t)}
 {(\frac12-t)(\frac12-s-t)}.}
 
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

\]
Consequently
\[
\boxed{96P_a=7680\pi^3\mathcal H_*.}

\]
There is no added polynomial or zero-index compensation. Numerically, from the proved beta-product representation,
\[
\mathcal H_*=135.0234860111609249908488197821688196879586538126766890134710495752391\ldots.
\]
This numerical check is not an interval certificate.




## 6. Counts and numerical scope of this alternative

There are four ordinary univariate Meijer G values, three unit-slope bivariate
H values at (1,1), and one classical KdF value at ((1+i)/2,(1+i)/2). Taking
Re(Omega F) is a specified real linear projection of one complex function call.
This count does not prove the independence or dimension of the underlying periods.

Fresh computations checked the new polylog block only, using its own root-based
coefficients and separate HPL continuation. No other sector was numerically
reevaluated in this run. Results and exact finite algebra checks are in results/.
The recorded full C6 value remains inherited from the prior calculation.
