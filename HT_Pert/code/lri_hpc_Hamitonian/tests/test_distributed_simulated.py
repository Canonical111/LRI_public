"""Exercise MPI data/ownership protocol with blocking in-process collectives.

This is NOT a real MPI benchmark and cannot validate the MPI ABI, cluster
runtime, network performance, or interprocess race/failure behavior.
"""
import sys,types,threading,copy,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np,numba
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lri_hpc.solver import compute
fake=types.ModuleType('mpi4py');fake.MPI=types.SimpleNamespace(INT64_T='i8',DOUBLE='f8',SUM='sum')
sys.modules['mpi4py']=fake
class Group:
 def __init__(self,n):self.n=n;self.bar=threading.Barrier(n,timeout=90);self.slots=[None]*n
class Comm:
 def __init__(self,g,r):self.g=g;self.r=r
 def Get_rank(self):return self.r
 def Get_size(self):return self.g.n
 def call(self,x,fn):
  self.g.slots[self.r]=x;self.g.bar.wait()
  y=fn(self.g.slots);self.g.bar.wait();return y
 def Alltoall(self,s,r):
  vals=self.call(np.array(s[0],copy=True),lambda a:np.array([x[self.r] for x in a]));r[0][:]=vals
 def Alltoallv(self,s,r):
  data,cnt,dis,_=s
  def out(slots):
   ans=np.empty_like(r[0]).reshape(-1)
   for sender,(a,c,d) in enumerate(slots):
    seg=a.reshape(-1)[d[self.r]:d[self.r]+c[self.r]]
    assert len(seg)==r[1][sender]
    ans[r[2][sender]:r[2][sender]+r[1][sender]]=seg
   return ans
  ans=self.call((np.array(data,copy=True),np.array(cnt),np.array(dis)),out);r[0].reshape(-1)[:]=ans
 def Allreduce(self,s,r,op=None):r[0][:]=self.call(np.array(s[0],copy=True),lambda a:np.sum(a,axis=0))
 def allgather(self,x):return self.call(x,lambda a:copy.deepcopy(a))
 def bcast(self,x,root=0):return self.call(x,lambda a:copy.deepcopy(a[root]))

rows=[]
for task,degree in [('thermal',7),('phi6',5)]:
 numba.set_num_threads(1);target=compute(8,task,degree)
 for n in [2,3]:
  g=Group(n)
  def run(r):
   numba.set_num_threads(1)
   try:return compute(8,task,degree,comm=Comm(g,r))
   except BaseException:g.bar.abort();raise
  with ThreadPoolExecutor(n) as ex:result=list(ex.map(run,range(n)))
  errors=[]
  for got in result:
   for pres in ([None] if task=='thermal' else ['raw','vacuum_subtracted']):
    a=got[pres] if pres else got;b=target[pres] if pres else target
    for k in ['C','r','g']+(['D6'] if task=='phi6' else []):
     errors.append(float(np.max(abs(np.array(a[k])-b[k]))))
     np.testing.assert_allclose(a[k],b[k],rtol=2e-11,atol=1e-7)
  row={'task':task,'simulated_ranks':n,'max_abs_difference':max(errors),'ranks':result[0]['ranks']}
  rows.append(row);print(task,n,max(errors),flush=True)
(Path(__file__).resolve().parents[1]/'benchmarks/simulated_mpi_validation.json').write_text(json.dumps(rows,indent=2)+'\n')
