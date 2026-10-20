# C6(1): real-valued alternatives without quintic parameters

## Scope

The input is the project's nine-value expression in `inputs/C6_seventh_unit_slopes_expression.json`. The later eight-call alternative combines two polylogarithmic components in the real projection of a complex Kampé de Fériet value with five quintic-root parameters. Its own source does not claim an eight-dimensional independent period basis.

The recommended rewrite below uses two established real-valued functions at the real angle pi/2. It keeps nine fixed values and the eighteen-monomial polynomial, and removes explicit Re/Im from the coefficient. The multiple Clausen replacement of D5 is a change of standard real-function convention, not a new summation theorem. The weight-three replacement is a differential identity with an explicit polynomial term.

A second, genuinely transformed real-function specification uses only three log-sine values for the polylogarithmic sector. It has ten fixed values overall. It lowers the weight-five iterated-integral depth from three to two, at the cost of one additional value. Neither version asserts arithmetic independence, minimality, or a new evaluation in gamma/zeta constants.

All seven other fixed values, the source correction, the wheel's zero-index convention, and the inherited graph/RG identifications are unchanged. This calculation has no new full-C6 numerical or interval certificate.

## 1. Established real-function conventions

Following Borwein–Straub [1],
\[
\operatorname{Ls}_3(\sigma)=-\int_0^\sigma
\log^2\!\left|2\sin\frac{\theta}{2}\right|d\theta.
\]
Their multiple Clausen function at odd total weight is the cosine component of the strict descending-index multiple polylogarithm. In particular,
\[
\operatorname{Cl}_{2,1,2}(\sigma)
=\sum_{n>m>k\ge1}\frac{\cos(n\sigma)}{n^2m k^2}.
\]
These are standard function definitions, not additional residual integration/summation operations in the final coefficient. The Clausen convention uses descending indices, as in the input C6 formula.

For the optional single-family version, use Umezawa's iterated log-sine convention [2]:
\[
\operatorname{Ls}_{k_1,\ldots,k_d}^{(0,\ldots,0)}(\sigma)
=(-1)^d\int_{0<\theta_1<\cdots<\theta_d<\sigma}
\prod_{j=1}^d\log^{k_j-1}\!\left|2\sin\frac{\theta_j}{2}\right|
\,d\theta_1\cdots d\theta_d.
\]
The first index belongs to the innermost variable. This convention is independent of that paper's opposite multiple-polylogarithm index ordering.

Set
\[
L=\operatorname{Ls}_3(\pi/2),\quad C=\operatorname{Cl}_{2,1,2}(\pi/2),\quad
U=\operatorname{Ls}_{2,3}^{(0,0)}(\pi/2),\quad
V=\operatorname{Ls}_{4,1}^{(0,0)}(\pi/2).
\]
All four are real. Only L,C are used in the recommended expression; the alternative uses L,U,V instead.

## 2. The weight-three identity

Retain D3=Im Li_(2,1)(i,1) and D5=Re Li_(2,1,2)(i,1,1) for the proof. Let
\[
l(\theta)=\log(2\sin(\theta/2)),\qquad q=(\theta-\pi)/2,
\qquad 0<\theta<2\pi.
\]
Principal logarithms give log(1-exp(i theta))=l(theta)+i q. The iterated-integral derivative
\[
\frac{d}{dz}\operatorname{Li}_{2,1}(z,1)=\frac{\log^2(1-z)}{2z}
\]
therefore implies
\[
\frac{d}{d\theta}\Im\operatorname{Li}_{2,1}(e^{i\theta},1)
=\frac12[l(\theta)^2-q^2].
\]
Its initial imaginary part at theta=0 is zero. Integration to pi/2 proves
\[
\boxed{D3=-\frac12L-\frac{7\pi^3}{192},\qquad D5=C.}
\]
The second equality is simply the published Clausen convention.

## 3. The recommended two-value substitution

The complete old block is
\[
B_{\rm pol}=4352[(32G+9\pi^2)D3-64D5].
\]
Consequently
\[
\boxed{B_{\rm pol}=-2176[(32G+9\pi^2)L+128C]
-\frac{476}{3}\pi^3(32G+9\pi^2).}
\]
Thus E_real=E-476 pi^3(32G+9 pi^2)/3. Only two existing monomial coefficients change: G pi^3 from -544/3 to -15776/3, and pi^5 from 37631/128 to -145153/128. The Q-dependent block is untouched, and the polynomial still has 18 monomials.

This is a real-function representation, not an independence theorem. In particular, replacing D5 by C has not evaluated the weight-five period in simpler constants.

## 4. Optional: express C entirely in real log-sine functions

The following additional identity removes the multiple Clausen function as well:
\[
\boxed{
C=-GL+\frac32U+\frac12V-\frac{13}{192}G\pi^3
+\frac{451}{3072}\pi^2\zeta(3)+\frac{7635}{2048}\zeta(5).
}
\]
It is proved below by differentiation, integration by parts, and an endpoint value. No integer-relation fit is used.

