"""Exploratory spectral-cutoff extrapolations, NOT fits in physical delta.
The reported variations are diagnostics, not rigorous error bars.
"""
import numpy as np,json,argparse
from pathlib import Path
from math import pi
from resummed import ROOT
MODELS=[[1.75,2.75],[1.75,2.75,3.5],[1.75,2.75,3.75],[1.75,2.75,3.5,3.75],[1.75,2.75,3.75,4.75],[1.75,2.75,3.5,3.75,4.75]]
def fits(seq,minimum_fractions=(.4,.5,.625,.75)):
 y=np.asarray(seq,float);N=len(y);out=[]
 for pp in MODELS:
  for f in minimum_fractions:
   ns=np.arange(max(8,int(f*N)),N+1);u=ns/N
   A=np.array([np.ones_like(u)]+[u**(-p) for p in pp]).T
   c=np.linalg.lstsq(A,y[ns-1],rcond=None)[0];res=A@c-y[ns-1]
   out.append(dict(powers=pp,Nmin=int(ns[0]),Nmax=N,limit=float(c[0]),max_residual=float(np.max(abs(res))),condition=float(np.linalg.cond(A))))
 return out

def assemble_seq(d):
 k=d['order'];a=d['lam'];cc=ROOT/f'counter_imp{k}_a{a}_N2048.json' if k else ROOT/f'counter_a{a}_N2048.json'
 if not cc.exists():return None
 co=json.loads(cc.read_text());b=co['two_point'];m=co['mixed'][-1]
 cs=[x for x in json.loads((ROOT/'improved_constants.json').read_text()) if x['order']==k and x['n']==512][0]
 t=cs['ct']/a;kap=cs['kappa'];const=b['Xdisc']+t*m['Xmixed']-kap*b['Dmixed']+t*t*32*pi*pi/3
 return np.array(d['Xchain'])+const
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=128);p.add_argument('--print-all',action='store_true');aa=p.parse_args();out=[]
 for fn in sorted(ROOT.glob(f'sequence_N{aa.size}_k*_a*.json')):
  d=json.loads(fn.read_text());seq=assemble_seq(d)
  if seq is None:continue
  ff=fits(seq);row=dict(order=d['order'],lam=d['lam'],last=float(seq[-1]),fits=ff);out.append(row)
  print('\nCASE',d['order'],d['lam'],'last',seq[-1])
  for f in ff:
   if aa.print_all or (len(f['powers'])>=3 and f['Nmin']>=aa.size/2):print(f['powers'],f['Nmin'],round(f['limit'],8),f['max_residual'])
 (ROOT/f'fit_diagnostics_N{aa.size}.json').write_text(json.dumps(out,indent=2))
