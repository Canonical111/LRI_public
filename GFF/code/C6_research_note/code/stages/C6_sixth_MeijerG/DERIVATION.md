# C6(1): a finite ordinary-Meijer-G reduction of the sixth-power block

## Scope

This continuation reduces **P_b**, not the unresolved primitive **P_a**.
The supplied current representation has a finite polylogarithmic block, thirteen
ordinary generalized hypergeometric values, and three unevaluated elliptic
quadrature blocks. Three of those thirteen ordinary values constitute P_b.
Their complete contribution is replaced here by two ordinary univariate Meijer G
values with rational parameters. An optional single-value form uses one
nonrational, explicitly elementary parameter.

No integral, infinite sum, derivative, or limiting prescription occurs in either
new finite formula for P_b. The full C6 coefficient has **not** thereby been
evaluated without integration: the wheel, seventh logarithmic sector, and P_a
remain unresolved in the requested finite Mathematica-built-in basis. Their
previous definitions are unchanged.

The initial graph/RG identification, source correction, and the saved
central-binomial identity for P_b are inherited analytic inputs. The new result
is a finite basis change using standard Meijer G residue and reflection
identities. No value of C6 was used to determine its coefficients.

The input is an unchanged copy of `partial_expression.json` from the supplied
`C6_finite_polylog_reduction.zip`. Its hash is in the output JSON.

## 1. Two rational-parameter values

Repeated entries below mean repeated parameters, not derivatives. Set

\[
X_{35}=G_{6,6}^{3,5}\!\left(1\middle|\begin{matrix}(1/2)^{[6]}\\0^{[6]}\end{matrix}\right),
\qquad
X_{44}=G_{6,6}^{4,4}\!\left(1\middle|\begin{matrix}(1/2)^{[6]}\\0^{[6]}\end{matrix}\right).
\]

These are the ordinary functions in Mathematica's documented `MeijerG` interface
[1], not its earlier bivariate extension. The exact result is

\[
\boxed{P_b=8\pi(13X_{35}+11X_{44}).}\tag{1}
\]

In the fixed normalization r6=2187 C6(1), this reads

\[
\boxed{24P_b=192\pi(13X_{35}+11X_{44}).}\tag{2}
\]

The Wolfram parameter splitting is specified in the standalone patch file.
It is essential: identical complete upper/lower lists with different numerator
splits represent different Meijer G functions.

## 2. The inherited identity and normalization

Write Q=Gamma(1/4)^4/pi. The saved ordinary form is

\[
P_b=\frac{6Q^3}{\pi}(2H_- -1)-104\pi^5H_0
       +\frac{2^{18}\pi^5}{Q^3}H_+,
\]

where

\[
H_-={}_7F_6(1,(1/4)^{[6]};(3/4)^{[6]};1),\quad
H_0={}_6F_5((1/2)^{[6]};1^{[5]};1),
\]
\[
H_+={}_7F_6(1,(3/4)^{[6]};(5/4)^{[6]};1).
\]

The previously established even-sector identity also gives

\[
P_b=24\pi^3\sum_{n\ge0}a_n^6
        (88\pi h_n+312h_n^2+13\delta_n),\tag{3}
\]
\[
a_n=(1/2)_n/n!,\quad
h_n=\log2+H_n-H_{2n},\quad
\delta_n=\pi^2/3-4H_{2n}^{(2)}+2H_n^{(2)}.
\]

Equation (3) is an input from `C6_even_sector_derivation.md`, equations (3)-(4),
not a new summation theorem claimed here. Sums used below are proof devices;
(1)-(2) are the proposed finite replacements.

## 3. Standard Mellin kernels

For j=1,...,5 use, in the proof only,

\[
g_j(x)=G_{6,6}^{j,6-j}\!\left(x\middle|\begin{matrix}(1/2)^{[6]}\\0^{[6]}\end{matrix}\right).
\]

The inverse-Mellin form of the standard definition [2] has kernel

\[
M_j(s)=\frac{\Gamma(s)^j\Gamma(1/2-s)^{6-j}}
 {\Gamma(1-s)^{6-j}\Gamma(1/2+s)^j}.
\tag{4}
\]

One may take the upward line Re(s)=1/4. Its left poles are at nonpositive
integers, and its right poles are at positive half-integers. The denominators
only introduce zeros. Gamma reflection [3] gives

\[
M_j(s)=\left[\frac{\Gamma(s)}{\Gamma(s+1/2)}\right]^6
                    \tan^{6-j}(\pi s).\tag{5}
\]

On this contour |tan(pi s)|=1, and the gamma ratio has sixth power O(|Im s|^-3).
Thus all five Mellin integrals are absolutely convergent at x=1. There is no
regularization at the argument used in (1).

