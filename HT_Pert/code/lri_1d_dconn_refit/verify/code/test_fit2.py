import gzip, json, random, numpy as np
from mytabs import get, weights
from myjoint2 import fit2
L,raw,T=get(); W=weights(L,T)
R='<TMP>/scratchpad/dconn_refit72/joint/out/r72/'
random.seed(7); recs=[]
for f in ('scan_o8.jsonl.gz','scan_o8_w.jsonl.gz'):
    for line in gzip.open(R+f,'rt'):
        if random.random()<0.0006:
            r=json.loads(line)
            if 'err' not in r and r['ds'] in ('dconn','dconn_w','dconn_s46'): recs.append(r)
DS={'dconn':T['fmean'],'dconn_w':T['fmean'],'dconn_s46':T['s46']}
mx={}
for r in recs:
    noisy=r['ds'] in ('dconn','dconn_w')
    o=fit2(L,DS[r['ds']],r['lo'],r['hi'],r['base'],r['mode'],r['sh'],r['gap'],hi_low=118 if r['low']=='th118' else None,wrel=W if noisy else None,weighted=r['ds']=='dconn_w')
    for n in (6,7,8):
        ref=r['o'][str(n)]
        for j,name in ((4,'stat'),(7,'erms'),(0,'rms')):
            d=abs(o[n][name]-ref[j])/abs(ref[j]); mx[(name,n)]=max(mx.get((name,n),0),d)
        mx[('lim',n)]=max(mx.get(('lim',n),0),abs(o[n]['lim']-r['lim'][str(n)])/abs(r['lim'][str(n)]))
print(len(recs),{k:'%.1e'%v for k,v in sorted(mx.items())})
