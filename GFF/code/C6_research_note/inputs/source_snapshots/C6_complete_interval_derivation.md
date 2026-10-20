# A rational interval for the complete retained C6(1) representation

## Result, normalization, and scope

The input is the uploaded `C6_central_binomial_wheel_expression.json`, copied
without modification to `inputs/expression.json`. Define `C6_rep` to be the value
of its explicitly specified right hand side divided by 2187:

\[
\begin{aligned}
2187C_6^{\rm rep}(1)={}&E_{\rm central}+835584\Lambda+391680H_5\\
 &+13056\sqrt2(32G+3\pi^2)H_3-393\pi^3W_{\rm central}
 +96P_a-784\pi^{3/2}\mathscr L_7.
\end{aligned}
\]

The complete known polynomial and every inherited special-value definition are
in the unchanged input JSON. In particular, the `V` in that polynomial is the
ordinary 6F5 value specified below; it is NOT the local wheel notation
`sum (4n+1)*a_n^6` used in the preceding derivation.

The new computation encloses **this entire analytic representation**, including
finite arithmetic error, initial transcendental constants, and every infinite
series tail. It gives

\[
C_6^{\rm rep}(1)=
14331.6870327580543204454632552462171183173230619887904582031423\ldots
\]

with exact rational interval width less than `1.183e-145`. Its two rational
endpoints have a common prefix through 144 places after the decimal point.
The endpoint integers and denominator are in `results/complete_refined.json`.

**This is not an independent derivation or certification of the upstream
six-loop graph/RG identification.** The association of the saved representation
with the physical Ising coefficient, the supplied period identifications, and
the previously repaired source terms remain inherited analytic inputs. No
additional finite-special-value identity eliminating Wcentral, Pa, or L7 is
claimed. All three remain in the analytic formula. No numerical C6 reference
was used to choose a coefficient, a tail bound, or an interval endpoint.

The earlier wheel certificate explicitly covered the central series only.
This continuation adds the complete weighted arithmetic enclosure, an
independently derived recurrence-only bound for Pa, beta-measure error bounds
for the alternating logarithmic series, and finite rational telescopers for all
ten positive ordinary hypergeometric values needed in the assembly.

## 1. New a posteriori bound for the primitive recurrence

Use the two branches of the supplied recurrence, lambda=0 and lambda=1/2.
Each branch has nine components and logarithmic coefficients j=0,1,2. Write
`z_n` for all 27 coefficients together, with `z[n,3]=0`.
The input recurrence is

\[
\begin{aligned}
((n+\lambda)I-\mathbf A)z_{n,j}
={}&\mathbf C z_{n-1,j}+((n-1+\lambda)I+\mathbf A)z_{n-2,j}\\
&+(j+1)(z_{n-2,j+1}-z_{n,j+1}).
\end{aligned}
\]

The matrices and seed polynomials are unchanged. Direct exact computation gives

\[
\|\mathbf A\|_\infty=4,\qquad \|\mathbf C\|_\infty=10.
\]

Let D be the logarithmic shift `(Dz)_j=(j+1)z_(j+1)`, so its induced infinity
norm is 2. On the full coefficient vector the recurrence is

\[
((n+\lambda)I-\mathbf A+D)z_n
 =\mathbf C z_{n-1}+((n-1+\lambda)I+\mathbf A+D)z_{n-2}.
\]

The Neumann-series inverse bound, for n+lambda>6, therefore proves

\[
\|z_n\|_\infty\le
\frac{10\|z_{n-1}\|_\infty+(n+\lambda+5)\|z_{n-2}\|_\infty}
 {n+\lambda-6}.
\]

Set

\[
\rho=3-2\sqrt2,\qquad U_n=\rho^n\|z_n\|_\infty.
\]

Then

\[
U_n\le \frac{10\rho}{n+\lambda-6}U_{n-1}
 +\frac{\rho^2(n+\lambda+5)}{n+\lambda-6}U_{n-2}.
\tag{1}
\]

Since rho<1/5, the two coefficients are at most
`a_n=2/(n-6)` and `b_n=(n+5)/(25(n-6))`. For n>=48,

\[
\frac{a_n}{1/4}+\frac{b_n}{(1/4)^2}
=\frac{16n+280}{25(n-6)}\le1.
\]

For either branch, let

\[
K_\lambda=\max\{U_{N-1},\tfrac14 U_{N-2}\},\qquad N\ge48.
\]

Induction in (1) gives

