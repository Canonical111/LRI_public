"""Fit prior same-scheme data and freeze predictions of new complete cutoffs.
No newly generated coefficient file is read here. No C4..C8 continuum reference.
These are explicitly model-dependent forecasts, not derived analytic amplitudes.
"""
from pathlib import Path
import sys, json, hashlib
import mpmath as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'vendor'))
from fit_models import sequential,expo,integral_expo,subcolumns,exactc2,limits23
mp.mp.dps=70

def evaluate(model,L,base,mode):
    o={int(k):v for k,v in model['orders'].items()};known=limits23();known.update({int(k):mp.mpf(v['intercept']) for k,v in o.items()})
    ell=mp.log(L);t=exactc2(L,mp.mp.dps)-known[2]
    row3=[t]+subcolumns(L,base);b3=list(map(mp.mpf,model['third_order_control']['coefficients']))
    w={int(k):mp.mpf(v) for k,v in model['omega_used'].items()}; sources={};pred={2:t+known[2]}
    pred[3]=known[3]+sum(a*b for a,b in zip(row3,b3))-w[1]*ell*t
    # Recreate the fit's per-order parameter convention, including free omega.
    for n in range(4,9):
        b=list(map(mp.mpf,o[n]['coefficients']));free=(n==8) or (mode=='free_omega' and n>=5)
        new=(mode=='source5' and n==5) or (mode=='sources567' and 5<=n<=7)
        row=[mp.mpf(1),t]+subcolumns(L,base)
        if new:row.append(ell/mp.sqrt(L))
        if free:row.append(-ell*t)
        wcalc=w.copy()
        if free:wcalc[n-2]=mp.mpf(0)
        force=sum(v*integral_expo(ell,wcalc,n-k)/mp.sqrt(L) for k,v in sources.items() if k<=n)
        v=sum(a*b for a,b in zip(row,b))+force
        e=expo(ell,wcalc,n-2)
        v-=sum(e[j]*(pred[n-j]-known[n-j]) for j in range(1,n-1))
        pred[n]=v
        if new:sources[n]=b[-1]
    return {str(k):mp.nstr(v,40) for k,v in pred.items()}

def main():
    D=json.loads((ROOT/'inputs/scheme_data.json').read_text());g=json.loads((ROOT/'inputs/independent_gap_inputs.json').read_text())['extended']
    rows=[]
    for lo in [4,8]:
      for base in ['S','A']:
       for mode in ['homogeneous','source5','sources567','free_omega']:
        row=dict(lo=lo,base=base,mode=mode)
        try:
            fit=sequential(D,g,'dconn',lo,{3:118,4:118,5:118,6:28,7:28,8:24},8,base,mode)
            row.update(status='completed',fit=fit,predictions={str(L):evaluate(fit,L,base,mode) for L in range(26,45,2)})
        except Exception as e:row.update(status='rejected',error=repr(e))
        rows.append(row);print(lo,base,mode,row['status'],flush=True)
    file=ROOT/'results/frozen_forecasts.json'
    if file.exists():raise FileExistsError('Forecasts already frozen; refusing overwrite')
    file.write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    (ROOT/'results/forecast_sha256.txt').write_text(hashlib.sha256(file.read_bytes()).hexdigest()+'  frozen_forecasts.json\n')
if __name__=='__main__':main()
