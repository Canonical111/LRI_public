# C6(1): the entire seventh-power sector in two fixed values

## Result and scope

The input is `inputs/previous_expression.json`, copied from
`C6_seventh_cubic_quartic_expression.json`. It has twelve fixed function values,
five of which describe the seventh sector. The present calculation replaces
those five Kampé de Fériet values by ONE ordinary Meijer G and ONE bivariate Fox H.
The complete coefficient therefore has nine fixed values. The polynomial and
all other completed blocks are unchanged.

This is a finite representation reduction, not an elementary summation,
arithmetic-independence theorem, or a new identification of the physical six-loop
coefficient. The project-specific identity of the complete seventh sector with
its central-binomial series is inherited from
`inputs/central_seventh_derivation.md`. The new residue calculation below matches
the complete polynomial of that series, including its n=0 term and ordinary
corrections. The former three polynomial root problems are no longer needed in
the seventh sector. The primitive's separate parameter specification is unchanged.

There is a function-class tradeoff. The new bivariate H has one shared slope
pair (2,1), rather than only unit slopes. Its second argument is -1, with
Log(-1)=i*pi. Absolute convergence on the explicitly supplied contours is proved
below. No unevaluated integral, derivative, regulator, or residual series occurs
in the final fixed-value formula. Integrals and series in this derivation are
proof or numerical-verification devices.

## 1. The two-value answer

Put A=pi+4 log(2), and define
\[
a_7=259A-49\pi,\qquad b_7=481A-539\pi,\qquad c_7=407A-1127\pi,
\]
where c_7 here is a quadratic coefficient, NOT the old shorthand cos(pi/8)^7.
Set
\[
\Delta_7=\sqrt{b_7^2-4a_7c_7},\qquad
\rho_7=\sqrt{(a_7-c_7)^2+b_7^2},
\]
\[
\eta_\pm=\frac1\pi\arctan\frac{b_7\pm\Delta_7}{2a_7},\qquad
\beta=\frac1\pi\arctan\frac{13+i\sqrt{139}}{14}.
\]
All square roots displayed above are positive real roots. The inverse tangents
for eta are real principal values; the complex inverse tangent for beta is
principal. The conjugate of beta supplies the other local parameter. The
constants obey a_7>0, b_7>0, c_7<0. Thus Delta_7 is positive, and eta_+ and eta_-
are real with opposite signs. These signs follow, for example, from
2/3<log(2)<7/10 and 3<pi<22/7. No parameter is fitted to a period value.

Define
\[
\boxed{\mathcal G_7=G_{10,10}^{3,8}\!\left(
1\;\middle|\;\begin{matrix}-\tfrac14,(\tfrac12)^{[7]},\eta_+,\eta_-\\
0^{[7]},\tfrac34,\eta_+,\eta_-\end{matrix}\right).}
\tag{1}
\]
The ordered upper list has eight numerator entries; the ordered lower list has
three numerator entries. In the standard inverse-Mellin convention its kernel is
\[
N_7(s)=\frac{\Gamma(s)^3\Gamma(\tfrac12-s)^7\Gamma(\tfrac54-s)}
{\Gamma(1-s)^4\Gamma(\tfrac14-s)
\Gamma(s+\eta_+)\Gamma(1-s-\eta_+)
\Gamma(s+\eta_-)\Gamma(1-s-\eta_-)}.
\tag{2}
\]

For the second value use the same standard bivariate H convention as the input.
Let
\[
\mathbf a=((-\tfrac14,1),(\tfrac12,1)^{[7]},(\beta,1),(\bar\beta,1)),
\]
\[
\mathbf b=((0,1)^{[6]},(1,1),(\tfrac34,1),(\beta,1),(\bar\beta,1)).
\]
Then
\[
\boxed{\mathcal H_7=
H_{1,1;\,10,10;\,2,2}^{0,1;\,3,8;\,1,2}
\!\left[\begin{matrix}
(0;2,1):\mathbf a;(0,1),(0,1)\\
(-1;2,1):\mathbf b;(0,1),(-1,1)
\end{matrix}\;\middle|\;1,-1\right].}
\tag{3}
\]
The first local numerator counts are n=8 upper and m=3 lower. The second local
counts are n=2 upper and m=1 lower. The shared counts are n=1 upper and m=0 lower.

