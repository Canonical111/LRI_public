"""Reassemble full C7(2) from independent, complete power/power-free campaigns.

The power correction is measured, never set to zero. Pilots are excluded.
All covariance propagation acts on regulator-dependent RG input jets.
"""
from pathlib import Path
import argparse, hashlib, json, math, sys
import numpy as np
W=Path(__file__).resolve().parents[1]
OLD=W.parent/'LRI_C7_d2_progress'
sys.path.insert(0,str(OLD/'code'))
from analyze import coefficients, jacobians, read
from finalize import checked, primitive

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def mean_cov(streams):
    m={L:sum(a[L].mean(0) for a in streams)/len(streams) for L in range(3,8)}
    v={L:sum(np.cov(a[L],rowvar=False)/len(a[L]) for a in streams)/len(streams)**2 for L in m}
    return m,v

def read_power(spec,plan):
    ar={}; per={}; records=[]; B=spec['replicates']; tag=spec['tag']
    for meta in spec['loops']:
        L=meta['loop']; path=W/meta['output']; dat=json.loads(path.read_text())
        assert dat['schema']=='c7-d2-native-1' and dat['L']==L
        assert dat['seed']==spec['seed'] and abs(float(dat['rate'])-float(spec['rate']))<1e-15
        assert dat['layout']==0 and dat['bits']==52 and dat['long_double_bits']>=64
        pl=plan['allocations'][str(L)]; expected={(g,r,0,N,N)for g,N in ((int(k),v)for k,v in pl.items())for r in range(B)}
        seen=set(); vals=np.zeros((B,2*(8-L))); gg={int(g):np.zeros_like(vals)for g in pl}
        for row in dat['rows']:
            key=(row['graph'],row['rep'],row['begin'],row['end'],row['total'])
            assert key in expected and key not in seen; seen.add(key)
            x=np.asarray(row['values'],float); assert len(x)==2*(8-L) and np.isfinite(x).all()
            vals[row['rep']]+=x;gg[row['graph']][row['rep']]+=x
        assert seen==expected
        toks=path.with_suffix('.tasks').read_text().split();assert int(toks[2])==len(seen)
        byid={int(toks[i]):list(map(int,toks[i:i+6]))for i in range(3,len(toks),6)}
        for row in dat['rows']:
            assert byid[row['uid']]==[row[k]for k in ('uid','rep','graph','begin','end','total')]
        inv=json.load(open(W/f'inputs/L{L}/inventory.json'))
        required={g['id']for g in inv if g['status']=='finite-kernel'and(L<7 or g['mass_numerator']!=4)}
        assert required==set(gg)
        ar[L]=vals;per[L]=gg
        records.append(dict(file=str(path.relative_to(W)),sha256=digest(path),task_sha256=digest(path.with_suffix('.tasks')),net_sha256=digest(W/f'inputs/{tag}_L{L}.net'),loop=L,graphs=len(gg),replicates=B,points=B*sum(pl.values()),complete=True,quad=sum(r['quad']for r in dat['rows']),mp=sum(r['mp']for r in dat['rows'])))
    return ar,per,records

