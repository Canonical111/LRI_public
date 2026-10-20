from full_runner import *

def run(name,i):
 folder=ROOT/name;src=folder/f'source_b{i:03d}.tsv';dest=folder/f'fixed_b{i:03d}.jsonl';rp=folder/f'fixed_b{i:03d}.report.json';sh=hashlib.sha256(src.read_bytes()).hexdigest()
 if dest.exists() and rp.exists():
  r=json.loads(rp.read_text());assert r['input_sha256']==sh and r['output_sha256']==hashlib.sha256(dest.read_bytes()).hexdigest();return r
 g={};n=0;t=time.time();seq=0
 for line in src.open():
  key,c,mu=line.rstrip('\n').split('\t');n+=1;d=g.setdefault(key,{});d[c]=d.get(c,0)+int(mu)
 cache={};nout=0;tmp=dest.with_suffix('.tmp')
 with tmp.open('w') as out:
  while g:
   key,d=g.popitem();dens={}
   for ct,mul in d.items():
    if ct not in cache:cache[ct]=rm.parseK(ct)
    c=cache[ct];den=frozenset(c.denf.items());num=dens.get(den,K.ring.zero)+c.numer*mul
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
    w,tail,ll=json.loads(key);out.write(json.dumps([[[],[],[],[],w,tail],ll,str(heap[0][2])],separators=(',',':'))+'\n');nout+=1
   if len(g)%500==0:print('F4_SUM',name,i,'left',len(g),'out',nout,time.time()-t,flush=True)
 tmp.replace(dest);r={'complete':True,'input_rows':n,'output_rows':nout,'input_sha256':sh,'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'seconds':time.time()-t};rp.write_text(json.dumps(r,indent=2));return r
if __name__=='__main__':print(json.dumps(run(sys.argv[1],int(sys.argv[2])),indent=2))
