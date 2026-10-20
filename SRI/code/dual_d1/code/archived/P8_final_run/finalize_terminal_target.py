from pathlib import Path
from fractions import Fraction as F
import json,hashlib,time,sys
sys.path.insert(0,'/mnt/data/P8_final_run');import period_algebra as pa
folder=Path(sys.argv[1]);target=sys.argv[2];scale=F(sys.argv[3]);src=folder/'terminal_fibration' if (folder/'terminal_fibration').exists() else folder
nb=json.loads((src/'report.json').read_text())['sum_buckets'];out={};records=[];st=time.time();nr=0
for i in range(nb):
 p=src/'terminal'/f'b{i:03d}.jsonl';rp=src/'terminal'/f'b{i:03d}.report.json'
 if not rp.exists():raise RuntimeError(('missing terminal',i))
 r=json.loads(rp.read_text());assert r['complete'] and r['output_sha256']==hashlib.sha256(p.read_bytes()).hexdigest();assert r['input_sha256']==hashlib.sha256((src/f'b{i:03d}.tsv').read_bytes()).hexdigest();records.append(r)
 for line in p.open():
  w,ll,zm,c=json.loads(line);key=(tuple(w),tuple(ll),tuple(zm));val=out.get(key,F(0))+scale*F(c)
  if val:out[key]=val
  else:out.pop(key,None)
  nr+=1
print('RAW_SUM',target,nr,len(out),time.time()-st,flush=True)
rawpath=folder/(target+'_raw.jsonl')
with rawpath.open('w') as f:
 for (w,ll,z),c in out.items():f.write(json.dumps([w,ll,z,str(c)],separators=(',',':'))+'\n')
canon={};count=0
for (w,ll,zm),c in out.items():
 pref={():c}
 for k in ll:pref=pa.mul(pref,pa.log(k))
 for k,n in zip([2,3,5,7],zm):
  if n:pref=pa.mul(pref,pa.powp(pa.atom('Z'+str(k)),n))
 pa.add(canon,pa.mul(pref,pa.R(w)));count+=1
 if count%20000==0:print('CANON',target,count,len(canon),time.time()-st,flush=True)
fp=folder/(target+'.expr');fp.write_text(pa.dump(canon));positive=[]
for m,c in canon.items():
 for a,n in m:
  if a.startswith('R_') and any(not x.startswith('m') and x!='0' for x in a.split('_')[1:]):positive.append(a)
report={'complete_terminal_sum':True,'target':target,'prefactor':str(scale),'inputs':nb,'source_terms':nr,'raw_period_terms':len(out),'canonical_terms':len(canon),'rational_projection':str(canon.get((),F(0))),'positive_letter_periods':sorted(set(positive)),'exact_expression':str(fp),'sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'seconds':time.time()-st}
(folder/(target+'_report.json')).write_text(json.dumps(report,indent=2));print('TARGET_DONE',report,flush=True)
