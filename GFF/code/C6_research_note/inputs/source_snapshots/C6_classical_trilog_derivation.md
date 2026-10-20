# Classical trilogarithm reduction of the weight-three C6 input

## Scope and what is new in this pass

Input: `inputs/flat_expression.json`, the supplied
`C6_flat_harmonic_expression.json`. The normalization is
`r6 = 2187 C6(1)`.

This pass applies a relation **already established in the earlier cyclotomic
notes**, equation (25), to the latest flat-harmonic formula. It is not claimed
as a newly discovered functional equation. The new deliverables are the full
weighted substitution in the current coefficient, its collected polynomial,
and a positive rational geometric representation and exact interval for the
classical trilogarithm.

The weight-three Euler sum D3 is removed from the active formula in favor of
one classical, single-variable trilogarithm. There are still two non-elementary
polylogarithmic inputs (T3 and S5), 18 expanded known monomials, and three
unchanged elliptic quantities. No elliptic residual is eliminated. The explored
integer-beta-moment recurrence does not, by itself, establish a one-index
reduction of the half-shifted coupled primitive; no such reduction is claimed.

The prior source correction and upstream graph/RG identification remain
inherited. The new rational interval certifies T3 only. The numerical C6
reassembly is not a new full-C6 interval calculation.

## 1. The exact replacement

Put

\[
\ell=\log 2,\qquad A=\pi+4\ell,\qquad
Q=\frac{\Gamma(1/4)^4}{\pi},\qquad G=\beta(2),
\]

and define the classical value

\[
\boxed{\mathcal T_3=\Im\operatorname{Li}_3\left(\frac{1+i}{2}\right).}
\tag{1}
\]

The principal classical polylogarithm has its absolutely convergent defining
series at this argument, whose modulus is 1/sqrt(2). Equivalently, directly by
Pochhammer cancellation,

\[
\operatorname{Li}_3(z)=z\,{}_4F_3(1,1,1,1;2,2,2;z),\qquad |z|<1.
\]

Thus this is a finite ordinary one-variable special value, not a newly named
integral or a hidden multiple series.

The old weight-three value obeys

\[
\boxed{
\mathcal D_3=-\mathcal T_3+
\frac{3\pi^3}{128}+\frac{\pi\ell^2}{32}-\frac{G\ell}{2}.
}\tag{2}
\]

This is precisely the previously retained cyclotomic identity, solved for D3.

## 2. Complete insertion in C6

The input formula is

\[
2187C_6(1)=E_H+39168\pi^2\mathcal D_3-417792\mathcal S_5
+\pi^3\mathcal E_c+24\pi^3\mathscr M_7
+192\pi^2\mathscr P_c^{(3)}.
\]

Define

\[
\Delta E=39168\pi^2
\left(\frac{3\pi^3}{128}+\frac{\pi\ell^2}{32}-\frac{G\ell}{2}\right).
\]

Substitution of ell=(A-pi)/4 gives the exact polynomial

\[
\boxed{
\Delta E=
\frac{153}{2}A^2\pi^3-153A\pi^4+\frac{1989}{2}\pi^5
-4896AG\pi^2+4896G\pi^3.
}\tag{3}
\]

The updated full formula is

\[
\boxed{
\begin{aligned}
2187C_6(1)={}&E_{\rm cl}
-13056\bigl(3\pi^2\mathcal T_3+32\mathcal S_5\bigr)\\
&+\pi^3\mathcal E_c+24\pi^3\mathscr M_7
+192\pi^2\mathscr P_c^{(3)},
\end{aligned}}
\tag{4}
\]

where E_cl=E_H+Delta E, namely

\[
\begin{aligned}
E_{\rm cl}={}&\frac Q8\left[
63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)\right]\\
&+Q^2(29\pi-249A)+\mathcal P_{\rm cl},
\end{aligned}
\tag{5}
\]

\[
\boxed{\begin{aligned}
\mathcal P_{\rm cl}={}&
\frac{21}{640}A^5+\frac7{64}A^3\pi^2
+\frac{6045}{64}A^2\pi^3+\frac{7863}{16}A^2\zeta(3)\\
&+96AG(32G-45\pi^2)-\frac{83067}{640}A\pi^4
+5440G\pi^3\\
&+\frac{164927}{128}\pi^5
+\frac{219725}{16}\pi^2\zeta(3)-\frac{805959}{8}\zeta(5).
\end{aligned}}
\tag{6}
\]