\[
U_n\le K_\lambda(1/4)^{n-N+1}\quad(n\ge N-2),
\qquad \sum_{n=N}^\infty U_n\le K_\lambda/3.
\tag{2}
\]

The elementary weights in the input primitive series are

\[
J_j(s)=\rho^s\sum_{r=0}^j\binom jr\frac{(-1)^r r!\log^{j-r}\rho}{s^{r+1}}.
\]

For j<=2, s>=N and |log rho|<2,

\[
\sum_{j=0}^2|J_j(s)|/\rho^s
\le\frac7N+\frac5{N^2}+\frac2{N^3}<\frac8N\quad(N\ge48).
\]

The half-integer branch has only j=0,1, so the same bound also applies to it.
Using the input's factor 4 and powers rho^(n+1/2), rho^(n+1), (2) proves

\[
\boxed{
|P_a-P_{a,N}|\le\frac{32}{3N}
 \left(\sqrt\rho\,K_0+\rho K_{1/2}\right),\qquad N\ge48.
}
\tag{3}
\]

This is a finite-state, a posteriori bound. It uses the actual last two computed
states with outward-rounded upper norms. It does not invoke the input bound
`2**29*(10*rho/9)**N`, an infinite asymptotic expansion, or a numerical Pa
reference. `primitive.py` evaluates all finite terms by rational intervals.

The twelve seed equations (two branches, two initial n values, three logarithmic
channels) are checked as exact polynomial identities. The matrices are upper
triangular in the solve, so no numerical matrix inversion is used.

At N=280 the resulting full Pa interval, including arithmetic, has width
less than `4.818e-204` and begins

\[
P_a=334926.045248051837883222001240077786613085905253136679683127\ldots.
\]

## 2. New Euler error bounds for Z(t) and the logarithmic series

For the five input shifts

\[
t\in\{1/8,1/4,3/8,5/8,7/8\},\quad a=t+1/4,\quad b=t+3/4,
\quad g_0=\Gamma(a)/\Gamma(b),
\]

define

\[
Z(t)=\sum_{n\ge0}(-1)^n(n+t)
 \left[\frac{\Gamma(n+a)}{\Gamma(n+b)}\right]^7,
\]

\[
L(t)=\sum_{n\ge0}(-1)^n(n+t)
 \left[\frac{\Gamma(n+a)}{\Gamma(n+b)}\right]^7 H_{2n}(2a).
\]

The retained L7 is exactly the input weighted combination of these L(t).
The ordinary Z terms and PZ5 use the same five Z(t), with the supplied weights.

For a sequence f_n, write the finite Euler approximant as

\[
\mathcal E_N[f]=\sum_{n=0}^{N-1}(-1)^n w_{N,n}f_n,
\qquad
w_{N,n}=1-2^{-N}\sum_{k=0}^n\binom Nk.
\tag{4}
\]

The equivalent expression
`w_(N,n)=sum_(k=n)^(N-1) binomial(k,n)/2^(k+1)` follows from finite binomial
summation and is checked exactly. Formula (4) avoids constructing a potentially
ill-conditioned forward-difference table.

### 2.1 Ordinary moment remainder

Euler's beta integral [2] expresses the normalized coefficient

\[
\left[\frac{(a)_n}{(b)_n}\right]^7
\]

as E[S^n], where S is the product of seven independent Beta(a,1/2) variables.
For a fixed 0<=s<=1, the infinite alternating generating function of
f_n=(n+t)s^n is

\[
\frac{t}{1+s}-\frac{s}{(1+s)^2}.
\]

Its finite Euler remainder is, with u=(1-s)/2,

\[
r_N(s)=\frac{t u^N}{1+s}-\frac{s u^N}{(1+s)^2}
 -\frac{Ns(1-s)^{N-1}}{2^N(1+s)}.
\tag{5}
\]

For N>=1, `Ns(1-s)^(N-1)<=1`, including the endpoints. Hence

\[
|r_N(s)|\le(t+2)2^{-N}.
\]

Integrating against the positive beta measure proves

\[
\boxed{|Z(t)-Z_N(t)|\le (t+2)g_0^7 2^{-N}.}
\tag{6}
\]

### 2.2 Harmonic insertion and total variation

Deform each beta density to Beta(a+x,1/2-2x). Its normalized n-th moment is
`(a+x)_n/(b-x)_n`. For seven copies,

