#!/usr/bin/env python3
"""FIT_PLAN.md §5.0–5.1 unit and integration checks for the v2 protocol (synthetic data only).

(1)  nonlinear field: field order 2 with a1 = 0 reproduces the order-1 design/chi2/Delta_eps; synthetic (Delta_eps, omega, a1)
     are recovered.
(0a) calibrated residual gate: rejects sign-alternating / monotone pull patterns, accepts >= 97 % of fully refitted
     independent null datasets.
(0a') common-valid mask uses existence/convergence only: through crosscheck_series and paired_comparison, a draw whose
     extrapolation chi2 exceeds the central cutoff stays valid, and a draw invalid for one member of E is excluded for all.
(0b) the shared schedule gives identical resampled observables through BOTH production resampling paths
     (fit_fss.resample_data and quotients.resample_entries) on a synthetic summary directory with block archives; an
     unscheduled run differs; a bootstrap refit exception invalidates only its draw.
(0c) the crossing extrapolation recovers synthetic (Delta_inf, c_U, c_Y, omega'), flags omega' at a bound and rejects a
     singular covariance.
"""
import json,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import fit_fss,quotients,select_model as sm
from bootstrap_schedule import block_indices

def synthetic_entries(a1=0.,seed=5,noise=1.,sizes=(4096,8192,16384,32768,65536,131072),betas=(.4735,.4742,.4749,.4756,.4763)):
    rng=np.random.default_rng(seed);entries=[]
    scales=np.array([.002,.02,.6,.001,.012,.4])
    for n in sizes:
        for b in betas:entries.append(dict(N=n,s=.875,beta=b,data=[1]*6,cov=np.diag(scales**2).tolist()))
    m=fit_fss.ProfileFit(entries,degree=3,field_order=2);p=np.array([.4,.59,.45,a1])   # k=0.4 -> beta_c = ref + 0.004
    amp=np.array([1.2,.34,.08,-.04,-.16,.03,-.02, .44,.10,-.03,.01,.04,-.02,.015])
    exact=m.design(p)@amp
    for e,v in zip(entries,exact):e['data']=(v+noise*scales*rng.standard_normal(6)).tolist()
    return entries,p,amp

def check_field_order():
    entries,p,amp=synthetic_entries(a1=0.,noise=0.)
    m1=fit_fss.ProfileFit(entries,degree=3,field_order=1);m2=fit_fss.ProfileFit(entries,degree=3,field_order=2)
    assert np.allclose(m1.design(p[:3]),m2.design(np.r_[p[:3],0.]),rtol=0,atol=1e-12),'field-order-2 design with a1=0 differs from order 1'
    f1=m1.fit();f2=m2.fit(initial=np.r_[f1['parameters'],0.],multistart=False)
    assert abs(f1['Delta_epsilon']-f2['Delta_epsilon'])<1e-8 and abs(f1['chi2']-f2['chi2'])<1e-8,(f1['Delta_epsilon'],f2['Delta_epsilon'])
    entries,p,amp=synthetic_entries(a1=-8.,noise=0.)
    f=fit_fss.ProfileFit(entries,degree=3,field_order=2).fit()
    assert abs(f['Delta_epsilon']-p[1])<2e-6 and abs(f['omega_correction']-p[2])<2e-5 and abs(f['field_coefficients'][0]-p[3])<1e-3,(f['parameters'],f['flags'])
    return dict(field_order_identity=True,recovered=f['parameters'])

