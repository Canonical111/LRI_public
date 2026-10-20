# Exact seed relations for the C6 primitive's Meijer-G coefficients

## Result and scope

The inherited primitive has

\[
P_a=8\pi^3\left[\Phi_0+2\sum_{n\ge1}(-1)^n\Phi_n\right],
\quad
\Phi_n=10G_{1,n}^2+21G_{1,n}G_{2,n}+18G_{2,n}^2+15G_{2,n}G_{3,n}.
\]

This note proves a contiguous seed difference and derives a constant discrete determinant from the previously established first-moment identity. The recurrence can consequently be initialized using three fixed Meijer-G values instead of its six listed seeds. It does **not** evaluate the unweighted infinite product sum, change the accepted C6 polynomial, remove a residual, or prove arithmetic independence. No new physical graph/RG identification or interval certificate is claimed. The determinant relation is equivalent, through the inherited Fourier transform, to an earlier first-moment evaluation; it is not a new independent primitive-period constraint.

## 1. Coefficient convention

The functions are ordinary univariate Meijer G values in the Wolfram/NIST convention [1,2]:

```wolfram
G1[n_] := MeijerG[{{1/2,1/2,1/2},{1/2}},{{n},{0,0,-n}},1];
G2[n_] := MeijerG[{{1/2,1/2},{1/2,1/2}},{{0,n},{0,-n}},1];
G3[n_] := MeijerG[{{1/2},{1/2,1/2,1/2}},{{0,0,n},{-n}},1];
```

All n below are nonnegative integers. Their inverse-Mellin kernels, with upward contour Re(s)=1/4, are

\[
A_{j,n}(s)=
\frac{\Gamma(s)^{j-1}\Gamma(s+n)\Gamma(1/2-s)^{4-j}}
{\Gamma(1-s)^{3-j}\Gamma(1/2+s)^j\Gamma(n+1-s)}.
\]

At n=0, contour reflection gives G_(3,0)=G_(1,0). The inherited recurrence is

\[
(2n+1)^3G_{j,n+1}-4n(4n^2+1)G_{j,n}+(2n-1)^3G_{j,n-1}
=32(j-2)n(-1)^n/\pi,\quad n\ge1. \tag{1}
\]

This recurrence and the coefficient/primitive identification are input results, not re-proved here. They are recorded in `C6_primitive_Chebyshev_derivation.md`.

## 2. An elementary contiguous difference

The new seed identity is

\[
\boxed{G_{3,1}-G_{1,1}=8/\pi.} \tag{2}
\]

Put

\[
K(s)=\frac{\Gamma(s)\Gamma(1/2-s)^3}{\Gamma(1-s)^3\Gamma(1/2+s)},
\qquad r(s)=\frac{s}{1-s}.
\]

The kernel of G_(1,1) is K(s)r(s). Reflecting the G_(3,1) contour by s -> 1/2-s gives K(s)r(1/2-s), so their difference has kernel

\[
K(s)d(s),\qquad
 d(s)=\frac{4s-1}{(s-1)(2s+1)}.
\]

Gamma recurrence [3] supplies K(s+1)/K(s)=s^4/(s+1/2)^4. For the rational function

\[
q(s)=-\frac{(2s-1)^3}{s-1},
\]

one checks identically that

\[
\boxed{K(s)d(s)=K(s+1)q(s+1)-K(s)q(s).} \tag{3}
\]

This is an exact rational certificate after division by K(s), not an integer relation on numerical values.

### The finite contour boundary does not vanish

Let T>0, integrate (3) upward from 1/4-iT to 1/4+iT, and compare the two vertical sides of the rectangle with real parts 1/4 and 5/4. The function K(s)q(s) has no poles in this strip. Its apparent singularity at 1/2 is removed by the triple zero of q; at 1 the triple zero of K cancels the simple pole of q.

Reflection and gamma-ratio asymptotics [3,4] give, uniformly across this finite-width strip,

\[
K(s)=\left[\frac{\Gamma(s)}{\Gamma(s+1/2)}\right]^4\tan^3(\pi s),
\qquad q(s)\sim-8s^2,
\]

and hence

\[
q(s)K(s)\longrightarrow
\begin{cases}8i,&\Im s\to+\infty,\\-8i,&\Im s\to-\infty.\end{cases}
\]

With counterclockwise orientation, the bottom horizontal segment is directed right and the top segment left. Each contributes -8i in the limit. Thus the upward right vertical integral minus the upward left one tends to 16i. Dividing by 2pi i proves (2).

The original difference K(s)d(s) is absolutely integrable: it is O(|Im s|^-3). The two modified vertical integrals of Kq need not exist separately as infinite integrals; the argument keeps their finite-height difference until the limit. Dropping the horizontal boundary would incorrectly produce zero instead of 8/pi.

## 3. A constant determinant

Set

\[
V_n=G_{2,n},\qquad U_n=G_{1,n}+G_{3,n}.
\]

Both solve the homogeneous version of (1). Elementary substitution therefore shows that

\[
C_n=(2n+1)^3(V_nU_{n+1}-V_{n+1}U_n)
\]

is independent of n. Its exact normalization is

\[
\boxed{C_n=16/\pi,\qquad n\ge0.} \tag{4}
\]

### Fixing the normalization from an inherited moment

For clarity, write

\[
v(x)={}_2F_1(1/4,1/4;1;x),\quad
h(x)={}_2F_1(1/4,1/4;1/2;x),\quad Q=\Gamma(1/4)^4/\pi,
\]

