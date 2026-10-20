"""Parallel exact terminal source partitions with complete independent assembly."""
from chunked_stage4 import *
import argparse,subprocess

def evaluate(root,rows=1000,workers=1,worker=None,directory='terminal_parallel'):
 root=Path(root);source=root/'combined_stage4.jsonl';meta=json.loads((root/'combined_meta.json').read_text());assert hash_file(source)==meta['output_sha256'];out=root/directory;out.mkdir(exist_ok=True);st=time.time()
 if workers>1 and worker is None:
  children=[]
  for j in range(workers):
   log=(out/f'worker{j}.log').open('w');cmd=[sys.executable,str(Path(__file__).resolve()),str(root),'--rows',str(rows),'--workers',str(workers),'--worker',str(j),'--directory',directory];children.append((subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT),log))
  codes=[]
  for child,log in children:codes.append(child.wait());log.close()
  assert all(c==0 for c in codes),codes
 start=0;records=[];evaluated=0
 with source.open() as f:
  for k in itertools.count():
   lines=list(itertools.islice(f,rows))
   if not lines:break
   if worker is not None and k%workers!=worker:start+=len(lines);continue
   dest=out/f'part{k:04d}.json';sha=hashlib.sha256(''.join(lines).encode()).hexdigest()
   if dest.exists():
    d=json.loads(dest.read_text());assert d['source_sha256']==sha and d['start']==start and d['rows']==len(lines) and d['status']=='complete_exact_terminal_partition'
   else:
    if workers>1 and worker is None:raise RuntimeError(('missing worker output',k))
    begin=time.time();items=parse(lines);v,n,neg=sb.last_two_scaled(items,8);d={'status':'complete_exact_terminal_partition','start':start,'rows':len(lines),'source_sha256':sha,'value':str(v),'negative':list(map(str,neg)),'terminal_terms':n,'seconds':time.time()-begin,'worker':worker};atomic(dest,d);print('EXACT_TERMINAL_PART',k,d['value'],d['seconds'],flush=True);del items
    sb.tb.br.rr.clear();sb.aword_scaled.cache_clear();sb.rparts.cache_clear();evaluated+=1
    if evaluated%5==0:clear()
   records.append(d);start+=len(lines)
 assert start==meta['output_rows']
 if worker is not None:
  d={'status':'worker_partitions_complete','worker':worker,'workers':workers,'partitions':len(records),'seconds':time.time()-st};atomic(out/f'worker{worker}.json',d);print('TERMINAL_WORKER_DONE',json.dumps(d),flush=True);return d
 # The master re-hashes every disjoint slice and counts all rows itself.
 assert sum(r['rows'] for r in records)==meta['output_rows']
 value=sum((Q(d['value']) for d in records),Q(0));negative=[sum((Q(d['negative'][i]) for d in records),Q(0)) for i in range(6)]
 result={'status':'complete_weighted_boundary_aggregate','definition':'dimensionless boundary constant and six inverse-Euler moments','value':str(value),'negative':list(map(str,negative)),'source_sha256':meta['output_sha256'],'source_rows':start,'terminal_terms':sum(d['terminal_terms'] for d in records),'seconds':time.time()-st,'slices':len(records),'all_source_rows_covered_exactly':True,'workers':workers,'terminal_directory':directory}
 atomic(root/'result_parallel.json',result);print('EXACT_AGGREGATE_RESULT',json.dumps(result),flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--rows',type=int,default=1000);p.add_argument('--workers',type=int,default=1);p.add_argument('--worker',type=int);p.add_argument('--directory',default='terminal_parallel');a=p.parse_args();evaluate(a.root,a.rows,a.workers,a.worker,a.directory)
