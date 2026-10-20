"""d(phi) spacing only, Pmax=9 (exact for p0,p1,d1 through eps^4; p3 only used through eps^3 for g2,g3;
g4 is NOT reliable here and is not used: <V_0> = 0 in both phi and d phi)."""
import sys, json, gc, time
import numpy as np
from htb_big import *
def run_d1(L):
    t0=time.time()
    sp=BigSpace(L,9); S=bubble_S_table(L+1,K)
    idx={k:sp.index(STATES[k]) for k in ('p0','p1','p3','d1')}
    r,g,refs=tune_all(sp,None)
    sp8=BigSpace(L,8)
    jneed=sorted({(4*L-sp.E4[idx[k]])//2 for k in ('p0','p1','p3','d1')})
    vac=vacuum_at(sp8,r,g,jneed,S); del sp8; gc.collect()
    Xg=g2D_full(sp,g,4*L,S)
    W={k:int(((L+1)//2)-(((4*L-sp.E4[i])//4+1)//2)) for k,i in idx.items()}
    rowvals={}
    for k,i in idx.items():
        j=(4*L-sp.E4[i])//2
        rg=Xg[i].copy(); r3=rg.copy(); r3[3]+=g[1]**3*W[k]
        rowvals[k]={'g2D':rg,'g2D+g3W':r3,'Dfull_raw':vac[2*L][0]-vac[j][0],'Dfull_c':vac[2*L][1]-vac[j][1]}
    variants=['raw','g2D','g2D+g3W','Dfull_raw','Dfull_c']
    def Xof(v):
        if v=='raw': return None
        X=Xg.copy()
        for k,i in idx.items(): X[i]=rowvals[k][v]
        return X
    tuned={}
    for v in variants:
        X=Xof(v); rr,gg,E=ref_variant(refs,r,g,X); tuned[v]=(rr,gg,E); del X
    del refs; gc.collect()
    b=base(sp,idx['d1'],r,g); res={'L':L,'dim':sp.dim,'variants':{}}
    for v in variants:
        rr,gg,E=tuned[v]; X=Xof(v); Ed=b.finish(rr,gg,X); del X
        res['variants'][v]={'r':rr.tolist(),'spacing_d1':(Ed-E[1]).tolist()}
    res['seconds']=time.time()-t0
    print(json.dumps({'L':L,'dim':sp.dim,'sec':round(res['seconds'],1),**{v:res['variants'][v]['spacing_d1'][2:] for v in variants}}),flush=True)
    return res
if __name__=='__main__':
    for L in [int(a) for a in sys.argv[1:]]:
        json.dump(run_d1(L),open(f'd1_L{L}.json','w'),indent=1)
