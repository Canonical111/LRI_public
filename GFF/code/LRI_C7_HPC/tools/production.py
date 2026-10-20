#!/usr/bin/env python3
"""Plan/run all streams needed to re-evaluate C7 with the existing frozen design.
New seeds by default; the original allocations, lower inputs and controls are retained.
Use --multiplier (power of two) and --replicate-multiplier to spend more compute, or a
per-campaign --design file. Each production directory is self-contained: its numerical
inputs are copied into <production>/inputs and every internal path is relative.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from campaign import dump,digest,publish_or_verify,verify_campaign
PAIRS=[(f'{a}_L{L}',f'{b}_L{L}') for a,b in [('tprodA','tprodB'),('power_coarseA','power_coarseB')] for L in (5,6,7)]
DESIGN_KEYS={'multiplier','replicate_multiplier','shards','checkpoint_tasks','chunk_points'}

def specs(refine7:bool=False)->list[dict]:
    """The archived accepted design: name, L, mode, replicates, uniform points, degrees, rate, counts file, weight, level, role."""
    out=[]
    def add(name,L,mode,B,n,degrees,rate,counts,weight,level,role='estimator'):
        out.append(dict(name=name,L=L,mode=mode,B=B,n=n,degrees=degrees,rate=rate,counts=counts,weight=weight,level=level,role=role))
    for tag,rate in [('tprodA','.8'),('tprodB','.7')]:
        for L in (5,6,7):add(f'{tag}_L{L}',L,'qmc',16,0,[0],rate,f'tree_production_counts_L{L}.txt',.5,'free')
    for tag,B,w in [('power_coarseA',32,2/3),('power_coarseB',16,1/3)]:
        for L,n in [(5,512),(6,256),(7,128)]:add(f'{tag}_L{L}',L,'power',B,n,[1],'.8',None,w,'coarse')
    for L,n,B in [(5,128,32),(6,32,16),(7,0,16)]:
        tag='power_refine3B' if L==7 else 'power_refine3';count='power_refine3B_counts_L7.txt' if L==7 else None
        add(f'{tag}_L{L}',L,'power',B,n,[1,3],'.8',count,1,'refine3')
    for tag,degrees,triples in [('power_refine5',[3,5],[(5,32,16),(6,8,16),(7,1,8)]),('power_refine6',[5,6],[(5,8,8),(6,2,8),(7,1,4)])]:
        for L,n,B in triples:add(f'{tag}_L{L}',L,'power',B,n,degrees,'.8',None,1,tag.split('_')[1])
    if refine7: # Degree-6 -> 7 quadrature-convergence check at the refine6 allocation; never part of the estimator.
        for L,n,B in [(5,8,8),(6,2,8),(7,1,4)]:add(f'power_refine7_L{L}',L,'power',B,n,[6,7],'.8',None,1,'refine7','check')
    return out

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
    r={'multiplier':a.multiplier,'replicate_multiplier':a.replicate_multiplier,'shards':a.shards_per_stream,'checkpoint_tasks':a.checkpoint_tasks,'chunk_points':a.chunk_points,**d}
    if s['mode']=='qmc' and r['multiplier']&(r['multiplier']-1):raise ValueError(s['name']+': QMC sample multiplier must be a power of two')
    return r

def snapshot(out:Path,source:Path,extra:Path|None,plan:list[dict])->Path:
    """Copy every numerical input the planned campaigns hash (never symlinks), plus the extra weights."""
    dest=out/'inputs';dest.mkdir()
    files=set()
    for s in plan:
        L=s['L'];files|={f'L{L}_coord.txt',f'L{L}_coord.txt.idx',f'cgamma_L{L}.txt',f'exact_zero_L{L}.txt'}
        if s['counts']:files.add(s['counts'])
        for N in s['degrees']:
            if N:files|={f'cw_L{L}_N{N}.txt',f'cw_L{L}_N{N}.bin'}
    for name in sorted(files):
        if (source/name).is_file():shutil.copy2(source/name,dest/name)
    if extra:
        for f in sorted(extra.iterdir()):
            if f.is_file() and f.name.startswith('cw_L') and f.suffix=='.txt':
                if (dest/f.name).exists():raise FileExistsError('extra input would replace a snapshot file: '+f.name)
                shutil.copy2(f,dest/f.name)
    for s in plan:
        for N in s['degrees']:
            if N and not ((dest/f'cw_L{s["L"]}_N{N}.txt').exists() or (dest/f'cw_L{s["L"]}_N{N}.bin').exists()):raise FileNotFoundError(f'no weights for {s["name"]} degree {N}')
    return dest

def plan(a):
    out=a.directory.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'production.json').exists() or (out/'inputs').exists():raise FileExistsError('production plan exists')
    if a.multiplier<1 or a.multiplier&(a.multiplier-1) or a.replicate_multiplier<1:raise ValueError('invalid multipliers')
    ss=specs(a.refine7);design,design_sha=load_design(a.design,{s['name'] for s in ss})
    conf={s['name']:settings(s,a,design) for s in ss}
    for x,y in PAIRS: # Fixed A/B design weights stay valid only if both members scale identically.
        if (conf[x]['multiplier'],conf[x]['replicate_multiplier'])!=(conf[y]['multiplier'],conf[y]['replicate_multiplier']):raise ValueError(f'{x} and {y} must share multiplier and replicate_multiplier')
    exe=a.executable.resolve();inputs=snapshot(out,a.inputs.resolve(),a.extra_inputs.resolve() if a.extra_inputs else None,ss)
    shutil.copy2(ROOT/'reference/verification/full_affine_assembly.json',out/'full_affine_assembly.json')
    jobs=[];plans=[];sources=[]
    for s in ss:
        name=s['name'];c=conf[name];dest=out/name;seed=int.from_bytes(hashlib.sha256(f'{a.seed}:{name}'.encode()).digest()[:8],'little')
        cmd=[sys.executable,str(ROOT/'tools/campaign.py'),'plan','--out',str(dest),'--mode',s['mode'],'--L',str(s['L']),'--replicates',str(s['B']*c['replicate_multiplier']),'--seed',str(seed),'--matrix-seed',str(seed^0x17219317),
             '--points',str(s['n']),'--multiplier',str(c['multiplier']),'--selection','free' if s['mode']=='qmc' else 'power','--rate',s['rate'],'--shards',str(c['shards']),'--threads',str(a.threads),'--checkpoint-tasks',str(c['checkpoint_tasks']),
             '--chunk-points',str(c['chunk_points']),'--inputs',str(inputs),'--executable',str(exe)]
        if s['counts']:cmd+=['--counts',str(inputs/s['counts'])]
        if s['mode']=='power':cmd+=['--degrees',*map(str,s['degrees'])]
        subprocess.run(cmd,check=True)
        m=json.loads((dest/'manifest.json').read_text());plans.append(name)
        jobs.extend({'campaign':name,'index':r['id']} for r in m['shards'])
        hi=max(s['degrees']);src={'name':name,'campaign':name,'level':s['level'],'role':s['role'],'L':s['L'],'kind':'power' if s['mode']=='power' else 'free','weight':s['weight'],'path':f'{name}/merged/N{hi}.json'}
        if len(s['degrees'])==2:src['subtract']=f'{name}/merged/N{min(s["degrees"])}.json'
        sources.append(src)
    final=json.loads((ROOT/'reference/verification/C7_assembled_result.json').read_text());prim=final['components']['retained_primitive']
    dump(out/'assembly.json',{'affine_map':'full_affine_assembly.json','sources':sources,'retained_primitive':{'mean':prim['mean_C7'],'sampling_se':prim['sampling_se']},
         'primitive_guard':{'inventory':'inputs/L7_coord.txt','L':7},'quadrature_note':'degree-six endpoint rule; refine7 (if present) is a convergence check only'})
    dump(out/'production.json',{'schema':'c7-production-2','label':a.label,'campaigns':plans,'jobs':jobs,'seed':a.seed,'multiplier':a.multiplier,'replicate_multiplier':a.replicate_multiplier,
         'design':design,'design_sha256':design_sha,'settings':conf,'refine7':a.refine7,'executable':str(exe),'executable_sha256':digest(exe)})
    print('Total Slurm array entries:',len(jobs),'indices: 0..',len(jobs)-1)

def assemble_production(directory:Path,scratch:Path|None=None)->Path:
    """Merge (or re-verify) every campaign, then publish the final result idempotently."""
    d=json.loads((directory/'production.json').read_text())
    for c in d['campaigns']:
        if (directory/c/'merged/audit.json').exists():verify_campaign(directory/c);continue
        cmd=[sys.executable,str(ROOT/'tools/campaign.py'),'merge',str(directory/c)]
        if scratch:cmd+=['--scratch',str(scratch)]
        subprocess.run(cmd,check=True)
    from assemble import assemble,result_text
    out=directory/'C7_result.json';new=publish_or_verify(out,result_text(assemble(json.loads((directory/'assembly.json').read_text()),directory)))
    print('C7 result','written:' if new else 'verified identical:',out);return out

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    q=s.add_parser('plan');q.add_argument('directory',type=Path);q.add_argument('--seed',type=int,required=True);q.add_argument('--multiplier',type=int,default=1);q.add_argument('--replicate-multiplier',type=int,default=1)
    q.add_argument('--shards-per-stream',type=int,default=32);q.add_argument('--threads',type=int,default=8);q.add_argument('--checkpoint-tasks',type=int,default=64);q.add_argument('--chunk-points',type=int,default=65536)
    q.add_argument('--inputs',type=Path,default=ROOT/'reference/inputs');q.add_argument('--extra-inputs',type=Path,help='directory of additional cw_L*_N*.txt weights (e.g. degree 7)')
    q.add_argument('--executable',type=Path,default=ROOT/'bin/c7_integrate');q.add_argument('--design',type=Path,help='per-campaign JSON {name:{multiplier,replicate_multiplier,shards,checkpoint_tasks,chunk_points}}')
    q.add_argument('--refine7',action='store_true',help='add the paired degree 6/7 check campaigns');q.add_argument('--label',default='')
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
    else:assemble_production(directory,a.scratch)
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print('Production failed:',e,file=sys.stderr);sys.exit(2)
