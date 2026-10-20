from pathlib import Path
import json,time,mpmath as m
W=Path(__file__).resolve().parents[1];m.mp.dps=65;q=m.mpf(3)/4;t0=time.time()
rows=[]
with (W/'inputs/gamma_d3_7.txt').open('w')as f:
 for L in range(2,8):
  norm=2*(-1)**(L+1)*m.gamma(2*q)**L/m.gamma(q)**(2*L)
  logs=[m.mpf(0)]+[(L*(m.polygamma(k-1,2*q)-m.polygamma(k-1,1))/2**k+(m.mpf(L)/2)**k*m.polygamma(k-1,1)-2*L*m.polygamma(k-1,q)/4**k)/m.factorial(k)for k in range(1,6)]
  print(7-L,m.nstr(norm,60),*[m.nstr(v,60)for v in logs],file=f)
  rows.append(dict(L=L,norm=str(norm),log_jets=list(map(str,logs))))
(W/'verification/gamma_jets.json').write_text(json.dumps(dict(d=3,dps=m.mp.dps,rows=rows),indent=2))
def numerator(z):
 a=q+z/4;b=q+3*z/4
 F1=m.hyper([2*q,z/2,a],[1-z/2,a+m.mpf('.5')],m.mpf('.25'))
 F2=m.hyper([z,2*a,b],[1+z/2,b+m.mpf('.5')],m.mpf('.25'))
 r=m.gamma(2*q+z/2)/m.gamma(1+z/2)
 w=r*r*m.gamma(1+z)*m.gamma(1-z/2)*m.gamma(b)**2/(m.gamma(a)**2*m.gamma(2*q)*m.gamma(2*b))
 return 4*F1-2*w*F2
records=[]
for rad,n in [('0.04',64),('0.07',80)]:
 r=m.mpf(rad);v=[numerator(r*m.exp(2j*m.pi*(j+m.mpf('.5'))/n))for j in range(n//2)]
 cs=[-12*m.fsum(m.re(v[j]*m.exp(-2j*m.pi*(j+m.mpf('.5'))*k/n))for j in range(n//2))/(n*r**k)for k in range(1,7)]
 records.append(dict(radius=rad,nodes=n,B2=list(map(str,cs))))
report=dict(d=3,dps=m.mp.dps,records=records,max_difference=str(max(abs(m.mpf(x)-m.mpf(y))for x,y in zip(records[0]['B2'],records[1]['B2']))),seconds=time.time()-t0)
(W/'inputs/two_loop.json').write_text(json.dumps(dict(dimension=3,order=7,B2=records[-1]['B2']),indent=2))
(W/'verification/two_loop_checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
