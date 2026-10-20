from pathlib import Path
import mpmath as m,json,time
W=Path(__file__).resolve().parents[1];m.mp.dps=60;t=time.time();records=[];d=m.mpf(3);q=d/4

def numerator(z):
 a=q+z/4;b=q+3*z/4
 F1=m.hyper([d/2,z/2,a],[1-z/2,a+m.mpf('.5')],m.mpf('.25'))
 F2=m.hyper([z,2*a,b],[1+z/2,b+m.mpf('.5')],m.mpf('.25'))
 r=m.gamma(d/2+z/2)/m.gamma(1+z/2)
 w=r*r*m.gamma(1+z)*m.gamma(1-z/2)*m.gamma(b)**2/(m.gamma(a)**2*m.gamma(d/2)*m.gamma(2*b))
 return 4*F1-2*w*F2
for rad,n in [('0.05',48),('0.07',64)]:
 r=m.mpf(rad);v=[numerator(r*m.exp(2j*m.pi*(j+m.mpf('.5'))/n))for j in range(n//2)]
 coeff=[]
 for k in range(1,6):
  val=2*m.fsum(m.re(v[j]*m.exp(-2j*m.pi*(j+m.mpf('.5'))*k/n))for j in range(n//2))/(n*r**k)
  coeff.append(-6*val)
 records.append({'radius':rad,'nodes':n,'b2_jets':[str(v)for v in coeff],'c2_jets':[str(v/6)for v in coeff]})
(W/'records/two_loop_d3.json').write_text(json.dumps({'d':3,'dps':60,'records':records,'max_difference':str(max(abs(m.mpf(x)-m.mpf(y))for x,y in zip(records[0]['b2_jets'],records[1]['b2_jets']))),'seconds':time.time()-t},indent=2))
print(records[-1],time.time()-t)