For an unambiguous independent specification of the convention, its kernel is
\[
A_7(s)\frac{\Gamma(t)\Gamma(1-t)^2}{\Gamma(2-t)}
\frac{\Gamma(1-2s-t)}{\Gamma(2-2s-t)}e^{-i\pi t},
\tag{4}
\]
where
\[
A_7(s)=\frac{\Gamma(s)^3\Gamma(\tfrac12-s)^7\Gamma(\tfrac54-s)}
{\Gamma(1-s)^3\Gamma(-s)\Gamma(\tfrac14-s)
 \Gamma(s+\beta)\Gamma(1-s-\beta)
 \Gamma(s+\bar\beta)\Gamma(1-s-\bar\beta)}.
\tag{5}
\]
The upward lines Re(s)=1/4 and Re(t)=1/8 use the usual measure
 ds dt/(2 pi i)^2. The phase in (4) is exactly the named function's
(-1)^(-t) factor, not an additional operation applied afterward.

With B_7 denoting the COMPLETE seventh contribution in r6=2187 C6 units,
\[
\boxed{B_7=24\pi^{3/2}
 [\rho_7\mathcal G_7+392\sqrt{185}\,\mathcal H_7].}
\tag{6}
\]
Equivalently the old central value satisfies
\[
\boxed{\mathscr M_7=
\frac{\rho_7\mathcal G_7+392\sqrt{185}\,\mathcal H_7}{\pi^{3/2}}.}
\tag{7}
\]
No term is removed from the zero mode and no polynomial compensation is added.

## 2. Match the complete central coefficient by residues

This is the core calculation. It starts from the retained exact identity
B_7=24 pi^3 M7, not from a numerical value of B_7.

For the proof put
\[
a_n=(1/2)_n/n!,\quad y_n=n+1/4,\quad
h_n=\log2+H_n-H_{2n},\quad
\delta_n=\pi^2/3-4H_{2n}^{(2)}+2H_n^{(2)}.
\]
The source defines
\[
u_n=1-14y_nh_n,\quad
v_n=196y_nh_n^2-28h_n+7y_n(\delta_n-\pi^2),
\]
\[
T_n=80\pi^2y_n-26\pi u_n+11v_n,\quad
K_n=28\pi^2y_n-10\pi u_n+3v_n,
\]
\[
\begin{split}
F_n={}&(98H_{2n}+74\log2-6\pi)T_n-98\pi K_n\\
&-98(11u_n-13\pi y_n)(\pi^2/3+4H_{2n}^{(2)})
-8624y_n[\zeta(3)-H_{2n}^{(3)}],
\end{split}
\]
and M7=sum (-1)^n a_n^7 F_n, including n=0.

Let
\[
Y(s)=1/4-s,\quad R(s)=\left[\frac{\Gamma(s)}{\Gamma(s+1/2)}\right]^7,
\quad z(s)=\tan(\pi s),
\]
\[
M_j(s)=Y(s)R(s)\sec(\pi s)z(s)^{7-j},\qquad j=1,2,3.
\]
Near s=-n+epsilon, recurrence and polygamma values give
\[
\frac{\Gamma(-n+\epsilon)}{\Gamma(1/2-n+\epsilon)}
=\frac{a_n}{\sqrt\pi\epsilon}
 \exp\left[2h_n\epsilon+
 \tfrac12(\delta_n-2\pi^2/3)\epsilon^2+O(\epsilon^3)\right].
\]
Together with the tangent/secant expansions this gives the following residues,
with the common factor (-1)^n a_n^7 omitted:
\[
\begin{array}{c|l}
M_1&\pi^{5/2}y_n\\
M_2&\pi^{3/2}(14y_nh_n-1)\\
M_3&\sqrt\pi\,[y_n(98h_n^2+7\delta_n/2-\pi^2/2)-14h_n].
\end{array}
\tag{8}
\]

Use the SINGLE digamma insertion
\[
\Psi(s)=\psi(1-2s)+\gamma_{\mathrm E}.
\]
At the same poles,
\[
\Psi(-n)=H_{2n},\qquad
\Psi'(-n)=2H_{2n}^{(2)}-\pi^2/3,\qquad
\Psi''(-n)=-8[\zeta(3)-H_{2n}^{(3)}].
\tag{9}
\]
These are ordinary integer polygamma formulas. Euler's constant occurs only in
this proof; it is absent from (1)-(7).

Let
\[
p(z)=7z^2+13z+11,\qquad q_A(z)=a_7z^2+b_7z+c_7.
\]
Define the proof kernel
\[
I(s)=Y(s)R(s)\sec(\pi s)z(s)^4
 [196p(z(s))\Psi(s)+q_A(z(s))].
\tag{10}
\]
Substitution of (8)-(9) gives the exact polynomial identity
\[
\boxed{\operatorname{Res}_{s=-n} I(s)
=\sqrt\pi\,(-1)^n a_n^7 F_n.}
\tag{11}
\]
The verifier checks (11) with h, delta, H_(2n), H_(2n)^(2), H_(2n)^(3), y,
pi, log(2), and zeta(3) treated as independent symbols. The equality includes
the whole source polynomial, not only its cubic or logarithmic part.

