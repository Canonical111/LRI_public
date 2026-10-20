# Central-binomial normal form for the complete even-power sector of C6(1)

## Result and scope

Input: `inputs/expression.json`, the retained central-seventh expression.
Normalization: `r6 = 2187 C6(1)`.

The new results in this continuation are the sixth-power identity (4), the
eighth-power identities (8)-(10), and their complete weighted assembly (13).
The lower Bsum/Bdiff identities are inherited from the earlier wheel
normalizations, not claimed as new summation theorems.

All eight ordinary unit-argument values occurring inside Bminus, Bplus, Pb,
PZ6 and PK6 can be removed as separate active inputs. Their complete contribution
and the old wheel become ONE explicit central-binomial harmonic sum. This is
a structural reduction: those eight values have been absorbed into a new
even-sector residual, not separately evaluated in a finite ordinary-value
basis. The number of retained auxiliary quantities remains three: Ecentral,
Pa, and M7central. No arithmetic-independence or minimality assertion is made.

The even-sector harmonic degree is at most two. Its terms are signed and have
O(n^-2) decay, slower than the former positive wheel alone. All terms start at
n=0, and the wheel zero-index correction cancels the explicit pi^6 monomial.
The known polynomial has 20 monomials rather than 30 in the input's symbol
convention. This is a bookkeeping count, not transcendence degree.

The source repair, graph/RG identification, earlier U,V evaluations, primitive,
polylogarithms, and the complete M7 definition are retained. No numerical value
of C6 is used to choose a coefficient.

## 1. Definitions and the two inherited lower-period identities

Put
\[
 a_n=\frac{(1/2)_n}{n!}=\frac{\binom{2n}{n}}{4^n},\quad
 y_n=n+\frac14,\quad \ell=\log2,\quad A=\pi+4\ell,\quad
 Q=\frac{\Gamma(1/4)^4}{\pi},
\]
\[
 h_n=\ell+H_n-H_{2n},\qquad
 \delta_n=\frac{\pi^2}{3}-4H_{2n}^{(2)}+2H_n^{(2)}.
\]
Here H_0^(j)=0. The elementary updates are
\[
 a_{n+1}=a_n\frac{2n+1}{2n+2},\quad
 h_{n+1}=h_n+\frac1{2n+2}-\frac1{2n+1},\quad
 \delta_{n+1}=\delta_n-\frac4{(2n+1)^2}+\frac1{(n+1)^2}.
\]

Let B_s=Bminus+Bplus and B_d=Bminus-Bplus. Retain the earlier wheel identities
\[
 \boxed{B_s=2\pi^4\sum_{n\ge0}(4n+1)a_n^6,\qquad
 B_d=4\pi^3\sum_{n\ge0}a_n^4.}                                  \tag{1}
\]
Equivalently,
\[
 B_\mp=\pi^4\sum_{n\ge0}(4n+1)a_n^6
       \ \mathbin{\pm}\ 2\pi^3\sum_{n\ge0}a_n^4,
\]
where the plus sign on the right belongs to Bminus.

For provenance, the first equality is the saved
B_s=2 pi^4 V, V=sum(4n+1)a_n^6. The second follows from the retained
M(1/2)=pi*4F3((1/2)^4;1,1,1;1) and
M(1/2)=B_d/(4*pi^2). Both are recorded in the earlier
`four_shift_wheel.md` copied into this package. They are also freshly checked
numerically against the input's separate quarter-parameter series.

## 2. New sixth-power reduction of Pb

The input definition is
\[
 H_-=\sum_{n\ge0}\left[\frac{(1/4)_n}{(3/4)_n}\right]^6,\quad
 H_0=\sum_{n\ge0}a_n^6,\quad
 H_+=\sum_{n\ge0}\left[\frac{(3/4)_n}{(5/4)_n}\right]^6,
\]
\[
 P_b=\frac{6Q^3}{\pi}(2H_--1)-104\pi^5H_0
             +\frac{2^{18}\pi^5}{Q^3}H_+.
\]

