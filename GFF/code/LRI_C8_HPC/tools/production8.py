#!/usr/bin/env python3
"""Plan/run/merge one self-contained C8 batch (exact low-loop stage, pilot, or a production batch).

A unit-design file lists the campaigns: name, L, mode (qmc|power|exact), replicates B, uniform points n (or a
per-graph counts file), degrees, rate, assembly weight, level, role and A/B pair. A --design file scales campaigns
by {multiplier, replicate_multiplier, shards, checkpoint_tasks, chunk_points}. The batch directory holds a copied
snapshot of every hashed numerical input; all internal paths are relative. New seeds per batch and campaign.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from campaign import dump,digest,verify_campaign
from c8lib import check_level,LEVEL_SPEC
DESIGN_KEYS={'multiplier','replicate_multiplier','shards','checkpoint_tasks','chunk_points'}
LEVELS=('exact','free','coarse','refine3','refine5','refine6','refine7','refine8','refine9')

def load_unit(path:Path)->tuple[list[dict],str]:
    raw=path.read_bytes();u=json.loads(raw);out=[];names=set()
    for s in u['campaigns']:
        need={'name','L','mode','B','n','degrees','rate','weight','level','role'}
        if need-set(s):raise ValueError(f'unit design entry lacks {need-set(s)}: {s}')
        if s['name'] in names:raise ValueError('duplicate campaign '+s['name'])
        if s['mode'] not in ('qmc','power','exact') or s['level'] not in LEVELS or s['role'] not in ('estimator','check','input'):raise ValueError('invalid mode/level/role: '+s['name'])
        check_level(s['level'],s['mode'],s['role'],list(s['degrees'])) # canonical (mode, role, degrees) per level
        if s['mode']=='exact' and s.get('selection','all')!='all':raise ValueError(s['name']+': exact inputs integrate every active graph (selection all)')
        names.add(s['name']);out.append(s)
    for s in out:
        if s.get('pair') and s['pair'] not in names:raise ValueError(s['name']+': unknown pair '+s['pair'])
    return out,hashlib.sha256(raw).hexdigest()

def load_design(path:Path|None,names:set)->tuple[dict,str|None]:
    if path is None:return {},None
    raw=path.read_bytes();d=json.loads(raw)
    if not isinstance(d,dict) or set(d)-names:raise ValueError('design lists unknown campaigns: '+', '.join(sorted(set(d)-names)) if isinstance(d,dict) else 'design must be a JSON object')
    for name,v in d.items():
        if not isinstance(v,dict) or set(v)-DESIGN_KEYS:raise ValueError('invalid design entry for '+name)
        for k,x in v.items():
            if not isinstance(x,int) or isinstance(x,bool) or x<(0 if k=='chunk_points' else 1):raise ValueError(f'design {name}.{k} must be a positive integer')
    return d,hashlib.sha256(raw).hexdigest()

def settings(s:dict,a,design:dict)->dict:
    d=design.get(s['name'],{})
    r={'multiplier':1,'replicate_multiplier':1,'shards':a.shards_per_stream,'checkpoint_tasks':a.checkpoint_tasks,'chunk_points':a.chunk_points,**d}
    if s['mode']=='qmc' and r['multiplier']&(r['multiplier']-1):raise ValueError(s['name']+': QMC sample multiplier must be a power of two')
    if s['mode']=='exact' and (r['multiplier']!=1 or r['replicate_multiplier']!=1):raise ValueError(s['name']+': exact campaigns cannot be scaled')
    return r

def snapshot(out:Path,source:Path,unit_dir:Path,plan:list[dict])->Path:
    """Copy every numerical input the planned campaigns hash (never symlinks)."""
    dest=out/'inputs';dest.mkdir();files=set();counts=set()
    for s in plan:
        L=s['L'];files|={f'L{L}_coord.txt',f'L{L}_coord.txt.idx',f'cgamma_L{L}.txt',f'exact_zero_L{L}.txt'}
        for N in s['degrees']:
            if N:files.add(f'cw_L{L}_N{N}.txt')
        if s.get('counts'):counts.add(s['counts'])
    for name in sorted(files):
        if (source/name).is_file():shutil.copy2(source/name,dest/name)
        elif not name.startswith('exact_zero'):raise FileNotFoundError(f'missing input {source/name}')
    for c in sorted(counts):
        p=(unit_dir/c);shutil.copy2(p,dest/Path(c).name)
    return dest

def frozen_bundle(meta_path:Path|None,unit_path:Path,design_sha:str|None)->tuple[set,dict]:
    """(forbidden campaign seeds, meta) of a frozen design bundle: the design file and every counts file must match
    the digests recorded by design8.py; pilot and control-training seeds can never be reused."""
    if meta_path is None:return set(),{}
    meta=json.loads(meta_path.read_text())
    if meta.get('design_sha256')!=design_sha:raise ValueError('design file does not match the frozen design bundle')
    for name,h in meta.get('counts_sha256',{}).items():
        if digest(unit_path.resolve().parent/name)!=h:raise ValueError('counts file differs from the frozen design bundle: '+name)
    if meta.get('unit_sha256') and digest(unit_path)!=meta['unit_sha256']:raise ValueError('unit design differs from the frozen design bundle')
    return {int(x) for x in meta.get('forbidden_seeds',[])},meta

def plan(a):
    out=a.directory.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'production.json').exists() or (out/'inputs').exists():raise FileExistsError('batch plan exists')
    ss,unit_sha=load_unit(a.unit);design,design_sha=load_design(a.design,{s['name'] for s in ss})
    if any(s.get('counts') for s in ss) and not a.design_meta:raise ValueError('a production unit (frozen counts files) must be planned with --design-meta (verified frozen bundle)')
    forbidden,meta=frozen_bundle(a.design_meta,a.unit,design_sha)
    if a.seed in {int(x) for x in meta.get('forbidden_batch_seeds',[])}:raise ValueError('batch seed was used by the pilot')
    conf={s['name']:settings(s,a,design) for s in ss}
    for s in ss: # A/B design weights stay valid only if both members scale identically.
        if s.get('pair'):
            x,y=conf[s['name']],conf[s['pair']]
            if (x['multiplier'],x['replicate_multiplier'])!=(y['multiplier'],y['replicate_multiplier']):raise ValueError(f"{s['name']} and {s['pair']} must share multiplier and replicate_multiplier")
    exe=a.executable.resolve();inputs=snapshot(out,a.inputs.resolve(),a.unit.resolve().parent,ss)
    shutil.copy2(a.unit,out/'unit_design.json')
    jobs=[];plans=[];sources=[]
    for s in ss:
        name=s['name'];c=conf[name];dest=out/name;seed=int.from_bytes(hashlib.sha256(f'{a.seed}:{name}'.encode()).digest()[:8],'little')
        if seed in forbidden:raise ValueError(f'{name}: campaign seed {seed} was used by the pilot or for control training')
        sel=s.get('selection') or ('free' if s['mode']=='qmc' else 'power' if s['mode']=='power' else 'all')
        cmd=[sys.executable,str(ROOT/'tools/campaign.py'),'plan','--out',str(dest),'--mode',s['mode'],'--L',str(s['L']),'--replicates',str(s['B']*c['replicate_multiplier']),'--seed',str(seed),'--matrix-seed',str(seed^0x17219317),
             '--points',str(s['n']),'--multiplier',str(c['multiplier']),'--selection',sel,'--rate',s['rate'],'--shards',str(c['shards']),'--threads',str(a.threads),'--checkpoint-tasks',str(c['checkpoint_tasks']),
             '--chunk-points',str(c['chunk_points']),'--inputs',str(inputs),'--executable',str(exe)]
        if s.get('counts'):cmd+=['--counts',str(inputs/Path(s['counts']).name)]
        if s['mode'] in ('power','exact'):cmd+=['--degrees',*map(str,s['degrees'])]
        subprocess.run(cmd,check=True)
        m=json.loads((dest/'manifest.json').read_text());plans.append(name)
        exp=meta.get('expected_input_sha256')
        if meta and not exp:raise ValueError('frozen bundle lacks expected_input_sha256')
        for k,h in (m['input_sha256'].items() if exp else []): # production inputs must be the frozen pilot inputs (R16)
            if k in exp and exp[k]!=h:raise ValueError(f'{name}: input {k} differs from the frozen pilot inputs')
            if k not in exp:raise ValueError(f'{name}: input {k} is not covered by the frozen pilot inputs')
        jobs.extend({'campaign':name,'index':r['id']} for r in m['shards'])
        hi=max(s['degrees']);src={'name':name,'campaign':name,'level':s['level'],'role':s['role'],'L':s['L'],'kind':{'qmc':'free','power':'power','exact':'exact'}[s['mode']],'weight':s['weight'],'path':f'{name}/merged/N{hi}.json'}
        if s['mode']=='power' and len(s['degrees'])==2:src['subtract']=f'{name}/merged/N{min(s["degrees"])}.json'
        if s['mode']=='exact':src['degrees']=sorted(s['degrees'])
        sources.append(src)
    dump(out/'assembly.json',{'sources':sources,'quadrature_note':'degree-eight estimator; refine9 (degree 8->9) is a convergence check only'})
    dump(out/'production.json',{'schema':'c8-production-1','label':a.label,'campaigns':plans,'jobs':jobs,'seed':a.seed,'unit_sha256':unit_sha,'design':design,'design_sha256':design_sha,'settings':conf,
         'design_meta_sha256':digest(a.design_meta) if a.design_meta else None,'forbidden_seeds_checked':len(forbidden),
         'executable':str(exe),'executable_sha256':digest(exe)})
    print('Total Slurm array entries:',len(jobs),'indices: 0..',len(jobs)-1)

def merge_all(directory:Path,scratch:Path|None=None)->None:
    d=json.loads((directory/'production.json').read_text())
    for c in d['campaigns']:
        if (directory/c/'merged/audit.json').exists():verify_campaign(directory/c);continue
        cmd=[sys.executable,str(ROOT/'tools/campaign.py'),'merge',str(directory/c)]
        if scratch:cmd+=['--scratch',str(scratch)]
        subprocess.run(cmd,check=True)
    print('merged and verified',len(d['campaigns']),'campaigns')

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    q=s.add_parser('plan');q.add_argument('directory',type=Path);q.add_argument('--unit',type=Path,required=True);q.add_argument('--seed',type=int,required=True)
    q.add_argument('--shards-per-stream',type=int,default=8);q.add_argument('--threads',type=int,default=16);q.add_argument('--checkpoint-tasks',type=int,default=64);q.add_argument('--chunk-points',type=int,default=65536)
    q.add_argument('--inputs',type=Path,default=ROOT/'inputs8');q.add_argument('--executable',type=Path,default=ROOT/'bin/c8_integrate');q.add_argument('--design',type=Path);q.add_argument('--design-meta',type=Path,help='frozen design bundle metadata (design8.py): digests and forbidden pilot seeds');q.add_argument('--label',default='')
    q=s.add_parser('run');q.add_argument('directory',type=Path);q.add_argument('--index',type=int,required=True);q.add_argument('--threads',type=int);q.add_argument('--scratch',type=Path)
    q.add_argument('--executable',type=Path);q.add_argument('--allow-oversubscribe',action='store_true')
    q=s.add_parser('merge');q.add_argument('directory',type=Path);q.add_argument('--scratch',type=Path)
    a=p.parse_args()
    if a.action=='plan':plan(a);return
    directory=a.directory.resolve();d=json.loads((directory/'production.json').read_text())
    if a.action=='run':
        if not 0<=a.index<len(d['jobs']):raise ValueError('job index out of range')
        j=d['jobs'][a.index];cmd=[sys.executable,str(ROOT/'tools/campaign.py'),'run',str(directory/j['campaign']),'--index',str(j['index'])]
        if a.threads:cmd+=['--threads',str(a.threads)]
        if a.scratch:cmd+=['--scratch',str(a.scratch)]
        if a.executable:cmd+=['--executable',str(a.executable)]
        if a.allow_oversubscribe:cmd+=['--allow-oversubscribe']
        subprocess.run(cmd,check=True)
    else:merge_all(directory,a.scratch)
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print('Production failed:',e,file=sys.stderr);sys.exit(2)
