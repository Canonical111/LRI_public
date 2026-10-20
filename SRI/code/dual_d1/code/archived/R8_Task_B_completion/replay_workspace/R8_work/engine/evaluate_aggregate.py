"""Exact terminal evaluation of a completely specified weighted source sum."""
from chunked_stage4 import *
import argparse

def evaluate(root,rows=1000):
 root=Path(root);source=root/'combined_stage4.jsonl';meta=json.loads((root/'combined_meta.json').read_text());assert hash_file(source)==meta['output_sha256'];out=root/'terminal';out.mkdir(exist_ok=True);start=0;records=[];st=time.time()
 with source.open() as f:
  for k in itertools.count():
   lines=list(itertools.islice(f,rows))
   if not lines:break
   p=out/f'part{k:04d}.json';sha=hashlib.sha256(''.join(lines).encode()).hexdigest()
   if p.exists():
    d=json.loads(p.read_text());assert d['source_sha256']==sha and d['start']==start and d['rows']==len(lines)
   else:
    begin=time.time();items=parse(lines);v,n,neg=sb.last_two_scaled(items,8);d={'status':'complete_exact_terminal_partition','start':start,'rows':len(lines),'source_sha256':sha,'value':str(v),'negative':list(map(str,neg)),'terminal_terms':n,'seconds':time.time()-begin};atomic(p,d);print('AGGREGATE_TERMINAL_PART',k,d['value'],d['seconds'],flush=True);del items
    sb.tb.br.rr.clear();sb.aword_scaled.cache_clear();sb.rparts.cache_clear()
    if (k+1)%5==0:clear()
   records.append(d);start+=len(lines)
 assert start==meta['output_rows'];v=sum((Q(d['value']) for d in records),Q(0));neg=[sum((Q(d['negative'][j]) for d in records),Q(0)) for j in range(6)]
 result={'status':'complete_weighted_boundary_aggregate','definition':'dimensionless boundary constant and six inverse-Euler moments','value':str(v),'negative':list(map(str,neg)),'source_sha256':meta['output_sha256'],'source_rows':start,'terminal_terms':sum(d['terminal_terms'] for d in records),'seconds':time.time()-st,'slices':len(records),'all_source_rows_covered_exactly':True}
 atomic(root/'result.json',result);print('AGGREGATE_RESULT',json.dumps(result),flush=True)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--rows',type=int,default=1000);a=p.parse_args();evaluate(a.root,a.rows)
