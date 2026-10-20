#!/usr/bin/env python3
"""Assemble independent complete campaign streams using the archived affine map.
Paired quadrature levels are differenced WITHIN replicates before covariance.
This does not refit controls or assume the power correction vanishes. It reproduces
every diagnostic of the archived final_analysis.py and applies the pre-registered
empirical allowance policy; check-role sources (degree-7) never enter the estimate.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from campaign import inventory,publish_or_verify,verify_campaign
# Reference coefficients C0..C6 used by the archived lower-order checks (final_analysis.py).
REFS=[.5,-1/6,.657131263981,-3.719856322902,45.42488010356,-731.13947662454,14331.77074705]
LEVELS=[('coarse',1),('refine3',3),('refine5',5),('refine6',6)];CHECK_DEGREE={'refine7':7}

def load(path):return json.loads(Path(path).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stats(x):
    import numpy as np
    return x.mean(0),np.atleast_2d(np.cov(x,rowvar=False,ddof=1))/len(x)
def summary(m,c):
    import numpy as np
    return {'mean':list(map(float,m)),'sampling_se':np.sqrt(np.maximum(0,np.diag(c))).tolist(),'covariance':c.tolist()}
def ceil_2sf(x:float)->float:
    """Round up to two significant figures (24000 for 23447.1; 240 for 233.2)."""
    if x<=0:return 0.
    step=10.**(math.floor(math.log10(x))-1);return float(math.ceil(x/step)*step)

def original_config(root:Path)->dict:
    sources=[]
    def add(name,L,tag,w,level,hi=None,lo=None):
        src={'name':name,'campaign':name,'level':level,'role':'estimator','L':L,'kind':'power' if hi is not None else 'free','weight':w,'legacy_archive':True,
             'path':str(root/'records'/f'{tag}_L{L}{"_N"+str(hi) if hi is not None else ""}.json')}
        if lo is not None:src['subtract']=str(root/'records'/f'{tag}_L{L}_N{lo}.json')
        sources.append(src)
    for tag in ('tprodA','tprodB'):
        for L in (5,6,7):add(f'{tag}_L{L}',L,tag,.5,'free')
    for tag,w in [('power_coarseA',2/3),('power_coarseB',1/3)]:
        for L in (5,6,7):add(f'{tag}_L{L}',L,tag,w,'coarse',1)
    for label,lo,hi in [('refine3',1,3),('refine5',3,5),('refine6',5,6)]:
        for L in (5,6,7):
            tag='power_refine3B' if label=='refine3' and L==7 else 'power_'+label
            add(f'{tag}_L{L}',L,tag,1,label,hi,lo)
    final=load(root/'verification/C7_assembled_result.json');primitive=final['components']['retained_primitive']
    return {'affine_map':str(root/'verification/full_affine_assembly.json'),'sources':sources,'legacy_affine_map':True,
            'retained_primitive':{'mean':primitive['mean_C7'],'sampling_se':primitive['sampling_se']},'primitive_guard':{'inventory':str(root/'inputs/L7_coord.txt'),'L':7},
            'quadrature_note':'degree-six endpoint rule; examine the final paired correction before quoting precision'}

_SUMS=None
def archive_sums()->dict:
    """The authenticated archive manifest reference/SHA256SUMS as {relative path: sha256}."""
    global _SUMS
    if _SUMS is None:_SUMS={line.split(None,1)[1].strip().lstrip('*'):line.split()[0] for line in ((ROOT/'reference').resolve()/'SHA256SUMS').read_text().splitlines() if line.strip()}
    return _SUMS

def authenticate(p:Path,h:str)->None:
    """Legacy archive records carry no manifest; they are accepted only if they match reference/SHA256SUMS."""
    ref=(ROOT/'reference').resolve();sums=archive_sums()
    try:rel=str(p.resolve().relative_to(ref))
    except ValueError:raise ValueError(f'{p}: legacy_archive sources must lie in the delivered reference archive') from None
    if sums.get(rel)!=h:raise ValueError(f'{p}: does not match its reference/SHA256SUMS entry')

def archive_input_hash(name:str)->str|None:
    """SHA-256 of a frozen numerical input in the authenticated archive manifest (reference/SHA256SUMS)."""
    return archive_sums().get('inputs/'+name)

def check_new(p:Path,d:dict,cache:dict)->None:
    if d.get('method')!='c7_hpc_complete_stream_merge' or d.get('complete') is not True or not d.get('manifest_sha256'):
        raise ValueError(f'{p}: not a complete, provenance-carrying campaign output (legacy_archive is only for the authenticated archive)')
    camp=p.resolve().parent.parent
    if camp not in cache:cache[camp]=verify_campaign(camp)
    r=cache[camp];rel=str(p.resolve().relative_to(camp))
    if r['manifest_sha256']!=d['manifest_sha256'] or {'file':rel,'sha256':sha(p)} not in r['audit']['outputs']:raise ValueError(f'{p}: not the audited merged output of its campaign')

def pair_check(s:dict,d:dict,dd:dict,a,b)->None:
    if dd.get('N') is None or d.get('N') is None or not dd['N']<d['N']:raise ValueError(s['name']+': subtracted stream must have the lower quadrature degree')
    keys=['L','seed','replicates']+([] if s.get('legacy_archive') else ['rate','counts','manifest_sha256'])
    for key in keys:
        if d.get(key)!=dd.get(key):raise ValueError(s['name']+': paired streams differ in '+key)
    for key in ('samples_per_graph','counts'): # Archived metadata, compared wherever both records carry it.
        if key in d and key in dd and d[key]!=dd[key]:raise ValueError(s['name']+': paired streams differ in '+key)
    if a.shape!=b.shape:raise ValueError(s['name']+': paired shapes differ')

def assemble(config:dict,base:Path,cache:dict|None=None)->dict:
    import numpy as np
    base=Path(base).resolve();cache={} if cache is None else cache
    def path(s):p=Path(s);return p if p.is_absolute() else base/p
    def rel(p):return os.path.relpath(Path(p).resolve(),base)
    amap=path(config['affine_map']);mapping=load(amap);ah=sha(amap)
    if config.get('legacy_affine_map'):authenticate(amap,ah)
    K=np.array(mapping['K'],dtype=float);mean=K.copy();cov=np.zeros((8,8));unc=K.copy();ucov=np.zeros((8,8))
    components={};levels={};checks={};control={};rawpower={};rawcov={};streams=[];seen=set();used=[]
    for s in config['sources']:
        role=s.get('role','estimator');L=int(s['L']);level=s.get('level','free' if s['kind']=='free' else 'power')
        if role not in ('estimator','check'):raise ValueError(s['name']+': unknown role')
        if s['name'] in components:raise ValueError('duplicate source name '+s['name'])
        if role=='check' and s['kind']!='power':raise ValueError(s['name']+': only power levels can be checks')
        files=[path(s['path'])]+([path(s['subtract'])] if 'subtract' in s else [])
        rec={'name':s['name']}
        for tag,p in zip(('path','subtract'),files):
            rp=p.resolve();h=sha(rp)
            # Every stream enters at most once, as primary or subtraction: a reuse would drop its covariance.
            if rp in seen or h in seen:raise ValueError(f'stream used twice ({s["name"]}): {p}')
            seen|={rp,h};rec[tag]=rel(rp);rec[tag+'_sha256']=h
            if s.get('legacy_archive'):authenticate(rp,h)
        d=load(files[0]);a=np.array(d['batches'],dtype=float);camp=files[0].resolve().parent.parent
        if d['L']!=L:raise ValueError('loop mismatch')
        if not s.get('legacy_archive'):
            check_new(files[0],d,cache);m0=cache[camp]['manifest']
            # Source metadata must describe the verified campaign it points to (kind, loop, degrees, selection).
            sel='primitive' if level=='primitive' else ('power' if s['kind']=='power' else 'free')
            if (s['kind']=='power')!=(m0['mode']=='power') or int(m0['L'])!=L or m0.get('selection')!=sel or d.get('N')!=max(m0['degrees']) or len(m0['degrees'])!=(2 if 'subtract' in s else 1):
                raise ValueError(s['name']+': source metadata does not match its verified campaign manifest')
        if len(a)<2 or a.shape[1:]!=(14,) or not np.isfinite(a).all():raise ValueError('invalid replicate data')
        if 'subtract' in s:
            dd=load(files[1]);b=np.array(dd['batches'],dtype=float)
            if not s.get('legacy_archive'):
                check_new(files[1],dd,cache)
                if dd.get('N')!=min(cache[camp]['manifest']['degrees']) or files[1].resolve().parent.parent!=camp:raise ValueError(s['name']+': subtracted stream is not the lower degree of the same campaign')
            pair_check(s,d,dd,a,b);a=a-b
        used.append((s,d,camp));Jf=np.array(mapping['loops'][str(L)]['J']);Ja=np.array(mapping['loops'][str(L)]['adjusted'])
        w=float(s['weight']);y=a@(Ja if s['kind']=='power' else Jf).T*w;m,c=stats(y)
        components[s['name']]={'campaign':s.get('campaign',s['name']),'level':level,'role':role,'L':L,'kind':s['kind'],'weight':s['weight'],'replicates':len(a),
                               'mean':m.tolist(),'sampling_se':np.sqrt(np.maximum(0,np.diag(c))).tolist(),'covariance':c.tolist(),**{k:v for k,v in rec.items() if k!='name'}}
        if role=='check':checks.setdefault(level,[]).append((m,c));continue
        mean+=m;cov+=c;streams.append(y);levels.setdefault(level,[]).append((m,c))
        mu,cu=stats(a@Jf.T*w);unc+=mu;ucov+=cu # Uncontrolled estimator: J for every stream, no zero-pole control.
        if s['kind']=='power':
            mc,cc=stats(a@(Jf-Ja).T*w);control.setdefault(L,[]).append((mc,cc))
            rm,rc=stats(a);rawpower[L]=rawpower.get(L,0)+w*rm;rawcov[L]=rawcov.get(L,0)+w*w*rc
    # The L7 primitive sector (classes primitive && !power; the inventory flag alone means "no subdivergences") is
    # counted exactly once: either by the retained input (no source may support a guarded class) or by exactly one
    # direct primitive source of unit weight that supports exactly those classes (no other source may support any).
    prim=config.get('retained_primitive');pm=prim['mean'] if prim else 0.;pse=prim['sampling_se'] if prim else 0.
    mean[7]+=pm;cov[7,7]+=pse**2;unc[7]+=pm;ucov[7,7]+=pse**2
    guard=config.get('primitive_guard')
    if not guard or int(guard.get('L',0))!=7:raise ValueError('a primitive_guard for L=7 is required (the primitive sector must be counted exactly once)')
    inv=path(guard['inventory']);ih=sha(inv);rows7=inventory(inv.parent,7);primitive_ids={r['id'] for r in rows7 if r['primitive'] and not r['power']};power_ids={r['id'] for r in rows7 if r['power']}
    if inv.name!='L7_coord.txt' or not primitive_ids:raise ValueError('primitive_guard inventory must be an L7_coord.txt with primitive classes')
    direct=[s for s,_,_ in used if s.get('level')=='primitive'];W={g:0. for g in primitive_ids}
    if prim and direct:raise ValueError('a primitive-level source cannot be combined with a retained primitive input')
    if not prim and len(direct)!=1:raise ValueError('without a retained primitive input exactly one primitive-level source is required')
    shared={} # every new-style campaign at one loop order must use identical inventory, index and Gamma inputs
    for s,d,camp in used:
        if s.get('legacy_archive'):continue
        ins=cache[camp]['manifest']['input_sha256'];Ls=int(s['L'])
        for key in (f'L{Ls}_coord.txt',f'L{Ls}_coord.txt.idx',f'cgamma_L{Ls}.txt'):
            if key in ins and shared.setdefault(key,ins[key])!=ins[key]:raise ValueError(s['name']+': numerical input '+key+' differs from the other sources at this loop order')
        for key in (f'L{Ls}_coord.txt',f'cgamma_L{Ls}.txt'): # bound to the frozen archive, also when mixed with archived records
            if ins.get(key)!=archive_input_hash(key):raise ValueError(s['name']+': numerical input '+key+' differs from the authenticated archive input')
    for s,d,camp in used:
        if int(s['L'])!=7:continue
        # The guard inventory must be the one the stream was integrated with: archive checksum or campaign manifest.
        if s.get('legacy_archive'):authenticate(inv,ih)
        elif cache[camp]['manifest']['input_sha256'].get('L7_coord.txt')!=ih:raise ValueError(s['name']+': primitive_guard inventory differs from the inventory its campaign integrated')
        if not s.get('legacy_archive'): # support comes from the verified manifest, never from the merged file alone
            mc=cache[camp]['manifest']['counts']
            if d.get('counts')!=mc:raise ValueError(s['name']+': merged counts differ from the verified manifest')
            support={g for g,c in enumerate(mc) if c}
        elif d.get('counts') is not None:support={g for g,c in enumerate(d['counts']) if c}
        elif s.get('legacy_archive') and d.get('selection')=='power' and (d.get('samples_per_graph') or 0)>0:support=power_ids # archived writer integrates power classes only
        else:raise ValueError(s['name']+': counts missing, cannot verify the primitive-sector exclusion')
        if s.get('level')=='primitive':
            if s['kind']!='free' or s.get('role','estimator')!='estimator' or float(s['weight'])!=1. or 'subtract' in s or support!=primitive_ids:
                raise ValueError(s['name']+': the primitive source must be a unit-weight free estimator supporting exactly the L7 primitive classes')
        elif support&primitive_ids:raise ValueError(s['name']+': supports primitive classes that '+('the retained primitive input' if prim else 'the primitive source')+' already covers')
        for g in support&primitive_ids:W[g]+=float(s['weight'])
    if any(abs(v-(0. if prim else 1.))>1e-12 for v in W.values()):raise ValueError('primitive classes are not covered with total weight exactly '+('0' if prim else '1'))
    SE=float(np.sqrt(cov[7,7]))
    # Reconciliation: estimator components plus K and primitive rebuild the total exactly; checks stay separate.
    em=K.copy();ec=np.zeros((8,8))
    for v in components.values():
        if v['role']=='estimator':em+=np.array(v['mean']);ec+=np.array(v['covariance'])
    em[7]+=pm;ec[7,7]+=pse**2
    if not (np.allclose(em,mean,rtol=1e-9,atol=1e-9) and np.allclose(ec,cov,rtol=1e-9,atol=1e-9*max(1.,float(abs(cov).max())))):raise ArithmeticError('component reconciliation failed')
    lv={k:summary(sum(x[0] for x in v),sum(x[1] for x in v)) for k,v in levels.items()}
    ck={k:{**summary(sum(x[0] for x in v),sum(x[1] for x in v)),'degree':CHECK_DEGREE.get(k),'role':'check: never added to the estimate'} for k,v in checks.items()}
    # Degrees are telescopic, NOT a fitted extrapolation.
    prefix=K.copy();prefix[7]+=pm;pc=np.zeros((8,8));pc[7,7]=pse**2
    for lev in ('free','primitive'):
        if lev in levels:prefix+=np.array(lv[lev]['mean']);pc+=np.array(lv[lev]['covariance'])
    resolutions=[]
    for lev,N in LEVELS:
        if lev in lv:prefix+=np.array(lv[lev]['mean']);pc+=np.array(lv[lev]['covariance']);resolutions.append({'degree':N,**summary(prefix,pc)})
    checks_lo=[]
    for n in [3,4,5,6]:
        se=float(np.sqrt(cov[n,n]));checks_lo.append({'n':n,'value':float(mean[n]),'sampling_se':se,'reference':REFS[n],'difference_over_sampling_se':float((mean[n]-REFS[n])/se) if se>0 else None})
    poles=[]
    for L in sorted(rawpower):
        se=np.sqrt(np.maximum(0,np.diag(rawcov[L])))
        for k in list(range(L-1))+list(range(7,7+L-1)):
            if se[k]>1e-12:poles.append({'L':L,'column':k,'mean':float(rawpower[L][k]),'sampling_se':float(se[k]),'z_score':float(rawpower[L][k]/se[k])})
    halves=[]
    for half in [0,1]:
        est=mean.copy()
        for y in streams:sl=y[:len(y)//2] if half==0 else y[len(y)//2:];est+=sl.mean(0)-y.mean(0)
        halves.append(est.tolist())
    rng=np.random.default_rng(718395);R=4096;boot=np.repeat(mean[None,:],R,axis=0)
    for y in streams:boot+=y[rng.integers(0,len(y),size=(R,len(y)))].mean(1)-y.mean(0)
    boot[:,7]+=rng.normal(0,pse,R)
    ctl={str(L):summary(sum(x[0] for x in v),sum(x[1] for x in v)) for L,v in sorted(control.items())}
    ctot=summary(sum(sum(x[0] for x in v) for v in control.values()),sum(sum(x[1] for x in v) for v in control.values())) if control else None
    # Pre-registered allowance: an empirical error policy, not a mathematical enclosure.
    half_shift=max(abs(h[7]-mean[7]) for h in halves);cand={'4SE':4*SE,'half_split_shift':half_shift}
    if 'refine6' in lv:cand['refine6']=2*abs(lv['refine6']['mean'][7])+4*lv['refine6']['sampling_se'][7]
    if 'refine7' in ck:cand['refine7']=2*abs(ck['refine7']['mean'][7])+4*ck['refine7']['sampling_se'][7]
    archived=[cand[k] for k in ('4SE','refine6','half_split_shift') if k in cand]
    allowance={'headline_2sf':ceil_2sf(max(cand.values())+.01),'archived_ceil1000':float(math.ceil((max(archived)+.01)/1000)*1000),'candidates':cand,
               'headline_policy':'ceil_2sf(max(4*SE,2*|R6|+4*SE_R6,2*|R7|+4*SE_R7,max half-split shift)+0.01)','archived_policy':'ceil_to_1000(max(4*SE,2*|R6|+4*SE_R6,max half-split shift)+0.01)'}
    flags=[f'systematic tension: C{c["n"]} differs from its reference by {c["difference_over_sampling_se"]:.2f} SE' for c in checks_lo if c['n'] in (5,6) and c['difference_over_sampling_se'] is not None and abs(c['difference_over_sampling_se'])>3]
    crosscheck=None;rc=config.get('retained_primitive_crosscheck')
    if rc and direct:
        dm,ds=lv['primitive']['mean'][7],lv['primitive']['sampling_se'][7];crosscheck={'retained':rc,'direct_mean_C7':dm,'direct_sampling_se':ds,'z':(dm-rc['mean'])/math.hypot(ds,rc['sampling_se'])}
    agg={}
    for v in components.values():
        g=agg.setdefault(v['campaign'],{'role':v['role'],'level':v['level'],'L':v['L'],'sources':0,'mean':np.zeros(8),'covariance':np.zeros((8,8))})
        g['sources']+=1;g['mean']=g['mean']+np.array(v['mean']);g['covariance']=g['covariance']+np.array(v['covariance'])
    agg={k:{'role':g['role'],'level':g['level'],'L':g['L'],'sources':g['sources'],'mean_C7':float(g['mean'][7]),'sampling_se_C7':float(np.sqrt(max(0,g['covariance'][7,7])))} for k,g in agg.items()}
    return {'C7_full':float(mean[7]),'sampling_se':SE,'allowance':allowance,'coefficients':mean.tolist(),'covariance':cov.tolist(),
            'components':components,'campaign_aggregates':agg,'power_levels':{k:v for k,v in lv.items() if k not in ('free','primitive')},'free_level':lv.get('free'),'check_levels':ck,
            'resolution_sequence':resolutions,'lower_order_checks':checks_lo,'spurious_pole_checks':poles,'half_splits':halves,'bootstrap_replicates':R,'bootstrap_se':float(boot[:,7].std(ddof=1)),
            'raw_uncontrolled_C7':float(unc[7]),'raw_uncontrolled':{'coefficients':unc.tolist(),'sampling_se':float(np.sqrt(ucov[7,7]))},
            'applied_zero_pole_control_C7':float(unc[7]-mean[7]),'zero_pole_control':{'per_L':ctl,'total':ctot},
            'retained_primitive':prim,'primitive_source':({'name':direct[0]['name'],'mean_C7':lv['primitive']['mean'][7],'sampling_se_C7':lv['primitive']['sampling_se'][7]} if direct else None),
            'retained_primitive_crosscheck':crosscheck,'affine_map':{'path':rel(amap),'sha256':ah},'sources':[{'name':s['name'],**{k:v for k,v in components[s['name']].items() if k in ('path','path_sha256','subtract','subtract_sha256')}} for s,_,_ in used],'primitive_guard':{'inventory':rel(inv),'sha256':ih,'primitive_classes':len(primitive_ids)},
            'flags':flags,'status':'sampling estimator with a pre-registered empirical allowance; quadrature convergence, inherited-input and framework errors are assessed by the reported checks, not proved'}

def result_text(result:dict)->str:return json.dumps(result,indent=2,allow_nan=False)+'\n'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path);p.add_argument('--original',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not a.original and not a.config:raise SystemExit('give --config or --original')
    c=original_config(ROOT/'reference') if a.original else load(a.config)
    result=assemble(c,ROOT if a.original else a.config.resolve().parent)
    a.output.parent.mkdir(parents=True,exist_ok=True);new=publish_or_verify(a.output,result_text(result))
    print('C7 =',result['C7_full'],'sampling SE =',result['sampling_se'],'allowance =',result['allowance']['headline_2sf'],'' if new else '(existing identical result verified)')
if __name__=='__main__':main()
