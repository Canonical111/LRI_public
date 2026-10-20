#!/usr/bin/env python3
"""FIT_MODEL_V3.md §8.2 checks (synthetic data only): x-window selection and coverage guard after the Nmin cut; population
equilibration rule; ratio label anchors; log variant reduces to 'leading'; local-degree dof rule and d*+1 handling;
series deduplication (|E| = 2 with both degree rules, |E| = 1 with one); input validation; quotation ordering; N0
diagnostic: noiseless cancellation fixture PASSES with T = 0, calibrated null FAIL rate ≈ 1 %, +5σ-biased derivatives FAIL,
a value set needing degree > 6 is INCONCLUSIVE."""
import hashlib
import json,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import fit_fss,quotients,select_model as v2,select_model_v3 as v3,n0_diagnostic as n0
from equilibration import check_population

def check_windows_and_coverage():
    pre=dict(beta_c=.4749,Delta_epsilon=.5)
    # offsets defined in x: x_k = 0.15 k (N/1024)^0.25 grows with N -> 5 in-window points at 4096, 3 at 16384/65536, 1 at 262144
    ents=[dict(s=.875,N=N,beta=.4749+0.15*k*(N/1024)**0.25/(100*(N/1024)**0.5),data=[1]*6,cov=np.eye(6).tolist()) for N in (1024,4096,16384,65536,262144) for k in (-2,-1,0,1,2)]
    sub=v3.select_window(ents,'x0.45',pre,4096)
    assert all(abs(v3.xpre(e,pre))<=0.45 and e['N']>=4096 for e in sub)
    ok,per=v3.coverage_ok(sub);assert per[4096]==5 and per[262144]<3 and not ok,(per,ok)   # wide windows at large N fail the guard
    ents2=[dict(s=.875,N=N,beta=.4749+k*0.004*(N/1024)**-0.5,data=[1]*6,cov=np.eye(6).tolist()) for N in (4096,8192,16384,32768,65536) for k in (-2,-1,0,1,2)]
    ok2,per2=v3.coverage_ok(v3.select_window(ents2,'x0.45',pre,4096));assert ok2,per2                    # x-matched windows pass
    assert v3.select_window(ents,'full',pre,16384)==[e for e in ents if e['N']>=16384]                    # legacy: Nmin cut only
    # IR7-001: N2 grids (prepare_stageBx.py: beta_c + k h'/2, h' = x_max/(100 (N/1024)^(1-Deps))) sit exactly on the x0.35 boundary and must be inside
    for beta_c,deps in ((0.25,0.5),(0.3105044,0.48426),(0.4748578,0.58975),(0.2418133,0.48087)):
        pre2=dict(beta_c=beta_c,Delta_epsilon=deps);grid=[]
        for N in (65536,131072,262144,524288):
            h=0.35/100*(N/1024)**(-(1-deps));grid+=[dict(s=1-2*deps,N=N,beta=beta_c+k*h/2,data=[1]*6,cov=np.eye(6).tolist()) for k in (-2,-1,0,1,2)]
        for w in ('x0.35','x0.45','x0.6'):assert len(v3.select_window(grid,w,pre2,65536))==20,(beta_c,w,len(v3.select_window(grid,w,pre2,65536)))
        assert all(v3.in_window(e,pre2,0.35) for e in grid) and not v3.in_window(dict(grid[0],beta=grid[0]['beta']-1e-7),pre2,0.35)
    return dict(coverage_guard=True)

def check_population_rule():
    def reps(z_half=0.5,shift=0.,tau=3.):
        return [dict(initialization='hot' if i%2==0 else 'cold',m2_mean=.233+(shift if i%2 else 0.),m2_block_stderr=2.5e-4,first_vs_second_half_z=z_half,tau_estimate=dict(K=tau)) for i in range(8)]
    ent=lambda d,b=.4749:dict(s=.875,N=4096,beta=b,block_size=4096,replica_diagnostics=d)
    z35=2.5e-4*np.sqrt(2/4)*3.5      # hot/cold shift giving |z| = 3.5 exactly (err = sqrt(2 * sigma^2/4))
    groups=[ent(reps(),b=.47+i*1e-4) for i in range(49)]+[ent(reps(shift=z35),b=.48)]
    r=check_population(groups);assert r['passed'] and r['groups_hotcold_over_3']==1,(r['passed'],r['groups_hotcold_over_3'])   # 1 of 50 at 3.5 sigma -> PASS
    groups2=[ent(reps(),b=.47+i*1e-4) for i in range(48)]+[ent(reps(shift=z35),b=.48),ent(reps(shift=z35),b=.481)]
    assert not check_population(groups2)['passed']                                                        # 2 of 50 above 3 -> FAIL (4 %)
    z45=2.5e-4*np.sqrt(2/4)*4.5
    groups3=[ent(reps(),b=.47+i*1e-4) for i in range(99)]+[ent(reps(shift=z45),b=.48)]
    assert not check_population(groups3)['passed']                                                        # any group above 4 -> FAIL
    return dict(population_rule=True)

