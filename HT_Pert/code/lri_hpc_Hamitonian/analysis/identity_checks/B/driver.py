import numpy as np, time, json, sys
from htb import *
sys.path.insert(0,'<TMP>/scratchpad/identity/B/pkgref')
K=4
STATES={'p0':[], 'p1':[0], 'p2':[0,0], 'p3':[0,0,0], 'd1':[1], 'd2':[0,1], 'd3':[0,0,1]}
def run(L, out):
    t0=time.time()
    sp=Space(L,11,K)
    S=bubble_S_table(L+1,K)
    # raw tuning (full, from scratch) through K
    r,g,refs=tune(sp,K)
    idx={k:sp.index(v) for k,v in STATES.items()}
    base=base_states(sp,K,r,g,idx)
    t1=time.time()
    raw,conn,sp8=vacuum_tables(L,K,r,g,None,S)
    t2=time.time()
    Xs={'raw':None,
        'g2D':g2D_diag(sp,g,4*L,S,K)}
    W=window_W(sp)
    X=Xs['g2D'].copy(); X[:,3]+= (g[1]**3)*W
    Xs['g2D+g3W']=X
    Xs['Dfull_raw']=dfull_diag(sp,raw)
    Xs['Dfull_c']=dfull_diag(sp,conn)
    res={'L':L,'dim':sp.dim,'dim8':sp8.dim,'r_raw':r.tolist(),'g_raw':g.tolist(),
         'Evac_raw':raw.tolist(),'Evac_conn':conn.tolist(),'variants':{}}
    for name,X in Xs.items():
        rr,gg,sts=finish(base,K,r,g,X)
        E={k:np.array(v.E) for k,v in sts.items()}
        d={'r':rr.tolist(),'g':gg.tolist(),
           'C':(E['p2']-E['p0']).tolist(),
           'tune1':(E['p1']-E['p0']).tolist(),'tune3':(E['p3']-E['p0']).tolist(),
           'E':{k:v.tolist() for k,v in E.items()}}
        for p in (1,2,3):
            d['spacing_d%d'%p]=(E['d%d'%p]-E['p%d'%p]).tolist()
        if X is not None:
            d['Xdiag']={k:X[idx[k]].tolist() for k in STATES}
        res['variants'][name]=d
    res['W']={k:int(W[idx[k]]) for k in STATES}
    res['seconds']=time.time()-t0; res['vac_seconds']=t2-t1
    out.append(res)
    return res
if __name__=='__main__':
    Ls=[int(a) for a in sys.argv[1:]]
    out=[]
    for L in Ls:
        res=run(L,out)
        v=res['variants']
        print(f"L={L} dim={res['dim']} dim8={res['dim8']} t={res['seconds']:.1f}s (vac {res['vac_seconds']:.1f}s)",flush=True)
        print('  r_raw',np.array(res['r_raw']),' g_raw',np.array(res['g_raw']))
        for name,d in v.items():
            print(f"  {name:10s} r4={d['r'][4]:+.12f} g4={d['g'][4]:+.12f} C={np.array(d['C'][2:])}  d1={np.array(d['spacing_d1'][2:])} d2={np.array(d['spacing_d2'][2:])} d3={np.array(d['spacing_d3'][2:])}",flush=True)
        json.dump(res,open(f'res_L{L}.json','w'),indent=1)
