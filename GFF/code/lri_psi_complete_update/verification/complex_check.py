#!/usr/bin/env python3
"""Higher-working-precision complex test, following loss of digits in a 75-digit tail."""
from pathlib import Path
import json,time
import mpmath as m
from hyp3_asym import hyp3
st=time.perf_counter();m.mp.dps=130;t=m.mpc('.12','.07')
F=lambda z:hyp3([m.mpf('.5'),m.mpf('.5'),z],[1,1],N=180,order=64)
G=lambda z:hyp3([z,z,z],[m.mpf('.5')+z]*2,N=180,order=64)
r=m.cos(m.pi*t)**2*G(t)*G(-t)+m.pi**2*t*t*F(t)*F(-t)-1
rec={'working_digits':130,'N':180,'order':64,'t':['.12','.07'],'residual':m.nstr(r,50),'elapsed_seconds':time.perf_counter()-st,'reason':'Increased working precision to control complex-parameter tail cancellation; the 75-digit records are retained unchanged.'}
Path(__file__).with_name('complex_bilinear_130.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2))
