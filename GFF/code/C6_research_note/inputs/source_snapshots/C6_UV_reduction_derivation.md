# Two ordinary special values eliminated from the retained C6(1) formula

## Result and scope

Let `inputs/expression.json` be the supplied central-binomial representation, in
`r6 = 2187 C6(1)` units. Retain

\[
\ell=\log 2,\qquad A=\pi+4\ell,\qquad Q=\frac{\Gamma(1/4)^4}{\pi}.
\]

The two ordinary hypergeometric values in its known polynomial satisfy

\[
\boxed{U={}_5F_4\!\left(\begin{matrix}1/4,(1/2)^4\\5/4,1^3\end{matrix};1\right)
       =\frac{Q^2}{96\pi^3}},
\tag{1}
\]
\[
\boxed{V={}_6F_5\!\left(\begin{matrix}1,1,(5/4)^4\\2,(7/4)^4\end{matrix};1\right)
       =54\pi-243\ell.}
\tag{2}
\]

Here repeated parameters are denoted by powers in the parameter lists. In
particular, **V in (2) is not the shorthand `sum (4n+1) a_n^6` used in the
previous wheel proof**. That separate wheel quantity is not evaluated here.

Identity (1) is a known summation, credited to Campbell and also proved in
Zhou [1]. Below, (2) is proved by a nonterminating summation-by-parts identity,
Dixon's summation, and a second representation of the same Legendre integral
used for (1). No claim that either special-value identity is new to the
literature is needed for this application.

The complete affected block collapses to

\[
\boxed{
Q^2\left(\frac{285}{2}A+\frac{58}{9}V-\frac{1247}{2}\pi\right)
-8352\pi^4U=Q^2(29\pi-249A).
}
\tag{3}
\]

Thus two ordinary special values disappear. The three residual quantities
`Wcentral`, `Pa`, and `L7` are unchanged; no new residual replaces U or V.
The physical graph/RG identification and source correction remain inherited
inputs. This is an analytic reduction of the saved expression, not a new
independent derivation of the six-loop graph sum.

## 1. The U evaluation and a companion 4F3

Set

\[
a_n=\frac{(1/2)_n}{n!},\qquad
T_{\mu,\nu}=\int_{-1}^1P_\mu(t)P_\nu(t)P_\nu(-t)\,dt.
\]

The parameter pair `(1/4;5/4)` gives

\[
U=\sum_{n=0}^\infty\frac{a_n^4}{4n+1}.
\]

Zhou [1], equations (5.10a), (5.10b), and (5.11), gives the following
specializations at `mu=nu=-1/2`:

\[
T_{-1/2,-1/2}=4U,
\qquad
T_{-1/2,-1/2}=\frac{32}{\pi^2}F_*,
\qquad
T_{-1/2,-1/2}=\frac{\pi\Gamma(1/4)^2}{3\Gamma(3/4)^6},
\tag{4}
\]
where

\[
F_*={}_4F_3\!\left(\begin{matrix}1,1/2,3/4,3/4\\5/4,5/4,3/2\end{matrix};1\right).
\]

The apparently indeterminate trigonometric factor in (5.10a) has the limit
`cos(pi*nu)/(2*nu+1) -> pi/2`. The two 5F4 values there coincide, and the
coefficients combine to 4. In (5.10b), the two 4F3 values coincide and their
coefficients combine to `32/pi^2`.

Euler reflection, `Gamma(1/4) Gamma(3/4)=sqrt(2) pi`, reduces (4) to

\[
\boxed{U=\frac{Q^2}{96\pi^3},\qquad
F_*=\frac{\pi^2}{8}U=\frac{Q^2}{768\pi}.}
\tag{5}
\]

The U summation is also stated explicitly as equation (1.24) of [1].

## 2. Reindex V into a reciprocal-index quarter-ratio sum

Define

