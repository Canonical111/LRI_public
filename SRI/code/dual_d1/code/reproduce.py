#!/usr/bin/env python3
"""Execute named, explicitly scoped reproduction workflows in generated work/ copies."""
from __future__ import annotations
import argparse,json,subprocess,sys,time,os
from pathlib import Path
from prepare_workflows import ROOT,prepare

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--task',choices=['certificates','c8-saved','c8-numerical','c8-positive-check','low-integrals','c8-rational-algebra','conjectures','all-saved'],default='c8-saved')
 p.add_argument('--timeout',type=int,default=None,help='Optional per-command limit; no cached PASS is substituted after a timeout.')
 a=p.parse_args(); jobs=[];w=ROOT/'work'
 if a.task in ['certificates','all-saved']:
  prepare('baseline');prepare('c7-proof')
  jobs.extend([
   ('D3_certificate',w/'D3_analytic_proof/verify_D3_proof_standalone.py',[]),
   ('C6_certificate',w/'C6_closed_form/verify_C6_period_identity.py',[]),
   ('C7_input_map',w/'C7_closed_form_proof/code/verify_input_map.py',[]),
   ('C7_certificate',w/'C7_closed_form_proof/proof/verify_C7_certificate.py',['--prefix',str(w/'C7_closed_form_proof/proof/C7')])])
 if a.task in ['c8-saved','c8-numerical','all-saved']:
  prepare('c8-candidate'); args=['--skip-hashes']
  if a.task=='c8-numerical':args.append('--numerical')
  jobs.append(('C8_candidate_workflow',w/'C8_zeta_candidate/run_checks.py',args))
 if a.task in ['c8-positive-check','all-saved']:
  prepare('c8-full');args=['--skip-hashes']
  if a.task=='c8-positive-check':args.append('--numerical-small')
  jobs.append(('C8_full_assembly',w/'C8_full_numerical_completion/run_checks.py',args))
 if a.task=='low-integrals':
  prepare('baseline');jobs.append(('analytic_periods',w/'LRI_thermal_closed_form/code/verify_closed_forms.py',['--dps','60']))
 if a.task=='c8-rational-algebra':
  # A separate fixed-point implementation and all data needed for its rational substitution.
  prepare('c8-candidate');jobs.append(('coefficient_algebra',ROOT/'code/reproduce_summary.py',[]))
 if a.task=='conjectures':
  prepare('conjectures')
  jobs += [('gamma_exclusion',w/'LRI_Gamma_exclusion/run_checks.py',['--minimal']),('rational_audit',w/'LRI_conjecture_audit/check_rational_predictions.py',[])]
 out=ROOT/'outputs/verification/replayed';out.mkdir(parents=True,exist_ok=True)
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='2')
 records=[]
 for name,path,args in jobs:
  if not path.is_file():raise FileNotFoundError(path)
  cmd=[sys.executable,str(path),*args];print('RUN',name,flush=True);start=time.time()
  try:
   with (out/(name+'.txt')).open('w') as log:
    result=subprocess.run(cmd,cwd=path.parent,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout)
   status='PASS' if result.returncode==0 else 'FAIL'
  except subprocess.TimeoutExpired:status='TIMEOUT'
  records.append({'name':name,'status':status,'seconds':time.time()-start,'command':cmd,'log':str((out/(name+'.txt')).relative_to(ROOT))})
  (out/f'{a.task}.json').write_text(json.dumps({'task':a.task,'checks':records,'scope':'Fresh execution of named checks. Saved-expression replay is not raw reintegration; numerical recognition is not an analytic C8 certificate.'},indent=2)+'\n')
  print(status,name,flush=True)
  if status!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
