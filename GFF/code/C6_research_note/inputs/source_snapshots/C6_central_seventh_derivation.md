# One central-binomial sequence for the complete seventh-power sector of C6(1)

## Result and scope

Input: `inputs/expression.json`, the supplied **U,V-reduced** expression. The
normalization is `r6 = 2187 C6(1)`. All physical graph/RG identifications, the
source repair, and the earlier U,V summations remain inherited assumptions.

This continuation proves the exact sector identity

\[
\boxed{-36AP_5-392\pi^{3/2}C_Z-784\pi^{3/2}\mathscr L_7
       =24\pi^3\mathscr M_7.}                                      \tag{1}
\]

The left side is the **complete existing seventh-power contribution**, including
its ordinary correction. The right side has one central-binomial coefficient
sequence, rather than five differently shifted gamma-ratio sequences.

This is not a finite ordinary-hypergeometric evaluation of the logarithmic
period. The old ordinary values are folded into the same sector, not separately
proved elementary or dependent. Three auxiliary quantities remain: Wcentral,
Pa, and M7central. Harmonic polynomial degree rises from one to three. Both the
old and new series have absolute term bounds of order log(n)/n^(5/2).

Keeping n=0 in the new series makes the remaining elementary polynomial
**unchanged**. The active known polynomial loses P5 and all five Z values; its
expanded expression has 30 monomials instead of 55 in the input's same symbol
convention. This count is bookkeeping, not transcendence degree.

## 1. Explicit new series; no derivatives or variable-argument gamma values

Put
\[
 \ell=\log2,\quad A=\pi+4\ell,\quad a_n=\frac{(1/2)_n}{n!}
 =\frac{\binom{2n}{n}}{4^n},\quad y_n=n+\frac14,
\]
\[
 h_n=\ell+H_n-H_{2n},\qquad
 \delta_n=\frac{\pi^2}{3}-4H_{2n}^{(2)}+2H_n^{(2)},
 \qquad H_0^{(j)}=0.
\]
Define the following **finite polynomials** in these quantities:
\[
 u_n=1-14y_nh_n,
\]
\[
 v_n=196y_nh_n^2-28h_n+7y_n(\delta_n-\pi^2),
\]
\[
 T_n=80\pi^2y_n-26\pi u_n+11v_n,
 \qquad K_n=28\pi^2y_n-10\pi u_n+3v_n.
\]
The machine file uses the local name `V_n` for K_n; this is not the ordinary V
that was eliminated in the preceding continuation.

Set
\[
\boxed{\begin{aligned}
 F_n={}&(98H_{2n}+74\ell-6\pi)T_n-98\pi K_n\\
 &-98(11u_n-13\pi y_n)
       \left(\frac{\pi^2}{3}+4H_{2n}^{(2)}\right)\\
 &-8624y_n\left[\zeta(3)-H_{2n}^{(3)}\right].
\end{aligned}}                                                    \tag{2}
\]
Then
\[
\boxed{\mathscr M_7=\sum_{n=0}^{\infty}(-1)^n a_n^7F_n.}           \tag{3}
\]
Only pi, log(2), zeta(3), binomial coefficients, and finite harmonic numbers
occur. There is no Q, Catalan constant, eighth-shift gamma constant, hidden
special-function derivative, integral, or multiple summation index in (3).

For an implementation audit, the included n=0 term is
\[
\begin{aligned}
F_0={}&39886\ell^3-10906\pi\ell^2-22792\ell^2
-2188\pi^2\ell+8156\pi\ell\\
&-\frac{1679}{6}\pi^3+\frac{2330}{3}\pi^2-2156\zeta(3).
\end{aligned}                                                     \tag{4}
\]
It is **not** added again to the known polynomial.

Gamma-ratio and harmonic asymptotics give
\[
 (-1)^n a_n^7F_n
 =\frac{294(-1)^n\log n}{\pi^{3/2}n^{5/2}}+O(n^{-5/2}).             \tag{5}
\]
In particular, the series is absolutely convergent. The new harmonic degree is
at most three, principally through H_(2n) h_n^2. Literal finite partial sums are
not what produces the long numerical value below.

## 2. Complete updated coefficient

