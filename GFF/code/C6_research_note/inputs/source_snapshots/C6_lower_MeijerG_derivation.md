# A lower-order finite Meijer-G representation of the U4,U6 block in C6(1)

## Result and scope

The accepted input is `inputs/previous_expression.json`, an unchanged copy of
`C6_eighth_MeijerG_expression.json`. The Dougall companion and parameter-direction
notes were diagnostics and did not replace that accepted formula.

This continuation reduces the U6 very-well-poised 7F6(1) to a G44^(2,2)(1) with
only zero and half-integer parameters. It also combines the U4,U6 block into one
ordinary univariate G55^(2,3)(1), with a real angle parameter determined by the
already known A and Q. The latter is a linear-combination encoding, not a theorem
of arithmetic dependence or a new elementary evaluation of these periods.

The three unresolved blocks remain the wheel, the seventh-power logarithmic
sector, and the primitive Pa. No integration-free/sum-free full C6 is claimed.
All graph/RG identifications and the source correction are inherited. No new
full-coefficient numerical evaluation or interval certificate is made.

## 1. Complete finite substitution

Put
\[
 A=\pi+4\log2,\qquad Q=\Gamma(1/4)^4/\pi,
\]
\[
 C_d=96Q-42A^2-18A\pi-1227\pi^2,
 \qquad C_s=60Q-\frac{105}{4}A^2-9A\pi-\frac{2469}{4}\pi^2.
\]
The two input values are
\[
 U_4={}_4F_3((1/2)^{[4]};1^{[3]};1),
\]
\[
 U_6={}_7F_6(5/4,(1/2)^{[6]};1/4,1^{[5]};1),
\]
and their COMPLETE contribution to r6=2187 C6(1) is
\[
 B_{\rm lower}=4\pi^3C_dU_4+2\pi^4C_sU_6.                  \tag{1}
\]
The symbols U4 and U6 here are the current central-binomial periods, not the
older ordinary U,V values already eliminated in a previous continuation.

Define two ordinary Meijer-G values with their splits understood as in [1,2]:
\[
 g_{13}=G_{4,4}^{1,3}(1\mid (1/2)^{[4]};0^{[4]}),\qquad
 g_{22}=G_{4,4}^{2,2}(1\mid (1/2)^{[4]};0^{[4]}).
\]
Then
\[
 \boxed{U_4=\frac{g_{13}}\pi,\qquad
 U_6=\frac{2g_{22}}{\pi^2}.}                              \tag{2}
\]
Consequently a rational-parameter alternative to (1) is
\[
 \boxed{B_{\rm lower}=4\pi^2(C_dg_{13}+C_sg_{22}).}         \tag{3}
\]

To combine the two function calls, set
\[
 X=-C_d,\quad Y=-C_s,\quad
 \rho=\sqrt{X^2+Y^2},\qquad
 \alpha=\frac1\pi\arctan\frac YX.
\]
For the actual A,Q, both X and Y are positive. Hence alpha is an unambiguous
real number in (0,1/2). Introduce the fixed ordinary value
\[
 g_\alpha=G_{5,5}^{2,3}
 \left(1\;\middle|\;(1/2)^{[4]},\alpha;0^{[4]},\alpha\right),
\]
with exact Mathematica splits

```wolfram
MeijerG[
  {{1/2, 1/2, 1/2}, {1/2, alpha}},
  {{0, 0}, {0, 0, alpha}},
  1
]
```

The full replacement is
\[
 \boxed{B_{\rm lower}=-4\pi^2\rho\,g_\alpha.}              \tag{4}
\]
The two alpha entries do NOT cancel. Both are in denominator gamma groups.
The final value (4) contains no integration, sum, limit, or parameter derivative.
Alpha is computed only from known constants, not from U4 or U6.

## 2. Proof of the lower-order identities

All Barnes contours in this section run upward on Re(s)=1/4. Write
\[
 R(s)=\left[\frac{\Gamma(s)}{\Gamma(s+1/2)}\right]^4.
\]
The kernels of g13 and g22 are respectively
\[
 M_1(s)=\frac{\Gamma(s)\Gamma(1/2-s)^3}
               {\Gamma(1-s)^3\Gamma(1/2+s)},
\]
\[
 M_2(s)=\frac{\Gamma(s)^2\Gamma(1/2-s)^2}
               {\Gamma(1-s)^2\Gamma(1/2+s)^2}.
\]
Gamma reflection [3] gives
\[
 M_1=R\tan^3(\pi s),\qquad M_2=R\tan^2(\pi s).             \tag{5}
\]
On this line |tan(pi s)|=1 and R(s)=O((1+|Im s|)^(-2)), so the Barnes
integrals are absolutely convergent at argument 1.

