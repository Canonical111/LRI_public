from pathlib import Path
import sys,json

from period_polynomial import parse,add
r=Path(__file__).resolve().parent.parent;f=r/'XE_terminal/b000'
a=parse((f/'growth_finite.expr').read_text());b=parse((f/'finite.expr').read_text());d=a.copy();add(d,b,-1)
print('A',len(a),a.get(()),'B',len(b),b.get(()),'DIFF',len(d),d.get(()),flush=True)
from assemble_new_finite import write_poly
(r/'data/growth_comparison_residual.expr').write_text(write_poly(d))
(r/'data/growth_comparison.json').write_text(json.dumps({'growth_terms':len(a),'reference_terms':len(b),'residual_terms':len(d),'rational_growth':str(a.get(())),'rational_reference':str(b.get(()))},indent=2))
for k,v in list(d.items())[:10]:print(k,v,flush=True)
