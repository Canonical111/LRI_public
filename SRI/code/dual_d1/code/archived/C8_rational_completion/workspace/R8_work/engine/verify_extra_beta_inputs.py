"""Exact independent low-order check of all six previously supplied C8 inputs.
Raw boundary residues and new finite integrals are assembled only after source
coverage/hash checks. The two-kink finite derivatives are integrated analytically.
"""
from pathlib import Path
from fractions import Fraction as F
from math import factorial
import json
from finalize_tail import load
from assemble_C8_full_beta import finite
from check_lower_tables_stdlib import raw
ROOT=Path(__file__).resolve().parent.parent

def two_pair_finite(a,b):
 # Q2 = integral_eps^1 (1-r)/r * exp(E(log r)) dr,
 # E=-2zL-(1+z)delta L^2-(1+z)delta^2 L^3/3+O(delta^3).
 E={(1,0,1):F(-2),(0,1,2):F(-1),(1,1,2):F(-1),(0,2,3):F(-1,3),(1,2,3):F(-1,3)}
 def mul(p,q):
  out={}
  for (i,j,l),c in p.items():
   for (k,m,n),d in q.items():
    if i+k<=a and j+m<=b:
     key=(i+k,j+m,l+n);out[key]=out.get(key,F(0))+c*d
  return {k:v for k,v in out.items() if v}
 exp={(0,0,0):F(1)};term=dict(exp)
 for n in range(1,a+b+1):
  term=mul(term,E)
  for key,c in term.items():exp[key]=exp.get(key,F(0))+c/F(factorial(n))
 p={l:c*factorial(a)*factorial(b) for (i,j,l),c in exp.items() if i==a and j==b}
 value=sum((c*(-1)**(l+1)*factorial(l) for l,c in p.items()),F(0))
 return value,{str(k):str(v) for k,v in sorted(p.items()) if v}

def residue(kind,n,d):
 b,_,faces,_=load(kind,n,d,False)
 return -b,faces

def main():
 rr={};faces={}
 for k,n,d in [('Q',4,'base'),('A',5,'dd'),('Z',4,'dd'),('Q',4,'vvv'),('Q',4,'vvd'),('Q',4,'vdd'),('Q',6,'vv')]:
  key=f'{k}{n}_{d}';rr[key],faces[key]=residue(k,n,d)
 reference=raw(4,'Q','base',0).get(0,());assert rr['Q4_base']==reference[1]
 tags=['EA3_dd','EZ2_dd','EQ2_vvv','EQ2_vvd','EQ2_vdd','EQ4_vv','Q4_vvv'];fv={t:finite(t) for t in tags}
 pair={};poly={}
 for tag,a,b in [('Q2_vvvv',4,0),('Q2_vvvd',3,1),('Q2_vvdd',2,2)]:pair[tag],poly[tag]=two_pair_finite(a,b)
 w=json.loads((ROOT/'three_tail_cubic_check.json').read_text())
 new={'W':F(w['W']),
 'S':rr['A5_dd']/2+fv['EA3_dd']-fv['EZ2_dd']-rr['Z4_dd']/2-F(8455,2),
 'L3':-F(4,3)*fv['EQ2_vvv']+F(8,3)*pair['Q2_vvvv']-F(2,3)*rr['Q4_vvv']-640,
 'M21':-4*fv['EQ2_vvd']+8*pair['Q2_vvvd']-2*rr['Q4_vvd']+2368,
 'M12':-4*fv['EQ2_vdd']+8*pair['Q2_vvdd']-2*rr['Q4_vdd']-7392,
 'N2':-4*fv['EQ4_vv']+8*fv['Q4_vvv']-2*rr['Q6_vv']-28148}
 prior=json.loads((ROOT/'prior_inputs/new_six_checkpoint.json').read_text())['coefficients']
 checks={k: v==F(prior[k]) for k,v in new.items()}
 report={'status':'all_six_prior_new_beta_inputs_freshly_verified' if all(checks.values()) else 'low_order_discrepancy_requires_investigation',
 'fresh_values':{k:str(v) for k,v in new.items()},'prior_checkpoint':prior,'exact_comparisons':checks,
 'boundary_residues':{k:str(v) for k,v in rr.items()},'finite_integrals':{k:str(v) for k,v in fv.items()},
 'two_pair_finite_derivatives':{k:str(v) for k,v in pair.items()},'two_pair_log_insertions':poly,
 'boundary_faces':faces,'Q4_base_reference':str(reference[1]),'C8_conjecture_used_as_input':False}
 (ROOT/'extra_beta_input_checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert all(checks.values()),checks
if __name__=='__main__':main()
