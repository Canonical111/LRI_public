# Four-shift periodization proves the wheel relation and removes one auxiliary series

## Result and scope

The previously conjectural wheel identity is proved:

\[
8c_0+c_1=(2\pi^2+20\pi\ell+52\ell^2)B_-
 -(4\pi\ell+12\ell^2)B_+,\qquad \ell=\log2.
\]

The proof uses Bailey's **two-term nonterminating** transformation and a four-shift gamma-ratio periodization. No numerical integer relation is used. In the latest working expression the two separately retained wheel series K6,T4 reduce to one simpler, fast-convergent series Wq. The auxiliary-series count goes from five to four. The polylogarithms, the other three recurrence series, the graph/RG assembly, the earlier missing-pole repair, and the ordinary period identifications are inherited unchanged.

This is not a finite ordinary-hypergeometric evaluation of the one remaining wheel series. It is a genuine analytic relation among the previously retained wheel inputs, not a minimality or arithmetic-independence theorem. All substitutions use r6=2187 C6(1). The numerical checks below certify no new physical precision for the full six-loop coefficient.

## 1. The new compact series and coefficient formula

Set
\[
 a_n=\frac{(1/2)_n}{n!},\quad H_n^{(r)}=\sum_{j=1}^n j^{-r},\quad H_0^{(r)}=0,
\]
\[
 h_n=\ell+H_n-H_{2n},\qquad
 \delta_n=\frac{\pi^2}{3}-4H_{2n}^{(2)}+2H_n^{(2)}.
\]
Define the explicit one-index sum
\[
 \boxed{\mathscr W_4=\sum_{n=0}^\infty a_n^4
   [(\pi-10h_n)\delta_n-80h_n^3].} \tag{1}
\]
No inner sum, parameter derivative, or unevaluated moment is part of this definition. The sum is signed; all terms with n>=2 are positive. The summands are asymptotic to 1/(2 pi n^4).

Let B_s=B_-+B_+ and B_d=B_--B_+, where
\[
 B_- =\Gamma(1/4)^4\,{}_4F_3(1/4,1/4,1/2,1/2;3/4,3/4,1;1),
\]
\[
 B_+=\frac{64\pi^4}{\Gamma(1/4)^4}
 {}_4F_3(3/4,3/4,1/2,1/2;5/4,5/4,1;1).
\]
The current wheel combination has the exact replacement
\[
 \boxed{-6\pi^3\mathscr K_6-3360\pi^3\mathscr T_4
     =\Delta_{\rm per}-3144\pi^2\mathscr W_4,} \tag{2}
\]
\[
 \boxed{\Delta_{\rm per}
 =(180\ell^2-1515\pi^2)B_s+(66\pi^2+180\pi\ell)B_d.} \tag{3}
\]

The full working expression is therefore
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E_4+417792\Xi-39168\pi^2\Theta
 -3144\pi^2\mathscr W_4\\
&+96\mathscr A-\pi^3\mathscr Z_{\rm rec}+576\pi\mathscr R_A,
\end{aligned}} \tag{4}
\]
with E4=Erec+Delta_per. The inherited definitions are
\[
 \Xi=\Re\operatorname{Li}_{2,2,1}(i,-i,1),\qquad
 \Theta=\Im\operatorname{Li}_3((1+i)/2).
\]
The three recurrence series AP, Zrec, RA and their complete initial data are retained byte-for-byte as structured JSON. The output does not redefine them through a numerical target.

Only the coefficients of the known wheel values P4 and L change in E. Put A=pi+4log2. Using
\[
 P_4=13B_--3B_+,\qquad
 \mathcal L=-\frac{13A-3\pi}{2}B_-+\frac{3A-\pi}{2}B_+,
\]
their new collected part is
\[
\boxed{
\left(12Q-\frac{57}{4}A^2+\frac{6663}{2}A\pi-\frac{3945}{4}\pi^2\right)P_4
+(-18A+6663\pi)\mathcal L,
}\tag{5}
\]
where Q=Gamma(1/4)^4/pi. The previous A^3 P4/pi and A^2 L/pi terms cancel exactly. The JSON contains the entire collected E4, not just this change.

