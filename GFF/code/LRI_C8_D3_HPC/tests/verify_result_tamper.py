#!/usr/bin/env python3
"""A-ASM-7 and A-ASM-6 on synthetic data (Mac).

A-ASM-7  tools/verify_result.py accepts an untouched result and its test-only, pilot and partial forms, and rejects a
         tampered value (C8, a coefficient, a mean, a stored pull, a gate value), a forged null-row flag, a deleted
         gates block (and a deleted gate in it), an added key (top level, inside a block, inside test_partial), a
         physical number at the top level of a test result, error_by_loop not summing to Var(C8), power_free_se or
         power_free_correction_covariance changed alone (the variance identity); it recomputes the a/b pull and
         bootstrap-ratio flags (changed inputs or forged flags are rejected), the PP8 marker (deleted, forged or moved
         to order 7) and the coverage records, the campaign record included (groups, graphs, source = campaign role; null
         only for test; deleted or nulled rejected); it requires the provenance its writer always records (evaluate:
         EVAL_PROV, the tail monitor, a role matching the label, 24 merged groups; combine: batches, combined_from) and
         the tail monitor's flags following from its listed rows; error_by_loop's schema and every share and se recomputed
         from its variances (S3-008: a changed share or se, a deleted share, an added loop, sector or row key rejected);
         a combined result's batch invariants (S3-007): a one-of-two partial promoted to a final production result, a
         per_batch or combined_from row removed or repeated, a forged dof or chi-square, a deleted design identity or
         batch role, a test-only role in a final result and mixed roles are rejected; S3-R2-003: non-finite batch
         statistics (a NaN or infinite per-batch C8, an infinite or NaN SE, a NaN or infinite stored chi-square, Codex's
         per_batch C8 and chi-square both 1e309) are rejected in process, and a result FILE holding NaN, Infinity or an
         overflowing literal 1e309 is rejected by `verify_result.py FILE` (exit 1); S3-R2-007: the scientific identities
         (science_sha256, per group; per batch in combined_from) are required and well formed. tools/assemble.coverage_guard (the non-test assemble) refuses one L8
         group removed, one graph removed, one bundle counts file removed or altered (its digest), counts other than
         the bundle counts x s, and accepts the complete campaign.
A-ASM-6  tools/combine.combine_batches accepts two complete batches of one bundle (the result verifies) and refuses a
         different bundle, a repeated group seed, a different numerics profile, a different rates identity, a different
         inputs manifest, a test-only batch beside a production one in either order (D.16), a different campaign role,
         a role other than production or test, and too few batches without --partial (and --partial for the full
         count); two test-only batches give a partial result; a partial combination holds no physical number at the
         top level; the chi-square equals the hand value.
The end-to-end refusals of `assemble` and `combine` on real campaign directories are in tests/test_pipeline.py.
Usage: python3 -B tests/verify_result_tamper.py [--output FILE]"""
from __future__ import annotations
import argparse,copy,hashlib,json,math,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import assemble as asm  # noqa: E402
import combine  # noqa: E402
import verify_result as vr  # noqa: E402
from assembly_checks import synthetic_ar  # noqa: E402

def jl(x):return json.loads(json.dumps(x,allow_nan=False))