Contour reflection gives

\[
M_j(1/2-s)=M_{6-j}(s),\qquad g_j(1)=g_{6-j}(1).
\tag{6}
\]

In particular, g2(1)=g4(1).

The exact standard kernels for the two values in (1) are

\[
N_{35}(s)=\frac{\Gamma(s)^3\Gamma(1/2-s)^5}
                  {\Gamma(1-s)^3\Gamma(1/2+s)},
\]
\[
N_{44}(s)=\frac{\Gamma(s)^4\Gamma(1/2-s)^4}
                  {\Gamma(1-s)^2\Gamma(1/2+s)^2}.
\]

Since 1+tan^2=sec^2, reflection yields

\[
\boxed{N_{35}=\pi^2(M_1+M_3),\qquad
       N_{44}=\pi^2(M_2+M_4).}\tag{7}
\]

Therefore

\[
X_{35}=\pi^2[g_1(1)+g_3(1)],\qquad
X_{44}=2\pi^2g_2(1).\tag{8}
\]

These are identities between fixed ordinary special-function values.

## 4. Residues: the harmonic polynomial matches exactly

Near s=-n+epsilon, gamma recurrence and the integer/half-integer polygamma
values [3,4] give

\[
\frac{\Gamma(-n+\epsilon)}{\Gamma(1/2-n+\epsilon)}
=\frac{a_n}{\sqrt\pi\,\epsilon}
 \exp\left[2h_n\epsilon+
       \frac12(\delta_n-2\pi^2/3)\epsilon^2+O(\epsilon^3)\right].\tag{9}
\]

For example, the n=0 logarithmic derivative is 2 log 2, and its second
coefficient follows from zeta(2)-psi1(1/2)=-pi^2/3. Shifting from zero to -n
adds 2(H_n-H_2n) and -4H_2n^(2)+2H_n^(2), respectively. These finite shift
identities are tested with exact rational arithmetic.

Taking the simple, double, and triple pole residues in (5) gives

\[
g_1(1)=\pi^2\sum a_n^6,
\qquad g_2(1)=12\pi\sum a_n^6h_n,
\]
\[
g_3(1)=\sum a_n^6(72h_n^2+3\delta_n-\pi^2).
\tag{10}
\]

To justify the endpoint use of these expansions, first take 0<x<1 and close
on the left. At x approaching 1, the Mellin side is dominated on Re(s)=1/4
by an integrable O((1+|Im s|)^-3) majorant. The residue sums are absolutely
convergent: a_n^6=O(n^-3) and h_n,delta_n are bounded. This gives (10) without
an extra limiting value in the final definition.

Inserting (10) into (8) cancels the pi^2 term in X35 and gives

\[
\boxed{X_{35}=3\pi^2\sum a_n^6(24h_n^2+\delta_n),
\qquad X_{44}=24\pi^3\sum a_n^6h_n.}\tag{11}
\]

Now multiply the first identity by 13, the second by 11, and then by 8pi:

\[
8\pi(13X_{35}+11X_{44})
=24\pi^3\sum a_n^6(312h_n^2+13\delta_n+88\pi h_n).
\]

The result is precisely the inherited (3). This proves (1); no coefficient was
inferred from a numerical fit.

## 5. Optional one-value compression

There is also a literal one-Meijer-G form. Put

\[
\alpha=\frac{\arctan(11/13)}\pi,
\qquad
X(\alpha)=G_{7,7}^{4,5}\!\left(1\middle|
\begin{matrix}(1/2)^{[6]},\alpha\\0^{[6]},\alpha\end{matrix}\right).
\]

The parameter alpha belongs to BOTH denominator groups in the Mellin kernel;
these repeated parameters are not a cancelling numerator/denominator pair.
Its kernel is

\[
N_\alpha(s)=\frac{\Gamma(s)^4\Gamma(1/2-s)^5}
 {\Gamma(1-s)^2\Gamma(1/2+s)\Gamma(s+\alpha)\Gamma(1-s-\alpha)}.
\]

Reflection shows

\[
N_\alpha=N_{44}\frac{\sin\pi(s+\alpha)}{\cos\pi s}
=\cos(\pi\alpha)N_{35}+\sin(\pi\alpha)N_{44}.
\]

Since cos(pi alpha)=13/sqrt(290) and sin(pi alpha)=11/sqrt(290),

\[
\boxed{P_b=8\pi\sqrt{290}\,X(\alpha).}\tag{12}
\]

