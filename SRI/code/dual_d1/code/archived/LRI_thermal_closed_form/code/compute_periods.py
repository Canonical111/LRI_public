"""Mellin coefficients of cutoff ordered Coulomb-gas integrals.
Gaussian Laguerre quadrature and derivative (not subtractive) sector regularization.
No physical RG constants are assigned by this program.
"""
import numpy as np, sympy as s, itertools,math,json,sys,time,os
os.environ.setdefault("NUMBA_NUM_THREADS", "8")
from build_sectors import build_sectors
from scipy.special import roots_laguerre
from numba import njit,prange
from pathlib import Path
B=Path(__file__).resolve().parent / 'data'
B.mkdir(exist_ok=True)
@njit
def muljet(a,b,ii,jj,kk,ns):
 c=np.zeros(ns)
 for n in range(len(ii)):c[kk[n]]+=a[ii[n]]*b[jj[n]]
 return c
@njit
def jetpoly(coords,monos,coefs,inds):
 out=np.zeros(len(inds))
 d=len(coords)
 for j in range(len(inds)):
  for mo in range(len(coefs)):
   vv=coefs[mo]
   for ax in range(d):
    n=monos[mo,ax];k=inds[j,ax]
    if k>n:vv=0.;break
    b=1.
    for r in range(k):b*= (n-r)/(r+1.)
    vv*= b*coords[ax]**(n-k)
   out[j]+=vv
 return out
@njit(parallel=True)
def make_coeffs(points,inds,ii,jj,kk,pol_m,pol_c,pol_len,expo,slopes,sm,sc,depth,prefactor,derivative_v):
 npnt=len(points);ns=len(inds);C=np.zeros((npnt,depth+1));Cv=np.zeros_like(C);Ls=np.zeros(npnt)
 derivfactor=1.
 for ax in range(points.shape[1]):
  for j in range(1,inds[-1,ax]+1):derivfactor*=j
 for point in prange(npnt):
  coords=points[point];F=np.zeros(ns);F[0]=prefactor;Log=np.zeros(ns)
  for ff in range(len(expo)):
   P=jetpoly(coords,pol_m[ff,:pol_len[ff]],pol_c[ff,:pol_len[ff]],inds)
   p0=P[0];P/=p0;P[0]=0.
   power=np.zeros(ns);power[0]=1.;fac=np.zeros(ns);fac[0]=1.
   lg=np.zeros(ns);lg[0]=np.log(p0)
   binom=1.
   for n in range(1,depth+1):
    power=muljet(power,P,ii,jj,kk,ns)
    binom*= (expo[ff]-n+1.)/n
    for j in range(ns):
     fac[j]+=binom*power[j]
     lg[j]+=((-1.)**(n-1)/n)*power[j]
   fac*=p0**expo[ff]
   F=muljet(F,fac,ii,jj,kk,ns)
   if derivative_v:Log+=slopes[ff]*lg
  FV=muljet(F,Log,ii,jj,kk,ns) if derivative_v else np.zeros(ns)
  P=jetpoly(coords,sm,sc,inds);p0=P[0];Ls[point]=np.log(p0);P/=p0;P[0]=0.
  power=np.zeros(ns);power[0]=1.
  for k in range(depth+1):
   if k:power=muljet(power,P,ii,jj,kk,ns)
   J=muljet(F,power,ii,jj,kk,ns);C[point,k]=derivfactor*J[-1]
   if derivative_v:
    JV=muljet(FV,power,ii,jj,kk,ns);Cv[point,k]=derivfactor*JV[-1]
 return C,Cv,Ls
@njit
def kernel(q,t,m,p):
 lt=np.log(t)
 if m==0:
  v=np.exp((p+q)*lt);return v,lt*v
 tq=np.exp(q*lt);v=0.j;dv=0.j
 for k in range(m):
  fac=(-1.)**k
  for jf in range(1,k+1):fac/=jf
  for jf in range(1,m-k):fac/=jf
  den=q-k
  tk=t**k
  v+=fac*(tk-tq)/den
  dv+=fac*(-den*tq*lt-(tk-tq))/(den*den)
 return v,dv
@njit(parallel=True)
def integrate_q(qs,points,weights,C,Cv,Ls,int_axes,ms,ps,cs,derivative_v):
 vals=np.zeros(len(qs),dtype=np.complex128);vvals=vals.copy()
 for iq in prange(len(qs)):
  q=qs[iq];binoms=np.empty(C.shape[1],dtype=np.complex128);binoms[0]=1.
  for k in range(1,len(binoms)):binoms[k]=binoms[k-1]*(-q-k+1.)/k
  ans=0.j;av=0.j
  for j in range(len(points)):
   h=0.j;hv=0.j
   for k in range(len(binoms)):
    h+=binoms[k]*C[j,k]
    if derivative_v:hv+=binoms[k]*Cv[j,k]
   kp=1.j*0+1.;kv=0.j
   for ix in range(len(int_axes)):
    ax=int_axes[ix];v,dv=kernel(q,points[j,ax],ms[ix],ps[ix]);dv*=cs[ix]
    kv=kv*v+kp*dv;kp*=v
   ep=np.exp(-q*Ls[j]);ans+=weights[j]*ep*h*kp
   if derivative_v:av+=weights[j]*ep*(hv*kp+h*kv)
  vals[iq]=ans;vvals[iq]=av
 return vals,vvals

def polydata(P,xx):
 pp=s.Poly(P,*xx);return np.array(pp.monoms(),dtype=np.int64),np.array([float(c) for c in pp.coeffs()])