Define the proof-only entire periodic function
\[
 f_6(t)=\pi^3\sum_{m\in\mathbb Z}
       [\Gamma(3/4+m+t)\Gamma(3/4-m-t)]^{-6}.                    \tag{2}
\]
It is even and one-periodic. Gamma reflection and ratio asymptotics [1,2]
give locally uniform convergence and, on a vertical strip,
\[
 f_6(t)=O(e^{6\pi|\Im t|}(1+|\Im t|)^{-2}).
\]
Moving Fourier-coefficient contours vertically excludes |k|>=3, including the
boundary frequencies because of the factor (1+|Im t|)^-2. Hence
\[
 f_6(t)=c_0+c_1\cos2\pi t+c_2\cos4\pi t.
\]
For every function in this three-dimensional space,
\[
384f(0)-104f(1/4)+32f(1/2)
=312f(1/4)-\frac{176}{\pi}f'(1/4)+\frac{52}{\pi^2}f''(1/4).
\]
Gamma reflection fixes the sample normalizations exactly:
\[
 f_6(0)=\frac{Q^3}{64\pi^6}(2H_--1),\quad f_6(1/4)=H_0,\quad
 f_6(1/2)=\frac{8192}{Q^3}H_+.
\]
Consequently P_b equals pi^5 times the displayed interpolation functional.

At t=1/4 each negative-index term in (2) vanishes to order six. All derivatives
needed here have order at most two, so this half contributes zero. On the
nonnegative half, polygamma reflection and recurrence [3] yield
\[
 f_6(1/4)=\sum a_n^6,\quad f_6'(1/4)=-12\sum a_n^6h_n,
\]
\[
 f_6''(1/4)=\sum a_n^6(144h_n^2+6\delta_n-6\pi^2).               \tag{3}
\]
The constant 312 term cancels the -6*pi^2 derivative term. Thus
\[
 \boxed{P_b=24\pi^3\sum_{n=0}^{\infty}
       a_n^6(88\pi h_n+312h_n^2+13\delta_n).}                   \tag{4}
\]
This is a positive central-binomial series. It does not separately give finite
evaluations of Hminus, H0, or Hplus.

## 3. New eighth-power reduction

The input Y values have the ordinary series
\[
 Y(t)=\sum_{n\ge0}(n+t)
   \left[\frac{\Gamma(n+t+1/4)}{\Gamma(n+t+3/4)}\right]^8,\quad
 Y_r=Y(r/8),
\]
\[
 {\cal H}=(17+12\sqrt2)Y_1-(17-12\sqrt2)Y_7.
\]
The periods in the input are
\[
 P_{Z,6}=\pi^2[(816-828\sqrt2)Y_2+23{\cal H}],\quad
 P_K=\pi^2[432(1-\sqrt2)Y_2+12{\cal H}].
\]

Define another proof-only function
\[
 f_8(t)=\pi^4\sum_{m\in\mathbb Z}
 \frac{m+t}{[\Gamma(3/4+m+t)\Gamma(3/4-m-t)]^8}.                 \tag{5}
\]
It is odd and one-periodic. The same argument gives
\[
 f_8(t)=O(e^{8\pi|\Im t|}(1+|\Im t|)^{-2}),
\]
so frequencies |k|>=4 vanish, including k=+/-4. Thus
\[
 f_8(t)=d_1\sin2\pi t+d_2\sin4\pi t+d_3\sin6\pi t.
\]
Interpolation on these three sine modes gives the exact identity
\[
 f_8(1/8)=\frac{5\sqrt2}{8}f_8(1/4)
          -\frac1{4\pi}f_8'(1/4)
          +\frac{\sqrt2}{32\pi^2}f_8''(1/4).
\]
Gamma reflection, including the sign from the numerator of the negative half,
gives
\[
 Y_2=\pi^4 f_8(1/4),\qquad {\cal H}=64\pi^4 f_8(1/8).            \tag{6}
\]
The factors 64 are fixed by
cos(pi/8)^8=(17+12sqrt2)/64 and
sin(pi/8)^8=(17-12sqrt2)/64.

