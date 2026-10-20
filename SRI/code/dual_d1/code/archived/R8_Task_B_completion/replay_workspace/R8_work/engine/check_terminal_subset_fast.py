"""Production implementation on the exact source range of the reference check."""
from chunked_stage4 import *
source=sb.ROOT/'remaining_aggregate/remaining_spec_work/combined_stage4.jsonl'
with source.open() as inp:
 for _ in range(80000):next(inp)
 lines=list(itertools.islice(inp,16))
assert len(lines)==16
items=parse(lines);st=time.time();v,n,neg=sb.last_two_scaled(items,8)
d={'source_start':80000,'source_rows':16,'source_sha256':hashlib.sha256(''.join(lines).encode()).hexdigest(),'value':str(v),'negative':list(map(str,neg)),'method':'production moving-letter endpoint; exact GMP scalars','seconds':time.time()-st}
atomic(sb.ROOT/'independent_terminal_tail_fast.json',d);print(json.dumps(d),flush=True)
