# Ordinary harmonic coefficients for the remaining C6 polylogarithmic sector

## Result and scope

Input: `inputs/cyclotomic_expression.json`, the supplied
`C6_cyclotomic_expression.json`. The normalization is `r6 = 2187 C6(1)`.
All three elliptic definitions, their graph/RG identifications, and the saved
source correction remain inherited inputs. This is an analytic simplification
of that representation, not an independent six-loop calculation.

The new calculation removes the finite nested harmonic coefficient from the
weight-five polylogarithmic value. A single real alternating sum with ordinary
harmonic numbers of orders one, two, and three replaces it. Its harmonic
polynomial degree is at most two. The mixed product G*D3 cancels from the active
polylogarithmic block. There are still TWO non-elementary polylogarithmic/Euler
sum values, THREE elliptic quantities, and 18 expanded known monomials.
Neither arithmetic independence nor elimination of an elliptic period is claimed.

The new basis is not merely defined as a linear combination of the old values:
its coefficients are specified directly by ordinary finite harmonic sums. The
identity linking it to the old value is proved by finite stuffles and a ten-word
shuffle. A separate exact rational Euler evaluator certifies both new defining
series without any initial transcendental constant.

## 1. Definitions and complete replacement

Use the strict multiple-polylogarithm convention of the input. When only one
argument is shown below, all remaining arguments are one. Put

\[
 H_N^{(p)}=\sum_{j=1}^N j^{-p},\quad H_0^{(p)}=0,\quad H_N=H_N^{(1)}.
\]

Retain
\[
 D_3=\Im\operatorname{Li}_{2,1}(i,1)
 =\sum_{r=0}^{\infty}\frac{(-1)^rH_{2r}}{(2r+1)^2}.
\]
Define independently
\[
 \boxed{S_5=\sum_{r=1}^{\infty}(-1)^r
 \left\{\frac{H_{2r-1}H_{2r-1}^{(2)}-H_{2r-1}^{(3)}}{4r^2}
       +\frac{H_{2r-1}^{\,2}-H_{2r-1}^{(2)}}{8r^3}\right\}.}       \tag{1}
\]
Equivalently, for
\[
 q_n=\frac{H_{n-1}H_{n-1}^{(2)}-H_{n-1}^{(3)}}{n^2}
       +\frac{H_{n-1}^{\,2}-H_{n-1}^{(2)}}{n^3},
\]
we have
\[
 S_5=\sum_{n\ge1}\cos(n\pi/2)q_n.
\]
The first nonzero term is q_4=11/96, with positive sign. The zero terms at the
start remain in the convention and cause no known-polynomial compensation.
Both series converge absolutely: H_N=O(log(N+1)), whereas H_N^(2),H_N^(3) are
bounded. The cosine notation is optional; evaluating (1) needs rational numbers
and a sign only. No nested H_N(1,2), derivative, matrix, or complex-valued special
function evaluation is required.

The exact identity replacing the input D5=Re Li_(2,1,2)(i,1,1) is
\[
 \boxed{D_5=\frac32 S_5+\frac12G D_3
       +\frac{29\pi^2\zeta(3)}{6144}-\frac{\pi^3G}{384}.}       \tag{2}
\]
It follows that
\[
\begin{aligned}
4352(32G+9\pi^2)D_3-278528D_5
={}&39168\pi^2D_3-417792S_5\\
&+\frac{2176}{3}G\pi^3-\frac{3944}{3}\pi^2\zeta(3).
\end{aligned}                                                   \tag{3}
\]
In particular, 139264*G*D3 - (278528/2)*G*D3 = 0.

## 2. Full updated C6 expression

Put A=pi+4log(2), Q=Gamma(1/4)^4/pi, G=beta(2). The complete formula is
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_H+13056(3\pi^2D_3-32S_5)\\
&+\pi^3\mathcal E_c+24\pi^3\mathscr M_7
 +192\pi^2\mathscr P_c^{(3)}.
\end{aligned}}                                                   \tag{4}
\]
All three elliptic sums in (4) are exactly the input definitions, reproduced in
full in `results/updated_expression.json`. In particular
P_a=2*pi^2*PaCubic remains unchanged; no index-zero term of any elliptic sum is
separated or counted again.

The new known part is
\[
 E_H=\frac Q8[63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)]
       +Q^2(29\pi-249A)+\mathcal P_H,