\[
\left.\frac{d}{dx}\left[\frac{(a+x)_n}{(b-x)_n}\right]^7\right|_{x=0}
=14\left[\frac{(a)_n}{(b)_n}\right]^7 H_{2n}(2a).
\tag{7}
\]

Here the duplication of the finite harmonic sum gives
`H_(2n)(2a)=[H_n(a)+H_n(b)]/2`.
The one-density logarithmic derivative is

\[
\ell(s)-\mathbb E\ell(s),\qquad \ell(s)=\log s-2\log(1-s).
\]

Its mean absolute value is at most `2 E|ell|`. The seven independent copies,
combined with the factor 1/14 in (7), thus give a signed measure whose total
variation is at most

\[
\mathbb E|\ell(s)|\le\psi(b)-\psi(a)
 +2[\psi(b)-\psi(1/2)].
\]

The polygamma series [3] and an elementary integral comparison give
`psi_1(a)<=a^(-2)+a^(-1)`. Since a>=3/8 and b<=13/8,

\[
\psi(b)-\psi(a)\le44/9,
\quad
2[\psi(b)-\psi(1/2)]\le45/4,
\quad 44/9+45/4<17.
\]

We used `psi_1(1/2)=pi^2/2<5`. Integrating (5) against this signed measure
therefore proves the uniform bound

\[
\boxed{|L(t)-L_N(t)|\le17(t+2)g_0^7 2^{-N}.}
\tag{8}
\]

The beta parameters remain positive near x=0; logarithmic beta moments are
integrable, which justifies differentiation and the finite Euler operation.
The defining sums also converge absolutely. No undeclared derivative remains
in the evaluator: (7) is only a proof of its error bound.

Applying the retained five weights, with interval gamma values and elementary
constants, encloses the complete L7. The refined calculation begins

\[
\mathscr L_7=107.402769187925909163168077248379900587691250831494\ldots.
\]

## 3. Finite rational telescopers for the ordinary positive series

The ten positive unit-argument series have rational term ratios

\[
R(n)=t_{n+1}/t_n=\prod_i(n+a_i)/\prod_i(n+b_i),\qquad t_0=1,
\]

with all shifts positive, equal numerator/denominator degrees, and
`alpha=sum b_i-sum a_i>1`. Their gamma-product asymptotics imply
`t_n=O(n^(-alpha))` [1,4].

For a finite M>=1 choose

\[
q_M(n)=\sum_{j=0}^M c_j n^{1-j}
\]

so that

\[
q_M(n)-R(n)q_M(n+1)=1+O(n^{-M-1}).
\]

This is a finite triangular rational calculation: the leading multiplier for
c_j is `alpha+j-1`, which is positive. To turn it into a bound, put y=1/n and

\[
A(y)=\prod_i(1+a_i y),\quad B(y)=\prod_i(1+b_i y),\quad
C(y)=\sum_{j=0}^M c_j y^j.
\]

The exact polynomial

\[
\begin{aligned}
E(y)={}&y(1+y)^{M-1}B(y)-(1+y)^{M-1}B(y)C(y)\\
 &+A(y)\sum_{j=0}^M c_j y^j(1+y)^{M-j}
\end{aligned}
\tag{9}
\]

is checked to have zero coefficients through degree M+1. The exact rational
residual is

\[
r(n)=1-q_M(n)+R(n)q_M(n+1)
=\frac{E(y)}{y(1+y)^{M-1}B(y)}.
\]

Since the denominator factors other than y are >=1 for y>=0, for n>=N,

\[
|r(n)|\le\varepsilon_{N,M}:=
 \sum_{k\ge M+2}|[y^k]E(y)|N^{1-k}.
\tag{10}
\]

This is a finite rational number, not an omitted asymptotic term.
The identity `t_n R(n)=t_(n+1)` telescopes, and `t_n q_M(n)->0` because
alpha>1. For T_N=sum_(n>=N)t_n,

\[
|T_N-t_Nq_M(N)|\le\varepsilon_{N,M}T_N.
\]

Whenever epsilon<1 and q_M(N)>0 (both checked exactly),

\[
\boxed{
\frac{t_Nq_M(N)}{1+\varepsilon_{N,M}}
\le T_N\le
\frac{t_Nq_M(N)}{1-\varepsilon_{N,M}}.
}
\tag{11}
\]

Adding the finite rational partial sum gives an exact rational interval for
each ordinary series. `rational_tails.py` constructs (9), checks its vanishing
coefficients, and additionally checks the rational identity at three exact
arguments per series. No infinite-order limiting assumption is involved.

