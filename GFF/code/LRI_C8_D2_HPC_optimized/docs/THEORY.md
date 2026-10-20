# Eighth order in two dimensions

This package extends the supplied two-dimensional, seventh-order calculation
to the coefficient of epsilon to the eighth power in the energy-operator
dimension. It uses the same finite zero-momentum prescription, graph weights,
and mixed logarithmic/local-mass forests as the supplied C7 package. The
derivations below specify the extension. A numerical value for the physical
coefficient requires a complete integration of the required graph classes;
the analytic inputs and assembly checks by themselves do not supply that value.

The source equations are in `long_range_ising_condensed.tex`, supplied with the
task: sections labelled `cn:finiteAssembly`, `app:C7d2`, and `app:C8complete`.
The last section concerns one dimension; its eighth-order counting and
topological graph inventory are useful cross-checks, while its coordinate-space
numerics are a different prescription from the two-dimensional Schwinger
calculation used here.

## Physical convention and required information

At fixed dimension d = 2, write

\[
\epsilon=2s-2,\qquad
\Delta_{\mathcal E}=1-\frac{\epsilon}{2}
+\widehat\gamma_r(g_*,\epsilon),
\]

\[
\widehat\beta(g,z)=-zg+\sum_{L=1}^8\widehat b_L(z)g^{L+1},
\qquad
\widehat\gamma_r(g,z)=\sum_{L=1}^8\widehat c_L(z)g^L,
\qquad \widehat b_1=3,\quad\widehat c_1=1.
\]

The independent analytic regulator z is set equal to epsilon only after
retaining the required Taylor coefficients. For C8 these are:

| Loop order L | Highest regulator power | Number of coefficients per channel |
|---:|---:|---:|
| 2 | 6 | 7 |
| 3 | 5 | 6 |
| 4 | 4 | 5 |
| 5 | 3 | 4 |
| 6 | 2 | 3 |
| 7 | 1 | 2 |
| 8 | 0 | 1 |

The one-loop coefficients are exact constants. Both coupling and mass jets
must be retained. Reusing only the seventh-order moments loses one newly
required coefficient at every lower loop order. Substitution of only the
constant regulator coefficients into a regulator-independent MS polynomial
also gives a different truncated problem.

## Graph classes, weights, and exclusions

An L-loop class has L+1 vertices and 2L individually labelled internal lines.
For multiplicities m_ij and external half-edge counts e_i = 4 - degree(i),

\[
D_G=|\operatorname{Aut}G|\prod_{i<j}m_{ij}!\prod_i e_i!,\qquad
s_G=\sum_i e_i(e_i-1),
\]

\[
w_A=\frac{24}{D_G},\qquad
w_B=\frac{s_G}{12}w_A,\qquad
3w_B-w_A=\frac{6(s_G-4)}{D_G}.
\]

A proper one-particle-irreducible subgraph with v vertices and e internal
lines is logarithmic when e = 2v - 2 and is an unmarked power-divergent
two-point subgraph when e = 2v - 1. With h = e - v + 1, the latter has h = v.
Enumeration must include non-induced edge subgraphs, nested subgraphs, and
the compatible mixed forests; an induced-vertex-only search needs an
independent completeness check.

The supplied manuscript reports 26,540 nine-vertex classes at eighth order,
7,231 containing a power-divergent subgraph, and 248 primitive classes. These
are topology checks for the new inventory. Its reported 3,908 coordinate-forest
zeros in one dimension are not a certificate of the zero list for the
two-dimensional mixed Schwinger kernel.

The seventh-order reference inventories already contain 2,441 nonzero
power-free kernels, including 44 primitives, and 709 nonzero power-containing
kernels. The C7 integration retained only 2,298 and 590 of them respectively,
because it could omit the final-order classes with s_G = 4. At eighth order,
the additional 143 power-free and 119 power-containing classes must be
restored: the seventh loop is now a lower-loop input. Their kernel files are
present in the supplied reference inventories even though the C7 production
pack omitted them. The resulting seventh-loop inventory has 3,150 nonzero
kernels. Exact forest zeros remain excluded.

## Mixed forest kernel

Let

\[
U_G(x)=\sum_T\prod_{e\notin T}x_e,\qquad S(x)=\sum_e x_e,
\qquad d\Omega=\delta(1-S)\prod_e dx_e.
\]

For a compatible mixed forest F, U_F is the product of block Symanzik
polynomials after contracting children. Equivalently, retain a co-tree
monomial m exactly when |m intersect E_gamma| = h_gamma for every selected
subgraph gamma. If F_log is the logarithmic part of F, set

