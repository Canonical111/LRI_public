# A one-index Meijer-G representation of the cubic primitive

## Result and scope

The starting point is the supplied cubic primitive, with
`Pa = 2*pi^2*PaCubic` and contribution `96*Pa = 192*pi^2*PaCubic`
to `r6 = 2187*C6(1)`. Its identification with the Gauss-product integral,
the earlier cubic contour identity, the source correction, and the upstream
physical graph/RG identification are inherited. This note does not re-prove
the physical graph calculation.

The new step is a Chebyshev projection and Parseval reduction. It replaces the
cubic two-index harmonic sum by ONE absolutely convergent series with three
explicit ordinary univariate Meijer-G coefficient families. No coefficient is
a new integral, a parameter derivative, or a hidden finite convolution. Each is
a fixed standard G_(4,4) value at 1, with parameters 1/2, 0, and +/- an integer.

This is NOT a finite special-value-only closed form. The new series is signed,
instead of termwise positive. Raw convergence is algebraic. The older geometric
primitive evaluator remains a useful alternative. No bivariate function is used.
The other C6 blocks and the known polynomial are unchanged.

## 1. Self-contained replacement

For every integer n>=0 define
\[
 \mathcal G_{j,n}=G_{4,4}^{j,4-j}\!\left(
 1\;\middle|\;
 \begin{matrix}(1/2)^{[4]}\\0^{[j-1]},n,0^{[3-j]},-n\end{matrix}
 \right),\qquad j=1,2,3.
\]
The first 4-j upper parameters and first j lower parameters are numerator
gamma groups, as in the ordinary Mathematica MeijerG convention. Empty lists
are allowed. In particular the complete Wolfram splits are

```wolfram
G1[n_] := MeijerG[{{1/2,1/2,1/2},{1/2}},{{n},{0,0,-n}},1];
G2[n_] := MeijerG[{{1/2,1/2},{1/2,1/2}},{{0,n},{0,-n}},1];
G3[n_] := MeijerG[{{1/2},{1/2,1/2,1/2}},{{0,0,n},{-n}},1];
```

Set the finite quadratic polynomial
\[
 \Phi_n=10\mathcal G_{1,n}^2+21\mathcal G_{1,n}\mathcal G_{2,n}
       +18\mathcal G_{2,n}^2+15\mathcal G_{2,n}\mathcal G_{3,n}.
\]
Then
\[
 \boxed{P_a=8\pi^3\left[\Phi_0+2\sum_{n=1}^{\infty}(-1)^n\Phi_n\right],}
\]
\[
 \boxed{\mathscr P_c^{(3)}=4\pi\left[\Phi_0+2\sum_{n=1}^{\infty}(-1)^n\Phi_n\right].}
\]
The full primitive contribution is
\[
 \boxed{96P_a=768\pi^3\left[\Phi_0+2\sum_{n=1}^{\infty}(-1)^n\Phi_n\right].}
\]
The factor two for positive n comes from the cosine norm, not a reflection
factor inserted a second time. The zeroth mode is included ONCE.

At n=0, contour reflection gives G_(3,0)=G_(1,0). Thus
\[
 \Phi_0=10g_{13}^2+36g_{13}g_{22}+18g_{22}^2,
\]
where the already retained lower-period values satisfy
\[
 g_{13}=\pi U_4,\qquad g_{22}=\pi^2U_6/2.
\]
This Fourier zeroth mode is not the old double sum's (m,n)=(0,0) summand.
It stays in the primitive; no polynomial compensation is made.

## 2. Retained primitive basis

Let
\[
 v(x)={}_2F_1(1/4,1/4;1;x),\quad
 h(x)={}_2F_1(1/4,1/4;1/2;x),\quad Q=\Gamma(1/4)^4/\pi,
\]
\[
 p_0=v^2,\quad p_1=\sqrt Q\,v(x)h(1-x),\quad p_2=Qh(1-x)^2.
\]
Use the proof-only pairing
\[
 \langle f,g\rangle=\int_0^1\frac{f(x)g(1-x)}{\sqrt{x(1-x)}}\,dx.
\]
The supplied cubic identity is
\[
 P_a=60\pi\langle p_1,p_2\rangle-60\pi^2\langle p_0,p_2\rangle
       +24\pi^2\langle p_1,p_1\rangle+56\pi^4\langle p_0,p_0\rangle.
\]
The supplied standard-primitive derivation identifies
\[
 g_j(x)=G_{3,3}^{j,3-j}(x\mid(1/2)^{[3]};0^{[3]})
\]
by
\[
 g_1=\sqrt\pi p_0,\quad
 g_2=(p_1-\pi p_0)/\sqrt\pi,\quad
 g_3=(p_2-2\pi p_1)/(2\pi^{3/2}).
\]
Substitution and reflection symmetry give
\[
 P_a=8\pi^3\{10\langle g_1,g_1\rangle+21\langle g_1,g_2\rangle
            +18\langle g_2,g_2\rangle+15\langle g_2,g_3\rangle\}.
\]
This uses an inherited identity, not a new contour relation.