\]
\[
\boxed{\begin{aligned}
\mathcal P_H={}&\frac{21}{640}A^5+\frac7{64}A^3\pi^2
 +\frac{1149}{64}A^2\pi^3+\frac{7863}{16}A^2\zeta(3)\\
&+192AG(16G+3\pi^2)+\frac{14853}{640}A\pi^4+544G\pi^3\\
&+\frac{37631}{128}\pi^5+\frac{219725}{16}\pi^2\zeta(3)
 -\frac{805959}{8}\zeta(5).
\end{aligned}}                                                   \tag{5}
\]
Thus
\[
 E_H-E_{\rm cyc}=\frac{2176}{3}G\pi^3-\frac{3944}{3}\pi^2\zeta(3).
\]
Only two known coefficients change:
G*pi^3: -544/3 -> 544;
pi^2*zeta(3): 722279/48 -> 219725/16.
The Q-dependent block, A^4*pi and A^2*G*pi cancellations, and absence of an
explicit pi^6 term all remain intact. The source correction is preserved once.

## 3. Proof by finite stuffle and shuffle

Let
\[
 S(z)=\sum_{n\ge1}z^n q_n,\qquad |z|\le1.
\]
All multiple series used here converge absolutely on this closed disk. Define
H_N(a,b)=sum_(N>=j>k>=1) j^(-a)k^(-b). Elementary multiplication of finite sums
and separation of the diagonal give
\[
 H_NH_N^{(2)}-H_N^{(3)}=H_N(1,2)+H_N(2,1),
\]
\[
 H_N^2-H_N^{(2)}=2H_N(1,1).
\]
Therefore
\[
 S(z)=\operatorname{Li}_{2,1,2}(z)
      +\operatorname{Li}_{2,2,1}(z)
      +2\operatorname{Li}_{3,1,1}(z).                            \tag{6}
\]

In the HPL convention omega_0=dz/z, omega_1=dz/(1-z), word 01 represents Li2
and 011 represents Li_(2,1). The shuffle product of their iterated integrals
[1] gives precisely
\[
 01\shuffle011=6(00111)+3(01011)+(01101).
\]
Consequently
\[
 \operatorname{Li}_2(z)\operatorname{Li}_{2,1}(z)
 =6\operatorname{Li}_{3,1,1}(z)
  +3\operatorname{Li}_{2,2,1}(z)+\operatorname{Li}_{2,1,2}(z).
\]
Combining this with (6) proves the functional identity
\[
 \boxed{2\operatorname{Li}_{2,1,2}(z)
          =3S(z)-\operatorname{Li}_2(z)\operatorname{Li}_{2,1}(z).} \tag{7}
\]
The standard shuffle algebra is an external input, not a claimed new theorem.
The application to the saved C6 block and the direct coefficient specification
(1) are the present calculation. No numerical integer relation is used.

### 3.1 A unit-circle real part

The defining series immediately gives Li2(i)=-pi^2/48+iG. We also need
\[
 \boxed{\Re\operatorname{Li}_{2,1}(i)=\frac{29}{64}\zeta(3)-\frac\pi4G.} \tag{8}
\]
Here is a self-contained calculation of (8). The HPL differential rule [1] gives
\[
 \frac{d}{dz}\operatorname{Li}_{2,1}(z)=\frac{\log^2(1-z)}{2z}.
\]
For 0<theta<2pi, the principal logarithm satisfies
\[
 \log(1-e^{i\theta})=\log(2\sin(\theta/2))+
                      \frac i2(\theta-\pi).
\]
Thus
\[
 \frac{d}{d\theta}\Re\operatorname{Li}_{2,1}(e^{i\theta})
  =\frac{\pi-\theta}{2}\log(2\sin(\theta/2)).
\]
The value at theta=0 is zeta(3), as follows by substituting u=1-z in
(1/2)int_0^1 log^2(1-z)/z dz and expanding 1/(1-u).
Use the Abel-regularized Fourier expansion
log(2sin(theta/2))=-sum_(k>=1)cos(k theta)/k and then take its integrable endpoint
limit. Integration gives, for 0<=alpha<=2pi,
\[
 \Re\operatorname{Li}_{2,1}(e^{i\alpha})
 =\frac{\zeta(3)}2+\frac{\Re\operatorname{Li}_3(e^{i\alpha})}{2}
  -\frac{\pi-\alpha}{2}\Im\operatorname{Li}_2(e^{i\alpha}).    \tag{9}
\]
The classical Fourier/polylogarithm conventions are those of [2]. At alpha=pi/2,
phase filtering gives ReLi3(i)=-3*zeta(3)/32 and ImLi2(i)=G, proving (8).
Taking real parts of (7) at z=i and inserting (8) now proves (2).

## 4. Exact rational Euler evaluation and error bounds

The analytic simplification does not rely on high precision. Independently,
both new defining series admit rational finite approximants and rational error
bounds. This provides a useful check without any gamma, Catalan, zeta, or pi
initial value.

