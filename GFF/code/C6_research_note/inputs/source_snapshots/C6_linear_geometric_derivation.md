# A linear-H2 geometric series for the complete C6 polylogarithmic block

## Result, starting point, and limitations

Input: `inputs/classical_expression.json`, exactly the supplied
`C6_classical_trilog_expression.json`. The normalization remains
`r6 = 2187 C6(1)`.

The input is

\[
2187C_6(1)=E_{\rm cl}-39168\pi^2\mathcal T_3-417792\mathcal S_5
 +\pi^3\mathcal E_c+24\pi^3\mathscr M_7+192\pi^2\mathscr P_c^{(3)}.
\]

The new functional identity converts the complete polylogarithmic block to
one geometrically convergent, real series with **one linear second-order
harmonic accumulator**. Products of harmonic numbers, first- and third-order
harmonic accumulators, and an independent active T3 sum are not required by
this evaluator. The fixed argument is z=(1+i)/2; blockwise evaluation uses real
rational coefficients and the elementary constants pi, log(2), Catalan.

This is a reduction of coefficient complexity and combination of sums at a
common argument. It is NOT a proof of fewer arithmetically independent periods
or an evaluation of S5 in elementary/classical constants. The known polynomial
grows from 18 to 21 expanded monomials. All three elliptic quantities, their
normalizations, the repaired source terms, and the upstream graph/RG
identification are inherited and unchanged.

## 1. The explicit new series

Put
\[
\ell=\log2,\quad z=\frac{1+i}{2},\quad G=\beta(2),\qquad
\kappa=\frac{3\pi^2}{64}+\frac{\pi\ell}{8}-\frac G2.
\]
For H_0^(2)=0 and H_N^(2)=sum_{j=1}^N 1/j^2, define
\[
\boxed{\mathcal K_5=\Re\sum_{n=1}^{\infty}z^n
 \left[\frac{H_{n-1}^{(2)}+i\kappa}{n^3}
 +\frac{3\ell/2+3i\pi/4}{n^4}+\frac3{n^5}\right].}       \tag{1}
\]
The subscript denotes weight, not loop order. The machine symbol is K5linear.
Every coefficient is explicit; there is no nested finite harmonic sum,
parameter derivative, integral, or unspecified graph master in (1).

An equivalent fixed-function specification is
\[
\mathcal K_5=\Re\left[
\operatorname{Li}_{3,2}(z,1)-3\log\bar z\,\operatorname{Li}_4(z)
+3\operatorname{Li}_5(z)+i\kappa\operatorname{Li}_3(z)\right]. \tag{2}
\]
Here log(bar z)=-ell/2-i*pi/4, and the strict convention is
Li_(3,2)(z,1)=sum_(n>m>=1) z^n/(n^3 m^2).
Formula (1), not a claim of classical reduction of Li_(3,2), is the one-series
specification. It uses harmonic order two and degree one; the old S5 used
orders one through three and degree two.

## 2. Full coefficient and known-polynomial compensation

Define the elementary weight-five polynomial
\[
\boxed{\begin{aligned}
P_0={}&\frac{G\pi\ell^2}{32}+\frac{11G\pi^3}{384}
-\frac{163}{256}\zeta(3)\ell^2+\frac{457}{1536}\pi^2\zeta(3)
-\frac{753}{256}\zeta(5)\\
&-\frac{13}{1920}\ell^5+\frac{35}{2304}\pi^2\ell^3
+\frac{1001}{92160}\pi^4\ell.
\end{aligned}}                                                   \tag{3}
\]
The complete block identity is
\[
\boxed{-39168\pi^2\mathcal T_3-417792\mathcal S_5
       =835584\mathcal K_5-417792P_0.}                            \tag{4}
\]
Thus
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_{\rm geo}+835584\mathcal K_5
 +\pi^3\mathcal E_c+24\pi^3\mathscr M_7
 +192\pi^2\mathscr P_c^{(3)},\\
E_{\rm geo}={}&E_{\rm cl}-417792P_0.
\end{aligned}}                                                  \tag{5}
\]
All elliptic zero-index terms remain in their original sums. The shift in (5)
comes from a functional identity, not an index shift or an added graph term.

