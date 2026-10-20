# C6(1): retained nine-value formula and optional constant-parameter basis

The nine-value formula below remains the default. The new identity in the accompanying derivation supplies an optional ten-value expression with lower-order, A-independent seventh-sector Meijer-G parameters. It does not remove another period.

For the optional form, replace only rho7*G7 by

\[
\frac{(407A-1127\pi)\sqrt{6649}J_L+(259A-49\pi)\sqrt{13546}J_R}{75}.
\]

The values J_L and J_R, their exact ordered parameter lists, and the proof are in the appended derivation. No polynomial or other block changes.

---

# C6(1): nine fixed values with all bivariate arguments (1,1)

This is an exact transformation of the supplied nine-value formula. Only the
seventh-sector H-value changes: H7 = (pi/2) H7unit. The new value has unit slopes
and positive arguments. The fixed-value count remains nine. The cost is six
additional rational parameter entries. No elementary or arithmetic-independence
reduction, new graph/RG derivation, or full-coefficient numerical certificate is
claimed. The interpretation of generalized H as a named special function is the
same as in the supplied formula; this is not a sum-free elementary evaluation.

The coefficient contains no explicit residual sum, integral, parameter derivative,
or limit. Kernel specifications below fix named-function conventions rather than
adding residual integration operations. All upstream physical identifications
remain inherited.

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
+196\pi\sqrt{185}\,\mathcal H_7^{(u)}\bigr]
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

The expression has two multiple-polylogarithm values, four ordinary univariate
Meijer G values, and three unit-slope bivariate H values, all three at (1,1).
The last class is the bivariate Meijer-G subclass, NOT the univariate `MeijerG`
interface in Mathematica. The known polynomial still has eighteen monomials.

The new exact conversion is
\[
\mathcal H_7=\frac\pi2\mathcal H_7^{(u)},\qquad
B_7=24\pi^{3/2}[\rho_7\mathcal G_7+196\pi\sqrt{185}\mathcal H_7^{(u)}].
\]

The new value begins
\[
\mathcal H_7^{(u)}=-12.9610754129279968570904722321988879869693310107184108390656762086403754\ldots.
\]
At 80 working digits the independently summed central seventh sector and the
new fixed-value expression differ by less than 8.85e-74 in r6 units. This is a
floating-point check, not a rigorous interval. The outer Barnes kernel was
computed after analytically performing its inner transform, and separate inner
quadratures checked that transform. No independent full two-dimensional Barnes
quadrature, fresh all-sector C6 computation, or Mathematica-kernel execution
was performed.

The recorded full analytic coefficient remains
\[
C_6^{\rm rep}(1)=14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]
That is an inherited full-coefficient value, not a newly computed one in this pass.

See DERIVATION.md and results/ for the exact algebra, numerical methods,
source hashes, and unchanged input expression. Reproduction needs Python,
SymPy, and mpmath; no network or proprietary kernel is required.


---

# C6(1): a constant-parameter seventh-sector basis

## Result and qualification

The accepted input is `inputs/C6_seventh_unit_slopes_expression.json`. It contains
nine fixed function values. This calculation does **not** claim a reduction to
eight values. The accepted nine-value expression is preserved, including its
known polynomial, source correction, three bivariate functions, and physical
interpretation qualifications.

Two exact alternatives are supplied:

1. A shorter scalar parameter specification of its existing seventh-sector
   contribution, with the fixed-value count still nine.
2. A constant-parameter basis in which two order-(9,9) univariate Meijer G values
   replace one order-(10,10) value. This removes A from the seventh-sector
   special-function parameters, but raises the full count from nine to ten.

Neither alternative is an elementary evaluation, an independence theorem,
a new graph/RG identification, or a rigorous interval certificate. The new
identity is a finite gamma-kernel identity, proved below. It should not be
mistaken for the elimination of the seventh-sector period.

## 1. Starting contribution

Let A = pi + 4 log(2). The inherited complete seventh block, in r6=2187 C6 units, is

\[
 B_7=24\pi^{3/2}\left[\rho_7\mathcal G_7+
          196\pi\sqrt{185}\,\mathcal H_7^{(u)}\right],
\]

where

\[
 a=259A-49\pi,\qquad b=481A-539\pi,\qquad c=407A-1127\pi,
\]

\[
 \rho_7=\sqrt{(a-c)^2+b^2},\qquad
 \eta_\pm=\frac1\pi\arctan\frac{b\pm\sqrt{b^2-4ac}}{2a},
\]

