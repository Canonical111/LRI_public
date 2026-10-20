# C6(1): the last custom primitive becomes four fixed bivariate H-values

## Result, input, and scope

Input: `inputs/seventh_expression.json`, the supplied
`C6_standard_seventh_expression.json`. The normalization is `r6=2187*C6(1)`.

The new replacement is

\[
\boxed{P_a=8\pi^3\left(10\mathfrak G_{11}+21\mathfrak G_{12}
                         +18\mathfrak G_{22}+15\mathfrak G_{23}\right).} \tag{1}
\]

The four quantities on the right are fixed values of the **standard bivariate
Fox H-function**, with all slope parameters equal to one. They therefore belong
to its bivariate Meijer G subclass. Their complete published-function parameter
specification is in Section 1. They are not definitions of new project-specific
series or unevaluated graph masters.

This expands the accepted standard-function class beyond Kampe de Feriet;
it does **not** give an ordinary one-variable hypergeometric evaluation or a
reduction in arithmetic period dimension. It replaces one custom double sum by
four standard bivariate values, not by fewer total transcendental inputs. It
requires no third or fourth function variable.

The project-specific symmetric/cubic primitive identity is an inherited input.
The new steps are the Meijer G identification of its three Frobenius solutions,
the absolutely convergent beta-to-bivariate-H transform, and the complete finite
weighted substitution. All other sectors and the upstream graph/RG identification
remain inherited. No new full-C6 interval certificate or physical identification
is claimed.

## 1. Four fixed values in a published normalization

Use the bivariate H convention in Andrade, Rathie, Farias [1], Definition B,
equations (4)-(8). A local pair `(a,A)` denotes a gamma parameter and its slope;
a shared triple `(b;B,C)` denotes its parameter and two slopes. Repeated lists
are denoted by a superscript `[r]`.

For the four index pairs `(j,k)=(1,1),(1,2),(2,2),(2,3)`, put

\[
\boxed{
\mathfrak G_{jk}=
H_{0,1;\,4,3;\,4,3}^{0,0;\,j,4-j;\,k,4-k}
\!\left[
\begin{matrix}
-:(\tfrac12,1)^{[4]};(\tfrac12,1)^{[4]}\\
(0;1,1):(0,1)^{[3]};(0,1)^{[3]}
\end{matrix}\;\middle|\;1,1\right].} \tag{2}
\]

The index `j` changes which gamma factors are in the numerator; it is **not**
a derivative order. Specifically the orders are:

| Value | Shared `(p,q;m,n)` | First local `(p,q;m,n)` | Second local `(p,q;m,n)` |
|---|---|---|---|
| G11 | (0,1;0,0) | (4,3;1,3) | (4,3;1,3) |
| G12 | (0,1;0,0) | (4,3;1,3) | (4,3;2,2) |
| G22 | (0,1;0,0) | (4,3;2,2) | (4,3;2,2) |
| G23 | (0,1;0,0) | (4,3;2,2) | (4,3;3,1) |

All four arguments are the same point `(1,1)`. The only gamma parameters are zero
and one-half, and every slope is one. Repeated zero lower parameters are allowed;
there is no parameter limit or regularization.

To remove convention ambiguity, the Mellin-Barnes kernel specified by (2) is

\[
\mathfrak G_{jk}=\frac1{(2\pi i)^2}
\int_{\Re s=1/4}\int_{\Re t=1/4}
\frac{\Gamma(s)^j\Gamma(\tfrac12-s)^{4-j}
      \Gamma(t)^k\Gamma(\tfrac12-t)^{4-k}}
{\Gamma(1-s)^{3-j}\Gamma(\tfrac12+s)^j
 \Gamma(1-t)^{3-k}\Gamma(\tfrac12+t)^k\Gamma(1-s-t)}\,dt\,ds. \tag{3}
\]

Both contours run upward. Equation (3) states the defining kernel of the
**already established function** in (2); it is not an additional residual in the
active C6 formula. Absolute convergence on these exact contours is proved below.

## 2. Complete C6 substitution, without a polynomial shift

The current coefficient is

\[
\begin{aligned}
2187C_6(1)={}&E_{\rm KdF}
+208896\Re\mathcal L_{01110}(i)\\
&+13056(32G-3\pi^2)\Im\operatorname{Li}_3((1+i)/2)\\
&+\mathcal H_{\rm even}+\mathcal H_7+192\pi^2\mathscr P_c^{(3)}.
\end{aligned}
\]

Here the two H blocks are exactly the finite expressions called
`standard_even_values` and `standard_seventh_values` in the input, not new
special functions. Their complete rational parameter lists and coefficients are
preserved verbatim in `results/updated_expression.json`.

The inherited normalization is `P_a=2*pi^2*PaCubic`. Hence (1) gives