For a complete compact polynomial, put A=pi+4ell and
Q=Gamma(1/4)^4/pi. Then
\[
\boxed{\begin{aligned}
E_{\rm geo}={}&\frac Q8[63A^3+120AG+79A\pi^2+2013\pi^3
                  +54204\zeta(3)]\\
&+Q^2(29\pi-249A)+\mathcal P_{\rm geo},
\end{aligned}}                                                  \tag{6}
\]
where
\[
\boxed{\begin{aligned}
\mathcal P_{\rm geo}={}&\frac1{1920}\big[
5367A^5-26520A^4\pi-137150A^3\pi^2+699510A^2\pi^3\\
&\hspace{28mm}-2972057A\pi^4+4837177\pi^5\big]\\
&+48G[64AG-17A^2\pi-56A\pi^2-153\pi^3]\\
&+\frac{\zeta(3)}{16}[273879A^2-532032A\pi-1503123\pi^2]
+\frac{9025209}{8}\zeta(5).
\end{aligned}}                                                  \tag{7}
\]
The entire Q-dependent block is unchanged. There is still no explicit pi^6
term or reciprocal Q in the known polynomial. Its 21-monomial count, compared
with 18 in the input, is a cost of this representation, not a simplification
claim about its term count.

## 3. The functional identity underlying (4)

Retain the prior real sum
\[
\mathcal S_5=\Re S(i),\qquad
S(w)=\operatorname{Li}_{2,1,2}(w,1,1)
+\operatorname{Li}_{2,2,1}(w,1,1)
+2\operatorname{Li}_{3,1,1}(w,1,1).
\]
Its equivalence to the input's ordinary harmonic coefficients follows by
multiplying finite harmonic sums and removing their diagonal. All these
series converge absolutely at i.

Define, for the proof,
\[
U(w)=\operatorname{Li}_{3,2}(w,1)
-3\log(1-w)\operatorname{Li}_4(w)+3\operatorname{Li}_5(w).
\]
At z=(1+i)/2, 1-z=bar z, so this U is the bracket in (2) before its i*kappa*Li3
completion. The new identity is
\[
\boxed{\mathcal S_5+2\Re U(z)
       =\left(\frac{\pi\ell}{4}-G\right)\mathcal T_3+P_0.}    \tag{8}
\]
No numerical relation is assumed. Sections 3.1-3.3 give an exact finite
iterated-integral certificate for (8).

### 3.1 Word conventions and transformations

Use H_w with letters omega_0=dw/w and omega_1=dw/(1-w), as in the retained
Remiddi-Vermaseren convention [1]. Thus
H_01=Li2, H_001=Li3, H_00101=Li_(3,2), and
\[
S=H_{01101}+H_{01011}+2H_{00111},\quad
U=H_{00101}+3H_1H_{0001}+3H_{00001}.
\]
Products obey the shuffle rule. Reflection includes its full endpoint data:
\[
H_w(1-z)=\sum_{j=0}^{|w|}(-1)^j
 H_{\overline{w_1\cdots w_j}}(z)\,H_{w_{j+1}\cdots w_{|w|}}(1),
\]
where a bar exchanges binary letters, not complex conjugation.
Shuffle-regularized endpoint constants occur only inside this proof; the
final series (1) and every MPL defining S5 are ordinarily convergent.

For phi(z)=z/(z-1), the exact pullback is
\[
\phi^*\omega_0=\omega_0+\omega_1,\qquad
\phi^*\omega_1=-\omega_1.
\]
The words here end in 1, fixing their zero-basepoint values under this
transformation. Along the path to z=(1+i)/2, phi(z) approaches -i without
crossing a singularity, and phi(1-z)=i. These are the standard HPL
transformations and branch conventions [1,2].

### 3.2 The complete finite lower-word identity