def check_log_variant_and_ratio():
    entries=[dict(N=n,s=.875,beta=b,data=[1]*6,cov=np.diag([1e-6]*6).tolist()) for n in (4096,8192,16384,32768,65536) for b in (.4742,.4749,.4756)]
    m1=fit_fss.ProfileFit(entries,degree=3,variant='leading');m2=fit_fss.ProfileFit(entries,degree=3,variant='log')
    assert m2.npar==m1.npar+2 and m2.nlog==2                                                            # c_Y, c_U are nonlinear parameters (§4.8)
    A1=m1.design(np.array([.1,.59,.4]));A2=m2.design(np.array([.1,.59,.4,0.,0.]));assert A1.shape==A2.shape and np.allclose(A1,A2)   # c_Q = 0 reduces to 'leading'
    A3=m2.design(np.array([.1,.59,.4,.7,-.3]));lg=1/np.log(m2.L/256.);nb=A1.shape[-1]//2;nF=m1.degree+1
    assert np.allclose(A3[:,:,:nF],(1+.7*lg)[:,None,None]*A1[:,:,:nF]) and np.allclose(A3[:,:,nb:nb+nF],(1-.3*lg)[:,None,None]*A1[:,:,nb:nb+nF])   # F_Q columns x (1 + c_Q/ln(N/N0)), values and derivatives alike
    assert np.allclose(A3[:,:,nF:nb],A1[:,:,nF:nb]) and np.allclose(A3[:,:,nb+nF:],A1[:,:,nb+nF:])       # r^-omega G columns untouched
    # the fit recovers a synthetic c_Q: data from 'log' with (c_Y, c_U) = (0.8, -0.4) and no noise
    rng=np.random.default_rng(7);amp=rng.standard_normal(A1.shape[-1]);ptrue=np.array([.1,.59,.4,.8,-.4]);pred=m2.design(ptrue)@amp
    m3=fit_fss.ProfileFit([dict(e,data=pred[i].tolist()) for i,e in enumerate(entries)],degree=3,variant='log');f=m3.fit(initial=ptrue+np.array([0,.01,.05,-.2,.1]),multistart=False)
    assert abs(f['Delta_epsilon']-.59)<1e-4 and np.allclose(f['log_coefficients'],[.8,-.4],atol=2e-3),(f['Delta_epsilon'],f['log_coefficients'],f['chi2'])
    # ratio label at the pre-stated anchors (FIT_MODEL_V3 §4.3)
    assert 0.00072<=v3.RATIO_LABEL*0.00054 and 0.00356>v3.RATIO_LABEL*0.00057
    return dict(log_variant=True,log_recovery=f['log_coefficients'],ratio_anchors=True)

def check_crossing_and_schedule():
    # FITV3-001: a doubling pair whose local polynomials have different degrees must cross (polynomial subtraction with padding)
    rng=np.random.default_rng(11);ref=.4749
    def group(N,slope):
        ee=[]
        for b in (.4740,.4745,.4749,.4753,.4758):
            x=100*(b-ref);vals=[1+slope*x+.02*x**2,slope+.04*x,.04,.6+.5*slope*x+.01*x**2,.5*slope+.02*x,.02]
            ee.append(dict(N=N,s=.875,beta=b,data=(np.array(vals)+1e-5*rng.standard_normal(6)).tolist(),cov=np.diag([1e-10]*6).tolist()))
        return ee
    # REV-001: a rank-deficient local design (two temperatures give 6 constraints per family; degree 6 needs 7 coefficients) is refused at the
    # shared cutoff, not silently pseudo-inverted; degree 5 (square) is accepted
    two=[e for e in group(4096,.30) if e['beta'] in (.4740,.4758)]
    try:quotients.LocalCurve(two,ref,6);raise AssertionError('rank-deficient local design accepted')
    except ValueError as ex:assert 'rank deficient' in str(ex)
    quotients.LocalCurve(two,ref,5)
    a=quotients.LocalCurve(group(4096,.30),ref,3);b=quotients.LocalCurve(group(8192,.34),ref,5);ca=a.fit()[0];cb=b.fit()[0]
    assert ca.shape[1]==4 and cb.shape[1]==6
    out=quotients.crossing(a,b,ca,cb,1);assert a.lo<=out[0]<=a.hi and np.all(np.isfinite(out)),out
    # FITV3-003: two campaigns at identical coordinates get different resampling indices; the same campaign is reproducible
    from bootstrap_schedule import block_indices
    i1=block_indices(1,.875,4096,.4749,0,3,100,campaign='stageB');i2=block_indices(1,.875,4096,.4749,0,3,100,campaign='stageBx_4096');i3=block_indices(1,.875,4096,.4749,0,3,100,campaign='stageB')
    assert np.array_equal(i1,i3) and not np.array_equal(i1,i2)
    assert np.array_equal(block_indices(1,.875,4096,.4749,0,3,100),block_indices(1,.875,4096,.4749,0,3,100,campaign=None))
    return dict(unequal_degree_crossing=True,campaign_schedule=True)

def check_local_ladder_and_dedup():
    # three temperatures: admissible local degrees satisfy 2(d+1) <= 6*3-2 -> d <= 7; degree 8 never admissible
    rng=np.random.default_rng(1);betas=[.4742,.4749,.4756]
    def group(N,deg_true=3):
        ee=[]
        for b in betas:
            x=100*(b-.4749);vals=[1+.3*x+.05*x**2+.01*x**3,.3+.1*x+.03*x**2,.1+.06*x,.6+.2*x+.02*x**2,.2+.04*x,.04]
            ee.append(dict(N=N,s=.875,beta=b,data=(np.array(vals)+1e-4*rng.standard_normal(6)).tolist(),cov=np.diag([1e-8]*6).tolist()))
        return ee
    lad=v3.local_ladder({4096:group(4096),8192:group(8192)},.4749)
    for n,rec in lad.items():assert max(rec['admissible'])==7 and 8 not in rec['admissible'],rec
    # RV3-002: two campaigns at the SAME three temperatures give 6 entries but 3 distinct temperatures -> admissible degrees still end at 7
    both=group(4096)+[dict(e,campaign='c2') for e in group(4096)];lad2=v3.local_ladder({4096:both},.4749)
    assert lad2[4096]['n_temps']==3 and max(lad2[4096]['admissible'])==7,lad2[4096]
    # d*+1 beyond d_max -> plus unusable
    rec=lad[4096];assert rec['d_star']<=7 and (rec['d_plus'] is None or rec['d_plus']<=7)
    # FITV3-009: the admissible set follows the dof rule only (n = 4 -> d <= 10, n = 5 -> d <= 13), no fixed cap
    assert v3.local_degrees(3)==list(range(2,8)) and v3.local_degrees(4)==list(range(2,11)) and v3.local_degrees(5)==list(range(2,14))
    # FITV3-008: the 'plus' rule is judged by the d*+1 gate alone — a size whose d* fit fails its gate but whose d*+1 fit passes is usable for 'plus'
    fake={4096:dict(usable=False,d_star=2,d_plus=3,plus_usable=True),8192:dict(usable=True,d_star=3,d_plus=4,plus_usable=False),16384:dict(usable=False,reason='2 in-window temperatures')}
    def pick(rule):
        deg={}
        for n,r in fake.items():
            if rule=='star':
                if r.get('usable'):deg[n]=r['d_star']
            elif r.get('plus_usable'):deg[n]=r['d_plus']
        return deg
    assert pick('star')=={8192:3} and pick('plus')=={4096:3}
    # FITV3-005: the deduplication signature uses only the sizes of the selected pairs; a difference at an unused size is no difference
    idA={1024:('a',),2048:('b',),4096:('c',),8192:('d',),16384:('e',),32768:('f',)};idB={**idA,1024:('a2',)}
    deg={str(n):3 for n in idA};pairs=[2048,4096,8192,16384]
    assert v3.series_signature(idA,deg,pairs)==v3.series_signature(idB,deg,pairs)
    assert v3.series_signature(idA,deg,pairs)!=v3.series_signature({**idA,4096:('c2',)},deg,pairs)
    assert v3.series_signature(idA,deg,pairs)!=v3.series_signature(idA,dict(deg,**{'4096':4}),pairs)
    # deduplication on signatures: identical -> one configuration; different degrees -> two
    idents={'a':v3.series_signature(idA,deg,pairs),'b':v3.series_signature(idB,deg,pairs),'c':v3.series_signature(idA,dict(deg,**{'4096':4}),pairs)}
    series={k:dict(eligible=True) for k in idents};E=[];seen=set()
    for n in series:
        if idents[n] not in seen:E.append(n);seen.add(idents[n])
    assert E==['a','c']
    return dict(local_dof_rule=True,plus_rule_independent=True,dedup=True)

