from pathlib import Path
from fractions import Fraction
from decimal import Decimal, localcontext
import json, shutil, zipfile

root=Path(__file__).resolve().parent
obj=json.loads((root/'results.json').read_text())

def rounded(rec, places=60):
    den=1<<rec['denominator_power_of_two']
    lo=Fraction(int(rec['lower_numerator']), den)
    hi=Fraction(int(rec['upper_numerator']), den)
    with localcontext() as ctx:
        ctx.prec=places+30
        quantum=Decimal(1).scaleb(-places)
        a=(Decimal(lo.numerator)/Decimal(lo.denominator)).quantize(quantum)
        b=(Decimal(hi.numerator)/Decimal(hi.denominator)).quantize(quantum)
        assert a==b, 'Endpoints do not round alike at requested precision'
        return format(a,'f')

labels=[
 ('Wheel, n >= 1: Wcentral','Wcentral_n_ge_1'),
 ('Wheel, n >= 0: W0','Wzero_n_ge_0'),
 ('Complete seventh-power series: M7','M7'),
 ('Primitive spectral bracket: Phi_0 + 2 sum_{n>=1} (-1)^n Phi_n','primitive_spectral_bracket'),
 ('Cubic primitive normalization: PaCubic = Pa/(2 pi^2)','PaCubic'),
 ('Original primitive: Pa','Pa'),
 ('Combined contribution of all three residuals to C6','three_residuals_total_in_C6'),
]
text=['C6(1): numerical evaluation of the three current residual series',
      '=============================================================', '',
      'There are THREE explicit residual infinite sums. In the latest representation',
      'each has one infinite index. Fixed standard special-function values and finite',
      'harmonic-number coefficients are not additional residual infinite sums.', '',
      'Normalization: r6 = 2187 C6(1).',
      'Wheel W0 includes n=0; Wcentral begins at n=1.',
      'W0 = Wcentral + (8 + 5 pi) pi^2/3.',
      'Primitive spectral bracket = Pa/(8 pi^3) = PaCubic/(4 pi).', '',
      'All displayed values below are rounded to 60 places; both exact interval',
      'endpoints round to the stated value.', '']
for label,key in labels:
    text += [label, rounded(obj['values'][key]), '']
text += ['Contributions to C6 (already divided by 2187):','']
for key,factor in [('wheel','-393 pi^3 W0 / 2187'),
                   ('seventh','24 pi^3 M7 / 2187'),
                   ('primitive','768 pi^3 spectral_bracket / 2187 = 96 Pa / 2187')]:
    text += [key+': '+factor, rounded(obj['contributions_in_C6'][key]), '']
text += [
    'Previously recorded complete C6 value (not all fixed values rerun here):',
    rounded(obj['values']['C6_saved_full_certificate']), '',
    'Methods rerun in this calculation:',
    'Wheel: exact rational finite tail corrections, N=256, orders 40 and 41.',
    'Seventh: Euler-weighted finite sum, N=600; explicit tail allowance 2^(100-N).',
    'Primitive: retained two-branch geometric recurrence, N=200; error bound from',
    'the last two recurrence states. Spectral normalization uses its exact identity',
    'with Pa. No raw spectral partial sum was treated as the limiting value.',
    'Every finite arithmetic operation used outward-rounded 1280-bit dyadic intervals.', '',
    'The three new intervals overlap the corresponding saved source certificates.',
    'The source packages supply the analytic tail theorems and the identity between',
    'the primitive representations. This run is not a new proof of those inputs.',
    'No new finite closed-form evaluation, physical graph/RG identification, or',
    'independent evaluation of all fixed terms of C6 is claimed.',
    'The finite-part value included in the JSON is obtained by subtraction from the',
    'saved full C6 certificate and is explicitly labelled as such.',
]
report='\n'.join(text)+'\n'
(root/'report.txt').write_text(report)
(root.parent/'C6_three_residual_sums_evaluated.txt').write_text(report)
shutil.copyfile(root/'results.json',root.parent/'C6_three_residual_sums_intervals.json')
(root/'README.md').write_text('''# Evaluate the three current C6 residual sums

Run `python evaluate.py` and then `python make_report.py` with Python 3,
SymPy and mpmath installed. The `work/` directory preserves the supplied
evaluation packages. `evaluate.py` recomputes the residuals using those packages;
prior values are read only afterward for overlap checks and the labelled
inherited full-C6 record. All comparison certificates are included locally.
The report and result archive are written alongside this directory.

The numerical values are not new symbolic finite summations. The primitive
spectral bracket is evaluated through its exact normalization with the faster
retained primitive recurrence. See `report.txt` for definitions and scope.
''')
with zipfile.ZipFile(root.parent/'C6_three_residual_sums_evaluation.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in root.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            z.write(p,Path(root.name)/p.relative_to(root))
print(report)
