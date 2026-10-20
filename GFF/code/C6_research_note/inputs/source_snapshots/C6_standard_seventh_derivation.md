# C6(1): remove the custom seventh-power sum using standard Kampé de Fériet values

## Scope

The input is the supplied `C6_standard_even_expression.json`. Its normalization
is r6 = 2187 C6(1). The inherited standard even sector, standard polylogarithms,
primitive, graph/RG identifications, and source correction are not rederived.

The new result is a finite replacement of M7central by FIVE fixed classical
Kampé de Fériet values at (-1,-1) and FIVE ordinary generalized hypergeometric
values at -1. The paired reciprocal in the logarithmic insertion is combined
before identifying parameters; two bivariate values per shift are not needed.

The active custom list becomes just PaCubic. This is a conversion to established
bivariate functions, not an ordinary one-variable evaluation, a proof of fewer
independent periods, or a reduction in the total number of named special values.
The number of ordinary pFq values rises from eight to thirteen, and KdF values
from two to seven. No regulator derivative or limiting prescription remains.
The known polynomial is unchanged (21 expanded monomials).

## 1. The standard values and complete insertion

Let r belong to {1,2,3,5,7}, and write

\[
 t=r/8,\qquad a=t+1/4,\quad b=t+3/4,\quad c=t+1/2=(a+b)/2.
\]

A superscript [j] below means j repeated parameters. Define the standard value

\[
 \mathfrak J_r=F_{8:0;3}^{8:1;4}\left[
 \begin{matrix}
 t+2,(a+1)^{[7]}:1;1,c+1,a,b\\
 t+1,(b+1)^{[7]}:-;c,a+1,b+1
 \end{matrix};-1,-1\right].                                    \tag{1}
\]

The notation is the classical complex-variable Kampé de Fériet convention
stated in [1, Introduction]: shared parameters depend on m+n, x-local
parameters on m, and y-local parameters on n, with the factors 1/(m! n!).
It is not the finite-field analogue developed later in that paper.
For lists A,B,C and A',B',C', the convention is

