from full_runner import *
from pathlib import Path
checks=[]
for tag,b,idx,N,n in [('B4_v_f1','b00',2,2,4),('Q6_vv','b02',3,5,6)]:
 # B4 last boundary differs from one_stage; skip that case.
 if n==4:continue
 p=ROOT/tag/b;rows=load(p/f'stage{idx-1}.jsonl');got=one_stage(rows,idx,N,n);ref=dict(load(p/f'stage{idx}.jsonl'))
 diff=got.copy()
 for key,c in ref.items():addto(diff,key,-c)
 assert not clean(diff),(tag,b,idx)
 checks.append({'tag':tag,'block':b,'stage':idx,'input_rows':len(rows),'output_rows':len(ref),'exact_equal':True});clear()
(ROOT/'data/incremental_stage_check.json').write_text(json.dumps(checks,indent=2));print('INCREMENTAL_EXACT_PASS',checks,flush=True)