The entire Q-dependent block is unchanged. The five altered coefficients are:

| Monomial | Input | Output |
|---|---:|---:|
| A^2 pi^3 | 1149/64 | 6045/64 |
| A G pi^2 | 576 | -4320 |
| A pi^4 | 14853/640 | -83067/640 |
| G pi^3 | 544 | 5440 |
| pi^5 | 37631/128 | 164927/128 |

No A^4*pi, A^2*G*pi, or explicit pi^6 term is reintroduced. The known part
still has 18 monomials. The preserved primitive normalization is
P_a=2*pi^2*PaCubic, so its coefficient remains 192*pi^2.

For completeness, the retained weight-five value is

\[
\boxed{\mathcal S_5=\sum_{r=1}^{\infty}(-1)^r\left[
\frac{H_{2r-1}H_{2r-1}^{(2)}-H_{2r-1}^{(3)}}{4r^2}
+\frac{H_{2r-1}^{\,2}-H_{2r-1}^{(2)}}{8r^3}\right].}
\tag{7}
\]

Here H_N^(j)=sum_{k=1}^N k^(-j), with H_0^(j)=0. Equation (7) and every
elliptic summand, starting index, and source-correction field are copied
unchanged into `results/updated_expression.json`.

## 3. Short branch-tracked proof of (2)

This section rederives the inherited identity; it does not introduce a
new assumed special-value relation.

Let L21(z)=Li_(2,1)(z,1). Its defining series or iterated integral gives

\[
L_{21}'(z)=\frac{\log^2(1-z)}{2z}.
\]

Differentiate the following right-hand side and use its value at z=0 to obtain

\[
\boxed{L_{21}(z)=\zeta(3)-\operatorname{Li}_3(1-z)
+\log(1-z)\operatorname{Li}_2(1-z)
+\frac12\log z\,\log^2(1-z).}
\tag{8}
\]

The identity first holds on 0<z<1, and continues along the path to z=i with
principal logarithms. On that path no relevant cut is crossed. This proof
fixes the additive constant, not merely the derivative.

At z=i, let w=1-i. Then

\[
\log i=\frac{i\pi}{2},\qquad
\log w=\frac\ell2-\frac{i\pi}{4},\qquad
\log(-w)=\frac\ell2+\frac{3i\pi}{4}.
\]

The classical dilogarithm reflection relation gives

\[
\operatorname{Li}_2(i)=-\frac{\pi^2}{48}+iG,
\qquad
\operatorname{Li}_2(w)=\frac{\pi^2}{16}
-i\left(G+\frac{\pi\ell}{4}\right).
\tag{9}
\]

Integrating the standard dilogarithm inversion relation, or specializing the
classical polylogarithm inversion formula, gives

\[
\operatorname{Li}_3(w)-\operatorname{Li}_3(1/w)
=-\frac16\log^3(-w)-\frac{\pi^2}{6}\log(-w).
\tag{10}
\]

The integration constant is zero at w=-1 in the same analytic domain.
Because 1/w=(1+i)/2, its imaginary part is

\[
\Im\operatorname{Li}_3(w)
=\mathcal T_3-\frac{3\pi\ell^2}{32}-\frac{7\pi^3}{128}.
\tag{11}
\]

Finally insert (9)-(11) into (8). Exact collection gives

\[
\Im L_{21}(i)=-\mathcal T_3+
\frac{3\pi^3}{128}+\frac{\pi\ell^2}{32}-\frac{G\ell}{2},
\]

which is (2). No parameter derivative or nonclassical function remains in the
active weight-three definition.

## 4. A positive rational geometric series for T3

For z=(1+i)/2 one has z^8=1/16. The imaginary parts of z^j for j=1,...,8 are

\[
\frac12,\ \frac12,\ \frac14,\ 0,\ -\frac18,\ -\frac18,\ -\frac1{16},\ 0.
\]

Grouping the absolutely convergent classical series into blocks of eight gives

\[
\boxed{\mathcal T_3=\sum_{r=0}^{\infty}16^{-r}b_r,}
\tag{12}
\]

