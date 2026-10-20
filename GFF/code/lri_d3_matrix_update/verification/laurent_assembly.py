"""Precision-preserving independent Laurent/minimal-subtraction assembly."""
from pathlib import Path
import json, sys
import mpmath as mp
mp.mp.dps=80
R=Path(__file__).parent
SOURCE=R/'inputs/historical_five_loop_results.json'

def la_add(a,b,scale=1):
 d=dict(a)
 for k,v in b.items():d[k]=d.get(k,mp.mpf(0))+scale*v
 return {k:v for k,v in d.items()if v}
def la_mul(a,b):
 d={}
 for i,x in a.items():
  for j,y in b.items():d[i+j]=d.get(i+j,mp.mpf(0))+x*y
 return {k:v for k,v in d.items()if v}
def gc(a,b,n):
 c=[{}for _ in range(n+1)]
 for i,x in enumerate(a[:n+1]):
  for j,y in enumerate(b[:n+1-i]):c[i+j]=la_add(c[i+j],la_mul(x,y))
 return c

def scalar_mul(a,b,n):
 c=[mp.mpf(0)]*(n+1)
 for i,x in enumerate(a[:n+1]):
  for j,y in enumerate(b[:n+1-i]):c[i+j]+=x*y
 return c

def C_from_rg(beta,gamma):
 inv=[1/beta[0]]
 for n in range(1,5):inv.append(-mp.fsum(beta[j]*inv[n-j]for j in range(1,n+1))/beta[0])
 cs=[mp.mpf('.5')]
 for n in range(1,6):
  pw=[mp.mpf(1)]
  for _ in range(n):pw=scalar_mul(pw,inv,n-1)
  c=mp.fsum((i+1)*gamma[i]*pw[n-1-i]for i in range(n))/n
  if n==1:c-=mp.mpf('.5')
  cs.append(c)
 return cs

def assemble(data):
 A={1:{-1:mp.mpf(3)}};B={1:{-1:mp.mpf(1)}}
 for L,pair in data.items():
  L=int(L);A[L]={int(k):mp.mpf(str(v))for k,v in pair[0].items()};B[L]={int(k):mp.mpf(str(v))for k,v in pair[1].items()}
 G=[{}, {0:mp.mpf(1)}]+[{}for _ in range(5)]
 for n in range(2,7):
  pw=G[:];v={}
  for L in range(1,n):
   pw=gc(pw,G,n);v=la_add(v,la_mul(A[L],pw[n]),(-1)**L)
  G[n]={k:-x for k,x in v.items()if k<0}
 H=[{0:mp.mpf(1)}]+[{}for _ in range(5)]
 pw=[{0:mp.mpf(1)}]+[{}for _ in range(5)]
 for L in range(1,6):
  pw=gc(pw,G,5)
  for i in range(6):H[i]=la_add(H[i],la_mul(B[L],pw[i]),(-1)**L)
 Z=[{0:mp.mpf(1)}]
 for n in range(1,6):
  v={}
  for i in range(n):v=la_add(v,la_mul(H[n-i],Z[i]))
  Z.append({k:-x for k,x in v.items()if k<0})
 beta=[L*G[L+1].get(-1,mp.mpf(0))for L in range(1,6)]
 gamma=[L*Z[L].get(-1,mp.mpf(0))for L in range(1,6)]
 cs=C_from_rg(beta,gamma)
 be=[{}, {1:mp.mpf(-1)}]+[{0:b}for b in beta]
 ga=[{}]+[{0:c}for c in gamma]
 dg=[{k:i*v for k,v in G[i].items()}for i in range(1,len(G))]
 dz=[{k:i*v for k,v in Z[i].items()}for i in range(1,len(Z))]
 gr=gc(be,dg,6)
 for i in range(7):gr[i]=la_add(gr[i],{k+1:v for k,v in G[i].items()})
 zz=gc(be,dz,5); gz=gc(ga,Z,5)
 for i in range(6):zz[i]=la_add(zz[i],gz[i])
 norm=lambda a:max([abs(x)for row in a for x in row.values()]or[mp.mpf(0)])
 return dict(beta=beta,gamma=gamma,C=cs,D5=3*gamma[-1]-beta[-1],G=G,Z=Z,pole_residuals=[norm(gr),norm(zz)])

def serial(obj):
 if isinstance(obj,dict):return {str(k):serial(v)for k,v in obj.items()}
 if isinstance(obj,(list,tuple)):return [serial(v)for v in obj]
 if isinstance(obj,mp.mpf):return mp.nstr(obj,65)
 return obj

def reference():
 import sympy as s
 A=mp.pi+4*mp.log(2);Q=mp.gamma(mp.mpf(1)/4)**4/mp.pi
 K=2*mp.polygamma(1,mp.mpf(1)/4)**2-mp.pi**2*mp.polygamma(1,mp.mpf(1)/4)+A*mp.polygamma(2,mp.mpf(1)/4)/2
 fm=mp.hyper([mp.mpf(1)/4]*2+[mp.mpf(1)/2]*2,[mp.mpf(3)/4]*2+[1],1)
 fp=mp.hyper([mp.mpf(3)/4]*2+[mp.mpf(1)/2]*2,[mp.mpf(5)/4]*2+[1],1)
 Bm=mp.pi*Q*fm;Bp=64*mp.pi**3/Q*fp;P4=13*Bm-3*Bp
 L=-(5*mp.pi+26*mp.log(2))*Bm+(mp.pi+6*mp.log(2))*Bp
 P5=mp.quad(lambda y:y*abs(mp.gamma(mp.mpf(1)/4+1j*y))**14*(mp.sinh(6*mp.pi*y)+13*mp.sinh(4*mp.pi*y)+29*mp.sinh(2*mp.pi*y)),[0,mp.mpf('.25'),mp.mpf('.5'),1,2,4,8,mp.inf])/mp.pi**(mp.mpf(11)/2)
 keys=['pi','log2','Catalan','Q','K','zeta3','B4'];loc={k:s.Symbol(k)for k in keys}
 num=[mp.pi,mp.log(2),mp.catalan,Q,K,mp.zeta(3),P4]
 def val(t):return s.lambdify(list(loc.values()),s.sympify(t,locals=loc),'mpmath')(*num)
 rows=json.load(open(R/'inputs/residue_certificate.json'))
 b4=mp.fsum(val(r['wb'])*val(r['r'])for r in rows['4'])-6*P4
 c4=mp.fsum(val(r['wc'])*val(r['r'])for r in rows['4'])
 D5=mp.fsum((3*val(r['wc'])-val(r['wb']))*val(r['r'])for r in rows['5'])-54*A*P4-9*L-63*Q**2-24*P5
 b3=6*Q+mp.mpf(87)/4*A*A-3*mp.pi**2/4-4*mp.pi
 c3=mp.mpf(7)/2*A*A-mp.pi**2/6-4*mp.pi/3
 lower=(336*A**4-60*A*A*b3+108*A*A*c3+b3*b3-3*b3*c3-10*A*b4+24*A*c4)/729
 C5=lower+D5/729
 H=2*mp.pi**2/3+8*mp.catalan
 closed=(-1536*(P5+K)+384*A*P4-576*L-1728*Q**2+48*Q*(15*A*A+149*H+7*mp.pi**2)-15*A**4-30*A*A*mp.pi**2-828*A*mp.pi**3-21456*A*mp.zeta(3)-83*mp.pi**4)/46656
 return dict(A=A,Q=Q,K=K,L=L,P4=P4,P5=P5,b3=b3,c3=c3,b4=b4,c4=c4,D5=D5,lower=lower,C5=C5,assembly_minus_closed=C5-closed)

