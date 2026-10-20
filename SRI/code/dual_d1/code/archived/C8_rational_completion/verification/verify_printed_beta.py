"""Optional SymPy check of the beta polynomials printed in the note.
No new integral is evaluated. The check compares their full-Jacobian trace
with the accepted independently assembled result rather than a conjecture.
"""
from pathlib import Path
import json
import sympy as s
u,z,d=s.symbols('u z delta');Q=s.Rational
F=z+u*(1+8*d-8*z**2-16*d*z-24*d**2+16*z**3+72*d*z**2+160*d**2*z+168*d**3)+u**2*(-18+36*z+154*d-240*z**2+22*d*z-1751*d**2)+u**3*(-16-904*z+Q(16534,3)*d)-Q(10192,3)*u**4
H=-d+4*u+u**2*(-16+32*z-32*d-288*d*z+160*d**2+128*z**3-384*d*z**2+2720*d**2*z)+u**3*(128+16*z-1976*d+3712*z**2-20848*d*z)+u**4*(Q(2032,3)+Q(77920,3)*z)
us=d/4+d**2/4+5*d**3/8+Q(505,96)*d**4
zs=-d/4-Q(9,8)*d**2-Q(65,16)*d**3-Q(1471,96)*d**4
sub={u:us,z:zs}
def jet(p):return s.Poly(s.expand(p.subs(sub)),d)
for p in (F,H):
 j=jet(p)
 assert all(j.nth(k)==0 for k in range(5))
T=jet(s.diff(2*u*F,u)+s.diff((1+z)*H,z))
trace=[str(T.nth(k)) for k in range(5)]
root=Path(__file__).resolve().parent.parent
accepted=json.loads((root/'result.json').read_text())
assert trace==accepted['independent_trace']['trace']
assert str(8*T.nth(4))==accepted['C8_weight_zero']
report={'status':'printed_polynomials_and_full_Jacobian_exactly_match','trace':trace,'C8_weight_zero':str(8*T.nth(4)),'fixed_point_constraints_vanish_through_delta4':True}
(root/'verification/printed_beta_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