\[
\boxed{\begin{aligned}
b_r={}&\frac1{2(8r+1)^3}+\frac1{2(8r+2)^3}+\frac1{4(8r+3)^3}\\
&-\frac1{8(8r+5)^3}-\frac1{8(8r+6)^3}-\frac1{16(8r+7)^3}.
\end{aligned}}
\tag{13}
\]

For a>0 and c>0,

\[
f_c(a)=\frac{c}{a^3}-\frac{c}{4(a+4)^3}>0,
\quad f_c'(a)=-\frac{3c}{a^4}+\frac{3c}{4(a+4)^4}<0.
\]

The block is the sum of f_(1/2)(8r+1), f_(1/2)(8r+2), and
f_(1/4)(8r+3). Thus b_r is strictly positive and decreasing, and

\[
0<b_r<\frac{5}{4(8r+1)^3}.
\]

Let T3_N=sum_{r=0}^{N-1}16^(-r)b_r. For every integer N>=1,

\[
\boxed{0<\mathcal T_3-T_{3,N}
<\frac{16}{15}\,16^{-N}b_N
<\frac43\frac{16^{-N}}{(8N+1)^3}.}
\tag{14}
\]

This is an ordinary positive partial sum with a geometric tail bound. It needs
no Euler transform, numerical quadrature, gamma value, harmonic number, or
initial transcendental constant. Finite partial sums and endpoints are exact
rational numbers.

The newly computed exact intervals are nested:

| Complete blocks N | Interval width |
|---:|---:|
| 32 | <1.742e-46 |
| 64 | <6.416e-86 |
| 128 | <6.937e-164 |

The exact numerators and denominators are in `results/T3_intervals.json`.

\[
\mathcal T_3=
0.57007740708876897819560975759007455106314580991872873286697047901592967\ldots.
\]

These enclosures certify the defined classical value, not the upstream Ising
coefficient.

## 5. Executed checks and inherited quantities

`reduce.py` checks the imaginary branch constants and the weighted substitution
with exact symbolic algebra. It also checks exact phase blocks, bound
comparisons, nesting, and preservation of the source correction and all three
elliptic definitions. The implementation includes two floating comparisons in
its overall check count; `results/checks.json` labels them explicitly.

At 220 decimal digits of working precision:

* A freshly generated 512-term rational Euler approximant for D3 differs from
  the classical replacement by 2.162e-155, smaller than its retained analytic
  bound 64*2^(-512) = 4.774e-153.
* Independent quadrature of (1/2)int_0^1 log^2(1-i*t)/t dt checks the defining
  L21(i), with imaginary-part residual below 5.534e-222.
* Using the preceding certified D3 midpoint, the old and new complete
  known-plus-polylogarithmic blocks differ by less than 9.283e-215.

The quadrature and high-precision comparisons are floating-point checks, not
interval proofs. The functional argument in Section 3 establishes the identity;
Section 4 separately certifies the new T3 value.

The unchanged even and seventh-sector values and primitive contribution are
read from their supplied interval certificates. Reassembly using their
midpoints gives

\[
C_6^{\rm rep}(1)=
14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]

The source correction is not added again. The graph/RG identification and all
previous elliptic transformations are retained assumptions. No numerical value
of the complete coefficient is used to determine any coefficient here.

## Reproduction

Python 3 with SymPy and mpmath suffices:

```text
python reduce.py
```

This regenerates the active expression, exact rational T3 intervals, finite
checks, numerical cross-checks, and provenance information. No network access
is used by the script.

## Sources and provenance

1. Supplied `C6_flat_harmonic_expression.json` and
   `C6_flat_harmonic_derivation.md`: current full formula, S5, and inherited
   elliptic definitions.
2. Supplied `C6_cyclotomic_derivation.md`, equation (25): the existing classical
   trilogarithm identity used in this pass. A copy is included under inputs/.
3. NIST Digital Library of Mathematical Functions, Section 25.12, especially
   equations 25.12.4, 25.12.6, 25.12.10, and 25.12.13:
   https://dlmf.nist.gov/25.12 . Classical definitions, reflection and inversion.
4. E. Remiddi and J. A. M. Vermaseren, *Harmonic Polylogarithms*,
   arXiv:hep-ph/9905237: https://arxiv.org/html/hep-ph/9905237 .
   Iterated-integral and differential conventions for L21.

The application (3)-(6), rational grouping (12)-(13), and interval construction
are supplied explicitly here; no priority claim is made for the elementary
phase grouping.