def assembled(f,p,pm):
    full=coefficients({L:f[L]+p[L]for L in f});pf=coefficients(f)
    delta=full-pf;full[7]+=pm;pf[7]+=pm
    return full,pf,delta

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bootstrap',type=int,default=4096);args=ap.parse_args()
    manifest=json.load(open(W/'verification/production_manifest.json'));plan=json.load(open(W/'inputs/production_plan.json'))
    assert digest(W/'inputs/production_plan.json')==manifest['allocation_sha256']
    powers=[];covchecks=[];per=[]
    for spec in manifest['campaigns']:
        a,g,r=read_power(spec,plan);powers.append(a);per.append(g);covchecks+=r
    oldchecks=[checked(t)for t in ('productionA','productionB','primitiveA','primitiveB')]
    frees=[read(t)[0]for t in ('productionA','productionB')]
    for a in frees:a.pop(2,None)
    prs=[primitive(t)for t in ('primitiveA','primitiveB')];pm=sum(p['mean']for p in prs)/2;pv=sum(p['sampling_se']**2 for p in prs)/4
    fm,Vf=mean_cov(frees);pp,Vp=mean_cov(powers);m={L:fm[L]+pp[L]for L in fm}
    full,pf,delta=assembled(fm,pp,pm);J=jacobians(m);Jf=jacobians(fm)
    cf={L:J[L]@Vf[L]@J[L].T for L in m};cp={L:J[L]@Vp[L]@J[L].T for L in m}
    cd={L:(J[L]-Jf[L])@Vf[L]@(J[L]-Jf[L]).T+cp[L]for L in m}
    cross=sum(Jf[L]@Vf[L]@(J[L]-Jf[L]).T for L in m)
    cov=sum(cf.values())+sum(cp.values());cov[7,7]+=pv;dcov=sum(cd.values())
    fpcov=sum(Jf[L]@Vf[L]@Jf[L].T for L in m);fpcov[7,7]+=pv
    assert np.allclose(cov,fpcov+dcov+cross+cross.T,rtol=1e-11,atol=1e-9)
    se=np.sqrt(np.maximum(0,np.diag(cov)));dse=np.sqrt(np.maximum(0,np.diag(dcov)))
    campaigns=[]
    for i,a in enumerate(powers):
        am={L:x.mean(0)for L,x in a.items()};f,_,d=assembled(fm,am,pm);j=jacobians({L:fm[L]+am[L]for L in m})
        # Shared PF data are excluded from between-campaign correction comparison.
        cv=sum(j[L]@np.cov(x,rowvar=False)@j[L].T/len(x)for L,x in a.items())
        campaigns.append(dict(tag=manifest['campaigns'][i]['tag'],full_coefficients_with_common_pf=f.tolist(),power_correction=d.tolist(),independent_power_sampling_errors=np.sqrt(np.maximum(0,np.diag(cv))).tolist()))
    halves=[]
    for k in range(2):
        fmh={L:sum(a[L][k*len(a[L])//2:(k+1)*len(a[L])//2].mean(0)for a in frees)/2 for L in m}
        pmh={L:sum(a[L][k*len(a[L])//2:(k+1)*len(a[L])//2].mean(0)for a in powers)/2 for L in m}
        ff,fp,dd=assembled(fmh,pmh,pm);halves.append(dict(full=ff.tolist(),power_free=fp.tolist(),correction=dd.tolist()))
    rng=np.random.default_rng(195076332);boots=[];dboots=[]
    for _ in range(args.bootstrap):
        f={L:sum(a[L][rng.integers(len(a[L]),size=len(a[L]))].mean(0)for a in frees)/2 for L in m}
        p={L:sum(a[L][rng.integers(len(a[L]),size=len(a[L]))].mean(0)for a in powers)/2 for L in m}
        pri=sum(rng.choice(r['replicates'],size=len(r['replicates']),replace=True).mean()for r in prs)/2
        ff,fp,dd=assembled(f,p,pri);boots.append(ff);dboots.append(dd)
    bs=np.array(boots);ds=np.array(dboots)
    refs={3:-.8748500126526,4:5.048868431355,5:-38.83364589623,6:362.3489137997967}
    lower=[dict(order=k,estimate=float(full[k]),reference=v,sampling_se=float(se[k]),pull=float((full[k]-v)/(se[k]**2+(.15264446036381157 if k==6 else 0)**2)**.5))for k,v in refs.items()]
    halfshift=max(abs(h['full'][7]-full[7])for h in halves)
    allowance=math.ceil(max(4*se[7],halfshift)/10)*10
    out=dict(status='full finite-scheme numerical estimator with explicit local mass and logarithmic forest subtractions; empirical uncertainty, not rigorous enclosure',dimension=2,epsilon='2s-2',C7_full=float(full[7]),sampling_se=float(se[7]),empirical_allowance=float(allowance),allowance_policy='round upward to next 10: max(4*propagated SE, largest independent half-stream displacement); not a bound on shared theory error',power_free_C7=float(pf[7]),power_free_se=float(fpcov[7,7]**.5),power_correction=float(delta[7]),power_correction_se=float(dse[7]),power_free_correction_covariance=float(cross[7,7]),coefficients=full.tolist(),sampling_errors=se.tolist(),covariance=cov.tolist(),power_differences=delta.tolist(),power_difference_errors=dse.tolist(),power_difference_covariance=dcov.tolist(),campaigns=campaigns,half_streams=halves,lower_order_checks=lower,error_by_loop={str(L):dict(inherited_powerfree=float(max(0,cf[L][7,7])**.5),new_power=float(max(0,cp[L][7,7])**.5),power_correction_including_pf_dependency=float(max(0,cd[L][7,7])**.5))for L in m},primitive=dict(mean=pm,se=pv**.5,accounted_once=True),bootstrap=dict(replicates=args.bootstrap,seed=195076332,full_se=bs.std(0,ddof=1).tolist(),power_se=ds.std(0,ddof=1).tolist(),full_bias=(bs.mean(0)-full).tolist(),power_bias=(ds.mean(0)-delta).tolist()),new_samples=sum(r['points']for r in covchecks),new_coverage=covchecks,inherited_coverage=oldchecks,means=dict(power_free={str(L):x.tolist()for L,x in fm.items()},power={str(L):x.tolist()for L,x in pp.items()}),scope='No control requiring any power correction to vanish was used. Pilots excluded. Earlier power-free and primitive data are reused; only the missing power sector was freshly produced.')
    (W/'verification/C7_full_result.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items()if k not in ('covariance','power_difference_covariance','new_coverage','inherited_coverage','means')},indent=2))
if __name__=='__main__':main()