\[
b_n=\frac{(1/4)_n}{(3/4)_n},\qquad
S_2=\sum_{n=1}^\infty\frac{b_n^2}{n},\qquad
S_4=\sum_{n=1}^\infty\frac{b_n^4}{n}.
\]

Because

\[
\frac{(1)_n(1)_n}{(2)_n n!}=\frac1{n+1},\qquad
\frac{(5/4)_n}{(7/4)_n}=3b_{n+1},
\]

we have the exact, absolutely convergent reindexing

\[
\boxed{V=81S_4.}\tag{6}
\]

Dixon's nonterminating 3F2 summation [2], differentiated at its vanishing
upper parameter, gives

\[
D(x)={}_3F_2(x,1/4,1/4;3/4+x,3/4+x;1)
\]
\[
=\frac{\Gamma(1+x/2)\Gamma(3/4+x)^2\Gamma(1/2+x/2)}
{\Gamma(1+x)\Gamma(3/4+x/2)^2\Gamma(1/2+x)}.
\]

Here `D(0)=1`, and termwise differentiation gives `D'(0)=S2`. Its gamma
logarithmic derivative is

\[
S_2=\psi(3/4)-\frac12\psi(1)-\frac12\psi(1/2)
=\frac\pi2-2\ell.
\tag{7}
\]

Only a proof device is differentiated; no parameter derivative survives in
(1), (2), or the resulting C6 formula.

## 3. A nonterminating connection identity with an explicit finite certificate

Define the analytic continuation through `x=0` of

\[
\mathcal S(x)={}_7F_6\!\left(
\begin{matrix}x,1+x/2,(1/4)^4,2x\\x/2,(3/4+x)^4,1-x\end{matrix};1\right),
\]

and put

\[
T(x)={}_3F_2(1/4,1/4,2x;3/4+x,3/4+x;1),
\]
\[
F(x)={}_4F_3\!\left(
\begin{matrix}1,1/2+x,3/4-x,3/4-x\\5/4,5/4,3/2-x\end{matrix};1\right),
\]
\[
C(x)=\frac{\Gamma(1/2-x)\Gamma(3/4+x)^2\Gamma(1-x)}
{\Gamma(1+x)\Gamma(1/2+x)\Gamma(3/4-x)^2},
\]
\[
B(x)=\frac{\Gamma(3/4+x)^4\Gamma(1-x)}
{(1/2-x)\Gamma(1+x)\Gamma(5/4)^2\Gamma(1/4)^2\Gamma(2x)}.
\]

The needed nonterminating identity is

\[
\boxed{\mathcal S(x)=C(x)T(x)-B(x)F(x).}\tag{8}
\]

The minus sign is essential. We prove (8) below by a finite coefficient
identity followed by controlled limits; a terminating Dougall identity is
not differentiated in its integer termination index.

### 3.1 The finite telescoping identity

For an integer `m>=0` and initially `0<x<1/8`, set

\[
a=m+x,\quad b=d=m+1/4,\quad \alpha=\beta=1/4,\quad\gamma=2x.
\]

These obey `1+2a=b+d+alpha+beta+gamma`. Let

\[
t_m(n)=\frac{a+2n}{a}
\frac{(a)_n(b)_n(d)_n(\alpha)_n(\beta)_n(\gamma)_n}
{n!(1+a-b)_n(1+a-d)_n(1+a-\alpha)_n(1+a-\beta)_n(1+a-\gamma)_n}.
\]

Write `S_m=sum_{n>=0} t_m(n)`; thus `S_0=mathcal S(x)`. Define

\[
\kappa_m=
\frac{(m+x+1)(m+x+1/2)(m+3/4-x)^2}
{(m+1/2-x)(m+x+3/4)^2(m+1-x)},
\]
\[
g_m(n)=
\frac{(a+n)(b+n)(d+n)(n+\alpha)(n+\beta)(n+\gamma)(n+1+b+d)}
{bd(a-b-d)(a+2n)
(n+1+a-\alpha)(n+1+a-\beta)(n+1+a-\gamma)}.
\]