### 3.1 Parameter ratios used

The following lists include the factorial denominator where applicable. A
superscript xk denotes k repetitions. The Y series are normalized by their
n=0 term, which is restored afterward.

| Series | Numerator shifts a_i | Denominator shifts b_i | alpha |
|---|---|---|---:|
| Bminus hypergeometric factor | 1/4,1/4,1/2,1/2 | 3/4,3/4,1,1 | 2 |
| Bplus hypergeometric factor | 3/4,3/4,1/2,1/2 | 5/4,5/4,1,1 | 2 |
| U | 1/4,(1/2)x4 | 5/4,1x4 | 3 |
| V (ordinary) | 1,1,(5/4)x4 | 2,(7/4)x4,1 | 3 |
| Hminus | (1/4)x6 | (3/4)x6 | 3 |
| H0 | (1/2)x6 | 1x6 | 3 |
| Hplus | (3/4)x6 | (5/4)x6 | 3 |
| Y_r normalized, r=1,2,7 | t+1,(t+1/4)x8 | t,(t+3/4)x8 | 3 |

Here t=r/8. The gamma prefactors and linear combinations constructing
Bminus, Bplus, Poct, Ell, PB6, PK6, PZ6, and PZ5 are the unchanged input
formulas. Each is evaluated with outward-rounded interval operations.

## 4. Elementary constants, geometric series, and the wheel

All certificate arithmetic is implemented in `dyadic.py`. Each endpoint is an
integer divided by 2^P. Integer floors/ceilings enclose every multiplication and
division; square roots use integer square roots. Addition and subtraction of
endpoint integers are exact. There are no binary floating-point special-value
calls in the construction.

Pi is enclosed by Machin's arctangent identity with alternating rational tails.
Logarithms use range reduction and a finite atanh series with a geometric tail;
exponentials use range reduction and a factorial Taylor remainder.

For positive gamma arguments, shift the argument to X=a+K, apply the finite
log-gamma Stirling expansion, and subtract the logarithm of the exact product
`a(a+1)...(a+K-1)`. The real-positive remainder has the sign of, and magnitude
at most, its first omitted Bernoulli term [1]. Exponentiating the resulting
interval encloses gamma. This uses a finite remainder theorem, not assumed
convergence of Stirling's infinite formal series.

Catalan and zeta(3), zeta(5) are enclosed by Euler-transformed alternating
Hausdorff-moment sums with nonnegative tails <=2^(-N); the zeta values include
the exact Dirichlet-eta prefactor. Zeta(2)=pi^2/6. The trigonometric eighth-angle
constants are algebraic expressions in sqrt(2).

The input H3 and H5 half-argument series are positive, with tails bounded by
twice their first omitted term.

For Lambda, the original strict double-polylogarithm definition reduces by
n=m+r and `((1+i)/2)*(1-i)=1` to

\[
\Lambda=\Re\sum_{r\ge1}z^r C_r,\quad z=(1+i)/2,
\]

\[
C_r=\frac{\zeta(3)-H_r^{(3)}}{r^2}
+\frac{3\zeta(2)-2H_r^{(2)}}{r^3}-\frac{3H_r}{r^4}
=\sum_{m\ge1}\frac1{m^2(m+r)^3}.
\]

The partial fraction identity is checked exactly. Since
`C_r<=zeta(2)/(r+1)^3`, `|z|<3/4`, and `zeta(2)/(1-|z|)<8`, the tail is less
than `8*(3/4)^(N+1)/(N+2)^3`. The real and imaginary powers of z are generated
using rational interval recurrences.

The central wheel is recomputed from the preceding exact rational fourth- and
sixth-power correction code, at N=256, M4=40, M6=41, using the new pi interval.
The wheel construction and its finite Taylor remainder proof are retained in
`inputs/wheel_derivation.md` and `wheel/`. The old wheel endpoints are read only
for an overlap check; they are not used to construct the new interval.

## 5. Complete assembly and numerical results

Each run evaluates the complete known polynomial and all six additional
weighted contributions before division by 2187. The source repair remains
included exactly as in the input polynomial; it is not added again.

| Configuration | Arithmetic bits | Ordinary N/M | Primitive N | Full interval width |
|---|---:|---:|---:|---:|
| smoke | 640 | 128/40 | 140 | <4.673e-67 |
| release | 1024 | 256/80 | 240 | <1.986e-136 |
| refined | 1280 | 320/96 | 280 | <1.183e-145 |

