#!/usr/bin/env python3
"""Combine independent fresh-seed production batches of one frozen design into one C7 result.

Every campaign of every batch is re-verified. Batches must share a byte-identical canonical
scientific configuration; only seeds, nets, paths and labels may differ. Each batch source
enters once with weight/K under a batch-qualified name; the retained primitive enters once.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from campaign import digest,dump,publish_or_verify,verify_campaign
from assemble import assemble,result_text

def _verify(d:str)->tuple[str,dict]:return d,verify_campaign(Path(d))

def canonical(batch:Path,cache:dict)->tuple[dict,dict]:
    """Scientific configuration of one batch, with the seed-dependent fields listed separately."""
    prod=json.loads((batch/'production.json').read_text());conf=json.loads((batch/'assembly.json').read_text())
    if prod.get('schema')!='c7-production-2':raise ValueError(f'{batch}: not a c7-production-2 batch')
    camps={};seeds={}
    for c in prod['campaigns']:
        d=(batch/c).resolve();r=cache[d] if d in cache else verify_campaign(d);cache[d]=r;m=r['manifest']
        camps[c]={k:m[k] for k in ('schema','mode','L','degrees','rate','replicates','counts','selection','inventory_count','input_sha256','executable_sha256','tile','scratch_mib')}
        seeds[c]={'seed':m['seed'],'net_sha256':(m['net'] or {}).get('sha256')}
    amap=batch/conf['affine_map']
    srcs=[{**{k:s.get(k) for k in ('name','campaign','level','role','L','kind','weight')},'path':s['path'],'subtract':s.get('subtract')} for s in conf['sources']]
    sci={'campaigns':camps,'sources':srcs,'affine_map_sha256':digest(amap),'retained_primitive':conf['retained_primitive'],'primitive_guard':conf.get('primitive_guard'),
         'design_sha256':prod.get('design_sha256'),'design':prod.get('design'),'settings':prod.get('settings'),'refine7':prod.get('refine7'),'executable_sha256':prod['executable_sha256']}
    return sci,{'label':prod.get('label') or batch.name,'seed':prod['seed'],'campaign_seeds':seeds}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('batches',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--primitive',type=Path,help='verified campaign (qmc, L7, selection primitive) that replaces the retained primitive input')
    p.add_argument('--jobs',type=int,default=1,help='parallel processes for re-verifying campaigns (results are identical)');a=p.parse_args()
    batches=[b.resolve() for b in a.batches];out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if len(set(batches))!=len(batches):raise ValueError('a batch is listed twice')
    cache={}
    if a.jobs>1: # re-verification dominates the runtime; every campaign is still verified in full, only in parallel
        dirs=[str((b/c).resolve()) for b in batches for c in json.loads((b/'production.json').read_text())['campaigns']]+([str(a.primitive.resolve())] if a.primitive else [])
        with ProcessPoolExecutor(a.jobs) as ex:
            for d,r in ex.map(_verify,dirs,chunksize=2):cache[Path(d)]=r
    info=[canonical(b,cache) for b in batches];ref=json.dumps(info[0][0],sort_keys=True)
    def diff(x,y,at=''):
        if isinstance(x,dict) and isinstance(y,dict):return [d for k in sorted(set(x)|set(y)) for d in diff(x.get(k),y.get(k),f'{at}.{k}' if at else str(k))]
        return [] if json.dumps(x,sort_keys=True)==json.dumps(y,sort_keys=True) else [at or '<root>']
    for b,(sci,_) in zip(batches,info):
        if json.dumps(sci,sort_keys=True)!=ref:raise ValueError(f'{b}: scientific configuration differs from {batches[0]} in {", ".join(diff(info[0][0],sci)[:8])}; batches of different designs cannot be combined')
    labels=[x[1]['label'] for x in info];seeds=[x[1]['seed'] for x in info]
    cseeds=[s['seed'] for x in info for s in x[1]['campaign_seeds'].values()]
    if len(set(labels))!=len(labels) or len(set(seeds))!=len(seeds) or len(set(cseeds))!=len(cseeds):raise ValueError('batch labels, batch seeds and campaign seeds must all be distinct')
    K=len(batches);sources=[]
    for b,(_,meta) in zip(batches,info):
        conf=json.loads((b/'assembly.json').read_text())
        for s in conf['sources']:
            t={**s,'name':f'{meta["label"]}/{s["name"]}','campaign':s.get('campaign',s['name']),'weight':s['weight']/K,'path':os.path.relpath(b/s['path'],out)}
            if 'subtract' in s:t['subtract']=os.path.relpath(b/s['subtract'],out)
            sources.append(t)
    first=json.loads((batches[0]/'assembly.json').read_text())
    config={'affine_map':os.path.relpath(batches[0]/first['affine_map'],out),'sources':sources,'retained_primitive':first['retained_primitive'],
            'primitive_guard':{**first['primitive_guard'],'inventory':os.path.relpath(batches[0]/first['primitive_guard']['inventory'],out)} if first.get('primitive_guard') else None,
            'batches':[{'label':m['label'],'seed':m['seed'],'path':os.path.relpath(b,out)} for b,(_,m) in zip(batches,info)],'quadrature_note':first.get('quadrature_note')}
    if a.primitive: # Direct primitive campaign replaces the retained input; assemble() enforces the exactly-once guard.
        pd=a.primitive.resolve();cache[pd]=cache[pd] if pd in cache else verify_campaign(pd);pm=cache[pd]['manifest']['input_sha256']
        ref=info[0][0]['campaigns'][next(c for c in info[0][0]['campaigns'] if info[0][0]['campaigns'][c]['mode']=='qmc' and info[0][0]['campaigns'][c]['L']==7)]['input_sha256']
        bad=[k for k in ('L7_coord.txt','L7_coord.txt.idx','cgamma_L7.txt') if pm.get(k)!=ref.get(k)]
        if bad:raise ValueError('primitive campaign numerical inputs differ from the batches: '+', '.join(bad))
        config['sources'].append({'name':'primitive/'+pd.name,'campaign':'primitive','level':'primitive','role':'estimator','L':7,'kind':'free','weight':1,'path':os.path.relpath(pd/'merged'/'N0.json',out)})
        config['retained_primitive_crosscheck']=config['retained_primitive'];config['retained_primitive']=None
    publish_or_verify(out/'combined_assembly.json',json.dumps(config,indent=2,allow_nan=False)+'\n')
    result=assemble(config,out,cache)
    per=[]
    for b,(_,m) in zip(batches,info):
        r=assemble(json.loads((b/'assembly.json').read_text()),b,cache);per.append({'label':m['label'],'C7_full':r['C7_full'],'sampling_se':r['sampling_se']})
    # Inter-batch scatter checks the replicate-based standard errors (each batch carries the same primitive, a shared constant).
    # Per-batch results contain the retained primitive; centre on the combined estimate with that same primitive, so
    # the chi2 of the non-primitive batches does not change when the primitive input is replaced.
    ps=first['retained_primitive']['sampling_se'];centre=result['C7_full']-(result['primitive_source']['mean_C7']-first['retained_primitive']['mean'] if a.primitive else 0.)
    chi2=sum((x['C7_full']-centre)**2/(x['sampling_se']**2-ps**2) for x in per) if K>1 else None
    result['batches']={'count':K,'per_batch':per,'chi2_about_combined':chi2,'dof':K-1,'chi2_centre':centre,'note':'per-batch SE excludes the shared primitive SE in the chi2; centre uses the retained primitive, as the per-batch results do'}
    new=publish_or_verify(out/'C7_final.json',result_text(result))
    print(json.dumps({'batches':K,'C7_full':result['C7_full'],'sampling_se':result['sampling_se'],'allowance_headline_2sf':result['allowance']['headline_2sf'],'chi2':chi2,'dof':K-1,'written':new},indent=2))
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,ArithmeticError) as e:print('Combine failed:',e,file=sys.stderr);sys.exit(2)
