from hyperlog_core import *
import six_moment_reduction as base
from sympy.polys.fields import field
import sympy as s,time,json
from pathlib import Path
start=time.time()
B,xx,zz=field('x,z',QQ)
def bc(t):return B.from_expr(t.xreplace({base.x:s.Symbol('x'),base.z:s.Symbol('z')}))
c0=[bc(base.C[j,0]) for j in range(4)];cx=[bc(base.C[j,base.x]) for j in range(4)];cz=[bc(base.C[j,base.z]) for j in range(4)]
d0=[bc(base.D[j,0]) for j in range(4)];dx=[bc(base.D[j,base.x]) for j in range(4)];dz=[bc(base.D[j,base.z]) for j in range(4)]
Uvec=[[c0[j]-cx[j] for j in range(4)],cz,[d0[j]+dx[j] for j in range(4)],dz]
Vvec=[c0,[cx[j]-cz[j] for j in range(4)],d0,[dx[j]+dz[j] for j in range(4)]]
Q=[[bc(base.Q[j,k]) for k in range(4)] for j in range(4)];P=bc(base.pref)
x=2*e+u;z=4*e+v

def convert(f):
    def pconv(p):return sum((K(c)*x**ij[0]*z**ij[1] for ij,c in p.items()),K.zero)
    return pconv(f.numer)/pconv(f.denom)
# Each key contains a canonical word in u and a canonical word in v.
Us=[{((-e,),()):K.one},{((v+3*e,),()):K.one},
    {((),()):1/e-1/(x-e)},{((),()):1/(z-x+e)-1/(z-e)}]
Vs=[{((),(-3*e,)):K.one,((-3*e,),()):-K.one},
    {((),(-e,)):K.one,((v+e,),()):K.one},
    {((),()):1/(x+e)-1/(z-e)}, {((),()):1/e-1/(z-x-e)}]
expr={}
for i in range(4):
 for j in range(4):
  b=P*sum((Uvec[i][k]*Q[k][l]*Vvec[j][l] for k in range(4) for l in range(4) if Q[k][l]),B.zero)
  if not b:continue
  print('coupling',i,j,str(b),flush=True)
  cb=convert(b)
  for (wu,wv),cu in Us[i].items():
   for (wu2,wv2),cv in Vs[j].items():
    for ww,mu in shuffle(wu,wu2).items():
     for vv,mv in shuffle(wv,wv2).items():addto(expr,(ww,vv),cb*cu*cv*mu*mv)
expr=clean(expr)
print('Initial',len(expr),time.time()-start,flush=True)
# First integration, u=0..v, followed by exact fibration.
out={}
for n,((wu,wv),R) in enumerate(expr.items()):
 ant=integrate_rat(R,wu,1)
 for w,c in ant.items():
  cv=sub(c,1,v)
  for ww,mu in fibrate(w,2).items():
   for word,mv in shuffle(ww,wv).items():addto(out,word,cv*mu*mv)
  if not w:addto(out,wv,-sub(c,1,K.zero))
 print('first',n+1,'/',len(expr),'terms',len(out),'seconds',time.time()-start,flush=True)
out=clean(out)
(Path(__file__).resolve().parent / 'six_first.json').write_text(json.dumps([([str(a) for a in w],str(c)) for w,c in out.items()]))
print('Fibrated first',len(out),time.time()-start,flush=True)
# Second integration.
ans={}
for n,(w,R) in enumerate(out.items()):
 for ww,c in integrate_rat(R,w,2).items():addto(ans,ww,c)
 print('second',n+1,'/',len(out),'terms',len(ans),'seconds',time.time()-start,flush=True)
ans=clean(ans)
T=1-5*e;result={};singular={}
for w,c in ans.items():
 try:addto(result,w,sub(c,2,T))
 except ZeroDivisionError:singular[w]=c
 if not w:addto(result,(),-sub(c,2,K.zero))
result=clean(result)
(Path(__file__).resolve().parent / 'six_primitive.json').write_text(json.dumps([([str(a) for a in w],str(c)) for w,c in ans.items()]))
(Path(__file__).resolve().parent / 'six_result.json').write_text(json.dumps([([str(a) for a in w],str(c)) for w,c in result.items()]))
(Path(__file__).resolve().parent / 'six_singular.json').write_text(json.dumps([([str(a) for a in w],str(c)) for w,c in singular.items()]))
print('Done',len(result),'singular',len(singular),'seconds',time.time()-start,flush=True)
