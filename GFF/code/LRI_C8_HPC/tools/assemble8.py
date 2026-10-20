#!/usr/bin/env python3
"""Assemble C8(1) from the frozen affine map, the exact loop-5 vector and verified sampled campaigns (loops 6..8).

mean = K + J5 v5(N5) + sum over estimator sources of weight * (stream @ M^T), M = adjusted (power) or J (free).
Paired quadrature levels are differenced WITHIN replicates before covariance. Check sources (refine9, degree 8->9)
are reported, never added. A coverage guard requires every active class of loops 6..8 to be integrated exactly once
per level (free classes: free sources with total weight 1; power classes: coarse total weight 1 and every refinement
level weight 1), with the exclusions listed in the config. The allowance rule is fixed in advance (see ALLOWANCE).
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from campaign import inventory,publish_or_verify,verify_campaign,campaign_inputs,plan_counts,digest
from c8lib import NW,NV,TOP,REFS,C7_REF,pole_columns,LEVEL_SPEC,SAMPLED_LOOPS,check_level,shared_input_names
LEVELS=[('coarse',1),('refine3',3),('refine5',5),('refine6',6),('refine7',7),('refine8',8)];CHECK={'refine9':9};ESTIMATOR_TOP='refine8'
ALLOWANCE='ceil_2sf(max(4*SE, 2|R8|+4*SE_R8, 2|R9|+4*SE_R9, max half-split shift, 2|L5 last degree step|)+0.01)'
NC=NW+1 # coefficients C0..C8

def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stats(x):return x.mean(0),np.atleast_2d(np.cov(x,rowvar=False,ddof=1))/len(x)
def summary(m,c):return {'mean':list(map(float,m)),'sampling_se':np.sqrt(np.maximum(0,np.diag(c))).tolist(),'covariance':c.tolist()}
def ceil_2sf(x:float)->float:
    if x<=0:return 0.
    step=10.**(math.floor(math.log10(x))-1);return float(math.ceil(x/step)*step)

def exact_complete(camp:Path,m:dict)->None:
    """A deterministic input must integrate every active graph over all ordered trees (selection all, full tree counts)."""
    inputs=campaign_inputs(camp,m)
    for name,h in m['input_sha256'].items():
        if h!='absent' and digest(inputs/name)!=h:raise ValueError(f'{camp}: input {name} differs from the manifest')
    _,want=plan_counts(inputs,m['L'],'exact','all',None,0,1)
    if m.get('selection')!='all' or m['counts']!=want or m['replicates']!=1:raise ValueError(f'{camp}: exact campaign does not cover every active graph with all ordered trees')

def exact_vector(path:Path,cache:dict)->tuple[np.ndarray,dict]:
    camp=path.resolve().parent.parent
    if camp not in cache:cache[camp]=verify_campaign(camp)
    r=cache[camp];m=r['manifest'];d=load(path)
    if m['mode']!='exact' or d.get('manifest_sha256')!=r['manifest_sha256'] or {'file':str(path.resolve().relative_to(camp)),'sha256':sha(path)} not in r['audit']['outputs']:raise ValueError(f'{path}: not an audited exact output')
    exact_complete(camp,m)
    return np.array(d['batches'],dtype=float)[0],{'L':m['L'],'N':d['N'],'campaign':str(camp),'manifest_sha256':r['manifest_sha256']}

def check_new(p:Path,d:dict,cache:dict)->dict:
    if d.get('method')!='c8_hpc_complete_stream_merge' or d.get('complete') is not True or not d.get('manifest_sha256'):raise ValueError(f'{p}: not a complete C8 campaign output')
    camp=p.resolve().parent.parent
    if camp not in cache:cache[camp]=verify_campaign(camp)
    r=cache[camp];rel=str(p.resolve().relative_to(camp))
    if r['manifest_sha256']!=d['manifest_sha256'] or {'file':rel,'sha256':sha(p)} not in r['audit']['outputs']:raise ValueError(f'{p}: not the audited merged output of its campaign')
    return r['manifest']

def coverage_guard(used:list,exclusions:dict,inputs_of:dict,shared:dict)->dict:
    """Every active class of loops 6, 7, 8 is integrated with total weight exactly 1 at every estimator level AND at the
    refine9 check level (all levels are required). The inventory and exact-zero files read here are authenticated
    against the hashes shared by every source of the loop. Returns the coverage summary."""
    out={}
    for L in SAMPLED_LOOPS:
        if L not in inputs_of:raise ValueError(f'coverage guard: no sources for loop {L}')
        for name in (f'L{L}_coord.txt',f'exact_zero_L{L}.txt'):
            h=shared.get((L,name))
            if h is None:raise ValueError(f'coverage guard: {name} is not hashed by the loop-{L} sources')
            p=inputs_of[L]/name
            if (h=='absent')!=(not p.exists()) or (h!='absent' and digest(p)!=h):raise ValueError(f'coverage guard: {p} differs from the hash shared by the sources')
        rows=inventory(inputs_of[L],L);excl=set(exclusions.get(str(L),{}).get('classes',[]))
        zp=inputs_of[L]/f'exact_zero_L{L}.txt';zeros=set(map(int,zp.read_text().split()[1:])) if zp.exists() else set()
        active={r['id'] for r in rows if r['terms']>0 and r['id'] not in zeros and r['id'] not in excl and (L<TOP or abs(3*float(r['wb'])-float(r['wa']))>=1e-17)}
        power={r['id'] for r in rows if r['power']}
        lev={}
        for s,d,m in used:
            if int(s['L'])!=L:continue
            for g,c in enumerate(m['counts']):
                if c:lev.setdefault(s['level'],{}).setdefault(g,0.);lev[s['level']][g]+=float(s['weight'])
        need={l:(active-power if l=='free' else active&power) for l in LEVEL_SPEC}
        for l,ids in need.items():
            got=lev.get(l,{})
            missing=[g for g in ids if abs(got.get(g,0.)-1)>1e-12];extra=[g for g in got if g not in ids]
            if missing or extra:raise ValueError(f'coverage guard L{L} level {l}: {len(missing)} classes not covered with weight 1, {len(extra)} unexpected classes (e.g. {(missing+extra)[:5]})')
        out[str(L)]={'active':len(active),'free':len(active-power),'power':len(active&power),'excluded_listed':len(excl),'exact_zero':len(zeros)}
    return out

def load_bundle(meta_path:Path,amap_sha:str)->dict:
    """The frozen design bundle (design8.py): digests of the design, production unit and counts files are re-checked,
    and the affine map used for the estimate must be the one the design was frozen with."""
    meta=load(meta_path);d=meta_path.parent
    if meta.get('affine_sha256')!=amap_sha:raise ValueError('affine map differs from the one the frozen design was built with')
    if digest(d/'design.json')!=meta.get('design_sha256') or digest(d/'unit_production.json')!=meta.get('unit_sha256'):raise ValueError('frozen bundle design/unit digest mismatch')
    for cf,h in meta.get('counts_sha256',{}).items():
        if digest(d/cf)!=h:raise ValueError('frozen bundle counts digest mismatch: '+cf)
    unit={s['name']:s for s in load(d/'unit_production.json')['campaigns']};design=load(d/'design.json')
    return {'dir':d,'meta':meta,'unit':unit,'design':design}

def bundle_check(s:dict,m:dict,bundle:dict,nbatch:int)->None:
    """A source must be exactly a campaign of the frozen bundle: spec, replicate count, per-graph counts and weight."""
    c=s.get('campaign',s['name']);sp=bundle['unit'].get(c);dz=bundle['design'].get(c)
    if sp is None or dz is None:raise ValueError(s['name']+': campaign '+c+' is not part of the frozen design')
    from decimal import Decimal as Dd
    if (sp['mode'],int(sp['L']),sorted(sp['degrees']) if sp['mode']!='qmc' else [0],sp['level'],sp['role'])!=(m['mode'],int(m['L']),m['degrees'],s['level'],s.get('role','estimator')) or Dd(str(sp['rate']))!=Dd(str(m['rate'])):
        raise ValueError(s['name']+': manifest differs from the frozen campaign specification')
    if m['replicates']!=int(sp['B'])*int(dz['replicate_multiplier']):raise ValueError(s['name']+': replicate count differs from the frozen design')
    toks=list(map(int,(bundle['dir']/sp['counts']).read_text().split()));ng=toks[0];frozen=[0]*ng
    for g,c in zip(toks[1::2],toks[2::2]):frozen[g]=c*int(dz.get('multiplier',1))
    if m['counts']!=frozen:raise ValueError(s['name']+': per-graph counts differ from the frozen allocation (no masking by another inventory or zero list)')
    exp=bundle['meta'].get('expected_input_sha256')
    if not exp:raise ValueError('frozen bundle lacks expected_input_sha256')
    for name,h in m['input_sha256'].items():
        if name in exp and exp[name]!=h:raise ValueError(s['name']+': numerical input '+name+' differs from the frozen pilot inputs')
    for name in shared_input_names(int(sp['L']),m['degrees']):
        if name not in exp or name not in m['input_sha256']:raise ValueError(s['name']+': '+name+' is not bound to the frozen pilot inputs')
    if abs(float(s['weight'])*nbatch-float(sp['weight']))>1e-12:raise ValueError(s['name']+': assembly weight differs from the frozen design')

def campaign_inputs_dir(s:dict)->Path:return s['_inputs']

def assemble(config:dict,base:Path,cache:dict|None=None)->dict:
    base=Path(base).resolve();cache={} if cache is None else cache
    def path(s):p=Path(s);return p if p.is_absolute() else base/p
    def rel(p):return os.path.relpath(Path(p).resolve(),base)
    amap=path(config['affine_map']);mapping=load(amap);ah=sha(amap)
    if mapping.get('schema')!='c8-full-affine-1':raise ValueError('affine map must be the frozen c8-full-affine-1 map (controls8.py)')
    K=np.array(mapping['K'],dtype=float);J={int(L):np.array(v['J']) for L,v in mapping['loops'].items()};A={int(L):np.array(v['adjusted']) for L,v in mapping['loops'].items()}
    preview=bool(config.get('preview'))
    forbidden={int(x) for x in config.get('forbidden_seeds',[])}
    bundle=None;seeds={}
    if not preview: # a final result is always the frozen design: bundle digests, affine map and every source re-checked
        if not config.get('design_meta'):raise ValueError('a non-preview assembly requires the frozen design bundle (design_meta)')
        dm=path(config['design_meta']['path'])
        if sha(dm)!=config['design_meta']['sha256']:raise ValueError('design_meta digest mismatch')
        bundle=load_bundle(dm,ah);forbidden|={int(x) for x in bundle['meta'].get('forbidden_seeds',[])}
    e5=config['exact_loop5'];v5,i5=exact_vector(path(e5['path']),cache);v5p,i5p=exact_vector(path(e5['previous']),cache)
    if i5['L']!=5 or i5p['L']!=5 or i5['campaign']!=i5p['campaign'] or not i5p['N']<i5['N']:raise ValueError('exact_loop5 needs two degrees of the same verified loop-5 exact campaign (previous < chosen)')
    if bundle is not None: # R19: the loop-5 input is the frozen one (manifest and the two degrees recorded by design8)
        f5=bundle['meta'].get('exact_loop5')
        if not f5 or i5['manifest_sha256']!=f5['manifest_sha256'] or (i5['N'],i5p['N'])!=(f5['chosen_degree'],f5['previous_degree']):raise ValueError('exact loop-5 input differs from the frozen calculation')
        if mapping.get('sources',{}).get('5',{}).get('manifest_sha256')!=f5['manifest_sha256']:raise ValueError('affine map loop-5 provenance differs from the frozen calculation')
    c5=J[5]@v5;step5=J[5]@(v5-v5p)
    mean=K+c5;cov=np.zeros((NC,NC));unc=mean.copy();ucov=np.zeros((NC,NC))
    components={};levels={};checks={};control={};rawpower={};rawcov={};streams=[];seen=set();used=[];inputs_of={};shared={}
    nbatch=max(1,len(config.get('batches',[]) or [None]))
    if not preview: # control-training streams can never be estimator streams
        for L,v in mapping['loops'].items():forbidden|={int(x['seed']) for x in v.get('training',[]) if 'seed' in x}
    for s in config['sources']:
        role=s.get('role','estimator');L=int(s['L']);level=s['level']
        if role not in ('estimator','check'):raise ValueError(s['name']+': unknown role')
        if s['name'] in components:raise ValueError('duplicate source name '+s['name'])
        if L not in (6,7,8) or s['kind'] not in ('free','power'):raise ValueError(s['name']+': sampled sources are loops 6..8, free or power')
        if level not in LEVEL_SPEC or LEVEL_SPEC[level][1]!=role:raise ValueError(s['name']+f': level {level} with role {role} is not canonical')
        files=[path(s['path'])]+([path(s['subtract'])] if 'subtract' in s else []);rec={}
        for tag,p in zip(('path','subtract'),files):
            rp=p.resolve();h=sha(rp)
            if rp in seen or h in seen:raise ValueError(f'stream used twice ({s["name"]}): {p}')
            seen|={rp,h};rec[tag]=rel(rp);rec[tag+'_sha256']=h
        d=load(files[0]);a=np.array(d['batches'],dtype=float);camp=files[0].resolve().parent.parent;m0=check_new(files[0],d,cache)
        sel='power' if s['kind']=='power' else 'free'
        check_level(level,m0['mode'],role,m0['degrees']) # the verified manifest's degrees must be exactly the level's pair
        if (s['kind']=='power')!=(m0['mode']=='power') or int(m0['L'])!=L or m0.get('selection')!=sel or d.get('N')!=max(m0['degrees']) or len(m0['degrees'])!=(2 if 'subtract' in s else 1):
            raise ValueError(s['name']+': source metadata does not match its verified campaign manifest')
        if int(m0['seed']) in forbidden:raise ValueError(s['name']+': campaign seed was used by the pilot or for control training')
        if seeds.setdefault(int(m0['seed']),camp)!=camp:raise ValueError(s['name']+': random streams (seed) shared with another campaign '+str(seeds[int(m0['seed'])])) # stream identity, not file identity
        if bundle is not None:bundle_check({**s,'_inputs':campaign_inputs(camp,m0)},m0,bundle,nbatch)
        for name in shared_input_names(L,m0['degrees']): # identical numerical inputs across every source of one loop
            h=m0['input_sha256'].get(name)
            if h is None:
                if preview and name.startswith('exact_zero'):continue
                raise ValueError(s['name']+': manifest does not hash '+name)
            if shared.setdefault((L,name),h)!=h:raise ValueError(s['name']+': numerical input '+name+' differs from the other sources of loop '+str(L))
        if s['kind']=='power' and level!='coarse' and 'subtract' not in s:raise ValueError(s['name']+': refinement level without its paired lower degree')
        if len(a)<2 or a.shape[1:]!=(NV,) or not np.isfinite(a).all():raise ValueError('invalid replicate data '+s['name'])
        if 'subtract' in s:
            dd=load(files[1]);b=np.array(dd['batches'],dtype=float);check_new(files[1],dd,cache)
            if dd.get('N')!=min(m0['degrees']) or files[1].resolve().parent.parent!=camp or dd.get('seed')!=d.get('seed') or dd.get('counts')!=d.get('counts') or b.shape!=a.shape:raise ValueError(s['name']+': subtracted stream is not the paired lower degree of the same campaign')
            a=a-b
        inputs_of.setdefault(L,campaign_inputs(camp,m0))
        used.append((s,d,m0))
        w=float(s['weight']);y=a@(A[L] if s['kind']=='power' else J[L]).T*w;m,c=stats(y)
        components[s['name']]={'campaign':s.get('campaign',s['name']),'level':level,'role':role,'L':L,'kind':s['kind'],'weight':s['weight'],'replicates':len(a),
                               'mean':m.tolist(),'sampling_se':np.sqrt(np.maximum(0,np.diag(c))).tolist(),'covariance':c.tolist(),**rec}
        if role=='check':checks.setdefault(level,[]).append((m,c));continue
        mean+=m;cov+=c;streams.append(y);levels.setdefault(level,[]).append((m,c))
        mu,cu=stats(a@J[L].T*w);unc+=mu;ucov+=cu
        if s['kind']=='power':
            mc,cc=stats(a@(J[L]-A[L]).T*w);control.setdefault(L,[]).append((mc,cc))
            rm,rc=stats(a);rawpower[L]=rawpower.get(L,0)+w*rm;rawcov[L]=rawcov.get(L,0)+w*w*rc
    if preview:
        for L in SAMPLED_LOOPS:shared.setdefault((L,f'exact_zero_L{L}.txt'),digest(inputs_of[L]/f'exact_zero_L{L}.txt') if L in inputs_of and (inputs_of[L]/f'exact_zero_L{L}.txt').exists() else 'absent')
    cov_summary=coverage_guard(used,config.get('exclusions',{}),inputs_of,shared)
    if 'refine9' not in checks:raise ValueError('the refine9 check level is required')
    SE=float(np.sqrt(cov[TOP,TOP]))
    lv={k:summary(sum(x[0] for x in v),sum(x[1] for x in v)) for k,v in levels.items()}
    ck={k:{**summary(sum(x[0] for x in v),sum(x[1] for x in v)),'degree':CHECK[k],'role':'check: never added to the estimate'} for k,v in checks.items()}
    prefix=K+c5;pc=np.zeros((NC,NC))
    if 'free' in lv:prefix=prefix+np.array(lv['free']['mean']);pc=pc+np.array(lv['free']['covariance'])
    resolutions=[]
    for lev,N in LEVELS:
        if lev in lv:prefix=prefix+np.array(lv[lev]['mean']);pc=pc+np.array(lv[lev]['covariance']);resolutions.append({'degree':N,**summary(prefix,pc)})
    if not np.allclose(prefix,mean,rtol=1e-11,atol=1e-9):raise ArithmeticError('resolution prefix does not rebuild the estimate')
    lower=[]
    for n in (3,4,5,6):
        se=float(np.sqrt(cov[n,n]));lower.append({'n':n,'value':float(mean[n]),'sampling_se':se,'reference':REFS[n],'difference':float(mean[n]-REFS[n]),'difference_over_sampling_se':float((mean[n]-REFS[n])/se) if se>0 else None})
    se7=float(np.sqrt(cov[7,7]));lower.append({'n':7,'value':float(mean[7]),'sampling_se':se7,'reference':C7_REF[0],'reference_se':C7_REF[1],'difference':float(mean[7]-C7_REF[0]),'difference_over_combined_se':float((mean[7]-C7_REF[0])/math.hypot(se7,C7_REF[1]))})
    poles=[]
    for L in sorted(rawpower):
        se=np.sqrt(np.maximum(0,np.diag(rawcov[L])))
        for k in pole_columns(L):
            if se[k]>1e-12:poles.append({'L':L,'column':k,'mean':float(rawpower[L][k]),'sampling_se':float(se[k]),'z_score':float(rawpower[L][k]/se[k])})
    halves=[]
    for half in (0,1):
        est=mean.copy()
        for y in streams:sl=y[:len(y)//2] if half==0 else y[len(y)//2:];est=est+sl.mean(0)-y.mean(0)
        halves.append(est.tolist())
    rng=np.random.default_rng(718395);R=4096;boot=np.full(R,mean[TOP]) # bootstrap of the C8 column only, in bounded blocks
    for y in streams:
        col=np.ascontiguousarray(y[:,TOP]);n=len(col);step=max(1,(1<<24)//n)
        for r0 in range(0,R,step):
            r1=min(R,r0+step);boot[r0:r1]+=col[rng.integers(0,n,size=(r1-r0,n))].mean(1)-col.mean()
    ctl={str(L):summary(sum(x[0] for x in v),sum(x[1] for x in v)) for L,v in sorted(control.items())}
    half_shift=max(abs(h[TOP]-mean[TOP]) for h in halves);cand={'4SE':4*SE,'half_split_shift':half_shift,'L5_degree_step':2*abs(float(step5[TOP]))}
    if ESTIMATOR_TOP in lv:cand[ESTIMATOR_TOP]=2*abs(lv[ESTIMATOR_TOP]['mean'][TOP])+4*lv[ESTIMATOR_TOP]['sampling_se'][TOP]
    for k in ck:cand[k]=2*abs(ck[k]['mean'][TOP])+4*ck[k]['sampling_se'][TOP]
    allowance={'headline_2sf':ceil_2sf(max(cand.values())+.01),'candidates':cand,'policy':ALLOWANCE}
    tail=None
    if 'refine9' in ck and ESTIMATOR_TOP in lv:
        r8=lv[ESTIMATOR_TOP]['mean'][TOP];r9=ck['refine9']['mean'][TOP];rho=r9/r8 if r8 else None
        tail={'R8':r8,'R9':r9,'ratio':rho,'E9':float(mean[TOP]+r9)}
        if rho is not None and 0<rho<1:
            t=r9*rho/(1-rho);tail.update({'geometric_tail_beyond_9':t,'truncation_aware':float(mean[TOP]+r9+t),'truncation_aware_combined_1sigma':float(math.sqrt(SE**2+ck['refine9']['sampling_se'][TOP]**2+t**2)),'status':'post hoc; tail model uncertain by 100%'})
    flags=[f'C{c["n"]} differs from its exact reference by {c["difference_over_sampling_se"]:.2f} SE' for c in lower if c['n'] in (6,) and c.get('difference_over_sampling_se') is not None and abs(c['difference_over_sampling_se'])>3]
    if abs(lower[2]['difference'])>1e-6*abs(REFS[5]):flags.append(f'deterministic C5 differs from the exact value by {lower[2]["difference"]:.3e}')
    agg={}
    for v in components.values():
        g=agg.setdefault(v['campaign'],{'role':v['role'],'level':v['level'],'L':v['L'],'sources':0,'mean':np.zeros(NC),'covariance':np.zeros((NC,NC))})
        g['sources']+=1;g['mean']=g['mean']+np.array(v['mean']);g['covariance']=g['covariance']+np.array(v['covariance'])
    agg={k:{'role':g['role'],'level':g['level'],'L':g['L'],'sources':g['sources'],'mean_C8':float(g['mean'][TOP]),'sampling_se_C8':float(np.sqrt(max(0,g['covariance'][TOP,TOP])))} for k,g in agg.items()}
    return {'C8_full':float(mean[TOP]),'sampling_se':SE,'allowance':allowance,'coefficients':mean.tolist(),'covariance':cov.tolist(),
            'loop5_exact':{'degree':i5['N'],'previous_degree':i5p['N'],'contribution':c5.tolist(),'last_degree_step':step5.tolist(),'campaign':rel(i5['campaign'])},
            'components':components,'campaign_aggregates':agg,'power_levels':{k:v for k,v in lv.items() if k!='free'},'free_level':lv.get('free'),'check_levels':ck,
            'resolution_sequence':resolutions,'lower_order_checks':lower,'spurious_pole_checks':poles,'half_splits':halves,'bootstrap_replicates':R,'bootstrap_se':float(boot.std(ddof=1)),
            'raw_uncontrolled':{'C8':float(unc[TOP]),'sampling_se':float(np.sqrt(ucov[TOP,TOP])),'coefficients':unc.tolist()},'applied_zero_pole_control_C8':float(unc[TOP]-mean[TOP]),'zero_pole_control':ctl,
            'truncation_assessment':tail,'coverage':cov_summary,'affine_map':{'path':rel(amap),'sha256':ah},'flags':flags,'preview':preview,'forbidden_seeds_checked':len(forbidden),
            'frozen_design':({'design_sha256':bundle['meta']['design_sha256'],'unit_sha256':bundle['meta']['unit_sha256'],'counts_sha256':bundle['meta']['counts_sha256']} if bundle else None),
            'status':'sampling estimator with a pre-registered empirical allowance; quadrature convergence and framework errors are assessed by the reported checks, not proved'}

def result_text(result:dict)->str:return json.dumps(result,indent=2,allow_nan=False)+'\n'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=assemble(load(a.config),a.config.resolve().parent)
    a.output.parent.mkdir(parents=True,exist_ok=True);new=publish_or_verify(a.output,result_text(result))
    print('C8 =',result['C8_full'],'sampling SE =',result['sampling_se'],'allowance =',result['allowance']['headline_2sf'],'' if new else '(existing identical result verified)')
if __name__=='__main__':main()
