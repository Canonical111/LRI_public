#!/usr/bin/env python3
"""Run a defined set of fresh checks, without substituting cached success.

minimal: Python standard library; exact certificates, input-map audit, archives.
standard: also SymPy and mpmath; coefficient algebra and independent low-order
          integral checks. Neither level regenerates all raw kink integrations.
"""
from __future__ import annotations
import argparse,json,os,platform,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--level',choices=['minimal','standard'],default='minimal')
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output',type=Path,help='Default: verification/latest_<level>')
    p.add_argument('--timeout',type=int,default=240,help='Per-check timeout in seconds')
    args=p.parse_args();root=args.root.resolve()
    out=(args.output or root/'verification'/('latest_'+args.level)).resolve();out.mkdir(parents=True,exist_ok=True)
    py=sys.executable
    jobs=[
      ('archive_integrity','code/verify_manifest.py',['--archives-only','--report',str(out/'archive_integrity.json')]),
      ('D3_exact_certificate','stages/D3_exact/verify_D3_proof_standalone.py',[]),
      ('C6_exact_certificate','stages/C6_exact/verify_C6_period_identity.py',['--report',str(out/'C6_certificate.json')]),
      ('C6_input_map','code/verify_C6_input_map.py',['--report',str(out/'C6_input_map.json')]),
    ]
    if args.level=='standard':
      jobs += [
       ('thermal_series','code/verify_series.py',['--report',str(out/'thermal_series.json')]),
       ('response_recurrence','stages/C6_integrals/reproducibility/check_response_recurrence.py',[]),
       ('trace_full_jacobian','stages/C6_exact/proof/derive_trace.py',[]),
       ('weight_five_MZV','stages/C6_exact/proof/audit_mzv_and_structure.py',[]),
       ('all_order_algebra','stages/C6_exact/proof/verify_all_orders.py',[]),
       ('D4_symbolic','stages/C7_partial/derive_D4.py',[]),
       ('low_order_closed_forms','stages/delta2_exact/code/verify_closed_forms.py',['--dps','60']),
      ]
    report={'level':args.level,'started_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
            'scope':'Fresh exact selected checks and, at standard level, low-order numerical integrals. No full raw reintegration; no Omega evaluation.',
            'jobs':[],'status':'RUNNING'}
    reportpath=out/'summary.json';reportpath.write_text(json.dumps(report,indent=2)+'\n')
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    for name,rel,flags in jobs:
        script=root/rel;cmd=[py,str(script),*flags];start=time.monotonic()
        print('RUN',name,flush=True)
        try:
            proc=subprocess.run(cmd,cwd=script.parent,env=env,capture_output=True,text=True,timeout=args.timeout)
            log=proc.stdout+('\nSTDERR:\n'+proc.stderr if proc.stderr else '')
            item={'name':name,'script':rel,'returncode':proc.returncode,'status':'PASS' if proc.returncode==0 else 'FAIL'}
        except subprocess.TimeoutExpired as exc:
            def txt(v):return v.decode(errors='replace') if isinstance(v,bytes) else (v or '')
            log=txt(exc.stdout)+'\nTIMEOUT\n'+txt(exc.stderr)
            item={'name':name,'script':rel,'returncode':None,'status':'TIMEOUT'}
        item['seconds']=round(time.monotonic()-start,4);item['log']=name+'.log';report['jobs'].append(item)
        (out/(name+'.log')).write_text(log)
        if item['status']!='PASS':
            report['status']='FAIL';reportpath.write_text(json.dumps(report,indent=2)+'\n')
            print('FAILED',name,'See',out/(name+'.log'));sys.exit(1)
        reportpath.write_text(json.dumps(report,indent=2)+'\n');print('PASS',name,flush=True)
    report['status']='PASS';report['finished_utc']=datetime.now(timezone.utc).isoformat()
    reportpath.write_text(json.dumps(report,indent=2)+'\n')
    print('All selected checks passed. Report:',reportpath)
if __name__=='__main__':main()
