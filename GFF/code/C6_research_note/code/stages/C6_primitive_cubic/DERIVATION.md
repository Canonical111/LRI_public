# A contour relation reduces the C6 primitive to cubic harmonic degree

## Result and scope

Input: `inputs/central_expression.json`, the supplied
`C6_primitive_central_expression.json`. The normalization is
`r6 = 2187 C6(1)`. The identification of the primitive with the saved Gauss
pairing, the other period reductions, the source correction, and the upstream
physical graph/RG identification remain inherited inputs.

This continuation proves the beta-pairing relation
\[
\boxed{I_{22}-4I_{12}+4I_{02}-4I_{00}=0.}                 \tag{1}
\]
The pairings are normalized and defined in Section 2. The proof is a contour
argument with an explicitly specified numerator; it does not assume an integer
relation on numerical values.

Applying (1) removes the primitive's complete quartic logarithmic product.
Its positive central-binomial double sum then has maximum harmonic degree and
order **three**, instead of four. In particular, neither H_k^(4) nor a square
of H_k^(2) survives in the active primitive summand.

There are still two summation indices and three active elliptic quantities in
the full C6 formula. This is not a finite ordinary one-variable evaluation of
P_a, nor an elimination of that residual constant. Raw convergence is not
improved. No new full-C6 interval certificate is constructed.

## 1. The explicit cubic double sum

Put
\[
 a_n=\frac{(1/2)_n}{n!}=\frac{\binom{2n}{n}}{4^n},\qquad
 h_n=\log2+H_n-H_{2n},\qquad
 \delta_n=\frac{\pi^2}{3}-4H_{2n}^{(2)}+2H_n^{(2)},
\]
where H_0^(r)=0. For m,n>=0 write k=m+n and define
\[
 \boxed{t_{m,k}=8h_m+H_k-H_m,\qquad
 e_{m,k}=4\delta_m+H_k^{(2)}-H_m^{(2)}.}                 \tag{2}
\]
For compactness below, t_m and e_m mean t_(m,k) and e_(m,k), and likewise for n.
Set
\[
\boxed{\begin{aligned}
 T_{m,n}={}&15t_mt_n(t_m+t_n)+15(t_me_n+t_ne_m)\\
 &+72\pi\bigl(t_mt_n+H_k^{(2)}\bigr)\\
 &+\bigl(30H_k^{(2)}+7\pi^2\bigr)(t_m+t_n)\\
 &+28\pi^3-60\bigl[\zeta(3)-H_k^{(3)}\bigr].
\end{aligned}}                                                   \tag{3}
\]
Then
\[
\boxed{
 \mathscr P_{\rm c}^{(3)}=
 \sum_{m,n\ge0}\frac{a_m^4a_n^4}{\binom{m+n}{m}}T_{m,n},\qquad
 P_a=2\pi^2\mathscr P_{\rm c}^{(3)}.
}                                                               \tag{4}
\]
The superscript (3) records the harmonic degree; it is not a loop order.
The machine symbol is `PaCubic`.

The old symbol PaCentral denoted P_a/pi. Thus
\[
 \boxed{\mathscr P_{\rm c}=2\pi\mathscr P_{\rm c}^{(3)}.}           \tag{5}
\]
The changed normalization must be included when inserting the new sum in C6.

Only pi, log(2), zeta(3), rational binomial coefficients, and finite harmonic
numbers occur in (2)-(4). There are no Gauss functions, derivatives, Q, Catalan
constant, or matrices in this final definition.

Both zero indices are included. Their term is
\[
\boxed{T_{0,0}=15360\log^3 2+4608\pi\log^2 2
 +432\pi^2\log2+28\pi^3-60\zeta(3).}                            \tag{6}
\]
It is not separated into the known polynomial.

## 2. The pairing identity and its effect on the primitive

Retain the kernels
\[
 v(x)={}_2F_1(\tfrac14,\tfrac14;1;x),\qquad
 h(x)={}_2F_1(\tfrac14,\tfrac14;\tfrac12;x),\qquad
 Q=\Gamma(1/4)^4/\pi.
\]
As before, h(x) is not the finite harmonic remainder h_n. Define
\[
 p_0(x)=v(x)^2,\quad
 p_1(x)=\sqrt Q\,v(x)h(1-x),\quad
 p_2(x)=Qh(1-x)^2,
\]
and the six symmetric pairings
\[
 \boxed{I_{ij}=\int_0^1
  \frac{p_i(x)p_j(1-x)}{\pi^{i+j}\sqrt{x(1-x)}}\,dx,
  \qquad 0\le i,j\le2.}                                      \tag{7}
\]
Reflection gives I_ij=I_ji. They converge: at either endpoint only the
zero-balanced Gauss factor can be logarithmic, and the weight is integrable.

