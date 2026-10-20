# Symmetric primitive reduction for the retained C6(1) expression

## Result and scope

The input is `inputs/even_sector_expression.json`. Its normalization is
\(r_6=2187C_6(1)\). All graph/RG identifications, source corrections, previous
summations, and kernel identities remain inherited inputs.

This continuation establishes two results:

1. The optional Bailey numerator for \(P_a\) collapses from six product
   monomials to three symmetric products built from only two Gauss functions.
   An equivalent finite expression uses three explicitly defined four-index
   Horn values, all with beta weight \((1/2,1/2)\).
2. The previous universal rational-row antiderivative obstruction also excludes
   every row algebraic over \(\mathbb C(x)\), by normalized field trace.

Neither result evaluates \(P_a\) in a finite ordinary one-variable pFq basis.
The active one-index representation, the known polynomial, and the active
auxiliary list `Ecentral, Pa, M7central` are unchanged. The new formulas are
saved as an optional analytic representation, not counted as an elimination
of an independent period.

## 1. Two Gauss functions and three symmetric products

Write
\[
 Q=\frac{\Gamma(1/4)^4}{\pi},\qquad
 h(x)={}_2F_1(\tfrac14,\tfrac14;\tfrac12;x),\qquad
 v(x)={}_2F_1(\tfrac14,\tfrac14;1;x).
\]
These are the Gauss kernels already used in the input; \(h(x)\) is not the
harmonic remainder \(h_n\) in the even and seventh sectors.

Define
\[
 R(x)=Qh(x)h(1-x),\qquad
 S(x)=2\pi^2v(x)v(1-x).
\]
Then
\[
 \boxed{
 P_a=\int_0^1\frac{15R(x)^2+12R(x)S(x)-S(x)^2}{\sqrt{x(1-x)}}\,dx.
 } \tag{1}
\]
Equivalently,
\[
 \boxed{\begin{aligned}
 P_a={}&15Q^2\int_0^1\frac{h(x)^2h(1-x)^2}{\sqrt{x(1-x)}}\,dx\\
 &+24Q\pi^2\int_0^1
 \frac{h(x)h(1-x)v(x)v(1-x)}{\sqrt{x(1-x)}}\,dx\\
 &-4\pi^4\int_0^1\frac{v(x)^2v(1-x)^2}{\sqrt{x(1-x)}}\,dx .
 \end{aligned}} \tag{2}
\]
There are no \(u,g,F,J\) kernels, inverse powers of Q, or separately defined
logarithmic companions in (1)-(2). All three products have the same measure
and reflection symmetry. These are simplifications of the integrand, not
finite evaluations of the three integrals.

## 2. Exact cancellation in the inherited numerator

For \(0<x<1/2\), put \(z=4x(1-x)\). The saved Bailey product identities are
\[
 F(z)=v(x)h(x),\quad
 B(z)=\sqrt Q\,h(x)h(1-x),
\]
\[
 C(z):=v(x)v(1-x)=\frac{\sqrt Q}{2\pi}F(z)
                   -\sqrt{\frac zQ}J(z).                         \tag{3}
\]
Their definitions are retained under
`optional_bailey_primitive_reduction.product_identities`.

The saved primitive numerator and beta integral are
\[
 \begin{aligned}
 N(z)={}&Q[15B^2+12\pi FB-\pi^2F^2]\\
 &+4\pi^2\sqrt z\,J(\pi F-6B)-\frac{4\pi^4zJ^2}{Q},\\
 P_a={}&\int_0^1\frac{N(z)}{\sqrt{z(1-z)}}\,dz.                 \tag{4}
 \end{aligned}
\]
Equation (3) is equivalent to
\[
 \sqrt z J=\frac{Q}{2\pi}F-\sqrt Q C.
\]
Direct substitution into (4), with no parameter specialization or numerical
fit, gives
\[
 \boxed{N(z)=15QB^2+24\pi^2\sqrt Q\,BC-4\pi^4C^2.}             \tag{5}
\]
In particular, every term containing F cancels.

On the half interval,
\[
 \frac{dz}{\sqrt{z(1-z)}}=\frac{2\,dx}{\sqrt{x(1-x)}}.
\]
Inserting the Gauss products in (5) yields
\(15R^2+12RS-S^2\). This is invariant under \(x\mapsto1-x\);
extending the half-interval integral to the full interval gives (1).
There is no additional factor of two in (1).

The exact polynomial and Jacobian identities are checked in `verify.py`.

## 3. A finite three-value Horn specification

