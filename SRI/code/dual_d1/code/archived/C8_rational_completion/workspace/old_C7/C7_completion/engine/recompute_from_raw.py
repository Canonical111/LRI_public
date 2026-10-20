"""Recompute beta coefficients and C6 from the saved exact regulated integrals.
This clears the derived cutoff/response caches; it does NOT use the candidate
closed form, saved beta coefficients, or saved numerical period values.
"""
from pathlib import Path
import argparse,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--label',default='reproduced');a=ap.parse_args()
cache=ROOT/'series'
if cache.exists():shutil.rmtree(cache)
cache.mkdir()
for name in ['a_check','p_check','A_check','E_check','c_check','f_check','q_check','b_check','G_check','k_check','L','M','R','N','J','V','B_old','C6','T3']:
 (ROOT/(name+'_symbolic.expr')).unlink(missing_ok=True)
def run(*args):
 print('RUN',*args,flush=True);subprocess.run([sys.executable,*args],cwd=ROOT,check=True)
run('compute_second_tail.py')
run('assemble_C6.py')
run('finish_C6_assembly.py')
run('derive_trace.py');run('check_response_recurrence.py')
run('check_higher_logs.py');run('check_tail_auxiliary.py')
run('evaluate_final.py','--label',a.label)
print('Completed fresh assembly from exact raw integrals.',flush=True)
