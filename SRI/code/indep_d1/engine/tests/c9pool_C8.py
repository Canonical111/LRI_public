#!/usr/bin/env python3
"""C9[v0d0][eps^-1 l^k] pole check of validate_C8.py with the sector-pooled error of the c8chkBC (N = 1009) inputs
(2026-10-06, tiers B/C production; archive-free).  Same input order as results/validate_C8_tierBC; the c8chkBC
scalars get the pooled projection of assembly/pooled_errors.py, all other inputs their linear error.
Writes results/validate_C8_tierBC_c9pool.json.  Superseded as a check by the N = 4001 rerun (c8chkBC_N4001)."""
import sys, os, json, math
ENG='<PROJECT>/LRI_SRI_C6C7_independent/engine'
sys.path.insert(0, ENG+'/tests'); sys.path.insert(0, ENG+'/py'); sys.path.insert(0, ENG+'/../assembly')
os.chdir(ENG)
import validate_C8 as V
import pooled_errors as PE
import mpmath as mp
runs=[os.path.abspath('runs/'+r) for r in ['c8tierC_s3_topup1','c8tierC_s3_r2','c8tierC_s3_can','c8tierB_s0.01_topup1','c8tierB_s0.01_r1','c8tierB_s0.01_can','c8chkBC','c8tierA_topup1','c8tierA','c8val','c8conv','c8kplus1']]
dat, info = V.c8_input(11, runs)
NA = V.C8Assembler(dat, 11)
jobs = PE.job_sector_values('runs/c8chkBC', all_coeffs=True, tag='c8chkBC:')
chk = {nm for d in jobs.values() for sec in d['sectors'].values() for nm in sec}
print('chk scalars', sorted(chk)[:3], len(chk))
checks = [('C',9,(0,0,0),-1,k) for k in range(0,6)] + [('K',8,(1,0,0),-2,3),('K',8,(1,0,0),-2,4)]
out=[]
for X,n,mon,p,k in checks:
    def fn(asm, X=X, n=n, mon=mon, p=p, k=k):
        jj=(asm['C'] if X=='C' else asm['K'])[n].get(mon); return jj.coef(p,k)
    x=fn(NA.central); g=PE.input_gradient(x, NA.inp)
    st=NA.stats(fn)
    gchk={nm:v for nm,v in g.items() if nm in chk}; goth={nm:v for nm,v in x.g.items() if nm not in chk}
    # linear variance split (errmodel on the internal gradient)
    v_all=NA.em.variance(x.g); v_oth=NA.em.variance(goth)
    rep_chk, pool_chk, per = PE.pooled_projection(jobs, gchk)
    lin_oth=float(mp.sqrt(v_oth)); lin_chk=float(mp.sqrt(max(v_all-v_oth,0)))
    sig_pool=math.sqrt(lin_oth**2+pool_chk**2); sig_max=max(float(st['sigma']), sig_pool)
    val=float(st['value'])
    r={'check':f'{X}{n}[v{mon[0]}d{mon[1]}][eps^{p} l^{k}]','value':val,'sigma_rep':float(st.get('sigma_rep',0)),'sigma_lin':float(st['sigma_lin']),
       'lin_chk':lin_chk,'lin_other':lin_oth,'chk_rep':rep_chk,'chk_pool':pool_chk,'sigma_with_pool':sig_pool,'pull_rep':val/float(st['sigma']) if float(st['sigma']) else None,
       'pull_pool':val/sig_pool if sig_pool else None,'pull_max':val/sig_max if sig_max else None}
    out.append(r)
    print(f"{r['check']:24s} value {val:+.3e} sigma(rep/lin) {float(st['sigma']):.2e} [lin: chk {lin_chk:.2e} other {lin_oth:.2e}] chk rep {rep_chk:.2e} pool {pool_chk:.2e} -> sigma(pool) {sig_pool:.2e}; pull rep {r['pull_rep']:+.2f} pool {r['pull_pool']:+.2f} max {r['pull_max']:+.2f}")
json.dump(out, open(ENG+'/results/validate_C8_tierBC_c9pool.json','w'), indent=1)
