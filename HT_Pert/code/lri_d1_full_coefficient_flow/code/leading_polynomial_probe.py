"""Complete leading-polynomial *hypothesis* tested on full coefficient increments.
The amplitudes below are exploratory fitted parameters, not analytic tail results.
All logarithms of the postulated leading sector are retained. No thermal targets.
"""
from pathlib import Path
import sys,json,csv
import mpmath as mp
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'vendor'))
from fit_models import qr_fit
mp.mp.dps=80

def main():
 new={int(f.stem.split('_L')[1].split('_')[0]):json.loads(f.read_text()) for f in (ROOT/'results/new_coefficients').glob('dconn_L*_d8.json')}
 Lmax=max(new);rows=[];allout=[]
 for n in [4,5,6,7,8]:
  for lo in [8,12,16,20]:
   for extra in [0,1,2]:
    train=[L for L in range(lo,Lmax-8,2) if L in new and L+2 in new] # leave the four highest cutoff values out
    test=[L for L in range(Lmax-8,Lmax,2) if L in new and L+2 in new]
    def funcs(L):
     l=mp.log(mp.mpf(L)/32)
     return [l**k/mp.sqrt(L) for k in range(n-1)]+[mp.mpf(L)**(-mp.mpf(1+j/2)) for j in range(extra)]
    def diff(L):return [b-a for a,b in zip(funcs(L),funcs(L+2))]
    r=dict(order=n,lo=lo,extra_powers=extra,train_max=max(train)+2,withheld_max=Lmax)
    try:
     b,info=qr_fit([diff(L) for L in train],[mp.mpf(str(new[L+2]['C'][n]))-mp.mpf(str(new[L]['C'][n])) for L in train])
     # Prediction integrates the fitted shell response from the last known point.
     anchor=max(train)+2;const=mp.mpf(str(new[anchor]['C'][n]))-mp.fsum(x*y for x,y in zip(funcs(anchor),b))
     pred=[]
     for L in sorted({L+2 for L in test}):
      val=const+mp.fsum(x*y for x,y in zip(funcs(L),b));obs=mp.mpf(str(new[L]['C'][n]));pred.append(dict(L=L,predicted=mp.nstr(val,35),observed=float(obs),error=float(val-obs)))
     r.update(status='completed',coefficients=[mp.nstr(x,40) for x in b],intercept=mp.nstr(const,40),max_holdout_error=max(abs(z['error']) for z in pred),predictions=pred,**info)
     # Influence of bounded correlated input noise is calculated from the original C rows.
     X=mp.matrix([diff(L) for L in train]);col=mp.matrix(funcs(anchor))
     linear=mp.lu_solve(X.T*X,col);weights={L:mp.mpf(0) for L in set(train+[t+2 for t in train])};weights[anchor]+=1
     for j,L in enumerate(train):
      z=mp.fsum(X[j,k]*linear[k] for k in range(X.cols));weights[L]+=z;weights[L+2]-=z
     bound=mp.fsum(abs(w)*mp.mpf('3e-13')*max(1,abs(mp.mpf(str(new[L]['C'][n])))) for L,w in weights.items())
     r['bounded_input_noise_sensitivity']=float(bound)
    except Exception as exc:r.update(status='rejected',error=repr(exc))
    allout.append(r)
    rows.append({k:r.get(k,'') for k in ['order','lo','extra_powers','status','train_max','withheld_max','intercept','max_holdout_error','condition','bounded_input_noise_sensitivity']})
 with (ROOT/'results/leading_polynomial_probes.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 (ROOT/'results/leading_polynomial_probes.json').write_text(json.dumps(allout,indent=2)+'\n')
 for n in [6,7,8]:
  ok=[r for r in rows if r['order']==n and r['status']=='completed'];print('Order',n,'fits',len(ok))
  for r in ok:print(r)
if __name__=='__main__':main()