\[
\mathscr P_c^{(3)}=4\pi(10\mathfrak G_{11}+21\mathfrak G_{12}
                                  +18\mathfrak G_{22}+15\mathfrak G_{23}),
\]

and the full new coefficient is

\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_{\rm KdF}+208896\Re\mathcal L_{01110}(i)\\
&+13056(32G-3\pi^2)\Im\operatorname{Li}_3((1+i)/2)\\
&+\mathcal H_{\rm even}+\mathcal H_7\\
&+768\pi^3(10\mathfrak G_{11}+21\mathfrak G_{12}
                    +18\mathfrak G_{22}+15\mathfrak G_{23}).
\end{aligned}} \tag{4}
\]

No term is extracted from an old series. The exact known shift is zero.
The known polynomial still has 21 expanded monomials. In compact form, using
`A=pi+4 log(2)`, `Q=Gamma(1/4)^4/pi`, `G=Catalan`, it is

\[
\begin{aligned}
E_{\rm KdF}={}&-144Q^3/\pi
+\frac Q8[63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)]\\
&+Q^2(29\pi-249A)
+\frac{21}{640}A^5+\frac7{64}A^3\pi^2+\frac{6045}{64}A^2\pi^3
+\frac{7863}{16}A^2\zeta(3)\\
&-\frac{83067}{640}A\pi^4+\frac{164927}{128}\pi^5
+\frac{4301}{16}\pi^2\zeta(3)-\frac{805959}{8}\zeta(5)\\
&+3072G^2(18A-17\pi)-48\pi G(17A^2+56A\pi+153\pi^2).
\end{aligned} \tag{5}
\]

The previously included source repair is preserved exactly once.
The old cubic sum remains available under a `legacy_...` field for provenance,
but is absent from the active coefficient and the active auxiliary list.

## 3. Identify the logarithmic solutions as ordinary Meijer G-functions

For the proof, retain the input kernels and products

\[
v(x)={}_2F_1(\tfrac14,\tfrac14;1;x),\qquad
h(x)={}_2F_1(\tfrac14,\tfrac14;\tfrac12;x),
\]
\[
p_0=v(x)^2,\quad p_1=\sqrt Q\,v(x)h(1-x),\quad p_2=Qh(1-x)^2.
\]

Define the standard one-variable functions

\[
g_j(x)=G_{3,3}^{j,3-j}\!\left(x\;\middle|\;
\begin{matrix}\tfrac12,\tfrac12,\tfrac12\\0,0,0\end{matrix}\right),
\qquad j=1,2,3,\quad 0<x<1. \tag{6}
\]

In the inverse-Mellin convention, their kernels are

\[
M_j(s)=\frac{\Gamma(s)^j\Gamma(\tfrac12-s)^{3-j}}
{\Gamma(1-s)^{3-j}\Gamma(\tfrac12+s)^j}. \tag{7}
\]

The new exact basis identification is

\[
\boxed{
 g_1=\sqrt\pi\,p_0,\qquad
 g_2=\frac{p_1-\pi p_0}{\sqrt\pi},\qquad
 g_3=\frac{p_2-2\pi p_1}{2\pi^{3/2}}.} \tag{8}
\]

### Proof of (8)

The standard Meijer G differential equation [2,3] gives for every function (6)

\[
[\theta^3-x(\theta+\tfrac12)^3]g_j=0,\qquad \theta=x\partial_x.
\]

The inherited Gauss products `p_i` satisfy that same equation: it is the
symmetric square of

\[
x(1-x)y''+(1-3x/2)y'-y/16=0.
\]

It remains to match their complete leading logarithm polynomials, not just a
single leading coefficient.

Let `L=-log(x)`, `ell=log(2)`. Gamma reflection gives

\[
M_j(s)=\left[\frac{\Gamma(s)}{\Gamma(s+1/2)}\right]^3
                  \tan^{3-j}(\pi s).
\]

The Laurent expansion needed at `s=0` is

\[
\left[\frac{\Gamma(s)}{\Gamma(s+1/2)}\right]^3
=\frac{1}{\pi^{3/2}s^3}
 [1+6\ell s+(18\ell^2-\pi^2/2)s^2+O(s^3)].
\]

The coefficients use `psi(1)-psi(1/2)=2 log(2)` and
`psi1(1)-psi1(1/2)=-pi^2/3` [4]. Together with the appropriate tangent powers,
the three residues of `M_j(s)*x^(-s)` yield

\[
\begin{aligned}
g_1(x)&=\sqrt\pi+O(x),\\
g_2(x)&=(L+6\ell)/\sqrt\pi+O(x|\log x|),\\
g_3(x)&=[(L+6\ell)^2-\pi^2]/(2\pi^{3/2})+O(x\log^2x).
\end{aligned}
\]

The input's zero-balanced Gauss normalization, also following from [5], is

