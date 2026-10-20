from pathlib import Path
import json,sympy as s
from read_expression import load
from finite_extract_fast import *
root=Path(__file__).resolve().parent.parent
for tag in ['EQ6_v','Q6_vv']:
 folder=root/tag/'b00';rows=json.loads((folder/'negative.json').read_text())
 x=extract_finite(rows,5);old=load(folder/'coefficient_0.expr');assert s.expand(x-old)==0
 print('FULL_CONTROL_FINITE_EXACT',tag,len(rows),flush=True)
for w in [(-1,),(-2,-1),(-3,-2,-1),(0,-1,-3),(-1,0,0)]:
 for j in range(4):
  for k in range(4):assert s.expand(big_coefficient(w,j,k)-s.expand(ag.big(w,j)).coeff(ag.L,k))==0,(w,j,k)
(root/'data/fast_finite_checks.json').write_text(json.dumps({'whole_controls':['EQ6_v_b00','Q6_vv_b00'],'big_coefficient_checks':80,'all_exact_equal':True},indent=2))