The saved primitive is precisely
\[
 P_a=\pi^4(15I_{22}+24I_{11}-4I_{00}).                         \tag{8}
\]
Using (1) gives
\[
\boxed{P_a=\pi^4(60I_{12}-60I_{02}+24I_{11}+56I_{00}).}       \tag{9}
\]
This removes the logarithm-squared times logarithm-squared pairing I22.
It does not separately evaluate the four pairings in (9).

A useful positive version of (9) is
\[
\begin{aligned}
P_a=\int_0^1\frac{dx}{\sqrt{x(1-x)}}\Big\{
 &30\pi\big[(p_1(x)-\pi p_0(x))p_2(1-x)\\
 &\hspace{21mm}+(p_1(1-x)-\pi p_0(1-x))p_2(x)\big]\\
 &+24\pi^2p_1(x)p_1(1-x)+56\pi^4p_0(x)p_0(1-x)\Big\}.
\end{aligned}                                                  \tag{10}
\]
The common Frobenius expansions in the input have, with L=-log(x),
\[
\begin{aligned}
 p_0(x)&=\sum a_n^3x^n,\\
 p_1(x)&=\sum a_n^3x^n(L+\pi+6h_n),\\
 p_2(x)&=\sum a_n^3x^n\big[(L+\pi+6h_n)^2+3\delta_n-\pi^2\big].
\end{aligned}                                                  \tag{11}
\]
Consequently p1-pi*p0 has coefficients L+6h_n>0. All the coefficient
polynomials contributing to (10) are positive for 0<x<1. The largest total
logarithmic degree is now three.

## 3. A complete contour proof of the pairing relation

### 3.1 Branches and real boundary data

Use principal Gauss functions, with their usual cut [1,infinity), and separate
principal square roots sqrt(z), sqrt(1-z). Define, on the upper half-plane,
\[
 f(z)=v(z),\qquad
 g(z)=\frac{\sqrt Q}{\pi}h(1-z)-v(z),\qquad
 f_*=f(1-z),\quad g_*=g(1-z).                                  \tag{12}
\]
The star is evaluation at 1-z, NOT complex conjugation.
All four factors in (12) are holomorphic in the open upper half-plane.

The Gauss cut-jump formula [1] gives, for real x<0,
\[
 f(x+i0)=u,\qquad g(x+i0)=r-iu,
 \quad u,r\in\mathbb R.                                      \tag{13}
\]
Indeed the jump of the zero-balanced h across its cut has coefficient
2*pi*i/sqrt(Q) times v(1-x). The reflected argument 1-(x+i0) approaches that
cut from below, fixing the minus sign in (13).

For x>1 the Gauss connection formula [2] reads
\[
 v(z)=\frac{\sqrt Q}{2\pi}h(1-z)
 -\frac2{\sqrt Q}\sqrt{1-z}\,
 {}_2F_1(\tfrac34,\tfrac34;\tfrac32;1-z).
\]
Its second term is imaginary on the upper bank; thus
\[
 f(x+i0)=a+ib,\qquad g(x+i0)=a-ib,
 \quad a,b\in\mathbb R.                                     \tag{14}
\]
The lower-bank data are the complex conjugates, because the parameters and
normalizations are real. Combining (13)-(14), the two exterior intervals
have the following exact boundary patterns (u,r,a,b are local real values):

| Region | f | g | f_* | g_* |
|---|---|---|---|---|
| x<0, z=x+i0 | u | r-iu | a-ib | a+ib |
| x>1, z=x+i0 | a+ib | a-ib | u | r+iu |

### 3.2 The contour numerator