Direct rational algebra gives, for `n>=1`,

\[
\boxed{t_m(n)-\kappa_m t_{m+1}(n)
=t_m(n)g_m(n)-t_m(n-1)g_m(n-1).}\tag{9}
\]

At `n=0` the previous-index boundary is defined as zero and the same identity
holds. `verify.py` checks (9) after division by `t_m(n)` as an identity in
three symbolic indeterminates `m,n,x`, not just at sampled indices.

Thus every finite sum obeys

\[
\sum_{n=0}^N[t_m(n)-\kappa_m t_{m+1}(n)]=t_m(N)g_m(N).
\tag{10}
\]

The gamma-ratio asymptotic gives

\[
\lim_{N\to\infty}t_m(N)g_m(N)=-B_m,
\]
\[
B_m=
\frac{\Gamma(3/4+x)^2\Gamma(m+3/4+x)^2\Gamma(m+1-x)}
{(m+1/2-x)\Gamma(m+1+x)\Gamma(m+5/4)^2\Gamma(1/4)^2\Gamma(2x)}.
\]

This is also evident in sign from `a-b-d=x-1/2-m<0`, with all the other
large-index factors positive. We obtain

\[
S_m=\kappa_m S_{m+1}-B_m.\tag{11}
\]

### 3.2 Iterate without discarding an upper boundary

Put `P_0=1` and

\[
P_M=\prod_{m=0}^{M-1}\kappa_m
=\frac{(1+x)_M(1/2+x)_M(3/4-x)_M^2}
{(1/2-x)_M(3/4+x)_M^2(1-x)_M}.
\]

Iteration gives exactly

\[
S_0=P_MS_M-\sum_{m=0}^{M-1}P_mB_m.
\tag{12}
\]

The numerator and denominator parameter sums in `P_M` are equal, so
`P_M -> C(x)`. Moreover,

\[
P_mB_m=B(x)
\frac{(1/2+x)_m(3/4-x)_m^2}{(5/4)_m^2(3/2-x)_m}.
\tag{13}
\]

The sum of (13) is precisely `B(x)F(x)` and is absolutely convergent.

For completeness, `S_M -> T(x)` follows by dominated convergence, not merely
pointwise convergence of the summands. Divide `t_M(n)` by the nth summand
of `T(x)`. The quotient is

\[
R_M(n)=\left(1+\frac{2n}{M+x}\right)
\frac{(M+x)_n(M+1/4)_n^2}
{(M+1-x)_n(M+x+3/4)_n^2}.
\]

For positive `y,delta`,

\[
\frac{(y)_n}{(y+\delta)_n}
\le\left(\frac{y+\delta}{y+\delta+n}\right)^\delta,
\]

by `log(1+u)>=u/(1+u)` and integral comparison. The three parameter gaps in
`R_M` sum to 2 and their denominator bases do not exceed `M+1`. Hence for
`M>=1`, with `v=n/(M+1)`,

\[
0<R_M(n)\le\frac{1+4v}{(1+v)^2}\le4.
\]

The series `T(x)` converges (excess one), so this supplies a summable
majorant independent of M. Taking limits in (12) proves (8).

All three hypergeometric series in (8), after removing the explicit
removable singularity at zero, are analytic on a small complex neighborhood
of zero. Their excesses are fixed at 2, 1, and 1. Uniform gamma-ratio bounds
there justify first differentiation of their series. The identity proved
for `0<x<1/8` therefore gives its derivative at zero.

### 3.3 Evaluate the first derivative

For `n>=1`, the derivative at zero of the nth summand of `mathcal S` is
`4 b_n^4/n`. Thus

\[
\mathcal S(0)=1,\qquad\mathcal S'(0)=4S_4.
\]

The other factors give

