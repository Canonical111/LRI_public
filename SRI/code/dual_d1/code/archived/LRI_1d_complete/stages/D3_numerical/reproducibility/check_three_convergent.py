"""Independent convergent-integral checks of the new cubic beta derivatives."""
import mpmath as m,json
from pathlib import Path
m.mp.dps=75
root=Path(__file__).resolve().parent;d=json.loads((root/'data'/'three_derivatives.json').read_text())
A=-m.mpf(d['vv']['-2'])/2;E=4-m.mpf(d['vd']['-2'])
z2=m.zeta(2);z3=m.zeta(3);p=8-2*z2-7*z3-8*m.log(2)
K=lambda t:1/(t*t*(1-t)**2)
I2=m.quad(lambda t:K(t)*m.log1p(-t)**2,[0,m.mpf('.25'),m.mpf('.5')])
I3=m.quad(lambda t:K(t)*m.log1p(-t)**3,[0,m.mpf('.25'),m.mpf('.5')])
I12=m.quad(lambda t:K(t)*m.log(t)*m.log1p(-t)**2,[0,m.mpf('.25'),m.mpf('.5')])
print('A from Mellin =',m.nstr(A,65))
print('A from convergent integral =',m.nstr(-4*I2,65))
print('A exact =',m.nstr(-8-4*z2-2*z3+16*m.log(2),65))
print('A residual:',m.nstr(A+4*I2,10))
Eval=p-4*I3+8*I12
print('E from Mellin =',m.nstr(E,65))
print('E from independent convergent integral =',m.nstr(Eval,65))
print('E residual:',m.nstr(E-Eval,10))
assert abs(A+4*I2)<m.mpf('1e-42');assert abs(E-Eval)<m.mpf('1e-42')
print('Independent three-insertion derivative checks PASS.')
