# One bivariate H value for the complete C6 primitive

## Result and scope

Input: the supplied `C6_unrestricted_finite_expression.json`. The starting finite representation contains 22 fixed special-function values. Its primitive sector is

\[
P_a=8\pi^3 S,\qquad S=10H_{11}+21H_{12}+18H_{22}+15H_{23}.
\]

This calculation proves the exact representation compression

\[
\boxed{S=10H_*,\qquad P_a=80\pi^3H_*,\qquad 96P_a=7680\pi^3H_*.}
\]

Here H_* is one fixed bivariate Fox H value of local orders (6,5;3,3), specified below. The shared order remains (0,1;0,0), and all slopes remain one. The previous primitive used four values of local orders (4,3;j,4-j).

This is a compression within the already admitted bivariate function class. It increases parameter complexity. It is not an elementary evaluation, a new arithmetic-independence relation, or an evaluation of the primitive by a univariate function. No unknown period or value of C6 is used to choose a parameter.

The global definite-pairing relation H33+2 H13-H22=0 is an inherited analytic input from the preceding primitive contour derivation. It is not reproved here. The new steps are an algebraic factorization modulo that relation and its conversion to a single standard gamma-product kernel.

Using also the PREVIOUSLY ESTABLISHED sixth-sector packing (two univariate G values into one) gives 18 fixed values overall. No explicit residual sum, integral, derivative, or limit is added to the active coefficient. The known polynomial and source correction are unchanged. The graph/RG identification remains inherited.

## 1. Exact parameter specification

Let lambda be the unique real root in (15,16) of

\[
f(\lambda)=4\lambda^3-112\lambda^2+909\lambda-2250=0.
\]

Equivalently, with principal real inverse cosine,

\[
\lambda=\frac{28+\sqrt{409}\cos\!\left[\frac13\arccos\!\frac{7298}{409\sqrt{409}}\right]}3.
\]

Set

\[
e=\frac{\sqrt{40\lambda-279}}{20},\qquad
\chi=\frac{2(21\lambda-150)}{40\lambda-279},
\]

and, for sigma=+1,-1,

\[
B_\sigma=\frac{21}{20}+\sigma e,\qquad
C_\sigma=\frac\lambda{10}+\sigma e\chi,
\]

\[
\beta_\sigma=\frac1\pi\arctan\!\left(\frac{B_\sigma}{2}
+i\sqrt{C_\sigma-\frac{B_\sigma^2}{4}}\right).
\]

All real square roots displayed are positive. Both radicands C_sigma-B_sigma^2/4 are positive. The principal complex inverse tangent is used; its conjugate supplies the second local parameter. This fixes the branches without a limiting prescription.

For a check of the specification,

\[
\begin{aligned}
\lambda&=15.98484037480277357101233458387959\ldots,\\
\beta_+&=0.35627621787113686543544919374277\ldots
 +0.13875888001191026888369405089220\ldots i,\\
\beta_-&=0.04130739977929640873995188248197\ldots
 +0.33348330689534004546198666319775\ldots i.
\end{aligned}
\]

Define local parameter lists (each pair is parameter,slope)

\[
\mathbf a_\sigma=((1/2,1)^{[4]},(\beta_\sigma,1),(\bar\beta_\sigma,1)),\quad
\mathbf b_\sigma=((0,1)^{[3]},(\beta_\sigma,1),(\bar\beta_\sigma,1)).
\]

Then, in the bivariate H convention of Andrade-Rathie-Farias, Definition B,

\[
\boxed{H_*=H_{0,1;6,5;6,5}^{0,0;3,3;3,3}
\left[\begin{matrix}-:\mathbf a_+;\mathbf a_-\\
(0;1,1):\mathbf b_+;\mathbf b_-\end{matrix}\middle|1,1\right].}
\]

For both local lists the first three upper and first three lower parameters are numerator groups. All remaining local parameters are denominator groups. The shared denominator is Gamma(1-s-t).

## 2. The new value's gamma kernel

To remove notation ambiguity, put

\[
\Psi_\sigma(s)=
\frac{\Gamma(s)^3\Gamma(1/2-s)^3}
{\Gamma(1/2+s)\Gamma(s+\beta_\sigma)\Gamma(1-s-\beta_\sigma)
 \Gamma(s+\bar\beta_\sigma)\Gamma(1-s-\bar\beta_\sigma)}.
\]

The standard inverse-Mellin kernel of H_* is

\[
\frac{\Psi_+(s)\Psi_-(t)}{\Gamma(1-s-t)},
\]

