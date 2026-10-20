#!/usr/bin/env python3
from decimal import Decimal,localcontext
from pathlib import Path
import json,time,sys
import sympy as s
from read_expression import parse
from finite_gpl_check import detrail
ROOT=Path(__file__).resolve().parent
def finite_values(words,T,dps=55,N=180,sf='.3'):
 with localcontext() as ctx:
  ctx.prec=dps+15;D=Decimal
  close={()}
  for word in words:
   for j in range(len(word)+1):close.add(tuple(word[j:]))
  ws=sorted(close,key=lambda w:(len(w),w));ix={w:i for i,w in enumerate(ws)}
  tails=[ix[w[1:]] if w else 0 for w in ws]
  vals=[D(1)]+[D(0)]*(len(ws)-1);t=D(0);T=D(T);sf=D(sf)
  aa=[D(w[0]) if w else D(1) for w in ws]
  haszero=any(a==0 for a in aa[1:])
  invn=[D(0)]+[D(1)/j for j in range(1,N+1)]
  while t<T:
   h=min(T-t,sf*(t if t>0 and haszero else t+1))
   prev=vals.copy();ans=vals.copy();hn=D(1)
   inverses=[D(1)/(t+a) if t+a else D(0) for a in aa]
   for n in range(1,N+1):
    cur=[D(0)]
    for i in range(1,len(ws)):
     if t==0 and aa[i]==0:cur.append(cur[tails[i]]*invn[n])
     else:cur.append((prev[tails[i]]-(n-1)*prev[i])*inverses[i]*invn[n])
    hn*=h;ans=[a+hn*c for a,c in zip(ans,cur)];prev=cur
   t+=h;vals=ans
  return {w:vals[ix[w]] for w in words}
def main():
 tag=sys.argv[1];start=time.time();eps=s.Rational(1,10);T=s.Integer(7);D=Decimal
 rows=json.loads((ROOT/(tag+'_negative.json')).read_text())
 expr=[];words=set()
 for ww,logs,c in rows:
  det=detrail(tuple(-a for a in ww))
  expr.append((det,logs,c));words.update(det)
 vals=finite_values(words,str(T))
 with localcontext() as ctx:
  ctx.prec=65
  le=D(str(s.N(s.log(eps),65)));lt=D(str(s.N(s.log(T),65)))
  logs={n:D(str(s.N(s.log(n),65))) for _,ls,_ in expr for n in ls}
  ans=D(0);se=s.Symbol('e');symL=s.Symbol('L')
  for dic,ll,c in expr:
   co=parse(c).subs(se,eps)
   for n in range(2,9):co=co.subs(s.Symbol(f'Z{n}'),s.zeta(n))
   co=D(str(s.N(co,65)))
   for a in ll:co*=le+logs[a]
   vv=D(0)
   for w,pol in dic.items():
    mult=D(str(s.N(pol.subs(symL,s.Float(str(lt),65)),65)))
    vv+=vals[w]*mult
   ans+=co*vv
  out={'tag':tag,'eps':'1/10','value':str(ans),'words':len(words),
       'method':'finite-argument Taylor ODE of the exact integrated kernel',
       'seconds':time.time()-start,'interval_certified':False}
 (ROOT.parent/'verification'/(tag+'_finite_check.json')).write_text(json.dumps(out,indent=2))
 print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':main()
