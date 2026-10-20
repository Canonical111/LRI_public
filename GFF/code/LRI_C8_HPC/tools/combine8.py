#!/usr/bin/env python3
"""Combine independent fresh-seed production batches of one frozen design into one C8 result.

Every campaign of every batch is re-verified. Batches must share a byte-identical canonical scientific configuration
(campaign settings, inputs, executable, design); only seeds, nets, paths and labels may differ. Each batch source
enters once with weight/K under a batch-qualified name; the frozen affine map, the exact loop-5 vector and the
exclusions are shared. Reports the inter-batch chi-square of the per-batch C8 estimates.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from campaign import digest,verify_campaign,publish_or_verify,blocks,identity
from assemble8 import assemble,result_text

def _verify(d:str)->tuple[str,dict]:return d,verify_campaign(Path(d))

def checkpoint_counts(camp:Path)->tuple[int,int]:
    """(present, planned) checkpoints (shard, part, degree) of a campaign from its manifest and hash-checked task plans;
    raises when the planning metadata itself is missing or inconsistent."""
    m=json.loads((camp/'manifest.json').read_text());planned=present=0
    for sh,part,_,_ in blocks(camp,m):
        for N in m['degrees']:planned+=1;present+=(camp/'checkpoints'/(identity(sh['id'],part,N)+'.json')).is_file()
    return present,planned

def planned_configuration(batch:Path)->tuple[dict,dict]:
    """canonical()'s scientific configuration read from the planning metadata alone (no merged outputs needed), with
    each campaign's task plans hash-checked; used for planned batches that are not combined."""
    prod=json.loads((batch/'production.json').read_text());conf=json.loads((batch/'assembly.json').read_text())
    if prod.get('schema')!='c8-production-1':raise ValueError(f'{batch}: not a c8-production-1 batch')
    camps={};seeds={}
    for c in prod['campaigns']:
        d=batch/c;m=json.loads((d/'manifest.json').read_text())
        for _ in blocks(d,m):pass # every task plan must match its manifest digest
        camps[c]={k:m[k] for k in ('schema','mode','L','degrees','rate','replicates','counts','selection','inventory_count','input_sha256','executable_sha256','tile','scratch_mib','shards','checkpoint_tasks','chunk_points','total_work_units','samples_per_degree')}
        seeds[c]=m['seed']
    srcs=[{**{k:s.get(k) for k in ('name','campaign','level','role','L','kind','weight')},'path':s['path'],'subtract':s.get('subtract')} for s in conf['sources']]
    sci={'campaigns':camps,'sources':srcs,'unit_sha256':prod.get('unit_sha256'),'design_sha256':prod.get('design_sha256'),'design':prod.get('design'),'settings':prod.get('settings'),'executable_sha256':prod['executable_sha256'],'jobs':prod['jobs']}
    return sci,{'prod':prod,'campaign_seeds':seeds}

def derived_seed(batch_seed:int,name:str)->int:return int.from_bytes(hashlib.sha256(f'{batch_seed}:{name}'.encode()).digest()[:8],'little') # production8.py plan

