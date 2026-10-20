"""Exact change of variables in saved unscaled intermediate integrals.
The interval factor is removed and homogeneous rational coefficients are
specialized to e=1; dimensionless hyperlogarithm letters are specialized likewise.
"""
from pathlib import Path
import json,time,hashlib,argparse
import scaled_b as sb
from hyperlog_core import *

def convert(items,n,stage):
 N=n-2;out={};count=0
 interval=1-(n-1)*e-GEN[N]
 for (words,logs),co in items:
  assert not logs
  r=co/interval
  ds=set(map(sum,r.numer))
  assert len(ds)<=1,('nonhomogeneous numerator',stage,ds)
  for fac in r.denf:assert len(set(map(sum,fac)))==1,('nonhomogeneous denominator',fac)
  den_degree=sum(next(iter(set(map(sum,f))))*p for f,p in r.denf.items())
  if ds:assert next(iter(ds))-den_degree==-(N-stage),(stage,ds,den_degree,N)
  coeff=sub(r,0,K.one)
  wnew=tuple(tuple(sub(a,0,K.one) for a in w) for w in words)
  addto(out,(wnew,()),coeff);count+=1
 return clean(out),count

def one(name):
 n=int(name.split('_')[0][1:]);old=sb.ROOT/'blocks'/name;new=sb.OUT/name;st=time.time()
 if not (new/'source.json').exists():return
 report={'id':name,'conversions':[]}
 # Check the entire separately regenerated initial source.
 rows=sb.tb.br.rr.load(old/'stage1.jsonl');conv,_=convert(rows,n,1)
 fresh=dict(sb.tb.br.rr.load(new/'stage1.jsonl'))
 assert set(conv)==set(fresh),(name,len(conv),len(fresh))
 for key,co in conv.items():assert co==fresh[key],('source mismatch',name,key)
 report['independent_source_equality_exact']=True
 del rows,conv,fresh;sb.tb.br.rr.clear()
 for stage in reversed(range(2,n-3)):
  p=old/f'stage{stage}.jsonl';dest=new/f'stage{stage}.jsonl'
  if not p.exists():continue
  if dest.exists():break
  rows=sb.tb.br.rr.load(p);conv,count=convert(rows,n,stage)
  sb.tb.br.rr.dump(dest,conv)
  report['conversions'].append({'stage':stage,'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'input_rows':count,'output_rows':len(conv),'homogeneity_exact':True})
  del rows,conv;sb.tb.br.rr.clear();break
 report['seconds']=time.time()-st
 (new/'conversion.json').write_text(json.dumps(report,indent=2));print('CONVERTED',report,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--block');a=p.parse_args()
 one(a.block)