\[
v(x)=1+O(x),\qquad
\sqrt Q h(1-x)=L+\pi+6\ell+O(x|\log x|).
\]

It gives exactly the same three leading polynomials on the right of (8).
The regular-singular equation at zero has exponent zero of multiplicity three.
Its Frobenius recurrence fixes all subsequent coefficients from these three
leading polynomials. Thus (8) holds on `0<x<1`.

No assertion is made that these real-interval identities identify all possible
analytic continuations outside that interval. No derivative appears in (6)-(8).

## 4. Beta integration gives the published bivariate H-values

Let

\[
\langle f,g\rangle=\int_0^1
     \frac{f(x)g(1-x)}{\sqrt{x(1-x)}}\,dx.
\]

This notation is used only in the proof. Inserting the two inverse-Mellin
representations (7), Euler's beta integral [6] gives

\[
\int_0^1x^{-s-1/2}(1-x)^{-t-1/2}dx
=\frac{\Gamma(1/2-s)\Gamma(1/2-t)}{\Gamma(1-s-t)}.
\]

Hence

\[
\boxed{\langle g_j,g_k\rangle=\mathfrak G_{jk}.} \tag{9}
\]

The beta factors add one upper gamma factor `Gamma(1/2-s)` and
`Gamma(1/2-t)` to the two local Meijer kernels, taking their orders from `(3,3)`
to `(4,3)`. Its reciprocal shared gamma factor is exactly the shared lower
triple `(0;1,1)` in (2). This proves the complete parameter identification.

### Absolute convergence and the interchanges

On the vertical line `s=1/4+i u`,

\[
|\tan(\pi s)|=1.
\]

The gamma-ratio asymptotic [7] therefore gives, for **all three** indices,

\[
|M_j(1/4+i u)|=O((1+|u|)^{-3/2}).
\]

Thus each Mellin kernel is in `L^1` on that line. Taking absolute values in the
three integrations before performing the beta integration is bounded by

\[
\frac{B(1/4,1/4)}{(2\pi)^2}
\left(\int_{\mathbb R}|M_j(1/4+i u)|du\right)
\left(\int_{\mathbb R}|M_k(1/4+i v)|dv\right)<\infty.
\]

Fubini is therefore justified. It proves the absolute convergence of the
specific bivariate H-values on the stated straight contours. No angular
continuation limit or regularization is needed at `(1,1)`. The zero lower
parameters produce repeated poles to the **left**, not poles on these contours.

## 5. Why only four values, with small integer weights, survive

The retained pairings are

\[
I_{ij}=\pi^{-i-j}\langle p_i,p_j\rangle.
\]

The inherited contour relation is

\[
I_{22}-4I_{12}+4I_{02}-4I_{00}=0.
\]

It gives the already proved cubic formula

\[
P_a=\pi^4(60I_{12}-60I_{02}+24I_{11}+56I_{00}). \tag{10}
\]

Solving (8) for the `p_i` gives

\[
p_0=g_1/\sqrt\pi,\qquad
p_1=\sqrt\pi(g_1+g_2),\qquad
p_2=2\pi^{3/2}(g_1+g_2+g_3).
\]

Substitute these into (10), and use the symmetry of (9):

\[
\begin{aligned}
P_a/\pi^3
={}&120(\mathfrak G_{11}+2\mathfrak G_{12}+\mathfrak G_{13}
                       +\mathfrak G_{22}+\mathfrak G_{23})\\
 &-120(\mathfrak G_{11}+\mathfrak G_{12}+\mathfrak G_{13})\\
 &+24(\mathfrak G_{11}+2\mathfrak G_{12}+\mathfrak G_{22})
 +56\mathfrak G_{11}\\
={}&80\mathfrak G_{11}+168\mathfrak G_{12}
                 +144\mathfrak G_{22}+120\mathfrak G_{23}.
\end{aligned}
\]

This is (1). In particular, the cross-pair `G13` cancels exactly.

For an alternative check, substitution into the original quartic primitive
produces six values. The old contour relation becomes

\[
\mathfrak G_{33}+2\mathfrak G_{13}-\mathfrak G_{22}=0.
\]

It removes `G33` and `G13` from that six-value result and gives the same (1).
This does not contradict the earlier obstruction to a universal algebraic-row
antiderivative: the contour relation is a global definite-pairing identity.

### Positivity

All `g_j(x)` are positive on `(0,1)`. For `g1` this follows from (8). For the
other two, the Gauss connection formula [5]

\[
v(x)=\frac{\sqrt Q}{2\pi}h(1-x)
 -\frac2{\sqrt Q}\sqrt{1-x}\,
 {}_2F_1(\tfrac34,\tfrac34;\tfrac32;1-x)
\]

shows both `p1-pi*p0>0` and