For a sequence (a_r) define
\[
 \mathcal E_N[a]=\sum_{r=0}^{N-1}(-1)^r w_{N,r}a_r,
 \qquad
 w_{N,r}=1-2^{-N}\sum_{j=0}^r\binom Nj.
\]
The approximants are
\[
 D_{3,N}=\mathcal E_N\left[\frac{H_{2r}}{(2r+1)^2}\right],
 \qquad S_{5,N}=-\mathcal E_N[q_{2r+2}].                       \tag{10}
\]
The minus sign in the second formula is important. For every integer N>=1,
\[
 \boxed{|D_3-D_{3,N}|<64\,2^{-N},\qquad
 |S_5-S_{5,N}|<2^{17}(N+1)2^{-N}.}                            \tag{11}
\]
The approximants in (10) are Euler-weighted, not literal partial sums.

### 4.1 Two analytic coefficient families

For integer n>=1 let
\[
 c_n(a)=\frac{\Gamma(n+a)}{\Gamma(n)\Gamma(1+a)}
        =\prod_{j=1}^{n-1}(1+a/j),
\]
\[
 F_n(a,b)=\frac{c_n(a)^2c_n(b)}{c_n(a+b)}.
\]
At a=b=0, ordinary finite-product differentiation gives
\[
 c_n'(0)=H_{n-1},\quad c_n''(0)=H_{n-1}^2-H_{n-1}^{(2)},
\]
\[
 \frac12\partial_a^2\partial_b F_n(0,0)
    =H_{n-1}H_{n-1}^{(2)}-H_{n-1}^{(3)}.                    \tag{12}
\]
In particular q_n is the indicated combination of derivatives of
F_n(a,b)/n^2 and c_n(a)/n^3. These derivatives are proof devices only.

Take |a|,|b|<=1/16. By the beta integral [3], with T=t1*t2*t3,
\[
\begin{aligned}
 \frac{F_n(a,b)}{n^2}
 ={}&(n+a+b)K(a,b)\int_{[0,1]^3}T^{n-1}
 t_1^a t_2^a t_3^b\\
 &\hspace{12mm}\times(1-t_1)^{-a}(1-t_2)^b(1-t_3)^{-b}
 \,dt_1dt_2dt_3,
\end{aligned}                                                   \tag{13}
\]
where
\[
 K(a,b)=\frac{\Gamma(1+a+b)}
 {\Gamma(1+a)^2\Gamma(1+b)^2\Gamma(1-a)\Gamma(1-b)}.
\]
Also
\[
 \frac{c_n(a)}n=\frac1{\Gamma(1+a)\Gamma(1-a)}
     \int_0^1 t^{n+a-1}(1-t)^{-a}\,dt.                       \tag{14}
\]
Additional factors 1/n in (14) are represented by additional uniform moments.
These integrals merely establish bounds; the evaluator computes rational finite
harmonic sums, not beta or gamma functions.

### 4.2 Uniform masses

For |u|<1 the log-gamma series [4] implies
\[
 |\log\Gamma(1+u)|\le |u|+\frac{|u|^2}{1-|u|}
                      =\frac{|u|}{1-|u|}.
\]
Here use 0<gamma<1, zeta(k)<2, and 2/k<=1 for k>=2. Thus
\[
 |K(a,b)|\le\exp(1/7+6/15)<2.
\]
The last inequality follows from 1/7+6/15<2/3<log2. Every beta density has total
absolute mass bounded by
\[
 \int_0^1[t(1-t)]^{-1/16}\,dt
 \le\frac{16}{15}2^{1/8}<\frac65.
\]
To obtain the first inequality split at 1/2 and bound the nonsingular factor;
the second uses 2^(1/8)<9/8. Therefore the complete mass in (13) is less than
2*(6/5)^3<4. The mass for (14), including any uniform moments, is less than
2*(6/5)<3.

### 4.3 Exact remainder kernel and Cauchy estimates

For the geometric sequence a_r=x^r, 0<=x<1, the Euler remainder is exactly
\[
 R_N(x)=\frac1{1+x}-\sum_{r=0}^{N-1}(-x)^r w_{N,r}
       =\frac{2^{-N}(1-x)^N}{1+x}.                           \tag{15}
\]
The endpoint limits suffice in the integrals. For N>=1,
\[
 |R_N(x)|\le2^{-N},\qquad |xR_N'(x)|\le(N+1)2^{-N}.
\]
For the n=2r+2 subsequence of (13), the moment is T*(T^2)^r and its linear
factor n+a+b is 2r+2+a+b. Hence its Euler remainder, at fixed T, is T times
\[
 (2x\partial_x+2+a+b)R_N(x),\qquad x=T^2,
\]
whose absolute value is at most (2N+5)*2^(-N). The whole F-family remainder is
therefore at most 4(2N+5)*2^(-N). Cauchy's estimate for
(1/2)partial_a^2 partial_b on the polydisc of radius 1/16 multiplies this by
16^3. Its contribution is at most 16384(2N+5)*2^(-N).

