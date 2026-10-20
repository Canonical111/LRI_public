"""Independent Decimal-arithmetic Taylor/large-radius evaluation of periods.
The differential and asymptotic recurrences are derived in the note. Constants
are evaluated from the ODE; no zeta-basis ansatz is used. Only suffix expansions
needed by a later word are stored, keeping memory bounded at weight six.
"""
from decimal import Decimal,localcontext
from math import factorial
import time

def evaluate(words,dps=80,R=90,ntaylor=230,nasym=120,stepfrac='.35',guard=12):
 with localcontext() as ctx:
  ctx.prec=dps+guard;start=time.time();D=Decimal;zero=D(0);one=D(1)
  closure={()}
  for w in words:
   for k in range(len(w)+1):closure.add(tuple(w[k:]))
  ws=sorted(closure,key=lambda w:(len(w),w));ix={w:i for i,w in enumerate(ws)}
  tails=[ix[w[1:]] if w else 0 for w in ws];aa=[D(w[0]) if w else one for w in ws]
  needed={w[1:] for w in ws[1:]};haszero=any(a==0 for a in aa[1:]);vals=[zero]*len(ws);vals[0]=one;t=zero;end=D(R);sf=D(stepfrac);steps=0
  inverse_n=[zero]+[one/n for n in range(1,ntaylor+1)]
  while t<end:
   h=min(sf*(t if t>0 and haszero else t+1),end-t);prev=vals.copy();ans=vals.copy();hn=one
   inverse=[one/(t+a) if t+a else zero for a in aa]
   for n in range(1,ntaylor+1):
    cn=[zero];nm1=n-1;inn=inverse_n[n]
    for i in range(1,len(ws)):
     if t==0 and aa[i]==0:cn.append(cn[tails[i]]*inn)
     else:cn.append((prev[tails[i]]-nm1*prev[i])*inverse[i]*inn)
    hn*=h;ans=[v+hn*c for v,c in zip(ans,cn)];prev=cn
   t+=h;vals=ans;steps+=1
   if steps%5==0:print('DECIMAL ODE',steps,'T',str(t)[:12],'seconds',time.time()-start,flush=True)
  logR=end.ln();constants={():one};polynomials={():[[one]]+[[zero] for _ in range(nasym)]}
  def padd(a,b):return [(a[j] if j<len(a) else zero)+(b[j] if j<len(b) else zero) for j in range(max(len(a),len(b)))]
  def polyval(a,x):
   y=zero
   for c in reversed(a):y=y*x+c
   return y
  for i,w in enumerate(ws[1:],1):
   tail=w[1:];p0=[zero]+[constants[w[k:]]/factorial(k) for k in range(1,len(w)+1)];save=w in needed;ps=[p0] if save else None
   sn=polynomials[tail][0].copy();rem=zero;invpow=one
   for n in range(1,nasym+1):
    sn=padd(polynomials[tail][n],[-w[0]*c for c in sn]);yy=[zero]*len(sn)
    for j in range(len(sn)-1,-1,-1):yy[j]=((j+1)*(yy[j+1] if j+1<len(yy) else zero)-sn[j])/n
    if save:ps.append(yy)
    invpow/=end;rem+=invpow*polyval(yy,logR)
   z=vals[i]-polyval(p0,logR)-rem;constants[w]=z
   if save:ps[0][0]=z;polynomials[w]=ps
  print('DECIMAL PERIODS',len(ws),'stored suffixes',len(polynomials),'seconds',time.time()-start,flush=True)
  return {w:constants[w] for w in words}