\[
E_R^{\log}(F)=E_G\setminus\bigcup_{\gamma\in F_{\log}}E_\gamma.
\]

The inherited full finite kernel is

\[
K_G(x)=\sum_F(-1)^{|F|}
\frac{\sum_{e\in E_R^{\log}(F)}x_e}{S(x)U_F(x)}.
\]

Only logarithmic subgraphs remove edges from the root numerator. A selected
power subgraph changes the denominator through its local zero-momentum
Taylor subtraction while retaining its interaction order in that numerator.
Removing its edges from the numerator would change the prescription and
already fails the supplied three-loop check.

In the normalization r(2,z) = 1,

\[
\begin{pmatrix}\widehat b_L(z)\\\widehat c_L(z)\end{pmatrix}
=\frac{2(-1)^{L+1}\Gamma(1+Lz/2)}
 {\Gamma(\tfrac12+z/4)^{2L}}
\sum_G\begin{pmatrix}w_A(G)\\w_B(G)\end{pmatrix}
\int d\Omega\,\prod_e x_e^{-1/2+z/4}K_G(x).
\]

The formula applies to both the power-free and power-containing sectors in
the same scheme. Selected denominators and integer numerators are combined
exactly before floating-point evaluation. Numerically large individual
forest terms are not independent integrable observables and must not be
sampled separately.

## Regulator moments and normalization

On a projective chart with one edge fixed to one, define

\[
h(x)=\frac14\sum_e\log x_e-\frac L2\log S(x),\qquad
\mathcal G_L(z)=
\frac{\pi^L\Gamma(1+Lz/2)}{\Gamma(\tfrac12+z/4)^{2L}}.
\]

Since G_L(0) = 1, write log G_L(z) = sum_j ell_j z^j. The coefficients are

\[
\ell_1=L\log 2,\qquad
\ell_j=\frac{(-1)^j\zeta(j)}{j}
\left[\left(\frac L2\right)^j-
\frac{2L(2^j-1)}{4^j}\right],\quad j\ge2.
\]

Equivalently,

\[
\ell_j=\frac{(L/2)^j\psi_{j-1}(1)
-2L(1/4)^j\psi_{j-1}(\tfrac12)}{j!}.
\]

With a_0(x) = 1, the normalized integrand moments follow from

\[
a_n(x)=\frac1n\sum_{j=1}^n
j\left(\ell_j+\delta_{j1}h(x)\right)a_{n-j}(x),
\qquad n\le 8-L.
\]

The overall constant is 2(-1)^(L+1)/pi^L. The generated
`inputs/gamma_d2_8.txt` has one row per loop L = 2,...,8, with fields
`8-L`, this constant, and ell_0,...,ell_6; ell_0 is zero. The file includes
the full six-coefficient logarithmic expansion even when a loop needs
fewer moments, preserving a fixed row format. All 42 retained values (six
normalizations and six sets of ell_0 through ell_5) reproduce the supplied
C7 file at its full 65 significant digits.

## Analytic two-loop input through z^6

The supplied prescription has c2(z) = b2(z)/6 and

\[
\widehat b_2(z)=-6z\left[S_2(z)-\frac2{z^2}\right]
=-6\frac{N(z)-2}{z}.
\]

For a = 1/2 + z/4 and b = 1/2 + 3z/4, the retained representation is

\[
N(z)=4\,{}_3F_2\!\left(\begin{matrix}1,z/2,a\\1-z/2,a+1/2\end{matrix};\frac14\right)
-2W(z)\,{}_3F_2\!\left(\begin{matrix}z,2a,b\\1+z/2,b+1/2\end{matrix};\frac14\right),
\]

\[
W(z)=\frac{\Gamma(1+z)\Gamma(1-z/2)\Gamma(b)^2}
{\Gamma(a)^2\Gamma(2b)}.
\]

N(0) = 2. Consequently, b_(2,j) = -6 [z^(j+1)] N(z), so the additional
coefficient requires the seventh Taylor coefficient of N.

`tools/analytic_inputs.py` obtains that coefficient by finite Taylor
arithmetic on the convergent hypergeometric series. The second 3F2 has an
exactly cancelling upper/lower parameter, 2a = 1+z/2, and is independently
summed as a 2F1 in this implementation. The logarithm of W is differentiated
analytically with polygamma functions. This gives

\[
b_{2,6}=-266.52096796135938173225219261908980094902003629215748\ldots.
\]

