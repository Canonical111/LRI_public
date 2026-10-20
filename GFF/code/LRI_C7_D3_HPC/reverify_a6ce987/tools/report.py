#!/usr/bin/env python3
"""Read-only re-verification and report of a FINISHED C7(3) campaign, including campaigns planned and run with the
delivered tools (manifest schema c7-d3-production-1, e.g. run1 on symmetry, 2026-09-30).

  report.py RUN --output FILE [--bootstrap N]

Checks by data identity only (the tools and executable that produced the campaign are NOT required): the manifest
schema, every group config against the manifest's hash, every merged.json (schema, completeness, manifest and config
hashes, payload hash, sector, loop, replicate count, shape) and its graph_replicates.csv digest, the expected group set
(campaigns a, b x sectors free, power x the plan's loops) and the campaign weights. Assembly inputs are verified
against the campaign's inputs manifest hash (assemble.verified_inputs). The assembly is recomputed with
assemble.calculate; when the campaign holds a result file, C7, its SE and the coefficient vector must equal it: bit for
bit on the CPU type that assembled it, otherwise to relative 1e-12 (recorded: the float64 assembly depends on the CPU
type through NumPy/OpenBLAS SIMD paths).
The report adds every consistency gate (assemble.gate_checks). Test-only campaigns are refused. Nothing is written
inside RUN.
"""
from __future__ import annotations
import argparse,datetime,hashlib,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,canon,digest,dump,host_info,load,object_hash,read_verified
import assemble
SCHEMAS={'c7-d3-production-1':'c7-d3-group-1','c7-d3-production-2':'c7-d3-group-2'}
EXISTING_REL=1e-12

class ReportError(Exception):
    def __init__(self,code,msg):super().__init__(msg);self.code=code

def merged_of(p:Path,cfg:dict,m:dict,mh:str)->dict:
    d=load(p/'merged.json')
    if d.get('schema')!='c7-d3-merged-1'or d.get('dimension')!=3 or d.get('complete')is not True or d.get('manifest_sha256')!=mh or d.get('config_hash')!=object_hash(cfg)\
       or d.get('primitive_mode')!=m['primitive_mode']or d.get('L')!=cfg['L']or d.get('sector')!=cfg['sector']:
        raise ReportError(1,'merged.json does not belong to this campaign: '+str(p/'merged.json'))
    if object_hash({k:v for k,v in d.items()if k!='payload_sha256'})!=d.get('payload_sha256'):raise ReportError(1,'merged payload checksum mismatch: '+str(p/'merged.json'))
    if digest(p/'graph_replicates.csv')!=d['graph_replicates_sha256']:raise ReportError(1,'Checksum mismatch: '+str(p/'graph_replicates.csv'))
    if d.get('replicates')!=cfg['replicates']or len(d['batches'])!=cfg['replicates']:raise ReportError(1,'merged replicate count mismatch: '+str(p/'merged.json'))
    return d

def load_finished(run:Path):
    data=(run/'manifest.json').read_bytes();m=json.loads(data);mh=hashlib.sha256(data).hexdigest()
    if m.get('schema')not in SCHEMAS:raise ReportError(64,f'unsupported campaign schema {m.get("schema")}')
    if m.get('dimension')!=3 or m.get('order')!=7:raise ReportError(64,'not a C7(3) campaign')
    if m.get('test_only'):raise ReportError(64,'test-only campaign (--test-graphs): not a physical result; its partial values are in assemble.py\'s C7_test_result.json')
    if m.get('campaign_weights')!={'a':.5,'b':.5}:raise ReportError(1,'changed campaign weights')
    loops=list(m['loops'])if m['schema']=='c7-d3-production-2'else[3,4,5,6,7]
    want={(t,s,L)for t in 'ab'for s in ('free','power')for L in loops};seen=set();hashes={}
    ar={s:{t:{}for t in ('a','b')}for s in ('free','power')}
    for g in m['groups']:
        p=run/'groups'/g['name'];cfg=read_verified(p/'config.json',g['sha256'])
        if cfg.get('schema')!=SCHEMAS[m['schema']]:raise ReportError(1,'wrong group config schema: '+g['name'])
        key=(cfg['campaign'],cfg['sector'],cfg['L'])
        if key in seen:raise ReportError(1,'duplicate group '+g['name'])
        seen.add(key);d=merged_of(p,cfg,m,mh);x=np.asarray(d['batches'],float)
        if x.shape!=(cfg['replicates'],2*(8-cfg['L'])):raise ReportError(1,'wrong data shape: '+g['name'])
        ar[cfg['sector']][cfg['campaign']][cfg['L']]=x;hashes[g['name']]=digest(p/'merged.json')
    if seen!=want:raise ReportError(1,f'merged groups {sorted(seen)} do not match the plan {sorted(want)}')
    return m,mh,ar,hashes