and

\[
 \mathcal G_7=G_{10,10}^{3,8}\left(1\;\middle|\;
  -\tfrac14,(\tfrac12)^{[7]},\eta_+,\eta_-;
  0^{[7]},\tfrac34,\eta_+,\eta_-\right).
\]

The first n upper and first m lower entries are numerator gamma groups. The
bivariate value H7^(u), with its complete fixed parameter lists, is preserved
in the included input formula. It does not depend on A.

## 2. One scalar for the accepted nine-value form

Set

\[
 \chi=\frac{37A}{49\pi},\qquad
 r(\chi)=\sqrt{185\chi^2-462\chi+605},\qquad
 d(\chi)=\sqrt{-139\chi^2+402\chi+29}.
\]

Then

\[
 a=49\pi(7\chi-1),\quad b=49\pi(13\chi-11),\quad
 c=49\pi(11\chi-23),
\]

\[
 \rho_7=49\pi r(\chi),\qquad
 \eta_\pm=\frac1\pi\arctan\frac{13\chi-11\pm d(\chi)}{14\chi-2}.
\]

Consequently the same two-value seventh sector has the compact form

\[
 \boxed{B_7=1176\pi^{5/2}
 \left[r(\chi)\mathcal G_7+4\sqrt{185}\,\mathcal H_7^{(u)}\right].}
\]

This is algebraic collection, not a new summation theorem. For the actual
A the square roots and real inverse tangents have the same branches as the input.
Numerically chi=1.4215116086243354249525622847645644544... .

## 3. Two universal lower-order values

Define

\[
 \alpha_L=\frac1\pi\arctan\frac{75}{32},\qquad
 \alpha_R=\frac1\pi\arctan\frac{89}{75}.
\]

Both are real and lie in (0,1/2). They contain no A, log(2), Q, or period value.

\[
 J_L=G_{9,9}^{3,7}\left(1\;\middle|\;
 -\tfrac14,(\tfrac12)^{[7]},\alpha_L;
 0^{[7]},\tfrac34,\alpha_L\right),
\]

\[
 J_R=G_{9,9}^{2,8}\left(1\;\middle|\;
 -\tfrac14,(\tfrac12)^{[7]},\alpha_R;
 0^{[7]},\tfrac34,\alpha_R\right).
\]

The exact identity is

\[
 \boxed{\rho_7\mathcal G_7
 =\frac{c\sqrt{6649}\,J_L+a\sqrt{13546}\,J_R}{75}.}
\]

It yields

\[
 \boxed{B_7=\frac{8\pi^{3/2}}{25}\left[
 (407A-1127\pi)\sqrt{6649}\,J_L+
 (259A-49\pi)\sqrt{13546}\,J_R+
 14700\pi\sqrt{185}\,\mathcal H_7^{(u)}\right].}
\]

There is no polynomial compensation. This optional representation makes all A
and log(2) dependence explicit in the coefficients of the seventh block. It has
three seventh-sector values instead of two. Its total number of listed parameter
entries is larger; its benefit is lower individual univariate orders and removal
of A from their parameters, not a lower total parameter count or proven speed gain.

## 4. Proof of the gamma-kernel identity

Use the standard inverse-Mellin convention for ordinary Meijer G [1]. For the
proof only put

\[
 Y(s)=\tfrac14-s,\qquad R(s)=
 [\Gamma(s)/\Gamma(s+\tfrac12)]^7,\qquad z=\tan(\pi s).
\]

The coefficient constraint

\[
 75b=89a+32c
\]

implies the exact polynomial identity

\[
 \boxed{az^2+bz+c=
 \frac{c(32z+75)+az(75z+89)}{75}.}
\]

For alpha_L and alpha_R, sine addition gives

\[
 32z+75=\sqrt{6649}\frac{\sin\pi(s+\alpha_L)}{\cos\pi s},
\]

\[
 75z+89=\sqrt{13546}\frac{\sin\pi(s+\alpha_R)}{\cos\pi s}.
\]

The three direct gamma kernels are

\[
 N_7(s)=\frac{\Gamma(s)^3\Gamma(\tfrac12-s)^7\Gamma(\tfrac54-s)}
 {\Gamma(1-s)^4\Gamma(\tfrac14-s)
  \Gamma(s+\eta_+)\Gamma(1-s-\eta_+)
  \Gamma(s+\eta_-)\Gamma(1-s-\eta_-)},
\]