with measure ds dt/(2 pi i)^2 and both upward contours Re(s)=Re(t)=1/4. Its arguments are exactly (1,1). This is a specification of a member of an established function family, not an additional integration operation in the active C6 expression.

The only numerator pole families are the old integers and half-integers. New complex parameters occur in denominator gamma factors and introduce zeros, not new contour-separation difficulties.

## 3. Algebraic reduction of the four pairings

Use the inherited basis

\[
g_j(x)=G_{3,3}^{j,3-j}\left(x\middle|(1/2)^{[3]};0^{[3]}\right),
\]

and the symmetric beta pairing, only in this proof,

\[
\langle u,v\rangle=\int_0^1u(x)v(1-x)\frac{dx}{\sqrt{x(1-x)}}.
\]

The inherited identities are H_jk=<g_j,g_k> and

\[
H_{33}+2H_{13}-H_{22}=0.
\]

In the ordered basis (g1,g2,g3), S has the coefficient matrix

\[
M=\begin{pmatrix}10&21/2&0\\21/2&18&15/2\\0&15/2&0\end{pmatrix}.
\]

The zero pairing has coefficient matrix

\[
N=\begin{pmatrix}0&0&1\\0&-1&0\\1&0&1\end{pmatrix}.
\]

Direct calculation gives

\[
\det(M+\lambda N)=\frac{f(\lambda)}4.
\]

Choosing the specified root makes this matrix rank two and indefinite. Completing the square yields, with P_sigma(z)=z^2+B_sigma z+C_sigma,

\[
\boxed{5[P_+(z)P_-(w)+P_-(z)P_+(w)]
=Q(z,w)+\lambda(z^2+w^2-zw+1),}
\]

where

\[
Q(z,w)=10z^2w^2+\frac{21}{2}(z^2w+zw^2)+18zw+\frac{15}{2}(z+w).
\]

This is an exact polynomial identity subject to f(lambda)=0, not a sampled equality. Before imposing f=0, the left-minus-right difference is precisely f(lambda)/(40 lambda-279).

Set

\[
f_\sigma(x)=g_1(x)+B_\sigma g_2(x)+C_\sigma g_3(x).
\]

Symmetry of the beta pairing and the inherited zero identity now give

\[
\boxed{S=10\langle f_+,f_-\rangle.}
\]

Thus the use of the contour relation is essential: the original kernel is not being asserted to factor pointwise without it.

## 4. Convert the two factors to standard Meijer G kernels

Gamma reflection gives the kernels of g_j as

\[
R(s)^3\tan^{3-j}(\pi s),\qquad R(s)=\frac{\Gamma(s)}{\Gamma(s+1/2)}.
\]

Consequently the kernel of f_sigma is R(s)^3 P_sigma(tan pi s).

Put D_sigma=sqrt((1-C_sigma)^2+B_sigma^2). By construction,

\[
P_\sigma(\tan\theta)=D_\sigma\,
\frac{\sin(\theta+\pi\beta_\sigma)\sin(\theta+\pi\bar\beta_\sigma)}{\cos^2\theta}.
\]

Using sin(pi z)=pi/[Gamma(z)Gamma(1-z)] and the analogous cosine formula turns the right side into a single gamma quotient. It follows that

\[
\frac{f_\sigma(x)}{D_\sigma}=
G_{5,5}^{3,2}\!\left(x\middle|
\begin{matrix}(1/2)^{[3]},\beta_\sigma,\bar\beta_\sigma\\
0^{[3]},\beta_\sigma,\bar\beta_\sigma\end{matrix}\right).
\]

The first two upper half-parameters are numerator groups. The upper denominator list is (1/2,beta_sigma,conjugate beta_sigma); the lower numerator list is (0,0,0), and the lower denominator list is (beta_sigma,conjugate beta_sigma).

The normalization has an unexpectedly simple exact cancellation:

\[
\boxed{D_+D_-=1.}
\]

For a short verification, set z=w=i in the polynomial identity above. The zero-pairing polynomial vanishes there, and Q(i,i)=-8-6i, so

\[
P_+(i)P_-(i)=-\frac45-\frac35i.
\]

Taking moduli gives the displayed result because |P_sigma(i)|=D_sigma.

Beta integration of the two univariate kernels multiplies them by
Gamma(1/2-s) Gamma(1/2-t)/Gamma(1-s-t). The result is exactly the standard H_* kernel in Section 2. Since D_+D_-=1,

