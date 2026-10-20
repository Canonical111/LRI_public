import numpy as np, json, glob, itertools
def load():
    files=glob.glob('big_L*.json')
    R={}
    for f in files:
        d=json.load(open(f)); R[d['L']]=d
    return dict(sorted(R.items()))
def basis_cols(L, model):
    """model: list of (power, logpow) tail terms; constant always included."""
    l=np.log(L)
    cols=[np.ones_like(L)]
    for (p,q) in model:
        cols.append(L**(-p)*l**q)
    return np.array(cols).T
def fit(L,y,model,Lmin,Lmax=None):
    m=(L>=Lmin)&((L<=Lmax) if Lmax else True)
    A=basis_cols(L[m],model); c,res,rk,sv=np.linalg.lstsq(A,y[m],rcond=None)
    pred=basis_cols(L,model)@c
    return c, np.max(np.abs(pred[m]-y[m])), m.sum()
MODELS={
 'h':[(0.5,0)],
 'h,1':[(0.5,0),(1,0)],
 'h,1,3h':[(0.5,0),(1,0),(1.5,0)],
 'hl,h':[(0.5,0),(0.5,1)],
 'hl,h,1':[(0.5,0),(0.5,1),(1,0)],
 'hl,h,1,1l':[(0.5,0),(0.5,1),(1,0),(1,1)],
 'hl2,hl,h':[(0.5,0),(0.5,1),(0.5,2)],
 'hl2,hl,h,1':[(0.5,0),(0.5,1),(0.5,2),(1,0)],
 'hl2,hl,h,1,1l':[(0.5,0),(0.5,1),(0.5,2),(1,0),(1,1)],
 'hl2,hl,h,1,1l,1l2':[(0.5,0),(0.5,1),(0.5,2),(1,0),(1,1),(1,2)],
 'l,1':[(1,0)],
 '1,1l':[(1,0),(1,1)],
 '1,1l,2':[(1,0),(1,1),(2,0)],
 '1,3h':[(1,0),(1.5,0)],
 '1,3h,2':[(1,0),(1.5,0),(2,0)],
}
