# C6(1): replace the custom polylogarithmic sum by standard single-valued HPLs

## Result and scope

Input: the supplied `C6_linear_geometric_expression.json`, copied unchanged to
`inputs/linear_geometric_expression.json`. The normalization remains
`r6 = 2187 C6(1)`.

The previous active formula contained four project-specific series when its
polylogarithmic and elliptic sectors are counted together: K5linear, Ecentral,
M7central and PaCubic. This continuation removes K5linear from the active
formula and replaces it by two standard function values:

- Brown's single-valued harmonic polylogarithm with word (0,1,1,1,0), at i;
- the ordinary classical trilogarithm at (1+i)/2.

The standard SVHPL is NOT defined by assigning a new name to K5. It is the
function fixed independently by Brown's single-valued construction, in the
normalization of Dixon-Duhr-Pennington [1, equations (3.15)-(3.16) and
(3.23)-(3.30)]. An exact finite word calculation relates it to the input.

There are now THREE project-specific series, all in the unchanged elliptic
sector. No elliptic sum has been evaluated in ordinary gamma/hypergeometric
constants. No arithmetic-independence, minimality, or new graph/RG claim is
made. The standard SVHPL is a nonclassical polylogarithm, not an ordinary pFq.
The polynomial has 20 expanded monomials instead of 21.

## 1. Complete updated coefficient

Put
\[
\ell=\log2,\qquad z=\frac{1+i}{2},\qquad
A=\pi+4\ell,\qquad Q=\frac{\Gamma(1/4)^4}{\pi},\qquad G=\beta(2).
\]
The new active formula is
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_{\rm sv}
+13056\left[16\Re\mathcal L_{0,1,1,1,0}(i)
 +(32G-3\pi^2)\Im\operatorname{Li}_3(z)\right]\\
&+\pi^3\mathcal E_{\rm c}+24\pi^3\mathscr M_7
 +192\pi^2\mathscr P_{\rm c}^{(3)}.
\end{aligned}}                                                     \tag{1}
\]
Here \(\mathcal L_w\) is the STANDARD Brown single-valued HPL, not one of the
previous custom sums. The elliptic definitions and the normalization
\(P_a=2\pi^2\mathscr P_{\rm c}^{(3)}\) are unchanged.

The entire known part is
\[
\boxed{\begin{aligned}
E_{\rm sv}={}&\frac Q8[63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)]\\
&+Q^2(29\pi-249A)+\mathcal P_{\rm sv},
\end{aligned}}                                                     \tag{2}
\]
where
\[
\boxed{\begin{aligned}
\mathcal P_{\rm sv}={}&\frac{21}{640}A^5+\frac7{64}A^3\pi^2
 +\frac{6045}{64}A^2\pi^3+\frac{7863}{16}A^2\zeta(3)\\
&-\frac{83067}{640}A\pi^4+\frac{164927}{128}\pi^5
 +\frac{4301}{16}\pi^2\zeta(3)-\frac{805959}{8}\zeta(5)\\
&+3072G^2(18A-17\pi)
 -48\pi G(17A^2+56A\pi+153\pi^2).
\end{aligned}}                                                     \tag{3}
\]
The Q-dependent block is exactly unchanged. The old A^4*pi and A*pi*zeta(3)
monomials vanish; G^2*pi appears, so the net count is 21 -> 20. No pi^6 term
is introduced.

## 2. The exact replacement for K5

Only in this proof write
\[
V=\Re\mathcal L_{0,1,1,1,0}(i),\qquad
J=\Im\operatorname{Li}_3((1+i)/2).
\]
These are shorthand for standard functions, not new defining series.

The identity is
\[
\boxed{\mathcal K_5=\frac14V+
 \left(\frac G2-\frac{3\pi^2}{64}\right)J+P_{\rm sv},}             \tag{4}
\]
with the fully elementary compensation
\[
\boxed{\begin{aligned}
P_{\rm sv}={}&\frac14G^2\ell-\frac{163}{512}\zeta(3)\ell^2
 +\frac{815}{6144}\pi^2\zeta(3)-\frac{753}{512}\zeta(5)\\
&-\frac{13}{3840}\ell^5+\frac{35}{4608}\pi^2\ell^3
 +\frac{1001}{184320}\pi^4\ell.
\end{aligned}}                                                     \tag{5}
\]
Consequently
\[
E_{\rm sv}=E_{\rm geo}+835584P_{\rm sv}.                           \tag{6}
\]
There is no change of a sum's lower index, no extracted elliptic zero-index
term, and no new physical contribution in (6).