## 3. Compute each Chebyshev coefficient as an ordinary G_(4,4)

Let T_n be the ordinary Chebyshev polynomial of the first kind and use
T_n(1-2x). The weight dx/sqrt(x(1-x)) becomes d(theta) for
x=(1-cos(theta))/2, 0<theta<pi.

Euler beta integration, or its terminating Gauss specialization, gives
\[
 \int_0^1\frac{x^{-s}T_n(1-2x)}{\sqrt{x(1-x)}}\,dx
 =\sqrt\pi\,\frac{\Gamma(1/2-s)\Gamma(s+n)}
 {\Gamma(s)\Gamma(n+1-s)},\qquad\Re s<1/2.
\]
Equivalently, after division by B(1/2-s,1/2), the result is
(s)_n/(1-s)_n. The identity extends analytically across removable factors;
the working contour is Re(s)=1/4 and encounters none of them.

The standard inverse-Mellin kernel for g_j is
\[
 M_j(s)=\frac{\Gamma(s)^j\Gamma(1/2-s)^{3-j}}
 {\Gamma(1-s)^{3-j}\Gamma(1/2+s)^j}.
\]
Multiplying by the evaluated Chebyshev beta moment gives
\[
 \frac{\Gamma(s)^{j-1}\Gamma(s+n)\Gamma(1/2-s)^{4-j}}
 {\Gamma(1-s)^{3-j}\Gamma(1/2+s)^j\Gamma(n+1-s)},
\]
which is EXACTLY the kernel of G_(j,n) specified in Section 1. Therefore
\[
 \boxed{\int_0^1\frac{g_j(x)T_n(1-2x)}{\sqrt{x(1-x)}}\,dx
        =\sqrt\pi\,\mathcal G_{j,n}.}
\]
There is no parameter derivative or implicit finite sum in this identification.

### Interchanging the integrals

On s=1/4+it, gamma reflection yields
\[
 M_j(s)=\left[\frac{\Gamma(s)}{\Gamma(s+1/2)}\right]^3
              \tan^{3-j}(\pi s),
\]
with |tan(pi s)|=1. Gamma-ratio asymptotics imply
|M_j(1/4+it)|=O((1+|t|)^(-3/2)). This is integrable.
Since |T_n(1-2x)|<=1, the x integral of its absolute majorant is at most
B(1/4,1/2). Thus Fubini applies absolutely. The specified G44 contours also
converge without regularization.

## 4. Parseval removes one infinite index

The normalized cosine coefficients of
F_j(theta)=g_j((1-cos(theta))/2) are G_(j,n)/sqrt(pi).
Chebyshev orthogonality gives norm pi at n=0 and pi/2 at n>0.
Reflection x->1-x multiplies the nth coefficient by (-1)^n.
Consequently Parseval gives
\[
 \boxed{\langle g_j,g_k\rangle=
 \mathcal G_{j,0}\mathcal G_{k,0}
 +2\sum_{n=1}^{\infty}(-1)^n\mathcal G_{j,n}\mathcal G_{k,n}.}
\]
Inserting this into Section 2 proves the advertised one-index primitive.

This is not the relabeling k=m+n of a double sum: every coefficient in the
remaining index n has the single ordinary G44 evaluation in Section 1.

### Absolute convergence

Near x=0 the g_j grow at most as log^2(x), and near x=1 they are bounded.
Their squares are integrable against dx/sqrt(x(1-x)), so their cosine
coefficient sequences are in l^2. Cauchy-Schwarz makes every product series
in the Parseval formula absolutely convergent. The quadratic sum Phi_n
therefore converges absolutely after multiplication by (-1)^n as well.
No claim of termwise positivity or geometric convergence is made.

## 5. One scalar three-term recurrence for the coefficients

The same coefficient families obey, for n>=1,
\[
 \boxed{(2n+1)^3\mathcal G_{j,n+1}
 -4n(4n^2+1)\mathcal G_{j,n}
 +(2n-1)^3\mathcal G_{j,n-1}
 =\frac{32(j-2)n(-1)^n}{\pi}.}
\]
The six seeds are the finite G44 values at n=0 and n=1. The middle family is
homogeneous; the first and third have equal opposite sources. This recurrence
is optional numerical machinery, not a hidden definition needed by the formula.

