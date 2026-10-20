"""Independent numerical check of exact hyperlog expressions by Taylor ODE.
Not used as an analytic proof or to choose a transcendental basis.
"""
import mpmath as mp,sympy as s,json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def evaluate(words,dps=80,R=100,ntaylor=240,nasym=100):
 mp.mp.dps=dps;start=time.time()
 closure={()}
 for w in words:
  for k in range(len(w)+1):closure.add(tuple(w[k:]))
 ws=sorted(closure,key=lambda w:(len(w),w));ix={w:i for i,w in enumerate(ws)}
 ti=[ix[w[1:]] if w else 0 for w in ws]
 aa=[mp.mpf(-w[0]) if w else mp.mpf(-1) for w in ws]
 vals=[mp.mpf(0) for w in ws];vals[0]=mp.mpf(1);t=mp.mpf(0);R=mp.mpf(R)
 steps=0
 while t<R:
  h=min(mp.mpf('.4')*(t+1),R-t);prev=vals.copy();ans=vals.copy();hn=mp.mpf(1)
  inv=[1/(t-a) for a in aa]
  for n in range(1,ntaylor+1):
   cn=[mp.mpf(0)]+[(prev[ti[i]]-(n-1)*prev[i])*inv[i]/n for i in range(1,len(ws))]
   hn*=h
   ans=[ans[i]+hn*cn[i] for i in range(len(ws))]
   prev=cn
  t+=h;vals=ans;steps+=1
  if steps%5==0:print('ODE',steps,'R',mp.nstr(t,8),'sec',time.time()-start,flush=True)
 # Regularized large-R constants, triangular in word length.
 L=mp.log(R);ZT={():mp.mpf(1)};PT={():[[mp.mpf(1)]]+[[mp.mpf(0)]]*nasym}
 def padd(a,b):return [(a[j] if j<len(a) else 0)+(b[j] if j<len(b) else 0) for j in range(max(len(a),len(b)))]
 for i,w in enumerate(ws[1:],1):
  tail=w[1:];nweight=len(w);P0=[mp.mpf(0)]+[ZT[w[k:]]/mp.factorial(k) for k in range(1,nweight+1)]
  Ps=[P0];Sn=PT[tail][0].copy();rem=mp.mpf(0);invpow=mp.mpf(1)
  for n in range(1,nasym+1):
   Sn=padd(PT[tail][n],[(-w[0])*c for c in Sn])
   yy=[mp.mpf(0)]*len(Sn)
   for d in range(len(Sn)-1,-1,-1):yy[d]=((d+1)*(yy[d+1] if d+1<len(yy) else 0)-Sn[d])/n
   Ps.append(yy);invpow/=R
   rem+=invpow*mp.polyval(list(reversed(yy)),L)
  z=vals[i]-mp.polyval(list(reversed(P0)),L)-rem
  ZT[w]=z;Ps[0][0]=z;PT[w]=Ps
 print('periods evaluated',len(ws),'seconds',time.time()-start,flush=True)
 return {w:ZT[w] for w in words}

def main():
 exprs={p.stem:s.sympify(p.read_text()) for p in ROOT.glob('*.expr') if p.name.endswith('_symbolic.expr') or p.name in ['Avv3_0_0.expr','Qv4_0_0.expr','Zv4_0_1.expr','Qdelta4_0_1.expr','Av5_0_1.expr','Qbase6_0_1.expr','Zbase4_0_0.expr']}
 symbols=set().union(*(ex.free_symbols for ex in exprs.values()))
 registry={x:tuple(int(t[1:]) for t in str(x).split('_')[1:]) for x in symbols if str(x).startswith('R_')}
 vals=evaluate(set(registry.values()),dps=int(sys.argv[1]) if len(sys.argv)>1 else 80)
 subs={x:s.Float(mp.nstr(vals[w],mp.mp.dps),mp.mp.dps) for x,w in registry.items()}
 for n in [2,3,4,5]:subs[s.Symbol('Z'+str(n))]=s.Float(mp.nstr(mp.zeta(n),mp.mp.dps),mp.mp.dps)
 out={}
 for name,ex in exprs.items():
  val=s.N(ex.subs(subs),mp.mp.dps-10)
  out[name]=str(val);print(name,val,flush=True)
 (ROOT/'hyperlog_numeric_check.json').write_text(json.dumps(out,indent=2))
 (ROOT/'regularized_period_values.json').write_text(json.dumps({','.join(map(str,w)):mp.nstr(v,mp.mp.dps) for w,v in vals.items()},indent=2))
if __name__=='__main__':main()
