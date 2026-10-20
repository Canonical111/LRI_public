#!/usr/bin/env python3
"""Check distribution integrity and exact saved scalar assemblies.
This does not prove the proposed C8 zeta identity or reintegrate every kernel.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse,hashlib,json,subprocess,sys,time,os
ROOT=Path(__file__).resolve().parent

def main():
 if not __debug__:raise RuntimeError('Use Python without -O; assertions are part of the archived verifiers.')
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--skip-hashes',action='store_true');p.add_argument('--certificates',action='store_true');p.add_argument('--algebra',action='store_true');p.add_argument('--numerical',action='store_true');a=p.parse_args()
 start=time.time();records=[]
 if not a.skip_hashes:
  manifest=ROOT/'reproduction/MANIFEST.json'
  if not manifest.is_file():raise FileNotFoundError('Missing immutable distribution manifest')
  m=json.loads(manifest.read_text())
  for rec in m['files']:
   path=ROOT/rec['path']
   if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=rec['sha256']:raise RuntimeError('Missing/changed distribution file: '+str(path))
  print('PASS distribution hashes:',len(m['files']),flush=True)
  records.append({'check':'distribution_hashes','files':len(m['files']),'status':'PASS'})
 layout=json.loads((ROOT/'reproduction/layout.json').read_text())['files'];seen=set()
 for rec in layout:
  if rec['path'] in seen:raise RuntimeError('Duplicate virtual path '+rec['path'])
  seen.add(rec['path'])
  if not (ROOT/rec['stored']).is_file():raise FileNotFoundError(rec['stored'])
 assert -F(111389,24)+F(3,4)*(-F(910891,6))+F(1,4)*F(1423087,3)==88
 assert -F(8411,6)+F(3,4)*F(16534,3)-F(10192,12)-F(20848,8)+F(77920,96)==88
 records.append({'check':'virtual_layout_and_independent_rational_sums','status':'PASS','C8_weight_zero':'88'})
 # Individual standard-library saved-expression checkers; never execute a numerical recognition as an analytic proof.
 sys.path.insert(0,str(ROOT/'code'))
 from prepare_workflows import prepare
 w=prepare('c8-candidate');prepare('c8-full')
 out=ROOT/'outputs/verification/replayed';out.mkdir(parents=True,exist_ok=True)
 commands=[
 ('P6_saved_exact_sum',w/'C8_zeta_candidate/code/check_P6_sum.py',[]),
 ('C8_decimal_input_Jacobian',w/'C8_zeta_candidate/code/check_assembly.py',[]),
 ('P8_J9_exact_scalar_maps',w/'C8_full_numerical_completion/code/check_exact_scalars.py',[])]
 if a.algebra:commands.append(('summary_symbolic_algebra',ROOT/'code/reproduce_summary.py',[]))
 if a.certificates:commands.append(('complete_period_certificates',ROOT/'code/reproduce.py',['--task','certificates']))
 if a.numerical:commands.append(('fresh_P6_numerical_evaluations',ROOT/'code/reproduce.py',['--task','c8-numerical']))
 for name,script,args in commands:
  print('RUN',name,flush=True);t=time.time()
  with (out/(name+'.txt')).open('w') as fp:
   proc=subprocess.run([sys.executable,str(script),*args],cwd=script.parent,stdout=fp,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1'))
  records.append({'check':name,'status':'PASS' if proc.returncode==0 else 'FAIL','seconds':time.time()-t,'log':str((out/(name+'.txt')).relative_to(ROOT))})
  if proc.returncode:raise RuntimeError('Check failed; see '+str(out/(name+'.txt')))
  print('PASS',name,flush=True)
 report={'status':'PASS','checks':records,'seconds':time.time()-start,'scope':'Exact saved-expression/input-algebra verification; optional numerical replay and finite certificates have their own scopes. No analytic C8 certificate is claimed.'}
 (out/'quick_check.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS all requested checks. C8 compact zeta identity remains unproved.',flush=True)
if __name__=='__main__':main()
