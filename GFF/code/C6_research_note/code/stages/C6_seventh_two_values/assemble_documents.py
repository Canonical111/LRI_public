from pathlib import Path
import json, shutil, zipfile
B=Path(__file__).resolve().parent
old=(B/'inputs/previous_formula.md').read_text()
der=(B/'DERIVATION.md').read_text()
unchanged=old[old.index('### Complete known polynomial'):old.index('## 4. Seventh-sector parameter reduction')]
primitive=old[old.index('## 5. The primitive:'):old.index('## 6. Verification and counts')]
newsection=der[der.index('## 1. The two-value answer'):der.index('## 2. Match the complete central coefficient')]
newsection=newsection.replace('## 1. The two-value answer','## 4. The seventh sector: one Meijer G and one bivariate H')
header=r'''# C6(1): a finite nine-value representation

## Scope

This is an exact finite reformulation of the retained analytic C6 coefficient.
The complete seventh sector now uses two fixed values, not five. Its former
Kampé de Fériet calls and cubic/quartic root sets are absent. Four explicit
nonrational shifts, determined using square roots and inverse tangents, suffice.
All other sectors and the complete known polynomial are copied from the accepted
input. The physical graph/RG identification remains inherited.

The new bivariate H has a shared slope pair (2,1), and argument (1,-1), with
Log(-1)=i*pi. Unlike the old wheel and primitive values it is not restricted to
unit slopes. It is absolutely convergent on the contours specified in Section 4.
No integral, infinite sum, parameter derivative, or limiting operation remains
to be applied in the coefficient itself. The standard-function kernel
specifications below fix conventions; they are not extra remainder blocks.
This is not an elementary evaluation or an arithmetic-independence theorem.

## 1. Complete coefficient

Put
\[
\ell=\log2,\qquad A=\pi+4\ell,\qquad
Q=\frac{\Gamma(1/4)^4}{\pi},\qquad G=\operatorname{Catalan}.
\]
Then
\[
\boxed{\begin{aligned}
2187C_6(1)={}&E+B_{\rm pol}+B_{\rm low}+B_6+B_8
-393\pi\sqrt{89}\,\mathcal H_W\\
&+24\pi^{3/2}\bigl[\rho_7\mathcal G_7
+392\sqrt{185}\,\mathcal H_7\bigr]
+7680\pi^3\mathcal H_*.
\end{aligned}}
\]
All symbols are specified below. There is no polynomial compensation:
Delta E=0. The source correction and all included zero-index terms remain
included exactly once.

'''
footer=r'''
## 6. Numerical checks and representation size

At 80 working decimal digits,
\[
\mathcal G_7=8.38817429186383748625482510888136818661142660132305\ldots,
\]
\[
\mathcal H_7=-20.35920964993894539299593231407576888649928855816310\ldots,
\]
\[
B_7=-11409730.02189293040856018259030951811363354779663423\ldots.
\]
The new expression was checked against a fresh central-series Euler evaluation
and a fresh original five-shift evaluation. Discrepancies were below 1.239e-73
and 3.007e-73, respectively. These are floating-point cross-checks, not new
interval certificates. The H value was evaluated via its own outer gamma kernel
with an analytically evaluated inner Barnes transform; that inner identity was
also checked separately by direct contour quadrature. No new all-sector C6 or
physical graph/RG verification is claimed. The previously recorded complete
analytic coefficient remains approximately
14331.6870327580543204454632552462171183173230619887904582031423.

| Fixed value class | Count |
|---|---:|
| Multiple polylogarithms | 2 |
| Univariate Meijer G | 4 |
| Bivariate Fox H | 3 |
| Kampé de Fériet | 0 |
| Total | 9 |
| Explicit residual infinite sums or integrals | 0 |

The known polynomial has eighteen expanded monomials. The ninth-value count
excludes elementary constants and gamma/zeta prefactors; it does not measure
arithmetic independence.

## Standard conventions and reproduction

In G_(p,q)^(m,n), the first n upper and first m lower entries are numerator
gamma groups. In the bivariate H convention used here, a shared upper numerator
triple (e;E,F) gives Gamma(1-e-E*s-F*t). A shared lower denominator triple
(f;A,B) gives Gamma(1-f-A*s-B*t) in the denominator. Local upper numerator and
upper denominator pairs (a,A) give Gamma(1-a-A*s) and reciprocal Gamma(a+A*s),
respectively. Local lower numerator and lower denominator pairs (b,B) give
Gamma(b+B*s) and reciprocal Gamma(1-b-B*s), respectively. The second variable
obeys the same rules. The variables supply x^(-s)y^(-t). Every specialized
kernel and required branch is specified above.

References: NIST DLMF 5.5, 5.11, 5.15, 16.17; the inherited bivariate convention
is Andrade--Rathie--Farias, Definition B, DOI 10.1007/s40314-017-0451-z.
The project-specific source and proof are listed in DERIVATION.md.

To reproduce the finite checks and numerical comparisons:

```text
python build_and_verify.py
python numerical.py 45
python numerical.py 80
python check_inner.py
python check_shifted.py
```

The numerical scripts require mpmath; exact checks require SymPy.
No Wolfram kernel or external multivariate-special-function package was used.
'''
full=header+unchanged+newsection+primitive+footer
(B/'FORMULA.md').write_text(full)
checks=json.loads((B/'results/exact_checks.json').read_text())
report={'exact_finite_checks':checks,'numerical_45':json.loads((B/'results/numerical_45.json').read_text()),'numerical_80':json.loads((B/'results/numerical_80.json').read_text()),'independent_inner_Barnes':json.loads((B/'results/inner_checks.json').read_text()),'original_five_shift_comparison':json.loads((B/'results/shifted_check.json').read_text()),'all_sector_reevaluation':False,'new_rigorous_interval_certificate':False,'physical_graph_RG_identification':'inherited','Wolfram_kernel_execution':False}
(B/'results/check_report.json').write_text(json.dumps(report,indent=2))
(B/'README.md').write_text('''# Nine-value C6 representation\n\nRead FORMULA.md for the complete finite expression and DERIVATION.md for the new\nseventh-sector proof and limitations. The unchanged input and central-series\nsource are under inputs/. Run build_and_verify.py for the exact finite checks.\nRun numerical.py 45, numerical.py 80, check_inner.py, then check_shifted.py for\nthe recorded numerical routes. Numerical quadrature is not interval certified.\nThe special-function expression contains no explicit integration/summation\noperator; the numerical scripts evaluate the named values through proved\nrepresentations. This package does not independently derive the physical graph\ncoefficient or certify the complete C6 value.\n''')
out=Path('/mnt/data')
for src,dst in [('FORMULA.md','C6_seventh_two_values_formula.md'),('DERIVATION.md','C6_seventh_two_values_derivation.md'),('results/expression.json','C6_seventh_two_values_expression.json'),('results/check_report.json','C6_seventh_two_values_checks.json')]:
    shutil.copyfile(B/src,out/dst)
with zipfile.ZipFile(out/'C6_seventh_two_values_reduction.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(B.rglob('*')):
        if p.is_file() and '__pycache__' not in str(p): z.write(p,Path('C6_seventh_two_values')/p.relative_to(B))
print('Assembled:',out/'C6_seventh_two_values_reduction.zip')
