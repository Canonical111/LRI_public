# A positive central-binomial double sum for the complete primitive P_a

## Result and precise scope

Input: `inputs/symmetric_expression.json`, the supplied
`C6_primitive_symmetric_expression.json`. The normalization is
`r6 = 2187 C6(1)`. The starting symmetric primitive, all prior period
identifications, source correction, and upstream graph/RG assumptions remain
inherited. This is a reduction of that saved analytic representation, not a
new verification of the physical six-loop graph calculation.

The complete primitive has the exact representation
\[
\boxed{P_a=\pi\,\mathscr P_c,\qquad
\mathscr P_c=\sum_{m,n\geq0}
 \frac{a_m^4a_n^4}{\binom{m+n}{m}}\,F_{m,n}.}                 \tag{1}
\]
The summand below is explicit, symmetric, and strictly positive. Its only
initial transcendental constants are pi, log(2), and zeta(3). There is no Q,
Catalan constant, quarter-shifted gamma sequence, integral, parameter
derivative, or matrix recurrence in (1).

The three four-index beta/Horn pairings in the most recent optional formula
are replaced by one two-index harmonic sum. The older optional Bailey formula
also had two indices, but used two different coefficient sequences, Q and
1/Q. The new formula instead uses precisely the same central-binomial
sequence as the even and seventh sectors.

**This is not a finite ordinary one-variable special-value evaluation of P_a,
nor a proof of fewer independent periods.** There are still three retained
auxiliary quantities. The new primitive is two-index; it is not being described
as a one-index series by hiding a finite convolution. Its literal convergence
is slower than the retained geometric nine-component recurrence, which remains
available as an alternative evaluator.

## 1. Fully explicit summand

For every integer n>=0, define
\[
 a_n=\frac{(1/2)_n}{n!}=\frac{\binom{2n}{n}}{4^n},\qquad
 h_n=\log2+H_n-H_{2n},\qquad
 \delta_n=\frac{\pi^2}{3}-4H_{2n}^{(2)}+2H_n^{(2)}.
\]
Here \(H_n^{(r)}=\sum_{j=1}^n j^{-r}\), and \(H_0^{(r)}=0\).
Put k=m+n and
\[
\boxed{
 u_{m,k}=\pi+8h_m+H_k-H_m,\qquad
 v_{m,k}=4\delta_m-\pi^2+H_k^{(2)}-H_m^{(2)}.}                \tag{2}
\]
Equivalently,
\[
 u_{m,k}=\pi+8\log2+H_k+7H_m-8H_{2m},
\]
\[
 v_{m,k}=\frac{\pi^2}{3}+H_k^{(2)}+7H_m^{(2)}-16H_{2m}^{(2)}.
\]
The complete polynomial is
\[
\boxed{\begin{aligned}
 F_{m,n}={}&15(u_{m,k}^2+v_{m,k})(u_{n,k}^2+v_{n,k})\\
 &+(60H_k^{(2)}+14\pi^2)u_{m,k}u_{n,k}\\
 &-60[\zeta(3)-H_k^{(3)}](u_{m,k}+u_{n,k})\\
 &+30(H_k^{(2)})^2+14\pi^2H_k^{(2)}+90H_k^{(4)}
       -\frac{49}{6}\pi^4.
\end{aligned}}                                                    \tag{3}
\]
Its maximum harmonic order and polynomial degree are four. No zeta(4) value
needs separate initialization: it has been replaced by pi^4/90 in (3).

Both indices begin at zero. With \(b=\pi+8\log2\), the included initial term is
\[
\boxed{F_{0,0}=15b^4+24\pi^2b^2-120b\zeta(3)-\frac{13}{2}\pi^4.} \tag{4}
\]
It is not added separately to the known C6 polynomial.

The rational coupling weight \(w_{m,n}=a_m^4a_n^4/\binom{m+n}{m}\) has
\[
 w_{0,0}=1,\qquad
 \frac{w_{m+1,n}}{w_{m,n}}=
 \frac{(m+1/2)^4}{(m+1)^3(m+n+1)},
\]
and the analogous update in n. Thus the summation kernel needs only rational
updates and the displayed harmonic accumulators.

## 2. Three Gauss products on one Frobenius family