For \(c,d\in\{1/2,1\}\), set
\[
 a_c(n)=\frac{(1/4)_n^2}{(c)_n n!}.
\]
Define the fixed, four-index value
\[
 \boxed{\begin{aligned}
 {\mathfrak B}_{c,d}
 =\pi\sum_{m_1,m_2,n_1,n_2\ge0}
 &\frac{(1/2)_{m_1+m_2}(1/2)_{n_1+n_2}}
 {(1)_{m_1+m_2+n_1+n_2}}\\
 &\times a_c(m_1)a_d(m_2)a_c(n_1)a_d(n_2).
 \end{aligned}}                                                \tag{6}
\]
All four arguments are one. Increasing any local index multiplies the
summand by a rational function of all four indices, so (6) is an explicitly
specified Horn-type hypergeometric series. It is not an ordinary one-variable
pFq value.

Euler beta integration [1] gives
\[
 {\mathfrak B}_{c,d}
 =\int_0^1
 \frac{f_c(x)f_d(x)f_c(1-x)f_d(1-x)}{\sqrt{x(1-x)}}\,dx,
 \quad f_c(x)={}_2F_1(\tfrac14,\tfrac14;c;x).                    \tag{7}
\]
Thus the integral-free alternative to (1) is
\[
 \boxed{P_a=
 15Q^2{\mathfrak B}_{1/2,1/2}
 +24Q\pi^2{\mathfrak B}_{1/2,1}
 -4\pi^4{\mathfrak B}_{1,1}.}                                  \tag{8}
\]
This uses three fixed values with only two local parameter triples. It
does not meet a strictly ordinary one-variable summation target, and it
does not replace the existing one-index evaluator.

### Convergence and positivity

The coefficients of h and v are positive. At an endpoint h has at most a
logarithmic singularity, whereas v is finite; this follows from the
zero-balanced Gauss connection formula and the positive-excess case
[2,3]. Accordingly, the integrands in (7) are bounded by a beta weight
times an endpoint logarithm of degree at most two. Each integral converges.

Since the summands in (6) are nonnegative, termwise beta integration is
justified by monotone convergence, and its finite integral proves absolute
convergence of each of the three Horn values. No cancellation between
divergent series is used.

The signed expression in (1) is itself positive. Termwise comparison gives
\(h(x)\ge v(x)>0\). Also
\[
 \Gamma(1/4)>\int_0^1 t^{-3/4}(1-t)\,dt=\frac{16}{5},
 \qquad (16/5)^4>2(22/7)^3,
\]
so \(Q>2\pi^2\). Therefore \(R>S>0\), and
\[
 15R^2+12RS-S^2=15R^2+S(12R-S)>0.
\]
The optional completed-square form is
\[
 15R^2+12RS-S^2=51R^2-(S-6R)^2.
\]
The positivity argument uses the former form, not subtraction of nearly
equal large numbers.

## 4. Insertion in C6(1)

Keep the complete known part \(E_{\rm alg}\), and the other definitions,
from the even-sector input. Its active formula remains
\[
 \boxed{\begin{aligned}
 2187C_6(1)={}&E_{\rm alg}+835584\Lambda+391680H_5\\
 &+13056\sqrt2(32G+3\pi^2)H_3
 +\pi^3{\cal E}_{\rm c}+24\pi^3{\mathscr M}_7+96P_a.
 \end{aligned}}                                                \tag{9}
\]
An optional finite-Horn insertion is
\[
 \boxed{96P_a=
 1440Q^2{\mathfrak B}_{1/2,1/2}
 +2304Q\pi^2{\mathfrak B}_{1/2,1}
 -384\pi^4{\mathfrak B}_{1,1}.}                                 \tag{10}
\]
There is no compensating known-part shift: it is exactly zero. No source
correction, even-sector zero-index term, or seventh-sector zero-index term
is added again. The exported JSON preserves every pre-existing field,
including the entire active formula, verbatim as data; it adds only
`optional_symmetric_primitive_reduction`.

## 5. The rational boundary obstruction extends to algebraic rows

This section is a new consequence of the exact obstruction proved in the
previous even-sector derivation. It restricts one integration strategy; it
does not exclude finite definite-period evaluations.

For the retained nine-dimensional system, let
\[
 V'(x)=\mathsf R(x)V(x),\qquad
 \mathsf R(x)=\frac{(1+x^2)(\mathbf A+I/2)+x\mathbf C}
                  {x(1-x^2)}.
\]
The actual rational matrices \(\mathbf A,\mathbf C\) are embedded in the
input JSON. A universal linear boundary primitive \(r(x)V(x)\) for the
primitive density would require
\[
 r'(x)+r(x)\mathsf R(x)=\frac4x e_0^T.                          \tag{11}
\]
"Universal" means an identity for every local solution of the nine-dimensional
system, not just the particular initial data that define Pa.

The previous pole analysis restricts every rational solution to
\[
 r(x)=a\,x+b+\frac c{x}+\frac d{x+1},
\]
where a,b,c,d are constant nine-entry rows. For completeness the rationale
is as follows. The residue eigenvalues at zero are 1/2,1,3/2; the only
positive integer available for a rational pole order is one. At +1 the
eigenvalues are 0,-1,-2,-2,-3,-4,-4,-5,-6, excluding a pole. At -1 all
eigenvalues are one. At infinity a polynomial degree above one is excluded
by the leading matrix. An ordinary point cannot support a pole.