\[
g_3(x)=\frac2{\sqrt\pi}\sqrt{1-x}\,h(1-x)
 {}_2F_1(\tfrac34,\tfrac34;\tfrac32;1-x)>0.
\]

Consequently the four values in (1) and all their displayed weights are positive.
The primitive contains no hidden cancellation between divergent terms.

## 6. Executed verification and numerical scope

`verify.py` passes **67 finite exact checks**. They cover the symmetric-square
ODE, Frobenius normalizations, the standard-H parameter lists, the full primitive
substitution, the equivalent old contour relation, all four weights, exact
preservation of unaffected input fields, and the unchanged 21-monomial known
polynomial and source repair. These are implementation checks, not 67
independent analytic theorems.

`numerical.py` evaluates the four values using (9), with stable Gauss connection
formulas to avoid subtracting a tiny number from 1 at an endpoint. It compares
24 separate interior values against `mpmath.meijerg`, and separately integrates
the original symmetric quartic primitive. The input primitive interval midpoint
is used only after those evaluations as a comparison, never to determine a
coefficient or a new value.

At 100 decimal working digits the four values begin

\[
\begin{aligned}
\mathfrak G_{11}&=12.24704755370962287559051988381450188657433901589295\ldots,\\
\mathfrak G_{12}&=20.49996005697176236355113720437020598150116868292083\ldots,\\
\mathfrak G_{22}&=30.71452773140303989138578912560755447749764974167425\ldots,\\
\mathfrak G_{23}&=16.29358161419008623153766089538885812049072735175757\ldots.
\end{aligned}
\]

They give

\[
P_a=334926.045248051837883222001240077786613085905253136679683127
4570505827753219951325656148073571261702\ldots.
\]

The measured absolute differences are:

- new four-value primitive versus original symmetric primitive: `<3.746e-96`;
- new primitive versus the inherited rational interval midpoint: `<2.354e-96`;
- the 24 univariate Meijer G point checks: maximum `<3.429e-100`;
- equivalent pairing identity: `<2.286e-100`.

These are **floating-point checks, not newly certified errors**. The bivariate
H integral (3) is identified analytically; it was not independently evaluated by
a second two-dimensional contour-quadrature implementation. The unchanged even,
seventh and polylogarithmic sectors were not freshly evaluated in this pass.
No new full-C6 numerical or interval certification is claimed.

## 7. Resulting standard-function inventory

The active coefficient has no project-defined infinite-sum remainder. It uses
13 ordinary generalized hypergeometric values, 7 Kampe de Feriet values,
4 unit-slope bivariate Fox H values, and the 2 unchanged polylogarithmic values.
These counts exclude elementary/gamma/zeta constants. They are a notation and
representation count, **not** a count of algebraically independent periods.

The next stronger goal is compression within a smaller standard-function class,
particularly ordinary one-variable values. The result here completes removal
of bespoke sum definitions only in the enlarged, at-most-bivariate class.

## Reproduction

Python 3 with SymPy and mpmath; no network access is required for the scripts.

```text
python formula.py
python verify.py
python numerical.py --digits 40
python numerical.py --digits 100
```

`results/updated_expression.json` contains every active parameter list and finite
coefficient. Its `legacy_PaCubic_definition` is provenance, not an active sum.
`results/numerical_100.json` and `results/exact_checks.json` record executed runs.

## References and inherited inputs

[1] J. A. A. Andrade, P. N. Rathie, R. B. A. Farias, *Exact Bayesian computation
using H-functions*, Computational and Applied Mathematics **37** (2018),
2277-2293, published online 6 May 2017. Definition B, equations (4)-(8).
DOI: https://doi.org/10.1007/s40314-017-0451-z . Author-posted text:
https://www.researchgate.net/publication/316770540_Exact_Bayesian_computation_using_H-functions .
Used for the standard function convention, not as a published evaluation of Pa.

[2] NIST DLMF 16.17: https://dlmf.nist.gov/16.17 .

[3] NIST DLMF 16.21: https://dlmf.nist.gov/16.21 .

[4] NIST DLMF 5.15: https://dlmf.nist.gov/5.15 .

[5] NIST DLMF 15.8: https://dlmf.nist.gov/15.8 .

[6] NIST DLMF 5.12: https://dlmf.nist.gov/5.12 .

[7] NIST DLMF 5.11: https://dlmf.nist.gov/5.11 .

[8] Supplied `C6_primitive_central_derivation.md`: common Gauss products,
Frobenius normalization and symmetric primitive. Copied into `inputs/`.

[9] Supplied `C6_primitive_cubic_derivation.md`: the project-specific contour
relation and positive cubic primitive. Copied into `inputs/`. Inherited rather
than independently reproved in this pass.

[10] Supplied `C6_standard_seventh_expression.json`: current complete formula;
`C6_complete_interval_certificate.json`: inherited primitive midpoint used only
for a numerical comparison. Both are copied into `inputs/`.
