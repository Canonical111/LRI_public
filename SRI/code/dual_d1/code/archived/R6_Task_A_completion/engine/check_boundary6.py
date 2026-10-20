from pathlib import Path
import json,time
from fractions import Fraction as F
import sympy as s
from read_expression import parse
import boundary_residue as b
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'boundary'
results=[]
for deriv in ['base','v','d']:
 ds=[]
 for face in [1,2,3]:
  b.run(6,face,deriv)
  ds.append(json.loads((OUT/f'B6_{deriv}_f{face}_result.json').read_text()))
 value=-(2*F(ds[0]['boundary_constant'])+2*F(ds[1]['boundary_constant'])+F(ds[2]['boundary_constant']))
 expr=parse((ROOT/'series'/f'Q6_{deriv}_p0.expr').read_text())
 repl={a:s.S.Zero for a in expr.free_symbols if str(a)!='ell'};repl[s.pi]=s.S.Zero
 for a in s.preorder_traversal(expr):
  if a.func in (s.log,s.polylog,s.zeta):repl[a]=s.S.Zero
 expected=s.expand(expr.xreplace(repl)).coeff(s.Symbol('ell'),1)
 d={'derivative':deriv,'boundary_computed':str(value),'archived_residue':str(expected),'equal':value==F(str(expected)),'faces':ds}
 assert d['equal'],d
 results.append(d);(ROOT.parent/'boundary6_controls.json').write_text(json.dumps(results,indent=2));print('CONTROL_VERIFIED',d,flush=True)
 b.rr.clear();b.tp.clear_caches()
