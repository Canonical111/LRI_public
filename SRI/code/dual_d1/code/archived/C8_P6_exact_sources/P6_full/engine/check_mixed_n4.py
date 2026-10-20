import boundary_mixed as b
import sympy as s
from read_expression import load as expr
from pathlib import Path
import json,time
r=b.ROOT;out=0;logs=[]
for face in (1,2):
 b.fb.sources_boundary(4,face,'vd')
 tag=f'B4_vd_f{face}';m=json.loads((r/tag/'manifest.json').read_text());cv=0
 for x in m['blocks']:
  b.fb.worker_boundary(tag,x['block'])
  cv+=expr(r/tag/x['block']/'finite.expr');b.clear()
 cv=s.expand(cv);out-=(2 if face==1 else 1)*cv;logs.append({'face':face,'value':str(cv)})
(r/'control').mkdir(exist_ok=True);p=r/'control/Q4_vd_log.expr';p.write_text(s.sstr(s.expand(out),order='none'))
rat=out.xreplace({**{x:s.S.Zero for x in out.atoms(s.Function)},**{x:s.S.Zero for x in out.free_symbols if str(x).startswith(('R_','Z'))},s.pi:s.S.Zero})
print('N4_RATIONAL',s.expand(rat),flush=True);assert s.expand(rat)==712
(r/'control/eval_manifest.json').write_text(json.dumps({'Q4_vd_log':str(p)}))
(r/'control/faces.json').write_text(json.dumps(logs,indent=2))
print('CONTROL_INTEGRATED')