def check_inputs_and_ordering():
    with tempfile.TemporaryDirectory(prefix='lri-v3-') as tmp:
        tmp=Path(tmp)
        def mk(name,bs,ids=((4096,.4742),(4096,.4749),(8192,.4742),(8192,.4749))):
            d=tmp/name;d.mkdir();ents=[dict(s=.875,N=N,beta=b,beta_simulated=b,block_size=bs,blocks_file='x.npz',data=[1]*6,cov=np.eye(6).tolist(),campaign='c') for N,b in ids]
            (d/'summary.json').write_text(json.dumps(dict(entries=ents)));return d
        base=mk('b4096',4096);r2=mk('b2048',2048);r8=mk('b8192',8192);ok,notes,by=v3.validate_inputs(base,[r2,r8]);assert ok and sorted(by)==[2048,8192],notes
        ok,notes,_=v3.validate_inputs(base,[mk('b2048b',2048),mk('b8192b',2048)]);assert not ok                       # repeated block size
        ok,notes,_=v3.validate_inputs(base,[r2,mk('b8192c',8192,ids=((4096,.4742),(4096,.4749),(8192,.4742),(8192,.4750)))]);assert not ok   # identity mismatch
        # FITV3-011: same coordinates from different chains (task ids) are different measurements; FITV3-012: reweighted entries are rejected
        d=mk('tasks',8192);ents=json.loads((d/'summary.json').read_text())['entries']
        for e in ents:e['replica_diagnostics']=[dict(task_id=7,replica=0)]
        (d/'summary.json').write_text(json.dumps(dict(entries=ents)));ok,notes,_=v3.validate_inputs(base,[r2,d]);assert not ok and any('identities differ' in n for n in notes),notes
        d2=tmp/'rew';d2.mkdir();ents=json.loads((base/'summary.json').read_text())['entries'];ents[0]['beta']=ents[0]['beta']+1e-4
        (d2/'summary.json').write_text(json.dumps(dict(entries=ents)))
        try:v3.load_all(d2/'summary.json',.875);raise AssertionError('reweighted entry accepted')
        except ValueError as ex:assert 'reweighted' in str(ex)
        assert len(v3.load_all(base/'summary.json',.875))==4
    q=[dict(config='x0.6_leading_Nmin4096_K1',Nmin=4096,nparams=20,window='x0.6',variant='leading',K=1,degree=4),
       dict(config='x0.45_leading_Nmin4096_K1',Nmin=4096,nparams=20,window='x0.45',variant='leading',K=1,degree=4),
       dict(config='x0.45_second_Nmin4096_K1',Nmin=4096,nparams=20,window='x0.45',variant='second',K=1,degree=4)]
    key=lambda x:(x['nparams'],v3.WINDOW_RANK[x['window']],v3.VARIANT_RANK[x['variant']],x['K'],x['degree'],x['config'])
    import itertools
    assert all(min(list(perm),key=key)['config']=='x0.45_leading_Nmin4096_K1' for perm in itertools.permutations(q))
    return dict(input_validation=True,quotation_ordering=True)

def synth_n0(N,noise=1.,deg=5,bias=0.,seed=3,a=1.0):
    """9 temperatures at spacing delta around 0.3105; Y and U follow a degree-`deg` polynomial (deg 5: the cancellation case);
    derivatives consistent; Gaussian noise with a realistic 6x6 covariance."""
    rng=np.random.default_rng(seed);delta=1e-4;beta=.3105+delta*np.arange(-4,5);x=beta-beta.mean();data=np.zeros((9,6));cov=np.zeros((9,6,6))
    for iv,i1,i2,base in ((0,1,2,5.),(3,4,5,.6)):
        if deg==5:f=a*x*(x**2-delta**2)*(x**2-4*delta**2)/delta**5;f1=a*(5*x**4-15*delta**2*x**2+4*delta**4)/delta**5;f2=a*(20*x**3-30*delta**2*x)/delta**5
        else:f=a*(x**6-3*delta**2*x**4)/delta**6;f1=a*(6*x**5-12*delta**2*x**3)/delta**6;f2=a*(30*x**4-36*delta**2*x**2)/delta**6
        data[:,iv]=base+.01*f;data[:,i1]=.01*f1;data[:,i2]=.01*f2
    for j in range(9):
        sd=np.array([2e-3,.5,3e2,1e-3,.3,2e2]);C=np.outer(sd,sd)*(0.3*np.ones((6,6))+0.7*np.eye(6));cov[j]=C
        data[j]+=noise*np.linalg.cholesky(C)@rng.standard_normal(6)
    for _,(iv,i1,_) in n0.OBS.items():data[:,i1]+=bias*np.sqrt(cov[:,i1,i1])
    return dict(N=N,s=.65,beta=beta,data=data,cov=cov)