def check_residual_gate():
    entries,p,amp=synthetic_entries(noise=1.,seed=11)
    m=fit_fss.ProfileFit(entries,degree=3);f=m.fit();pred=np.array(f['predictions']);p0=np.array(f['parameters'])
    rng=np.random.default_rng(3);null=[]
    for _ in range(400):
        g=m.fit(pred+m.colour(rng.standard_normal(pred.size)),initial=p0,multistart=False)
        if g['success'] and not g['flags']:null.append(sm.residual_stats(g['pulls'])[:2])
    null=np.array(null);Tq=np.quantile(null[:,0],.01);Rq=np.quantile(null[:,1],.99)
    rng2=np.random.default_rng(99);acc=0;n=300
    for _ in range(n):
        g=m.fit(pred+m.colour(rng2.standard_normal(pred.size)),initial=p0,multistart=False)
        T,R,_=sm.residual_stats(g['pulls']);acc+=int(not(T<Tq or R>Rq))
    frac=acc/n;assert frac>=.97,f'null acceptance {frac}'
    rows=sorted(f['pulls'],key=lambda d:(d['N'],d['beta']));mag=np.abs([d['pull'] for d in rows])
    alt=[dict(N=d['N'],beta=d['beta'],pull=(mag[i]*(1 if i%2 else -1)).tolist()) for i,d in enumerate(rows)]
    mono=[dict(N=d['N'],beta=d['beta'],pull=(mag[i]*(1 if i<len(rows)//2 else -1)).tolist()) for i,d in enumerate(rows)]
    for name,rr in (('alternating',alt),('monotone',mono)):
        T,R,_=sm.residual_stats(rr);assert T<Tq or R>Rq,f'{name} pattern not rejected (T={T}, R={R}, Tq={Tq}, Rq={Rq})'
    # stable, hash()-free calibration seeds
    assert sm.calibration_seed(20260916,.875,3,2)==[20260916,875000,3,2]
    return dict(null_acceptance=frac,T_q01=float(Tq),R_q99=float(Rq))

def synthetic_crossings(nd=40,seed=2,truth=dict(Delta_inf=.59,c_U=.8,c_Y=-1.1,omega=.5),sig=2e-3):
    """A quotients-like result and samples array for the four largest pairs plus one smaller pair."""
    rng=np.random.default_rng(seed);pairs=[16384]+sm.XCHECK_PAIRS;rows=[];samples=np.full((nd,2*len(pairs),3),np.nan)
    for j,N in enumerate(pairs):
        dU=truth['Delta_inf']+truth['c_U']*N**(-truth['omega']);dY=truth['Delta_inf']+truth['c_Y']*N**(-truth['omega'])
        for which,name in enumerate('YU'):
            rows.append(dict(N=N,N2=2*N,crossing_observable=name,beta_crossing=.4749,Delta_epsilon_eff_from_Y=dY,Delta_epsilon_eff_from_U=dU))
            samples[:,2*j+which,0]=.4749+1e-5*rng.standard_normal(nd)
            samples[:,2*j+which,1]=dY+sig*rng.standard_normal(nd);samples[:,2*j+which,2]=dU+sig*rng.standard_normal(nd)
    diag={str(N):dict(chi2=8.,dof=8) for N in pairs+[2*pairs[-1]]}
    return dict(crossings=rows,local_fit_diagnostics=diag,warnings=[]),samples

def check_common_valid_mask():
    """Production path: crosscheck_series + paired_comparison. Draw 5 gets a large deviation in one series (its per-draw
    extrapolation chi2 is far above the central cutoff but converges -> must stay valid, FIT-010); draw 7 gets a NaN root
    in series B only -> excluded from the common-valid set of everyone (FIT-007)."""
    qrA,sA=synthetic_crossings(seed=2);qrB,sB=synthetic_crossings(seed=3)
    iU=[i for i,r in enumerate(qrA['crossings']) if r['N']==sm.XCHECK_PAIRS[0] and r['crossing_observable']=='U'][0]
    sA[5,iU,2]+=0.05                       # chi2 of draw 5 in A >> 2*dof, yet a finite unique minimum exists
    sB[7,iU,1]=np.nan                      # draw 7 invalid for B only
    A=sm.crosscheck_series(qrA,sA);B=sm.crosscheck_series(qrB,sB)
    assert A['eligible'] and B['eligible'],(A.get('reason'),B.get('reason'))
    g5=sm.gls_extrapolate(np.concatenate([sA[5,A['row_indices'],2],sA[5,A['row_indices'],1]]),np.array(A['covariance']),np.array(sm.XCHECK_PAIRS*2,float),np.array([0]*4+[1]*4))
    assert g5['chi2']/g5['dof']>sm.XCHECK_CHI2_DOF_MAX and A['draw_converged'][5],('draw 5 must stay valid despite chi2',g5['chi2'],A['draw_converged'][5])
    assert not B['draw_valid'][7] and not B['draw_converged'][7]
    nd=sA.shape[0];qdraws=[dict(draw=k,success=True,flags=[],Delta_epsilon=.5905+1e-3*np.sin(k)) for k in range(nd)]
    qdraws[9]['flags']=['optimizer did not converge']          # global fit invalid on draw 9
    X=sm.paired_comparison({'A':A,'B':B},['A','B'],qdraws,nd,.5905)
    m=np.array(X['common_valid_mask']);assert m[5] and not m[7] and not m[9] and m.sum()==nd-2,(m.sum(),m[5],m[7],m[9])
    assert X['status'] in ('pass','CROSS-CHECK FAILED (|difference| > 2 sigma_D)') and len(X['paired_differences'])==nd-2
    X1=sm.paired_comparison({'A':A},['A'],qdraws,nd,.5905);assert 'UNAVAILABLE' in X1['status']
    return dict(common_valid=int(m.sum()),status=X['status'],Delta_inf=X['Delta_inf_central'])

def check_schedule():
    """Both production resampling paths on a synthetic summary directory with block archives."""
    a=block_indices(20260916,.875,4096,.4749,3,17,55);b=block_indices(20260916,.875,4096,.4749,3,17,55)
    assert np.array_equal(a,b) and a.min()>=0 and a.max()<55
    assert not np.array_equal(a,block_indices(20260916,.875,4096,.4749,3,18,55)),'different draws must differ'
    assert not np.array_equal(a,block_indices(20260916,.875,4096,.4749,4,17,55)),'different replicas must differ'
    with tempfile.TemporaryDirectory(prefix='lri-v2-') as tmp:
        tmp=Path(tmp);rng=np.random.default_rng(0);entries=[]
        for i,(N,beta) in enumerate([(4096,.4742),(4096,.4749),(8192,.4742),(8192,.4749)]):
            nb=[30,34];blocks=np.concatenate([np.abs(rng.standard_normal((n,4,3)))+np.array([[.2,.05,.02]]*4) for n in nb])
            reps=np.concatenate([np.full(n,r) for r,n in enumerate(nb)])
            np.savez(tmp/f'blocks_{i}.npz',blocks=blocks,replicas=reps)
            entries.append(dict(s=.875,N=N,beta=beta,beta_simulated=beta,blocks_file=f'blocks_{i}.npz',data=[1]*6,cov=np.eye(6).tolist()))
        (tmp/'summary.json').write_text(json.dumps(dict(entries=entries)))
        src_fit=fit_fss.load_sources(tmp/'summary.json',entries)
        src_q=[]
        for e in entries:
            with np.load(tmp/e['blocks_file']) as z:src_q.append([(int(r),z['blocks'][z['replicas']==r]) for r in np.unique(z['replicas'])])
        for k in (0,1,17):
            v1=fit_fss.resample_data(entries,src_fit,np.random.default_rng(1),20260916,k)
            v2=quotients.resample_entries(entries,src_q,k,np.random.default_rng(2),20260916)
            assert np.array_equal(v1,v2),f'scheduled resamples differ on draw {k}'
        u1=fit_fss.resample_data(entries,src_fit,np.random.default_rng(1),None,0);u2=quotients.resample_entries(entries,src_q,0,np.random.default_rng(2),None)
        assert not np.array_equal(u1,u2),'unscheduled resamples should not coincide'
        # a refit exception invalidates only its draw (FITV2-007)
        class Boom:
            def __init__(self):self.calls=0
            def __call__(self,*a,**k):
                self.calls+=1
                if self.calls==2:raise np.linalg.LinAlgError('synthetic failure')
                return dict(Delta_epsilon=.59,beta_c=.4749,omega_correction=.4,flags=[],success=True,parameters=[0,.59,.4])
        boom=Boom();orig=fit_fss.ProfileFit.fit
        entries2,_,_=synthetic_entries(noise=1.,seed=4)
        try:
            fit_fss.ProfileFit.fit=lambda self,*a,**k:boom(*a,**k)
            src=[[(0,np.abs(np.random.default_rng(i).standard_normal((12,4,3)))+.1)] for i in range(len(entries2))]
            fit_fss.load_sources=lambda summary,ent:src
            r=fit_fss.run_fit(tmp/'summary.json',entries2,3,bootstrap=4,schedule=20260916)
        finally:fit_fss.ProfileFit.fit=orig
        d=r['bootstrap']['draws'];assert len(d)==4 and not d[0]['success'] and d[0]['flags'][0].startswith('refit exception') and all(x['success'] for x in d[1:]),d
        assert r['bootstrap']['valid']==3
        # crossing bootstrap: a numerical failure of one size on one draw only NaNs that draw's affected rows (FITV2-012)
        entries3=[];rng3=np.random.default_rng(7)
        for i,N in enumerate([1024,2048,4096]):
            for beta in (.4742,.4749,.4756):
                nb=[16,16];blocks=np.abs(rng3.standard_normal((sum(nb),4,3)))+np.array([[.2,.05,.02]]*4)
                fn=f'blk_{N}_{beta}.npz';np.savez(tmp/fn,blocks=blocks,replicas=np.concatenate([np.full(n,r) for r,n in enumerate(nb)]))
                entries3.append(dict(s=.875,N=N,beta=beta,beta_simulated=beta,blocks_file=fn,data=[1]*6,cov=np.eye(6).tolist()))
        # data with exact size-doubling crossings at beta_c = 0.4749 (linear in beta, slopes growing as (N/1024)^0.4)
        for e in entries3:
            r=(e['N']/1024)**.4;v=e['beta']-.4749
            e['data']=[.3+20*r*v,20*r,0.,.6+10*r*v,10*r,0.];e['cov']=np.diag([1e-8]*6).tolist()
        orig_fit=quotients.LocalCurve.fit;state={'k':0}
        def flaky(self,data=None):
            if data is not None and state['k']==1 and self.n==2048:raise np.linalg.LinAlgError('synthetic failure')
            return orig_fit(self,data)
        orig_res=quotients.resample_entries
        def counting(entries,sources,k,rng,schedule=None):
            # the resampling path itself is checked above; here the process() loop is driven with central data + tiny noise
            state['k']=k;return np.array([e['data'] for e in entries])+1e-6*np.random.default_rng(k).standard_normal((len(entries),6))
        try:
            quotients.LocalCurve.fit=flaky;quotients.resample_entries=counting
            r,smp=quotients.process(entries3,tmp,2,3,np.random.default_rng(0),20260916)
        finally:quotients.LocalCurve.fit=orig_fit;quotients.resample_entries=orig_res
        assert r['bootstrap_draw_failure_count']==1 and 'draw 1 N=2048' in r['bootstrap_draw_failures'][0],r['bootstrap_draw_failures']
        rows=r['crossings'];assert rows,'no crossings in the synthetic set'
        for j,row in enumerate(rows):
            uses2048=row['N']==2048 or row['N2']==2048
            assert np.all(np.isnan(smp[1,j]))==uses2048,(row,smp[1,j])
            assert np.all(np.isfinite(smp[0,j])) and np.all(np.isfinite(smp[2,j])),(row,smp[:,j])
    return dict(schedule_identity=True,exception_isolated=True,crossing_failure_isolated=True)

def check_reblock_validation():
    """FITV2-001/010/011: reblock inputs must carry their block size in BOTH summaries with c3 entries identical to the
    full-window ones; a copied block-4096 summary_c3.json is rejected."""
    with tempfile.TemporaryDirectory(prefix='lri-v2-rb-') as tmp:
        tmp=Path(tmp)
        betas=[.4735,.4742,.4749,.4756,.4763]
        def mk(name,bs,c3_bs=None,c3_data_shift=0.):
            d=tmp/name;d.mkdir();ents=[]
            for N in (4096,8192):
                for i,beta in enumerate(betas):
                    fn=f'b{N}_{i}.npz';np.savez(d/fn,blocks=np.ones((4,4,3)),replicas=np.zeros(4,int))
                    ents.append(dict(s=.875,N=N,beta=beta,beta_simulated=beta,block_size=bs,blocks_file=fn,data=[float(i)]*6,cov=np.eye(6).tolist()))
            (d/'summary.json').write_text(json.dumps(dict(entries=ents)))
            c3=[dict(e,block_size=c3_bs or bs,data=[x+c3_data_shift for x in e['data']]) for e in ents if e['beta'] in betas[1:4]]
            (d/'summary_c3.json').write_text(json.dumps(dict(entries=c3)));return d
        base=mk('b4096',4096);good2=mk('b2048',2048);good8=mk('b8192',8192)
        ok,notes,by=sm.validate_reblock(base,[good2,good8]);assert ok and sorted(by)==[2048,8192],notes
        bad=mk('b2048_copiedc3',2048,c3_bs=4096);ok,notes,_=sm.validate_reblock(base,[bad,good8]);assert not ok and 'mixed block sizes' in ' '.join(notes),notes
        bad2=mk('b8192_shift',8192,c3_data_shift=1e-3);ok,notes,_=sm.validate_reblock(base,[good2,bad2]);assert not ok and 'differs from its full-window counterpart' in ' '.join(notes),notes
        ok,notes,_=sm.validate_reblock(base,[good2]);assert not ok and 'missing for block sizes [8192]' in ' '.join(notes),notes
        ok,notes,_=sm.validate_reblock(base,[good2,base]);assert not ok,notes
    return dict(reblock_validation=True)

def check_windows_and_gates():
    """FITV2-014: copied full summary as c3 (or a c3 that is not the middle three) is rejected; FITV2-018: coordinate
    precision; FITV2-013: the equilibration gate rejects a drifting replica set and accepts a healthy one."""
    with tempfile.TemporaryDirectory(prefix='lri-v2-w-') as tmp:
        tmp=Path(tmp);betas=[.4735,.4742,.4749,.4756,.4763]
        def mk(name,c3_betas,bs=4096):
            d=tmp/name;d.mkdir();ents=[]
            for N in (4096,8192):
                for i,b in enumerate(betas):
                    fn=f'b{N}_{i}.npz';np.savez(d/fn,blocks=np.ones((4,4,3)),replicas=np.zeros(4,int))
                    ents.append(dict(s=.875,N=N,beta=b,beta_simulated=b,block_size=bs,blocks_file=fn,data=[float(i)]*6,cov=np.eye(6).tolist()))
            (d/'summary.json').write_text(json.dumps(dict(entries=ents)))
            (d/'summary_c3.json').write_text(json.dumps(dict(entries=[e for e in ents if e['beta'] in c3_betas])));return d
        good=mk('good',betas[1:4]);b,notes=sm.window_consistency(good);assert b==4096 and not notes,notes
        copied=mk('copied',betas);b,notes=sm.window_consistency(copied);assert b is None and 'middle three' in ' '.join(notes),notes
        wrong=mk('wrong',betas[0:3]);b,notes=sm.window_consistency(wrong);assert b is None,notes
        base=mk('b4096',betas[1:4]);r2=mk('b2048',betas[1:4],2048);r8=mk('b8192',betas[1:4],8192);ok,notes,_=sm.validate_reblock(base,[r2,r8]);assert ok,notes
        bad=mk('b2048c',betas,2048);ok,notes,_=sm.validate_reblock(base,[bad,r8]);assert not ok,notes
    assert sm.ds_of(0.654533)==(0.1727335,'0.1727335') and sm.ds_of(0.875)==(0.0625,'0.0625') and sm.ds_of(0.8)==(0.1,'0.1')
    from equilibration import check as eq
    def reps(z_half=0.5,m_shift=0.,tau=3.):
        out=[]
        for i in range(8):
            out.append(dict(initialization='hot' if i%2==0 else 'cold',m2_mean=.233+(m_shift if i%2 else 0.),m2_block_stderr=2.5e-4,
                            first_vs_second_half_z=z_half,tau_estimate=dict(K=tau,m2_cluster=tau)))
        return out
    ent=lambda d:dict(s=.875,N=4096,beta=.4749,block_size=4096,replica_diagnostics=d)
    assert eq([ent(reps())])['passed']
    assert not eq([ent(reps(z_half=5.))])['passed'] and not eq([ent(reps(m_shift=2e-3))])['passed'] and not eq([ent(reps(tau=300.))])['passed']
    assert not eq([])['passed']
    return dict(window_validation=True,coordinate_precision=True,equilibration_gate=True)

def check_sys_cap():
    assert sm.sys_cap(0.0625)==0.0015 and sm.sys_cap(0.1)==0.004
    grid=[k/80 for k in range(1,20)]+[0.1727335];caps=[sm.sys_cap(d) for d in sorted(grid)]
    assert all(b>=a for a,b in zip(caps,caps[1:])),caps
    assert abs(sm.sys_cap(0.2375)-0.0095)<1e-12 and sm.sys_cap(0.0125)==0.0015 and abs(sm.sys_cap(0.08125)-0.00275)<1e-12
    return dict(caps={str(d):sm.sys_cap(d) for d in sorted(grid)})

def check_extrapolation():
    sizes=np.array(sm.XCHECK_PAIRS*2,float);kinds=np.array([0]*4+[1]*4);truth=dict(Delta_inf=.59,c_U=.8,c_Y=-1.1,omega=.5)
    vals=truth['Delta_inf']+np.where(kinds==0,truth['c_U'],truth['c_Y'])*sizes**(-truth['omega'])
    cov=np.diag(np.full(8,1e-4**2))
    g=sm.gls_extrapolate(vals,cov,sizes,kinds)
    assert abs(g['Delta_inf']-truth['Delta_inf'])<1e-6 and abs(g['omega']-truth['omega'])<1e-9 and abs(g['c_U']-truth['c_U'])<1e-4 and abs(g['c_Y']-truth['c_Y'])<1e-4,g
    assert g['unique'] and not g['on_bound']
    rng=np.random.default_rng(4);draws=np.array([sm.gls_extrapolate(vals+1e-3*rng.standard_normal(8),np.diag(np.full(8,1e-3**2)),sizes,kinds)['Delta_inf'] for _ in range(200)])
    sig=(np.percentile(draws,84)-np.percentile(draws,16))/2;assert abs(draws.mean()-truth['Delta_inf'])<3*sig/np.sqrt(200)+1e-4,(draws.mean(),sig)
    vals_b=.59+np.where(kinds==0,.8,-1.1)*sizes**(-3.);gb=sm.gls_extrapolate(vals_b,np.diag(np.full(8,1e-6**2)),sizes,kinds)
    assert gb['on_bound'],gb
    sing=np.diag(np.r_[np.full(7,1e-6),0.]);assert 'reason' in sm.gls_extrapolate(vals,sing,sizes,kinds),'singular covariance must be rejected'
    assert 'reason' in sm.gls_extrapolate(np.r_[vals[:7],np.nan],cov,sizes,kinds)
    return dict(recovered=g,bootstrap_sigma=float(sig),at_bound_flagged=True,singular_rejected=True)

def main():
    report={}
    for name,fn in [('field_order',check_field_order),('residual_gate',check_residual_gate),('common_valid_mask',check_common_valid_mask),
                    ('schedule',check_schedule),('extrapolation',check_extrapolation),('reblock_validation',check_reblock_validation),('sys_cap',check_sys_cap),('windows_and_gates',check_windows_and_gates)]:
        report[name]=fn();print(name,'ok',json.dumps(report[name],default=float)[:200],flush=True)
    (ROOT/'tests/fit_v2_test_results.json').write_text(json.dumps(report,indent=1,default=float)+'\n');print('all v2 checks passed')
if __name__=='__main__':main()
