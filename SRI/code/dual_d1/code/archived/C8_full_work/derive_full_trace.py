"""Formal full fixed-point trace through delta^4; no period projection."""
from pathlib import Path
import sympy as s, json
ROOT=Path(__file__).resolve().parent
FT={'a':(1,1,0),'p':(1,0,1),'A':(1,2,0),'E':(1,1,1),'V':(1,0,2),'alpha':(1,3,0),'beta':(1,2,1),'gamma':(1,1,2),'W':(1,0,3),'b':(2,0,0),'G':(2,1,0),'R':(2,0,1),'Phi':(2,2,0),'Psi':(2,1,1),'S':(2,0,2),'J':(3,0,0),'Omega':(3,1,0),'U':(3,0,1),'J9':(4,0,0)}
HT={'c':(2,0,0),'f':(2,1,0),'q':(2,0,1),'L':(2,2,0),'M':(2,1,1),'Q':(2,0,2),'L3':(2,3,0),'M21':(2,2,1),'M12':(2,1,2),'k':(3,0,0),'N':(3,1,0),'P':(3,0,1),'N2':(3,2,0),'Nd':(3,1,1),'K':(4,0,0),'Kv':(4,1,0)}
N=4
keys={k:s.Symbol(k) for k in FT|HT}
F={(0,1,0):s.S.One,(1,0,0):s.S.One,**{m:keys[k] for k,m in FT.items()}}
H={(0,0,1):-s.S.One,(1,0,0):s.Integer(4),**{m:keys[k] for k,m in HT.items()}}
def add(a,b):return [s.expand(x+y) for x,y in zip(a,b)]
def mul(a,b):return [s.expand(sum(a[j]*b[i-j] for j in range(i+1))) for i in range(N+1)]
def scale(a,c):return [s.expand(c*x) for x in a]
def powr(a,k):
 out=[s.S.One]+[s.S.Zero]*N
 for i in range(k):out=mul(out,a)
 return out
def ev(poly,u,z,d):
 pw={0:{i:powr(u,i) for i in range(5)},1:{i:powr(z,i) for i in range(4)},2:{i:powr(d,i) for i in range(4)}}
 out=[s.S.Zero]*(N+1)
 for (i,j,k),c in poly.items():out=add(out,scale(mul(mul(pw[0][i],pw[1][j]),pw[2][k]),c))
 return out
def diff(poly,v):
 out={}
 for m,c in poly.items():
  if m[v]:mm=list(m);mm[v]-=1;out[tuple(mm)]=m[v]*c
 return out
u=[s.S.Zero]*5;z=u.copy();d=u.copy();d[1]=s.S.One
for order in range(1,5):
 h=ev(H,u,z,d)[order];f=ev(F,u,z,d)[order];u[order]=-h/4;z[order]=s.expand(-f-u[order]);print('fixed',order,flush=True)
 assert ev(F,u,z,d)[:order+1]==[0]*(order+1)
 assert ev(H,u,z,d)[:order+1]==[0]*(order+1)
trace=add(add(scale(ev(F,u,z,d),2),scale(mul(u,ev(diff(F,0),u,z,d)),2)),add(ev(H,u,z,d),mul(add([s.S.One]+[s.S.Zero]*4,z),ev(diff(H,1),u,z,d))))
ans=s.expand(8*trace[4]);new=['W','S','U','J9','L3','M21','M12','N2','Nd','Kv'];coefs={k:ans.coeff(keys[k]) for k in new};rest=s.expand(ans.subs({keys[k]:0 for k in new}))
assert s.expand(ans-rest-sum(keys[k]*v for k,v in coefs.items()))==0
out={'F':str(sum(c*s.Symbol('u')**i*s.Symbol('z')**j*s.Symbol('delta')**k for (i,j,k),c in F.items())),'H':str(sum(c*s.Symbol('u')**i*s.Symbol('z')**j*s.Symbol('delta')**k for (i,j,k),c in H.items())),'C8':str(ans),'old_part':str(rest),'new_coefficients':{k:str(v) for k,v in coefs.items()},'trace':list(map(str,trace)),'u':list(map(str,u)),'z':list(map(str,z))}
(ROOT/'full_trace.json').write_text(json.dumps(out,indent=2));print('C8 oldterms',len(s.Add.make_args(rest)),'new',coefs,flush=True)