Let E_UV be the entire known polynomial in the supplied U,V-reduced file. Set
\[
 E_* = E_{UV}+36AP_5+392\pi^{3/2}C_Z.                               \tag{6}
\]
Thus the terms on the right of (6) cancel exactly the existing P5 and Z block;
(6) is not a new added physical contribution. The full coefficient is
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_*+835584\Lambda+391680H_5\\
&+13056\sqrt2(32G+3\pi^2)H_3
-393\pi^3\mathscr W_{\rm c}+96P_a+24\pi^3\mathscr M_7.
\end{aligned}}                                                    \tag{7}
\]
A complete compact known part is
\[
\begin{aligned}
E_*={}&24P_b+24P_{Z,6}+\frac13P_K\\
&-\frac34(91A^2+36A\pi-208Q+2459\pi^2)B_-\\
&+\frac94(7A^2+4A\pi-16Q+271\pi^2)B_+\\
&+\frac Q8[63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)]\\
&+Q^2(29\pi-249A)+\mathcal P,
\end{aligned}                                                     \tag{8}
\]
where
\[
\begin{aligned}
\mathcal P={}&-\frac{4059}{640}A^5+\frac{255}{8}A^4\pi
-\frac{2985}{64}A^3\pi^2-\frac{7827}{64}A^2\pi^3
+\frac{7863}{16}A^2\zeta(3)-3264A^2G\pi\\
&+3072AG^2+2208AG\pi^2+\frac{788693}{640}A\pi^4-34816G\pi^3\\
&-655\pi^6-\frac{413393}{128}\pi^5
-\frac{3651379}{16}\pi^2\zeta(3)+\frac{20237049}{8}\zeta(5).
\end{aligned}                                                     \tag{9}
\]
Here Q=Gamma(1/4)^4/pi and G is Catalan's constant. All definitions of Bminus,
Bplus, Pb, PZ6, PK, Lambda, H3, H5, Wcentral, and Pa are retained exactly in the
JSON. In particular, this calculation does not eliminate the separate
**eighth-power** Y values in PZ6 and PK.

## 3. Why five shifted streams become one

### 3.1 A finite-Fourier family

For |x| sufficiently small define, as a proof device,
\[
\Phi_x(t)=
\left[\frac{\pi\Gamma(1-x)}
 {\Gamma(1/2+x)\cos(\pi x)}\right]^7
\sum_{m\in\mathbb Z}
\frac{m+t}
 {[\Gamma(3/4-x+m+t)\Gamma(3/4-x-m-t)]^7}.                         \tag{10}
\]
One may use |x|<=1/64 throughout the argument. Each summand is entire in t.
Gamma reflection [1] and the gamma-ratio asymptotic [2] give locally uniform
absolute convergence in t, since the real-index decay is
O(|m|^(-5/2+14 Re(x))). Parameter and t derivatives used below also converge
locally uniformly.

Reindexing shows that Phi is one-periodic and odd in t. To see its Fourier
support directly, reflect a gamma factor and use the positive-real-side gamma
ratio. Uniformly in a vertical strip the sum is bounded by
\[
 C_x e^{7\pi|\operatorname{Im}t|}
 (1+|\operatorname{Im}t|)^{14\operatorname{Re}x-3/2}.
\]
A harmless additional fixed polynomial factor would suffice as well. Move the
contour for a Fourier coefficient vertically in the direction giving decay.
Coefficients of frequency 2 pi k vanish for |k|>=4, since 2 pi |k|>7 pi. Oddness
then gives
\[
\boxed{\Phi_x(t)=b_1(x)\sin(2\pi t)+b_2(x)\sin(4\pi t)
                    +b_3(x)\sin(6\pi t).}                       \tag{11}
\]
No explicit evaluation of b1, b2, b3 is being assumed.

