# A positive quadratic-harmonic wheel form of the corrected C6(1)

## Scope

This pass uses the latest depth-two-polylogarithm expression as its input. It removes the cubic harmonic product from the one remaining wheel series, replacing it by a positive series containing only a product of two harmonic remainders and a linear third-order remainder. The number of auxiliary constants remains four. This is an exact simplification, not a finite ordinary-hypergeometric evaluation and not a new reduction in the number of constants.

All substitutions are in r6 = 2187 C6(1). The inherited graph/RG calculation, source-level missing-pole repair, prior period identifications and depth-two polylogarithm relation are unchanged. The other three auxiliary recurrence series are retained literally. No numerical C6 value is used to infer an identity.

The analytic inputs from earlier packages are the quartic periodization and mixed-Mellin contour normalization, copied under inputs/. The cubic consequence and the weighted simplification are derived below. The proof does not require another integer-relation search.

## 1. Explicit positive replacement

Let
\[
 a_n=\frac{(1/2)_n}{n!},\qquad
 H_n^{(r)}=\sum_{j=1}^n j^{-r},\qquad H_0^{(r)}=0,
\]
\[
 h_n=\log2+H_n-H_{2n},\qquad
 \delta_n=\frac{\pi^2}{3}-4H_{2n}^{(2)}+2H_n^{(2)},
\]
and introduce
\[
 \tau_n=12\zeta(3)-16H_{2n}^{(3)}+4H_n^{(3)}.
\]
The new positive series is
\[
 \boxed{\mathscr W_+=\sum_{n=0}^{\infty}
 a_n^4\big[(8\pi+40h_n)\delta_n+5\tau_n\big].}                 \tag{1}
\]
There is one unbounded summation index; the harmonic numbers in each coefficient are finite sums. No parameter derivative, hidden convolution, or unevaluated moment appears in this definition.

The old series was
\[
 \mathscr W_4=\sum_{n\ge0}a_n^4[(\pi-10h_n)\delta_n-80h_n^3].
\]
The exact identity is
\[
 \boxed{\mathscr W_4=\frac18\mathscr W_+
             -\frac5{16}(B_-+B_+).}                              \tag{2}
\]
The constants on the right are already evaluated:
\[
 B_-=\Gamma(1/4)^4\,{}_4F_3(1/4,1/4,1/2,1/2;3/4,3/4,1;1),
\]
\[
 B_+=\frac{64\pi^4}{\Gamma(1/4)^4}
       {}_4F_3(3/4,3/4,1/2,1/2;5/4,5/4,1;1).
\]
Numerically,
\[
 \mathscr W_+=246.83591539843339490236600176830620752332780350849\ldots.
\]

## 2. A complete cubic sum is evaluated

The useful summation is
\[
 \boxed{\sum_{n\ge0}a_n^4
       [128h_n^3+24h_n\delta_n+\tau_n]
       =\frac{B_-+B_+}{2}.}                                      \tag{3}
\]
It follows from an additional cubic consequence of the established quartic periodization.

Put
\[
 g(z)=\frac{\Gamma(z+1/2)}{\Gamma(z+1)},\qquad
 \mathcal B(t)=\sum_{n\ge0}g(n+t)^4.
\]
Gamma reflection gives
\[
 g(-1/2-z)=-\cot(\pi z)g(z).
\]
Consequently
\[
 \Phi(t)=\cos^4(\pi t)\mathcal B(t)
       +\sin^4(\pi t)\mathcal B(1/2-t)
\]
is the cosine-multiplied bilateral sum. It is entire and periodic of period one. The cosine factor removes all fourth-order half-integer poles. In a vertical strip,
\[
 |\Phi(x+iy)|=O(e^{4\pi|y|}/|y|).
\]
The decay factor excludes Fourier frequencies +2 and -2 as well as all larger frequencies. Reflection under t -> 1/2-t removes the cosine mode, leaving
\[
 \Phi(t)=\alpha+\beta\sin(2\pi t).
\]
This is the earlier quartic periodization, not an assumption inferred from the new numerical values. Gamma reflection and asymptotics are standard [1,3].

Since sin^4(pi t) B(1/2-t) starts at order four and
cos^4(pi t)=1-2pi^2 t^2+O(t^4),
\[
 \Phi'(0)=\mathcal B'(0),\qquad
 \Phi'''(0)=\mathcal B'''(0)-12\pi^2\mathcal B'(0).
\]
The finite Fourier form gives Phi'''(0)=-4pi^2 Phi'(0). Hence
\[
 \boxed{\mathcal B'''(0)=8\pi^2\mathcal B'(0).}                    \tag{4}
\]

### First-derivative normalization

