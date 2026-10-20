# An exactly summed companion of the C6 wheel

## Result and scope

The current accepted coefficient is the unchanged `C6_eighth_MeijerG_expression.json`.
The subsequent parameter-direction note is a diagnostic, not a new active formula.
All upstream graph/RG identifications remain inherited. No whole-C6 evaluation is
performed in this continuation and no new physical normalization is asserted.

This note proves a finite zeta-value evaluation for a neighboring fourth-power
wheel moment and derives its generating identity from Rogers--Dougall summation.
It also checks the full local Mishev symmetry on the sixth-power wheel direction.
Neither calculation eliminates a block of the active C6 expression.

The new finite evaluation is

\[
 \boxed{\sum_{n=0}^\infty(4n+1)a_n^4\delta_n
       =\frac{28\zeta(3)}{\pi^2}},\qquad
 a_n=\frac{(1/2)_n}{n!},\quad
 \delta_n=\frac{\pi^2}{3}-4H_{2n}^{(2)}+2H_n^{(2)}.       \tag{1}
\]

The extra weight `(4n+1)` is essential. The actual zero-included wheel is

\[
 B_W=-3144\pi^3D_4-1965\pi^4D_6,\quad
 D_4=\sum a_n^4\delta_n,\quad
 D_6=\sum(4n+1)a_n^6\delta_n.                            \tag{2}
\]

Neither sum in (2) is the sum in (1). We do not install (1) as an evaluation of
D4 or D6, do not introduce a replacement custom C6 sum, and do not modify the
known polynomial. The original `n>=1` wheel is
`Wcentral=8D4+5*pi*D6-(8+5*pi)*pi^2/3`; no zero-index correction changes here.

## 1. A finite digamma generating identity

For |u|<1/2 define the proof coefficient

\[
 R_n(u)=\frac{\Gamma(n+\tfrac12+u)\Gamma(n+\tfrac12-u)
                 \Gamma(n+1)^2}
              {\Gamma(n+1+u)\Gamma(n+1-u)\Gamma(n+\tfrac12)^2}.
\]

Then

\[
\boxed{\sum_{n=0}^\infty(4n+1)a_n^4\,[R_n(u)-1]
 =\frac2{\pi^2}\left[2\psi(\tfrac12)-\psi(\tfrac12+u)
                                      -\psi(\tfrac12-u)\right].} \tag{3}
\]

The right side uses only the ordinary digamma function (`PolyGamma[0,z]` in
Wolfram Language). The left side and the regulator below are proof devices;
no new residual series is added to C6.

### 1.1 Apply a convergent Rogers--Dougall sum

For 0<v<1/4 and u in a compact disk |u|<1/2, let

\[
 \Phi_v(u)=A(u)\,{}_5F_4\left(\begin{matrix}
 \tfrac12,\tfrac54,\tfrac12+u,\tfrac12-u,\tfrac12-v\\
 \tfrac14,1-u,1+u,1+v
 \end{matrix};1\right),
\quad
 A(u)=\frac{\Gamma(\tfrac12+u)\Gamma(\tfrac12-u)}
 {\pi\Gamma(1+u)\Gamma(1-u)}.
\]

Its excess is 2v>0. Rogers--Dougall summation, DLMF 16.4.9, gives exactly

\[
 \Phi_v(u)=\frac2{\pi^2}\Gamma(1+v)\Gamma(v)
 \frac{\Gamma(\tfrac12+u)\Gamma(\tfrac12-u)}
      {\Gamma(\tfrac12+v+u)\Gamma(\tfrac12+v-u)}.          \tag{4}
\]

Subtract Phi_v(0) BEFORE taking v down to zero. The gamma ratio in (4) equals
1 at v=0 and has v-derivative `-psi(1/2+u)-psi(1/2-u)` there. Since
`Gamma(1+v)*Gamma(v)=1/v+O(1)`, the difference tends to the right side of (3).
The two individual series at v=0 would diverge. No value is assigned to either
one separately.

### 1.2 Justify the subtraction and limiting sum

The difference of the nth coefficients is exactly

\[
 (4n+1)a_n^4 T_n(v)[R_n(u)-1],\qquad
 T_n(v)=\frac{(\tfrac12-v)_n(1)_n}{(1+v)_n(\tfrac12)_n}.
\]

