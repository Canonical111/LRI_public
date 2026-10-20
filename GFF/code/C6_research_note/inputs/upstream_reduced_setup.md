# A complete finite special-function representation of the corrected C₆(1)

## Scope and precise meaning of the result

Starting from the corrected renormalization-group reduction supplied in this conversation, all four remaining integrals are replaced here by **43 explicitly specified four-index generalized-Lauricella/Horn values** at unit arguments. All their parameters are positive rationals, and every defining multiple series converges absolutely. There are no regulator derivatives, Laurent-coefficient extractions, undefined graph masters, or remaining integrals in the final representation.

This is a complete finite representation **in an enlarged special-function class**. It is **not** a proof of a reduction to the ordinary one-variable gamma–hypergeometric basis requested earlier. The existing finite multiple-polylogarithm evaluation of the kite is retained. A formula in explicitly defined multivariate hypergeometric functions must not be described as a new one-variable summation theorem.

The starting graph identities, previously evaluated primitive periods, finite polylogarithm table, and repaired RG assembly are inherited analytic inputs. This calculation verifies their conversion and numerical assembly; it does not independently rederive the whole six-loop calculation. In particular, the previously stated zig-zag identification qualifications remain applicable.

No numerical value of the full coefficient is used to determine any coefficient in the formulas below. The unproved wheel relation involving 8c₀+c₁ is not used.

The convention is
\[
\Delta_{\mathcal E}=\frac12-\frac\epsilon6+\sum_{n\ge2}C_n(1)\epsilon^n,
\qquad r_6=2187C_6(1).
\]

## 1. The four-index function, defined by its convergent series

For two lists of Gauss parameter triples
\[
\mathcal A=((a_i,b_i;c_i))_{i=1}^{r},\qquad
\mathcal B=((\tilde a_j,\tilde b_j;\tilde c_j))_{j=1}^{s},\qquad r+s=4,
\]
put M=Σmᵢ and N=Σnⱼ and define
\[
\boxed{\begin{aligned}
\mathbb H_{\alpha,\beta}(\mathcal A;\mathcal B)
={}&\frac{\Gamma(\alpha)\Gamma(\beta)}{\Gamma(\alpha+\beta)}
\sum_{\substack{m_1,\ldots,m_r\ge0\\n_1,\ldots,n_s\ge0}}
\frac{(\alpha)_M(\beta)_N}{(\alpha+\beta)_{M+N}}\\
&\times\prod_{i=1}^{r}\frac{(a_i)_{m_i}(b_i)_{m_i}}{(c_i)_{m_i}m_i!}
\prod_{j=1}^{s}\frac{(\tilde a_j)_{n_j}(\tilde b_j)_{n_j}}{(\tilde c_j)_{n_j}n_j!}.
\end{aligned}}\tag{1}
\]
Empty lists and empty products are permitted. All four variables of this multiple hypergeometric function are set to one. Here (a)ₙ=Γ(a+n)/Γ(a).

This is a specialization of a generalized Lauricella/Horn hypergeometric series, rather than an ordinary pFq. For example, increasing a left index by one multiplies its summand by
\[
\frac{\alpha+M}{\alpha+\beta+M+N}
\frac{(a_i+m_i)(b_i+m_i)}{(c_i+m_i)(m_i+1)},
\]
a rational function of the indices. The right-index ratio has β+N in place of α+M. These ratios also specify the associated Horn system. General gamma-ratio multiple-series conventions are described in Bytev–Kniehl–Moch, especially their generalized-Lauricella appendix; their work is not an evaluation of this Ising coefficient.

Only these five parameter triples occur:

| Formal letter | (a,b;c) |
|---|---|
| k | (1/2,1/2;1) |
| u | (1/4,3/4;1) |
| v | (1/4,1/4;1) |
| h | (1/4,1/4;1/2) |
| j | (1,1;2) |

A barred letter denotes the same triple placed in the **right list** of (1); an unbarred letter is placed in the left list. Define the finite linear evaluation map
\[
T_{\alpha,\beta}[x_1\cdots x_r\bar y_1\cdots\bar y_s]
=\mathbb H_{\alpha,\beta}((x_1,\ldots,x_r);(y_1,\ldots,y_s)),\qquad r+s=4,
\tag{2}
\]
where each letter is replaced by its tabled triple. Extend this map linearly to the finite degree-four polynomials below. **T is finite substitution notation, not an unevaluated integral operator.** For example,
\[
T_{1/2,5/2}[k^2\bar j^2]
=\mathbb H_{1/2,5/2}
\bigl((\tfrac12,\tfrac12;1),(\tfrac12,\tfrac12;1);
(1,1;2),(1,1;2)\bigr).
\]