### General-angle derivation

Let B(theta)=Cl_2(theta), I(theta)=Im Li_(2,1)(exp(i theta)),
A3(theta)=Re Li_3(exp(i theta)), B4(theta)=Im Li_4(exp(i theta)),
A5(theta)=Re Li_5(exp(i theta)). These are proof variables. Their derivatives are
\[
B'=-l,\quad I'=(l^2-q^2)/2,\quad A3'=-B,\quad B4'=A3,\quad A5'=-B4.
\]
For ordinary HPLs, the shuffle identity gives
\[
H_{1101}=\tfrac12H_1^2H_{01}-2H_1H_{011}+3H_{0111}.
\]
Since d/dtheta H_(01101)(exp(i theta))=i H_(1101)(exp(i theta)), this fixes the derivative of its real part. Use
\[
H_1=-l-iq,\quad \Re H_{01}=q^2-\pi^2/12,
\quad \Re H_{011}=\zeta(3)/2+A3/2+qB.
\]
If J(theta)=integral_0^theta l(u)^3 du, integration of the derivative of H_(0111) gives
\[
\Im H_{0111}=-J/6-q^2B/2-qA3/2-\pi\zeta(3)/4+B4/4.
\]
Define the two real iterated log-sine functions at general theta by U(theta)=Ls_(2,3)^(0,0)(theta) and V(theta)=Ls_(4,1)^(0,0)(theta). Then U'=-B l^2 and V'=J. Direct differentiation now proves
\[
\begin{aligned}
\Re H_{01101}(e^{i\theta})={}&\zeta(2,1,2)+2BI+\tfrac32U(\theta)+\tfrac12V(\theta)
+B(q^3-\pi^2q/12)\\
&+[(\theta-\pi)^2/8-\pi^2/24]A3
+[5\pi\theta/4-\theta^2/4-\pi^2/12]\zeta(3)\\
&+\tfrac34[A5-\zeta(5)].
\end{aligned}
\]
At theta=0 the nonconstant terms cancel, so the endpoint is correct. MZV duality and the weight-five shuffle/stuffle formulas give
\[
\zeta(2,1,2)=\zeta(2,3)=\tfrac92\zeta(5)-2\zeta(2)\zeta(3).
\]
At theta=pi/2, B=G, A3=-3 zeta(3)/32, A5=-15 zeta(5)/512. Inserting these and the weight-three identity yields the displayed formula for C. In particular, the intermediate B4 terms cancel: no new Dirichlet beta(4) value enters.

### Complete coefficient substitution

The all-log-sine contribution is
\[
-6528(3\pi^2-32G)L-139264(3U+V),
\]
with polynomial compensation
\[
E_{\rm LS}-E=
\frac{41344}{3}G\pi^3-1428\pi^5
-\frac{122672}{3}\pi^2\zeta(3)-1038360\zeta(5).
\]
It still has 18 expanded monomials. Relative to E, the coefficients of G pi^3, pi^5, pi^2 zeta(3), zeta(5) become respectively
\[
13600,\quad -145153/128,\quad -413491/16,\quad -9112839/8.
\]
This form uses three log-sine values instead of the two old polylogarithmic components. It removes complex projection operations at the cost of one function value; it is not a reduction in the proved dimension of the constant space.

## 5. Executed verification

`check.py` compares independent original HPL evaluations (own series at i/2 plus Taylor continuation) with real log-sine quadrature and Euler-weighted real cosine coefficients. The three-log-sine identity is additionally checked by the exact general-angle derivative and endpoint, not just numerical agreement.

Runs were made for 45 and 90 requested digits, with 15 guard digits. The 90-digit run used 105-digit working precision. The largest weighted discrepancy was below 2.286e-100. These are floating-point checks, not rigorous interval certificates. The cosine evaluation was run at two different finite Euler cutoffs; no raw truncation was equated to the exact limit.

There are seven exact algebra/differential checks and twenty exact preservation checks. The seven inherited non-polylogarithmic fixed-function definitions and the source correction are unchanged. The full C6 was not freshly evaluated. The old wheel certificates retain their wheel-only scope.

## Sources

[1] J. M. Borwein and A. Straub, *Special Values of Generalized Log-sine Integrals*, arXiv:1103.4298, definition (1), Section 2, equations (4)-(5). The multiple-polylogarithm convention there is descending-index.
https://arxiv.org/abs/1103.4298

[2] R. Umezawa, *Evaluation of iterated log-sine integrals in terms of multiple polylogarithms*, arXiv:1912.07201, Definition 1. Only the real iterated log-sine convention and its function family are used; that paper is not an evaluation of the Ising coefficient.
https://arxiv.org/abs/1912.07201

[3] The supplied C6_seventh_unit_slopes_expression.json and C6_polylog_basis_audit.zip supply the inherited coefficient, reference HPL conventions, and old evaluation code. The new single-angle identity is derived explicitly above.
