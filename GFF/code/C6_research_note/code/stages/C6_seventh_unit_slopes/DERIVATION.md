# C6(1): a positive-argument, unit-slope seventh-sector value

## Result and scope

The accepted input is `inputs/previous_expression.json`, copied from
`C6_seventh_two_values_expression.json`. It contains nine fixed function values.
The seventh sector is

\[
 B_7=24\pi^{3/2}[\rho_7\mathcal G_7+392\sqrt{185}\,\mathcal H_7].
\]

The old H-value uses arguments (1,-1), Log(-1)=i*pi, and the shared slope
pair (2,1). This continuation proves

\[
 \boxed{\mathcal H_7=\frac\pi2\mathcal H_7^{(u)}}
\]

where the new H-value has arguments (1,1) and all slopes equal to one.
The complete coefficient still has NINE fixed values. All three of its
bivariate values can now be specified in the unit-slope bivariate Meijer-G
subclass. The tradeoff is six additional rational parameter-list entries:
the second local order changes from 2/2 to 5/5. No elementary evaluation,
arithmetic-independence reduction, or smaller number of periods is asserted.

This is an exact transformation, not a new function defined by assigning the
old value to a symbol. The standard bivariate H convention is [1], Definition B.
The complete lists below identify the named function independently of the
conversion formula. The new proof concerns the phase average and gamma
multiplication. The prior identification of the sector with C6, the full
known polynomial, all other blocks, and the graph/RG assumptions are inherited.

## 1. Parameters of the new fixed value

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

## 2. Remove the negative-argument phase by a proved average

Let B_c denote the upward Barnes contour value with measure dz/(2*pi*i).
For Re(s)=1/4 and c=1/8 define, only for the proof,

\[
 J_\pm(s)=\mathcal B_{1/8}
 \left[\frac{\Gamma(t)\Gamma(1-t)e^{\pm i\pi t}}
 {(1-t)(1-2s-t)}\right].
 \tag{5}
\]

The accepted old H uses J_-(s). Its inner evaluation is

\[
 J_-(s)=\frac{\psi(1-2s)+\gamma_E}{-2s}.
 \tag{6}
\]

This can be checked independently by residues at t=-k: their values are
1/[(k+1)(k+1-2s)], and the partial fractions give (6). The digamma series
and recurrence are standard [2,3]. It is a proof identity, not a surviving
digamma call in the finite expression.

The difference of the two phases simplifies exactly:

\[
 \Gamma(t)\Gamma(1-t)
 (e^{-i\pi t}-e^{i\pi t})=-2\pi i.
\]

Therefore

\[
 J_-(s)-J_+(s)
 =-2\pi i\mathcal B_{1/8}
 \left[\frac1{(1-t)(1-2s-t)}\right]=0.
 \tag{7}
\]

Both poles of the rational integrand are to the right: Re(t)=1 and
Re(t)=1/2. Closing left gives zero, and the large boundary vanishes because
the rational integrand is O(|t|^-2). Thus the equality is analytic; it is
not an appeal to the final value being real.

Averaging (5), using (7), and applying gamma reflection gives

\[
 J_-(s)=\pi\mathcal B_{1/8}
 \left[\frac{\cot(\pi t)}{(1-t)(1-2s-t)}\right].
 \tag{8}
\]

## 3. Remove the doubled slope

In (8), substitute t=2v. The measure contributes a factor 2, whereas the
two denominators contribute 4. Hence

\[
 J_-(s)=\frac\pi2\mathcal B_{1/16}
 \left[\frac{\cot(2\pi v)}{(\frac12-v)(\frac12-s-v)}\right].
 \tag{9}
\]

The needed unit-slope gamma identity is

\[
 \cot(2\pi v)=
 \frac{\Gamma(v)\Gamma(v+\frac12)\Gamma(1-v)\Gamma(\frac12-v)}
 {\Gamma(v+\frac14)\Gamma(v+\frac34)
  \Gamma(\frac14-v)\Gamma(\frac34-v)}.
 \tag{10}
\]

It follows from gamma reflection and the sine double-angle formula. In
particular, the numerator pair-products are 2*pi^2/sin(2*pi*v), and the
denominator pair-products are 2*pi^2/cos(2*pi*v). There is NO extra factor
of pi in (10).

Multiplying (9) by the unchanged A7(s) kernel, equation (10) and gamma
recurrence give exactly (2)-(3), and thus

\[
 \boxed{\mathcal H_7=\frac\pi2\mathcal H_7^{(u)}.}\tag{11}
\]

The same argument gives the useful inner evaluation

\[
 \mathcal B_{1/16}
 \left[\frac{\cot(2\pi v)}{(\frac12-v)(\frac12-s-v)}\right]
 =-\frac{\psi(1-2s)+\gamma_E}{\pi s}.
 \tag{12}
\]

## 4. Absolute convergence and reality

On s=1/4+iu and t=1/16+iv,