Here is an analytic derivation. The common differential equation
[theta_x^3-x(theta_x+1/2)^3]g=0 becomes
\[
 8(\cos\theta-1)F'''-12\sin\theta F''
 +(2-6\cos\theta)F'+\sin\theta F=0.
\]
Test against sin(n theta) and integrate by parts. The adjoint's three cosine
coefficients are
\[
 \tfrac12(2n+1)^3,\quad -2n(4n^2+1),\quad \tfrac12(2n-1)^3.
\]
The endpoint theta=0 contributes zero: its potentially singular factors are
O(theta log^2 theta). At theta=pi the only surviving boundary term is
16 n (-1)^n F'_j(pi). Gauss connection formulas (or the established elliptic
transform together with Legendre's relation) give
\[
 F'_1(\pi)=1/\sqrt\pi,\quad F'_2(\pi)=0,\quad F'_3(\pi)=-1/\sqrt\pi.
\]
Dividing by sqrt(pi) and multiplying by two gives the displayed recurrence.
The nonzero boundary terms are essential; dropping them would incorrectly make
all three sequences homogeneous.

## 6. Effect on C6 and verification

In the current self-contained expression make only the replacement
\[
 192\pi^2\mathscr P_c^{(3)}
 \longmapsto
 768\pi^3[\Phi_0+2\sum_{n\ge1}(-1)^n\Phi_n].
\]
The known polynomial, wheel, seventh sector, and all finite terms are unchanged.
No source repair is removed or added twice. The old double sum is retained in
inputs as provenance.

The finite exact verifier checks 44 polynomial/kernel/normalization identities.
The numerical script evaluates coefficients by two separate routes:
(1) the new G44 Barnes kernel; (2) real Chebyshev moments of the retained
elliptic/Gauss kernels. These are tested for j=1,2,3 and n=0,1,2,3,8.
The recurrence is compared to the independent Barnes values at n=2,3,8.
The original quartic Gauss primitive is independently integrated as a reference.

Runs at 35 and 45 decimal working digits are in results/. At 45 digits the
largest coefficient discrepancy is below 1.095e-47, and the largest recurrence
comparison discrepancy is below 5.255e-46. The old Gauss quadrature gives

    Pa = 334926.045248051837883222001240077786613085905...

Literal new partial sums, retaining 0<=n<N, give:

| N | Pa partial | Partial minus original Gauss quadrature |
|---:|---:|---:|
| 32 | 334904.8520212503683489451191052896497414 | -21.1932268015 |
| 128 | 334924.5469983306249777017198486851982924 | -1.49824972121 |
| 512 | 334925.9395741682625891898791494471742466 | -0.105673883575 |
| 2048 | 334926.0378693920353407729194543391357550 | -0.00737865980254 |

These are literal finite sums, not high-precision approximations to the infinite
value. No new rigorous tail/rounding certificate is claimed. The analytic proof
of the infinite identity is Parseval with the explicit coefficient transform.
No complete all-sector C6 evaluation was performed, and the Wolfram file has not
been run in a Wolfram kernel. Its expressions are supplied for execution there.

## References and inherited inputs

- Supplied C6_primitive_cubic_derivation.md: cubic polynomial, normalization,
  unweighted pairing identity, inherited physical identification.
- Supplied C6_standard_primitive_derivation.md: the g_j-to-p_i basis transform.
- Supplied C6_current_self_contained.wl: current coefficient, retained unchanged.
- NIST DLMF 16.17: standard univariate Meijer-G definition and gamma-group splits.
  https://dlmf.nist.gov/16.17
- NIST DLMF 18.3: shifted Chebyshev weight and normalization.
  https://dlmf.nist.gov/18.3
- NIST DLMF 18.2(viii): completeness of orthogonal polynomials.
  https://dlmf.nist.gov/18.2#viii
- NIST DLMF 5.12: Euler beta integral.
  https://dlmf.nist.gov/5.12
- NIST DLMF 5.11(iii): gamma-ratio asymptotics.
  https://dlmf.nist.gov/5.11#iii
- NIST DLMF 15.8: Gauss connection and endpoint formulas.
  https://dlmf.nist.gov/15.8
- Wolfram Language MeijerG documentation: native parameter convention.
  https://reference.wolfram.com/language/ref/MeijerG.html

The Chebyshev coefficient transform and its application to this exact primitive
are derived in this note. The references supply the standard special-function
and orthogonality facts, not a published C6 evaluation.