\[
\langle f_+,f_-\rangle=H_*.
\]

This proves S=10H_* and all primitive normalizations stated at the start.

### Convergence

Each new univariate kernel is a finite linear combination of the old g_j kernels divided by D_sigma. On Re(s)=1/4, |tan(pi s)|=1 and R(s)^3=O((1+|Im s|)^(-3/2)). The two local kernels are absolutely integrable. Before beta integration, the absolute x integral is bounded by B(1/4,1/4). Fubini therefore justifies the beta transform and proves absolute convergence of the bivariate value. No regularization or parameter limit is used.

## 5. Already available sixth-sector compression

The input writes B6=192 pi(13 X35+11 X44). Reuse the previously established identity

\[
\alpha_6=\pi^{-1}\arctan(11/13),\qquad
G_6=G_{7,7}^{4,5}\!\left(1\middle|(1/2)^{[6]},\alpha_6;0^{[6]},\alpha_6\right),
\]

\[
\sqrt{290}\,G_6=13X_{35}+11X_{44},\qquad
B_6=192\pi\sqrt{290}\,G_6.
\]

This is the prior sine-addition packing, not a second new summation theorem. Its Wolfram splits are upper numerator (1/2)^5, upper denominator (1/2,alpha6); lower numerator 0^4, lower denominator (0,0,alpha6).

## 6. Full coefficient, preservation and counts

The full updated expression, with all untouched definitions, is `FORMULA.md` and `results/expression.json`. Only the primitive four-value block and the sixth-power two-value block change. The master expression is

\[
\begin{aligned}
2187C_6(1)={}&E+B_{pol}+B_{low}+192\pi\sqrt{290}G_6+B_8
-9432\pi^3F_4-5895\pi^4F_6\\
&+96\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}
[b_r Z_r-98p_r\nu_r J_r]+7680\pi^3H_*.
\end{aligned}
\]

The displayed sum has five terms. No infinite series or integral is present in the active formula. Counts change as follows: bivariate H 4->1, ordinary Meijer G 4->3, and the other counts stay at 2 multiple polylogarithms, 5 ordinary pFq and 7 Kampe de Feriet values. Total 22->18; this is an occurrence count, not the transcendence degree.

The full 18-monomial known polynomial and repaired source contributions are preserved exactly. Wheel zero-index handling and all seventh coefficients are unchanged. No new all-sector value or interval certificate is claimed.

## 7. Executed verification

`python build_verify.py` passes 39 finite exact checks: the determinant, root isolation, polynomial factorization, normalization, beta-pairing substitution, function parameter lengths, complete C6 substitution, value counts, and preservation of every unaffected block and source correction.

`python numerical.py --dps 40 --meijer` and the same command at 70 working digits were executed. Six separate direct mpmath Meijer G evaluations per run check the local G_(5,5) identification; six complex-contour gamma-product checks per run check its kernel. The new H_* is evaluated by its proved beta-pairing representation. It was not independently computed by two-dimensional Barnes integration.

At 70 working digits:

- H_* = 135.0234860111609249908488197821688196879586538126766890134710495752391...
- P_a = 334926.0452480518378832220012400777866130859052531366796831274570505828...
- The new primitive and a separately integrated original symmetric quartic primitive agree after rounding at the working precision.
- The largest of the six local direct Meijer G discrepancies is below 4.347e-70.
- At 40 working digits the primitive discrepancy is below 6.019e-36.

These are floating-point cross-checks, not rigorous error certificates. No Wolfram kernel was used. The exact algebra is conditional on the inherited global primitive identity and the previously established local g_j identifications.

## References and provenance

1. Supplied `C6_unrestricted_finite_expression.json`: current 22-value input, normalization, polynomial, and coefficients.
2. Supplied `C6_standard_primitive_derivation.md`, Sections 3-5: inherited g_j basis, beta pairings, and H33+2 H13-H22=0.
3. Supplied `C6_sixth_MeijerG_derivation.md`: already established two-to-one sixth-sector packing.
4. J. A. A. Andrade, P. N. Rathie, R. B. A. Farias, *Exact Bayesian computation using H-functions*, Computational and Applied Mathematics 37 (2018), 2277-2293, Definition B, equations (4)-(8). DOI: 10.1007/s40314-017-0451-z. Used only for the bivariate H convention, not as a source of this primitive identity.
5. NIST DLMF 5.5, 5.11, 5.12, 16.17: gamma reflection/asymptotics, beta integration, and ordinary Meijer G normalization.
