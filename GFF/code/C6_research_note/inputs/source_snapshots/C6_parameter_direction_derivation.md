# C6(1): isolate the remaining hypergeometric parameter directions

## Result and scope

Input: `inputs/latest_expression_unchanged.json`, copied verbatim from
`C6_eighth_MeijerG_expression.json`. The normalization is `r6 = 2187 C6(1)`.

This continuation gives exact parameter-direction identities for the wheel and
seventh-power logarithmic block, and an arbitrary-finite-pole-order restriction
on a particular termwise Meijer-G matching method. It does **not** evaluate those
parameter derivatives in fixed built-in special-function values. Consequently it
does **not** supply the requested integration-, sum-, and derivative-free closed
form of the full coefficient. The accepted fixed-value expression and its known
polynomial are not modified.

The prior sixth- and eighth-power reductions, finite polylogarithmic expression,
source correction, and upstream graph/RG identification remain inherited. No
new all-sector numerical evaluation or interval certificate is claimed. The
primitive P_a is unchanged. Failed exploratory fits are not used in any identity.

The function families below are ordinary generalized hypergeometric functions,
not additional C6-specific infinite sums. Their derivatives are **intermediate
analytic targets**, not a substitute for the user's requested final values.

## 1. Separate the wheel's second-order parameter directions

For the proof retain

\[
 a_n=(1/2)_n/n!,\qquad h_n=\log2+H_n-H_{2n},\qquad
 \delta_n=\pi^2/3-4H_{2n}^{(2)}+2H_n^{(2)}.
\]

The current, zero-index-included wheel contribution is

\[
 B_W=-3144\pi^3D_4-1965\pi^4D_6,
 \quad D_4=\sum_{n\ge0}a_n^4\delta_n,
 \quad D_6=\sum_{n\ge0}(4n+1)a_n^6\delta_n.
\]

This is equivalent to the current native wheel quadrature, not to the old
n>=1 wheel without its index-zero compensation. For provenance that old object
satisfies

\[
 W_c=8D_4+5\pi D_6-(8+5\pi)\pi^2/3.
\]

Define the ordinary families, with u a proof parameter unrelated to the physical
epsilon expansion,

\[
 F_4(u)={}_4F_3\left(\begin{matrix}
 1/2+u,1/2-u,1/2,1/2\\1+u,1-u,1
 \end{matrix};1\right),
\]

\[
 F_6(u)={}_7F_6\left(\begin{matrix}
 5/4,1/2+u,1/2-u,1/2,1/2,1/2,1/2\\
 1/4,1+u,1-u,1,1,1
 \end{matrix};1\right).
\]

Both excesses are exactly one; both functions are even in u. They are analytic
on a sufficiently small complex neighborhood of zero, for example |u|<=1/8.
Set U4=F4(0), U6=F6(0). The exact identities are

\[
 \boxed{D_4=\tfrac12F_4''(0)+\tfrac{\pi^2}{3}F_4(0),\qquad
 D_6=\tfrac12F_6''(0)+\tfrac{\pi^2}{3}F_6(0).}
 \tag{1}
\]

### Coefficient proof

Without the optional (4n+1) weight, the nth coefficient of the p=4 or p=6
family is

\[
 c_{p,n}(u)=a_n^{p-2}\prod_{j=0}^{n-1}
 \frac{(j+1/2)^2-u^2}{(j+1)^2-u^2}.
\]

Hence c(0)=a_n^p, c'(0)=0, and

\[
 c_{p,n}''(0)=2a_n^p\left(2H_n^{(2)}-4H_{2n}^{(2)}\right)
 =2a_n^p(\delta_n-\pi^2/3).
\]

Multiplying by (4n+1) for p=6 and summing proves (1). On |u|<=1/8, the ratio
c_{p,n}(u)/a_n^p is uniformly bounded: its product consists of factors differing
from one by O((j+1)^-2), uniformly in u. Cauchy estimates on a slightly larger
small disk bound the first two derivatives by constant multiples of a_n^p.
The p=4 series and the weighted p=6 series are O(n^-2); thus uniform absolute
convergence justifies differentiation. No asymptotic expansion is being
summed, and no divergent series are subtracted.

A normalized version is sometimes useful. Gamma reflection gives

\[
 A(u)=\frac{\Gamma(1/2+u)\Gamma(1/2-u)}
 {\pi\Gamma(1+u)\Gamma(1-u)}
 =\frac{\tan(\pi u)}{\pi u},\qquad A(0)=1.
\]

As A'(0)=0 and A''(0)=2pi^2/3, one has (A F_p)''(0)=2D_p.
The gamma expression, not an unevaluated 0/0 quotient, fixes the normalization
at zero. This normalized formulation is still a parameter derivative.

### Complete wheel contribution in r6 units

Equation (1) gives

\[
 \boxed{B_W=-1572\pi^3F_4''(0)
 -\frac{1965}{2}\pi^4F_6''(0)-1048\pi^5U_4-655\pi^6U_6.}
 \tag{2}
\]

