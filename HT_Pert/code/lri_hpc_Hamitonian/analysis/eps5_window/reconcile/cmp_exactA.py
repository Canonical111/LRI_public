import json
from fractions import Fraction as F
S='<TMP>/scratchpad/eps5'
VM={'raw':'raw','g2D':'g2D','g2D3W':'g2D+g3W','Dconn':'Dconn','Dfull':'Dfull_raw'}
mx=0;n=0
for c in (32,33,48,49,64,65):
    e=json.load(open(f'{S}/B/exact5_c{c}.json')); lam=c/4
    fn=f'{S}/A/res5_{lam:g}.json'
    try: a=json.load(open(fn))['summary']
    except FileNotFoundError: print('no A file',fn); continue
    for va,vb in VM.items():
        V=e['variants'][vb]
        for ka,kb in [('C','C'),('v_dphi1','spacing_d1'),('v_dphi2','spacing_d2')]:
            if kb not in V: continue
            for k in range(2,6):
                x=a[va][ka][k]; y=float(F(V[kb][k])); d=abs(x-y)/max(1,abs(y)); n+=1
                if d>mx: mx=d; w=(lam,va,ka,k,x,y)
print('A vs B exact rationals: n=%d max rel %.2e'%(n,mx), w)