\[
 |\cot(2\pi t)|\le1+\sqrt2,
\]

and the two rational denominators in (4) have absolute values

\[
 \sqrt{(7/16)^2+v^2},\qquad
 \sqrt{(3/16)^2+(u+v)^2}.
\]

Cauchy--Schwarz supplies the uniform estimate

\[
 \int_{\mathbb R}\frac{dv}
 {\sqrt{(7/16)^2+v^2}\sqrt{(3/16)^2+(u+v)^2}}
 \le\frac{16\pi}{\sqrt{21}}.
\]

The first local factor has

\[
 |A_7(1/4+iu)|=O((1+|u|)^{-3/2}e^{-\pi|u|}),
\]

by gamma-ratio asymptotics [4]. The product is absolutely integrable, so
Fubini is legitimate. The new value is real: conjugation reverses both
imaginary coordinates and preserves its conjugate parameter pairs.
No positivity claim is made; the value is negative.

## 5. Complete C6 substitution

Keep the old elementary parameters

\[
 A=\pi+4\log2,\quad a_7=259A-49\pi,\quad
 b_7=481A-539\pi,\quad c_7=407A-1127\pi,
\]

\[
 \Delta_7=\sqrt{b_7^2-4a_7c_7},\quad
 \rho_7=\sqrt{(a_7-c_7)^2+b_7^2},\quad
 \eta_\pm=\pi^{-1}\arctan\frac{b_7\pm\Delta_7}{2a_7},
\]

and the same G7=G_(10,10)^(3,8)(1) with upper list
(-1/4,(1/2)^[7],eta+,eta-) and lower list (0^[7],3/4,eta+,eta-).
Then

\[
 \boxed{B_7=24\pi^{3/2}
 [\rho_7\mathcal G_7+196\pi\sqrt{185}\,\mathcal H_7^{(u)}].}
\]

The full coefficient is

\[
 \boxed{\begin{aligned}
 2187C_6(1)={}&E+B_{\rm pol}+B_{\rm low}+B_6+B_8
 -393\pi\sqrt{89}\,\mathcal H_W\\
 &+24\pi^{3/2}[\rho_7\mathcal G_7
 +196\pi\sqrt{185}\,\mathcal H_7^{(u)}]
 +7680\pi^3\mathcal H_*.
 \end{aligned}}
\]

Every other block is unchanged. FORMULA.md repeats every definition and the
complete known polynomial. Delta E=0. No zero-index term is separated and no
source correction is re-added. There are still nine fixed values: two multiple
polylogarithms, four ordinary univariate Meijer G values, and three unit-slope
bivariate H values. This is not an identification of the bivariate functions
with Mathematica's univariate MeijerG implementation.

## 6. Executed checks

The finite verifier regenerates the parameter-to-kernel identities, contour
separation inequalities, the Jacobian factor, the full weighted substitution,
and unchanged polynomial/source fields. It passes 39 finite exact checks.
These are implementation checks, not 39 independent analytic theorems.

`check_inner.py` evaluates J-, J+, and the new unit-slope inner contour directly
at three complex s values, at 40 and 65 working decimal digits. The new local
gamma quotient is separately checked against its cotangent form.

`numerical.py` evaluates the new outer gamma kernel using the proved inner
identity (12), and separately evaluates G7. It compares the resulting B7 with
a fresh Euler-weighted sum of the ORIGINAL central-binomial coefficient. Runs
at 45 and 80 working digits are recorded. At 80 digits:

    H7unit = -12.961075412927996857090472232198887986969331010718410839065676208640375404010557
    B7 = -11409730.021892930408560182590309518113633547796634226659894210756965908394081253
    absolute old/new B7 discrepancy = 8.8434366004167113e-74

These are floating-point comparisons, NOT interval certificates. The new H
was NOT independently computed by a full two-dimensional Barnes quadrature;
the direct inner quadratures and outer computation are separate checks.
No full-C6 numerical evaluation or Wolfram-kernel execution was performed.

## References

[1] J. A. A. Andrade, P. N. Rathie, R. B. A. Farias, Exact Bayesian computation
using H-functions, Definition B, equations (4)-(8), DOI
https://doi.org/10.1007/s40314-017-0451-z . Author-posted full text:
https://www.researchgate.net/publication/316770540_Exact_Bayesian_computation_using_H-functions .
Used for the standard bivariate function convention, not as a source for this C6 identity.

[2] NIST DLMF 5.5, gamma reflection, recurrence, and duplication:
https://dlmf.nist.gov/5.5 .

[3] NIST DLMF 5.15, polygamma functions: https://dlmf.nist.gov/5.15 .

[4] NIST DLMF 5.11, gamma-ratio asymptotics: https://dlmf.nist.gov/5.11 .

[5] Input files copied in inputs/: the preceding exact ninth-value formula,
its gamma kernels, and its project-specific seventh-sector identity. These
analytic inputs are inherited, not rederived by the phase transformation.
