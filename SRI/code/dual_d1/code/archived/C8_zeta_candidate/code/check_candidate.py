"""Recognize on first run, then test fixed relation on second run. Not an analytic period proof."""
from pathlib import Path
from fractions import Fraction as F
import json,mpmath as mp
from check_assembly import assemble
ROOT=Path(__file__).resolve().parent.parent
mp.mp.dps=115
r=assemble();z=mp.zeta
basis=[z(2),z(3),z(4),z(5),z(2)*z(3),z(6),z(3)**2,z(7),z(2)*z(5),z(3)*z(4)]
first=mp.mpf(r['runs'][0]['C8']);second=mp.mpf(r['runs'][1]['C8'])
expected=[3,534,-330,-339,-14676,7128,8630,-5616,36504,-18144,-4608]
rel=mp.pslq(mp.matrix([first-88]+basis),tol=mp.mpf('1e-55'),maxcoeff=100000,maxsteps=10000)
assert rel==expected or rel==[-v for v in expected]
coeff=[F(-v,expected[0]) for v in expected[1:]]
candidate=mp.mpf(88)+mp.fsum(mp.mpf(c.numerator)/c.denominator*b for c,b in zip(coeff,basis))
err=second-candidate
assert abs(err)<mp.mpf('1e-80')
piform=88-mp.mpf(89)/3*mp.pi**2+mp.mpf(113)/90*mp.pi**4-mp.mpf(1726)/567*mp.pi**6+(110-396*mp.pi**2+mp.mpf(256)/15*mp.pi**4)*z(3)+(4892+1008*mp.pi**2)*z(5)+1872*z(3)**2-12168*z(7)
assert abs(candidate-piform)<mp.mpf('1e-100')
free_relation=mp.pslq(mp.matrix([second,mp.mpf(1)]+basis),tol=mp.mpf('1e-80'),maxcoeff=100000,maxsteps=20000)
free_expected=[3,-264]+expected[1:]
assert free_relation==free_expected or free_relation==[-v for v in free_expected]
report={'free_rational_intercept_relation':free_relation,'free_rational_intercept_recovered':'88','relation_first_run':rel,'candidate':mp.nstr(candidate,105),'second_run':mp.nstr(second,105),'second_run_minus_candidate':mp.nstr(err,35),'first_run_minus_candidate':mp.nstr(first-candidate,30),'two_P6_runs_C8_difference':mp.nstr(second-first,30),'coefficients':['88']+list(map(str,coeff)),'pi_form_matches':True,'analytic_zeta_proof':False,'interval_certified':False,'prior_rational_88_used_to_choose_basis':True}
(ROOT/'verification/candidate_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
