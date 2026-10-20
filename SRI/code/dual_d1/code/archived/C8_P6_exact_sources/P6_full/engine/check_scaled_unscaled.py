import os
from pathlib import Path
import sys,json

from period_polynomial import parse,add
r=Path(__file__).resolve().parent.parent
p=r/'SEQ6_v/b00/finite.expr';q=r/'EQ6_v/b00/coefficient_0.expr'
a=parse(p.read_text());b=parse(q.read_text());d=a.copy();add(d,b,-1)
report={'scaled':str(p),'unscaled':str(q),'scaled_terms':len(a),'unscaled_terms':len(b),'rational_scaled':str(a.get((),0)),'rational_unscaled':str(b.get((),0)),'exact_word_polynomial_equal':not d,'residual_terms':len(d)}
(Path(os.environ.get('F3_REPORT_DIRECTORY',str(r/'data')))/'scaled_unscaled_EQ6_b00.json').write_text(json.dumps(report,indent=2));print(report)
if d:
 def dump(poly):
  out=[]
  for mon,c in poly.items():
   at='*'.join(x if n==1 else f'({x})**{n}' for x,n in mon);out.append(str(c)+('*'+at if at else ''))
  return ' + '.join(out)
 (r/'data/scaled_unscaled_EQ6_b00_residual.expr').write_text(dump(d))
