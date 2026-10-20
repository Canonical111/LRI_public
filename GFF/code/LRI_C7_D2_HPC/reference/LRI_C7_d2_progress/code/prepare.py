from pathlib import Path
import json,sys,hashlib,mpmath as m
W=Path(__file__).resolve().parents[1];sys.path.insert(0,str(W/'code'))
from sobol_net import make_net
m.mp.dps=75
with open(W/'inputs/gamma_d2_7.txt','w')as f:
 for L in range(2,8):
  norm=2*(-1)**(L+1)/m.pi**L
  logs=[m.mpf(0)]+[(m.mpf(L/2)**k*m.polygamma(k-1,1)-2*L*m.mpf('.25')**k*m.polygamma(k-1,m.mpf('.5')))/m.factorial(k)for k in range(1,6)]
  print(7-L,m.nstr(norm,65),*map(lambda v:m.nstr(v,65),logs),file=f)
def numerator(z):
 a=m.mpf('.5')+z/4;b=m.mpf('.5')+3*z/4
 F1=m.hyper([1,z/2,a],[1-z/2,a+m.mpf('.5')],m.mpf('.25'))
 F2=m.hyper([z,2*a,b],[1+z/2,b+m.mpf('.5')],m.mpf('.25'))
 w=m.gamma(1+z)*m.gamma(1-z/2)*m.gamma(b)**2/(m.gamma(a)**2*m.gamma(2*b))
 return 4*F1-2*w*F2
rr=[]
for rad,n in[('.05',80),('.08',96)]:
 r=m.mpf(rad);v=[numerator(r*m.exp(2j*m.pi*(j+m.mpf('.5'))/n))for j in range(n//2)]
 cs=[-12*m.fsum(m.re(v[j]*m.exp(-2j*m.pi*(j+m.mpf('.5'))*k/n))for j in range(n//2))/(n*r**k)for k in range(1,7)]
 rr.append(dict(radius=rad,nodes=n,B2=list(map(str,cs))))
report=dict(dps=m.mp.dps,records=rr,max_changed_contour_difference=str(max(abs(m.mpf(a)-m.mpf(b))for a,b in zip(rr[0]['B2'],rr[1]['B2']))))
(W/'verification/two_loop_extension.json').write_text(json.dumps(report,indent=2))
(W/'inputs/two_loop.json').write_text(json.dumps(dict(B2=rr[-1]['B2']),indent=2))
inv={};summary={}
for L in range(2,8):
 rows=json.load(open(W/f'inputs/L{L}/inventory.json'));inv[str(L)]=rows
 from collections import Counter
 summary[L]=dict(Counter(g['status']for g in rows));summary[L]['primitive']=sum(g['primitive']for g in rows)
 for campaign,seed in [('pilot',12983),('a',837425),('b',915437)]:
  make_net(W/f'inputs/{campaign}_L{L}.net',16,4*L-1,52,seed+L*7893)
(W/'verification/inventory_summary.json').write_text(json.dumps(summary,indent=2))
print(report['max_changed_contour_difference']);print(json.dumps(summary))
