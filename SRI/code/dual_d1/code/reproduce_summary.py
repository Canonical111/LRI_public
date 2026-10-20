#!/usr/bin/env python3
"""Regenerate coefficient tables and check invariant identities.
C8's compact expression is ALWAYS marked a conjecture. This program checks
algebra and numerical agreement with archived outputs, not the C8 period proof.
"""
from pathlib import Path
from fractions import Fraction as Q
from decimal import Decimal,localcontext
import ast,csv,json,sys
ROOT=Path(__file__).resolve().parents[1]

def main():
 import mpmath as mp
 import sympy as s
 mp.mp.dps=110
 z=s.zeta
 c={1:-s.Integer(2),2:s.Rational(1,2),3:s.Rational(39,16)+2*z(2),
 4:4-4*z(2)-8*z(3),
 5:s.Rational(11249,1024)-s.Rational(361,16)*z(2)+24*z(3)+s.Rational(49,2)*z(4),
 6:26-38*z(2)+104*z(3)-80*z(4)-272*z(5)+112*z(2)*z(3),
 7:s.Rational(1798583,32768)-s.Rational(90637,1024)*z(2)+s.Rational(453,4)*z(3)-s.Rational(16835,64)*z(4)+1224*z(5)-540*z(2)*z(3)+s.Rational(4335,8)*z(6)-320*z(3)**2,
 8:88-178*z(2)+110*z(3)+113*z(4)+4892*z(5)-2376*z(2)*z(3)-s.Rational(8630,3)*z(6)+1872*z(3)**2-12168*z(7)+6048*z(2)*z(5)+1536*z(3)*z(4)}
 rational={1:Q(-2),2:Q(1,2),3:Q(39,16),4:Q(4),5:Q(11249,1024),6:Q(26),7:Q(1798583,32768),8:Q(88)}
 t=s.symbols('t');f=1+sum(c[n]*t**n for n in c);other=f.subs(t,-t)
 T=s.expand(f+other-2);D=s.expand((f-1)*(other-1))
 invariants={'T1':s.Rational(1,2),'T2':2-2*z(2)-4*z(3),'T3':c[6]/4,'T4_candidate':c[8]/8,'D1':-2,'D2':s.Rational(5,2)+2*z(2),'D3':s.Rational(21,4)-13*z(2)+11*z(3)+11*z(4),'D4':13-s.Rational(179,8)*z(2)+s.Rational(47,2)*z(3)-s.Rational(493,8)*z(4)+289*z(5)-130*z(2)*z(3)+s.Rational(499,4)*z(6)-76*z(3)**2}
 checks=[]
 for name,target in invariants.items():
  m=int(name[1]);source=T if name.startswith('T') else D
  residual=s.simplify(source.coeff(t,2*m)/2**m-target)
  assert residual==0,(name,residual);checks.append({'identity':name,'residual':'0','scope':'formal characteristic-polynomial identity'})
 # Verify trace polynomial from scratch on the rational beta inputs.
 layout=json.loads((ROOT/'reproduction/layout.json').read_text())['files'];lookup={r['path']:ROOT/r['stored'] for r in layout}
 def locate(suffix):
  choices=[p for v,p in lookup.items() if v.endswith(suffix)]
  if not choices:raise FileNotFoundError(suffix)
  return choices[0]
 from importlib.util import spec_from_file_location,module_from_spec
 jpath=locate('C8_zeta_candidate/code/full_jacobian.py');sp=spec_from_file_location('independent_full_jacobian',jpath);module=module_from_spec(sp);sp.loader.exec_module(module)
 old=json.loads(locate('prior_inputs/T4_rational_reduction.json').read_text()) if any(v.endswith('prior_inputs/T4_rational_reduction.json') for v in lookup) else None
 if old is None:
  names=['a','p','A','E','c','f','q','b','G','k','V','R','J','L','M','N','alpha','beta','gamma','Phi','Psi','Omega','Q','P','K']
  vals=['0','8','-8','-16','-16','32','-32','-18','36','128','-24','154','-16','0','-288','16','16','72','160','-240','22','-904','160','-1976','2032/3']
  coeff=dict(zip(names,vals))
 else:coeff=old['old_rational_beta_inputs']
 coeff.update(W='168',S='-1751',L3='128',M21='-384',M12='2720',N2='3712',U='16534/3',J9='-10192/3',Nd='-20848',Kv='77920/3')
 jac=module.calculate({k:Q(v) for k,v in coeff.items()});assert jac['C8']==88
 checks.append({'identity':'independent rational full-Jacobian C8','result':'88','scope':'exact rational polynomial assembly; inherited beta inputs'})
 assert -Q(111389,24)+Q(3,4)*(-Q(910891,6))+Q(1,4)*Q(1423087,3)==88
 result=json.loads(locate('C8_zeta_candidate/result.json').read_text())
 with localcontext() as ctx:
  ctx.prec=105
  assembled=Decimal(result['Cfixed_inherited_numeric_assembly'])-Decimal(result['P6_fresh'])/2
  archive=Decimal(result['C8_assembled_without_candidate']);assert abs(assembled-archive)<Decimal('1e-90')
 candidate=mp.mpf(str(s.N(c[8],108)))
 residual=mp.mpf(str(assembled))-candidate
 assert abs(residual)<mp.mpf('1e-80')
 rows=[]
 for n in c:
  status='published baseline' if n<=2 else ('analytic archived-period reduction' if n<=7 else 'numerically supported candidate; NOT proved')
  rows.append({'n':n,'power_of_x':str(Q(n,2)),'expression':str(c[n]),'latex':s.latex(c[n]),'decimal':str(s.N(c[n],70)),'rational_part':str(rational[n]),'status':status})
 (ROOT/'data/coefficients.json').write_text(json.dumps({'notation':'Delta_epsilon(x)=1+sum C_n x^(n/2), delta=2x','coefficients':rows,'scope':'Higher coefficients are conditional on the archived matched prescription. C8 expression is a conjectural period reduction.'},indent=2)+'\n')
 out=ROOT/'outputs/tables';out.mkdir(parents=True,exist_ok=True)
 with (out/'thermal_coefficients.csv').open('w',newline='') as fp:
  writer=csv.DictWriter(fp,fieldnames=['n','power_of_x','decimal','rational_part','status']);writer.writeheader();writer.writerows({k:r[k] for k in writer.fieldnames} for r in rows)
 (out/'invariants.json').write_text(json.dumps({k:{'expression':str(v),'decimal':str(s.N(v,70))} for k,v in invariants.items()},indent=2)+'\n')
 report={'status':'PASS','checks':checks,'C8_candidate_residual':mp.nstr(residual,35),'C8_analytic_certificate':False,'integer_relation_not_a_proof':True,'full_interval_bound':None}
 (ROOT/'outputs/verification/summary_algebra.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