\[
q_0=v^2,\quad q_1=(\sqrt Q/\pi)v(x)h(1-x),\quad
q_2=(Q/\pi^2)h(1-x)^2.
\]

The source `C6_primitive_first_moments_derivation.md` establishes

\[
J_{12}-J_{02}=\pi,\qquad
J_{ij}=\int_0^1\frac{(2x-1)q_i(x)q_j(1-x)}{\sqrt{x(1-x)}}\,dx.
\]

The underlying functions with coefficient sequences U,V are

\[
U(x)=\sqrt\pi(q_0-q_1+q_2/2),\qquad
V(x)=\sqrt\pi(q_1-q_0).
\]

Their first moment is consequently

\[
\int_0^1\frac{(2x-1)V(x)U(1-x)}{\sqrt{x(1-x)}}dx
=\frac\pi2(J_{12}-J_{02})=\frac{\pi^2}{2}. \tag{5}
\]

The inherited cosine coefficients are normalized by

\[
\int_0^\pi V((1-\cos\theta)/2)\cos(n\theta)d\theta=\sqrt\pi V_n,
\]

and analogously for U. Multiplication by 2x-1=-cos(theta), reflection, and cosine orthogonality turn (5) into

\[
\sum_{n\ge0}(-1)^n(V_nU_{n+1}-V_{n+1}U_n)
=C\sum_{n\ge0}\frac{(-1)^n}{(2n+1)^3}=C\frac{\pi^3}{32}.
\]

The familiar beta(3)=pi^3/32 follows, for example, by twice integrating the sine series for the constant function on (0,pi). All adjacent-coefficient products are absolutely summable by Cauchy-Schwarz and the source square-integrability result, so this Fourier manipulation is justified. Equating with pi^2/2 proves (4).

This argument identifies the determinant with an already evaluated *weighted* moment. It does not evaluate the unweighted primitive norm.

## 4. Three fixed seeds suffice

Let

\[
X=G_{1,0},\qquad Y=G_{2,0},\qquad Z=G_{2,1}.
\]

Here Y>0 from its positive elliptic coefficient integral. Equations (2),(4) and G_(3,0)=G_(1,0) give

\[
\boxed{
G_{1,1}=\frac{XZ+8/\pi}{Y}-\frac4\pi,
\qquad
G_{3,1}=\frac{XZ+8/\pi}{Y}+\frac4\pi,
\qquad G_{3,0}=X.
} \tag{6}
\]

An equivalent finite bilinear relation is

\[
\boxed{(\pi G_{1,1}+4)G_{2,0}-\pi G_{1,0}G_{2,1}=8.}
\]

X and Y are the existing lower-period values pi*U4 and pi^2*U6/2; only Z is an extra seed call. Reducing seed calls does not establish that the sum over all coefficients is an algebraic function of those calls.

## 5. Optional rational difference sequence

Define for evaluation only r_n=pi(G_(3,n)-G_(1,n)). Subtraction of (1) yields

\[
(2n+1)^3r_{n+1}-4n(4n^2+1)r_n+(2n-1)^3r_{n-1}
=64n(-1)^n,\quad r_0=0,\quad r_1=8.
\]

Thus every r_n is rational; the first values are

\[
0,\quad8,\quad32/9,\quad712/225,\quad24704/11025,\quad204296/99225.
\]

The primitive coefficient may be evaluated as

\[
\Phi_n=10G_{1,n}^2+36G_{1,n}G_{2,n}+18G_{2,n}^2
+(15/\pi)r_nG_{2,n}.
\]

This avoids a third Meijer-G coefficient family in numerical generation. It is optional recurrence machinery, not a proposed closed form for the remaining infinite sum.

## 6. Executed checks

`verify.py` executes 16 exact finite algebra checks, including (3), recurrence invariance of C_n, seed substitutions, and the first rational difference values. These checks accompany but do not replace the analytic boundary argument.

`numerical.py` freshly evaluates the coefficient functions by their inherited real elliptic/Chebyshev projection, independently of the recurrence and new seed relations. At 90 decimal working digits it evaluates U_n,V_n,G_(1,n) at n=0,1,2,3. The largest determinant residual at n=0,1,2 is less than 2.946e-90. The direct seed-difference residual rounds to zero at that working precision; the reduced G_(1,1) formula differs by about 9.205e-92.

These are floating-point cross-checks, not interval certificates. No full C6 evaluation, direct Wolfram-kernel execution, or upstream physical re-verification was performed.

## 7. Reproduce

```
python verify.py
python numerical.py 90
```

The Wolfram file contains finite MeijerG definitions, reduced seeds, rational difference recurrence, and optional finite numerical checks. It does not supply a value for the full primitive or silently set a residual to zero.

## Sources

Inherited project inputs:
- C6_primitive_Chebyshev_derivation.md: coefficient normalization, primitive expression, recurrence and square-integrability.
- C6_primitive_first_moments_derivation.md: J12-J02=pi with the displayed normalized q_i.
- C6_current_self_contained.md: accepted C6 expression, unchanged.

External standard identities (not sources of a claimed Ising closed form):
1. NIST DLMF 16.17, Meijer G definition: https://dlmf.nist.gov/16.17
2. Wolfram Language MeijerG documentation: https://reference.wolfram.com/language/ref/MeijerG.html
3. NIST DLMF 5.5, gamma recurrence and reflection: https://dlmf.nist.gov/5.5
4. NIST DLMF 5.11, gamma-ratio asymptotics: https://dlmf.nist.gov/5.11