At a general argument z define the proof expression
\[
\begin{aligned}
\mathcal L(z)={}&\tfrac12[S(\phi(z))+S(\phi(1-z))]
+U(z)+U(1-z)\\
&+\operatorname{Li}_5(\phi(z))+
  \operatorname{Li}_5(\phi(1-z)).
\end{aligned}
\]
Direct word expansion cancels every independent word of lengths four and five.
For an explicit certificate, set
\[
X=H_0(z),\quad Y=H_1(z),\quad D=H_{01}(z),\quad
T=H_{001}(z),\quad B=H_{011}(z),\quad Z_j=\zeta(j).
\]
The entire surviving polynomial is
\[
\begin{aligned}
\mathcal L={}&-Z_2^2(X/10+2Y/5)+\tfrac72Z_2Z_3-3Z_5\\
&+Z_2\left[X^3/4+3X^2Y/4-XD/2-3XY^2/2+T/2+DY-B-Y^3/3\right]\\
&+Z_3\left[X^2/4+7XY/2-D/2+Y^2/2\right]\\
&+T\left[X^2/4+XY/2+D/2\right]
+B\left[-XY+D/2-Y^2/4\right]\\
&+D\left[-X^3/6-X^2Y/4+XY^2+Y^3/12\right]-D^2Y/2\\
&+X^5/40+X^4Y/8+X^3Y^2/6-5X^2Y^3/12-XY^4/12-Y^5/40.
\end{aligned}                                                   \tag{9}
\]
`word_certificate.py` constructs (9) from the transformations, rather than
assuming its coefficient list, and saves the expanded expression. The retained
shuffle implementation and endpoint table are `word_algebra.py`; its exhaustive
weight-at-most-five product checks are rerun.

### 3.3 Specialization and all constants

At z=(1+i)/2 the retained lower-weight values are
\[
X=-\ell/2+i\pi/4,\quad Y=\ell/2+i\pi/4,
\]
\[
D=5\pi^2/96-\ell^2/8+i(G-\pi\ell/8),
\]
\[
T=-5\pi^2\ell/192+35\zeta(3)/64+\ell^3/48+i\mathcal T_3,
\]
\[
B=-\zeta(2)Y+\zeta(3)-XY^2/2+DY-\overline T.
\]
The last equation is the reflected H001 identity, not a numerical evaluation.
These are the same principal-branch lower-weight reductions used in the
cyclotomic input. Their standard reflection/inversion rules are in [1,3].

Substitution into (9) gives exactly
\[
\Re\mathcal L(z)=
(\pi\ell/4-G)\mathcal T_3+P_0-15\zeta(5)/256.
\]
On the other hand, the elementary phase filter gives
\[
\operatorname{Li}_5(i)+\operatorname{Li}_5(-i)=-15\zeta(5)/256.
\]
Thus the two identical zeta(5) terms cancel and give (8). This proof does not
use Broadhurst's fifth-order ladder identity or an integer-relation fit.

Finally, Re U(z)=K5+kappa*T3. Rearranging (8) yields
\[
\boxed{\mathcal S_5=-2\mathcal K_5-\frac{3\pi^2}{32}\mathcal T_3+P_0.}
                                                               \tag{10}
\]
The term -417792*(-3*pi^2/32)*T3 is +39168*pi^2*T3, which cancels the entire
old -39168*pi^2*T3 contribution. Equation (4) follows.

## 4. A real block form and a direct rigorous tail

Although (1) uses compact complex notation, its evaluator is real rational
arithmetic with rational intervals for pi, ell and G. Write
\[
z^{8r+j}=16^{-r}(a_j+ib_j),\qquad j=1,\ldots,8,
\]
with
\[
(a_j)=(1/2,0,-1/4,-1/4,-1/8,0,1/16,1/16),
\]
\[
(b_j)=(1/2,1/2,1/4,0,-1/8,-1/8,-1/16,0).
\]
Then K5=sum_(r>=0)16^(-r) B_r, where the eight-term real block is
\[
B_r=\sum_{j=1}^8\left[
 a_j\left(\frac{H_{n-1}^{(2)}}{n^3}+\frac{3\ell}{2n^4}+\frac3{n^5}\right)
-b_j\left(\frac\kappa{n^3}+\frac{3\pi}{4n^4}\right)\right],\quad n=8r+j.
\]
The inner range has fixed length eight, not a second infinite index. Terms
are signed; no termwise positivity claim is made.

