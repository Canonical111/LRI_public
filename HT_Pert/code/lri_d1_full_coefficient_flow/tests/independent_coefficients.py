"""Fresh full-order and exact-rational checks of the new ragged quotient engine."""
from pathlib import Path
import sys,json,contextlib,io
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'code'),str(ROOT/'vendor')]
from ragged_quotient import run
from window_jets import solve
from exact_window import solve as exact

def err(a,b,keys):
 return float(max(np.max(abs(np.array(a[k])-b[k])/np.maximum(1,abs(np.array(b[k])))) for k in keys))
def main():
 rows=[]
 for L,d,scheme in [(2,8,'dconn'),(4,8,'dconn'),(8,6,'dconn'),(12,7,'dconn'),(24,8,'dconn'),(28,8,'dconn'),(24,8,'raw')]:
  print('checking',L,d,scheme,flush=True)
  with contextlib.redirect_stdout(io.StringIO()):a=run(L,d,scheme,batch=2)
  b=solve(L,d,scheme,batch=3);e=err(a,b,['C','r','g','energies','vacuum_grid_coefficients']);assert e<1e-10
  rows.append(dict(L=L,degree=d,scheme=scheme,type='ordinary full-order reference',scaled_error=e))
  (ROOT/'results/independent_validation.json').write_text(json.dumps(rows,indent=2)+'\n')
  if L<=4:
   print('Fraction',L,flush=True)
   x=exact(L,d,scheme);e=err(a,dict(C=x['C']),['C']);assert e<1e-10;rows.append(dict(L=L,type='independent Fraction recursion',scaled_error=e))
 with contextlib.redirect_stdout(io.StringIO()):a=run(16,8,batch=1);b=run(16,8,batch=7)
 e=err(a,b,['C','r','g','energies','vacuum_grid_coefficients']);assert e<1e-11
 rows.append(dict(L=16,type='batch size 1 versus 7',scaled_error=e))
 (ROOT/'results/independent_validation.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
