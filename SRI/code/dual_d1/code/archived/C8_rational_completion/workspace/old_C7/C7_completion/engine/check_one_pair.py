"""Independent elementary-integral checks of the new tail insertions."""
import sympy as s,json
from pathlib import Path
from asymptotic_gpl import extract_rows,ell,E as a
ROOT=Path(__file__).resolve().parent

def I(m):
 p=sum((-1)**j*s.factorial(m)/s.factorial(m-j)*ell**(m-j) for j in range(m+1))
 return -ell**(m+1)/s.Integer(m+1)-(-1)**m*s.factorial(m)+a*p
checks={}
for tag,expect in [('Q2_dd',I(4)-s.Rational(2,3)*I(3)),('Q2_vdd',-2*I(5)+s.Rational(10,3)*I(4)-s.Rational(2,3)*I(3))]:
 rows=json.loads((ROOT/(tag+'_negative.json')).read_text())
 raw=sum(a**p*extract_rows(rows,1,p,None) for p in (0,1))
 diff=s.expand_log(raw-s.expand(expect),force=True).expand()
 assert diff==0,(tag,diff)
 checks[tag]={'exact_residual':str(diff),'elementary_result':str(s.expand(expect))}
print(json.dumps(checks,indent=2))
(ROOT/'one_pair_checks.json').write_text(json.dumps(checks,indent=2))