If this *optional derivative form* is used alongside the current ordinary
U4,U6 block, its two ordinary coefficients become

\[
 4\pi^3(C_d-262\pi^2)U_4,
 \qquad 2\pi^4(C_s-655\pi^2/2)U_6,
\]

where the existing coefficients are

\[
 C_d=96Q-42A^2-18A\pi-1227\pi^2,
 \quad C_s=60Q-105A^2/4-9A\pi-2469\pi^2/4.
\]

There is no known-polynomial shift. Equation (2) is not installed as a new
fixed-value answer in the preserved input expression.

## 2. Why the existing local Meijer-G construction cannot isolate delta

The previous sixth/eighth reductions used gamma-ratio kernels times rational
and trigonometric factors. Consider, more generally, the class

\[
 K(s)=\left[\frac{\Gamma(s)}{\Gamma(s+1/2)}\right]^p T(s),
 \qquad p\in\mathbb Z_{>0},
\]

where T has finite Laurent principal parts at s=-n and the corresponding
coefficients are independent of the formal harmonic variables h_n, delta_n,
and higher harmonic remainders. Rational and trigonometric multipliers and
finite linear combinations of the previously used kernels satisfy this local
condition. **This is not the class of all possible Meijer-G kernels.**

The inherited gamma/polygamma local expansion is

\[
 \frac{\Gamma(-n+e)}{\Gamma(1/2-n+e)}
 =\frac{a_n}{\sqrt\pi e}
 \exp\left[2h_ne+\frac12(\delta_n-2\pi^2/3)e^2+O(e^3)\right].
\]

Absorb e^-p T(-n+e) into a Laurent series. If the resulting pole has order
at most three, write its principal part as c3/e^3+c2/e^2+c1/e. After removing
the common a_n^p/pi^(p/2), the residue is

\[
 \boxed{c_1+2pc_2h_n+
 c_3\left(2p^2h_n^2+\frac p2\delta_n-\frac{p\pi^2}{3}\right).}
 \tag{3}
\]

It necessarily satisfies the **formal coefficient identity**

\[
 \boxed{[h_n^2]\operatorname{Res}=4p[\delta_n]\operatorname{Res}.}
 \tag{4}
\]

Thus a nonzero delta_n coefficient cannot appear without an h_n^2 coefficient
in a formal termwise match. The required ratios are 16 for p=4 and 24 for p=6.
The factor (4n+1) does not affect the conclusion.

### Higher finite pole order does not evade this formal restriction

For a pole of order N, the highest power of the formal variable h_n is

\[
 c_N\frac{(2p)^{N-1}}{(N-1)!}h_n^{N-1}.
\]

All higher logarithmic cumulants in the gamma expansion are independent of
h_n. Therefore, in a formal match to a polynomial of harmonic degree at most
two, a pole order N>3 forces c_N=0. Repeating this argument reduces the match
to order at most three, where (4) applies. The same argument applies after a
finite linear combination of kernels has been formed.

This extends the earlier three-kernel observation to arbitrary finite pole
order **within this local ansatz and under formal termwise matching**. It does
not assume or establish algebraic independence of harmonic sequences. It does
not exclude identities that hold only after summation, new gamma pole families,
other transformations, or a finite evaluation of the definite wheel period.
In particular this is not a theorem that C6 or its wheel is irreducible.

This also explains the successful preceding blocks. The inherited P_b
coefficient contains `312 h_n^2 + 13 delta_n`, whose ratio is 24=4*6.
The inherited eighth-power coefficient contains
`256 y_n h_n^2 + 8 y_n delta_n`, whose ratio is 32=4*8. Both fit (4).
The isolated wheel coefficient has a nonzero delta_n part and no h_n^2
part, so it does not fit the same local mechanism. This observation uses the
actual retained weights, not merely an example polynomial.

The paired parameter directions in (1) explain what is different: first-order
log derivatives cancel between +u and -u before taking the second derivative.
The trigamma term is then produced without its squared first derivative. A
separate functional identity is needed to evaluate that direction in fixed
values; a larger rational/trigonometric multiplier in the old kernel family
alone does not provide one.

## 3. First parameter derivatives for the five seventh-power streams

For r in {1,2,3,5,7}, set t=r/8, a=t+1/4, b=t+3/4. Define the ordinary family

\[
 Z_r(u)=t\left[\frac{\Gamma(a)}{\Gamma(b)}\right]^7
 {}_9F_8\left(\begin{matrix}
 1,1+t,(a+u)^{[7]}\\t,(b-u)^{[7]}
 \end{matrix};-1\right).
\]

The gamma prefactor is **fixed at u=0**. It must not be differentiated as if
it contained a+u or b-u. Then

