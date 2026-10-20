# C63d d=3 cost model (RECON section 6.3). Inputs: C7(3) run1 archive (graph_replicates.csv, merged.json, config.json,
# C7_result.json, checkpoints) extracted by run_all.sh into a work directory; light parsing only.
import json, numpy as np, csv, collections
P='run1-20260930-m4096/'
import os
HERE=os.path.dirname(os.path.abspath(__file__))
B2=np.array([float(x) for x in json.load(open(os.path.join(HERE,'b2_d3_z6.json')))['B2']])   # 7 entries z^0..z^6 (b_{2,6} new)
RES=json.load(open(P+'C7_result.json'))
SECT=('free','power'); CAMP='ab'; LOOPS=range(3,8)
def coefficients(vals,N,B2=B2,C0=1.5):
    dtype=np.result_type(*[np.asarray(v).dtype for v in vals.values()]) if vals else float
    b={1:np.array([3],dtype=dtype),2:B2[:N-1].astype(dtype)};c={1:np.array([1],dtype=dtype),2:B2[:N-1].astype(dtype)/6}
    for L,a in vals.items():
        a=np.asarray(a);k=N-L;assert a.shape==(2*k,),(L,a.shape,k);b[L]=a[:k];c[L]=a[k:]
    def mul(x,y):
        v=np.convolve(x,y)[:N];return np.pad(v,(0,N-len(v)))
    g=np.zeros(N,dtype=dtype);e=g.copy();e[1]=1
    for _ in range(N):
        gp=g.copy();tmp=np.zeros(N,dtype=dtype)
        for L in range(2,N):gp=mul(gp,g);tmp+=mul(b.get(L,np.zeros(1)),gp)
        g=(e-tmp)/3
    ga=np.zeros(N,dtype=dtype);gp=ga.copy();gp[0]=1
    for L in range(1,N):gp=mul(gp,g);ga+=mul(c.get(L,np.zeros(1)),gp)
    ga[0]+=C0;ga[1]-=.5;return ga
def jac(means,N,order):
    out={}
    for L,a in means.items():
        cols=[]
        for j in range(len(a)):
            t={k:np.asarray(v,dtype=complex).copy() for k,v in means.items()};t[L][j]+=1e-20j
            cols.append(coefficients(t,N).imag[order]/1e-20)
        out[L]=np.array(cols)
    return out
def ext(v,L,top=(0.,0.)):
    k=8-L;b,c=v[:k],v[k:];return np.concatenate([b,[top[0]],c,[top[1]]])
means={s:{L:np.array(RES['means'][s][str(L)]) for L in LOOPS} for s in SECT}
m7={L:means['free'][L]+means['power'][L] for L in LOOPS}
def batches(t,s,L): return np.asarray(json.load(open(P+f'groups/{t}_{s}_L{L}/merged.json'))['batches'],float)
def graph_reps(t,s,L):
    """returns dict graph -> array (64, width)"""
    d=collections.defaultdict(dict)
    with open(P+f'groups/{t}_{s}_L{L}/graph_replicates.csv') as f:
        rd=csv.reader(f);hdr=next(rd)
        for row in rd:
            d[int(row[1])][int(row[0])]=[float(x) for x in row[2:]]
    return {g:np.array([v[r] for r in sorted(v)]) for g,v in d.items()}
def counts(t,s,L): return {int(k):v for k,v in json.load(open(P+f'groups/{t}_{s}_L{L}/config.json'))['counts'].items()}
CK=json.load(open('ckpt_agg.json'))
def graph_cost(t,s,L):
    out={}
    for key,v in CK['per_graph'].items():
        grp,g=key.split('|')
        if grp==f'{t}_{s}_L{L}': out[int(g)]=v   # samples, seconds, quad, mp, sec_amd, samp_amd
    return out