At the center, the negative half now vanishes to order eight. Put
\[
 u_n^{(8)}=1-16y_nh_n,\qquad
 v_n^{(8)}=256y_nh_n^2-32h_n+8y_n\delta_n-8\pi^2y_n.
\]
Then
\[
 f_8(1/4)=\sum a_n^8y_n,\quad
 f_8'(1/4)=\sum a_n^8u_n^{(8)},\quad
 f_8''(1/4)=\sum a_n^8v_n^{(8)}.                                \tag{7}
\]
It follows that
\[
 \boxed{P_{Z,6}=\sum_{n\ge0}a_n^8[
 (816+92\sqrt2)\pi^6y_n-368\pi^5u_n^{(8)}
                       +46\sqrt2\pi^4v_n^{(8)}],}              \tag{8}
\]
\[
 \boxed{P_K=\sum_{n\ge0}a_n^8[
 (432+48\sqrt2)\pi^6y_n-192\pi^5u_n^{(8)}
                       +24\sqrt2\pi^4v_n^{(8)}].}              \tag{9}
\]
For the combination needed in C6 these give
\[
\boxed{\begin{aligned}
24P_{Z,6}+\frac13P_K=8\pi^4\sum_{n\ge0}a_n^8\big[
 &(2466-834\sqrt2)\pi^2 y_n-1112\pi(1-16y_nh_n)\\
 &+139\sqrt2(256y_nh_n^2-32h_n+8y_n\delta_n)\big].
\end{aligned}}                                                  \tag{10}
\]
No eighth-shifted gamma value or parameter derivative occurs on the right.
This is a conversion of the combined ordinary periods to explicit harmonic
sums, not a finite elementary evaluation.

## 4. Complete even-sector substitution

The Bminus/Bplus block in the input is
\[
 C_s B_s+C_d B_d,
\]
where
\[
 C_s=60Q-\frac{105}{4}A^2-9A\pi-\frac{2469}{4}\pi^2,\quad
 C_d=96Q-42A^2-18A\pi-1227\pi^2.
\]
Using (1), (4), and (10), define the finite polynomials
\[
 \boxed{R_{4,n}=384Q-168A^2-72A\pi-4908\pi^2-3144\delta_n,}
\]
\[
\boxed{\begin{aligned}
 R_{6,n}={}&\pi y_n(480Q-210A^2-72A\pi-4938\pi^2-7860\delta_n)\\
 &+50688\pi h_n+179712h_n^2+7488\delta_n,
\end{aligned}}
\]
\[
\boxed{\begin{aligned}
 R_{8,n}=8\pi\big[
 &(2466-834\sqrt2)\pi^2y_n-1112\pi(1-16y_nh_n)\\
 &+139\sqrt2(256y_nh_n^2-32h_n+8y_n\delta_n)\big].
\end{aligned}}
                                                                    \tag{11}
\]
The new residual is
\[
 \boxed{{\cal E}_{\rm c}=\sum_{n=0}^{\infty}
  a_n^4[R_{4,n}+a_n^2R_{6,n}+a_n^4R_{8,n}].}                    \tag{12}
\]
Every weight is a power of ONE a_n sequence. The only harmonic quantities in
this even-sector sum are h_n, h_n^2, and delta_n.

The complete exact insertion is
\[
\boxed{\begin{aligned}
 C_sB_s+C_dB_d+24P_b+24P_{Z,6}+\frac13P_K
       -393\pi^3{\mathscr W}_{\rm c}
 =\pi^3{\cal E}_{\rm c}+1048\pi^5+655\pi^6.
\end{aligned}}                                                   \tag{13}
\]
The last two terms come ONLY from changing the wheel lower index from one
to zero:
\[
393\pi^3\frac{(8+5\pi)\pi^2}{3}=1048\pi^5+655\pi^6.
\]
The +655*pi^6 cancels the explicit -655*pi^6 in the previous known part. The
new standalone pi^5 coefficient is
\[
 -\frac{413393}{128}+1048=-\frac{279249}{128}.
\]
No seventh-power n=0 term is separated or added again.

## 5. Updated full coefficient

The complete active formula is
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_{\rm alg}+835584\Lambda+391680H_5\\
 &+13056\sqrt2(32G+3\pi^2)H_3+96P_a
   +\pi^3{\cal E}_{\rm c}+24\pi^3{\mathscr M}_7,
\end{aligned}}                                                   \tag{14}
\]
where G is Catalan's constant and
\[
 E_{\rm alg}=\frac Q8[
 63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)]
 +Q^2(29\pi-249A)+{\cal P}_0,