\[
 \boxed{Z_r(0)=Z_r^{\rm old}(-1),\qquad Z_r'(0)=14L(r/8).} \tag{5}
\]

Indeed the logarithmic derivative of the nth normalized coefficient is
7[H_n(a)+H_n(b)]=14H_(2n)(2a). The old n=0 harmonic insertion is zero, consistent
with the derivative of the fixed coefficient. On a sufficiently small disk,
e.g. |u|<=1/56, the excess 3/2-14u has positive real part at least 5/4.
The differentiated coefficients have a summable log(n) times power bound, which
justifies the termwise derivative.

The complete logarithmic part is therefore

\[
 \boxed{B_7=672\pi^{3/2}\sum_{r\in\{1,2,3,5,7\}}p_r Z_r'(0),} \tag{6}
\]

where the displayed sum has exactly five terms and the existing weights are

\[
\begin{split}
 p_1&=\cos^7(\pi/8)(13+22\sqrt2),\quad p_2=-35,\\
 p_3&=\cos^7(\pi/8)(22\sqrt2-13),\\
 p_5&=-\sin^7(\pi/8)(22\sqrt2-13),\\
 p_7&=\sin^7(\pi/8)(13+22\sqrt2).
\end{split}
\]

Along with the retained ordinary seventh part, the full seventh contribution
can equivalently be organized as
96pi^(3/2) times the five-term finite combination
`b_r Z_r(0) + 7 p_r Z_r'(0)`.
The ordinary b_r coefficients are unchanged. Omitting them would incorrectly
discard the ordinary correction. Again (5)-(6) are intermediate parameter
identities, not an evaluated fixed-value expression.

## 4. The primitive and unchanged status

The primitive's previous Mellin convolution retains the shared factor
Gamma(1/2-s) Gamma(1/2-t) / Gamma(1-s-t). This is the beta coupling, not a
separable product of one-variable factors. This pass does not eliminate that
factor or produce a one-variable evaluation of P_a. In particular, the existing
primitive constant and all zero-index conventions are preserved.

Neither the parameter identities nor the restricted matching result prove
anything new about the graph/RG identification. The count of unresolved
fixed-value blocks remains three. No new full numerical C6 assembly was run.

## 5. Executed checks

`verify_exact.py` checks finite rational coefficient products independently of
the logarithmic differentiation derivation: n=0 through 20 for both wheel
families and all five seventh families. It also checks the generic residue
polynomial, the formal coefficient restriction, representative higher pole
orders, and complete r6 weights. Most of its 355 assertions are finite
coefficient checks, not separate mathematical identities.

Fresh mpmath differentiation at 70 decimal working digits gives:

| Family | Parameter derivative at zero | Reconstructed target |
|---|---|---|
| F4, second | -0.7390881409432229705654950892931654343009... | D4=3.3106221328531753153524813631844503710929... |
| F6, second | -0.9309704212628636166366294600715213586678... | D6=3.3158554158321918585143241125768512077640... |

The reconstructed values differ from the *inherited* fine interval midpoints
by less than 7.25e-71 and 3.63e-71, respectively. These discrepancies are
floating-point checks, not newly certified errors.

For the five seventh streams, fresh parameter differentiation divided by 14
agrees with the *saved* 60-digit quadratures to absolute discrepancy below
4.82e-60. Those quadratures were not rerun here. Their rounded source values
limit the meaningful comparison. Reports distinguish all fresh computations
from inherited references.

The WL file is diagnostic. It deliberately marks derivatives as inactive and
reports `FullFixedValueFormEstablished -> False`. It was not executed in a
Wolfram kernel. There is no function purporting to return the full C6 value.

## Sources and retained inputs

- Latest C6_eighth_MeijerG_expression.json: unchanged accepted partial formula,
  known polynomial, and three unresolved blocks. Included verbatim under inputs.
- C6_central_binomial_wheel_reduction.md and expression.json: central wheel
  definition, index convention, gamma-ratio expansion and inherited symmetries.
- C6_Mathematica_native.wl: weights of the zero-included wheel and five seventh
  logarithmic streams. These weights were not fitted to a C6 numerical value.
- C6_standard_even_intervals.json: inherited rational D4/3 and D6/3 enclosures.
- C6_Mathematica_native_checks.json: inherited 60-digit seventh quadratures.
- NIST DLMF 16.2: ordinary hypergeometric coefficients and convergence.
  https://dlmf.nist.gov/16.2
- NIST DLMF 16.17: standard Meijer-G Mellin-Barnes convention.
  https://dlmf.nist.gov/16.17
- NIST DLMF 5.15 and 5.5: polygamma values/recurrence and gamma reflection.
  https://dlmf.nist.gov/5.15 ; https://dlmf.nist.gov/5.5
- Wolfram HypergeometricPFQ and Derivative documentation:
  https://reference.wolfram.com/language/ref/HypergeometricPFQ.html
  https://reference.wolfram.com/language/ref/Derivative.html

The new coefficient and restricted-matching arguments above are derived here;
they are not attributed as stated theorems to the general references.