### 2.1 The U4 normalization

Closing the first kernel on the left at 0<x<1, its simple-pole residue at s=-n
is
\[
 \frac{(-1)^n}{n!}\,
 \frac{\Gamma(n+1/2)^3}{\Gamma(n+1)^3\Gamma(1/2-n)}
 =\pi\left[\frac{(1/2)_n}{n!}\right]^4.
\]
Letting x approach 1 is justified both by the integrable Barnes majorant and
by the summable n^-2 residue bound. This proves g13=pi U4.

### 2.2 The U6 normalization

Use the Bailey-Mishev 7F6 and Barnes representations [4] at
(a,b,c,d;e;f,g)=(1/2,1/2,1/2,1/2;1;1,1). They give the same completed function as
\[
 L_0=\frac{U_6}{2\pi}
 =\frac1{\pi^5}\frac1{2\pi i}\int K(s)\,ds,
\]
where
\[
 K(s)=\frac{\Gamma(s)^2\Gamma(1/2-s)^4}{\Gamma(1-s)^2}.
\]
These specializations can also be read from equations (2.9)-(2.10) of [5].
They have no singular parameter derivative in this use of the Barnes form.

Put
\[
 M_0(s)=\frac{\Gamma(1/2-s)^4}{\Gamma(1-s)^4}.
\]
Reflection and 1+tan^2=sec^2 give
\[
 K(s)=\pi^2\{M_2(s)+M_0(s)\}.                             \tag{6}
\]
The integral of M0 on the specified contour is ZERO. It is important to justify
this boundary value rather than simply omit the kernel. Changing variables
s to 1/2-s identifies that integral with the inverse Mellin integral of R(s)
at x=1. Equivalently R(s) is the Laplace transform of the fourfold additive
convolution of
\[
 b(t)=\frac1{\sqrt\pi\sqrt{1-e^{-t}}},\qquad t>0.
\]
Indeed the beta integral [6] gives its Laplace transform as
Gamma(s)/Gamma(s+1/2). Near t=0,
b(t)=t^(-1/2)/sqrt(pi)*(1+O(t)), so its fourfold convolution is
`t*(1+O(t))`, and its value at zero is zero. Fourier/Laplace inversion is valid
here because R(1/4+i u) is integrable. Thus the M0 contour contributes zero.

It follows from (6) that
\[
 \frac{\pi^4}{2}U_6=\pi^2g_{22},
\]
proving the second identity in (2). This is an application of the classical
Bailey-Mishev representation, not a claimed first discovery of that representation.

A useful independent real form for numerical checking is
\[
 g_{22}=\frac1\pi\int_0^\infty
 \left|\frac{\Gamma(1/4+it)}{\Gamma(3/4+it)}\right|^4dt.
\]
It is a PROOF/CHECK representation, not part of the finite expression (2).

## 3. One-call encoding of the lower block

The exact gamma kernel of g_alpha is
\[
 N_\alpha(s)=
 \frac{\Gamma(s)^2\Gamma(1/2-s)^3}
 {\Gamma(1-s)^2\Gamma(1/2+s)
  \Gamma(s+\alpha)\Gamma(1-s-\alpha)}.                     \tag{7}
\]
Gamma reflection gives
\[
 N_\alpha(s)=M_2(s)\frac{\sin\pi(s+\alpha)}{\cos\pi s}.
\]
Therefore sine addition and (5) imply the kernel identity
\[
 N_\alpha=\cos(\pi\alpha)M_1+\sin(\pi\alpha)M_2.
\]
All three kernels are absolutely integrable on the common contour; hence
\[
 g_\alpha=\frac X\rho g_{13}+\frac Y\rho g_{22}.
\]
Equation (4) follows immediately from (3).

This packing step does not reduce the arithmetic dimension of the two periods.
Its benefits are one fewer special-function call and a maximum Meijer-G order
five instead of the preceding 7F6 order seven. Its cost is a real nonrational
parameter containing A,Q. Equation (3) is preferable when simple rational
parameters matter more than one fewer call. Neither form is claimed to be faster
or numerically more stable in an actual Mathematica kernel.

### Fixing the inverse-tangent branch without sampled signs

The elementary inequalities pi>3 and log(2)>1/2 give A>5. Also
\[
 \Gamma(1/4)
 <\int_0^1t^{-3/4}(1-t+t^2/2)dt+\int_1^\infty e^{-t}dt
 <4-\frac45+\frac29+\frac25<4.
\]
Thus Q<256/3. These bounds imply
\[
 C_s<5120-\frac{105}{4}25-135-\frac{2469}{4}9=-\frac{2453}{2},
\]
\[
 C_d<8192-42\cdot25-270-1227\cdot9=-4171.
\]
Hence X,Y>0, proving the stated alpha branch.