def extension_batches(ext_path:Path,mh:str,meta:dict,batches:list,info:list,ref:str)->tuple[int,dict]:
    """Amendment A1 (docs/EXTENSION_A1.md): the given batches must be exactly the frozen design's base batches (count
    from the bundle; identity = label, seed and production.json digest recorded in the amendment) plus every planned
    extension batch whose campaigns are complete. A planned extension batch may be left out only when one of its
    campaigns lacks a planned checkpoint; one with complete checkpoints must be merged and given. Returns (K, record)."""
    ext=json.loads(ext_path.read_text());base=ext_path.resolve().parent
    if ext.get('schema')!='c8-extension-1' or ext.get('design_meta_sha256')!=mh:raise ValueError('extension amendment does not belong to this frozen design bundle')
    bl,el=ext.get('base',[]),ext.get('extension',[])
    labels=[x['label'] for x in bl+el];seeds=[int(x['seed']) for x in bl+el];paths=[(base/x['path']).resolve() for x in el]
    if len(set(labels))!=len(labels) or len(set(seeds))!=len(seeds) or len(set(paths))!=len(paths):raise ValueError('extension amendment: labels, seeds and extension paths must all be distinct')
    if len(bl)!=int(meta['batches']):raise ValueError(f'extension amendment lists {len(bl)} base batches; the frozen design has {meta["batches"]}')
    given={m['label']:(m['seed'],b) for b,(_,m) in zip(batches,info)}
    for b,(_,m) in zip(batches,info): # every combined batch's streams are the ones its batch seed derives (base and extension)
        bad=[c for c,v in m['campaign_seeds'].items() if int(v['seed'])!=derived_seed(int(m['seed']),c)]
        if bad:raise ValueError(f'{b}: campaign seeds of {bad[:3]} are not derived from batch seed {m["seed"]}')
    for x in bl:
        if x['label'] not in given or given[x['label']][0]!=int(x['seed']):raise ValueError(f'base batch {x["label"]} (seed {x["seed"]}) must be given')
        if digest(given[x['label']][1]/'production.json')!=x.get('production_sha256'):raise ValueError(f'base batch {x["label"]}: production.json differs from the record in the amendment')
    planned={x['label']:(int(x['seed']),p) for x,p in zip(el,paths)};basel={x['label'] for x in bl}
    for lab,(seed,b) in given.items():
        if lab in basel:continue
        if lab not in planned or planned[lab]!=(seed,b):raise ValueError(f'{b}: batch {lab} is neither a base batch nor the planned extension batch of that label, seed and path')
    omitted=[]
    for lab,(seed,b) in planned.items():
        if lab in given:continue
        try: # every declared extension batch must have valid planning metadata, consistent with the combined batches
            sci,pm=planned_configuration(b);prod=pm['prod']
            if int(prod['seed'])!=seed or (prod.get('label') or b.name)!=lab:raise ValueError('another seed or label')
            if prod.get('design_meta_sha256')!=mh:raise ValueError('not planned against the frozen design bundle')
            if json.dumps(sci,sort_keys=True)!=ref:raise ValueError('scientific configuration differs from the combined batches')
            if any(cs!=derived_seed(seed,c) for c,cs in pm['campaign_seeds'].items()):raise ValueError('campaign seeds are not derived from the batch seed')
            counts=[checkpoint_counts(b/c) for c in prod['campaigns']]
        except (OSError,ValueError,KeyError,TypeError) as e:raise ValueError(f'planned extension batch {lab} ({b}) lacks valid planning metadata: {e}') from e
        present,need=sum(x[0] for x in counts),sum(x[1] for x in counts)
        if present==need:raise ValueError(f'extension batch {lab} has every planned checkpoint: merge it and include it (amendment A1)')
        omitted.append({'label':lab,'checkpoints_present':present,'checkpoints_planned':need,'completed_fraction':present/need,'reason':'incomplete: planned checkpoints missing'})
    included=[lab for lab in planned if lab in given]
    return len(bl)+len(included),{'amendment':str(ext_path.resolve()),'amendment_sha256':digest(ext_path),'base':[x['label'] for x in bl],'included_extension':included,'omitted_incomplete':omitted}

