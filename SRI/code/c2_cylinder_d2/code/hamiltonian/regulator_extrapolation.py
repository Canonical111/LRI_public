"""Regulator-limit diagnostics for direct g^4 coefficients, NOT physical-delta fits.
The model variations below do not constitute certified uncertainty bounds.
"""
import json,numpy as np
from pathlib import Path
from resummed import ROOT
from analyze_fine import analyze

def pick_current():
 rows=[]
 ts=json.loads((ROOT/'tail_transseries_fits.json').read_text()) if (ROOT/'tail_transseries_fits.json').exists() else []
 for fn in sorted(ROOT.glob('fine_k*.json')):
  d=analyze(json.loads(fn.read_text()));k=d['order'];lam=d['lam']
  z=[z for z in ts if z['order']==k and z['lam']==lam]
  if z:
   ff=[f for f in z[0]['fits'] if len(f['powers'])>=3 and f['exponential_order'] in [1,2] and f['Nmin']>=160]
  else:ff=[f for f in d['raw_fits'] if len(f['powers'])>=4 and f['Nmin']>=160]
  v=np.array([f['limit'] for f in ff]);m=float(np.median(v));er=float((max(v)-min(v))/2)
  rows.append(dict(order=k,lam=lam,h_estimate=m,spectral_model_half_spread=er,spectral_model_values=v.tolist()))
 return rows

def basis(x,name):
 if name=='2log':return x*x*np.log(x)
 if name=='3log':return x*x*x*np.log(x)
 if name=='4log':return x**4*np.log(x)
 return x**float(name)

def local_models(rows):
 out=[]
 for k in sorted(set(r['order'] for r in rows)):
  rr=[r for r in rows if r['order']==k];x=np.array([r['lam'] for r in rr]);y=np.array([r['h_estimate'] for r in rr]);sig=np.array([max(1e-3,r['spectral_model_half_spread']) for r in rr])
  for nn in range(3,len(rr)+1):
   xx=x[:nn];yy=y[:nn];ss=sig[:nn]
   for powers in [['2','2log'],['2','3'],['2','2log','3'],['2','2log','4'],['2','3','4'],['2','2log','3','4']]:
    if len(powers)+1>nn:continue
    A=np.array([np.ones_like(xx)]+[basis(xx,p) for p in powers]).T
    for w in [False,True]:
     aa=A/ss[:,None] if w else A;bb=yy/ss if w else yy
     c=np.linalg.lstsq(aa,bb,rcond=None)[0]
     out.append(dict(order=k,npoints=nn,max_lambda=float(xx[-1]),powers=powers,weighted=w,h0=float(c[0]),max_residual=float(np.max(abs(A@c-yy)))))
 return out

if __name__=='__main__':
 rows=pick_current();out=local_models(rows)
 for r in rows:print('POINT',r['order'],r['lam'],r['h_estimate'],r['spectral_model_half_spread'])
 for r in out:print('FIT',r['order'],r['npoints'],r['powers'],r['weighted'],r['h0'],r['max_residual'])
 (ROOT/'regulator_diagnostics.json').write_text(json.dumps(dict(points=rows,fits=out),indent=2))
