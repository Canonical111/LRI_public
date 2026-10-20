from full_runner import *
name=sys.argv[1];folder=ROOT/name;meta=json.loads((folder/'source_manifest.json').read_text());nb=meta['buckets'];total=folder/'moving_total.jsonl';groups={};inputs=[];seq=0;st=time.time();nin=0
for i in range(nb):
 p=folder/f'moving_b{i:03d}.jsonl';r0=json.loads((folder/f'moving_b{i:03d}.report.json').read_text());assert r0['complete'] and r0['output_sha256']==hashlib.sha256(p.read_bytes()).hexdigest();inputs.append({'path':str(p),'sha256':r0['output_sha256']})
 for line in p.open():
  w,tail,ll,ct=json.loads(line);nin+=1;key=json.dumps([w,tail,ll],separators=(',',':'));dd=groups.setdefault(key,{})
  if meta['kappa']==1 and not meta['interval_factor']:
   # Every moving hyperlog has at most logarithmic growth. A proper rational
   # prefactor therefore contributes O(epsilon log^k epsilon), not a finite term.
   R=rm.parseK(ct);poly,_=apart(R,6);R=sum((c*GEN[6]**p for p,c in poly.items()),K.zero)
   if not R:continue
   ct=str(R)
  dd[ct]=dd.get(ct,0)+1
 print('F4_COLLECT',name,i,nin,len(groups),time.time()-st,flush=True)
outrows=0;tmp=total.with_suffix('.tmp')
with tmp.open('w') as out:
 while groups:
  key,vals=groups.popitem();byden={}
  for ct,mu in vals.items():
   c=rm.parseK(ct);den=frozenset(c.denf.items());nn=byden.get(den,K.ring.zero)+c.numer*mu
   if nn:byden[den]=nn
   else:byden.pop(den,None)
  heap=[]
  for den,num in byden.items():
   nn,dd=ff.cancel_factors(num,dict(den))
   if nn:heapq.heappush(heap,(len(nn)+len(dd),seq,ff.Frac(K,nn,dd)));seq+=1
  while len(heap)>1:
   _,_,a=heapq.heappop(heap);_,_,b=heapq.heappop(heap);c=a+b
   if c:heapq.heappush(heap,(len(c.numer)+len(c.denf),seq,c));seq+=1
  if heap:
   w,tail,ll=json.loads(key);out.write(json.dumps([w,tail,ll,str(heap[0][2])],separators=(',',':'))+'\n');outrows+=1
  if len(groups)%2000==0:print('F4_MOVING_SUM',name,len(groups),outrows,time.time()-st,flush=True)
tmp.replace(total);(folder/'moving_total_report.json').write_text(json.dumps({'complete':True,'input_rows':nin,'output_rows':outrows,'sources':inputs,'output_sha256':hashlib.sha256(total.read_bytes()).hexdigest(),'growth_projection':meta['kappa']==1 and not meta['interval_factor'],'seconds':time.time()-st},indent=2));print('F4_MOVING_SUM_DONE',name,outrows,flush=True)
