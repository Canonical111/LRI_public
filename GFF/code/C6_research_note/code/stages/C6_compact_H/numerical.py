#!/usr/bin/env python3
"""Floating-point checks; no interval or independent 2D Barnes certificate."""
from pathlib import Path
import argparse,json,time
import mpmath as mp
BASE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--dps',type=int,default=50);ap.add_argument('--meijer',action='store_true');args=ap.parse_args()
mp.mp.dps=args.dps;p=mp.pi;half=mp.mpf(1)/2;start=time.time()
l=(28+mp.sqrt(409)*mp.cos(mp.acos(7298/(409*mp.sqrt(409)))/3))/3
eta=mp.sqrt((40*l-279)/400);mu=2*(21*l-150)/(40*l-279)
params={};fmt=lambda x:mp.nstr(x,args.dps)
report={'working_dps':args.dps,'rigorous_interval':False,'lambda':fmt(l),'eta':fmt(eta),'chi':fmt(mu),'parameters':{},'gamma_kernel_checks':[],'meijerg_checks':[], 'meijerg_failures':[]}
for sig in [1,-1]:
 B=mp.mpf(21)/20+sig*eta;C=l/10+sig*eta*mu;D=mp.sqrt((1-C)**2+B*B)
 beta=mp.atan(B/2+1j*mp.sqrt(C-B*B/4))/p
 params[sig]=(B,C,D,beta,mp.conj(beta))
for sig,pars in params.items():
 B,C,D,b,bc=pars
 report['parameters'][str(sig)]={'B':fmt(B),'C':fmt(C),'D':fmt(D),'beta_upper':{'real':fmt(mp.re(b)),'imag':fmt(mp.im(b))}}
 for im in ['0.17','0.9','3']:
  s=mp.mpf('.25')+1j*mp.mpf(im)
  T=mp.gamma(s)**3*mp.gamma(half-s)**2/(mp.gamma(half+s)*mp.gamma(s+b)*mp.gamma(1-s-b)*mp.gamma(s+bc)*mp.gamma(1-s-bc))
  R=(mp.gamma(s)/mp.gamma(half+s))**3;tt=mp.tan(p*s);expected=R*(tt*tt+B*tt+C)/D
  report['gamma_kernel_checks'].append({'sigma':sig,'imag_s':im,'absolute_difference':fmt(abs(T-expected))})
def bases(x):
 lam=x/(2*(1+mp.sqrt(1-x)));K=mp.ellipk(lam);Kc=mp.elliprf(0,lam,1);f=p**mp.mpf('1.5')
 return (4*K*K/f,4*K*Kc/f,2*(Kc*Kc-K*K)/f)
if args.meijer:
 for sig,pars in params.items():
  B,C,D,b,bc=pars
  for xstr in ['0.2','0.5','0.8']:
   x=mp.mpf(xstr);v=bases(x);expected=(v[0]+B*v[1]+C*v[2])/D
   try:
    got=mp.meijerg(([half,half],[half,b,bc]),([0,0,0],[b,bc]),x,series=1)
    report['meijerg_checks'].append({'sigma':sig,'x':xstr,'difference':fmt(abs(got-expected))})
    print('Meijer check',sig,xstr,fmt(abs(got-expected)),flush=True)
   except Exception as ex:report['meijerg_failures'].append({'sigma':sig,'x':xstr,'exception':repr(ex)})
def pair_data(t):
 x=t**4/2;lx=x/(2*(1+mp.sqrt(1-x)));ly=(1-mp.sqrt(x))/2
 kx=mp.ellipk(lx);cx=mp.elliprf(0,lx,1);ky=mp.ellipk(ly);cy=mp.elliprf(0,ly,1);f=p**mp.mpf('1.5')
 gx=(4*kx*kx/f,4*kx*cx/f,2*(cx*cx-kx*kx)/f);gy=(4*ky*ky/f,4*ky*cy/f,2*(cy*cy-ky*ky)/f)
 return x,kx,cx,ky,cy,gx,gy
def local(g,sgn):
 B,C,D,_,_=params[sgn];return (g[0]+B*g[1]+C*g[2])/D
def new_kernel(t):
 if not t:return mp.mpf(0)
 x,kx,cx,ky,cy,gx,gy=pair_data(t)
 return 2*mp.sqrt(2)*t/mp.sqrt(1-x)*(local(gx,1)*local(gy,-1)+local(gy,1)*local(gx,-1))
def old_kernel(t):
 if not t:return mp.mpf(0)
 x,kx,cx,ky,cy,_,_=pair_data(t);R=4*(kx+cx)*(ky+cy);S=8*kx*ky
 return 4*mp.sqrt(2)*t/mp.sqrt(1-x)*(15*R*R+12*R*S-S*S)
def zero_kernel(t):
 if not t:return mp.mpf(0)
 x,_,_,_,_,gx,gy=pair_data(t);z=gx[2]*gy[2]+gx[0]*gy[2]+gx[2]*gy[0]-gx[1]*gy[1]
 return 4*mp.sqrt(2)*t/mp.sqrt(1-x)*z
pts=[0,mp.mpf('.25'),mp.mpf('.5'),mp.mpf('.75'),1]
Hstar=mp.quad(new_kernel,pts);Pa_new=80*p**3*Hstar;Pa_old=mp.quad(old_kernel,pts);zrel=mp.quad(zero_kernel,pts)
report.update({'new_bivariate_H_via_proved_beta_pairing':fmt(Hstar),'Pa_from_new_H':fmt(Pa_new),'Pa_from_old_symmetric_quartic':fmt(Pa_old),'Pa_absolute_difference':fmt(abs(Pa_new-Pa_old)),'inherited_contour_relation_quadrature_residual':fmt(abs(zrel)),'normalization_product_minus_one':fmt(params[1][2]*params[-1][2]-1),'seconds':time.time()-start,'method_note':'New H evaluated via the proved beta-product formula, not independent 2D Barnes quadrature. Gamma-product kernels and optional direct univariate G calls checked separately. No full-C6 reevaluation or interval certificate.'})
out=BASE/'results'/f'numerical_{args.dps}.json';out.write_text(json.dumps(report,indent=2)+'\n')
print('Hstar',fmt(Hstar));print('Pa',fmt(Pa_new));print('Pa discrepancy',fmt(abs(Pa_new-Pa_old)));print('seconds',report['seconds'])
