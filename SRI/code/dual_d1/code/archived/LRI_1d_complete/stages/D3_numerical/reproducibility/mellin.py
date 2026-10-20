"""128-bit Hepp-sector quadrature with independently checked Jacobi moments.
Computes raw, not vacuum-normalized, Mellin transforms.
"""
import os
import ctypes as C,mpmath as mp,numpy as np,sympy as s,time,json,argparse,itertools
from pathlib import Path
from sectors import sectors
mp.mp.dps=55
ROOT=Path(__file__).resolve().parent;LIB=C.CDLL(str(ROOT/os.environ.get('LRI_QUADLIB','quad_sector.so')));fn=LIB.integrate
ptri=np.ctypeslib.ndpointer(dtype=np.int64,flags='C_CONTIGUOUS');ptrd=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
fn.argtypes=[C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.POINTER(C.c_char_p),C.POINTER(C.c_char_p),ptri,ptrd,ptri,ptri,ptri,ptri,ptri,ptrd]+[C.c_char_p]*8

def jacobi_initial(N,beta):
 k=np.arange(1,N,dtype=float);diag=np.empty(N,dtype=np.complex128);diag[0]=(beta+1)/(beta+2);diag[1:]=.5+beta*beta/(2*(2*k+beta)*(2*k+beta+2))
 kk=np.arange(1,N,dtype=float);off=np.sqrt(kk**2*(kk+beta)**2/((2*kk+beta)**2*((2*kk+beta)**2-1))+0j)
 return np.linalg.eigvals(np.diag(diag)+np.diag(off,1)+np.diag(off,-1))
def mpjacobi(N,beta):
 a=[(beta+1)/(beta+2)]+[mp.mpf('.5')+beta*beta/(2*(2*k+beta)*(2*k+beta+2)) for k in range(1,N)]
 b=[None]+[mp.mpf(k)**2*(k+beta)**2/((2*k+beta)**2*((2*k+beta)**2-1)) for k in range(1,N)]
 norm=1/(beta+1)
 for y in b[1:]:norm*=y
 def pd(x):
  P=mp.mpc(1);prev=mp.mpc(0);der=mp.mpc(0);dp=mp.mpc(0)
  for k in range(N):
   bb=0 if k==0 else b[k];Q=(x-a[k])*P-bb*prev;dq=P+(x-a[k])*der-bb*dp;prev,P=P,Q;dp,der=der,dq
  return P,der,prev
 nodes=[];weights=[]
 for x0 in jacobi_initial(N,complex(beta)):
  x=mp.mpc(complex(x0))
  for _ in range(14):
   P,dP,prev=pd(x);dx=P/dP;x-=dx
   if abs(dx)<mp.mpf('1e-48'):break
  P,dP,prev=pd(x);nodes.append(x);weights.append(norm/(dP*prev))
 for k in range(min(8,N)):
  err=abs(sum(w*x**k for x,w in zip(nodes,weights))-1/(beta+k+1))
  if err>mp.mpf('1e-39'):raise ArithmeticError(('Jacobi moment failed',N,str(beta),k,str(err)))
 return nodes,weights

def pdata(P,xx):
 pp=s.Poly(P,*xx);return np.array(pp.monoms(),dtype=np.int64),np.array([float(x) for x in pp.coeffs()])
def prepare(sec):
 fac=sec['factors'];sl=sec['slopes'];sl2=sec['slopes2'];xx=sec['xx'];pols=sorted(set(fac)|set(sl)|set(sl2),key=str)
 dat=[pdata(P,xx) for P in pols];d=len(xx);M=max(len(c) for m,c in dat);pm=np.zeros((len(pols),M,d),dtype=np.int64);pc=np.zeros((len(pols),M));pn=[]
 for j,(m,c) in enumerate(dat):pm[j,:len(c)]=m;pc[j,:len(c)]=c;pn.append(len(c))
 e=np.array([fac.get(P,0) for P in pols],dtype=np.int64);s1=np.array([sl.get(P,0) for P in pols],dtype=np.int64);s2=np.array([sl2.get(P,0) for P in pols],dtype=np.int64)
 sm,sc=pdata(sec['S'],xx);return pm,pc,np.array(pn),e,s1,s2,sm,sc,len(sc)
def strarray(zs):
 v=[]
 for z in zs:v.extend([mp.nstr(mp.re(z),45).encode(),mp.nstr(mp.im(z),45).encode()])
 return (C.c_char_p*len(v))(*v)
