# C6(1): exact polylogarithmic basis audit

## 0. Result and its limits

The active input is the supplied optional eight-call expression
`C6_eight_value_alternative_expression.json`, preserved byte-for-byte in
`inputs/accepted_eight_call_expression.json`. It combines two real
polylogarithmic components into the real projection of one complex Kampé de
Fériet value. Its own source correctly distinguishes that call-count
compression from arithmetic basis reduction.

This continuation does **not** eliminate another active C6 value. It obtains
three exact reductions for candidate depth-two MPL values, and performs an
exact finite coefficient-space audit of all weight-five Brown SVHPL words at
i. The latter shows what the specified shuffle/inversion relations do not
suffice to eliminate. Neither the formal rank nor an unsuccessful search is
a theorem about arithmetic independence of the actual numerical periods.

The known polynomial, the wheel, seventh sector, primitive and the source
correction in C6 are unchanged. There is no new all-sector numerical evaluation
or physical graph/RG verification. The old wheel enclosure is an enclosure of
its explicitly defined series, not a new physical certificate.

## 1. Convention and three candidate reductions

Use the project's descending-index convention
\[
 \operatorname{Li}_{a,b}(z,1)=\sum_{n>m\ge1}\frac{z^n}{n^a m^b}.
\]
All the values used below converge at z=i. Write
\[
 G=\operatorname{Catalan},\quad \ell=\log2,\quad
 B_4=\operatorname{Im}\operatorname{Li}_4(i)=\beta(4).
\]
The beta symbol is the ordinary Dirichlet beta function, not a new C6 period.
For a finite conventional alternative,
\[
 B_4=\frac{\psi^{(3)}(1/4)-\psi^{(3)}(3/4)}{1536}.
\]
The normalization follows directly from the polygamma reciprocal-power formula
[3]. The three identities derived by the finite inversion calculation are
\[
\boxed{\operatorname{Re}\operatorname{Li}_{4,1}(i,1)
=-\frac{\pi B_4}{4}+\frac{\pi^2\zeta(3)}{48}
 +\frac{467}{1024}\zeta(5),}
\tag{1}
\]
\[
\boxed{\operatorname{Re}\operatorname{Li}_{3,2}(i,1)
=\frac{3\pi B_4}{4}-\frac{61}{1536}\pi^2\zeta(3)
 -\frac{1943}{1024}\zeta(5),}
\tag{2}
\]
\[
\boxed{\operatorname{Re}\operatorname{Li}_{2,3}(i,1)
=-\frac{3\pi B_4}{4}-\frac{\pi^2\zeta(3)}{256}
 -\frac{G\pi^3}{32}+\frac{3027}{1024}\zeta(5).}
\tag{3}
\]
In particular a combination eliminating B4 is
\[
\boxed{\operatorname{Re}[\operatorname{Li}_{3,2}(i,1)
 +3\operatorname{Li}_{4,1}(i,1)]
 =\frac{35}{1536}\pi^2\zeta(3)-\frac{271}{512}\zeta(5).}
\tag{4}
\]
These are specializations of the standard inversion/parity mechanism [1,2],
not claims to have discovered a new general MPL theorem. They prune a candidate
search basis. They are not a substitution for the active depth-three value
\(\operatorname{Re}\operatorname{Li}_{2,1,2}(i,1,1)\).

## 2. Finite inversion derivation, with branches

For HPLs use omega0=dz/z and omega1=dz/(1-z). The dictionary relevant here is
\[
 H_{00011}=\operatorname{Li}_{4,1},\quad
 H_{00101}=\operatorname{Li}_{3,2},\quad
 H_{01001}=\operatorname{Li}_{2,3}.
\]
Under z -> 1/z the pulled-back letters are
\[
 \omega_0\mapsto-\omega_0,\qquad
 \omega_1\mapsto\omega_0+\omega_1.
\]
On the upper half-plane the branch is fixed by
\[
 H_0(1/z)=-H_0(z),\qquad
 H_1(1/z)=H_0(z)+H_1(z)-i\pi.
\tag{5}
\]
These two relations and the HPL differential equations recursively determine
inversion, up to endpoint constants. Tangential endpoint constants at z=1
are fixed by replacing the divergent H1 by -i*pi on the inverted side.
All other constants are the shuffle-regularized MZVs of weight at most five.
In particular the convergent values needed include
\[
 H_{00011}(1)=2\zeta(5)-\zeta(2)\zeta(3),\quad
 H_{00101}(1)=3\zeta(2)\zeta(3)-\frac{11}{2}\zeta(5).
\]
The regularized bookkeeping occurs only in the proof. The final values at i
are ordinary convergent values with no regularization operation.

