"""Power-log moment quadrature for full endpoint tails.
Real Gauss-Legendre interpolation, analytically continued Mellin moments.
NOT a rational projection or an integer-relation fitting procedure.
"""
from pathlib import Path
import argparse,ctypes as C,itertools,json,time,os
from functools import lru_cache
import mpmath as mp
import numpy as np
import sympy as s
from full_tail_sectors import sectors
mp.mp.dps=60
ROOT=Path(__file__).resolve().parent
QMAX=3

def jet_mul(a,b):return [sum(a[i]*b[n-i] for i in range(n+1)) for n in range(4)]
def jet_div(a,b):
 out=[]
 for n in range(4):out.append((a[n]-sum(b[i]*out[n-i] for i in range(1,n+1)))/b[0])
 return out

def moment_weights(N,betas):
 xx,ww=mp.gauss_quadrature(N,'legendre');xx=[(x+1)/2 for x in xx];ww=[w/2 for w in ww]
 leg=[[mp.mpf(1),2*x-1] for x in xx]
 for row,x in zip(leg,xx):
  for k in range(1,N-1):row.append(((2*k+1)*(2*x-1)*row[k]-k*row[k-1])/(k+1))
 out={}
 for be in betas:
  moments=[jet_div([1,0,0,0],[be+1,1,0,0])]
  for l in range(1,N):moments.append(jet_mul(moments[-1],jet_div([be-l+1,1,0,0],[be+l+1,1,0,0])))
  mat=[[w*sum((2*l+1)*leg[j][l]*moments[l][k] for l in range(N))*mp.factorial(k) for k in range(4)] for j,w in enumerate(ww)]
  # Recheck analytically continued power-log moments at several monomial degrees.
  err=max(abs(sum(row[k]*xx[j]**n for j,row in enumerate(mat))-(-1)**k*mp.factorial(k)/(be+n+1)**(k+1)) for n in [0,1,min(5,N-1),N-1] for k in range(4))
  assert err<mp.mpf('1e-45'),('moment exactness failed',N,be,err)
  out[be]=[(row[0],row[1]/row[0],row[2]/row[0]-(row[1]/row[0])**2,row[3]/row[0]-3*row[1]*row[2]/row[0]**2+2*(row[1]/row[0])**3) for row in mat]
 return xx,out

def strarray(v,complex_=True):
 if complex_:ls=[mp.nstr(w,48).encode() for z in v for w in (mp.re(z),mp.im(z))]
 else:ls=[mp.nstr(z,48).encode() for z in v]
 return (C.c_char_p*len(ls))(*ls)

def prep(sec):
 xx=sec['xx'];polfac=sorted(set(sec['factors'])|{p for k,p in sec['pairs'] if p!=1},key=str)
 prs=[s.Poly(p,*xx) for p in polfac];d=len(xx);M=max(len(p.terms()) for p in prs)
 mons=np.zeros((len(prs),M,d),dtype=np.int64);coef=np.zeros((len(prs),M),dtype=np.int64);pn=[]
 for j,p in enumerate(prs):
  terms=p.terms();pn.append(len(terms))
  for k,(ex,c) in enumerate(terms):mons[j,k]=ex;coef[j,k]=int(c)
 ex=np.array([sec['factors'].get(p,0) for p in polfac],dtype=np.int64)
 keys=sorted(sec['pairs'],key=lambda kp:(kp[0],str(kp[1])))
 pk=np.array([k for k,p in keys],dtype=np.int64);pi=np.array([-1 if p==1 else polfac.index(p) for k,p in keys],dtype=np.int64)
 ps=np.array([sec['pairs'][k] for k in keys],dtype=np.int64)
 return mons,coef,np.array(pn,dtype=np.int64),ex,pk,pi,ps,np.array(sec['c'],dtype=np.int64)

