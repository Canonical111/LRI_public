# Two exact first moments of the C6 primitive

## Status and normalization

This continuation studies the primitive, not a newly renamed C6 remainder.
The accepted input is `inputs/accepted_expression.json`, copied byte-for-byte
from `C6_lower_MeijerG_expression.json`. Its polynomial, all completed reductions,
and the source correction are unchanged. The latest wheel-curvature work is also
left unchanged.

The two new evaluations are J01 = pi/2 and J12-J02 = pi, with J defined below.
They concern **first moments with weight 2x-1**. The C6 primitive uses unweighted
moments. These identities do not yet give a finite Mathematica-built-in value
for Pa, the wheel, or the seventh logarithmic block. They are not a full C6
closed form, an arithmetic-independence theorem, or a new graph/RG derivation.

## 1. Definitions and results

Retain Q=Gamma(1/4)^4/pi and the Gauss kernels

\[
 v(x)={}_2F_1(1/4,1/4;1;x),\qquad
 h(x)={}_2F_1(1/4,1/4;1/2;x).
\]

Use the normalized products already implicit in the cubic primitive file:

\[
 q_0(x)=v(x)^2,\quad
 q_1(x)=\frac{\sqrt Q}{\pi}v(x)h(1-x),\quad
 q_2(x)=\frac Q{\pi^2}h(1-x)^2.
\]

They are p_i/pi^i in that file. Define proof/diagnostic moments

\[
 I_{ij}=\int_0^1\frac{q_i(x)q_j(1-x)}{\sqrt{x(1-x)}}\,dx,\qquad
 J_{ij}=\int_0^1\frac{(2x-1)q_i(x)q_j(1-x)}{\sqrt{x(1-x)}}\,dx.
\]

Then I_ij=I_ji, J_ij=-J_ji, and J_ii=0. All these finite-interval
integrals converge absolutely: the products have endpoint logarithms of
degree at most two with the integrable inverse-square-root weight.

The exact evaluations are

\[
 \boxed{J_{01}=\frac{\pi}{2},\qquad J_{12}-J_{02}=\pi.}          \tag{1}
\]

These are new first-moment constraints. They are not the inherited unweighted
contour relation

\[
 I_{22}-4I_{12}+4I_{02}-4I_{00}=0.                             \tag{2}
\]

The primitive still is

\[
 \boxed{P_a=\pi^4[60(I_{12}-I_{02})+24I_{11}+56I_{00}].}        \tag{3}
\]

In particular, (1) does NOT replace I12-I02 by pi. That would confuse two
different weights and would be false. No such replacement is made.

## 2. Two holomorphic contour kernels

On the open upper half-plane use the principal Gauss functions and set

\[
 f(z)=v(z),\qquad g(z)=\frac{\sqrt Q}{\pi}h(1-z)-v(z),\qquad
 f_*=f(1-z),\quad g_*=g(1-z).
\]

The star means reflection, not conjugation. Put
r(z)=(f^2,fg,g^2)^T. For two constant matrix pairs define

\[
 {\cal K}_{A,B}(z)=
 \frac{r(z)^T(C_{A,B}+iD_{A,B})r(1-z)}
      {\sqrt z\,\sqrt{1-z}}.
\]

The separate square roots are principal. The matrices are

\[
 C_A=\begin{pmatrix}0&-4&0\\4&0&0\\0&0&0\end{pmatrix},\quad
 D_A=\begin{pmatrix}5&0&-1\\0&0&0\\-1&0&1\end{pmatrix},
\]

\[
 C_B=\begin{pmatrix}0&1&0\\-1&0&-1\\0&1&0\end{pmatrix},\quad
 D_B=\begin{pmatrix}-2&0&0\\0&2&0\\0&0&0\end{pmatrix}.           \tag{4}
\]

The four factors are holomorphic in the upper half-plane. The inherited
Gauss cut-jump and connection formulas give the upper-bank data

| Region | f | g | f_* | g_* |
|---|---|---|---|---|
| x<0 | u | r-iu | a-ib | a+ib |
| x>1 | a+ib | a-ib | u | r+iu |

Here u,r,a,b are real. These are the SAME signs as in the prior cubic contour
derivation, reproduced under `inputs/cubic_derivation.md`.

