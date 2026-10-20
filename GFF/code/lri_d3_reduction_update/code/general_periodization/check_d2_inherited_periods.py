"""Check new exact d=2 factorizations using the retained d=1 pFq values.
No d=2 period is used as input.  Previous fresh computations are comparisons.
"""
import mpmath as mp, sympy as sp, json,time
from pathlib import Path
mp.mp.dps=60
start=time.time();half=mp.mpf('.5');quarter=mp.mpf('.25')
fm=mp.hyper([quarter,quarter,half,half],[1-quarter,1-quarter,1],1)
fp=mp.hyper([1-quarter,1-quarter,half,half],[1+quarter,1+quarter,1],1)
bm=mp.gamma(quarter)**4*fm;bp=64*mp.pi**4/mp.gamma(quarter)**4*fp
p4=(bm**2-bp**2)/(4*mp.pi**3)
ys={}
for r in [1,2,3,5,7]:
 z=mp.mpf(r)/8;A=(mp.mpf(r)+2)/8;B=(mp.mpf(r)+6)/8
 ys[r]=z*(mp.gamma(A)/mp.gamma(B))**7*mp.hyper([1,1+z]+[A]*7,[z]+[B]*7,-1)
 print('Y',r,ys[r],flush=True)
c=mp.cos(mp.pi/8);s=mp.sin(mp.pi/8)
x0=ys[2];xp=c**7*ys[3]-s**7*ys[5];xm=c**7*ys[1]+s**7*ys[7]
p5=8/mp.pi*(25*x0*x0-28*mp.sqrt(2)*x0*(xp+xm)+18*(xp*xp+xm*xm)+28*xp*xm)
old=json.loads(Path(__file__).resolve().parents[2].joinpath('verification/general_periodization/d2_control.json').read_text())
x,p,m=sp.symbols('x p m',real=True);aa=(x+(p+m)/sp.sqrt(2))/2;gg=(x-(p+m)/sp.sqrt(2))/2;bb=(p-m)/2
check=sp.expand(aa*aa-14*aa*gg+8*bb*bb+113*gg*gg-(25*x*x-28*sp.sqrt(2)*x*(p+m)+18*(p*p+m*m)+28*p*m))
out={'working_digits':mp.mp.dps,'scope':'Literal ordinary mpmath.hyper evaluations; comparisons against independently recomputed d=2 Gamma-ratio/finite-sampling values. No interval bounds.',
'Y':{str(k):str(v) for k,v in ys.items()},'B_minus':str(bm),'B_plus':str(bp),
'P4':str(p4),'P5':str(p5),
'P4_difference':str(p4-mp.mpf(old['W4']['value'])),
'P5_difference':str(p5-mp.mpf(old['P5']['value'])),
'quadratic_basis_change_exact_zero':check==0,'seconds':time.time()-start}
print(out,flush=True)
Path(__file__).resolve().parents[2].joinpath('verification/general_periodization/d2_inherited_periods.json').write_text(json.dumps(out,indent=2))