\[
T(0)=C(0)=1,\quad B(0)=0,\quad F(0)=F_*,
\]
\[
T'(0)=2S_2,\quad C'(0)=2\pi-8\ell,\quad B'(0)=\frac{256\pi^2}{Q^2}.
\]

Although T is not exactly D(2x), their first derivatives at zero agree:
the denominator-parameter derivative multiplies the vanishing upper
Pochhammer in every positive-index term. Equations (5), (7), and (8) yield

\[
4S_4=(2\pi-8\ell)+2S_2-\frac{256\pi^2}{Q^2}F_*
=3\pi-12\ell-\frac{32\pi^4}{Q^2}U.
\tag{14}
\]

Using (1),

\[
\boxed{S_4=\frac{2\pi}{3}-3\ell,\qquad V=54\pi-243\ell.}
\]

This is the analytic proof; the integer relation found during exploration
is not an assumption in the final expression.

### Sign/provenance note

The summation-by-parts construction is related to Chu [3], Section 2.
However, the displayed nonterminating 7F6 formula on printed page 1616 has a
plus sign on its first 4F3 contribution. For the specialization here that
sign disagrees with the explicit upper boundary (10). We do not use that
printed formula as a theorem with an unexamined sign. The independently
verified finite identity (9) fixes the required minus sign, and the
convergence argument above proves (8). Fresh evaluations at x=0.1 and
x=0.01 also check the minus-sign formula. The uniterated recurrence on the
preceding page retains the signed factor `a-b-d` after specialization.

## 4. Insert both evaluations into the full coefficient

From the input polynomial, the affected terms are exactly

\[
\frac{285}{2}AQ^2+\frac{58}{9}Q^2V-\frac{1247}{2}\pi Q^2-8352\pi^4U.
\]

The U substitution gives `-87*pi*Q^2`. The V substitution gives
`348*pi*Q^2-1566*ell*Q^2`. Their sum with the other two terms is

\[
Q^2\left(\frac{285}{2}A-\frac{725}{2}\pi-1566\ell\right)
=Q^2(29\pi-249A),
\]

using `ell=(A-pi)/4`. This proves (3) with no additive change to C6.

### A compact complete known part

The output `results/reduced_expression.json` contains the expanded known
polynomial with neither U nor V. An equivalent compact version is

\[
\begin{aligned}
E_{\rm red}={}&24P_b+24P_{Z,6}+\frac13P_K-36AP_5\\
&-\frac34(91A^2+36A\pi-208Q+2459\pi^2)B_-\\
&+\frac94(7A^2+4A\pi-16Q+271\pi^2)B_+\\
&+\frac Q8[63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)]\\
&+Q^2(29\pi-249A)-392\pi^{3/2}C_Z+\mathcal P,
\end{aligned}\tag{15}
\]

where

\[
\begin{aligned}
\mathcal P={}&-\frac{4059}{640}A^5+\frac{255}{8}A^4\pi
-\frac{2985}{64}A^3\pi^2-\frac{7827}{64}A^2\pi^3
+\frac{7863}{16}A^2\zeta(3)\\
&-3264A^2G\pi+3072AG^2+2208AG\pi^2
+\frac{788693}{640}A\pi^4-34816G\pi^3\\
&-655\pi^6-\frac{413393}{128}\pi^5
-\frac{3651379}{16}\pi^2\zeta(3)+\frac{20237049}{8}\zeta(5).
\end{aligned}\tag{16}
\]

Here `P_b=PB6`, `P_5=PZ5`, `P_K=PK6`. All other period definitions are
retained in the input and output JSON. In particular,

\[
B_-=\pi Q\,{}_4F_3(1/4,1/4,1/2,1/2;3/4,3/4,1;1),
\]
\[
B_+=\frac{64\pi^3}{Q}\,{}_4F_3(3/4,3/4,1/2,1/2;5/4,5/4,1;1).
\]

The two B coefficients in (15) result only from collecting the inherited
relations