For the proof define normalized elliptic moments
\[
 k(t)={}_2F_1(1/2,1/2;1;t),
\]
\[
 \mathcal M(s)=\int_0^1t^{s-1}k(t)k(1-t)\,dt,
\qquad
 \mathcal I(s)=\int_0^1t^{s-1}(1-t)^{-s}k(t)k(1-t)\,dt.
\]
The inherited contour identity is
\[
 \mathcal I(s)=\frac{\mathcal M(s)-\mathcal M(1-s)}{\cos\pi s}.
\]
Taking its removable value at 1/2 and using the known zeroth moment gives
\[
 \mathcal M'(1/2)=-\frac\pi2\mathcal I(1/2),\qquad
 \mathcal I(1/2)=\frac{B_-+B_+}{4\pi^2}.
\]
The ordinary Mellin series is
\[
 \mathcal M(s)=\frac{\Gamma(s)^2}{\Gamma(s+1/2)^2}
 {}_4F_3(1/2,1/2,s,s;1,s+1/2,s+1/2;1).
\]
Termwise differentiation shows M'(1/2)=B'(0)/(2pi). Therefore
\[
 \boxed{\mathcal B'(0)=-\frac{B_-+B_+}{4}.}                        \tag{5}
\]
All these differentiated series converge locally normally in the required neighborhood. The stored contour proof and normalization are copied under inputs/.

### Evaluate the cubic coefficient

The finite harmonic expressions have the polygamma meanings
\[
 (\log g)'(n)=-2h_n,\quad
 (\log g)''(n)=\delta_n,\quad
 (\log g)'''(n)=-\tau_n.
\]
These follow from half-integer recurrence and special values [2]. Thus
\[
 \left.\frac{d^3}{dt^3}g(n+t)^4\right|_{t=0}
 =-4\pi^2a_n^4(128h_n^3+24h_n\delta_n+\tau_n).
\]
Equations (4)-(5) give (3). Finally the pointwise polynomial equality
\[
 (8\pi+40h)\delta+5\tau
 -8[(\pi-10h)\delta-80h^3]
 =5(128h^3+24h\delta+\tau)
\]
proves (2). This eliminates the cubic harmonic product using an evaluated complete sum; it does not evaluate the remaining quadratic sum.

## 3. Exact insertion into the actual latest expression

The weighted replacement is
\[
 \boxed{-3144\pi^2\mathscr W_4
 =-393\pi^2\mathscr W_+
 +\frac{1965}{2}\pi^2(B_-+B_+).}                                  \tag{6}
\]
Set A=pi+4log2 and retain
\[
 P_4=13B_--3B_+,\qquad
 \mathcal L=-\frac{13A-3\pi}{2}B_-+\frac{3A-\pi}{2}B_+.
\]
Then
\[
 B_-+B_+=(1-4A/\pi)P_4-8\mathcal L/\pi.
\]
The known-part shift is exactly
\[
 \boxed{\Delta_+=
 \left(\frac{1965}{2}\pi^2-3930A\pi\right)P_4
 -7860\pi\mathcal L.}                                            \tag{7}
\]
The collected wheel-period part of the known expression simplifies to
\[
 \boxed{\left(12Q-\frac{57}{4}A^2-\frac{1197}{2}A\pi
                   -\frac{15}{4}\pi^2\right)P_4
 -(18A+1197\pi)\mathcal L.}                                       \tag{8}
\]
Every other monomial is literally unchanged.

The latest depth-two alternative now reads
\[
 \boxed{\begin{aligned}
 2187C_6(1)={}&E_+
 +835584\Lambda+783360\operatorname{Li}_5(1/2)
 -(417792G+39168\pi^2)\Theta\\
 &-393\pi^2\mathscr W_+
 +96\mathscr A-\pi^3\mathscr Z_{\rm rec}+576\pi\mathscr R_A,
 \end{aligned}}                                                   \tag{9}
\]
where E_+=E_(2)+Delta_+. The input polynomial E_(2), the fully collected E_+, and all recurrence initial data are stored in the JSON files. The polylogarithm definitions are unchanged:
\[
 \Lambda=\Re\operatorname{Li}_{3,2}((1+i)/2,1-i),\quad
 \Theta=\Im\operatorname{Li}_3((1+i)/2).
\]
The strict descending convention for the multiple polylogarithm is retained. The compact Xi alternative is obtained by making exactly the same wheel substitution; neither polylogarithm relation is proved anew here.

No term is dropped. The known shift compensates the evaluated sum in (3). The missing-pole repair is retained once as part of the inherited polynomial, not added again.

## 4. Positivity and explicit direct-tail control

For x=n+1/4, the integral representations are
\[
 h_n=\frac14\int_0^\infty e^{-xt}\operatorname{sech}(t/4)\,dt,
\]
\[
 \delta_n=\frac12\int_0^\infty t e^{-xt}\operatorname{sech}(t/4)\,dt,
\qquad
 \tau_n=\frac12\int_0^\infty t^2e^{-xt}\operatorname{sech}(t/4)\,dt.
\]
All three are positive. Therefore every summand of W_+ is positive, including n=0.
They give
\[
 h_n<\frac1{4x},\qquad\delta_n<\frac1{2x^2},\qquad\tau_n<\frac1{x^3}.
\]
Together with the elementary induction bound
\[
 a_n^2\le\frac1{3n+1},
\]
the summand in (1) is smaller than
\[
 \frac{4\pi}{9x^4}+\frac{10}{9x^5}.
\]
For a partial sum retaining 0<=n<N,
\[
 \boxed{0<\mathscr W_+-\mathscr W_{+,N}
 <\frac{4\pi}{27(N-3/4)^3}
  +\frac5{18(N-3/4)^4},\quad N\ge1.}                              \tag{10}
\]
The summands are asymptotic to 4/(pi n^4). This is the same tail order as the old Wq, not a new geometric acceleration. The advantages are removal of cubic harmonic products, full positivity, and the cancellations in (8).

The bound covers exact partial sums, not floating-point rounding or the accelerated asymptotic remainder.

## 5. Verification actually performed

`derive.py` passes 85 exact checks: the cubic Fourier consequence, Bell polynomial, harmonic recurrences, binomial-bound induction, full weighted substitution, collected P4/L coefficients, and preservation of unaffected JSON data. These are mostly coefficient/bookkeeping checks, not 85 new integral identities.

`evaluate.py` separately evaluates the new positive series and the old cubic series with exact-rational gamma-asymptotic coefficients and Hurwitz-zeta tails. It compares them with independently coded AGM elliptic moments. The elliptic reference does not use the new cubic elimination in its integrand.

| Working digits | Direct terms / asymptotic order | Cubic sum vs Bsum/2 | New positive series vs moments | Weighted C6 replacement residual |
|---:|---:|---:|---:|---:|
|50|100 / 30|1.72e-49|1.37e-48|4.11e-48|
|90|180 / 50|5.19e-88|2.74e-86|4.40e-87|
|120|260 / 65|1.65e-111|1.45e-109|1.47e-110|

The observed residuals are floating-point checks, not interval error bounds. The increasing-precision runs show their usable common precision; no claim is made that every printed working digit is accurate.

Literal positive partial sums give:

| N | Partial sum | Reference minus partial | Bound (10) |
|---:|---:|---:|---:|
|8|246.83494435346278420950|9.711e-4|1.322e-3|
|32|246.83590189754302487052|1.351e-5|1.555e-5|
|128|246.83591519392411064994|2.046e-7|2.270e-7|
|512|246.83591539526294836478|3.171e-9|3.488e-9|

### Exact propagation of prior certified intervals

A separate script propagates the existing rational enclosures for c0,c1,Bminus,Bplus,pi,log2. It does not rerun the older interval-series proof. With Bs=Bminus+Bplus and Bd=Bminus-Bplus, the accumulated exact wheel identities give
\[
 72c_0-384c_1=\Delta_{\rm pos}-393\pi^2\mathscr W_+,
\]
\[
 \Delta_{\rm pos}=
 (180\ell^2+72\pi\ell-1161\pi^2/2)B_s
 +(288\ell^2+108\pi\ell-1170\pi^2)B_d.
\]
Exact fraction arithmetic then gives a propagated W_+ interval of width
\[
 \boxed{\text{width}<2.38\times10^{-82}.}
\]
The source intervals and all rational endpoints are included. This enclosure is conditional on the already proved period identities and the inherited certified moment enclosures. It is not a new independent six-loop certification. Both new high-precision series runs lie inside it.

## 6. What remains

There are still four auxiliary single-index series: W_+, AP, Zrec, RA. The number of constants and the retained polylogarithm depth are unchanged. No new finite fixed-parameter ordinary-hypergeometric evaluation is established in this pass.

The exact improvement is the evaluated cubic combination (3), the positive quadratic-harmonic representation (1), and the simpler polynomial (8). The result does not imply that the four-series basis is minimal.

## Reproduction

Python 3, SymPy, and mpmath suffice. Run:

```
python derive.py
python evaluate.py 50 100 30
python evaluate.py 90 180 50
python evaluate.py 120 260 65
python propagate_interval.py
```

## Sources and provenance

1. NIST DLMF 5.5: gamma reflection and recurrence, https://dlmf.nist.gov/5.5 .
2. NIST DLMF 5.15: polygamma series, reflection and recurrences, https://dlmf.nist.gov/5.15 .
3. NIST DLMF 5.11: gamma-ratio asymptotics, https://dlmf.nist.gov/5.11 .
4. Inherited quartic periodization, first-moment normalization, four-shift wheel result and depth-two expression: copied under inputs/. The new relation is derived from those analytic inputs; the generic references are not presented as prior publications of this Ising-coefficient reduction.
