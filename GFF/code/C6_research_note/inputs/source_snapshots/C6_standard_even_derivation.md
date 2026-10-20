# C6(1): a standard Kampé de Fériet representation of the even sector

## Result and scope

Input: `inputs/svhpl_expression.json`, the supplied
`C6_standard_svhpl_expression.json`. The normalization is
`r6 = 2187 C6(1)`.

The single bespoke even-sector definition Ecentral can be replaced by EIGHT
ordinary generalized hypergeometric values and TWO fixed values of the
classical Kampé de Fériet function. The active bespoke series are then only
M7central and PaCubic. All parameters of the newly specified hypergeometric
values are positive rational numbers; all arguments are 1 or (1,1).

This is a derivative-free **conversion to a standard two-variable function
class**, not an evaluation in fewer ordinary one-variable constants, a theorem
about period independence, or a reduction in the total number of function
values. In particular, it partially reverses the earlier consolidation of
ordinary periods into Ecentral. The standard-function list grows. Literal
triangular summation of the new double series is also slower than the old
one-index delta series. These tradeoffs are part of the result.

The previous two standard polylogarithm terms, the complete M7 and cubic
primitive definitions, source repair, and upstream graph/RG identification
remain inherited. No new physical six-loop verification is made.

## 1. Standard function convention and two fixed values

Use the classical complex-variable Kampé de Fériet convention in [1,
Introduction], NOT the finite-field analogue developed later in that paper:

