"""Predict singular tail of A7-Z6 exclusively from lower complete moments.
Also extract archived base and first charge boundary jets for scale restoration.
"""
import install_fastq;install_fastq.install_domain()
import lower_controls as lc
from pathlib import Path
from fractions import Fraction as Q
import json,time
root=Path(__file__).resolve().parent.parent
lc.ARCH=root.parent/'old_C7/C7_completion/engine'
start=time.time();tables={}
for n,k,mx in [(3,'A',1),(5,'A',0),(2,'Z',0),(4,'Z',0)]:
 for deriv in ['base','d']:
  tables[n,k,deriv]=lc.raw(n,k,deriv,mx)
  print('RAW',k,n,deriv,time.time()-start,flush=True)
terms=[(1,[(5,'A'),(2,'Z')]),(-1,[(3,'A'),(2,'Z'),(2,'Z')]),(1,[(3,'A'),(4,'Z')]),(1,[(2,'Z'),(2,'Z'),(2,'Z')]),(-2,[(2,'Z'),(4,'Z')])]
pred={}
for sign,fs in terms:
 for it in range(len(fs)):
  prod={0:(Q(1),)}
  for j,(n,k) in enumerate(fs):prod=lc.mult(prod,tables[n,k,'d' if it==j else 'base'],minp=-10,maxp=8)
  for p,poly in prod.items():
   if p<0:pred[p]=lc.tp.padd(pred.get(p,()),lc.tp.pscale(poly,sign))
print('PREDICTED',{p:list(map(str,v)) for p,v in pred.items()},flush=True)
arch={}
for n,k in [(7,'A'),(6,'Z')]:
 for deriv in ['base','v']:
  tab=lc.raw(n,k,deriv,0);print('CONTROL',k,n,deriv,time.time()-start,flush=True)
  arch[k+str(n)+'_'+deriv]={str(p):list(map(str,v)) for p,v in tab.items()}
report={'status':'independent_lower_moment_prediction','prediction_reads_new_tail_residues':False,'C8_conjecture_used':False,
 'singular_tail_difference':{str(p):list(map(str,v)) for p,v in pred.items()},'archived_base_and_charge_polynomials':arch,
 'lower_moments':{k+str(n)+'_'+d:{str(p):list(map(str,v)) for p,v in tab.items()} for (n,k,d),tab in tables.items()},'seconds':time.time()-start}
(root/'tail_lower_controls.json').write_text(json.dumps(report,indent=2));print('PREDICTION_DONE',flush=True)