## 3. Standard normalization and finite HPL expansion

Use HPL letters \(\omega_0=dw/w\), \(\omega_1=dw/(1-w)\), so
\(H_0=\log w\), \(H_1=-\log(1-w)\), \(H_{01}=\operatorname{Li}_2(w)\),
\(H_{011}=\operatorname{Li}_{2,1}(w,1)\). These are the
Remiddi-Vermaseren conventions [2]. A bar in this section is complex
conjugation at the SAME argument: \(\bar H_u=H_u(\bar w)\).

Brown's normalization is fixed by single-valuedness, the differential rules
\[
\partial_w\mathcal L_{0u}=\mathcal L_u/w,\qquad
\partial_w\mathcal L_{1u}=\mathcal L_u/(1-w),
\]
and \(\mathcal L_{0^n}=\log^n|w|^2/n!\), while words not consisting only of
zeros tend to zero at w=0. The standard construction and these normalizations
are given in [1].

For the particular word needed here its finite expansion is
\[
\boxed{\begin{aligned}
\mathcal L_{01110}(w)={}&H_{01110}+\bar H_{01110}
 +H_0\bar H_{0111}+H_{0111}\bar H_0\\
&+H_{01}\bar H_{011}+H_{011}\bar H_{01}\\
&+2\zeta(3)\left(H_0\bar H_1+\bar H_{10}-\bar H_{01}\right).
\end{aligned}}                                                     \tag{7}
\]
This is a finite expansion of the PUBLISHED function, not a project-specific
infinite-sum definition.

### 3.1 Check the single-valued completion, including its zeta term

The standard generating construction is
\[
\mathcal L(w)=L_X(w)\widetilde L_Y(\bar w),\qquad
L_X(w)=\sum_u H_u(w)u,
\]
where the tilde reverses words, and the alphabets satisfy
\[
y_0=x_0,\qquad
\widetilde Z(Y)y_1\widetilde Z(Y)^{-1}=Z(X)^{-1}x_1Z(X).
\]
These formulas are [1, equations (3.23)-(3.30)]. The finite calculation in
`verify.py` works through word length five. It obtains
\[
\begin{aligned}
y_1=x_1+\zeta(3)\big(&-2x_{0011}+4x_{0101}-2x_{0111}-4x_{1010}\\
&+6x_{1011}+2x_{1100}-6x_{1101}+2x_{1110}\big)
\end{aligned}
\]
through that order, with no length-five correction. Here x_u denotes
concatenation. The length-four coefficients agree with [1, equation (3.25)].
The coefficient of x_01110 in the full product is (7).

The final line in (7) is essential. Leaving it out shifts the real value at i
by \(\pi^2\zeta(3)/12\). The verifier derives it from the associator rather
than adjusting it to numerical data.

## 4. A unit-circle identity with a short proof

Temporarily put
\[
S(w)=H_{01101}(w)+H_{01011}(w)+2H_{00111}(w).
\]
At w=i, its real part is the S5 of the preceding flat-harmonic representation.
This relation is an inherited identification, also reproduced in the latest
linear-geometric proof.

The required shuffle is
\[
H_0H_{0111}=H_{01110}+H_{01101}+H_{01011}+2H_{00111}.
\]
Thus \(H_{01110}=H_0H_{0111}-S\). Also
\(H_{10}=H_0H_1-H_{01}\).

For \(|w|=1\), away from w=1 and continued on consistent principal branches,
\(H_0+\bar H_0=0\). Taking real parts of (7) therefore gives
\[
\boxed{\Re\mathcal L_{01110}(w)
=-2\Re S(w)
+2\Re\left[\operatorname{Li}_2(w)\overline{\operatorname{Li}_{2,1}(w,1)}\right]
-4\zeta(3)\Re\operatorname{Li}_2(w).}                              \tag{8}
\]
Every operation is finite shuffle algebra; no relation on numerical values is
assumed.

At w=i the lower-weight inputs are
\[
\operatorname{Li}_2(i)=-\frac{\pi^2}{48}+iG,
\quad
\operatorname{Li}_{2,1}(i,1)=\frac{29}{64}\zeta(3)-\frac{\pi G}{4}+iD_3.
\]
The real-part evaluation of Li21(i) was proved in the supplied flat-harmonic
notes (their Section 3.1). Substitution into (8) yields
\[
\boxed{V=-2S_5+2GD_3+\frac{G\pi^3}{96}
 +\frac{33}{512}\pi^2\zeta(3).}                                  \tag{9}
\]

