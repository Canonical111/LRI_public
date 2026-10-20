#!/usr/bin/env python3
"""Verify the completed parts without treating missing raw integrals as zero."""
import argparse,json,subprocess,sys,hashlib,os
from pathlib import Path
from decimal import Decimal,localcontext
ROOT=Path(__file__).resolve().parent

def call(args):
 subprocess.run(args,check=True,cwd=ROOT,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='2'))

def main():
 snapshots={p:p.read_bytes() for p in [ROOT/'F2/verification/exact_assembly.json', ROOT/'F2/verification/independent_period_check.json', ROOT/'F3/data/F3_shift_assembly.json', ROOT/'F3/verification/independent_derivative.json'] if p.exists()}
 p=argparse.ArgumentParser();p.add_argument('--analytic',action='store_true');p.add_argument('--numerical',action='store_true');p.add_argument('--skip-hashes',action='store_true');a=p.parse_args()
 manifest=ROOT/'MANIFEST.json'
 if manifest.exists() and not a.skip_hashes:
  for r in json.loads(manifest.read_text())['files']:
   f=ROOT/r['path'];assert f.is_file(),r['path'];assert hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256'],r['path']
 call([sys.executable,str(ROOT/'F2/code/check_exact_assembly.py')])
 aa=json.loads((ROOT/'F2/verification/run80.json').read_text());bb=json.loads((ROOT/'F2/verification/run110dfs.json').read_text())
 with localcontext() as ctx:
  ctx.prec=125
  differences={k:str(abs(Decimal(aa['values'][k])-Decimal(v))) for k,v in bb['values'].items()}
  assert max(map(Decimal,differences.values()))<Decimal('1e-63')
  p=ROOT/'F3/verification';da=json.loads((p/'F3_70.json').read_text());db=json.loads((p/'F3_100.json').read_text())
  assert all(abs(Decimal(v)-Decimal(db['values'][k]))<Decimal('1e-53') for k,v in da['values'].items())
 if a.analytic:
  call([sys.executable,str(ROOT/'F2/code/check_leading_tail_log.py')])
  call([sys.executable,str(ROOT/'F3/engine/assemble_F3_shift.py')])
  call([sys.executable,str(ROOT/'F3/engine/check_F3_derivative.py')])
 if a.numerical:
  cpp=ROOT/'F2/code/periods_gmp.cpp';exe=cpp.with_suffix('')
  call(['g++','-O3','-std=c++17','-fopenmp',str(cpp),'-lgmpxx','-lgmp','-o',str(exe)])
  call([sys.executable,str(ROOT/'F2/code/check_decimal_and_closed_periods.py')])
  for label,dps,r,nt,na,step in [('replay80',80,120,260,165,'.30'),('replay110',110,160,330,200,'.25')]:
   call([sys.executable,str(ROOT/'F2/code/evaluate_set.py'),'--manifest',str(ROOT/'F2/data/evaluation_manifest.json'),'--out',str(ROOT/'F2/verification'/f'{label}.json'),'--dps',str(dps),'--radius',str(r),'--taylor',str(nt),'--asymptotic',str(na),'--step',step])
  call([sys.executable,str(ROOT/'F2/code/compare_fresh_numeric.py')])
 report={'F2_exact_scalar_assembly':True,'F2_recorded_two_run_numeric_comparison':True,'F3_recorded_two_run_shift_comparison':True,'reran_analytic_checks':a.analytic,'reran_full_F2_numeric_evaluations':a.numerical,'F2_all_subleading_logs_verified':False,'F3_complete':False}
 replays=ROOT/'verification/replays'; replays.mkdir(exist_ok=True)
 for path,old in snapshots.items():
  if path.exists() and path.read_bytes()!=old:
   dest=replays/('_'.join(path.relative_to(ROOT).parts)); dest.write_bytes(path.read_bytes()); path.write_bytes(old)
 (ROOT/'verification/replay_summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