The three full intervals are nested, checked using their exact rational
endpoints. All runs use the same central-wheel cutoff; its finite tail bound
therefore dominates the last run.

For orientation, the weighted contributions in C6 units are:

| Contribution | Numerical value, displayed approximately |
|---|---:|
| Ecentral/2187 | -860.425586056980310935696 |
| 835584 Lambda/2187 | 23.2838245873048504052053 |
| 391680 H5/2187 | 182.103647807601104103872 |
| 13056 sqrt(2)(32G+3pi^2) H3/2187 | 502.487032751269016440720 |
| -393 pi^3 Wcentral/2187 | -3.19953062632696237570703 |
| 96 Pa/2187 | 14701.8291466908900031044 |
| -784 pi^(3/2) L7/2187 | -214.391502395703380297326 |

The refined weighted interval widths are bounded above by:

| Sector | Width upper bound |
|---|---:|
| Wheel | 1.1826e-145 |
| Known polynomial | 6.1870e-166 |
| Primitive | 2.1146e-205 |
| Lambda | 2.7549e-244 |
| H3 | 3.7886e-280 |
| H5 | 7.1367e-284 |
| Logarithmic | 4.9568e-323 |

These are outward-rounded upper bounds, not reported residuals between two
floating-point approximations. The exact dyadic widths remain in the JSON.

### 5.1 Independent and finite checks

`validate.py` checks integer interval operations against exact rational
endpoint calculations, finite Euler-weight identities, finite Euler generating
remainders, the recurrence majorant, the harmonic-density bound, the Lambda
partial fractions, unchanged source-correction metadata, and exact nesting.
The primitive seeds and wheel finite identities are separately checked by the
certificate constructor. Test counts are implementation checks, not numbers
of independent mathematical results.

As supplementary checks only, 450-digit mpmath values for elementary/gamma
constants lie in the independently constructed intervals. In a separate
80-digit quadrature, the original folded Gauss-kernel integral for Pa differs
from the certified recurrence interval midpoint by approximately 6.02e-73.
The quadrature integrand contains none of the new recurrence-tail construction.
Its endpoint acceleration and working precision are floating-point numerical
choices, not a second interval proof.

The complete C6 decimal agrees with the previously saved numerical assembly.
That agreement is not used to determine any bound. In particular, the earlier
comparison with a separate all-sector estimator and its empirical allowance
must not be reinterpreted as a newly proved physical accuracy statement.

## 6. Reproduction and remaining analytic task

Python 3, SymPy, and mpmath are sufficient; mpmath is only needed for the
supplementary validation/quadrature checks. The interval constructors use no
network or binary floating-point arithmetic in their bounds.

```text
python certify_complete.py smoke
python certify_complete.py release
python certify_complete.py refined
python validate.py
python check_numerical.py 80
```

The retained expression itself is unchanged. This continuation closes its
numerical error budget, rather than reducing its finite special-value basis.
The finite-evaluation targets remain

\[
W_{\rm central},\qquad P_a,\qquad\mathscr L_7.
\]

An identity eliminating one of them must be proved separately. Likewise,
independent verification of the upstream graph/RG assembly is a distinct task
from certifying the explicit right hand side evaluated here.

## References and inherited material

[1] NIST DLMF, Section 5.11, especially the positive-real remainder statement
in Section 5.11(ii) and gamma-ratio asymptotics in Section 5.11(iii).
https://dlmf.nist.gov/5.11

[2] NIST DLMF, Section 5.12, Euler beta integral.
https://dlmf.nist.gov/5.12

[3] NIST DLMF, Section 5.15, polygamma series and half-integer values.
https://dlmf.nist.gov/5.15

[4] NIST DLMF, Section 16.2, generalized hypergeometric definitions and
convergence at unit argument.
https://dlmf.nist.gov/16.2

[5] Uploaded `C6_central_binomial_wheel_expression.json`: the complete corrected
analytic expression, ordinary period definitions, primitive recurrence and
seeds, logarithmic-series weights, and source repair. Copied without changes.

[6] Uploaded central-wheel verification package and derivation: finite rational
fourth/sixth-power corrections and their global finite remainder estimates.
The two code files used by the new constructor are copied under `wheel/`.

The new bounds (3), (6), (8), and (11), their application to the complete saved
assembly, and the full interval implementation are derived in this continuation.
No claim of priority over the general numerical-analysis literature is made.