def report(run:Path,bootstrap:int|None=None)->dict:
    run=run.resolve();m,mh,ar,hashes=load_finished(run)
    vi=assemble.verified_inputs(m['inputs_manifest_sha256']);refs,rsha=assemble.references()
    existing=run/'C7_result.json';prior=load(existing)if existing.exists()else None
    if bootstrap is None:
        # Default: the existing result's bootstrap count (0 when it was assembled with --bootstrap 0, i.e. bootstrap:
        # null), else 4096 when the campaign has no result yet.
        bootstrap=int(((prior.get('bootstrap')or{}).get('replicates')or 0))if prior is not None else 4096
    primitive=vi['primitive']if m['primitive_mode']=='retained'else None
    r=assemble.calculate(ar,primitive,bootstrap,vi['B2']);checks=assemble.gate_checks(r,refs)
    match=None
    if prior is not None:
        # Bitwise on the CPU type that assembled the result; on another type the float64 assembly may differ in the
        # last bits (NumPy/OpenBLAS SIMD dispatch), which is accepted up to EXISTING_REL and reported.
        keys=('C7_full','sampling_standard_error','coefficients');same={k:canon(prior.get(k))==canon(r[k])for k in keys}
        rel={k:assemble.rounding_difference(prior.get(k),r[k],EXISTING_REL)for k in keys}
        bad=[k for k in keys if rel[k]is None]
        if bad:raise ReportError(1,f'the recomputed assembly differs from {existing} beyond float rounding: '+', '.join(bad))
        match={'path':str(existing),'sha256':digest(existing),'identical':sorted(k for k in keys if same[k]),'bitwise':all(same.values()),
               'max_relative_difference':max(rel.values()),'tolerance_relative':EXISTING_REL,'bootstrap_replicates_of_existing':(prior.get('bootstrap')or{}).get('replicates',0)}
    return {'schema':'c7-d3-report-1','generated_utc':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),'host':host_info(),
            'campaign':{'directory':str(run),'manifest_schema':m['schema'],'manifest_sha256':mh,'seed':m.get('seed'),'seed_scheme':m.get('seed_scheme','legacy (delivered tools)'),
                        'backend':m['backend'],'executable_sha256':m['executable_sha256'],'primitive_mode':m['primitive_mode'],'loops':sorted({L for s in ar for t in ar[s]for L in ar[s][t]}),
                        'replicates':{n:len(load(run/'groups'/n/'merged.json')['batches'])for n in hashes},'merged_sha256':hashes},
            'C7_full':r['C7_full'],'sampling_standard_error':r['sampling_standard_error'],'max_order':r['max_order'],'checks':checks,'existing_result':match,
            'assembly':r,'provenance':{'input_sha256':vi['sha256'],'references_sha256':rsha,'tool_sha256':assemble.provenance()},
            'scope':'Read-only re-verification by data identity and re-assembly; sampling precision only. Consistency gates are reported, never used as constraints.'}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('directory',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bootstrap',type=int,help='bootstrap replicates (default: those of the existing result, 0 if it has none; 4096 without a result)');a=p.parse_args(argv)
    run=a.directory.resolve();out=a.output.resolve()
    try:
        if out==run or run in out.parents:raise ReportError(64,f'refusing to write inside the campaign directory {run}')
        if a.bootstrap is not None and(a.bootstrap<0 or a.bootstrap==1):raise ReportError(64,'bootstrap must be zero or >= 2')
        doc=report(run,a.bootstrap)
    except ReportError as e:print('C7 report: '+str(e),file=sys.stderr);return e.code
    except ValueError as e:print('C7 report: '+str(e),file=sys.stderr);return 1
    if out.exists():print(f'C7 report: {out} exists; not overwritten',file=sys.stderr);return 1
    dump(out,doc)
    ex=doc['existing_result'];print(json.dumps({'C7_full':doc['C7_full'],'sampling_standard_error':doc['sampling_standard_error'],'max_order':doc['max_order'],'existing_result_bitwise':ex and ex['bitwise'],'existing_result_max_relative_difference':ex and ex['max_relative_difference'],'host':doc['host'],'output':str(out)}))
    for line in assemble.summary_lines({'checks':doc['checks']}):print(line)
    return 0
if __name__=='__main__':sys.exit(main())
