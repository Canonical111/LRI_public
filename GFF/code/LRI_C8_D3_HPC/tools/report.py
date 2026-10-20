#!/usr/bin/env python3
"""Read-only re-verification and report of a FINISHED C8(3) campaign (PLAN D.1 disposition; schema c8-d3-report-1).

  report.py RUN --output FILE [--bootstrap N]

Checks by data identity: the manifest and the vendored pins (production.verify_base with --accept-tool-change, so a
reporting fix applies to an existing campaign without re-planning; changed tools are recorded), every group config
against the manifest's hash, every merged.json (schema, completeness, hashes, payload, shape) and its tables. The
assembly is recomputed with assemble.combine (the vendored module); when the campaign holds its result file, C8, its SE
and the coefficient vector must equal it to relative 1e-12 (bitwise on the CPU type that assembled it), and the
stored result must pass tools/verify_result.py. A pilot_subset campaign is refused (65). Nothing is written inside RUN.
A test or pilot campaign's report holds no physical number (S3-009): its top-level C8 and sampling_standard_error are
null and its assembly is assemble.py's view of that role (values only under test_partial or sizing_only).
"""
from __future__ import annotations
import argparse,datetime,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Refuse,canon,digest,dump,host_info,load
import assemble as asm
EXISTING_REL=1e-12

def report(run:Path,bootstrap:int|None=None)->dict:
    run=Path(run).resolve();m,I,mh,ar,hashes,changes,cfgs,_=asm.load_campaign(run,accept_tool_change=True)
    role=m['campaign_role'];name={'test':'C8_test_result.json','pilot_full':'C8_pilot_result.json','production':'C8_result.json'}[role]
    existing=run/name;prior=load(existing)if existing.exists()else None
    if bootstrap is None:bootstrap=int(((asm.values_of(prior).get('bootstrap')or{}).get('replicates')or 0))if prior else 1024
    B2,b2sha=asm.two_loop(8,I.dir,I.m['sha256']);r=asm.combine(ar,8,asm.HALF_D,bootstrap,B2)
    match=None
    if prior is not None:
        import verify_result as vr
        vr.verify(prior);pv=asm.values_of(prior)
        keys=('C8_full','sampling_standard_error','coefficients');diff={}
        for k in keys:
            a,b=pv.get(k),r[k]
            if isinstance(a,list):diff[k]=max((abs(x-y)/max(abs(x),abs(y),1e-300)for x,y in zip(a,b)),default=0.)
            else:diff[k]=abs(a-b)/max(abs(a),abs(b),1e-300)
        bad=[k for k,v in diff.items()if v>EXISTING_REL]
        if bad:raise ValueError(f'the recomputed assembly differs from {existing} beyond float rounding: {bad}')
        match={'path':str(existing),'sha256':digest(existing),'bitwise':all(canon(pv.get(k))==canon(r[k])for k in keys),'max_relative_difference':max(diff.values()),
               'tolerance_relative':EXISTING_REL}
    view={'production':lambda x:x,'test':asm.test_only_view,'pilot_full':asm.pilot_view}[role](r);phys=role=='production'   # S3-009: assemble.py's views
    return {'schema':'c8-d3-report-1','generated_utc':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),'host':host_info(),
            'campaign':{'directory':str(run),'manifest_sha256':mh,'seed':m['seed'],'campaign_role':role,'backend':m['backend'],'executable_sha256':m['executable_sha256'],
                        'merged_sha256':hashes,'accepted_tool_changes':changes or None},
            'C8':r['C8_full']if phys else None,'sampling_standard_error':r['sampling_standard_error']if phys else None,'existing_result':match,'assembly':view,'two_loop_sha256':b2sha,
            'label':{'test':'test (no physical number)','pilot_full':'pilot (for sizing only, never an estimate)','production':'production'}[role],
            'scope':'Read-only re-verification by data identity and re-assembly; sampling precision only. Consistency gates are reported, never used as constraints.'}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('directory',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bootstrap',type=int);a=p.parse_args(argv)
    run=a.directory.resolve();out=a.output.resolve()
    try:
        if out==run or run in out.parents:raise Refuse(64,f'refusing to write inside the campaign directory {run}')
        if a.bootstrap is not None and(a.bootstrap<0 or a.bootstrap==1):raise Refuse(64,'bootstrap must be zero or >= 2')
        doc=report(run,a.bootstrap)
    except Refuse as e:print('C8 report: '+str(e),file=sys.stderr);return e.code
    except (ValueError,ArithmeticError)as e:print('C8 report: '+str(e),file=sys.stderr);return 1
    if out.exists():print(f'C8 report: {out} exists; not overwritten',file=sys.stderr);return 1
    dump(out,doc)
    print(json.dumps({'label':doc['label'],'C8':doc['C8']if doc['campaign']['campaign_role']=='production'else None,'existing_result':doc['existing_result'],'output':str(out)}))
    return 0
if __name__=='__main__':sys.exit(main())
