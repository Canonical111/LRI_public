"""Full exact ordered integration with rational endpoint coefficients grouped
before fibration. No constant period projection. This changes only addition order.
"""
from full_runner import *

def moving_stage(paths,idx,N):
 groups={};st=time.time();rows=0
 def put(key,c):
  if not c:return
  dd=frozenset(c.denf.items());p=groups.setdefault(key,{});v=p.get(dd,K.ring.zero)+c.numer
  if v:p[dd]=v
  else:p.pop(dd,None)
 for path in paths:
  for line in Path(path).open():
   ww,ll,tx=json.loads(line);words=tuple(tuple(rm.parseK(a) for a in w) for w in ww);logs=tuple(sorted(ll));R=rm.parseK(tx);assert not any(words[:idx-1]);active=words[idx-1]
   pol,po=apart(R,idx)
   for kin,a,p,pref in [('poly',K.zero,p,c) for p,c in pol.items()]+[('pole',a,p,c) for (a,p),c in po.items()]:
    audit_basis(kin,a,p,active,idx)
    for wa,c in integrate_basis(kin,a,p,active,idx).items():
     for wb,cb in endpoint_value(c,wa,idx,GEN[idx+1]).items():put((wb,words[idx:],logs),pref*cb)
     for wb,cb in endpoint_value(c,wa,idx,K.zero,lower=True).items():
      assert not wb;put(((),words[idx:],logs),-pref*cb)
   rows+=1
   if rows%100==0:print('MOVING_STAGE',idx,rows,len(groups),time.time()-st,flush=True)
 out={};seq=0;total=len(groups)
 while groups:
  key,ds=groups.popitem();heap=[]
  for den,num in ds.items():
   nn,dd=ff.cancel_factors(num,dict(den))
   if nn:heapq.heappush(heap,(len(nn)+len(dd),seq,ff.Frac(K,nn,dd)));seq+=1
  while len(heap)>1:
   _,_,a=heapq.heappop(heap);_,_,b=heapq.heappop(heap);c=a+b
   if c:heapq.heappush(heap,(len(c.numer)+len(c.denf),seq,c));seq+=1
  if heap:out[key]=heap[0][2]
  if len(groups)%1000==0:print('COLLAPSED_MOVING',total-len(groups),total,len(out),time.time()-st,flush=True)
 return out,rows

def fibrate_stage(group,idx,N):
 out={};st=time.time();n=len(group);j=0
 while group:
  (moving,tail,ll),c=group.popitem();j+=1
  for w,mu in endpoint_fibrate(moving,idx+1).items():
   for sh,num in shuffle(w,tail[0]).items():
    ww=((),)*idx+(sh,)+tail[1:];addto(out,(ww,ll),c*mu*num)
  if j%500==0:
   out=clean(out)
   print('FIBRATE_STAGE',idx,j,n,len(out),time.time()-st,flush=True)
 return clean(out)

def dump_moving(path,group):
 tmp=path.with_suffix('.tmp');tmp.parent.mkdir(parents=True,exist_ok=True)
 with tmp.open('w') as f:
  for (w,tail,ll),c in group.items():f.write(json.dumps([list(map(str,w)),[list(map(str,a)) for a in tail],list(ll),str(c)],separators=(',',':'))+'\n')
 tmp.replace(path)
def load_moving(path):
 out={}
 for line in Path(path).open():
  w,tail,ll,c=json.loads(line);out[(tuple(rm.parseK(a) for a in w),tuple(tuple(rm.parseK(x) for x in a) for a in tail),tuple(ll))]=rm.parseK(c)
 return out
if __name__=='__main__':
 if sys.argv[1]=='check':
  ix=int(sys.argv[2]);source=ROOT/'B8_stage3_buckets'/f'bucket{ix:03}.jsonl';g,n=moving_stage([source],4,6);ng=len(g);ans=fibrate_stage(g,4,6);ref=dict(load(ROOT/'B8_after4'/f'b{ix:03}'/'stage4.jsonl'));dif=ans.copy()
  for k,v in ref.items():addto(dif,k,-v)
  assert not clean(dif),len(clean(dif));report={'source_rows':n,'moving_terms':ng,'full_output_rows':len(ans),'all_coefficients_exact_equal':True}
  (ROOT/'data/group_before_fibration_check.json').write_text(json.dumps(report,indent=2));print('EXACT_GENERAL_GROUP_CHECK',report,flush=True)
 else:
  spec=json.loads(Path(sys.argv[1]).read_text());folder=ROOT/spec['output'];folder.mkdir(exist_ok=True);path=folder/'moving.jsonl';idx=spec['idx'];N=spec['N']
  if not path.exists():
   paths=[ROOT/r['path'] for r in spec['inputs']];g,n=moving_stage(paths,idx,N);dump_moving(path,g)
   (folder/'moving_report.json').write_text(json.dumps({'source_rows':n,'moving_terms':len(g),'idx':idx,'N':N,'inputs':[{'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],'output_sha256':hashlib.sha256(path.read_bytes()).hexdigest()},indent=2))
  else:g=load_moving(path)
  if '--moving-only' in sys.argv:print('MOVING_ONLY_DONE',len(g),flush=True);sys.exit(0)
  ans=fibrate_stage(g,idx,N);dest=folder/f'stage{idx}.jsonl';dump(dest,ans)
  (folder/'report.json').write_text(json.dumps({'complete':True,'output_rows':len(ans),'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}));print('GROUPED_STAGE_DONE',idx,len(ans),flush=True)
