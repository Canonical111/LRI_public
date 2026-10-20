from pathlib import Path
ROOT=Path(__file__).resolve().parent
old=(ROOT/'inputs/C6_compact_H_formula.md').read_text()
start=old.index('## 1. Complete coefficient')
text='# C6(1): finite representation with 17 fixed special-function values\n\n'
text+='## Scope\n\nThis is the full current finite representation in the admitted multivariate class. The two wheel Kampé de Fériet values have been replaced by one unit-slope bivariate Fox H value. The previous single-H primitive and all other blocks are retained. The full function count is 17 rather than 18. No explicit residual infinite sum, integral, parameter derivative or limit is present. This is representation compression, not an elementary evaluation or arithmetic-independence theorem. Physical graph/RG identification remains inherited.\n\n'
text+=old[start:]
text=text.replace('-9432\\pi^3\\mathfrak F_4-5895\\pi^4\\mathfrak F_6','-393\\pi\\sqrt{89}\\,\\mathcal H_W',1)
i=text.index('## 3. The wheel:'); j=text.index('## 4. The seventh sector:')
new=r'''## 3. The wheel: one fixed bivariate H value

Put
\[
\alpha_W=\frac1\pi\arctan\frac58.
\]
All slopes in the following standard bivariate Fox H value are one:
\[
\boxed{\mathcal H_W=
H_{2,2;\,5,5;\,2,2}^{0,2;\,2,3;\,2,2}
\left[
\begin{matrix}
(\frac12;1,1)^{[2]}:
 (\frac12,1)^{[4]},(\alpha_W,1);
 (\frac12,1),(0,1)\\
(-\frac12;1,1)^{[2]}:
 (0,1)^{[4]},(\alpha_W,1);
 (0,1),(\frac12,1)
\end{matrix}\;\middle|\;1,1\right].}
\tag{7}
\]
The standard convention is Andrade–Rathie–Farias Definition B. The numerator indices are shared n=2; s-local m=2,n=3; t-local m=2,n=2. Ordered repeated alphaW parameters belong to denominator groups and do not cancel.

For exact normalization, set
\[
N_{\alpha}(s)=\frac{\Gamma(s)^2\Gamma(\frac12-s)^3}
{\Gamma(1-s)^2\Gamma(\frac12+s)\Gamma(s+\alpha)\Gamma(1-s-\alpha)},
\]
\[
P(t)=\Gamma(t)\Gamma(t+\tfrac12)\Gamma(\tfrac12-t)\Gamma(1-t).
\]
The inverse-Mellin kernel is
\[
\boxed{\frac{N_{\alpha_W}(s)P(t)}{(\frac12-s-t)^2},}
\tag{8}
\]
with upward contours Re(s)=1/4, Re(t)=1/8 and standard measure ds dt/(2 pi i)^2. This fixes the named-function parameters; it is not an extra integral in the master expression.

The entire zero-included wheel is
\[
\boxed{W_0=\frac{\sqrt{89}}{\pi^2}\mathcal H_W,\qquad
-393\pi^3 W_0=-393\pi\sqrt{89}\mathcal H_W.}
\tag{9}
\]
For the original n>=1 notation, Wcentral=W0-(8+5*pi)*pi**2/3. The master formula uses W0; no additional zero-index compensation or source correction is to be added.

Numerically, H_W = 82.198372839948704474444779671977025125648737334356408964906750... . The optional interval file propagates the previously proved rational wheel enclosure. See DERIVATION.md for the inherited global identity and new kernel conversion.

'''
text=text[:i]+new+text[j:]
i=text.index('## 6. Verification and limits')
text=text[:i]+r'''## 6. Verification and limits

`build_verify.py` passes 36 finite checks of the new parameter lists, gamma kernel, coefficient weights, full-formula substitution, counts, and preservation of the polynomial, primitive, seventh sector and source correction. The global fourth/sixth wheel identity is explicitly inherited, as explained in DERIVATION.md.

Independent new-kernel calculations at 35 and 65 working digits agree with the old wheel component interval midpoints. At 65 digits the discrepancy in W0 is below 1.520e-64. The analytically evaluated inner Barnes transform was separately checked by direct contour quadrature at three complex s-points. These are floating-point implementation checks, not new rigorous Barnes quadrature certificates.

`propagate_interval.py` transfers the accepted rational wheel enclosure to H_W with exact rational arithmetic and a bracket for sqrt(89). Its width is less than 2.221e-146. The certificate is labelled propagated; no new independent verification of the physical coefficient or all-sector numerical reassembly is claimed.

The previously recorded value of the inherited analytic representation remains
\[
C_6^{\rm rep}(1)=14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]

| Standard function class | Fixed values |
|---|---:|
| Multiple polylogarithms | 2 |
| Ordinary generalized hypergeometric | 5 |
| Ordinary univariate Meijer G | 3 |
| Kampé de Fériet | 5 |
| Bivariate Fox H | 2 |
| **Total** | **17** |
| Explicit residual infinite sums or integrals | 0 |

This is a representation count, not minimality or transcendence degree. The five seventh-sector Kampé de Fériet values are unchanged. The wheel and primitive each use one bivariate H value with a different parameter list.

## Appendix A. Standard conventions

For Kampé de Fériet
\[
F_{q:s;u}^{p:r;t}\!\left[
\begin{matrix}\boldsymbol a:\boldsymbol b;\boldsymbol c\\
\boldsymbol d:\boldsymbol e;\boldsymbol f\end{matrix};x,y\right],
\]
the coefficient of x^m y^n in its standard defining expansion is
\[
\frac{(\boldsymbol a)_{m+n}(\boldsymbol b)_m(\boldsymbol c)_n}
{(\boldsymbol d)_{m+n}(\boldsymbol e)_m(\boldsymbol f)_n\,m!n!}.
\]
List Pochhammer symbols mean products over their lists. This specifies all five J_r in section 4. Those values converge absolutely at (-1,-1); their absolute total-index diagonal is O(log(k+2)/(k+1)^(5/2)).

For the bivariate H function, shared upper numerator triples (e;E,F) produce Gamma(1-e-E*s-F*t); shared lower denominator triples (f;A,B) produce Gamma(1-f-A*s-B*t) in the denominator. A local upper numerator pair (a,A) gives Gamma(1-a-A*s), while an upper denominator pair gives Gamma(a+A*s) in the denominator. A local lower numerator pair (b,B) gives Gamma(b+B*s), while a lower denominator pair gives Gamma(1-b-B*s) in the denominator. The second local variable obeys the same convention. Both H kernels are explicitly specified above.

## Sources and reproduction

The input `C6_compact_H_expression.json` supplies the accepted complete coefficient. The input curvature derivation makes the inherited wheel contour identity explicit. The input `C6_central_binomial_wheel_intervals.json` supplies the previously proved rational numerical enclosure; it is not used to choose any formula coefficient.

The newly derived wheel identity and all assumptions are detailed in DERIVATION.md. Standard definitions and identities are from NIST DLMF 5.5, 5.11, 5.12, 5.15 and 16.17; Andrade–Rathie–Farias, *Exact Bayesian computation using H-functions* (2018), Definition B; and the classical complex-variable definition in the introduction of Ito–Kumabe–Nakagawa–Nemoto, arXiv:2212.14321v2. No general special-function reference is cited as an independent Ising graph calculation.

Run:
```
python build_verify.py
python numerical.py 35 --inner
python numerical.py 65 --inner
python propagate_interval.py
```
'''
assert 'mathfrak F_4' not in text
assert 'mathfrak F_6' not in text
(ROOT/'FORMULA.md').write_text(text)
print('Wrote complete formula',len(text),'characters')
