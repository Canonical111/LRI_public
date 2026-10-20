import mpmath as mp,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
out=[]
for dps in (40,80):
 mp.mp.dps=dps
 pi=mp.pi;A=pi+4*mp.log(2);Q=mp.gamma(mp.mpf(1)/4)**4/pi
 Cd=96*Q-42*A**2-18*A*pi-1227*pi**2
 Cs=60*Q-mp.mpf(105)/4*A**2-9*A*pi-mp.mpf(2469)/4*pi**2
 X=-Cd;Y=-Cs;rho=mp.sqrt(X*X+Y*Y);alpha=mp.atan(Y/X)/pi
 U4=mp.hyper([mp.mpf('.5')]*4,[1]*3,1)
 U6=mp.hyper([mp.mpf('1.25')]+[mp.mpf('.5')]*6,[mp.mpf('.25')]+[1]*5,1)
 def kernel(s,alpha):
  return mp.exp(2*mp.loggamma(s)+3*mp.loggamma(mp.mpf('.5')-s)-2*mp.loggamma(1-s)-mp.loggamma(mp.mpf('.5')+s)-mp.loggamma(alpha+s)-mp.loggamma(1-alpha-s))
 t=time.time()
 gv=mp.quad(lambda t:mp.re(kernel(mp.mpf('.25')+1j*t,alpha)),[0,mp.mpf('.5'),2,10,mp.inf])/pi
 g22=mp.quad(lambda t:abs(mp.gamma(mp.mpf('.25')+1j*t)/mp.gamma(mp.mpf('.75')+1j*t))**4,[0,mp.mpf('.5'),2,10,mp.inf])/pi
 old=4*pi**3*Cd*U4+2*pi**4*Cs*U6
 new=-4*pi**2*rho*gv
 r={k:mp.nstr(v,dps) for k,v in locals().copy().items() if k in ('A','Q','Cd','Cs','X','Y','rho','alpha','U4','U6','gv','g22','old','new')}
 r.update(dps=dps,elapsed=time.time()-t,error_lower=mp.nstr(abs(old-new),8),error_U6=mp.nstr(abs(U6-2*g22/pi**2),8))
 print(json.dumps(r,indent=2),flush=True);out.append(r)
json.dump(out,open(ROOT/'results'/'numerical_checks.json','w'),indent=2)