\[
P_4=13B_--3B_+,\qquad
\mathcal L=-\frac{13A-3\pi}{2}B_-+\frac{3A-\pi}{2}B_+.
\]

This collection is not counted as another independent special-value
elimination.

Similarly, `CZ` is the already saved finite five-value combination

\[
C_Z=\sum_{r\in\{1,2,3,5,7\}}q_rZ_r,
\]

not a new auxiliary constant. With `c7=cos(pi/8)^7`, `s7=sin(pi/8)^7`, its
unchanged coefficients are

\[
\begin{aligned}
q_1&=c_7[\ell(624+1056\sqrt2)-\pi(408+12\sqrt2)],\\
q_2&=840\ell-192\pi,\\
q_3&=c_7[\pi(408-12\sqrt2)+(8-4\ell)(156-264\sqrt2)],\\
q_5&=-s_7[\pi(408-12\sqrt2)+(8/3-4\ell)(156-264\sqrt2)],\\
q_7&=s_7[-\pi(408+12\sqrt2)+(48/5-4\ell)(-156-264\sqrt2)].
\end{aligned}
\]

The full result is

\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_{\rm red}+835584\Lambda+391680H_5\\
&+13056\sqrt2(32G+3\pi^2)H_3\\
&-393\pi^3\mathscr W_{\rm c}+96P_a-784\pi^{3/2}\mathscr L_7.
\end{aligned}}\tag{17}
\]

The saved source repair is retained exactly once. No weight, initial data,
or definition of Wcentral, Pa, L7, Lambda, H3, or H5 is changed.

## 5. Verification and reproduction

Run

```text
python verify.py
python verify.py --numeric
```

The first run checks the rational telescope symbolically, its lower
boundary and iteration ratios, the elementary derivative algebra, complete
weighted substitution, compact expression, and preservation of every
unaffected inherited field (the special-value count metadata is updated).

It also constructs exact rational enclosures for the closed U and V using
the saved rational pi, Q, and log(2) intervals. Each closed-value enclosure
is entirely contained in its corresponding independently computed ordinary
series interval from the preceding certificate. This is a numerical
cross-check of the identities, not their proof. The saved interval
certificate is copied for reproducibility of these comparisons; its
constructor is in the preceding package, not rerun here.

The optional numerical run checks (8) at two nonzero parameter values and
checks the old and new polynomial evaluations. Numerical agreements are
reported separately from the exact checks in `results/verification.json`.

The coefficient's previously enclosed value is unchanged:

\[
C_6^{\rm rep}(1)=14331.68703275805432044546325524621711831732306198879\ldots.
\]

The advance is two finite evaluations and their exact elimination, not a
new digit count. The three finite-special-value targets remain Wcentral,
Pa, and L7. No minimality or arithmetic independence is asserted.

## References

[1] Yajun Zhou, *Notes on certain binomial harmonic sums of Sun's type*,
arXiv:2503.05599, equations (1.24), (5.10a-b), (5.11).
https://arxiv.org/html/2503.05599
The U identity is credited there to John M. Campbell, *On a higher-order
version of a formula due to Ramanujan*, Integral Transforms and Special
Functions 35 (2024), 260-269. This package uses Zhou's explicit formulas.

[2] NIST Digital Library of Mathematical Functions, 16.4.4, Dixon's
nonterminating well-poised sum; gamma/polygamma values from Chapter 5.
https://dlmf.nist.gov/16.4.E4
https://dlmf.nist.gov/5.15

[3] Wenchang Chu, *Nonterminating well-poised hypergeometric series*,
Hacettepe Journal of Mathematics and Statistics 49(5) (2020), 1611-1624.
https://dergipark.org.tr/en/download/article-file/970414
The finite telescope in this note is checked independently; see the sign
qualification in Section 3.3.

[4] Supplied central-binomial expression and previous complete interval
certificate, copied under `inputs/`. Their graph/RG assumptions and source
correction are inherited, not replaced by these general summation results.