Use the existing kernels
\[
 v(x)={}_2F_1(1/4,1/4;1;x),\qquad
 h(x)={}_2F_1(1/4,1/4;1/2;x),\qquad
 Q=\Gamma(1/4)^4/\pi.
\]
The function h(x) is distinct from the harmonic remainder h_n.
For 0<x<1 set L=-log(x), and define
\[
 p_0(x)=v(x)^2,\qquad
 p_1(x)=\sqrt Q\,v(x)h(1-x),\qquad
 p_2(x)=Qh(1-x)^2.
\]
Their common-coefficient expansions are
\[
\boxed{\begin{aligned}
 p_0(x)&=\sum_{n\ge0}a_n^3x^n,\\
 p_1(x)&=\sum_{n\ge0}a_n^3x^n(L+\pi+6h_n),\\
 p_2(x)&=\sum_{n\ge0}a_n^3x^n
       [(L+\pi+6h_n)^2+3\delta_n-\pi^2].
\end{aligned}}                                                    \tag{5}
\]
The first identity is Clausen's square identity [1]. The third was already
present in the supplied expression under `frobenius_square_identity`. The
second follows from the same Frobenius construction. For completeness all
three are proved together here, so that their relative normalization is fixed.

### A common differential equation and its initial data

Both v(x) and h(1-x) satisfy
\[
 x(1-x)y''+(1-3x/2)y'-y/16=0.
\]
Their quadratic products therefore satisfy
\[
 \mathcal L p=0,\qquad
 \mathcal L=\theta^3-x(\theta+1/2)^3,\quad \theta=x\frac{d}{dx}.
                                                               \tag{6}
\]
This symmetric-square equation is checked directly; it is also the standard
3F2 differential equation [2].

Introduce the proof-only family
\[
 f_\varepsilon(x)=\sum_{n\ge0}
 \left[\frac{(1/2+\varepsilon)_n}{(1+\varepsilon)_n}\right]^3
 x^{n+\varepsilon}.
\]
Its coefficient recurrence gives exactly
\[
 \mathcal L f_\varepsilon=\varepsilon^3 x^\varepsilon.
\]
Thus the first three derivatives of orders 0,1,2 at epsilon=0 solve (6).
The logarithmic coefficient derivatives are
\[
 \left.\partial_\varepsilon\log c_n(\varepsilon)\right|_0
      =6(H_{2n}-H_n),
\]
\[
 \left.\partial_\varepsilon^2\log c_n(\varepsilon)\right|_0
      =6H_n^{(2)}-12H_{2n}^{(2)}=3\delta_n-\pi^2.
\]
These are finite rational harmonic identities. Let d0=pi+6log(2).
Then p0=f0, p1=d0*f0-f'_0, and p2=f''_0-2*d0*f'_0+d0^2*f0.

To identify the solutions, the zero-balanced Gauss connection formula and
quarter-argument digamma value give [3,4]
\[
 v(x)=1+O(x),\qquad
 \sqrt Q\,h(1-x)=-\log x+\pi+6\log2+O(x\log x).
\]
They match the complete constant/logarithm polynomials of the three solutions
at zero. Uniqueness of the Frobenius solutions fixes (5), including the constant
term in p2. In particular, no undetermined multiple of p0 is discarded.

All parameter derivatives in this argument are proof devices. Formula (1)
has none.

## 3. Cancellation of Q in the complete primitive

The inherited symmetric primitive is
\[
\begin{aligned}
 P_a=\int_0^1\frac{dx}{\sqrt{x(1-x)}}\big[
 &15Q^2h(x)^2h(1-x)^2\\
 &+24Q\pi^2h(x)h(1-x)v(x)v(1-x)\\
 &-4\pi^4v(x)^2v(1-x)^2\big].
\end{aligned}
\]
In terms of (5), this is exactly
\[
\boxed{P_a=\int_0^1\frac{
 15p_2(x)p_2(1-x)+24\pi^2p_1(x)p_1(1-x)
 -4\pi^4p_0(x)p_0(1-x)}{\sqrt{x(1-x)}}\,dx.}               \tag{7}
\]
Since all three series (5) use a_n^3 and pi/log(2), Q no longer occurs in the
coefficients. This does not remove Q from the known polynomial or the even
sector of C6; it concerns the new definition of P_a only.

## 4. Perform every beta moment explicitly

For fixed m,n let k=m+n, X have the beta(m+1/2,n+1/2) probability density, and
write L=-log X, K=-log(1-X). Put
\[
 b_m(L)=L+\pi+6h_m,\qquad
 q_m(L)=b_m(L)^2+3\delta_m-\pi^2.
\]
Euler's beta integral [5] gives
\[
 B(m+1/2,n+1/2)=\pi\frac{a_ma_n}{\binom{k}{m}}.
\]
Multiplying by the two coefficients a_m^3 a_n^3 produces exactly the rational
weight in (1), times pi. The remaining polynomial is the beta expectation
\[
 F_{m,n}=\mathbb E\{15q_m(L)q_n(K)+24\pi^2b_m(L)b_n(K)-4\pi^4\}.
                                                               \tag{8}
\]
This expectation is evaluated below, not left as part of the definition.