## 2. Analytic moment identities used in the proof

Use the elliptic **parameter** convention and the normalized kernel
\[
 k(t)={}_2F_1(1/2,1/2;1;t)=2K(t)/\pi.
\]
For the proof only, define
\[
 \mathcal N(a,b)=\int_0^1t^{a-1}(1-t)^{b-1}k(t)k(1-t)\,dt,
\]
\[
 \mathcal J(s)=\mathcal N(s,s),\quad
 \mathcal I(s)=\mathcal N(s,1-s),\quad
 \mathcal M(s)=\mathcal N(s,1),
\]
\[
 \mathcal F(x)=2^{2x}\mathcal J(1/2+x).
\]
These integrals and their fixed-order logarithmic derivatives are holomorphic in their common positive-beta domain. Endpoints have at most logarithmic growth.

The inherited Fourier-Legendre evaluation is
\[
\mathcal J(s)=\frac\pi2\frac{\Gamma(s)^2}{\Gamma(2s)}
 {}_7F_6(5/4,(1/2)^{\times5},1-s;
             1/4,1^{\times4},s+1/2;1). \tag{6}
\]
The inherited mixed Mellin evaluation is
\[
\mathcal M(s)=\frac{\Gamma(s)^2}{\Gamma(s+1/2)^2}
 {}_4F_3(1/2,1/2,s,s;1,s+1/2,s+1/2;1). \tag{7}
\]
These identities are retained from the preceding derivations; the new parameter transformation below is independently checked against the defining integrals.

For the square moment
\[
\mathcal M_2(a,b)=\int_0^1t^{a-1}(1-t)^{b-1}k(t)^2\,dt,
\]
the existing upper-half-plane contour relation reads, c=2-a-b,
\[
0=\mathcal M_2(a,b)-e^{i\pi a}\mathcal M_2(a,c)
-e^{-i\pi b}[\mathcal M_2(c,b)-\mathcal M_2(b,c)+2i\mathcal N(c,b)]. \tag{8}
\]
Arcs vanish when Re(a),Re(b),Re(c)>0. Taking (a,b,c)=(s,1,1-s) gives
\[
\mathcal M_2(s,1-s)=\frac{2\mathcal M(1-s)}{\sin\pi s}.
\]
Taking (a,b,c)=(1,s,1-s), and its imaginary part, then gives
\[
 \boxed{\mathcal I(s)=\frac{\mathcal M(s)-\mathcal M(1-s)}{\cos\pi s}.} \tag{9}
\]
The singularity at s=1/2 is removable. All derivatives below include the derivative of this denominator; losing its minus sign would reverse the quadratic identity.

## 3. Bailey's two-term identity in the required normalization

Put
\[
 g(z)=\frac{\Gamma(z+1/2)}{\Gamma(z+1)}.
\]
The new parameter identity is
\[
\boxed{
 \mathcal F(x)=\frac{\cot\pi x}{\pi}
 \sum_{n=0}^\infty
 [g(n)^3g(n-x)-g(n)g(n+x)^3].
}\tag{10}
\]
It holds near x=0 (and, by continuation, away from exceptional parameters in the common domain). The apparent singularity at zero is removable. The sums on both sides of the difference are absolutely and locally normally convergent. Each has n^-2 decay; their difference vanishes at x=0.

This is the specialization of equations (3.2)-(3.3) of Groenevelt's Wilson-function paper [1], which records Bailey's decomposition into **two nonterminating balanced 4F3 series**. It is not the one-term terminating Whipple formula.

To reproduce the normalization, use source parameters
\[
 a=d=1/2-x/2,\quad b=c=1/2+x/2,\quad iX=x/2,\quad i\Lambda=0.
\]
Their dual parameters are
\[
 \widetilde a=\widetilde b=\widetilde c=1/2,
 \qquad\widetilde d=1/2-x.
\]
The Wilson 7F6 is exactly the 7F6 in (6), at s=1/2+x. The source Wilson function multiplied by pi Gamma(1/2+x)^2 is F(x), by duplication.