\]
\[
\boxed{\begin{aligned}
{\cal P}_0={}&-\frac{4059}{640}A^5+\frac{255}{8}A^4\pi
-\frac{2985}{64}A^3\pi^2-\frac{7827}{64}A^2\pi^3
+\frac{7863}{16}A^2\zeta(3)-3264A^2G\pi\\
&+3072AG^2+2208AG\pi^2+\frac{788693}{640}A\pi^4
-34816G\pi^3-\frac{279249}{128}\pi^5\\
&-\frac{3651379}{16}\pi^2\zeta(3)+\frac{20237049}{8}\zeta(5).
\end{aligned}}                                                   \tag{15}
\]
The full definitions of Pa, M7, Lambda, H3, and H5 are retained in the updated
JSON, as are all old definitions for provenance. In particular, M7 is exactly
the previous alternating seventh-power sum, not a newly adjusted constant.

There are no separate ordinary hypergeometric periods at argument one in
(14)-(15). H3 and H5 remain at argument one half. The period content has been
consolidated into Ecentral, not proved to have fewer independent constants.

## 6. Absolute convergence and an explicit direct tail bound

The inherited Laplace representations of h_n and delta_n give
\[
 0<h_n<\frac1{4y_n},\qquad 0<\delta_n<\frac1{2y_n^2},\qquad
 a_n^2\le\frac1{3n+1}\le\frac1{3y_n}.
\]
These bounds also follow from the polygamma series and their positive
integral representations [3].

Set
\[
 b_4=384Q-168A^2-72A\pi-4908\pi^2,\quad
 b_6=480Q-210A^2-72A\pi-4938\pi^2,\quad
 b_8=2466-834\sqrt2>0.
\]
One has |1-16y_nh_n|<=3. Writing q=y_nh_n in [0,1/4],
\[
 -1\le256q^2-32q\le8.
\]
Consequently
\[
 |256y_nh_n^2-32h_n+8y_n\delta_n|\le12/y_n.
\]
It follows that the absolute value of the summand of (12) is at most
\[
 K_2y_n^{-2}+K_3y_n^{-3}+K_4y_n^{-4}+K_5y_n^{-5},
\]
where
\[
 K_2=\frac{|b_4|}{9}+\frac{\pi|b_6|}{27},\quad
 K_3=\frac{8\pi^3 b_8}{81},
\]
\[
 K_4=\frac{1572}{9}+\frac{16602\pi}{27}
                      +\frac{26688\pi^2}{81},\quad
 K_5=\frac{14976}{27}+\frac{13344\sqrt2\pi}{81}.
\]
For the literal partial sum with 0<=n<N, N>=1,
\[
\boxed{|{\cal E}_{\rm c}-{\cal E}_{{\rm c},N}|
 \le\frac{K_2}{N-3/4}+\frac{K_3}{2(N-3/4)^2}
 +\frac{K_4}{3(N-3/4)^3}+\frac{K_5}{4(N-3/4)^4}.}               \tag{16}
\]
This is a direct exact-arithmetic tail bound, not a bound on the separate
asymptotic numerical accelerator.

The leading summand is
\[
 \frac{864Q-378A^2-144A\pi-9846\pi^2}{\pi^2n^2}+O(n^{-3}).
\]
This explains why the literal sum is slower than the old wheel alone.
The earlier numerical evaluator remains a valid alternative.

## 7. Executed checks and interval provenance

`verify.py` passes 30 exact algebra checks. These include both finite Fourier
interpolations on every basis mode, sample normalizations, the period
polynomials, the complete pointwise weighted substitution, the known-part
shift, and unchanged source correction / primitive / M7 / polylogarithms.

`check_numerical.py` independently sums the NEW central-binomial moments.
It uses exact-rational gamma-ratio asymptotic coefficients and finite
Hurwitz-zeta tails. It does not insert the old period values in the new sums.
The old interval midpoints are read only afterwards for comparison.

The runs (working digits,N,J)=(75,128,30), (110,224,44), and (190,512,85) are
saved. N counts direct terms and J the finite asymptotic order. Each is also
rerun with (N+32,J+6). These are floating-point checks, NOT new certified
asymptotic error bounds.

At 190 working digits the largest discrepancy for the five ordinary periods
Bminus, Bplus, Pb, PZ6, PK6 is below 4.35e-159. Changing N and J changes the new
Ecentral value by about 3.17e-159. These observations do not certify 190 digits.