def check_n0():
    # noiseless cancellation fixture -> PASS with T = 0
    sets=[synth_n0(65536,noise=0.),synth_n0(262144,noise=0.,seed=4)];res=n0.procedure(sets)
    assert res['outcome'] is None and res['T']<1e-6 and all(r['degree']==5 for r in res['rows']),(res['T'],res['rows'])
    # noisy null: calibration and achieved rate (reduced replicate count for the test)
    sets=[synth_n0(65536,seed=5),synth_n0(262144,seed=6)];obs=n0.procedure(sets);assert obs['outcome'] is None
    null=n0.null_mean(sets,obs['rows']);Ts,excl,numfail,draws=n0.calibrate(null,1500,np.random.default_rng(1))
    thr=float(np.quantile(Ts,0.99));Ts2,_,_,_=n0.calibrate(null,1500,np.random.default_rng(2));rate=float(np.mean(Ts2>=thr))
    assert 0.003<=rate<=0.02 and numfail==0,(rate,numfail)
    # +5 sigma biased derivatives -> FAIL with high power
    ratio=float(np.median([v for d_ in n0.detectable_bias(sets,obs['rows']) for v in d_['ratio']]))   # sigma_R / sigma(Q'): resolvable bias scale
    Tb,_,_,_=n0.calibrate(null,400,np.random.default_rng(3),bias_sigma=5.*ratio);power=float(np.mean(Tb>=thr));assert power>=0.95,(power,ratio)
    # values needing degree > 6 -> INCONCLUSIVE
    bad=synth_n0(65536,noise=0.);bad['data'][:,0]+=0.05*np.array([(-1)**j for j in range(9)]);assert n0.procedure([bad])['outcome']=='INCONCLUSIVE'   # alternating +-25 sigma: no degree <= 6 fits
    # revision 11 rule: a residual orthogonal to every polynomial of degree <= 6 gives the same chi2 at all degrees; chi2 = 10 at
    # dof 6 (p = 0.125) is accepted at degree 2 (the old cut 1.5 would have excluded it), chi2 = 25 (p = 3e-4 at dof 6, 4e-6 at dof 2) is INCONCLUSIVE
    beta=.3105+1e-4*np.arange(-4,5);t=(beta-beta.mean())/np.max(np.abs(beta-beta.mean()));V=np.vander(t,7,increasing=True)
    Qm,_=np.linalg.qr(np.hstack([V,np.random.default_rng(2).standard_normal((9,2))]));r=Qm[:,7];base=1+.2*t+.05*t**2
    n0.RULE='rev11';d,c2,p=n0.select_degree(beta,base+np.sqrt(10.)*r,np.ones(9));assert d==2 and abs(c2-10/6)<1e-6 and 0.12<p<0.13,(d,c2,p)
    assert n0.select_degree(beta,base+5.*r,np.ones(9))[0] is None
    n0.RULE='preregistered';assert n0.select_degree(beta,base+np.sqrt(10.)*r,np.ones(9))[0] is None;n0.RULE='joint'   # chi2/dof 1.67 > 1.5 under the pre-registered cut
    # ---- revision 12 joint test (j)
    ds=synth_n0(65536,seed=8);ents=[dict(N=ds['N'],s=ds['s'],beta=float(b),data=ds['data'][j].tolist(),cov=ds['cov'][j].tolist()) for j,b in enumerate(ds['beta'])]
    for d in (2,3,5):
        jf=n0.joint_polyfit(ds,d);coef,chi,dof=quotients.LocalCurve(ents,float(np.median(ds['beta'])),d).fit()
        assert abs(jf['chi2']-chi)<1e-6*max(1,chi) and jf['dof']==dof,(d,jf['chi2'],chi)                          # same statistic as the production local fit
    models=n0.joint_models([synth_n0(65536,noise=0.,seed=3),synth_n0(262144,noise=0.,seed=4)])
    for name,(m,bias,exp,extra) in models.items():
        nl=n0.joint_procedure(m)
        if exp is not None:
            exp_out='INCONCLUSIVE' if exp>n0.JOINT_PASS_MAX_DEGREE else 'PASS'   # the degree-9 null-space fixture is INCONCLUSIVE, never FAIL (V3-030)
            assert nl['outcome']==exp_out and all(ps['d_star']==exp for ps in nl['per_size']) and max(f['chi2'] for ps in nl['per_size'] for f in ps['fits'] if f['degree']==exp)<1e-8,(name,nl['outcome'],[ps['d_star'] for ps in nl['per_size']])
    assert abs(n0.combined_fail_bound(2)-0.0199)<1e-12
    # IR9-003: array identifiers in the submitter's queue parser
    from slurm_queue import array_count
    assert array_count('54360000')==1 and array_count('54360000_7')==1 and array_count('54360000_[0-31%8]')==32 and array_count('54360000_[1,10-13]')==5
    # V3-033: the legacy generator is the original definition (amplitude 0.02 mean|Q| / delta^deg), distinct from the revision-13 one
    base=[synth_n0(65536,noise=0.,seed=3)];lg=n0.synthetic_model_legacy(base,5)[0];x=base[0]['beta']-base[0]['beta'].mean();delta=x[1]-x[0]
    amp=0.02*abs(base[0]['data'][:,0]).mean()/delta**5;assert np.allclose(lg['data'][:,0]-base[0]['data'][:,0].mean(),amp*x*(x**2-delta**2)*(x**2-4*delta**2))
    assert not np.allclose(lg['data'][:,0],n0.synthetic_model(base,5)[0]['data'][:,0])
    # V3-031: a singular covariance makes every fit fail -> NUMERICAL FAILURE, counted as such in validation, never PASS/FAIL
    sing=synth_n0(65536,seed=3);sing['cov'][0]=np.zeros((6,6));rs=n0.joint_size(sing);assert rs['outcome']=='NUMERICAL FAILURE' and rs['failed_degrees'],rs['outcome']
    vs_=n0.joint_validate([sing],5,np.random.default_rng(1));assert vs_['numerical_failures']==5 and vs_['classified']==0
    # V3-029: block-level generation with covariance re-estimation runs and stays calibrated (loose check, 200 datasets)
    vre=n0.joint_validate(models['cancellation_deg5'][0],200,np.random.default_rng(21),reestimate_blocks=[[488]*9,[488]*9]);assert vre['numerical_failures']==0 and vre['rates']['FAIL']<=0.05,vre
    # V3-028: one-sided acceptance tests against the declared bound / power
    fake={'null':dict(datasets=10000,classified=10000,numerical_failures=0,counts=dict(PASS=9800,FAIL=199,INCONCLUSIVE=1),rates={},noiseless=None),
          'bad':dict(datasets=10000,classified=10000,numerical_failures=0,counts=dict(PASS=9600,FAIL=400,INCONCLUSIVE=0),rates={},noiseless=None),
          'x_bias5sigma':dict(datasets=1000,classified=1000,numerical_failures=0,counts=dict(PASS=100,FAIL=900,INCONCLUSIVE=0),rates={},noiseless=None)}
    bad=n0.joint_validation_failures(fake,2);assert any(b.startswith('bad:') for b in bad) and any(b.startswith('x_bias5sigma') for b in bad) and not any(b.startswith('null:') for b in bad),bad
    m5=models['cancellation_deg5'][0];v=n0.joint_validate(m5,300,np.random.default_rng(5));assert v['rates']['FAIL']<=0.03 and v['numerical_failures']==0,v
    # the synthetic fixture's derivatives are far less precise relative to its values than the real N0 data, so its resolvable bias is
    # larger: a +40 sigma(Q') constant bias (about 5 % of Q') and a 10 % relative bias must be caught; the real-covariance power is measured in the run
    vb=n0.joint_validate(m5,100,np.random.default_rng(6),bias_sigma=40.);assert vb['rates']['FAIL']>=0.95,vb
    vr=n0.joint_validate(m5,100,np.random.default_rng(9),bias_rel=0.10);assert vr['rates']['FAIL']>=0.95,vr
    m4=models['boundary_quadratic_plus_weak_cubic'][0];v4=n0.joint_validate(m4,300,np.random.default_rng(7));assert v4['rates']['FAIL']<=0.03,v4   # weak cubic: PASS at d*=3, not a false FAIL
    bad=synth_n0(65536,noise=0.);bad['data'][:,0]+=0.05*np.array([(-1)**j for j in range(9)]);assert n0.joint_procedure([bad])['outcome']=='INCONCLUSIVE'   # values not smooth -> INCONCLUSIVE, not FAIL (realisable form of the plan's "degree > 9" fixture: no value polynomial with dof >= 1 fits; V3-R16-003)
    # a derivative bias with smooth values -> FAIL (values smooth, joint not)
    biased=synth_n0(65536,noise=0.,seed=3);biased['data'][:,1]*=1.10;assert n0.joint_procedure([biased])['outcome']=='FAIL'                      # 10 % Y' scale error, smooth values
    biased=synth_n0(65536,noise=0.,seed=3);biased['data'][:,1]+=8*np.sqrt(biased['cov'][:,1,1])*np.array([(-1)**j for j in range(9)]);assert n0.joint_procedure([biased])['outcome']=='FAIL'   # non-smooth Y' error
    # V3-027: manifest and no-overwrite
    with tempfile.TemporaryDirectory(prefix='lri-n0-') as tmp:
        out=Path(tmp)/'run';out.mkdir();n0.check_fresh_out(out)
        class A:pass
        a=A();a.seed=1;a.summaries=[Path(__file__)];a.out=out;a.reps=10;a.validate=False;a.rule='joint'
        man=n0.write_manifest(out,a,'joint');assert man['plan_sha256'] and 'n0_diagnostic.py' in man['implementation'] and man['inputs'] and man['rule']=='joint'
        assert (out/'source/n0_diagnostic.py').exists() and hashlib.sha256((out/'source/n0_diagnostic.py').read_bytes()).hexdigest()==man['implementation']['n0_diagnostic.py']   # V3-033 source snapshot
        try:n0.check_fresh_out(out);raise AssertionError('overwrite accepted')
        except SystemExit as ex:assert 'refusing to overwrite' in str(ex)
    # FITV3-006: the procedure validation uses independent replicate sets (threshold set != evaluation set) and enforces the criteria
    val=n0.validate_model(n0.synthetic_model(sets,5),300,seed=21,bias_units=5.)
    assert val['threshold_set']['draws']!=val['evaluation_set']['draws'] or val['threshold_set']['T_threshold_99']!=float(np.quantile([0],0.99))
    assert val['evaluation_set']['conclusive']==300 and val['biased_set']['conclusive']==300 and val['noiseless']['T']<1e-8
    assert 0<=val['evaluation_set']['fail_rate_conditional']<=0.05 and val['biased_set']['fail_rate_conditional']>=0.95,val
    assert n0.validation_failures({'m':val},300)==[] or all('outside' in f for f in n0.validation_failures({'m':val},300)),n0.validation_failures({'m':val},300)   # with 300 replicates the 1 % band is not resolvable: only the rate criterion may trip
    badval={'m':dict(val,evaluation_set=dict(val['evaluation_set'],fail_rate_conditional=0.05))};assert any('outside' in f for f in n0.validation_failures(badval,300))
    return dict(noiseless_pass=True,null_fail_rate=rate,biased_power=power,bias_scale_in_derivative_sigmas=5*ratio,inconclusive_case=True,validation_independent=True)

