from full_runner import *
from fractions import Fraction

def aggregate(specpath,outpath):
 spec=json.loads(Path(specpath).read_text()); groups={};st=time.time();inputs=[];total=0
 def normalize():
  nonlocal groups
  new={};seq=0
  for key,g in groups.items():
   heap=[]
   for den,num in g.items():
    nn,dd=ff.cancel_factors(num,dict(den))
    if nn:
     val=ff.Frac(K,nn,dd);heapq.heappush(heap,(len(nn)+len(dd),seq,val));seq+=1
   while len(heap)>1:
    _,_,a=heapq.heappop(heap);_,_,b=heapq.heappop(heap);v=a+b
    if v:heapq.heappush(heap,(len(v.numer)+len(v.denf),seq,v));seq+=1
   if heap:
    v=heap[0][2];new[key]={frozenset(v.denf.items()):v.numer}
  groups=new
 for i,rec in enumerate(spec['inputs']):
  path=ROOT/rec['path'];rows=load(path);weight=K.from_expr(str(rec['weight']));total+=len(rows)
  for key,c in rows:
   c=c*weight
   if not c:continue
   g=groups.setdefault(key,{});den=frozenset(c.denf.items());nn=g.get(den,K.ring.zero)+c.numer
   if nn:g[den]=nn
   else:g.pop(den,None)
  inputs.append({'path':rec['path'],'weight':str(rec['weight']),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':len(rows)})
  del rows;normalize();clear()
  print('ADDED',i+1,len(spec['inputs']),total,len(groups),time.time()-st,flush=True)
 out={}
 for key,g in groups.items():
  for den,num in g.items():
   if num:out[key]=ff.Frac(K,num,dict(den))
 dump(Path(outpath),out)
 report={'input_rows':total,'output_rows':len(out),'inputs':inputs,'full_constants':True,'output_sha256':hashlib.sha256(Path(outpath).read_bytes()).hexdigest(),'seconds':time.time()-st}
 Path(outpath).with_suffix('.assembly.json').write_text(json.dumps(report,indent=2));print('AGGREGATED',report['input_rows'],report['output_rows'],flush=True)
if __name__=='__main__':aggregate(sys.argv[1],sys.argv[2])
