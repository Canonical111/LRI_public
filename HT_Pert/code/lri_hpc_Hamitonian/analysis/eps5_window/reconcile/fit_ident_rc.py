"""Reconciler's own extrapolation of the eps^5 (and eps^4) descendant identities from the union A+B data.
Tails in x = L^-1/2 with log^j L factors; families a-g; Lmin in {16,20,24,32}; Lmax = all data of that phase."""
import json, numpy as np, itertools
R='<TMP>/scratchpad/eps5/reconcile'
D={float(k):v for k,v in json.load(open(R+'/ident_union.json')).items()}
F={'a':['1','x','x2','x3','x4'],'b':['1','x','xl','x2','x3'],'c':['1','x','xl','x2','x2l','x3'],
   'd':['1','x','xl','xl2','x2','x3'],'e':['1','x','xl','xl2','x2','x2l'],'g':['1','x','x2','x2l','x3','x4'],
   'f_rich':['1','x','xl','xl2','xl3','x2','x2l']}
def col(n,L):
    x=L**-.5; l=np.log(L)
    return {'1':np.ones_like(L),'x':x,'xl':x*l,'xl2':x*l*l,'xl3':x*l**3,'x2':x*x,'x2l':x*x*l,'x3':x**3,'x4':x**4}[n]
def fit(L,y,fam):
    X=np.column_stack([col(n,L) for n in F[fam]]); s=np.linalg.norm(X,axis=0)
    p=np.linalg.lstsq(X/s,y,rcond=None)[0]/s
    return p[0], float(np.max(np.abs(X@p-y)))
out={}
for ph in (0.0,0.25,0.75):
    Ls=np.array(sorted(l for l in D if abs(l%2-ph)<1e-9 and l>=8))
    for var in ('raw','g2D','g2D3W','Dconn','Dfull'):
        for q in ('v_dphi1','v_d2phi','v_d3phi'):
            for k in (4,5):
                LL=np.array([l for l in Ls if q in D[l][var]])
                y=np.array([D[l][var][q][k] for l in LL])
                res=[]
                for fam in F:
                    for lmin in (16,20,24,32):
                        m=LL>=lmin
                        if m.sum()<len(F[fam])+3: continue
                        c0,r=fit(LL[m],y[m],fam); res.append((fam,lmin,c0,r))
                vals=np.array([r[2] for r in res]); simple=np.array([r[2] for r in res if r[0]!='f_rich'])
                out[(ph,var,q,k)]=dict(median=float(np.median(simple)),lo=float(simple.min()),hi=float(simple.max()),
                                      rich_lo=float(vals.min()),rich_hi=float(vals.max()),Lmax=float(LL.max()),last=float(y[-1]),n=len(res))
json.dump({'|'.join(map(str,k)):v for k,v in out.items()},open(R+'/fit_ident_rc.json','w'),indent=1)
for ph in (0.0,0.25,0.75):
    print(f'=== phase {ph}')
    for q in ('v_dphi1','v_d2phi','v_d3phi'):
        for k in (4,5):
            s=f'{q:8s} eps{k}: '
            for var in ('raw','g2D','g2D3W','Dconn','Dfull'):
                o=out[(ph,var,q,k)]
                s+=f"{var} {o['median']:+.3f}[{o['lo']:+.3f},{o['hi']:+.3f}] "
            o=out[(ph,'Dconn',q,k)]
            print(s+f"| Dconn rich [{o['rich_lo']:+.3f},{o['rich_hi']:+.3f}] last(L={o['Lmax']:g})={o['last']:+.4f}")