Let
\[
\begin{aligned}
\mathcal N={}&g^2g_*^2+g^2f_*^2+f^2g_*^2
 -4fgf_*g_*-3f^2f_*^2\\
 &+4i\big(fg f_*^2-f^2f_*g_*\big),
\end{aligned}                                                   \tag{15}
\]
and set
\[
 \mathcal K(z)=\frac{\mathcal N(z)}{\sqrt z\sqrt{1-z}}.           \tag{16}
\]
On EITHER exterior row of the table, direct polynomial expansion yields
\[
 \boxed{\mathcal N=2r(a-b)\big[(a+b)r-2(a-b)u\big]\in\mathbb R.} \tag{17}
\]
This exact identity is checked symbolically in verify.py, with arbitrary
real u,r,a,b, rather than at selected values of z.

Meanwhile, on the upper bank,
\[
 \frac1{\sqrt{x+i0}\sqrt{1-x-i0}}=
 \begin{cases}
 -i/\sqrt{(-x)(1-x)},&x<0,\\
 +i/\sqrt{x(x-1)},&x>1.
 \end{cases}
\]
Therefore Re K(x+i0)=0 on both exterior intervals.

For another exact specification of (15), in the basis (f^2,fg,g^2),
\[
\mathcal N=
(f^2,fg,g^2)(\mathsf C+i\mathsf D)
(f_*^2,f_*g_*,g_*^2)^T,
\]
\[
 \mathsf C=\begin{pmatrix}-3&0&1\\0&-4&0\\1&0&1\end{pmatrix},
 \qquad
 \mathsf D=\begin{pmatrix}0&-4&0\\4&0&0\\0&0&0\end{pmatrix}.
\]
Allowing a general real symmetric C and real antisymmetric D gives nine real
coefficients. Requiring the numerator to be real on both exterior patterns
produces an exact rank-eight system. The displayed coefficients span its
one-dimensional solution space. This is a statement only about this contour
ansatz, not about independence of the periods or all possible identities.

### 3.3 No omitted contour boundaries

The equal-upper-parameter Gauss asymptotics at infinity [2,3] give, uniformly
on a large upper semicircle,
\[
 f(z),g(z),f_*,g_*=O(|z|^{-1/4}(1+\log|z|)),
\]
and hence
\[
 \mathcal K(z)=O(|z|^{-2}(1+\log|z|)^4).
\]
The large semicircle integral tends to zero.
At z=0, the unreflected pair has at most logarithmic growth, while the
reflected pair is finite. Thus
\[
 \mathcal K(z)=O(|z|^{-1/2}(1+|\log z|)^2).
\]
The analogous bound holds at z=1. Small semicircle contributions are
O(sqrt(epsilon)*(1+abs(log(epsilon)))^2), so they also vanish. There are no
poles or branch cuts in the interior of the contour.

Cauchy's theorem and these integrable bounds therefore give
\[
 0=\int_{-\infty}^{\infty}\mathcal K(x+i0)\,dx.
\]
Taking real parts, (17) removes both exterior intervals:
\[
 0=\int_0^1\frac{\Re\mathcal N(x)}{\sqrt{x(1-x)}}\,dx.          \tag{18}
\]

### 3.4 Identify the integral

On 0<x<1, all f,g,f_*,g_* are real. In this basis,
\[
 p_0=f^2,\qquad p_1/\pi=f(f+g),\qquad p_2/\pi^2=(f+g)^2.
\]
Writing q_i=p_i/pi^i, direct algebra gives
\[
\begin{aligned}
 \Re\mathcal N={}&q_2q_{2,*}
 -2(q_1q_{2,*}+q_2q_{1,*})\\
 &+2(q_0q_{2,*}+q_2q_{0,*})-4q_0q_{0,*}.
\end{aligned}
\]
Substitute into (18) and use I_ij=I_ji. This proves (1), including every
normalization and sign.

The proof is a GLOBAL definite-pairing relation, not a pointwise vanishing
polynomial. It does not contradict the earlier obstruction to a universal
algebraic-coefficient boundary antiderivative for the nine-state primitive.

## 4. Compute the cubic beta coefficient

For each m,n set k=m+n and let X have beta(m+1/2,n+1/2) density.
Write L=-log(X), K=-log(1-X), and
\[
 b_m=L+\pi+6h_m,\quad q_m=b_m^2+3\delta_m-\pi^2,
\]
with the corresponding n-dependent expressions in K.
Euler beta integration [4] gives
\[
 B(m+\tfrac12,n+\tfrac12)
 =\pi\frac{a_ma_n}{\binom{k}{m}}.
\]
Together with the two coefficients a_m^3*a_n^3 from (11), this supplies the
weight pi*w_mn, where w_mn=a_m^4*a_n^4/binomial(k,m).

