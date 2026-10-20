from pathlib import Path
import json,sympy as s,hashlib
from read_expression import load
ROOT=Path(__file__).resolve().parent.parent
out=s.S.Zero;coverage=[]
for f,mu in [(1,2),(2,1)]:
 folder=ROOT/f'B4_v_f{f}';meta=json.loads((folder/'manifest.json').read_text())
 for rec in meta['blocks']:
  pp=folder/rec['block']/'finite.expr';assert pp.is_file()
  out-=mu*load(pp);coverage.append(str(pp.relative_to(ROOT)))
ref=ROOT/'inherited/Q4_v_p0.expr'
reference=s.expand(load(ref)).coeff(s.Symbol('ell'),1)
diff=s.expand(out-reference)
(ROOT/'data/B4_v_control.expr').write_text(s.sstr(s.expand(out),order='none'))
(ROOT/'data/B4_v_reference.expr').write_text(s.sstr(reference,order='none'))
(ROOT/'data/B4_v_difference.expr').write_text(s.sstr(diff,order='none'))
report={'blocks':coverage,'symbolic_difference_zero':diff==0,'difference_terms':len(s.Add.make_args(diff)),'rational_new':str(s.expand(out).as_coeff_Add()[0]),'rational_reference':str(reference.as_coeff_Add()[0])}
(ROOT/'data/B4_control_report.json').write_text(json.dumps(report,indent=2));print(report)
