import json, glob, numpy as np
S='<TMP>/scratchpad/eps5'
VM={'raw':'raw','g2D':'g2D','g2D3W':'g2D+g3W','Dconn':'Dconn','Dfull':'Dfull_raw'}
A={}
for f in glob.glob(S+'/A/res5_*.json'):
    o=json.load(open(f)); A[float(o['Lam'])]=o['summary']
B={}
for f in glob.glob(S+'/B/full5_c*.json'):
    o=json.load(open(f)); B[float(o['Lambda'])]=o['variants']
common=sorted(set(A)&set(B))
print('common cutoffs:', len(common), common[:5], '...', common[-5:])
stats={}
n=0
worst=[]
for lam in common:
    for va,vb in VM.items():
        a=A[lam][va]; b=B[lam][vb]
        pairs=[('C','C'),('v_dphi1','spacing_d1'),('v_dphi2','spacing_d2')]
        if va=='raw': pairs+= [('r','r'),('g','g')]
        for ka,kb in pairs:
            for k in range(2,6):
                x=a[ka][k]; y=b[kb][k]
                d=abs(x-y); rel=d/max(1,abs(x)); n+=1
                key=(ka,k); stats[key]=max(stats.get(key,0),rel)
                worst.append((rel,lam,va,ka,k,x,y))
worst.sort(reverse=True)
print('numbers compared', n)
for k,v in sorted(stats.items()): print(k, f'{v:.2e}')
print('worst 8:')
for w in worst[:8]: print(w)
# also variant-level r,g for corrections
mx=0
for lam in common:
    for va,vb in VM.items():
        if va=='raw': continue
        a=A[lam][va]; b=B[lam][vb]
        # A stores dr4..; B stores r,g full
        ra=np.array(A[lam]['raw']['r']); ga=np.array(A[lam]['raw']['g'])
        r4=ra[4]+a['dr4']; r5=ra[5]+a['dr5']; g4=ga[4]+a['dg4']; g5=ga[5]+a['dg5']
        for x,y in [(r4,b['r'][4]),(r5,b['r'][5]),(g4,b['g'][4]),(g5,b['g'][5])]:
            mx=max(mx,abs(x-y)/max(1,abs(y)))
print('variant r4,r5,g4,g5 max rel diff', f'{mx:.2e}')