Put
\[
 U=\pi+t_{m,k},\quad V=\pi+t_{n,k},\quad
 c=H_k^{(2)}-\pi^2/6,\quad d=-2[\zeta(3)-H_k^{(3)}].
\]
The beta gamma quotient and polygamma recurrences [4,5] yield
\[
 \mathbb E b_m=U,\quad
 \mathbb E q_m=t_{m,k}^2+2\pi t_{m,k}+e_{m,k}=:A_m,
\]
\[
 \mathbb E(b_mb_n)=UV+c,
\]
\[
 \mathbb E(b_mq_n)=U A_n+2Vc+d.
\]
For example, c is the covariance of L and K and d is their mixed cumulant
of order (1,2). No fourth-order cumulant is needed.

Use the symmetric quantities
\[
 E_{02}=\frac{A_m+A_n}{2},\qquad E_{11}=UV+c,
\]
\[
 E_{12}=\frac{U A_n+V A_m}{2}+(U+V)c+d.
\]
Substituting these beta moments in the weighted primitive (9) gives the
coefficient
\[
 G_{m,n}=60\pi E_{12}-60\pi^2E_{02}+24\pi^2E_{11}+56\pi^4.
\]
A finite polynomial calculation gives
\[
 \boxed{G_{m,n}=2\pi T_{m,n},}
\]
where T is precisely (3). Multiplication by the beta weight pi*w_mn proves (4).

Equivalently, in terms of the OLD quartic polynomial F_mn in the input,
\[
 \boxed{\sum_{m,n\ge0}w_{m,n}\big[F_{m,n}-2\pi T_{m,n}\big]=0.} \tag{19}
\]
The summands in (19) are not individually zero. This global identity is what
allows the fourth-degree and fourth-order terms to disappear.

## 5. Positivity, convergence and a literal tail bound

The harmonic remainders h_n and delta_n are positive, as in the input.
Because k>=m,n, (2) implies t_m,e_m,t_n,e_n>0. Also
\[
 0<\zeta(3)-H_k^{(3)}\le\zeta(3)<5/4.
\]
Consequently
\[
 \boxed{T_{m,n}>28\pi^3-60\zeta(3)>681.}                      \tag{20}
\]
The last bound uses pi>3. Positivity is therefore a theorem for every pair,
not a numerical observation.

Termwise beta integration can alternatively be justified directly from the
positive coefficient polynomials in (10)-(11). Their endpoint growth is an
integrable beta weight times finite logarithmic powers. Monotone convergence
proves that the double series is absolutely convergent.

An explicit elementary bound is also available. For k>=1, let
B_k=7+log(k), and label the larger index n>=m. Since n>=1 and n>=k/2,
\[
 0<t_m<B_k,\qquad
 0<t_n<8h_1+\log2=9\log2-4<5/2,
\]
\[
 0<e_m<3\pi^2/2<15,\qquad
 0<e_n<3\pi^2/2-13<2,
 \qquad H_k^{(2)}<5/3.
\]
Here h_n and delta_n decrease; H_k-H_n<=log(k/n). With
log2<7/10, pi<16/5, pi^2<10 and pi^3<32, dropping the negative term in (3)
gives
\[
 T_{m,n}<\frac{75}{2}B_k^2+\frac{3279}{4}B_k+\frac{4285}{2}
 <200B_k^2,\quad B_k\ge7.
\]
The last inequality is a positive quadratic in B_k-7, checked exactly.

Increasing coefficient ratios imply a_m*a_n<=a_(m+n). The induction bound
a_k^2<=1/(3k+1) and binomial(k,m)>=k for 1<=m<=k-1 give
\[
 \sum_{m+n=k}w_{m,n}
 \le a_k^4\sum_{m=0}^k\binom{k}{m}^{-1}
 <\frac1{3k^2}.
\]
Thus, for the exact triangular partial sum
\[
 P_{a,N}^{(3)}=2\pi^2\sum_{m+n<N}w_{m,n}T_{m,n},
\]
we obtain
\[
\boxed{0<P_a-P_{a,N}^{(3)}<
 \frac{400\pi^2}{3(N-1)}
 \big[B_N^2+2B_N+2\big],\quad
 B_N=7+\log(N-1),\quad N\ge2.}                              \tag{21}
\]
This is a bound on the omitted exact series terms. Floating-point rounding
of a computed partial sum must be bounded separately for interval use.

