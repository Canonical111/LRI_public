import json,numpy as np
from resummed import ROOT
from analyze_fine import analyze

def fits_with_tail(y,a_tail):
    y=np.asarray(y);N=len(y);out=[]
    for ps in [[2.75,3.75],[2.75,3.5],[2.75,3.5,3.75],[2.75,3.75,4.75],[2.75,3.5,3.75,4.75],[2.75,3.75,4.75,5.75]]:
      for frac in [.375,.5,.625,.75]:
        n=np.arange(round(frac*N),N+1);u=n/N
        yy=y[n-1]+a_tail*n.astype(float)**(-1.75)
        A=np.array([np.ones_like(u)]+[u**(-p) for p in ps]).T
        c=np.linalg.lstsq(A,yy,rcond=None)[0];err=np.max(abs(A@c-yy))
        out.append(dict(powers=ps,Nmin=int(n[0]),limit=float(c[0]),max_residual=float(err)))
    return out

if __name__=='__main__':
    t=json.loads((ROOT/'exact_leading_tail.json').read_text());rows=[]
    for f in sorted(ROOT.glob('fine_k*.json')):
      d=analyze(json.loads(f.read_text()));ts=[z for z in t if z['order']==d['order'] and z['lam']==d['lam']]
      if not ts:continue
      ts=max(ts,key=lambda z:z['N']);a=ts['asymptotic_tail_coefficient'];fs=fits_with_tail(d['sequence'],a)
      rows.append(dict(order=d['order'],lam=d['lam'],tail=ts,fits=fs))
      print('\n',d['order'],d['lam'],'a_tail',a,'tail256',a*256**(-1.75),flush=True)
      for ff in fs:
        if ff['Nmin']>=160:print(ff['powers'],ff['Nmin'],round(ff['limit'],9),ff['max_residual'])
    (ROOT/'leading_tail_analysis.json').write_text(json.dumps(rows,indent=2))