### No omitted negative half-integer poles

The ratio R(s) has a zero of order seven at s=-n-1/2. In M_j, tangent and secant
remove only 8-j of these orders, leaving a net zero of order j-1, which is
nonnegative for j=1,2,3. The insertion Psi is analytic at these points.
Therefore the only poles to the left of Re(s)=1/4 are the integer poles used
in (11). This check is important: using an additional tangent power would
introduce an unwanted second pole family.

On s=1/4+iu, the kernels are O((1+|u|)^(-5/2) exp(-pi |u|)), with an additional
logarithm for Psi. On the lines Re(s)=-N-1/4, reflection rewrites the gamma ratio
using Gamma(1/2-s)/Gamma(1-s), giving a uniform O(N^(-5/2) log(N+2)) bound on the
vertical integral. Horizontal boundaries vanish exponentially. Closing left is
therefore justified and yields
\[
\mathscr M_7=\pi^{-1/2}\mathcal B[I],
\tag{12}
\]
where B is the usual upward Barnes contour on Re(s)=1/4.

## 3. Factor the two quadratics into gamma quotients

The branch choices in Section 1 give, for complex theta away from poles,
\[
p(\tan\theta)=\sqrt{185}
\frac{\sin(\theta+\pi\beta)\sin(\theta+\pi\bar\beta)}{\cos^2\theta},
\]
\[
q_A(\tan\theta)=\rho_7
\frac{\sin(\theta+\pi\eta_+)\sin(\theta+\pi\eta_-)}{\cos^2\theta}.
\tag{13}
\]
For example tan(pi beta)+tan(pi betabar)=13/7 and their product is 11/7.
Also 49(1+tan(pi beta)^2)(1+tan(pi betabar)^2)=185. For the other pair the sum
and product are b_7/a_7 and c_7/a_7, while the normalizing square is
(a_7-c_7)^2+b_7^2. Principal cosines give the positive normalizations in (13).

Using gamma reflection, define
\[
N_p(s)=\frac{\Gamma(s)^3\Gamma(1/2-s)^7\Gamma(5/4-s)}
{\Gamma(1-s)^4\Gamma(1/4-s)
 \Gamma(s+\beta)\Gamma(1-s-\beta)
 \Gamma(s+\bar\beta)\Gamma(1-s-\bar\beta)}.
\]
Then
\[
YR\sec(\pi s)z^4p(z)=\frac{\sqrt{185}}{\pi}N_p(s),\qquad
YR\sec(\pi s)z^4q_A(z)=\frac{\rho_7}{\pi}N_7(s),
\tag{14}
\]
and A_7(s)=(-s)N_p(s), since Gamma(1-s)/Gamma(-s)=-s.

## 4. The inner Barnes identity removes the digamma

On Re(s)=1/4, use the upward t-contour Re(t)=1/8. Then
\[
\boxed{
\frac{1}{2\pi i}\int
 \frac{\Gamma(t)\Gamma(1-t)^2}{\Gamma(2-t)}
 \frac{\Gamma(1-2s-t)}{\Gamma(2-2s-t)}e^{-i\pi t}\,dt
 =\frac{\psi(1-2s)+\gamma_{\mathrm E}}{-2s}.}
\tag{15}
\]
The left side reduces to Gamma(t)Gamma(1-t)e^(-i pi t) divided by
(1-t)(1-2s-t). Its residue at t=-k is
1/[(k+1)(k+1-2s)]: the (-1)^k gamma residue and phase cancel.
The resulting absolutely convergent partial fraction expansion is exactly
the digamma difference on the right. Closing the contour is justified by the
quadratic rational decay in the undamped direction and exponential decay in
the other direction.

By (14)-(15),
\[
\mathcal B[YR\sec(\pi s)z^4p(z)\Psi(s)]
 =\frac{2\sqrt{185}}{\pi}\mathcal H_7,
\]
while
\[
\mathcal B[YR\sec(\pi s)z^4q_A(z)]
 =\frac{\rho_7}{\pi}\mathcal G_7.
\]
Together with (10)-(12), these prove (7), and multiplication by 24 pi^3 gives (6).

### Absolute convergence of the bivariate value

