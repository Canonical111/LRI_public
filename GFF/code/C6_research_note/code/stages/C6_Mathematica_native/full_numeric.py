from pathlib import Path
import sys,json,time
import mpmath as mp
import sympy as sp
ROOT=Path(__file__).resolve().parent
mp.mp.dps=int(sys.argv[1]) if len(sys.argv)>1 else 35
p=mp.pi;Q=mp.gamma(mp.mpf(1)/4)**4/p;G=mp.catalan;A=p+4*mp.log(2)
D=json.loads((ROOT/'results/expression.json').read_text())
def expr(v):
 return mp.mpf(str(sp.sympify(v,locals={'Gamma':sp.gamma,'sqrt':sp.sqrt,'sin':sp.sin,'cos':sp.cos,'A':sp.Symbol('A'),'Q':sp.Symbol('Q'),'G':sp.Symbol('G'),'pi':sp.Symbol('pi'),'c7':sp.Symbol('c7'),'s7':sp.Symbol('s7')}).subs({sp.Symbol('A'):sp.Float(str(A),mp.mp.dps),sp.Symbol('Q'):sp.Float(str(Q),mp.mp.dps),sp.Symbol('G'):sp.Float(str(G),mp.mp.dps),sp.Symbol('pi'):sp.pi,sp.Symbol('z3'):sp.zeta(3),sp.Symbol('z5'):sp.zeta(5),sp.Symbol('c7'):sp.cos(sp.pi/8)**7,sp.Symbol('s7'):sp.sin(sp.pi/8)**7}).evalf(mp.mp.dps)))
def frac(a):return mp.mpf(a) if '/' not in a else mp.mpf(a.split('/')[0])/mp.mpf(a.split('/')[1])
vals={};tot=mp.mpf(0);start=time.monotonic()
for row in D['ordinary_hypergeometric_terms']:
 v=expr(row['prefactor'])*mp.hyper([frac(a) for a in row['upper']],[frac(a) for a in row['lower']],frac(row['argument']))
 w=expr(row['coefficient_in_r6'])*v;tot+=w;vals[row['id']]=mp.nstr(v,mp.mp.dps)
 print(row['id'],mp.nstr(v,14),time.monotonic()-start,flush=True)
# Full integral of the wheel, with no imported interval or coefficient series.
wh=mp.mpf(0)
for power in (4,6):
 up=[mp.mpf(1)/2]*4 if power==4 else [mp.mpf(5)/4]+[mp.mpf(1)/2]*6
 lo=[1]*3 if power==4 else [mp.mpf(1)/4]+[1]*5
 def f(u):
  if u==0 or u==1:return 0
  x=u**4
  return -16*u**3*mp.log(x)/(1+x)*mp.hyper(up,lo,x*x)
 v=mp.quad(f,[0,mp.mpf(1)/2,mp.mpf(9)/10,1],method='gauss-legendre',maxdegree=7)
 wh += (-3144*p**3 if power==4 else -1965*p**4)*v
 vals['D'+str(power)+'_full_integral']=mp.nstr(v,mp.mp.dps)
 print('FULL WHEEL',power,mp.nstr(v,16),time.monotonic()-start,flush=True)
# Use the newly computed native polylog/primitive/seventh quadratures of the
# separate run (not inherited values). They were computed at at least this dps.
report=json.loads((ROOT/'results'/f'numerical_{mp.mp.dps}.json').read_text())
pol=mp.mpf(report['polylog_integral']);pr=96*mp.mpf(report['Pa_elliptic_integral'])
sev=mp.mpf(0)
for r,row in D['finite_weights'].items():sev+=9408*p**mp.mpf('1.5')*expr(row['p_r'])*mp.mpf(report['seventh_integrals'][r]['L_integral'])
known=expr(D['native_known_polynomial']);t3=-39168*p*p*mp.im(mp.polylog(3,mp.mpc(1,1)/2))
res=(known+tot+t3+wh+pol+pr+sev)/2187
out={'working_digits':mp.mp.dps,'C6_native_quadratures':mp.nstr(res,mp.mp.dps),'parts_r6':{k:mp.nstr(v,mp.mp.dps) for k,v in {'known':known,'ordinary':tot,'trilog':t3,'wheel':wh,'polylog':pol,'seventh':sev,'primitive':pr}.items()},'ordinary_and_wheel_values':vals,'seconds':time.monotonic()-start,'Wolfram_kernel_executed':False,'certified':False}
(ROOT/'results'/f'full_numerical_{mp.mp.dps}.json').write_text(json.dumps(out,indent=2)+'\n')
print('FULL C6',out['C6_native_quadratures'],flush=True)