For real 0<=v<1/4, 0<T_n(v)<=1. On every closed disk |u|<=r<1/2,
`R_n(u)-1=O_r((n+1)^(-2))` uniformly. One way to see this is the convergent
logarithmic expansion

\[
 \log R_n(u)=\sum_{j\ge1}\frac{u^{2j}}{j}\,\delta_n^{[2j]},\quad
 \delta_n^{[2j]}=\sum_{k\ge0}\left[
 (n+k+\tfrac12)^{-2j}-(n+k+1)^{-2j}\right].              \tag{5}
\]

The bracket is positive. The elementary inequality
`a^j-b^j <= j*a^(j-1)*(a-b)` for 0<b<=a implies

\[
 \delta_n^{[2j]}\le j(n+\tfrac12)^{-2j+2}\delta_n^{[2]},
\]

so the logarithm is uniformly O_r((n+1)^(-2)). Meanwhile
`(4n+1)*a_n^4=O((n+1)^(-1))`. The subtracted summand is therefore uniformly
O_r((n+1)^(-3)), an absolutely summable majorant. Dominated convergence proves
(3). Local uniform analyticity also justifies coefficient extraction in u.

### 1.3 Extract the quadratic coefficient

From (5), R_n(u)=1+delta_n*u^2+O(u^4). The digamma side uses

\[
 \psi^{(2)}(\tfrac12)=-14\zeta(3).
\]

Its u^2 coefficient is `-2*psi^(2)(1/2)/pi^2=28*zeta(3)/pi^2`, proving (1).
This is a specialization derived from a classical summation theorem; no claim
of first discovery in the literature is made.

## 2. Two higher companion evaluations

Let

\[
 \delta_n^{[2j]}=(2^{2j}-2)\zeta(2j)
                 -2^{2j}H_{2n}^{(2j)}+2H_n^{(2j)}.
\]

Thus delta_n^[2]=delta_n. The fourth- and sixth-degree coefficients of (3) give

\[
 \boxed{\sum_{n\ge0}(4n+1)a_n^4
       [\delta_n^2+\delta_n^{[4]}]
       =\frac{248\zeta(5)}{\pi^2}},                       \tag{6}
\]

\[
 \boxed{\sum_{n\ge0}(4n+1)a_n^4
       [\delta_n^3+3\delta_n\delta_n^{[4]}+2\delta_n^{[6]}]
       =\frac{3048\zeta(7)}{\pi^2}}.                     \tag{7}
\]

The general coefficient on the digamma side is
`4*(2^(2j+1)-1)*zeta(2j+1)/pi^2` at u^(2j).
These further identities are checks and possible tools for later reductions;
they do not replace the unweighted D4 or sixth-power D6 in C6.

## 3. Full local symmetry does not force the sixth-wheel derivative to vanish

Mishev's completed balanced function L(a,b,c,d;e;f,g) obeys the fundamental
involution

\[
 (a,b,c,d;e;f,g)\longmapsto
 (a,b,g-c,g-d;1+a+b-f;1+a+b-e,g),
\]

upper-parameter permutations, and interchange of f,g. These generate its W(D5)
invariance. Sources: Mishev arXiv:1008.1011 and Bao arXiv:2609.34016.

Work at p0=(1/2,1/2,1/2,1/2;1;1,1). In tangent coordinates
`x=(da,db,dc,dd,de,df)`, set `dg=da+db+dc+dd-de-df`. The exact script constructs
all five generating matrices. Their common fixed vector is

\[
 r=(1,1,1,1,0,2),
\]

and a common invariant covector is

\[
 \ell(x)=de-\tfrac12(da+db+dc+dd).
\]

Write S=da+db+dc+dd. A second invariant quadratic form is

\[
 q(x)=\tfrac12(da^2+db^2+dc^2+dd^2)+df^2+de\,df-df\,S
           +\tfrac12(de-S/2)^2.                           \tag{8}
\]

It has rank five and kernel spanned by r. Solving the full rational linear
system for invariant symmetric matrices gives dimension TWO. Thus every
invariant quadratic Taylor polynomial is of the form `c1*ell(x)^2+c2*q(x)`.
The constants c1,c2 are not determined by group invariance alone.