The exact reflection identity
\[
\mathbb H_{\alpha,\beta}(\mathcal A;\mathcal B)
=\mathbb H_{\beta,\alpha}(\mathcal B;\mathcal A)\tag{3}
\]
is used to combine repeated values. No other conjectural identification is made.

## 2. Finite formulas replacing the four remaining moments

Set
\[
\eta=\frac{\Gamma(1/4)^2}{2\pi^{3/2}}=\frac{\sqrt Q}{2\pi},
\qquad Q=\frac{\Gamma(1/4)^4}{\pi},
\]
and form the explicit commuting polynomials
\[
S=k+\bar k,\qquad
M=u^2+\bar u^2+\frac3{\sqrt2}u\bar u,
\]
\[
B=2\eta^2\bar h^2+\eta v\bar h,
\qquad \bar B=2\eta^2h^2+\eta\bar v h.
\tag{4}
\]
A bar interchanges every barred and unbarred letter; it is not complex conjugation here.

The new expressions are
\[
\boxed{P_a=16\pi^4\left\{2T_{1/2,1}[M\bar B]+T_{1/2,1/2}[B\bar B]\right\},}\tag{5}
\]
\[
\boxed{\begin{aligned}
\mu=8\pi^3\bigl\{
&-T_{1,3/2}[S(M+B)\bar j]
+T_{2,1/2}[SMj]
+T_{3/2,1/2}[S\bar B j]\bigr\},
\end{aligned}}\tag{6}
\]
\[
\boxed{c_1=2\pi^2\left\{
T_{1/2,5/2}[S^2\bar j^2]
-T_{3/2,3/2}[S^2j\bar j]
+T_{1/2,3}[S^2\bar j^2]\right\},}\tag{7}
\]
\[
\boxed{c_0=2\pi^2\left\{
T_{3/2,3/2}[S^2j\bar j]
+2T_{5/2,1}[S^2j^2]
-2T_{3/2,2}[S^2j\bar j]\right\}.}\tag{8}
\]

Equations (1), (2), and (4) make (5)–(8) finite specifications of ordinary fixed-parameter multiple hypergeometric values. The individual formulas contain 9, 20, 8, and 8 distinct values after (3). Two wheel values are shared, leaving **43 distinct values** in their combined contribution. This is not a count of independent transcendental constants.

## 3. The complete coefficient, with no remaining integral symbols

Define
\[
\boxed{\begin{aligned}
\mathcal R={}&1536\pi^4\left\{2T_{1/2,1}[M\bar B]+T_{1/2,1/2}[B\bar B]\right\}\\
&+784\pi^3\left\{T_{1,3/2}[S(M+B)\bar j]-T_{2,1/2}[SMj]-T_{3/2,1/2}[S\bar B j]\right\}\\
&+\pi^2\left\{912T_{3/2,3/2}[S^2j\bar j]+288T_{5/2,1}[S^2j^2]
-288T_{3/2,2}[S^2j\bar j]\right.\\
&\hspace{20mm}\left.-768T_{1/2,5/2}[S^2\bar j^2]-768T_{1/2,3}[S^2\bar j^2]\right\}.
\end{aligned}}\tag{9}
\]
This is the fully substituted form of 96Pₐ+72c₀−384c₁−98μ.

The corrected thermal coefficient is
\[
\boxed{C_6(1)=\frac{E+\mathcal C_{\rm MPL}+\mathcal R}{2187}.}\tag{10}
\]
Every object on the right is explicitly defined below or in (1)–(9). In particular, there is no N₆, unspecified subtraction term, or graph-indexed coefficient left in (10).