For a compact exact record, put L=log z. The recursion gives
\[
\begin{aligned}
H_{00011}(1/z)={}&-H_{00011}(z)+3\operatorname{Li}_5(z)
 +(i\pi-L)\operatorname{Li}_4(z)\\
&-\frac{L^5}{120}+\frac{i\pi L^4}{24}
 +\frac{\pi^2L^3}{12}-\frac{i\pi^3L^2}{12}
 +\frac{\zeta(3)L^2}{2}\\
&-\frac{\pi^4 L}{45}-i\pi\zeta(3)L
 -\frac{i\pi^5}{90}-\frac{\pi^2\zeta(3)}3+\zeta(5),
\end{aligned}
\tag{6}
\]
\[
\begin{aligned}
H_{00101}(1/z)={}&-H_{00101}(z)-7\operatorname{Li}_5(z)
 +(3L-3i\pi)\operatorname{Li}_4(z)\\
&+\left(-\frac{L^2}{2}+i\pi L+\frac{\pi^2}{3}\right)
 \operatorname{Li}_3(z)\\
&-\frac{L^5}{120}+\frac{i\pi L^4}{24}
 +\frac{\pi^2L^3}{18}-\zeta(3)L^2
 -\frac{\pi^4L}{90}+2i\pi\zeta(3)L\\
&+\frac{i\pi^5}{30}+\frac{2\pi^2\zeta(3)}3-4\zeta(5).
\end{aligned}
\tag{7}
\]
At z=i, 1/z=-i and H_w(-i)=conjugate(H_w(i)). Use
\[
\begin{aligned}
\operatorname{Li}_2(i)&=-\pi^2/48+iG,\\
\operatorname{Li}_3(i)&=-3\zeta(3)/32+i\pi^3/32,\\
\operatorname{Li}_4(i)&=-7\pi^4/11520+iB_4,\\
\operatorname{Li}_5(i)&=-15\zeta(5)/512+5i\pi^5/1536,
\end{aligned}
\]
and L=i*pi/2. Equations (6)-(7) become precisely twice (1)-(2).
The shuffle identity
\[
 \operatorname{Li}_2\operatorname{Li}_3
 =\operatorname{Li}_{2,3}+3\operatorname{Li}_{3,2}
  +6\operatorname{Li}_{4,1}
\tag{8}
\]
then gives (3). The program checks these finite identities exactly.

## 3. Why this does not eliminate the active real depth-three value

The current unpacked polylogarithmic block is
\[
 B_{\rm pol}=4352[(32G+9\pi^2)D_3-64D_5],
\]
\[
 D_3=\operatorname{Im}\operatorname{Li}_{2,1}(i,1),\qquad
 D_5=\operatorname{Re}\operatorname{Li}_{2,1,2}(i,1,1).
\]
The parity theorem reduces the conjugation combination
\[
 \operatorname{Li}_{\boldsymbol n}(\boldsymbol z)
 -(-1)^{w-d}\operatorname{Li}_{\boldsymbol n}(1/\boldsymbol z),
\]
where w is the weight and d is the depth [1]. At roots of unity this reduces
real parts when w-d is odd and imaginary parts when it is even. Index reversal
converts the ascending convention of [1] to the descending convention used
here without changing w or d.

Thus it reduces Re Li21, not D3, and Im Li212, not D5. The depth-two identities
(1)-(3) are on the reducible side of the parity rule; the two components active
in C6 are on the other side. The rule alone is not an independence theorem.

## 4. Exact formal audit of all weight-five Brown SVHPL words

Use the same standard Brown SVHPL normalization as the supplied earlier
single-valued reduction, described in [4]. The code retains that source's
finite associator construction through word length five. No numerical fit is
used to choose a linear relation.

Let
\[
 V=\operatorname{Re}\mathcal L_{01110}(i),\qquad
 R_{221}=\operatorname{Re}\operatorname{Li}_{2,2,1}(i,1,1).
\]
The finite construction and the inversion relations give
\[
\boxed{V=\frac83GD_3-\frac43D_5
 +\frac{G\pi^3}{144}+\frac{163\pi^2\zeta(3)}{2304}.}
\tag{9}
\]
This particular identity is a recovery of the already retained single-valued
conversion. The larger all-word audit is the new diagnostic.

After the known elementary and zeta terms are removed, take all 32 binary
words of weight five and both their real and imaginary components. Expand
using shuffle, inversion and the displayed lower-weight values. Every one of
these 64 coefficient vectors satisfies
\[
\boxed{[D_3]+2G[D_5]-G[R_{221}]=0.}
\tag{10}
\]
Square brackets in (10) mean a coefficient in this explicitly constructed
formal reduction, not an operation on numerical constants.