The even-sector value begins
\[
 {\cal E}_{\rm c}
 =438146.4246106938412895706051971211076099444261530146661664550922\ldots.
\]

`propagate_intervals.py` uses exact outward-rounded dyadic arithmetic to
propagate the inherited period intervals through (13). It gives
\[
 \operatorname{width}(I_{{\cal E}_{\rm c}})<8.341\times10^{-144}.
\]
The new 190-digit floating calculation lies inside that propagated interval.
The interval proof is the inherited bounds plus the new analytic identities;
it is not the floating-point containment test.

Reassembling (14) using the inherited Pa, polylogarithm, and certified M7
intervals gives
\[
 C_6^{\rm rep}(1)
 =14331.6870327580543204454632552462171183173230619887904582031423\ldots
\]
with interval width below 1.183e-145, overlapping the previous complete
certificate. No new physical graph/RG accuracy claim is made.

## 8. A checked obstruction for one proposed Pa boundary reduction

This section is separate from the even-sector identity. It records a failed
analytic route precisely, so the same rational-antiderivative search need not
be repeated. It does NOT prove that Pa lacks a finite special-value evaluation.

Let A and C denote the two inherited 9-by-9 recurrence matrices in this section
only. The recurrence implies
\[
 Z'(x)=\frac{(1+x^2)A+xC+x^2I}{x(1-x^2)}Z(x).
\]
Writing V(x)=sqrt(x)Z(x) gives
\[
 V'(x)=R(x)V(x),\qquad
 R(x)=\frac{(1+x^2)(A+I/2)+xC}{x(1-x^2)}.
\]
The primitive integrand is 4 V_0(x)/x. A universal rational-row boundary
primitive would require a row r(x) satisfying
\[
 r'(x)+r(x)R(x)=4e_0^T/x.                                      \tag{17}
\]

Local residue analysis bounds the possible rational divisor completely.
At x=0 the residue eigenvalues are 1/2,1,3/2 (multiplicity three each).
At x=1 they are 0,-1,-2,-2,-3,-4,-4,-5,-6, so no pole of r is possible.
At x=-1 all nine residue eigenvalues are 1. At infinity the maximum possible
integer polynomial degree is one. There can be no pole at an ordinary point
of the equation. Therefore every rational solution of (17), if one existed,
would have the form
\[
 r(x)=a\,x+b+c/x+d/(x+1)
\]
with four constant nine-entry rows.

Clearing denominators yields 54 rational equations for 36 coefficients.
The exact coefficient matrix has rank 36; its augmentation has rank 37.
`check_boundary_obstruction.py` supplies and verifies a rational left-null
certificate lambda with lambda*M=0 and lambda*b=1.

Thus there is no such rational row for the FULL nine-dimensional module.
This does not exclude identities specific to the particular seeded solution,
algebraic or transcendental boundary coefficients, transformations to other
function classes, or finite period relations of a different type.

## Reproduction

Python 3, SymPy, and mpmath suffice. No network access is needed.

```text
python formula.py
python verify.py
python check_numerical.py 75 128 30
python check_numerical.py 110 224 44
python check_numerical.py 190 512 85
python propagate_intervals.py
python check_boundary_obstruction.py
```

The JSON contains the full active formula and all inherited definitions.
The source correction is preserved exactly once. Files under `inputs/` are
provenance inputs; obsolete formula fields retained inside the JSON are
explicitly identified as legacy.

## References and analytic provenance

[1] NIST DLMF 5.5, gamma reflection and recurrence:
`https://dlmf.nist.gov/5.5`.

[2] NIST DLMF 5.11, gamma-ratio asymptotics:
`https://dlmf.nist.gov/5.11`.

[3] NIST DLMF 5.15, polygamma recurrence, reflection and half-integer values:
`https://dlmf.nist.gov/5.15`.

[4] Supplied central-seventh expression and certificate: the starting formula,
M7 definition, and all physical graph/RG assumptions.

[5] Earlier `four_shift_wheel.md`, copied into inputs: the retained Bsum/Bdiff
normalizations used in (1). The sixth-/eighth-power interpolation reductions
and complete weighted assembly are derived here, not attributed to DLMF.