## 6. Full C6 insertion and preservation

The current active formula becomes
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_{\rm alg}+835584\Lambda+391680H_5\\
 &+13056\sqrt2(32G+3\pi^2)H_3\\
 &+\pi^3\mathcal E_{\rm c}+24\pi^3\mathscr M_7
 +192\pi^2\mathscr P_{\rm c}^{(3)}.
\end{aligned}}                                                \tag{22}
\]
This is the sole active-term change:
\[
 96\pi\mathscr P_{\rm c}=192\pi^2\mathscr P_{\rm c}^{(3)}.
\]
The complete known polynomial is copied unchanged in `results/cubic_expression.json`.
All coefficients and definitions of Ecentral, M7central, Lambda, H3real and
H5real are retained. The source correction remains exactly as in the input.

No zero-index term is removed, so Delta(E_alg)=0. In particular, (6) is not an
additional elementary contribution. The previous quartic definition and the
legacy geometric recurrence definitions are retained for provenance and use
as alternative representations.

## 7. Executed verification

The package passes 122 exact algebra/implementation checks. Many are unchanged
metadata-field checks, not independent theorems. Substantive checks include
both exterior branch patterns, the contour numerator, the rank-eight boundary
system, the pairing normalization, the entire weighted Pa replacement, the
cubic beta polynomial, the old-minus-new global relation, the zero-index term,
the elementary tail majorant, and preservation of the full C6 inputs.

Independent numerical beta-pairing evaluations were run at 60 and 120 working
decimal digits. The normalized relation residuals are respectively
1.245e-60 and 7.746e-120. At 120 working digits the old pairing expression,
new pairing expression, and inherited primitive midpoint round to the same
mpmath value. A displayed zero difference means equality after working-
precision rounding, NOT a certified zero error.

Five direct beta-logarithm integrations, distinct from the Gauss quadrature,
check (3). Their largest absolute difference at 120 working digits is below
2.538e-116. Additional near-cut numerical samples check the branch orientation;
their nonzero errors scale with the finite imaginary displacement used.

The new normalized value begins
\[
\mathscr P_{\rm c}^{(3)}=
16967.5516685898950813989109176482635997931055439623294203959175\ldots,
\]
so
\[
P_a=334926.045248051837883222001240077786613085905253136679683127\ldots.
\]

Literal sums illustrate the tradeoff:

| Region | Cubic partial sum for Pa | Difference from inherited midpoint |
|---|---:|---:|
| m+n<32 | 334596.184326098490469 | 329.860921953347 |
| m+n<128 | 334841.659324618452939 | 84.385923433385 |
| m+n<512 | 334903.898940048263320 | 22.146308003575 |

These partial sums increase to Pa, but converge slowly. At N=512 the previous
quartic partial sum had a smaller error (about 14.8574); reducing harmonic
degree is not the same as improving direct-sum speed. The long numerical
value above comes from the separate pairing quadrature, not the raw double
sum. The existing geometric interval evaluator remains an alternative in the
earlier package. No new rigorous full-C6 interval is claimed here.

## References and analytic inputs

1. NIST Digital Library of Mathematical Functions, Section 15.2, especially
   equation 15.2.3: principal branches and the Gauss cut jump.
2. NIST DLMF Section 15.8: Gauss connection and limiting formulas, especially
   15.8.4, 15.8.8 and 15.8.10.
3. NIST DLMF Section 15.12(i): large-variable hypergeometric asymptotics.
4. NIST DLMF Section 5.12: Euler's beta integral and its gamma quotient.
5. NIST DLMF Section 5.15: polygamma recurrence and integer/half-integer values.
6. Supplied C6_primitive_central_derivation.md and expression JSON, copied under
   inputs/: the symmetric primitive, common Frobenius expansions, normalization,
   known polynomial, all other sectors, and inherited source/graph assumptions.

The new pairing relation is proved in Section 3. The references supply the
standard Gauss/beta identities, not a published evaluation of this C6 primitive.
