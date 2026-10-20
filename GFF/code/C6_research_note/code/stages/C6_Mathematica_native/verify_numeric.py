"""Independent Python/mpmath checks of the new native-function formulas.
No Wolfram kernel is called. Quadrature results are NOT certified intervals.
Inherited rational intervals are used only as post-computation references.
"""
from pathlib import Path
import json, time, argparse
import mpmath as mp
ROOT=Path(__file__).resolve().parent

def readj(n):return json.loads((ROOT/'inputs'/n).read_text())
def rational(v):return mp.mpf(v['numerator'])/mp.mpf(v['denominator'])
def midpoint(v):return (rational(v['lower'])+rational(v['upper']))/2

def run(dps):
 mp.mp.dps=dps;ts=time.monotonic();p=mp.pi;q=mp.mpf(1)/4;ell=mp.log(2)
 Q=mp.gamma(q)**4/p;rtQ=mp.sqrt(Q);G=mp.catalan
 fmt=lambda v:mp.nstr(v,dps)
 report={'working_digits':dps,'Wolfram_kernel_executed':False,'new_interval_certificate':False}
 # Native polylogarithmic quadrature.
 def pol(x):
  if not x:return mp.mpf(0)
  w=1-1j*x
  return -417792*mp.log(x)*mp.re((p*mp.log(w)**2/4-1j*mp.polylog(3,w))/w)
 ip=mp.quad(pol,[0,q,mp.mpf(1)/2,1])
 flat=readj('C6_flat_harmonic_intervals.json')
 runs=flat.get('runs',flat.get('enclosures',None))
 S5=midpoint(runs[-1]['S5'])
 shift=17408*G*p**3-40256*p**2*mp.zeta(3)
 report['polylog_integral']=fmt(ip)
 report['polylog_residual_vs_independent_Euler_S5']=fmt(abs(ip+417792*S5+shift))
 print('polylog',report['polylog_residual_vs_independent_Euler_S5'],flush=True)
 # Complete elliptic K conversion; stable complementary K via Carlson RF.
 def vals(x):
  lam=x/(2*(1+mp.sqrt(1-x)))
  return mp.ellipk(lam),mp.elliprf(0,lam,1)
 errs=[]
 for x in [mp.mpf(1)/100,mp.mpf(1)/5,mp.mpf(1)/2,mp.mpf(4)/5,mp.mpf(99)/100]:
  k,kc=vals(x)
  errs += [abs(2*k/p-mp.hyp2f1(q,q,1,x)),
           abs(2*(k+kc)-rtQ*mp.hyp2f1(q,q,mp.mpf(1)/2,1-x))]
  gexpr=[4*k*k/p**mp.mpf('1.5'),4*k*kc/p**mp.mpf('1.5'),2*(kc*kc-k*k)/p**mp.mpf('1.5')]
  for j in (1,2,3):
   actual=mp.meijerg([[mp.mpf(1)/2]*(3-j),[mp.mpf(1)/2]*j],[[0]*j,[0]*(3-j)],x)
   errs.append(abs(actual-gexpr[j-1]))
 report['elliptic_point_checks']=len(errs)
 report['maximum_elliptic_point_residual']=fmt(max(errs))
 def prim(u):
  if not u:return mp.mpf(0)
  x=u**4/2
  ka,kca=vals(x)
  lb=(1-mp.sqrt(x))/2
  kb=mp.ellipk(lb);kcb=mp.elliprf(0,lb,1)
  aa=(ka+kca)*(kb+kcb);bb=ka*kb
  return 64*mp.sqrt(2)*u*(15*aa*aa+24*aa*bb-4*bb*bb)/mp.sqrt(1-x)
 pa=mp.quad(prim,[0,q,mp.mpf(1)/2,1]) # 16 * folded Jacobian 4 sqrt2 u
 cert=readj('C6_complete_interval_certificate.json')
 v=cert['weighted_parts_in_C6_units']['primitive']
 pref=(mp.mpf(v['lower_numerator'])+mp.mpf(v['upper_numerator']))/mp.mpf(2)**(v['denominator_power_of_two']+1)*mp.mpf(2187)/96
 report['Pa_elliptic_integral']=fmt(pa)
 report['Pa_residual_vs_inherited_interval_midpoint']=fmt(abs(pa-pref))
 print('primitive',report['Pa_residual_vs_inherited_interval_midpoint'],flush=True)
 # Five univariate hypergeometric integral representations.
 ivals=readj('C6_standard_seventh_intervals.json')['runs'][-1]['values']
 seventh={};Zs={}
 for r in [1,2,3,5,7]:
  t=mp.mpf(r)/8;a=t+q;b=a+mp.mpf(1)/2
  up=[1,1+t]+[a]*7;lo=[t]+[b]*7;c0=t*(mp.gamma(a)/mp.gamma(b))**7
  def z(w):return c0*mp.hyper(up,lo,w)
  z0=z(-1)
  zp=(t+1)*(mp.gamma(a+1)/mp.gamma(b+1))**7*mp.hyper([2,2+t]+[a+1]*7,[t+1]+[b+1]*7,-1)
  def f(u):
   if not u:return mp.mpf(0)
   if u==1:return -8*zp
   return 4*u**(r+1)*(z0-z(-u**8))/(1-u**4)
  L=mp.quad(f,[0,q,mp.mpf(1)/2,mp.mpf(3)/4,1],method='gauss-legendre',maxdegree=7)
  nu=(t+1)*(a+b)/(2*a*b)*(mp.gamma(a+1)/mp.gamma(b+1))**7
  ref=-nu*midpoint(ivals[str(r)]['J'])
  seventh[str(r)]={'L_integral':fmt(L),'residual_vs_KdF_interval_midpoint':fmt(abs(L-ref))}
  Zs[str(r)]=z0
  print('seventh',r,fmt(abs(L-ref)),flush=True)
 report['seventh_integrals']=seventh
 # Wheel: finite proper subinterval integration, with an explicit analytic tail
 # envelope. This avoids describing high-cost near-endpoint pFq quadrature as a
 # high-precision independently certified calculation.
 ec=readj('C6_standard_even_intervals.json')['high_accuracy'][-1]
 c=mp.mpf(99)/100;uc=mp.root(c,4)
 wh={}
 for degree in [4,6]:
  up=[mp.mpf(1)/2]*4 if degree==4 else [mp.mpf(5)/4]+[mp.mpf(1)/2]*6
  lo=[1]*3 if degree==4 else [mp.mpf(1)/4]+[1]*5
  def fw(u):
   if not u:return mp.mpf(0)
   x=u**4
   return -16*u**3*mp.log(x)/(1+x)*mp.hyper(up,lo,x*x)
  part=mp.quad(fw,[0,uc/2,uc],method='gauss-legendre',maxdegree=6)
  ref=3*midpoint(ec['F'+str(degree)])
  upperU=mp.mpf(4)/3 if degree==4 else mp.mpf(13)/9
  allowance=2*upperU*(1-c)**2/(c*(1+c))
  wh[str(degree)]={'upper_integration_limit':fmt(c),'proper_integral':fmt(part),
   'inherited_full_value':fmt(ref),'omitted_endpoint_absolute_upper_bound':fmt(allowance),
   'tail_containment_check_with_floating_quadrature':bool(0<ref-part<allowance)}
  print('wheel',degree,wh[str(degree)]['tail_containment_check_with_floating_quadrature'],flush=True)
 report['wheel_checks']=wh
 report['scope']='New quadratures and point identities checked in Python. No independent new full-C6 interval certificate; no physical RG recertification.'
 report['seconds']=time.monotonic()-ts
 (ROOT/'results'/f'numerical_{dps}.json').write_text(json.dumps(report,indent=2)+'\n')
 print('complete',report['seconds'],flush=True)
 return report
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--digits',type=int,default=35);args=ap.parse_args();run(args.digits)