def job(n,N,samples=32,radius='.27',threads=4,quad=False,center=0,limit=None):
 start=time.time();ss=sectors(n);nq=samples//2
 # Nodes have conjugate partners at j and samples-1-j.
 qs=[mp.mpf(center)+mp.mpf(radius)*mp.exp(2j*mp.pi*(j+mp.mpf('.5'))/samples) for j in range(nq)]
 pp=sorted(set(p for sec in ss for p in sec['p']))
 xx,tab=moment_weights(N,[q+p for q in qs for p in pp]);qsarg=strarray(qs);nodes=strarray(xx,False)
 lib=C.CDLL(str(ROOT/('log_moment_quad128.so' if quad else 'log_moment_quad.so')));fn=lib.integral
 pi=np.ctypeslib.ndpointer(dtype=np.int64,flags='C_CONTIGUOUS');fn.argtypes=[C.c_int]*7+[C.POINTER(C.c_char_p)]*3+[pi]*8+[C.POINTER(C.c_char)]
 vals=[[mp.mpc(0) for _ in range(5)] for q in qs];records=[]
 tag=f'full_n{n}_N{N}_s{samples}_r{radius}_q{center}_'+('quad' if quad else 'ld')
 fnout=ROOT/'data'/f'{tag}.json';cachepath=ROOT/'data'/f'{tag}_sectors.json'
 if cachepath.exists():
  cache=json.loads(cachepath.read_text()); records=cache['sectors']
  for sec,rec in zip(ss,records):
   for iq,values in enumerate(rec['values']):
    for k,(r,i) in enumerate(values):vals[iq][k]+=sec['mult']*mp.mpc(r,i)
 for isec,sec in enumerate(ss[len(records):],start=len(records)):
  data=prep(sec);npol,nmon=data[0].shape[:2];weights=strarray([v for q in qs for p in sec['p'] for row in tab[q+p] for v in row]);res=C.create_string_buffer(nq*5*200)
  t=time.time();fn(n-2,N,nq,npol,nmon,len(data[4]),threads,nodes,weights,qsarg,*data,res)
  v=[[mp.mpc(res.raw[(5*iq+k)*200:].split(b'\0',1)[0].decode(),res.raw[(5*iq+k)*200+100:].split(b'\0',1)[0].decode()) for k in range(5)] for iq in range(nq)]
  for iq in range(nq):
   for k in range(5):vals[iq][k]+=sec['mult']*v[iq][k]
  records.append({'sector':isec,'values':[[[str(mp.re(z)),str(mp.im(z))] for z in row] for row in v]})
  cachepath.write_text(json.dumps({'settings':dict(n=n,N=N,samples=samples,radius=radius,quad=quad,center=center),'sectors':records}))
  print('SECTOR',isec+1,'/',len(ss),'sec',round(time.time()-t,2),'total',round(time.time()-start,2),flush=True)
  if limit is not None and len(records)>=limit:break
 if len(records)!=len(ss):return
 values={k:[] for k in ['base','v','d','vd']};a=-mp.mpf(n)/2
 for q,(j0,j1,j11,j2,j12) in zip(qs,vals):
  i0=1/q-1/(q+1);i1=-1/q**2+1/(q+1)**2;i2=2/q**3-2/(q+1)**3;i3=-6/q**4+6/(q+1)**4
  values['base'].append(i0*j0/q)
  values['v'].append((2*a*i1*j0+2*i0*j1)/q)
  values['d'].append((a*i2*j0+2*i1*j1+i0*j2)/q)
  values['vd'].append((2*a*a*i3*j0+(a*j0+6*a*j1)*i2+(2*j1+4*j11+2*a*j2)*i1+(j2+2*j12)*i0)/q)
 coeff={}
 for name,vs in values.items():
  coeff[name]={str(k):mp.nstr(sum(mp.re(v*(q-center)**(-k)) for q,v in zip(qs,vs))/nq,40) for k in range(-10,1)}
 out={'settings':dict(n=n,N=N,samples=samples,radius=radius,quad=quad,center=center),'method':'Gauss-Legendre polynomial interpolation with exactly continued power-log moments; no projection','coeff':coeff,'volume_log':{name:str(-mp.mpf(row['-2'])) for name,row in coeff.items()},'seconds':time.time()-start,'complete_sectors':len(ss),'not_interval_certified':True}
 fnout.write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('n',type=int);p.add_argument('--nodes',type=int,default=12);p.add_argument('--samples',type=int,default=32);p.add_argument('--radius',default='.27');p.add_argument('--threads',type=int,default=4);p.add_argument('--quad',action='store_true');p.add_argument('--center',type=int,default=0);p.add_argument('--limit',type=int);args=p.parse_args();job(args.n,args.nodes,args.samples,args.radius,args.threads,args.quad,args.center,args.limit)