From the beta gamma quotient and polygamma series [5,6],
\[
 \mathbb E b_m(L)=u_{m,k},\qquad
 \operatorname{Var}(L)+(3\delta_m-\pi^2)=v_{m,k},
\]
with the analogous identities for n,K. The mixed cumulants needed are
\[
 c=\operatorname{Cov}(L,K)=H_k^{(2)}-\pi^2/6,
\]
\[
 d=\kappa(L,L,K)=\kappa(L,K,K)=-2[\zeta(3)-H_k^{(3)}],
\]
\[
 e=\kappa(L,L,K,K)=-6[\zeta(4)-H_k^{(4)}].
\]
Here a mixed cumulant means the corresponding derivative of
log E exp(sL+tK). The fourth-moment polynomial is
\[
\begin{aligned}
 \mathbb E[q_m(L)q_n(K)]={}&
 (u_m^2+v_m)(u_n^2+v_n)+4u_mu_nc+2c^2\\
 &+2(u_m+u_n)d+e,
\end{aligned}
\]
and E[b_m(L)b_n(K)]=u_m u_n+c. Substitution in (8) and zeta(4)=pi^4/90 give
precisely (3). In particular, the constants combine to -49*pi^4/6; omitting
mixed third or fourth cumulants would give a wrong formula.

## 5. Positivity, absolute convergence, and a direct tail bound

The supplied harmonic remainders obey
\[
 h_n>0,\quad \delta_n>0,\quad
 h_n<\frac1{4n+1},\quad a_n^2\le\frac1{3n+1}.
\]
For example, h_n and delta_n have the positive integral representations
\[
 h_n=\frac14\int_0^\infty e^{-(n+1/4)t}\operatorname{sech}(t/4)dt,
\quad
 \delta_n=\frac12\int_0^\infty t e^{-(n+1/4)t}\operatorname{sech}(t/4)dt.
\]
They follow from the polygamma formulas [6]; the a_n inequality is elementary
induction.

For L>=0,
\[
 b_m(L)>\pi,
\]
\[
 q_m(L)=(L+6h_m)^2+2\pi(L+6h_m)+3\delta_m>0.
\]
Consequently the entire polynomial inside (8) is strictly greater than
20*pi^4, and
\[
\boxed{F_{m,n}>20\pi^4\quad(m,n\ge0).}                         \tag{9}
\]
This establishes positivity of the expanded summand even though (3) contains
negative terms. The endpoint growth in (7) is at most an integrable inverse
square-root weight times a squared logarithm. Thus Tonelli's theorem justifies
the termwise integration of the positive combined summand and proves absolute
convergence. No divergent pieces are subtracted.

Here is a completely explicit, deliberately conservative direct tail bound.
Let
\[
 P_{a,N}=\pi\sum_{m+n<N}w_{m,n}F_{m,n},\qquad N\ge2,
 \qquad T_N=10+\log(N-1).
\]
Then
\[
\boxed{0<P_a-P_{a,N}
 <\frac{610\pi}{3(N-1)}(T_N^2+2T_N+2).}                       \tag{10}
\]
It is a bound for literal triangular partial sums, not for an accelerated
Euler approximant.

### Proof of the bound

For fixed k>=2, take n>=m by symmetry, so n>=k/2>=1. We have
u_m<=10+log(k)=T, u_n<11/2, v_m<5 and v_n<0. To see the sharper n bounds,
use h_n<1/(4n+1) and H_k-H_n<=log(k/n)<=log2, together with
pi<22/7 and log2<7/10. Also delta_n<=delta_1, so
v_n<=pi^2/2-13<0. The quantities u_j^2+v_j are positive by (8).

In (3), the term containing -(zeta(3)-H_k^(3)) is negative. The remaining
constant polynomial is at most its limit -4*pi^4, also negative. Dropping
these terms and using pi^2<10 gives
\[
 F_{m,n}<\frac{1815}{4}(T^2+5)+1320T<610T^2,\qquad T\ge10.
\]
Because a_{j+1}/a_j increases with j, a_m*a_n<=a_k. Therefore
\[
 \sum_{m+n=k}w_{m,n}
 \le a_k^4\sum_{m=0}^k\binom{k}{m}^{-1}
 \le 3a_k^4<\frac1{3k^2}.
\]
For k>=3, the reciprocal-binomial sum is bounded by
2+4(k-2)/(k(k-1))<=3; the smaller cases are direct.
The function (10+log x)^2/x^2 decreases for x>=1. Summing and integrating
from N-1 to infinity now gives (10).

