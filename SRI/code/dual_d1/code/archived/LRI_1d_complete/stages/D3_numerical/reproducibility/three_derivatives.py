import mpmath as m,json,time
from pathlib import Path
m.mp.dps=65;OUT=Path(__file__).resolve().parent / 'generated_three_derivatives';OUT.mkdir(parents=True,exist_ok=True)
def M(q,p1=1,p2=1,Q=1):
 k=2-2*p1-2*p2+2*Q
 I=m.betainc(q+1-2*p1,1-2*p2,0,m.mpf('.5'))+m.betainc(q+1-2*p2,1-2*p1,0,m.mpf('.5'))
 return I/(q*(q+k)*(q+k+1))
def vv(q):return m.diff(lambda v:M(q,v,v,v),1,2)
def vd(q):
 def F(v):return v*(m.diff(lambda t:M(q,v,v,t),v,2)-2*m.diff(lambda t:M(q,t,v,v),v,2))/4
 return m.diff(F,1)
def v(q):return m.diff(lambda t:M(q,t,t,t),1)
allout={}
for name,F,center in [('vv',vv,0),('vd',vd,0),('v_at_minus1',v,-1)]:
 vals=[];start=time.time();N=56
 for j in range(N):
  w=m.mpf('.11')*m.exp(2j*m.pi*(j+m.mpf('.13'))/N);vals.append((w,F(center+w)))
  if j%16==0:print(name,j,time.time()-start,flush=True)
 out={str(k):str(m.re(sum(y/w**k for w,y in vals)/N)) for k in range(-8,1)};allout[name]=out;print(name,out,flush=True)
 (OUT/'three_derivatives.json').write_text(json.dumps(allout,indent=2))
