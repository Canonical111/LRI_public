import json
from fractions import Fraction as F
S='<TMP>/scratchpad/eps5'
VM={'raw':'raw','g2D':'g2D','g2D3W':'g2D+g3W','Dconn':'Dconn','Dfull':'Dfull_raw'}
mx=0;n=0
for c in (35,43,51):
    e=json.load(open(f'{S}/reconcile/exactL2/exact5_c{c}.json'))['variants']; lam=c/4
    a=json.load(open(f'{S}/A/res5_{lam:g}.json'))['summary']
    for va,vb in VM.items():
        for ka,kb in [('C','C'),('v_dphi1','spacing_d1'),('v_dphi2','spacing_d2')]:
            for k in range(2,6):
                x=a[va][ka][k]; y=float(F(e[vb][kb][k])); d=abs(x-y)/max(1,abs(y)); n+=1
                if d>mx: mx=d; w=(lam,va,ka,k,x,y)
    print(lam, 'v5 dphi raw/g2D3W/Dconn exact:', [round(float(F(e[VM[v]]['spacing_d1'][5])),12) for v in ('raw','g2D3W','Dconn')])
print('phase-3/4: A vs exact rationals n=%d max rel %.2e'%(n,mx), w)
