"""Portable saved-data checks, with optional fresh period evaluations."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys,os
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--numerical',action='store_true');p.add_argument('--skip-hashes',action='store_true');a=p.parse_args()
manifest=ROOT/'MANIFEST.json'
if manifest.exists() and not a.skip_hashes:
 for rec in json.loads(manifest.read_text())['files']:
  path=ROOT/rec['path'];assert path.is_file(),path
  assert hashlib.sha256(path.read_bytes()).hexdigest()==rec['sha256'],path
print('DISTRIBUTION_INPUTS_OK',flush=True)
for file in ['check_P6_sum.py','check_assembly.py','check_candidate.py']:
 subprocess.run([sys.executable,str(ROOT/'code'/file)],check=True,cwd=ROOT)
# These are checks of completed records, not re-evaluations.
from decimal import Decimal
record=json.loads((ROOT/'verification/divergences90.json').read_text())['values']
for key in ['diff_p-2','diff_p-1']:assert abs(Decimal(record[key]))<Decimal('1e-80')
assert (ROOT/'verification/Q4_vd_difference.expr').read_text().strip()=='0'
control=json.loads((ROOT/'verification/fibration_full_block.json').read_text());assert control['every_rational_difference_exact_zero']
if a.numerical:
 for digits,R,nt,na,step in [(70,100,230,155,'.30'),(100,140,320,195,'.25')]:
  out=ROOT/'verification'/f'replay_P6_{digits}.json'
  subprocess.run([sys.executable,str(ROOT/'code/numerical/evaluate_set.py'),'--manifest',str(ROOT/'data'/f'P6_manifest{digits}.json'),'--out',str(out),'--dps',str(digits),'--radius',str(R),'--taylor',str(nt),'--asymptotic',str(na),'--step',step,'--backend','gmp'],check=True,env=dict(os.environ,OMP_NUM_THREADS='3',OPENBLAS_NUM_THREADS='1'))
  old=json.loads((ROOT/'data'/f'P6_eval{digits}.json').read_text())['values']['P6'];new=json.loads(out.read_text())['values']['P6'];assert abs(Decimal(old)-Decimal(new))<Decimal(10)**(-(digits-15))
print('ALL_REQUESTED_CHECKS_PASSED; THIS IS NOT AN ANALYTIC C8 ZETA CERTIFICATE',flush=True)
