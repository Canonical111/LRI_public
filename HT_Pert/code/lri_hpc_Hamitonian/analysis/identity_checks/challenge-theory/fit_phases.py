"""Fixed-phase extrapolation of the eps^4 dphi identity v4 = [E(dphi)-E(phi)-1]_eps^4 (Dconn and raw)
at Lam = L + delta, and the level-local inversion (R_0, R_1/2, R_1, R_3/2) incl. retune terms:
 delta=0   : a0 = R_3/2 + R_1 + R_0/2      (A+B data, even L <= 76)
 delta=1/4 : a1 = R_0 + R_3/2              (= -3 * extra C4 residual at delta=0)
 delta=3/4 : a3 = R_1/2 + R_0
 delta=5/4 : a5 = R_1 + R_1/2
"""
import json, numpy as np, itertools
base='<TMP>/scratchpad/identity/'
here=base+'challenge-theory/'
def series_phase(ph, sch, k=4):
    d=json.load(open(here+f'offset_ph{ph}.json'))
    L=np.array([o['Lam'] for o in d])-float(ph); y=np.array([o[sch]['v_dphi'][k] for o in d])
    return L,y
def series_zero(sch,k=4):
    A=json.load(open(base+'A/analysis_table.json')); B=json.load(open(base+'B/results_table.json'))
    pres={'corr':'Dconn','raw':'raw'}[sch]; bmap={'Dconn':'Dfull_c','raw':'raw'}
    dd={int(Ls):av[pres]['dphi1'][k] for Ls,av in A.items()}
    for r in B:
        if r['variant']==bmap[pres] and r.get(f'dphi1_e{k}') is not None and r['L']>=8: dd.setdefault(r['L'],r[f'dphi1_e{k}'])
    L=np.array(sorted(dd),float); return L,np.array([dd[int(l)] for l in L])
FAM={
 'A:x,x2,x3':[(1,0),(2,0),(3,0)],
 'A:x,x2,x3,x4':[(1,0),(2,0),(3,0),(4,0)],
 'A:x,xl,x2,x3':[(1,0),(1,1),(2,0),(3,0)],
 'A:x,x2,x2l,x3':[(1,0),(2,0),(2,1),(3,0)],
 'R:x,xl,x2,x3,x4':[(1,0),(1,1),(2,0),(3,0),(4,0)],
 'R:x,xl,xl2,x2,x3':[(1,0),(1,1),(1,2),(2,0),(3,0)],
 'R:x,xl,xl2,x2,x2l,x3':[(1,0),(1,1),(1,2),(2,0),(2,1),(3,0)],
 'R:x,xl,xl2,x2,x2l,x2l2,x3':[(1,0),(1,1),(1,2),(2,0),(2,1),(2,2),(3,0)],
 'R:x,xl,xl2,x2,x2l,x3,x3l':[(1,0),(1,1),(1,2),(2,0),(2,1),(3,0),(3,1)],
 'R:x,xl,x2,x2l,x3,x3l,x4':[(1,0),(1,1),(2,0),(2,1),(3,0),(3,1),(4,0)],
}
def cols(L,t):
    x=L**-0.5; z=np.log(L); return np.column_stack([np.ones_like(L)]+[x**p*z**q for p,q in t])
def fitall(L,y,lmins=(16,24,32,40)):
    rows=[]
    for fn,t in FAM.items():
        for lo in lmins:
            m=L>=lo; X=cols(L[m],t)
            if m.sum()<X.shape[1]+4: continue
            c=np.linalg.lstsq(X,y[m],rcond=None)[0]; rows.append((fn,lo,int(m.sum()),float(c[0]),float(np.max(abs(X@c-y[m])))))
    return rows
out={}
for tag,(L,y) in {'d0':series_zero('corr'),'d1/4':series_phase('0.25','corr'),'d3/4':series_phase('0.75','corr'),'d5/4':series_phase('1.25','corr'),
                  'd0raw':series_zero('raw'),'d1/4raw':series_phase('0.25','raw'),'d3/4raw':series_phase('0.75','raw'),'d5/4raw':series_phase('1.25','raw')}.items():
    rows=fitall(L,y); good=[r for r in rows if r[4]<1e-7]
    cA=np.array([r[3] for r in rows if r[0].startswith('A:')]); cg=np.array([r[3] for r in good])
    simple=np.array([r[3] for r in rows if r[0].startswith('A:') and r[1] in (24,32)])
    out[tag]=dict(Lmax=float(L[-1]),last=float(y[-1]),simple_med=float(np.median(simple)),simple_lo=float(simple.min()),simple_hi=float(simple.max()),
                 good_n=len(good),good_med=float(np.median(cg)) if len(cg) else None,good_lo=float(cg.min()) if len(cg) else None,good_hi=float(cg.max()) if len(cg) else None,
                 rows=rows)
    print(f'{tag:8s} L<={L[-1]:.0f} last {y[-1]:+.5f} | simple(A-type, lo 24/32) med {np.median(simple):+.5f} [{simple.min():+.5f},{simple.max():+.5f}] | log-rich res<1e-7 n={len(good)} med {np.median(cg) if len(cg) else np.nan:+.5f} [{cg.min() if len(cg) else np.nan:+.5f},{cg.max() if len(cg) else np.nan:+.5f}]')
    for r in rows:
        if r[1] in (24,32): print(f'     {r[0]:30s} lo={r[1]} n={r[2]} c0={r[3]:+.5f} res={r[4]:.1e}')
json.dump(out,open(here+'fit_phases.json','w'),indent=1)
