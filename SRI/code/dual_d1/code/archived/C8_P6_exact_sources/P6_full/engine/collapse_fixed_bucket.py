"""Exact rational combination of a hash bucket of ordinary P8 words."""
from full_runner import *
from collections import defaultdict

BASE=Path('/mnt/data/P8_final_run/fibration')
prefactors=json.loads((BASE/'prefactors.json').read_text()) if (BASE/'prefactors.json').exists() else None

def run(i):
 global prefactors
 if prefactors is None:prefactors=json.loads((BASE/'prefactors.json').read_text())
 src=BASE/f'b{i:03d}.tsv';dest=ROOT/'P8_fixed4'/f'b{i:03d}.jsonl';rp=dest.with_suffix('.report.json')
 h=hashlib.sha256(src.read_bytes()).hexdigest()
 if dest.exists() and rp.exists():
  report=json.loads(rp.read_text());assert report['input_sha256']==h and report['output_sha256']==hashlib.sha256(dest.read_bytes()).hexdigest();return report
 st=time.time();groups={};nr=0
 for line in src.open():
  key,pid,mul=line.rstrip('\n').split('\t');pid=int(pid);mul=int(mul);nr+=1
  d=groups.setdefault(key,{})
  x=d.get(pid,0)+mul
  if x:d[pid]=x
  else:d.pop(pid,None)
 cache={};outn=0;seq=0;nonzero_before=sum(bool(d) for d in groups.values())
 dest.parent.mkdir(exist_ok=True);tmp=dest.with_suffix('.tmp')
 with tmp.open('w') as out:
  while groups:
   key,d=groups.popitem()
   dens={}
   for pid,mul in d.items():
    if pid not in cache:cache[pid]=rm.parseK(prefactors[pid])
    c=cache[pid];den=frozenset(c.denf.items());num=dens.get(den,K.ring.zero)+c.numer*mul
    if num:dens[den]=num
    else:dens.pop(den,None)
   heap=[]
   for den,num in dens.items():
    nn,dd=ff.cancel_factors(num,dict(den))
    if nn:heapq.heappush(heap,(len(nn)+len(dd),seq,ff.Frac(K,nn,dd)));seq+=1
   while len(heap)>1:
    _,_,a=heapq.heappop(heap);_,_,b=heapq.heappop(heap);c=a+b
    if c:heapq.heappush(heap,(len(c.numer)+len(c.denf),seq,c));seq+=1
   if heap:
    c=heap[0][2];wq,wr,ll=json.loads(key)
    def letter(pair):
     ar,b=pair
     return str(ar*GEN[6]+b)
    ww=[[],[],[],[],list(map(letter,wq)),list(map(letter,wr))]
    out.write(json.dumps([ww,ll,str(c)],separators=(',',':'))+'\n');outn+=1
   if len(groups)%500==0:print('COLLAPSE',i,'left',len(groups),'nonzero',outn,'seconds',time.time()-st,flush=True)
 tmp.replace(dest)
 report={'bucket':i,'complete':True,'input_rows':nr,'input_nonzero_vector_keys':nonzero_before,'output_rows':outn,'input_sha256':h,'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'seconds':time.time()-st,'method':'integer prefactor combination then exact factored QQ rational addition'}
 rp.write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
 print(json.dumps(run(int(sys.argv[1])),indent=2),flush=True)