\[
F_{a':b';c'}^{a:b;c}\!\left[
\begin{matrix}\boldsymbol\alpha:\boldsymbol\beta;\boldsymbol\gamma\\
\boldsymbol\alpha':\boldsymbol\beta';\boldsymbol\gamma'
\end{matrix};x,y\right]
=\sum_{m,n\ge0}
\frac{(\boldsymbol\alpha)_{m+n}(\boldsymbol\beta)_m(\boldsymbol\gamma)_n}
{(\boldsymbol\alpha')_{m+n}(\boldsymbol\beta')_m(\boldsymbol\gamma')_n}
\frac{x^m y^n}{m!n!}.
\]

The six indices specify the lengths of the six parameter lists. A list
Pochhammer symbol means the product of its entries. Empty products equal one.
A superscript [j] below denotes j repeated parameters, not a power of a function.

Set
\[
\mathbf c=(7/4,1/2,1/2,1,1),\qquad
\mathbf d=(3/4,3/2,3/2,2,2).
\]
The following symbols abbreviate TWO FIXED VALUES of that standard function:
\[
\mathfrak F_4=
F_{5:3;0}^{5:4;1}\!\left[
\begin{matrix}\mathbf c:(1/2)^{[4]};1\\
\mathbf d:1^{[3]};-
\end{matrix};1,1\right],
\]
\[
\mathfrak F_6=
F_{5:6;0}^{5:7;1}\!\left[
\begin{matrix}\mathbf c:5/4,(1/2)^{[6]};1\\
\mathbf d:1/4,1^{[5]};-
\end{matrix};1,1\right].
\]
There are no parameter derivatives, regulator limits, branch prescriptions,
finite harmonic coefficients, or implicit parameter choices in these values.

## 2. The new coefficient identification

Retain
\[
a_n=(1/2)_n/n!,\qquad
\delta_n=\pi^2/3-4H_{2n}^{(2)}+2H_n^{(2)}.
\]
The integer and half-integer polygamma identities [2] give
\[
\delta_n=\psi_1(n+1/2)-\psi_1(n+1)
=\sum_{r\ge0}\left\{\frac1{(n+r+1/2)^2}-\frac1{(n+r+1)^2}\right\}.
\]
For k a nonnegative integer, define the rational coefficient temporarily by
\[
b_k=\frac1{(k+1/2)^2}-\frac1{(k+1)^2}
=\frac{k+3/4}{(k+1/2)^2(k+1)^2}>0.
\]
It has the exact Pochhammer representation
\[
\boxed{b_k=3\frac{(7/4)_k(1/2)_k^2(1)_k^2}
{(3/4)_k(3/2)_k^2(2)_k^2}.}
\tag{1}
\]
One can verify (1) either by cancelling factors or by its initial value b_0=3
and its rational consecutive-term ratio. This identity is proved here; [1]
supplies only the standard function convention, not a C6 summation theorem.

The local m coefficients in the two Kampé de Fériet values are respectively
\[
\frac{((1/2)_m)^4}{(m!)^4}=a_m^4,
\qquad
\frac{(5/4)_m}{(1/4)_m}\frac{((1/2)_m)^6}{(m!)^6}
=(4m+1)a_m^6.
\]
The local n coefficient is (1)_n/n!=1. Therefore
\[
\boxed{\sum_{n\ge0}a_n^4\delta_n=3\mathfrak F_4,\qquad
\sum_{n\ge0}(4n+1)a_n^6\delta_n=3\mathfrak F_6.}
\tag{2}
\]
Every term before and after exchanging summations is nonnegative, so Tonelli's
theorem applies. Finiteness is proved in Section 6; neither equality is a
subtraction of two divergent multiple series.

As a corollary, the legacy wheel itself has the fixed-function evaluation
\[
\boxed{\mathscr W_c=24\mathfrak F_4+15\pi\mathfrak F_6
-\frac{(8+5\pi)\pi^2}{3}.}
\tag{3}
\]
The subtraction in (3) is its n=0 term, because the legacy Wc starts at n=1.
The ACTIVE Ecentral already starts at n=0; no such constant is to be added
again to the current coefficient.

## 3. The eight ordinary values

All the following are standard pFq values at unity [3]:
\[
U_4={}_4F_3((1/2)^{[4]};1^{[3]};1),
\quad
U_6={}_7F_6(5/4,(1/2)^{[6]};1/4,1^{[5]};1),
\]
\[
U_8={}_9F_8(5/4,(1/2)^{[8]};1/4,1^{[7]};1),
\]
\[
H_-={}_7F_6(1,(1/4)^{[6]};(3/4)^{[6]};1),\quad
H_0={}_6F_5((1/2)^{[6]};1^{[5]};1),
\]
\[
H_+={}_7F_6(1,(3/4)^{[6]};(5/4)^{[6]};1).
\]
For r=1,7 only, put t=r/8 and
\[
Y_r=t\left[\frac{\Gamma(t+1/4)}{\Gamma(t+3/4)}\right]^8
{}_{10}F_9\!\left(
\begin{matrix}1,1+t,(t+1/4)^{[8]}\\t,(t+3/4)^{[8]}\end{matrix};1\right).
\]
These are finite abbreviations for ordinary functions, not bespoke infinite
series. The exact gamma prefactors are included in the exported JSON.
All lower parameters are positive. The pFq excess is 1 for U4 and U6, and 2
for the other six values, so every defining series converges absolutely at 1.

Set
\[
C_s=60Q-\frac{105}{4}A^2-9A\pi-\frac{2469}{4}\pi^2,
\quad C_d=96Q-42A^2-18A\pi-1227\pi^2,
\]
where A=pi+4log2 and Q=Gamma(1/4)^4/pi. Let the following be merely a FINITE
linear combination of the eight explicitly tabulated values:
\[
\begin{aligned}
\mathcal O={}&4\pi^3C_dU_4+2\pi^4C_sU_6
+\frac{288Q^3}{\pi}H_- -2496\pi^5H_0
+\frac{3\cdot2^{21}\pi^5}{Q^3}H_+\\
&+\pi^6(4932-5004\sqrt2)U_8\\
&+556\pi^2\{(17+12\sqrt2)Y_1-(17-12\sqrt2)Y_7\}.
\end{aligned}
\tag{4}
\]
No new infinite-sum definition is assigned to O.

## 4. Complete weighted insertion

The inherited even-sector identities in `inputs/even_sector_derivation.md`
are used in the reverse direction for the non-wheel pieces:
\[
B_s=2\pi^4U_6,\quad B_d=4\pi^3U_4,
\]
\[
P_b=\frac{6Q^3}{\pi}(2H_--1)-104\pi^5H_0
+\frac{2^{18}\pi^5}{Q^3}H_+,
\]
\[
24P_{Z,6}+P_K/3
=\pi^2\{(19728-20016\sqrt2)Y_2
+556[(17+12\sqrt2)Y_1-(17-12\sqrt2)Y_7]\},
\quad Y_2=\pi^4U_8/4.
\]
The ordinary-period identifications and their earlier Fourier proofs are
inherited, not newly inferred from numerical agreement.

From the explicit R4,R6,R8 polynomials in the latest expression, direct
collection gives
\[
\begin{aligned}
\pi^3\mathcal E_c={}& C_sB_s+C_dB_d+24P_b+24P_{Z,6}+P_K/3\\
&-3144\pi^3\sum_{n\ge0}a_n^4\delta_n
-1965\pi^4\sum_{n\ge0}(4n+1)a_n^6\delta_n.
\end{aligned}
\]
This equality is checked symbolically as a polynomial identity in a_n,h_n,
delta_n,n,A,Q,pi. Inserting (2) and the eight ordinary values yields
\[
\boxed{\pi^3\mathcal E_c=
\mathcal O-\frac{144Q^3}{\pi}
-9432\pi^3\mathfrak F_4-5895\pi^4\mathfrak F_6.}
\tag{5}
\]
The only standalone constant in (5) comes from expanding (2H_--1) in 24Pb.
It is NOT a second wheel zero-index correction.

Let E_sv be the exact input known polynomial. Define
\[
E_{\rm KdF}=E_{\rm sv}-144Q^3/\pi.
\]
The complete new coefficient is
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_{\rm KdF}
+208896\Re\mathcal L_{0,1,1,1,0}(i)\\
&+13056(32G-3\pi^2)\Im\operatorname{Li}_3((1+i)/2)\\
&+\mathcal O-9432\pi^3\mathfrak F_4-5895\pi^4\mathfrak F_6\\
&+24\pi^3\mathscr M_7+192\pi^2\mathscr P_c^{(3)}.
\end{aligned}}
\tag{6}
\]
The full E_sv polynomial and all unchanged standard and custom definitions are
embedded in `results/expression.json` (E_KdF is stored already expanded).

