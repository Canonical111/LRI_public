#!/usr/bin/env python3
"""Combine K independent batches of one frozen design into one C8(3) result (PLAN E.4; port of combine8.py).

  combine.py BATCH [BATCH ...] --output DIR [--partial] [--bootstrap N]

A batch is a merged campaign planned with `production.py plan --design BUNDLE`. Every batch must share the bundle (the
sha256 of its design_meta.json), the inputs manifest, the numerics profile, the rates identity (the group configs'
rates: `default` = a .8, b .7) and the campaign role with its test_only flag (a test-only design campaign, role test,
never joins a production batch: D.16's test-only result separation, whatever the argument order), be
complete (every group's merged.json valid), and every group seed must be distinct across the batches. The replicates of
each (sector, campaign, L) are concatenated and assembled by tools/assemble.combine (the vendored order-8 module); C8
of every batch and the inter-batch chi-square about the combination (sum (C8_k - C8)^2 / SE_k^2, K - 1 dof) are
reported. The final combination needs exactly the bundle's batch count and campaign role production in every batch,
and is published as C8_final.json (final: true); --partial, and any combination of test-only batches, publishes
C8_partial.json (final: false, values under partial_values). A batch of another role is refused. A pilot_subset
campaign is refused (65) before any group data is read. Publication is no-clobber (assemble.publish_result): an
identical result is kept; one whose only change is a batch's merged_sha256 (combined_from; a group re-merged after a
recovered index, its science unchanged: every batch's scientific identity per group, combined_from[i].science_sha256,
equal; S3-R2-007) is superseded, the old bytes kept as <name>.superseded.<sha12>.json (F8-d3).
"""
from __future__ import annotations
import argparse,json,math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Refuse,digest,load
import assemble as asm
import production as prod

SAME=('meta_sha256','inputs_manifest_sha256','numerics','rates_identity','campaign_role','test_only')

def batch_of(run:Path)->dict:
    run=Path(run).resolve();m,I,mh,ar,hashes,changes,cfgs,science=asm.load_campaign(run)
    if not m.get('design'):raise ValueError(f'{run}: not a design campaign (--design BUNDLE): only batches of a frozen bundle are combined')
    rates={c:sorted({cfg['rate']for (cc,_,_),cfg in cfgs.items()if cc==c})for c in asm.CAMPAIGNS}
    ident='default'if all(rates[c]==[prod.RATES[c]]for c in asm.CAMPAIGNS)else json.dumps(rates,sort_keys=True)
    return {'run':str(run),'label':run.name,'meta_sha256':m['design']['meta_sha256'],'inputs_manifest_sha256':m['inputs_manifest_sha256'],'numerics':m['numerics'],'rates_identity':ident,
            'test_only':m['test_only'],'campaign_role':m['campaign_role'],'planned_batches':int(m['design']['batches']),'seeds':[cfg['seed']for cfg in cfgs.values()],'ar':ar,'I':I,
            'graphs':{f'{c}:{s}:{L}':sorted(cfg['counts'])for (c,s,L),cfg in cfgs.items()},'merged_sha256':hashes,'science_sha256':science}

def combine_batches(batches:list,partial:bool=False,bootstrap:int=1024,B2=None)->dict:
    if not batches:raise ValueError('no batch given')
    for k in SAME:
        if len({json.dumps(b[k])for b in batches})!=1:
            raise ValueError(f'the batches differ in {k}; batches of different bundles, inputs, numerics or campaign roles (test-only and production) cannot be combined')
    role=batches[0]['campaign_role'];test=bool(batches[0]['test_only'])
    if (role,test)not in(('production',False),('test',True)):raise ValueError(f'campaign_role {role!r} with test_only {test}: only production or test-only design batches are combined')
    if len({json.dumps(b['graphs'],sort_keys=True)for b in batches})!=1:raise ValueError('the batches integrate different graph sets in some group')
    if len({b['label']for b in batches})!=len(batches):raise ValueError('batch labels must be distinct')
    seeds=[s for b in batches for s in b['seeds']]
    if len(set(seeds))!=len(seeds):raise ValueError('a group seed repeats across batches: the batches are not independent')
    planned=batches[0]['planned_batches'];K=len(batches)
    if not partial and K!=planned:raise ValueError(f'the bundle plans {planned} batches; {K} given (use --partial for an interim combination)')
    if partial and K>=planned:raise ValueError('--partial is only for fewer batches than the bundle plans')
    ar={s:{t:{L:np.concatenate([np.asarray(b['ar'][s][t][L])for b in batches])for L in range(3,9)}for t in asm.CAMPAIGNS}for s in asm.SECTORS}
    r=asm.combine(ar,8,asm.HALF_D,bootstrap,B2)
    per=[]
    for b in batches:
        x=asm.combine(b['ar'],8,asm.HALF_D,0,B2);per.append({'label':b['label'],'C8':x['C8_full'],'sampling_se':x['sampling_standard_error']})
    chi2=sum((p['C8']-r['C8_full'])**2/p['sampling_se']**2 for p in per)if K>1 else None
    # S3-007: the design identity and every batch's role are persisted, so verify_result.combined_check re-derives finality
    r['batches']={'count':K,'planned':planned,'per_batch':per,'chi2_about_combined':chi2,'dof':K-1,'design_meta_sha256':batches[0]['meta_sha256']}
    # S3-R2-007: every batch's scientific identity per group (assemble.group_science) beside its merged.json sha256s, so a
    # re-merged batch supersedes a published combination only when its scientific tables are unchanged
    r['combined_from']=[{'run':b['run'],'merged_sha256':b['merged_sha256'],'science_sha256':b['science_sha256'],'campaign_role':b['campaign_role'],
                         'test_only':bool(b['test_only'])}for b in batches]
    if partial or role!='production':   # a final combination: every batch production (SAME), the bundle's batch count
        r=asm.hidden_view(r,'partial_values','partial',f'PARTIAL combination of {K} of {planned} planned batches: interim, not the final result; values only under partial_values.')
    else:r['label']='production';r['final']=True
    return r

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('batches',type=Path,nargs='+')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--partial',action='store_true');p.add_argument('--bootstrap',type=int,default=1024);a=p.parse_args(argv)
    try:
        bs=[batch_of(b)for b in a.batches]
        B2,_=asm.two_loop(8,bs[0]['I'].dir,bs[0]['I'].m['sha256'])
        r=combine_batches(bs,a.partial,a.bootstrap,B2)
        import verify_result as vr
        vr.verify(r)
        a.output.mkdir(parents=True,exist_ok=True)
        dest=a.output/('C8_partial.json'if r['label']=='partial'else'C8_final.json');state=asm.publish_result(dest,r)
    except Refuse as e:print(f'combine: {e}',file=sys.stderr);return e.code
    except ArithmeticError as e:print(f'combine: hard gate failed: {e}',file=sys.stderr);return 3
    except (ValueError,OSError)as e:print(f'combine: {e}',file=sys.stderr);return 1
    v=asm.values_of(r)
    print(json.dumps({'output':str(dest),'state':state,'label':r['label'],'final':r['final'],'C8':v['C8_full'],'sampling_se':v['sampling_standard_error'],
                      'chi2':v['batches']['chi2_about_combined'],'dof':v['batches']['dof']}))
    return 0
if __name__=='__main__':sys.exit(main())