This is a standard univariate built-in value at 1, without integration or
summation. The cost of one value instead of two is a nonrational parameter.
It packages the same linear combination; it is not a theorem reducing the
arithmetic dimension of its period space. Formula (1) is the rational-parameter
alternative.

## 6. Complete coefficient bookkeeping

The current expression records the constant from 24 P_b separately in its
known polynomial. Consequently it is the WHOLE block

\[
-\frac{144Q^3}{\pi}+\frac{288Q^3}{\pi}H_-
-2496\pi^5H_0+\frac{6291456\pi^5}{Q^3}H_+
\]

that must be replaced by (2), or by 192 pi sqrt(290) X(alpha).

The updated known polynomial is

\[
E_{\rm new}=E_{\rm previous}+144Q^3/\pi.
\]

This addition cancels the existing negative term. It is not an additional
physical contribution. The exact conversion leaves 18 expanded monomials,
compared with 19 in the current polylogarithm-patched formula. It removes the
Q^3 monomial and the reciprocal-Q^3 multiplier from the finite block.

The ten other ordinary hypergeometric records are retained byte-for-byte as
JSON objects; the two finite polylogarithmic values and the three unresolved
elliptic blocks are unchanged. Their source correction is not added again.

The updated JSON is intentionally called a PARTIAL expression, with
`full_integral_free_sum_free_C6_established: false`. It does not present the
finite part as the full physical coefficient.

## 7. Verification

The symbolic script checks (7), (6), the Laurent shifts for n=0,...,10, the
full coefficient conversion, the optional angle compression, and all retained
input fields. Its exact check count is recorded in `results/exact_checks.json`.
These finite tests supplement the analytic argument; they are not independent
proofs of the inherited graph calculation.

For independent numerical verification, put

\[
K(u)=\frac{|\Gamma(1/4+iu)|^8}{|\Gamma(3/4+iu)|^4}.
\]

The two Barnes integrals reduce on the chosen line to

\[
X_{44}=\pi^{-1}\int_0^\infty K(u)du,
\qquad X_{35}=\pi^{-1}\int_0^\infty K(u)\operatorname{sech}(2\pi u)du.
\]

These integrals are used ONLY to check the finite Meijer G values numerically;
they do not appear in the proposed Wolfram expression. They converge
exponentially and prove X44>X35>0. The optional X(alpha) is checked with its
own gamma-product kernel rather than assigned the linear-combination value.

Separately, the old H-,H0,H+ values are evaluated using finite exact-rational
hypergeometric tail enclosures from the retained `rational_tails.py` evaluator.
Gamma prefactors are then evaluated in floating point. Two working precisions
were tested. At 90 digits, both new formulas and the old one agree after
rounding at that working precision:

```
X35 = 439.411958956372210429719906575496619240314895243432410278885420348106991481283585562754198
X44 = 518.368388269934723600265225600082246903301229718158856850078467741964527237023721545146561
alpha = 0.223535323940410124548181513147168721647006460925892983365015522997378121068023755332181418
Xalpha = 670.277101718760328715141787716539324100838878091427011541868408253516461812383097991125231
Pb = 286875.355943207969497610667613593257878343545521647412174403713266510974420740153357221126
```

Agreement at working precision is not an exact numerical zero or a rigorous
90-digit certificate. No new rigorous interval for these Meijer G values is
claimed. No new all-sector C6 evaluation was run. The Wolfram patch has been
checked statically but was not executed in a Wolfram kernel.

## Reproduction

Python 3, SymPy and mpmath suffice for the executed checks:

```
python build_and_verify.py
python numerical.py 50 128 36
python numerical.py 90 192 60
```

In Mathematica (not executed here):

```
Get["C6_sixth_MeijerG_patch.wl"];
PbMeijerPair[]
PbMeijerSingle[]
PbContributionR6[]
PbNumericalCheck[30]
```

## Sources and provenance

[1] Wolfram Language documentation, `MeijerG`, standard parameter-list splitting:
https://reference.wolfram.com/language/ref/MeijerG.html

[2] NIST DLMF 16.17, standard Mellin-Barnes definition:
https://dlmf.nist.gov/16.17

[3] NIST DLMF 5.5, gamma recurrence and reflection:
https://dlmf.nist.gov/5.5

[4] NIST DLMF 5.15, polygamma recurrence and integer/half-integer values:
https://dlmf.nist.gov/5.15

[5] NIST DLMF 5.11, gamma-ratio asymptotics:
https://dlmf.nist.gov/5.11

Inherited project inputs: `C6_even_sector_derivation.md` equations (3)-(4),
`C6_Mathematica_native.wl` ordinary table, and the latest finite-polylogarithm
patch. The source-correction and physical graph/RG identification are unchanged.
