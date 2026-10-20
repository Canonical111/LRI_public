import gzip, json, random, sys, time, numpy as np
from mytabs import get, weights
from myjoint import fit
L,raw,T=get()
W=weights(L,T)
print('my wrel max per order',{n:round(float(w.max()),2) for n,w in W.items()})
DS={'raw':T['raw'],'dconn':T['fmean'],'dconn_w':T['fmean'],'dconn_s46':T['s46'],'dconn_old':T['old']}
R='<TMP>/scratchpad/dconn_refit72/joint/out/r72/'
kind=sys.argv[1]; nsamp=int(sys.argv[2]); seed=int(sys.argv[3])
files={'o8':['scan_o8.jsonl.gz','scan_o8_w.jsonl.gz'],'o7':['scan_o7.jsonl.gz','scan_o7_w.jsonl.gz']}[kind]
random.seed(seed)
recs=[]
for f in files:
    n=0
    pool=[]
    for line in gzip.open(R+f,'rt'):
        n+=1
        if random.random()<nsamp/90000.:
            r=json.loads(line)
            if 'err' not in r: pool.append(r)
    recs+=pool
print(kind,'sampled',len(recs))
t=time.time(); worst={}
for r in recs:
    C=DS[r['ds']]
    sig={n:W[n] for n in W} if r['ds']=='dconn_w' else None
    try:
        m=fit(L,C,r['lo'],r['hi'],r['base'],r['mode'],r['sh'],r['gap'],maxorder=8 if kind=='o8' else 7,hi_low=118 if r['low']=='th118' else None,sig=sig)
    except ValueError as e:
        print('fail',r['ds'],r['base'],e); continue
    for n,v in m['lim'].items():
        ref=r['lim'][str(n)]
        d=abs(v-ref)/max(1,abs(ref))
        key=(r['ds'],n)
        if d>=worst.get(key,(-1,))[0]: worst[key]=(d,r['base'],r['mode'],r['lo'],r['hi'],r['low'],v,ref)
print('time %.1fs'%(time.time()-t))
for k in sorted(worst): print(k,'max rel diff %.2e'%worst[k][0],worst[k][1:6],'%.6f %.6f'%worst[k][6:8])