For both rows, substitution into each numerator in (4) gives a real polynomial.
This is checked identically with arbitrary real u,r,a,b, not at sampled values.
On the exterior intervals,

\[
 (\sqrt{x+i0}\sqrt{1-x-i0})^{-1}
 =\begin{cases}-i/\sqrt{(-x)(1-x)},&x<0,\\
 +i/\sqrt{x(x-1)},&x>1.\end{cases}
\]

Thus Re K_A = Re K_B = 0 there. Multiplication by the real boundary value x
does not change this fact.

## 3. The nonzero boundary at infinity

Multiplying a kernel by z changes its large-arc contribution. It must NOT be
discarded on the ground that the unweighted contour had a vanishing arc.

Let L=log(z)+6log(2) and epsilon=exp(i*pi/4). The equal-upper-parameter
Gauss connection formula, DLMF 15.8.8 with m=0, gives the following leading
terms in the upper half-plane, all after removing z^(-1/4)/pi:

\[
 f:\ \epsilon(L-i\pi)/\sqrt2,\qquad
 g:\ L+\pi-\epsilon(L-i\pi)/\sqrt2,
\]
\[
 f_*:\ L/\sqrt2,\qquad
 g_*:\ \epsilon(L+\pi-i\pi)-L/\sqrt2.
\]

Each omitted term is O(z^(-1)log z) relative to the removed factor.
The constants use
Gamma(1/4)Gamma(3/4)=sqrt(2)pi,
2psi(1)-psi(1/4)-psi(3/4)=6log2,
2psi(1)-2psi(1/4)=pi+6log2.

Substitution in the two numerator polynomials gives, exactly,

\[
 P_A(L)=-2\pi^4,\qquad P_B(L)=-\pi^4.
\]

All powers of L cancel. Since sqrt(z)sqrt(1-z)=-iz(1+O(1/z)),

\[
 {\cal K}_A(z)=-\frac{2i}{z^2}
    +O(z^{-3}(1+\log|z|)^4),\qquad
 {\cal K}_B(z)=-\frac{i}{z^2}
    +O(z^{-3}(1+\log|z|)^4).                   \tag{5}
\]

On the counterclockwise upper semicircle, the integrals of z K_A and
z K_B therefore tend to 2pi and pi, respectively.

IMPORTANT convergence detail: z K has a 1/z tail. The proof uses a finite
closed contour with real segment [-R,R] and takes its REAL PART before
R tends to infinity. It does not add separately convergent complex
integrals on the two exterior half-lines. Their real parts are exactly zero.
Equivalently, a symmetric-cutoff complex contour may be used.
The evaluated finite-interval moments themselves are absolutely convergent.

Near either finite endpoint K=O(distance^(-1/2)(1+|log distance|)^2).
Both small indentation arcs vanish, also after multiplication by z.
There are no upper-half-plane singularities inside the contour.

Cauchy's theorem, including the large arc, now gives

\[
 \Re\int_0^1 x{\cal K}_A(x)\,dx=-2\pi,\qquad
 \Re\int_0^1 x{\cal K}_B(x)\,dx=-\pi.                         \tag{6}
\]

Their real numerators are antisymmetric under x -> 1-x. Hence their
unweighted real integrals vanish, and

\[
 \Re\int_0^1(2x-1){\cal K}_A(x)\,dx=-4\pi,\qquad
 \Re\int_0^1(2x-1){\cal K}_B(x)\,dx=-2\pi.                  \tag{7}
\]

## 4. Convert the real numerators to the original normalized pairings

On 0<x<1,

\[
 q_0=f^2,\qquad q_1=f(f+g),\qquad q_2=(f+g)^2.
\]

Equivalently r=Tq, where

\[
 T=\begin{pmatrix}1&0&0\\-1&1&0\\1&-2&1\end{pmatrix}.
\]

Exact multiplication gives

\[
 T^TC_AT=\begin{pmatrix}0&-4&0\\4&0&0\\0&0&0\end{pmatrix},\quad
 T^TC_BT=\begin{pmatrix}0&0&1\\0&0&-1\\-1&1&0\end{pmatrix}.
\]

