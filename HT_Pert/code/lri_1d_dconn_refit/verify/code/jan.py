import pickle, numpy as np
REF={4:45.42488010356,5:-731.13947662454,6:14331.68703277,7:-322550.0,8:8066723.0}
S92={4:7e-13,5:9e-12,6:8e-11,7:8e-10,8:1.5e-8}; S118={4:1e-12,5:1e-11,6:1e-10,7:1.1e-9}
def ld(kind):
    A=pickle.load(open('../out/scan_%s.pkl'%kind,'rb')); B=pickle.load(open('../out/scan_%s_w.pkl'%kind,'rb'))
    T={k:np.concatenate([A[k],B[k]]) for k in A if k in B}
    N=len(T['kind'])
    r118=((T['kind']=='o7')&(T['hi']>=104))|((T['kind']=='o8')&(T['low']=='th118'))
    for n in range(4,9):
        if 'C%d'%n not in T: continue
        T['dof%d'%n]=T['npts%d'%n]-T['ncol%d'%n]
        sig=np.full(N,S92[n]) if n==8 else np.where(r118,S118[n],S92[n])
        with np.errstate(all='ignore'):
            T['flw%d'%n]=T['erms%d'%n]*np.sqrt(T['npts%d'%n]/T['dof%d'%n])/sig
            T['flp%d'%n]=T['rms%d'%n]*np.sqrt(T['npts%d'%n]/T['dof%d'%n])/sig
        T['miss%d'%n]=T['C%d'%n]-REF[n]
    return T
def s(x):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)==0: return 'n=0'
    return 'n=%d med %.6g [16-84 %.6g, %.6g]'%(len(x),np.median(x),np.percentile(x,16),np.percentile(x,84))