For any function f in this three-dimensional trigonometric space, direct
interpolation yields
\[
\begin{aligned}
&(22\sqrt2+13)f(1/8)+(22\sqrt2-13)f(3/8)-35f(1/4)\\
&\qquad=\left[20f-\frac{13}{2\pi}f'
                 +\frac{11}{4\pi^2}f''\right]_{t=1/4},
\end{aligned}                                                     \tag{12}
\]
\[
\begin{aligned}
&(10+12\sqrt2)f(1/8)+(-10+12\sqrt2)f(3/8)-16f(1/4)\\
&\qquad=\left[14f-\frac5\pi f'+\frac{3}{2\pi^2}f''\right]_{t=1/4}.
\end{aligned}                                                     \tag{13}
\]
The verifier proves both equations on each of the three sine basis functions.
Denote the operators in square brackets by D and E, respectively.

### 3.2 Match the retained shifted definitions, including the ordinary terms

For this proof only, put
\[
 Z_x(t)=\sum_{n\ge0}(-1)^n(n+t)
 \left[\frac{\Gamma(n+t+1/4+x)}{\Gamma(n+t+3/4-x)}\right]^7.
\]
Gamma reflection gives the exact pairing
\[
\Phi_x(t)=
\frac{\sin^7\!\pi(t+1/4+x)Z_x(t)
      +\sin^7\!\pi(1/4-t+x)Z_x(1-t)}
 {[\Gamma(1/2+x)\cos(\pi x)/\Gamma(1-x)]^7}.                     \tag{14}
\]
At x=0, the three samples in (12) are precisely
Xminus/pi^(7/2), Xzero/pi^(7/2), and Xplus/pi^(7/2). The saved P5 definition
therefore becomes
\[
\boxed{P_5=16\pi^5[D\Phi_0]_{t=1/4}.}                            \tag{15}
\]

Differentiating Z_x is legitimate by the convergence bounds above. The
logarithmic insertion is fixed by digamma duplication [1]: with a=t+1/4,
\[
\left.\partial_x
 \left[\frac{\Gamma(n+a+x)}{\Gamma(n+a+1/2-x)}\right]^7\right|_0
=14\left[\frac{\Gamma(n+a)}{\Gamma(n+a+1/2)}\right]^7
 [H_{2n}(2a)+\psi(2a)-\ell].                                    \tag{16}
\]
The derivative of the normalization in (14) is essential.

Here is an explicit coefficient audit. For r=1,2,3,5,7 let
\[
(\sigma_r)=(c^7,1,c^7,-s^7,s^7),\quad
(\alpha_r)=(22\sqrt2+13,-35,22\sqrt2-13,22\sqrt2-13,22\sqrt2+13),
\]
\[
(\beta_r)=(10+12\sqrt2,-16,-10+12\sqrt2,-10+12\sqrt2,10+12\sqrt2),
\]
where c=cos(pi/8), s=sin(pi/8). The input harmonic weights satisfy
w_r=-12 alpha_r sigma_r. Its ordinary coefficients satisfy
\[
 q_r=w_r\left[2\{\psi((r+2)/4)+\gamma\}
       +\pi\cot\frac{\pi(r+2)}8+2\ell\right]
       +12\pi\beta_r\sigma_r.                                   \tag{17}
\]
The five cases are checked exactly against the saved JSON, using the elementary
quarter-digamma values. The Euler constant gamma cancels from the final result.
Thus (12)-(17), including every q_r term, give
\[
\boxed{\mu=-\frac{48\pi^5}{7}[D\partial_x\Phi_x]_{x=0,t=1/4}
       -6\ell P_5+48\pi^6[E\Phi_0]_{t=1/4}.}                    \tag{18}
\]
The input relation is mu=8 pi^(3/2) L7+4 pi^(3/2) CZ. Omitting CZ would not
produce (18) or the correct C6 insertion.

### 3.3 All needed derivatives become central-binomial sums

At t=1/4, x=0, every m<0 summand in (10) has a zero of total order seven,
coming from an inverse gamma factor at a nonpositive integer. All the mixed
derivatives used here have total order at most three, so the entire negative
half contributes zero to each. This leaves just one central sequence.

Write b_n=(-1)^n a_n^7 and J_n=H_(2n), and define
\[
 R_n=-7\left(\frac{\pi^2}{3}+4H_{2n}^{(2)}\right),\qquad
 S_n=-112\left[\zeta(3)-H_{2n}^{(3)}\right].
\]
Polygamma reflection, recurrence, and half-integer values [3] give the following
six identities, all evaluated at x=0,t=1/4:
\[
\begin{aligned}
\Phi&=\sum b_n y_n,&\quad\Phi_t&=\sum b_nu_n,&\quad\Phi_{tt}&=\sum b_nv_n,\\
\Phi_x&=\sum b_n14J_ny_n,\\
\Phi_{xt}&=\sum b_n(14J_nu_n+y_nR_n),\\
\Phi_{xtt}&=\sum b_n(14J_nv_n+2u_nR_n+y_nS_n).
\end{aligned}                                                     \tag{19}
\]
For example, the local logarithmic derivatives of a positive-index summand are
\[
 L_t=y_n^{-1}-14h_n,\qquad
 L_{tt}=-y_n^{-2}-7\pi^2+7\delta_n,
\]
\[
 L_x=14H_{2n},\quad L_{xt}=R_n,\quad L_{xtt}=S_n.
\]
No global logarithm of a signed summand is required; these are its local
logarithmic derivatives.

Substituting (19) into (15) and (18) gives, term by term,
\[
\begin{aligned}
-36AP_5-98\mu
=\pi^5\big[672D\partial_x\Phi
       +7104\ell D\Phi-\pi(576D+4704E)\Phi\big]
=24\pi^3\sum_{n\ge0}b_nF_n.
\end{aligned}                                                     \tag{20}
\]
The last polynomial identity is checked symbolically in independent variables
pi, ell, y, h, delta, H_(2n), H_(2n)^(2), H_(2n)^(3), and zeta(3).
Equations (1)-(3) follow. All parameter derivatives are thereby eliminated from
the active formula, rather than simply renamed as new constants.

## 4. Explicit error bound for a finite Euler evaluation

For N>=1 set
\[
 w_{N,n}=1-2^{-N}\sum_{k=0}^n\binom Nk,\qquad
 M_{7,N}^{E}=\sum_{n=0}^{N-1}(-1)^nw_{N,n}a_n^7F_n.
\]
A deliberately loose but fully explicit bound is
\[
\boxed{|\mathscr M_7-M_{7,N}^{E}|\le2^{100-N}.}                    \tag{21}
\]
This is a bound for the Euler approximant, not the raw N-term partial sum. The
large power 100 is a conservative coefficient bound, not a fitted parameter.

### 4.1 Uniform analytic bound on a two-parameter neighborhood

Set t=1/4+s and restrict |x|,|s|<=1/64. The nonnegative-index half Psi(x,s)
of (10) has a sevenfold beta-moment representation [4] with
\[
 a=1/2+s+x,\quad d=1/2-2x,\quad
 C(x,s)=\left[
 \frac{\Gamma(1-x)\cos\pi(s+x)}
 {\Gamma(1/2+x)\cos\pi x\,\Gamma(1/2-2x)}\right]^7.
\]
The moment variable is q=u1...u7 in [0,1]. The alternating kernel is
\[
 \sum_{n\ge0}(-1)^n(n+t)q^n=\frac{t}{1+q}-\frac{q}{(1+q)^2}.
\]
The exact remainder after its N Euler coefficients is
\[
2^{-N}\left[
\frac{t(1-q)^N}{1+q}
-\frac{Nq(1-q)^{N-1}}{1+q}
-\frac{q(1-q)^N}{(1+q)^2}\right].                                \tag{22}
\]
Its absolute value is <=(|t|+2)2^(-N), since Nq(1-q)^(N-1)<=1.

On the polydisk Re(a), Re(d)>=15/32 and
B(Re(a),Re(d))<16. Elementary integral bounds give |Gamma(1-x)|<3.
Reflection and the same integral bounds give
|1/Gamma(1/2+x)|<2 and |1/Gamma(1/2-2x)|<2. Also
|cos pi(s+x)|<2 and |1/cos pi x|<2. Thus
\[
 |C(x,s)|B(\operatorname{Re}a,\operatorname{Re}d)^7
 <(48\cdot16)^7<2^{70}.
\]
The uniform Euler remainder for Psi is consequently <2^(72-N).

### 4.2 Differentiate a bounded analytic remainder, not an asymptotic expansion

Cauchy's coefficient bound yields
\[
|\partial_x^a\partial_s^b(\Psi-\Psi_N^E)(0,0)|
 \le a!b!64^{a+b}2^{72-N},\quad a=0,1,\quad b=0,1,2.
\]
The negative-index part vanishes to order seven at the center, so these are the
same six derivatives needed in (19). Their linear combination for M7 has
coefficients
\[
\begin{array}{c|c}
\text{derivative}&\text{coefficient}\\\hline
\Psi_x&560\pi^2\\
\Psi_{xs}&-182\pi\\
\Psi_{xss}&77\\
\Psi&5920\ell\pi^2-3224\pi^3\\
\Psi_s&-1924\ell\pi+1136\pi^2\\
\Psi_{ss}&814\ell-360\pi.
\end{array}
\]
Using pi<4 and 0<ell<1, the sum of the Cauchy-weighted absolute coefficients
is less than
\[
 2^{20}+2^{22}+2^{26}+2^{19}+2^{21}+2^{25}<2^{27}.
\]
This proves the slightly stronger 2^(99-N) bound; (21) leaves one further bit
of slack. The proof is finite and uniform. It makes no assumption that an
infinite asymptotic expansion converges.

## 5. Executed checks and numerical enclosures

`verify.py` passes 39 exact checks: the five retained harmonic weights, all five
ordinary q coefficients, the two interpolation identities on all three Fourier
modes, derivative-polynomial identities, the complete weighted substitution,
the included n=0 term, unchanged primitive/wheel/polylogarithm inputs, unchanged
source correction, and finite Euler remainder identities.

`check_numerical.py` evaluates the paired shifted gamma sums in (14), not the
new central harmonic sum. It checks the three-mode reconstruction at separate
real and complex t values, for x=0, x=1/100, and x=-1/100+i/250. At 60 and 90
working digits, the largest observed differences are 4.279e-61 and 1.166e-90.
These 18 comparisons are floating-point implementation checks, not proofs of
error bounds or of the upstream physics.

`certify.py` separately initializes pi via Machin's formula, log(2) via a
rational atanh series, and zeta(3) via an Euler-transformed eta series. It uses
outward-rounded integer/dyadic intervals for every finite operation and adds
(21). It never initializes M7 from the old value. The resulting intervals nest:

| N | Width of the new M7 interval |
|---:|---:|
| 300 | <1.245e-60 |
| 600 | <6.110e-151 |
| 900 | <3.000e-241 |

The value starts
\[
\mathscr M_7=
-15332.5541947745752769789465340930315749885217640430336681175677525365981545886018999956957138476989737102\ldots.
\]

Only after this computation, the old five-shift intervals are read to compare
(1). The old interval for the same sector overlaps the new one. Reassembly of
the updated coefficient uses the inherited certified intervals for unchanged
periods. It gives
\[
C_6^{\rm rep}(1)=14331.6870327580543204454632552462171183173230619887904582031423\ldots
\]
with complete representation interval width <1.183e-145. This is consistent
with the prior complete certificate, not a different coefficient. The new
full interval is dominated by the unchanged wheel allowance.

## 6. Reproduction and limitations

Python 3, SymPy, and mpmath suffice. No network access is used by the scripts.

```text
python formula.py
python verify.py
python check_numerical.py
python certify.py
```

`results/reduced_expression.json` contains the entire active expression and
explicit new sum, with all inherited definitions retained for provenance.
`results/intervals.json` gives exact dyadic endpoints, all truncation bounds,
the overlap checks, and the reassembled complete interval.

The analytic gain is removal of five shifted gamma-ratio coefficient streams
from the seventh-power sector. It is not a proof that the individual Z values
are elementary, a finite evaluation of the remaining logarithmic content, or
a minimality/independence theorem. No claim is made that this particular
periodization identity is new to the mathematical literature.

The three remaining targets are Wcentral, Pa, and M7central. Unchanged Y values
remain in the ordinary PZ6/PK definitions. The source repair is kept once, and
nothing here independently rederives the upstream graph/RG representation.

## References and analytic inputs

[1] NIST DLMF 5.5: gamma reflection, recurrence, and digamma duplication.
https://dlmf.nist.gov/5.5

[2] NIST DLMF 5.11: gamma and gamma-ratio asymptotics.
https://dlmf.nist.gov/5.11

[3] NIST DLMF 5.15: polygamma recurrence, reflection, and integer/half-integer
values. https://dlmf.nist.gov/5.15

[4] NIST DLMF 5.12: Euler beta integral. https://dlmf.nist.gov/5.12

[5] Supplied C6_UV_reduced_expression.json: exact seventh-power weights,
ordinary corrections, P5 definition, and corrected full assembly.

[6] Supplied C6_complete_interval.zip/results/complete_refined.json: inherited
intervals for unchanged constants and an independent check of the new sector.
These endpoints are not used to construct the new M7 interval.