The actual opposite-parameter sixth-wheel family is obtained on the path

\[
 p(u)=(\tfrac12+u,\tfrac12+u,\tfrac12+u,\tfrac12+u;
       1+2u;1+u,1+u).
\]

Its six-coordinate direction v=(1,1,1,1,2,1) satisfies

\[
 \ell(v)=0,\qquad q(v)=1.                                 \tag{9}
\]

In particular the path lies outside the fixed direction, but its quadratic
invariant is NOT zero. It is not one of the isotropic Coxeter eigenpaths whose
quadratic coefficient vanishes. An arbitrary coefficient of q is compatible
with all the symmetries above. This concerns the deductions from this symmetry
group alone, not the arithmetic independence or non-reducibility of a period.

The Bailey--Mishev representation specializes to

\[
 L(p(u))=\frac{F_6(u)}{2\pi\Gamma(1+u)\Gamma(1-u)},
\]

where F6(u) is exactly the preceding opposite-shift 7F6 family. Using the
retained identity `F6''(0)=2D6-2*pi^2*U6/3` gives

\[
 \left.\frac{d^2}{du^2}L(p(u))\right|_{0}
       =\frac{2D_6-\pi^2U_6}{2\pi}.                       \tag{10}
\]

Equation (10) identifies the specific curvature still not evaluated. It does
not assert that the derivative is a permitted final special value.

## 4. Numerical and exact checks

`verify.py` executes 75 finite symbolic checks: coefficient recurrences through
u^6 at n=0,...,8; zeta multipliers; invariance under every generating matrix;
rank-five quadratic form and dimension-two invariant Hessian space; the exact
7F6 path parameter lists; and the curvature normalization.

Separate finite numerical sums were evaluated at 60 decimal working digits.
They are not interval-arithmetic certificates. The first-moment tail is bounded
analytically as follows. With x=n+1/4, the retained inequalities
`a_n^2<=1/(3n+1)<=1/(3x)` and `0<delta_n<1/(2x^2)` imply

\[
 (4n+1)a_n^4\delta_n<\frac{2}{9(n+1/4)^3}.
\]

Hence, retaining n=0,...,N-1,

\[
 0<\frac{28\zeta(3)}{\pi^2}-S_N
   <\frac{1}{9(N-3/4)^2},\qquad N\ge1.                   \tag{11}
\]

The finite sums at N=128,512,2048 agree within this exact-arithmetic tail bound.
The bound excludes floating-point rounding, although the 60-digit arithmetic
uncertainty is far smaller than the displayed tails. The N=2048 first-moment
error is about 2.4163e-8. For (6) and (7) the N=2048 numerical differences are
about 4.3217e-15 and 1.7177e-21. The latter are checks, not claimed bounds.
Two nonzero real/complex u specializations of (3) were also checked by finite
partial sums; their residuals are recorded without an invented precision claim.

The value in (1) is

```
3.41022719054004632738817141276933498446405415703708086...
```

No global C6 evaluation was run. The Wolfram diagnostic file has not been
executed in a Mathematica kernel. It is not labeled a complete C6 formula.

## Sources and provenance

* Rogers--Dougall 5F4 summation: NIST DLMF 16.4.9,
  https://dlmf.nist.gov/16.4.E9
* Gamma and polygamma recurrence and half-integer values: DLMF 5.5 and 5.15,
  https://dlmf.nist.gov/5.15
* I. D. Mishev, Coxeter group actions on Saalschuetzian 4F3(1) series and
  very-well-poised 7F6(1) series, arXiv:1008.1011,
  https://arxiv.org/html/1008.1011
* D. Bao, Coxeter Symmetry in Hypergeometric Functions and Elliptic Integral
  Moments, arXiv:2609.34016v1, especially Section 5,
  https://arxiv.org/html/2609.34016v1
* Supplied C6_parameter_direction_derivation.md: the actual D4,D6 parameter
  targets and previously tested termwise MeijerG restriction.
* Supplied C6_central_binomial_wheel_reduction.md: wheel coefficients,
  zero-index convention, and positivity/tail estimates.

The current coefficient file is preserved byte-for-byte under `inputs/`.
