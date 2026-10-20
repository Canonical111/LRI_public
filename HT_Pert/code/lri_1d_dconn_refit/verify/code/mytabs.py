"""All verifier tables incl. s46 and own weights; cached to npz."""
import json, numpy as np, os
from myjoint import tables, old_table, eser, W_EXT
from myload import SCR
CACHE='../out/tabs.npz'
def floor_curves(k, qf=3.0):
    V=json.load(open(SCR+'/delta/out/variants_full_hi72.json'))
    b=V['dC%d'%k]; P=np.array(b['pred']); mr=np.array(b['maxres'])
    lo=np.array([int(s.split('lo=')[1].split('|')[0]) for s in b['labels']])
    best={x:mr[lo==x].min() for x in set(lo)}
    fl=np.array([mr[i]<=qf*best[lo[i]] for i in range(len(mr))])
    return b['L'],P,fl
def get():
    if os.path.exists(CACHE):
        z=np.load(CACHE,allow_pickle=True); return z['L'],z['raw'],z['T'].item()
    L,raw,T,D=tables()
    T['old']=old_table(L,raw)
    s46=T['fmean'].copy()
    Ls=list(L.astype(int))
    for k in (6,7,8):
        Lv,P,fl=floor_curves(k)
        for j,l in enumerate(Lv):
            if 46<=l<=72:
                i=Ls.index(l); s46[i,k]=raw[i,k]+P[fl,j].mean()
    T['s46']=s46
    T['raw']=raw
    np.savez(CACHE,L=L,raw=raw,T=np.array(T,dtype=object))
    return L,raw,T
def weights(L,T,SIGQ={4:7e-13,5:9e-12,6:8e-11,7:8e-10,8:1.5e-8},noise=None):
    """relative per-row noise of Y_n (1 at quiet rows); noise realization = fmean - s46 at 46..72, or given sigmas."""
    cl=(L>=46)&(L<=72)
    dC=np.nan_to_num(T['fmean']-T['s46'])
    l=np.log(L); w=W_EXT
    e=[np.ones_like(l)]
    for n in range(1,7):
        e.append(l/n*sum(j*w.get(j,0.)*e[n-j] for j in range(1,n+1)))
    out={}
    for n in range(4,9):
        dY=dC[:,n]+sum(e[j]*dC[:,n-j] for j in range(1,n-1))
        s=float(np.sqrt(np.mean(dY[cl]**2))) if noise is None else noise[n]
        out[n]=np.where(cl,np.sqrt(1+(s/SIGQ[n])**2),1.)
    return out