Consequently the left sides of (7) are -8 J01 and 2(J02-J12).
Equation (1) follows.

## 5. Equivalent complete-elliptic-integral evaluations

This subsection is an alternative rendering, not a C6 replacement.

Use Mathematica's parameter convention for K=EllipticK, and put

\[
 \lambda(x)=\frac{1-\sqrt{1-x}}2,\quad
 K_x=K(\lambda(x)),\quad K_x^c=K(1-\lambda(x)).
\]

The previously proved kernel transformations are f=2K_x/pi and
g=2K_x^c/pi. By reflection symmetry, the symmetric part in J01 has zero
first moment. Equation (1) therefore also gives

\[
 \boxed{\int_0^1\frac{(2x-1)K_x^2K_{1-x}K_{1-x}^c}
 {\sqrt{x(1-x)}}\,dx=\frac{\pi^5}{32},}                         \tag{8}
\]

\[
 \boxed{\int_0^1\frac{(2x-1)K_xK_x^c(K_{1-x}+K_{1-x}^c)^2}
 {\sqrt{x(1-x)}}\,dx=\frac{\pi^5}{16}.}                         \tag{9}
\]

These finite values are not the even, unweighted quartic combination
required for Pa.

## 6. The whole constant-matrix ansatz

Remove the symmetry assumptions on C,D and allow arbitrary real 3x3
matrices (18 coefficients). Requiring the numerator to be real for BOTH
exterior patterns yields 18 linear equations with exact rank 15.

The nullspace has dimension 3. It is spanned by (C_A,D_A), (C_B,D_B),
and the inherited pair

\[
 C_0=\begin{pmatrix}-3&0&1\\0&-4&0\\1&0&1\end{pmatrix},\quad
 D_0=\begin{pmatrix}0&-4&0\\4&0&0\\0&0&0\end{pmatrix}.
\]

C0 is symmetric; CA and CB are antisymmetric. Therefore the extra two
directions have identically vanishing unweighted real integrals by
reflection parity. The original direction supplies only the already-known
unweighted relation (2). Merely dropping the matrix symmetry assumptions
does NOT give a second independent relation among the unweighted Iij.

This classifies ONLY constant 3x3 bilinear numerators with this specific
boundary-reality mechanism. It does not classify all contour identities,
rational-matrix kernels, transformations, or arithmetic period relations.

## 7. Checks and reproduction

Run

```
python verify.py --digits 50
python verify.py --digits 80
```

The exact script checks both exterior patterns for all three kernels, rank
and nullspace basis, parity, the q-basis transformations, all leading
large-z polynomials, arc signs, and the elliptic normalization factors.

Independent real quadrature folds the interval at 1/2 and sets x=u^4/2.
The complementary elliptic value uses Carlson RF(0,lambda,1), avoiding
cancellation in 1-lambda. At 50 and 80 working decimal digits the two moment
differences from pi/2 and pi round to zero at the working precision.
Those are floating-point checks, NOT a new rigorous interval certificate.

The Wolfram file reproduces the finite polynomial checks and lists the
two exact moment values. It does not claim to return the complete C6 and
has not been run in a Wolfram kernel here.

No full-C6 numerical evaluation, physical graph certification, or new
accepted formula is produced. The current wheel and seventh-logarithmic
targets are unchanged.

## Sources and inherited inputs

1. Supplied `C6_primitive_cubic_derivation.md`: p_i, Iij, the cubic primitive,
   the upper/lower-bank signs, and the old unweighted contour identity.
2. Supplied `C6_Mathematica_native_derivation.md`: the ordinary EllipticK
   identities used for stable independent real quadrature.
3. NIST DLMF 15.8.8, 15.8.10 and 15.12: principal Gauss connection
   formulas, equal-upper-parameter expansions, and asymptotics.
   https://dlmf.nist.gov/15.8
   https://dlmf.nist.gov/15.12
4. NIST DLMF 5.5 and 5.15: gamma reflection and polygamma special values.
   https://dlmf.nist.gov/5.5
   https://dlmf.nist.gov/5.15

The matrices (4), their first-moment evaluations, and the unrestricted
18-coefficient linear-algebra calculation are the work in this continuation,
not results attributed to the general references.