## 5. Match (9) to the latest expression

The two previously established identities are
\[
D_3=-J+\frac{3\pi^3}{128}+\frac{\pi\ell^2}{32}-\frac{G\ell}{2},
\]
and
\[
S_5=-2\mathcal K_5-\frac{3\pi^2}{32}J+P_0,
\]
where the latest input defines
\[
\begin{aligned}
P_0={}&\frac{G\pi\ell^2}{32}+\frac{11G\pi^3}{384}
 -\frac{163}{256}\zeta(3)\ell^2+\frac{457}{1536}\pi^2\zeta(3)
 -\frac{753}{256}\zeta(5)\\
&-\frac{13}{1920}\ell^5+\frac{35}{2304}\pi^2\ell^3
 +\frac{1001}{92160}\pi^4\ell.
\end{aligned}
\]
Insert these in (9) and solve for K5. The G*pi*ell^2 and G*pi^3 terms cancel
from the compensation, leaving exactly (4)-(5). Multiplying by 835584 gives
(1) and (6). `verify.py` checks the full polynomial, not selected coefficients.

This proof uses the inherited K5/S5 and D3 identities. It does not silently
rederive or independently validate the entire earlier polylogarithm reduction.

## 6. Numerical checks and reproducibility

`verify.py` performs 27 grouped exact checks: the finite associator, the full
Brown word expansion, both shuffles, the unit-circle identity, its i
specialization, the inherited-identity substitution, the full weighted
coefficient, the polynomial, and preservation of the elliptic definitions and
source correction. These are implementation checks, not 27 independent new
theorems.

`numerical.py` evaluates the Brown function from its own finite HPL construction.
The HPL values are initialized by ordinary convergent multiple-polylogarithm
series at i/2 and continued by their differential equations to 3i/4 and i.
Separately, K5 is evaluated from the original linear-H2 geometric series at
(1+i)/2. No K5 value is used as an input to the Brown evaluation.

The standard value is
\[
\Re\mathcal L_{01110}(i)=
0.715776934357249324419788645513667108831028834320188680791756354594468254110200646913826390974\ldots.
\]
The classical value is
\[
\Im\operatorname{Li}_3((1+i)/2)=
0.570077407088768978195609757590074551063145809918728732866970479015929673943275771736170548514\ldots.
\]
At 210 working decimal digits (requested check precision 180), the absolute
residual in (4) is below 5.704e-211. The residual in the complete weighted
replacement is below 5.732e-205. These are FLOATING checks, not new certified
error enclosures.

Using the inherited intervals for the three unchanged elliptic inputs only as
midpoints, the new expression reassembles to
\[
C_6^{\rm rep}(1)=14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]
Only the displayed prefix is intended as an assembly check. More working
digits in the report do not increase the precision of the inherited inputs.

Run, without network access:

```text
python formula.py
python verify.py
python numerical.py 100
python numerical.py 180
```

The updated expression retains historical definitions for provenance. Its
active formula and term lists are the new standard-function form; the old
series definitions in legacy sections do not count as active inputs.

## References and inherited inputs

[1] L. J. Dixon, C. Duhr, J. Pennington, *Single-valued harmonic polylogarithms
and the multi-Regge limit*, arXiv:1207.0186, Section 3.2-3.3, especially equations
(3.15)-(3.16), (3.23)-(3.30).
https://arxiv.org/html/1207.0186

[2] E. Remiddi, J. A. M. Vermaseren, *Harmonic Polylogarithms*,
arXiv:hep-ph/9905237, definitions and shuffle algebra.
https://arxiv.org/html/hep-ph/9905237

[3] NIST DLMF, Section 25.12, classical polylogarithm conventions.
https://dlmf.nist.gov/25.12

[4] Supplied `C6_linear_geometric_derivation.md` and expression JSON: current
K5 expression, its relation to S5, P0, and all elliptic inputs.

[5] Supplied `C6_flat_harmonic_derivation.md`, Section 3.1: Re Li21(i) value.
Supplied `C6_classical_trilog_derivation.md`: D3 to classical trilogarithm.

No reference above is presented as an independent derivation of the Ising
six-loop graph/RG coefficient.
