#!/usr/bin/env python3
"""One-command self-contained reproduction of the final two-dimensional C2 method.

Every accepted result is recomputed from the packaged code. Saved reference
outputs are read only by the final comparison/assembly step. No network access,
external archive, global cache, or path outside this package is used.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,platform,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,default=ROOT/'inputs/calculation.json')
    args=p.parse_args();config=json.loads(args.config.read_text())
    dps=int(config['working_dps']);audit_dps=int(config['independent_working_dps']);terms=int(config['half_interval_terms'])
    if dps<60 or audit_dps<75:raise ValueError('Require formula dps>=60 and independent checks dps>=75.')
    for d in ['raw','tables','figures','logs']:(ROOT/'outputs'/d).mkdir(parents=True,exist_ok=True)
    jobs=[
      ('three_4f3',['lri_C2_three_4F3.py','--dps',str(dps),'--terms',str(terms),'--check','--symbolic','--json',str(ROOT/f'outputs/raw/three_4f3_{dps}dps.json')]),
      ('certificate_boundaries',['certificate_boundaries.py']),
      ('analytic_bridges',['analytic_bridge_checks.py','--dps','50','--json',str(ROOT/'outputs/raw/analytic_bridges.json')]),
      ('renormalization',['lri_C2_renormalization_checks.py','--dps',str(dps),'--symbolic','--json',str(ROOT/f'outputs/raw/renormalization_{dps}dps.json')]),
      ('source_contacts',['source_contact_checks.py','--dps',str(dps),'--json',str(ROOT/f'outputs/raw/source_contacts_{dps}dps.json')]),
      ('independent',['independent_c2_checks.py','--dps',str(audit_dps),'--tail-terms',str(config['direct_series_terms']),'--output',str(ROOT/f'outputs/raw/independent_c2_{audit_dps}dps.json')]),
      ('convergence',['convergence.py','--dps',str(dps),'--terms',*[str(n) for n in config['convergence_terms']]]),
      ('assemble',['assemble_outputs.py','--config',str(args.config.resolve())]),
    ]
    manifest={'scope':'Fresh C2-only calculation; saved reference comparisons are explicitly separate.',
      'started_utc':utc(),'status':'running','config':config,
      'environment':{'python':sys.version,'platform':platform.platform()},
      'code_sha256':{p.name:sha(p) for p in sorted((ROOT/'code').glob('*.py'))},'steps':[]}
    receipt=ROOT/'outputs/run_manifest.json'
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['OPENBLAS_NUM_THREADS']='1';env['MPLCONFIGDIR']=str(ROOT/'outputs/.matplotlib')
    for name,command in jobs:
        argv=[sys.executable,str(ROOT/'code'/command[0]),*command[1:]]
        step={'name':name,'arguments':[command[0],*command[1:]],'started_utc':utc(),'status':'running'}
        manifest['steps'].append(step);receipt.write_text(json.dumps(manifest,indent=2)+'\n')
        print('RUN',name,flush=True);t=time.perf_counter()
        with (ROOT/'outputs/logs'/f'{name}.log').open('w') as log:
            result=subprocess.run(argv,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        step.update(returncode=result.returncode,elapsed_seconds=time.perf_counter()-t,finished_utc=utc(),status='passed' if result.returncode==0 else 'failed')
        receipt.write_text(json.dumps(manifest,indent=2)+'\n')
        if result.returncode:
            manifest['status']='failed';receipt.write_text(json.dumps(manifest,indent=2)+'\n')
            raise RuntimeError(f'{name} failed. See outputs/logs/{name}.log; no failed result is accepted.')
        print('PASS',name,f'{step["elapsed_seconds"]:.2f}s',flush=True)
    manifest.update(status='complete',finished_utc=utc())
    manifest['result_sha256']={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'outputs/raw').glob('*.json'))}
    receipt.write_text(json.dumps(manifest,indent=2)+'\n');print('COMPLETE: outputs/summary.json',flush=True)
if __name__=='__main__':main()
