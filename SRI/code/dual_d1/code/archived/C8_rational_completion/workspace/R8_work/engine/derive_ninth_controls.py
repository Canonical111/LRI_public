"""Singular A9-Z8 predicted solely from lower odd and vacuum moments."""
import install_fastq;install_fastq.install_domain()
import lower_controls as lc
from pathlib import Path
from fractions import Fraction as F
import json,time
root=Path(__file__).resolve().parent.parent;lc.ARCH=root.parent/'old_C7/C7_completion/engine';st=time.time();tab={}
for k,n,mx in [('A',3,2),('A',5,1),('A',7,0),('Z',2,0),('Z',4,1),('Z',6,0)]:
 tab[k,n]=lc.raw(n,k,'base',mx);print('LOWER_NINTH',k,n,time.time()-st,flush=True)
terms=[(1,[('A',7),('Z',2)]),(-1,[('A',5),('Z',2),('Z',2)]),(1,[('A',5),('Z',4)]),(1,[('A',3),('Z',2),('Z',2),('Z',2)]),(-2,[('A',3),('Z',2),('Z',4)]),(1,[('A',3),('Z',6)]),(-1,[('Z',2)]*4),(3,[('Z',2),('Z',2),('Z',4)]),(-1,[('Z',4),('Z',4)]),(-2,[('Z',2),('Z',6)])]
pred={}
for sign,fs in terms:
 prod={0:(F(1),)}
 for key in fs:prod=lc.mult(prod,tab[key],minp=-12,maxp=8)
 for p,v in prod.items():
  if p<0:pred[p]=lc.tp.padd(pred.get(p,()),lc.tp.pscale(v,sign))
r={'status':'ninth_singular_prediction_from_lower_moments','A9_or_Z8_new_inputs_used':False,'C8_conjecture_used':False,'polynomials':{str(p):list(map(str,v)) for p,v in pred.items()},'lower_moment_tables':{k+str(n):{str(p):list(map(str,v)) for p,v in data.items()} for (k,n),data in tab.items()},'seconds':time.time()-st}
(root/'ninth_lower_controls.json').write_text(json.dumps(r,indent=2));print('NINTH_PREDICTED',r['polynomials'])
