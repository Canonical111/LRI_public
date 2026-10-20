"""Reconciler: independent tail fits + zero-intercept profile for eps^3/eps^4 descendant violations (Dconn = B's Dfull_c),
merged A (L<=72) and B (L<=76) finite-L data (they agree to <=4e-13)."""
import json, itertools
import numpy as np
base='<TMP>/scratchpad/identity/'
A=json.load(open(base+'A/analysis_table.json')); B=json.load(open(base+'B/results_table.json'))
def series(key,pres,k):
    d={}
    for Ls,av in A.items():
        if pres in av and key in av[pres]: d[int(Ls)]=av[pres][key][k]
    bmap={'Dconn':'Dfull_c','Dfull':'Dfull_raw','g2D':'g2D','raw':'raw'}
    if key in ('dphi1','dphi2'):
        for r in B:
            if r['variant']==bmap[pres] and r.get(f'{key}_e{k}') is not None and r['L']>=8:
                d.setdefault(r['L'],r[f'{key}_e{k}'])
    L=np.array(sorted(d),float); return L,np.array([d[int(l)] for l in L])
def cols(L,terms):
    x=L**-0.5; z=np.log(L)
    return np.column_stack([np.ones_like(L)]+[x**p*z**q for p,q in terms])
# terms: (power of x=L^-1/2, log power)
FAM={
 'x,x2,x3,x4':[(1,0),(2,0),(3,0),(4,0)],
 'x,xl,x2,x3,x4':[(1,0),(1,1),(2,0),(3,0),(4,0)],
 'x,xl,xl2,x2,x3':[(1,0),(1,1),(1,2),(2,0),(3,0)],
 'x,xl,xl2,x2,x2l,x3':[(1,0),(1,1),(1,2),(2,0),(2,1),(3,0)],
 'x,xl,xl2,x2,x2l,x2l2,x3':[(1,0),(1,1),(1,2),(2,0),(2,1),(2,2),(3,0)],
 'x,xl,xl2,x2,x2l,x3,x3l':[(1,0),(1,1),(1,2),(2,0),(2,1),(3,0),(3,1)],
 'x,xl,xl2,x2,x2l,x2l2,x3,x3l':[(1,0),(1,1),(1,2),(2,0),(2,1),(2,2),(3,0),(3,1)],
 'x,xl,x2,x2l,x3,x3l,x4':[(1,0),(1,1),(2,0),(2,1),(3,0),(3,1),(4,0)],
}
FLOOR=1e-12
out={}
for key,ks in (('dphi1',(3,4)),('d2phi',(3,4)),('dphi2',(4,)),('d3phi',(4,))):
  for k in ks:
    for pres in ('g2D','Dconn'):
      L,y=series(key,pres,k)
      rows=[]
      for fn,t in FAM.items():
        for lo in (16,24,32,40):
          m=L>=lo; n=m.sum(); X=cols(L[m],t)
          if n<X.shape[1]+4: continue
          c=np.linalg.lstsq(X,y[m],rcond=None)[0]; r1=np.max(abs(X@c-y[m]))
          c0=np.linalg.lstsq(X[:,1:],y[m],rcond=None)[0]; r0=np.max(abs(X[:,1:]@c0-y[m]))
          rows.append((fn,lo,int(n),c[0],r1,r0,np.linalg.cond(X/np.linalg.norm(X,axis=0))))
      good=[r for r in rows if r[4]<1e-7]
      c=np.array([r[3] for r in good]) if good else np.array([np.nan])
      print(f'\n{key} eps^{k} {pres}: L={int(L[0])}..{int(L[-1])} last={y[-1]:+.6f}; fits with maxres<1e-7: n={len(good)} intercept median {np.median(c):+.5f} range [{c.min():+.5f},{c.max():+.5f}]')
      for r in rows:
        if r[4]<1e-7 or r[1]==24:
          print(f'   {r[0]:30s} lo={r[1]:2d} n={r[2]:2d} c0={r[3]:+.5f} res={r[4]:.1e} res(c0=0)={r[5]:.1e} ratio={r[5]/max(r[4],FLOOR):9.1f} cond={r[6]:.0e}')
      out[f'{key}|e{k}|{pres}']=dict(n_good=len(good),median=float(np.median(c)),lo=float(c.min()),hi=float(c.max()),
            rows=[dict(basis=r[0],lmin=r[1],c0=r[3],res=r[4],res_zero=r[5]) for r in rows])
json.dump(out,open(base+'reconcile/desc_profile.json','w'),indent=1)