\[
 F\!\left[\begin{matrix} A:B;C\\ A':B';C'\end{matrix};x,y\right]
 =\sum_{m,n\ge0}\frac{(A)_{m+n}(B)_m(C)_n}
 {(A')_{m+n}(B')_m(C')_n}\frac{x^m y^n}{m!n!}.                  \tag{2}
\]

All parameter lists in (1) are fixed by r. Every denominator parameter is positive.
The full parameter values t,a,b,c are

| r | t | a | b | c |
|---|---|---|---|---|
| 1 | 1/8 | 3/8 | 7/8 | 5/8 |
| 2 | 1/4 | 1/2 | 1 | 3/4 |
| 3 | 3/8 | 5/8 | 9/8 | 7/8 |
| 5 | 5/8 | 7/8 | 11/8 | 9/8 |
| 7 | 7/8 | 9/8 | 13/8 | 11/8 |

The accompanying ordinary value and normalization are

\[
 \mathcal Z_r=t\left[\frac{\Gamma(a)}{\Gamma(b)}\right]^7
 {}_9F_8\!\left(\begin{matrix}1,1+t,a^{[7]}\\t,b^{[7]}\end{matrix};-1\right),
                                                                  \tag{3}
\]
\[
 \nu_r=\frac{(t+1)c}{ab}
       \left[\frac{\Gamma(a+1)}{\Gamma(b+1)}\right]^7.             \tag{4}
\]
At r=2, an upper/lower 1 cancels in (3), yielding an 8F7. The JSON performs
this cancellation. These Z values are seventh powers at -1, NOT the
positive-argument eighth-power Y values in the even sector.

Put ell=log(2), A=pi+4ell, c7=cos(pi/8)^7, s7=sin(pi/8)^7,
and Rplus=13+22sqrt(2), Rminus=22sqrt(2)-13. The weights are

| r | p_r | b_r |
|---|---|---|
|1|c7 Rplus|c7[(2303+1127sqrt(2))pi-55 A Rplus]|
|2|-35|(3283pi-1295A)/2|
|3|c7 Rminus|c7[(392-55A)Rminus+(1127sqrt(2)-2303)pi]|
|5|-s7 Rminus|s7[(55A-392/3)Rminus+(2303-1127sqrt(2))pi]|
|7|s7 Rplus|s7[(2352/5-55A)Rplus+(2303+1127sqrt(2))pi]|

The exact replacement is

\[
 \boxed{24\pi^3\mathscr M_7=
 96\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}
 [b_r\mathcal Z_r-98p_r\nu_r\mathfrak J_r].}                    \tag{5}
\]

The sum over r has exactly FIVE terms. It is finite substitution notation,
not the definition of a further infinite series.

If E is the complete input `known_polynomial` and E_even is the complete input
`standard_even_values`, then the full new coefficient is

\[
\boxed{\begin{aligned}
2187C_6(1)={}&E+208896\Re\mathcal L_{01110}(i)
+13056(32G-3\pi^2)\Im\operatorname{Li}_3((1+i)/2)\\
&+E_{\rm even}+96\pi^{3/2}
 \sum_{r\in\{1,2,3,5,7\}}[b_r\mathcal Z_r-98p_r\nu_r\mathfrak J_r]
 +192\pi^2\mathscr P_c^{(3)}.
\end{aligned}}                                                  \tag{6}
\]

The exact polynomial E, the ten old standard even-sector values, and the full
primitive definition are preserved in the output JSON. In particular,
P_a=2 pi^2 PaCubic and Delta E=0. The previous -144Q^3/pi term stays present.
The saved source repair stays present exactly once.

## 2. Coefficient proof of the new bivariate conversion

For the proof only, consider the old logarithmic stream

\[
 L(t)=\sum_{n\ge0}(-1)^n(n+t)
 \left[\frac{\Gamma(n+a)}{\Gamma(n+b)}\right]^7 H_{2n}(2a),
 \quad H_N(x)=\sum_{j=0}^{N-1}\frac1{x+j}.
\]

Separate the even and odd finite indices:

\[
 H_{2n}(2a)=\frac12\sum_{j=0}^{n-1}
             \left[\frac1{j+a}+\frac1{j+b}\right].              \tag{7}
\]

Because c=(a+b)/2, both terms combine into ONE hypergeometric coefficient:

\[
 \frac12\left[\frac1{j+a}+\frac1{j+b}\right]
 =\frac{j+c}{(j+a)(j+b)}
 =\frac{c}{ab}\frac{(c+1)_j(a)_j(b)_j}
 {(c)_j(a+1)_j(b+1)_j}.                                       \tag{8}
\]

Now n>=1 and 0<=j<n are equivalent to n=m+j+1 with m,j>=0. With k=m+j,

\[
 n+t=(t+1)\frac{(t+2)_k}{(t+1)_k},
 \quad
 \frac{\Gamma(n+a)}{\Gamma(n+b)}
 =\frac{\Gamma(a+1)}{\Gamma(b+1)}\frac{(a+1)_k}{(b+1)_k},
\]

and (-1)^n=-(-1)^{m+j}. Insert (8) and supply (1)_m/m!=(1)_j/j!=1.
The resulting parameter table is exactly (1), and hence

\[
 \boxed{L(t)=-\nu_r\mathfrak J_r.}                             \tag{9}
\]

The minus sign is forced by the index shift n=m+j+1. At n=0 the original
harmonic factor is zero. There is no missing constant and no compensation to E.
Equations (7)-(9) are derived here. They are not identities quoted from [1].

## 3. Match the complete old sector, including ordinary corrections

The inherited central-seventh derivation supplies

\[
 24\pi^3\mathscr M_7=-36AP_5-392\pi^{3/2}C_Z-784\pi^{3/2}\mathscr L_7.
                                                                  \tag{10}
\]

The original fixed definitions give

\[
 P_5=16\pi^{3/2}\sum_r p_r\mathcal Z_r,\quad
 C_Z=\sum_r q_r\mathcal Z_r,\quad
 \mathscr L_7=\sum_r w_rL(r/8).
\]

Their literal coefficient tables satisfy w_r=-12p_r, and the table in Section 1
satisfies

\[
 b_r=-6Ap_r-\frac{49}{12}q_r,\qquad ell=(A-\pi)/4.              \tag{11}
\]

Both identities are checked for all five shifts using the original JSON fields.
Substituting (9) into (10) produces

\[
 \pi^{3/2}\sum_r[(-576Ap_r-392q_r)\mathcal Z_r
                         -9408p_r\nu_r\mathfrak J_r],
\]

which is (5). In particular, the entire C_Z correction is included; dropping it
would give incorrect b weights. The central-to-five-shift identity (10) is an
inherited analytic input; the present pass does not independently reprove its
periodization or the physical graph identification.

## 4. Absolute convergence and ordinary triangular sums

The gamma-ratio asymptotic [2] gives the shared coefficient in (1) as O(k^-5/2).
The local j coefficient is a positive rational function O(1/(j+1)). Thus the
absolute sum on the diagonal m+j=k is O(log(k+2)/(k+1)^(5/2)). Summing the
diagonals proves absolute convergence on |x|=|y|=1, including (-1,-1).
All changes of summation order above are therefore justified.
The ordinary 9F8 in (3) has excess 3/2, so it is absolutely convergent at -1 [3].

Here is also a direct uniform bound. Let

\[
 D_k=\frac{(t+2)_k(a+1)_k^7}{(t+1)_k(b+1)_k^7}
       \sum_{j=0}^k\frac{(c+1)_j(a)_j(b)_j}{(c)_j(a+1)_j(b+1)_j}.
\]

These are the positive diagonal coefficients of the STANDARD function (1),
used for proof and evaluation, not a new active special-value definition.
The elementary inequality x(x+1)<(x+1/2)^2 implies

\[
 \left[\frac{(a+1)_k}{(b+1)_k}\right]^2
 \le\frac{a+1}{a+k+1}.
\]

Using (8), for k>=1 and the five listed shifts,

\[
 D_k<32(5+\log k)k^{-5/2}.
\]

One uniform coefficient constant is justified by
(a+1)^(7/2) ab/[c(t+1)] < (17/8)^4(7/5)<32;
1/a+log(1+k/a)<5+log k. Consequently, for N>=2,

\[
 \left|\mathfrak J_r-\sum_{k=0}^{N-1}(-1)^kD_k\right|
 <\frac{64}{3(N-1)^{3/2}}\left[\frac{17}{3}+\log(N-1)\right].     \tag{12}
\]

A sharper alternating enclosure is available. The local j coefficients are
positive and decreasing. Therefore their partial sums U_k satisfy
U_(k+1)/U_k <= (k+2)/(k+1). It follows that

\[
 \frac{D_{k+1}}{D_k}\le
 \frac{k+t+2}{k+t+1}\left(\frac{k+a+1}{k+b+1}\right)^7
 \frac{k+2}{k+1}<1.
\]

For each of the five rational t values, the last strict inequality is proved by
the polynomial

\[
 (k+t+1)(k+b+1)^7(k+1)-(k+t+2)(k+a+1)^7(k+2).
\]

All its coefficients are positive. The exact rational coefficient lists are
exported to `results/monotonicity_certificate.json`. Thus the diagonal
alternating remainder has the sign of (-1)^N and magnitude less than D_N.
These bounds apply to the triangular set m+j<N, not arbitrary rectangles.

## 5. Independent rational Euler certificates

No gamma value is needed to certify the normalized standard functions. Let
Zhat_r be the pFq in (3) without its external prefactor. Define the finite Euler
weights

\[
 w_{N,k}=1-2^{-N}\sum_{j=0}^k\binom Nj.
\]

The exact-rational approximants use these weights on the ordinary coefficients
of Zhat and the diagonal coefficients D_k of J. We prove the uniform errors

\[
 |\widehat{\mathcal Z}_r-Z_{r,N}^{E}|<17\,2^{-N},\qquad
 |\mathfrak J_r-J_{r,N}^{E}|<100\,2^{-N}.                        \tag{13}
\]

These estimates apply to Euler-weighted approximants, not plain partial sums.

### Proof of (13)

Euler beta integration [4] represents [(p)_k/(p+1/2)_k]^7 as the k-th moment of
the product of seven independent Beta(p,1/2) variables. Write its probability
measure as mu_p. For a measure mu on [0,1], the exact Euler remainder kernel is

\[
 R_N(x)=2^{-N}(1-x)^N/(1+x).
\]

A coefficient (s+k)/s corresponds to applying (s+x d/dx)/s to that kernel.
For s>0 and N>=1,

\[
 |(s+x\partial_x)R_N(x)|\le(s+2)2^{-N},\quad 0\le x\le1,
\]

because Nx(1-x)^(N-1)<=1. For Zhat take p=a and s=t>=1/8. The probability
measure has mass one, so (1+2/t)<=17 proves the first bound.

For J take p=a+1 and s=t+1. Its diagonal coefficient can be written

\[
 D_k=\frac{s+k}{s}\left[\frac{(p)_k}{(p+1/2)_k}\right]^7
       \left[1+\frac{ab}{c}H_{2k}(2p)\right].                  \tag{14}
\]

To control the last harmonic insertion, deform each beta distribution to
Beta(p+epsilon,1/2-2epsilon). The derivative of the seventh-power moment is
14 times the harmonic part of (14). Divide the derivative pushforward measure
by 14, calling it nu_p. Direct bounding of its centered logarithmic score gives

\[
 \|\nu_p\|_{TV}\le B(p):=
 \psi(p+1/2)-\psi(p)+2[\psi(p+1/2)-\psi(1/2)].
\]

For clarity, if W=log Y-2log(1-Y), the score of the seven-variable probability
density is sum(W_j-E W_j). Its L1 norm is at most 14 E|W|, and
E|W| <= -Elog Y-2Elog(1-Y)=B(p). Passing to the product pushforward cannot
increase total variation.

Here 11/8<=p<=17/8. The positive decreasing trigamma series [5] gives
psi1(p)<=psi1(1)=zeta(2)<2 and psi1(1/2)=pi^2/2<5. Hence

\[
 B(p)<1+2(17/8)5=89/4<23.
\]

Also ab/c=c-1/(16c)<3/2. Thus the signed measure
sigma=mu_p+(ab/c)nu_p has total variation less than 36. Since s>=9/8,

\[
 \|\sigma\|_{TV}(1+2/s)<36\cdot25/9=100,
\]

proving the second bound. Derivatives occur only in this proof, not in the
standard functions, their parameter tables, or the rational evaluator.

### Construction and results

`certify_values.py` builds shared and local Pochhammer ratios using rational
arithmetic, sums the local coefficients, forms the exact finite Euler sums,
adds (13), and rounds OUTWARD to rational dyadics at N+40 bits.
The intervals for each of the ten normalized functions are nested:

| N | width for each J_r | width for each Zhat_r |
|---|---|---|
|128|<5.878e-37|<9.992e-38|
|256|<1.728e-75|<2.937e-76|
|512|<1.492e-152|<2.536e-153|

The exact endpoints are in `results/rational_intervals.json`. Separate exact
triangular intervals at m+j<64 contain the fine Euler intervals for all five J.
Gamma prefactors, the weighted seventh sector, and the complete C6 are NOT
interval-certified anew by these files.

## 6. Numerical comparison and preservation checks

The five J values begin

| r | J_r |
|---|---|
|1|0.79699344353070403995321866948809880758574634666700...|
|2|0.76873705333359582978891425180141207932328302472645...|
|3|0.74226917994763237881134882753647373812994197887813...|
|5|0.69445661274951954190667149108281612700638321415860...|
|7|0.65295127466760489517105251173270886821121283003950...|

At 220-digit working precision, a FRESH N=800 Euler evaluation of the central
cubic-binomial M7 definition gives

M7 = -15332.5541947745752769789465340930315749885217640430336681175677525366...

The new standard-function expression is evaluated from the rational certificates
and fresh gamma/pi/log values, not from that central result. Comparisons are:

| Euler cutoff for new values | absolute difference in M7 | change in C6 units |
|---|---|---|
|128|2.99882956618e-35|1.02038451847e-35|
|256|7.82926854831e-74|2.66399414884e-74|
|512|5.88195541395e-151|2.00139958284e-151|

The new central evaluation differs from the midpoint of the inherited central
interval by about 3.626e-217. This is a FLOATING-POINT comparison, not an
additional proof of that interval or the physical identification. The full-C6
number in the report uses the inherited other sectors and agrees through the
shown 75 digits. The polynomial and all unchanged JSON blocks are tested for
exact equality, including the complete source-correction object.

`verify.py` passes 191 finite exact checks. They include the five entire weighted
substitutions, the generic paired-reciprocal identity, fixed-index coefficient
checks, monotonicity polynomials, ordinary-series identification, exact Euler
kernel identities, and preservation of the whole unchanged expression blocks.
They supplement, not replace, the all-index proof and convergence arguments.

## 7. Reproduction

Python 3, SymPy, and mpmath are required. No network access is used by the code.

```
python formula.py
python verify.py
python certify_values.py 128 256 512
python check_numerical.py
```

The earlier one-index M7 evaluator remains useful; the new standard double
function is not claimed to be faster under literal summation. The remaining
custom target is the two-index positive cubic primitive PaCubic. No identity
eliminating that primitive or evaluating the new KdF functions in ordinary
one-variable constants has been established in this continuation.

## References and inherited inputs

[1] R. Ito, S. Kumabe, A. Nakagawa, Y. Nemoto, *Kampé de Fériet hypergeometric
functions over finite fields*, arXiv:2212.14321v2, Introduction, first displayed
formula defining the CLASSICAL complex-variable family.
https://arxiv.org/html/2212.14321

[2] NIST DLMF 5.11(iii), gamma-ratio asymptotics.
https://dlmf.nist.gov/5.11

[3] NIST DLMF 16.2, ordinary generalized-hypergeometric series and convergence.
https://dlmf.nist.gov/16.2

[4] NIST DLMF 5.12, Euler beta integral.
https://dlmf.nist.gov/5.12

[5] NIST DLMF 5.15, positive-real trigamma series and integer/half-integer values.
https://dlmf.nist.gov/5.15

Inherited: current standard-even expression; central-seventh derivation equation
(1); original wheel expression fields L7.weights, ordinary_constant_coefficients,
and the retained P5 identification. The manuscript derives no new graph/RG input.
