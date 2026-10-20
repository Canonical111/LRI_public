import json,numpy as np
from pathlib import Path
from math import pi,log
from resummed import ROOT
from analyze_sequences import fits as rawfits
B0=1.2684043089391425437948799174

def analyze(d):
    N=d['N'];a=d['lam'];k=d['order'];b=d['two_point'];mi=d['mixed'];c=d['planar'];cv=d['curvature']
    # Exact mixed-sum tail fits are very well inside N*lambda >>1.
    mf=[f for f in mi['fits'] if len(f['powers'])>=3 and f['Nmin']>=2048]
    med=float(np.median([f['limit'] for f in mf]));spread=float(max(f['limit'] for f in mf)-min(f['limit'] for f in mf))
    t=c['ct']/a+cv['thermal_lambda_coefficient']*a;kk=-c['kappa']
    con=b['Xdisc']+t*med+kk*b['Dmixed']+t*t*32*pi*pi/3-2*B0*log(a)*b['X2']
    seq=np.array(d['raw']['Xchain'])+con
    rf=rawfits(seq)
    return dict(order=k,lam=a,N=N,last=float(seq[-1]),mixed_limit=med,mixed_spread=spread,t2_improved=t,X2=b['X2'],raw_fits=rf,sequence=seq.tolist())
if __name__=='__main__':
    out=[]
    for fn in sorted(ROOT.glob('fine_k*.json')):
        d=analyze(json.loads(fn.read_text()));out.append(d)
        print('\nFINE',d['order'],d['lam'],'last',d['last'],'mixedspread',d['mixed_spread'])
        for f in d['raw_fits']:
            if len(f['powers'])>=3 and f['Nmin']>=128:print(f['powers'],f['Nmin'],round(f['limit'],9),'res',f['max_residual'])
    (ROOT/'fine_analysis.json').write_text(json.dumps(out,indent=2))