def check_fix_round2():
    import hashlib
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    # R2-004: coincident betas of several campaigns count as ONE temperature
    same=[dict(s=.875,N=N,beta=.4749,data=[1]*6,cov=np.eye(6).tolist(),campaign=c) for N in (4096,8192,16384,32768) for c in 'abc']
    ok,per=v3.coverage_ok(same);assert not ok and all(v==1 for v in per.values()),per
    dist=[dict(s=.875,N=N,beta=.4749+k*1e-4,data=[1]*6,cov=np.eye(6).tolist(),campaign='a') for N in (4096,8192,16384,32768) for k in (-1,0,1)]
    assert v3.coverage_ok(dist)[0]
    # REV-002: two betas 2e-11 apart straddling a rounding-bin edge are ONE temperature; three such pairs + one distinct = 2 temperatures -> guard fails
    edge=[dict(s=.875,N=N,beta=b,data=[1]*6,cov=np.eye(6).tolist()) for N in (4096,8192,16384,32768) for b in (0.30000000049,0.30000000051,0.31)]
    ok,per=v3.coverage_ok(edge);assert not ok and all(v==2 for v in per.values()),per
    chain=[dict(s=.875,N=4096,beta=0.3+k*0.6e-9,data=[1]*6,cov=np.eye(6).tolist()) for k in range(4)]   # 0, .6, 1.2, 1.8 ns: clusters {0,.6}, {1.2,1.8} -> 2
    assert v3.coverage_ok(chain)[1][4096]==2
    # R2-003 guard
    with tempfile.TemporaryDirectory(prefix='lri-v3-') as tmp:
        tmp=Path(tmp);m=tmp/'merged';m.mkdir()
        ents=[dict(s=.875,N=4096,beta=.4749,beta_simulated=.4749,block_size=4096,blocks_file='b.npz',data=[1]*6,cov=np.eye(6).tolist(),campaign='c1',replica_diagnostics=[dict(task_id=0),dict(task_id=1)]),
              dict(s=.875,N=4096,beta=.4749,beta_simulated=.4749,block_size=4096,blocks_file='b.npz',data=[1]*6,cov=np.eye(6).tolist(),campaign='c2',replica_diagnostics=[dict(task_id=5),dict(task_id=6)])]
        (m/'summary.json').write_text(json.dumps(dict(entries=ents)));assert v3.multi_campaign_pairs(m)==[(0.875,4096)]
        # R2-002: lineage verification on a consistent (manifest, evidence) pair, then tampered
        ents=[ents[0]];(m/'summary.json').write_text(json.dumps(dict(entries=ents)));np.savez(m/'b.npz',blocks=np.zeros((4,4,3)),replicas=np.array([0,0,1,1]))
        # a reblocking input with its own archive (IR14-002: its archive must be in the manifest too)
        rb=tmp/'merged_b8192';rb.mkdir();(rb/'summary.json').write_text(json.dumps(dict(entries=[dict(ents[0],block_size=8192,blocks_file='b8.npz')])));np.savez(rb/'b8.npz',blocks=np.zeros((2,4,3)),replicas=np.array([0,1]))
        reg='ab'*32;ev=tmp/'completion_T_hostA.json';E=dict(result='PASS',registry_sha256=reg,host='hostA',campaigns={'c1':{}},tasks=[dict(campaign='c1',task=0,s=.875,N=4096,beta=.4749,seed=1,samples_sha256='a1'*32),dict(campaign='c1',task=1,s=.875,N=4096,beta=.4749,seed=2,samples_sha256='a2'*32)]);ev.write_text(json.dumps(E))
        man=tmp/'analysis.manifest'
        def write_man(*extra):man.write_text(f"snapshot x\n{reg}  campaigns.json\n{sha(m/'summary.json')}  {m/'summary.json'}\n{sha(m/'b.npz')}  {m/'b.npz'}\n{sha(rb/'summary.json')}  {rb/'summary.json'}\n"+''.join(f'{sha(x)}  {x}\n' for x in extra))
        write_man(rb/'b8.npz',ev);ok,notes,rec=v3.verify_lineage(m,[rb],man,[ev],False);assert ok and rec['manifest']['block_archives_in_manifest']=='2/2' and rec['entries_matched']==1,notes
        write_man(ev);ok,notes,_=v3.verify_lineage(m,[rb],man,[ev],False);assert not ok and any('block archives' in n for n in notes),notes          # IR14-002: 8192 archive missing from the manifest
        write_man(rb/'b8.npz');ok,notes,_=v3.verify_lineage(m,[rb],man,[ev],False);assert not ok and any('not listed in the manifest' in n and 'evidence' in n for n in notes),notes   # IR14-003: evidence hash absent
        write_man(rb/'b8.npz',ev)
        E2=dict(E,result='FAIL');ev.write_text(json.dumps(E2));write_man(rb/'b8.npz',ev);ok,notes,_=v3.verify_lineage(m,[rb],man,[ev],False);assert not ok and any("!= 'PASS'" in n for n in notes),notes
        E3=dict(E,tasks=[dict(E['tasks'][0],task=7)]+E['tasks'][1:]);ev.write_text(json.dumps(E3));write_man(rb/'b8.npz',ev);ok,notes,_=v3.verify_lineage(m,[rb],man,[ev],False);assert not ok and any('task identities' in n for n in notes),notes   # IR14-003: identities, not counts
        ev.write_text(json.dumps(E));write_man(rb/'b8.npz',ev)
        # IR14-004: two per-host records covering different campaigns aggregate; a duplicated (campaign, task) across records is rejected
        ents2=[dict(ents[0],campaign='c2',N=8192,replica_diagnostics=[dict(task_id=3),dict(task_id=4)])];(m/'summary.json').write_text(json.dumps(dict(entries=ents+ents2)))
        evB=tmp/'completion_T_hostB.json';EB=dict(result='PASS',registry_sha256=reg,host='hostB',campaigns={'c2':{}},tasks=[dict(campaign='c2',task=3,s=.875,N=8192,beta=.4749,seed=5,samples_sha256='b3'*32),dict(campaign='c2',task=4,s=.875,N=8192,beta=.4749,seed=6,samples_sha256='b4'*32)]);evB.write_text(json.dumps(EB))
        (rb/'summary.json').write_text(json.dumps(dict(entries=[dict(e,block_size=8192,blocks_file='b8.npz') for e in ents+ents2])));write_man(rb/'b8.npz',ev,evB)
        ok,notes,rec=v3.verify_lineage(m,[rb],man,[ev,evB],False);assert ok and rec['evidence_tasks']==4 and len(rec['completion_evidence'])==2,notes
        ok,notes,_=v3.verify_lineage(m,[rb],man,[ev],False);assert not ok and any('absent from the completion evidence' in n for n in notes),notes
        evB2=tmp/'completion_T_hostC.json';evB2.write_text(json.dumps(dict(EB,host='hostC')));write_man(rb/'b8.npz',ev,evB,evB2)
        ok,notes,_=v3.verify_lineage(m,[rb],man,[ev,evB,evB2],False);assert not ok and any('duplicated across evidence' in n for n in notes),notes
        # IR5-001: two differently named campaigns holding the same chain (same seed/coordinates or same archive hash) are not independent
        EB3=dict(EB,tasks=[dict(EB['tasks'][0],seed=E['tasks'][0]['seed'],N=4096,beta=.4749)]+EB['tasks'][1:]);evB.write_text(json.dumps(EB3));write_man(rb/'b8.npz',ev,evB)
        ok,notes,rec=v3.verify_lineage(m,[rb],man,[ev,evB],False);assert not ok and any('independence' in n and 'seed' in n for n in notes),notes
        EB4=dict(EB,tasks=[dict(t,samples_sha256='ff'*32) for t in EB['tasks']]);E4=dict(E,tasks=[dict(t,samples_sha256='ff'*32) for t in E['tasks']]);evB.write_text(json.dumps(EB4));ev.write_text(json.dumps(E4));write_man(rb/'b8.npz',ev,evB)
        ok,notes,rec=v3.verify_lineage(m,[rb],man,[ev,evB],False);assert not ok and any('archives shared' in n for n in notes),notes
        # IR6-001: a legacy record (no s) and a new record (with s) with identical (N, beta, seed) and different archives are NOT independent
        from independence import check_independence
        mixed=[dict(campaign='old',task=0,N=4096,beta=.4749,seed=11,samples_sha256='01'*32),dict(campaign='new',task=0,s=.875,N=4096,beta=.4749,seed=11,samples_sha256='02'*32)]
        pr=check_independence(mixed);assert any('(N, beta, seed) shared' in q for q in pr),pr
        assert any('without seed' in q for q in check_independence([dict(campaign='x',task=0,N=4096,beta=.4749,samples_sha256='03'*32)]))
        assert check_independence([dict(campaign='a',task=0,N=4096,beta=.4749,seed=1,samples_sha256='04'*32),dict(campaign='b',task=0,N=4096,beta=.4749,seed=2,samples_sha256='05'*32)])==[]
        ev.write_text(json.dumps(E));evB.write_text(json.dumps(EB));write_man(rb/'b8.npz',ev,evB)
        (m/'summary.json').write_text(json.dumps(dict(entries=ents,note='tampered')));ok,notes,_=v3.verify_lineage(m,[rb],man,[ev],False);assert not ok and any('not listed' in n for n in notes),notes
        assert not v3.verify_lineage(m,[rb],None,[ev],False)[0] and not v3.verify_lineage(m,[rb],man,[],False)[0]
        # IR14-007: EQUILIBRATION FAILED withdraws the quotation
        P=dict(quoted=dict(config='x',degree=4,Delta_epsilon=.5,sigma_stat=1e-3),sigma_sys=dict(value=1e-3,ratio=1.),crossing_value=dict(Delta_inf=.5))
        v3.suppress_quotation(P);assert P['quoted'] is None and P['sigma_sys']['value'] is None and P['crossing_value'] is None and P['quoted_diagnostic_not_quoted']['Delta_epsilon']==.5
        # R2-005: the frozen pre-fit comes from a production-family central fit on the block-4096 input only
        fd=tmp/'fits_v2';(fd/'fits').mkdir(parents=True)
        base=dict(Delta_sigma=.1,dof=10,summary_file='/x/merged_b4096_T/summary_c3.json')
        (fd/'fits/ds0.1_c3_leading_Nmin4096_K1_deg4.json').write_text(json.dumps(dict(base,chi2=10.,beta_c=.41,Delta_epsilon=.53)))
        (fd/'fits/reblock_b2048_ds0.1_c3_leading_Nmin4096_K1_deg4.json').write_text(json.dumps(dict(base,chi2=1.,beta_c=.42,Delta_epsilon=.54,summary_file='/x/merged_b2048_T/summary_c3.json')))
        (fd/'fits/ds0.1_c3_leading_Nmin4096_K1_deg8.json').write_text(json.dumps(dict(base,chi2=.5,beta_c=.43,Delta_epsilon=.55,comparator_only=True)))
        (fd/'fits/ds0.1_full_leading_Nmin4096_K1_deg4.json').write_text(json.dumps(dict(base,chi2=2.,beta_c=.44,Delta_epsilon=.56,summary_file='/x/merged_b8192_T/summary.json')))
        pre=v3.freeze_pre(fd);assert list(pre)==[0.8] and pre[0.8]['source']=='ds0.1_c3_leading_Nmin4096_K1_deg4.json' and pre[0.8]['beta_c']==.41,pre
        # R2-001: N0 input requirements
        def n0summary(path,N,betas,reps=4,sweeps=2000000):
            ents=[dict(s=.65,N=N,beta=b,beta_simulated=b,data=[1.,0.,0.,.6,0.,0.],cov=np.eye(6).tolist(),replica_diagnostics=[dict(task_id=i) for i in range(reps)],used_sweeps=sweeps) for b in betas]
            Path(path).write_text(json.dumps(dict(entries=ents)))
        grid=[.3105+1e-4*j for j in range(-4,5)];n0summary(tmp/'a.json',65536,grid);n0summary(tmp/'b.json',262144,[.3105+5e-5*j for j in range(-4,5)])
        sets=[n0.load(tmp/'a.json'),n0.load(tmp/'b.json')];assert n0.input_problems(sets,10000)==[]
        assert any('sizes' in p for p in n0.input_problems(sets[:1],10000)) and any('--reps' in p for p in n0.input_problems(sets,2000))
        n0summary(tmp/'c.json',262144,[.3105+5e-5*j for j in range(-4,5)],reps=3);assert any('chains' in p for p in n0.input_problems([sets[0],n0.load(tmp/'c.json')],10000))
        bad=list(grid);bad[3]+=3e-5;n0summary(tmp/'d.json',65536,bad)
        try:n0.load(tmp/'d.json');raise AssertionError('unequal spacing accepted')
        except ValueError as ex:assert 'equally spaced' in str(ex)
    # R2-006: the two largest usable pairs across the family, with series provenance
    def row(N):return dict(N=N,N2=2*N,crossing_observable='U',beta_crossing=.31,Delta_epsilon_eff_from_U=.5,Delta_epsilon_eff_from_Y=.45,bootstrap_standard_error=[1e-5,1e-3,2e-3],valid_bootstrap_draws=300)
    raw={'xc0.45_star':dict(crossings=[row(N) for N in (1024,2048,4096,8192)],degrees={'1024':3}),'xc0.6_star':dict(crossings=[row(131072),row(262144)],degrees={'131072':3})}
    fb=v3.pair_fallback(raw);assert [q['N'] for q in fb['pairs']]==[131072,262144] and all(q['series']=='xc0.6_star' for q in fb['pairs']),fb
    # R2-008: unresolved equilibration diagnostics fail
    def reps(stderr=2.5e-4,shift=0.,zhalf=0.5):
        return [dict(initialization='hot' if i%2==0 else 'cold',m2_mean=.233+(shift if i%2 else 0.),m2_block_stderr=stderr,first_vs_second_half_z=zhalf,tau_estimate=dict(K=3.)) for i in range(8)]
    ent=lambda d,b=.4749:dict(s=.875,N=4096,beta=b,block_size=4096,replica_diagnostics=d)
    r=check_population([ent(reps(stderr=0.,shift=1e-3))]);assert not r['passed'] and 'zero hot/cold uncertainty' in r['failing'][0]['reasons'][0],r['failing']
    r=check_population([ent(reps(zhalf=None))]);assert not r['passed'] and 'half-chain' in r['failing'][0]['reasons'][0]
    assert check_population([ent(reps()) for _ in range(3)])['passed']
    # IR14-006: the N0 CLI leaves an immutable NUMERICAL FAILURE record when the central fit cannot be computed (non-PD covariance) even with --validate
    with tempfile.TemporaryDirectory(prefix='lri-n0cli-') as tmp:
        tmp=Path(tmp);bad=synth_n0(65536,seed=3);cov=np.array(bad['cov']);cov[:,0,1]=cov[:,1,0]=2*np.sqrt(cov[:,0,0]*cov[:,1,1])   # |corr| = 2: not positive definite
        ents=[dict(s=.65,N=65536,beta=float(b),beta_simulated=float(b),data=bad['data'][j].tolist(),cov=cov[j].tolist(),replica_diagnostics=[dict(task_id=i) for i in range(4)],used_sweeps=2000000,nblocks=488) for j,b in enumerate(bad['beta'])]
        (tmp/'bad.json').write_text(json.dumps(dict(entries=ents)))
        r=subprocess.run([sys.executable,str(ROOT/'n0_diagnostic.py'),str(tmp/'bad.json'),'--out',str(tmp/'run'),'--reps','50','--validate'],capture_output=True,text=True)
        rec=json.loads((tmp/'run'/'n0_result.json').read_text());assert r.returncode==1 and rec['outcome']=='NUMERICAL FAILURE' and rec['production'] is False and (tmp/'run'/'N0_RESULT.md').exists() and (tmp/'run'/'n0_manifest.json').exists(),(r.returncode,rec.get('reason'))
        # AUDIT-003: a malformed input (8 temperatures) still leaves manifest + failure record and exits 1
        (tmp/'bad8.json').write_text(json.dumps(dict(entries=ents[:8])));r8=subprocess.run([sys.executable,str(ROOT/'n0_diagnostic.py'),str(tmp/'bad8.json'),'--out',str(tmp/'run8'),'--reps','50'],capture_output=True,text=True)
        rec8=json.loads((tmp/'run8'/'n0_result.json').read_text());assert r8.returncode==1 and rec8['outcome']=='NUMERICAL FAILURE' and (tmp/'run8'/'n0_manifest.json').exists() and 'expected 9' in rec8['reason'],(r8.returncode,rec8.get('reason'))
    return dict(distinct_temperatures=True,multi_campaign_guard=True,lineage=True,pre_source=True,n0_inputs=True,largest_pairs=True,unresolved_equilibration=True,evidence_aggregation=True,quotation_suppression=True,n0_failure_record=True)

def main():
    report={}
    for name,fn in [('windows_and_coverage',check_windows_and_coverage),('population_rule',check_population_rule),('log_variant_and_ratio',check_log_variant_and_ratio),
                    ('crossing_and_schedule',check_crossing_and_schedule),('local_ladder_and_dedup',check_local_ladder_and_dedup),('inputs_and_ordering',check_inputs_and_ordering),('n0_diagnostic',check_n0),('fix_round2',check_fix_round2)]:
        report[name]=fn();print(name,'ok',json.dumps(report[name],default=float)[:160],flush=True)
    (ROOT/'tests/fit_v3_test_results.json').write_text(json.dumps(report,indent=1,default=float)+'\n');print('all v3 checks passed')
if __name__=='__main__':main()
