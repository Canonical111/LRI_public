from pathlib import Path
import json,time
import sympy as s
from read_expression import load
from asymptotic_gpl import extract_rows
ROOT=Path(__file__).resolve().parent
out=[]
for tag,n,p in [('A5_vv',5,0),('A5_vd',5,-1),('Q6_v',6,0)]:
 start=time.time();rows=json.loads((ROOT/(tag+'_negative.json')).read_text());old=load(ROOT/'series'/f'{tag}_p{p}.expr')
 new=extract_rows(rows,n-1,p,None);assert s.expand(new-old)==0,(tag,p)
 r={'tag':tag,'power':p,'rows':len(rows),'exact_residual':'0','seconds':time.time()-start};out.append(r);print(r,flush=True)
(ROOT/'fast_extraction_checks.json').write_text(json.dumps(out,indent=2))
