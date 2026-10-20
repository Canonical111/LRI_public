"""Optional integer-relation recognition AFTER the independent first evaluation.
An identity found here is a conjecture, not an analytic proof.
"""
from pathlib import Path
import json,time
import mpmath as mp
import sympy as s
ROOT=Path(__file__).resolve().parent;src=ROOT/'final_evaluation_C7_first.json'
data=json.loads(src.read_text());mp.mp.dps=90;dv=mp.mpf(data['coefficients']['D4_value'])
z2,z3,z4,z5,z6=s.symbols('Z2 Z3 Z4 Z5 Z6')
basis=[s.S.One,z2,z3,z4,z5,z2*z3,z6,z3*z3]
num=[mp.mpf(1),mp.zeta(2),mp.zeta(3),mp.zeta(4),mp.zeta(5),mp.zeta(2)*mp.zeta(3),mp.zeta(6),mp.zeta(3)**2]
st=time.time();relation=mp.pslq(mp.matrix([dv]+num),tol=mp.mpf('1e-68'),maxcoeff=100000000,maxsteps=10000)
out={'status':'no_relation_found','source':src.name,'basis':[str(x) for x in basis],'dps':90,'tol':'1e-68','maxcoeff':100000000,'seconds':time.time()-st,'proof_status':'No analytic reduction certificate has been computed at this order.'}
if relation and relation[0]:
 from read_expression import load
 D=-sum(s.Rational(a,relation[0])*b for a,b in zip(relation[1:],basis))
 offset=s.Rational(94647,32768)+s.Rational(1011,1024)*z2+s.Rational(77,4)*z3-s.Rational(1059,64)*z4+68*z5-20*z2*z3+s.Rational(343,8)*z6-16*z3**2
 C=s.expand(4*D+offset);Dnum=-mp.fsum(mp.mpf(a)*b for a,b in zip(relation[1:],num))/relation[0]
 out.update({'status':'candidate_from_first_evaluation_before_second_comparison','integer_relation':list(map(int,relation)),'D4_candidate':str(s.expand(D)),'C7_candidate':str(C),'first_D4_residual':mp.nstr(dv-Dnum,80)})
 (ROOT/'D4_candidate.expr').write_text(str(s.expand(D)));(ROOT/'C7_candidate.expr').write_text(str(C))
print(json.dumps(out,indent=2));(ROOT/'C7_candidate_recognition.json').write_text(json.dumps(out,indent=2))