The two balanced series in the decomposition are
\[
{}_4F_3(1/2,1/2,1/2,1/2-x;1,1,1-x;1)
\]
and
\[
{}_4F_3(1/2,1/2+x,1/2+x,1/2+x;1+x,1+x,1+x;1).
\]
Their complete gamma coefficients, after multiplication by pi Gamma(1/2+x)^2, are
\[
\sqrt\pi\frac{\Gamma(x)}{\Gamma(1/2+x)},\qquad
\frac{\Gamma(-x)\Gamma(1/2+x)^2}
 {\sqrt\pi\Gamma(1+x)^2\Gamma(1/2-x)}.
\]
Gamma reflection [2] changes these into precisely +cot(pi x)/pi times g(0)^3g(-x), and -cot(pi x)/pi times g(0)g(x)^3. This proves (10), retaining both terms.

## 4. Four-shift periodization supplies the missing constraints

For four small offsets lambda_i define
\[
\Phi_{\boldsymbol\lambda}(z)=
\left[\prod_{i=1}^4\cos\pi(z+\lambda_i)\right]
\sum_{n\in\mathbb Z}\prod_{i=1}^4g(n+z+\lambda_i). \tag{11}
\]
The bilateral tails are O(n^-2). Gamma reflection gives
\[
 g(-1/2-z)=-\cot(\pi z)g(z).
\]
Thus, writing P(z;lambda)=sum_{n>=0}prod_i g(n+z+lambda_i),
\[
\Phi_\lambda(z)=
\prod_i\cos\pi(z+\lambda_i)P(z;\lambda)
+\prod_i\sin\pi(z+\lambda_i)P(1/2-z;-\lambda). \tag{12}
\]
Every possible pole of g is a simple half-integer pole. The cosine product removes it, including when several offsets coincide. Hence Phi is entire and one-periodic.

Gamma-ratio asymptotics and reflection [2,3] give, uniformly on a vertical strip and for small fixed offsets,
\[
|\Phi_\lambda(z)|=O(e^{4\pi|\Im z|}/|\Im z|).
\]
Indeed the one-sided sum of four gamma ratios is bounded by a constant times sum_{n>=0}|n+z|^-2=O(1/|Im z|). Fourier-contour shifting therefore excludes every frequency of absolute value at least two, including the boundary frequencies +/-2. Consequently
\[
\Phi_\lambda(z)=\alpha(\lambda)+\beta(\lambda)\sin(2\pi z)
+\gamma(\lambda)\cos(2\pi z). \tag{13}
\]
Directly from reflection,
\[
\Phi_\lambda(1/2-z)=\Phi_{-\lambda}(z).
\]
For lambda_i=a_i x, alpha and beta are even in x and gamma is odd. In particular,
\[
 [z^2x^2]\Phi_{a x}(z)=0,\qquad
 [zx^3]\Phi_{a x}(z)=0. \tag{14}
\]
These exact zero coefficients are the new information not supplied by the unshifted periodization alone.

### 4.1 Explicit derivative identities from the shifts

For proof notation only, write
\[
 d_n=(\log g)'(n),\quad\delta_n=(\log g)''(n),\quad
 \tau_n=(\log g)'''(n),\quad\upsilon_n=(\log g)''''(n),
\]
\[
 \langle f\rangle=\sum_{n\ge0}g(n)^4 f_n,
 \quad B_0=\langle1\rangle,
 \quad B_h=\sum_{n\ge0}g(n+1/2)^4,
 \quad D=\langle\delta\rangle.
\]
All displayed derivative sums converge normally.