def canonical(batch:Path,cache:dict)->tuple[dict,dict]:
    prod=json.loads((batch/'production.json').read_text());conf=json.loads((batch/'assembly.json').read_text())
    if prod.get('schema')!='c8-production-1':raise ValueError(f'{batch}: not a c8-production-1 batch')
    camps={};seeds={}
    for c in prod['campaigns']:
        d=(batch/c).resolve();r=cache[d] if d in cache else verify_campaign(d);cache[d]=r;m=r['manifest']
        camps[c]={k:m[k] for k in ('schema','mode','L','degrees','rate','replicates','counts','selection','inventory_count','input_sha256','executable_sha256','tile','scratch_mib','shards','checkpoint_tasks','chunk_points','total_work_units','samples_per_degree')}
        seeds[c]={'seed':m['seed'],'net_sha256':(m['net'] or {}).get('sha256')}
    srcs=[{**{k:s.get(k) for k in ('name','campaign','level','role','L','kind','weight')},'path':s['path'],'subtract':s.get('subtract')} for s in conf['sources']]
    sci={'campaigns':camps,'sources':srcs,'unit_sha256':prod.get('unit_sha256'),'design_sha256':prod.get('design_sha256'),'design':prod.get('design'),'settings':prod.get('settings'),'executable_sha256':prod['executable_sha256'],'jobs':prod['jobs']}
    return sci,{'label':prod.get('label') or batch.name,'seed':prod['seed'],'campaign_seeds':seeds}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('batches',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--affine',type=Path,required=True,help='frozen c8-full-affine-1 map');p.add_argument('--exact5',type=Path,nargs=2,required=True,metavar=('CHOSEN','PREVIOUS'),help='merged exact loop-5 outputs (chosen degree, previous degree)')
    p.add_argument('--exclusions',type=Path,help='JSON {L: {classes: [...], reason: ...}} of classes legitimately not sampled');p.add_argument('--jobs',type=int,default=1)
    p.add_argument('--design-meta',type=Path,required=True,help='frozen design bundle metadata: its pilot/training seeds are forbidden in every source')
    p.add_argument('--partial',action='store_true',help='combine fewer batches than the frozen design: published as C8_partial.json, never as the final result')
    p.add_argument('--extension',type=Path,help='extension amendment (c8-extension-1): every base batch plus every complete planned extension batch must be given')
    p.add_argument('--closed',action='store_true',help='with --extension: no extension lane runs or will run; publish C8_final.json (else C8_interim.json, final=false)');a=p.parse_args()
    if a.extension and a.partial:raise ValueError('--partial and --extension are exclusive')
    if a.closed and not a.extension:raise ValueError('--closed requires --extension')
    batches=[b.resolve() for b in a.batches];out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if len(set(batches))!=len(batches):raise ValueError('a batch is listed twice')
    cache={}
    if a.jobs>1:
        dirs=[str((b/c).resolve()) for b in batches for c in json.loads((b/'production.json').read_text())['campaigns']]
        with ProcessPoolExecutor(a.jobs) as ex:
            for d,r in ex.map(_verify,dirs,chunksize=2):cache[Path(d)]=r
    info=[canonical(b,cache) for b in batches];ref=json.dumps(info[0][0],sort_keys=True)
    for b,(sci,_) in zip(batches,info):
        if json.dumps(sci,sort_keys=True)!=ref:raise ValueError(f'{b}: scientific configuration differs from {batches[0]}; batches of different designs cannot be combined')
    labels=[x[1]['label'] for x in info];seeds=[x[1]['seed'] for x in info];cseeds=[s['seed'] for x in info for s in x[1]['campaign_seeds'].values()]
    if len(set(labels))!=len(labels) or len(set(seeds))!=len(seeds) or len(set(cseeds))!=len(cseeds):raise ValueError('batch labels, batch seeds and campaign seeds must all be distinct')
    K=len(batches);sources=[]
    for b,(_,meta) in zip(batches,info):
        conf=json.loads((b/'assembly.json').read_text())
        for s in conf['sources']:
            t={**s,'name':f'{meta["label"]}/{s["name"]}','campaign':s.get('campaign',s['name']),'weight':s['weight']/K,'path':os.path.relpath(b/s['path'],out)}
            if 'subtract' in s:t['subtract']=os.path.relpath(b/s['subtract'],out)
            sources.append(t)
    excl=json.loads(a.exclusions.read_text()) if a.exclusions else {}
    def rp(x):return os.path.relpath(Path(x).resolve(),out)
    meta=json.loads(a.design_meta.read_text());mh=digest(a.design_meta)
    planned=int(meta['batches']);ext=None
    if a.extension:planned,ext=extension_batches(a.extension,mh,meta,batches,info,ref)
    if (len(batches)!=planned) and not a.partial:raise ValueError(f'the frozen design has {planned} batches; {len(batches)} given (use --partial for an interim, non-final combination)')
    if a.partial and len(batches)>=planned:raise ValueError('--partial is only for fewer batches than the frozen design')
    bundle_names={s['name'] for s in json.loads((a.design_meta.parent/'unit_production.json').read_text())['campaigns']}
    for b,(sci,_) in zip(batches,info):
        prod=json.loads((b/'production.json').read_text())
        if sci['design_sha256']!=meta.get('design_sha256') or prod.get('design_meta_sha256')!=mh:raise ValueError(f'{b}: batch was not planned against the frozen design bundle of --design-meta')
        if set(prod['campaigns'])!=bundle_names:raise ValueError(f'{b}: batch campaigns differ from the frozen design')
        for s in json.loads((b/'assembly.json').read_text())['sources']: # each source is its own batch's declared campaign
            c=s.get('campaign',s['name'])
            if c not in prod['campaigns'] or Path(s['path']).parts[0]!=c or ('subtract' in s and Path(s['subtract']).parts[0]!=c):raise ValueError(f'{b}: source {s["name"]} is not bound to its declared campaign')
    config={'affine_map':rp(a.affine),'exact_loop5':{'path':rp(a.exact5[0]),'previous':rp(a.exact5[1])},'exclusions':excl,'sources':sources,
            'forbidden_seeds':meta.get('forbidden_seeds',[]),'design_meta':{'path':rp(a.design_meta),'sha256':digest(a.design_meta)},
            'batches':[{'label':m['label'],'seed':m['seed'],'path':os.path.relpath(b,out)} for b,(_,m) in zip(batches,info)]}
    if ext:config['extension']={**ext,'amendment':rp(ext['amendment'])}
    publish_or_verify(out/'combined_assembly.json',json.dumps(config,indent=2,allow_nan=False)+'\n')
    result=assemble(config,out,cache);per=[]
    for b,(_,m) in zip(batches,info):
        conf=json.loads((b/'assembly.json').read_text());bc={**config,'batches':[x for x in config['batches'] if x['label']==m['label']],'sources':[{**s,'path':os.path.relpath(b/s['path'],out),**({'subtract':os.path.relpath(b/s['subtract'],out)} if 'subtract' in s else {})} for s in conf['sources']]}
        r=assemble(bc,out,cache);per.append({'label':m['label'],'C8_full':r['C8_full'],'sampling_se':r['sampling_se']})
    chi2=sum((x['C8_full']-result['C8_full'])**2/x['sampling_se']**2 for x in per) if K>1 else None
    result['batches']={'count':K,'planned':planned,'per_batch':per,'chi2_about_combined':chi2,'dof':K-1}
    result['final']=not a.partial and (ext is None or a.closed)
    if a.partial:result['status']='PARTIAL combination of '+str(K)+' of '+str(planned)+' planned batches: interim, not the final result. '+result['status']
    if ext:
        result['extension']={**config['extension'],'closed':a.closed}
        if not a.closed:result['status']='INTERIM extension combination (amendment A1; lanes may still run): not the final result. '+result['status']
    name='C8_partial.json' if a.partial else 'C8_interim.json' if ext and not a.closed else 'C8_final.json'
    new=publish_or_verify(out/name,result_text(result))
    print(json.dumps({'batches':K,'C8_full':result['C8_full'],'sampling_se':result['sampling_se'],'allowance_headline_2sf':result['allowance']['headline_2sf'],'chi2':chi2,'dof':K-1,'written':new},indent=2))
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,ArithmeticError) as e:print('Combine failed:',e,file=sys.stderr);sys.exit(2)
