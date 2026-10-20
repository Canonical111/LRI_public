"""Numerical recognition only: no identity is asserted by this search."""
import mpmath as mp,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
mp.mp.dps=90
label=sys.argv[1] if len(sys.argv)>1 else 'run1'
r=json.loads((root/f'final_evaluation_{label}.json').read_text());C=mp.mpf(r['coefficients']['C6'])
basis=[C,mp.mpf(1),mp.zeta(2),mp.zeta(3),mp.zeta(4),mp.zeta(5),mp.zeta(2)*mp.zeta(3)]
print('C6',mp.nstr(C,70));print('basis C6,1,zeta2,zeta3,zeta4,zeta5,zeta2*zeta3')
out=[]
for tol in ['1e-35','1e-45','1e-55']:
 rel=mp.pslq(mp.matrix(basis),tol=mp.mpf(tol),maxcoeff=10000000,maxsteps=10000)
 residual=mp.fsum(c*v for c,v in zip(rel,basis)) if rel else None
 print(tol,rel,'residual',mp.nstr(residual,15) if rel else None,flush=True)
 out.append({'tolerance':tol,'relation':rel,'residual':str(residual)})
(root/f'C6_recognition_{label}.json').write_text(json.dumps(out,indent=2))