def evalsector(sec,dt,q,dv,dw,N,cache):
 nodes=[];weights=[]
 for p,c,c2,qm in zip(sec['p'],sec['c'],sec['c2'],sec['qmask']):
  key=p,c,c2,qm
  if key not in cache:cache[key]=mpjacobi(N,p+qm*q+c*dv+c2*dw)
  x,w=cache[key];nodes.append(x);weights.append(w)
 pm,pc,pn,e,s1,s2,sm,sc,snm=dt;re=C.create_string_buffer(128);im=C.create_string_buffer(128)
 st=[mp.nstr(t,45).encode() for t in [mp.re(q),mp.im(q),mp.re(dv),mp.im(dv),mp.re(dw),mp.im(dw)]]
 fn(len(nodes),N,len(pn),pm.shape[1],snm,strarray(sum(nodes,[])),strarray(sum(weights,[])),pm,pc,pn,e,s1,s2,sm,sc,*st,re,im)
 return mp.mpc(re.value.decode(),im.value.decode())

def job(n,charge,N=12,samples=32,task='base',endpoint=False,center=0,radius='.13',step='0.00001',pair=None):
 ss=sectors(n,charge,endpoint,pair);dat=[prepare(sec) for sec in ss];start=time.time();vals=[];ep=mp.mpf(step)
 print('sectors',len(ss),'task',task,'n',n,'N',N,'center',center,flush=True)
 # Complex four-point rules suppress leading derivative truncation error.
 circle=[ep*mp.exp(2j*mp.pi*(j+mp.mpf('.173'))/4) for j in range(4)]
 if task=='base':params=[(mp.mpc(0),mp.mpc(0),mp.mpc(1))]
 elif task=='v':params=[(t,mp.mpc(0),1/(4*t)) for t in circle]
 elif task=='e':params=[(mp.mpc(0),t,1/(4*t)) for t in circle]
 elif task=='e2':
  ep=mp.mpf('1e-8');params=[(mp.mpc(0),ep,1/(2*ep)),(mp.mpc(0),-ep,-1/(2*ep))]
 elif task=='v2':
  ep=mp.mpf('1e-8');params=[(ep,mp.mpc(0),1/(2*ep)),(-ep,mp.mpc(0),-1/(2*ep))]
 elif task=='vv':params=[(t,mp.mpc(0),2/(4*t*t)) for t in circle]
 elif task=='ve':
  # High precision central mixed difference, O(step^2).
  ep=mp.mpf('1e-8');params=[(i*ep,j*ep,i*j/(4*ep*ep)) for i,j in itertools.product([-1,1],repeat=2)]
 else:raise ValueError(task)
 for iq in range(samples):
  w=mp.mpf(radius)*mp.exp(2j*mp.pi*(iq+mp.mpf('.127'))/samples);q=mp.mpf(center)+w;ans=mp.mpc(0)
  for dv,dw,cw in params:
   cache={};raw=mp.mpc(0)
   for sec,dt in zip(ss,dat):raw+=sec['mult']*evalsector(sec,dt,q,dv,dw,N,cache)
   if endpoint:raw/=q
   else:
    kk=ss[0]['k0']+ss[0]['kshift']*dv;raw/=q*(q+kk)*(q+kk+1)
   ans+=cw*raw
  vals.append((w,ans))
  checkpoint=dict(n=n,charge=charge,endpoint=endpoint,N=N,task=task,center=center,pair=pair,values=[[str(mp.re(ww)),str(mp.im(ww)),str(mp.re(yy)),str(mp.im(yy))] for ww,yy in vals])
  (ROOT/'data'/f'checkpoint_{n}_{int(charge)}_{int(endpoint)}_{task}_{N}_{center}_{pair}.json').write_text(json.dumps(checkpoint))
  if iq%4==0:print('q',iq,'secs',time.time()-start,'value',mp.nstr(ans,16),flush=True)
 out=dict(n=n,charge=charge,endpoint=endpoint,N=N,samples=samples,task=task,center=center,radius=radius,pair=pair,coeff={})
 for k in range(-8,2):
  v=sum(val/w**k for w,val in vals)/samples;out['coeff'][str(k)]=[str(mp.re(v)),str(mp.im(v))]
 out['seconds']=time.time()-start
 tag=f'm{n}_{int(charge)}_e{int(endpoint)}_{task}_N{N}_c{center}'+('' if pair is None else '_p'+''.join(map(str,pair)))
 path=ROOT/'data'/f'{tag}.json';path.write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('n',type=int);p.add_argument('--charge',action='store_true');p.add_argument('--endpoint',action='store_true');p.add_argument('--nodes',type=int,default=12);p.add_argument('--samples',type=int,default=32);p.add_argument('--task',default='base');p.add_argument('--center',type=int,default=0);p.add_argument('--pair');p.add_argument('--radius',default='.13');p.add_argument('--step',default='0.00001');a=p.parse_args();pair=tuple(map(int,a.pair)) if a.pair else None
 job(a.n,a.charge,a.nodes,a.samples,a.task,a.endpoint,a.center,radius=a.radius,step=a.step,pair=pair)
