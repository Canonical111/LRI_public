"""Sector-grouped version, same continued power-log quadrature."""
from full_mellin import *

def prepared_groups(ss):
 pairs=sorted(set((tuple(sec['p']),tuple(sec['c'])) for sec in ss));d=len(ss[0]['xx'])
 pp=sorted(set(p for sec in ss for p in sec['factors'])|set(p for sec in ss for k,p in sec['pairs'] if p!=1),key=str)
 prs=[s.Poly(p,*ss[0]['xx']) for p in pp];nm=max(len(p.terms()) for p in prs)
 mons=np.zeros((len(pp),nm,d),dtype=np.int64);coef=np.zeros((len(pp),nm),dtype=np.int64);pn=[]
 for j,p in enumerate(prs):
  terms=p.terms();pn.append(len(terms))
  for k,(ex,c) in enumerate(terms):mons[j,k]=ex;coef[j,k]=int(c)
 exp=np.array([[sec['factors'].get(p,0) for p in pp] for sec in ss],dtype=np.int64)
 npmax=max(len(sec['pairs']) for sec in ss);pk=np.zeros((len(ss),npmax),dtype=np.int64);pi=pk.copy();ps=pk.copy();pn2=[]
 for i,sec in enumerate(ss):
  keys=sorted(sec['pairs'],key=lambda a:(a[0],str(a[1])));pn2.append(len(keys))
  for j,(k,p) in enumerate(keys):pk[i,j]=k;pi[i,j]=-1 if p==1 else pp.index(p);ps[i,j]=sec['pairs'][k,p]
 group=np.array([pairs.index((tuple(sec['p']),tuple(sec['c']))) for sec in ss],dtype=np.int64)
 multi=np.array([sec['mult'] for sec in ss],dtype=np.int64);cs=np.array([c for p,c in pairs],dtype=np.int64)
 return pairs,(mons,coef,np.array(pn,dtype=np.int64),exp,pk,pi,ps,np.array(pn2,dtype=np.int64),group,multi,cs)

def compute(n,N,samples=48,radius='.27',threads=4,quad=False,center=0,chunk=32768,limit=None):
 if n not in (4,6): raise ValueError('This native grouped kernel is capacity-checked only for n=4 or n=6; do not use it for n=8.')
 start=time.time();ss=sectors(n);nq=samples//2;pairs,data=prepared_groups(ss);ng=len(pairs);d=n-2
 qs=[mp.mpf(center)+mp.mpf(radius)*mp.exp(2j*mp.pi*(j+mp.mpf('.5'))/samples) for j in range(nq)]
 pp=sorted(set(p for sec in ss for p in sec['p']));xx,tab=moment_weights(N,[q+p for q in qs for p in pp]);qsarg=strarray(qs);nodes=strarray(xx,False)
 weights=strarray([v for q in qs for p,c in pairs for be in p for row in tab[q+be] for v in row]);print('PREPARED',ng,len(ss),data[0].shape,N,time.time()-start,flush=True)
 lib=C.CDLL(str(ROOT/('grouped_kahan128.so' if quad else 'grouped_quad.so')));fn=lib.grouped
 it=np.ctypeslib.ndpointer(dtype=np.int64,flags='C_CONTIGUOUS');fn.argtypes=[C.c_int]*9+[C.POINTER(C.c_char_p)]*3+[it]*11+[C.c_longlong]*2+[C.POINTER(C.c_char)]
 total=N**d;tag=f'gfull_n{n}_N{N}_s{samples}_r{radius}_q{center}_'+('quad_kahan' if quad else 'ld')
 folder=ROOT/'data'/tag;folder.mkdir(exist_ok=True)
 vals=[[mp.mpc(0) for _ in range(5)] for q in qs]
 for ib,begin in enumerate(range(0,total,chunk)):
  end=min(begin+chunk,total);dest=folder/f'chunk_{begin}_{end}.json'
  if dest.exists():rec=json.loads(dest.read_text());v=[[mp.mpc(*z) for z in row] for row in rec['values']]
  else:
   res=C.create_string_buffer(nq*5*200);st=time.time()
   fn(d,N,nq,data[0].shape[0],data[0].shape[1],len(ss),data[4].shape[1],ng,threads,nodes,weights,qsarg,*data,begin,end,res)
   v=[[mp.mpc(res.raw[(5*iq+k)*200:].split(b'\0',1)[0].decode(),res.raw[(5*iq+k)*200+100:].split(b'\0',1)[0].decode()) for k in range(5)] for iq in range(nq)]
   rec={'settings':dict(n=n,N=N,samples=samples,radius=radius,quad=quad,center=center),'begin':begin,'end':end,'values':[[[str(mp.re(z)),str(mp.im(z))] for z in row] for row in v],'seconds':time.time()-st}
   dest.write_text(json.dumps(rec))
   print('CHUNK',ib+1,(total+chunk-1)//chunk,begin,end,'seconds',rec['seconds'],'total',time.time()-start,flush=True)
  for iq in range(nq):
   for k in range(5):vals[iq][k]+=v[iq][k]
  if limit is not None and ib+1>=limit:return
 values={k:[] for k in ['base','v','vv','d','vd']};a=-mp.mpf(n)/2
 for q,(j0,j1,j11,j2,j12) in zip(qs,vals):
  i0=1/q-1/(q+1);i1=-1/q**2+1/(q+1)**2;i2=2/q**3-2/(q+1)**3;i3=-6/q**4+6/(q+1)**4
  values['vv'].append((4*a*a*i2*j0+8*a*i1*j1+4*i0*j11)/q);values['base'].append(i0*j0/q);values['v'].append((2*a*i1*j0+2*i0*j1)/q);values['d'].append((a*i2*j0+2*i1*j1+i0*j2)/q)
  values['vd'].append((2*a*a*i3*j0+(a*j0+6*a*j1)*i2+(2*j1+4*j11+2*a*j2)*i1+(j2+2*j12)*i0)/q)
 coeff={name:{str(k):mp.nstr(sum(mp.re(v*(q-center)**(-k)) for q,v in zip(qs,vs))/nq,40) for k in range(-10,1)} for name,vs in values.items()}
 out={'settings':dict(n=n,N=N,samples=samples,radius=radius,quad=quad,center=center),'method':'Grouped full power-log Mellin integration; no projection','coeff':coeff,'volume_log':{name:str(-mp.mpf(row['-2'])) for name,row in coeff.items()},'volume_finite':{name:row['-1'] for name,row in coeff.items()},'seconds':time.time()-start,'complete_sectors':len(ss),'complete_groups':len(pairs),'not_interval_certified':True}
 (ROOT/'data'/f'{tag}.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('n',type=int);p.add_argument('--nodes',type=int,default=16);p.add_argument('--samples',type=int,default=48);p.add_argument('--radius',default='.27');p.add_argument('--threads',type=int,default=4);p.add_argument('--quad',action='store_true');p.add_argument('--center',type=int,default=0);p.add_argument('--chunk',type=int,default=32768);p.add_argument('--limit',type=int);a=p.parse_args();compute(a.n,a.nodes,a.samples,a.radius,a.threads,a.quad,a.center,a.chunk,a.limit)