The Brown SVHPL convention is exactly the input convention. The primitive still
obeys Pa=2*pi^2*PaCubic. Its zero-index term and that of M7 are not changed.
The source repair is copied unchanged and is not added separately.

For clarity about complexity: the fully expanded elementary known part now has
21 monomials rather than 20; -144Q^3/pi is new. An explicit Q^(-3) multiplier also
returns in the H+ coefficient. Keeping 144Q^3/pi*(2H_--1) grouped instead leaves
the previous known polynomial untouched. Neither bookkeeping choice is claimed
to be an arithmetic simplification.

## 5. Numerical checks actually executed

The exact verifier performs 77 finite checks of coefficient identities,
Pochhammer ratios, all three powers in the even-sector assembly, parameter
counts and positive pFq excess, the complete polynomial shift, and unchanged
source correction, polylogarithms, M7 and cubic primitive. These are
implementation checks, not 77 independent summation theorems.

The two fixed standard values begin
\[
\mathfrak F_4=1.1035407109510584384508271210614834570309524830406935292410409798338\ldots,
\]
\[
\mathfrak F_6=1.1052851386107306195047747041922837359213384731340019288408321995045\ldots.
\]

All eight ordinary values were freshly evaluated using the retained exact
rational-ratio tail algorithm, with (N,M)=(128,36) and (192,60). At 180 working
digits in the second run, their finite standard-function assembly differs
from the inherited Ecentral interval midpoint by 7.391e-103. The full new C6
assembly differs from the previous assembly by 1.048e-104 and begins

