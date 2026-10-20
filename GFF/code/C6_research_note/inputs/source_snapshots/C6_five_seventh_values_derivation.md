# C6(1): a zero-boundary telescope gives a 12-value alternative

## Result and qualification

The accepted input is C6_single_wheel_H_expression.json (17 fixed function
values). This continuation produces an OPTIONAL 12-value representation by
replacing the five ordinary seventh-sector values and their five logarithmic
Kampé de Fériet companions by five higher-order Kampé de Fériet values.
All three univariate G values, both bivariate H values, the two polylogarithms,
the known polynomial and the source correction remain unchanged.

This is not an elementary evaluation or a proof of arithmetic dependence. It
adds considerable parameter complexity: sixteen roots of an explicit polynomial
per shift, with new local orders 26/25 instead of 4/3. The simpler-parameter
17-value input is retained. No numerical value of C6 or of a period is used to
choose a parameter. No new function class or third variable is introduced.

The original graph/RG normalization and sector identifications are inherited.
The new step is proved below rather than attributed to a general reference.

## 1. The precise inherited block

For r in {1,2,3,5,7}, let t=r/8, a=t+1/4, b=t+3/4, c=t+1/2. Let p_r and b_r be
the exact weights in the input. The full seventh contribution is
\[
B_7=96\pi^{3/2}\sum_r[b_r Z_r-98p_r\nu_r J_r],
\]
where
\[
Z_r=\sum_{n\ge0}u_n,\quad
\nu_r J_r=-\sum_{n\ge0}u_n H_n,
\]
\[
u_n=(-1)^n(n+t)\left[\frac{\Gamma(n+a)}{\Gamma(n+b)}\right]^7,
\qquad H_n=\frac12\sum_{j=0}^{n-1}\left(\frac1{j+a}+\frac1{j+b}\right).
\]
The letter H_n in THIS section is the old shifted harmonic insertion, not an
ordinary harmonic number and not the primitive Fox H function. Both sums are
proof devices. Put xi=b_r/(98p_r). Then a single old bracket is
\[
b_r Z_r-98p_r\nu_r J_r=98p_r\sum_{n\ge0}u_n(H_n+\xi).
\]

## 2. A telescope whose two boundary values are zero

Let
\[
R(n)=\frac{n}{n+t},\quad \kappa=t(b/a)^7,
\quad f(x)=\frac{\kappa}{x+t}\left[x+(x+1)\left(\frac{x+a}{x+b}\right)^7\right].
\]
Using Gamma(z+1)=z Gamma(z), the exact consecutive ratio is
\[
\frac{u_{n+1}}{u_n}=-\frac{n+t+1}{n+t}
\left(\frac{n+a}{n+b}\right)^7.
\]
Therefore the elementary rational identity
\[
\boxed{u_n f(n)=\kappa[u_nR(n)-u_{n+1}R(n+1)]}
\]
holds for every integer n>=0. In particular f(0)=1 but R(0)=0.

At infinity, the standard gamma-ratio asymptotic gives u_n=O(n^(-5/2)) and
R(n)=O(1), so u_n R(n) tends to zero. Both boundaries vanish, yielding
\[
\boxed{\sum_{n\ge0}u_n f(n)=0.}
\]
The series is absolutely convergent: f(n) tends to the finite constant 2 kappa.
This is NOT a subtraction of divergent sums.

Define
\[
h(x)=\frac{x+c}{(x+a)(x+b)},\qquad d(x)=h(x)-\xi[f(x+1)-f(x)].
\]
Because H_n=sum_(j<n) h(j) and f(0)=1,
\[
\widetilde H_n:=\sum_{j=0}^{n-1}d(j)=H_n-\xi[f(n)-1].
\]
It follows exactly that
\[
\boxed{\sum_{n\ge0}u_n(H_n+\xi)=\sum_{n\ge1}u_n\widetilde H_n.}
\]
The original ordinary n=0 term is accounted for through the telescope; it has
not been dropped. In finite form, with terms n<N, the old-minus-new difference is
\[
-\xi\kappa u_N\frac{N}{N+t}.
\]
This explicit boundary expression is checked by rational arithmetic for N=1,...,12
for each of the five rational parameter sets, with xi left symbolic.

## 3. Identify the resulting single standard bivariate value

Put
\[
D(x)=(x+a)(x+t)(x+t+1)(x+b)^7(x+b+1)^7,\quad P(x)=D(x)d(x).
\]
The rational denominators cancel: P is a monic polynomial of degree sixteen.
The leading coefficient follows also from d(x)=1/x+O(x^-2).
Let P(x)=product_(j=1..16)(x+beta_j), counting all roots and multiplicities.
There is no ordering ambiguity because the parameter lists are symmetric.

Elementary Pochhammer cancellation now gives
\[
\boxed{\frac{d(j)}{d(0)}=
\frac{(a)_j(t)_j(b)_j^7}{(a+1)_j(t+2)_j(b+2)_j^7}
\prod_{k=1}^{16}\frac{(1+\beta_k)_j}{(\beta_k)_j}.}
\]
Indeed, the product is P(j)/P(0), and the other factors are D(0)/D(j).
This identity identifies a standard hypergeometric LOCAL coefficient. It does
not define a new family of special functions.