Let B(t)=sum_{n>=0}g(n+t)^4. The unshifted case gives
\[
 B''(0)=4\pi^2B_0,\quad B'''(0)=8\pi^2B'(0),
\]
\[
 B''''(0)=56\pi^4B_0-24\pi^4B_h. \tag{15}
\]
The coefficient z^2 x^2 with offsets (x,x,-x,-x) yields
\[
\boxed{\langle16d^2\delta+4\delta^2+8d\tau+\upsilon\rangle
=2\pi^4(B_0+B_h)+4\pi^2D.} \tag{16}
\]
The coefficient z x^3 with offsets (x,x,x,-3x) yields
\[
\boxed{\langle4d\tau+\upsilon\rangle=2\pi^4(B_0-B_h).} \tag{17}
\]
For example, the positive-side z^2 x^2 coefficient before averaging is
\[
16d^2\delta+4\delta^2+8d\tau+\upsilon
-16\pi^2d^2-8\pi^2\delta+2\pi^4;
\]
the complementary side contributes -2 pi^4 B_h. Using (15) gives (16).

Eliminating the fourth-order derivative sums from (15)-(17) gives
\[
\boxed{\langle4d^4+3d^2\delta\rangle
=\tfrac34\pi^4B_0-\pi^4B_h-\tfrac34\pi^2D.} \tag{18}
\]
The exact script constructs the bivariate expansions, including the complementary side, instead of taking (16)-(18) as input.

## 5. The cubic wheel response is no longer independent