GRAPHS=24173
SCI={'graph_replicates.csv':'a'*64,'graph_tails.csv':'b'*64,'graph_promotions.csv':'c'*64,'graph_prefixes.csv':None,'merged_science':'e'*64}   # a group_science record
def evaluated(core:dict,role:str)->dict:
    """An assemble.evaluate-shaped result of campaign role `role` around the values `core`: the tail monitor (one listed L8
    graph with a 5% share, so one flag) beside the values, the campaign coverage record (null for test), the view of the
    role, and the provenance keys at the top (as evaluate writes them)."""
    r=copy.deepcopy(core);row={'sector':'power','L':8,'graph':5,'xi_a':0.5,'xi_b':0.48,'xi_mean':0.49,'listed':'possible infinite variance (production)','share':{'a':0.05,'b':0.01}}
    r['tail_monitor']={'rule':'test','listed':[row],'flags':[{**row,'flag':'more than 3% of its group variance: for the results review'}],'undefined':[],'diagnostics_L_le_7':[],'graphs':GRAPHS}
    r['gates']['coverage']['campaign']=None if role=='test'else{'groups':24,'graphs':2*GRAPHS,'source':role}
    groups=[f'{c}_{s}_L{L}'for c in 'ab'for s in asm.SECTORS for L in range(3,9)]
    prov=dict(source_manifest_sha256='5'*64,merged_sha256={g:'6'*64 for g in groups},science_sha256={g:SCI for g in groups},backend='gmp',build={'exe':'bin/c8d3_gmp'},
              numerics='exact',mp_check='on',campaign_role=role,test_only=role=='test',allocation=None,two_loop_sha256='7'*64,references_sha256='8'*64,tool_sha256={'assemble.py':'9'*64})
    if role=='test':r=asm.test_only_view(r)
    elif role=='pilot_full':r=asm.pilot_view(r)
    else:r['label']='production';r['final']=True
    r.update(prov);return jl(r)

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path);a=ap.parse_args()
    results,failed=[],[]
    def check(name:str,ok:bool,detail='')->None:
        detail=detail if isinstance(detail,str)else json.dumps(detail,default=str)
        results.append(dict(check=name,passed=bool(ok),detail=detail[-600:]))
        if not ok:failed.append(name)
        print(('PASS 'if ok else 'FAIL ')+name+(f': {detail[-300:]}'if detail and not ok else''),flush=True)
    def verifies(x)->str:
        try:vr.verify(x);return ''
        except (vr.Mismatch,ValueError,KeyError,TypeError,ArithmeticError)as e:return f'{type(e).__name__}: {e}'
    B2,_=asm.two_loop(8)
    core=jl(asm.combine(synthetic_ar(np.random.default_rng(777),R=8),8,asm.HALF_D,8,B2))
    r=evaluated(core,'production')
    check('an untouched result verifies',verifies(r)=='',verifies(r))
    comb=copy.deepcopy(core);comb['batches']={'count':1,'planned':2,'per_batch':[{'label':'x','C8':core['C8_full'],'sampling_se':core['sampling_standard_error']}],
                                              'chi2_about_combined':None,'dof':0,'design_meta_sha256':'d'*64}
    comb['combined_from']=[{'run':'/runs/x','merged_sha256':{},'science_sha256':{},'campaign_role':'production','test_only':False}]
    views={'test':evaluated(core,'test'),'pilot':evaluated(core,'pilot_full'),'partial':jl(asm.hidden_view(comb,'partial_values','partial','p'))}
    for k,x in views.items():check(f'its {k} form verifies',verifies(x)=='',verifies(x))
    to=views['test'];po=views['pilot'];cases=[]
    def case(name,base,f):
        t=copy.deepcopy(base);f(t);cases.append((name,t))
    case('a tampered C8_full (relative 1e-6)',r,lambda t:t.__setitem__('C8_full',t['C8_full']*(1+1e-6)))
    case('a tampered coefficient',r,lambda t:t['coefficients'].__setitem__(5,t['coefficients'][5]+1e-6*abs(t['coefficients'][5])+1e-300))
    case('a tampered loop-3 mean (the stored coefficients no longer follow)',r,lambda t:t['means']['free']['3'].__setitem__(0,t['means']['free']['3'][0]*1.001))
    case('a tampered stored pull',r,lambda t:t['lower_order_checks'][2].__setitem__('pull',t['lower_order_checks'][2]['pull']+0.01))
    for k in range(5):
        case(f'a forged order-{k+3} null-row flag',r,lambda t,k=k:t['power_null_checks']['null_rows'][k].__setitem__('flag',None if t['power_null_checks']['null_rows'][k]['flag']else'not proved zero'))
    case('a changed POWER_PROTOCOL pin',r,lambda t:t['power_protocol'].__setitem__('sha256','0'*64))
    case('a changed assembly module pin',r,lambda t:t['assembly'].__setitem__('module_sha256','0'*64))
    case('a tampered gate value',r,lambda t:t['gates']['hard']['top_slot']['rows'][0].__setitem__('dC_db',t['gates']['hard']['top_slot']['rows'][0]['dC_db']*1.001)
         if 'dC_db'in t['gates']['hard']['top_slot']['rows'][0]else t['gates']['hard']['top_slot']['rows'][0].__setitem__('L',99))
    case('a deleted gates block',r,lambda t:t.pop('gates'))
    case('a deleted gate inside the gates block',r,lambda t:t['gates']['hard'].pop('loop7'))
    case('an added top-level key',r,lambda t:t.__setitem__('extra',1))
    case('an added key inside a block',r,lambda t:t['power_protocol'].__setitem__('note','x'))
    case('error_by_loop no longer summing to Var(C8)',r,lambda t:t['error_by_loop']['free']['8'].__setitem__('variance',t['error_by_loop']['free']['8']['variance']*2))
    # S3-008: error_by_loop's derived values and keys (E.3, A-ASM-7)
    ebl=lambda t,s='free',L='8':t['error_by_loop'][s][L]
    case('an error_by_loop share changed (S3-008)',r,lambda t:ebl(t).__setitem__('share',ebl(t)['share']*1.5+0.01))
    case('an error_by_loop se changed (S3-008)',r,lambda t:ebl(t,'power','5').__setitem__('se',ebl(t,'power','5')['se']*2+1e-30))
    case('an error_by_loop share deleted (S3-008)',r,lambda t:ebl(t).pop('share'))
    case('an error_by_loop se deleted (S3-008)',r,lambda t:ebl(t,'power','3').pop('se'))
    case('an error_by_loop row key added (S3-008)',r,lambda t:ebl(t).__setitem__('note','x'))
    case('an error_by_loop loop added (S3-008)',r,lambda t:t['error_by_loop']['free'].__setitem__('9',{'variance':0.,'share':0.,'se':0.}))
    case('an error_by_loop sector added (S3-008)',r,lambda t:t['error_by_loop'].__setitem__('mixed',{}))
    case('an error_by_loop share changed in test_partial (S3-008)',to,lambda t:t['test_partial']['error_by_loop']['free']['7'].__setitem__('share',0.5))
    case('power_free_se changed alone (variance identity)',r,lambda t:t.__setitem__('power_free_se',t['power_free_se']*1.01))
    case('power_free_correction_covariance changed alone (variance identity)',r,lambda t:t.__setitem__('power_free_correction_covariance',t['power_free_correction_covariance']+0.05*abs(t['covariance'][8][8])))
    case('a standard error changed alone',r,lambda t:t['standard_errors'].__setitem__(8,t['standard_errors'][8]*1.01))
    case('a test-only result with a physical value at the top level',to,lambda t:t.__setitem__('C8_full',t['test_partial']['C8_full']))
    case('a tampered test-only partial value',to,lambda t:t['test_partial']['coefficients'].__setitem__(8,t['test_partial']['coefficients'][8]+1.))
    case('a key added to test_partial',to,lambda t:t['test_partial'].__setitem__('extra',1))
    case('a key deleted from test_partial',to,lambda t:t['test_partial'].pop('power_free_correction_covariance'))
    case('a test result marked final',to,lambda t:t.__setitem__('final',True))
    case('a test result holding two hidden blocks',to,lambda t:t.__setitem__('sizing_only',t['test_partial']))
    # the recomputed flags: the a/b pull, the bootstrap ratio, the PP8 marker, the coverage records
    case('a changed campaign-b C8 (the stored a/b pull no longer follows)',r,lambda t:t['campaigns']['b'].__setitem__('C8',t['campaigns']['b']['C8']+10*t['campaigns']['b']['sampling_se']))
    case('a forged a/b pull flag',r,lambda t:t['gates']['consistency']['campaign_pull'].__setitem__('flag',not t['gates']['consistency']['campaign_pull']['flag']))
    case('a changed bootstrap SE (the stored ratio no longer follows)',r,lambda t:t['bootstrap']['full_se'].__setitem__(8,t['bootstrap']['full_se'][8]*3))
    case('a forged bootstrap-ratio flag',r,lambda t:t['gates']['consistency']['bootstrap_ratio'].__setitem__('flag',not t['gates']['consistency']['bootstrap_ratio']['flag']))
    case('a forged PP8 marker at order 7',r,lambda t:t['gates'].__setitem__('pp8',[{'order':7,'pp8':asm.PP8_TEXT}]))
    case('a forged coverage record (loops 3..7)',r,lambda t:t['gates']['coverage'].__setitem__('loops',[3,4,5,6,7]))
    case('a forged coverage record (complete false)',r,lambda t:t['gates']['coverage'].__setitem__('complete',False))
    case('a forged affinity-loops record',r,lambda t:t['gates']['coverage'].__setitem__('affinity_loops',[5,6,7]))
    # the campaign coverage record and the provenance assemble.evaluate always writes (Stage 3a repair round 1)
    cc=lambda t:t['gates']['coverage']['campaign']
    case('a campaign coverage record with 23 groups',r,lambda t:cc(t).__setitem__('groups',23))
    case('a campaign coverage record with another graph count',r,lambda t:cc(t).__setitem__('graphs',2*GRAPHS-2))
    case('a campaign coverage source production -> pilot_full',r,lambda t:cc(t).__setitem__('source','pilot_full'))
    case('a campaign coverage record set to null (production)',r,lambda t:t['gates']['coverage'].__setitem__('campaign',None))
    case('a campaign coverage record deleted',r,lambda t:t['gates']['coverage'].pop('campaign'))
    case('a campaign coverage record set to null (pilot)',po,lambda t:t['sizing_only']['gates']['coverage'].__setitem__('campaign',None))
    case('a campaign coverage source pilot_full -> production (pilot)',po,lambda t:t['sizing_only']['gates']['coverage']['campaign'].__setitem__('source','production'))
    case('a campaign coverage record on a test result',to,lambda t:t['test_partial']['gates']['coverage'].__setitem__('campaign',{'groups':24,'graphs':2*GRAPHS,'source':'test'}))
    for k in ('source_manifest_sha256','merged_sha256','campaign_role','tool_sha256'):
        case(f'a deleted provenance key {k}',r,lambda t,k=k:t.pop(k))
        case(f'a deleted provenance key {k} (pilot)',po,lambda t,k=k:t.pop(k))
    case('a deleted tail monitor',r,lambda t:t.pop('tail_monitor'))
    case('a deleted tail monitor (pilot)',po,lambda t:t['sizing_only'].pop('tail_monitor'))
    case('a tail-monitor flag removed',r,lambda t:t['tail_monitor'].__setitem__('flags',[]))
    case('a tail-monitor flag forged (share 1%)',r,lambda t:t['tail_monitor']['listed'][0]['share'].__setitem__('a',0.01))
    case('a tail-monitor graph count changed',r,lambda t:t['tail_monitor'].__setitem__('graphs',GRAPHS-1))
    case('a campaign role that does not match the label (production result, role pilot_full)',r,lambda t:t.__setitem__('campaign_role','pilot_full'))
    case('a pilot result relabelled production',po,lambda t:t.__setitem__('label','production'))
    case('merged_sha256 naming 23 groups',r,lambda t:t['merged_sha256'].pop('a_free_L3'))
    # S3-R2-007: the scientific identities assemble.evaluate always writes
    case('a deleted science_sha256 (S3-R2-007)',r,lambda t:t.pop('science_sha256'))
    case('a deleted science_sha256 (pilot; S3-R2-007)',po,lambda t:t.pop('science_sha256'))
    case('science_sha256 naming 23 groups (S3-R2-007)',r,lambda t:t['science_sha256'].pop('a_free_L3'))
    case('a science record without merged_science (S3-R2-007)',r,lambda t:t['science_sha256']['a_free_L3'].pop('merged_science'))
    case('a science record with a non-digest table hash (S3-R2-007)',r,lambda t:t['science_sha256']['b_power_L8'].__setitem__('graph_tails.csv','x'))
    # a flagged order-6 row: the PP8 marker is recomputed; deleting or moving it is rejected
    f6=copy.deepcopy(r);f6['power_differences'][6]=f6['power_difference_errors'][6]*10+f6['power_free_coefficients'][6]*0;f6['coefficients'][6]=f6['power_free_coefficients'][6]+f6['power_differences'][6]
    pn=jl(asm.power_null_checks(np.asarray(f6['power_differences']),np.asarray(f6['power_difference_errors']),8));f6['power_null_checks']=pn
    f6['gates']=jl(asm.gates_block(f6,8));pp8_present=bool(f6['gates']['pp8'])and f6['gates']['pp8'][0]['order']==6
    check('an order-6 flag carries the PP8 marker in the gates block (recomputed from power_differences)',pp8_present,f6['gates']['pp8'])
    t=copy.deepcopy(f6);t['gates']['pp8']=[];reason=verifies(t);check('rejects a deleted PP8 marker',bool(reason),'accepted')
    t=copy.deepcopy(f6);t['power_null_checks']['null_rows'][3]['pp8']=None;reason=verifies(t);check('rejects a PP8 marker removed from its null row',bool(reason),'accepted')
    for name,t in cases:
        reason=verifies(t);check(f'rejects {name}',bool(reason),'accepted'if not reason else reason)
    # the coverage guard (the non-test assemble): a synthetic inventory and design bundle
    rng=np.random.default_rng(5);inv={s:{str(L):[{'id':i,'primitive':bool(s=='free'and L==8 and i%3==0)}for i in range(1,3+L)]for L in range(3,9)}for s in asm.SECTORS}
    S={f'{s}_L{L}':2 for s in asm.SECTORS for L in range(3,9)};S['free_L8_primitive']=3;R={f'{s}_L{L}':4 for s in asm.SECTORS for L in range(3,9)}
    with tempfile.TemporaryDirectory(prefix='c8d3_bundle_')as td:
        b=Path(td);(b/'counts').mkdir();dg={};cfgs={}
        for c in asm.CAMPAIGNS:
            for s in asm.SECTORS:
                for L in range(3,9):
                    fr={row['id']:int(rng.integers(1,5))*1024 for row in inv[s][str(L)]};name=f'counts/{c}_{s}_L{L}.txt'
                    data=''.join(f'{k} {v}\n'for k,v in sorted(fr.items())).encode();(b/name).write_bytes(data);dg[name]=hashlib.sha256(data).hexdigest()
                    mult=lambda g,s=s,L=L:S['free_L8_primitive'if(s=='free'and L==8 and next(x for x in inv[s][str(L)]if x['id']==g)['primitive'])else f'{s}_L{L}']
                    cfgs[(c,s,L)]={'counts':{str(k):v*mult(k)for k,v in fr.items()},'replicates':4}
        (b/'design_meta.json').write_text(json.dumps({'counts_sha256':dg}))
        m={'campaign_role':'production','design':{'bundle':str(b),'meta_sha256':asm.digest(b/'design_meta.json'),'s':S,'r':R}}
        cg=asm.coverage_guard(m,cfgs,inv);check('the coverage guard accepts the complete campaign (24 groups, counts = bundle counts x s)',cg['groups']==24,cg)
        def refuses(name,mm,cc):
            try:asm.coverage_guard(mm,cc,inv);check(f'the coverage guard refuses {name}',False,'accepted')
            except ValueError as e:check(f'the coverage guard refuses {name}',True,str(e))
        g=dict(cfgs);del g[('a','free',8)];refuses('a campaign with one L8 group removed',m,g)
        g=copy.deepcopy(cfgs);g[('b','power',8)]['counts'].pop(next(iter(g[('b','power',8)]['counts'])));refuses('a group with one graph removed',m,g)
        g=copy.deepcopy(cfgs);k=next(iter(g[('a','power',5)]['counts']));g[('a','power',5)]['counts'][k]*=2;refuses('counts other than the bundle counts x s',m,g)
        g=copy.deepcopy(cfgs);g[('a','power',5)]['replicates']=5;refuses('replicates other than the bundle r',m,g)
        p=b/'counts/a_free_L8.txt';orig=p.read_bytes();p.write_bytes(orig.replace(b'\n',b'0\n',1));refuses('a bundle counts file altered after the freeze (its digest)',m,cfgs)
        p.unlink();refuses('a bundle counts file removed',m,cfgs);p.write_bytes(orig)
        meta=b/'design_meta.json';mo=meta.read_bytes();meta.write_bytes(mo+b' ');refuses('a design_meta.json other than the planned one',m,cfgs);meta.write_bytes(mo)
        check('the restored bundle is accepted again',asm.coverage_guard(m,cfgs,inv)['groups']==24)
    # A-ASM-6: combine_batches
    def batch(label,seed,seeds,**kw):
        d=dict(run=f'/runs/{label}',label=label,meta_sha256='d'*64,inputs_manifest_sha256='i'*64,numerics='exact',rates_identity='default',test_only=False,
               campaign_role='production',planned_batches=2,seeds=seeds,ar=synthetic_ar(np.random.default_rng(seed),R=6),graphs={'a:free:3':[1,2]},merged_sha256={},
               science_sha256={})
        d.update(kw);return d
    b1,b2=batch('sym',11,list(range(24))),batch('exp',22,list(range(100,124)))
    fin=jl(combine.combine_batches([b1,b2],bootstrap=0,B2=B2))
    check('A-ASM-6: two complete batches of one bundle are accepted, final, and verify',fin['final']is True and fin['label']=='production'and verifies(fin)=='',verifies(fin))
    per=fin['batches']['per_batch'];hand=sum((x['C8']-fin['C8_full'])**2/x['sampling_se']**2 for x in per)
    sep=[asm.combine(b['ar'],8,asm.HALF_D,0,B2)for b in (b1,b2)]
    check('A-ASM-6: the chi-square equals the hand value (K - 1 = 1 dof; per-batch C8 recomputed alone)',abs(fin['batches']['chi2_about_combined']-hand)<=1e-12*hand and fin['batches']['dof']==1
          and all(x['C8']==y['C8_full']and x['sampling_se']==y['sampling_standard_error']for x,y in zip(per,sep)),dict(stored=fin['batches']['chi2_about_combined'],hand=hand))
    def refused(name,bs,**kw):
        try:combine.combine_batches(bs,bootstrap=0,B2=B2,**kw);check(f'A-ASM-6: combine refuses {name}',False,'accepted')
        except ValueError as e:check(f'A-ASM-6: combine refuses {name}',True,str(e))
    refused('a batch of a different bundle',[b1,batch('exp',22,list(range(100,124)),meta_sha256='e'*64)])
    refused('a repeated group seed',[b1,batch('exp',22,list(range(23,47)))])
    refused('a different numerics profile',[b1,batch('exp',22,list(range(100,124)),numerics='fast')])
    refused('a different rates identity',[b1,batch('exp',22,list(range(100,124)),rates_identity='{"a": [".7"], "b": [".7"]}')])
    refused('a different inputs manifest',[b1,batch('exp',22,list(range(100,124)),inputs_manifest_sha256='j'*64)])
    refused('a different graph set',[b1,batch('exp',22,list(range(100,124)),graphs={'a:free:3':[1]})])
    # D.16 test-only result separation (Stage 3a repair round 2): a test-only design batch (role test) never joins a
    # production batch, in either order; two test-only batches give a partial (non-final) result; another role is refused
    tb=batch('test1',33,list(range(200,224)),test_only=True,campaign_role='test')
    refused('a production batch followed by a test-only batch',[b1,tb]);refused('a test-only batch followed by a production batch',[tb,b1])
    refused('a batch whose campaign_role differs (test_only equal)',[b1,batch('exp',22,list(range(100,124)),campaign_role='test')])
    refused('two batches of campaign_role pilot_full',[batch('p1',11,list(range(24)),campaign_role='pilot_full'),batch('p2',22,list(range(100,124)),campaign_role='pilot_full')])
    tt=jl(combine.combine_batches([tb,batch('test2',44,list(range(300,324)),test_only=True,campaign_role='test')],bootstrap=0,B2=B2))
    check('A-ASM-6/D.16: two complete test-only batches give a partial, non-final result that verifies',tt['final']is False and tt['label']=='partial'
          and tt['C8_full']is None and verifies(tt)=='',verifies(tt))
    refused('too few batches without --partial',[b1])
    refused('--partial with the full batch count',[b1,b2],partial=True)
    par=jl(combine.combine_batches([b1],partial=True,bootstrap=0,B2=B2))
    check('A-ASM-6: a partial combination is not final, holds no physical number at the top level and verifies',par['final']is False and par['C8_full']is None
          and par['partial_values']['C8_full']is not None and verifies(par)=='',verifies(par))
    t=copy.deepcopy(par);t['final']=True;check('rejects a partial combination marked final',bool(verifies(t)),'accepted')
    for name,f in (('combined_from deleted',lambda t:t.pop('combined_from')),('batches deleted',lambda t:t.pop('batches')),('a campaign_role added',lambda t:t.__setitem__('campaign_role','production'))):
        t=copy.deepcopy(fin);f(t);check(f'rejects a combined result with {name}',bool(verifies(t)),'accepted')
    # S3-007: the combined result's roles, design identity and batch-count invariants
    check('S3-007: a final combination records the design identity and every batch role',fin['batches']['design_meta_sha256']=='d'*64
          and [(x['campaign_role'],x['test_only'])for x in fin['combined_from']]==[('production',False)]*2 and tt['partial_values']['combined_from'][0]['test_only']is True,fin['combined_from'])
    def promoted(p):   # a one-of-two partial result's values moved to the top level, labelled production and final (Codex's S3-007 case)
        t={k:v for k,v in copy.deepcopy(p).items()if k!='partial_values'};t.update(copy.deepcopy(p['partial_values']));t['label']='production';t['final']=True;return t
    bad7=[('a one-of-two partial result promoted to a final production result',promoted(par)),
          ('two test-only batches promoted to a final production result',promoted(tt))]
    def b7(name,base,f):t=copy.deepcopy(base);f(t);bad7.append((name,t))
    pv=lambda t:t.get('partial_values')or t
    b7('a per_batch row removed',fin,lambda t:t['batches']['per_batch'].pop())
    b7('a per_batch row repeated (count 3)',fin,lambda t:(t['batches']['per_batch'].append(t['batches']['per_batch'][0]),t['batches'].__setitem__('count',3)))
    b7('a combined_from row removed',fin,lambda t:t['combined_from'].pop())
    b7('a combined_from row repeated',fin,lambda t:t['combined_from'].__setitem__(1,t['combined_from'][0]))
    b7('a forged dof',fin,lambda t:t['batches'].__setitem__('dof',5))
    b7('a forged chi-square',fin,lambda t:t['batches'].__setitem__('chi2_about_combined',t['batches']['chi2_about_combined']*1.01+1e-9))
    b7('a count above planned',fin,lambda t:t['batches'].__setitem__('planned',1))
    b7('a deleted design identity',fin,lambda t:t['batches'].pop('design_meta_sha256'))
    b7('a deleted batch role',fin,lambda t:t['combined_from'][0].pop('campaign_role'))
    b7('a test-only batch role in a final result',fin,lambda t:t['combined_from'][1].update(campaign_role='test',test_only=True))
    b7('test-only roles throughout a final result',fin,lambda t:[x.update(campaign_role='test',test_only=True)for x in t['combined_from']])
    b7('a pilot_full batch role',par,lambda t:pv(t)['combined_from'][0].update(campaign_role='pilot_full'))
    b7('a partial combination of the full planned production count',par,lambda t:pv(t)['batches'].__setitem__('planned',1))
    for name,t in bad7:check(f'S3-007: rejects {name}',bool(verifies(t)),'accepted')
    # S3-R2-003: non-finite batch statistics, in process (Codex's case: per_batch C8 and the chi-square both 1e309 = inf)
    INF,NAN=float('inf'),float('nan');pb0=lambda t:t['batches']['per_batch'][0]  # noqa: E731
    def rechi(t):   # the stored chi-square recomputed from the tampered rows, so only the non-finite value is wrong
        b=t['batches'];c=t['C8_full'];b['chi2_about_combined']=sum((x['C8']-c)**2/x['sampling_se']**2 for x in b['per_batch'])
    bad3=[]
    def b3(name,f):t=copy.deepcopy(fin);f(t);bad3.append((name,t))
    b3('per_batch C8 and the chi-square both 1e309 (inf)',lambda t:(pb0(t).__setitem__('C8',1e309),t['batches'].__setitem__('chi2_about_combined',1e309)))
    b3('a NaN per_batch C8 (chi-square left as stored)',lambda t:pb0(t).__setitem__('C8',NAN))
    b3('a NaN per_batch C8 (chi-square recomputed: NaN)',lambda t:(pb0(t).__setitem__('C8',NAN),rechi(t)))
    b3('an infinite per_batch sampling_se (chi-square recomputed)',lambda t:(pb0(t).__setitem__('sampling_se',INF),rechi(t)))
    b3('a NaN per_batch sampling_se',lambda t:pb0(t).__setitem__('sampling_se',NAN))
    b3('a NaN stored chi-square',lambda t:t['batches'].__setitem__('chi2_about_combined',NAN))
    b3('an infinite stored chi-square',lambda t:t['batches'].__setitem__('chi2_about_combined',INF))
    b3('a negative infinite per_batch C8',lambda t:(pb0(t).__setitem__('C8',-INF),t['batches'].__setitem__('chi2_about_combined',INF)))
    b3('a combined_from row without science_sha256 (S3-R2-007)',lambda t:t['combined_from'][0].pop('science_sha256'))
    b3('a combined_from science_sha256 naming another group (S3-R2-007)',lambda t:t['combined_from'][1]['science_sha256'].__setitem__('a_free_L3',SCI))
    for name,t in bad3:check(f'S3-R2-003: rejects {name}',bool(verifies(t)),'accepted')
    # ... and in a result FILE: the JSON constants NaN, Infinity, -Infinity and the overflowing literal 1e309 (verify_result.py FILE)
    with tempfile.TemporaryDirectory(prefix='c8d3_nonfinite_')as td:
        f=Path(td)/'C8_final.json';f.write_text(json.dumps(fin));check('S3-R2-003: the untouched combined result file verifies (exit 0)',vr.main([str(f)])==0)
        SENT=123456.78125   # a sentinel per_batch C8, replaced textually below
        for name,lit in (('NaN','NaN'),('Infinity','Infinity'),('-Infinity','-Infinity'),('1e309','1e309'),('-1e309','-1e309')):
            for where in ('C8','chi2'):
                t=copy.deepcopy(fin);pb0(t)['C8']=SENT
                if where=='chi2':t['batches']['chi2_about_combined']=SENT;pb0(t)['C8']=fin['batches']['per_batch'][0]['C8']
                text=json.dumps(t);assert text.count(repr(SENT))==1;f.write_text(text.replace(repr(SENT),lit))
                check(f'S3-R2-003: verify_result.py rejects a result file whose {"per_batch C8" if where=="C8" else "stored chi-square"} is the JSON {name}',vr.main([str(f)])==1)
        t=copy.deepcopy(fin);pb0(t)['C8']=SENT;t['batches']['chi2_about_combined']=SENT*2
        f.write_text(json.dumps(t).replace(repr(SENT*2),'1e309').replace(repr(SENT),'1e309'))
        check('S3-R2-003: verify_result.py rejects Codex\'s file (per_batch C8 and chi2_about_combined both the literal 1e309)',vr.main([str(f)])==1)
    rec=dict(schema='c8-d3-gate-1',gate='A-ASM-6/7 verify_result_tamper',passed=not failed,failed=failed,checks=results)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(f'verify_result_tamper: {len(results)-len(failed)}/{len(results)} checks passed')
    return 0 if not failed else 1
if __name__=='__main__':sys.exit(main())
