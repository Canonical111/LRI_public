"""Independent direct fixed-point/eigenvalue check of the extracted C7.
This is an algebraic consistency check of the stated beta jets, not a new
physical derivation or a numerical enclosure of the critical exponent.
"""
from pathlib import Path
import json,mpmath as mp,sys
ROOT=Path(__file__).resolve().parent;mp.mp.dps=160
old=json.loads((ROOT/'final_evaluation_run2.json').read_text())['coefficients']
source=sys.argv[1] if len(sys.argv)>1 else 'final_evaluation_C7_second.json'
new=json.loads((ROOT/source).read_text())['coefficients']
labels={'a':'a_check','p':'p_check','A':'A_check','E':'E_check','c':'c_check','f':'f_check','q':'q_check','b':'b_check','G':'G_check','k':'k_check'}
p={a:mp.mpf(old[b]) for a,b in labels.items()}
p.update({a:mp.mpf(old[a]) for a in ('V','R','J','L','M','N')})
p.update({a:mp.mpf(new[a]) for a in ('alpha','beta','gamma','Phi','Psi','Omega')})
p.update({a:mp.mpf(new[b]) for a,b in {'Q':'Qnew','P':'Pnew','K':'Knew'}.items()})
zeta=mp.zeta
cs=[mp.mpf(1),mp.mpf(-2),mp.mpf(1)/2,mp.mpf(39)/16+2*zeta(2),4-4*zeta(2)-8*zeta(3),mp.mpf(11249)/1024-mp.mpf(361)/16*zeta(2)+24*zeta(3)+mp.mpf(49)/2*zeta(4),26-38*zeta(2)+104*zeta(3)-80*zeta(4)-272*zeta(5)+112*zeta(2)*zeta(3)]
expected=mp.mpf(new['C7']);out=[]
for power in [6,10,14,18,22]:
 x=mp.mpf(10)**(-power);d=2*x
 def F(u,z):
  return z+u*(1+p['a']*z+p['p']*d+p['A']*z*z+p['E']*z*d+p['V']*d*d+p['alpha']*z**3+p['beta']*z*z*d+p['gamma']*z*d*d)+u*u*(p['b']+p['G']*z+p['R']*d+p['Phi']*z*z+p['Psi']*z*d)+u**3*(p['J']+p['Omega']*z)
 def H(u,z):return -d+4*u+u*u*(p['c']+p['f']*z+p['q']*d+p['L']*z*z+p['M']*z*d+p['Q']*d*d)+u**3*(p['k']+p['N']*z+p['P']*d)+p['K']*u**4
 u,z=mp.findroot((F,H),(d/4,-d/4),tol=mp.mpf('1e-115'),maxsteps=100)
 bu=lambda u,z:2*u*F(u,z);bz=lambda u,z:(1+z)*H(u,z)
 mat=mp.matrix([[mp.diff(lambda t:fun(t,z),u),mp.diff(lambda t:fun(u,t),z)] for fun in [bu,bz]])
 T=mat[0,0]+mat[1,1];D=mp.det(mat);dim=1+T/2-mp.sqrt(T*T/4-D)
 residual=(dim-mp.fsum(cs[n]*x**(mp.mpf(n)/2) for n in range(7)))/x**(mp.mpf(7)/2)
 record={'x':str(x),'extracted_C7':mp.nstr(residual,45),'difference':mp.nstr(residual-expected,35),'fixed_point_residual':mp.nstr(max(abs(F(u,z)),abs(H(u,z))),10)}
 print(record,flush=True);out.append(record)
assert abs(residual-expected)<mp.mpf('1e-4')
(ROOT/'direct_eigenvalue_limit_check.json').write_text(json.dumps({'source':source,'checks':out,'qualification':'Finite-jet algebra check; remainder need not be a bound on omitted physical orders.'},indent=2))