Write s=1/4+iu and t=1/8+iv. The phase-normalized gamma pair satisfies
\[
\Gamma(t)\Gamma(1-t)e^{-i\pi t}
=\frac{2\pi i}{e^{2\pi i t}-1},
\]
whose modulus is uniformly bounded on this t-line. The two reciprocal factors
are bounded by a constant times
\[
\frac{1}{\sqrt{(7/8)^2+v^2}\sqrt{(3/8)^2+(v+2u)^2}}.
\]
Cauchy--Schwarz gives a uniform bound for its integral over v, because both
factors have finite L2 norm and translation preserves that norm. Meanwhile
A_7(1/4+iu)=O((1+|u|)^(-3/2) exp(-pi|u|)). The double integral is therefore
absolutely convergent. Fubini and the inner evaluation are justified.

The value H7 is real: after (15), the outer integrand has conjugation symmetry
about the real axis. It is negative for this specialization; no positivity of
its terms or gamma kernel is claimed.

## 5. Effect on the complete coefficient

Replace the old entire seventh block by (6). The full r6 expression is
\[
\begin{split}
2187C_6(1)={}&E+B_{\rm pol}+B_{\rm low}+B_6+B_8
-393\pi\sqrt{89}\,\mathcal H_W\\
&+24\pi^{3/2}[\rho_7\mathcal G_7+392\sqrt{185}\,\mathcal H_7]
+7680\pi^3\mathcal H_*.
\end{split}
\]
The known polynomial changes by ZERO. The old eighth-shifted gamma prefactors,
five KdF values, cubic/quartic root lists, and finite sum over r all disappear
from the active seventh sector. The old ordinary corrections have already been
included through the inherited whole-sector identity, so they are not added again.

There are now 2 multiple polylogarithms, 4 univariate Meijer G values, and 3
bivariate H values: nine in total. This counts fixed function occurrences, not
independent periods. For the seventh sector, 184 listed parameter entries are
replaced by 46 (20 in G7 and 26 in H7, including the two shared triples as two
parameter entries). Four nonrational shifts beta, betabar, eta_+, eta_- are
explicit. No cubic/quartic root solve remains there.

## 6. Executed checks

`build_and_verify.py` performs 47 finite algebra and preservation checks.
They include the entire residue polynomial, the two quadratic factorizations,
the gamma-parameter lists, and preservation of the complete non-seventh part.
These finite checks are distinct from the analytic contour arguments above.

Numerical runs at 45 and 80 working decimal digits evaluate G7 through its own
gamma kernel. H7 is evaluated through its own outer gamma kernel after the
proved inner identity (15); it is NOT an independent full two-dimensional
Barnes quadrature. Equation (15) itself is independently checked by direct
inner contour quadrature at three real/complex values of s.

The result at 80 working digits is
\[
\mathcal H_7=-20.3592096499389453929959323140757688864992885581631049981858593\ldots,
\]
\[
\mathcal G_7=8.38817429186383748625482510888136818661142660132305061025074452\ldots.
\]
The seventh block is
\[
B_7=-11409730.0218929304085601825903095181136335477966342266598942108\ldots.
\]
The discrepancy from a separately formed central Euler sum is about 1.239e-73;
the discrepancy from the original five shifted gamma/harmonic sums is about
3.007e-73. These are FLOATING-POINT checks, not interval certificates. Euler
partial-sum errors are not silently treated as zero. No new full-C6 evaluation,
new upstream graph/RG proof, or Wolfram-kernel execution is claimed.

## References and inherited inputs

1. `inputs/previous_expression.json`: latest twelve-value expression, known
   polynomial, source correction, and unchanged standard-function conventions.
2. `inputs/central_seventh_derivation.md`, equations (1)-(3): inherited identity
   for the entire seventh sector and the explicit central coefficient F_n.
3. NIST DLMF 5.5: gamma recurrence and reflection; https://dlmf.nist.gov/5.5 .
4. NIST DLMF 5.15: integer and half-integer polygamma identities;
   https://dlmf.nist.gov/5.15 .
5. NIST DLMF 5.11: gamma-ratio asymptotics; https://dlmf.nist.gov/5.11 .
6. NIST DLMF 16.17: ordinary Meijer G convention; https://dlmf.nist.gov/16.17 .
7. The bivariate convention is the same one already fixed by the input, based
   on Andrade--Rathie--Farias, Definition B, DOI 10.1007/s40314-017-0451-z.
   The kernels (4)-(5) independently fix every normalization and branch here.

The standard references supply function conventions and identities, not this
C6-specific seventh-sector reduction.