Put A=π+4log2 and G=Σₙ≥₀(−1)ⁿ/(2n+1)² (Catalan's constant). The ordinary-special-value part is
\[
\boxed{\begin{aligned}
E={}&24P_b+24P_{Z,6}+\frac13P_K-36AP_5
+(12Q-12A^2-6\pi^2)P_4-9A\mathcal L\\
&+\frac Q8\left[63A^3+120AG+79A\pi^2+2013\pi^3
+54204\zeta(3)+1140AQ\right]\\
&+Q^2\left(\frac{58}{9}V-\frac{1247}{2}\pi\right)-8352\pi^4U+\mathcal P,
\end{aligned}}\tag{11}
\]
where
\[
\boxed{\begin{aligned}
\mathcal P={}&\frac{21}{640}A^5-\frac{4345}{64}A^3\pi^2
+\frac{23997}{64}A^2\pi^3+\frac{99255}{16}A^2\zeta(3)\\
&-624AG(16G+3\pi^2)-\frac{398587}{640}A\pi^4-11424A\pi\zeta(3)\\
&+272\pi G(48G-\pi^2)+\frac{76799}{128}\pi^5
+\frac{69581}{16}\pi^2\zeta(3)+\frac{1410297}{8}\zeta(5).
\end{aligned}}\tag{12}
\]
The polynomial (11)–(12) includes the previously repaired contributions R147,−3=R148,−3=2/5. They must **not** be added a second time. It also includes the polynomial part of the finite kite evaluation. Its nonpolynomial part is precisely C_MPL in Section 5.

### 3.1 Ordinary hypergeometric definitions

The notation a^{×m} means m repeated parameters. Define
\[
B_-=\Gamma(1/4)^4\,{}_4F_3\left(\begin{matrix}1/4,1/4,1/2,1/2\\3/4,3/4,1\end{matrix};1\right),
\]
\[
B_+=\frac{64\pi^4}{\Gamma(1/4)^4}\,{}_4F_3\left(\begin{matrix}3/4,3/4,1/2,1/2\\5/4,5/4,1\end{matrix};1\right),
\]
\[
P_4=13B_--3B_+,\qquad
\mathcal L=-\frac{13A-3\pi}{2}B_-+\frac{3A-\pi}{2}B_+.
\tag{13}
\]
The two product-period values are
\[
U={}_5F_4\left(\begin{matrix}1/4,(1/2)^{\times4}\\5/4,1^{\times3}\end{matrix};1\right),
\qquad
V={}_6F_5\left(\begin{matrix}1,1,(5/4)^{\times4}\\2,(7/4)^{\times4}\end{matrix};1\right).
\tag{14}
\]
For P_b put
\[
H_-={}_7F_6\left(\begin{matrix}1,(1/4)^{\times6}\\(3/4)^{\times6}\end{matrix};1\right),\quad
H_0={}_6F_5\left(\begin{matrix}(1/2)^{\times6}\\1^{\times5}\end{matrix};1\right),\quad
H_+={}_7F_6\left(\begin{matrix}1,(3/4)^{\times6}\\(5/4)^{\times6}\end{matrix};1\right),
\]
\[
P_b=\frac{6Q^3}{\pi}(2H_--1)-104\pi^5H_0+\frac{2^{18}\pi^5}{Q^3}H_+.
\tag{15}
\]
For k=7,8 define the finite-parameter family
\[
\begin{aligned}
Z_r^{(k)}(z)={}&\frac r8
\left[\frac{\Gamma((r+2)/8)}{\Gamma((r+6)/8)}\right]^k\\
&\times{}_{k+2}F_{k+1}\left(\begin{matrix}1,1+r/8,((r+2)/8)^{\times k}\\r/8,((r+6)/8)^{\times k}\end{matrix};z\right).
\end{aligned}\tag{16}
\]
Set Yᵣ=Zᵣ⁽⁸⁾(1), r=1,2,7, and
\[
\mathcal H=(17+12\sqrt2)Y_1-(17-12\sqrt2)Y_7.
\]
Then
\[
P_{Z,6}=\pi^2[(816-828\sqrt2)Y_2+23\mathcal H],
\qquad
P_K=\pi^2[432(1-\sqrt2)Y_2+12\mathcal H].
\tag{17}
\]
For P₅ put Zᵣ=Zᵣ⁽⁷⁾(−1), r=1,2,3,5,7, c=cos(π/8), s=sin(π/8), and
\[
X_0=Z_2,\quad X_+=c^7Z_3-s^7Z_5,\quad X_-=c^7Z_1+s^7Z_7.
\]
The existing evaluation is
\[
P_5=16\pi^{3/2}\left[-35X_0+(22\sqrt2-13)X_++(22\sqrt2+13)X_-\right].
\tag{18}
\]
All the one-variable values in (13)–(18) are convergent. Their graph identifications and prior analytic assumptions are inherited, not inferred from the current numerical agreement.

## 4. Derivation of the new four-index evaluations

The inherited corrected expression is
\[
2187C_6=E_{\rm repaired}+96P_a+72c_0-384c_1-98\mu.
\tag{19}
\]
With
\[
F(x)=\int_{\mathbb R}|y(1-y)(y-x)|^{-1/2}\,dy,
\quad
J(x)=\int_{\mathbb R}\frac{F(y)}{\sqrt{|y(1-y)(x-y)|}}\,dy,
\]
its four moments are
\[
P_a=\int_{\mathbb R}J(x)J(1/x)\frac{dx}{|x|},
\quad
\mu=\int_{\mathbb R}\frac{F(x)J(x)}{\sqrt{|1-x|}}\log\left|\frac{x}{1-x}\right|dx,
\]
\[
c_1=\frac14\int_{\mathbb R}\rho(x)\log^2\left|\frac{x}{1-x}\right|dx,
\qquad
c_0=\frac12\int_{\mathbb R}\rho(x)\log|x|\log|1-x|dx,
\quad \rho(x)=\frac{F(x)^2}{\sqrt{|x(1-x)|}}.
\tag{20}
\]
These integrals are used only to prove the new fixed-value formulas; they do not remain in (10).

For this derivation, interpret the formal letters in Section 1 as Gauss functions of t, and bars as evaluation at 1−t. The earlier kernel evaluations give
\[
F(t)=2\pi S(t),\qquad J(t)=4\pi^2M(t),\quad 0<t<1,
\]
\[
J(-a)=\frac{4\pi^2}{\sqrt{1+a}}B\!\left(\frac a{1+a}\right),\quad a>0,
\qquad J(x)=J(1-x).
\tag{21}
\]
They follow from the evaluated repeated trivalent kernel; the negative-interval prefactor is essential. The Gauss coefficient η in (4) is fixed by that formula, not fitted.

### 4.1 Folding P_a

The positive real intervals are paired by x→1/x. For 0<x<1,
\[
J(1/x)=4\pi^2\sqrt x\,B(1-x).
\]
For x=−a use t=a/(1+a). Since da/a=dt/[t(1−t)], equation (21) gives
\[
P_a=32\pi^4\int_0^1t^{-1/2}M(t)B(1-t)dt
+16\pi^4\int_0^1[t(1-t)]^{-1/2}B(t)B(1-t)dt.
\tag{22}
\]
This proves the beta weights in (5).

### 4.2 Folding the five-loop logarithmic moment

Use F(−t/(1−t))=√(1−t)F(t) and F(1/t)=√tF(t). Splitting the real line into its three intervals yields
\[
\begin{aligned}
\mu=4\pi^2\int_0^1F(t)\left[
\frac{M(t)+B(t)}{\sqrt{1-t}}\log t
-\left(\frac{M(t)}{\sqrt{1-t}}+
\frac{B(1-t)}{\sqrt{t(1-t)}}\right)\log(1-t)\right]dt.
\end{aligned}\tag{23}
\]
The logarithms have the elementary Gauss evaluations
\[
\log t=-(1-t)\,{}_2F_1(1,1;2;1-t),\qquad
\log(1-t)=-t\,{}_2F_1(1,1;2;t).
\tag{24}
\]
Thus no differentiation of a beta or hypergeometric parameter is needed. Substitute (24) into (23), and F=2πS, to obtain (6).

### 4.3 Folding the two wheel moments

Let L=log t, C=log(1−t),
\[
d_0=[t(1-t)]^{-1/2},\quad d_-=t^{-1/2},\quad d_+=(1-t)^{-1/2}.
\]
The three-interval folding of (20) gives
\[
c_1=\pi^2\int_0^1S(t)^2\{d_0(L-C)^2+d_-L^2+d_+C^2\}\,dt,
\]
\[
c_0=2\pi^2\int_0^1S(t)^2\{d_0LC+d_-(C^2-LC)+d_+(L^2-LC)\}\,dt.
\]
Because S(t)² is symmetric about 1/2, these become
\[
c_1=2\pi^2\int_0^1S(t)^2\{d_0L^2-d_0LC+d_-L^2\}\,dt,
\]
\[
c_0=2\pi^2\int_0^1S(t)^2\{d_0LC+2d_-(C^2-LC)\}\,dt.
\tag{25}
\]
Applying (24) supplies exactly the shifted beta exponents in (7)–(8). This does not use the conjectural identity for 8c₀+c₁.

### 4.4 Evaluation of the beta products and convergence

Expanding each Gauss function in the right-hand side of (22)–(25), each term integrates to
\[
\int_0^1t^{\alpha+M-1}(1-t)^{\beta+N-1}dt
=\frac{\Gamma(\alpha)\Gamma(\beta)}{\Gamma(\alpha+\beta)}
\frac{(\alpha)_M(\beta)_N}{(\alpha+\beta)_{M+N}}.
\tag{26}
\]
This is precisely (1), via Euler beta integration. Each Gauss factor has positive series coefficients. The four zero-balanced factor types grow at most logarithmically at their singular endpoint; v has c−a−b=1/2 and is finite there. All beta exponents used in (5)–(8) are positive. Consequently every product is bounded by an integrable beta weight times a polynomial in endpoint logarithms. Tonelli's theorem justifies integration term by term and proves absolute convergence of each individual four-index series at (1,1,1,1).

No cancellation of divergent series is used. Signed coefficients appear only when the finitely many separately convergent values are combined.

## 5. Explicit finite multiple-polylogarithm part

The pre-existing kite formula contributes
\[
\boxed{\mathcal C_{\rm MPL}=1632\mathfrak a_4+1632\pi\mathfrak b_3-1224\pi^2\mathfrak b_2.}\tag{27}
\]
The following finite word rules specify it without referring to a master integral or a parameter derivative. They are the unchanged definitions from the earlier kite evaluation.

For indices sᵢ≥1 use
\[
\operatorname{Li}_{s_1,\ldots,s_d}(z_1,\ldots,z_d)
=\sum_{n_1>\cdots>n_d>0}\frac{z_1^{n_1}\cdots z_d^{n_d}}
{n_1^{s_1}\cdots n_d^{s_d}}.
\tag{28}
\]
For a word ending in a nonzero letter, define its GPL value by
\[
\mathcal V(0^{s_1-1},a_1,\ldots,0^{s_d-1},a_d)
=(-1)^d\operatorname{Li}_{s_1,\ldots,s_d}
(1/a_1,a_1/a_2,\ldots,a_{d-1}/a_d).
\tag{29}
\]
All words in the fully expanded final table start with a letter different from 1 and end in a nonzero letter. The resulting multiple-polylogarithm arguments belong to {1,−1,i,−i}. They are convergent values; no regularized endpoint value remains in the exported expression.

For a compact finite description use letters e₀,e₁,e₋₁,eᵢ,e₋ᵢ, ordinary concatenation, and the shuffle product ⨿. Constants multiply the empty word. Put
\[
q=e_1+e_{-1}+e_i+e_{-i},\quad \ell_-=e_1+e_{-1},\quad\ell_+=e_i+e_{-i},
\]
\[
F_2=-4e_0q,\quad F_3=8e_0qq,\quad F_4=-16e_0qqq+16e_0qe_0q,
\]
\[
\mathscr T_-(W)=\tfrac12(e_{-1}-e_1)W,\qquad
\mathscr T_+(W)=\frac{e_i-e_{-i}}{2i}W.
\]
Then
\[
\begin{aligned}
\mathfrak a_4=\mathcal V\mathscr T_-\left[
F_4-\frac{19\pi^4}{360}
+2\ell_-\amalg(F_3-2\zeta(3))
+2(\ell_-\amalg\ell_-)\amalg(F_2-\pi^2/6)
\right],
\end{aligned}
\]
\[
\mathfrak b_2=\mathcal V\mathscr T_+[F_2+2\ell_+\amalg\ell_+],
\]
\[
\mathfrak b_3=\mathcal V\mathscr T_+\left[
F_3+2\ell_+\amalg F_2+\tfrac43\ell_+\amalg\ell_+\amalg\ell_+
\right].\tag{30}
\]
Before applying (29), eliminate intermediate words beginning in 1 by the finite shuffle reduction assigning the single-letter word (1) the regularized value zero. Explicitly, for w=(1,v), expand the shuffle (1)⨿v. If w occurs with multiplicity m, replace w by −1/m times the sum of the other shuffle terms, and continue recursively; an all-1 word maps to zero. On these endpoint-subtracted combinations this operation produces their ordinary convergent limits. The attached machine table already performs this operation, so evaluating (10) does not require any limiting procedure.

Expanding (27)–(30) gives exactly the 292 GPL terms in `results/complete_expression.json`. `inputs/Y_multiple_polylogarithms.json` separately lists the equivalent multiple-Li values for Y; the nonpolynomial weights in C_MPL are 17/3 times those Y weights. The table is inherited and not counted as a new polylogarithm reduction.

## 6. Direct evaluation of the four-index values

The numerical implementation evaluates the fixed-value formula (1), not the supplied graph moments. It uses Gauss connection formulas to develop each factor about the appropriate endpoint on two half intervals. This is an exponentially convergent acceleration of the positive multiple sum, not a new integration.

For a zero-balanced Gauss factor,
\[
{}_2F_1(a,b;a+b;1-x)
=\frac{\Gamma(a+b)}{\Gamma(a)\Gamma(b)}
\sum_{n\ge0}\frac{(a)_n(b)_n}{(n!)^2}
\left[2\psi(n+1)-\psi(n+a)-\psi(n+b)-\log x\right]x^n.
\tag{31}
\]
The reflected v factor has the two convergent branches
\[
\begin{aligned}
{}_2F_1(1/4,1/4;1;1-x)
={}&\frac{\sqrt\pi}{\Gamma(3/4)^2}{}_2F_1(1/4,1/4;1/2;x)\\
&-\frac{2\sqrt\pi}{\Gamma(1/4)^2}\sqrt x\,{}_2F_1(3/4,3/4;3/2;x).
\end{aligned}\tag{32}
\]
The j factor at 1−x is −log x/(1−x). Multiplying these expansions and the analytic weight (1−x)^{β−1} produces only powers xⁿ, half-powers xⁿ⁺¹ᐟ², and powers of log x through degree four. Each term is summed by
\[
\int_0^{1/2}x^{s-1}(-\log x)^d dx
=2^{-s}\sum_{k=0}^d\binom dk\frac{k!(\log2)^{d-k}}{s^{k+1}}.
\tag{33}
\]
Integer fixed-point polynomial products accelerate these finite convolutions. There is no quadrature call in `evaluate_values.py`.

### Explicit analytic truncation bound

On |x|=3/4, the sum of analytic coefficient-function majorants for any one of the five Gauss types, in either endpoint expansion, is at most 40. This follows from the coefficient ratio bounds, the zero-balanced leading digamma constants (the largest is π+6log2<8), and (32). The analytic beta-weight factor has bound at most 4 for the β values used here. Thus the product majorant is at most 4·40⁴, including the finite logarithmic and half-power channels.

Cauchy's coefficient bound and s≥1/2 give the uniform one-value tail
\[
\boxed{|\mathbb H-\mathbb H_N|
\le 2\cdot3\cdot(4\cdot40^4)\cdot768\,(2/3)^N.}\tag{34}
\]
Here degrees n=0,...,N−1 are retained in each analytic endpoint series. The factors 2 and 3 count the two halves and the geometric tail; 768 bounds d!/s^{d+1} for d≤4,s≥1/2. Terms with half-powers only improve the bound.

For the complete weighted contribution R/2187, summing absolute coefficient bounds gives a truncation allowance below 3.63×10⁻⁹¹ at N=600. The coefficient norm is bounded by the exact integer 75798528, using π<4, √2<3/2, and η<2. The last inequality follows from Γ(1/4)<4+1/2 and π>3; thus no floating-point gamma estimate is used in this bound. **This is an exact-arithmetic series-tail bound. It does not include rounding of gamma/elementary constants or fixed-point convolutions.** The current evaluator is not interval arithmetic. No new rigorous 90-digit enclosure of the complete coefficient is claimed.

### Fresh numerical comparisons

Independent evaluations of the multiple-series formula were run at (N,digits)=(180,55),(400,85),(600,125). At the last setting they give
\[
P_a=334926.04524805183788322200124007778661308590525313668\ldots,
\]
\[
\mu=54292.238443788236565004976469781432292265267961065230\ldots,
\]
\[
c_1=9859.10247185916821546853047871650868118760915635997\ldots,
\qquad c_0=691.40121478917148734772701193096297014587050472304\ldots.
\]
The combined contribution is
\[
\frac{\mathcal R}{2187}
=10560.65227004692684305804529768668365362995491742778\ldots.
\tag{35}
\]

Fresh quadrature of the pre-series moment formulas, using stable elliptic AGM and Gauss kernels, was separately run at 65 and 85 decimal digits. At 85 digits the largest observed absolute difference from the new series is 1.27×10⁻⁸⁰ (Pₐ). For c₀ it is 2.48×10⁻⁸³; μ and c₁ round to the same numbers at that precision. These are numerical cross-checks, not interval-certified errors. Both routes retain the inherited graph-to-kernel identities.

The exact conversion/implementation checker passes 288 checks. Most are parameter/convergence and term-count checks, not new integral identities. The substantive checks include both wheel foldings, logarithm insertion, reflection combination, equality of the complete weighted expression, invariance of the known polynomial, unchanged finite GPL terms, retention of the source repair exactly once, and signed integer convolution against a separately calculated exact product.

## 7. Numerical full-coefficient assembly and limitations

The ordinary pFq constants in (13)–(18) were freshly evaluated at 50 and 85 digits. The existing 292 GPL terms were also freshly summed, by midpoint Taylor expansions rather than a graph integral. Combined with (35), the formula gives
\[
\boxed{C_6(1)\approx14331.687032758054320445463255246217118317323061989.}\tag{36}
\]
This is the numerical value of the **accumulated corrected analytic representation**, not a newly certified physical accuracy claim. It differs from the independently retained all-sector estimator 14331.6870327683769636393... by −1.03226431938×10⁻⁸, within the original empirical allowance 4.9×10⁻⁷. That allowance remains empirical. The agreement does not independently prove every upstream graph normalization or special-period identification.

The present pass does not use or prove the conjecture
\[
8c_0+c_1\stackrel?=(2\pi^2+20\pi\log2+52\log^22)B_-
-(4\pi\log2+12\log^22)B_+.
\]

**What is complete:** the finite specification (10) in ordinary hypergeometric, multiple-polylogarithmic, and four-index Horn special values, with every parameter explicit and no remaining integral or regulator derivative.

**What is not complete:** reduction to the earlier strictly one-variable gamma–hypergeometric basis; minimality or arithmetic independence; a rigorous enclosure of the full physical coefficient; a new independent derivation of the entire upstream RG/graph calculation.

## 8. Reproduction

The scripts need Python 3, mpmath, and SymPy. No network access is needed.

```text
python formula.py
python verify_algebra.py
python evaluate_values.py 180 55
python evaluate_values.py 400 85
python evaluate_values.py 600 125
python gpl_values.py 85 350
python check_quadrature.py 85
python evaluate_complete.py 85
```

`results/four_index_values.json` gives every one of the 43 values with its rational parameters and coefficient. `results/complete_expression.json` combines that table with the explicit ordinary-special-value polynomial and the finite GPL table. Input hashes and origins are recorded in `PROVENANCE.json`.

## References and provenance

1. Supplied `C6_missing_pole_repair_and_zigzag_reduction.md` and `C6_corrected_reduced_expression.json`: corrected RG expression, the two omitted leading poles, moment normalizations, and numerical all-sector comparison.
2. Supplied `C6_new_primitive_closed_form.md`, `C6_wheel_certified_evaluation.md`, and preceding period notes: kernel evaluations and inherited special-value identities.
3. Supplied `C6_cyclotomic_kite_evaluation.md` and `Y_multiple_polylogarithms.json`: finite GPL formula and conventions.
4. V. Bytev, B. Kniehl, S. Moch, *Derivatives of Horn-type hypergeometric functions with respect to their parameters*, arXiv:1712.07579, especially the gamma-ratio series and generalized-Lauricella notation: https://arxiv.org/html/1712.07579 . Used to identify the function class, not as a published Ising evaluation.
5. NIST DLMF §15.6, Euler integral representations: https://dlmf.nist.gov/15.6 .
6. NIST DLMF §15.8, Gauss connection formulas, especially the zero-balanced limiting formula: https://dlmf.nist.gov/15.8 .
7. E. Panzer, *Algorithms for the symbolic integration of hyperlogarithms with applications to Feynman integrals*, arXiv:1403.3385: https://arxiv.org/html/1403.3385 . General GPL/shuffle context; the finite kite word table is an inherited project result.

The graph-specific formulas (5)–(12) are derived in this note from the inherited kernel and corrected-assembly inputs. They are not attributed to the general references.