14331.687032758054320445463255246217118317323061988790458203142303743126964076393293879098356458544836219349...

These differences are floating-point cross-checks using inherited values for
unchanged sectors, not a new full-C6 certificate or physical verification.
The old Ecentral value was not used to choose any coefficient or parameter.

## 6. Convergence and independent positive bounds

For k=m+n<N the literal triangular partial sums of the two standard double
series are efficiently evaluated by their finite diagonals:
\[
F_{4,N}=\frac13\sum_{k=0}^{N-1}b_k\sum_{m=0}^k a_m^4,
\quad
F_{6,N}=\frac13\sum_{k=0}^{N-1}b_k\sum_{m=0}^k(4m+1)a_m^6.
\]
These are numerical partial-sum instructions, not new active function names.

The inherited elementary bound a_m^2<=1/(3m+1), integral comparison, and the
positive trigamma integral give
\[
\sum_{m\ge0}a_m^4<4/3,\qquad
\sum_{m\ge0}(4m+1)a_m^6<13/9,
\quad
0<\delta_N<\frac1{2(N+1/4)^2}.
\]
For the last inequality one can directly use
\[
\delta_N=\frac12\int_0^\infty u\,e^{-(N+1/4)u}\operatorname{sech}(u/4)\,du.
\]
It follows that
\[
\boxed{0<\mathfrak F_4-F_{4,N}<\frac2{9(N+1/4)^2},\quad
0<\mathfrak F_6-F_{6,N}<\frac{13}{54(N+1/4)^2}.}
\tag{7}
\]
This proves finite absolute convergence at the corner (1,1), with no
regularization. The actual triangular decay is O(N^-2); the old one-index
D4,D6 tails decay as O(N^-3). No claim of faster literal summation is made.

Exact rational triangular intervals at N=32,128,512 independently contain the
fine intervals described next. No pi or gamma approximation is required to
construct these triangular intervals.

For practical high accuracy, `certify_kdf.py` splits the PREVIOUS PROVEN wheel
certificate into its fourth- and sixth-power parts, then divides each by three
using (2). It recomputes those rational coefficients and its pi enclosure.
This is a reuse of inherited finite-tail proofs, not a new independent
high-precision evaluator of the literal double series.

For N=256, M4=40, M6=41, the outward-rounded widths are respectively less than
2.365e-148 and 3.299e-148. The certificates at the three configurations nest.
The bounds include arithmetic uncertainty; no decimal target is an input.

## Reproduction

Python 3, SymPy and mpmath suffice; no network calls are made by the scripts.

```
python formula.py
python verify.py
python certify_kdf.py
python numerical.py 128 36 120
python numerical.py 192 60 180
```

`legacy/` contains the supplied rational tail implementations unchanged.
`inputs/` retains the exact source expression and inherited interval/check
files. `results/` contains the new complete expression, exact tests, KdF
intervals, and numerical comparisons.

## References and attribution

[1] R. Ito, S. Kumabe, A. Nakagawa, Y. Nemoto, *Kampé de Fériet hypergeometric
functions over finite fields*, arXiv:2212.14321, Introduction: the displayed
CLASSICAL complex-variable definition is used here; no finite-field theorem
is being applied to C6. https://arxiv.org/html/2212.14321

[2] NIST DLMF 5.15, polygamma series and recurrences.
https://dlmf.nist.gov/5.15

[3] NIST DLMF 16.2, ordinary generalized hypergeometric definition and convergence
at unity. https://dlmf.nist.gov/16.2

[4] Supplied C6_even_sector_derivation.md: inherited ordinary-period identities
and their central-binomial coefficients. Supplied central-wheel derivation:
inherited exact rational fourth-/sixth-power tail estimates.

[5] Supplied C6_standard_svhpl_expression.json: unchanged starting normalization,
known part, source repair, standard polylogarithms, M7 and PaCubic definitions.
