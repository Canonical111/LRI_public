import json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
import mpmath as m
m.mp.dps=150
D=json.load(open(ROOT/'inputs'/'C6_three_residual_sums_intervals.json'))
def midpoint(key):
 v=D['values'][key]
 return (m.mpf(int(v['lower_numerator']))+m.mpf(int(v['upper_numerator'])))/m.power(2,v['denominator_power_of_two']+1)
p=m.pi;l=m.log(2);q=m.gamma(m.mpf(1)/4)**4/p;g=m.catalan;z3=m.zeta(3);z5=m.zeta(5)
# A finite search in explicit candidate bases is only exploratory.
cases=[
('wheel_elementary',midpoint('Wzero_n_ge_0'),['pi^2','pi^3','zeta3','pi*zeta3','Catalan','pi*Catalan','log2*pi^2'],[p*p,p**3,z3,p*z3,g,p*g,l*p*p]),
('primitive_gamma',midpoint('Pa'),['Q^3','Q^2*pi','Q*pi^3','Q*zeta3','pi^5','pi^2*zeta3','zeta5','pi^4*log2'],[q**3,q*q*p,q*p**3,q*z3,p**5,p*p*z3,z5,p**4*l]),
('seventh_elementary',midpoint('M7'),['1','pi','pi^2','pi^3','log2','log2^2','log2^3','pi*log2','pi*log2^2','pi^2*log2','zeta3'],[m.mpf(1),p,p*p,p**3,l,l*l,l**3,p*l,p*l*l,p*p*l,z3]),
]
res=[]
for label,target,names,vals in cases:
 t=time.time(); rel=m.pslq(m.matrix([target]+vals),tol=m.mpf('1e-125'),maxcoeff=10**6,maxsteps=20000)
 res.append({'label':label,'basis':['target']+names,'result':rel,'tol':'1e-125','maxcoeff':10**6,'seconds':time.time()-t})
 print(label,rel,time.time()-t,flush=True)
json.dump({'working_digits':150,'input':'C6_three_residual_sums_intervals.json','scope':'Finite exploratory integer-relation search only. None is not a proof of nonexistence or independence. No coefficients fitted for C6.','runs':res},open(ROOT/'recognition.json','w'),indent=2)