The bound concerns exact arithmetic. The shipped mpmath output evaluates
both finite sums and this bound in floating point and is not an outward-
rounded interval certificate.

## 6. Full C6 insertion and preservation

With E_alg, Lambda, H3, H5, E_c and M7 unchanged from the input,
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_{\rm alg}+835584\Lambda+391680H_5\\
 &+13056\sqrt2(32G+3\pi^2)H_3\\
 &+\pi^3\mathcal E_c+24\pi^3\mathscr M_7+96\pi\mathscr P_c.
\end{aligned}}                                                   \tag{11}
\]
The compensating known-part shift is **zero**. Neither the (0,0) primitive
term nor any existing even/seventh zero-index term is separated. The source
correction is preserved verbatim and not added again.

The exported JSON has the complete input definitions. Its active primitive
is PaCentral, while the old recurrence is retained verbatim under
`retained_primitive_recurrence_series_terms`. The previous symmetric and
Bailey alternatives remain intact. The current active list is
`Ecentral, PaCentral, M7central`: two one-index harmonic sums and one two-index
harmonic sum, all on the same a_n sequence. Historical count/provenance fields
from older steps remain historical; `counts.this_continuation` describes this
step explicitly.

This change does not assert that the three quantities are arithmetically
independent. It also does not prove an additional finite ordinary summation.

## 7. Executed checks

`verify.py` passes 351 exact checks. Most are finite coefficient tests, not
independent theorems: the first 25 coefficients of the three product identities,
144 beta/binomial weights, and elementary bound samples. The substantive
symbolic tests include the general Frobenius recurrence, its symmetric-square
operator, the full beta fourth moment, the compact polynomial, and the included
zero-index term. `build_expression.py` separately checks the full r6 weight and
preservation of every unaffected top-level field.

At 65-digit working precision, `check_numerical.py` compares all three series
(5) against independent Gauss calls at x=0.1,0.25,0.5,0.75, retaining 650 terms.
The largest difference is below 1.368e-63. Five separate beta integrations of
(8), including unequal m,n, agree with the explicit polynomial; the largest
absolute difference is below 1.245e-60. These are floating-point cross-checks.

The new literal double sums, computed without Q or a reference value in their
summands, give the following P_a approximants:

| N, retaining m+n<N | P_a,N | Difference from inherited P_a value | Bound (10), floating evaluation |
|---:|---:|---:|---:|
| 1 | 318561.142626980936683107800291 | 16364.9026210709 | not applied |
| 8 | 334036.860773713623228250820808 | 889.184474338215 | 15385.4144015975 |
| 32 | 334717.014497164334337152629132 | 209.030750887504 | 4313.69019440873 |
| 128 | 334871.044075297571740249581458 | 55.0011727542661 | 1267.71378366141 |
| 512 | 334911.187801594160188256151955 | 14.8574464576777 | 372.639175168353 |

The comparison value is the inherited
334926.045248051837883222001240077786613085905253136679683127...
It is not an input to the new summation. The table explicitly shows why the
long prior value must not be attributed to a short raw truncation of (1).
No new high-precision interval for P_a or the full coefficient is constructed
here; the preceding certificates and their scope are retained.

## Reproduction

Python 3, SymPy and mpmath suffice. No network access is needed to run:

```text
python verify.py
python build_expression.py
python check_numerical.py
```

The output JSON files under results/ contain the exact check list, preservation
record, numerical comparisons, and complete updated expression.

## Sources

Input-specific primitive normalization and prior reductions: the supplied
C6_primitive_symmetric_expression.json and C6_primitive_symmetric_derivation.md.
The p2 expansion was already an inherited identity; the proof in section 2
reconstructs it along with the normalized mixed product.

[1] NIST DLMF 16.12, Clausen product identities:
https://dlmf.nist.gov/16.12
[2] NIST DLMF 16.8.3, generalized hypergeometric differential equation:
https://dlmf.nist.gov/16.8
[3] NIST DLMF 15.8.10, zero-balanced Gauss connection expansion:
https://dlmf.nist.gov/15.8
[4] NIST DLMF 5.4, digamma special values:
https://dlmf.nist.gov/5.4
[5] NIST DLMF 5.12.1, Euler beta integral:
https://dlmf.nist.gov/5.12
[6] NIST DLMF 5.15, polygamma recurrences, series and half-integer values:
https://dlmf.nist.gov/5.15

The project-specific combination (1)-(3), its positivity and tail bound,
and the full substitution (11) are derived here from the inherited primitive;
they are not attributed to the general DLMF references.
