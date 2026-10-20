"""Differentiate continued Gaussian quadrature analytically.
Long-double integrand arithmetic; validate against 128-bit finite differences.
"""
import ctypes as C,mpmath as mp,numpy as np,time,json,argparse
from pathlib import Path
from mellin import mpjacobi,prepare,strarray,ROOT
from sectors import sectors
mp.mp.dps=55
LIB=C.CDLL(str(ROOT/'analytic_sector.so'));fn=LIB.integrate
ptri=np.ctypeslib.ndpointer(dtype=np.int64,flags='C_CONTIGUOUS');ptrd=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
fn.argtypes=[C.c_int]*5+[C.POINTER(C.c_char_p)]*4+[ptri,ptrd,ptri,ptri,ptri,ptri,ptrd]+[C.c_char_p]*4

def jacobi_dot(N,beta):
 xs,ws=mpjacobi(N,beta)
 a=[(beta+1)/(beta+2)]+[mp.mpf('.5')+beta*beta/(2*(2*k+beta)*(2*k+beta+2)) for k in range(1,N)]
 ad=[1/(beta+2)**2]+[beta/((2*k+beta)*(2*k+beta+2))-beta**2*(2*k+beta+1)/((2*k+beta)**2*(2*k+beta+2)**2) for k in range(1,N)]
 b=[0]+[mp.mpf(k)**2*(k+beta)**2/((2*k+beta)**2*((2*k+beta)**2-1)) for k in range(1,N)]
 logbd=[0]+[2/(k+beta)-2/(2*k+beta)-2*(2*k+beta)/((2*k+beta)**2-1) for k in range(1,N)]
 bd=[x*y for x,y in zip(b,logbd)];lnorm=-1/(beta+1)+sum(logbd[1:]);xd=[];wd=[]
 for x in xs:
  p=mp.mpc(1);px=mp.mpc(0);pb=mp.mpc(0);pxx=mp.mpc(0);pxb=mp.mpc(0)
  prev=pxprev=pbprev=pxxprev=pxbprev=mp.mpc(0)
  for k in range(N):
   pp=(x-a[k])*p-b[k]*prev
   xx=p+(x-a[k])*px-b[k]*pxprev
   bb=-ad[k]*p+(x-a[k])*pb-bd[k]*prev-b[k]*pbprev
   xxx=2*px+(x-a[k])*pxx-b[k]*pxxprev
   xxb=pb-ad[k]*px+(x-a[k])*pxb-bd[k]*pxprev-b[k]*pxbprev
   prev,p=p,pp;pxprev,px=px,xx;pbprev,pb=pb,bb;pxxprev,pxx=pxx,xxx;pxbprev,pxb=pxb,xxb
  dx=-pb/px;dw=lnorm-(pxb+pxx*dx)/px-(pbprev+pxprev*dx)/prev
  xd.append(dx);wd.append(dw)
 for k in range(min(N,8)):
  val=sum(w*(dw*x**k+(k*x**(k-1)*dx if k else 0)) for x,w,dx,dw in zip(xs,ws,xd,wd))
  err=abs(val+1/(beta+k+1)**2)
  if err>mp.mpf('1e-36'):raise ArithmeticError(('Derivative moment',beta,k,err))
 return xs,ws,xd,wd

def evaluate(sec,dt,q,N,cache,direction):
 nd=[];we=[];dd=[];ww=[]
 for p,cv,ce,qm in zip(sec['p'],sec['c'],sec['c2'],sec['qmask']):
  key=p,qm
  if key not in cache:cache[key]=jacobi_dot(N,p+qm*q)
  xs,ws,xd,wd=cache[key];slope=ce if direction=='e' else cv
  nd.append(xs);we.append(ws);dd.append([slope*t for t in xd]);ww.append([slope*t for t in wd])
 pm,pc,pn,e,sv,se,sm,sc,snm=dt;sl=se if direction=='e' else sv
 re=C.create_string_buffer(128);im=C.create_string_buffer(128)
 fn(len(nd),N,len(pn),pm.shape[1],snm,strarray(sum(nd,[])),strarray(sum(we,[])),strarray(sum(dd,[])),strarray(sum(ww,[])),pm,pc,pn,e,sl,sm,sc,mp.nstr(mp.re(q),45).encode(),mp.nstr(mp.im(q),45).encode(),re,im)
 return mp.mpc(re.value.decode(),im.value.decode())

def job(n,charge,N=12,samples=24,direction='e',endpoint=True,radius='.13',one=False):
 ss=sectors(n,charge,endpoint,None);dat=[prepare(sec) for sec in ss];start=time.time();vals=[]
 for iq in range(1 if one else samples):
  w=mp.mpf(radius)*mp.exp(2j*mp.pi*(iq+mp.mpf('.127'))/samples);cache={};ans=mp.mpc(0)
  for sec,dt in zip(ss,dat):ans+=sec['mult']*evaluate(sec,dt,w,N,cache,direction)
  if endpoint:ans/=w
  else:raise NotImplementedError('Add derivative of radial denominator for no-endpoint mode.')
  vals.append((w,ans));print('q',iq,'secs',time.time()-start,'value',mp.nstr(ans,22),flush=True)
  (ROOT/'data'/f'analytic_checkpoint_{n}_{int(charge)}_{N}_{direction}.json').write_text(json.dumps([[str(mp.re(q)),str(mp.im(q)),str(mp.re(v)),str(mp.im(v))] for q,v in vals]))
 if one:return
 out=dict(n=n,charge=charge,endpoint=endpoint,N=N,samples=samples,task='analytic_'+direction,center=0,radius=radius,coeff={})
 for k in range(-8,2):
  vv=sum(val/q**k for q,val in vals)/samples;out['coeff'][str(k)]=[str(mp.re(vv)),str(mp.im(vv))]
 out['seconds']=time.time()-start
 (ROOT/'data'/f'm{n}_{int(charge)}_e1_analytic{direction}_N{N}_c0.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('n',type=int);p.add_argument('--charge',action='store_true');p.add_argument('--nodes',type=int,default=12);p.add_argument('--samples',type=int,default=24);p.add_argument('--direction',default='e');p.add_argument('--one',action='store_true');a=p.parse_args();job(a.n,a.charge,a.nodes,a.samples,a.direction,one=a.one)