## 4. Effect on the complete coefficient

Only the two records U4,U6 in the accepted ordinary-function block are replaced.
The unchanged known polynomial has eighteen expanded monomials. Its source
correction remains included once. The Pb Meijer pair, the eighth-power Meijer
value, all five ordinary seventh-power values and both polylogarithmic values
are retained without coefficient changes.

The finite count, excluding the initial constants pi, log(2), Gamma(1/4),
Catalan and zeta values, changes as follows when the rational Pb pair is used:

| Type | Input | New packed form |
|---|---:|---:|
| Ordinary hypergeometric values | 7 | 5 |
| Ordinary Meijer-G values | 3 | 4 |
| Polylogarithmic values | 2 | 2 |
| Total finite special values | 12 | 11 |
| Unresolved elliptic blocks | 3 | 3 |

The unchanged wheel has the exact original n>=1 definition
`sum a_n^4 [8+5*pi*(4n+1)*a_n^2] delta_n`. The Dougall companion evaluates a
different, extra-weighted fourth-power moment and is not substituted for it.
The current wheel, seventh logarithmic sector and Pa therefore still prevent a
justified full integration- and infinite-sum-free expression in fixed ordinary
Mathematica special values. This pass does not assert that their reduction is
impossible.

`C6LowerFinitePartR6[]` in the Wolfram file returns the FINITE PART ONLY. It does
not divide by 2187 or silently treat the omitted blocks as zero.
`C6LowerReductionStatus[]` lists them explicitly. The updated JSON retains the
unresolved formulas and marks full completion as false.

## 5. Executed checks

The two ordinary hypergeometric values were evaluated independently of the
Barnes integrals. The packed value was integrated from its own gamma kernel (7),
not generated by inserting the old lower block as its value. At 80 decimal
working digits:

```
U4 = 1.1186363871641870683496192575256409167948575515293611914806186469240462896637041
U6 = 1.1493897240844601023893837503075790452446086911879363368497664407729896067029155
g22 = 5.6720109396954355002489582639189178306468844804866440480429353553260969251748832
alpha = 0.13436220716359474627530186859083131546501693810567757075254138225150240062155545
rho = 9464.0558190277677214055474742327848472906444211383826518165150590030340113912893
g_alpha = 5.5295869072119298589144352551633701511210963315326053430312142861961988791741401
B_lower = -2065997.1494510410791101366134125448706591495801397566766904891020090257458246603
```

The observed absolute discrepancies are 2.1084396e-81 for U6 and 4.4217183e-75
for the complete lower block. A separate 40-digit calculation is also recorded.
These are floating-point cross-checks, not rigorous enclosures and not 80-digit
accuracy certificates. No full C6 reassembly was performed.

`build_verify.py` passes 47 finite algebra/preservation/static checks. The
Barnes inversion and convergence arguments remain analytic proofs in this note,
not claims that a finite test suite alone proves infinite identities.
The Wolfram file was checked statically but was NOT run in a Wolfram kernel.

## Reproduction

Python 3, SymPy and mpmath suffice for the executed calculations:

```text
python build_verify.py
python numerical.py
```

In Mathematica:

```wolfram
Get["C6_lower_MeijerG_patch.wl"];
C6U6Meijer[]
C6LowerBlockSingle[]
C6LowerBlockRational[]
C6LowerNumericalCheck[40]
C6LowerReductionStatus[]
```

## References and input provenance

[1] Wolfram Language, MeijerG: parameter-group convention and the actual built-in.
https://reference.wolfram.com/language/ref/MeijerG.html

[2] NIST DLMF 16.17: Mellin-Barnes definition of the ordinary Meijer G.
https://dlmf.nist.gov/16.17

[3] NIST DLMF 5.5: gamma reflection identities.
https://dlmf.nist.gov/5.5

[4] I. D. Mishev, Coxeter group actions on Saalschuetzian 4F3(1) series and
very-well-poised 7F6(1) series, arXiv:1008.1011, completed-L Barnes and
very-well-poised representations.
https://arxiv.org/html/1008.1011

[5] D. Bao, Coxeter Symmetry in Hypergeometric Functions and Elliptic Integral
Moments, arXiv:2609.34016v1, equations (2.9)-(2.10), displaying the two
representations used at the symmetric point.
https://arxiv.org/html/2609.34016v1

[6] NIST DLMF 5.12: Euler beta integral used for the boundary argument.
https://dlmf.nist.gov/5.12

Input: C6_eighth_MeijerG_expression.json, copied byte-for-byte under inputs.
The original coefficients Cs,Cd,U4,U6 and all physical identifications are
inherited. The transformed expression records the input SHA-256. The latest
Dougall companion remains a separate, unchanged diagnostic.