In the implementation the remaining formal columns are
D3, D5, B4, ImLi32, ImLi311, ImLi221, ImLi2111, ReLi221, ReLi2111.
The matrix of those 64 rows has rank four over the rational-function field in
the known symbolic constants. Adding the C6 target row
\[
 (32G+9\pi^2,-64,0,\ldots,0)
\]
raises its rank to five. Its value in (10) is 9*pi^2-96*G, not zero.

Equivalently, recovering the known V conversion yields the exact complete
block relation
\[
\boxed{\begin{aligned}
B_{\rm pol}={}&208896V
 +13056(3\pi^2-32G)D_3\\
&-\frac{4352}{3}G\pi^3-\frac{44336}{3}\pi^2\zeta(3).
\end{aligned}}
\tag{11}
\]
The remaining coefficient is provably nonzero. Indeed, pi>157/50 and the
alternating-series upper bound
G<1-1/9+1/25-1/49+1/81 imply
\[
3\pi^2-32G>\frac{1114843}{9922500}>0.
\]
Numerically it is about 0.29791418959706737475616052.

**Scope of this statement:** (10) and the rank computation specify the limits
of the tested algebraic reductions. The remaining formal symbols have not
been proved arithmetically independent. Additional special-value identities,
other arguments, other function families, or relations involving the elliptic
sectors are not excluded. In particular this is not a lower bound on the true
number of independent constants in C6.

## 5. Check of the quintic route

The previous eight-call construction uses
\[
P(x)=[a(x+1)^2+c(x+1)+3](x+2)^3
-z[a(x+2)^2+c(x+2)+2](x+1)^3,
\]
where a=i*kappa. A structural factorization was also investigated. At the
formal specialization a=c=1, z=1/2, twice this polynomial is
\[
 f(x)=x^5+10x^4+44x^3+108x^2+139x+72.
\]
It is irreducible modulo 5 and factors modulo 53 as
\[
 (x+7)(x-24)(x-17)(x^2-9x-12),
\]
with the quadratic irreducible. Its Galois group, also computed directly, is
S5. This is an exact result for that rational specialization. It gives no
classification of the Galois group or potential special simplifications at
the actual C6 parameters. The program deliberately makes no such inference.
This exploratory result is not used in (1)-(11) or in the active C6 formula.

## 6. Executed checks

`analysis.py` passes 73 finite checks, including all 64 real/imaginary
coefficient invariants, the three depth-two evaluations, the formal rank
calculation and the complete weighted identity (11). These are implementation
checks of a finite calculation, not 73 independent mathematical theorems.

`numerical.py` uses each MPL's own strict series at i/2, then two Taylor steps
to i. No closed formula from (1)-(3) initializes those series. Separate runs
use 60 and 100 working digits, with Taylor orders 460 and 700. At 100 working
digits the largest discrepancy among (1)-(3) is below 2.858e-101; the weighted
identity (11) has discrepancy below 9.364e-97. The checks also compare beta(4)
to its polygamma formula.

These are floating-point checks, **not** rigorous interval certificates. No
Wolfram kernel or fresh complete-C6 evaluation was performed. The accepted
expression in inputs is hashed and left unchanged.

## 7. State of the actual coefficient

* Active fixed function calls: eight in the optional packed form, or nine in
  the simpler-parameter unpacked form.
* Active values eliminated in this pass: zero.
* Known-polynomial change: zero.
* Explicit residual sums or integrals added to the active coefficient: zero.
* Arithmetic basis dimension established: none.

The exact work here narrows the candidate polylogarithmic search and identifies
a specific obstruction within the tested inversion/shuffle framework. It must
not be described as an eight-to-seven C6 reduction.

## Sources and provenance

1. E. Panzer, *The parity theorem for multiple polylogarithms*, arXiv:1512.04482v3,
   Theorem 1.3 and Sections 3-4. https://arxiv.org/html/1512.04482v3
2. E. Remiddi and J. A. M. Vermaseren, *Harmonic Polylogarithms*,
   arXiv:hep-ph/9905237. https://arxiv.org/abs/hep-ph/9905237
3. NIST DLMF, Sections 5.15 and 25.12: polygamma and classical polylogarithm
   conventions. https://dlmf.nist.gov/5.15 ; https://dlmf.nist.gov/25.12
4. L. J. Dixon, C. Duhr and J. Pennington, *Single-valued harmonic polylogarithms
   and the multi-Regge limit*, arXiv:1207.0186. https://arxiv.org/abs/1207.0186
5. Supplied C6_standard_svhpl_reduction.zip: finite shuffle and associator
   implementation used here, including its normalization of Brown's functions.
6. Supplied C6_eight_value_alternative_expression.json and its derivation:
   unchanged accepted coefficient and the limitation of function-call packing.
7. Supplied central-wheel derivation and certificate: retained normalization,
   zero-index convention, tail bounds, source repair and physical qualifications.

The literature is used for standard function identities and conventions, not
as a source of an independently proved Ising C6 coefficient.