def factors(H,Ws,S,nW,xx):
 cn,num=s.factor_list(s.fraction(H)[0]);cd,den=s.factor_list(s.fraction(H)[1]);facs={}
 for p,e in num:facs[p]=facs.get(p,0)+int(e)
 for p,e in den:facs[p]=facs.get(p,0)-int(e)
 # slopes from log(Wsmooth) + nW log(S)
 slopes={}
 for pol,mul in [(s.fraction(Ws)[0],1),(s.fraction(Ws)[1],-1),(S,nW)]:
  cc,ff=s.factor_list(pol)
  for p,e in ff:slopes[p]=slopes.get(p,0)+mul*int(e)
 for p in slopes:
  if p not in facs:facs[p]=0
 polys=list(facs); data=[polydata(p,xx) for p in polys];nm=max(len(x[1]) for x in data);d=len(xx)
 pm=np.zeros((len(data),nm,d),dtype=np.int64);pc=np.zeros((len(data),nm));pl=[]
 for j,(m,c) in enumerate(data):pm[j,:len(c)]=m;pc[j,:len(c)]=c;pl.append(len(c))
 return pm,pc,np.array(pl),np.array([facs[p] for p in polys],dtype=np.float64),np.array([slopes.get(p,0) for p in polys],dtype=np.float64),float(cn/cd)

def main(name,N,deriv=True,idx=None,radius=.19,samples=48):
 sectors=build_sectors(name)
 lag,ww=roots_laguerre(N);nodes=np.exp(-lag)
 # Nodes beyond ~exp(-200) contribute negligibly and can overflow some powers.
 keep=lag<180.;nodes=nodes[keep];ww=ww[keep]
 qs=radius*np.exp(2j*np.pi*(np.arange(samples)+.25)/samples)
 total=np.zeros(samples,dtype=complex);totalv=total.copy();start=time.time()
 for sector_i,sec in enumerate(sectors):
  if idx is not None and sector_i!=idx:continue
  xx=sec['xx'];d=len(xx);p=sec['p'];c=sec['c'];m=[max(0,-pp) for pp in p]
  pm,pc,pl,expo,slopes,pref=factors(sec['H0'],sec['W'],sec['S'],sec['nW'],xx);sm,sc=polydata(sec['S'],xx)
  st=np.zeros(samples,dtype=complex);stv=st.copy()
  for orders in itertools.product(*[range(mm+1) if mm else (0,) for mm in m]):
   int_axes=[j for j in range(d) if orders[j]==m[j]]
   boundary=[j for j in range(d) if j not in int_axes]
   # Multi-indices, with last entry the requested spatial derivative.
   inds=np.array(list(itertools.product(*[range(o+1) for o in orders])),dtype=np.int64)
   lookup={tuple(a):i for i,a in enumerate(inds)};trip=[]
   for i,a in enumerate(inds):
    for j,b in enumerate(inds):
     v=tuple(a+b)
     if v in lookup:trip.append((i,j,lookup[v]))
   ii,jj,kk=[np.array([t[j] for t in trip],dtype=np.int64) for j in range(3)]
   if int_axes:
    gidx=list(itertools.product(range(len(nodes)),repeat=len(int_axes)));pts=np.zeros((len(gidx),d));weights=np.ones(len(gidx))
    for j,g in enumerate(gidx):
     for ax,k in zip(int_axes,g):pts[j,ax]=nodes[k];weights[j]*=ww[k]
   else:pts=np.zeros((1,d));weights=np.ones(1)
   C,Cv,Ls=make_coeffs(pts,inds,ii,jj,kk,pm,pc,pl,expo,slopes,sm,sc,sum(orders),pref,deriv)
   va,vav=integrate_q(qs,pts,weights,C,Cv,Ls,np.array(int_axes,dtype=np.int64),np.array([m[a] for a in int_axes],dtype=np.int64),np.array([p[a] for a in int_axes],dtype=np.int64),np.array([c[a] for a in int_axes],dtype=np.float64),deriv)
   coeff=np.ones(len(qs),dtype=complex);coeffv=np.zeros(len(qs),dtype=complex)
   for ax in boundary:
    j=orders[ax];den=qs+p[ax]+j+1.;v=1/(math.factorial(j)*den);dv=-c[ax]/(math.factorial(j)*den**2) if deriv else np.zeros_like(den)
    coeffv=coeffv*v+coeff*dv;coeff*=v
   st+=coeff*va;stv+=coeff*vav+coeffv*va
  total+=sec['mult']*st;totalv+=sec['mult']*stv
  print(name,N,'sector',sector_i,'mult',sec['mult'],'A0',np.mean(st),'Av0',np.mean(stv),'secs',time.time()-start,flush=True)
 out={'N':N,'idx':idx,'radius':radius,'samples':samples,'coeff':{},'vcoeff':{} if deriv else None}
 for k in range(-5,3):
  val=np.mean(total/qs**k);vval=np.mean(totalv/qs**k);out['coeff'][str(k)]=[float(val.real),float(val.imag)]
  if deriv:out['vcoeff'][str(k)]=[float(vval.real),float(vval.imag)]
 print(json.dumps(out,indent=2),flush=True)
 fn=f'{name}_jet_N{N}'+('' if idx is None else f'_s{idx}')+f'_r{radius:g}_m{samples}.json';json.dump(out,open(B/fn,'w'),indent=2)
if __name__ == '__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('name', choices=['Q4','Z4','G5'])
 parser.add_argument('--nodes',type=int,default=96)
 parser.add_argument('--radius',type=float,default=.19)
 parser.add_argument('--samples',type=int,default=48)
 parser.add_argument('--sector',type=int,default=None)
 args=parser.parse_args()
 if args.nodes<12 or not 0<args.radius<.5 or args.samples<24:
  parser.error('Use nodes >=12, 0<radius<.5, and samples >=24.')
 main(args.name,args.nodes,args.name=='Q4',args.sector,args.radius,args.samples)