At 120 decimal working digits the coefficient series stops after 183 terms.
Two checks evaluate the original 3F2 representation on Cauchy grids
(radius 0.05, 128 nodes) and (radius 0.08, 160 nodes). Their maximum
discrepancy from the Taylor-series results is 5.26 times 10^(-112). The
first six coefficients agree with the supplied C7 input exactly in
binary64, with a maximum high-precision discrepancy of 4.07 times 10^(-70).
The independent identity b_(2,0) = -24 log 2 is also checked, implying
C2(2) = 4 log 2 / 9. The saved file contains 100 significant digits.
These are reproducibility checks of the finite special-function input,
not an uncertainty estimate for the high-loop integrals.

## Fixed-point extraction and eighth-loop channel

Write B(g,z) = 3 + sum_(L=2)^8 b_L(z) g^(L-1). Lagrange inversion with z
held fixed, followed by z = epsilon, gives

\[
C_n(2)=-\frac12\delta_{n1}
+\sum_{k=1}^n\frac1k[g^{k-1}z^{n-k}]
\partial_g\widehat\gamma_r(g,z)B(g,z)^{-k},\qquad C_0=1.
\]

An independent implementation solves

\[
g=\frac13\left[\epsilon-\sum_{L=2}^8
\widehat b_L(\epsilon)g^L\right]\pmod{\epsilon^9}
\]

and substitutes the result into 1 - epsilon/2 + gamma. Nine fixed-point
iterations from g = 0 suffice. The highest-loop contribution is exactly

\[
\boxed{C_8(2)\big|_{\text{loop }8}=
\frac{3c_{8,0}-b_{8,0}}{19683}}.
\]

Thus dC8/db_(8,0) = -1/19683 and dC8/dc_(8,0) = 1/6561. At loop eight,
and only for the final-order extraction, s_G = 4 excludes a graph exactly.
Consequently, the saved separate b8 and c8 sums are representatives of this
complete physical channel: they omit equal cancelling contributions with
3 delta(c8) = delta(b8). They are not the complete individual eight-loop RG
coefficients. In particular, the intermediate fixed-point coupling through
epsilon^8 should not be reported as the full coupling of the supplied scheme.
At loop seven the contribution instead contains

\[
\frac{3c_{7,1}-b_{7,1}}{6561}
+\frac{(3b_{2,0}-2c_{2,0})b_{7,0}-7b_{2,0}c_{7,0}}{19683}.
\]

Even when c_(7,j) = b_(7,j)/3 for a graph, its constant term contributes
b_(2,0) b_(7,0) / 59049, using c_(2,0) = b_(2,0)/6. This proves why the
262 previously excluded seventh-order graph classes must be restored.
Their linear-regulator top-channel combination still vanishes; keeping both
jets uniformly is a straightforward implementation choice.

For fixed loop-one through loop-four inputs, C0 through C8 are affine in
all loop-five through loop-eight jets. Two such high-loop insertions first
appear at order nine. This does not make the entire calculation affine in
the sampled lower-loop inputs.

`tests/assembly_formula.py` compares the univariate iteration and the
bivariate Lagrange formula in 24 exact rational cases. It checks the two
highest-loop derivatives, the reappearance of C7 channel-zero graphs, the
need for the new two-loop moment, and affine dependence on loops five
through eight. Its optional `--production-module` argument compares the
floating-point assembly to these independent exact-rational results.

## Full power correction and interpretation of errors

Let f and p be the power-free and power-containing jets in this one
prescription, and F8 the complete fixed-point coefficient map. The required
coefficient and the power correction are

\[
C_8(2)=F_8(f+p),\qquad
\Delta_p C_8=F_8(f+p)-F_8(f).
\]

The correction includes lower-loop changes inside the nonlinear fixed-point
map. It is not the simple-pole sum of eight-loop power graphs. The small
lower-order power corrections in the supplied calculation are consistency
checks and cannot be imposed as exact constraints at eighth order.

Uncertainty propagation uses whole randomized replicates as its statistical
units and preserves the covariance of all moments and both channels from a
stream. Integration chunks are not additional independent replicates. A
fresh pilot is needed to allocate the eighth-order workload; the old C7
allocation targets a different coefficient and misses the restored classes.
Small pilots may have skewed replicate distributions, as the supplied
one-dimensional eighth-order account explicitly illustrates.

Independent campaigns, half-stream comparisons, lower-order by-products,
precision promotions, and kernel endpoint checks help assess the numerical
calculation. A sampling standard error or an empirical reporting allowance
does not bound an error shared by the graph/renormalization prescription or
the omitted higher powers of the physical epsilon expansion. Extending the
software and reproducing lower orders do not constitute an independent
field-theory derivation of the inherited all-order mixed-forest rule.
