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
