"""Large-L forms of the reconciled Delta C5 and its pieces (L<=152; L>118 from B's table)."""
import json, numpy as np, mpmath as mp
R='<TMP>/scratchpad/eps5/reconcile'
T={int(k):v for k,v in json.load(open(R+'/dC_reconciled.json')).items()}
K=0.06161193084267987; a=1/17496
cols={'1':lambda L:L**0,'lg':np.log,'x':lambda L:L**-.5,'xl':lambda L:L**-.5*np.log(L),'xl2':lambda L:L**-.5*np.log(L)**2,
      '1/L':lambda L:1/L,'lg/L':lambda L:np.log(L)/L,'lg2/L':lambda L:np.log(L)**2/L,'x3':lambda L:L**-1.5,'x3l':lambda L:L**-1.5*np.log(L),'1/L2':lambda L:L**-2.,'lg/L2':lambda L:np.log(L)/L**2,'x5':lambda L:L**-2.5,'1/L3':lambda L:L**-3.}
def fit(L,y,terms,fixed_log=None):
    yy=y-(fixed_log*np.log(L) if fixed_log is not None else 0)
    X=np.column_stack([cols[t](L) for t in terms]); s=np.linalg.norm(X,axis=0)
    p=np.linalg.lstsq(X/s,yy,rcond=None)[0]/s
    return p, float(np.max(np.abs(X@p-yy)))
bases_log={'L1':['1','lg','x','1/L','lg/L','x3','1/L2'],'L2':['1','lg','x','xl','1/L','lg/L','x3'],'L3':['1','lg','1/L','lg/L','1/L2','lg/L2','1/L3'],
           'L4':['1','lg','x','1/L','lg/L','lg2/L','x3','1/L2']}
bases_nolog={'N1':['1','x','1/L','lg/L','x3','1/L2','x5'],'N2':['1','x','xl','1/L','lg/L','x3','1/L2'],'N3':['1','1/L','lg/L','lg2/L','1/L2','lg/L2','1/L3'],
             'N4':['1','x','xl','xl2','1/L','lg/L','x3']}
def run(name,key,Lmin_list=(24,40,56),Lmax=152,fixed=None,src=None):
    Ls=np.array(sorted(l for l in T if l<=Lmax and l>=8 and T[l].get(key) is not None),float)
    y=np.array([T[int(l)][key] for l in Ls])
    print(f'--- {name} ({key}), L<={int(Ls.max())}')
    for grp,bs in (('free log',bases_log),('no log',bases_nolog)):
        rs=[]
        for bn,b in bs.items():
            for lmin in Lmin_list:
                m=Ls>=lmin
                p,r=fit(Ls[m],y[m],b)
                rs.append((bn,lmin,p[0],p[1] if b[1]=='lg' else 0.,r))
        c=[x[2] for x in rs if x[4]<1e-9] or [x[2] for x in rs]
        lg=[x[3] for x in rs if x[4]<1e-9] or [x[3] for x in rs]
        print(f'   {grp:8s}: c0 {min(c):.6f}..{max(c):.6f}  log {min(lg):+.3e}..{max(lg):+.3e}  (n={len(c)}, max res of these {max(x[4] for x in rs):.1e})')
    if fixed is not None:
        rs=[]
        for bn,b in bases_nolog.items():
            for lmin in Lmin_list:
                m=Ls>=lmin; p,r=fit(Ls[m],y[m],b,fixed_log=fixed); rs.append((p[0],r))
        print(f'   log fixed {fixed:.4e}: c0 {min(x[0] for x in rs):.6f}..{max(x[0] for x in rs):.6f} (max res {max(x[1] for x in rs):.1e})')
run('g2D package','dC5_g2D',fixed=5.5388e-4)
run('rows4','dC5_rows4')
run('rows5 = -B5/3','dC5_rows5')
run('complete Delta C5','dC5_Dconn',fixed=5.5388e-4-2*a)
run('complete Delta C4','dC4_Dconn',fixed=a)
print('bubble exact limit: -2K - 2 logL/17496 =', -2*K, ' log coef', -2*a)
