from pathlib import Path
import re
BASE=Path(__file__).resolve().parent
old=(BASE/'inputs/previous_formula.md').read_text()
t=old.replace('# C6(1): a finite multivariate-special-function expression','# C6(1): compressed finite representation with 18 fixed special values',1)
scope=r'''## Scope

This is the complete current formula in the admitted multivariate special-function class. The primitive has one fixed bivariate Fox H value instead of four. The earlier optional sixth-sector combination is also packed into one ordinary Meijer G value instead of two. Total fixed-value count: 18 instead of 22.

This is an exact representation compression, not an elementary summation or an arithmetic-independence result. Primitive parameter complexity increases: four half-integer-parameter H values become one higher-order H with four explicit complex-conjugate parameters obtained from a fixed cubic algebraic number. There is still no explicit residual infinite sum, integral, parameter derivative, or limit in the active formula.

The known polynomial, wheel normalization, seventh-sector coefficients, and repaired source contribution are unchanged. The previously proved primitive contour identity is an inherited input. See DERIVATION.md for the new algebraic factorization and exact verification. No new full-C6 evaluation or interval certificate is claimed.

'''
t=t[:t.index('## Scope')]+scope+t[t.index('## 1. Complete coefficient'):]
t=t.replace(r'&+768\pi^3\left(10\mathfrak H_{11}+21\mathfrak H_{12}'+'\n'+r'+18\mathfrak H_{22}+15\mathfrak H_{23}\right).',r'&+7680\pi^3\mathcal H_*.')
start=t.index('The sixth-power block is');end=t.index('For the eighth-power block set',start)
t=t[:start]+r'''For the sixth-power block put
\[
\alpha_6=\frac{1}{\pi}\arctan\frac{11}{13},\qquad
\mathcal G_6=G_{7,7}^{4,5}\!\left(1\;\middle|\;
\begin{matrix}(1/2)^{[6]},\alpha_6\\0^{[6]},\alpha_6\end{matrix}\right).
\]
Then
\[
\boxed{B_6=192\pi\sqrt{290}\,\mathcal G_6=24P_b.}
\tag{5}
\]
This reuses the earlier identity sqrt(290) G6 = 13 X35 + 11 X44. Its exact Wolfram splits are

```wolfram
MeijerG[{{1/2,1/2,1/2,1/2,1/2},{1/2,alpha6}},
        {{0,0,0,0},{0,0,alpha6}},1]
```

'''+t[end:]
start=t.index('## 5. The primitive:');end=t.index('## 6. What was checked',start)
newprim=r'''## 5. The primitive: one bivariate Fox H value

Let lambda be the unique real root in (15,16) of
\[
4\lambda^3-112\lambda^2+909\lambda-2250=0.
\]
Equivalently,
\[
\lambda=\frac{28+\sqrt{409}\cos\!\left(\frac13\arccos\frac{7298}{409\sqrt{409}}\right)}3.
\]
Put
\[
e=\frac{\sqrt{40\lambda-279}}{20},\qquad
\chi=\frac{2(21\lambda-150)}{40\lambda-279},
\]
\[
B_\sigma=\frac{21}{20}+\sigma e,\qquad
C_\sigma=\frac\lambda{10}+\sigma e\chi,
\qquad \sigma\in\{+1,-1\},
\]
\[
\beta_\sigma=\frac1\pi\arctan\left(\frac{B_\sigma}{2}
+i\sqrt{C_\sigma-B_\sigma^2/4}\right).
\]
The real square roots are positive and the complex inverse tangent is principal. Both square-root radicands are positive. Conjugation supplies the second member of each pair. These parameters contain no unknown period.

Define the ordered parameter/slope lists
\[
\mathbf a_\sigma=((1/2,1)^{[4]},(\beta_\sigma,1),(\bar\beta_\sigma,1)),
\]
\[
\mathbf b_\sigma=((0,1)^{[3]},(\beta_\sigma,1),(\bar\beta_\sigma,1)).
\]
In the Andrade-Rathie-Farias bivariate H convention, set
\[
\boxed{\mathcal H_*=H_{0,1;6,5;6,5}^{0,0;3,3;3,3}
\!\left[\begin{matrix}-:\mathbf a_+;\mathbf a_-\\
(0;1,1):\mathbf b_+;\mathbf b_-\end{matrix}\;\middle|\;1,1\right].}
\tag{13}
\]
The first three upper and first three lower entries in each local group are numerator gamma groups. All slopes are one. This is a bivariate function, not Mathematica's univariate FoxH or MeijerG interface.

To fix the normalization without any ambiguity, define the gamma factor
\[
\Psi_\sigma(s)=\frac{\Gamma(s)^3\Gamma(1/2-s)^3}
{\Gamma(1/2+s)\Gamma(s+\beta_\sigma)\Gamma(1-s-\beta_\sigma)
\Gamma(s+\bar\beta_\sigma)\Gamma(1-s-\bar\beta_\sigma)}.
\]
The standard inverse-Mellin kernel is Psi_+(s) Psi_-(t)/Gamma(1-s-t), with upward lines Re(s)=Re(t)=1/4 and the standard measure ds dt/(2 pi i)^2. This is the named function's parameter specification; it is not an extra integration operation in the master coefficient.

The complete primitive is
\[
\boxed{P_a=80\pi^3\mathcal H_*,\qquad S_P=10\mathcal H_*,
\qquad \mathscr P_c^{(3)}=40\pi\mathcal H_*.}
\tag{14}
\]
Consequently
\[
\boxed{96P_a=7680\pi^3\mathcal H_*.}
\tag{15}
\]
There is no added polynomial or zero-index compensation. Numerically, from the proved beta-product representation,
\[
\mathcal H_*=135.0234860111609249908488197821688196879586538126766890134710495752391\ldots.
\]
This numerical check is not an interval certificate.

'''
t=t[:start]+newprim+t[end:]
start=t.index('## 6. What was checked');end=t.index('## Appendix A.',start)
t=t[:start]+r'''## 6. Verification and limits

`build_verify.py` checks the primitive coefficient-matrix determinant, its exact factorization modulo the cubic polynomial, the normalization identity, the standard-function parameter groups, the entire C6 substitution, and preservation of the full known polynomial and source correction. It passes 39 finite checks. DERIVATION.md specifies precisely which global identity is inherited.

`numerical.py --dps 40 --meijer` and the same run at 70 digits check the new local gamma kernels, direct univariate Meijer G values, and the primitive's factored beta pairing against a separate original quartic-kernel quadrature. There are six successful direct univariate G checks in each run. No independent two-dimensional Mellin-Barnes quadrature or new rigorous interval was computed. No full-C6 numerical reassembly was run.

The previously recorded value of the inherited analytic expression remains
\[
C_6^{\rm rep}(1)=14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]

| Standard function class | Fixed values |
|---|---:|
| Multiple polylogarithms | 2 |
| Ordinary generalized hypergeometric | 5 |
| Ordinary univariate Meijer G | 3 |
| Kampe de Feriet | 7 |
| Bivariate Fox H | 1 |
| Total | 18 |
| Explicit residual infinite sums or integrals | 0 |

This is an occurrence count, not a minimality or transcendence-degree claim. The tradeoff is fewer values with more complicated primitive parameters. The source's lower-order, rational-parameter alternatives remain in the input file.

'''+t[end:]
# Replace obsolete primitive-summary sentence; no bivariate old values remain active.
t=t.replace('The four bivariate H kernels converge absolutely on the stated contours.','The single new bivariate H kernel converges absolutely on the stated contours, as shown by the factored local-kernel bound in DERIVATION.md.')
t=t.replace('The primitive identification follows by beta pairing the inherited Meijer G_(3,3) basis: the beta quotient adds Gamma(1/2-s)Gamma(1/2-t)/Gamma(1-s-t) to the product of its two Mellin kernels.', 'The primitive compression combines the inherited beta pairing and its contour relation with an exact rank-two factorization. The gamma reflection factors convert its two local quadratics into single G_(5,5) kernels; beta integration then gives the displayed H_* parameters.')
# Keep the source list but add the current proof's provenance.
t+='\nNew derivation and reproduction: `DERIVATION.md`, `build_verify.py`, and `numerical.py`. The input expression and prior primitive/sixth-sector derivations are preserved under `inputs/`.\n'
assert r'7680\pi^3\mathcal H_*' in t
assert 'Total | 22' not in t
(BASE/'FORMULA.md').write_text(t)
