"""Reconciler refit: campaign thermal C4(L) + exact dC4_g2D(L) + Dconn top-shell shift(L), with the 18 tail variants of
explore_lower_edge.py (post hoc) and the pre-registered bases; plus the calibration check (exact C4 imposed).
Read-only use of the campaign code (no bytecode written)."""
import sys, json, math, glob
sys.dont_write_bytecode = True
import numpy as np
EXT='<PROJECT>/lri_hpc_Hamitonian/analysis/extended'
AN='<PROJECT>/lri_hpc_Hamitonian/analysis'
sys.path.insert(0, EXT); sys.path.insert(0, AN)
import analyze_joint
from analyze_joint import MODELS, load
from diagnose_systematic import thermal_fit, const_terms
sys.path.insert(0,'<PROJECT>/lri_eh_hpc/lri_eh')
from exact import fast
base='<TMP>/scratchpad/identity/'
EX4=45.42488010356
th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'][:5] for r in th])
ex = json.load(open(EXT+'/extended_summary.json'))
w_ext = {int(k): v for k, v in ex['gap_reference']['extended'].items()}
w_orig = {int(k): v for k, v in ex['gap_reference']['original'].items()}
# exact Dconn shift: B topshell/shift_all (L<=96), else from A raw shift minus H_odd(L-1)/8748, else 5-term fit
sh = {}
d=json.load(open(base+'B/shift_all.json'))
for l,s in zip(d['L'],d['shift']): sh[int(l)]=s
for f in glob.glob(base+'A/c4shift_*.json'):
    for k,v in json.load(open(f)).items():
        l=int(k); Hodd=math.fsum(1/e for e in range(1,l,2))
        val=v['dC4']-Hodd/8748
        if l in sh: assert abs(sh[l]-val)<1e-13,(l,sh[l],val)
        sh[l]=val
Ls=np.array(sorted(sh),float); S=np.array([sh[int(l)] for l in Ls])
m=Ls>=24
TT=[(1,0),(1,1),(1.5,0),(2,0),(2,1),(2.5,0),(3,0)]
X=lambda l: np.column_stack([np.ones_like(l)]+[l**-p*np.log(l)**q for p,q in TT])
cf=np.linalg.lstsq(X(Ls[m]),S[m],rcond=None)[0]
print('shift fit c0=%.10f, max resid %.1e (L>=24, %d pts, Lmax %d)'%(cf[0],np.max(abs(X(Ls[m])@cf-S[m])),m.sum(),Ls.max()))
shift=np.array([sh[int(l)] if int(l) in sh else float(X(np.array([l]))@cf) for l in L])
dg2=np.array([fast(int(l)) for l in L])
data={'raw':C.copy(),'g2D':C.copy(),'Dconn':C.copy()}
data['g2D'][:,4]+=dg2; data['Dconn'][:,4]+=dg2+shift
variants = {name: (const_terms(name), w_ext, False) for name in MODELS if name!='minimal'}
for name in ('A','B','D'):
    variants[f'{name}+free_exp'] = (const_terms(name), w_ext, True)
    variants[f'{name} gap=orig'] = (const_terms(name), w_orig, False)
for name in ('A','D'):
    variants[f'{name}+z^j/L'] = (lambda k, n=name: MODELS[n] + [(1, j) for j in range(1, k - 1) if (1, j) not in MODELS[n]], w_ext, False)
    variants[f'{name}+z^j/L^1.5'] = (lambda k, n=name: MODELS[n] + [(1.5, j) for j in range(2, k - 1) if (1.5, j) not in MODELS[n]], w_ext, False)
    variants[f'{name}+L^-0.75'] = (lambda k, n=name: MODELS[n] + [(0.75, 0)], w_ext, False)
rows=[]
for lo in (40,50,60,70):
    mm=(L>=lo)
    for lab,(tk,w,free) in variants.items():
        r=dict(lo=lo,variant=lab)
        for key,CC in data.items():
            lim,diag=thermal_fit(L[mm],CC[mm],w,tk,free_exponents=free,maxorder=4)
            limi,diagi=thermal_fit(L[mm],CC[mm],w,tk,free_exponents=free,maxorder=4,fixed={4:EX4})
            r[key]=lim[4]; r[key+'_res']=diag[4]['max_residual']; r[key+'_resfix']=diagi[4]['max_residual']; r['cond']=diag[4]['condition']
        rows.append(r)
print(f"{'lo':>3} {'variant':16s} {'raw':>10s} {'+g2D':>10s} {'+g2D+Dconn':>11s} {'miss':>8s} | res free  res(C4 fixed): raw  g2D  Dconn | ratio Dconn | cond")
for r in rows:
    print(f"{r['lo']:3d} {r['variant']:16s} {r['raw']:.5f} {r['g2D']:.5f} {r['Dconn']:.6f} {r['Dconn']-EX4:+.5f} | {r['Dconn_res']:.1e}  {r['raw_resfix']:.1e} {r['g2D_resfix']:.1e} {r['Dconn_resfix']:.1e} | {r['Dconn_resfix']/r['Dconn_res']:7.1f} {r['raw_resfix']/r['raw_res']:7.1f} | {r['cond']:.0e}")
for lo in (40,50,60,70):
    sel=[r for r in rows if r['lo']==lo]
    well=[r for r in sel if r['Dconn_res']<1e-8]
    print(lo,'all: miss %+.4f..%+.4f'%(min(r['Dconn'] for r in sel)-EX4,max(r['Dconn'] for r in sel)-EX4),
          ' well(res<1e-8, n=%d): %+.4f..%+.4f'%(len(well),min(r['Dconn'] for r in well)-EX4,max(r['Dconn'] for r in well)-EX4) if well else '',
          ' intercept shift Dconn-g2D: %.6f..%.6f'%(min(r['Dconn']-r['g2D'] for r in sel),max(r['Dconn']-r['g2D'] for r in sel)))
json.dump(rows,open(base+'reconcile/refit_corrected.json','w'),indent=1)