The per-term Taylor expansion of the bracket in (10), divided by g(n)^4, is
\[
\begin{aligned}
&-4d x-(4d^2+\delta)x^2\\
&-\left(\tfrac{14}{3}d^3+5d\delta+\tfrac23\tau\right)x^3\\
&-\left(\tfrac{10}{3}d^4+\tfrac{13}{2}d^2\delta+\delta^2
 +\tfrac43d\tau+\tfrac1{12}\upsilon\right)x^4+O(x^5).
\end{aligned}
\]
Multiplying by cot(pi x)/pi and using (15)-(18) gives
\[
\boxed{\mathcal F'''(0)=-\frac{11\pi^2}{4}B_0-\frac94D.} \tag{19}
\]
The second-order calculation, using (9) and B'''(0)=8pi^2 B'(0), gives
\[
 \mathcal F''(0)=\frac34\mathcal I''(1/2)+\frac14B'(0).
\]
Also F(0)=J(1/2)=-B'(0)/pi^2 and F'(0)=-B0. Therefore
\[
\boxed{\mathcal J''(1/2)=\frac34\mathcal I''(1/2)
 +4\ell B_0+(4\ell^2-\pi^2/4)\mathcal J(1/2).} \tag{20}
\]

The prior definitions give
\[
 B_0=\frac{B_d}{4\pi},\quad
 \mathcal J(1/2)=\frac{B_s}{4\pi^2},\quad
 D=\pi^2\mathscr T_4,
\]
\[
 \mathcal F'''(0)=-\frac{\pi^2}{2}\mathscr B_6.
\]
Hence (19) evaluates the formerly separate cubic response:
\[
\boxed{\mathscr B_6=\frac{11}{8\pi}B_d+\frac92\mathscr T_4.} \tag{21}
\]
This is a relation to already retained values, not a numerical fit to B6.

### 5.1 Proof of the earlier wheel conjecture

Write N_A^{ij}=partial_a^i partial_b^j N(1/2,1/2) and N_B^{ij}=partial_a^i partial_b^j N(1/2,1). Let N_A^0=B_s/(4pi^2), N_B^0=B_d/(4pi^2). Existing first-derivative contour/Landen identities give
\[
 N_A^{01}=-\tfrac\pi2N_B^0-\ell N_A^0,\qquad
 N_B^{01}=\ell N_B^0-\tfrac\pi4N_A^0.
\]
Equation (20) is equivalent to
\[
 N_A^{02}+7N_A^{11}=8\pi\ell N_B^0+(8\ell^2-\pi^2/2)N_A^0. \tag{22}
\]
The previous cubic-Landen identity for N(s,2-2s), combined with (21), gives
\[
 N_B^{02}-N_B^{11}=-\tfrac1{16}N_B^{20}+(\ell^2+\pi^2/8)N_B^0. \tag{23}
\]
The wheel moments, in the normalized k convention, obey the existing contour reductions
\[
\begin{aligned}
c_0=\tfrac{\pi^2}{4}[&-16\pi(N_A^{01}+N_B^{01})+40N_A^{11}
-16\pi^2N_B^0+64N_B^{02}-64N_B^{11}],\\
c_1=\tfrac{\pi^2}{4}[&4\pi^2N_A^0+40N_A^{02}-40N_A^{11}
+16\pi^2N_B^0+32N_B^{20}].
\end{aligned}
\]
Substituting (22)-(23) cancels all second-order unknowns in 8c0+c1 and proves
\[
\boxed{8c_0+c_1=(2\pi^2+20\pi\ell+52\ell^2)B_-
 -(4\pi\ell+12\ell^2)B_+.} \tag{24}
\]
The factor pi^2/4 above is necessary because the original wheel moments used K rather than k. A separate fresh quadrature of the original folded c0,c1 moments checks this normalization.

## 6. Derive the new one-index replacement

The existing series are
\[
\mathscr S_7=2\mathcal I''(1/2)/\pi^2,\quad
\mathscr S_+=2\mathcal J''(1/2)/\pi^2,
\]
\[
 C_{\rm bin}=\sum_{n\ge0}(4n+1)a_n^6=\frac{B_s}{2\pi^4},
\]
\[
\mathscr V_6=35\mathscr S_7-3\mathscr S_++2\pi^2 C_{\rm bin},
\qquad \mathscr K_6=5\pi\mathscr V_6-8\mathscr B_6.
\]
Equation (20) gives
\[
\mathscr S_+=\tfrac34\mathscr S_7+\frac{8\ell}{\pi^2}B_0
 +(4\ell^2-\pi^2/4)\frac{B_s}{2\pi^4}. \tag{25}
\]
From (7),(9), and the cubic identity in (15),
\[
\mathcal I''(1/2)=\frac{16}{\pi^2}\langle d^3\rangle
+\frac8{\pi^2}\langle d\delta\rangle-12\langle d\rangle.
\]
Use d_n=-2h_n, g(n)^4=pi^2 a_n^4 and
\[
\sum a_n^4h_n=\frac{B_s}{32\pi^2}.
\]
This gives
\[
\boxed{\mathscr S_7=\frac{3B_s}{2\pi^2}
-\frac{32}{\pi^2}\sum_{n\ge0}a_n^4h_n(8h_n^2+\delta_n).} \tag{26}
\]
Substitute (21),(25),(26) into the current pair -6pi^3 K6-3360pi^3 T4. Exact collection gives (2)-(3). Thus the new a_n^4 kernel replaces the previous a_n^6/log-cubed kernel. This is where the convergence rate improves.

## 7. Positivity after the first two terms and a direct tail bound

The positive integral representations give, with a=4n+1,
\[
0<h_n<1/a,\qquad 8/(a+1)^2<\delta_n<8/a^2.
\]
They follow from
\[
h_n=\int_0^\infty e^{-au}\operatorname{sech}u\,du,
\quad\delta_n=8\int_0^\infty u e^{-au}\operatorname{sech}u\,du,
\]
and e^{-u}<sech(u)<1. For n>=2, a>=9 and
\[
\pi>\frac{10}{a}+\frac{10(a+1)^2}{a^3},
\]
since the right side is decreasing and is less than three at a=9. Hence the bracket in (1) is positive. It is bounded above by pi delta_n.

The elementary induction estimate a_n^2<=1/(3n+1) then yields, for exact partial sums W_{4,N} retaining n=0,...,N-1,
\[
\boxed{0<\mathscr W_4-\mathscr W_{4,N}
<\frac{\pi}{54(N-3/4)^3},\qquad N\ge3.} \tag{27}
\]
This bounds exact-arithmetic truncation, not floating-point rounding.

One may instead use the positive series starting at n=2:
\[
 C_4=\mathscr W_4-r_{01},
\]
\[
\begin{aligned}
r_{01}={}&(\pi-10\ell)\pi^2/3-80\ell^3\\
&+\frac1{16}[(\pi-10\ell+5)(\pi^2/3-3)-80(\ell-1/2)^3].
\end{aligned}
\]
The output JSON supplies this optional equivalent expression, including the compensating polynomial -3144pi^2 r01. The main expression keeps the signed sum because its evaluated part is shorter.

## 8. Numerical verification and limitations

The new code evaluates the original mixed elliptic moments by AGM quadrature on two reflected half intervals. It does not use the new identities in those integrands. It also evaluates both balanced 4F3 series directly, and evaluates four-shift periodizations by their separate convergent 5F4 representations.

At 85 working digits, observed absolute residuals are:

| Check | Residual magnitude |
|---|---:|
| Symmetric/antisymmetric quadratic relation (20) | 1.030e-84 |
| Cubic collapse (21) | 1.030e-84 |
| Old wheel conjecture, original folded c0,c1 moments | 1.318e-82 |
| Bailey identity at x=0.1,-0.08,0.04+0.035i | <3.1e-85 |
| Four-shift finite Fourier form, two shift patterns and two test points | <2.0e-85 |
| New series vs old wheel pair, weighted in C6 units, N=160,J=45 | 3.857e-83 |

The series acceleration uses exact rational gamma-ratio asymptotic coefficients with Hurwitz-zeta tails, not a fit. With x=n+1/4 and c_j=E_{2j}/(4j16^j),
\[
\log[g(n)\sqrt x]\sim\sum_{j\ge1}c_jx^{-2j}.
\]
Then h_n and delta_n follow by differentiation, and the new summand separates into rational coefficients multiplying x^{-4-2j}/pi and x^{-5-2j}/pi^2. The asymptotic expansion is not treated as convergent. Numerical settings (N,J)=(100,30),(160,45) are compared with the original moments at 55 and 85 digits.

Values from the new series are
\[
\mathscr W_4=-39.12114074200214923277182804749268411656156740497191\ldots,
\]
\[
C_4=0.0031381855426228070882143273219930797953194673358419\ldots.
\]
The replaced pair in C6 units is
\[
\frac{-6\pi^3\mathscr K_6-3360\pi^3\mathscr T_4}{2187}
=-900.83801291041535431952080185697316672800278858244\ldots.
\]
Both the old and new forms give this value. The new series term alone contributes +555.06649056... and its evaluated shift contributes -1455.90450347...; neither is an additive correction to the physical coefficient.

The exact script passes 40 algebraic checks. They include bivariate coefficient extraction, Bailey gamma prefactors, elimination of the derivative moments, the old wheel identity, the full weighted replacement, positivity inequalities, the cancellation in the evaluated polynomial, and preservation of all unaffected series and definitions. These are checks of the analytic derivation, not forty independent integral theorems.

The small floating-point residuals are not interval-certified bounds. Equation (27) is the separate rigorous direct-tail statement. No new six-loop graph integration or independent certification of the entire inherited reduction is claimed.

## 9. Reproduction

Python 3, SymPy and mpmath are sufficient.

```
python verify_algebra.py
python evaluate.py 55 --periodization
python evaluate.py 85 --periodization
```

The result JSON retains all unaffected definitions and supplies the new series, the full evaluated polynomial, and the optional positive-tail form. `inputs/previous_expression.json` is retained verbatim. `PROVENANCE.json` records its hash and the hashes of the local analytic inputs.

## Analytic sources

1. W. Groenevelt, *The Wilson function transform*, arXiv:math/0306424, equations (3.2)-(3.3): the two-term nonterminating Bailey/Wilson transformation. https://arxiv.org/html/math/0306424
2. NIST DLMF 5.5: gamma recurrence, reflection, and duplication. https://dlmf.nist.gov/5.5
3. NIST DLMF 5.11: gamma-ratio asymptotic expansions. https://dlmf.nist.gov/5.11
4. The inherited parameterized J(s), Mellin M(s), normalized c0,c1 contour formulas, and cubic Landen identity are supplied in the previous project notes; the relevant local inputs are retained under `inputs/`. No general-method source is presented as a prior evaluation of C6 or of the new wheel relation.