\[
 N_L(s)=\frac{\Gamma(s)^3\Gamma(\tfrac12-s)^6\Gamma(\tfrac54-s)}
 {\Gamma(1-s)^4\Gamma(\tfrac12+s)\Gamma(\tfrac14-s)
  \Gamma(s+\alpha_L)\Gamma(1-s-\alpha_L)},
\]

\[
 N_R(s)=\frac{\Gamma(s)^2\Gamma(\tfrac12-s)^7\Gamma(\tfrac54-s)}
 {\Gamma(1-s)^5\Gamma(\tfrac14-s)
  \Gamma(s+\alpha_R)\Gamma(1-s-\alpha_R)}.
\]

Gamma reflection and recurrence [2] yield

\[
 \rho_7N_7=\pi YR\sec(\pi s)z^4(az^2+bz+c),
\]

\[
 \sqrt{6649}\,N_L=\pi YR\sec(\pi s)z^4(32z+75),
\]

\[
 \sqrt{13546}\,N_R=\pi YR\sec(\pi s)z^5(75z+89).
\]

Therefore, pointwise on the common contour,

\[
 \boxed{\rho_7N_7(s)=
 [c\sqrt{6649}\,N_L(s)+a\sqrt{13546}\,N_R(s)]/75.}
\]

All contours can run upward at Re(s)=1/4. The gamma ratio contributes
O(|Im(s)|^(-7/2)), Y contributes O(|Im(s)|), and sec(pi s) supplies exponential
decay. The tangent factors stay bounded on this line. Thus all three kernels
are O((1+|Im(s)|)^(-5/2) exp(-pi |Im(s)|)), and the integral identities are
absolutely justified [3]. The apparent zero at s=1/4 is not a pole; it comes
from the contiguous ratio Gamma(5/4-s)/Gamma(1/4-s)=1/4-s.

The Barnes integrals appear only in the proof, not as extra operations in the
fixed-value formulas.

## 5. Why this does not give one seventh-sector H value by rescaling

The logarithmic kernel contains p(z)=7z^2+13z+11. Its ordinary companion is
q(z)=az^2+bz+c. These polynomials are not proportional:

\[
 b-\frac{13}{7}a=-448\pi,\qquad
 c-\frac{11}{7}a=-1050\pi.
\]

Thus multiplying the existing H-value by a scalar cannot absorb the ordinary
term. This excludes only that scalar-merger ansatz. No non-reducibility theorem
for a different bivariate parameter transformation is claimed.

## 6. Verification and numerical scope

`build_verify.py` performs 18 finite exact algebra/parameter-list/preservation
checks. `numerical.py` evaluates each of the three gamma kernels separately,
not by assigning the old value to the new pair. Runs at 30 and 55 decimal
working digits are retained. At 55 digits:

- J_L = 28.77406498559502829795605156945296324592508254484144875...
- J_R = 27.4226740316101641326128750058188390552666295159981065...
- |rho7 G7 - (c sqrt(6649) J_L + a sqrt(13546) J_R)/75| < 3.35e-52.

The H7unit value was separately evaluated using its inherited inner Barnes
transform. The old and alternative B7 values agree after rounding at 55 working
digits. This is NOT a new interval certificate, full-C6 evaluation, or
independent verification of the physical six-loop reduction. No Mathematica
kernel was run.

Reproduction:

```
python numerical.py 30
python numerical.py 55
python build_verify.py
```

The attached expression stores the unchanged nine-value default and the complete
optional ten-value formula separately, to avoid silently replacing a shorter
expression with a longer one. All other sectors, the 18-monomial polynomial, the
wheel's zero-index convention, and the source correction are preserved.

## References and source basis

1. NIST DLMF 16.17, standard Meijer-G definition: https://dlmf.nist.gov/16.17
2. NIST DLMF 5.5, gamma reflection and recurrence: https://dlmf.nist.gov/5.5
3. NIST DLMF 5.11, gamma-ratio asymptotics: https://dlmf.nist.gov/5.11
4. Supplied C6_seventh_unit_slopes_expression.json and formula.md: accepted
   coefficient, normalization and all retained blocks.
5. Supplied C6_seventh_two_values_derivation.md: inherited identification of
   the seventh-sector Barnes kernel with the central-binomial sector.

The particular polynomial/kernel decomposition proved above is derived in this
note; the general references specify standard conventions, not an Ising summation.
