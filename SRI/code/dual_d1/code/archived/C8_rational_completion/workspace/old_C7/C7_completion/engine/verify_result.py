"""Algebraic checks and fresh evaluation from exact period expressions.
This is not an analytic certificate for the proposed zeta reduction.
"""
from pathlib import Path
import argparse,subprocess,sys,json
import mpmath as mp
ROOT=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--fresh-periods',action='store_true');args=ap.parse_args()
for script in ['derive_trace.py','check_response_recurrence.py','check_higher_logs.py','check_tail_auxiliary.py','verify_higher_logs.py']:
 subprocess.run([sys.executable,script],cwd=ROOT,check=True)
if args.fresh_periods:
 subprocess.run([sys.executable,'evaluate_final.py','--label','verification','--dps','100','--radius','120','--taylor','290','--asymptotic','150','--step','.35'],cwd=ROOT,check=True)
 fresh=json.loads((ROOT/'final_evaluation_verification.json').read_text())['coefficients']
 ref=json.loads((ROOT/'final_evaluation_run2.json').read_text())['coefficients']
 mp.mp.dps=100
 for key in ref:
  assert abs(mp.mpf(fresh[key])-mp.mpf(ref[key]))<mp.mpf('1e-75'),key
 print('PASS: fresh high-precision period assembly agrees with the saved result.')
else:
 print('The exact algebra and higher-log checks passed. Use --fresh-periods for a fresh full numerical assembly.')
print('Closed zeta reduction status: numerically supported conjecture, NOT analytically certified.')