Clearing denominators in (11) yields a 54-by-36 rational system M b0 = b1,
with rank(M)=36 and rank(M|b1)=37. The calculation has been rerun. An exact
rational row lambda satisfies
\[
 \lambda M=0,\qquad\lambda b_1=1.
\]
This also excludes rational functions with arbitrary complex constant
coefficients: the same inconsistency certificate remains valid over C.

### Field-trace lemma and proof

Let K/C(x) be a finite algebraic extension of degree d. The derivation
d/dx extends uniquely to K: for an algebraic element alpha with minimal
polynomial P, differentiating P(alpha)=0 determines alpha' uniquely because
P'(alpha) is nonzero in characteristic zero. Hence each embedding in a
normal closure commutes with differentiation, and therefore
\[
 (\operatorname{Tr} r)'=\operatorname{Tr}(r').
\]
If an algebraic row r solved (11), applying normalized trace entrywise would
produce
\[
 \bar r:=\frac1d\operatorname{Tr}_{K/C(x)}r\in C(x)^9,
 \qquad
 \bar r'+\bar r\mathsf R=\frac4x e_0^T.
\]
This contradicts the rational inconsistency certificate. Consequently,
\[
 \boxed{\text{Equation (11) has no row algebraic over }\mathbb C(x).} \tag{12}
\]
A finite radical substitution or finite algebraic covering cannot evade
this conclusion for a universal linear boundary primitive of this same
module.

This strengthens the previous note's statement, which had explicitly left
algebraic boundary coefficients open. It does NOT exclude identities of
the seeded solution, transcendental coefficients, other kinds of boundary
identities, or finite relations among the definite periods in (8).

## 6. Executed checks and numerical comparison

`verify.py` passes 32 exact algebra/implementation checks. They include
the inherited numerator substitution, reflection, beta Jacobian, fixed
Horn coefficient grouping, full r6 weights, preservation of every old
expression field, and the rerun rational obstruction. These are not
32 independent summation theorems.

`check_numerical.py` directly integrates the three new symmetric Gauss
products. Reflection reduces the interval to x in (0,1/2), and x=y^2
removes the algebraic endpoint singularity. The zero-balanced expansion
[2] is used near zero to avoid forming 1-y^2 after it has rounded to one.

The individually evaluated pairings begin
\[
 \begin{aligned}
 {\mathfrak B}_{1/2,1/2}&=6.03746946934458196727653051153459070225769020723630\ldots,\\
 {\mathfrak B}_{1/2,1}&=4.79573978274739849745747305834449820226697076621543\ldots,\\
 {\mathfrak B}_{1,1}&=3.89835631290878202888347516724663674009835142856836\ldots.
 \end{aligned}
\]
They assemble to
\[
 P_a=334926.045248051837883222001240077786613085905253136679683127
 \ldots.
\]

| Working decimal digits | Absolute difference from inherited Pa interval midpoint |
|---:|---:|
| 60 | \(7.886\times10^{-56}\) |
| 90 | \(1.448\times10^{-85}\) |

These differences are floating-point cross-checks. They are not a new
rigorous enclosure, and no certified accuracy is inferred from working
precision. The old interval is a comparison source only, not an input to
the new integrands. The exact algebra proves the replacement.

No new numerical interval for the complete coefficient is constructed in
this continuation. The previously certified value of the retained
representation and its upstream qualifications are unchanged.

## 7. Reproduction

Requires Python 3, SymPy, and mpmath.

```text
python verify.py
python check_numerical.py 60
python check_numerical.py 90
```

`results/updated_expression.json` retains the full input and adds the
optional reduction. `results/exact_checks.json` records the checks.
`results/boundary_obstruction.json` contains the exact left-null
certificate. Numerical comparisons are in `results/numerical_60.json`
and `results/numerical_90.json`.

## Sources and provenance

Input mathematical identities: the supplied `C6_even_sector_expression.json`,
especially `optional_bailey_primitive_reduction`, and the supplied
`C6_even_sector_derivation.md`, Section 8, for the rational-boundary obstruction.
The original source repair and graph/RG assumptions are not independently
rederived here.

[1] NIST DLMF 5.12.1, Euler beta integral:
https://dlmf.nist.gov/5.12

[2] NIST DLMF 15.8, Gauss connection and zero-balanced limiting formulas:
https://dlmf.nist.gov/15.8

[3] NIST DLMF 15.6, Euler integral representations, used for endpoint behavior:
https://dlmf.nist.gov/15.6

The cancellation (5), its symmetric/Horn insertion, and the normalized-trace
argument are derived explicitly in this note; they are not attributed to
the general DLMF references.
