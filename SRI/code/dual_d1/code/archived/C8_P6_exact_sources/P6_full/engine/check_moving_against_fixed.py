"""Compare the optimized final-variable fibration with a complete ordinary-word stage."""
import full_runner as b
import final_fibration as tf
import json,time,heapq
from fractions import Fraction as F
r=b.ROOT;source=r/'moving_s3/b000.jsonl';reference=r/'weighted_final/b000/stage3.jsonl';groups={};st=time.time();n=0
zs=(b.zeta2,b.zeta3,b.zeta5) # no weight-seven boundary constants needed here

def put(key,c):
 if not c:return
 d=frozenset(c.denf.items());row=groups.setdefault(key,{});v=row.get(d,b.K.ring.zero)+c.numer
 if v:row[d]=v
 else:row.pop(d,None)
for line in source.open():
 w,tail,ll,ct=json.loads(line);pref=b.rm.parseK(ct)
 for (fw,ll,zm),c in tf.expand(w,tail,ll).items():
  assert zm[3]==0
  val=pref*b.K(c.numerator)/c.denominator
  for z,p in zip(zs,zm[:3]):val*=z**p
  put((tuple(fw),tuple(ll)),val)
 n+=1
 if n%1000==0:print('FAST_EXPANDED',n,len(groups),time.time()-st,flush=True)
for line in reference.open():
 ww,ll,ct=json.loads(line);assert not any(ww[:-1]);key=(tuple(int(b.rm.parseK(a)) for a in ww[-1]),tuple(ll));put(key,-b.rm.parseK(ct))
print('REFERENCE_SUBTRACTED',len(groups),time.time()-st,flush=True)
count=0;seq=0
while groups:
 key,row=groups.popitem();heap=[]
 for den,num in row.items():
  nn,dd=b.ff.cancel_factors(num,dict(den))
  if nn:heapq.heappush(heap,(len(nn)+len(dd),seq,b.ff.Frac(b.K,nn,dd)));seq+=1
 while len(heap)>1:
  _,_,a=heapq.heappop(heap);_,_,c=heapq.heappop(heap);v=a+c
  if v:heapq.heappush(heap,(len(v.numer)+len(v.denf),seq,v));seq+=1
 assert not heap,(key,str(heap[0][2]))
 count+=1
 if count%20000==0:print('EXACT_ZEROS',count,time.time()-st,flush=True)
report={'complete':True,'all_period_coefficients_retained':True,'complete_source_rows':n,'ordinary_word_coefficients_checked':count,'every_rational_difference_exact_zero':True,'seconds':time.time()-st}
(r/'control/fibration_full_block.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