Writing n=m+j+1 for the triangular sum, the SHARED coefficient is
\[
u_{m+j+1}=-(t+1)\left[\frac{\Gamma(a+1)}{\Gamma(b+1)}\right]^7
(-1)^{m+j}
\frac{(t+2)_{m+j}(a+1)_{m+j}^7}
{(t+1)_{m+j}(b+1)_{m+j}^7}.
\]
The x-local coefficient is (1)_m/m!=1; supplying (1)_j/j!=1 gives exactly
\[
\mathcal K_r=F_{8:0;25}^{8:1;26}\!\left[
\begin{matrix}t+2,(a+1)^{[7]}:1;1,a,t,b^{[7]},1+\boldsymbol\beta_r\\
t+1,(b+1)^{[7]}:-;a+1,t+2,(b+2)^{[7]},\boldsymbol\beta_r\end{matrix};-1,-1\right].
\]
Thus, with Omega_r=(t+1)[Gamma(a+1)/Gamma(b+1)]^7 d_r(0),
\[
\boxed{b_rZ_r-98p_r\nu_rJ_r=-98p_r\Omega_r\mathcal K_r,}
\]
\[
\boxed{B_7=-9408\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}p_r\Omega_r\mathcal K_r.}
\]
The final sum has five terms. The factor 9408 is 96 times 98. There is no
polynomial compensation.

## 4. Excluded denominator parameters and absolute convergence

The only possible problematic lower parameters are beta_j; all others are
positive rational numbers. The finite parameter certificate constructs rational
bounds for pi with Machin's formula and alternating arctangent remainders, for
log(2) with the positive atanh(1/3) expansion and geometric remainder, and for
sqrt(2) with integer square roots. Interval operations are exact Fractions.

Every coefficient of P is affine in xi. At r=1,2,3,5, exact interval evaluation
proves that all seventeen coefficients are positive. Hence P has no
nonnegative real root. For r=7, the leading coefficient is positive and all
sixteen remaining coefficients are negative. Descartes' rule gives exactly one
positive root, and the rational intervals prove P(205)<0 and P(206)>0. Hence
no root can be a nonnegative integer. In particular, no beta_j is a
nonpositive integer, and P(0),d(0) are nonzero. No regularization or limiting
parameter prescription is used.

For r=2, P has the explicit factors (x+1)(x+2), which permit three matching
upper/lower cancellations and local order 23/22 instead of 26/25. This does
not alter the uniform sixteen-root specification.

The shared diagonal coefficient is O(k^-5/2). The new local coefficient
satisfies d(j)=1/j+O(j^-2), and is bounded at every nonnegative integer. Thus
sum_(j<=k)|d(j)|=O(log(k+2)). The absolute k-th diagonal of the defining KdF
series is consequently O(log(k+2)/(k+1)^(5/2)), proving absolute convergence
at (-1,-1) and justifying the triangular reindexing. Root parameters can be
complex, or negative noninteger; they introduce no singular coefficient.

## 5. What is and is not simplified

The active 17-value formula loses five Z values and replaces its five J values
by five K values: total fixed calls decrease to twelve. The counts exclude
initial constants and finite gamma prefactors, consistently with the input.
The known polynomial remains the exact same eighteen-monomial string. The
wheel and primitive each remain one bivariate H value.

This is a large PARAMETER-COMPLEXITY tradeoff. New local y lists have 26 upper
and 25 lower entries instead of 4 and 3, and require degree-sixteen roots.
Fewer fixed calls is not a theorem of fewer independent periods, easier
numerical evaluation, or an elementary/gamma-zeta evaluation. Both versions
are preserved; FORMULA.md is the fully specified twelve-value alternative.

## 6. Checks actually run

build_and_verify.py passes 202 finite checks. These include repeated coefficient
checks; this number is not a count of independent mathematical theorems.
The checks cover the exact telescope, every parameter set, the full old-block
weighting and preservation of all unchanged fields.

numerical.py builds the NEW KdF diagonals directly from d(j)/d(0). It separately
builds the old J diagonals from h(j)/h(0) and evaluates the ordinary Z values
using mpmath.hyper. Euler-weighted finite approximants were compared at
(N,working digits)=(256,110),(400,155). The complete r6 discrepancy in the larger
run is 4.7289624e-116. The NEW tail bound is not certified in this package, so
these are floating-point implementation checks, NOT a new interval certificate.

check_roots.py independently solves the sixteen-root polynomials with 85-digit
root requests and checks the standard Pochhammer coefficient at
j=0,1,2,7,33,205,206,400. The maximum discrepancy is below 3.18e-87.
Root nonsingularity is established by the separate exact interval sign proof,
not by these floating-point root samples.

No Wolfram kernel or all-sector C6 run was performed. The original physical
six-loop graph/RG identification and the previous special-function identities
remain inherited inputs.

## Sources

1. Supplied C6_single_wheel_H_expression.json: complete input formula and
   five seventh-sector ordinary/logarithmic weights.
2. Supplied C6_standard_seventh_derivation.md: shifted harmonic series and its
   original KdF normalization. The new telescope is not present in that source.
3. R. Ito, S. Kumabe, A. Nakagawa, Y. Nemoto, arXiv:2212.14321v2,
   Introduction: classical complex-variable Kampé de Fériet definition.
   https://arxiv.org/html/2212.14321v2
4. NIST DLMF 5.5: Gamma recurrence; DLMF 5.11(iii): Gamma-ratio asymptotics.
   https://dlmf.nist.gov/5.5
   https://dlmf.nist.gov/5.11

The general references fix function conventions and asymptotics. They are not
being cited as published evaluations of this Ising coefficient.
