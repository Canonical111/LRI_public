"""Exact sum of all 64 complete stage-four moving-letter expressions.
No fibration, endpoint evaluation, or weight projection is performed here.
"""
from pathlib import Path
import json,hashlib,time,sys,heapq
ROOT=Path(__file__).resolve().parent.parent

def main():
 from full_runner import rm,K,ff
 from group_before_fibration import dump_moving
 inputs=[ROOT/'B8_moving4'/f'b{i:03}' for i in range(64)]
 for p in inputs:
  assert (p/'report.json').exists(),p
 folder=ROOT/'B8_moving4_total';folder.mkdir(exist_ok=True)
 reportpath=folder/'report.json';dest=folder/'moving.jsonl'
 if dest.exists() and reportpath.exists():
  old=json.loads(reportpath.read_text());assert hashlib.sha256(dest.read_bytes()).hexdigest()==old['output_sha256'];return
 groups={};total=0;records=[];st=time.time()
 for p in inputs:
  r=json.loads((p/'report.json').read_text());src=p/'moving.jsonl';digest=hashlib.sha256(src.read_bytes()).hexdigest();assert r['complete'] and digest==r['output_sha256'];rows=0
  for line in src.open():
   w,tail,ll,c=json.loads(line);key=(tuple(rm.parseK(x) for x in w),tuple(tuple(rm.parseK(x) for x in a) for a in tail),tuple(sorted(ll)))
   val=rm.parseK(c);d=frozenset(val.denf.items());g=groups.setdefault(key,{});num=g.get(d,K.ring.zero)+val.numer
   if num:g[d]=num
   else:g.pop(d,None)
   if not g:groups.pop(key,None)
   rows+=1
  assert rows==r['moving_rows'];total+=rows;records.append({'file':str(src),'sha256':digest,'rows':rows})
  rm.parseK.cache_clear()
  print('MOVING_ADDED',p.name,rows,len(groups),time.time()-st,flush=True)
 out={};seq=0;ng=len(groups)
 while groups:
  key,ds=groups.popitem();heap=[]
  for den,num in ds.items():
   nn,dd=ff.cancel_factors(num,dict(den))
   if nn:heapq.heappush(heap,(len(nn)+len(dd),seq,ff.Frac(K,nn,dd)));seq+=1
  while len(heap)>1:
   _,_,a=heapq.heappop(heap);_,_,b=heapq.heappop(heap);v=a+b
   if v:heapq.heappush(heap,(len(v.numer)+len(v.denf),seq,v));seq+=1
  if heap:out[key]=heap[0][2]
  if len(groups)%5000==0:print('MOVING_SUM_REDUCED',ng-len(groups),len(out),time.time()-st,flush=True)
 dump_moving(dest,out)
 report={'complete':True,'input_blocks':64,'input_rows':total,'input_files':records,'output_rows':len(out),'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'full_constant_periods_retained':True,'seconds':time.time()-st}
 reportpath.write_text(json.dumps(report,indent=2));print('ALL_MOVING_COMBINED',report['input_rows'],report['output_rows'],flush=True)
if __name__=='__main__':main()
