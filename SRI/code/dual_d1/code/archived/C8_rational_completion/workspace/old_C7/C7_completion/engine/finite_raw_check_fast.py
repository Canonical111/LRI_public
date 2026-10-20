"""Numerical check of a complete exact finite-cutoff raw expression.
This evaluates hyperlogarithms by a convergent Taylor ODE, not asymptotic
period constants or fitted critical exponents.
"""
from pathlib import Path
from functools import lru_cache
import ast,json,argparse,time
import mpmath as mp
import sympy as s
from finite_gpl_check import finite_values,detrail
ROOT=Path(__file__).resolve().parent

def run(n,kind,der,epsilon,dps=80,ntaylor=250):
 mp.mp.dps=dps;a=mp.mpf(epsilon);T=(1-(n-1)*a)/a;le=mp.log(a);Lt=mp.log(T);st=time.time()
 env={'e':a,**{f'Z{k}':mp.zeta(k) for k in range(2,7)}}
 @lru_cache(None)
 def coefficient(text):
  def ev(q):
   if isinstance(q,ast.Constant):return mp.mpf(q.value)
   if isinstance(q,ast.Name):return env[q.id]
   if isinstance(q,ast.UnaryOp):
    x=ev(q.operand);return -x if isinstance(q.op,ast.USub) else x
   if isinstance(q,ast.BinOp):
    if isinstance(q.op,(ast.Add,ast.Sub)):
     todo=[(q,1)];out=mp.mpf(0)
     while todo:
      t,sgn=todo.pop()
      if isinstance(t,ast.BinOp) and isinstance(t.op,(ast.Add,ast.Sub)):
       todo.append((t.left,sgn));todo.append((t.right,sgn if isinstance(t.op,ast.Add) else -sgn))
      else:out+=sgn*ev(t)
     return out
    l=ev(q.left);r=ev(q.right)
    if isinstance(q.op,ast.Mult):return l*r
    if isinstance(q.op,ast.Div):return l/r
    if isinstance(q.op,ast.Pow):return l**r
   raise ValueError(ast.dump(q))
  return ev(ast.parse(text.replace('^','**'),mode='eval').body)
 L=s.Symbol('L')
 @lru_cache(None)
 def evalpoly(expr):
  ans=mp.mpf(0)
  for (j,),c in s.Poly(expr,L).terms():ans+=mp.mpf(int(c.p))/int(c.q)*Lt**j
  return ans
 fp=ROOT/f'{kind}{n}_{der}_negative.json';rr=json.loads(fp.read_text());comb={}
 for word,logs,cc in rr:
  fac=coefficient(cc)*mp.fprod(le+mp.log(k) for k in logs)
  for w,p in detrail(tuple(-a for a in word)).items():comb[w]=comb.get(w,mp.mpf(0))+fac*evalpoly(p)
 print('prepared',len(rr),'rows',len(comb),'words','seconds',time.time()-st,flush=True)
 vals=finite_values(comb,T,ntaylor=ntaylor);terms=[c*vals[w] for w,c in comb.items()];ans=mp.fsum(terms);condition=mp.fsum(map(abs,terms))/abs(ans)
 out={'n':n,'kind':kind,'derivative':der,'epsilon':epsilon,'dps':dps,'taylor_terms':ntaylor,'value':mp.nstr(ans,dps-15),'absolute_sum_condition':mp.nstr(condition,20),'seconds':time.time()-st,'method':'convergent finite-argument hyperlogarithm ODE','qualification':'No interval enclosure claimed.'}
 (ROOT/f'{kind}{n}_{der}_finite_raw_check_{dps}.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
 return out
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('n',type=int);ap.add_argument('kind');ap.add_argument('der');ap.add_argument('--epsilon',default='0.1');ap.add_argument('--dps',type=int,default=80);ap.add_argument('--taylor',type=int,default=250);a=ap.parse_args();run(a.n,a.kind,a.der,a.epsilon,a.dps,a.taylor)