Elementary bounds 3<pi<22/7, 2/3<ell<7/10, and 0<G<1 give
\[
0<\kappa<1,\quad H_{n-1}^{(2)}<5/3,\quad3\ell/2+3\pi/4<7/2.
\]
The modulus of the coefficient in square brackets in (1) is therefore less
than (5/3+1+7/2+3)/n^3 < 10/n^3.
Since rho=abs(z)=1/sqrt(2), ordinary geometric comparison proves
\[
\boxed{|\mathcal K_5-K_{5,N}|<
\frac{25\,16^{-N}}{(8N+1)^3},\qquad
K_{5,N}=\Re\sum_{n=1}^{8N}(\cdots),\quad N\ge1.}              \tag{11}
\]
Indeed rho^(8N)=16^(-N) and 10*rho/(1-rho)=10(1+sqrt(2))<25.
There is no Euler transform or infinite asymptotic expansion in (11).

## 5. Rational enclosure and separate numerical checks

Each finite block sum is exactly
\[
K_{5,N}=c_0+c_\ell\ell+c_\pi\pi+c_\kappa\kappa,
\]
with four rational coefficients. `certify.py` constructs them using just
H_(n)^(2)=H_(n-1)^(2)+1/n^2 and the eight exact phases. It independently encloses
pi by Machin's formula and alternating arctangents; log2 by
2*sum_(k>=0) 1/((2k+1)3^(2k+1)); and G by the finite Euler expansion of its
positive moment integral int_0^1 (-log t)/(1+t^2)dt. For that constant only,
the finite Euler-kernel remainder is 2^(-M)(1-t^2)^M/(1+t^2), between 0 and
2^(-M). This is separate from the direct new-series tail (11).

All finite operations and endpoints are exact rationals. Constant intervals
are rounded outwards to a 1152-bit dyadic grid. The new series-tail allowance
is then added on both sides, and final endpoints are rounded outwards.

| Eight-term blocks N | Rational interval width for K5 |
|---:|---:|
|32|<8.657e-45|
|64|<3.199e-84|
|128|<3.463e-162|
|192|<8.870e-240|

The intervals are nested and include finite arithmetic uncertainty. The value
begins
\[
\mathcal K_5=0.577637626887494436961493200619981745680248640678162978289251183512\ldots.
\]

`word_certificate.py` passes 42 grouped exact checks; `check_arithmetic.py`
passes 19 additional finite exact checks. They verify phase powers, direct
versus blocked rational coefficient assembly, the finite Euler kernel, signed
interval arithmetic, the full known-polynomial compensation, and preservation
of the three elliptic definitions and source-correction metadata.

Independently, `numerical.py` computes the old S5 through three HPL suffix
systems continued from i/2 to i, and the new fixed-function expression through
a Li_(3,2) power series at z and classical polylogs. At 400 working digits:

- absolute residual of (8): <6.401e-401;
- complete weighted block residual: <2.238e-395;
- new interval midpoint versus the separate fixed-function evaluation:
  <4.882e-242.

These are floating implementation comparisons, not substitutes for the word
proof or rational bounds. The saved even/seventh intervals and primitive
contribution interval are inherited for reassembly. Both forms give
\[
C_6^{\rm rep}(1)=14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]
No new full-C6 interval, physical graph sum, or RG normalization is certified
by this pass. The certificate is for K5linear and the exact representation
change only.

## 6. Reproduction

Python 3, SymPy and mpmath suffice; no network is used by these scripts.

```
python word_certificate.py
python check_arithmetic.py
python certify.py
python numerical.py
```

The unchanged input expression is preserved in inputs/. The active updated
expression, exact word polynomial, interval endpoints, and numerical checks
are in results/. PROVENANCE.json identifies input hashes and retained code.

## Sources and inherited data

[1] E. Remiddi and J. A. M. Vermaseren, *Harmonic Polylogarithms*,
arXiv:hep-ph/9905237. HPL conventions, shuffle products, reflection and fractional
linear transformations: https://arxiv.org/html/hep-ph/9905237

[2] E. Panzer, *Algorithms for the symbolic integration of hyperlogarithms with
applications to Feynman integrals*, arXiv:1403.3385. General iterated-integral
and regularized-word context: https://arxiv.org/html/1403.3385

[3] NIST DLMF 25.12, *Polylogarithms*. Classical series and branch conventions:
https://dlmf.nist.gov/25.12

These references supply general rules, not a published Ising identity. The
specific identity (8), its linear-H2 conversion and full weighted insertion
are the calculation reproduced here. Lower-weight specializations and MZV
endpoint constants are retained from the supplied cyclotomic word algebra.
All physical/graph input qualifications are preserved.