For c_n(a)/n^3 the total mass is less than 3. Its second derivative contributes
at most 3*2*16^2*2^(-N)=1536*2^(-N). Their sum is bounded by
\[
 (32768N+83456)2^{-N}<2^{17}(N+1)2^{-N},
\]
proving the second bound in (11).

For D3 use n=2r+1, the family c_n(a)/n^2, and one derivative. Its mass is less
than 3 and its Cauchy multiplier is 16, giving 48*2^(-N)<64*2^(-N).
All coefficient families and their required derivatives converge locally
uniformly in the parameter polydisc: their terms are bounded by summable
powers n^(-2+1/16) times finite logarithmic powers. This justifies the parameter
operations. The signed moment construction is uniformly absolutely integrable,
so no exchange of divergent sums is being used.

## 5. Executed checks and numerical results

`verify.py` passes 101 exact finite checks. These include all ten shuffle
multiplicities, finite harmonic stuffles, the complex-real product coefficients,
the complete weighted substitution, the updated known polynomial, preservation
of every elliptic definition and the source correction, finite Euler kernel
identities, and the derivative-polynomial coefficients. Test count is an
implementation count, not a number of independent theorems.

`certify.py` constructs nested rational intervals. Widths include the full
infinite-tail bound and all finite arithmetic (which is exact):

| N | D3 interval width | S5 interval width |
|---:|---:|---:|
| 256 | <1.106e-75 | <5.819e-70 |
| 512 | <9.547e-153 | <1.003e-146 |
| 800 | <1.920e-239 | <3.150e-233 |

In particular
\[
 D_3=-0.113648917599903643441539501971145908418275607824704791929109\ldots,
\]
\[
 S_5=0.068263589940013007438040232736643216898984063630158706522937752424\ldots.
\]
These shown digits are covered by the rational intervals, not just by numerical
agreement. Exact endpoints and finite rational centers are in
`results/rational_intervals.json`.

Separately, `numerical.py` evaluates the needed MPLs from their own strict series
at i/2 and Taylor continuation to i. This routine is retained from the previous
cyclotomic package; it does not use the new harmonic interval to construct its
MPL values. At 290 working decimal digits, it finds:

- Shuffle identity residual: <2.835e-292.
- Real-part formula (8) residual: <8.017e-292.
- New D3 Euler center versus MPL: <3.918e-242.
- New S5 Euler center versus independent MPL combination: <4.635e-245.
- Full weighted old/new polylog block, including known shift: <1.513e-236.

The independent values lie inside the new rational intervals. These residuals
are floating-point checks, separate from the proofs and rational certificates.

Using inherited interval midpoints for the unchanged elliptic quantities, the
new full expression reassembles to
\[
 C_6^{\rm rep}(1)=14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]
The old/new full assemblies differ by less than 6.916e-240 at those settings.
No new full-C6 interval is constructed; the displayed full value inherits the
same upstream physical and period-identification qualifications as the input.

## 6. What remains

There are still three elliptic quantities (Ecentral, M7central, PaCubic), and two
non-elementary values in the polylogarithmic sector (D3 and S5). The primitive
still has two indices. The number of known monomials stays 18. The advance is
removal of a finite nested coefficient, replacement by quadratic ordinary
harmonic coefficients, and exact cancellation of the Catalan-times-D3 product.
Together with the inherited elliptic definitions, every active remainder can
now be specified using ordinary finite harmonic numbers through order three.
This is not a proof of a smaller transcendence basis.

## Reproduction

Python 3, SymPy and mpmath suffice; no network access is required.

```text
python formula.py
python verify.py
python certify.py 256 512 800
python numerical.py
```

`PROVENANCE.json` and `MANIFEST.sha256` record input and output hashes. Legacy
fields retained in the updated expression are provenance, not extra active
contributions.

## Sources

[1] E. Remiddi and J. A. M. Vermaseren, Harmonic Polylogarithms,
hep-ph/9905237, definitions, differentiation and shuffle products.
https://arxiv.org/html/hep-ph/9905237

[2] NIST DLMF 25.12, polylogarithm definitions and unit-circle expansions.
https://dlmf.nist.gov/25.12

[3] NIST DLMF 5.12, Euler beta integral and gamma quotient.
https://dlmf.nist.gov/5.12

[4] NIST DLMF 5.7, convergent log-gamma series (expanded also with the elementary
series for log(1+u)). https://dlmf.nist.gov/5.7

[5] Supplied cyclotomic expression and preceding cubic/even/seventh interval
records in inputs/. They supply the coefficient being simplified and the
unchanged elliptic definitions and numerical references, not the new shuffle
calculation or new rational harmonic certificate.
